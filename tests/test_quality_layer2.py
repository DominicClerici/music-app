"""Tests for the Layer-2 musical checks (PHASE_8 §8.1; SESSION_16 §4, T3).

L2-1 (chord-tone-on-strong-beat ratio, FAIL) and L2-2 (voice crossing, WARN).
Fixtures follow the `test_quality_layer1.py` style: a real `generate_trace(...)`
output mutated by `model_copy` (frozen pydantic) / `dataclasses.replace` (frozen
`GenerationTrace`), so every violating fixture is one edit from a passing trace,
and each is proven discriminating (fires its own rule; a real trace passes).

The L2-1 fixtures also prove the pinned beat-set asymmetry (§4): bass measures
beat 1 only, comping measures beats 1 & 3 — so flipping bass *beat-3* notes
out-of-set changes nothing, while flipping comping *beat-3* notes fires L2-1.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from trackgen.pipeline.trace import GenerationTrace, generate_trace
from trackgen.quality import calibration
from trackgen.quality._common import governing_chord
from trackgen.quality.layer2 import (
    _check_l2_2_voice_crossing,
    layer2_failures,
    layer2_warnings,
    load_l2_thresholds,
)
from trackgen.quality.suite import pipeline_warnings, validate_pipeline
from trackgen.theory.chords import chord_tones, scale_pcs

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}

_TICKS_PER_BAR = 1920
_BEAT_1 = frozenset({0})
_BEAT_3 = frozenset({960})


def _l2_1_fired(messages: list[str]) -> bool:
    return any(m.startswith("L2-1:") for m in messages)


def _l2_2_fired(messages: list[str]) -> bool:
    return any(m.startswith("L2-2:") for m in messages)


def _out_of_set_midi(trace: GenerationTrace, midi: int, tick: int) -> int | None:
    """A midi near `midi` whose pitch class is outside the governing chord's
    tones ∪ scale at `tick` (or `None` if the tick has no governing chord)."""
    chord = governing_chord(trace, tick)
    if chord is None:
        return None
    allowed = set(chord_tones(chord.chord)) | set(
        scale_pcs(chord.scale.root_pc, chord.scale.name)
    )
    for offset in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
        cand = midi + offset
        if 0 <= cand <= 127 and cand % 12 not in allowed:
            return cand
    return None


def _flip_role_strong_beats(
    trace: GenerationTrace, role: str, residues: frozenset[int]
) -> tuple[GenerationTrace, int]:
    """Rewrite every `role` note at a bar-relative onset in `residues` to an
    out-of-chord pitch class (kept a few semitones from the original, so it stays
    in register and does not cross into another voice). Returns `(trace, n_flipped)`."""
    doc = trace.document
    flipped = 0
    new_tracks = []
    for track in doc.tracks:
        if track.role != role:
            new_tracks.append(track)
            continue
        new_notes = []
        for note in track.notes:
            if (
                note.midi is not None
                and note.ticks % _TICKS_PER_BAR in residues
                and (nm := _out_of_set_midi(trace, note.midi, note.ticks)) is not None
            ):
                new_notes.append(note.model_copy(update={"midi": nm}))
                flipped += 1
            else:
                new_notes.append(note)
        new_tracks.append(track.model_copy(update={"notes": new_notes}))
    new_doc = doc.model_copy(update={"tracks": new_tracks})
    return replace(trace, document=new_doc), flipped


# ---------------------------------------------------------------------------
# Clean on real traces + threshold read-hook
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_layer2_clean_on_real_trace(params: dict[str, object]) -> None:
    """Both reference packs pass Layer 2 cleanly — no L2-1 fail and no L2-2
    crossing at any co-attacked bass/comping sonority."""
    trace = generate_trace(params)
    assert layer2_failures(trace.document, trace) == []
    assert layer2_warnings(trace.document, trace) == []


def test_load_l2_thresholds_returns_none_for_absent_artifact() -> None:
    """A pack with no `calibration.yaml` reads None — the signal to fall back
    to the engine defaults (0.95 / 0.98). (Until C5 blessed the first
    artifacts, this held for the reference packs too.)"""
    assert load_l2_thresholds("no_such_pack") is None


@pytest.mark.parametrize("pack", ["pop_rock", "jazz"])
def test_load_l2_thresholds_reads_blessed_artifact(pack: str) -> None:
    """C5 (session 19) committed the first blessed `calibration.yaml` per
    reference pack; the read-hook now returns pack-specific thresholds."""
    thresholds = load_l2_thresholds(pack)
    assert thresholds is not None
    bass, comping = thresholds
    assert 0.0 < bass <= 1.0 and 0.0 < comping <= 1.0


# ---------------------------------------------------------------------------
# L2-1 — chord-tone-on-strong-beat ratio (FAIL)
# ---------------------------------------------------------------------------


def test_l2_1_bass_beat1_out_of_set_fails() -> None:
    """Flipping every bass beat-1 note out-of-set drops the ratio below 0.95."""
    base = generate_trace(_POP)
    trace, flipped = _flip_role_strong_beats(base, "bass", _BEAT_1)
    assert flipped > 0
    messages = layer2_failures(trace.document, trace)
    assert _l2_1_fired(messages)
    assert any("role=bass" in m and "below threshold 0.950" in m for m in messages)


def test_l2_1_comping_strong_beats_out_of_set_fails() -> None:
    """Flipping every comping strong-beat (1 & 3) note out-of-set fails at 0.98."""
    base = generate_trace(_POP)
    trace, flipped = _flip_role_strong_beats(base, "comping", _BEAT_1 | _BEAT_3)
    assert flipped > 0
    messages = layer2_failures(trace.document, trace)
    assert _l2_1_fired(messages)
    assert any("role=comping" in m and "below threshold 0.980" in m for m in messages)


def test_l2_1_bass_beat3_is_ignored() -> None:
    """Beat-set asymmetry (bass side): flipping every bass *beat-3* note out-of-set
    does NOT fire L2-1 — bass only measures beat 1, so beat-3 pitches are irrelevant."""
    base = generate_trace(_POP)
    # sanity: the reference actually has bass notes on beat 3 to flip.
    bass_beat3 = [
        n
        for tr in base.document.tracks
        if tr.role == "bass"
        for n in tr.notes
        if n.midi is not None and n.ticks % _TICKS_PER_BAR == 960
    ]
    assert bass_beat3, "expected bass notes on beat 3 in the reference"
    trace, flipped = _flip_role_strong_beats(base, "bass", _BEAT_3)
    assert flipped > 0
    assert not _l2_1_fired(layer2_failures(trace.document, trace))


def test_l2_1_comping_beat3_counts() -> None:
    """Beat-set asymmetry (comping side): flipping every comping *beat-3* note
    out-of-set (leaving beat 1 intact) still fires L2-1 — beat-3 notes are in
    comping's strong-beat denominator, unlike bass's."""
    base = generate_trace(_POP)
    trace, flipped = _flip_role_strong_beats(base, "comping", _BEAT_3)
    assert flipped > 0
    messages = layer2_failures(trace.document, trace)
    assert _l2_1_fired(messages)
    assert any("role=comping" in m for m in messages)


def test_l2_1_uses_calibration_yaml_threshold_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `calibration.yaml` written into a pack dir overrides the engine-default
    L2-1 thresholds: `load_l2_thresholds` returns the file's values, and L2-1
    reports against the override (0.900) rather than the 0.95/0.98 defaults.

    Reconciliation coverage (C3/T4): `load_l2_thresholds` now delegates to
    `calibration.load_calibration`, so the file uses the per-`(pack, mood)`
    artifact shape (`moods.<mood>.l2Thresholds.{bass,comping}`) that `trackgen
    calibrate` writes — proving the calibrator's thresholds are actually READ by
    L2-1 end-to-end. `_POP` carries no `mood` param, so the mood resolves to the
    pack's interpreter default (`happy` for pop_rock); the read path is on
    `calibration.STYLES_ROOT`, monkeypatched to `tmp_path` so nothing is written
    under the real `styles/` tree."""
    base = generate_trace(_POP)
    pack = base.plan.style_pack.id

    pack_dir = tmp_path / pack
    pack_dir.mkdir(parents=True)
    (pack_dir / "calibration.yaml").write_text(
        yaml.safe_dump(
            {
                "pack": pack,
                "moods": {
                    "happy": {
                        "l2Thresholds": {"bass": 0.9, "comping": 0.9},
                        "bands": {},
                    }
                },
            }
        )
    )
    monkeypatch.setattr(calibration, "STYLES_ROOT", tmp_path)

    # The read-hook now returns the file's values instead of None.
    assert load_l2_thresholds(pack) == (0.9, 0.9)

    # Drop the bass strong-beat ratio to ~0 by flipping every beat-1 note
    # out-of-set; L2-1 must report against the override threshold, not 0.95.
    trace, flipped = _flip_role_strong_beats(base, "bass", _BEAT_1)
    assert flipped > 0
    messages = layer2_failures(trace.document, trace)
    assert _l2_1_fired(messages)
    assert any("role=bass" in m and "below threshold 0.900" in m for m in messages)
    # The default threshold is NOT what L2-1 measured against.
    assert not any("below threshold 0.950" in m for m in messages)


# ---------------------------------------------------------------------------
# L2-2 — voice crossing (WARN)
# ---------------------------------------------------------------------------


def _raise_bass_above_comping(
    trace: GenerationTrace,
) -> tuple[GenerationTrace, int]:
    """Raise one bass note (at a tick where comping is co-struck, off a strong
    beat so L2-1 stays out of it) above the lowest comping note sounding there,
    creating a voice crossing at that shared-onset sonority."""
    doc = trace.document
    comping_notes = [
        (n.ticks, n.ticks + n.duration_ticks, n.midi)
        for tr in doc.tracks
        if tr.role == "comping"
        for n in tr.notes
        if n.midi is not None
    ]
    comping_onsets = {start for start, _end, _midi in comping_notes}

    for ti, track in enumerate(doc.tracks):
        if track.role != "bass":
            continue
        for ni, note in enumerate(track.notes):
            if (
                note.midi is None
                or note.ticks not in comping_onsets
                or note.ticks % _TICKS_PER_BAR == 0  # dodge bass beat-1 L2-1
            ):
                continue
            sounding = [
                midi for start, end, midi in comping_notes if start <= note.ticks < end
            ]
            if not sounding:
                continue
            new_midi = min(sounding) + 1
            new_notes = list(track.notes)
            new_notes[ni] = note.model_copy(update={"midi": new_midi})
            new_tracks = list(doc.tracks)
            new_tracks[ti] = track.model_copy(update={"notes": new_notes})
            new_doc = doc.model_copy(update={"tracks": new_tracks})
            return replace(trace, document=new_doc), note.ticks
    raise AssertionError("no co-struck bass/comping onset to cross")


def test_l2_2_crossing_warns() -> None:
    base = generate_trace(_POP)
    trace, tick = _raise_bass_above_comping(base)
    warnings = layer2_warnings(trace.document, trace)
    assert _l2_2_fired(warnings)
    assert any(m.startswith("L2-2:") and f"ticks={tick}" in m for m in warnings)
    # discriminating: the crossing is off a strong beat, so it is not an L2-1
    # failure — it lands only in warnings, never in the fail channel.
    assert not _l2_1_fired(warnings)
    assert layer2_failures(trace.document, trace) == []


def test_l2_2_isolated_from_l2_1() -> None:
    """The dedicated L2-2 check fires on the crossing fixture on its own."""
    base = generate_trace(_POP)
    trace, tick = _raise_bass_above_comping(base)
    messages = _check_l2_2_voice_crossing(trace.document, trace)
    assert any(f"ticks={tick}" in m for m in messages)


def test_l2_2_warning_does_not_gate_the_pipeline() -> None:
    """Separation proof: an L2-2 crossing lands in `pipeline_warnings` but NOT in
    the `validate_pipeline` gate — a warn never marks a render invalid."""
    base = generate_trace(_POP)
    trace, tick = _raise_bass_above_comping(base)
    warnings = pipeline_warnings(trace.document, trace)
    failures = validate_pipeline(trace.document, trace)
    assert any(m.startswith("L2-2:") and f"ticks={tick}" in m for m in warnings)
    # The crossing surfaces as a warning, never as a gating failure: no L2-2
    # message ever reaches the `validate_pipeline` gate.
    assert not any(m.startswith("L2-2:") for m in failures)
