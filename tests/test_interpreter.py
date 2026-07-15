"""Interpreter-stage tests (PHASE_2 §6, §11.4-§11.6).

The §6.5 worked examples and the §6.5 seed vector are **normative** — golden
fixtures. Never edit an expected number to match code output; a divergence is
an implementation bug (or a golden-value-arbitration escalation), per
ROADMAP §3 and SESSION_02 §7.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trackgen.interpreter.params import Params
from trackgen.interpreter.stage import (
    ParamsInvalid,
    _resolve_mode,
    _resolve_swing,
    _swing_ratio_from_table,
    generate_plan,
    interpret,
)
from trackgen.packs.loader import registered_styles, resolve_pack
from trackgen.schema.ir import GenerationPlan
from trackgen.seeds import derive, stream_seed, to_base36

MASTER = 3735928559  # 0xDEADBEEF; base36 "1ps9wxb"

_U64_MAX = (1 << 64) - 1


# --- §6.5 golden worked examples (normative — do not edit to match code) -----


def _assert_example_1(plan: GenerationPlan) -> None:
    """PHASE_2 §6.5 Example 1 — {styleFamily: pop_rock, seed: 1ps9wxb}."""
    assert plan.style_pack.id == "pop_rock"
    assert plan.style_pack.version == "0.1.0"
    assert plan.seed.master == MASTER
    assert plan.seed.overrides == {}
    assert plan.key.tonic_pc == 4  # tonics.major[0] = E
    assert plan.key.mode == "major"  # happy V=+0.75 -> major
    assert plan.tempo_bpm == 123  # center 118.1 -> [106,130]; draw = 123
    assert plan.time_signature.numerator == 4
    assert plan.time_signature.denominator == 4
    assert plan.swing is None  # feel: straight8
    assert plan.max_length_ticks == 177120  # 180 s x 123 BPM x 8
    assert plan.role_flavors == {
        "drums": "acoustic_kit",
        "bass": "electric_fingered",
        "comping": "clean_electric",
        "pads": "warm_analog",
    }
    assert plan.mood_vector.valence == pytest.approx(0.75, abs=1e-9)
    assert plan.mood_vector.arousal == pytest.approx(0.4, abs=1e-9)
    b = plan.budgets
    assert b.note_density == pytest.approx(0.648, abs=1e-9)  # 0.20 + 0.690 x 0.65
    assert b.dissonance == pytest.approx(0.132, abs=1e-9)  # 0.05 + 0.235 x 0.35
    assert b.dynamics_base == pytest.approx(0.65, abs=1e-9)
    assert b.dynamics_range == pytest.approx(0.21, abs=1e-9)
    assert b.articulation_legato == pytest.approx(0.34, abs=1e-9)
    assert b.layers_max == 4
    assert b.harmonic_rhythm_base == pytest.approx(1.0, abs=1e-9)
    assert b.register_bias == pytest.approx(0.188, abs=1e-9)
    t = plan.timbre_directives
    assert t.brightness == pytest.approx(0.835, abs=1e-9)
    assert t.attack_hardness == pytest.approx(0.66, abs=1e-9)
    assert t.space == pytest.approx(0.36, abs=1e-9)


def _assert_example_2(plan: GenerationPlan) -> None:
    """PHASE_2 §6.5 Example 2 —
    {styleFamily: jazz, mood: melancholic, maxLengthSec: 240, seed: 1ps9wxb}."""
    assert plan.style_pack.id == "jazz"
    assert plan.style_pack.version == "0.1.0"
    assert plan.seed.master == MASTER
    assert plan.key.tonic_pc == 2  # tonics.minor[0] = D
    assert plan.key.mode == "minor"  # V=-0.50 -> minor
    assert plan.tempo_bpm == 69  # override center 68 -> [61,75]; draw = 69
    assert plan.time_signature.numerator == 4
    assert plan.time_signature.denominator == 4
    assert plan.swing is not None
    assert plan.swing.ratio == pytest.approx(0.722, abs=1e-9)  # 69<=90 -> 2.6:1
    assert plan.swing.subdivision == "8"
    assert plan.max_length_ticks == 132480  # 240 s x 69 BPM x 8
    assert plan.role_flavors == {
        "drums": "brush_kit",
        "bass": "upright",
        "comping": "piano",
        "pads": "airy_strings",
    }
    assert plan.mood_vector.valence == pytest.approx(-0.5, abs=1e-9)
    assert plan.mood_vector.arousal == pytest.approx(-0.45, abs=1e-9)
    b = plan.budgets
    assert b.note_density == pytest.approx(0.505, abs=1e-9)  # 0.25 + 0.393 x 0.65
    assert b.dissonance == pytest.approx(0.653, abs=1e-9)  # 0.35 + 0.550 x 0.55
    assert b.dynamics_base == pytest.approx(0.438, abs=1e-9)
    assert b.dynamics_range == pytest.approx(0.217, abs=1e-9)
    assert b.articulation_legato == pytest.approx(0.68, abs=1e-9)
    assert b.layers_max == 3
    assert b.harmonic_rhythm_base == pytest.approx(0.5, abs=1e-9)
    assert b.register_bias == pytest.approx(-0.125, abs=1e-9)
    t = plan.timbre_directives
    assert t.brightness == pytest.approx(0.333, abs=1e-9)
    assert t.attack_hardness == pytest.approx(0.32, abs=1e-9)
    assert t.space == pytest.approx(0.657, abs=1e-9)


def test_example_1_interpret_field_for_field() -> None:
    pack = resolve_pack("pop_rock")
    assert pack is not None
    plan = interpret(Params(style_family="pop_rock"), pack, MASTER, {})
    _assert_example_1(plan)


def test_example_1_generate_plan_matches() -> None:
    plan_a = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    _assert_example_1(plan_a)
    # The two-layer wiring reproduces the same plan from raw params.
    pack = resolve_pack("pop_rock")
    assert pack is not None
    plan_b = interpret(Params(style_family="pop_rock"), pack, MASTER, {})
    assert plan_a == plan_b


def test_example_2_generate_plan_field_for_field() -> None:
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    _assert_example_2(plan)


# --- §6.5 seed vector (normative) --------------------------------------------


def test_interpreter_seed_vector() -> None:
    seed = derive(MASTER, "interpreter")
    assert seed == 1597995742192405040
    assert to_base36(seed) == "c52i7pgxyq7k"
    rng = random.Random(stream_seed(MASTER, {}, "interpreter"))
    assert [rng.randrange(100) for _ in range(5)] == [70, 19, 35, 93, 77]


# --- §11.5 determinism -------------------------------------------------------


def test_same_params_same_seed_identical_plan() -> None:
    args = {"styleFamily": "jazz", "mood": "dreamy", "seed": "1ps9wxb"}
    assert generate_plan(dict(args)) == generate_plan(dict(args))


def test_zero_draws_when_tempo_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """§6.1/D4 — a user tempo consumes the interpreter stream not at all:
    `stream_rng` is never even constructed."""
    calls = {"factory": 0, "randrange": 0}

    def counting_factory(
        master: int, overrides: dict[str, int], name: str
    ) -> random.Random:
        calls["factory"] += 1
        base = random.Random(stream_seed(master, overrides, name))

        class _Counting(random.Random):
            def randrange(self, *a: object, **k: object) -> int:
                calls["randrange"] += 1
                return base.randrange(*a, **k)  # type: ignore[arg-type]

        return _Counting()

    monkeypatch.setattr("trackgen.interpreter.stage.stream_rng", counting_factory)

    plan = generate_plan(
        {"styleFamily": "pop_rock", "tempoBpm": 128, "seed": "1ps9wxb"}
    )
    assert plan.tempo_bpm == 128
    assert calls["factory"] == 0
    assert calls["randrange"] == 0


def test_exactly_one_draw_on_auto_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """§6.1/D4 — the auto tempo path builds the RNG once and draws exactly once."""
    calls = {"factory": 0, "randrange": 0}

    def counting_factory(
        master: int, overrides: dict[str, int], name: str
    ) -> random.Random:
        calls["factory"] += 1
        base = random.Random(stream_seed(master, overrides, name))

        class _Counting(random.Random):
            def randrange(self, *a: object, **k: object) -> int:
                calls["randrange"] += 1
                return base.randrange(*a, **k)  # type: ignore[arg-type]

        return _Counting()

    monkeypatch.setattr("trackgen.interpreter.stage.stream_rng", counting_factory)

    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    assert plan.tempo_bpm == 123  # counting RNG delegates -> same draw
    assert calls["factory"] == 1
    assert calls["randrange"] == 1


def test_user_mode_bypasses_ladder() -> None:
    """§6.3 — a user-supplied mode is used unchanged, ignoring the valence ladder
    (happy V=+0.75 would resolve to major)."""
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "happy",
            "key": {"mode": "dorian"},
            "seed": "1ps9wxb",
        }
    )
    assert plan.key.mode == "dorian"
    assert plan.key.tonic_pc == 2  # tonics.dorian[0] = D


def test_user_tonic_bypasses_pool() -> None:
    plan = generate_plan(
        {"styleFamily": "pop_rock", "key": {"tonic": "F#"}, "seed": "1ps9wxb"}
    )
    assert plan.key.tonic_pc == 6  # F# = pitch class 6


def test_user_tempo_bypasses_draw() -> None:
    plan = generate_plan(
        {"styleFamily": "jazz", "mood": "calm", "tempoBpm": 150, "seed": "1ps9wxb"}
    )
    assert plan.tempo_bpm == 150


def test_generate_plan_raises_on_invalid_params() -> None:
    with pytest.raises(ParamsInvalid) as excinfo:
        generate_plan({"styleFamily": "not_a_pack"})
    codes = {e.code for e in excinfo.value.errors}
    assert "STYLE_UNKNOWN" in codes


@pytest.mark.parametrize(
    "raw",
    [
        {"styleFamily": "jazz", "tempoBpm": 120.5},  # fractional int field
        {"styleFamily": "jazz", "key": "Dm"},  # key not a mapping
        {"styleFamily": "jazz", "roleFlavors": ["piano"]},  # not a mapping
    ],
)
def test_generate_plan_wraps_malformed_types_as_params_invalid(
    raw: dict[str, object],
) -> None:
    """A malformed field TYPE is not a §3.1 semantic condition, but it must
    still surface as a structured ParamsInvalid, never a raw pydantic error."""
    with pytest.raises(ParamsInvalid) as excinfo:
        generate_plan(raw)
    assert all(e.code == "PARAM_MALFORMED" for e in excinfo.value.errors)
    assert excinfo.value.errors  # non-empty


def test_resolve_mode_nearest_rung_and_tie_break() -> None:
    """§6.3 auto mode selection: nearest rung wins; ties break brighter (lower).
    The pinned example — mysterious V=-0.20 (ideal dorian) on [major, minor] →
    minor (distance 1 < 2)."""
    assert _resolve_mode(None, -0.20, ["major", "minor"]) == "minor"
    # Tie at ideal rung 1 (mixolydian) between major(0) and dorian(2) → brighter.
    assert _resolve_mode(None, 0.10, ["major", "dorian"]) == "major"
    # A user-supplied mode is used verbatim (bypasses the ladder).
    assert _resolve_mode("phrygian", 0.9, ["major", "phrygian"]) == "phrygian"


def test_degenerate_tempo_window_clamps_without_drawing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§6.2 — when [0.9c,1.1c] ∩ packRange is empty, tempo is clamped and the
    RNG stream is never consumed."""
    pack = resolve_pack("pop_rock")
    assert pack is not None
    narrow_manifest = pack.manifest.model_copy(update={"tempo_range": (200, 205)})
    narrow_pack = pack.model_copy(update={"manifest": narrow_manifest})

    def fail_factory(*args: object, **kwargs: object) -> object:
        raise AssertionError("stream_rng must not be built on the degenerate path")

    monkeypatch.setattr("trackgen.interpreter.stage.stream_rng", fail_factory)
    # happy center 118.1 → window [106,130]; ∩ [200,205] empty → clamp to 200.
    plan = interpret(Params(style_family="pop_rock"), narrow_pack, MASTER, {})
    assert plan.tempo_bpm == 200


# --- §11.6 property tests: pack × supported mood × auto-everything ------------


def _pack_mood_matrix() -> list[tuple[str, str]]:
    matrix: list[tuple[str, str]] = []
    for pack_id in sorted(registered_styles()):
        pack = resolve_pack(pack_id)
        assert pack is not None and pack.interpreter is not None
        for mood in pack.interpreter.supported_moods:
            matrix.append((pack_id, mood))
    return matrix


@pytest.mark.parametrize(("pack_id", "mood"), _pack_mood_matrix())
def test_plan_invariants_every_pack_mood(pack_id: str, mood: str) -> None:
    pack = resolve_pack(pack_id)
    assert pack is not None and pack.interpreter is not None
    plan = generate_plan({"styleFamily": pack_id, "mood": mood, "seed": "1ps9wxb"})

    assert isinstance(plan, GenerationPlan)  # pydantic-valid by construction

    lo, hi = pack.manifest.tempo_range
    assert plan.tempo_bpm == int(plan.tempo_bpm)  # integral BPM
    assert lo <= plan.tempo_bpm <= hi

    assert plan.key.mode in pack.interpreter.modes

    b = plan.budgets
    for field in (
        b.note_density,
        b.dissonance,
        b.dynamics_base,
        b.dynamics_range,
        b.articulation_legato,
    ):
        assert 0.0 <= field <= 1.0
    # §11.6 — the two pack-scaled budgets must land inside the pack's declared
    # expression range (not merely [0,1], which pydantic already guarantees).
    d_lo, d_hi = pack.interpreter.expression_ranges.density
    x_lo, x_hi = pack.interpreter.expression_ranges.dissonance
    assert d_lo <= b.note_density <= d_hi
    assert x_lo <= b.dissonance <= x_hi
    assert -1.0 <= b.register_bias <= 1.0
    assert b.harmonic_rhythm_base in (0.5, 1.0)
    assert b.layers_max in (2, 3, 4)

    t = plan.timbre_directives
    for field in (t.brightness, t.attack_hardness, t.space):
        assert 0.0 <= field <= 1.0

    if plan.swing is not None:
        assert 0.5 <= plan.swing.ratio <= 0.75


@given(master=st.integers(min_value=0, max_value=_U64_MAX))
def test_invariants_over_master_seeds(master: int) -> None:
    """Hypothesis: over arbitrary master seeds the plan stays valid and is
    deterministic per seed."""
    pack = resolve_pack("jazz")
    assert pack is not None
    params = Params(style_family="jazz", mood="tense")
    plan = interpret(params, pack, master, {})

    lo, hi = pack.manifest.tempo_range
    assert lo <= plan.tempo_bpm <= hi
    assert plan.swing is not None and 0.5 <= plan.swing.ratio <= 0.75

    # Deterministic per seed.
    assert interpret(params, pack, master, {}) == plan


# ---------------------------------------------------------------------------
# Swing table + swing16/pack-override branches (PHASE_2 §6.4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "eff_bpm, expected_r",
    [
        (50.0, 2.60),  # clamp below 90
        (90.0, 2.60),
        (120.0, 2.24),
        (130.0, 2.12),  # midpoint 120<->140
        (140.0, 2.00),
        (160.0, 1.80),
        (200.0, 1.40),
        (240.0, 1.00),
        (300.0, 1.00),  # clamp above 240
    ],
)
def test_swing_ratio_table_interpolation(eff_bpm: float, expected_r: float) -> None:
    assert _swing_ratio_from_table(eff_bpm) == pytest.approx(expected_r, abs=1e-9)


def test_resolve_swing16_evaluates_at_double_tempo() -> None:
    """swing16 evaluates the table at 2*tempo (§6.4)."""
    pack = resolve_pack("jazz")
    assert pack is not None and pack.interpreter is not None
    interp16 = pack.interpreter.model_copy(update={"feel": "swing16"})
    pack16 = pack.model_copy(update={"interpreter": interp16})
    # tempo 70 -> eff 140 -> r=2.00 -> 2/(1+2)=0.667
    swing = _resolve_swing(pack16, 70)
    assert swing is not None
    assert swing.subdivision == "16"
    assert swing.ratio == pytest.approx(0.667, abs=1e-9)


def test_resolve_swing_pack_ratio_override_bypasses_table() -> None:
    """A pack swingRatio is the final ratio and bypasses the tempo table (§6.4)."""
    pack = resolve_pack("jazz")
    assert pack is not None and pack.interpreter is not None
    interp = pack.interpreter.model_copy(update={"swing_ratio": 0.60})
    packo = pack.model_copy(update={"interpreter": interp})
    swing = _resolve_swing(packo, 69)  # table would give 0.722 at 69 bpm
    assert swing is not None
    assert swing.ratio == 0.6
    assert swing.subdivision == "8"


def test_resolve_swing_straight_feel_is_none() -> None:
    pack = resolve_pack("pop_rock")
    assert pack is not None  # pop_rock feel is straight8
    assert _resolve_swing(pack, 120) is None
