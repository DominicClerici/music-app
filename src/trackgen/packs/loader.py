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
from pydantic import BaseModel, ValidationError

from trackgen.packs.models import (
    BassBank,
    DrumsBank,
    FormsConfig,
    InterpreterConfig,
    Manifest,
    PatternEnvelope,
    ProgressionsConfig,
    StylePack,
    TimbresConfig,
    VoicedBank,
    VoicingConfig,
    _is_degree1_rooted,
)
from trackgen.schema.document import Role
from trackgen.theory import chord_function

PATTERN_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")
_PATTERN_RUNGS = (1, 2, 3, 4)

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


def _apply_bank_retarget_default(raw: dict[str, Any]) -> dict[str, Any]:
    """PHASE_5 §7 — fill each pattern entry's missing `retarget` from the
    bank-level `retarget:` default. Runs on raw entry dicts BEFORE
    `PatternEnvelope.model_validate`, so PT9 sees a present retarget on entries
    that omit their own; an entry authoring its own `retarget` keeps it
    (override). Only pitched-role banks (BassBank/VoicedBank) declare a
    `retarget` field, so drums never reach this — a drums-bank `retarget:` is
    left in place for `extra="forbid"` to reject."""
    default = raw.get("retarget")
    patterns = raw.get("patterns")
    if default is None or not isinstance(patterns, list):
        return raw
    filled = [
        {**entry, "retarget": default}
        if isinstance(entry, dict) and entry.get("retarget") is None
        else entry
        for entry in patterns
    ]
    return {**raw, "patterns": filled}


def _load_bank[BankT: BaseModel](bank_path: Path, model: type[BankT]) -> BankT:
    """Read and validate one per-role pattern-bank file into `model`.

    A `None` or absent `patterns:` key normalizes to an empty list, so an
    unauthored bank stays structurally loadable (Phase 1 behavior). Entry-level
    PT1/PT2/PT3/PT8/PT9 and the bank-block PT4/PT6/PT7 checks fire as pydantic
    validators inside `model_validate`."""
    raw = _read_yaml(bank_path)
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise PackLoadError(f"{bank_path}: pattern bank must be a mapping")
    if "patterns" in raw and raw["patterns"] is None:
        raw = {**raw, "patterns": []}
    if "retarget" in model.model_fields:
        raw = _apply_bank_retarget_default(raw)
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise PackLoadError(f"{bank_path}: invalid pattern bank\n{exc}") from exc


def _check_completeness(
    pack_dir: Path, role: str, entries: list[PatternEnvelope]
) -> None:
    """PT5 (§3.2) for one role's bank: an ungated `main` at each rung 1–4 plus
    an ungated `intro` and `ending` — so pattern selection can never come up
    empty (the F13/P6 pattern applied to rhythm)."""
    bank_path = pack_dir / "patterns" / f"{role}.yaml"
    for rung in _PATTERN_RUNGS:
        if not any(
            env.kind == "main" and env.energy_level == rung and not env.is_gated
            for env in entries
        ):
            raise PackLoadError(
                f"{bank_path}: role {role!r} has no ungated 'main' pattern at "
                f"rung {rung} (PT5)"
            )
    for kind in ("intro", "ending"):
        if not any(env.kind == kind and not env.is_gated for env in entries):
            raise PackLoadError(
                f"{bank_path}: role {role!r} has no ungated {kind!r} pattern (PT5)"
            )


def _check_pattern_banks(
    pack_dir: Path,
    drums: DrumsBank,
    bass: BassBank,
    comping: VoicedBank,
    pads: VoicedBank,
) -> None:
    """Loader-level pattern-bank rules that need the whole pack: PT1 (role
    matches file + ids unique per pack) always; and — for Phase-5-authored packs
    (those declaring `layeringOrder`/`mode`/`voicing`) — PT10 (layering order),
    PT6 (bass mode/walking cross-check), PT7 (voicing presence), and PT5
    (completeness). Legacy packs carrying only the Phase-1 flat envelope (no
    Phase-5 markers — `_stub` and the pre-T2 reference banks) skip the Phase-5
    bank rules, so they keep loading until their banks are authored."""
    role_patterns: dict[str, list[PatternEnvelope]] = {
        "drums": drums.patterns,
        "bass": bass.patterns,
        "comping": comping.patterns,
        "pads": pads.patterns,
    }

    # PT1: `role` matches the file it was authored in.
    for role, entries in role_patterns.items():
        for env in entries:
            if env.role != role:
                raise PackLoadError(
                    f"{pack_dir / 'patterns' / f'{role}.yaml'}: pattern "
                    f"{env.id!r} declares role {env.role!r} but lives in the "
                    f"{role!r} bank (PT1)"
                )

    # PT1: pattern ids unique across the whole pack.
    all_ids = [env.id for entries in role_patterns.values() for env in entries]
    dupes = sorted({i for i in all_ids if all_ids.count(i) > 1})
    if dupes:
        raise PackLoadError(
            f"{pack_dir / 'patterns'}: duplicate pattern id(s) across the pack: "
            f"{dupes} (PT1)"
        )

    phase5 = (
        drums.layering_order is not None
        or bass.mode is not None
        or bass.walking is not None
        or comping.voicing is not None
        or pads.voicing is not None
    )
    if not phase5:
        return

    # PT10: layeringOrder present once, a permutation of the four roles.
    if drums.layering_order is None:
        raise PackLoadError(
            f"{pack_dir / 'patterns' / 'drums.yaml'}: layeringOrder is required "
            f"once per pack (PT10)"
        )
    if sorted(drums.layering_order) != sorted(PATTERN_ROLES):
        raise PackLoadError(
            f"{pack_dir / 'patterns' / 'drums.yaml'}: layeringOrder "
            f"{list(drums.layering_order)} must be a permutation of "
            f"{list(PATTERN_ROLES)} (PT10)"
        )

    # PT6: bass mode required; walking block present iff mode == walking.
    if bass.mode is None:
        raise PackLoadError(
            f"{pack_dir / 'patterns' / 'bass.yaml'}: mode is required "
            f"('patterns' | 'walking') (PT6)"
        )
    if bass.mode == "walking" and bass.walking is None:
        raise PackLoadError(
            f"{pack_dir / 'patterns' / 'bass.yaml'}: mode 'walking' requires a "
            f"walking block (PT6)"
        )
    if bass.mode != "walking" and bass.walking is not None:
        raise PackLoadError(
            f"{pack_dir / 'patterns' / 'bass.yaml'}: walking block is only "
            f"allowed with mode 'walking' (PT6)"
        )

    # PT7: comping/pads must declare a voicing block.
    for role, voiced in (("comping", comping), ("pads", pads)):
        if voiced.voicing is None:
            raise PackLoadError(
                f"{pack_dir / 'patterns' / f'{role}.yaml'}: a voicing block is "
                f"required (PT7)"
            )

    # PT5: completeness per role with a pattern bank; `mode: walking` bass exempt.
    completeness_roles = ["drums", "comping", "pads"]
    if bass.mode == "patterns":
        completeness_roles.append("bass")
    for role in completeness_roles:
        _check_completeness(pack_dir, role, role_patterns[role])


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

    patterns_dir = pack_dir / "patterns"
    drums_bank = _load_bank(patterns_dir / "drums.yaml", DrumsBank)
    bass_bank = _load_bank(patterns_dir / "bass.yaml", BassBank)
    comping_bank = _load_bank(patterns_dir / "comping.yaml", VoicedBank)
    pads_bank = _load_bank(patterns_dir / "pads.yaml", VoicedBank)
    _check_pattern_banks(pack_dir, drums_bank, bass_bank, comping_bank, pads_bank)

    patterns: dict[str, list[PatternEnvelope]] = {
        "drums": drums_bank.patterns,
        "bass": bass_bank.patterns,
        "comping": comping_bank.patterns,
        "pads": pads_bank.patterns,
    }
    voicing: dict[Role, VoicingConfig] = {}
    if comping_bank.voicing is not None:
        voicing["comping"] = comping_bank.voicing
    if pads_bank.voicing is not None:
        voicing["pads"] = pads_bank.voicing

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

    timbres: TimbresConfig | None = None
    timbres_path = pack_dir / "timbres.yaml"
    if timbres_path.exists():
        raw_timbres = _read_yaml(timbres_path)
        if not isinstance(raw_timbres, dict):
            raise PackLoadError(f"{timbres_path}: timbres must be a mapping")
        try:
            timbres = TimbresConfig.model_validate(raw_timbres)
        except ValidationError as exc:
            raise PackLoadError(
                f"{timbres_path}: invalid timbres config\n{exc}"
            ) from exc

    return StylePack(
        manifest=manifest,
        patterns=patterns,
        layering_order=drums_bank.layering_order,
        bass_mode=bass_bank.mode,
        walking=bass_bank.walking,
        voicing=voicing,
        interpreter=interpreter,
        forms=forms,
        progressions=progressions,
        timbres=timbres,
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
