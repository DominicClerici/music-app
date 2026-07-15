"""Tests for the pydantic schema models (PHASE_1 §3, §4 field-level contracts)."""

from typing import Any

import pytest
from pydantic import ValidationError

from trackgen.schema import (
    ArrangementEntry,
    ArrangementPlan,
    Bus,
    Channel,
    ChordEvent,
    ChordSpec,
    EffectPatch,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Header,
    InstrumentPatch,
    Key,
    Master,
    Meta,
    NoteEvent,
    Phrase,
    PhraseNote,
    PlanTimeSignature,
    Register,
    Section,
    SeedSpec,
    Send,
    SongForm,
    StylePackRef,
    SwingSpec,
    Tempo,
    TimeSignature,
    Track,
    TrackDocument,
)

# ---------------------------------------------------------------------------
# Valid minimal instances — document models
# ---------------------------------------------------------------------------


def make_note_event(**overrides: Any) -> NoteEvent:
    fields: dict[str, Any] = {
        "ticks": 0,
        "duration_ticks": 240,
        "midi": 60,
        "velocity": 0.8,
    }
    fields.update(overrides)
    return NoteEvent(**fields)


def make_instrument_patch(**overrides: Any) -> InstrumentPatch:
    fields: dict[str, Any] = {"type": "MonoSynth", "options": {}}
    fields.update(overrides)
    return InstrumentPatch(**fields)


def make_track(**overrides: Any) -> Track:
    fields: dict[str, Any] = {
        "id": "bass",
        "role": "bass",
        "name": "Bass",
        "instrument": make_instrument_patch(),
        "effects": [],
        "channel": Channel(volume_db=0.0, pan=0.0, mute=False),
        "sends": [],
        "notes": [make_note_event()],
    }
    fields.update(overrides)
    return Track(**fields)


def make_track_document() -> TrackDocument:
    return TrackDocument(
        meta=Meta(
            generator_version="0.1.0",
            tone_version="^15.1.0",
            seed="1ps9wxb",
            seed_overrides={},
            params={"styleFamily": "pop_rock"},
            title="Test",
        ),
        header=Header(
            ppq=480,
            tempos=[Tempo(ticks=0, bpm=96)],
            time_signatures=[TimeSignature(ticks=0, numerator=4, denominator=4)],
        ),
        sections=[
            Section(
                type="intro", label="Intro", start_tick=0, end_tick=1920, energy=0.3
            ),
        ],
        buses=[Bus(id="reverb", effects=[EffectPatch(type="Reverb", options={})])],
        master=Master(
            effects=[
                EffectPatch(type="Compressor", options={"threshold": -24, "ratio": 4})
            ]
        ),
        tracks=[
            make_track(
                sends=[Send(bus="reverb", gain_db=-18.0)],
            )
        ],
    )


def test_note_event_valid() -> None:
    note = make_note_event()
    assert note.ticks == 0
    assert note.midi == 60


def test_instrument_patch_valid() -> None:
    patch = make_instrument_patch(
        type="PolySynth", voice="FMSynth", max_polyphony=12, options={"harmonicity": 3}
    )
    assert patch.voice == "FMSynth"
    assert patch.max_polyphony == 12


def test_effect_patch_valid() -> None:
    effect = EffectPatch(type="Reverb", options={"decay": 2.2, "wet": 0.25})
    assert effect.type == "Reverb"


def test_channel_valid() -> None:
    channel = Channel(volume_db=-2.0, pan=0.05, mute=False)
    assert channel.pan == 0.05


def test_send_valid() -> None:
    send = Send(bus="reverb", gain_db=-18.0)
    assert send.bus == "reverb"


def test_bus_valid() -> None:
    bus = Bus(id="reverb", effects=[EffectPatch(type="Reverb", options={})])
    assert bus.id == "reverb"


def test_master_valid() -> None:
    master = Master(effects=[EffectPatch(type="Limiter", options={"threshold": -1})])
    assert len(master.effects) == 1


def test_section_valid() -> None:
    section = Section(
        type="chorus", label="Chorus", start_tick=0, end_tick=7680, energy=0.9
    )
    assert section.type == "chorus"


def test_header_valid() -> None:
    header = Header(
        ppq=480,
        tempos=[Tempo(ticks=0, bpm=96)],
        time_signatures=[TimeSignature(ticks=0, numerator=4, denominator=4)],
    )
    assert header.ppq == 480


def test_meta_valid() -> None:
    meta = Meta(
        generator_version="0.1.0",
        tone_version="^15.1.0",
        seed="1ps9wxb",
        seed_overrides={},
        params={"a": 1},
    )
    assert meta.title is None


def test_track_valid() -> None:
    track = make_track()
    assert track.role == "bass"


def test_track_document_valid() -> None:
    doc = make_track_document()
    assert doc.schema_version == 1
    assert len(doc.tracks) == 1


# ---------------------------------------------------------------------------
# Valid minimal instances — IR models
# ---------------------------------------------------------------------------


def test_generation_plan_valid() -> None:
    plan = GenerationPlan(
        style_pack=StylePackRef(id="pop_rock", version="0.1.0"),
        seed=SeedSpec(master=3735928559, overrides={}),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=96.0,
        time_signature=PlanTimeSignature(numerator=4, denominator=4),
        swing=SwingSpec(ratio=0.6, subdivision="8"),
        max_length_ticks=30720,
        role_flavors={"drums": "default"},
    )
    assert plan.swing is not None
    assert plan.swing.ratio == 0.6


def test_generation_plan_swing_none() -> None:
    plan = GenerationPlan(
        style_pack=StylePackRef(id="pop_rock", version="0.1.0"),
        seed=SeedSpec(master=1, overrides={}),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=96.0,
        time_signature=PlanTimeSignature(numerator=4, denominator=4),
        swing=None,
        max_length_ticks=30720,
        role_flavors={},
    )
    assert plan.swing is None


def test_song_form_valid() -> None:
    form = SongForm(
        sections=[
            FormSection(
                id="intro-1",
                type="intro",
                index=1,
                start_bar=0,
                length_bars=4,
                energy=0.3,
            )
        ],
        total_bars=4,
    )
    assert form.total_bars == 4


def test_harmonic_plan_valid() -> None:
    plan = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=0,
                duration_ticks=1920,
                section_id="intro-1",
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
            )
        ]
    )
    assert plan.chords[0].chord.quality == "maj"


def test_arrangement_plan_valid() -> None:
    plan = ArrangementPlan(
        entries=[
            ArrangementEntry(
                section_id="intro-1",
                role="bass",
                active=True,
                intensity=2,
                density_budget=0.5,
                register=Register(low_midi=36, high_midi=60),
            )
        ]
    )
    assert plan.entries[0].intensity == 2


def test_phrase_valid() -> None:
    phrase = Phrase(
        track_id="bass",
        role="bass",
        start_tick=0,
        end_tick=1920,
        notes=[
            PhraseNote(
                ticks=0, duration_ticks=480, midi=36, velocity=0.8, tags=["accent"]
            )
        ],
    )
    assert phrase.notes[0].tags == ["accent"]


# ---------------------------------------------------------------------------
# Field-level constraint rejections
# ---------------------------------------------------------------------------


def test_velocity_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        make_note_event(velocity=0.0)


def test_velocity_over_one_rejected() -> None:
    with pytest.raises(ValidationError):
        make_note_event(velocity=1.5)


def test_pan_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        Channel(volume_db=0.0, pan=2.0, mute=False)


def test_volume_db_over_six_rejected() -> None:
    with pytest.raises(ValidationError):
        Channel(volume_db=6.1, pan=0.0, mute=False)


def test_duration_ticks_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        make_note_event(duration_ticks=0)


def test_ticks_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        make_note_event(ticks=-1)


def test_bad_instrument_type_enum_rejected() -> None:
    with pytest.raises(ValidationError):
        make_instrument_patch(type="Sampler")


def test_bad_effect_type_enum_rejected() -> None:
    with pytest.raises(ValidationError):
        # Deliberately outside the Literal whitelist; asserting the runtime
        # ValidationError, not the (correct) static rejection.
        EffectPatch(type="Flanger", options={})  # type: ignore[arg-type]


def test_bad_role_enum_rejected() -> None:
    with pytest.raises(ValidationError):
        make_track(role="lead")


def test_midi_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        make_note_event(midi=200)


def test_denominator_invalid_rejected() -> None:
    with pytest.raises(ValidationError):
        TimeSignature(ticks=0, numerator=4, denominator=5)  # type: ignore[arg-type]


def test_bpm_not_positive_rejected() -> None:
    with pytest.raises(ValidationError):
        Tempo(ticks=0, bpm=0)


def test_swing_ratio_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        SwingSpec(ratio=0.4, subdivision="8")


def test_intensity_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        ArrangementEntry(
            section_id="intro-1",
            role="bass",
            active=True,
            intensity=5,
            density_budget=0.5,
            register=Register(low_midi=36, high_midi=60),
        )


def test_energy_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        Section(type="chorus", label="Chorus", start_tick=0, end_tick=7680, energy=1.5)


def test_length_bars_under_four_rejected() -> None:
    with pytest.raises(ValidationError):
        FormSection(
            id="intro-1", type="intro", index=1, start_bar=0, length_bars=3, energy=0.3
        )


def test_density_budget_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        ArrangementEntry(
            section_id="intro-1",
            role="bass",
            active=True,
            intensity=2,
            density_budget=1.5,
            register=Register(low_midi=36, high_midi=60),
        )


def test_pitch_class_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        Key(tonic_pc=12, mode="major")
    with pytest.raises(ValidationError):
        ChordSpec(root_pc=12, quality="maj", symbol="C")
    with pytest.raises(ValidationError):
        ChordSpec(root_pc=0, quality="maj", bass_pc=12, symbol="C")


def test_bad_chord_quality_rejected() -> None:
    with pytest.raises(ValidationError):
        ChordSpec(root_pc=0, quality="power", symbol="C5")  # type: ignore[arg-type]


def test_bad_polysynth_voice_rejected() -> None:
    with pytest.raises(ValidationError):
        make_instrument_patch(type="PolySynth", voice="NoiseSynth", max_polyphony=8)


# ---------------------------------------------------------------------------
# Frozen models
# ---------------------------------------------------------------------------


def test_note_event_frozen() -> None:
    note = make_note_event()
    with pytest.raises(ValidationError):
        note.ticks = 100


def test_track_document_frozen() -> None:
    doc = make_track_document()
    with pytest.raises(ValidationError):
        doc.schema_version = 2


def test_generation_plan_frozen() -> None:
    plan = GenerationPlan(
        style_pack=StylePackRef(id="pop_rock", version="0.1.0"),
        seed=SeedSpec(master=1, overrides={}),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=96.0,
        time_signature=PlanTimeSignature(numerator=4, denominator=4),
        swing=None,
        max_length_ticks=30720,
        role_flavors={},
    )
    with pytest.raises(ValidationError):
        plan.tempo_bpm = 100.0


# ---------------------------------------------------------------------------
# camelCase JSON serialization contract (§3.9)
# ---------------------------------------------------------------------------


def test_track_document_serializes_camel_case() -> None:
    doc = make_track_document()
    dumped = doc.model_dump(by_alias=True)

    assert dumped["schemaVersion"] == 1
    assert set(dumped["meta"].keys()) >= {
        "generatorVersion",
        "toneVersion",
        "seed",
        "seedOverrides",
        "params",
        "title",
    }
    assert set(dumped["header"].keys()) == {"ppq", "tempos", "timeSignatures"}
    assert set(dumped["sections"][0].keys()) == {
        "type",
        "label",
        "startTick",
        "endTick",
        "energy",
    }
    track = dumped["tracks"][0]
    assert "instrument" in track and "channel" in track
    assert set(track["channel"].keys()) == {"volumeDb", "pan", "mute"}
    assert set(track["sends"][0].keys()) == {"bus", "gainDb"}


def test_note_event_serializes_duration_ticks() -> None:
    note = make_note_event()
    dumped = note.model_dump(by_alias=True)
    assert "durationTicks" in dumped
    assert dumped["durationTicks"] == 240


def test_instrument_patch_max_polyphony_camel_case() -> None:
    patch = make_instrument_patch(
        type="PolySynth", voice="FMSynth", max_polyphony=12, options={}
    )
    dumped = patch.model_dump(by_alias=True)
    assert dumped["maxPolyphony"] == 12


def test_round_trip_by_alias_and_by_name() -> None:
    doc = make_track_document()
    by_alias = doc.model_dump(by_alias=True)
    reconstructed = TrackDocument.model_validate(by_alias)
    assert reconstructed == doc
