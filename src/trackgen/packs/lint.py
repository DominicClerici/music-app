"""Pack linter analysis engine (PHASE_8 §9.2).

Two tiers over a style-pack directory:

- `collect_pack_errors(pack_dir)` — runs every existing loader rule in
  *collect mode* (accumulate rather than raise-on-first) and reports each
  failure as a `LintError` with **file-level context + rule tag**.
- `collect_pack_warnings(pack, pack_dir)` — the five §9.2 authoring-quality
  warning classes (never blocking).

Collect-mode granularity (documented, bounded limitation)
---------------------------------------------------------
The loader (`packs/loader.py` + `packs/models.py`) raises on the FIRST failure;
there is no accumulate path. This linter recovers as much as is *cheap*:

- Each `model_validate` is run directly and its **full** `ValidationError
  .errors()` list is expanded — pydantic aggregates every field-level error of a
  model in one pass, so a config with N independent field errors surfaces N
  `LintError`s at once.
- Every **independent** loader cross-file check (`_check_f11`,
  `_check_progressions_cross_file`, `_check_pattern_banks`, `_check_completeness`
  via `_check_pattern_banks`, `_window_and_check_fills`, the inline PT12/TR5, and
  TB1) is wrapped in its own try/except that appends and continues.

The residual limit: two failures **inside the same `model_validator`** (which
raises on its first) still surface one-at-a-time across re-runs — the validator
returns after the first `raise`, so the second is only reachable once the first
is fixed. Likewise a single cross-file check function that raises on its first
internal failure (e.g. `_check_pattern_banks` runs PT1 → PT10 → PT6 → …
sequentially) surfaces only that first. A full validator refactor to accumulate
inside each `model_validator` is out of scope for this tool.

`yaml.safe_load` drops line numbers, so context is **file-level only** (no line
numbers) — a known, accepted limitation (PHASE_8 §9.2 / C1 scoping).

A clean pack returns `[]` errors.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from trackgen.arrangement.intensity import intensity
from trackgen.form import section_energy
from trackgen.interpreter import derived_defaults
from trackgen.interpreter.moods import load_moods
from trackgen.packs.loader import (
    PackLoadError,
    _apply_bank_retarget_default,
    _check_f11,
    _check_pattern_banks,
    _check_progressions_cross_file,
    _read_yaml,
    _window_and_check_fills,
)
from trackgen.packs.models import (
    BassBank,
    DrumsBank,
    FormsConfig,
    FormTemplate,
    InterpreterConfig,
    Manifest,
    PatternEnvelope,
    ProgressionsConfig,
    RepeatBlock,
    StylePack,
    TransitionsSpec,
    VoicedBank,
)
from trackgen.parts.selection import _eligible_set, section_kind
from trackgen.quality.layer1 import _STRAIGHT_GRID, _TRIPLET_GRID
from trackgen.schema.document import Role

_TICKS_PER_BEAT = 480

# A rule tag embedded in a validator/loader message: F13, PT5, TR6, P11, TB1,
# and the compound PT12/TR5. Tags are trailing, so the LAST match wins.
_RULE_RE = re.compile(r"\b([A-Z]{1,3}\d{1,2}(?:/[A-Z]{1,3}\d{1,2})?)\b")

# The 0.90 dominance threshold for weight degeneracy (§9.2).
_DEGENERACY_RATIO = 0.90

# The per-id silence marker for unreachable-content (§9.2). `safe_load` drops
# comments, so the raw bank-file TEXT is scanned: a pattern id is silenced iff
# its `- id: <name>` declaration line also carries this token as a trailing
# comment. Silence is per pattern id, so a live sibling in the same file still
# warns.
_UNREACHABLE_MARKER = "expected-unreachable"

# A `- id: <name>` list-item declaration line, capturing the id.
_ID_DECL_RE = re.compile(r"^\s*-\s*id:\s*(\S+)")

# Cap on repeat-count enumeration when a template's repeat block is unbounded
# (`count.max == null` — budget-bounded in production, not statically knowable
# here). Over-approximating the count only widens the reachable set UPWARD: a
# larger repeat count lowers the R2 solo arch's minimum index/total ratio (whose
# floor is `lo + clamp01(0.60 + 0.10*arousal) * (hi-lo)`, i.e. at least the
# envelope midpoint — for a wide envelope that can sit below the rung-3 line, so
# the guarantee is directional, not a fixed rung floor) and raises R1 escalation
# indices (adding only higher rungs). The operative property holds regardless: a
# larger count only adds indices at the ends of an already-swept 1..total range,
# so it can never manufacture a spurious LOW rung the sample set missed, and so
# cannot mask a genuine section-kind-floor dormancy (C-23). Verified empirically:
# the reachable set is identical at caps 16/40/200/2000 for all five shipped
# packs. NOTE: `_positional_samples` tracks a single `count_max` per template; a
# future template with two differing repeat blocks would need per-block counts
# (latent — no shipped template has >1 repeat block), as would a fallback section
# absent from the spine.
_MAX_REPEAT_SAMPLE = 16


@dataclass(frozen=True)
class LintError:
    """A blocking pack error: a loader rule that failed.

    `file` is the pack-relative-or-absolute path of the offending file (no line
    number — `yaml.safe_load` drops positions). `rule` is the parsed rule tag
    (e.g. `"PT5"`, `"F3"`, or a pydantic error type like `"missing"`)."""

    file: str
    rule: str
    message: str


@dataclass(frozen=True)
class LintWarning:
    """A non-blocking authoring-quality warning (§9.2).

    `kind` is one of the five §9.2 classes; `location` names the file + the
    offending id (pattern/template/pool)."""

    kind: str
    location: str
    message: str


def _parse_rule(message: str, fallback: str) -> str:
    matches = _RULE_RE.findall(message)
    return matches[-1] if matches else fallback


def _expand_validation_error(
    exc: ValidationError, file: str, errors: list[LintError]
) -> None:
    """Append one `LintError` per field-level error in a `ValidationError`.

    Pydantic aggregates every failing field of one model in a single
    `.errors()` list, so this is where collect-mode gains its multi-error
    granularity: a config with several independent field errors yields several
    `LintError`s from one `model_validate`."""
    for err in exc.errors():
        raw_msg = str(err.get("msg", ""))
        # A `@model_validator` `raise ValueError(...)` surfaces as a
        # 'value_error' whose msg pydantic prefixes with "Value error, ".
        msg = raw_msg
        prefix = "Value error, "
        if msg.startswith(prefix):
            msg = msg[len(prefix) :]
        loc = ".".join(str(p) for p in err.get("loc", ()))
        err_type = str(err.get("type", "error"))
        rule = _parse_rule(msg, fallback=err_type)
        full = f"{msg} [at {loc}]" if loc else msg
        errors.append(LintError(file=file, rule=rule, message=full))


def _validate[ModelT: BaseModel](
    model: type[ModelT], raw: Any, file: str, errors: list[LintError]
) -> ModelT | None:
    """`model.model_validate(raw)` in collect mode: on failure, expand the full
    `ValidationError` into `errors` and return `None`."""
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        _expand_validation_error(exc, file, errors)
        return None


def _read_config(
    path: Path, file: str, errors: list[LintError]
) -> dict[str, Any] | None:
    """Read one YAML config, appending a `LintError` on read/YAML/non-mapping."""
    try:
        raw = _read_yaml(path)
    except PackLoadError as exc:
        errors.append(LintError(file=file, rule="read", message=str(exc)))
        return None
    if not isinstance(raw, dict):
        errors.append(
            LintError(file=file, rule="read", message=f"{path}: must be a mapping")
        )
        return None
    return raw


def _load_bank_collecting[BankT: BaseModel](
    bank_path: Path, model: type[BankT], errors: list[LintError]
) -> BankT | None:
    """`loader._load_bank`, but collecting: mirror the pre-validation
    normalization then expand the `ValidationError` instead of wrapping it into
    a single `PackLoadError` (which would hide the per-field granularity)."""
    file = str(bank_path)
    try:
        raw = _read_yaml(bank_path)
    except PackLoadError as exc:
        errors.append(LintError(file=file, rule="read", message=str(exc)))
        return None
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        errors.append(
            LintError(file=file, rule="read", message="pattern bank must be a mapping")
        )
        return None
    if "patterns" in raw and raw["patterns"] is None:
        raw = {**raw, "patterns": []}
    if "retarget" in model.model_fields:
        raw = _apply_bank_retarget_default(raw)
    return _validate(model, raw, file, errors)


def _append_check(file: str, errors: list[LintError], fn: Any, *args: Any) -> None:
    """Run one independent loader cross-file check, appending its
    `PackLoadError`/`ValueError` (with parsed tag) and continuing."""
    try:
        fn(*args)
    except (PackLoadError, ValueError) as exc:
        msg = str(exc)
        errors.append(LintError(file=file, rule=_parse_rule(msg, "check"), message=msg))


def collect_pack_errors(pack_dir: Path) -> list[LintError]:
    """Run every loader rule over `pack_dir` in collect mode (see module doc).

    A clean pack returns `[]`. Mirrors `loader.load_pack`'s order and guards;
    cross-file checks only run when their inputs validated."""
    from trackgen.sound.timbres import (
        TimbresConfig,
        check_flavor_completeness,
    )

    errors: list[LintError] = []
    pack_dir = Path(pack_dir)

    manifest_path = pack_dir / "manifest.yaml"
    manifest: Manifest | None = None
    raw_manifest = _read_config(manifest_path, str(manifest_path), errors)
    if raw_manifest is not None:
        manifest = _validate(Manifest, raw_manifest, str(manifest_path), errors)

    patterns_dir = pack_dir / "patterns"
    drums = _load_bank_collecting(patterns_dir / "drums.yaml", DrumsBank, errors)
    bass = _load_bank_collecting(patterns_dir / "bass.yaml", BassBank, errors)
    comping = _load_bank_collecting(patterns_dir / "comping.yaml", VoicedBank, errors)
    pads = _load_bank_collecting(patterns_dir / "pads.yaml", VoicedBank, errors)

    if None not in (drums, bass, comping, pads):
        assert drums is not None and bass is not None
        assert comping is not None and pads is not None
        _append_check(
            str(patterns_dir),
            errors,
            _check_pattern_banks,
            pack_dir,
            drums,
            bass,
            comping,
            pads,
        )

    interpreter: InterpreterConfig | None = None
    interpreter_path = pack_dir / "interpreter.yaml"
    if interpreter_path.exists():
        raw = _read_config(interpreter_path, str(interpreter_path), errors)
        if raw is not None:
            interpreter = _validate(
                InterpreterConfig, raw, str(interpreter_path), errors
            )

    forms: FormsConfig | None = None
    forms_path = pack_dir / "forms.yaml"
    if forms_path.exists():
        raw = _read_config(forms_path, str(forms_path), errors)
        if raw is not None:
            forms = _validate(FormsConfig, raw, str(forms_path), errors)
        if forms is not None and manifest is not None:
            _append_check(str(forms_path), errors, _check_f11, forms, manifest)

    progressions: ProgressionsConfig | None = None
    progressions_path = pack_dir / "progressions.yaml"
    if progressions_path.exists():
        raw = _read_config(progressions_path, str(progressions_path), errors)
        if raw is not None:
            progressions = _validate(
                ProgressionsConfig, raw, str(progressions_path), errors
            )
        if progressions is not None:
            _append_check(
                str(progressions_path),
                errors,
                _check_progressions_cross_file,
                progressions,
                forms,
                interpreter,
            )

    timbres_path = pack_dir / "timbres.yaml"
    if timbres_path.exists():
        raw = _read_config(timbres_path, str(timbres_path), errors)
        if raw is not None:
            timbres = _validate(TimbresConfig, raw, str(timbres_path), errors)
            if timbres is not None and interpreter is not None:
                declared = {role: set(ids) for role, ids in interpreter.flavors.items()}
                _append_check(
                    str(timbres_path),
                    errors,
                    check_flavor_completeness,
                    timbres,
                    declared,
                )

    if drums is not None:
        _append_check(
            str(patterns_dir / "drums.yaml"),
            errors,
            _window_and_check_fills,
            pack_dir,
            drums,
        )

    transitions_path = pack_dir / "transitions.yaml"
    if transitions_path.exists():
        raw = _read_config(transitions_path, str(transitions_path), errors)
        if raw is not None:
            transitions = _validate(TransitionsSpec, raw, str(transitions_path), errors)
            if transitions is not None and drums is not None:
                if not any(
                    env.kind == "fill" and not env.is_gated for env in drums.patterns
                ):
                    errors.append(
                        LintError(
                            file=str(transitions_path),
                            rule="PT12/TR5",
                            message=(
                                "pack has no ungated drum 'fill' pattern, so fill "
                                "resolution could come up empty (PT12/TR5)"
                            ),
                        )
                    )

    return errors


# --- warnings -----------------------------------------------------------------


def _mood_windows(pack: StylePack) -> list[tuple[str, int, int]]:
    """Per supported mood, the inclusive integer tempo window the auto-path can
    draw, mirroring `interpreter/stage.py` (center from `derived_defaults`, then
    `[round(0.9c), round(1.1c)]` clamped to the pack tempo range; a degenerate
    window collapses to the clamped center)."""
    interp = pack.interpreter
    if interp is None:
        return []
    table = load_moods()
    lo_range, hi_range = pack.manifest.tempo_range
    out: list[tuple[str, int, int]] = []
    for mood in interp.supported_moods:
        center = float(derived_defaults(mood, table)["tempoCenter"])
        lo = max(round(0.9 * center), lo_range)
        hi = min(round(1.1 * center), hi_range)
        if lo > hi:
            single = max(lo_range, min(round(center), hi_range))
            out.append((mood, single, single))
        else:
            out.append((mood, lo, hi))
    return out


def _active_roles(pack: StylePack) -> list[Role]:
    """Pattern-selecting roles: those with a non-empty bank, minus walking bass
    (the walker serves it — it never draws a pattern, §3.2)."""
    roles: list[Role] = []
    for role in ("drums", "bass", "comping", "pads"):
        if role == "bass" and pack.bass_mode == "walking":
            continue
        if pack.patterns.get(role):
            roles.append(role)
    return roles


def _warn_variety_coverage(pack: StylePack) -> list[LintWarning]:
    """Any `(role, kind, rung)` slot with <= 1 surviving candidate for some
    supported `(mood, tempo)` cell — zero reroll variety (§9.2)."""
    windows = _mood_windows(pack)
    if not windows:
        return []
    warnings: list[LintWarning] = []
    for role in _active_roles(pack):
        # `main` is rung-sensitive (energyLevel == rung); intro/ending ignore
        # rung, so one representative slot each (dummy rung 1).
        slots: list[tuple[str, int]] = [("main", r) for r in (1, 2, 3, 4)]
        slots += [("intro", 1), ("ending", 1)]
        for kind, rung in slots:
            worst: tuple[int, str, int] | None = None
            for mood, lo, hi in windows:
                for tempo in range(lo, hi + 1):
                    survivors = len(_eligible_set(pack, role, kind, rung, tempo))  # type: ignore[arg-type]
                    if worst is None or survivors < worst[0]:
                        worst = (survivors, mood, tempo)
            if worst is not None and worst[0] <= 1:
                count, mood, tempo = worst
                label = f"{kind} rung {rung}" if kind == "main" else kind
                warnings.append(
                    LintWarning(
                        kind="variety-coverage",
                        location=f"patterns/{role}.yaml ({role} {label})",
                        message=(
                            f"only {count} candidate(s) survive all gates at "
                            f"mood={mood!r} tempo={tempo} — zero reroll variety"
                        ),
                    )
                )
    return warnings


def _warn_grid_mixing(pack: StylePack) -> list[LintWarning]:
    """A pattern whose authored `env.events` mix a straight-grid-only `pos` and
    a triplet-grid-only `pos` (§3.1; reuses the layer1 grid constants over
    `event.pos`, not rendered phrases)."""
    warnings: list[LintWarning] = []
    for role, entries in pack.patterns.items():
        for env in entries:
            has_straight = False
            has_triplet = False
            for event in env.events:
                pos = event.pos % _TICKS_PER_BEAT
                on_straight = pos in _STRAIGHT_GRID
                on_triplet = pos in _TRIPLET_GRID
                if on_straight and not on_triplet:
                    has_straight = True
                elif on_triplet and not on_straight:
                    has_triplet = True
            if has_straight and has_triplet:
                warnings.append(
                    LintWarning(
                        kind="grid-mixing",
                        location=f"patterns/{role}.yaml ({env.id})",
                        message=(
                            "authored events mix straight-grid and triplet-grid "
                            "positions within one pattern (§3.1 one-grid-per-pattern)"
                        ),
                    )
                )
    return warnings


def _positional_samples(
    template: FormTemplate,
) -> list[tuple[str, int, int, float | None]]:
    """Every `(section_type, index, total_of_type, override)` a body slot of
    `template` can present to `section_energy` under some reachable form
    realization — the inputs the energy model's §6.2 positional rules key off.

    Positions are over-approximated upward (`total_of_type` swept from 1, repeat
    counts up to `_MAX_REPEAT_SAMPLE`) — safe per that constant's note. A type is
    given the positional sweep only if it has at least one NON-override
    occurrence; every explicit `slot.energy` override is emitted as its own
    fixed sample (`section_energy` ignores index/total when `override` is set)."""
    top_slots: dict[str, int] = defaultdict(int)
    repeat_slots: dict[str, int] = defaultdict(int)
    count_max: int | None = 1
    overrides: list[tuple[str, float]] = []
    has_non_override: set[str] = set()

    def record(section: str, energy: float | None) -> None:
        if energy is not None:
            overrides.append((section, energy))
        else:
            has_non_override.add(section)

    for element in template.spine:
        if isinstance(element, RepeatBlock):
            count_max = element.repeat.count[1]
            for slot in element.repeat.slots:
                repeat_slots[slot.section] += 1
                record(slot.section, slot.energy)
        else:
            top_slots[element.section] += 1
            record(element.section, element.energy)

    reps = _MAX_REPEAT_SAMPLE if count_max is None else count_max
    samples: list[tuple[str, int, int, float | None]] = []
    for section in set(top_slots) | set(repeat_slots):
        if section not in has_non_override:
            continue
        max_total = top_slots.get(section, 0) + reps * repeat_slots.get(section, 0)
        for total in range(1, max(1, max_total) + 1):
            for index in range(1, total + 1):
                samples.append((section, index, total, None))
    for section, energy in overrides:
        samples.append((section, 1, 1, energy))
    return samples


def _reachable_rungs(pack: StylePack) -> set[int] | None:
    """The intensity rungs a `main` pattern can actually be selected at: the
    union, over every supported mood's arousal × every `main`-kind section type
    in the templates × its reachable positional `(index, total)` and energy
    overrides, of `intensity(section_energy(...))`.

    This is the real per-render reachable set — `section_kind` maps `intro`/
    `outro` to their own pattern kinds (energy-blind), so only body sections
    (the ones whose rung is `intensity(section.energy)`, PHASE_5 §3.1 →
    `select_patterns`) contribute. It narrows the prior envelope-only
    over-approximation, which modeled neither §6.3 arousal scaling nor the §6.1
    section-kind energy floors and so reported every rung reachable (the C-22 /
    C-23 / C-28 lint gap).

    Returns `None` when the pack lacks forms or an interpreter (the moods the
    per-mood computation needs)."""
    forms = pack.forms
    interp = pack.interpreter
    if forms is None or interp is None:
        return None
    table = load_moods()
    arousals = [table.moods[m].arousal for m in interp.supported_moods]
    if not arousals:
        return None
    energy_range = forms.energy_range
    reachable: set[int] = set()
    for template in forms.templates:
        for section, index, total, override in _positional_samples(template):
            if section_kind(section) != "main":
                continue
            for arousal in arousals:
                energy = section_energy(
                    section, index, total, arousal, energy_range, override=override
                )
                reachable.add(intensity(energy))
    return reachable


def _silenced_ids(pack_dir: Path) -> dict[str, set[str]]:
    """Per role, the set of pattern ids carrying the `# expected-unreachable`
    marker on their `- id: <name>` declaration line. Comments are dropped by
    `safe_load`, so the raw TEXT is scanned line by line; only the id whose own
    declaration bears the marker is silenced, so sibling patterns still warn."""
    silenced: dict[str, set[str]] = {}
    for role in ("drums", "bass", "comping", "pads"):
        path = pack_dir / "patterns" / f"{role}.yaml"
        if not path.is_file():
            continue
        ids: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if _UNREACHABLE_MARKER not in line:
                continue
            match = _ID_DECL_RE.match(line)
            if match is not None:
                ids.add(match.group(1))
        if ids:
            silenced[role] = ids
    return silenced


def _warn_unreachable_content(pack: StylePack, pack_dir: Path) -> list[LintWarning]:
    """A `main` pattern at a rung no reachable section energy quantizes to —
    "reachable" being the per-mood × per-section-kind × per-position union
    `_reachable_rungs` computes (not merely the pack envelope). Silenced
    per pattern id by the `# expected-unreachable` marker (§9.2)."""
    reachable = _reachable_rungs(pack)
    if reachable is None:
        return []
    silenced = _silenced_ids(pack_dir)
    warnings: list[LintWarning] = []
    for role, entries in pack.patterns.items():
        silenced_here = silenced.get(role, set())
        for env in entries:
            if env.id in silenced_here:
                continue
            if env.kind == "main" and env.energy_level not in reachable:
                warnings.append(
                    LintWarning(
                        kind="unreachable-content",
                        location=f"patterns/{role}.yaml ({env.id})",
                        message=(
                            f"'main' pattern at rung {env.energy_level} is "
                            f"unreachable: no supported (mood x section-kind x "
                            f"position) section energy quantizes to it "
                            f"(reachable rungs {sorted(reachable)})"
                        ),
                    )
                )
    return warnings


def _warn_dangling_gates(pack: StylePack) -> list[LintWarning]:
    """An `Eligibility.tempoBpm` band (pattern) or `TemplateEligibility.arousal`
    band (template) that no supported `(mood, tempo/arousal)` cell can enter
    (§9.2)."""
    warnings: list[LintWarning] = []
    windows = _mood_windows(pack)

    if windows:
        for role, entries in pack.patterns.items():
            for env in entries:
                band = env.eligibility.tempo_bpm
                if band is None:
                    continue
                blo, bhi = band
                if not any(blo <= whi and wlo <= bhi for _, wlo, whi in windows):
                    warnings.append(
                        LintWarning(
                            kind="dangling-gate",
                            location=f"patterns/{role}.yaml ({env.id})",
                            message=(
                                f"eligibility.tempoBpm band {list(band)} is entered "
                                f"by no supported (mood, tempo) cell"
                            ),
                        )
                    )

    interp = pack.interpreter
    if pack.forms is not None and interp is not None:
        table = load_moods()
        arousals = [table.moods[m].arousal for m in interp.supported_moods]
        for template in pack.forms.templates:
            if template.eligibility is None:
                continue
            alo, ahi = template.eligibility.arousal
            if not any(alo <= a <= ahi for a in arousals):
                warnings.append(
                    LintWarning(
                        kind="dangling-gate",
                        location=f"forms.yaml ({template.id})",
                        message=(
                            f"eligibility.arousal band [{alo}, {ahi}] is entered by "
                            f"no supported mood"
                        ),
                    )
                )
    return warnings


def _degeneracy_ratio(weights: list[int]) -> float | None:
    total = sum(weights)
    if len(weights) < 2 or total <= 0:
        return None
    return max(weights) / total


def _warn_weight_degeneracy(pack: StylePack) -> list[LintWarning]:
    """Any multi-entry pool where one entry holds > 90 % of the weight (§9.2).

    Singletons are skipped (their trivially-1.0 ratio is a variety-coverage
    concern, not degeneracy)."""
    warnings: list[LintWarning] = []

    def check(kind_label: str, location: str, weights: list[int]) -> None:
        ratio = _degeneracy_ratio(weights)
        if ratio is not None and ratio > _DEGENERACY_RATIO:
            warnings.append(
                LintWarning(
                    kind="weight-degeneracy",
                    location=location,
                    message=(
                        f"{kind_label}: one entry holds {ratio:.0%} of the pool "
                        f"weight (> 90 %)"
                    ),
                )
            )

    prog = pack.progressions
    if prog is not None:
        for tag, entries in prog.pools.items():
            check(
                "progression pool",
                f"progressions.yaml (pool {tag!r})",
                [e.weight for e in entries],
            )
        check(
            "turnarounds",
            "progressions.yaml (turnarounds)",
            [e.weight for e in prog.turnarounds],
        )
        check("finals", "progressions.yaml (finals)", [e.weight for e in prog.finals])

    bank_groups: dict[tuple[str, str, int | None], list[PatternEnvelope]] = defaultdict(
        list
    )
    for role, envs in pack.patterns.items():
        for env in envs:
            rung = env.energy_level if env.kind == "main" else None
            bank_groups[(role, env.kind, rung)].append(env)
    for (role, kind, rung), group in bank_groups.items():
        label = f"{kind} rung {rung}" if rung is not None else kind
        check(
            "pattern bank",
            f"patterns/{role}.yaml ({role} {label})",
            [env.weight for env in group],
        )

    if pack.forms is not None:
        check(
            "template pool",
            "forms.yaml (templates)",
            [t.weight for t in pack.forms.templates],
        )

    trans = pack.transitions
    if trans is not None:
        for role_name, table in (
            ("drums", trans.mutation.drums),
            ("comping", trans.mutation.comping),
        ):
            if table is not None:
                check(
                    "mutation table",
                    f"transitions.yaml (mutation.{role_name})",
                    list(table.values()),
                )

    return warnings


def collect_pack_warnings(pack: StylePack, pack_dir: Path) -> list[LintWarning]:
    """The five §9.2 authoring-quality warning classes (non-blocking)."""
    warnings: list[LintWarning] = []
    warnings += _warn_variety_coverage(pack)
    warnings += _warn_grid_mixing(pack)
    warnings += _warn_unreachable_content(pack, Path(pack_dir))
    warnings += _warn_dangling_gates(pack)
    warnings += _warn_weight_degeneracy(pack)
    return warnings
