"""Serializer unit tests (PHASE_5 §8.3, D-C — SESSION_09 T2).

Drives the real pipeline for both worked examples (pop_rock/happy,
jazz/melancholic at seed `1ps9wxb`) to prove `validate_document == []`, and uses
targeted synthetic phrase sets (built on the real plan/form so the surrounding
document is valid) to exercise the V-rule edges D-C is responsible for.
"""

from __future__ import annotations

import pytest

from trackgen.arrangement import arrange
from trackgen.form.stage import form as build_form
from trackgen.form.stage import section_label
from trackgen.harmony.stage import harmony
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.generators import generate
from trackgen.parts.selection import select_patterns
from trackgen.pipeline.serialize import _EMIT_ORDER, serialize
from trackgen.schema.document import Role, Tempo, TrackDocument
from trackgen.schema.ir import (
    GenerationPlan,
    Phrase,
    PhraseNote,
    SongForm,
)
from trackgen.schema.validate import validate_document
from trackgen.seeds import Rng, stream_rng, to_base36
from trackgen.sound.stage import SoundDesign, sound_design


def _design(plan: GenerationPlan, pack: StylePack) -> SoundDesign:
    """The sound-design stage output for the pack (the reserved `sound` stream is
    never drawn, so any Rng is fine)."""
    assert pack.timbres is not None
    return sound_design(plan, pack.timbres, Rng(0))


_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")
_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


def _drive(
    params: dict[str, object],
) -> tuple[GenerationPlan, StylePack, SongForm, list[Phrase]]:
    """Replicate `_drive_full` from test_generator_goldens.py:62-93."""
    plan = generate_plan(params)
    pack = resolve_pack(params["styleFamily"])  # type: ignore[arg-type]
    assert pack is not None and pack.forms is not None and pack.progressions is not None
    sf = build_form(plan, pack.forms)
    hp = harmony(
        plan,
        sf,
        pack.progressions,
        stream_rng(plan.seed.master, plan.seed.overrides, "harmony"),
    )
    ap = arrange(plan, sf, pack, Rng(0))
    sel = select_patterns(plan, sf, ap, pack, plan.seed.master, plan.seed.overrides)
    phrases: list[Phrase] = []
    for role in _ROLES:
        phrases += generate(
            role,
            ap,
            hp,
            sf,
            plan,
            pack,
            sel,
            master=plan.seed.master,
            overrides=plan.seed.overrides,
        )
    return plan, pack, sf, phrases


def _build_doc(
    params: dict[str, object],
) -> tuple[TrackDocument, SongForm, list[Phrase]]:
    plan, pack, sf, phrases = _drive(params)
    design = _design(plan, pack)
    doc = serialize(plan, sf, phrases, design, params=params)
    return doc, sf, phrases


@pytest.fixture(scope="module")
def pop() -> tuple[TrackDocument, SongForm, list[Phrase]]:
    return _build_doc(_POP)


@pytest.fixture(scope="module")
def jazz() -> tuple[TrackDocument, SongForm, list[Phrase]]:
    return _build_doc(_JAZZ)


# --- Full-pipeline validity (DoD 8) -----------------------------------------


def test_pop_doc_is_valid(pop: tuple[TrackDocument, SongForm, list[Phrase]]) -> None:
    doc, _, _ = pop
    assert validate_document(doc) == []


def test_jazz_doc_is_valid(jazz: tuple[TrackDocument, SongForm, list[Phrase]]) -> None:
    doc, _, _ = jazz
    assert validate_document(doc) == []


# --- V5: drum trigger injection / snare stays None --------------------------


def test_v5_snare_none_others_carry_trigger(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, _, _ = pop
    by_id = {t.id: t for t in doc.tracks}
    assert all(n.midi is None for n in by_id["snare"].notes)
    assert by_id["snare"].notes, "snare should have hits in the pop example"
    for track_id, trigger in (("kick", 24), ("hats", 80), ("ride", 82)):
        if track_id in by_id and by_id[track_id].notes:
            assert all(n.midi == trigger for n in by_id[track_id].notes)


# --- V4: no non-drum note above the register ceiling ------------------------


def test_v4_no_pitched_note_above_71(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
    jazz: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    for doc, _, _ in (pop, jazz):
        for track in doc.tracks:
            if track.role == "drums":
                continue
            assert all(n.midi is not None and n.midi <= 71 for n in track.notes)


# --- V8: truncation to song end + duration clamp ----------------------------


def test_v8_truncation_and_duration_clamp(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    plan, pack, sf, _ = _drive(_POP)
    design = _design(plan, pack)
    song_end = (sf.sections[-1].start_bar + sf.sections[-1].length_bars) * 1920

    phrases = [
        Phrase(
            track_id="kick",
            role="drums",
            start_tick=0,
            end_tick=song_end,
            notes=[
                PhraseNote(ticks=0, duration_ticks=1000, midi=None, velocity=0.9),
                PhraseNote(
                    ticks=song_end - 10, duration_ticks=500, midi=None, velocity=0.9
                ),
            ],
        )
    ]
    doc = serialize(plan, sf, phrases, design, params=_POP)
    assert validate_document(doc) == []
    kick = next(t for t in doc.tracks if t.id == "kick")
    last = kick.notes[-1]
    assert last.ticks == song_end - 10
    assert last.ticks + last.duration_ticks == song_end
    assert all(n.duration_ticks >= 1 for n in kick.notes)


def test_v8_note_at_song_end_is_dropped() -> None:
    plan, pack, sf, _ = _drive(_POP)
    design = _design(plan, pack)
    song_end = (sf.sections[-1].start_bar + sf.sections[-1].length_bars) * 1920
    phrases = [
        Phrase(
            track_id="kick",
            role="drums",
            start_tick=0,
            end_tick=song_end,
            notes=[
                PhraseNote(ticks=0, duration_ticks=100, midi=None, velocity=0.9),
                PhraseNote(ticks=song_end, duration_ticks=100, midi=None, velocity=0.9),
            ],
        )
    ]
    doc = serialize(plan, sf, phrases, design, params=_POP)
    kick = next(t for t in doc.tracks if t.id == "kick")
    assert len(kick.notes) == 1
    assert kick.notes[0].ticks == 0


# --- Sections: contiguous, 1:1 with the form, correct labels ----------------


def test_sections_mirror_form(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, sf, _ = pop
    assert len(doc.sections) == len(sf.sections)
    assert doc.sections[0].start_tick == 0
    for prev, nxt in zip(doc.sections, doc.sections[1:], strict=False):
        assert prev.end_tick == nxt.start_tick
    for section, fs in zip(doc.sections, sf.sections, strict=True):
        assert section.type == fs.type
        assert section.label == section_label(
            fs.type, fs.index, fs.total_of_type, fs.variant
        )
        assert section.start_tick == fs.start_bar * 1920
        assert section.end_tick == (fs.start_bar + fs.length_bars) * 1920
        assert section.energy == fs.energy


# --- Header: single base tempo + single time signature ----------------------


def test_header_single_tempo_and_time_signature(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, _, _ = pop
    plan = generate_plan(_POP)
    assert doc.header.ppq == 480
    assert len(doc.header.tempos) == 1
    assert doc.header.tempos[0].ticks == 0
    assert doc.header.tempos[0].bpm == plan.tempo_bpm
    assert len(doc.header.time_signatures) == 1
    assert doc.header.time_signatures[0].ticks == 0
    assert doc.header.time_signatures[0].numerator == plan.time_signature.numerator
    assert doc.header.time_signatures[0].denominator == plan.time_signature.denominator


# --- V1: ritard tempo events thread after the tick-0 base -------------------


def test_tempo_events_thread_after_base_and_stay_valid() -> None:
    """A non-empty `tempo_events` list appends after the tick-0 base in order,
    and the document still passes V1 (first tempo at tick 0, ascending ticks)."""
    plan, pack, sf, phrases = _drive(_POP)
    design = _design(plan, pack)
    events = [
        Tempo(ticks=1000, bpm=118.0),
        Tempo(ticks=2000, bpm=110.0),
        Tempo(ticks=3000, bpm=100.0),
    ]
    doc = serialize(plan, sf, phrases, design, tempo_events=events, params=_POP)
    assert validate_document(doc) == []
    assert doc.header.tempos[0] == Tempo(ticks=0, bpm=plan.tempo_bpm)
    assert doc.header.tempos[1:] == events


@pytest.mark.parametrize("events", [None, []], ids=["none", "empty"])
def test_no_tempo_events_yields_single_base(events: list[Tempo] | None) -> None:
    """`tempo_events=None`/`[]` (a cold close) yields exactly the base tempo."""
    plan, pack, sf, phrases = _drive(_POP)
    design = _design(plan, pack)
    doc = serialize(plan, sf, phrases, design, tempo_events=events, params=_POP)
    assert doc.header.tempos == [Tempo(ticks=0, bpm=plan.tempo_bpm)]


# --- Crash: stage-6 crash track serializes with trigger midi 84 -------------


def test_crash_track_serializes_with_trigger_midi() -> None:
    """A phrase set containing a `crash` drum track serializes a crash `Track`
    carrying its kit trigger midi 84 and the sound-design stage's crash mix."""
    plan, pack, sf, _ = _drive(_POP)
    design = _design(plan, pack)
    song_end = (sf.sections[-1].start_bar + sf.sections[-1].length_bars) * 1920
    phrases = [
        Phrase(
            track_id="crash",
            role="drums",
            start_tick=0,
            end_tick=song_end,
            notes=[
                PhraseNote(ticks=0, duration_ticks=1440, midi=None, velocity=0.95),
            ],
        )
    ]
    doc = serialize(plan, sf, phrases, design, params=_POP)
    assert validate_document(doc) == []
    crash = next(t for t in doc.tracks if t.id == "crash")
    assert crash.role == "drums"
    assert [n.midi for n in crash.notes] == [84]
    assert crash.channel == design.track_sounds["crash"].channel


# --- Meta: seed / overrides / params echo -----------------------------------


def test_meta_seed_and_params(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, _, _ = pop
    plan = generate_plan(_POP)
    assert doc.meta.seed == to_base36(plan.seed.master)
    assert doc.meta.seed_overrides == {
        k: to_base36(v) for k, v in plan.seed.overrides.items()
    }
    assert doc.meta.generator_version == "0.1.1"
    assert doc.meta.tone_version == "^15.1.0"
    assert doc.meta.params == _POP
    assert doc.meta.title is None


# --- Sound design: per-track mix / sends / buses / master -------------------


def test_mix_sends_buses_and_master_from_sound_design() -> None:
    """Every emitted track takes its channel/effects/sends verbatim from the
    sound-design stage; the reverb bus is included (senders exist) and the master
    is the pack chain (PHASE_7 §7)."""
    plan, pack, sf, phrases = _drive(_POP)
    design = _design(plan, pack)
    doc = serialize(plan, sf, phrases, design, params=_POP)
    for track in doc.tracks:
        sound = design.track_sounds[track.id]
        assert track.channel == sound.channel
        assert track.channel.mute is False
        assert track.effects == list(sound.effects)
        assert track.sends == list(sound.sends)
    # A pop document always has reverb senders (comping/pads/cymbals), so the bus
    # is kept and every send targets it.
    assert [bus.id for bus in doc.buses] == ["reverb"]
    sent = {send.bus for track in doc.tracks for send in track.sends}
    assert sent == {"reverb"}
    assert doc.master == design.master
    assert doc.master.effects[-1].type == "Limiter"


def test_bus_omitted_when_no_emitted_track_sends() -> None:
    """§7 omission rule — if no emitted track sends to the reverb bus, the
    document omits the bus even though the stage always emits it."""
    plan, pack, sf, _ = _drive(_POP)
    design = _design(plan, pack)
    song_end = (sf.sections[-1].start_bar + sf.sections[-1].length_bars) * 1920
    # kick is dry (no reverb send), so a kick-only document sends to no bus.
    phrases = [
        Phrase(
            track_id="kick",
            role="drums",
            start_tick=0,
            end_tick=song_end,
            notes=[PhraseNote(ticks=0, duration_ticks=100, midi=None, velocity=0.9)],
        )
    ]
    assert design.track_sounds["kick"].sends == []
    doc = serialize(plan, sf, phrases, design, params=_POP)
    assert [t.id for t in doc.tracks] == ["kick"]
    assert doc.buses == []
    assert validate_document(doc) == []


# --- Track set / order + no tags in the dumped dict -------------------------


def test_track_set_and_order(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, _, phrases = pop
    with_notes = {p.track_id for p in phrases if any(True for _ in p.notes)}
    emitted = [t.id for t in doc.tracks]
    assert all(tid in with_notes for tid in emitted)
    # Emitted in the pinned order (drum sub-order, then bass/comping/pads).
    order_index = {tid: i for i, tid in enumerate(_EMIT_ORDER)}
    assert emitted == sorted(emitted, key=lambda tid: order_index[tid])
    for tid in emitted:
        assert tid in order_index


def test_dumped_notes_have_no_tags(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, _, _ = pop
    dumped = doc.model_dump(by_alias=True, exclude_none=True)
    for track in dumped["tracks"]:
        for note in track["notes"]:
            assert "tags" not in note


def test_track_names_are_human_labels(
    pop: tuple[TrackDocument, SongForm, list[Phrase]],
) -> None:
    doc, _, _ = pop
    names = {t.id: t.name for t in doc.tracks}
    if "kick" in names:
        assert names["kick"] == "Kick"
    if "tom_low" in names:
        assert names["tom_low"] == "Tom Low"
    if "bass" in names:
        assert names["bass"] == "Bass"
