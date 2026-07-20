"""The thin Serializer (PHASE_5 §8.3, D-C; PHASE_7 §7).

`serialize(plan, form, phrases, design)` assembles the `TrackDocument` from the
generated `Phrase`s, the `SongForm`, and the sound-design stage's `SoundDesign`.
It is a pure function: no I/O, no draws, no wall-clock. The output passes every
PHASE_1 §3.8 validator rule (V1-V8).

Each emitted track takes its instrument/effects/channel/sends verbatim from the
stage's per-track `TrackSound`; the document `buses`/`master` come from the same
`SoundDesign`. The reverb bus is included only when >= 1 emitted track sends to
it (§7 omission rule).
"""

import json

from trackgen.form.stage import section_label
from trackgen.parts.generators import _TRACK_ORDER
from trackgen.schema.document import (
    Header,
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
from trackgen.sound.stage import SoundDesign

_TICKS_PER_BAR = 1920

# Track emit order: the drum sub-order, then the pitched roles.
_EMIT_ORDER: tuple[str, ...] = (*_TRACK_ORDER, "bass", "comping", "pads")

_GENERATOR_VERSION = "0.1.2"
_TONE_VERSION = "^15.1.0"


def serialize(
    plan: GenerationPlan,
    form: SongForm,
    phrases: list[Phrase],
    design: SoundDesign,
    *,
    tempo_events: list[Tempo] | None = None,
    params: dict[str, object] | None = None,
) -> TrackDocument:
    """Assemble a `TrackDocument` from generated phrases (PHASE_5 §8.3, D-C).

    `tempo_events` are the stage-7 ritard tempo events (empty for a cold close).
    """
    sections = _build_sections(form)
    song_end = sections[-1].end_tick

    grouped = _group_by_track(phrases)
    tracks = [
        track
        for track_id in _EMIT_ORDER
        if track_id in grouped
        for track in (_build_track(track_id, grouped[track_id], design, song_end),)
        if track is not None
    ]

    # §7 bus-omission rule: keep only buses at least one emitted track sends to.
    sent_buses = {send.bus for track in tracks for send in track.sends}
    buses = [bus for bus in design.buses if bus.id in sent_buses]

    meta = Meta(
        generator_version=_GENERATOR_VERSION,
        tone_version=_TONE_VERSION,
        seed=to_base36(plan.seed.master),
        seed_overrides={k: to_base36(v) for k, v in plan.seed.overrides.items()},
        params=params if params is not None else {},
    )
    header = Header(
        ppq=480,
        # V1-safe: the ritard events are absolute-tick ascending and the base sits
        # at tick 0, so appending after it keeps the list sorted with the first
        # tempo at tick 0.
        tempos=[Tempo(ticks=0, bpm=plan.tempo_bpm), *(tempo_events or [])],
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
        buses=buses,
        master=design.master,
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
    design: SoundDesign,
    song_end: int,
) -> Track | None:
    role: Role = track_phrases[0].role
    is_drum = role == "drums"
    sound = design.track_sounds[track_id]
    trigger_midi = sound.midi if is_drum else None

    events: list[NoteEvent] = []
    for phrase in sorted(track_phrases, key=lambda p: p.start_tick):
        for note in phrase.notes:
            event = _to_event(note, is_drum, trigger_midi, song_end)
            if event is not None:
                events.append(event)

    if not events:
        return None

    events.sort(key=lambda e: (e.ticks, e.midi if e.midi is not None else -1))

    return Track(
        id=track_id,
        role=role,
        name=track_id.replace("_", " ").title(),
        instrument=sound.instrument,
        effects=list(sound.effects),
        channel=sound.channel,
        sends=list(sound.sends),
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
