"""Bless workflow (PHASE_8 §8.2 / D11) — re-render the corpus, diff, capture.

The third leg of the golden workflow: `corpus` owns the cell matrix and the
on-disk encoding, `blessdiff` owns the semantic report, and this module runs
them against the committed baselines. `bless()` re-renders every cell, diffs it,
and (only under `--approve`) rewrites the baselines.

**§8.2 pins exactly two legal moves on a divergence**: fix the code, or
`bless --approve` in a dedicated commit. This module enforces the second one's
price — the `generatorVersion`-bump check (S18-8). If any cell shows a
*note-affecting* divergence while the committed baseline's
`meta.generatorVersion` still equals the freshly-rendered one, `--approve` is
**refused**: blessing changed music without recording that the generator moved
is precisely the rubber-stamp the workflow exists to prevent. A non-note-affecting
divergence (a mix level, a synth parameter) is approvable at an unchanged
version, and a **first capture** — no baseline on disk at all — is not a
divergence and is always allowed.

`note_affecting` is deliberately conjunctive: the `document` stage must have
moved *and* `blessdiff` must attribute at least one note to it. A `songform`
rename that re-attributes untouched notes therefore does not trip the guard,
matching the "the document did NOT change" wording `blessdiff` prints for that
case.

**The guard fails closed, in every direction.** A guard that degrades *open* —
that waves a change through whenever it cannot evaluate itself — is worse than
no guard, because CI stays green while the regression surface quietly shrinks.
Four states are therefore refusals rather than passes:

- an **incomplete baseline** (the cell directory exists but a stage file is
  gone) is a corrupted baseline, never a "first capture". Only a genuinely
  absent cell *directory* is a first capture;
- a **baseline whose `meta.generatorVersion` cannot be read** fails the S18-8
  comparison instead of skipping it;
- the pinned S18-8 case: notes moved at an unchanged version;
- a **baseline that no longer validates back into its models** is reported (and
  refused) rather than raising an unhandled traceback out of the reporter.

**The Layer-3 baseline adapter.** §8.2 wants metric deltas, but
`quality.layer3.compute_metrics` takes a whole `GenerationTrace` (it needs
`_common.governing_chord`, i.e. the harmony IR) while a baseline is ten parsed
JSON files. `trace_from_stages` rebuilds a real `GenerationTrace` from those
files — every stage is a pydantic model and validates straight back. The one
field the corpus does not store is `selection` (S18-5: §8.2 omits it from the
boundary list and `SelectionResult` is tuple-keyed, so it is not
JSON-round-trippable). Widening the corpus to an eleventh stage file to avoid
that gap would move a pinned boundary set and needs sign-off.

A rebuilt trace is therefore **metrics-only, not a drop-in `GenerationTrace`**.
`compute_metrics` reads exactly `document`, `harmony` and `song_form`, so it is
sound; `quality.layer1.run_layer1` is *not*, because its W4 check reads
`trace.selection.by_section` and an empty mapping would make it pass vacuously
with zero violations and no error — a silently disarmed validator. So the
synthesized field is `_RebuiltSelection`, which **raises**
`RebuiltSelectionError` on any read rather than answering "nothing selected".

**The version-stamp refresh.** `meta.generatorVersion` is excluded from the
semantic diff (S18-8) so that a bump does not report as a divergence in all 24
cells and drown the real signal. That exclusion is right for the *report* and
wrong for the *corpus*: the field is written into every cell's `document.json`,
so a bump makes every baseline byte-diverge from a fresh render while `bless`
truthfully reports "no divergence". A corpus that is not byte-reproducible is
not worth having, so the corpus wins on the write side: when `--approve`
proceeds and a cell's baseline records a different `generatorVersion` than the
fresh render, that cell's `document.json` is rewritten **even when the cell is
semantically clean**. Only `document.json` — the nine IR stages do not carry the
field and are left untouched. The diff itself is unchanged; this is a write-side
fix, and `format_result` reports the two write reasons separately so a reader
sees why 24 cells were touched when 6 changed musically.

**Bumping `generatorVersion` — the procedure.**

`_GENERATOR_VERSION` lives in `src/trackgen/pipeline/serialize.py:38`. A bump is
a deliberate, dedicated commit (§8.2), and it moves artifacts **outside this
module's reach**. `bless` rewrites the golden corpus and nothing else; it cannot
fix the following and must not pretend to. In the same commit, a human updates:

1. `fixtures/pop_rock.milestone.trackdoc.json`,
   `fixtures/jazz.milestone.trackdoc.json` and
   `fixtures/milestone.trackdoc.json` — each embeds `meta.generatorVersion`.
   The first two are re-serialized by
   `tests/test_whole_document_goldens.py::test_fixture_reserializes_identically`
   (**2 failures** until regenerated).
2. `tests/test_serialize.py::test_meta_seed_and_params` — asserts the version as
   a hardcoded literal (`assert doc.meta.generator_version == "0.1.0"`)
   (**1 failure** until updated).

The full sequence, then, is: edit `serialize.py` → `uv run trackgen bless
--approve` (blesses the semantic change and refreshes every stale stamp) →
regenerate the three `fixtures/*.milestone.trackdoc.json` → update the
`test_serialize.py` literal → run all four gates → commit as one bless commit.

Nothing here prints: `format_result` returns a string and `cli.py` echoes it,
matching the C3 tooling split between computation and formatting.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from trackgen.packs.models import PatternEnvelope
from trackgen.parts.selection import SelectionKey, SelectionResult
from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality.layer3 import Metrics, compute_metrics
from trackgen.schema.document import Role, Tempo, TrackDocument
from trackgen.schema.ir import (
    ArrangementPlan,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    SongForm,
)
from trackgen.sound.stage import SoundDesign
from trackgen.tooling import corpus
from trackgen.tooling.blessdiff import CellDiff, diff_cell, divergent_stages
from trackgen.tooling.blessdiff import format_report as format_diff_report

_DOCUMENT_STAGE: Final = "document"

# `document.json` is dumped `by_alias=True`, hence the camelCase read path.
_META_KEY: Final = "meta"
_VERSION_KEY: Final = "generatorVersion"

# Where a refused approval tells the author to go (S18-8).
_VERSION_SOURCE: Final = "src/trackgen/pipeline/serialize.py:38"

# Cap on the blessed-cell list in the report; the count is always exact. Sized
# past §8.2's full five-pack matrix (60 cells) so a whole-corpus approve lists
# every cell it rewrote rather than eliding the tail a reviewer needs to see.
_MAX_WRITTEN_ROWS: Final = 60


class RebuiltSelectionError(RuntimeError):
    """Raised when a corpus-rebuilt trace's `selection` is read (S18-5)."""


_SELECTION_REFUSAL: Final = (
    "this GenerationTrace was rebuilt from the golden corpus, which does not "
    "store `selection` (SESSION_18 S18-5: SelectionResult is tuple-keyed and "
    "not JSON-round-trippable, and §8.2 omits it from the boundary list). "
    "A rebuilt trace is METRICS-ONLY: quality.layer3.compute_metrics reads "
    "only document/harmony/song_form and is sound. It must NOT be passed to "
    "quality.layer1.run_layer1 — the W4 check reads selection.by_section, and "
    "an empty mapping there would make it pass vacuously with zero violations. "
    "Re-render the cell with corpus.render_cell() for a trace carrying a real "
    "selection."
)


class _RebuiltSelection(SelectionResult):
    """The `selection` of a corpus-rebuilt trace: refuses to be read.

    Deliberately not an empty `SelectionResult`. An empty one answers every
    lookup with "nothing was selected", which is indistinguishable from "nothing
    violated the rule" to any validator that iterates it — so the field would
    silently disarm `run_layer1`'s W4 check instead of announcing that the data
    is simply absent. Reading it raises `RebuiltSelectionError` instead.
    """

    __slots__ = ()

    def __init__(self) -> None:
        # Deliberately does NOT call the frozen-dataclass `__init__`: the two
        # fields are shadowed by raising properties below and there is no value
        # to store.
        pass

    @property
    def by_section(self) -> dict[tuple[str, Role], PatternEnvelope]:
        raise RebuiltSelectionError(_SELECTION_REFUSAL)

    @property
    def by_key(self) -> dict[SelectionKey, PatternEnvelope]:
        raise RebuiltSelectionError(_SELECTION_REFUSAL)

    def __repr__(self) -> str:
        # The inherited dataclass `__repr__` would read the fields and raise,
        # which would turn any incidental logging or a pytest assertion dump
        # into a confusing traceback far from the real misuse.
        return "_RebuiltSelection(<corpus-rebuilt: no selection stored>)"

    def __eq__(self, other: object) -> bool:
        return other is self

    def __hash__(self) -> int:
        return id(self)


def cell_id(cell: corpus.Cell) -> str:
    """`<pack>/<mood>/<len>-<seed>` — the cell's report name and dir path."""
    return f"{cell.pack}/{cell.mood}/{cell.length_sec}-{cell.seed}"


def trace_from_stages(stages: Mapping[str, Any]) -> GenerationTrace:
    """Rebuild a **metrics-only** `GenerationTrace` from a `read_cell` bundle.

    Every corpus stage is validated back into its pydantic model, so those ten
    fields are genuine. `selection` is the one field the corpus does not store
    (S18-5); it is **not** reconstituted empty but as `_RebuiltSelection`, which
    raises `RebuiltSelectionError` on any read.

    That makes the result safe for `quality.layer3.compute_metrics` — which
    reads only `document`/`harmony`/`song_form` — and *only* for it. It is not a
    general-purpose trace: `quality.layer1.run_layer1` reads
    `trace.selection.by_section` in its W4 check, and an empty mapping there
    would make that check pass vacuously. Re-render the cell with
    `corpus.render_cell()` if you need a trace a validator can consume.
    """
    return GenerationTrace(
        plan=GenerationPlan.model_validate(stages["plan"]),
        song_form=SongForm.model_validate(stages["songform"]),
        harmony=HarmonicPlan.model_validate(stages["harmony"]),
        arrangement=ArrangementPlan.model_validate(stages["arrangement"]),
        selection=_RebuiltSelection(),
        phrases_stage5=[Phrase.model_validate(p) for p in stages["phrases_stage5"]],
        phrases_stage6=[Phrase.model_validate(p) for p in stages["phrases_stage6"]],
        phrases_stage7=[Phrase.model_validate(p) for p in stages["phrases_stage7"]],
        tempo_events=[Tempo.model_validate(t) for t in stages["tempo_events"]],
        sound_design=SoundDesign.model_validate(stages["sound_design"]),
        document=TrackDocument.model_validate(stages["document"]),
    )


def baseline_metrics(stages: Mapping[str, Any]) -> Metrics:
    """Layer-3 metrics for a baseline read off disk (§8.2 metric deltas)."""
    return compute_metrics(trace_from_stages(stages))


def encode_trace(trace: GenerationTrace) -> dict[str, Any]:
    """A freshly rendered trace as the same parsed shape `read_cell` returns.

    Encoding then decoding (rather than dumping the models directly) is what
    makes the comparison honest: the fresh side goes through the exact writer
    the baseline came from, so a stage that cannot survive its own round-trip
    shows up as a divergence instead of hiding behind an in-memory compare.
    """
    return {
        stage: corpus.decode_stage(stage, corpus.encode_stage(trace, stage))
        for stage in corpus.STAGES
    }


def note_affecting(diff: CellDiff) -> bool:
    """True iff this cell's divergence actually moved notes (S18-8 gate).

    Conjunctive on purpose: the `document` stage must differ *and* at least one
    note must be attributed to the change. A section-attribution shift over an
    unchanged document, or a document change that touches only channel/mix data,
    is not note-affecting and is approvable without a version bump.
    """
    return _DOCUMENT_STAGE in diff.diverged_stages and bool(diff.notes)


def _version_of(stages: Mapping[str, Any] | None) -> str | None:
    if stages is None:
        return None
    document = stages.get(_DOCUMENT_STAGE)
    if not isinstance(document, dict):
        return None
    meta = document.get(_META_KEY)
    if not isinstance(meta, dict):
        return None
    version = meta.get(_VERSION_KEY)
    return version if isinstance(version, str) else None


def read_baseline(
    cell: corpus.Cell, *, root: Path | None = None
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """`(baseline, missing_stages)` for `cell` — the fail-closed baseline read.

    Returns `(None, ())` **only** when the cell directory does not exist: that is
    the one genuine first capture. When the directory exists, every stage file it
    is missing is named in `missing_stages` and the stages that *are* present are
    still parsed and returned, so the diff can localize as usual.

    `corpus.read_cell` cannot make this distinction on its own — it raises
    `FileNotFoundError` on the first stage file it cannot open, so "no cell at
    all" and "nine of ten files present" arrive identically. Reading that as a
    first capture is exactly how the guard would degrade open: the cell would be
    rewritten under `--approve` with no diff reported and no `generatorVersion`
    check, and a plain `bless` would exit 0 while the regression surface shrank.
    """
    directory = corpus.cell_dir(cell, root=root)
    if not directory.is_dir():
        return None, ()

    missing = tuple(
        stage for stage in corpus.STAGES if not (directory / f"{stage}.json").is_file()
    )
    if not missing:
        return corpus.read_cell(cell, root=root), ()
    return {
        stage: corpus.decode_stage(
            stage, (directory / f"{stage}.json").read_text(encoding="utf-8")
        )
        for stage in corpus.STAGES
        if stage not in missing
    }, missing


def _incomplete_message(missing: Sequence[str]) -> str:
    """The `stage_errors` line for a partial baseline (never a first capture)."""
    names = ", ".join(f"{stage}.json" for stage in missing)
    return (
        f"INCOMPLETE BASELINE — {len(missing)} stage file(s) missing from a cell "
        f"directory that exists: {names}. This is a corrupted/partial baseline, "
        f"not a first capture, and is never silently approvable. Restore the "
        f"file(s) from git, or delete the whole cell directory to re-capture the "
        f"cell deliberately."
    )


def _unreadable_message(exc: Exception) -> str:
    """The `stage_errors` line for a baseline that no longer parses back."""
    detail = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    return (
        f"UNREADABLE BASELINE — the stored stages do not validate back into "
        f"their models ({type(exc).__name__}: {detail}). No layer-3 metric "
        f"deltas could be computed, and the baseline cannot be trusted as the "
        f"thing this run diffed against. Restore the cell from git, or delete "
        f"its directory to re-capture it deliberately."
    )


@dataclass(frozen=True)
class _CellRun:
    """One cell's rendered state, kept so `--approve` can write it back."""

    cell: corpus.Cell
    trace: GenerationTrace
    diff: CellDiff
    baseline_version: str | None
    fresh_version: str | None
    missing_stages: tuple[str, ...] = ()
    baseline_unreadable: bool = False


@dataclass(frozen=True)
class BlessResult:
    """The outcome of one `bless()` run — what `format_result` consumes.

    `written` and `refreshed` are disjoint and name the two reasons a baseline
    moved: `written` is a blessed *semantic* change (or a first capture) and
    rewrites all ten stages; `refreshed` is a semantically clean cell whose
    `document.json` alone was rewritten to carry the current
    `meta.generatorVersion`. Keeping them apart is the point — a bump touches
    every cell, and a reader must be able to tell those apart from the handful
    that actually changed musically.
    """

    diffs: tuple[CellDiff, ...]
    written: tuple[str, ...] = ()
    refreshed: tuple[str, ...] = ()
    generator_version: str | None = None
    refusal: str | None = None

    @property
    def divergent(self) -> tuple[CellDiff, ...]:
        """Cells needing review. A first capture is not one (§8.2)."""
        return tuple(
            diff for diff in self.diffs if not diff.clean and not diff.missing_baseline
        )

    @property
    def first_captures(self) -> tuple[CellDiff, ...]:
        """Cells with no baseline on disk — captured, not reviewed."""
        return tuple(diff for diff in self.diffs if diff.missing_baseline)

    @property
    def ok(self) -> bool:
        """True when the run needs no decision: nothing diverged, nothing refused."""
        return self.refusal is None and not self.divergent


def _refusal_message(
    runs: Sequence[_CellRun], *, root: Path | None = None
) -> str | None:
    """The `--approve` refusal, or `None` if the run may proceed.

    Four fail-closed cases, ordered so the message a reader gets is the most
    specific one that applies:

    1. an **incomplete baseline** — stage files missing from a directory that
       exists. Structural, and nothing downstream of it would mean anything;
    2. among note-affecting cells that have a baseline, an **unreadable
       `meta.generatorVersion`** — the S18-8 comparison cannot be evaluated, and
       an unevaluable guard must not pass;
    3. the pinned **S18-8** case — notes moved while the version stands still;
    4. an **unreadable baseline** — the stored stages no longer validate back
       into their models, so the mandated metric deltas were never computed.

    A cell whose baseline predates a bump is already recording the change and
    passes; a first capture has no baseline and is never a candidate.
    """
    incomplete = [run for run in runs if run.missing_stages]
    if incomplete:
        first = incomplete[0]
        names = ", ".join(f"{stage}.json" for stage in first.missing_stages)
        return (
            f"REFUSED --approve: {len(incomplete)} cell(s) have an INCOMPLETE "
            f"baseline on disk — stage file(s) missing from a cell directory "
            f"that exists.\n"
            f"  A partial baseline is a corrupted one, not a first capture: "
            f"blessing it would rewrite the cell with nothing reviewed and no "
            f"generatorVersion check behind it.\n"
            f"  first offender: {first.diff.cell_id} "
            f"({corpus.cell_dir(first.cell, root=root)}) — missing {names}\n"
            f"  restore the file(s) from git, or delete the whole cell directory "
            f"to re-capture that cell deliberately, then re-run."
        )

    candidates = [
        run
        for run in runs
        if note_affecting(run.diff) and not run.diff.missing_baseline
    ]

    unversioned = [
        run
        for run in candidates
        if run.baseline_version is None or run.fresh_version is None
    ]
    if unversioned:
        first = unversioned[0]
        path = corpus.cell_dir(first.cell, root=root) / f"{_DOCUMENT_STAGE}.json"
        side = "baseline" if first.baseline_version is None else "fresh render"
        return (
            f"REFUSED --approve: {len(unversioned)} cell(s) changed notes while "
            f"meta.generatorVersion could not be read from the {side}.\n"
            f"  §8.2's guard *is* that comparison — with no version to compare, "
            f"it cannot pass, so it refuses rather than waving the change "
            f"through.\n"
            f"  first offender: {first.diff.cell_id} ({path})\n"
            f"  repair meta.generatorVersion in that baseline (or delete the "
            f"cell directory to re-capture it deliberately), then re-run."
        )

    stalled = [run for run in candidates if run.baseline_version == run.fresh_version]
    if stalled:
        first = stalled[0]
        path = corpus.cell_dir(first.cell, root=root) / f"{_DOCUMENT_STAGE}.json"
        return (
            f"REFUSED --approve: {len(stalled)} cell(s) changed notes while "
            f"meta.generatorVersion is still {first.baseline_version!r}.\n"
            f"  §8.2 requires a generatorVersion bump to accompany a blessed note "
            f"change — otherwise the baselines move with nothing recording that "
            f"they did.\n"
            f"  first offender: {first.diff.cell_id} ({path})\n"
            f"  bump `_GENERATOR_VERSION` in {_VERSION_SOURCE} and re-run, or fix "
            f"the code instead of blessing it."
        )

    corrupted = [run for run in runs if run.baseline_unreadable]
    if corrupted:
        first = corrupted[0]
        return (
            f"REFUSED --approve: {len(corrupted)} cell(s) have an UNREADABLE "
            f"baseline on disk — the stored stages no longer validate back into "
            f"their models.\n"
            f"  The layer-3 metric deltas §8.2 mandates could not be computed "
            f"against them, so blessing would overwrite a baseline that was "
            f"never fully read.\n"
            f"  first offender: {first.diff.cell_id} "
            f"({corpus.cell_dir(first.cell, root=root)})\n"
            f"  restore the cell from git, or delete its directory to re-capture "
            f"it deliberately, then re-run."
        )

    return None


def _needs_version_refresh(run: _CellRun) -> bool:
    """True iff this cell is semantically clean but records a stale version.

    Restricted to `diff.clean` cells on purpose: a divergent cell is rewritten
    in full by `write_cell` anyway, and a first capture has no stored stamp to
    be stale. `clean` also implies a complete, readable baseline, so the two
    versions being compared are both real reads.
    """
    return run.diff.clean and run.baseline_version != run.fresh_version


def _write_document_stage(
    trace: GenerationTrace, cell: corpus.Cell, *, root: Path | None = None
) -> Path:
    """Rewrite only `document.json` for `cell` — the minimal stamp refresh.

    Deliberately not `corpus.write_cell`: the nine IR stages do not carry
    `meta.generatorVersion`, so rewriting them would touch nine files to change
    nothing and blur which cells the run actually moved.
    """
    target = corpus.cell_dir(cell, root=root)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{_DOCUMENT_STAGE}.json"
    path.write_text(
        corpus.encode_stage(trace, _DOCUMENT_STAGE),
        encoding="utf-8",
    )
    return path


def bless(
    *,
    approve: bool = False,
    cells: Sequence[corpus.Cell] | None = None,
    root: Path | None = None,
) -> BlessResult:
    """Re-render the golden corpus, diff it, and optionally rewrite baselines (§8.2).

    `cells` defaults to the pinned 24-cell matrix and `root` to the committed
    `fixtures/goldens/`. Without `approve` nothing is ever written — not even a
    first capture — so a plain `bless` run is read-only by construction. With
    `approve`, the fail-closed checks run first and refuse the whole run
    (writing nothing) rather than blessing part of it.

    A cell counts as a first capture only when its directory is absent; a
    directory missing a stage file is reported as an incomplete baseline and
    refuses `--approve` (see `read_baseline`).
    """
    selected = list(corpus.corpus_cells()) if cells is None else list(cells)

    runs: list[_CellRun] = []
    for cell in selected:
        trace = corpus.render_cell(cell)
        fresh = encode_trace(trace)
        # Only an absent cell *directory* is a first capture; a directory missing
        # a stage file is a corrupted baseline and comes back with `missing`.
        baseline, missing = read_baseline(cell, root=root)
        unreadable: str | None = None

        if baseline is None:
            diff = diff_cell(cell_id(cell), None, fresh)
        elif missing:
            # Metrics need all ten stages, so a partial baseline gets the
            # structural diff only; the missing files are the finding.
            partial = diff_cell(cell_id(cell), baseline, fresh)
            diff = replace(
                partial,
                stage_errors=(_incomplete_message(missing), *partial.stage_errors),
            )
        elif divergent_stages(baseline, fresh):
            # Metrics derive from document/harmony/song_form, so an all-stages-
            # identical cell provably has identical metrics: computing them
            # would only re-validate ten files to learn nothing.
            base_metrics: Metrics | None = None
            try:
                base_metrics = baseline_metrics(baseline)
            except (ValidationError, KeyError, TypeError, ValueError) as exc:
                # A baseline that no longer parses back into its own models is a
                # corrupted baseline, and the report is where a corrupted
                # baseline belongs — not an unhandled traceback out of a tool
                # whose whole job is to report. It stays a divergence (a
                # `stage_errors` entry is never clean) and, like a missing stage
                # file, it refuses `--approve` below.
                unreadable = _unreadable_message(exc)
            diff = diff_cell(
                cell_id(cell),
                baseline,
                fresh,
                baseline_metrics=base_metrics,
                fresh_metrics=None if base_metrics is None else compute_metrics(trace),
            )
            if unreadable is not None:
                diff = replace(diff, stage_errors=(unreadable, *diff.stage_errors))
        else:
            diff = diff_cell(cell_id(cell), baseline, fresh)

        runs.append(
            _CellRun(
                cell=cell,
                trace=trace,
                diff=diff,
                baseline_version=_version_of(baseline),
                fresh_version=_version_of(fresh),
                missing_stages=missing,
                baseline_unreadable=unreadable is not None,
            )
        )

    diffs = tuple(run.diff for run in runs)
    fresh_version = next((run.fresh_version for run in runs), None)
    if not approve:
        return BlessResult(diffs=diffs, generator_version=fresh_version)

    refusal = _refusal_message(runs, root=root)
    if refusal is not None:
        return BlessResult(
            diffs=diffs, generator_version=fresh_version, refusal=refusal
        )

    written = [run for run in runs if not run.diff.clean]
    for run in written:
        corpus.write_cell(run.trace, run.cell, root=root)

    # A semantically clean cell whose stored stamp is stale: the diff excludes
    # meta.generatorVersion (S18-8), so it reports clean while its committed
    # bytes provably differ from a fresh render. Only `document.json` carries
    # the field, so only `document.json` is rewritten.
    refreshed = [run for run in runs if _needs_version_refresh(run)]
    for run in refreshed:
        _write_document_stage(run.trace, run.cell, root=root)

    return BlessResult(
        diffs=diffs,
        written=tuple(run.diff.cell_id for run in written),
        refreshed=tuple(run.diff.cell_id for run in refreshed),
        generator_version=fresh_version,
    )


def _cell_list(cell_ids: Sequence[str]) -> str:
    """`cell_ids` joined, elided past `_MAX_WRITTEN_ROWS` with the count named."""
    shown = ", ".join(cell_ids[:_MAX_WRITTEN_ROWS])
    elided = len(cell_ids) - _MAX_WRITTEN_ROWS
    return f"{shown}, … and {elided} more" if elided > 0 else shown


def format_result(result: BlessResult, *, approve: bool = False) -> str:
    """The §8.2 report for a whole run, plus the approval outcome.

    The diff report is `blessdiff.format_report` verbatim — never a raw JSON
    diff — with the write/refusal verdict appended so the two are never read
    apart.
    """
    lines = [format_diff_report(result.diffs)]

    if result.refusal is not None:
        lines.extend(["", result.refusal])
        return "\n".join(lines)

    if result.written or result.refreshed:
        lines.append("")
        if result.written:
            lines.append(
                f"blessed {len(result.written)} cell(s) — semantic change, all "
                f"stages rewritten: {_cell_list(result.written)}"
            )
        if result.refreshed:
            version = (
                "unknown"
                if result.generator_version is None
                else repr(result.generator_version)
            )
            lines.append(
                f"version-stamp refresh: {len(result.refreshed)} cell(s) — "
                f"semantically clean, document.json only, restamped to "
                f"generatorVersion {version}: {_cell_list(result.refreshed)}"
            )
            lines.append(
                "  (meta.generatorVersion is excluded from the semantic diff "
                "(S18-8), so these cells report clean; their baselines are "
                "rewritten anyway to keep the corpus byte-reproducible.)"
            )
        lines.append(
            "Commit these baselines on their own (§8.2: a dedicated bless commit)."
        )
    elif approve:
        lines.extend(["", "nothing to bless — every cell already matches."])
    elif result.divergent or result.first_captures:
        lines.extend(
            ["", "no baseline was written (re-run with --approve to accept these)."]
        )

    return "\n".join(lines)
