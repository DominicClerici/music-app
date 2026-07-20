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
    InterpreterConfig,
    Manifest,
    PatternEnvelope,
    ProgressionsConfig,
    StylePack,
    TransitionsSpec,
    VoicedBank,
)
from trackgen.parts.selection import _eligible_set
from trackgen.quality.layer1 import _STRAIGHT_GRID, _TRIPLET_GRID
from trackgen.schema.document import Role

_TICKS_PER_BEAT = 480

# A rule tag embedded in a validator/loader message: F13, PT5, TR6, P11, TB1,
# and the compound PT12/TR5. Tags are trailing, so the LAST match wins.
_RULE_RE = re.compile(r"\b([A-Z]{1,3}\d{1,2}(?:/[A-Z]{1,3}\d{1,2})?)\b")

# The 0.90 dominance threshold for weight degeneracy (§9.2).
_DEGENERACY_RATIO = 0.90

# The file-level silence marker for unreachable-content (§9.2). `safe_load`
# drops comments, so the raw bank-file TEXT is scanned for this token.
_UNREACHABLE_MARKER = "expected-unreachable"


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


def _reachable_rungs(pack: StylePack) -> set[int] | None:
    """The intensity rungs any energy in the pack's `energyRange` quantizes to
    (`intensity()` is monotone, so the reachable set is a contiguous span)."""
    if pack.forms is None:
        return None
    lo, hi = pack.forms.energy_range
    return set(range(intensity(lo), intensity(hi) + 1))


def _silenced_files(pack_dir: Path) -> set[str]:
    """Bank files carrying the `# expected-unreachable` marker. Comments are
    dropped by `safe_load`, so the raw TEXT is scanned; silence is coarse
    (file-level), which is acceptable per §9.2."""
    silenced: set[str] = set()
    for role in ("drums", "bass", "comping", "pads"):
        path = pack_dir / "patterns" / f"{role}.yaml"
        if path.is_file() and _UNREACHABLE_MARKER in path.read_text(encoding="utf-8"):
            silenced.add(role)
    return silenced


def _warn_unreachable_content(pack: StylePack, pack_dir: Path) -> list[LintWarning]:
    """A `main` pattern at a rung no reachable section energy quantizes to
    (via `intensity()` over `energyRange`); silenced file-wide by the
    `# expected-unreachable` marker (§9.2)."""
    reachable = _reachable_rungs(pack)
    if reachable is None:
        return []
    silenced = _silenced_files(pack_dir)
    warnings: list[LintWarning] = []
    for role, entries in pack.patterns.items():
        if role in silenced:
            continue
        for env in entries:
            if env.kind == "main" and env.energy_level not in reachable:
                warnings.append(
                    LintWarning(
                        kind="unreachable-content",
                        location=f"patterns/{role}.yaml ({env.id})",
                        message=(
                            f"'main' pattern at rung {env.energy_level} is "
                            f"unreachable: no section energy in energyRange "
                            f"{pack.forms.energy_range} quantizes to it "  # type: ignore[union-attr]
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
