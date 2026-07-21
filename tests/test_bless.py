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
import os
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
    _VERSION_SOURCE,
    _VERSION_SYMBOL,
    BlessResult,
    RebuiltSelectionError,
    baseline_metrics,
    bless,
    cell_id,
    encode_trace,
    format_result,
    is_downgrade,
    note_affecting,
    read_baseline,
    trace_from_stages,
    version_key,
)
from trackgen.tooling.blessdiff import CellDiff, NoteDelta

_CELLS = corpus.corpus_cells()

# One pop_rock and one jazz cell for the synthetic half — both packs, cheapest
# length. The committed half covers all 36.
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


def _rename_first_section(cell: corpus.Cell, root: Path) -> tuple[str, str]:
    """Rename the baseline's first `FormSection.id`, leaving the document alone.

    The real S18-8 shape the `note_affecting` conjunction exists for: `songform`
    diverges, `document.json` stays byte-identical, and every note in the renamed
    span is re-attributed to a different bucket. Returns `(old_id, new_id)`.
    """
    path = corpus.cell_dir(cell, root=root) / "songform.json"
    form = json.loads(path.read_text(encoding="utf-8"))
    old = str(form["sections"][0]["id"])
    new = f"{old.rsplit('-', 1)[0]}-9"
    form["sections"][0]["id"] = new
    path.write_text(json.dumps(form, separators=(",", ":")) + "\n", encoding="utf-8")
    return old, new


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
    # One cell of 36 is a scoped run, so the diff report is followed by the
    # scope notice; the verdict itself is still the single clean line.
    assert format_result(result).splitlines()[0] == (
        "bless report — 1 cell(s), no divergence."
    )


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


def test_note_affecting_requires_the_document_stage_not_just_notes() -> None:
    """`note_affecting` is a conjunction; this pins the `document` conjunct.

    `test_mix_only_change_is_not_note_affecting` covers the other side — notes
    empty on a diverged document — but it is satisfied by a mutant that drops the
    stage test entirely (`return bool(diff.notes)`), because `notes == ()` is
    falsey either way. Only a diff with notes attributed and **no** document
    divergence discriminates.
    """
    notes = (NoteDelta("bass", "verse-1", added=27, removed=27, moved=0, changed=0),)
    attribution_only = CellDiff(
        cell_id="c",
        first_stage="songform",
        diverged_stages=("songform",),
        notes=notes,
    )
    real_note_change = CellDiff(
        cell_id="c",
        first_stage="document",
        diverged_stages=("document",),
        notes=notes,
    )

    assert not note_affecting(attribution_only)
    assert note_affecting(real_note_change)


def test_section_rename_is_approvable_without_a_version_bump(tmp_path: Path) -> None:
    """End-to-end proof of the same conjunct, through the real pipeline.

    A `songform` section rename re-attributes untouched notes: `document.json` is
    byte-identical, so no music changed and §8.2's version-bump price does not
    apply. A guard keyed on `bool(diff.notes)` alone would refuse this — blocking
    a legitimate bless behind a bump that records nothing.
    """
    _write_baseline(_POP_CELL, tmp_path)
    old, new = _rename_first_section(_POP_CELL, tmp_path)
    assert old != new

    diff = bless(cells=[_POP_CELL], root=tmp_path).diffs[0]

    assert diff.diverged_stages == ("songform",), (
        "the document must stay identical for this case to mean anything"
    )
    assert sum(d.total for d in diff.notes) > 0, "notes must actually be attributed"
    assert diff.stage_errors == ()
    assert not note_affecting(diff)

    approved = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert approved.refusal is None
    assert approved.written == (cell_id(_POP_CELL),)


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
    assert "src/trackgen/pipeline/serialize.py" in report
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


# --- a baseline stamped NEWER than this build (the other side of S18-8) ------
#
# S18-8's literal pin tests equality, so `baseline != fresh` passes — including
# when the baseline is *ahead* of the code (a rollback, a branch merge, a
# reverted bless commit). Left alone, the guard fails open on a note-affecting
# change AND the rewrite stamps the older version over the newer one, destroying
# the only evidence the corpus was ever ahead.


@pytest.mark.parametrize(
    ("baseline", "fresh", "expected"),
    [
        ("0.1.0", "0.1.0", False),
        ("0.0.9", "0.1.0", False),
        ("0.1.0", "0.0.9", True),
        # Numeric, not lexicographic: "0.10.0" > "0.9.0" although "1" < "9".
        ("0.10.0", "0.9.0", True),
        ("0.9.0", "0.10.0", False),
        # An unreadable side has its own refusal and is never a downgrade.
        (None, "0.1.0", False),
        ("0.1.0", None, False),
        (None, None, False),
    ],
)
def test_is_downgrade_compares_versions_numerically(
    baseline: str | None, fresh: str | None, expected: bool
) -> None:
    assert is_downgrade(baseline, fresh) is expected


def test_version_key_orders_double_digit_components_correctly() -> None:
    """The string compare this key exists to replace gets these backwards."""
    assert version_key("0.10.0") > version_key("0.9.0")
    assert version_key("1.0.0") > version_key("0.99.99")
    # Total on any string: a hand-edited baseline must never raise here.
    assert version_key("nonsense") > version_key("0.1.0")


def test_approve_refused_when_the_baseline_version_is_newer(tmp_path: Path) -> None:
    """A newer baseline + a note change must refuse, not fail open (fail closed)."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note, version="9.9.9")
    document = corpus.cell_dir(_POP_CELL, root=tmp_path) / "document.json"
    before = document.read_text(encoding="utf-8")

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is not None, (
        "a newer baseline satisfies `!=`, so the equality-only check waves it "
        "through — the divergence must still be refused"
    )
    assert "NEWER" in result.refusal
    assert "9.9.9" in result.refusal
    assert cell_id(_POP_CELL) in result.refusal
    assert result.written == () and result.refreshed == ()
    assert document.read_text(encoding="utf-8") == before
    assert (
        json.loads(document.read_text(encoding="utf-8"))["meta"]["generatorVersion"]
        == "9.9.9"
    ), "the newer stamp must not be downgraded"

    assert "REFUSED --approve" in format_result(result, approve=True)


def test_a_clean_cell_with_a_newer_stamp_is_not_downgraded(tmp_path: Path) -> None:
    """The version-stamp refresh must not quietly walk a stamp backwards either.

    No note moved here, so no S18-8 candidate exists at all — the downgrade would
    come from the refresh path, which rewrites `document.json` on any version
    mismatch in either direction.
    """
    _write_baseline(_POP_CELL, tmp_path, version="9.9.9")
    before = _snapshot(tmp_path)

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is not None
    assert "NEWER" in result.refusal
    assert result.refreshed == ()
    assert _snapshot(tmp_path) == before


def test_an_older_baseline_still_blesses_normally(tmp_path: Path) -> None:
    """Non-regression: the downgrade check must only fire in one direction."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note, version="0.0.9")

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)

    assert result.refusal is None
    assert result.written == (cell_id(_POP_CELL),)


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


# --- the version-stamp refresh (a bump must leave the corpus reproducible) ----
#
# `meta.generatorVersion` is excluded from the semantic diff (S18-8) but IS
# written into every cell's `document.json`. A bump therefore changes all 36
# cells' bytes while `bless` reports only the cells that moved musically, and
# blessing just those leaves the corpus on mixed stamps — provably not
# byte-reproducible while the tool says it is fine. These tests pin the
# write-side fix: the report stays clean, the corpus still gets restamped.

# A fixed, deterministic mtime (no wall-clock — ROADMAP invariant 5). Used to
# prove *which* files a run rewrote, since a refreshed IR stage would be
# byte-identical and so invisible to a content compare.
_PINNED_MTIME_NS = 1_000_000_000 * 1_000_000_000


def _pin_mtimes(cell: corpus.Cell, root: Path) -> None:
    for path in corpus.cell_dir(cell, root=root).glob("*.json"):
        os.utime(path, ns=(_PINNED_MTIME_NS, _PINNED_MTIME_NS))


def _rewritten_files(cell: corpus.Cell, root: Path) -> set[str]:
    """Names of the cell's stage files whose pinned mtime no longer holds."""
    return {
        path.name
        for path in corpus.cell_dir(cell, root=root).glob("*.json")
        if path.stat().st_mtime_ns != _PINNED_MTIME_NS
    }


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.json"))
    }


def _assert_byte_reproducible(cell: corpus.Cell, root: Path) -> None:
    """Every committed byte of `cell` equals what a fresh render would write."""
    trace = corpus.render_cell(cell)
    directory = corpus.cell_dir(cell, root=root)
    for stage in corpus.STAGES:
        committed = (directory / f"{stage}.json").read_text(encoding="utf-8")
        assert committed == corpus.encode_stage(trace, stage), (
            f"{cell_id(cell)}: {stage}.json is not byte-reproducible"
        )


def test_version_only_change_still_reports_clean(tmp_path: Path) -> None:
    """The exclusion stays: a pure bump must not flood the report (S18-8)."""
    for cell in (_POP_CELL, _JAZZ_CELL):
        _write_baseline(cell, tmp_path, version="0.0.9")

    result = bless(cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.ok
    assert result.divergent == ()
    assert format_result(result).splitlines()[0] == (
        "bless report — 2 cell(s), no divergence."
    )


def test_plain_run_with_a_stale_version_writes_nothing(tmp_path: Path) -> None:
    """The refresh is an `--approve`-only act; a plain run stays read-only."""
    for cell in (_POP_CELL, _JAZZ_CELL):
        _write_baseline(cell, tmp_path, version="0.0.9")
    before = _snapshot(tmp_path)

    result = bless(cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.written == ()
    assert _snapshot(tmp_path) == before
    assert result.refreshed == ()


def test_approve_refreshes_every_stale_version_stamp(tmp_path: Path) -> None:
    """The rehearsal's gap: a bump must not leave the corpus on mixed stamps."""
    for cell in (_POP_CELL, _JAZZ_CELL):
        _write_baseline(cell, tmp_path, version="0.0.9")
        _pin_mtimes(cell, tmp_path)

    result = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.refusal is None
    assert result.written == (), "no cell diverged semantically"

    for cell in (_POP_CELL, _JAZZ_CELL):
        # The property the corpus exists for — asserted first, so the unfixed
        # behavior fails on the corpus itself, not on a missing attribute.
        _assert_byte_reproducible(cell, tmp_path)
        # Minimal write: the nine IR stages carry no version and stay untouched.
        assert _rewritten_files(cell, tmp_path) == {"document.json"}
        document = json.loads(
            (corpus.cell_dir(cell, root=tmp_path) / "document.json").read_text(
                encoding="utf-8"
            )
        )
        assert document["meta"]["generatorVersion"] != "0.0.9"

    assert result.refreshed == (cell_id(_POP_CELL), cell_id(_JAZZ_CELL))

    # And the run is now idempotent: nothing left to refresh.
    again = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)
    assert again.written == () and again.refreshed == ()


def test_refresh_verdict_names_its_reason(tmp_path: Path) -> None:
    """A human must see why 2 cells moved when 0 changed musically."""
    for cell in (_POP_CELL, _JAZZ_CELL):
        _write_baseline(cell, tmp_path, version="0.0.9")

    result = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)
    report = format_result(result, approve=True)

    assert "version-stamp refresh: 2 cell(s)" in report
    assert "document.json only" in report
    assert "excluded from the semantic diff" in report
    assert "blessed" not in report, "nothing changed musically"
    assert "nothing to bless" not in report
    assert cell_id(_POP_CELL) in report and cell_id(_JAZZ_CELL) in report
    assert result.generator_version is not None
    assert result.generator_version in report


def test_mixed_semantic_change_and_version_bump(tmp_path: Path) -> None:
    """The real rehearsal shape: some cells moved musically, all moved stamps."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note, version="0.0.9")
    _write_baseline(_JAZZ_CELL, tmp_path, version="0.0.9")
    for cell in (_POP_CELL, _JAZZ_CELL):
        _pin_mtimes(cell, tmp_path)

    result = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.refusal is None
    assert result.written == (cell_id(_POP_CELL),)
    for cell in (_POP_CELL, _JAZZ_CELL):
        _assert_byte_reproducible(cell, tmp_path)
    # The diverging cell is rewritten in full; the clean one, document only.
    assert _rewritten_files(_POP_CELL, tmp_path) == {
        f"{stage}.json" for stage in corpus.STAGES
    }
    assert _rewritten_files(_JAZZ_CELL, tmp_path) == {"document.json"}
    assert result.refreshed == (cell_id(_JAZZ_CELL),)

    report = format_result(result, approve=True)
    assert "blessed 1 cell(s)" in report
    assert "version-stamp refresh: 1 cell(s)" in report


def test_refusal_still_blocks_the_version_refresh(tmp_path: Path) -> None:
    """S18-8 keeps precedence: a refused run writes nothing at all."""
    # pop moves notes at an UNCHANGED version -> refusal; jazz is merely stale.
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note)
    _write_baseline(_JAZZ_CELL, tmp_path, version="0.0.9")
    before = _snapshot(tmp_path)

    result = bless(approve=True, cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.refusal is not None
    assert result.written == ()
    assert _snapshot(tmp_path) == before
    assert result.refreshed == ()


# --- scoped runs (`--pack`) ---------------------------------------------------
#
# The refresh above only iterates the *selected* runs, so after a bump
# `bless --approve --pack pop_rock` restamps 12 cells and leaves the other 24
# byte-non-reproducible — while `bless --pack pop_rock` keeps reporting "no
# divergence" about the slice it looked at. `--pack` exists for exactly the
# pack-at-a-time workflow that hits this, so the report has to say so.


def test_bless_records_how_much_of_the_corpus_it_covered(tmp_path: Path) -> None:
    result = bless(cells=[_POP_CELL, _JAZZ_CELL], root=tmp_path)

    assert result.selected_count == 2
    assert result.corpus_count == len(_CELLS)
    assert result.unselected_count == len(_CELLS) - 2
    assert result.scoped


def test_scoped_run_names_itself_with_exact_counts(tmp_path: Path) -> None:
    """No silent caps (ROADMAP §3): the unselected count is the whole finding."""
    _write_baseline(_POP_CELL, tmp_path)

    report = format_result(bless(cells=[_POP_CELL], root=tmp_path))

    assert f"SCOPED RUN — 1 of {len(_CELLS)} corpus cell(s) selected" in report
    assert f"the other {len(_CELLS) - 1} were NOT re-rendered" in report
    assert "unscoped `trackgen bless --approve`" in report


def test_scoped_approve_warns_the_rest_of_the_corpus_is_left_stale(
    tmp_path: Path,
) -> None:
    """The live C5 risk: a scoped restamp that silently leaves 23 cells behind."""
    _write_baseline(_POP_CELL, tmp_path, version="0.0.9")

    result = bless(approve=True, cells=[_POP_CELL], root=tmp_path)
    report = format_result(result, approve=True)

    assert result.refreshed == (cell_id(_POP_CELL),)
    assert "version-stamp refresh: 1 cell(s)" in report
    assert f"SCOPED RUN — 1 of {len(_CELLS)}" in report
    assert "stale meta.generatorVersion" in report
    assert "not byte-reproducible" in report


def test_a_refused_scoped_run_still_names_its_scope(tmp_path: Path) -> None:
    """A refusal must not swallow the scope caveat — both findings are real."""
    _write_baseline(_POP_CELL, tmp_path, mutate=_move_first_note)

    report = format_result(
        bless(approve=True, cells=[_POP_CELL], root=tmp_path), approve=True
    )

    assert "REFUSED --approve" in report
    assert "SCOPED RUN" in report


def test_cli_pack_scoped_run_says_it_was_scoped() -> None:
    """Through the real CLI surface, on the committed corpus."""
    result = CliRunner().invoke(app, ["bless", "--pack", "pop_rock"])

    assert result.exit_code == 0, result.stdout
    assert "SCOPED RUN — 12 of 36 corpus cell(s) selected" in result.stdout
    assert "the other 24 were NOT re-rendered" in result.stdout


# --- the `_VERSION_SOURCE` reference (must not rot) ---------------------------


def test_version_source_points_at_the_real_definition() -> None:
    """The refusal's file reference is resolved, not merely asserted present.

    It is echoed into a message a human is told to act on, so a stale reference
    is a real defect. Carrying no line number is half the fix; the other half is
    this test, which resolves the path against the live module and confirms the
    symbol is actually defined there — so a rename or a move fails here instead
    of misdirecting a reader.
    """
    import importlib
    import inspect

    # `import trackgen.pipeline.serialize as m` would bind the re-exported
    # *function* of that name from the package; this binds the module.
    serialize_module = importlib.import_module("trackgen.pipeline.serialize")

    assert ":" not in _VERSION_SOURCE, "a line number would rot silently"

    source_file = inspect.getsourcefile(serialize_module)
    assert source_file is not None
    assert Path(source_file).as_posix().endswith(_VERSION_SOURCE)

    value = getattr(serialize_module, _VERSION_SYMBOL, None)
    assert isinstance(value, str) and value, (
        f"{_VERSION_SYMBOL} is not defined in {_VERSION_SOURCE}"
    )


def test_bumping_generator_version_procedure_is_documented() -> None:
    """The out-of-scope blast radius a bump causes must be written down.

    `bless` rewrites the golden corpus and nothing else. These artifacts also
    embed the version and no tool here can fix them, so the module docstring
    names them by path rather than letting a bump fail three tests silently.
    """
    import trackgen.tooling.bless as bless_module

    doc = bless_module.__doc__ or ""
    assert "Bumping `generatorVersion`" in doc
    for path in (
        "src/trackgen/pipeline/serialize.py",
        "fixtures/pop_rock.milestone.trackdoc.json",
        "fixtures/jazz.milestone.trackdoc.json",
        "fixtures/milestone.trackdoc.json",
        "tests/test_whole_document_goldens.py::test_fixture_reserializes_identically",
        "tests/test_serialize.py::test_meta_seed_and_params",
    ):
        assert path in doc, path


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
    """Non-vacuity: 36 cells × 10 stages actually on disk (ROADMAP §3)."""
    assert len(_CELLS) == 36
    assert len({cell_id(c) for c in _CELLS}) == 36
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
    # An unscoped run covers the whole corpus, so no scope notice is appended
    # and the whole report really is the one clean line.
    assert not result.scoped
    assert result.selected_count == result.corpus_count == len(_CELLS)
    assert format_result(result) == "bless report — 36 cell(s), no divergence."


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
