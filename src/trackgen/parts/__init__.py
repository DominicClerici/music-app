"""Part-generation foundations (PHASE_5 §3.3-§3.5).

Chunk 1 lands the cross-cutting pure transforms the four part generators
(Chunk 3) compose: degree retargeting (§3.3), velocity/articulation (§3.4), and
density gating (§3.5). No randomness, no clock (ROADMAP invariant 5).
"""

from trackgen.parts.dynamics import (
    apply_articulation,
    apply_velocity,
    articulation_scales,
    is_event_active,
)
from trackgen.parts.generators import generate
from trackgen.parts.retarget import RetargetedNote, resolve_degree_pc, retarget_event
from trackgen.parts.selection import (
    SelectionKey,
    SelectionResult,
    section_kind,
    select_patterns,
)
from trackgen.parts.voicing import build_voicing_map
from trackgen.parts.walker import WalkNote, walk

__all__ = [
    "RetargetedNote",
    "SelectionKey",
    "SelectionResult",
    "WalkNote",
    "apply_articulation",
    "apply_velocity",
    "articulation_scales",
    "build_voicing_map",
    "generate",
    "is_event_active",
    "resolve_degree_pc",
    "retarget_event",
    "section_kind",
    "select_patterns",
    "walk",
]
