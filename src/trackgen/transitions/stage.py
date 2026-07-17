"""Stage 6 entry point — the Transition engine (PHASE_6 §3).

`transitions(phrases, form, chords, arr, plan, pack)` runs the three sub-passes
in pinned order: **6a ending HOLD → 6b boundary devices → 6c mutation**. 6a
settles the final bars first; 6b places fills/stops/dropouts/crashes at the
boundary taxonomy; 6c (Task T3, stubbed here) applies anti-repetition mutation.
Stage 6 owns all note-structural change; frozen `Phrase`s are rebuilt, never
mutated (§2 / SESSION_10 §2.1).
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
from trackgen.transitions._common import BAR, to_builders, to_phrases
from trackgen.transitions.devices import apply_devices
from trackgen.transitions.ending import find_t_last, hold_ending
from trackgen.transitions.mutation import mutate


def transitions(
    phrases: list[Phrase],
    form: SongForm,
    chords: HarmonicPlan,
    arr: ArrangementPlan,
    plan: GenerationPlan,
    pack: StylePack,
) -> list[Phrase]:
    """Transform `phrases` through stage 6 (§3), returning a new `Phrase` list."""
    if pack.transitions is None:
        raise ValueError("pack has no transitions spec (stage 6 requires it)")

    t_last = find_t_last(chords)
    builders = to_builders(phrases)

    hold_ending(builders, form, chords, plan, pack, t_last)  # 6a
    apply_devices(builders, form, arr, plan, pack, t_last // BAR)  # 6b

    result = to_phrases(builders)
    return mutate(result, form, chords, arr, plan, pack)  # 6c hook (T3)
