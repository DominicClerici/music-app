"""Tests for the bless workflow (PHASE_8 §8.2 / D11; SESSION_18 T3).

Two halves. The **synthetic** half writes a deliberately mutated baseline into
`tmp_path` and blesses a real render against it, so every divergence class is
exercised without touching the committed corpus. The **committed** half proves
`fixtures/goldens/` actually round-trips: every stage file re-reads, re-renders,
and compares equal, and a whole-corpus `bless()` is clean.

The mutation is applied to the *baseline* rather than to the engine on purpose:
the fresh side then goes through the untouched production chain, so a test that
passes proves the real pipeline output was compared, not a stubbed one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality.layer3 import compute_metrics
from trackgen.tooling import corpus
from trackgen.tooling.bless import (
    _MAX_WRITTEN_ROWS,
    BlessResult,
    RebuiltSelectionError,
    baseline_metrics,
    bless,
    cell_id,
    encode_trace,
    format_result,
    note_affecting,
    read_baseline,
    trace_from_stages,
)

_CELLS = corpus.corpus_cells()

# One pop_rock and one jazz cell for the synthetic half — both packs, cheapest
# length. The committed half covers all 24.
_POP_CELL = next(c for c in _CELLS if c.pack == "pop_rock" and c.length_sec == 120)
_JAZZ_CELL = next(c for c in _CELLS if c.pack == "jazz" and c.length_sec == 120)


def _write_baseline(
    cell: corpus.Cell,
    root: Path,
    *,
    mutate: Any = None,
    version: str | None = None,
) -> GenerationTrace:
    """Capture `cell` into `root`, optionally mutating its `document.json`.

    `mutate` receives the parsed document and edits it in place; `version`
    overrides `meta.generatorVersion`. Returns the (unmutated) trace so a test
    can compare against what the pipeline really produced.
    """
    trace = corpus.render_cell(cell)
    corpus.write_cell(trace, cell, root=root)
    if mutate is None and version is None:
        return trace

    path = corpus.cell_dir(cell, root=root) / "document.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(document)
    if version is not None:
        document["meta"]["generatorVersion"] = version
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return trace


def _move_first_note(document: dict[str, Any]) -> None:
    """Shift one note by an 8th — inside S18-6's move tolerance."""
    track = next(t for t in document["tracks"] if t.get("notes"))
    track["notes"][0]["ticks"] += 120


def _nudge_mix(document: dict[str, Any]) -> None:
    """Change a channel level: a real document divergence that moves no note."""
    document["tracks"][0]["channel"]["volumeDb"] -= 1.0


def _move_note_and_drop_version(document: dict[str, Any]) -> None:
    """A note-affecting baseline whose `meta.generatorVersion` is unreadable."""
    _move_first_note(document)
    del document["meta"]["generatorVersion"]


# --- first capture ------------------------------------------------------------


def test_first_capture_is_not_a_divergence(tmp_path: Path) -> None:
    """§8.2 — no baseline on disk is a capture, never something to review."""
    result = bless(cells=[_POP_CELL], root=tmp_path)
    assert result.first_captures and not result.divergent
    assert result.ok
    assert "first capture" in format_result(result)


def test_bless_without_approve_writes_nothing(tmp_path: Path) -> None:
    """A plain run is read-only — even the first capture is left uncaptured."""
    bless(cells=[_POP_CELL], root=tmp_path)
    assert list(tmp_path.rglob("*.json")) == []


def test_approve_captures_a_missing_baseline(tmp_path: Path) -> None:
    """First capture is always allowed, whatever the generatorVersion says."""
    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)
    assert result.refusal is None
    assert result.written == (cell_id(_POP_CELL),)
    directory = corpus.cell_dir(_POP_CELL, root=tmp_path)
    written = sorted(p.name for p in directory.iterdir())
    assert written == sorted(f"{stage}.json" for stage in corpus.STAGES)
    # And the freshly captured cell now blesses clean.
    assert bless(cells=[_POP_CELL], root=tmp_path).ok


def test_absent_cell_directory_is_the_only_first_capture(tmp_path: Path) -> None:
    """The pack/mood ancestors may exist; it is the *cell* dir that decides."""
    corpus.cell_dir(_POP_CELL, root=tmp_path).parent.mkdir(parents=True)
    baseline, missing = read_baseline(_POP_CELL, root=tmp_path)
    assert baseline is None and missing == ()

    result = bless(cells=[_POP_CELL], root=tmp_path)
    assert result.first_captures and not result.divergent
    assert result.ok


# --- incomplete baselines (a partial cell is never a first capture) ------------


def _delete_one_stage(cell: corpus.Cell, root: Path, stage: str = "harmony") -> Path:
    """Remove one stage file from an otherwise-complete captured cell."""
    path = corpus.cell_dir(cell, root=root) / f"{stage}.json"
    path.unlink()
    return path


def test_partial_baseline_is_not_read_as_a_first_capture(tmp_path: Path) -> None:
    """`read_cell` cannot tell 9-of-10 from 0-of-10; `read_baseline` must."""
    _write_baseline(_POP_CELL, tmp_path)
    _delete_one_stage(_POP_CELL, tmp_path)

    baseline, missing = read_baseline(_POP_CELL, root=tmp_path)
    assert missing == ("harmony",)
    # The surviving stages still come back, so the diff can still localize.
    assert baseline is not None
    assert set(baseline) == set(corpus.STAGES) - {"harmony"}


def test_plain_bless_over_a_partial_baseline_is_not_ok(tmp_path: Path) -> None:
    """A deleted stage file must not let CI stay green (exit 0) on a shrunk corpus."""
    _write_baseline(_POP_CELL, tmp_path)
    _delete_one_stage(_POP_CELL, tmp_path)

    result = bless(cells=[_POP_CELL], root=tmp_path)

    assert not result.ok, "a missing stage file must not report a clean corpus"
    diff = result.diffs[0]
    assert not diff.missing_baseline
    assert not diff.clean
    assert diff in result.divergent
    assert any("INCOMPLETE BASELINE" in error for error in diff.stage_errors)

    report = format_result(result)
    assert "no divergence" not in report
    assert "no baseline on disk" not in report, "must not read as a first capture"
    assert "harmony.json" in report


def test_partial_baseline_refuses_approve(tmp_path: Path) -> None:
    """The whole point: a corrupted cell is never silently re-blessed."""
    _write_baseline(_POP_CELL, tmp_path)
    deleted = _delete_one_stage(_POP_CELL, tmp_path)
    document = corpus.cell_dir(_POP_CELL, root=tmp_path) / "document.json"
    before = document.read_text(encoding="utf-8")

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is not None
    assert "INCOMPLETE" in result.refusal
    assert cell_id(_POP_CELL) in result.refusal
    assert result.written == ()
    assert not deleted.exists(), "a refused --approve must not re-capture the cell"
    assert document.read_text(encoding="utf-8") == before

    report = format_result(result, approve=True)
    assert "REFUSED --approve" in report


def test_partial_baseline_refuses_even_across_a_clean_batch(tmp_path: Path) -> None:
    """One corrupted cell refuses the run, exactly as one stalled version does."""
    _write_baseline(_POP_CELL, tmp_path)
    _write_baseline(_JAZZ_CELL, tmp_path)
    _delete_one_stage(_JAZZ_CELL, tmp_path, stage="document")

    result = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.refusal is not None
    assert cell_id(_JAZZ_CELL) in result.refusal
    assert result.written == ()


def test_deleting_the_whole_cell_directory_still_re_captures(tmp_path: Path) -> None:
    """The deliberate escape hatch the refusal names actually works."""
    _write_baseline(_POP_CELL, tmp_path)
    directory = corpus.cell_dir(_POP_CELL, root=tmp_path)
    for path in directory.iterdir():
        path.unlink()
    directory.rmdir()

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)
    assert result.refusal is None
    assert result.written == (cell_id(_POP_CELL),)


# --- divergence detection -----------------------------------------------------


@pytest.mark.parametrize("cell", [_POP_CELL, _JAZZ_CELL], ids=["pop_rock", "jazz"])
def test_matching_baseline_is_clean(cell: corpus.Cell, tmp_path: Path) -> None:
    _write_baseline(cell, tmp_path)
    result = bless(cells=[cell], root=tmp_path)
    assert result.ok
    assert result.diffs[0].clean
    assert format_result(result) == "bless report — 1 cell(s), no divergence."


@pytest.mark.parametrize("cell", [_POP_CELL, _JAZZ_CELL], ids=["pop_rock", "jazz"])
def test_note_affecting_change_is_detected(cell: corpus.Cell, tmp_path: Path) -> None:
    """A single 8th-shifted note in the baseline reads as one moved note."""
    _write_baseline(cell, tmp_path, mutate=_move_first_note)
    result = bless(cells=[cell], root=tmp_path)

    assert not result.ok
    diff = result.diffs[0]
    assert diff.first_stage == "document"
    assert diff.diverged_stages == ("document",)
    assert sum(d.moved for d in diff.notes) == 1
    assert sum(d.added + d.removed for d in diff.notes) == 0
    assert note_affecting(diff)

    report = format_result(result)
    assert "FIRST DIVERGENT STAGE: document" in report
    assert "--approve" in report
    assert "{" not in report  # §8.2: never a raw JSON diff


def test_mix_only_change_is_not_note_affecting(tmp_path: Path) -> None:
    """The guard keys on notes, not on any document byte (S18-8)."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_nudge_mix)
    diff = bless(cells=[_POP_CELL], root=tmp_path).diffs[0]
    assert diff.first_stage == "document"
    assert diff.notes == ()
    assert not note_affecting(diff)


def test_metric_deltas_are_reported_on_a_note_change(tmp_path: Path) -> None:
    """§8.2 mandates Layer-3 deltas; the baseline side comes from the adapter."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note)
    diff = bless(cells=[_POP_CELL], root=tmp_path).diffs[0]
    # A shifted onset moves mean IOI without adding or removing a note.
    assert any(delta.metric == "mean_ioi" for delta in diff.metrics)
    assert diff.stage_errors == ()


# --- the S18-8 generatorVersion check ----------------------------------------


def test_approve_refused_at_equal_generator_version(tmp_path: Path) -> None:
    """The DoD-5 mechanism: notes moved, version unchanged -> refuse, write nothing."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note)
    before = (corpus.cell_dir(_POP_CELL, root=tmp_path) / "document.json").read_text(
        encoding="utf-8"
    )

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is not None
    assert result.written == ()
    assert not result.ok
    after = (corpus.cell_dir(_POP_CELL, root=tmp_path) / "document.json").read_text(
        encoding="utf-8"
    )
    assert after == before, "a refused --approve must not rewrite any baseline"

    report = format_result(result, approve=True)
    assert "REFUSED --approve" in report
    assert "src/trackgen/pipeline/serialize.py:38" in report
    assert cell_id(_POP_CELL) in report


def test_approve_accepted_once_generator_version_bumped(tmp_path: Path) -> None:
    """The same divergence blesses once the baseline records an older version."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note, version="0.0.9")

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is None
    assert result.written == (cell_id(_POP_CELL),)
    # The rewritten baseline is now the live render.
    assert bless(cells=[_POP_CELL], root=tmp_path).ok


def test_approve_accepted_for_a_non_note_divergence(tmp_path: Path) -> None:
    """An unchanged version only blocks *note* changes, not mix/synth churn."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_nudge_mix)
    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)
    assert result.refusal is None
    assert result.written == (cell_id(_POP_CELL),)


def test_approve_refused_when_the_baseline_version_is_unreadable(
    tmp_path: Path,
) -> None:
    """A malformed baseline must refuse, not fall through the check (fail closed)."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_note_and_drop_version)

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is not None
    assert "could not be read" in result.refusal
    assert result.written == ()
    document = corpus.cell_dir(_POP_CELL, root=tmp_path) / "document.json"
    assert (
        "generatorVersion"
        not in json.loads(document.read_text(encoding="utf-8"))["meta"]
    ), "a refused --approve must not rewrite the baseline"


def test_unreadable_baseline_is_reported_not_raised(tmp_path: Path) -> None:
    """A baseline that no longer validates is a finding, not a traceback."""

    def _corrupt_without_moving_a_note(document: dict[str, Any]) -> None:
        _nudge_mix(document)
        del document["meta"]["generatorVersion"]

    _write_baseline(_POP_CELL, tmp_path, mutate=_corrupt_without_moving_a_note)

    result = bless(cells=[_POP_CELL], root=tmp_path)
    assert not result.ok
    assert any("UNREADABLE BASELINE" in error for error in result.diffs[0].stage_errors)

    approved = bless(approve=True, cells=[_POP_CELL], root=tmp_path)
    assert approved.refusal is not None
    assert "UNREADABLE" in approved.refusal
    assert approved.written == ()


def test_refusal_covers_a_mixed_batch(tmp_path: Path) -> None:
    """One offending cell refuses the whole run — no partial blessing."""
    _write_baseline(_POP_CELL, tmp_path)
    _write_baseline(_JAZZ_CELL, tmp_path, mutate=_move_first_note)

    result = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.refusal is not None
    assert cell_id(_JAZZ_CELL) in result.refusal
    assert result.written == ()


# --- the Layer-3 baseline adapter --------------------------------------------


def test_trace_from_stages_reproduces_live_metrics() -> None:
    """The adapter's metrics equal the live trace's, on both reference packs."""
    for cell in (_POP_CELL, _JAZZ_CELL):
        trace = corpus.render_cell(cell)
        rebuilt = trace_from_stages(encode_trace(trace))
        assert baseline_metrics(encode_trace(trace)) == compute_metrics(trace)
        assert rebuilt.document == trace.document
        assert rebuilt.harmony == trace.harmony
        assert rebuilt.song_form == trace.song_form


@pytest.mark.parametrize("cell", [_POP_CELL, _JAZZ_CELL], ids=["pop_rock", "jazz"])
@pytest.mark.parametrize("field", ["by_section", "by_key"])
def test_rebuilt_trace_selection_fails_loudly(cell: corpus.Cell, field: str) -> None:
    """S18-5's absent `selection` must announce itself, never read as empty.

    An empty `SelectionResult` makes `quality.layer1`'s W4 check pass with zero
    violations and no error — a silently disarmed validator. Reading the field
    raises instead.
    """
    rebuilt = trace_from_stages(encode_trace(corpus.render_cell(cell)))
    with pytest.raises(RebuiltSelectionError) as excinfo:
        getattr(rebuilt.selection, field)
    message = str(excinfo.value)
    assert "METRICS-ONLY" in message
    assert "run_layer1" in message
    # Repr must not itself detonate — it is read by pytest and by any logging.
    assert "corpus-rebuilt" in repr(rebuilt.selection)


def test_rebuilt_trace_w4_style_lookup_raises() -> None:
    """The exact access shape `layer1.py` uses (`by_section.get(...)`) raises."""
    rebuilt = trace_from_stages(encode_trace(corpus.render_cell(_POP_CELL)))
    with pytest.raises(RebuiltSelectionError):
        rebuilt.selection.by_section.get(("verse-1", "drums"))


# --- surface ------------------------------------------------------------------


def test_cell_id_matches_the_on_disk_path() -> None:
    for cell in _CELLS:
        assert cell_id(cell) == str(
            corpus.cell_dir(cell, root=Path(".")).relative_to(Path("."))
        )


def test_result_properties_partition_the_diffs(tmp_path: Path) -> None:
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note)
    result = bless(cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)
    assert len(result.diffs) == 2
    assert len(result.divergent) == 1
    assert len(result.first_captures) == 1
    assert isinstance(result, BlessResult)


# --- the committed corpus -----------------------------------------------------


@pytest.mark.parametrize("cell", _CELLS, ids=cell_id)
def test_committed_cell_round_trips(cell: corpus.Cell) -> None:
    """Every committed file parses and equals a fresh render, stage by stage."""
    baseline = corpus.read_cell(cell)
    fresh = encode_trace(corpus.render_cell(cell))
    assert set(baseline) == set(corpus.STAGES)
    for stage in corpus.STAGES:
        assert baseline[stage] == fresh[stage], f"{cell_id(cell)}: {stage} diverged"


def test_committed_corpus_is_complete() -> None:
    """Non-vacuity: 24 cells × 10 stages actually on disk (ROADMAP §3)."""
    assert len(_CELLS) == 24
    assert len({cell_id(c) for c in _CELLS}) == 24
    for cell in _CELLS:
        directory = corpus.cell_dir(cell)
        assert directory.is_dir(), directory
        assert sorted(p.name for p in directory.glob("*.json")) == sorted(
            f"{stage}.json" for stage in corpus.STAGES
        )


def test_bless_on_the_committed_corpus_is_clean() -> None:
    """The DoD claim: the whole committed corpus blesses with no divergence."""
    result = bless()
    assert result.ok
    assert result.first_captures == ()
    assert format_result(result) == "bless report — 24 cell(s), no divergence."


def test_cli_bless_exits_zero_on_the_committed_corpus() -> None:
    result = CliRunner().invoke(app, ["bless"])
    assert result.exit_code == 0, result.stdout
    assert "no divergence" in result.stdout


@pytest.mark.parametrize("pack", ["pop_rock", "jazz"])
def test_cli_bless_pack_filter_scopes_the_run(pack: str) -> None:
    """`--pack` blesses one pack's cells only (C5 ergonomics)."""
    expected = sum(1 for cell in _CELLS if cell.pack == pack)
    result = CliRunner().invoke(app, ["bless", "--pack", pack])
    assert result.exit_code == 0, result.stdout
    assert f"{expected} cell(s), no divergence" in result.stdout
    assert expected < len(_CELLS)


def test_cli_bless_rejects_an_unknown_pack() -> None:
    result = CliRunner().invoke(app, ["bless", "--pack", "no_such_pack"])
    assert result.exit_code != 0
    assert "unknown corpus pack" in result.output


def test_written_list_is_not_elided_for_a_full_corpus() -> None:
    """N3 — a whole-corpus approve must list every cell it rewrote."""
    assert _MAX_WRITTEN_ROWS >= len(_CELLS)
    result = BlessResult(diffs=(), written=tuple(cell_id(c) for c in _CELLS))
    report = format_result(result, approve=True)
    assert "more" not in report
    for cell in _CELLS:
        assert cell_id(cell) in report
