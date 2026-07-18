"""The engine feel data (PHASE_6 §5.3).

Loads `feel.yaml` — the Humanizer's micro-timing offset profiles, timing-jitter
table, velocity accent map, velocity-jitter widths, and bass legato factor —
into frozen pydantic models, and enforces the §5.3 recalibration caps
(`|offset| <= 25 ms`, `jitter <= 10 ms`, `|accent| <= 0.05`).

Module-local like `interpreter/moods.py` (D11): the data lives next to this
module and is read by the fixed-path `load_feel()`; the models are constructable
directly (`FeelData.model_validate({...})`) so tests can feed over-cap values
without editing the committed YAML.
"""

from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import ValidationError, model_validator

from trackgen.packs.models import PackModel

# The ten feel voice/role rows (§5.3). Drums key by voice (tom_* collapse to
# `toms` upstream); pitched roles key by role.
OFFSET_VOICES: tuple[str, ...] = (
    "kick",
    "snare",
    "hats",
    "ride",
    "toms",
    "crash",
    "perc",
    "bass",
    "comping",
    "pads",
)

# The five beat classes (§5.1), the exact keys a per-class map row may carry.
BEAT_CLASSES: tuple[str, ...] = ("down", "back2", "beat3", "back4", "off")

_OFFSET_CAP_MS = 25
_JITTER_CAP_MS = 10
_ACCENT_CAP = 0.05


class FeelLoadError(Exception):
    """Raised when `feel.yaml` is missing, malformed, or fails validation."""


class BeatClassMap(PackModel):
    """A per-beat-class offset row (§5.3): one int per beat class."""

    down: int
    back2: int
    beat3: int
    back4: int
    off: int

    def at(self, beat_class: str) -> int:
        return int(getattr(self, beat_class))


# An offset row is EITHER a scalar int (same value for every beat class) OR a
# per-beat-class map (§5.3).
OffsetRow = int | BeatClassMap


class OffsetProfile(PackModel):
    """One named offset profile (`swung` / `straight`): a scalar-or-map row per
    voice/role, capped at `|offset| <= 25 ms` across every row and profile."""

    kick: OffsetRow
    snare: OffsetRow
    hats: OffsetRow
    ride: OffsetRow
    toms: OffsetRow
    crash: OffsetRow
    perc: OffsetRow
    bass: OffsetRow
    comping: OffsetRow
    pads: OffsetRow

    def offset(self, voice: str, beat_class: str) -> int:
        """The offset in ms for `voice` at `beat_class`. A scalar row yields the
        same value for every class; a map row indexes by class."""
        row: OffsetRow = getattr(self, voice)
        if isinstance(row, BeatClassMap):
            return row.at(beat_class)
        return row

    @model_validator(mode="after")
    def _check_offset_cap(self) -> "OffsetProfile":
        for voice in OFFSET_VOICES:
            row: OffsetRow = getattr(self, voice)
            values = (
                [row.at(bc) for bc in BEAT_CLASSES]
                if isinstance(row, BeatClassMap)
                else [row]
            )
            for value in values:
                if abs(value) > _OFFSET_CAP_MS:
                    raise ValueError(
                        f"offset {value} ms for voice {voice!r} exceeds the "
                        f"|offset| <= {_OFFSET_CAP_MS} ms cap (§5.3)"
                    )
        return self


# The engine's named offset-profile menu (PHASE_8 §3.4): the original two plus
# `laidback` (lo-fi) and `tight` (fusion). A pack's `feelTable` selects by name.
FEEL_PROFILES: tuple[str, ...] = ("straight", "swung", "laidback", "tight")


class Offsets(PackModel):
    """The named offset profiles (§5.3, PHASE_8 §3.4): `straight`, `swung`,
    `laidback`, `tight`."""

    swung: OffsetProfile
    straight: OffsetProfile
    laidback: OffsetProfile
    tight: OffsetProfile

    def profile(self, name: str) -> OffsetProfile:
        """The named offset profile. `name` must be one of `FEEL_PROFILES`."""
        if name not in FEEL_PROFILES:
            raise ValueError(
                f"unknown feel profile {name!r}; expected one of {FEEL_PROFILES}"
            )
        return cast(OffsetProfile, getattr(self, name))


class JitterTable(PackModel):
    """The shared timing-jitter table (§5.3), one width in ms per voice/role,
    capped at `jitter <= 10 ms`."""

    kick: int
    snare: int
    hats: int
    ride: int
    toms: int
    crash: int
    perc: int
    bass: int
    comping: int
    pads: int

    def at(self, voice: str) -> int:
        return int(getattr(self, voice))

    @model_validator(mode="after")
    def _check_jitter_cap(self) -> "JitterTable":
        for voice in OFFSET_VOICES:
            value = int(getattr(self, voice))
            if abs(value) > _JITTER_CAP_MS:
                raise ValueError(
                    f"jitter {value} ms for voice {voice!r} exceeds the "
                    f"jitter <= {_JITTER_CAP_MS} ms cap (§5.3)"
                )
        return self


class AccentMap(PackModel):
    """The velocity accent map (§5.5), one delta per beat class, capped at
    `|accent| <= 0.05`."""

    down: float
    back2: float
    beat3: float
    back4: float
    off: float

    def at(self, beat_class: str) -> float:
        return float(getattr(self, beat_class))

    @model_validator(mode="after")
    def _check_accent_cap(self) -> "AccentMap":
        for beat_class in BEAT_CLASSES:
            value = float(getattr(self, beat_class))
            if abs(value) > _ACCENT_CAP:
                raise ValueError(
                    f"accent {value} for beat class {beat_class!r} exceeds the "
                    f"|accent| <= {_ACCENT_CAP} cap (§5.5)"
                )
        return self


class VelJitter(PackModel):
    """The velocity-jitter width parameters (§5.5): `base` + `rangeScale`."""

    base: float
    range_scale: float


class FeelData(PackModel):
    """The complete §5.3 feel data: offset profiles, jitter table, accent map,
    velocity-jitter widths, and the bass legato factor."""

    offsets_ms: Offsets
    jitter_ms: JitterTable
    accent: AccentMap
    vel_jitter: VelJitter
    bass_legato: float


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise FeelLoadError(f"{path}: could not read feel file ({exc})") from exc
    except yaml.YAMLError as exc:
        raise FeelLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_feel() -> FeelData:
    """Load and validate the module-adjacent `feel.yaml` into a `FeelData`."""
    path = Path(__file__).parent / "feel.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise FeelLoadError(f"{path}: feel file must be a mapping")
    try:
        return FeelData.model_validate(raw)
    except ValidationError as exc:
        raise FeelLoadError(f"{path}: invalid feel data\n{exc}") from exc
