"""Layer 2 — musical rule checks (PHASE_8 §8.1; SESSION_16 §4).

Two musical checks over `(doc, trace)`, split by severity: L2-1 is a **FAIL**
(gates a render as invalid), L2-2 is a **WARN** (non-gating). The suite realizes
that split by calling `layer2_failures` (L2-1) into its gating result and
`layer2_warnings` (L2-2) into its separate soft-warning result.

- **L2-1** chord-tone-on-strong-beat ratio (**FAIL** below threshold) —
  `layer2_failures`. For the fraction of a role's strong-beat notes whose pitch
  class lies in the governing chord's tones ∪ chord-scale, the ratio must clear
  the role threshold. The strong-beat sets are asymmetric (§8.1, confirmed §4):
  **bass** = beat 1 only (`ticks % 1920 == 0`); **comping** = strong beats 1 & 3
  (`ticks % 1920 in {0, 960}`).
- **L2-2** voice crossing (**WARN**) — `layer2_warnings`. At every
  *voiced-sonority* instant — a tick where a bass note AND a comping note are both
  struck (a shared onset) — `max(sounding bass midi) < min(sounding comping midi)`
  must hold; otherwise the voices cross and a warning is emitted. Warnings do NOT
  gate a render as invalid; they carry the `"L2-2:"` prefix. See the crossing-grain
  note on `_check_l2_2_voice_crossing`.

Thresholds are engine defaults in C2 (bass 0.95 / comping 0.98). `calibration.yaml`
does not exist yet (it is written by C3's `trackgen calibrate`), so the
`load_l2_thresholds` read-hook returns `None` and the defaults are used.
"""

from __future__ import annotations

from trackgen.packs.loader import STYLES_ROOT
from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality._common import governing_chord
from trackgen.schema.document import TrackDocument
from trackgen.theory.chords import chord_tones, scale_pcs

# PHASE_1: PPQ 480, 4/4 — one beat is 480 ticks, one bar 1920 ticks.
_TICKS_PER_BEAT = 480
_TICKS_PER_BAR = 1920

# Bar-relative strong-beat onsets: beat 1 at 0, beat 3 at 960 (2 * 480).
_BEAT_1 = 0
_BEAT_3 = 2 * _TICKS_PER_BEAT

# Engine-default L2-1 thresholds (SESSION_16 §4; C3 overrides via calibration.yaml).
_BASS_THRESHOLD = 0.95
_COMPING_THRESHOLD = 0.98

# Strong-beat set per role, as bar-relative onset residues.
_STRONG_BEATS: dict[str, frozenset[int]] = {
    "bass": frozenset({_BEAT_1}),
    "comping": frozenset({_BEAT_1, _BEAT_3}),
}


def load_l2_thresholds(pack: str) -> tuple[float, float] | None:
    """Read `(bass, comping)` L2-1 thresholds from a pack's `calibration.yaml`.

    Returns `None` when the file is absent — which is always the case in C2
    (`trackgen calibrate` writes it in C3). A `None` return signals the caller to
    fall back to the engine defaults `(0.95, 0.98)`. The read path is kept thin on
    purpose; every C2 test exercises the defaults branch.
    """
    path = STYLES_ROOT / pack / "calibration.yaml"
    if not path.is_file():
        return None
    import yaml  # local import: only reached once C3 authors the file

    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        return None
    l2 = data.get("l2")
    if not isinstance(l2, dict):
        return None
    bass = l2.get("bass_strong_beat_ratio")
    comping = l2.get("comping_strong_beat_ratio")
    if not isinstance(bass, int | float) or not isinstance(comping, int | float):
        return None
    return float(bass), float(comping)


def _check_l2_1_chord_tone_ratio(
    doc: TrackDocument, trace: GenerationTrace
) -> list[str]:
    """FAIL if a role's strong-beat chord-tone ratio falls below its threshold.

    For each strong-beat note (per-role beat set), the allowed pitch classes are
    the governing chord's tones ∪ its chord-scale. A note whose governing chord is
    undefined is skipped (excluded from both numerator and denominator) — with no
    chord in force there is no set to measure it against, and a real render always
    has a governing chord for every in-section note. A role with zero strong-beat
    notes is skipped entirely (no division)."""
    pack = trace.plan.style_pack.id
    loaded = load_l2_thresholds(pack)
    bass_threshold, comping_threshold = (
        loaded if loaded is not None else (_BASS_THRESHOLD, _COMPING_THRESHOLD)
    )
    thresholds = {"bass": bass_threshold, "comping": comping_threshold}

    violations: list[str] = []
    for track in doc.tracks:
        strong = _STRONG_BEATS.get(track.role)
        if strong is None:
            continue
        total = 0
        in_set = 0
        for note in track.notes:
            if note.midi is None:
                continue
            if note.ticks % _TICKS_PER_BAR not in strong:
                continue
            chord = governing_chord(trace, note.ticks)
            if chord is None:
                continue
            total += 1
            allowed = set(chord_tones(chord.chord)) | set(
                scale_pcs(chord.scale.root_pc, chord.scale.name)
            )
            if note.midi % 12 in allowed:
                in_set += 1
        if total == 0:
            continue
        ratio = in_set / total
        threshold = thresholds[track.role]
        if ratio < threshold:
            violations.append(
                f"L2-1: track '{track.id}' (role={track.role}) chord-tone ratio "
                f"{ratio:.3f} on {total} strong-beat note(s) is below threshold "
                f"{threshold:.3f} ({in_set}/{total} in-set)"
            )
    return violations


def _check_l2_2_voice_crossing(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """WARN when bass and comping cross at a voiced-sonority instant.

    Crossing is evaluated at each *shared onset* — a tick where both a bass note
    and a comping note are struck — comparing the highest bass and lowest comping
    pitch then sounding (`[ticks, ticks + duration_ticks)`). A warn fires when
    `max(sounding bass) >= min(sounding comping)`. One message per crossing tick.

    Crossing-grain note (SESSION_16 §4 deviation, flagged for T5): a naive sweep
    over *every* sustained temporal overlap flags the two lines whenever a walking
    bass note simply sustains past an independently-timed comping stab — on the
    jazz reference that is 44 such instants, 0 of which cross when the two voices
    are actually struck together. Those are the normal rhythmic independence of a
    walking bass and a comping part, not a crossed voicing. Voice crossing is a
    property of a voiced sonority, so it is checked where the voices co-attack;
    this keeps both reference packs clean while still firing on a genuine crossing
    (a bass note voiced at/above a co-struck comping note). Limitation: a bass note
    rising at/above a purely sustained comping chord with no shared onset is not
    caught by this grain."""
    bass_notes = [
        (n.ticks, n.ticks + n.duration_ticks, n.midi)
        for track in doc.tracks
        if track.role == "bass"
        for n in track.notes
        if n.midi is not None
    ]
    comping_notes = [
        (n.ticks, n.ticks + n.duration_ticks, n.midi)
        for track in doc.tracks
        if track.role == "comping"
        for n in track.notes
        if n.midi is not None
    ]
    if not bass_notes or not comping_notes:
        return []

    bass_onsets = {start for start, _end, _midi in bass_notes}
    comping_onsets = {start for start, _end, _midi in comping_notes}
    shared_onsets = sorted(bass_onsets & comping_onsets)

    violations: list[str] = []
    for tick in shared_onsets:
        bass_here = [midi for start, end, midi in bass_notes if start <= tick < end]
        comping_here = [
            midi for start, end, midi in comping_notes if start <= tick < end
        ]
        if not bass_here or not comping_here:
            continue
        top_bass = max(bass_here)
        bottom_comping = min(comping_here)
        if top_bass >= bottom_comping:
            violations.append(
                f"L2-2: voice crossing at ticks={tick} — sounding bass midi "
                f"{top_bass} >= comping midi {bottom_comping}"
            )
    return violations


def layer2_failures(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """L2-1 chord-tone-ratio **failures** (gating). Empty list == no failure."""
    return _check_l2_1_chord_tone_ratio(doc, trace)


def layer2_warnings(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """L2-2 voice-crossing **warnings** (non-gating). Empty list == no warning."""
    return _check_l2_2_voice_crossing(doc, trace)
