"""The validator-suite entry point (PHASE_8 §8.1; SESSION_16 §2, §4).

The suite separates **gating failures** from **soft warnings** (PHASE_8 §8.1:
Layer 2 is "warn by default, fail where marked"):

- `validate_pipeline(doc, trace)` returns only the **hard failures** that gate a
  render as invalid — the frozen document validator (V1-V8), Layer-1 (W1-W8), and
  Layer-2's fail-marked check (L2-1). Empty == valid; this is the gate used by
  CI/smoke.
- `pipeline_warnings(doc, trace)` returns the **soft, non-gating warnings** —
  Layer-2's warn-marked check (L2-2). A warning must NOT make a render invalid, so
  it is reported separately and never folded into `validate_pipeline`.

Layer 3 (statistical style bands) is batch-only / warn-only and stays out of this
per-render path entirely.

`validate_pipeline` **subsumes** the document validator: it calls the frozen
`schema/validate.py::validate_document(doc)` (V1-V8) and appends the
pipeline-aware Layer-1 (W-) and Layer-2 fail (L2-1) checks. It does not
reimplement V1-V8. Order is V* then W* then L2-1.
"""

from __future__ import annotations

from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality.layer1 import layer1_checks
from trackgen.quality.layer2 import layer2_failures, layer2_warnings
from trackgen.schema.document import TrackDocument
from trackgen.schema.validate import validate_document


def validate_pipeline(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Return every **gating** suite failure for `(doc, trace)`; empty == valid.

    Hard failures only: V1-V8 + W1-W8 + L2-1. Soft warnings (L2-2) are excluded —
    see `pipeline_warnings`."""
    violations: list[str] = []
    violations.extend(validate_document(doc))
    violations.extend(layer1_checks(doc, trace))
    violations.extend(layer2_failures(doc, trace))
    return violations


def pipeline_warnings(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Return the **non-gating** soft warnings for `(doc, trace)` (L2-2).

    Warnings never make a render invalid; they are surfaced separately from the
    `validate_pipeline` gate. Layer 3 is batch-only and is not included here."""
    return layer2_warnings(doc, trace)
