"""Milestone fixture (PHASE_1 §9 item 4) — schema + validator + structural facts.

The fixture is the de-risking artifact for the `TrackDocument` contract (D15):
it must parse into the pinned models, validate with ZERO violations, and
exercise every schema feature. These tests pin the structural facts so a future
edit that breaks the contract fails loudly.
"""

import json
from pathlib import Path

import pytest

from trackgen.schema.document import Track, TrackDocument
from trackgen.schema.validate import validate_document

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "milestone.trackdoc.json"
)

SONG_END = 30720
BAR = 1920


@pytest.fixture(scope="module")
def raw() -> dict[str, object]:
    with FIXTURE_PATH.open(encoding="utf-8") as fh:
        data: dict[str, object] = json.load(fh)
        return data


@pytest.fixture(scope="module")
def doc(raw: dict[str, object]) -> TrackDocument:
    return TrackDocument.model_validate(raw)


def test_fixture_parses_and_validates_zero_violations(doc: TrackDocument) -> None:
    assert validate_document(doc) == []


def test_meta_echo(doc: TrackDocument) -> None:
    assert doc.schema_version == 1
    assert doc.meta.generator_version == "0.1.2"
    assert doc.meta.tone_version == "^15.1.0"
    assert doc.meta.seed == "1ps9wxb"
    assert doc.meta.seed_overrides == {}
    assert doc.meta.title == "Milestone fixture"
    # params is an opaque echo; assert it round-trips as a plausible object.
    assert doc.meta.params == {
        "styleFamily": "pop_rock",
        "mood": "happy",
        "tempo": 96,
        "key": "C",
    }


def test_header_tempo_map(doc: TrackDocument) -> None:
    assert doc.header.ppq == 480
    assert [(t.ticks, t.bpm) for t in doc.header.tempos] == [(0, 96.0), (15360, 112.0)]
    assert [
        (t.ticks, t.numerator, t.denominator) for t in doc.header.time_signatures
    ] == [(0, 4, 4)]


def test_sections_cover_song(doc: TrackDocument) -> None:
    expected = [
        ("intro", 0, 7680),
        ("verse", 7680, 15360),
        ("chorus", 15360, 23040),
        ("outro", 23040, 30720),
    ]
    assert [(s.type, s.start_tick, s.end_tick) for s in doc.sections] == expected
    # contiguous from 0, exclusive ends, full coverage to song end (4 bars each).
    assert doc.sections[0].start_tick == 0
    assert doc.sections[-1].end_tick == SONG_END
    for prev, nxt in zip(doc.sections, doc.sections[1:], strict=False):
        assert prev.end_tick == nxt.start_tick
        assert nxt.end_tick - nxt.start_tick == 4 * BAR


def test_six_tracks_ids_roles_instruments(doc: TrackDocument) -> None:
    got = [(t.id, t.role, t.instrument.type) for t in doc.tracks]
    assert got == [
        ("kick", "drums", "MembraneSynth"),
        ("snare", "drums", "NoiseSynth"),
        ("hats", "drums", "MetalSynth"),
        ("bass", "bass", "MonoSynth"),
        ("comping", "comping", "PolySynth"),
        ("pads", "pads", "PolySynth"),
    ]


def _track(doc: TrackDocument, track_id: str) -> Track:
    return next(t for t in doc.tracks if t.id == track_id)


def test_snare_is_unpitched(doc: TrackDocument) -> None:
    snare = _track(doc, "snare")
    assert snare.instrument.type == "NoiseSynth"
    assert snare.notes  # non-empty
    assert all(n.midi is None for n in snare.notes)
    # V3: no duplicate ticks (no double-hits) on the unpitched track.
    ticks = [n.ticks for n in snare.notes]
    assert len(set(ticks)) == len(ticks)


def test_non_drum_register_ceiling(doc: TrackDocument) -> None:
    for track in doc.tracks:
        if track.role == "drums":
            continue
        assert track.notes
        assert all(n.midi is not None and n.midi <= 71 for n in track.notes)


def test_bass_changes_pitch_with_chords(doc: TrackDocument) -> None:
    bass = _track(doc, "bass")
    # First downbeat of each bar (ticks == bar*1920) is the chord root.
    downbeats = {n.ticks: n.midi for n in bass.notes if n.ticks % BAR == 0}
    roots = [downbeats[bar * BAR] for bar in range(16)]
    assert roots == [48, 43, 45, 41, 48, 43, 45, 41, 41, 43, 48, 45, 48, 43, 41, 48]
    assert len(set(roots)) > 1  # genuinely changes


def test_comping_is_polychord_that_changes(doc: TrackDocument) -> None:
    comping = _track(doc, "comping")
    inst = comping.instrument
    assert inst.type == "PolySynth"
    assert inst.voice == "FMSynth"
    assert inst.max_polyphony == 6
    # Bar 0 downbeat is a C major triad; bar 1 downbeat is a G major triad.
    bar0 = sorted(n.midi for n in comping.notes if n.ticks == 0 if n.midi is not None)
    bar1 = sorted(n.midi for n in comping.notes if n.ticks == BAR if n.midi is not None)
    assert bar0 == [60, 64, 67]
    assert bar1 == [55, 59, 62]


def test_pads_polysynth_with_chorus_insert(doc: TrackDocument) -> None:
    pads = _track(doc, "pads")
    assert pads.instrument.type == "PolySynth"
    assert pads.instrument.voice == "AMSynth"
    assert pads.instrument.max_polyphony == 6
    assert [e.type for e in pads.effects] == ["Chorus"]


def test_reverb_bus_and_sends(doc: TrackDocument) -> None:
    assert [b.id for b in doc.buses] == ["reverb"]
    assert [e.type for e in doc.buses[0].effects] == ["Reverb"]
    senders = {t.id: [(s.bus, s.gain_db) for s in t.sends] for t in doc.tracks}
    assert senders["snare"] == [("reverb", -18)]
    assert senders["comping"] == [("reverb", -15)]
    assert senders["pads"] == [("reverb", -12)]
    # kick and bass stay dry.
    assert senders["kick"] == []
    assert senders["bass"] == []
    assert senders["hats"] == []


def test_master_chain(doc: TrackDocument) -> None:
    assert [e.type for e in doc.master.effects] == ["Compressor", "Limiter"]


def test_channels_present(doc: TrackDocument) -> None:
    # per-track channel volumeDb/pan/mute exercised across tracks.
    for track in doc.tracks:
        assert track.channel.volume_db <= 6
        assert -1 <= track.channel.pan <= 1
        assert track.channel.mute is False
    # pans are not all identical (stereo placement is real).
    pans = {t.channel.pan for t in doc.tracks}
    assert len(pans) > 1
