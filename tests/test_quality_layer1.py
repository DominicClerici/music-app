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
from trackgen.quality import layer1
from trackgen.quality._common import (
    INTERNAL_TAGS,
    entry_index,
    section_span,
    sections_by_id,
    tick_to_section,
)
from trackgen.quality.layer1 import (
    _GRID_EXEMPT_TAGS,
    layer1_checks,
    regenerate_matches,
)
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.ir import Phrase
from trackgen.schema.validate import validate_document
from trackgen.transitions.ending import find_t_last

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}

_TICKS_PER_BAR = 1920

_W_RULES = ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8")


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


# ---------------------------------------------------------------------------
# W2 — device-policy compliance
# ---------------------------------------------------------------------------


def _flip_entered_section_to_breakdown(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, int]:
    """Retype an *entered* section (one at a section boundary) whose downbeat
    already carries a real entry crash to `"breakdown"`. That downbeat is now a
    suppression-class entry, so the real `"crash"`-tagged event there is illegal.

    This exercises W2's crash-suppression branch ONLY. It does NOT reach the §3.5
    dropout-truncation branch: no real note happens to sustain strictly across the
    retyped downbeat, so `entered_tick` never lands inside a note's
    `[ticks, ticks + duration_ticks)` span. The dropout branch is covered
    separately by `_sustain_note_across_breakdown_entry`, which forces such a
    sustain (all of this produced by no v1 reference form)."""
    sections = trace.song_form.sections
    for i in range(1, len(sections)):  # index >= 1 => entered at a section boundary.
        entered_tick = sections[i].start_bar * 1920
        has_crash = any(
            "crash" in note.tags and note.ticks == entered_tick
            for phrase in trace.phrases_stage6
            for note in phrase.notes
        )
        if not has_crash:
            continue
        new_sections = list(sections)
        new_sections[i] = sections[i].model_copy(update={"type": "breakdown"})
        new_form = trace.song_form.model_copy(update={"sections": new_sections})
        return replace(trace, song_form=new_form), entered_tick
    raise AssertionError("no entered section with an entry crash to retype")


def test_w2_breakdown_suppression_fires_only_w2() -> None:
    """A section retyped to `breakdown` whose downbeat still carries the (now
    illegal) entry crash fires W2 — the suppression-class branch — and no other
    W-rule."""
    base = generate_trace(_POP)
    trace, entered_tick = _flip_entered_section_to_breakdown(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W2"}
    assert any(
        m.startswith("W2:") and "crash" in m and str(entered_tick) in m
        for m in messages
    )
    # discriminating: the document is untouched, so V1-V8 stay clean.
    assert validate_document(trace.document) == []


def _add_stray_midsection_crash(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, str]:
    """Tag one interior groove note `"crash"` at a position that is no section
    boundary's entered downbeat — a stray entry-crash artifact."""
    boundary_ticks = {s.start_bar * 1920 for s in trace.song_form.sections}
    phrases = list(trace.phrases_stage6)
    for pi, phrase in enumerate(phrases):
        for ni, note in enumerate(phrase.notes):
            if note.ticks in boundary_ticks or "crash" in note.tags:
                continue
            new_notes = list(phrase.notes)
            new_notes[ni] = note.model_copy(update={"tags": [*note.tags, "crash"]})
            phrases[pi] = phrase.model_copy(update={"notes": new_notes})
            return replace(trace, phrases_stage6=phrases), phrase.track_id
    raise AssertionError("no interior note to mark with a stray crash")


def test_w2_stray_midsection_crash_fires_only_w2() -> None:
    """A `"crash"`-tagged event that lands mid-section (no boundary enters there)
    fires W2 only."""
    base = generate_trace(_POP)
    trace, track_id = _add_stray_midsection_crash(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W2"}
    assert any(
        m.startswith("W2:") and "not a legal entered downbeat" in m for m in messages
    )
    assert not any(m.startswith("L2-1:") for m in messages)


def _sustain_note_across_breakdown_entry(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, int, int]:
    """Retype the first *entered* section to `"breakdown"` AND stretch one
    stage-6 note so it sustains STRICTLY across that entered downbeat
    (`ticks < entered_tick < ticks + duration_ticks`), forcing W2's §3.5
    dropout-truncation branch — the branch `_flip_entered_section_to_breakdown`
    never reaches, since no real note happens to cross the boundary.

    Every real entered downbeat in the reference forms also carries an entry
    crash (§3.7), so retyping to a suppression class trips the crash branch too;
    both are W2 messages, so the fixture stays discriminating (`_w_rules_fired ==
    {"W2"}`) while the dropout message is asserted explicitly. Returns
    `(trace, entered_tick, sustaining_note_ticks)`."""
    sections = trace.song_form.sections
    entered_tick = sections[1].start_bar * _TICKS_PER_BAR
    new_phrases = list(trace.phrases_stage6)
    for pi, phrase in enumerate(new_phrases):
        for ni, note in enumerate(phrase.notes):
            if note.ticks >= entered_tick:
                continue
            # stretch this note one tick past the entered downbeat.
            new_dur = entered_tick - note.ticks + 1
            new_notes = list(phrase.notes)
            new_notes[ni] = note.model_copy(update={"duration_ticks": new_dur})
            new_phrases[pi] = phrase.model_copy(update={"notes": new_notes})
            new_sections = list(sections)
            new_sections[1] = sections[1].model_copy(update={"type": "breakdown"})
            new_form = trace.song_form.model_copy(update={"sections": new_sections})
            return (
                replace(trace, song_form=new_form, phrases_stage6=new_phrases),
                entered_tick,
                note.ticks,
            )
    raise AssertionError("no stage-6 note before the entered downbeat to stretch")


def test_w2_breakdown_dropout_truncation_fires_w2() -> None:
    """A note sustaining strictly across a `breakdown` entered downbeat trips the
    §3.5 dropout-truncation branch. The reference entered downbeat also carries an
    entry crash (now illegal under the retyped suppression class), so the crash
    branch fires too — both are W2, so only W2 is in the fired set — while the
    specific dropout message is asserted to prove that branch is genuinely
    reached (a non-firing dropout branch would fail this assertion)."""
    base = generate_trace(_POP)
    trace, entered_tick, note_ticks = _sustain_note_across_breakdown_entry(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W2"}
    assert any(
        m.startswith("W2:")
        and "dropout truncation not applied" in m
        and f"ticks={entered_tick}" in m
        and f"ticks={note_ticks}" in m
        for m in messages
    )
    assert not any(m.startswith("L2-1:") for m in messages)
    # discriminating: only the trace IRs were mutated, so V1-V8 stay clean.
    assert validate_document(trace.document) == []


def _tag_note_fill_outside_fill_bar(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, str, int]:
    """Tag one stage-6 note `"fill"` in a bar that is NOT a legal fill bar — not
    the last bar of an outgoing section, not the bar before an interior phrase
    start (§3.1) — so W2's fill-outside-fill-bar branch fires. The chosen note is
    an existing on-grid onset (its onset is untouched, so W7 stays clean) and
    carries no crash tag. Recomputes `legal_fill_bars` exactly as
    `_check_w2_device_policy` does. Returns `(trace, track_id, note_ticks)`."""
    sections = trace.song_form.sections
    legal_fill_bars: set[int] = set()
    for outgoing, _entered in zip(sections, sections[1:], strict=False):
        legal_fill_bars.add(outgoing.start_bar + outgoing.length_bars - 1)
    for section in sections:
        bar = section.start_bar
        for idx, section_phrase in enumerate(section.phrases):
            if idx > 0:
                legal_fill_bars.add(bar - 1)
            bar += section_phrase.bars

    new_phrases = list(trace.phrases_stage6)
    for pi, phrase in enumerate(new_phrases):
        for ni, note in enumerate(phrase.notes):
            bar = note.ticks // _TICKS_PER_BAR
            if bar in legal_fill_bars or "fill" in note.tags or "crash" in note.tags:
                continue
            new_notes = list(phrase.notes)
            new_notes[ni] = note.model_copy(update={"tags": [*note.tags, "fill"]})
            new_phrases[pi] = phrase.model_copy(update={"notes": new_notes})
            return (
                replace(trace, phrases_stage6=new_phrases),
                phrase.track_id,
                note.ticks,
            )
    raise AssertionError("no interior note in a non-fill bar to tag 'fill'")


def test_w2_fill_outside_fill_bar_fires_only_w2() -> None:
    """A `"fill"`-tagged event in a bar that is no legal fill bar fires W2's
    fill-placement branch, and only W2."""
    base = generate_trace(_POP)
    trace, track_id, note_ticks = _tag_note_fill_outside_fill_bar(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W2"}
    assert any(
        m.startswith("W2:")
        and "outside any fill bar" in m
        and track_id in m
        and f"ticks={note_ticks}" in m
        for m in messages
    )
    assert not any(m.startswith("L2-1:") for m in messages)
    # discriminating: the document is untouched, so V1-V8 stay clean.
    assert validate_document(trace.document) == []


def _tag_fill_at_suppressed_boundary(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, str, int]:
    """Retype an *entered* section to `"breakdown"` and tag one stage-6 note
    `"fill"` in that suppressed boundary's fill bar — the outgoing section's last
    bar (`entered.start_bar - 1`). §3.2 forbids a fill at a suppressed boundary,
    so once the boundary is a suppression class that bar is no longer a legal fill
    bar and W2's fill-placement branch fires. The chosen note keeps its onset (W7
    stays clean) and carries no crash tag. Returns `(trace, track_id, note_ticks)`."""
    sections = trace.song_form.sections
    for i in range(1, len(sections)):  # index >= 1 => entered at a section boundary.
        fill_bar = sections[i].start_bar - 1
        for pi, phrase in enumerate(trace.phrases_stage6):
            for ni, note in enumerate(phrase.notes):
                if note.ticks // _TICKS_PER_BAR != fill_bar:
                    continue
                if "fill" in note.tags or "crash" in note.tags:
                    continue
                new_sections = list(sections)
                new_sections[i] = sections[i].model_copy(update={"type": "breakdown"})
                new_form = trace.song_form.model_copy(update={"sections": new_sections})
                new_phrases = list(trace.phrases_stage6)
                new_notes = list(phrase.notes)
                new_notes[ni] = note.model_copy(update={"tags": [*note.tags, "fill"]})
                new_phrases[pi] = phrase.model_copy(update={"notes": new_notes})
                return (
                    replace(trace, song_form=new_form, phrases_stage6=new_phrases),
                    phrase.track_id,
                    note.ticks,
                )
    raise AssertionError("no note in a suppressed boundary's fill bar to tag 'fill'")


def test_w2_fill_at_suppressed_boundary_fires_only_w2() -> None:
    """A `"fill"`-tagged event in a suppressed (`breakdown`) boundary's fill bar
    is illegal under §3.2 — a suppressed boundary carries no fill — so W2's
    fill-placement branch fires, and only W2. (The retyped entered downbeat also
    carries the reference entry crash, now illegal too; both are W2, so the fired
    set stays `{"W2"}`.)"""
    base = generate_trace(_POP)
    trace, track_id, note_ticks = _tag_fill_at_suppressed_boundary(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W2"}
    assert any(
        m.startswith("W2:")
        and "outside any fill bar" in m
        and track_id in m
        and f"ticks={note_ticks}" in m
        for m in messages
    )
    assert not any(m.startswith("L2-1:") for m in messages)
    # discriminating: the document is untouched, so V1-V8 stay clean.
    assert validate_document(trace.document) == []


# ---------------------------------------------------------------------------
# W5 — determinism (regenerate from meta)
# ---------------------------------------------------------------------------


def _corrupt_doc_velocity(trace: GenerationTrace) -> GenerationTrace:
    """Change one document note's velocity to a different valid value — leaving
    `meta.params` intact — so regenerating from `meta` no longer reproduces this
    document, yet V1-V8 and every other W-rule stay clean."""
    doc = trace.document
    for ti, track in enumerate(doc.tracks):
        for ni, note in enumerate(track.notes):
            new_v = round(note.velocity / 2, 3) if note.velocity > 0.2 else 0.5
            if new_v == note.velocity:
                continue
            new_notes = list(track.notes)
            new_notes[ni] = note.model_copy(update={"velocity": new_v})
            new_tracks = list(doc.tracks)
            new_tracks[ti] = track.model_copy(update={"notes": new_notes})
            new_doc = doc.model_copy(update={"tracks": new_tracks})
            return replace(trace, document=new_doc)
    raise AssertionError("no document note to corrupt")


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_w5_regenerate_matches_real_trace(params: dict[str, object]) -> None:
    """`regenerate_matches` is True on a real document and `meta.params`
    round-trips the exact `raw_params` (incl. seed) that `serialize` echoed."""
    trace = generate_trace(params)
    assert trace.document.meta.params == params
    assert regenerate_matches(trace.document) is True


def test_w5_disabled_by_default_even_when_document_mismatches() -> None:
    """W5 doubles render cost, so it is skipped unless explicitly enabled: a
    corrupted document does NOT fire W5 under the default toggle."""
    assert layer1.REGENERATE_CHECK_ENABLED is False
    base = generate_trace(_POP)
    trace = _corrupt_doc_velocity(base)
    assert not regenerate_matches(trace.document)  # the mismatch is real...
    # ...but skipped under the default toggle.
    assert "W5" not in _w_rules_fired(layer1_checks(trace.document, trace))


def test_w5_mismatch_fires_only_w5_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the regenerate check enabled, a document that no longer reproduces
    from its own `meta` fires W5 — and only W5; the untouched document passes."""
    monkeypatch.setattr(layer1, "REGENERATE_CHECK_ENABLED", True)
    base = generate_trace(_POP)
    assert _w_rules_fired(layer1_checks(base.document, base)) == set()
    trace = _corrupt_doc_velocity(base)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W5"}
    assert any(m.startswith("W5:") for m in messages)


# ---------------------------------------------------------------------------
# W7 — pre-humanizer grid legality
# ---------------------------------------------------------------------------


def _shift_first_nonexempt_onset(
    phrases: list[Phrase], off: int = 37
) -> tuple[list[Phrase], str]:
    """Shift the first grid-non-exempt, non-fill onset by `off` ticks (off both
    grids: any legal pos + 37 lands on neither the straight nor triplet grid)."""
    phrases = list(phrases)
    for pi, phrase in enumerate(phrases):
        for ni, note in enumerate(phrase.notes):
            if any(t in _GRID_EXEMPT_TAGS for t in note.tags) or "fill" in note.tags:
                continue
            new_notes = list(phrase.notes)
            new_notes[ni] = note.model_copy(update={"ticks": note.ticks + off})
            new_notes.sort(
                key=lambda n: (n.ticks, n.midi if n.midi is not None else -1)
            )
            phrases[pi] = phrase.model_copy(update={"notes": new_notes})
            return phrases, phrase.track_id
    raise AssertionError("no non-exempt onset to displace")


def test_w7_offgrid_stage6_onset_fires_only_w7() -> None:
    base = generate_trace(_POP)
    new_phrases, track_id = _shift_first_nonexempt_onset(base.phrases_stage6)
    trace = replace(base, phrases_stage6=new_phrases)
    messages = validate_pipeline(trace.document, trace)
    assert _w_rules_fired(messages) == {"W7"}
    assert any(
        m.startswith("W7:") and track_id in m and "neither" in m for m in messages
    )


def test_w7_reads_stage6_not_stage7() -> None:
    """The identical off-grid displacement applied to `phrases_stage7` (where
    swing/jitter legitimately move onsets off-grid) does NOT trip W7 — W7 reads
    the pre-humanizer stage-6 snapshot."""
    base = generate_trace(_POP)
    new_phrases, _ = _shift_first_nonexempt_onset(base.phrases_stage7)
    trace = replace(base, phrases_stage7=new_phrases)
    assert "W7" not in _w_rules_fired(validate_pipeline(trace.document, trace))
