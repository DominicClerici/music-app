"""The three-layer quality / evaluation validator suite (PHASE_8 §8.1).

`quality/` reads the C1 `GenerationTrace` (every IR boundary) and its final
`TrackDocument`. It is a one-directional consumer: it imports
`validate_document`, `GenerationTrace`, the IR structs, and a few `parts`
helpers, and nothing under `schema/`/`pipeline/`/`parts/` imports it back.

The suite entry point is `validate_pipeline(doc, trace)` (see `suite.py`), which
subsumes the document validator by *calling* it and appending the pipeline-aware
Layer-1 and Layer-2 fail checks. Soft, non-gating warnings (Layer-2 L2-2) are
surfaced separately by `pipeline_warnings(doc, trace)`.
"""

from trackgen.quality.suite import pipeline_warnings, validate_pipeline

__all__ = ["pipeline_warnings", "validate_pipeline"]
