"""Style-pack structure (PHASE_1 §6).

Frozen pydantic v2 models for the pack manifest (§6.1), the shared pattern
envelope (§6.2), and the event primitives (§6.3). Bank-specific fields owned
by later phases (progressions/forms/timbres/interpreter schemas, and any
role-specific envelope extensions) are deliberately NOT modeled here.

`degree` is restricted to the §6.3 v1 core vocabulary only: `root, third,
fifth, seventh, guide3, guide7, tension, approach`. Phase 5's later
extensions (`sixth`, `chord`, `push`, `minDensity`) are out of scope.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from trackgen.schema.document import Role

Degree = Literal[
    "root",
    "third",
    "fifth",
    "seventh",
    "guide3",
    "guide7",
    "tension",
    "approach",
]

DrumVoice = Literal[
    "kick",
    "snare",
    "hat_closed",
    "hat_open",
    "ride",
    "crash",
    "tom_low",
    "tom_mid",
    "tom_high",
    "perc",
]

PatternKind = Literal["main", "fill", "intro", "ending", "break"]

OnChordChange = Literal["hold", "retrigger", "stop"]


class PackModel(BaseModel):
    """Shared base: frozen, camelCase JSON aliases, alias-or-name construction."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Manifest(PackModel):
    """§6.1 `manifest.yaml` (pinned)."""

    format_version: int
    id: str
    name: str
    version: str
    engine: str
    time_signatures: list[tuple[int, int]]
    tempo_range: tuple[int, int]


class PitchedEvent(PackModel):
    """§6.3 pitched-role event: rhythm + chord-degree, never a literal pitch."""

    pos: int = Field(ge=0)
    dur: int = Field(ge=1)
    degree: Degree
    octave: int
    velocity: float = Field(gt=0, le=1)


class DrumEvent(PackModel):
    """§6.3 drum event: voice + velocity, no harmonic content."""

    pos: int = Field(ge=0)
    voice: DrumVoice
    velocity: float = Field(gt=0, le=1)


class Retarget(PackModel):
    """§6.2 `retarget` — pinned envelope + event fields only."""

    register_low: int
    register_high: int
    on_chord_change: OnChordChange


class Eligibility(PackModel):
    """§6.2 `eligibility` — v1: optional `tempoBpm: [min, max]` only."""

    tempo_bpm: tuple[int, int] | None = None


class PatternEnvelope(PackModel):
    """§6.2 shared pattern envelope, carried by every entry in every bank."""

    id: str
    role: Role
    kind: PatternKind
    energy_level: int = Field(ge=1, le=4)
    length_ticks: int = Field(ge=1)
    weight: int = Field(ge=1)
    eligibility: Eligibility = Field(default_factory=Eligibility)
    events: list[PitchedEvent | DrumEvent]
    retarget: Retarget


class StylePack(PackModel):
    """A loaded, validated style pack: manifest + per-role pattern banks."""

    manifest: Manifest
    patterns: dict[str, list[PatternEnvelope]]
