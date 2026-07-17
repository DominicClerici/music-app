"""Pipeline stage wiring (PHASE_5 §8). Chunk 4 adds the orchestrator/serializer."""

from trackgen.pipeline.orchestrator import generate_track
from trackgen.pipeline.serialize import serialize, to_json
from trackgen.pipeline.stubs import TrackSound, humanize, sound_design, transitions

__all__ = [
    "TrackSound",
    "generate_track",
    "humanize",
    "serialize",
    "sound_design",
    "to_json",
    "transitions",
]
