"""The Arrangement planner (PHASE_5 §4).

`arrange()` turns a `SongForm` + `GenerationPlan` into an `ArrangementPlan`:
per section it activates a prefix of the pack's layering order (§4.1), computes
one density budget (§4.2), and places each role in its register lane with the
`registerBias` shift/ceiling applied (§4.3).

Fully deterministic and pure arithmetic: the `rng` parameter exists only for
interface uniformity with the part-generator stages -- the `arrangement` stream
is reserved and consumes **zero** draws in v1 (§3.6). No `random`/clock imports
(ROADMAP invariant 5).

The register-lane table (`lanes.yaml`) is engine-owned data loaded and validated
once at import, mirroring `intensity.yaml`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from trackgen.arrangement.intensity import intensity
from trackgen.interpreter.moods import clamp01
from trackgen.packs.models import StylePack
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementEntry,
    ArrangementPlan,
    FormSection,
    GenerationPlan,
    Register,
    SongForm,
)
from trackgen.seeds import Rng

# §4.1 rung -> base activation count, before per-type modifiers and the
# `layersMax` cap.
_BASE_COUNT: dict[int, int] = {1: 2, 2: 3, 3: 4, 4: 4}

# §4.3 the C-06 ceiling: every non-drum entry's `highMidi` is capped here after
# the `registerBias` shift (PHASE_1 §4.4 re-checks it).
_HIGH_CEILING = 71


class LanesLoadError(Exception):
    """Raised when `lanes.yaml` is missing, malformed, or fails validation."""


class _LanesTable(BaseModel):
    """The §4.3 register-lane table: one `[low, high]` per role."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lanes: dict[Role, tuple[int, int]]

    @model_validator(mode="after")
    def _check(self) -> _LanesTable:
        roles: set[Role] = {"drums", "bass", "comping", "pads"}
        if set(self.lanes) != roles:
            raise ValueError(
                f"lanes must cover exactly {sorted(roles)}, got {sorted(self.lanes)}"
            )
        for role, (low, high) in self.lanes.items():
            if not (0 <= low < high <= 127):
                raise ValueError(
                    f"lane {role!r} = [{low}, {high}] must satisfy "
                    f"0 <= low < high <= 127"
                )
            if high - low < 12:
                raise ValueError(
                    f"lane {role!r} = [{low}, {high}] span ({high - low}) must be "
                    f">= 12 (the §3.3 folding invariant)"
                )
        return self


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise LanesLoadError(f"{path}: could not read lanes file ({exc})") from exc
    except yaml.YAMLError as exc:
        raise LanesLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_lanes_table() -> _LanesTable:
    """Load and validate `lanes.yaml` into a `_LanesTable`."""
    path = Path(__file__).parent / "lanes.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise LanesLoadError(f"{path}: lanes file must be a mapping")
    try:
        return _LanesTable.model_validate(raw)
    except ValidationError as exc:
        raise LanesLoadError(f"{path}: invalid lanes table\n{exc}") from exc


_LANES = load_lanes_table()


def _provisional_count(section: FormSection, layers_max: int) -> int:
    """§4.1 count before the `intro` cross-section rule: the rung base count,
    capped by `layersMax` and by the `breakdown`/`bridge` type modifiers.

    `intro` is resolved separately (`arrange`) because it depends on the *next*
    section's count; every other modifier here is purely local to the section."""
    count = min(layers_max, _BASE_COUNT[intensity(section.energy)])
    if section.type == "breakdown":
        count = min(count, 2)
    elif section.type == "bridge":
        count = min(count, 3)
    return count


def _register_for(role: Role, register_bias: float) -> Register:
    """§4.3 the role's register lane. `drums`/`bass` use their lane unshifted;
    `comping`/`pads` shift both ends by `round(registerBias * 12)` then cap
    `highMidi` at the C-06 ceiling (71), leaving `lowMidi` unclamped."""
    low, high = _LANES.lanes[role]
    if role in ("comping", "pads"):
        shift = round(register_bias * 12)
        low += shift
        high = min(high + shift, _HIGH_CEILING)
    return Register(low_midi=low, high_midi=high)


def arrange(
    plan: GenerationPlan, form: SongForm, pack: StylePack, rng: Rng
) -> ArrangementPlan:
    """Build the `ArrangementPlan` (PHASE_5 §4). Deterministic; `rng` unused."""
    if pack.layering_order is None:
        raise ValueError(
            "arrange() requires a pack with a layeringOrder (§4.1); a Phase-5 "
            "pack must declare it. Got layering_order=None."
        )
    order: tuple[Role, ...] = pack.layering_order
    layers_max = plan.budgets.layers_max
    note_density = plan.budgets.note_density
    register_bias = plan.budgets.register_bias

    provisional = [_provisional_count(section, layers_max) for section in form.sections]

    counts: list[int] = []
    for i, section in enumerate(form.sections):
        if section.type == "intro":
            # §4.1: an intro is one layer thinner than what follows it. Edge
            # guard: an intro that is the LAST section (degenerate/fallback
            # form) has no successor, so it falls back to its own base count.
            if i + 1 < len(form.sections):
                counts.append(max(1, provisional[i + 1] - 1))
            else:
                counts.append(provisional[i])
        else:
            counts.append(provisional[i])

    registers = {role: _register_for(role, register_bias) for role in order}

    entries: list[ArrangementEntry] = []
    for section, count in zip(form.sections, counts, strict=True):
        rung = intensity(section.energy)
        density_budget = round(clamp01(note_density * (0.7 + 0.6 * section.energy)), 3)
        active_roles = set(order[:count])
        for role in order:
            entries.append(
                ArrangementEntry(
                    section_id=section.id,
                    role=role,
                    active=role in active_roles,
                    intensity=rung,
                    density_budget=density_budget,
                    register=registers[role],
                )
            )

    return ArrangementPlan(entries=entries)
