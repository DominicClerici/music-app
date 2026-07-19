"""Layer 2 — musical rule checks (PHASE_8 §8.1). STUB.

Task T3 fills this in with L2-1 (chord-tone-on-strong-beat ratio, fail below
threshold) and L2-2 (voice crossing, warn), plus the thin `calibration.yaml`
threshold read-hook (engine defaults 0.95 / 0.98 until a pack's `calibration.yaml`
exists in C3). The stub exists now so `suite.py::validate_pipeline` can import
and compose it without a later edit to the suite.
"""

from __future__ import annotations

from trackgen.pipeline.trace import GenerationTrace
from trackgen.schema.document import TrackDocument


def layer2_checks(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Return Layer-2 violation messages. STUB (T3 fills in): currently `[]`."""
    return []
