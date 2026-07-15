"""The energy model (PHASE_3 §6).

Loads `energy.yaml` — the engine's §6.1 base energy table for the 11
section types — into a frozen pydantic model, and implements the §6.2
positional rules, §6.3 arousal modulation, and §6.4 pack envelope as a pure
function.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError, model_validator

from trackgen.interpreter.moods import clamp01
from trackgen.packs.models import SECTION_TYPES, PackModel

# PHASE_3 §3.1 — the 11-type section vocabulary is owned by `trackgen.packs.models`
# (single source of truth); imported here rather than duplicated.
_SECTION_TYPE_SET = frozenset(SECTION_TYPES)

# PHASE_3 §6.2 — types eligible for the R1 repeat-escalation rule.
_R1_ESCALATION_TYPES = frozenset({"verse", "prechorus", "chorus", "postchorus", "main"})


class EnergyLoadError(Exception):
    """Raised when `energy.yaml` is missing, malformed, or fails validation."""


class EnergyTable(PackModel):
    """The §6.1 engine base energy table, keyed by section type."""

    base: dict[str, float]

    @model_validator(mode="after")
    def _check_vocabulary(self) -> "EnergyTable":
        keys = set(self.base)
        unknown = keys - _SECTION_TYPE_SET
        if unknown:
            raise ValueError(f"unknown section type(s) {sorted(unknown)}")
        missing = _SECTION_TYPE_SET - keys
        if missing:
            raise ValueError(f"missing section type(s) {sorted(missing)}")
        return self


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise EnergyLoadError(f"{path}: could not read energy file ({exc})") from exc
    except yaml.YAMLError as exc:
        raise EnergyLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_energy_table() -> EnergyTable:
    """Load and validate `energy.yaml` into an `EnergyTable`."""
    path = Path(__file__).parent / "energy.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise EnergyLoadError(f"{path}: energy file must be a mapping")
    try:
        return EnergyTable.model_validate(raw)
    except ValidationError as exc:
        raise EnergyLoadError(f"{path}: invalid energy table\n{exc}") from exc


_energy_table_cache: EnergyTable | None = None


def _default_table() -> EnergyTable:
    global _energy_table_cache
    if _energy_table_cache is None:
        _energy_table_cache = load_energy_table()
    return _energy_table_cache


def section_energy(
    section_type: str,
    index: int,
    total_of_type: int,
    arousal: float,
    energy_range: tuple[float, float],
    override: float | None = None,
    table: EnergyTable | None = None,
) -> float:
    """PHASE_3 §6.2 -> §6.3 -> §6.4, in that exact order.

    1. Determine base `e`: an explicit `override` (R4) replaces base + R1-R3
       outright; else `solo` gets the R2 arch (also replacing base, `head`
       has no such rule); else the table base plus R1 escalation and R3
       final-chorus peak.
    2. §6.3 arousal modulation: `e = clamp01(e + 0.10 * arousal)`.
    3. §6.4 pack envelope: `round(lo + e * (hi - lo), 3)` (half-even).
    """
    if table is None:
        table = _default_table()

    if override is not None:
        e = override
    elif section_type == "solo":
        e = 0.60 + 0.30 * index / total_of_type
    else:
        e = table.base[section_type]
        if section_type in _R1_ESCALATION_TYPES:
            e += 0.05 * min(index - 1, 2)
        if section_type == "chorus" and index == total_of_type and total_of_type >= 2:
            e += 0.15

    e = clamp01(e + 0.10 * arousal)

    lo, hi = energy_range
    return round(lo + e * (hi - lo), 3)
