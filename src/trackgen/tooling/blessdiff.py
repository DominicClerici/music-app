"""Bless diff report (PHASE_8 §8.2) — the semantic diff, never a raw JSON diff.

§8.2 pins two legal moves on a golden divergence: fix the code, or
`bless --approve`. **Reflexive re-blessing is the failure mode the report format
exists to prevent** — so the report must be small enough that a human actually
reads it before choosing. That is a hard constraint on this module, not a style
preference: nothing here may emit a raw JSON diff, and every section is
aggregated to a bounded number of lines.

Three answers, in the order a human needs them:

1. **Where did it first diverge?** `first_divergent_stage` walks `corpus.STAGES`
   in trace order and names the first stage whose parsed content moved. This is
   the whole payoff of storing all ten IR boundaries: a harmony bug reads as
   "harmony", not as "the document changed". Later divergent stages are reported
   as *derivative* — downstream of the first, not independent findings.
2. **What moved musically?** `note_deltas` gives added / removed / moved counts
   per `(track_id, section_id)`.
3. **Did the statistics shift?** `metric_deltas` gives the Layer-3 deltas.

Everything is a pure function over *parsed dicts* — the shapes `corpus.read_cell`
returns — so formatting drift can never present as a divergence, and the module
does no I/O and prints nothing. `format_report` returns a string; the caller
decides whether it reaches a terminal.

**Note identity (SESSION_18 S18-6).** `NoteEvent` has no id and phrase tags are
serialize-dropped, so "moved" needs an invented matching rule. Pinned: within a
`(track_id, section_id)` bucket, notes matching on `(midi, duration_ticks)` and
differing in `ticks` by <= `_MOVE_TOLERANCE_TICKS` (240 = an 8th) are one
`moved`; everything else is `added`/`removed` by multiset difference, paired by
ascending `ticks`. Two refinements this module had to settle, both preserving
those semantics:

- *Exact ticks cancel first.* Unchanged notes are removed from both sides before
  any move-pairing. Without this, one genuinely moved note can capture an
  unchanged neighbour and cascade into a spurious `added` + `removed` + `moved`
  triple (`b=[0, 1000]` vs `f=[900, 1000]` is the minimal case).
- *A velocity-only change is reported as `changed`*, an additive fourth counter.
  Velocity is not part of S18-6's identity, so such notes cancel as unchanged and
  would otherwise render as "the document diverged, 0 notes changed" — the
  precise shape of report that gets blessed reflexively. `changed` never alters
  the pinned added/removed/moved counts; it only names what would have been
  invisible.

**Section attribution (SESSION_18 S18-7).** From the cell's `songform.json`
(`FormSection.id`, e.g. `solo-2`), never from `doc.sections` — those carry only
`label`/`type`, with no id and no uniqueness guarantee (`quality/_common.py`
warns validators off them). Spans are half-open `[start, end)`, matching
`_common.section_span`, so a note landing exactly on a boundary belongs to the
*later* section. A note outside every span is bucketed under `_UNSECTIONED`, never
silently dropped. Notes are attributed within their own document, so a note that
moves *across* a section boundary reads as removed-from-A + added-to-B rather
than moved — a deliberate consequence of S18-6's per-bucket matching. When
`document` is *not* among the divergent stages, every such row is by construction
attribution movement and nothing else, and the report says so in those words: a
pure section rename would otherwise headline hundreds of "notes" on a document
where zero notes moved — the single most blessable-by-reflex report shape there
is.

**`meta.generatorVersion` is excluded** from every comparison here (S18-8), so a
version bump does not report as a divergence in all 24 cells and drown the signal
it was bumped to record.

**Nulls are meaningful, not zero.** `mean_ioi` is `None` below 2 notes,
`pitch_range` `None` with no pitched note, `scale_consistency` `None` for drums.
A `None` <-> value transition renders explicitly and never as a numeric delta.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

# The stage-name contract is owned by the corpus module; never redefined here.
from trackgen.tooling.corpus import STAGES

# S18-6: an 8th at PPQ 480. A same-pitch, same-duration note within this of its
# baseline onset is the *same* note, moved.
_MOVE_TOLERANCE_TICKS: Final = 240

# PHASE_1: PPQ 480, 4/4 -> 1920 ticks/bar (mirrors `quality/_common._TICKS_PER_BAR`;
# duplicated rather than imported because that helper works on a live trace and
# this module works on parsed dicts).
_TICKS_PER_BAR: Final = 1920

# The bucket for notes outside every form-section span. Parenthesized so it can
# never collide with a real `FormSection.id` (`f"{type}-{index}"`).
_UNSECTIONED: Final = "(unsectioned)"

# Scope name for the song-wide Layer-3 metrics (`n_bars`, `groove_consistency`).
_SONG_SCOPE: Final = "(song)"

_DOCUMENT_STAGE: Final = "document"

# S18-8: excluded from diff reporting so a deliberate bump is not itself the
# report. `document.json` is dumped `by_alias=True`, hence the camelCase key.
_EXCLUDED_META_KEY: Final = "generatorVersion"

# Readability caps (§8.2 "small enough to actually read"). Rows beyond the cap
# are summarized, never dropped silently -- the elided total is always printed.
_MAX_NOTE_ROWS: Final = 20
_MAX_METRIC_ROWS: Final = 20

# Sentinel for "this scope/metric exists on only one side".
_MISSING: Final = object()


class Absent:
    """Renders as `(absent)` — a metric scope present on only one side."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "(absent)"


ABSENT: Final = Absent()

MetricValue = float | int | str | None | Absent


@dataclass(frozen=True)
class NoteDelta:
    """Per-`(track_id, section_id)` note movement (S18-6)."""

    track_id: str
    section_id: str
    added: int
    removed: int
    moved: int
    changed: int

    @property
    def total(self) -> int:
        """Total notes implicated — the ranking key when rows must be elided."""
        return self.added + self.removed + self.moved + self.changed


@dataclass(frozen=True)
class MetricDelta:
    """One Layer-3 metric that moved, with both sides rendered explicitly."""

    scope: str
    metric: str
    baseline: MetricValue
    fresh: MetricValue


@dataclass(frozen=True)
class CellDiff:
    """One corpus cell's whole verdict — what `format_report` consumes."""

    cell_id: str
    first_stage: str | None = None
    diverged_stages: tuple[str, ...] = ()
    notes: tuple[NoteDelta, ...] = ()
    metrics: tuple[MetricDelta, ...] = ()
    missing_baseline: bool = False
    stage_errors: tuple[str, ...] = ()

    @property
    def clean(self) -> bool:
        """True when nothing to review: no divergence and a baseline existed."""
        return (
            not self.missing_baseline
            and self.first_stage is None
            and not self.notes
            and not self.metrics
            and not self.stage_errors
        )


# --- stage localization -------------------------------------------------------


def comparable_stage(stage: str, parsed: Any) -> Any:
    """`parsed` with the S18-8 exclusions removed, ready to compare.

    Only `document` is rewritten, and only to drop `meta.generatorVersion`; every
    other stage compares as-read. Returns a shallow-rebuilt structure — the input
    is never mutated.
    """
    if stage != _DOCUMENT_STAGE or not isinstance(parsed, dict):
        return parsed
    meta = parsed.get("meta")
    if not isinstance(meta, dict) or _EXCLUDED_META_KEY not in meta:
        return parsed
    return {
        **parsed,
        "meta": {k: v for k, v in meta.items() if k != _EXCLUDED_META_KEY},
    }


def divergent_stages(
    baseline: Mapping[str, Any], fresh: Mapping[str, Any]
) -> tuple[str, ...]:
    """Every stage in `STAGES` order whose parsed content differs.

    A stage present on exactly one side counts as divergent; a stage absent from
    both is skipped (it is not evidence of a change).
    """
    out: list[str] = []
    for stage in STAGES:
        base = baseline.get(stage, _MISSING)
        new = fresh.get(stage, _MISSING)
        if base is _MISSING and new is _MISSING:
            continue
        if base is _MISSING or new is _MISSING:
            out.append(stage)
            continue
        if comparable_stage(stage, base) != comparable_stage(stage, new):
            out.append(stage)
    return tuple(out)


def first_divergent_stage(
    baseline: Mapping[str, Any], fresh: Mapping[str, Any]
) -> str | None:
    """The first stage in `STAGES` order that differs, or `None` if identical.

    This is the localizer §8.2's ten-boundary corpus exists to enable: a harmony
    regression names `harmony`, and the eight downstream stages it perturbs are
    derivative rather than eight separate findings.
    """
    stages = divergent_stages(baseline, fresh)
    return stages[0] if stages else None


# --- note deltas (S18-6 / S18-7) ---------------------------------------------


def section_spans(songform: Mapping[str, Any]) -> list[tuple[int, int, str]]:
    """`[(start_tick, end_tick, section_id), …]` from a parsed `songform.json`.

    Half-open `[start, end)` per `quality/_common.section_span`. Ordered by start
    tick so the report reads in musical order rather than alphabetically.
    """
    spans: list[tuple[int, int, str]] = []
    for section in songform.get("sections", []):
        start = int(section["start_bar"]) * _TICKS_PER_BAR
        end = start + int(section["length_bars"]) * _TICKS_PER_BAR
        spans.append((start, end, str(section["id"])))
    spans.sort()
    return spans


def _section_of(spans: Sequence[tuple[int, int, str]], tick: int) -> str:
    for start, end, section_id in spans:
        if start <= tick < end:
            return section_id
    return _UNSECTIONED


# A note reduced to what S18-6 compares: identity key, onset, velocity.
_NoteKey = tuple[int | None, int]
_Bucket = dict[tuple[str, str], dict[_NoteKey, list[tuple[int, float]]]]


def _bucket_notes(
    doc: Mapping[str, Any], spans: Sequence[tuple[int, int, str]]
) -> _Bucket:
    buckets: _Bucket = defaultdict(lambda: defaultdict(list))
    for track in doc.get("tracks", []):
        track_id = str(track["id"])
        for note in track.get("notes", []):
            ticks = int(note["ticks"])
            # `exclude_none=True` drops `midi` entirely on NoiseSynth notes, so
            # the absent key and an explicit null must read the same.
            midi = note.get("midi")
            key: _NoteKey = (
                None if midi is None else int(midi),
                int(note["durationTicks"]),
            )
            section_id = _section_of(spans, ticks)
            buckets[(track_id, section_id)][key].append(
                (ticks, float(note.get("velocity", 0.0)))
            )
    return buckets


def _match_key_group(
    baseline: list[tuple[int, float]], fresh: list[tuple[int, float]]
) -> tuple[int, int, int, int]:
    """`(added, removed, moved, changed)` for one `(midi, duration)` group.

    Exact-onset pairs cancel first (comparing velocity to surface a `changed`),
    then the survivors are paired by ascending `ticks` with the S18-6 tolerance.

    **Known degenerate case, not a defect.** When a uniform shift happens to
    equal the inter-onset spacing exactly (`b=[0, 240, 480]` -> `f=[240, 480,
    720]`), cancellation consumes the two coincident onsets and the group reports
    `+1 -1 ~0` where the literal move rule would report `~3`. Both readings are
    true of id-less notes — the ambiguity is inherent to S18-6's matching, and
    cancelling first is the choice that keeps an unchanged neighbour from being
    captured by a genuinely moved note. Sub-spacing shifts (the realistic
    humanizer/swing case, where no fresh onset lands on a baseline one) are
    unaffected and still report as all-moved.
    """
    by_tick_b: dict[int, list[float]] = defaultdict(list)
    by_tick_f: dict[int, list[float]] = defaultdict(list)
    for ticks, velocity in baseline:
        by_tick_b[ticks].append(velocity)
    for ticks, velocity in fresh:
        by_tick_f[ticks].append(velocity)

    changed = 0
    residual_b: list[int] = []
    residual_f: list[int] = []
    for tick in sorted(set(by_tick_b) | set(by_tick_f)):
        # Sorted so duplicate onsets pair deterministically by velocity.
        vels_b = sorted(by_tick_b.get(tick, ()))
        vels_f = sorted(by_tick_f.get(tick, ()))
        paired = min(len(vels_b), len(vels_f))
        changed += sum(1 for i in range(paired) if vels_b[i] != vels_f[i])
        residual_b.extend([tick] * (len(vels_b) - paired))
        residual_f.extend([tick] * (len(vels_f) - paired))

    residual_b.sort()
    residual_f.sort()

    added = removed = moved = 0
    i = j = 0
    while i < len(residual_b) and j < len(residual_f):
        if abs(residual_f[j] - residual_b[i]) <= _MOVE_TOLERANCE_TICKS:
            moved += 1
            i += 1
            j += 1
        elif residual_b[i] < residual_f[j]:
            removed += 1
            i += 1
        else:
            added += 1
            j += 1
    removed += len(residual_b) - i
    added += len(residual_f) - j
    return added, removed, moved, changed


def note_deltas(
    baseline_doc: Mapping[str, Any],
    fresh_doc: Mapping[str, Any],
    songform: Mapping[str, Any],
    *,
    fresh_songform: Mapping[str, Any] | None = None,
) -> tuple[NoteDelta, ...]:
    """Per-`(track_id, section_id)` added/removed/moved/changed counts (S18-6).

    `songform` attributes the *baseline* document's notes; `fresh_songform`
    attributes the fresh one, defaulting to `songform` (the common case, where
    the form did not move). Only non-zero rows are returned, ordered by track id
    then section start tick, with `(unsectioned)` last.
    """
    base_spans = section_spans(songform)
    fresh_spans = (
        base_spans if fresh_songform is None else section_spans(fresh_songform)
    )

    base_buckets = _bucket_notes(baseline_doc, base_spans)
    fresh_buckets = _bucket_notes(fresh_doc, fresh_spans)

    # Section ordering for the report: musical order, then any section unique to
    # one side (alphabetical), then the unsectioned catch-all.
    order: dict[str, int] = {}
    for spans in (base_spans, fresh_spans):
        for start, _end, section_id in spans:
            order[section_id] = min(order.get(section_id, start), start)

    def sort_key(delta: NoteDelta) -> tuple[str, int, int, str]:
        if delta.section_id == _UNSECTIONED:
            return (delta.track_id, 2, 0, "")
        if delta.section_id in order:
            return (delta.track_id, 0, order[delta.section_id], delta.section_id)
        return (delta.track_id, 1, 0, delta.section_id)

    deltas: list[NoteDelta] = []
    for bucket in sorted(set(base_buckets) | set(fresh_buckets)):
        base_group = base_buckets.get(bucket, {})
        fresh_group = fresh_buckets.get(bucket, {})
        added = removed = moved = changed = 0
        for key in sorted(
            set(base_group) | set(fresh_group),
            key=lambda k: (k[0] is None, k[0] or 0, k[1]),
        ):
            a, r, m, c = _match_key_group(
                base_group.get(key, []), fresh_group.get(key, [])
            )
            added += a
            removed += r
            moved += m
            changed += c
        if added or removed or moved or changed:
            track_id, section_id = bucket
            deltas.append(
                NoteDelta(
                    track_id=track_id,
                    section_id=section_id,
                    added=added,
                    removed=removed,
                    moved=moved,
                    changed=changed,
                )
            )
    deltas.sort(key=sort_key)
    return tuple(deltas)


# --- Layer-3 metric deltas ----------------------------------------------------

# `TrackMetrics` keys, in the §8.1 metric order rather than alphabetically.
_TRACK_METRIC_KEYS: Final = (
    "role",
    "note_density",
    "mean_ioi",
    "pitch_range",
    "empty_bar_rate",
    "scale_consistency",
)
_SONG_METRIC_KEYS: Final = ("n_bars", "groove_consistency")


def metric_deltas(
    baseline: Mapping[str, Any], fresh: Mapping[str, Any]
) -> tuple[MetricDelta, ...]:
    """Every Layer-3 metric that moved, `None` transitions rendered explicitly.

    Both arguments are `quality.layer3.Metrics` bundles (a `TypedDict`, hence a
    `Mapping[str, Any]`) — or the same shape read back from disk.

    A `None` on either side is carried through as `None` and never coerced to
    `0`: `mean_ioi=None` means "fewer than 2 notes", not "an IOI of zero", and
    flattening that hides exactly the regressions Layer 3 exists to notice. A
    track present on only one side yields `ABSENT` for the missing side.
    """
    deltas: list[MetricDelta] = []

    for key in _SONG_METRIC_KEYS:
        base_value = baseline.get(key, ABSENT)
        fresh_value = fresh.get(key, ABSENT)
        if base_value != fresh_value:
            deltas.append(MetricDelta(_SONG_SCOPE, key, base_value, fresh_value))

    base_tracks: Mapping[str, Any] = baseline.get("tracks", {}) or {}
    fresh_tracks: Mapping[str, Any] = fresh.get("tracks", {}) or {}
    for track_id in sorted(set(base_tracks) | set(fresh_tracks)):
        base_track = base_tracks.get(track_id)
        fresh_track = fresh_tracks.get(track_id)
        for key in _TRACK_METRIC_KEYS:
            base_value = ABSENT if base_track is None else base_track.get(key, ABSENT)
            fresh_value = (
                ABSENT if fresh_track is None else fresh_track.get(key, ABSENT)
            )
            if base_value != fresh_value:
                deltas.append(MetricDelta(track_id, key, base_value, fresh_value))

    return tuple(deltas)


# --- assembly -----------------------------------------------------------------


def diff_cell(
    cell_id: str,
    baseline: Mapping[str, Any] | None,
    fresh: Mapping[str, Any],
    *,
    baseline_metrics: Mapping[str, Any] | None = None,
    fresh_metrics: Mapping[str, Any] | None = None,
) -> CellDiff:
    """Assemble one cell's `CellDiff` from two `corpus.read_cell`-shaped dicts.

    `baseline=None` means no baseline on disk — a first capture, which §8.2
    treats as "nothing to review", not as a divergence.
    """
    if baseline is None:
        return CellDiff(cell_id=cell_id, missing_baseline=True)

    stages = divergent_stages(baseline, fresh)

    notes: tuple[NoteDelta, ...] = ()
    errors: list[str] = []
    base_doc = baseline.get(_DOCUMENT_STAGE)
    fresh_doc = fresh.get(_DOCUMENT_STAGE)
    base_form = baseline.get("songform")
    fresh_form = fresh.get("songform")
    if isinstance(base_doc, dict) and isinstance(fresh_doc, dict):
        if isinstance(base_form, dict) and isinstance(fresh_form, dict):
            notes = note_deltas(
                base_doc, fresh_doc, base_form, fresh_songform=fresh_form
            )
        else:
            errors.append("songform.json missing — notes not attributed to sections")

    metrics: tuple[MetricDelta, ...] = ()
    if baseline_metrics is not None and fresh_metrics is not None:
        metrics = metric_deltas(baseline_metrics, fresh_metrics)
    elif baseline_metrics is not None or fresh_metrics is not None:
        # §8.2 mandates metric deltas, so half a metrics pair must announce
        # itself the way a missing `songform.json` does — silently reporting no
        # metric movement is indistinguishable from "the metrics held steady".
        # Neither side supplied means the caller did not ask for a metric
        # comparison at all, which is not a signal loss and stays quiet.
        missing = "baseline" if baseline_metrics is None else "fresh"
        errors.append(
            f"layer-3 metrics unavailable ({missing} side missing) — "
            "no metric deltas computed"
        )

    return CellDiff(
        cell_id=cell_id,
        first_stage=stages[0] if stages else None,
        diverged_stages=stages,
        notes=notes,
        metrics=metrics,
        stage_errors=tuple(errors),
    )


# --- report -------------------------------------------------------------------


def _format_value(value: MetricValue) -> str:
    """Render one metric side; `None` is `null`, never `0`."""
    if value is None:
        return "null"
    if isinstance(value, Absent):
        return "(absent)"
    if isinstance(value, bool):  # pragma: no cover - no bool metric today
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _format_metric(delta: MetricDelta) -> str:
    base = _format_value(delta.baseline)
    fresh = _format_value(delta.fresh)
    numeric = (
        isinstance(delta.baseline, (int, float))
        and isinstance(delta.fresh, (int, float))
        and not isinstance(delta.baseline, bool)
        and not isinstance(delta.fresh, bool)
    )
    if numeric:
        # mypy: guarded by `numeric` above.
        change = float(delta.fresh) - float(delta.baseline)  # type: ignore[arg-type]
        return f"{delta.metric}: {base} -> {fresh} ({change:+.6g})"
    # A None/absent transition deliberately carries no arithmetic delta.
    return f"{delta.metric}: {base} -> {fresh}"


def _note_row(delta: NoteDelta, *, attribution_only: bool = False) -> str:
    parts = [f"+{delta.added}", f"-{delta.removed}"]
    # In the attribution-churn case the moved/velocity counters are structurally
    # zero (an identical document cancels every note on exact onset), so printing
    # them would only invite the "notes moved" reading the header just denied.
    if not attribution_only:
        parts.append(f"~{delta.moved}")
        if delta.changed:
            parts.append(f"v{delta.changed}")
    return f"    {delta.track_id} / {delta.section_id}: {' '.join(parts)}"


def _cell_lines(diff: CellDiff) -> list[str]:
    lines = [diff.cell_id]

    if diff.missing_baseline:
        lines.append("  no baseline on disk — first capture, nothing to review")
        return lines

    if diff.first_stage is None:
        lines.append("  identical")
    else:
        lines.append(f"  FIRST DIVERGENT STAGE: {diff.first_stage}")
        derivative = diff.diverged_stages[1:]
        if derivative:
            lines.append(
                f"  also differs (derivative, downstream of {diff.first_stage}): "
                + ", ".join(derivative)
            )

    for error in diff.stage_errors:
        lines.append(f"  ! {error}")

    if diff.notes:
        total = sum(d.total for d in diff.notes)
        # `document` absent from the divergent set means not one note byte moved,
        # so every row here is a note being attributed to a *different section
        # id* — a `songform` rename or boundary shift. Presenting that as note
        # churn is the report reading a human is most likely to bless reflexively.
        attribution_only = _DOCUMENT_STAGE not in diff.diverged_stages
        if attribution_only:
            lines.append(
                "  section-attribution churn — the document did NOT change: "
                "no note was added, removed, re-timed or revoiced."
            )
            lines.append(
                f"  {total} note(s) changed which section id they fall under, "
                f"across {len(diff.notes)} track/section bucket(s)  "
                "[+gained -lost]:"
            )
        else:
            lines.append(
                f"  notes — {total} implicated across {len(diff.notes)} "
                "track/section bucket(s)  [+added -removed ~moved vvelocity]:"
            )
        # Elision is by descending `NoteDelta.total` (the documented ranking key)
        # so the loudest buckets survive the cap; ties break on the stored index,
        # which is already `(track_id, section_order)` and keeps output
        # byte-stable. The survivors are then re-emitted in stored order, so the
        # rows still read in musical order — only *which* rows are dropped
        # changed. `CellDiff.notes` itself is never reordered.
        ranked = sorted(range(len(diff.notes)), key=lambda i: (-diff.notes[i].total, i))
        kept = set(ranked[:_MAX_NOTE_ROWS])
        lines.extend(
            _note_row(delta, attribution_only=attribution_only)
            for i, delta in enumerate(diff.notes)
            if i in kept
        )
        elided = [delta for i, delta in enumerate(diff.notes) if i not in kept]
        if elided:
            lines.append(
                f"    … and {len(elided)} more bucket(s), "
                f"{sum(d.total for d in elided)} notes"
            )
    elif diff.first_stage is not None:
        lines.append("  notes — none (the divergence is not note-bearing)")

    if diff.metrics:
        lines.append(f"  layer-3 metrics — {len(diff.metrics)} moved:")
        by_scope: dict[str, list[MetricDelta]] = defaultdict(list)
        for delta in diff.metrics[:_MAX_METRIC_ROWS]:
            by_scope[delta.scope].append(delta)
        for scope, scoped in by_scope.items():
            rendered = "; ".join(_format_metric(delta) for delta in scoped)
            lines.append(f"    {scope}: {rendered}")
        elided_metrics = len(diff.metrics) - _MAX_METRIC_ROWS
        if elided_metrics > 0:
            lines.append(f"    … and {elided_metrics} more metric delta(s)")

    return lines


def format_report(results: Sequence[CellDiff]) -> str:
    """The §8.2 human report for a whole bless run — a string, never printed.

    Cells are emitted in the order given (the caller owns cell ordering, and
    `corpus.corpus_cells()` is already deterministic). Clean cells are summarized
    in one trailing count rather than listed, so a one-cell regression in a
    24-cell corpus reads as one stanza. **No raw JSON ever appears here.**
    """
    total = len(results)
    dirty = [diff for diff in results if not diff.clean]
    first_captures = [diff for diff in results if diff.missing_baseline]

    if not dirty:
        return f"bless report — {total} cell(s), no divergence."

    header = f"bless report — {total} cell(s), {len(dirty)} needing review"
    if first_captures:
        header += f" ({len(first_captures)} first capture(s))"
    lines = [header, ""]

    for diff in dirty:
        lines.extend(_cell_lines(diff))
        lines.append("")

    clean = total - len(dirty)
    lines.append(f"{clean} cell(s) clean.")

    stage_counts: dict[str, int] = defaultdict(int)
    for diff in dirty:
        if diff.first_stage is not None:
            stage_counts[diff.first_stage] += 1
    if stage_counts:
        summary = ", ".join(
            f"{stage}: {stage_counts[stage]}"
            for stage in STAGES
            if stage in stage_counts
        )
        lines.append(f"first divergent stage tally — {summary}")

    return "\n".join(lines)
