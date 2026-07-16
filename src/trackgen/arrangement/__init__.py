"""The Arrangement stage (PHASE_5 §3.1, §4).

Chunk 1 lands only the engine-owned intensity threshold table (§3.1); the
`arrange()` planner (§4) is Chunk 2.
"""

from trackgen.arrangement.intensity import intensity

__all__ = ["intensity"]
