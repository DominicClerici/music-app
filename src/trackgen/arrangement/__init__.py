"""The Arrangement stage (PHASE_5 §3.1, §4).

`intensity()` is the §3.1 energy->rung ladder (Chunk 1); `arrange()` is the §4
planner (Chunk 2).
"""

from trackgen.arrangement.arrange import arrange
from trackgen.arrangement.intensity import intensity

__all__ = ["arrange", "intensity"]
