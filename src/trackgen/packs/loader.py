"""Style-pack loader (PHASE_1 §6, §9 item 3).

`load_pack` reads a pack directory's `manifest.yaml` and per-role
`patterns/{drums,bass,comping,pads}.yaml` banks via `yaml.safe_load` and
validates everything into the frozen models in `trackgen.packs.models`.
"""

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from trackgen.packs.models import (
    FormsConfig,
    InterpreterConfig,
    Manifest,
    PatternEnvelope,
    ProgressionsConfig,
    StylePack,
    _is_degree1_rooted,
)
from trackgen.theory import chord_function

PATTERN_ROLES = ("drums", "bass", "comping", "pads")

STYLES_ROOT = Path(__file__).resolve().parents[3] / "styles"

_TICKS_PER_QUARTER = 480
_MIN_LENGTH_SEC = 30
_MIN_BAR_BUDGET = 4


class PackLoadError(Exception):
    """Raised when a pack file is missing or fails validation."""


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise PackLoadError(f"{path}: could not read pack file ({exc})") from exc
    except yaml.YAMLError as exc:
        raise PackLoadError(f"{path}: invalid YAML ({exc})") from exc


def _check_f11(forms: FormsConfig, manifest: Manifest) -> None:
    """PHASE_3 §5.1 F11 / D-S12 — `tempoRange.lo` must yield a bar budget
    >= 4 at the 30 s minimum-length floor, so the fitter always has room for
    one legal section. Needs the manifest, so this runs in the loader rather
    than a pure `FormsConfig` model validator."""
    tempo_lo = manifest.tempo_range[0]
    numerator, denominator = manifest.time_signatures[0]
    max_length_ticks = math.floor(_MIN_LENGTH_SEC * tempo_lo * 8)
    ticks_per_bar = numerator * (_TICKS_PER_QUARTER * 4 // denominator)
    bar_budget = max_length_ticks // ticks_per_bar
    if bar_budget < _MIN_BAR_BUDGET:
        raise ValueError(
            f"tempoRange.lo ({tempo_lo}) yields a bar budget of {bar_budget} "
            f"at the {_MIN_LENGTH_SEC}s minimum length, below the required "
            f"{_MIN_BAR_BUDGET} (F11)"
        )


def _forms_tag_usage(
    forms: FormsConfig,
) -> tuple[
    set[str],
    dict[str, set[tuple[frozenset[str], int]]],
    dict[str, set[str]],
]:
    """Walk every section type × bar option in `forms.yaml` (resolving
    `inherit`), returning: the set of harmonyTags used; per tag the set of
    `(phrase labels, phrase length in bars)` requirements each option imposes
    (P4); and per tag the set of section TYPES that serve it (P7)."""
    tags_used: set[str] = set()
    tag_reqs: dict[str, set[tuple[frozenset[str], int]]] = defaultdict(set)
    tag_types: dict[str, set[str]] = defaultdict(set)

    for type_name, section_def in forms.sections.items():
        resolved = (
            forms.sections[section_def.inherit]
            if section_def.inherit is not None
            else section_def
        )
        assert resolved.bars is not None
        assert resolved.phrases is not None
        assert resolved.harmony_tag is not None
        for n, _weight in resolved.bars:
            tag = resolved.harmony_tag[n]
            labels = resolved.phrases[n]
            tags_used.add(tag)
            tag_reqs[tag].add((frozenset(labels), n // len(labels)))
            tag_types[tag].add(type_name)

    return tags_used, tag_reqs, tag_types


def _check_progressions_cross_file(
    progressions: ProgressionsConfig,
    forms: FormsConfig | None,
    interpreter: InterpreterConfig | None,
) -> None:
    """PHASE_4 §4.3 cross-file rules — P1/P4/P7 against `forms.yaml`, P6 against
    `interpreter.yaml`. Like `_check_f11`, these need more than one file, so
    they live in the loader rather than a single-config model validator."""
    if forms is not None:
        tags_used, tag_reqs, tag_types = _forms_tag_usage(forms)

        # P1: every harmonyTag any forms bar option uses has a non-empty pool.
        for tag in tags_used:
            if not progressions.pools.get(tag):
                raise ValueError(
                    f"harmonyTag {tag!r} used by forms.yaml has no non-empty pool (P1)"
                )

        # P4: every pool entry provides exactly the labels each option using
        # its tag needs, each with that option's phrase length in bars.
        for tag, reqs in tag_reqs.items():
            entries = progressions.pools.get(tag)
            if not entries:
                continue  # P1 already raised
            for labels, phrase_len in reqs:
                for entry in entries:
                    if set(entry.phrases) != set(labels):
                        raise ValueError(
                            f"pool {tag!r} entry {entry.id!r}: phrase labels "
                            f"{sorted(entry.phrases)} != required "
                            f"{sorted(labels)} for a forms option (P4)"
                        )
                    for label in labels:
                        got = len(entry.phrases[label])
                        if got != phrase_len:
                            raise ValueError(
                                f"pool {tag!r} entry {entry.id!r}: phrase "
                                f"{label!r} is {got} bars, forms option needs "
                                f"{phrase_len} (P4)"
                            )

        # P7: cadence classes by the section TYPES a tag serves.
        for tag, types in tag_types.items():
            entries = progressions.pools.get(tag)
            if not entries:
                continue
            need_dominant = bool(types & {"prechorus", "bridge"})
            need_open = bool(types & {"intro", "verse"})
            if not (need_dominant or need_open):
                continue
            for entry in entries:
                final = entry.final_chord_token()
                if need_dominant and chord_function(final) != "D":
                    raise ValueError(
                        f"pool {tag!r} entry {entry.id!r}: final chord {final!r} "
                        f"must be D-function (serves prechorus/bridge) (P7)"
                    )
                if need_open and _is_degree1_rooted(final):
                    raise ValueError(
                        f"pool {tag!r} entry {entry.id!r}: final chord {final!r} "
                        f"must be open / not degree-1-rooted (serves intro/verse) "
                        f"(P7)"
                    )

    if interpreter is not None:
        # P6: for every interpreter mode, every pool and finals has >= 1 entry
        # listing that mode with NO valence/dissonance band (never empty).
        named_groups: list[tuple[str, tuple[Any, ...]]] = [
            *progressions.pools.items(),
            ("finals", progressions.finals),
        ]
        for mode in interpreter.modes:
            for name, entries in named_groups:
                if not any(
                    mode in entry.modes
                    and entry.valence is None
                    and entry.dissonance is None
                    for entry in entries
                ):
                    raise ValueError(
                        f"pool {name!r} has no unconditional entry for mode "
                        f"{mode!r} — selection could come up empty (P6)"
                    )


def load_pack(path: str | Path) -> StylePack:
    """Load and validate a style pack directory into a `StylePack`."""
    pack_dir = Path(path)

    manifest_path = pack_dir / "manifest.yaml"
    raw_manifest = _read_yaml(manifest_path)
    if not isinstance(raw_manifest, dict):
        raise PackLoadError(f"{manifest_path}: manifest must be a mapping")
    try:
        manifest = Manifest.model_validate(raw_manifest)
    except ValidationError as exc:
        raise PackLoadError(f"{manifest_path}: invalid manifest\n{exc}") from exc

    patterns: dict[str, list[PatternEnvelope]] = {}
    for role in PATTERN_ROLES:
        bank_path = pack_dir / "patterns" / f"{role}.yaml"
        raw_bank = _read_yaml(bank_path)
        if raw_bank is None:
            raw_bank = {}
        if not isinstance(raw_bank, dict):
            raise PackLoadError(f"{bank_path}: pattern bank must be a mapping")
        raw_entries = raw_bank.get("patterns")
        if raw_entries is None:
            raw_entries = []
        if not isinstance(raw_entries, list):
            raise PackLoadError(f"{bank_path}: 'patterns' must be a list")
        try:
            patterns[role] = [
                PatternEnvelope.model_validate(entry) for entry in raw_entries
            ]
        except ValidationError as exc:
            raise PackLoadError(f"{bank_path}: invalid pattern bank\n{exc}") from exc

    interpreter: InterpreterConfig | None = None
    interpreter_path = pack_dir / "interpreter.yaml"
    if interpreter_path.exists():
        raw_interpreter = _read_yaml(interpreter_path)
        if not isinstance(raw_interpreter, dict):
            raise PackLoadError(f"{interpreter_path}: interpreter must be a mapping")
        try:
            interpreter = InterpreterConfig.model_validate(raw_interpreter)
        except ValidationError as exc:
            raise PackLoadError(
                f"{interpreter_path}: invalid interpreter config\n{exc}"
            ) from exc

    forms: FormsConfig | None = None
    forms_path = pack_dir / "forms.yaml"
    if forms_path.exists():
        raw_forms = _read_yaml(forms_path)
        if not isinstance(raw_forms, dict):
            raise PackLoadError(f"{forms_path}: forms must be a mapping")
        try:
            forms = FormsConfig.model_validate(raw_forms)
        except ValidationError as exc:
            raise PackLoadError(f"{forms_path}: invalid forms config\n{exc}") from exc
        try:
            _check_f11(forms, manifest)
        except ValueError as exc:
            raise PackLoadError(f"{forms_path}: {exc}") from exc

    progressions: ProgressionsConfig | None = None
    progressions_path = pack_dir / "progressions.yaml"
    if progressions_path.exists():
        raw_progressions = _read_yaml(progressions_path)
        if not isinstance(raw_progressions, dict):
            raise PackLoadError(f"{progressions_path}: progressions must be a mapping")
        try:
            progressions = ProgressionsConfig.model_validate(raw_progressions)
        except ValidationError as exc:
            raise PackLoadError(
                f"{progressions_path}: invalid progressions config\n{exc}"
            ) from exc
        try:
            _check_progressions_cross_file(progressions, forms, interpreter)
        except ValueError as exc:
            raise PackLoadError(f"{progressions_path}: {exc}") from exc

    return StylePack(
        manifest=manifest,
        patterns=patterns,
        interpreter=interpreter,
        forms=forms,
        progressions=progressions,
    )


def registered_styles() -> set[str]:
    """PHASE_2 D-S3 — registered `styleFamily` ids: `styles/` subdirs with a
    `manifest.yaml`, excluding `_stub`."""
    if not STYLES_ROOT.is_dir():
        return set()
    return {
        entry.name
        for entry in STYLES_ROOT.iterdir()
        if entry.is_dir()
        and entry.name != "_stub"
        and (entry / "manifest.yaml").is_file()
    }


def resolve_pack(style_family: str) -> StylePack | None:
    """PHASE_2 D-S3 — load a registered style pack by id, or `None`."""
    if style_family not in registered_styles():
        return None
    return load_pack(STYLES_ROOT / style_family)
