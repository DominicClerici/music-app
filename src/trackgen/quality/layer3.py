"""Layer 3 — statistical style metrics (PHASE_8 §8.1; SESSION_16 T4).

Six MusPy-shaped metrics computed per track (per role where applicable) from the
final `TrackDocument`. Layer 3 is **WARN-ONLY, BATCH-ONLY**: it is *not* wired
into the per-render `validate_pipeline` suite (`quality/suite.py`) — its home is
the `trackgen calibrate` batch (C3) and the band computation in
`quality/calibration.py`. Distribution-comparison machinery (KLD/OA) is
explicitly not used (D9).

The six metrics (all grounded in `TrackDocument` fields, `_TICKS_PER_BAR = 1920`,
`n_bars = doc.sections[-1].end_tick // 1920`):

1. **note density** — `len(track.notes) / n_bars`, per track (each drum
   voice-track counted separately).
2. **mean IOI** — mean of successive `notes[i+1].ticks - notes[i].ticks`, per
   track. A track with < 2 notes has no inter-onset interval → reported as
   `None` (undefined, not 0).
3. **pitch range** — `max(midi) - min(midi)` over a track's pitched notes
   (`midi is not None`); a track with no pitched note (NoiseSynth snare, empty
   track) → `None`.
4. **empty-bar rate** — fraction of the song's bars in which the track has zero
   note onsets, bucketing each onset by `note.ticks // 1920`.
5. **groove consistency** — mean Hamming distance between adjacent bars'
   drum-onset vectors, computed song-wide over the document drum tracks (all
   `role == "drums"`). Onsets are floor-quantized to a 16th grid
   (step = 120 ticks → 16 slots/bar); a bar's onset vector is the binary set of
   `(voice_track_id, slot)` cells. The Hamming distance between two adjacent
   bars is the size of the symmetric difference of their onset sets; the metric
   is the mean over every consecutive bar pair. `None` when there are no drum
   tracks or fewer than 2 bars.
6. **scale consistency** — fraction of a track's pitched notes whose pitch class
   lies in the governing chord's scale (`scale_pcs(ce.scale.root_pc,
   ce.scale.name)` via `_common.governing_chord`). Computed **per pitched,
   non-drum track**: scale consistency is a pitched-harmonic-content metric, so
   drum voice-tracks (percussion trigger pitches) are excluded → `None`. Notes
   with no governing chord are dropped from the denominator.

Faithful readings resolved here (SESSION_16 §1 latitude):
- metrics 1–4 and 6 are **per-track**; metric 5 (groove) is **song-wide**;
- IOI on a < 2-note track is **undefined → `None`** (not 0);
- groove quantization is **floor** to the 16th grid so a humanized onset stays
  in the bar and slot it sounds in;
- scale consistency is **per non-drum pitched track** (MusPy scale_consistency
  is a per-track pitched metric).
"""

from __future__ import annotations

import statistics
from typing import TypedDict

from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality._common import governing_chord
from trackgen.schema.document import Role, Track
from trackgen.theory.chords import scale_pcs

_TICKS_PER_BAR = 1920
_SIXTEENTH = 120  # 120-tick step → 16 slots per bar


class TrackMetrics(TypedDict):
    """The per-track Layer-3 metrics (metric 5 is song-wide, kept on `Metrics`)."""

    role: Role
    note_density: float
    mean_ioi: float | None
    pitch_range: int | None
    empty_bar_rate: float
    scale_consistency: float | None


class Metrics(TypedDict):
    """The full Layer-3 metric bundle for one rendered document."""

    n_bars: int
    tracks: dict[str, TrackMetrics]
    groove_consistency: float | None


def compute_metrics(trace: GenerationTrace) -> Metrics:
    """Compute the six Layer-3 metrics for `trace.document` (warn/batch-only)."""
    doc = trace.document
    n_bars = doc.sections[-1].end_tick // _TICKS_PER_BAR if doc.sections else 0
    tracks: dict[str, TrackMetrics] = {
        track.id: _track_metrics(trace, track, n_bars) for track in doc.tracks
    }
    return {
        "n_bars": n_bars,
        "tracks": tracks,
        "groove_consistency": _groove_consistency(doc.tracks, n_bars),
    }


def _track_metrics(trace: GenerationTrace, track: Track, n_bars: int) -> TrackMetrics:
    notes = sorted(track.notes, key=lambda note: note.ticks)

    note_density = len(notes) / n_bars if n_bars else 0.0

    if len(notes) >= 2:
        iois = [notes[i + 1].ticks - notes[i].ticks for i in range(len(notes) - 1)]
        mean_ioi: float | None = statistics.fmean(iois)
    else:
        mean_ioi = None

    midis = [note.midi for note in notes if note.midi is not None]
    pitch_range = max(midis) - min(midis) if midis else None

    onset_bars = {note.ticks // _TICKS_PER_BAR for note in notes}
    empty = sum(1 for bar in range(n_bars) if bar not in onset_bars)
    empty_bar_rate = empty / n_bars if n_bars else 0.0

    scale_consistency: float | None = None
    if track.role != "drums" and midis:
        in_scale = 0
        total = 0
        for note in notes:
            if note.midi is None:
                continue
            chord = governing_chord(trace, note.ticks)
            if chord is None:
                continue
            total += 1
            if note.midi % 12 in scale_pcs(chord.scale.root_pc, chord.scale.name):
                in_scale += 1
        scale_consistency = in_scale / total if total else None

    return {
        "role": track.role,
        "note_density": note_density,
        "mean_ioi": mean_ioi,
        "pitch_range": pitch_range,
        "empty_bar_rate": empty_bar_rate,
        "scale_consistency": scale_consistency,
    }


def _groove_consistency(tracks: list[Track], n_bars: int) -> float | None:
    drum_tracks = [track for track in tracks if track.role == "drums"]
    if not drum_tracks or n_bars < 2:
        return None

    bars: list[set[tuple[str, int]]] = [set() for _ in range(n_bars)]
    for track in drum_tracks:
        for note in track.notes:
            bar = note.ticks // _TICKS_PER_BAR
            if 0 <= bar < n_bars:
                slot = (note.ticks % _TICKS_PER_BAR) // _SIXTEENTH
                bars[bar].add((track.id, slot))

    distances = [len(bars[bar] ^ bars[bar + 1]) for bar in range(n_bars - 1)]
    return statistics.fmean(distances) if distances else None
