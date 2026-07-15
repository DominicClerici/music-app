"""The `TrackDocument` contract (PHASE_1 §3).

Frozen pydantic v2 models mirroring the document tree exactly as pinned:
`Meta`, `Header` (+ `Tempo`, `TimeSignature`), `Section`, `Track`, `NoteEvent`,
`InstrumentPatch`, `EffectPatch`, `Bus`, `Master`, `Channel`, `Send`, and
`TrackDocument` itself.

The serialized JSON uses camelCase keys (PHASE_1 §3.9); every model here uses a
camelCase `alias_generator` with `populate_by_name=True` so both
`Model(**camel_kwargs)` and `Model(snake_field=...)` construction work, and
`model_dump(by_alias=True)` / `model_dump_json(by_alias=True)` emit the exact
contract keys.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Role = Literal["drums", "bass", "comping", "pads"]

InstrumentType = Literal[
    "Synth",
    "MonoSynth",
    "DuoSynth",
    "FMSynth",
    "AMSynth",
    "MembraneSynth",
    "NoiseSynth",
    "MetalSynth",
    "PluckSynth",
    "PolySynth",
]

PolySynthVoice = Literal[
    "Synth",
    "MonoSynth",
    "FMSynth",
    "AMSynth",
    "MembraneSynth",
    "MetalSynth",
]

EffectType = Literal[
    "Reverb",
    "Freeverb",
    "JCReverb",
    "Chorus",
    "FeedbackDelay",
    "PingPongDelay",
    "Distortion",
    "Filter",
    "EQ3",
    "Compressor",
    "Limiter",
    "StereoWidener",
    "AutoFilter",
    "Tremolo",
    "Vibrato",
]


class DocumentModel(BaseModel):
    """Shared base: frozen, camelCase JSON aliases, alias-or-name construction."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class Meta(DocumentModel):
    """§3.2 `meta` — regeneration identity."""

    generator_version: str
    tone_version: str
    seed: str
    seed_overrides: dict[str, str] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None


class Tempo(DocumentModel):
    ticks: int = Field(ge=0)
    bpm: float = Field(gt=0)


class TimeSignature(DocumentModel):
    ticks: int = Field(ge=0)
    numerator: int
    denominator: Literal[2, 4, 8, 16]


class Header(DocumentModel):
    """§3.3 `header` — timing."""

    ppq: Literal[480] = 480
    tempos: list[Tempo]
    time_signatures: list[TimeSignature]


class Section(DocumentModel):
    """§3.4 `sections` — explicit ranges, not markers.

    `type` is deliberately a plain `str`: the vocabulary is owned by Phase 3.
    """

    type: str
    label: str
    start_tick: int = Field(ge=0)
    end_tick: int = Field(ge=0)
    energy: float = Field(ge=0, le=1)


class NoteEvent(DocumentModel):
    """§3.5 `NoteEvent`.

    `midi` is `int | None` at the field layer; the "required unless NoiseSynth"
    rule is validator V5 (Task 3), not enforced here.
    """

    ticks: int = Field(ge=0)
    duration_ticks: int = Field(ge=1)
    midi: int | None = Field(default=None, ge=0, le=127)
    velocity: float = Field(gt=0, le=1)


class InstrumentPatch(DocumentModel):
    """§3.6 `InstrumentPatch`.

    PolySynth-only `voice`/`max_polyphony` are modeled as optional fields; the
    "PolySynth <=> has both, others <=> neither" rule is validator V7, not
    enforced here.
    """

    type: InstrumentType
    options: dict[str, Any] = Field(default_factory=dict)
    voice: PolySynthVoice | None = None
    max_polyphony: int | None = Field(default=None, ge=1)


class EffectPatch(DocumentModel):
    """§3.6 `EffectPatch`."""

    type: EffectType
    options: dict[str, Any] = Field(default_factory=dict)


class Channel(DocumentModel):
    volume_db: float = Field(le=6)
    pan: float = Field(ge=-1, le=1)
    mute: bool = False


class Send(DocumentModel):
    bus: str
    gain_db: float


class Track(DocumentModel):
    """§3.5 `tracks[]`."""

    id: str
    role: Role
    name: str
    instrument: InstrumentPatch
    effects: list[EffectPatch] = Field(default_factory=list)
    channel: Channel
    sends: list[Send] = Field(default_factory=list)
    notes: list[NoteEvent] = Field(default_factory=list)


class Bus(DocumentModel):
    """§3.6 `buses[]`."""

    id: str
    effects: list[EffectPatch] = Field(default_factory=list)


class Master(DocumentModel):
    """§3.1 `master` — the master effects chain."""

    effects: list[EffectPatch] = Field(default_factory=list)


class TrackDocument(DocumentModel):
    """§3.1 top level."""

    schema_version: int = 1
    meta: Meta
    header: Header
    sections: list[Section]
    buses: list[Bus] = Field(default_factory=list)
    master: Master
    tracks: list[Track]
