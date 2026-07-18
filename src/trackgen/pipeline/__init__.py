"""Pipeline stage wiring (PHASE_5 §8, PHASE_7 §7)."""

from trackgen.pipeline.orchestrator import generate_track
from trackgen.pipeline.serialize import serialize, to_json
from trackgen.pipeline.trace import GenerationTrace, generate_trace

__all__ = [
    "GenerationTrace",
    "generate_trace",
    "generate_track",
    "serialize",
    "to_json",
]
