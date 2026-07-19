"""The validator-suite entry point (PHASE_8 §8.1; SESSION_16 §2).

`validate_pipeline(doc, trace)` **subsumes** the document validator: it calls the
frozen `schema/validate.py::validate_document(doc)` (V1-V8) and appends the
pipeline-aware Layer-1 (W-) and Layer-2 (L2-) checks. It does not reimplement
V1-V8. The result is the concatenation of every layer's messages (empty ==
valid); order is V* then W* then L2*.
"""

from __future__ import annotations

from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality.layer1 import layer1_checks
from trackgen.quality.layer2 import layer2_checks
from trackgen.schema.document import TrackDocument
from trackgen.schema.validate import validate_document


def validate_pipeline(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Return every suite violation for `(doc, trace)`; empty list == valid."""
    violations: list[str] = []
    violations.extend(validate_document(doc))
    violations.extend(layer1_checks(doc, trace))
    violations.extend(layer2_checks(doc, trace))
    return violations
