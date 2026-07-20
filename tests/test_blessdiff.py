"""Tests for the §8.2 bless diff report (`tooling/blessdiff.py`).

The synthetic fixtures here are deliberately tiny: each pair differs in exactly
one way, so a passing assertion pins one behaviour and nothing else. Several
tests are written to *fail against a plausible-but-wrong matcher* (a matcher with
no tolerance bound, one that pairs before cancelling exact onsets, or one that
coerces a `None` metric to `0`) — that is the point of them.
"""

from __future__ import annotations

from typing import Any

import pytest

from trackgen.tooling.blessdiff import (
    ABSENT,
    CellDiff,
    MetricDelta,
    NoteDelta,
    comparable_stage,
    diff_cell,
    first_divergent_stage,
    format_report,
    metric_deltas,
    note_deltas,
    section_spans,
)
from trackgen.tooling.corpus import STAGES

_BAR = 1920


# --- fixture builders ---------------------------------------------------------


def _songform(*sections: tuple[str, int, int]) -> dict[str, Any]:
    """A minimal parsed `songform.json`: `(id, start_bar, length_bars)` triples."""
    return {
        "sections": [
            {
                "id": section_id,
                "type": section_id.rsplit("-", 1)[0],
                "index": 1,
                "start_bar": start_bar,
                "length_bars": length_bars,
            }
            for section_id, start_bar, length_bars in sections
        ],
        "total_bars": sum(length for _id, _start, length in sections),
        "template_id": "t",
    }


def _note(
    ticks: int, midi: int | None = 60, dur: int = 240, vel: float = 0.8
) -> dict[str, Any]:
    """One parsed `NoteEvent` in `document.json` (aliased) shape."""
    note: dict[str, Any] = {"ticks": ticks, "durationTicks": dur, "velocity": vel}
    if midi is not None:
        note["midi"] = midi
    return note


def _doc(
    tracks: dict[str, list[dict[str, Any]]], *, version: str = "0.1.0"
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "meta": {"generatorVersion": version, "seed": "abc"},
        "sections": [],
        "tracks": [
            {"id": track_id, "role": "comping", "notes": notes}
            for track_id, notes in tracks.items()
        ],
    }


_FORM = _songform(("verse-1", 0, 4), ("chorus-1", 4, 4))


# --- S18-6: the move-matching rule -------------------------------------------


def test_move_within_tolerance_is_one_moved() -> None:
    """120 ticks (a 16th) → exactly 1 `moved`, and no add/remove."""
    base = _doc({"bass": [_note(0), _note(480), _note(960)]})
    fresh = _doc({"bass": [_note(0), _note(600), _note(960)]})

    deltas = note_deltas(base, fresh, _FORM)

    assert deltas == (
        NoteDelta("bass", "verse-1", added=0, removed=0, moved=1, changed=0),
    )


def test_move_beyond_tolerance_is_add_plus_remove_not_moved() -> None:
    """480 ticks → 1 added + 1 removed and **0 moved**.

    This is the test that proves the 240-tick bound is real. A naive matcher —
    one that pairs any two same-`(midi, duration)` notes in a bucket regardless
    of distance — reports `moved=1, added=0, removed=0` here and fails all three
    assertions. It passes `test_move_within_tolerance_is_one_moved` unchanged, so
    only this test discriminates.
    """
    base = _doc({"bass": [_note(0), _note(480), _note(1440)]})
    fresh = _doc({"bass": [_note(0), _note(960), _note(1440)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert delta.moved == 0
    assert delta.added == 1
    assert delta.removed == 1


@pytest.mark.parametrize(
    ("offset", "expect_moved"),
    [(239, True), (240, True), (241, False)],
)
def test_tolerance_boundary_is_inclusive_at_240(
    offset: int, expect_moved: bool
) -> None:
    """S18-6 says "differing by <= 240" — 240 moves, 241 does not."""
    base = _doc({"bass": [_note(960)]})
    fresh = _doc({"bass": [_note(960 + offset)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.moved == 1) is expect_moved
    assert (delta.added, delta.removed) == ((0, 0) if expect_moved else (1, 1))


def test_unchanged_neighbour_cancels_before_move_pairing() -> None:
    """An unchanged note must not be captured by a moved one.

    Baseline `[0, 1000]` vs fresh `[900, 1000]`: the note at 1000 is unchanged and
    the other genuinely vanished/appeared 900 ticks apart. A matcher that pairs by
    ascending ticks *without* cancelling exact onsets first reports
    `1 moved + 1 added + 1 removed`; the correct answer is `1 added + 1 removed`.
    """
    base = _doc({"bass": [_note(0), _note(1000)]})
    fresh = _doc({"bass": [_note(900), _note(1000)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.added, delta.removed, delta.moved) == (1, 1, 0)


def test_two_candidates_within_tolerance_pair_by_ascending_ticks() -> None:
    """S18-6's tie-break: the earlier fresh onset wins the pairing.

    The fresh onsets are deliberately asymmetric about the baseline: 900 is
    within the 240-tick tolerance and 1300 is not. Ascending pairing therefore
    consumes 900 (`~1 +1`), while a descending-preference matcher tries 1300
    first, fails the tolerance, and reports `~0 +2 -1`. A symmetric pair such as
    `[900, 1100]` would score `~1 +1` under *both* orders and so could not fail.
    """
    base = _doc({"bass": [_note(1000)]})
    fresh = _doc({"bass": [_note(900), _note(1300)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.moved, delta.added, delta.removed) == (1, 1, 0)


def test_shift_equal_to_the_onset_spacing_is_the_documented_degenerate_case() -> None:
    """Pins the known ambiguity in `_match_key_group`'s docstring.

    A uniform shift that exactly equals the inter-onset spacing makes two fresh
    onsets land on two baseline ones, so cancellation consumes them and only the
    outer pair survives: `+1 -1 ~0`, not `~3`. Both readings are true of id-less
    notes; this test exists so the choice is a pinned behaviour rather than an
    accident nobody noticed.
    """
    base = _doc({"bass": [_note(t) for t in (0, 240, 480)]})
    fresh = _doc({"bass": [_note(t) for t in (240, 480, 720)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.added, delta.removed, delta.moved) == (1, 1, 0)


def test_sub_spacing_shift_still_reports_every_note_as_moved() -> None:
    """The realistic humanizer/swing case is unaffected by the above."""
    base = _doc({"bass": [_note(t) for t in (0, 240, 480)]})
    fresh = _doc({"bass": [_note(t) for t in (60, 300, 540)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.added, delta.removed, delta.moved) == (0, 0, 3)


def test_identity_is_midi_and_duration_not_ticks_alone() -> None:
    """A same-onset note with a different pitch is add+remove, never moved."""
    base = _doc({"bass": [_note(480, midi=60)]})
    fresh = _doc({"bass": [_note(480, midi=67)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.added, delta.removed, delta.moved) == (1, 1, 0)


def test_duration_change_is_add_plus_remove() -> None:
    base = _doc({"bass": [_note(480, dur=240)]})
    fresh = _doc({"bass": [_note(480, dur=480)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.added, delta.removed, delta.moved) == (1, 1, 0)


def test_velocity_only_change_is_reported_as_changed_not_silence() -> None:
    """Velocity is outside S18-6's identity, so it must not be invisible."""
    base = _doc({"bass": [_note(480, vel=0.8)]})
    fresh = _doc({"bass": [_note(480, vel=0.5)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.added, delta.removed, delta.moved, delta.changed) == (0, 0, 0, 1)


def test_pitchless_notes_bucket_together() -> None:
    """`exclude_none` drops `midi`; an absent key and a null must match."""
    base = _doc({"drums.snare": [_note(0, midi=None)]})
    fresh = _doc({"drums.snare": [_note(120, midi=None)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.moved, delta.added, delta.removed) == (1, 0, 0)


def test_identical_documents_report_no_note_deltas() -> None:
    doc = _doc({"bass": [_note(0), _note(480)], "pads": [_note(960, midi=72)]})

    assert note_deltas(doc, doc, _FORM) == ()


# --- S18-7: section attribution ----------------------------------------------


def test_section_attribution_uses_songform_ids() -> None:
    base = _doc({"bass": [_note(0), _note(4 * _BAR)]})
    fresh = _doc({"bass": [_note(120), _note(4 * _BAR + 120)]})

    deltas = note_deltas(base, fresh, _FORM)

    assert [(d.section_id, d.moved) for d in deltas] == [
        ("verse-1", 1),
        ("chorus-1", 1),
    ]


def test_section_span_boundary_tick_goes_to_the_later_section() -> None:
    """Tick 7680 is `end` of verse-1 and `start` of chorus-1 → chorus-1."""
    spans = section_spans(_FORM)
    assert spans == [(0, 4 * _BAR, "verse-1"), (4 * _BAR, 8 * _BAR, "chorus-1")]

    base = _doc({"bass": [_note(4 * _BAR)]})
    fresh = _doc({"bass": [_note(4 * _BAR, midi=67)]})

    (delta,) = note_deltas(base, fresh, _FORM)
    assert delta.section_id == "chorus-1"


def test_section_spans_are_sorted_by_start_tick_whatever_the_file_order() -> None:
    """The sort in `section_spans` is a contract, so an unsorted file must prove it.

    Every real `songform.json` already lists its sections in musical order, so a
    fixture built from one cannot distinguish "sorted" from "left alone" — this
    is the only shape that can. Without it, deleting `spans.sort()` changes no
    observable behaviour anywhere in the suite.
    """
    scrambled = _songform(("chorus-1", 4, 4), ("verse-1", 0, 4), ("outro-1", 8, 4))

    assert section_spans(scrambled) == [
        (0, 4 * _BAR, "verse-1"),
        (4 * _BAR, 8 * _BAR, "chorus-1"),
        (8 * _BAR, 12 * _BAR, "outro-1"),
    ]


def test_notes_outside_every_span_land_in_the_unsectioned_bucket() -> None:
    """A note past the last section must be counted, never silently dropped."""
    base = _doc({"bass": [_note(99 * _BAR)]})
    fresh = _doc({"bass": []})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert delta.section_id == "(unsectioned)"
    assert (delta.removed, delta.added, delta.moved) == (1, 0, 0)


def test_unsectioned_bucket_survives_into_the_report() -> None:
    base = _doc({"bass": [_note(99 * _BAR)]})
    fresh = _doc({"bass": []})

    text = format_report(
        [
            CellDiff(
                cell_id="c",
                first_stage="document",
                diverged_stages=("document",),
                notes=note_deltas(base, fresh, _FORM),
            )
        ]
    )

    assert "(unsectioned)" in text


def test_section_rows_are_ordered_musically_not_alphabetically() -> None:
    """`verse-1` (bar 0) precedes `chorus-1` (bar 4) despite `c` < `v`."""
    base = _doc({"bass": [_note(0), _note(4 * _BAR)]})
    fresh = _doc({"bass": [_note(120), _note(4 * _BAR + 120)]})

    deltas = note_deltas(base, fresh, _FORM)

    assert [d.section_id for d in deltas] == ["verse-1", "chorus-1"]


def test_missing_track_counts_all_its_notes() -> None:
    base = _doc({"bass": [_note(0)], "pads": [_note(0, midi=72), _note(480, midi=72)]})
    fresh = _doc({"bass": [_note(0)]})

    (delta,) = note_deltas(base, fresh, _FORM)

    assert (delta.track_id, delta.removed) == ("pads", 2)


# --- first-divergent-stage localizer -----------------------------------------


def _cell(**overrides: Any) -> dict[str, Any]:
    """A whole parsed cell — every stage present, trivially distinct."""
    base: dict[str, Any] = {stage: {"v": stage} for stage in STAGES}
    base["songform"] = _FORM
    base["document"] = _doc({"bass": [_note(0)]})
    base.update(overrides)
    return base


def test_first_divergent_stage_is_none_when_identical() -> None:
    assert first_divergent_stage(_cell(), _cell()) is None


def test_first_divergent_stage_localizes_to_harmony_not_the_document() -> None:
    """A stage-3 change with an **identical** stage-9 document reads `harmony`.

    This is the payoff §8.2 stores ten boundaries for: without the localizer the
    only honest answer would be "the harmony file changed and so did seven
    others", or worse, "the document is identical, nothing happened".
    """
    baseline = _cell()
    fresh = _cell(
        harmony={"v": "harmony", "chords": ["moved"]},
        arrangement={"v": "arrangement", "x": 1},
        phrases_stage5={"v": "phrases_stage5", "x": 1},
    )

    assert baseline["document"] == fresh["document"]
    assert first_divergent_stage(baseline, fresh) == "harmony"


def test_first_divergent_stage_walks_stages_in_trace_order() -> None:
    """`plan` precedes `harmony` even though only `harmony` was edited second."""
    fresh = _cell(plan={"v": "plan", "x": 1}, harmony={"v": "harmony", "x": 1})

    assert first_divergent_stage(_cell(), fresh) == "plan"


def test_stage_present_on_only_one_side_is_divergent() -> None:
    baseline = _cell()
    fresh = {k: v for k, v in _cell().items() if k != "sound_design"}

    assert first_divergent_stage(baseline, fresh) == "sound_design"


# --- S18-8: generatorVersion exclusion ---------------------------------------


def test_generator_version_only_change_is_not_a_divergence() -> None:
    baseline = _cell(document=_doc({"bass": [_note(0)]}, version="0.1.0"))
    fresh = _cell(document=_doc({"bass": [_note(0)]}, version="0.2.0"))

    assert baseline["document"] != fresh["document"]
    assert first_divergent_stage(baseline, fresh) is None

    diff = diff_cell("pop_rock/happy/120-1ps9wxb", baseline, fresh)
    assert diff.clean
    assert format_report([diff]) == "bless report — 1 cell(s), no divergence."


def test_comparable_stage_does_not_mutate_its_input() -> None:
    doc = _doc({"bass": []}, version="0.1.0")
    stripped = comparable_stage("document", doc)

    assert "generatorVersion" not in stripped["meta"]
    assert doc["meta"]["generatorVersion"] == "0.1.0"
    assert stripped["meta"]["seed"] == "abc"


def test_other_meta_fields_still_diverge() -> None:
    """Only `generatorVersion` is excluded — a seed change is a real divergence."""
    baseline = _cell()
    fresh_doc = _doc({"bass": [_note(0)]})
    fresh_doc["meta"]["seed"] = "different"

    assert first_divergent_stage(baseline, _cell(document=fresh_doc)) == "document"


# --- Layer-3 metric deltas ----------------------------------------------------


def _metrics(**tracks: dict[str, Any]) -> dict[str, Any]:
    return {"n_bars": 8, "tracks": dict(tracks), "groove_consistency": 3.0}


def _track_metrics(**overrides: Any) -> dict[str, Any]:
    base = {
        "role": "comping",
        "note_density": 4.0,
        "mean_ioi": 240.0,
        "pitch_range": 12,
        "empty_bar_rate": 0.0,
        "scale_consistency": 1.0,
    }
    base.update(overrides)
    return base


_METRICS_STUB = _metrics(bass=_track_metrics())


def test_none_to_float_metric_transition_renders_explicitly() -> None:
    """A `None` → value transition must never read as a numeric delta from 0.

    A formatter that coerced `None` to `0` would print `0 -> 240 (+240)`, which
    asserts a fact that is false: the baseline had no IOI at all.
    """
    baseline = _metrics(bass=_track_metrics(mean_ioi=None))
    fresh = _metrics(bass=_track_metrics(mean_ioi=240.0))

    (delta,) = metric_deltas(baseline, fresh)
    assert (delta.scope, delta.metric) == ("bass", "mean_ioi")
    assert delta.baseline is None
    assert delta.fresh == 240.0

    text = format_report(
        [CellDiff(cell_id="c", first_stage="document", metrics=(delta,))]
    )
    assert "mean_ioi: null -> 240" in text
    assert "0 -> 240" not in text
    assert "+240" not in text


def test_float_to_none_metric_transition_renders_explicitly() -> None:
    baseline = _metrics(lead=_track_metrics(pitch_range=12))
    fresh = _metrics(lead=_track_metrics(pitch_range=None))

    (delta,) = metric_deltas(baseline, fresh)
    text = format_report([CellDiff(cell_id="c", metrics=(delta,))])

    assert "pitch_range: 12 -> null" in text


def test_numeric_metric_delta_carries_a_signed_change() -> None:
    baseline = _metrics(bass=_track_metrics(note_density=4.0))
    fresh = _metrics(bass=_track_metrics(note_density=3.5))

    (delta,) = metric_deltas(baseline, fresh)
    text = format_report([CellDiff(cell_id="c", metrics=(delta,))])

    assert "note_density: 4 -> 3.5 (-0.5)" in text


def test_null_on_both_sides_is_not_a_delta() -> None:
    baseline = _metrics(drums=_track_metrics(scale_consistency=None))
    fresh = _metrics(drums=_track_metrics(scale_consistency=None))

    assert metric_deltas(baseline, fresh) == ()


def test_song_wide_metrics_are_scoped_separately() -> None:
    baseline = _metrics()
    fresh = {**_metrics(), "groove_consistency": None}

    (delta,) = metric_deltas(baseline, fresh)

    assert (delta.scope, delta.metric, delta.fresh) == (
        "(song)",
        "groove_consistency",
        None,
    )


def test_track_present_on_one_side_only_renders_absent() -> None:
    baseline = _metrics()
    fresh = _metrics(pads=_track_metrics())

    deltas = metric_deltas(baseline, fresh)

    assert {d.metric for d in deltas} == {
        "role",
        "note_density",
        "mean_ioi",
        "pitch_range",
        "empty_bar_rate",
        "scale_consistency",
    }
    assert all(d.baseline is ABSENT for d in deltas)
    assert "(absent)" in format_report([CellDiff(cell_id="c", metrics=deltas)])


@pytest.mark.parametrize(
    ("side", "kwargs"),
    [
        ("baseline", {"fresh_metrics": _METRICS_STUB}),
        ("fresh", {"baseline_metrics": _METRICS_STUB}),
    ],
)
def test_half_a_metrics_pair_is_flagged_not_silently_dropped(
    side: str, kwargs: dict[str, Any]
) -> None:
    """§8.2 mandates metric deltas, so "none computed" must be visible.

    Without a marker, an unavailable metrics side is indistinguishable from
    metrics that held perfectly steady — the report understates what it knows,
    exactly as a missing `songform.json` would if it did not raise its own
    `stage_error`.
    """
    diff = diff_cell("cell", _cell(), _cell(plan={"v": "plan", "x": 1}), **kwargs)

    assert diff.stage_errors
    assert not diff.clean
    text = format_report([diff])
    assert "layer-3 metrics unavailable" in text
    assert f"({side} side missing)" in text


def test_omitting_both_metrics_sides_is_not_an_error() -> None:
    """No metrics on either side means no metric comparison was requested."""
    diff = diff_cell("cell", _cell(), _cell(plan={"v": "plan", "x": 1}))

    assert diff.stage_errors == ()


def test_identical_metrics_report_nothing() -> None:
    metrics = _metrics(bass=_track_metrics())

    assert metric_deltas(metrics, metrics) == ()


# --- Layer-3 metric elision (§8.2 caps; ROADMAP §3: no silent caps) -----------
#
# This path is live on every real run: one corpus cell carries 11 tracks, i.e. up
# to 68 metric rows against a cap of 20. Note elision is covered above; these
# tests give the metric side the same treatment.


def _metric_rows(count: int) -> tuple[MetricDelta, ...]:
    """`count` deltas, each in its own scope so each renders as its own line."""
    return tuple(
        MetricDelta(scope=f"t{i:02d}", metric="note_density", baseline=1.0, fresh=2.0)
        for i in range(count)
    )


def _rendered_metric_scopes(text: str) -> list[str]:
    return [
        line.strip().split(":")[0]
        for line in text.splitlines()
        if line.startswith("    t") and "note_density" in line
    ]


def test_metric_rows_are_capped_at_twenty() -> None:
    """25 moved metrics must print 20 rows — not 25, and not `_MAX_METRIC_ROWS` = 2.

    The header count stays exact (25); only the rows are capped. Shrinking the
    cap changes how many scopes survive, so this is what pins the constant.
    """
    diff = CellDiff(cell_id="c", first_stage="document", metrics=_metric_rows(25))

    text = format_report([diff])
    scopes = _rendered_metric_scopes(text)

    assert "layer-3 metrics — 25 moved:" in text
    assert len(scopes) == 20
    assert scopes == [f"t{i:02d}" for i in range(20)]
    assert "t20" not in text


def test_elided_metric_total_is_always_printed() -> None:
    """§8.2/ROADMAP §3 — capped rows are summarized, never silently dropped.

    Dropping the "… and N more" line (or computing N as 0) leaves a report that
    claims 25 metrics moved and shows 20 with no acknowledgement of the gap.
    """
    diff = CellDiff(cell_id="c", first_stage="document", metrics=_metric_rows(25))

    text = format_report([diff])

    assert "… and 5 more metric delta(s)" in text


def test_metric_rows_at_exactly_the_cap_are_not_elided() -> None:
    """The boundary: 20 rows print in full with no elision line at all."""
    diff = CellDiff(cell_id="c", first_stage="document", metrics=_metric_rows(20))

    text = format_report([diff])

    assert len(_rendered_metric_scopes(text)) == 20
    assert "more metric delta(s)" not in text


def test_metric_elision_is_a_head_slice_not_a_ranking() -> None:
    """Documented asymmetry: notes elide by `total`, metrics elide by head slice.

    A metric delta has no comparable "size" — `role: comping -> bass` and
    `note_density: 4 -> 3.5` are not orderable against each other, and ranking by
    a numeric change would push every `None`/`(absent)` transition (the ones
    §8.2 most wants read) to the bottom. So the metric side keeps its stored
    order, which is already meaningful: song-wide scopes first, then tracks
    alphabetically, each in §8.1 metric order. This test pins that choice so it
    stays a decision rather than an oversight.
    """
    deltas = (
        *_metric_rows(20),
        MetricDelta(scope="zzz", metric="mean_ioi", baseline=None, fresh=999.0),
    )
    diff = CellDiff(cell_id="c", first_stage="document", metrics=deltas)

    text = format_report([diff])

    # The trailing row is dropped even though it is the largest change present.
    assert "zzz" not in text
    assert "… and 1 more metric delta(s)" in text


# --- the report ---------------------------------------------------------------


def test_clean_corpus_is_a_single_line() -> None:
    results = [CellDiff(cell_id=f"cell-{i}") for i in range(24)]

    assert format_report(results) == "bless report — 24 cell(s), no divergence."


def test_empty_run_reports_cleanly() -> None:
    assert format_report([]) == "bless report — 0 cell(s), no divergence."


def test_report_names_the_first_divergent_stage_prominently() -> None:
    diff = diff_cell(
        "pop_rock/happy/120-1ps9wxb",
        _cell(),
        _cell(
            harmony={"v": "harmony", "x": 1}, arrangement={"v": "arrangement", "x": 1}
        ),
    )
    text = format_report([diff])

    assert "FIRST DIVERGENT STAGE: harmony" in text
    assert "derivative, downstream of harmony" in text
    assert "arrangement" in text


def test_report_is_small_for_a_small_diff() -> None:
    """A 3-note diff must not read like a 300-line JSON dump (§8.2)."""
    base = _doc({"bass": [_note(t) for t in (0, 480, 960, 1440)]})
    fresh = _doc({"bass": [_note(t) for t in (0, 600, 960, 1440)]})
    diff = diff_cell(
        "pop_rock/happy/120-1ps9wxb",
        _cell(document=base),
        _cell(document=fresh),
    )

    text = format_report([diff])

    assert len(text.splitlines()) <= 10
    assert "{" not in text and "}" not in text  # never a raw JSON diff
    assert "bass / verse-1: +0 -0 ~1" in text


def test_report_never_emits_raw_json_for_a_large_diff() -> None:
    base = _doc({f"t{i}": [_note(t) for t in range(0, 1920, 120)] for i in range(30)})
    fresh = _doc(
        {f"t{i}": [_note(t + 60) for t in range(0, 1920, 120)] for i in range(30)}
    )
    diff = diff_cell("cell", _cell(document=base), _cell(document=fresh))

    text = format_report([diff])

    assert "{" not in text and "}" not in text
    # 30 buckets, capped at 20 rows + an explicit elision line.
    assert "more bucket(s)" in text
    assert len(text.splitlines()) <= 32


def test_elision_keeps_the_loudest_bucket_not_the_alphabetically_first() -> None:
    """`NoteDelta.total` is the documented ranking key — so it must rank.

    21 buckets against a 20-row cap. Twenty of them are one-note changes on
    tracks that sort early (`a00`…`a19`); the twenty-first, `zzz`, holds 30. A
    formatter that slices the stored `(track_id, section_order)` order — the
    defect this pins — elides `zzz` and prints twenty single-note rows, which is
    precisely the noise-crowds-out-signal shape §8.2 forbids.
    """
    quiet = {f"a{i:02d}": [_note(0)] for i in range(20)}
    base = _doc({**quiet, "zzz": [_note(t) for t in range(0, 30 * 60, 60)]})
    fresh = _doc({**{track: [] for track in quiet}, "zzz": []})

    diff = diff_cell("cell", _cell(document=base), _cell(document=fresh))
    text = format_report([diff])

    assert len(diff.notes) == 21
    assert "zzz / verse-1: +0 -30" in text
    # Exactly one one-note bucket is the thing dropped, and it is announced.
    assert "… and 1 more bucket(s), 1 notes" in text


def test_elision_survivors_still_read_in_musical_order() -> None:
    """Ranking decides *which* rows survive, never the order they print in."""
    base = _doc(
        {
            "bass": [_note(0), _note(4 * _BAR)],
        }
    )
    fresh = _doc({"bass": [_note(120), _note(4 * _BAR + 120)]})

    diff = diff_cell("cell", _cell(document=base), _cell(document=fresh))
    rows = [line for line in format_report([diff]).splitlines() if " / " in line]

    assert [line.split(" / ")[1].split(":")[0] for line in rows] == [
        "verse-1",
        "chorus-1",
    ]


def test_pure_section_rename_is_not_reported_as_note_churn() -> None:
    """An identical document must never headline "N notes implicated".

    Renaming `verse-1` to `verse-9` moves nothing musically, but per-bucket
    attribution makes every note read as removed-from-one + added-to-another.
    The report has the signal to know better — `document` is absent from
    `diverged_stages` — and must use it, because "350 notes changed" on a
    byte-identical document is the report a tired human blesses on reflex.
    """
    document = _doc({"bass": [_note(t) for t in (0, 480, 960, 1440)]})
    baseline = _cell(songform=_songform(("verse-1", 0, 4)), document=document)
    fresh = _cell(songform=_songform(("verse-9", 0, 4)), document=document)

    diff = diff_cell("cell", baseline, fresh)
    text = format_report([diff])

    assert diff.first_stage == "songform"
    assert "document" not in diff.diverged_stages
    assert sum(d.total for d in diff.notes) == 8

    assert "section-attribution churn" in text
    assert "the document did NOT change" in text
    assert "changed which section id they fall under" in text
    # The misleading headline and its moved/velocity counters are both gone.
    assert "implicated" not in text
    assert "~" not in text


def test_a_real_note_change_still_reads_as_note_churn() -> None:
    """The M2 relabel must not swallow a genuine document divergence."""
    baseline = _cell(document=_doc({"bass": [_note(0)]}))
    fresh = _cell(document=_doc({"bass": [_note(120)]}))

    text = format_report([diff_cell("cell", baseline, fresh)])

    assert "implicated" in text
    assert "section-attribution churn" not in text


def test_clean_cells_are_summarized_not_listed() -> None:
    dirty = diff_cell("dirty", _cell(), _cell(plan={"v": "plan", "x": 1}))
    results = [CellDiff(cell_id=f"clean-{i}") for i in range(23)] + [dirty]

    text = format_report(results)

    assert "23 cell(s) clean." in text
    assert "clean-0" not in text
    assert "first divergent stage tally — plan: 1" in text


def test_missing_baseline_is_a_first_capture_not_a_divergence() -> None:
    diff = diff_cell("new-cell", None, _cell())

    assert diff.missing_baseline
    assert diff.first_stage is None

    text = format_report([diff])
    assert "first capture" in text
    assert "FIRST DIVERGENT STAGE" not in text


def test_non_note_bearing_divergence_says_so() -> None:
    diff = diff_cell("cell", _cell(), _cell(sound_design={"v": "sound_design", "x": 1}))

    text = format_report([diff])

    assert "FIRST DIVERGENT STAGE: sound_design" in text
    assert "notes — none (the divergence is not note-bearing)" in text


def test_format_report_is_byte_stable_for_identical_inputs() -> None:
    """Determinism (invariant 5): no dict/set iteration order may leak out."""
    base = _doc(
        {
            "pads": [_note(t, midi=72) for t in (0, 960)],
            "bass": [_note(t, midi=40) for t in (0, 480, 4 * _BAR)],
            "drums.kick": [_note(t, midi=None) for t in (0, 960, 4 * _BAR)],
        }
    )
    fresh = _doc(
        {
            "drums.kick": [_note(t, midi=None) for t in (60, 960, 4 * _BAR)],
            "bass": [_note(t, midi=40) for t in (0, 480, 4 * _BAR + 3000)],
            "pads": [_note(t, midi=72) for t in (0, 1080)],
        }
    )
    metrics_a = _metrics(bass=_track_metrics(), pads=_track_metrics(mean_ioi=None))
    metrics_b = _metrics(pads=_track_metrics(), bass=_track_metrics(mean_ioi=None))

    def build() -> str:
        return format_report(
            [
                diff_cell(
                    "pop_rock/happy/120-1ps9wxb",
                    _cell(document=base),
                    _cell(document=fresh),
                    baseline_metrics=metrics_a,
                    fresh_metrics=metrics_b,
                )
            ]
        )

    first = build()
    assert all(build() == first for _ in range(5))
    assert first.encode("utf-8") == build().encode("utf-8")


def test_diff_cell_reports_both_songforms_when_the_form_moved() -> None:
    """A renamed/shifted section must not silently drop its notes."""
    base_form = _songform(("verse-1", 0, 4))
    fresh_form = _songform(("intro-1", 0, 4))
    base = _cell(songform=base_form, document=_doc({"bass": [_note(0)]}))
    fresh = _cell(songform=fresh_form, document=_doc({"bass": [_note(0, midi=67)]}))

    diff = diff_cell("cell", base, fresh)

    assert diff.first_stage == "songform"
    assert {d.section_id for d in diff.notes} == {"verse-1", "intro-1"}
    assert sum(d.total for d in diff.notes) == 2


def test_stage_errors_alone_make_a_cell_unclean() -> None:
    """`CellDiff.clean`'s `stage_errors` term, isolated from every other term.

    Deliberately constructed with **no** divergent stage, no notes and no
    metrics: the partial-baseline test elsewhere also carries a divergent stage,
    so `first_stage is not None` carries its assertion and the `stage_errors`
    term could be deleted without failing anything. The term is load-bearing —
    `bless()` gates every baseline write on `not diff.clean`, and
    `_needs_version_refresh` gates the version-stamp rewrite on `diff.clean` — so
    a cell whose only finding is a stage error must never read as clean.
    """
    diff = CellDiff(cell_id="c", stage_errors=("UNREADABLE BASELINE — boom",))

    assert diff.first_stage is None
    assert diff.diverged_stages == ()
    assert diff.notes == () and diff.metrics == ()
    assert not diff.missing_baseline
    assert not diff.clean

    text = format_report([diff])
    assert "1 needing review" in text
    assert "UNREADABLE BASELINE — boom" in text
    assert "no divergence" not in text


def test_diff_cell_flags_a_missing_songform_instead_of_dropping_notes() -> None:
    base = _cell()
    fresh = {k: v for k, v in _cell().items() if k != "songform"}

    diff = diff_cell("cell", base, fresh)

    assert diff.stage_errors
    assert "songform.json missing" in format_report([diff])
