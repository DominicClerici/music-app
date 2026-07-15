"""The Interpreter — pipeline stage 1 (PHASE_2).

Turns validated params into a `GenerationPlan`. This module currently
exports the mood model (PHASE_2 §4); a sibling task adds `params`/`stage`
and will extend these exports.
"""

from trackgen.interpreter.moods import (
    DERIVED_KEYS,
    MODE_LADDER,
    MOOD_VOCABULARY,
    MoodLoadError,
    MoodRow,
    MoodTable,
    apply_overrides,
    clamp01,
    derived_defaults,
    formulas,
    load_moods,
)

__all__ = [
    "DERIVED_KEYS",
    "MODE_LADDER",
    "MOOD_VOCABULARY",
    "MoodLoadError",
    "MoodRow",
    "MoodTable",
    "apply_overrides",
    "clamp01",
    "derived_defaults",
    "formulas",
    "load_moods",
]
