"""Pipeline stage wiring (PHASE_5 §8, PHASE_7 §7)."""

from trackgen.pipeline.orchestrator import generate_track
from trackgen.pipeline.serialize import serialize, to_json

__all__ = [
    "generate_track",
    "serialize",
    "to_json",
]
