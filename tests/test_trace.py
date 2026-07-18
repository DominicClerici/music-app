"""Trace orchestrator tests (PHASE_8 §8.2/§9.3, SESSION_15 T1).

`generate_trace` must expose every IR boundary while leaving `generate_track`
byte-identical: the production entry point delegates to `generate_trace(...).
document`, so these tests pin both the delegation (byte-identity) and the shape
of the captured boundaries — chiefly that the three phrase snapshots (post-5,
post-6, post-7) are separable, and that stage 7 preserves the stage-6 per-track
note counts (the PHASE_6 D1 humanizer contract, now assertable end to end).

Param dicts are copied from tests/test_pipeline_determinism.py (there is no
`tests` package to cross-import — the codebase convention is to copy)."""

from __future__ import annotations

import pytest

from trackgen.parts.selection import SelectionResult
from trackgen.pipeline import GenerationTrace, generate_trace, generate_track
from trackgen.pipeline.serialize import to_json
from trackgen.schema.document import TrackDocument
from trackgen.schema.ir import (
    ArrangementPlan,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    SongForm,
)
from trackgen.sound.stage import SoundDesign

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_trace_document_byte_identical_to_generate_track(
    params: dict[str, object],
) -> None:
    """`generate_trace(p).document` serializes byte-for-byte identically to
    `generate_track(p)` — the delegation is behavior-preserving."""
    assert to_json(generate_trace(params).document) == to_json(generate_track(params))


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_trace_fields_present_and_typed(params: dict[str, object]) -> None:
    """Every boundary field is present and of its stage-output type."""
    trace = generate_trace(params)
    assert isinstance(trace, GenerationTrace)
    assert isinstance(trace.plan, GenerationPlan)
    assert isinstance(trace.song_form, SongForm)
    assert isinstance(trace.harmony, HarmonicPlan)
    assert isinstance(trace.arrangement, ArrangementPlan)
    assert isinstance(trace.selection, SelectionResult)
    assert isinstance(trace.phrases_stage5, list)
    assert isinstance(trace.phrases_stage6, list)
    assert isinstance(trace.phrases_stage7, list)
    assert all(isinstance(p, Phrase) for p in trace.phrases_stage5)
    assert all(isinstance(p, Phrase) for p in trace.phrases_stage6)
    assert all(isinstance(p, Phrase) for p in trace.phrases_stage7)
    assert isinstance(trace.sound_design, SoundDesign)
    assert isinstance(trace.document, TrackDocument)


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_phrase_snapshots_are_distinct_lists(params: dict[str, object]) -> None:
    """The three snapshots are separate list objects — no in-place reuse across
    stages 5 -> 6 -> 7."""
    trace = generate_trace(params)
    assert trace.phrases_stage5 is not trace.phrases_stage6
    assert trace.phrases_stage6 is not trace.phrases_stage7
    assert trace.phrases_stage5 is not trace.phrases_stage7


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_stage6_differs_from_stage5(params: dict[str, object]) -> None:
    """Transitions (stage 6) mutate the generated phrases, so the post-6 snapshot
    is not a copy of the post-5 one."""
    trace = generate_trace(params)
    stage5 = [p.model_dump() for p in trace.phrases_stage5]
    stage6 = [p.model_dump() for p in trace.phrases_stage6]
    assert stage5 != stage6


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_humanize_preserves_note_counts(params: dict[str, object]) -> None:
    """PHASE_6 D1 — humanize (stage 7) is note-count preserving: every track's
    note count is unchanged from stage 6, now assertable end to end."""
    trace = generate_trace(params)
    stage6_counts = {p.track_id: len(p.notes) for p in trace.phrases_stage6}
    stage7_counts = {p.track_id: len(p.notes) for p in trace.phrases_stage7}
    assert stage7_counts == stage6_counts


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_generate_trace_is_deterministic(params: dict[str, object]) -> None:
    """Two runs on identical params yield equal documents (no new entropy)."""
    assert to_json(generate_trace(params).document) == to_json(
        generate_trace(params).document
    )
