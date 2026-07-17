"""Tick-domain swing repositioning (PHASE_6 §5.2).

Swing is a *proportional* effect, so it lives in the tick domain and scales
through the tempo map automatically (D9). It displaces offbeat-subdivision
events only — downbeats never move — and applies a gap-preserving duration
stretch so a note that filled up to a repositioned neighbour stays connected
and a repositioned note that filled up to the next grid point keeps that end
(the swung short note).

This pass is deterministic: it consumes no RNG (§5.8).
"""

from __future__ import annotations

from dataclasses import dataclass

from trackgen.schema.ir import PhraseNote, SwingSpec

# The offbeat modulus/remainder and the swing grid step per subdivision:
#   swing8:  offbeats sit at beat+240 (`tick % 480 == 240`); grid step 480.
#   swing16: offbeats sit at k*240+120 (`tick % 240 == 120`); grid step 240.
_SUBDIV: dict[str, tuple[int, int]] = {"8": (480, 240), "16": (240, 120)}

_ABUT_GAP = 10


@dataclass
class _SwingNote:
    orig_start: int
    orig_end: int
    is_off: bool
    new_start: int
    new_dur: int


def swing_phrase(
    notes: list[PhraseNote], swing: SwingSpec | None
) -> list[tuple[int, int]]:
    """Return the `(new_start, new_dur)` for each note under `swing`.

    Straight packs (`swing is None`) are a no-op — every note keeps its grid
    position and authored duration.
    """
    if swing is None:
        return [(n.ticks, n.duration_ticks) for n in notes]

    off_mod, off_rem = _SUBDIV[swing.subdivision]
    displacement = round(off_mod * swing.ratio)

    recs: list[_SwingNote] = []
    for n in notes:
        is_off = n.ticks % off_mod == off_rem
        new_start = (n.ticks - off_rem) + displacement if is_off else n.ticks
        recs.append(
            _SwingNote(
                orig_start=n.ticks,
                orig_end=n.ticks + n.duration_ticks,
                is_off=is_off,
                new_start=new_start,
                new_dur=n.duration_ticks,
            )
        )

    repositioned = [r for r in recs if r.is_off and r.new_start != r.orig_start]

    # Stretch any note whose original end abutted a repositioned note's original
    # start, so the connection to the delayed offbeat is preserved.
    for r in recs:
        for moved in repositioned:
            if moved is r:
                continue
            gap = moved.orig_start - r.orig_end
            if 0 <= gap <= _ABUT_GAP:
                r.new_dur = moved.new_start - r.new_start
                break

    # A repositioned note that abutted the next grid point keeps that end; its
    # start moved later, so its duration shrinks (the swung short note).
    for moved in repositioned:
        next_grid = moved.orig_start + off_rem
        gap = next_grid - moved.orig_end
        if 0 <= gap <= _ABUT_GAP:
            moved.new_dur = moved.orig_end - moved.new_start

    return [(r.new_start, r.new_dur) for r in recs]
