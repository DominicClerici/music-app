"""Tests for the Layer-1 validator suite (PHASE_8 §8.1, W1/W3/W4/W6/W8) and the
`validate_pipeline` subsumption of the frozen document validator (V1-V8).

Fixtures are built the `tests/test_validate.py` way — take a real
`generate_trace(...)` output and mutate exactly one field via `model_copy` (frozen
pydantic) / `dataclasses.replace` (the frozen `GenerationTrace` dataclass) — so
every violating fixture is one edit away from a passing trace, and each is proven
*discriminating*: it fires its own `WN:` rule and no other W-rule.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from trackgen.packs.models import DrumEvent
from trackgen.parts.generators import _VOICE_TRACK, _tile
from trackgen.pipeline.trace import GenerationTrace, generate_trace
from trackgen.quality._common import (
    INTERNAL_TAGS,
    entry_index,
    section_span,
    sections_by_id,
    tick_to_section,
)
from trackgen.quality.layer1 import layer1_checks
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.validate import validate_document
from trackgen.transitions.ending import find_t_last

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}

_W_RULES = ("W1", "W3", "W4", "W6", "W8")


def _w_rules_fired(messages: list[str]) -> set[str]:
    return {
        rule for rule in _W_RULES if any(m.startswith(rule + ":") for m in messages)
    }


# ---------------------------------------------------------------------------
# Subsumption / happy path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_validate_pipeline_clean_on_real_trace(params: dict[str, object]) -> None:
    """A real `generate_trace` document passes the full suite cleanly AND still
    passes the standalone document validator (V1-V8 subsumed, not broken)."""
    trace = generate_trace(params)
    assert validate_pipeline(trace.document, trace) == []
    assert validate_document(trace.document) == []


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_layer1_clean_on_real_trace(params: dict[str, object]) -> None:
    trace = generate_trace(params)
    assert layer1_checks(trace.document, trace) == []


# ---------------------------------------------------------------------------
# W1 — lane compliance
# ---------------------------------------------------------------------------


def _bump_note_above_lane(trace: GenerationTrace) -> tuple[GenerationTrace, str]:
    """Push one non-drum doc note's midi one semitone above its section lane
    ceiling while staying <= 71, so W1 fires but V4 (global <= 71) does not."""
    idx = entry_index(trace)
    locate = tick_to_section(trace)
    doc = trace.document
    for ti, track in enumerate(doc.tracks):
        if track.role == "drums":
            continue
        for ni, note in enumerate(track.notes):
            if note.midi is None:
                continue
            section = locate(note.ticks)
            if section is None:
                continue
            entry = idx.get((section.id, track.role))
            if entry is None:
                continue
            new_midi = entry.register.high_midi + 1
            if new_midi > 71:  # would also trip V4; we want a W1-only fixture.
                continue
            new_notes = list(track.notes)
            new_notes[ni] = note.model_copy(update={"midi": new_midi})
            new_notes.sort(
                key=lambda n: (n.ticks, n.midi if n.midi is not None else -1)
            )
            new_tracks = list(doc.tracks)
            new_tracks[ti] = track.model_copy(update={"notes": new_notes})
            new_doc = doc.model_copy(update={"tracks": new_tracks})
            return replace(trace, document=new_doc), track.id
    raise AssertionError("no non-drum note with a lane ceiling < 71 to bump")


def test_w1_lane_violation_fires_only_w1() -> None:
    base = generate_trace(_POP)
    trace, track_id = _bump_note_above_lane(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W1"}
    assert any(m.startswith("W1:") and track_id in m for m in messages)
    # discriminating: the mutation stays inside the document validator's bounds.
    assert validate_document(trace.document) == []


# ---------------------------------------------------------------------------
# W3 — ending integrity
# ---------------------------------------------------------------------------


def _break_final_root(trace: GenerationTrace) -> GenerationTrace:
    """Reroot the song's last `"final"`-tagged chord off the key tonic, so it is
    no longer degree-1-rooted (W3), leaving `T_last` and the document intact."""
    chords = list(trace.harmony.chords)
    final_i = max(i for i, c in enumerate(chords) if "final" in c.tags)
    chord_event = chords[final_i]
    new_pc = (trace.harmony.keys[0].tonic_pc + 1) % 12
    chords[final_i] = chord_event.model_copy(
        update={"chord": chord_event.chord.model_copy(update={"root_pc": new_pc})}
    )
    new_harmony = trace.harmony.model_copy(update={"chords": chords})
    return replace(trace, harmony=new_harmony)


def test_w3_non_degree1_final_fires_only_w3() -> None:
    base = generate_trace(_POP)
    trace = _break_final_root(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W3"}
    assert any("not degree-1-rooted" in m for m in messages)


def test_w3_missing_final_tag_fires_only_w3() -> None:
    # Strip every "final" tag to force the "no final anchor at all" branch.
    base = generate_trace(_POP)
    chords = [
        c.model_copy(update={"tags": [t for t in c.tags if t != "final"]})
        for c in base.harmony.chords
    ]
    trace = replace(base, harmony=base.harmony.model_copy(update={"chords": chords}))
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W3"}
    assert any("no ChordEvent tagged 'final'" in m for m in messages)


def _negatively_displace_hold_note(trace: GenerationTrace) -> GenerationTrace:
    """Rewrite one pitched `"hold"`-tagged stage-7 note as the humanizer would on a
    NEGATIVE onset offset: onset pulled 5 ticks *before* `T_last`, full authored
    span retained (the song-end clamp only fires on a LATE onset, so an early
    onset's end lands 5 ticks short of `final_end`). The note is still the tagged
    HOLD — W3 must not read that micro-timing as an ending-integrity break. This
    reproduces the reviewer's false-positive against the old onset-proximity /
    exact-`end == final_end` check on the document."""
    t_last = find_t_last(trace.harmony)
    final_section = tick_to_section(trace)(t_last)
    assert final_section is not None
    final_end = section_span(final_section)[1]
    phrases = list(trace.phrases_stage7)
    for pi, phrase in enumerate(phrases):
        if phrase.role == "drums":
            continue
        for ni, note in enumerate(phrase.notes):
            if "hold" not in note.tags:
                continue
            new_notes = list(phrase.notes)
            new_notes[ni] = note.model_copy(
                update={"ticks": t_last - 5, "duration_ticks": final_end - t_last}
            )
            phrases[pi] = phrase.model_copy(update={"notes": new_notes})
            return replace(trace, phrases_stage7=phrases)
    raise AssertionError("no pitched HOLD note to displace")


def test_w3_negative_hold_displacement_does_not_fire() -> None:
    """A HOLD pitched note pulled 5 ticks *before* T_last (its end thus 5 ticks
    short of the section end) is legitimate humanizer micro-timing, not an ending
    break: it is still the tagged HOLD, so W3 (and the whole suite) stays clean."""
    base = generate_trace(_POP)
    trace = _negatively_displace_hold_note(base)
    messages = validate_pipeline(trace.document, trace)
    assert "W3" not in _w_rules_fired(messages)
    assert messages == []


# ---------------------------------------------------------------------------
# W4 — density-gate recheck (drums, C-11 ornament backmap)
# ---------------------------------------------------------------------------


def _starve_drum_entry_with_ornament(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, str]:
    """Zero the density budget of a drums entry that has an instantiated
    `minDensity` drum event (an `ornament` note in stage 5), so the recomputed
    gate turns it off while the phrase note remains — the W4 drift signal."""
    idx = entry_index(trace)
    by_id = sections_by_id(trace)

    ornament_at: set[tuple[str, int, str]] = set()
    for phrase in trace.phrases_stage5:
        if phrase.role != "drums":
            continue
        for note in phrase.notes:
            if "ornament" in note.tags:
                voice = next((t for t in note.tags if t in _VOICE_TRACK), None)
                if voice is not None:
                    ornament_at.add((phrase.track_id, note.ticks, voice))

    for (section_id, role), entry in idx.items():
        if role != "drums" or not entry.active:
            continue
        env = trace.selection.by_section.get((section_id, role))
        section = by_id.get(section_id)
        if env is None or section is None:
            continue
        for abs_tick, event in _tile(section, env):
            if not isinstance(event, DrumEvent) or not event.min_density:
                continue
            if (_VOICE_TRACK[event.voice], abs_tick, event.voice) in ornament_at:
                new_entries = [
                    e.model_copy(update={"density_budget": 0.0})
                    if (e.section_id, e.role) == (section_id, role)
                    else e
                    for e in trace.arrangement.entries
                ]
                new_ap = trace.arrangement.model_copy(update={"entries": new_entries})
                return replace(trace, arrangement=new_ap), section_id
    raise AssertionError("no instantiated minDensity drum event to starve")


def test_w4_starved_ornament_fires_only_w4() -> None:
    base = generate_trace(_POP)
    trace, section_id = _starve_drum_entry_with_ornament(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W4"}
    assert any(m.startswith("W4:") and section_id in m for m in messages)


# ---------------------------------------------------------------------------
# W6 — tag vocabulary
# ---------------------------------------------------------------------------


def _add_stray_tag(trace: GenerationTrace) -> tuple[GenerationTrace, str]:
    phrases = list(trace.phrases_stage7)
    for pi, phrase in enumerate(phrases):
        if phrase.notes:
            note = phrase.notes[0]
            new_notes = list(phrase.notes)
            new_notes[0] = note.model_copy(update={"tags": [*note.tags, "bogus"]})
            phrases[pi] = phrase.model_copy(update={"notes": new_notes})
            return replace(trace, phrases_stage7=phrases), phrase.track_id
    raise AssertionError("no stage-7 note to tag")


def test_w6_stray_tag_fires_only_w6() -> None:
    base = generate_trace(_POP)
    trace, track_id = _add_stray_tag(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W6"}
    assert any(m.startswith("W6:") and "bogus" in m for m in messages)


def test_w6_c11_provenance_tags_do_not_fire() -> None:
    """The C-11 internal drum provenance tags (voice names + `ornament`) are
    present on real stage-7 drum notes yet W6 stays clean — `strip_internal`
    works, so W6 is discriminating (not vacuous)."""
    trace = generate_trace(_POP)
    provenance_seen = {
        tag
        for phrase in trace.phrases_stage7
        if phrase.role == "drums"
        for note in phrase.notes
        for tag in note.tags
        if tag in INTERNAL_TAGS
    }
    assert provenance_seen, "expected C-11 provenance tags on real drum notes"
    assert _w_rules_fired(validate_pipeline(trace.document, trace)) == set()


# ---------------------------------------------------------------------------
# W8 — humanizer note-count preservation
# ---------------------------------------------------------------------------


def _append_stage7_note(trace: GenerationTrace) -> tuple[GenerationTrace, str]:
    phrases = list(trace.phrases_stage7)
    for pi, phrase in enumerate(phrases):
        if phrase.notes:
            phrases[pi] = phrase.model_copy(
                update={"notes": [*phrase.notes, phrase.notes[0]]}
            )
            return replace(trace, phrases_stage7=phrases), phrase.track_id
    raise AssertionError("no stage-7 phrase to grow")


def test_w8_note_count_mismatch_fires_only_w8() -> None:
    base = generate_trace(_POP)
    trace, track_id = _append_stage7_note(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W8"}
    assert any(m.startswith("W8:") and track_id in m for m in messages)
