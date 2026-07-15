"""Tests for the document validator (PHASE_1 §3.8, rules V1-V8) and the
committed JSON Schema export drift guard."""

from typing import Any, Literal

from trackgen.schema import (
    Bus,
    Channel,
    EffectPatch,
    Header,
    InstrumentPatch,
    Master,
    Meta,
    NoteEvent,
    Section,
    Send,
    Tempo,
    TimeSignature,
    Track,
    TrackDocument,
)
from trackgen.schema.export import DEFAULT_SCHEMA_PATH, schema_json
from trackgen.schema.validate import validate_document

# ---------------------------------------------------------------------------
# Builders for a small, valid document (does not depend on the Task 5 fixture)
# ---------------------------------------------------------------------------

PPQ: Literal[480] = 480
BAR = PPQ * 4  # 4/4 at PPQ 480

# 4 bars: intro / verse / chorus / outro
INTRO_END = BAR * 4
VERSE_END = INTRO_END + BAR * 4
CHORUS_END = VERSE_END + BAR * 4
SONG_END = CHORUS_END + BAR * 4


def make_note_event(**overrides: Any) -> NoteEvent:
    fields: dict[str, Any] = {
        "ticks": 0,
        "duration_ticks": 240,
        "midi": 60,
        "velocity": 0.8,
    }
    fields.update(overrides)
    return NoteEvent(**fields)


def make_sections() -> list[Section]:
    return [
        Section(
            type="intro", label="Intro", start_tick=0, end_tick=INTRO_END, energy=0.3
        ),
        Section(
            type="verse",
            label="Verse",
            start_tick=INTRO_END,
            end_tick=VERSE_END,
            energy=0.5,
        ),
        Section(
            type="chorus",
            label="Chorus",
            start_tick=VERSE_END,
            end_tick=CHORUS_END,
            energy=0.9,
        ),
        Section(
            type="outro",
            label="Outro",
            start_tick=CHORUS_END,
            end_tick=SONG_END,
            energy=0.35,
        ),
    ]


def make_bass_track(**overrides: Any) -> Track:
    fields: dict[str, Any] = {
        "id": "bass",
        "role": "bass",
        "name": "Bass",
        "instrument": InstrumentPatch(type="MonoSynth", options={}),
        "effects": [],
        "channel": Channel(volume_db=0.0, pan=0.0, mute=False),
        "sends": [],
        "notes": [
            make_note_event(ticks=0, midi=36),
            make_note_event(ticks=480, midi=43),
        ],
    }
    fields.update(overrides)
    return Track(**fields)


def make_snare_track(**overrides: Any) -> Track:
    fields: dict[str, Any] = {
        "id": "snare",
        "role": "drums",
        "name": "Snare",
        "instrument": InstrumentPatch(type="NoiseSynth", options={}),
        "effects": [],
        "channel": Channel(volume_db=-6.0, pan=0.0, mute=False),
        "sends": [Send(bus="reverb", gain_db=-18.0)],
        "notes": [
            NoteEvent(ticks=480, duration_ticks=120, midi=None, velocity=0.8),
            NoteEvent(ticks=1440, duration_ticks=120, midi=None, velocity=0.8),
        ],
    }
    fields.update(overrides)
    return Track(**fields)


def make_comping_track(**overrides: Any) -> Track:
    fields: dict[str, Any] = {
        "id": "comping",
        "role": "comping",
        "name": "Comping",
        "instrument": InstrumentPatch(
            type="PolySynth", voice="FMSynth", max_polyphony=8, options={}
        ),
        "effects": [],
        "channel": Channel(volume_db=-3.0, pan=0.0, mute=False),
        "sends": [],
        "notes": [make_note_event(ticks=0, midi=60)],
    }
    fields.update(overrides)
    return Track(**fields)


def make_document(**overrides: Any) -> TrackDocument:
    fields: dict[str, Any] = {
        "meta": Meta(
            generator_version="0.1.0",
            tone_version="^15.1.0",
            seed="1ps9wxb",
            seed_overrides={},
            params={"styleFamily": "pop_rock"},
            title="Test",
        ),
        "header": Header(
            ppq=PPQ,
            tempos=[Tempo(ticks=0, bpm=96), Tempo(ticks=VERSE_END, bpm=112)],
            time_signatures=[TimeSignature(ticks=0, numerator=4, denominator=4)],
        ),
        "sections": make_sections(),
        "buses": [Bus(id="reverb", effects=[EffectPatch(type="Reverb", options={})])],
        "master": Master(
            effects=[
                EffectPatch(type="Compressor", options={"threshold": -24, "ratio": 4})
            ]
        ),
        "tracks": [make_bass_track(), make_snare_track(), make_comping_track()],
    }
    fields.update(overrides)
    return TrackDocument(**fields)


# ---------------------------------------------------------------------------
# Valid document: zero violations
# ---------------------------------------------------------------------------


def test_valid_document_has_no_violations() -> None:
    doc = make_document()
    assert validate_document(doc) == []


# ---------------------------------------------------------------------------
# V1 - header sorting
# ---------------------------------------------------------------------------


def test_v1_unsorted_tempos_reported() -> None:
    doc = make_document(
        header=Header(
            ppq=PPQ,
            tempos=[Tempo(ticks=1000, bpm=96), Tempo(ticks=0, bpm=112)],
            time_signatures=[TimeSignature(ticks=0, numerator=4, denominator=4)],
        )
    )
    violations = validate_document(doc)
    assert any(v.startswith("V1:") for v in violations)


def test_v1_tempos_not_starting_at_zero_reported() -> None:
    doc = make_document(
        header=Header(
            ppq=PPQ,
            tempos=[Tempo(ticks=10, bpm=96)],
            time_signatures=[TimeSignature(ticks=0, numerator=4, denominator=4)],
        )
    )
    violations = validate_document(doc)
    assert any(v.startswith("V1:") for v in violations)


# ---------------------------------------------------------------------------
# V2 - section contiguity
# ---------------------------------------------------------------------------


def test_v2_non_contiguous_sections_reported() -> None:
    sections = make_sections()
    # Introduce a gap between verse and chorus.
    sections[2] = sections[2].model_copy(
        update={"start_tick": sections[2].start_tick + 10}
    )
    doc = make_document(sections=sections)
    violations = validate_document(doc)
    assert any(v.startswith("V2:") for v in violations)


def test_v2_first_section_not_at_zero_reported() -> None:
    sections = make_sections()
    # Shift the whole song so the first section no longer starts at tick 0.
    sections[0] = sections[0].model_copy(update={"start_tick": 10})
    doc = make_document(sections=sections)
    violations = validate_document(doc)
    assert any(
        v.startswith("V2:") and "contiguous from tick 0" in v for v in violations
    )


def test_v2_valid_sections_pass() -> None:
    doc = make_document()
    violations = validate_document(doc)
    assert not any(v.startswith("V2:") for v in violations)


# ---------------------------------------------------------------------------
# V3 - note ordering / duration / velocity
# ---------------------------------------------------------------------------


def test_v3_unsorted_notes_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(
                notes=[
                    make_note_event(ticks=480, midi=36),
                    make_note_event(ticks=0, midi=43),
                ]
            ),
            make_snare_track(),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(
        v.startswith("V3:") and "not sorted by (ticks, midi)" in v for v in violations
    )


def test_v3_duplicate_unpitched_ticks_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(),
            make_snare_track(
                notes=[
                    NoteEvent(ticks=480, duration_ticks=120, midi=None, velocity=0.8),
                    NoteEvent(ticks=480, duration_ticks=120, midi=None, velocity=0.7),
                ]
            ),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V3:") and "duplicate ticks" in v for v in violations)


def test_v3_valid_notes_pass() -> None:
    doc = make_document()
    violations = validate_document(doc)
    assert not any(v.startswith("V3:") for v in violations)


# ---------------------------------------------------------------------------
# V4 - register ceiling
# ---------------------------------------------------------------------------


def test_v4_register_violation_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(notes=[make_note_event(ticks=0, midi=72)]),
            make_snare_track(),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V4:") for v in violations)


def test_v4_drums_exempt_from_register() -> None:
    # Drum tracks may exceed midi 71 (synthesis trigger params, not pitch).
    doc = make_document(
        tracks=[
            make_bass_track(),
            make_snare_track(),
            Track(
                id="hats",
                role="drums",
                name="Hats",
                instrument=InstrumentPatch(type="MetalSynth", options={}),
                effects=[],
                channel=Channel(volume_db=-8.0, pan=0.0, mute=False),
                sends=[],
                notes=[make_note_event(ticks=0, midi=91)],
            ),
        ]
    )
    violations = validate_document(doc)
    assert not any(v.startswith("V4:") for v in violations)


# ---------------------------------------------------------------------------
# V5 - midi presence conditional on NoiseSynth
# ---------------------------------------------------------------------------


def test_v5_missing_midi_on_pitched_track_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(
                notes=[NoteEvent(ticks=0, duration_ticks=240, midi=None, velocity=0.8)]
            ),
            make_snare_track(),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V5:") and "missing required midi" in v for v in violations)


def test_v5_extra_midi_on_noisesynth_track_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(),
            make_snare_track(
                notes=[NoteEvent(ticks=480, duration_ticks=120, midi=60, velocity=0.8)]
            ),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V5:") and "has midi set" in v for v in violations)


# ---------------------------------------------------------------------------
# V6 - bus references, track/bus id uniqueness
# ---------------------------------------------------------------------------


def test_v6_dangling_send_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(sends=[Send(bus="delay", gain_db=-12.0)]),
            make_snare_track(),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V6:") and "undeclared bus" in v for v in violations)


def test_v6_duplicate_track_ids_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(id="dup"),
            make_snare_track(id="dup"),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V6:") and "track ids not unique" in v for v in violations)


def test_v6_duplicate_bus_ids_reported() -> None:
    doc = make_document(
        buses=[
            Bus(id="reverb", effects=[EffectPatch(type="Reverb", options={})]),
            Bus(id="reverb", effects=[EffectPatch(type="Chorus", options={})]),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V6:") and "bus ids not unique" in v for v in violations)


# ---------------------------------------------------------------------------
# V7 - PolySynth voice/maxPolyphony rules
# ---------------------------------------------------------------------------


def test_v7_polysynth_missing_voice_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(),
            make_snare_track(),
            make_comping_track(
                instrument=InstrumentPatch(
                    type="PolySynth", options={}, max_polyphony=8
                )
            ),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V7:") and "missing a valid" in v for v in violations)


def test_v7_polysynth_missing_max_polyphony_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(),
            make_snare_track(),
            make_comping_track(
                instrument=InstrumentPatch(
                    type="PolySynth", options={}, voice="FMSynth"
                )
            ),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V7:") and "missing maxPolyphony" in v for v in violations)


def test_v7_non_polysynth_with_voice_and_max_polyphony_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(
                instrument=InstrumentPatch(
                    type="MonoSynth", options={}, voice="FMSynth", max_polyphony=8
                )
            ),
            make_snare_track(),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V7:") and "must not set voice" in v for v in violations)
    assert any(
        v.startswith("V7:") and "must not set maxPolyphony" in v for v in violations
    )


def test_v7_valid_polysynth_passes() -> None:
    doc = make_document()
    violations = validate_document(doc)
    assert not any(v.startswith("V7:") for v in violations)


# ---------------------------------------------------------------------------
# V8 - notes must end within the final section's endTick
# ---------------------------------------------------------------------------


def test_v8_note_overrunning_song_end_reported() -> None:
    doc = make_document(
        tracks=[
            make_bass_track(
                notes=[
                    make_note_event(ticks=SONG_END - 10, duration_ticks=100, midi=36),
                ]
            ),
            make_snare_track(),
            make_comping_track(),
        ]
    )
    violations = validate_document(doc)
    assert any(v.startswith("V8:") for v in violations)


def test_v8_note_within_song_end_passes() -> None:
    doc = make_document()
    violations = validate_document(doc)
    assert not any(v.startswith("V8:") for v in violations)


# ---------------------------------------------------------------------------
# Schema export drift guard
# ---------------------------------------------------------------------------


def test_schema_export_matches_committed_artifact() -> None:
    committed = DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")
    assert schema_json() == committed
