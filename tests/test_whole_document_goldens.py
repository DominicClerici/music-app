"""Whole-document milestone goldens (PHASE_5 DoD 8/10, SESSION_09 T4).

The two committed fixtures `fixtures/{pop_rock,jazz}.milestone.trackdoc.json`
are the pipeline's first whole-document golden regression surface (ROADMAP
Phase-8 mechanism, seeded here). They were blessed in spirit from the
authoritative engine (ROADMAP §3 rule 3) via `tests/_regen_milestone_fixtures.py`
— never hand-edited. Once committed the fixture, not the doc prose, is the
regression surface (arbitration rule 3): each test below asserts a fresh
`generate_track` re-serializes structure-identically to the committed file
(DoD 10), the committed doc passes V1–V8 (DoD 8), and a handful of §9.4/§9.5
worked-example anchors match the committed values (documentation cross-checks,
using the C-09-corrected §9.4 numbers).

If a generated value ever diverges from a §9.4/§9.5 anchor here the fixture wins
(recompute + escalate; ROADMAP §3) — do NOT tune code or the fixture to a printed
number.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trackgen.pipeline import generate_track
from trackgen.schema.document import Track, TrackDocument
from trackgen.schema.validate import validate_document

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_BAR = 1920

# name -> (fixture filename, the raw params dict — same seed chain as
# PHASE_2 §6.5 -> PHASE_3 §7.4 -> PHASE_4 §10 -> PHASE_5 §9, seed 1ps9wxb).
_EXAMPLES: dict[str, tuple[str, dict[str, object]]] = {
    "pop": (
        "pop_rock.milestone.trackdoc.json",
        {"styleFamily": "pop_rock", "seed": "1ps9wxb"},
    ),
    "jazz": (
        "jazz.milestone.trackdoc.json",
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        },
    ),
}

# Drum trigger midis the Serializer injects from the stub timbres (D-A / D-B):
# snare (NoiseSynth) stays None; the rest carry their trigger pitch.
_TRIGGER_MIDI = {"kick": 24, "hats": 80, "ride": 82}

# SESSION_12 T1 wires the real stages 6 (transitions) and 7 (humanize), so a fresh
# `generate_track` now emits fills/crashes, humanized ticks/velocities/durations,
# and (jazz) a ritard tempo map — diverging from the stale Phase-5 fixtures. Every
# assertion that compares against `generate_track` output is xfail'd here (strict:
# it must fail until T2 re-blesses the fixtures, then T2 un-marks these). The
# fixture-loading checks (validate / meta / invariants) below stay green.
_REBLESS = pytest.mark.xfail(
    strict=True,
    reason="Phase 6 output legitimately changes; re-blessed in SESSION_12 T2 "
    "(dedicated commit)",
)


def _load_raw(filename: str) -> dict[str, object]:
    with (_FIXTURES / filename).open(encoding="utf-8") as fh:
        data: dict[str, object] = json.load(fh)
        return data


def _track(doc: TrackDocument, track_id: str) -> Track:
    return next(t for t in doc.tracks if t.id == track_id)


@_REBLESS
@pytest.mark.parametrize("example", list(_EXAMPLES), ids=list(_EXAMPLES))
def test_fixture_reserializes_identically(example: str) -> None:
    """DoD 10 — a fresh `generate_track` re-serializes structure-identically
    to the committed fixture. This is the whole-document regression surface: any
    behavior or wiring change that shifts a single note fails here."""
    filename, params = _EXAMPLES[example]
    committed = _load_raw(filename)
    produced = generate_track(params).model_dump(by_alias=True, exclude_none=True)
    assert produced == committed


@pytest.mark.parametrize("example", list(_EXAMPLES), ids=list(_EXAMPLES))
def test_fixture_validates_zero_violations(example: str) -> None:
    """DoD 8 — the committed document passes PHASE_1 §3.8 V1–V8 and the schema."""
    filename, _params = _EXAMPLES[example]
    doc = TrackDocument.model_validate(_load_raw(filename))
    assert validate_document(doc) == []


@pytest.mark.parametrize("example", list(_EXAMPLES), ids=list(_EXAMPLES))
def test_meta_params_roundtrip(example: str) -> None:
    """`meta.params` is non-empty and carries `seed: "1ps9wxb"`, and `meta.seed`
    echoes the same seed — round-trip reproducibility (guards T2 params
    threading: an emitted doc can be regenerated from its own metadata)."""
    filename, params = _EXAMPLES[example]
    doc = TrackDocument.model_validate(_load_raw(filename))
    assert doc.meta.params
    assert doc.meta.params == params
    assert doc.meta.params["seed"] == "1ps9wxb"
    assert doc.meta.seed == "1ps9wxb"


@pytest.mark.parametrize("example", list(_EXAMPLES), ids=list(_EXAMPLES))
def test_whole_document_invariants(example: str) -> None:
    """Whole-doc invariant sweep across every track:
    - no non-drum note has midi > 71 (ROADMAP invariant 4 / V4);
    - every note ends `<= sections[-1].endTick` (V8);
    - snare (NoiseSynth) notes carry `midi is None` (V5);
    - kick/hats/ride notes carry their injected trigger midi (24/80/82)."""
    filename, _params = _EXAMPLES[example]
    doc = TrackDocument.model_validate(_load_raw(filename))
    song_end = doc.sections[-1].end_tick

    for track in doc.tracks:
        for note in track.notes:
            assert note.ticks + note.duration_ticks <= song_end, (track.id, note.ticks)
            if track.role != "drums":
                assert note.midi is not None and note.midi <= 71, (track.id, note)

    snare = _track(doc, "snare")
    assert snare.instrument.type == "NoiseSynth"
    assert snare.notes
    assert all(n.midi is None for n in snare.notes)

    for track_id, trigger in _TRIGGER_MIDI.items():
        track = _track(doc, track_id)
        assert track.notes
        assert all(n.midi == trigger for n in track.notes), track_id


# =============================================================================
# §9.4 / §9.5 documentation anchors (values FROM the committed fixture,
# cross-checked to the C-09-corrected §9.4/§9.5 prose). Fixture wins on conflict.
# =============================================================================


@_REBLESS
def test_pop_verse1_bar4_comping_anchor() -> None:
    """§9.4 pop verse-1 bar 4 (tick 7680), governing chord E: comping hits
    G♯3+B3+E4 = midis [56,59,64] at @0, dur 814, velocity 0.68 (C-09-corrected
    voicing — inherits the §9.3 verse-1 E voicing)."""
    doc = generate_track(_EXAMPLES["pop"][1])
    comping = _track(doc, "comping")
    lo = 4 * _BAR  # 7680 — verse-1's first bar
    hits = [n for n in comping.notes if n.ticks == lo]
    assert sorted(n.midi for n in hits if n.midi is not None) == [56, 59, 64]
    assert {(n.duration_ticks, n.velocity) for n in hits} == {(814, 0.68)}


@_REBLESS
def test_jazz_head1_bass_note_count_anchor() -> None:
    """§9.2/§9.4 jazz Head-In (ticks 0–23040) walker bass note count = 24."""
    doc = generate_track(_EXAMPLES["jazz"][1])
    bass = _track(doc, "bass")
    head_in = doc.sections[0]
    assert head_in.type == "head" and head_in.start_tick == 0
    head_bass = [
        n for n in bass.notes if head_in.start_tick <= n.ticks < head_in.end_tick
    ]
    assert len(head_bass) == 24


@_REBLESS
def test_jazz_head1_bar0_comping_charleston_anchor() -> None:
    """§9.4 jazz head-1 bar 0 (Dm9): Charleston comping voices F3+C4 =
    midis [53,60] at tick 0."""
    doc = generate_track(_EXAMPLES["jazz"][1])
    comping = _track(doc, "comping")
    hits = sorted(n.midi for n in comping.notes if n.ticks == 0 and n.midi is not None)
    assert hits == [53, 60]


@_REBLESS
def test_jazz_ending_final_low_d_whole_note_anchor() -> None:
    """§9.2/§9.5 jazz ending — the final bass note is a low D whole note settling
    under the outro. The last note is D2 (midi 38), a full-bar whole note (1920
    ticks) landing on the outro's last bar and ending exactly at song end."""
    doc = generate_track(_EXAMPLES["jazz"][1])
    bass = _track(doc, "bass")
    song_end = doc.sections[-1].end_tick
    last = bass.notes[-1]
    assert last.midi == 38  # D2
    assert last.duration_ticks == _BAR  # whole note (4/4 bar)
    assert last.ticks + last.duration_ticks == song_end
