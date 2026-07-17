"""The thin Serializer (PHASE_5 §8.3, D-C).

`serialize(plan, form, phrases, patches)` assembles the `TrackDocument` from the
generated `Phrase`s, the `SongForm`, and the sound-design patch map. It is a pure
function: no I/O, no draws, no wall-clock. The output passes every PHASE_1 §3.8
validator rule (V1-V8).

The channel/mix table below is the §8.3 **stub** engine table — authoritative for
the milestone and intentionally distinct from the PHASE_1 fixture's hand-authored
mix (PHASE_7 §7 replaces it with the sound-design stage's per-track mix).
"""

import json

from trackgen.form.stage import section_label
from trackgen.parts.generators import _TRACK_ORDER
from trackgen.pipeline.stubs import TrackSound
from trackgen.schema.document import (
    Channel,
    EffectPatch,
    Header,
    Master,
    Meta,
    NoteEvent,
    Role,
    Section,
    Tempo,
    TimeSignature,
    Track,
    TrackDocument,
)
from trackgen.schema.ir import GenerationPlan, Phrase, PhraseNote, SongForm
from trackgen.seeds import to_base36

_TICKS_PER_BAR = 1920

# §8.3 stub engine mix table (track_id -> (volumeDb, pan)); mute is always False.
_STUB_MIX: dict[str, tuple[float, float]] = {
    "kick": (-2, 0),
    "snare": (-4, 0),
    "hats": (-4, 0.2),
    "ride": (-4, -0.15),
    "tom_low": (-4, 0),
    "tom_mid": (-4, 0),
    "tom_high": (-4, 0),
    "perc": (-4, 0),
    "bass": (-3, 0),
    "comping": (-6, 0.1),
    "pads": (-10, -0.1),
}

# Track emit order: the drum sub-order, then the pitched roles.
_EMIT_ORDER: tuple[str, ...] = (*_TRACK_ORDER, "bass", "comping", "pads")

_GENERATOR_VERSION = "0.1.0"
_TONE_VERSION = "^15.1.0"

_MASTER_EFFECTS = (
    EffectPatch(type="Compressor", options={"threshold": -24, "ratio": 4}),
    EffectPatch(type="Limiter", options={"threshold": -1}),
)


def serialize(
    plan: GenerationPlan,
    form: SongForm,
    phrases: list[Phrase],
    patches: dict[str, TrackSound],
    *,
    params: dict[str, object] | None = None,
) -> TrackDocument:
    """Assemble a `TrackDocument` from generated phrases (PHASE_5 §8.3, D-C)."""
    sections = _build_sections(form)
    song_end = sections[-1].end_tick

    grouped = _group_by_track(phrases)
    tracks = [
        track
        for track_id in _EMIT_ORDER
        if track_id in grouped
        for track in (_build_track(track_id, grouped[track_id], patches, song_end),)
        if track is not None
    ]

    meta = Meta(
        generator_version=_GENERATOR_VERSION,
        tone_version=_TONE_VERSION,
        seed=to_base36(plan.seed.master),
        seed_overrides={k: to_base36(v) for k, v in plan.seed.overrides.items()},
        params=params if params is not None else {},
    )
    header = Header(
        ppq=480,
        tempos=[Tempo(ticks=0, bpm=plan.tempo_bpm)],
        time_signatures=[
            TimeSignature(
                ticks=0,
                numerator=plan.time_signature.numerator,
                denominator=plan.time_signature.denominator,
            )
        ],
    )
    return TrackDocument(
        meta=meta,
        header=header,
        sections=sections,
        buses=[],
        master=Master(effects=list(_MASTER_EFFECTS)),
        tracks=tracks,
    )


def _build_sections(form: SongForm) -> list[Section]:
    return [
        Section(
            type=s.type,
            label=section_label(s.type, s.index, s.total_of_type, s.variant),
            start_tick=s.start_bar * _TICKS_PER_BAR,
            end_tick=(s.start_bar + s.length_bars) * _TICKS_PER_BAR,
            energy=s.energy,
        )
        for s in form.sections
    ]


def _group_by_track(phrases: list[Phrase]) -> dict[str, list[Phrase]]:
    grouped: dict[str, list[Phrase]] = {}
    for phrase in phrases:
        grouped.setdefault(phrase.track_id, []).append(phrase)
    return grouped


def _build_track(
    track_id: str,
    track_phrases: list[Phrase],
    patches: dict[str, TrackSound],
    song_end: int,
) -> Track | None:
    role: Role = track_phrases[0].role
    is_drum = role == "drums"
    trigger_midi = patches[track_id].midi if is_drum else None

    events: list[NoteEvent] = []
    for phrase in sorted(track_phrases, key=lambda p: p.start_tick):
        for note in phrase.notes:
            event = _to_event(note, is_drum, trigger_midi, song_end)
            if event is not None:
                events.append(event)

    if not events:
        return None

    events.sort(key=lambda e: (e.ticks, e.midi if e.midi is not None else -1))

    sound = patches[track_id]
    volume_db, pan = _STUB_MIX[track_id]
    return Track(
        id=track_id,
        role=role,
        name=track_id.replace("_", " ").title(),
        instrument=sound.instrument,
        effects=list(sound.effects),
        channel=Channel(volume_db=volume_db, pan=pan, mute=False),
        sends=[],
        notes=events,
    )


def _to_event(
    note: PhraseNote,
    is_drum: bool,
    trigger_midi: int | None,
    song_end: int,
) -> NoteEvent | None:
    if note.ticks >= song_end:
        return None
    midi = trigger_midi if (is_drum and trigger_midi is not None) else note.midi
    duration = max(1, note.duration_ticks)
    if note.ticks + duration > song_end:
        duration = song_end - note.ticks
    return NoteEvent(
        ticks=note.ticks,
        duration_ticks=duration,
        midi=midi,
        velocity=note.velocity,
    )


def to_json(doc: TrackDocument) -> str:
    """Serialize a `TrackDocument` to the contract JSON (camelCase, drop None)."""
    return json.dumps(doc.model_dump(by_alias=True, exclude_none=True), indent=2)
