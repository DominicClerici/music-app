"""The mood model (PHASE_2 §4).

Loads `moods.yaml` — the 12-word mood vocabulary's (valence, arousal)
anchors plus per-mood overrides — into frozen pydantic models, and implements
the §4.2 derived-value formulas and §4.3 override application.

Coordinates are internal implementation detail (PHASE_2 D6): the public API
surface (a sibling task) accepts mood words only.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, ValidationError, model_validator

from trackgen.packs.models import PackModel

MOOD_VOCABULARY: tuple[str, ...] = (
    "happy",
    "energetic",
    "triumphant",
    "calm",
    "dreamy",
    "romantic",
    "nostalgic",
    "melancholic",
    "dark",
    "mysterious",
    "tense",
    "aggressive",
)

# PHASE_2 §6.3 / D8 — the engine mode ladder (empirically monotonic in
# valence; Lydian excluded in v1).
MODE_LADDER: tuple[str, ...] = ("major", "mixolydian", "dorian", "minor", "phrygian")

# PHASE_2 §4.2 — the 13 derived-value names; the only keys an override may
# name (§4.3).
DERIVED_KEYS: tuple[str, ...] = (
    "tempoCenter",
    "noteDensityNorm",
    "dissonanceNorm",
    "dynamicsBase",
    "dynamicsRange",
    "articulationLegato",
    "layersMax",
    "harmonicRhythmBase",
    "registerBias",
    "brightness",
    "attackHardness",
    "space",
)

_DERIVED_KEY_SET = frozenset(DERIVED_KEYS)
_MOOD_VOCABULARY_SET = frozenset(MOOD_VOCABULARY)


class MoodLoadError(Exception):
    """Raised when `moods.yaml` is missing, malformed, or fails validation."""


class MoodRow(PackModel):
    """A single mood's (valence, arousal) anchor plus optional overrides (§4.3)."""

    valence: float = Field(ge=-1, le=1)
    arousal: float = Field(ge=-1, le=1)
    overrides: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_override_keys(self) -> "MoodRow":
        unknown = set(self.overrides) - _DERIVED_KEY_SET
        if unknown:
            raise ValueError(
                f"unknown override key(s) {sorted(unknown)}; "
                f"must be a subset of {DERIVED_KEYS}"
            )
        return self


class MoodTable(PackModel):
    """The full 12-mood table, keyed by mood word."""

    moods: dict[str, MoodRow]

    @model_validator(mode="after")
    def _check_vocabulary(self) -> "MoodTable":
        keys = set(self.moods)
        unknown = keys - _MOOD_VOCABULARY_SET
        if unknown:
            raise ValueError(f"unknown mood word(s) {sorted(unknown)}")
        missing = _MOOD_VOCABULARY_SET - keys
        if missing:
            raise ValueError(f"missing mood word(s) {sorted(missing)}")
        return self


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise MoodLoadError(f"{path}: could not read mood file ({exc})") from exc
    except yaml.YAMLError as exc:
        raise MoodLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_moods() -> MoodTable:
    """Load and validate `moods.yaml` into a `MoodTable`."""
    path = Path(__file__).parent / "moods.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise MoodLoadError(f"{path}: mood file must be a mapping")
    try:
        return MoodTable.model_validate(raw)
    except ValidationError as exc:
        raise MoodLoadError(f"{path}: invalid mood table\n{exc}") from exc


def clamp01(x: float) -> float:
    """PHASE_2 §4.2 — `clamp01(x) = min(1, max(0, x))`."""
    return min(1.0, max(0.0, x))


def formulas(valence: float, arousal: float) -> dict[str, float | int]:
    """PHASE_2 §4.2 — the 13 derived values from a (valence, arousal) anchor.

    Every derived float is rounded to 3 decimals (half-even) except
    `tempoCenter`, which is kept unrounded (it is consumed as a raw BPM by
    later tempo logic; §4.4 shows it to 1 decimal only for display).
    """
    v, a = valence, arousal
    return {
        "tempoCenter": 100 * 2 ** (0.6 * a),
        "noteDensityNorm": round(clamp01(0.55 + 0.35 * a), 3),
        "dissonanceNorm": round(clamp01(0.40 - 0.30 * v + 0.15 * max(0.0, a)), 3),
        "dynamicsBase": round(clamp01(0.55 + 0.25 * a), 3),
        "dynamicsRange": round(clamp01(0.15 + 0.15 * abs(a)), 3),
        "articulationLegato": round(clamp01(0.5 - 0.4 * a), 3),
        "layersMax": 2 if a <= -0.7 else (3 if a <= 0.3 else 4),
        "harmonicRhythmBase": 0.5 if a < -0.4 else 1.0,
        "registerBias": round(0.25 * v, 3),
        "brightness": round(clamp01(0.55 + 0.30 * v + 0.15 * a), 3),
        "attackHardness": round(clamp01(0.5 + 0.4 * a), 3),
        "space": round(clamp01(0.5 - 0.35 * a), 3),
    }


def apply_overrides(
    overrides: dict[str, float], derived: dict[str, float | int]
) -> dict[str, float | int]:
    """PHASE_2 §4.3 — replace derived values with override values verbatim.

    Overrides act in normalized space, after the formula and before any pack
    scaling; override constants are already final and are never re-rounded.
    """
    result = dict(derived)
    result.update(overrides)
    return result


def derived_defaults(mood: str, table: MoodTable) -> dict[str, float | int]:
    """Look up `mood` in `table`, run the formulas, and apply its overrides."""
    row = table.moods[mood]
    derived = formulas(row.valence, row.arousal)
    return apply_overrides(row.overrides, derived)
