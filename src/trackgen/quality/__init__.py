"""The three-layer quality / evaluation validator suite (PHASE_8 §8.1).

`quality/` reads the C1 `GenerationTrace` (every IR boundary) and its final
`TrackDocument`. It is a one-directional consumer: it imports
`validate_document`, `GenerationTrace`, the IR structs, and a few `parts`
helpers, and nothing under `schema/`/`pipeline/`/`parts/` imports it back.

The suite entry point is `validate_pipeline(doc, trace)` (see `suite.py`), which
subsumes the document validator by *calling* it and appending the pipeline-aware
Layer-1 (and, later, Layer-2) checks.
"""

from trackgen.quality.suite import validate_pipeline

__all__ = ["validate_pipeline"]
