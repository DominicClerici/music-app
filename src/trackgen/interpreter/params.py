"""The public `params` schema and its validation-error catalog (PHASE_2 §3).

`Params` is the public API surface — a frozen pydantic model mirroring §3's
field table exactly, with camelCase JSON aliases. It intentionally carries no
domain defaults (PHASE_2 §3/D6): `meta.params` must be able to echo the
user's input verbatim, so defaults (mood, tempo, tonic, ...) are applied
later by the Interpreter, not baked in here.

`validate_params` implements the full §3.1 error catalog (all 14 codes)
against the *raw* client dict (camelCase keys), reporting the complete list
of violations rather than stopping at the first (PHASE_2 §3.1).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from trackgen.interpreter.moods import MOOD_VOCABULARY
from trackgen.packs.loader import registered_styles
from trackgen.packs.models import StylePack
from trackgen.schema.document import Role
from trackgen.seeds import STREAMS, from_base36

DEFAULT_PARAMS_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "schema" / "params.schema.json"
)

_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")

_TONIC_PITCH_CLASS: dict[str, int] = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}


class ParamsModel(BaseModel):
    """Shared base for the public `params` surface: frozen, camelCase JSON
    aliases, alias-or-name construction, no unknown fields (mirrors
    `trackgen.packs.models.PackModel`'s convention)."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class KeySpec(ParamsModel):
    """PHASE_2 §3 `params.key` — either subfield may be given alone."""

    tonic: str | None = None
    mode: str | None = None


class Params(ParamsModel):
    """PHASE_2 §3 — the complete `params` input surface.

    All fields but `style_family` are optional; no domain defaults are baked
    in here (defaults are the Interpreter's job, PHASE_2 §6).
    """

    style_family: str
    mood: str | None = None
    tempo_bpm: int | None = None
    key: KeySpec | None = None
    role_flavors: dict[str, str] = Field(default_factory=dict)
    ensemble_preset: str | None = None
    max_length_sec: int | None = None
    seed: str | None = None
    seed_text: str | None = None
    seed_overrides: dict[str, str] = Field(default_factory=dict)
    title: str | None = None


@dataclass(frozen=True)
class ParamError:
    """PHASE_2 §3.1 — a single structured validation error."""

    code: str
    field: str
    message: str


def parse_tonic(s: str) -> int | None:
    """PHASE_2 §3.1 tonic parser: note letter A-G (case-insensitive) with an
    optional single `#`/`b` accidental, to a pitch class 0-11.

    Returns `None` for anything unparsable (drives `KEY_TONIC_INVALID`).
    """
    if not isinstance(s, str) or not s:
        return None
    letter = s[0].upper()
    pitch_class = _TONIC_PITCH_CLASS.get(letter)
    if pitch_class is None:
        return None
    accidental_str = s[1:]
    if accidental_str == "":
        accidental = 0
    elif accidental_str == "#":
        accidental = 1
    elif accidental_str == "b":
        accidental = -1
    else:
        return None
    return (pitch_class + accidental) % 12


def _is_valid_base36_u64(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    try:
        from_base36(s)
    except ValueError:
        return False
    return True


def validate_params(raw: dict[str, Any], pack: StylePack | None) -> list[ParamError]:
    """PHASE_2 §3.1 — the full validation-error catalog against the raw
    (camelCase) client dict. Returns the complete list of violations; never
    stops at the first (SESSION_02 D-S6).

    `pack` is the already-resolved style pack (`resolve_pack(styleFamily)`),
    or `None` when `styleFamily` is missing or unregistered. When `pack` is
    `None`, `STYLE_UNKNOWN` is emitted and the pack-independent checks still
    run, but pack-relative checks (which need pack data) are skipped.
    """
    errors: list[ParamError] = []

    style_family = raw.get("styleFamily")
    if pack is None:
        errors.append(
            ParamError(
                code="STYLE_UNKNOWN",
                field="styleFamily",
                message=(
                    f"styleFamily {style_family!r} is not a registered style; "
                    f"registered styles: {sorted(registered_styles())}"
                ),
            )
        )

    # --- Pack-independent checks (always run) -------------------------------

    seed = raw.get("seed")
    seed_text = raw.get("seedText")
    if seed is not None and seed_text is not None:
        errors.append(
            ParamError(
                code="SEED_CONFLICT",
                field="seed",
                message="seed and seedText are mutually exclusive",
            )
        )
    if seed is not None and not _is_valid_base36_u64(seed):
        errors.append(
            ParamError(
                code="SEED_INVALID",
                field="seed",
                message=f"seed {seed!r} is not a valid base36 u64",
            )
        )

    max_length_sec = raw.get("maxLengthSec")
    if (
        isinstance(max_length_sec, (int, float))
        and not isinstance(max_length_sec, bool)
        and not (30 <= max_length_sec <= 600)
    ):
        errors.append(
            ParamError(
                code="LENGTH_OUT_OF_RANGE",
                field="maxLengthSec",
                message=f"maxLengthSec must be within [30, 600], got {max_length_sec}",
            )
        )

    mood = raw.get("mood")
    mood_known = mood is None or mood in MOOD_VOCABULARY
    if mood is not None and not mood_known:
        errors.append(
            ParamError(
                code="MOOD_UNKNOWN",
                field="mood",
                message=f"mood {mood!r} is not one of {MOOD_VOCABULARY}",
            )
        )

    title = raw.get("title")
    if isinstance(title, str) and len(title) > 120:
        errors.append(
            ParamError(
                code="TITLE_TOO_LONG",
                field="title",
                message=f"title exceeds 120 characters (got {len(title)})",
            )
        )

    raw_role_flavors = raw.get("roleFlavors")
    role_flavors = raw_role_flavors if isinstance(raw_role_flavors, dict) else {}
    for role in role_flavors:
        if role not in _ROLES:
            errors.append(
                ParamError(
                    code="ROLE_UNKNOWN",
                    field="roleFlavors",
                    message=f"roleFlavors key {role!r} is not one of {_ROLES}",
                )
            )

    raw_seed_overrides = raw.get("seedOverrides")
    seed_overrides = raw_seed_overrides if isinstance(raw_seed_overrides, dict) else {}
    for stream, value in seed_overrides.items():
        if stream not in STREAMS:
            errors.append(
                ParamError(
                    code="STREAM_UNKNOWN",
                    field="seedOverrides",
                    message=(
                        f"seedOverrides key {stream!r} is not a registered "
                        f"stream {STREAMS}"
                    ),
                )
            )
        elif not _is_valid_base36_u64(value):
            errors.append(
                ParamError(
                    code="SEED_INVALID",
                    field="seedOverrides",
                    message=(
                        f"seedOverrides[{stream!r}] value {value!r} is not a "
                        f"valid base36 u64"
                    ),
                )
            )

    key = raw.get("key") or {}
    tonic = key.get("tonic") if isinstance(key, dict) else None
    if tonic is not None and parse_tonic(tonic) is None:
        errors.append(
            ParamError(
                code="KEY_TONIC_INVALID",
                field="key.tonic",
                message=f"key.tonic {tonic!r} is not a parsable note name",
            )
        )

    # --- Pack-relative checks (skipped when pack is unresolved) -------------

    interp = pack.interpreter if pack is not None else None
    if pack is not None and interp is not None:
        if mood is not None and mood_known and mood not in interp.supported_moods:
            errors.append(
                ParamError(
                    code="MOOD_UNSUPPORTED",
                    field="mood",
                    message=(
                        f"mood {mood!r} is not supported by this pack; "
                        f"supported moods: {interp.supported_moods}"
                    ),
                )
            )

        tempo_bpm = raw.get("tempoBpm")
        if isinstance(tempo_bpm, (int, float)) and not isinstance(tempo_bpm, bool):
            lo, hi = pack.manifest.tempo_range
            if not (lo <= tempo_bpm <= hi):
                errors.append(
                    ParamError(
                        code="TEMPO_OUT_OF_RANGE",
                        field="tempoBpm",
                        message=(
                            f"tempoBpm must be within [{lo}, {hi}], got {tempo_bpm}"
                        ),
                    )
                )

        mode = key.get("mode") if isinstance(key, dict) else None
        if mode is not None and mode not in interp.modes:
            errors.append(
                ParamError(
                    code="MODE_UNSUPPORTED",
                    field="key.mode",
                    message=(
                        f"key.mode {mode!r} is not in the pack's mode menu "
                        f"{interp.modes}"
                    ),
                )
            )

        for role, flavor in role_flavors.items():
            if role in _ROLES:
                role_lit = cast(Role, role)
                if flavor not in interp.flavors.get(role_lit, []):
                    errors.append(
                        ParamError(
                            code="FLAVOR_UNKNOWN",
                            field="roleFlavors",
                            message=(
                                f"roleFlavors[{role!r}] = {flavor!r} is not a "
                                f"declared flavor for {role!r}"
                            ),
                        )
                    )

        ensemble_preset = raw.get("ensemblePreset")
        if ensemble_preset is not None and ensemble_preset not in interp.ensembles:
            errors.append(
                ParamError(
                    code="PRESET_UNKNOWN",
                    field="ensemblePreset",
                    message=(
                        f"ensemblePreset {ensemble_preset!r} is not declared "
                        f"by this pack"
                    ),
                )
            )

    return errors


def params_schema_json() -> str:
    """Return the exported `Params` JSON Schema as a deterministic, formatted
    string (mirrors `trackgen.schema.export.schema_json`)."""
    schema = Params.model_json_schema(by_alias=True)
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def export_params_schema(path: Path = DEFAULT_PARAMS_SCHEMA_PATH) -> Path:
    """Write the exported `Params` JSON Schema to `path` (mirrors
    `trackgen.schema.export.export_schema`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(params_schema_json(), encoding="utf-8")
    return path
