"""6c — anti-repetition mutation (PHASE_6 §3.7 mutation / §3.8 mutate stream).

STUB (Task T2): identity. Task T3 replaces `mutate` with the five
constructive-safe operators drawn per 2-bar drum / 8-bar comping unit on
per-unit sub-streams. The hook exists here so `stage.py` wires 6a → 6b → 6c in
pinned order with no further change when T3 lands.
"""

from __future__ import annotations

from trackgen.packs.models import StylePack
from trackgen.schema.ir import (
    ArrangementPlan,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    SongForm,
)


def mutate(
    phrases: list[Phrase],
    form: SongForm,
    chords: HarmonicPlan,
    arr: ArrangementPlan,
    plan: GenerationPlan,
    pack: StylePack,
) -> list[Phrase]:
    """STUB (T3): identity. Real 6c mutates 2-bar drum / 8-bar comping units."""
    return phrases
