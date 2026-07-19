"""Tests for the Layer-3 statistical metrics + band computation (PHASE_8 §8.1;
SESSION_16 T4).

Layer 3 is WARN-ONLY, BATCH-ONLY: `compute_metrics` grounds the six MusPy-shaped
metrics in the final `TrackDocument`; `compute_bands` turns a batch into
`mean ± 2.5·pstdev` bands per `(pack, mood)`. The suite (`quality/suite.py`) must
*not* import Layer 3 — it is not a per-render check.
"""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from trackgen.pipeline.trace import generate_trace
from trackgen.quality import suite
from trackgen.quality.calibration import (
    Band,
    Calibration,
    PackMoodCalibration,
    _pmc_from_yaml_dict,
    calibration_to_yaml_dict,
    compute_bands,
    load_calibration,
    pack_and_mood,
)
from trackgen.quality.layer3 import Metrics, TrackMetrics, compute_metrics

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}

_TICKS_PER_BAR = 1920


# ---------------------------------------------------------------------------
# compute_metrics — real traces, six metrics, one exact hand-check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_compute_metrics_has_six_metrics_with_sane_shapes(
    params: dict[str, object],
) -> None:
    trace = generate_trace(params)
    metrics = compute_metrics(trace)

    assert metrics["n_bars"] > 0
    assert metrics["tracks"], "every doc has at least one track"
    # groove is song-wide over the drum tracks — a real multi-bar doc has it.
    assert isinstance(metrics["groove_consistency"], float)

    for track in trace.document.tracks:
        tm = metrics["tracks"][track.id]
        assert tm["role"] == track.role
        assert tm["note_density"] >= 0.0
        assert 0.0 <= tm["empty_bar_rate"] <= 1.0
        if tm["mean_ioi"] is not None:
            assert tm["mean_ioi"] >= 0.0
        if tm["pitch_range"] is not None:
            assert tm["pitch_range"] >= 0
        if tm["scale_consistency"] is not None:
            assert 0.0 <= tm["scale_consistency"] <= 1.0


def test_note_density_is_notes_over_bars_exact() -> None:
    """Hand-check the note-density metric = len(notes) / n_bars, exactly, for a
    known track (bass), deriving both operands from the document itself."""
    trace = generate_trace(_POP)
    metrics = compute_metrics(trace)

    n_bars = trace.document.sections[-1].end_tick // _TICKS_PER_BAR
    assert metrics["n_bars"] == n_bars

    bass = next(t for t in trace.document.tracks if t.id == "bass")
    assert metrics["tracks"]["bass"]["note_density"] == len(bass.notes) / n_bars


def test_pitched_only_metrics_skip_percussion_and_noise() -> None:
    """The NoiseSynth snare (all midi None) has no pitch range; scale-consistency
    is a non-drum pitched metric, so every drum voice-track reports None."""
    trace = generate_trace(_POP)
    metrics = compute_metrics(trace)

    assert metrics["tracks"]["snare"]["pitch_range"] is None
    for track in trace.document.tracks:
        if track.role == "drums":
            assert metrics["tracks"][track.id]["scale_consistency"] is None


def test_mean_ioi_undefined_for_single_note_track() -> None:
    """A track with < 2 notes has no inter-onset interval -> mean_ioi is None."""
    trace = generate_trace(_POP)
    doc = trace.document
    one_note = next(
        (t for t in doc.tracks if len(t.notes) == 1),
        None,
    )
    if one_note is None:
        pytest.skip("no single-note track in this render")
    assert compute_metrics(trace)["tracks"][one_note.id]["mean_ioi"] is None


# ---------------------------------------------------------------------------
# pack_and_mood — the (pack, mood) key C3 groups a batch by
# ---------------------------------------------------------------------------


def test_pack_and_mood_reads_explicit_param() -> None:
    trace = generate_trace(_JAZZ)
    assert pack_and_mood(trace) == ("jazz", "melancholic")


def test_pack_and_mood_falls_back_to_pack_default() -> None:
    trace = generate_trace(_POP)  # no `mood` param
    pack, mood = pack_and_mood(trace)
    assert pack == "pop_rock"
    assert isinstance(mood, str) and mood


# ---------------------------------------------------------------------------
# compute_bands — mean ± 2.5·SD arithmetic, exactly
# ---------------------------------------------------------------------------


def _track_metrics(role: str, note_density: float) -> TrackMetrics:
    return cast(
        TrackMetrics,
        {
            "role": role,
            "note_density": note_density,
            "mean_ioi": None,
            "pitch_range": None,
            "empty_bar_rate": 0.0,
            "scale_consistency": None,
        },
    )


def _metrics(note_density: float, groove: float | None) -> Metrics:
    return cast(
        Metrics,
        {
            "n_bars": 8,
            "tracks": {"bass": _track_metrics("bass", note_density)},
            "groove_consistency": groove,
        },
    )


def test_compute_bands_reproduces_mean_plus_minus_2_5_sd() -> None:
    """Per-track note-density values [2, 4, 4, 6] -> mean 4, pstdev sqrt(2),
    band = (4 - 2.5·sqrt2, 4 + 2.5·sqrt2). Exact arithmetic."""
    batch = [_metrics(v, None) for v in (2.0, 4.0, 4.0, 6.0)]
    pmc = compute_bands(batch)

    sqrt2 = 2.0**0.5
    band = pmc.note_density["bass"]
    assert band.lo == pytest.approx(4.0 - 2.5 * sqrt2)
    assert band.hi == pytest.approx(4.0 + 2.5 * sqrt2)

    # empty_bar_rate was a constant 0.0 -> a zero-width band, not omitted.
    assert pmc.empty_bar_rate["bass"] == Band(lo=0.0, hi=0.0)
    # metrics that were all None across the batch are omitted entirely.
    assert pmc.mean_ioi == {}
    assert pmc.scale_consistency == {}
    assert pmc.groove_consistency is None
    # C2 defaults present until C3 writes a pack-specific override.
    assert pmc.l2_thresholds == {"bass": 0.95, "comping": 0.98}


def test_compute_bands_groove_is_song_wide() -> None:
    """Groove is one value per render; the band is over those [10, 20] ->
    mean 15, pstdev 5, band (2.5, 27.5)."""
    batch = [_metrics(3.0, 10.0), _metrics(3.0, 20.0)]
    pmc = compute_bands(batch)
    assert pmc.groove_consistency == Band(lo=2.5, hi=27.5)


def test_compute_bands_accepts_raw_traces() -> None:
    trace = generate_trace(_POP)
    pmc = compute_bands([trace])
    # single-render batch -> zero-width bands (pstdev of one value is 0).
    assert pmc.note_density["bass"].lo == pmc.note_density["bass"].hi
    assert isinstance(pmc, PackMoodCalibration)


# ---------------------------------------------------------------------------
# load_calibration — the C2 None branch (no file on disk yet)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pack", ["pop_rock", "jazz"])
def test_load_calibration_returns_none_when_absent(pack: str) -> None:
    assert load_calibration(pack) is None


def test_calibration_to_yaml_dict_shape() -> None:
    """The serialized dict C3 will dump is camelCase with the pinned band keys."""
    pmc = compute_bands([_metrics(v, 5.0) for v in (2.0, 4.0)])
    cal = Calibration(pack="pop_rock", moods={"happy": pmc})
    payload = calibration_to_yaml_dict(cal)
    assert payload["pack"] == "pop_rock"
    cell = payload["moods"]["happy"]
    assert cell["l2Thresholds"] == {"bass": 0.95, "comping": 0.98}
    assert "noteDensity" in cell["bands"]
    groove = pmc.groove_consistency
    assert groove is not None
    assert cell["bands"]["grooveConsistency"] == [groove.lo, groove.hi]


def test_calibration_yaml_dict_round_trips_through_pmc_reader() -> None:
    """A computed `PackMoodCalibration` survives the write/read round trip:
    `compute_bands` -> `calibration_to_yaml_dict` -> `_pmc_from_yaml_dict`
    reproduces the same cell (bands + L2 thresholds), covering the deserialization
    path (`_pmc_from_yaml_dict`/`_band_from_pair`) the C3 reader relies on."""
    batch = [_metrics(v, g) for v, g in ((2.0, 10.0), (4.0, 20.0), (6.0, 30.0))]
    pmc = compute_bands(batch)
    # non-trivial: a real spread of bands + a groove band, not all zero-width.
    assert pmc.note_density["bass"].lo != pmc.note_density["bass"].hi
    assert pmc.groove_consistency is not None

    cal = Calibration(pack="pop_rock", moods={"mysterious": pmc})
    body = calibration_to_yaml_dict(cal)["moods"]["mysterious"]
    parsed = _pmc_from_yaml_dict(body)

    assert parsed == pmc


# ---------------------------------------------------------------------------
# Layer 3 is batch-only — the per-render suite must not import it
# ---------------------------------------------------------------------------


def test_suite_does_not_wire_in_layer3() -> None:
    src = inspect.getsource(suite)
    assert "layer3" not in src
    assert "calibration" not in src
