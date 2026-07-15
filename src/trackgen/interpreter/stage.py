"""The Interpreter — pipeline stage 1 (PHASE_2 §6).

`interpret()` turns validated params into a complete `GenerationPlan`,
following the §6 resolution order exactly. Its only source of randomness is
`stream_rng` (the `random`-module boundary stays in `seeds.py`), and it makes
**exactly one** integer draw — the auto-path tempo draw (§6.1). When the user
supplies a tempo, the RNG is never constructed.

`generate_plan()` is the thin orchestrator entry: it resolves the pack,
validates the raw params, derives the master seed (`fresh_master()` is the only
entropy entry and lives only here, at the API boundary), and calls `interpret`.
"""

import math
from typing import Any, Literal, cast

from trackgen.interpreter.moods import apply_overrides, formulas, load_moods
from trackgen.interpreter.params import (
    ParamError,
    Params,
    parse_tonic,
    validate_params,
)
from trackgen.packs.loader import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.schema.ir import (
    Budgets,
    GenerationPlan,
    Key,
    MoodVector,
    SeedSpec,
    StylePackRef,
    SwingSpec,
    TimbreDirectives,
    TimeSignature,
)
from trackgen.seeds import (
    fresh_master,
    from_base36,
    master_from_string,
    stream_rng,
)

# PHASE_2 §6.3 — the engine mode ladder and per-rung valence bands. Rung index
# is the position in this tuple; the ideal rung for a valence is the first band
# (scanned brightest-first) that contains it.
_MODE_LADDER: tuple[str, ...] = ("major", "mixolydian", "dorian", "minor", "phrygian")

# PHASE_2 §6.4 — swing long:short ratio vs effective BPM (piecewise-linear;
# clamped flat below 90 and above 240). Ordered ascending by BPM.
_SWING_TABLE: tuple[tuple[float, float], ...] = (
    (90.0, 2.60),
    (120.0, 2.24),
    (140.0, 2.00),
    (160.0, 1.80),
    (200.0, 1.40),
    (240.0, 1.00),
)


class ParamsInvalid(Exception):
    """Raised by `generate_plan` when `validate_params` reports any error.

    Carries the full structured catalog (§3.1) so callers can surface every
    violation, not just the first.
    """

    def __init__(self, errors: list[ParamError]) -> None:
        self.errors = errors
        super().__init__(f"{len(errors)} parameter validation error(s): {errors}")


def _ideal_rung(valence: float) -> int:
    """PHASE_2 §6.3 — the mode-ladder rung whose valence band contains V."""
    if valence >= 0.25:
        return 0  # major
    if valence >= 0.00:
        return 1  # mixolydian
    if valence >= -0.30:
        return 2  # dorian
    if valence >= -0.65:
        return 3  # minor
    return 4  # phrygian


def _resolve_mode(user_mode: str | None, valence: float, modes: list[str]) -> str:
    """PHASE_2 §6.3 — pick the mode. A user mode (already validated ∈ pack menu)
    wins; otherwise choose the pack-menu mode minimizing rung distance to the
    valence-ideal rung, ties breaking toward the brighter (lower) rung."""
    if user_mode is not None:
        return user_mode
    ideal = _ideal_rung(valence)
    # `modes` is the ordered pack menu (ascending ladder order); scanning it and
    # keeping the strict minimum makes the lower (brighter) rung win ties.
    best_mode = modes[0]
    best_distance = abs(_MODE_LADDER.index(best_mode) - ideal)
    for mode in modes[1:]:
        distance = abs(_MODE_LADDER.index(mode) - ideal)
        if distance < best_distance:
            best_mode = mode
            best_distance = distance
    return best_mode


def _swing_ratio_from_table(effective_bpm: float) -> float:
    """PHASE_2 §6.4 — long:short ratio `r` by piecewise-linear interpolation on
    effective BPM, clamped flat outside [90, 240]."""
    lo_bpm, lo_r = _SWING_TABLE[0]
    if effective_bpm <= lo_bpm:
        return lo_r
    hi_bpm, hi_r = _SWING_TABLE[-1]
    if effective_bpm >= hi_bpm:
        return hi_r
    for (b0, r0), (b1, r1) in zip(_SWING_TABLE, _SWING_TABLE[1:], strict=False):
        if b0 <= effective_bpm <= b1:
            frac = (effective_bpm - b0) / (b1 - b0)
            return r0 + frac * (r1 - r0)
    raise AssertionError("unreachable: effective_bpm is within table bounds")


def _resolve_swing(pack: StylePack, tempo_bpm: int) -> SwingSpec | None:
    """PHASE_2 §6.4 — swing from pack feel + tempo (never mood). Pack
    `swingRatio`, when set, is the final ratio and bypasses the table."""
    interp = pack.interpreter
    assert interp is not None
    feel = interp.feel
    if feel in ("straight8", "straight16"):
        return None

    subdivision: Literal["8", "16"]
    if feel == "swing8":
        subdivision = "8"
        effective_bpm = float(tempo_bpm)
    else:  # swing16
        subdivision = "16"
        effective_bpm = 2.0 * tempo_bpm

    if interp.swing_ratio is not None:
        ratio = round(interp.swing_ratio, 3)
    else:
        r = _swing_ratio_from_table(effective_bpm)
        ratio = round(r / (1 + r), 3)
    return SwingSpec(ratio=ratio, subdivision=subdivision)


def interpret(
    params: Params,
    pack: StylePack,
    master_seed: int,
    overrides: dict[str, int],
) -> GenerationPlan:
    """PHASE_2 §6 — resolve validated params into a complete `GenerationPlan`.

    The single seeded draw is the auto-path tempo draw; when `params.tempo_bpm`
    is given (or the degenerate tempo window), `stream_rng` is never called.
    """
    interp = pack.interpreter
    if interp is None:
        raise ValueError(
            f"pack {pack.manifest.id!r} has no interpreter config; "
            "cannot run the Interpreter stage"
        )

    # Steps 2-5: mood -> anchor -> formulas -> overrides.
    mood = params.mood or interp.default_mood
    row = load_moods().moods[mood]
    valence, arousal = row.valence, row.arousal
    derived = apply_overrides(row.overrides, formulas(valence, arousal))

    # Step 6: tempo (§6.2) — THE single seeded draw, auto-path only.
    tempo_range = pack.manifest.tempo_range
    if params.tempo_bpm is not None:
        tempo = params.tempo_bpm  # user value wins; RNG stream untouched
    else:
        center = float(derived["tempoCenter"])  # unrounded
        lo = max(round(0.9 * center), tempo_range[0])
        hi = min(round(1.1 * center), tempo_range[1])
        if lo > hi:
            # Degenerate window: clamp the center into the pack range. No draw.
            tempo = max(tempo_range[0], min(round(center), tempo_range[1]))
        else:
            rng = stream_rng(master_seed, overrides, "interpreter")
            tempo = lo + rng.randrange(hi - lo + 1)

    # Step 7: key (§6.3, deterministic).
    user_mode = params.key.mode if params.key is not None else None
    user_tonic = params.key.tonic if params.key is not None else None
    resolved_mode = _resolve_mode(user_mode, valence, interp.modes)
    if user_tonic is not None:
        tonic_pc = parse_tonic(user_tonic)
    else:
        tonic_pc = parse_tonic(interp.tonics[resolved_mode][0])
    assert tonic_pc is not None  # validated / pack-authored, always parseable
    key = Key(tonic_pc=tonic_pc, mode=resolved_mode)

    # Step 8: swing (§6.4, deterministic).
    swing = _resolve_swing(pack, tempo)

    # Step 9: budgets + timbre. Density and dissonance pass through the pack's
    # expression ranges (§4.2); all other derived values are global.
    d_lo, d_hi = interp.expression_ranges.density
    x_lo, x_hi = interp.expression_ranges.dissonance
    budgets = Budgets(
        note_density=round(d_lo + float(derived["noteDensityNorm"]) * (d_hi - d_lo), 3),
        dissonance=round(x_lo + float(derived["dissonanceNorm"]) * (x_hi - x_lo), 3),
        dynamics_base=float(derived["dynamicsBase"]),
        dynamics_range=float(derived["dynamicsRange"]),
        articulation_legato=float(derived["articulationLegato"]),
        layers_max=int(derived["layersMax"]),
        harmonic_rhythm_base=float(derived["harmonicRhythmBase"]),
        register_bias=float(derived["registerBias"]),
    )
    timbre = TimbreDirectives(
        brightness=float(derived["brightness"]),
        attack_hardness=float(derived["attackHardness"]),
        space=float(derived["space"]),
    )

    # Step 10: role-flavor merge (default -> named preset -> user roleFlavors).
    preset = params.ensemble_preset or "default"
    merged: dict[str, str] = {
        str(role): flavor for role, flavor in interp.ensembles["default"].items()
    }
    merged.update(
        {str(role): flavor for role, flavor in interp.ensembles.get(preset, {}).items()}
    )
    merged.update(params.role_flavors)

    # Step 11: length (D-S8). All ints -> exact.
    max_length_sec = params.max_length_sec if params.max_length_sec is not None else 180
    max_length_ticks = math.floor(max_length_sec * tempo * 8)

    ts = pack.manifest.time_signatures[0]

    # Step 12: assemble.
    return GenerationPlan(
        style_pack=StylePackRef(id=pack.manifest.id, version=pack.manifest.version),
        seed=SeedSpec(master=master_seed, overrides=overrides),
        key=key,
        tempo_bpm=tempo,
        time_signature=TimeSignature(
            numerator=ts[0], denominator=cast(Literal[2, 4, 8, 16], ts[1])
        ),
        swing=swing,
        max_length_ticks=max_length_ticks,
        role_flavors=merged,
        mood_vector=MoodVector(valence=valence, arousal=arousal),
        budgets=budgets,
        timbre_directives=timbre,
    )


def generate_plan(raw_params: dict[str, Any]) -> GenerationPlan:
    """PHASE_2 §6 orchestrator entry — resolve, validate, seed, and interpret.

    `fresh_master()` is the only entropy entry and lives only on this path,
    never inside `interpret`.
    """
    style_family = raw_params.get("styleFamily")
    pack = resolve_pack(style_family) if isinstance(style_family, str) else None

    errors = validate_params(raw_params, pack)
    if errors:
        raise ParamsInvalid(errors)

    assert pack is not None  # a resolved-pack failure would have raised above

    params = Params.model_validate(raw_params)

    if params.seed is not None:
        master = from_base36(params.seed)
    elif params.seed_text is not None:
        master = master_from_string(params.seed_text)
    else:
        master = fresh_master()

    overrides_int = {
        name: from_base36(value) for name, value in params.seed_overrides.items()
    }

    return interpret(params, pack, master, overrides_int)
