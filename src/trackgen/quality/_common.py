"""Shared read-only helpers for the validator suite (PHASE_8 §8.1; SESSION_16 §3).

Every helper is a pure function over the `GenerationTrace` / IR fields — no RNG,
no wall-clock (TID251 enforces the import layer). The verified field names come
straight from `schema/ir.py`; where the SESSION_16 handoff sketch differed
(e.g. `registers[(id, role)]`), the real IR shape wins and is noted inline.
"""

from __future__ import annotations

from collections.abc import Callable

from trackgen.parts.generators import _VOICE_TRACK
from trackgen.pipeline.trace import GenerationTrace
from trackgen.schema.document import Role
from trackgen.schema.ir import ArrangementEntry, ChordEvent, FormSection

# PHASE_1: PPQ 480, 4/4 — one bar is 1920 ticks. v1 packs are 4/4 only.
_TICKS_PER_BAR = 1920


def entry_index(
    trace: GenerationTrace,
) -> dict[tuple[str, Role], ArrangementEntry]:
    """Index `trace.arrangement.entries` by `(section_id, role)`.

    The IR stores a flat list (`ArrangementPlan.entries`), not a keyed dict, so
    the index is built here. Each `ArrangementEntry` carries `section_id`,
    `role`, `active`, `intensity`, `density_budget`, and `register`
    (`Register.{low_midi, high_midi}`)."""
    return {
        (entry.section_id, entry.role): entry for entry in trace.arrangement.entries
    }


def sections_by_id(trace: GenerationTrace) -> dict[str, FormSection]:
    """Index `trace.song_form.sections` by `FormSection.id`.

    Uses the form sections (whose `id` matches `ArrangementEntry.section_id`),
    never `doc.sections` (which carry a display `label`, no matching `id`)."""
    return {section.id: section for section in trace.song_form.sections}


def section_span(section: FormSection) -> tuple[int, int]:
    """The `[start_tick, end_tick)` tick span of a form section (4/4, 1920/bar)."""
    start = section.start_bar * _TICKS_PER_BAR
    return start, start + section.length_bars * _TICKS_PER_BAR


def tick_to_section(
    trace: GenerationTrace,
) -> Callable[[int], FormSection | None]:
    """Return a mapper from a tick to its containing `FormSection` (or `None`).

    Spans are `[start_bar*1920, (start_bar+length_bars)*1920)` over
    `trace.song_form.sections`. The returned closure captures the (small) span
    table so a caller can map many ticks without rebuilding it."""
    spans = [(*section_span(section), section) for section in trace.song_form.sections]

    def finder(tick: int) -> FormSection | None:
        for start, end, section in spans:
            if start <= tick < end:
                return section
        return None

    return finder


def governing_chord(trace: GenerationTrace, tick: int) -> ChordEvent | None:
    """The `ChordEvent` in `trace.harmony.chords` whose span contains `tick`.

    A chord governs `[start_tick, start_tick + duration_ticks)`. Returns `None`
    if no event covers the tick. (Used by Layer-2's chord-tone checks; provided
    here as a shared §3 helper.)"""
    for chord in trace.harmony.chords:
        if chord.start_tick <= tick < chord.start_tick + chord.duration_ticks:
            return chord
    return None


# C-11: drum `PhraseNote`s carry internal provenance tags — the source drum
# *voice* name plus `"ornament"` for `minDensity`-gated events — that the
# serializer drops (they never reach the `TrackDocument`). They are NOT the §3.9
# contributed output tags, so the W6 output-vocabulary check strips them first.
# The voice names are single-sourced from `_VOICE_TRACK` (no drift-prone copy).
# `"crash"` is deliberately EXCLUDED: it is both a drum voice AND a pinned §3.9
# output tag, so it must survive `strip_internal` to be checked as an output tag.
INTERNAL_TAGS: frozenset[str] = (frozenset(_VOICE_TRACK) - {"crash"}) | {"ornament"}


def strip_internal(tags: list[str]) -> list[str]:
    """Drop the C-11 internal drum-provenance tags, keeping order + output tags."""
    return [tag for tag in tags if tag not in INTERNAL_TAGS]
