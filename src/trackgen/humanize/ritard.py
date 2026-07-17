"""Ritard tempo-curve renderer (PHASE_6 §5.7, D15).

The Friberg-Sundberg kinematic final-ritard model, sampled over the final
section's tag region into stepped `header.tempos` events. Fully deterministic —
pure position-domain math, no RNG or clock (§5.8: deterministic sub-passes
consume nothing).

    v(x) = (1 + (v_end**3 - 1) * x) ** (1/3)   x in [0, 1] over the tag, q = 3

Only `ending.close == "ritard"` emits events; `cold`/`fade` (the D7 alias) emit
none. Ticks are absolute (tag-start + rel); the Serializer prepends the tick-0
base tempo.
"""

from __future__ import annotations

from trackgen.schema.document import Tempo
from trackgen.schema.ir import GenerationPlan, SongForm

BAR = 1920

_V_END = 0.65
_CUBE = 1.0 / 3.0
_PER_8TH = 240
_PER_16TH = 120


def _v(x: float) -> float:
    """The §5.7 braking curve, normalized so v(0) = 1 and v(1) = v_end."""
    return float((1.0 + (_V_END**3 - 1.0) * x) ** _CUBE)


def _sample_rels(tag_length: int) -> list[int]:
    """Relative sample ticks: per-8th across every bar but the final tag bar,
    then per-16th across the final bar — density biased where the curve steepens
    (§5.7). The release downbeat `rel == tag_length` is never sampled."""
    final_bar_start = tag_length - BAR
    rels = list(range(0, final_bar_start, _PER_8TH))
    rels += range(final_bar_start, tag_length, _PER_16TH)
    return rels


def ritard_curve(tag_start: int, tag_length: int, base_bpm: float) -> list[Tempo]:
    """Render the ritard curve over a tag geometry (primitive form).

    Samples the curve (§5.7), rounds bpm to 0.1, and drops any sample equal to
    the prevailing tempo (starting from the tick-0 base) or to its predecessor.
    Returns absolute-tick `Tempo` events, ascending.
    """
    prevailing = round(base_bpm, 1)
    events: list[Tempo] = []
    for rel in _sample_rels(tag_length):
        bpm = round(base_bpm * _v(rel / tag_length), 1)
        if bpm == prevailing:
            continue
        events.append(Tempo(ticks=tag_start + rel, bpm=bpm))
        prevailing = bpm
    return events


def ritard_events(form: SongForm, plan: GenerationPlan) -> list[Tempo]:
    """The §5.7 renderer keyed off the final section's ending.

    Emits events only for a `ritard` close; empty form, no ending, or a
    `cold`/`fade` close returns `[]`.
    """
    if not form.sections:
        return []
    final = form.sections[-1]
    ending = final.ending
    if ending is None or ending.close != "ritard":
        return []

    tag_bars = ending.tag_bars if ending.tag_bars > 0 else 1
    end_tick = (final.start_bar + final.length_bars) * BAR
    tag_length = tag_bars * BAR
    tag_start = end_tick - tag_length
    return ritard_curve(tag_start, tag_length, plan.tempo_bpm)
