"""Energy -> intensity quantization (PHASE_5 §3.1, resolves PHASE_1 Q2).

A pure, deterministic transform: `intensity(energy)` maps a section energy in
[0, 1] onto the 1-4 intensity ladder via the global engine threshold table
(engine-owned data, `intensity.yaml`). No randomness, no clock (ROADMAP
invariant 5).

The threshold table is loaded and validated once at import (mirroring
`harmony/dressing.py`); the §3.1 printed bands are authoritative -- `intensity.yaml`
transcribes them verbatim and this module never tunes them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator


class IntensityLoadError(Exception):
    """Raised when `intensity.yaml` is missing, malformed, or fails validation."""


class _IntensityTable(BaseModel):
    """The §3.1 threshold table: three ascending rung boundaries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    thresholds: tuple[float, ...]

    @model_validator(mode="after")
    def _check(self) -> _IntensityTable:
        # Four rungs => exactly three interior boundaries, strictly ascending.
        if len(self.thresholds) != 3:
            raise ValueError(
                f"thresholds must have exactly 3 boundaries (rungs 1-4), got "
                f"{len(self.thresholds)}"
            )
        if list(self.thresholds) != sorted(self.thresholds) or len(
            set(self.thresholds)
        ) != len(self.thresholds):
            raise ValueError(
                f"thresholds must be strictly ascending, got {self.thresholds}"
            )
        return self


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise IntensityLoadError(
            f"{path}: could not read intensity file ({exc})"
        ) from exc
    except yaml.YAMLError as exc:
        raise IntensityLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_intensity_table() -> _IntensityTable:
    """Load and validate `intensity.yaml` into an `_IntensityTable`."""
    path = Path(__file__).parent / "intensity.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise IntensityLoadError(f"{path}: intensity file must be a mapping")
    try:
        return _IntensityTable.model_validate(raw)
    except ValidationError as exc:
        raise IntensityLoadError(f"{path}: invalid intensity table\n{exc}") from exc


_TABLE = load_intensity_table()


def intensity(energy: float) -> int:
    """The §3.1 intensity rung (1-4) for a section energy.

    Bands are half-open on the low side (an exact boundary opens the higher
    rung): `e < 0.30` -> 1, `0.30 <= e < 0.55` -> 2, `0.55 <= e < 0.80` -> 3,
    `e >= 0.80` -> 4.
    """
    return 1 + sum(1 for threshold in _TABLE.thresholds if energy >= threshold)
