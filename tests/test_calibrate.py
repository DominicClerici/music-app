"""Tests for `trackgen calibrate` (PHASE_8 §9.3; SESSION_17 T4).

`calibrate` batch-renders a pack across its moods × a small seed set, groups by
`(pack, mood)`, drives `compute_bands`, and writes `calibration.yaml`. These
tests prove the emit round-trips through `load_calibration`, matches the
documented per-`(pack, mood)` shape, is deterministic, and — the load-bearing
reconciliation proof — that the written L2 thresholds are actually READ by the
L2-1 path (closing the C2 shape divergence).

Batches are kept tiny (one mood, two seeds) so the suite stays fast, and every
write is directed at `tmp_path` — nothing is written under the committed
`styles/` tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trackgen.pipeline.trace import GenerationTrace, generate_trace
from trackgen.quality import calibration, layer2
from trackgen.quality.calibration import calibration_to_yaml_dict, load_calibration
from trackgen.quality.layer2 import layer2_failures, load_l2_thresholds
from trackgen.tooling.calibrate import calibrate

_PACK = "pop_rock"
_MOOD = "happy"
_SEEDS = ("1", "2")
_TICKS_PER_BAR = 1920


def _out(tmp_path: Path) -> Path:
    return tmp_path / _PACK / "calibration.yaml"


def test_calibrate_roundtrips_through_load_calibration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The written `calibration.yaml` reproduces the returned `Calibration` via
    `load_calibration`, with bands + l2Thresholds present for the mood."""
    cal = calibrate(_PACK, out_path=_out(tmp_path), moods=[_MOOD], seeds=_SEEDS)

    monkeypatch.setattr(calibration, "STYLES_ROOT", tmp_path)
    loaded = load_calibration(_PACK)

    assert loaded is not None
    assert loaded == cal
    assert set(loaded.moods) == {_MOOD}
    pmc = loaded.moods[_MOOD]
    assert pmc.l2_thresholds == {"bass": 0.95, "comping": 0.98}
    assert pmc.note_density  # at least one role banded


def test_calibrate_matches_documented_yaml_shape(tmp_path: Path) -> None:
    """The raw yaml matches `calibration.py`'s documented shape:
    `moods.<mood>.bands.noteDensity.<role>` and `moods.<mood>.l2Thresholds.bass`."""
    calibrate(_PACK, out_path=_out(tmp_path), moods=[_MOOD], seeds=_SEEDS)
    data = yaml.safe_load(_out(tmp_path).read_text())

    assert data["pack"] == _PACK
    cell = data["moods"][_MOOD]
    assert cell["l2Thresholds"]["bass"] == 0.95
    note_density = cell["bands"]["noteDensity"]
    assert "bass" in note_density
    lo, hi = note_density["bass"]
    assert lo <= hi


def test_calibrate_deterministic(tmp_path: Path) -> None:
    """Two runs on the same pack/seeds/moods produce byte-identical yaml."""
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    calibrate(_PACK, out_path=a, moods=[_MOOD], seeds=_SEEDS)
    calibrate(_PACK, out_path=b, moods=[_MOOD], seeds=_SEEDS)
    assert a.read_text() == b.read_text()


def test_calibrate_artifact_is_read_by_l2_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reconciliation proof: `calibrate`'s own emitted `calibration.yaml` is read
    by the L2-1 threshold lookup (same per-`(pack, mood)` shape both write and read
    use), and a non-default bass threshold in that artifact is what L2-1 measures
    against — closing the C2 divergence end-to-end."""
    cal = calibrate(_PACK, out_path=_out(tmp_path), moods=[_MOOD], seeds=_SEEDS)
    monkeypatch.setattr(calibration, "STYLES_ROOT", tmp_path)

    # The calibrator's default thresholds are read back through the L2-1 reader.
    assert load_l2_thresholds(_PACK, _MOOD) == (0.95, 0.98)

    # Rewrite only the bass threshold to a non-default value in the same shape.
    doc_dict = calibration_to_yaml_dict(cal)
    doc_dict["moods"][_MOOD]["l2Thresholds"]["bass"] = 0.5
    _out(tmp_path).write_text(yaml.safe_dump(doc_dict, sort_keys=False))
    assert load_l2_thresholds(_PACK, _MOOD) == (0.5, 0.98)

    # L2-1 reports against the artifact's 0.500, not the engine-default 0.950.
    base = generate_trace({"styleFamily": _PACK, "mood": _MOOD, "seed": "1"})
    trace, flipped = _flip_bass_beat1_out_of_set(base)
    assert flipped > 0
    messages = layer2_failures(trace.document, trace)
    assert any("role=bass" in m and "below threshold 0.500" in m for m in messages)
    assert not any("below threshold 0.950" in m for m in messages)


def _flip_bass_beat1_out_of_set(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, int]:
    """Push every bass beat-1 note to a pitch class outside the governing chord's
    tones ∪ scale, driving the bass strong-beat ratio to ~0 (mirrors the layer2
    fixture helper, kept local to this module)."""
    from dataclasses import replace

    from trackgen.quality._common import governing_chord
    from trackgen.theory.chords import chord_tones, scale_pcs

    doc = trace.document
    flipped = 0
    new_tracks = []
    for track in doc.tracks:
        if track.role != "bass":
            new_tracks.append(track)
            continue
        new_notes = []
        for note in track.notes:
            chord = (
                governing_chord(trace, note.ticks)
                if note.midi is not None and note.ticks % _TICKS_PER_BAR == 0
                else None
            )
            if chord is not None and note.midi is not None:
                allowed = set(chord_tones(chord.chord)) | set(
                    scale_pcs(chord.scale.root_pc, chord.scale.name)
                )
                nm = next(
                    (
                        note.midi + off
                        for off in (1, -1, 2, -2, 3, -3)
                        if 0 <= note.midi + off <= 127
                        and (note.midi + off) % 12 not in allowed
                    ),
                    None,
                )
                if nm is not None:
                    new_notes.append(note.model_copy(update={"midi": nm}))
                    flipped += 1
                    continue
            new_notes.append(note)
        new_tracks.append(track.model_copy(update={"notes": new_notes}))
    return replace(
        trace, document=doc.model_copy(update={"tracks": new_tracks})
    ), flipped


def test_calibrate_report_renders_expected_sections(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`report=True` prints the §9.3 human report: the mood label, a per-track
    `vel` line, and the tempo `vs manifest range` line."""
    calibrate(_PACK, out_path=_out(tmp_path), moods=[_MOOD], seeds=("1",), report=True)
    out = capsys.readouterr().out

    assert f"mood {_MOOD!r}" in out
    assert "vel " in out
    assert "vs manifest range" in out


def test_calibrate_unused_layer2_styles_root_removed() -> None:
    """Guard: layer2 no longer carries a `STYLES_ROOT` global (it delegates the
    read to `calibration.load_calibration`), so the reconciliation cannot silently
    fall back to a stale reader."""
    assert not hasattr(layer2, "STYLES_ROOT")
