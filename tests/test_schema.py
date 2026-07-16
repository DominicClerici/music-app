"""Tests for the pydantic schema models (PHASE_1 §3, §4 field-level contracts)."""

from typing import Any

import pytest
from pydantic import ValidationError

from trackgen.schema import (
    ArrangementEntry,
    ArrangementPlan,
    Budgets,
    Bus,
    Channel,
    ChordEvent,
    ChordSpec,
    EffectPatch,
    EventScale,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Header,
    InstrumentPatch,
    Key,
    KeyRegion,
    Master,
    Meta,
    MoodVector,
    NoteEvent,
    Phrase,
    PhraseNote,
    PlanTimeSignature,
    Register,
    Section,
    SectionEnding,
    SectionPhrase,
    SeedSpec,
    Send,
    SongForm,
    StylePackRef,
    SwingSpec,
    Tempo,
    TimbreDirectives,
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


def make_budgets(**overrides: Any) -> Budgets:
    fields: dict[str, Any] = {
        "note_density": 0.5,
        "dissonance": 0.3,
        "dynamics_base": 0.5,
        "dynamics_range": 0.2,
        "articulation_legato": 0.5,
        "layers_max": 3,
        "harmonic_rhythm_base": 1.0,
        "register_bias": 0.0,
    }
    fields.update(overrides)
    return Budgets(**fields)


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
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=make_budgets(),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
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
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=make_budgets(),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
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
                total_of_type=1,
                phrases=[SectionPhrase(label="a", bars=4)],
                harmony_tag="intro",
            )
        ],
        total_bars=4,
        template_id="verse_chorus_bridge",
    )
    assert form.total_bars == 4


def test_song_form_phase3_extension_fields() -> None:
    """PHASE_3 §4.4 — the worked `solo-2` fragment round-trips through
    FormSection/SongForm.
    """
    section = FormSection(
        id="solo-2",
        type="solo",
        index=2,
        start_bar=24,
        length_bars=12,
        energy=0.704,  # normative — do not edit to match code
        total_of_type=3,
        phrases=[
            SectionPhrase(label="a", bars=4),
            SectionPhrase(label="b", bars=4),
            SectionPhrase(label="c", bars=4),
        ],
        harmony_tag="blues_12",
        variant=None,
        ending=None,
    )
    form = SongForm(sections=[section], total_bars=64, template_id="head_solos_head")

    assert form.template_id == "head_solos_head"
    assert form.sections[0].id == "solo-2"
    assert form.sections[0].total_of_type == 3
    assert [p.bars for p in form.sections[0].phrases] == [4, 4, 4]
    assert form.sections[0].harmony_tag == "blues_12"
    assert form.sections[0].variant is None
    assert form.sections[0].ending is None


def test_section_ending_valid_round_trip() -> None:
    """PHASE_3 §4 — a valid `SectionEnding` attaches to a `FormSection` and
    round-trips through field access unchanged.
    """
    ending = SectionEnding(tag_bars=4, close="ritard")
    section = FormSection(
        id="outro-1",
        type="outro",
        index=1,
        start_bar=60,
        length_bars=4,
        energy=0.344,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=4)],
        harmony_tag="outro",
        ending=ending,
    )
    assert section.ending is not None
    assert section.ending.tag_bars == 4
    assert section.ending.close == "ritard"


def test_section_phrase_bars_sum_not_enforced() -> None:
    """PHASE_3 §4.1 — Σ phrases[].bars == length_bars is a stage/property-test
    invariant, not a schema constraint; the model must accept a partial fixture.
    """
    section = FormSection(
        id="verse-1",
        type="verse",
        index=1,
        start_bar=0,
        length_bars=8,
        energy=0.5,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=4)],  # sums to 4, not 8
        harmony_tag="verse",
    )
    assert section.length_bars == 8
    assert sum(p.bars for p in section.phrases) == 4


def test_section_ending_bad_tag_bars_rejected() -> None:
    """PHASE_3 §4.1 — `tagBars` is restricted to {0, 4, 8}."""
    with pytest.raises(ValidationError):
        SectionEnding(tag_bars=6, close="cold")  # type: ignore[arg-type]


def test_section_ending_bad_close_rejected() -> None:
    """PHASE_3 §4.1 — `close` is restricted to {ritard, cold, fade}."""
    with pytest.raises(ValidationError):
        SectionEnding(tag_bars=4, close="wrong")  # type: ignore[arg-type]


def test_form_section_total_of_type_zero_rejected() -> None:
    """PHASE_3 §4.1 — `totalOfType` must be >= 1."""
    with pytest.raises(ValidationError):
        FormSection(
            id="intro-1",
            type="intro",
            index=1,
            start_bar=0,
            length_bars=4,
            energy=0.3,
            total_of_type=0,
            phrases=[SectionPhrase(label="a", bars=4)],
            harmony_tag="intro",
        )


def test_harmonic_plan_valid() -> None:
    plan = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=0,
                duration_ticks=1920,
                section_id="intro-1",
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
                scale=EventScale(root_pc=0, name="ionian"),
                function="T",
            )
        ],
        keys=[KeyRegion(start_tick=0, tonic_pc=0, mode="major")],
    )
    assert plan.chords[0].chord.quality == "maj"


def test_harmonic_plan_phase4_extension_defaults() -> None:
    """PHASE_4 §7 — a plan built without `tags`/`pool_selections` fires their
    defaults; the required `scale`/`function`/`keys` round-trip.
    """
    plan = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=0,
                duration_ticks=1920,
                section_id="verse-1",
                chord=ChordSpec(root_pc=4, quality="maj", symbol="E"),
                scale=EventScale(root_pc=4, name="ionian"),
                function="T",
            )
        ],
        keys=[KeyRegion(start_tick=0, tonic_pc=4, mode="major")],
    )
    event = plan.chords[0]
    assert event.tags == []
    assert plan.pool_selections == {}
    assert event.scale.name == "ionian"
    assert event.function == "T"
    assert plan.keys[0].tonic_pc == 4
    assert plan.keys[0].mode == "major"


def test_harmonic_plan_phase4_extension_explicit_round_trip() -> None:
    """PHASE_4 §7 — explicit `tags` and `pool_selections` round-trip unchanged."""
    plan = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=0,
                duration_ticks=1920,
                section_id="chorus-1",
                chord=ChordSpec(root_pc=7, quality="dom7", symbol="G7"),
                scale=EventScale(root_pc=7, name="mixolydian"),
                function="D",
                tags=["final"],
            )
        ],
        keys=[KeyRegion(start_tick=0, tonic_pc=0, mode="major")],
        pool_selections={"chorus": "axis"},
    )
    assert plan.chords[0].tags == ["final"]
    assert plan.pool_selections == {"chorus": "axis"}


def test_key_region_frozen() -> None:
    """PHASE_4 §7.1 — `KeyRegion` is a frozen IR model."""
    region = KeyRegion(start_tick=0, tonic_pc=4, mode="major")
    with pytest.raises(ValidationError):
        region.tonic_pc = 5


def test_event_scale_frozen() -> None:
    """PHASE_4 §7.2 — `EventScale` is a frozen IR model."""
    scale = EventScale(root_pc=0, name="ionian")
    with pytest.raises(ValidationError):
        scale.name = "dorian"


def test_key_region_tonic_pc_out_of_range_rejected() -> None:
    """PHASE_4 §7.1 — `tonic_pc` is bounded to 0–11."""
    with pytest.raises(ValidationError):
        KeyRegion(start_tick=0, tonic_pc=12, mode="major")


def test_key_region_start_tick_negative_rejected() -> None:
    """PHASE_4 §7.1 — `start_tick` must be >= 0."""
    with pytest.raises(ValidationError):
        KeyRegion(start_tick=-1, tonic_pc=0, mode="major")


def test_event_scale_root_pc_out_of_range_rejected() -> None:
    """PHASE_4 §7.2 — `root_pc` is bounded to 0–11."""
    with pytest.raises(ValidationError):
        EventScale(root_pc=-1, name="ionian")


def test_chord_event_bad_function_rejected() -> None:
    """PHASE_4 §7.2 — `function` is restricted to {T, S, D, O}."""
    with pytest.raises(ValidationError):
        ChordEvent(
            start_tick=0,
            duration_ticks=1920,
            section_id="verse-1",
            chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
            scale=EventScale(root_pc=0, name="ionian"),
            function="X",  # type: ignore[arg-type]
        )


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
            id="intro-1",
            type="intro",
            index=1,
            start_bar=0,
            length_bars=3,
            energy=0.3,
            total_of_type=1,
            phrases=[SectionPhrase(label="a", bars=3)],
            harmony_tag="intro",
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
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=make_budgets(),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )
    with pytest.raises(ValidationError):
        plan.tempo_bpm = 100.0


def test_generation_plan_phase2_fields() -> None:
    plan = GenerationPlan(
        style_pack=StylePackRef(id="pop_rock", version="0.1.0"),
        seed=SeedSpec(master=1, overrides={}),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=96.0,
        time_signature=PlanTimeSignature(numerator=4, denominator=4),
        swing=None,
        max_length_ticks=30720,
        role_flavors={},
        mood_vector=MoodVector(valence=0.75, arousal=0.4),
        budgets=Budgets(
            note_density=0.648,
            dissonance=0.132,
            dynamics_base=0.65,
            dynamics_range=0.21,
            articulation_legato=0.34,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.188,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.835, attack_hardness=0.66, space=0.36
        ),
    )
    assert plan.mood_vector.valence == 0.75
    assert plan.budgets.layers_max == 4
    assert plan.timbre_directives.space == 0.36

    with pytest.raises(ValidationError):
        MoodVector(valence=-2, arousal=0.0)

    with pytest.raises(ValidationError):
        make_budgets(layers_max=5)

    with pytest.raises(ValidationError):
        TimbreDirectives(brightness=1.2, attack_hardness=0.5, space=0.5)


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
