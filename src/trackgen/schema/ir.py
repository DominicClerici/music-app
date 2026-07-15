"""The five pipeline IR pinned cores (PHASE_1 §4).

IRs are internal — never serialized into `TrackDocument` — so their Python
field names stay plain snake_case; no camelCase alias requirement.
"""

import warnings
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trackgen.schema.document import Role

ChordQuality = Literal[
    "maj",
    "min",
    "dim",
    "aug",
    "maj6",
    "min6",
    "dom7",
    "maj7",
    "min7",
    "minMaj7",
    "min7b5",
    "dim7",
    "sus2",
    "sus4",
    "dom7sus4",
]


class IRModel(BaseModel):
    """Shared base for all IR models: frozen, plain (non-aliased) fields."""

    model_config = ConfigDict(frozen=True)


# --- 4.1 GenerationPlan ------------------------------------------------------


class StylePackRef(IRModel):
    id: str
    version: str


class SeedSpec(IRModel):
    master: int = Field(ge=0)
    overrides: dict[str, int] = Field(default_factory=dict)


class Key(IRModel):
    tonic_pc: int = Field(ge=0, le=11)
    mode: str


class TimeSignature(IRModel):
    numerator: int
    denominator: Literal[2, 4, 8, 16]


class SwingSpec(IRModel):
    ratio: float = Field(ge=0.5, le=0.75)
    subdivision: Literal["8", "16"]


class MoodVector(IRModel):
    """§7.1 — the resolved mood's V/A anchor."""

    valence: float = Field(ge=-1, le=1)
    arousal: float = Field(ge=-1, le=1)


class Budgets(IRModel):
    """§7.2 — pack-scaled generation budgets."""

    note_density: float = Field(ge=0, le=1)
    dissonance: float = Field(ge=0, le=1)
    dynamics_base: float = Field(ge=0, le=1)
    dynamics_range: float = Field(ge=0, le=1)
    articulation_legato: float = Field(ge=0, le=1)
    layers_max: int = Field(ge=2, le=4)
    harmonic_rhythm_base: float
    register_bias: float = Field(ge=-1, le=1)


class TimbreDirectives(IRModel):
    """§7.3 — Phase 7 sound-design tendencies."""

    brightness: float = Field(ge=0, le=1)
    attack_hardness: float = Field(ge=0, le=1)
    space: float = Field(ge=0, le=1)


class GenerationPlan(IRModel):
    """§4.1 — produced by Interpreter, consumed by every stage."""

    style_pack: StylePackRef
    seed: SeedSpec
    key: Key
    tempo_bpm: float = Field(gt=0)
    time_signature: TimeSignature
    swing: SwingSpec | None = None
    max_length_ticks: int = Field(ge=0)
    role_flavors: dict[str, str] = Field(default_factory=dict)
    mood_vector: MoodVector
    budgets: Budgets
    timbre_directives: TimbreDirectives


# --- 4.2 SongForm -------------------------------------------------------------


class SectionPhrase(IRModel):
    """§4.1 — one phrase within a section's `phrases` list."""

    label: str
    bars: int = Field(ge=1)


class SectionEnding(IRModel):
    """§4.1 — the ending directive; non-null on the final section only."""

    tag_bars: Literal[0, 4, 8]
    close: Literal["ritard", "cold", "fade"]


class FormSection(IRModel):
    id: str
    type: str
    index: int = Field(ge=1)
    start_bar: int = Field(ge=0)
    length_bars: int = Field(ge=4)
    energy: float = Field(ge=0, le=1)
    total_of_type: int = Field(ge=1)
    phrases: list[SectionPhrase]
    harmony_tag: str
    variant: str | None = None
    ending: SectionEnding | None = None


class SongForm(IRModel):
    """§4.2 — produced by Form generator."""

    sections: list[FormSection]
    total_bars: int = Field(ge=0)
    template_id: str


# --- 4.3 HarmonicPlan ---------------------------------------------------------


class ChordSpec(IRModel):
    root_pc: int = Field(ge=0, le=11)
    quality: ChordQuality
    extensions: list[str] = Field(default_factory=list)
    bass_pc: int | None = Field(default=None, ge=0, le=11)
    symbol: str
    roman: str | None = None


class ChordEvent(IRModel):
    start_tick: int = Field(ge=0)
    duration_ticks: int = Field(ge=1)
    section_id: str
    chord: ChordSpec


class HarmonicPlan(IRModel):
    """§4.3 — produced by Harmony engine."""

    chords: list[ChordEvent]


# --- 4.4 ArrangementPlan -------------------------------------------------------


class Register(IRModel):
    low_midi: int = Field(ge=0, le=127)
    high_midi: int = Field(ge=0, le=127)


# `register` is pinned by §4.4; it shadows the inherited ABCMeta.register
# classmethod, which pydantic warns about. The classmethod is never used on these
# frozen data models, so we suppress that one warning while keeping the pinned name.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)

    class ArrangementEntry(IRModel):
        section_id: str
        role: Role
        active: bool
        intensity: int = Field(ge=1, le=4)
        density_budget: float = Field(ge=0, le=1)
        register: Register


class ArrangementPlan(IRModel):
    """§4.4 — produced by Arrangement planner."""

    entries: list[ArrangementEntry]


# --- 4.5 Phrase ----------------------------------------------------------------


class PhraseNote(IRModel):
    ticks: int = Field(ge=0)
    duration_ticks: int = Field(ge=1)
    midi: int | None = Field(default=None, ge=0, le=127)
    velocity: float = Field(gt=0, le=1)
    tags: list[str] = Field(default_factory=list)


class Phrase(IRModel):
    """§4.5 — produced by Part generators; consumed by Serializer."""

    track_id: str
    role: Role
    start_tick: int = Field(ge=0)
    end_tick: int = Field(ge=0)
    notes: list[PhraseNote]
