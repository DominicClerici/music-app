"""Pipeline stage wiring (PHASE_5 §8). Chunk 4 adds the orchestrator/serializer."""

from trackgen.pipeline.serialize import serialize, to_json
from trackgen.pipeline.stubs import TrackSound, humanize, sound_design, transitions

__all__ = [
    "TrackSound",
    "humanize",
    "serialize",
    "sound_design",
    "to_json",
    "transitions",
]
