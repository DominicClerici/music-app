"""The pipeline orchestrator (PHASE_5 §8.1, SESSION_09 T3).

`generate_track(raw_params)` wires the nine pipeline stages end to end and
returns a serialized `TrackDocument`. It follows the authoritative code chain
(SESSION_09 "Authoritative wiring facts" — the §8.1 pseudocode is stale): the
same interpret -> form -> harmony -> arrange -> select_patterns -> generate x4
loop the test-only `_drive_full` driver uses, then the real stages
transitions -> humanize (Phase 6) -> sound_design (Phase 7) -> serialize.

The stage chain lives in `trace.generate_trace`, which retains every IR
boundary; `generate_track` delegates to it and returns only the final document.
The orchestrator itself makes **no** RNG draws: `generate_plan` is the entropy
boundary (it derives the master seed), and every downstream stage receives its
seed material explicitly. No `random`/wall-clock import here (invariant 5).
"""

from trackgen.pipeline.trace import generate_trace
from trackgen.schema.document import TrackDocument


def generate_track(raw_params: dict[str, object]) -> TrackDocument:
    """Run the full pipeline for `raw_params` and return a `TrackDocument`.

    `raw_params` is the public client dict (camelCase keys, `styleFamily`
    required). It is threaded verbatim into `meta.params` (round-trip
    reproducibility, DoD 9), so an emitted document can be regenerated from
    its own metadata.
    """
    return generate_trace(raw_params).document
