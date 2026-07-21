"""Layer 1 — hard pipeline invariants (PHASE_8 §8.1, W1-W8).

Pipeline-aware checks that read the IR boundaries of a `GenerationTrace`, not
just the document (which is why they live beside — not inside —
`schema/validate.py`'s V1-V8). Each `_check_wN` returns a list of
human-readable messages, each prefixed with its rule id (`"W1: ..."`), mirroring
`validate.py`'s `_check_vN` style.

This module implements the five *mechanical* checks **W1, W3, W4, W6, W8**
(task T1) plus the three substantial checks **W2, W5, W7** (task T2), all in the
same `layer1_checks` aggregator (a list of check callables, so they slot in
cleanly).

The SESSION_16 §4 scoping decisions this file honors:
- **W1** (§4 non-star): per-`(section, role)` lane membership, strengthening V4.
- **W2** (§4 decision 2): a policy-consistency *evidence* check — for every
  section boundary, the rendered `phrases_stage6` devices legal for the entered
  section type per PHASE_6 §3.2 (not a per-boundary RNG re-derivation).
- **W3** (§4 non-star): ending integrity — final chord degree-1-rooted + `final`
  tags present + the §3.6 HOLD shape on `phrases_stage7` (identified by the
  `"hold"` tag, which survives into the phrases but not the tagless document).
- **W4** (§4 decision 4): a drums-only density-gate recompute using the C-11
  `ornament` backmap on `phrases_stage5` — the only role that exposes a
  note-to-event provenance link.
- **W5** (§4 decision 5): determinism — regenerating from `meta.params`
  reproduces a byte-identical document. Doubles render cost, so it is gated
  behind a module toggle (`REGENERATE_CHECK_ENABLED`, default off).
- **W6** (§4 decision 1): output-tag vocabulary over `phrases_stage7`, stripping
  the C-11 internal provenance tags first.
- **W7** (§4 decision 3): pre-humanizer grid legality on `phrases_stage6` —
  every non-exempt onset on the straight or triplet grid, one grid per Phrase.
- **W8** (§4 non-star): per-`track_id` note-count preservation stage 6 -> 7.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from trackgen.packs.models import DrumEvent
from trackgen.parts.dynamics import is_event_active
from trackgen.parts.generators import _VOICE_TRACK, _tile
from trackgen.pipeline.serialize import to_json
from trackgen.pipeline.trace import GenerationTrace, generate_trace
from trackgen.quality._common import (
    entry_index,
    section_span,
    sections_by_id,
    strip_internal,
    tick_to_section,
)
from trackgen.schema.document import TrackDocument
from trackgen.schema.ir import Phrase

_TICKS_PER_BEAT = 480
_TICKS_PER_BAR = 1920

# §3.2 suppression classes: the entered section types that carry no entry crash
# ("smooth continuation" / "clean cut into the thinned texture").
_SUPPRESSION_TYPES: frozenset[str] = frozenset({"postchorus", "breakdown"})

# W7 grid sets (§3.1). Straight = the union of the legal 16th (`{0,120,240,360}`)
# and 8th (`{0,240}`) straight positions; triplet = `{0,160,320}`. `0` is on both
# — a pos-0 onset is grid-neutral and constrains a Phrase to neither grid.
_STRAIGHT_GRID: frozenset[int] = frozenset({0, 120, 240, 360})
_TRIPLET_GRID: frozenset[int] = frozenset({0, 160, 320})

# W7 grid-exempt tags (§4 decision 3): mutation/device artifacts, not authored
# pattern onsets, so they are not held to the pattern grid.
_GRID_EXEMPT_TAGS: frozenset[str] = frozenset({"var", "crash", "hold"})

# The pinned §3.9 output-tag vocabulary (PHASE_6 contributes fill/crash/var/hold;
# push/ghost come from earlier stages). W6 asserts every non-provenance note tag
# is drawn from this set.
_OUTPUT_TAGS: frozenset[str] = frozenset(
    {"ghost", "push", "fill", "crash", "var", "hold"}
)

# The two drum tracks the §3.6 HOLD strikes at `T_last` — one struck crash + one
# kick, tagged `"hold"` in `transitions/ending.py`. All other drum onsets are
# cleared from `T_last` on.
_HOLD_DRUM_TRACKS: frozenset[str] = frozenset({"crash", "kick"})


# --- W1: lane compliance ------------------------------------------------------


def _check_w1_lane_compliance(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Every non-drum note lies within its `(section, role)` register lane.

    Stronger than V4 (global <= 71): the lane is the bias-shifted
    `ArrangementEntry.register` for the note's section + the track's role. Drums
    are skipped (V4's drum exemption; trigger midis are synthesis params, not
    pitch)."""
    violations: list[str] = []
    idx = entry_index(trace)
    locate = tick_to_section(trace)

    for track in doc.tracks:
        if track.role == "drums":
            continue
        for note in track.notes:
            if note.midi is None:
                continue
            section = locate(note.ticks)
            if section is None:
                continue
            entry = idx.get((section.id, track.role))
            if entry is None:
                continue
            lane = entry.register
            if note.midi < lane.low_midi or note.midi > lane.high_midi:
                violations.append(
                    f"W1: track '{track.id}' note at ticks={note.ticks} has "
                    f"midi={note.midi} outside section {section.id!r} lane "
                    f"[{lane.low_midi}, {lane.high_midi}]"
                )
    return violations


# --- W3: ending integrity -----------------------------------------------------


def _check_w3_ending_integrity(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Final chord degree-1-rooted with `final` tags present; §3.6 HOLD applied.

    Chord layer (exact, reads `trace.harmony`): >= 1 `"final"`-tagged
    `ChordEvent`, and the last such chord is rooted on the key tonic
    (`chord.root_pc == keys[0].tonic_pc`). `T_last` is that chord's `start_tick`.

    HOLD layer (reads `trace.phrases_stage7`): the §3.6 transform tags every note
    it authors `"hold"` in `transitions/ending.py`, and `phrases_stage7` retains
    phrase-note tags (only the document's `NoteEvent` drops them). Identifying the
    HOLD by that tag — not by onset-proximity to `T_last` — makes the check immune
    to the humanizer's micro-timing. `ending.py` authors exactly: one struck
    `crash` + one `kick` (via `add_crash_and_kick`, tagged `"hold"`), and every
    pitched note that attacked at `T_last` extended to the final section's end
    (tagged `"hold"`); later attacks are deleted. W3 mirrors that shape:
      * the drum HOLD is exactly one `crash` + one `kick` hold note;
      * no non-HOLD drum attack lands at/after `T_last`;
      * each pitched HOLD note reaches the final section end."""
    violations: list[str] = []

    finals = [chord for chord in trace.harmony.chords if "final" in chord.tags]
    if not finals:
        return ["W3: no ChordEvent tagged 'final' — ending anchor is undefined"]

    keys = trace.harmony.keys
    if not keys:
        return ["W3: harmony carries no key region — cannot check degree-1 root"]
    tonic_pc = keys[0].tonic_pc
    last_final = finals[-1]
    if last_final.chord.root_pc != tonic_pc:
        violations.append(
            f"W3: final chord root_pc={last_final.chord.root_pc} is not "
            f"degree-1-rooted (key tonic_pc={tonic_pc})"
        )

    t_last = last_final.start_tick
    final_section = tick_to_section(trace)(t_last)
    if final_section is None:
        violations.append(f"W3: T_last={t_last} falls in no form section")
        return violations
    # The final `"final"`-tagged chord sits in the song's last section, so its end
    # is the song end — the tick the humanizer's `_emit` down-clamps note ends to
    # (a late onset is pulled in to it; an early onset never reaches past it).
    final_end = section_span(final_section)[1]

    hold_drum_counts: dict[str, int] = defaultdict(int)
    for phrase in trace.phrases_stage7:
        if phrase.role == "drums":
            for note in phrase.notes:
                if "hold" in note.tags:
                    hold_drum_counts[phrase.track_id] += 1
                elif note.ticks >= t_last:
                    violations.append(
                        f"W3: drum track '{phrase.track_id}' has a non-HOLD attack "
                        f"at ticks={note.ticks} >= T_last={t_last} (HOLD clears "
                        f"drums)"
                    )
            continue
        for note in phrase.notes:
            if "hold" not in note.tags:
                continue
            # Authored to end at `final_end`; the humanizer preserves that span for
            # an early/on-grid onset and clamps a late onset's end down to the song
            # end, so the HOLD reaches `final_end` capped by its (displaced) onset.
            expected_end = min(note.ticks + (final_end - t_last), final_end)
            if note.ticks + note.duration_ticks != expected_end:
                violations.append(
                    f"W3: pitched track '{phrase.track_id}' HOLD note at "
                    f"ticks={note.ticks} does not extend to final section end "
                    f"(end={note.ticks + note.duration_ticks}, "
                    f"expected {expected_end})"
                )

    for track_id in sorted(_HOLD_DRUM_TRACKS):
        found = hold_drum_counts.pop(track_id, 0)
        if found != 1:
            violations.append(
                f"W3: expected exactly one HOLD {track_id} note, found {found}"
            )
    for track_id, found in sorted(hold_drum_counts.items()):
        violations.append(
            f"W3: unexpected HOLD-tagged drum note(s) on track '{track_id}' "
            f"(found {found}; HOLD strikes only crash + kick)"
        )

    return violations


# --- W4: density-gate recheck (drums only, C-11 ornament backmap) --------------


def _check_w4_density_gate(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """No gated-off `minDensity` drum event is nonetheless instantiated.

    Per §4 decision 4, a doc-note -> pattern-event backmap is only available for
    drums (the C-11 `ornament` tag on `phrases_stage5`). So W4 re-runs the
    `is_event_active` gate over each active drums entry's *selected* pattern
    envelope: for every tiled `minDensity` drum event whose recomputed state is
    gated off (`density_budget < minDensity`), it must NOT appear as an
    `ornament` note at its tiled `(tick, voice)` position. A stray one means the
    arrangement budget and the generated phrases have drifted apart.

    This is a cross-IR *consistency* check, not a from-scratch budget recompute:
    it reuses the generator's own `is_event_active` gate and `_tile` layout, so it
    reflects exactly what the generator would have decided and cannot drift from
    it — it only asserts the instantiated `phrases_stage5` ornament note agrees
    with that decision under the arrangement's `density_budget`."""
    violations: list[str] = []
    idx = entry_index(trace)
    by_id = sections_by_id(trace)
    selection = trace.selection

    # ornament notes from stage 5 (pre-mutation, pre-humanize), keyed for lookup:
    # (track_id, tick, voice) -> present. Stage 5 onsets are exact grid ticks.
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
        env = selection.by_section.get((section_id, role))
        section = by_id.get(section_id)
        if env is None or section is None:
            continue
        for abs_tick, event in _tile(section, env):
            if not isinstance(event, DrumEvent) or event.min_density is None:
                continue
            if is_event_active(event.min_density, entry.density_budget):
                continue  # gated ON — legitimately instantiated.
            track_id = _VOICE_TRACK[event.voice]
            if (track_id, abs_tick, event.voice) in ornament_at:
                violations.append(
                    f"W4: section {section_id!r} drum event voice={event.voice!r} "
                    f"at ticks={abs_tick} is instantiated (ornament note present) "
                    f"but its minDensity={event.min_density} exceeds "
                    f"densityBudget={entry.density_budget}"
                )
    return violations


# --- W6: tag vocabulary -------------------------------------------------------


def _check_w6_tag_vocabulary(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Every note's output tags are drawn from the pinned §3.9 set.

    Reads `phrases_stage7` (the document's `NoteEvent` is tagless). The C-11
    internal drum-provenance tags (voice names + `ornament`) are stripped first,
    so the mechanism does not false-positive; a stray/typo tag surviving the
    strip is not in `{ghost, push, fill, crash, var, hold}` and fires."""
    violations: list[str] = []
    for phrase in trace.phrases_stage7:
        for note in phrase.notes:
            stray = [
                tag for tag in strip_internal(note.tags) if tag not in _OUTPUT_TAGS
            ]
            if stray:
                violations.append(
                    f"W6: track '{phrase.track_id}' note at ticks={note.ticks} "
                    f"carries non-output tag(s) {stray}; allowed "
                    f"{sorted(_OUTPUT_TAGS)}"
                )
    return violations


# --- W8: humanizer note-count preservation ------------------------------------


def _check_w8_note_counts(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Per-`track_id` note counts are identical between stage 6 and stage 7.

    The PHASE_6 D1 humanizer contract: stage 7 only adjusts ticks / durations /
    velocities, never adds or removes a note."""
    violations: list[str] = []

    def counts(phrases: list[Phrase]) -> dict[str, int]:
        acc: dict[str, int] = defaultdict(int)
        for phrase in phrases:
            acc[phrase.track_id] += len(phrase.notes)
        return dict(acc)

    stage6 = counts(trace.phrases_stage6)
    stage7 = counts(trace.phrases_stage7)
    for track_id in sorted(set(stage6) | set(stage7)):
        c6 = stage6.get(track_id, 0)
        c7 = stage7.get(track_id, 0)
        if c6 != c7:
            violations.append(
                f"W8: track '{track_id}' note count changed stage6->stage7 "
                f"({c6} -> {c7}); humanize must preserve counts"
            )
    return violations


# --- W2: device-policy compliance ---------------------------------------------


def _check_w2_device_policy(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Rendered stage-6 devices are legal for each entered section type (§3.2).

    Per §4 decision 2 this is a *policy-consistency evidence* check, not a
    per-boundary RNG re-derivation (fill-vs-stop and phrase-fill inclusion are
    draws, so the exact device fired is not statically knowable). It asserts the
    devices that ARE present are legal for the entered section type:

      * a `"crash"`-tagged event only lands on a legal entered downbeat — a
        section-boundary downbeat whose entered type is not a suppression class.
        Suppression classes (`postchorus`, `breakdown`) therefore carry no entry
        crash, and a crash mid-section (or at a suppressed boundary) fires.
      * a `"fill"`-tagged event only lands in a fill bar — the last bar of an
        outgoing section (a section boundary whose entered type is not a
        suppression class) or the bar before an interior phrase start. A
        suppressed boundary's last bar is not a legal fill bar, mirroring the
        crash rule above. (`stop` deletes rather than tags, so a rendered stop
        window contributes no fill tags to check against.)
      * a `breakdown` entry shows the §3.5 dropout truncation: no note sustains
        across the entered downbeat.

    `"crash"` here is unambiguously the §3.9 output tag: groove/fill generation
    skips the `crash` voice entirely (generators §6.1 / devices §3.3), so the
    only `"crash"`-tagged stage-6 notes are the §3.7 entry crash+kick. The HOLD
    final crash is tagged `"hold"`, not `"crash"`. `breakdown`/`postchorus` are
    produced by no v1 reference form, so those branches are exercised only by a
    synthetic fixture."""
    violations: list[str] = []
    sections = trace.song_form.sections

    legal_crash_ticks: set[int] = set()
    legal_fill_bars: set[int] = set()
    breakdown_ticks: list[int] = []
    for outgoing, entered in zip(sections, sections[1:], strict=False):
        entered_tick = entered.start_bar * _TICKS_PER_BAR
        if entered.type not in _SUPPRESSION_TYPES:
            legal_fill_bars.add(outgoing.start_bar + outgoing.length_bars - 1)
            legal_crash_ticks.add(entered_tick)
        if entered.type == "breakdown":
            breakdown_ticks.append(entered_tick)
    for section in sections:  # interior phrase-boundary fill bars (§3.1).
        bar = section.start_bar
        for idx, section_phrase in enumerate(section.phrases):
            if idx > 0:
                legal_fill_bars.add(bar - 1)
            bar += section_phrase.bars

    for phrase in trace.phrases_stage6:
        for note in phrase.notes:
            if "crash" in note.tags and note.ticks not in legal_crash_ticks:
                violations.append(
                    f"W2: track '{phrase.track_id}' has a 'crash'-tagged event at "
                    f"ticks={note.ticks} that is not a legal entered downbeat "
                    f"(no non-suppression section boundary enters there)"
                )
            if (
                "fill" in note.tags
                and note.ticks // _TICKS_PER_BAR not in legal_fill_bars
            ):
                violations.append(
                    f"W2: track '{phrase.track_id}' has a 'fill'-tagged event at "
                    f"ticks={note.ticks} (bar {note.ticks // _TICKS_PER_BAR}) "
                    f"outside any fill bar"
                )

    for entered_tick in breakdown_ticks:
        for phrase in trace.phrases_stage6:
            for note in phrase.notes:
                if note.ticks < entered_tick < note.ticks + note.duration_ticks:
                    violations.append(
                        f"W2: breakdown entry at ticks={entered_tick}: track "
                        f"'{phrase.track_id}' note at ticks={note.ticks} sustains "
                        f"across it (§3.5 dropout truncation not applied)"
                    )

    return violations


# --- W5: determinism (regenerate from meta) -----------------------------------

# W5 re-runs the whole pipeline, so it roughly doubles render cost. It is wired
# into the roster but gated behind this toggle (default off) — its primary home
# is the C4 smoke matrix, and the per-render suite should not pay for it on every
# call. A caller that wants the determinism guarantee flips this to `True`.
REGENERATE_CHECK_ENABLED: bool = False


def regenerate_matches(doc: TrackDocument) -> bool:
    """Re-render from `doc.meta.params` and compare the contract JSON byte-for-byte.

    `serialize(..., params=raw_params)` echoes the exact `raw_params` (incl. the
    seed) into `meta.params`, so `generate_trace(doc.meta.params)` re-runs the
    identical seeded pipeline; determinism (ROADMAP invariant 5) then guarantees a
    byte-identical `TrackDocument`. Uses only the existing seeded path — no new
    RNG draw, no wall-clock."""
    regenerated = generate_trace(doc.meta.params).document
    return to_json(regenerated) == to_json(doc)


def _check_w5_determinism(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Regenerating from `meta.params` reproduces a byte-identical document.

    Skipped unless `REGENERATE_CHECK_ENABLED` is set (it doubles render cost)."""
    if not REGENERATE_CHECK_ENABLED:
        return []
    if not regenerate_matches(doc):
        return [
            "W5: regenerating from meta.params does not reproduce a byte-identical "
            "document (determinism broken)"
        ]
    return []


# --- W7: pre-humanizer grid legality ------------------------------------------


def _check_w7_grid_legality(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Every pre-humanizer onset lies on the straight or triplet grid (§3.1).

    Reads `phrases_stage6` (the humanizer legitimately moves onsets off-grid via
    swing/jitter, which is why the trace keeps the pre-humanizer snapshot). Per
    §4 decision 3: `pos_in_beat = ticks % 480` must be on the straight grid
    (`{0,120,240,360}`) or the triplet grid (`{0,160,320}`). Mutation/device
    artifacts (`var`/`crash`/`hold` tags) are grid-exempt.

    One-grid-per-pattern homogeneity (§3.1's flam rule) is enforced at the
    per-`Phrase` grouping — a Phrase is one `(section, role)` span. True
    per-source-pattern grouping is lost after tiling/mutation, so per-Phrase is
    the faithful mechanical proxy: a single Phrase's non-exempt onsets must be
    entirely straight OR entirely triplet, never mixed. (`pos 0` is on both grids,
    so it is grid-neutral and never forces a Phrase onto one grid.)"""
    violations: list[str] = []
    for phrase in trace.phrases_stage6:
        has_straight = False
        has_triplet = False
        for note in phrase.notes:
            if any(tag in _GRID_EXEMPT_TAGS for tag in note.tags):
                continue
            pos = note.ticks % _TICKS_PER_BEAT
            on_straight = pos in _STRAIGHT_GRID
            on_triplet = pos in _TRIPLET_GRID
            if not on_straight and not on_triplet:
                violations.append(
                    f"W7: track '{phrase.track_id}' onset at ticks={note.ticks} "
                    f"(pos_in_beat={pos}) is on neither the straight grid "
                    f"{sorted(_STRAIGHT_GRID)} nor the triplet grid "
                    f"{sorted(_TRIPLET_GRID)}"
                )
            elif on_straight and not on_triplet:
                has_straight = True
            elif on_triplet and not on_straight:
                has_triplet = True
        if has_straight and has_triplet:
            violations.append(
                f"W7: track '{phrase.track_id}' mixes straight-grid and "
                f"triplet-grid onsets within one Phrase (§3.1 one-grid-per-pattern)"
            )
    return violations


# --- aggregator ---------------------------------------------------------------

# The check roster. Each check has the `(doc, trace) -> list[str]` shape, so the
# aggregator needs no per-check special-casing. W5 is gated internally by
# `REGENERATE_CHECK_ENABLED` (default off) — see `_check_w5_determinism`.
_LAYER1_CHECKS: list[Callable[[TrackDocument, GenerationTrace], list[str]]] = [
    _check_w1_lane_compliance,
    _check_w2_device_policy,
    _check_w3_ending_integrity,
    _check_w4_density_gate,
    _check_w5_determinism,
    _check_w6_tag_vocabulary,
    _check_w7_grid_legality,
    _check_w8_note_counts,
]


def layer1_checks(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Run every Layer-1 check, returning the concatenated violation messages."""
    violations: list[str] = []
    for check in _LAYER1_CHECKS:
        violations.extend(check(doc, trace))
    return violations
