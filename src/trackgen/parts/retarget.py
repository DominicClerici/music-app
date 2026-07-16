"""Degree -> pitch retargeting (PHASE_5 §3.3).

Where pitch first appears in the pipeline (ROADMAP invariant 2): patterns author
degrees + chord-hits, never literal pitches; this module resolves a pattern
event against its governing `ChordEvent` into concrete MIDI notes. Pure and
deterministic -- no randomness, no clock (ROADMAP invariant 5). All chord/scale
math reuses the committed `trackgen.theory` helpers.

Public surface (what Chunk 3's generators call):

- `resolve_degree_pc(degree, chord_event, role, next_chord_event)` -> the pitch
  class (0-11) a single degree resolves to, with the §3.3 dressing-safe
  fallbacks. Raises for `degree == "chord"` (voiced, not a single pc).
- `retarget_event(...)` -> the list of `RetargetedNote`s one pattern event
  produces, handling `push`, octave placement + lane folding, and
  `onChordChange` splitting. `degree == "chord"` events emit the voicing the
  Chunk-3 voicing pass supplies via the `voicing_for` hook.

The voicing pass itself (§6.4/§6.5) is Chunk 3; here `voicing_for` is only a
`ChordEvent -> [midi]` callback the caller injects, so a `chord`-degree (or a
pushed chord) event emits that chord's pre-computed voicing notes unchanged
(placement/anchor rules do not apply to `chord`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import NamedTuple

from trackgen.packs.models import Degree
from trackgen.schema.document import Role
from trackgen.schema.ir import ChordEvent, ChordSpec, Register
from trackgen.theory import (
    EXTENSION_OFFSETS,
    QUALITY_INTERVALS,
    guide_tones,
    scale_pcs,
)

# §3.3 retrigger: a re-resolved remainder shorter than this is inaudible and
# dropped. Applied to every produced segment (the interpretation is documented
# in the T3 report as a candidate CAVEAT).
_MIN_REMAINDER_TICKS = 60

# Qualities that carry a genuine 7th chord tone (interval slot index 3 is the
# seventh). maj6/min6 also have a 4th tone at index 3, but it is the 6th, not a
# seventh -- handled explicitly in `_seventh_pc`.
_SEVENTH_QUALITIES = frozenset(
    {"dom7", "maj7", "min7", "minMaj7", "min7b5", "dim7", "dom7sus4"}
)
_SIXTH_QUALITIES = frozenset({"maj6", "min6"})

# The Voicing hook: given the chord governing a hit, return its pre-computed
# voicing as MIDI pitches (the Chunk-3 voicing pass, §6.4/§6.5). Only consulted
# for `degree == "chord"` events.
VoicingFor = Callable[[ChordEvent], Sequence[int]]


class RetargetedNote(NamedTuple):
    """One concrete note a pattern event resolves to, before §3.4 dynamics.

    A single-degree event yields one note per attack segment; a `chord`-degree
    event yields one per voicing pitch (same `ticks`/`duration_ticks`). The
    caller assembles these into `PhraseNote`s, applying authored velocity via
    §3.4 and merging any generator tags with `tags`.
    """

    ticks: int
    duration_ticks: int
    midi: int
    tags: tuple[str, ...]


# --- degree -> pitch class ----------------------------------------------------


def _root_pc(chord: ChordSpec, role: Role) -> int:
    """§3.3 `root`: the bass role honors a slash `bassPc` (Yamaha NTT-Bass);
    every other role roots on `rootPc`."""
    if role == "bass" and chord.bass_pc is not None:
        return chord.bass_pc
    return chord.root_pc


def _third_pc(chord: ChordSpec) -> int:
    """The quality's third slot -- the 2nd interval of the §8.1 stack
    (sus2 -> 2nd, sus4 -> 4th)."""
    return (chord.root_pc + QUALITY_INTERVALS[chord.quality][1]) % 12


def _fifth_pc(chord: ChordSpec) -> int:
    """The quality's fifth (dim -> b5, aug -> #5) -- interval slot index 2."""
    return (chord.root_pc + QUALITY_INTERVALS[chord.quality][2]) % 12


def _sixth_pc(chord: ChordSpec, scale_root: int, scale_name: str) -> int:
    """§3.3 `sixth`: the 6th chord tone (maj6/min6); fallback the chord-scale's
    6th degree."""
    if chord.quality in _SIXTH_QUALITIES:
        return (chord.root_pc + QUALITY_INTERVALS[chord.quality][3]) % 12
    return scale_pcs(scale_root, scale_name)[5]


def _seventh_pc(chord: ChordSpec) -> int:
    """§3.3 `seventh`: the 7th chord tone; fallback maj6/min6 -> the 6th,
    triads -> the fifth."""
    if chord.quality in _SEVENTH_QUALITIES:
        return (chord.root_pc + QUALITY_INTERVALS[chord.quality][3]) % 12
    if chord.quality in _SIXTH_QUALITIES:
        return (chord.root_pc + QUALITY_INTERVALS[chord.quality][3]) % 12  # the 6th
    return _fifth_pc(chord)


def _guide3_pc(chord: ChordSpec) -> int:
    """§3.3 `guide3`: `guide_tones().third`; when the quality has no third
    (suspended chords) fall back to the third slot (the suspension tone) -- the
    dressing-safe reading (documented as a candidate CAVEAT)."""
    third = guide_tones(chord).third
    if third is not None:
        return third
    return _third_pc(chord)


def _guide7_pc(chord: ChordSpec) -> int:
    """§3.3 `guide7`: `guide_tones().seventh`; fallback triads -> the fifth
    (extended to every quality lacking a seventh guide tone, incl. 6th chords)."""
    seventh = guide_tones(chord).seventh
    if seventh is not None:
        return seventh
    return _fifth_pc(chord)


def _tension_pc(chord: ChordSpec, scale_root: int, scale_name: str) -> int:
    """§3.3 `tension`: the first `extensions` entry (§8.1 offset); fallback the
    chord-scale's 2nd degree (the scale-correct 9th)."""
    if chord.extensions:
        return (chord.root_pc + EXTENSION_OFFSETS[chord.extensions[0]]) % 12
    return scale_pcs(scale_root, scale_name)[1]


def resolve_degree_pc(
    degree: Degree,
    chord_event: ChordEvent,
    role: Role,
    next_chord_event: ChordEvent | None = None,
) -> int:
    """The pitch class (0-11) a single degree resolves to against `chord_event`.

    Implements the §3.3 degree table with its dressing-safe fallback column.
    `next_chord_event` is required for `approach` (chromatic half-step below the
    next event's effective root); at song end (`None`) `approach` falls back to
    the governing chord's `root`. Raises for `degree == "chord"`, which is voiced
    (multiple pitches) and handled by `retarget_event` via the voicing hook.
    """
    chord = chord_event.chord
    scale_root = chord_event.scale.root_pc
    scale_name = chord_event.scale.name

    if degree == "root":
        return _root_pc(chord, role)
    if degree == "third":
        return _third_pc(chord)
    if degree == "fifth":
        return _fifth_pc(chord)
    if degree == "sixth":
        return _sixth_pc(chord, scale_root, scale_name)
    if degree == "seventh":
        return _seventh_pc(chord)
    if degree == "guide3":
        return _guide3_pc(chord)
    if degree == "guide7":
        return _guide7_pc(chord)
    if degree == "tension":
        return _tension_pc(chord, scale_root, scale_name)
    if degree == "approach":
        if next_chord_event is None:
            return _root_pc(chord, role)
        return (_root_pc(next_chord_event.chord, role) - 1) % 12
    raise ValueError(
        f"degree {degree!r} is not a single-pitch degree; `chord` is voiced and "
        f"resolved via retarget_event's voicing hook"
    )


# --- octave placement + lane folding ------------------------------------------


def _anchor(pattern_register: Register, lane: Register) -> float:
    """§3.3 anchor: the midpoint of (pattern `retarget` register n role lane);
    the lane alone when the two are disjoint."""
    lo = max(pattern_register.low_midi, lane.low_midi)
    hi = min(pattern_register.high_midi, lane.high_midi)
    if lo > hi:
        lo, hi = lane.low_midi, lane.high_midi
    return (lo + hi) / 2


def _octave_at(pc: int, anchor: float) -> int:
    """The unique MIDI value = `pc` (mod 12) in the half-open window
    `(anchor - 6, anchor + 6]`."""
    return pc + 12 * int((anchor + 6 - pc) // 12)


def _fold_into_lane(midi: int, lane: Register) -> int:
    """§3.3 lane folding: transpose `midi` by whole octaves to the nearest
    in-lane position, ties resolving downward (the Yamaha note-limit rule).
    Lanes span >= 12, so an in-lane octave always exists."""
    low, high = lane.low_midi, lane.high_midi
    candidates = [midi + 12 * k for k in range(-12, 13) if low <= midi + 12 * k <= high]
    return min(candidates, key=lambda p: (abs(p - midi), p))


def _place_pc(pc: int, anchor: float, octave: int, lane: Register) -> int:
    """Place a pitch class: nearest octave to `anchor`, shift by `12 * octave`
    (the event's authored offset), then fold into the lane."""
    midi = _octave_at(pc, anchor) + 12 * octave
    return _fold_into_lane(midi, lane)


def _place_degree(
    degree: Degree,
    octave: int,
    chord_event: ChordEvent,
    next_chord_event: ChordEvent | None,
    role: Role,
    lane: Register,
    pattern_register: Register,
) -> int:
    """Resolve a single degree to a concrete in-lane MIDI pitch (§3.3)."""
    lane_anchor = _anchor(pattern_register, lane)
    if degree == "approach" and next_chord_event is not None:
        # Anchored on the next root's own placement, not the lane midpoint.
        target_pc = _root_pc(next_chord_event.chord, role)
        target_midi = _place_pc(target_pc, lane_anchor, 0, lane)
        approach_pc = (target_pc - 1) % 12
        return _place_pc(approach_pc, float(target_midi), octave, lane)
    pc = resolve_degree_pc(degree, chord_event, role, next_chord_event)
    return _place_pc(pc, lane_anchor, octave, lane)


# --- governing-chord + boundary bookkeeping -----------------------------------


def _governing_index(chords: Sequence[ChordEvent], tick: int) -> int:
    """Index of the chord whose span contains `tick` -- the last event whose
    `start_tick <= tick` (assumes `chords` sorted by `start_tick`)."""
    idx = 0
    for i, chord in enumerate(chords):
        if chord.start_tick <= tick:
            idx = i
        else:
            break
    return idx


def _boundaries_in_span(
    chords: Sequence[ChordEvent], start: int, end: int
) -> list[int]:
    """Chord-event `start_tick`s in the half-open span `(start, end]`, ascending
    -- the boundaries a note attacked at `start` for `end - start` ticks crosses."""
    return [c.start_tick for c in chords if start < c.start_tick <= end]


# --- the public retarget entry point ------------------------------------------


def retarget_event(
    *,
    degree: Degree,
    octave: int,
    push: bool,
    ticks: int,
    duration_ticks: int,
    chords: Sequence[ChordEvent],
    role: Role,
    lane: Register,
    pattern_register: Register,
    on_chord_change: str,
    voicing_for: VoicingFor | None = None,
) -> list[RetargetedNote]:
    """Resolve one pitched pattern event to concrete `RetargetedNote`s (§3.3).

    Args (absolute-tick, already tiled by the caller):
      degree/octave/push: the authored event fields.
      ticks/duration_ticks: the event's absolute placement and length.
      chords: the full chord timeline (sorted by `start_tick`).
      role: the pitched role (`bass`/`comping`/`pads`); governs the `root`
        bass-slash rule.
      lane: the role's arrangement register lane.
      pattern_register: the pattern's `retarget` register (for the anchor).
      on_chord_change: `hold` | `retrigger` | `stop` -- applied to an un-pushed
        note whose span crosses a chord boundary.
      voicing_for: the Chunk-3 voicing-pass hook; required only when `degree`
        is `chord` (or a pushed chord). Returns the segment chord's voicing MIDI.

    Semantics:
      - `push`: resolves against the chord in effect immediately after the first
        boundary within `(ticks, ticks + durationTicks]` (else against the
        governing chord); the whole note sounds that chord, tagged `"push"`. No
        `onChordChange` split (an anticipation states one chord).
      - un-pushed with no boundary in span: one note against the governing chord.
      - `hold`: one note, full duration, resolved at the attack (governing) chord.
      - `stop`: one note truncated at the first boundary.
      - `retrigger`: split at every boundary; each piece re-resolved against its
        own chord; pieces shorter than 60 ticks are dropped.
      - `chord` degree: emits the segment chord's voicing (one note per pitch),
        placement/anchor rules skipped.
    """
    end = ticks + duration_ticks
    governing = chords[_governing_index(chords, ticks)]
    boundaries = _boundaries_in_span(chords, ticks, end)

    if push:
        # Anticipation: sound the chord after the first in-span boundary (or the
        # governing chord if none), for the whole note. Always tagged "push".
        effective = (
            chords[_governing_index(chords, boundaries[0])] if boundaries else governing
        )
        return _emit_segment(
            degree=degree,
            octave=octave,
            seg_start=ticks,
            seg_end=end,
            chord_event=effective,
            next_chord_event=_next_chord(chords, effective),
            role=role,
            lane=lane,
            pattern_register=pattern_register,
            voicing_for=voicing_for,
            extra_tags=("push",),
        )

    if not boundaries or on_chord_change == "hold":
        # Ring the attack chord across any boundary (hold), or no boundary at all.
        return _emit_segment(
            degree=degree,
            octave=octave,
            seg_start=ticks,
            seg_end=end,
            chord_event=governing,
            next_chord_event=_next_chord(chords, governing),
            role=role,
            lane=lane,
            pattern_register=pattern_register,
            voicing_for=voicing_for,
            extra_tags=(),
        )

    if on_chord_change == "stop":
        # Truncate at the first boundary.
        return _emit_segment(
            degree=degree,
            octave=octave,
            seg_start=ticks,
            seg_end=boundaries[0],
            chord_event=governing,
            next_chord_event=_next_chord(chords, governing),
            role=role,
            lane=lane,
            pattern_register=pattern_register,
            voicing_for=voicing_for,
            extra_tags=(),
        )

    # retrigger: split at every boundary, re-resolve each piece against its chord.
    notes: list[RetargetedNote] = []
    seg_starts = [ticks, *boundaries]
    seg_ends = [*boundaries, end]
    for seg_start, seg_end in zip(seg_starts, seg_ends, strict=True):
        if seg_end - seg_start < _MIN_REMAINDER_TICKS:
            continue
        seg_chord = chords[_governing_index(chords, seg_start)]
        notes.extend(
            _emit_segment(
                degree=degree,
                octave=octave,
                seg_start=seg_start,
                seg_end=seg_end,
                chord_event=seg_chord,
                next_chord_event=_next_chord(chords, seg_chord),
                role=role,
                lane=lane,
                pattern_register=pattern_register,
                voicing_for=voicing_for,
                extra_tags=(),
            )
        )
    return notes


def _next_chord(
    chords: Sequence[ChordEvent], chord_event: ChordEvent
) -> ChordEvent | None:
    """The chord event immediately after `chord_event` in the timeline, or
    `None` at song end (used for `approach` targets)."""
    for i, chord in enumerate(chords):
        if chord is chord_event:
            return chords[i + 1] if i + 1 < len(chords) else None
    idx = _governing_index(chords, chord_event.start_tick)
    return chords[idx + 1] if idx + 1 < len(chords) else None


def _emit_segment(
    *,
    degree: Degree,
    octave: int,
    seg_start: int,
    seg_end: int,
    chord_event: ChordEvent,
    next_chord_event: ChordEvent | None,
    role: Role,
    lane: Register,
    pattern_register: Register,
    voicing_for: VoicingFor | None,
    extra_tags: tuple[str, ...],
) -> list[RetargetedNote]:
    """Resolve one already-split segment against a single chord."""
    duration = seg_end - seg_start
    if degree == "chord":
        if voicing_for is None:
            raise ValueError(
                "degree 'chord' requires a voicing_for hook (the Chunk-3 voicing pass)"
            )
        return [
            RetargetedNote(seg_start, duration, midi, extra_tags)
            for midi in voicing_for(chord_event)
        ]
    midi = _place_degree(
        degree,
        octave,
        chord_event,
        next_chord_event,
        role,
        lane,
        pattern_register,
    )
    return [RetargetedNote(seg_start, duration, midi, extra_tags)]
