"""Tests for the Layer-2 musical checks (PHASE_8 §8.1; SESSION_16 §4, T3).

L2-1 (chord-tone-on-strong-beat ratio, FAIL) and L2-2 (voice crossing, WARN).
Fixtures follow the `test_quality_layer1.py` style: a real `generate_trace(...)`
output mutated by `model_copy` (frozen pydantic) / `dataclasses.replace` (frozen
`GenerationTrace`), so every violating fixture is one edit from a passing trace,
and each is proven discriminating (fires its own rule; a real trace passes).

The L2-1 fixtures also prove the pinned beat-set asymmetry (§4): bass measures
beat 1 only, comping measures beats 1 & 3 — so flipping bass *beat-3* notes
out-of-set changes nothing, while flipping comping *beat-3* notes fires L2-1.

**Grain (S23-1 / C-31).** L2-1 measures `trace.phrases_stage6`, not `doc.tracks`
— the humanizer displaces onsets off ticks 0/960, so a document-grain read sees
5–18 % of the population (0 % for jazz and chill_lofi comping). Every L2-1
fixture here therefore mutates the **stage-6 phrases**; the L2-2 fixtures still
mutate the document, which is L2-2's correct grain. `test_l2_1_measures_stage6_
grain_not_document_grain` pins that split and fails if the check ever reverts.
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
    _check_l2_1_unmeasurable,
    _check_l2_2_voice_crossing,
    _memoized_allowed_pitch_classes,
    allowed_pitch_classes,
    layer2_failures,
    layer2_skip_diagnostics,
    layer2_warnings,
    load_l2_thresholds,
    measure_l2_1,
)
from trackgen.quality.suite import pipeline_warnings, validate_pipeline
from trackgen.schema.ir import ChordEvent, ChordQuality, ChordSpec, EventScale
from trackgen.theory.chords import (
    EXTENSION_OFFSETS,
    chord_tones,
    legal_extensions,
    scale_pcs,
)

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


def _l2_1_skipped(messages: list[str]) -> bool:
    return any(m.startswith("L2-1-SKIP:") for m in messages)


def _l2_2_fired(messages: list[str]) -> bool:
    return any(m.startswith("L2-2:") for m in messages)


def _doc_strong_beat_count(trace: GenerationTrace, role: str) -> int:
    """Strong-beat, pitched notes of `role` visible in the **document** — i.e. the
    population the pre-S23-1 (post-humanizer) reader would have measured."""
    residues = _BEAT_1 if role == "bass" else _BEAT_1 | _BEAT_3
    return sum(
        1
        for track in trace.document.tracks
        if track.role == role
        for n in track.notes
        if n.midi is not None and n.ticks % _TICKS_PER_BAR in residues
    )


def _stage6_measured_count(trace: GenerationTrace, role: str) -> int:
    """The denominator L2-1 actually measures for `role`, summed over its tracks."""
    return sum(m.total for m in measure_l2_1(trace) if m.role == role)


def _out_of_set_midi(trace: GenerationTrace, midi: int, tick: int) -> int | None:
    """A midi near `midi` whose pitch class is outside L2-1's allowed set at
    `tick` (or `None` if the tick has no governing chord). Reads the allowed set
    from `allowed_pitch_classes` rather than recomputing it, so these fixtures
    stay genuinely out-of-set as that definition evolves (S22-13)."""
    chord = governing_chord(trace, tick)
    if chord is None:
        return None
    allowed = allowed_pitch_classes(chord)
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
    in register and does not cross into another voice). Returns `(trace, n_flipped)`.

    Mutates `phrases_stage6` — L2-1's grain since S23-1. Mutating the document
    instead would leave L2-1 completely unmoved, which is exactly what
    `test_l2_1_document_mutation_does_not_move_the_check` asserts."""
    flipped = 0
    new_phrases = []
    for phrase in trace.phrases_stage6:
        if phrase.role != role:
            new_phrases.append(phrase)
            continue
        new_notes = []
        for note in phrase.notes:
            if (
                note.midi is not None
                and note.ticks % _TICKS_PER_BAR in residues
                and (nm := _out_of_set_midi(trace, note.midi, note.ticks)) is not None
            ):
                new_notes.append(note.model_copy(update={"midi": nm}))
                flipped += 1
            else:
                new_notes.append(note)
        new_phrases.append(phrase.model_copy(update={"notes": new_notes}))
    return replace(trace, phrases_stage6=new_phrases), flipped


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
    # sanity: the reference actually has bass notes on beat 3 to flip (read at
    # L2-1's own stage-6 grain).
    bass_beat3 = [
        n
        for ph in base.phrases_stage6
        if ph.role == "bass"
        for n in ph.notes
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
# L2-1 — measurement grain (S23-1 / C-31)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "role"),
    [
        (_POP, "bass"),
        (_POP, "comping"),
        (_JAZZ, "bass"),
        (_JAZZ, "comping"),
    ],
    ids=["pop-bass", "pop-comping", "jazz-bass", "jazz-comping"],
)
def test_l2_1_measures_stage6_grain_not_document_grain(
    params: dict[str, object], role: str
) -> None:
    """L2-1's denominator is the **stage-6** strong-beat population, not the
    document's.

    The humanizer displaces onsets off ticks 0/960, so an exact-equality filter
    over `doc.tracks` sees only a fraction of the notes L2-1 is defined over —
    measured at 5-18 %, and **0 %** for jazz and chill_lofi comping, where the
    old reader's denominator collapsed to zero and the check passed vacuously.

    This test is the grain pin: it asserts the measured denominator equals the
    stage-6 population and is *strictly greater* than the document population.
    Reverting L2-1 to `doc.tracks` makes the equality fail on all four cases
    (and, for jazz comping, would put the denominator at 0)."""
    trace = generate_trace(params)

    measured = _stage6_measured_count(trace, role)
    doc_population = _doc_strong_beat_count(trace, role)

    # The stage-6 population really is the bigger one — otherwise this test
    # could not discriminate between the two readers.
    assert measured > doc_population, (
        f"{role}: stage-6 denominator {measured} must exceed the document's "
        f"{doc_population} for this pin to discriminate"
    )
    assert measured > 0

    # And the measured denominator is exactly the stage-6 strong-beat,
    # chord-governed, pitched population — recomputed here independently.
    residues = _BEAT_1 if role == "bass" else _BEAT_1 | _BEAT_3
    expected = sum(
        1
        for ph in trace.phrases_stage6
        if ph.role == role
        for n in ph.notes
        if n.midi is not None
        and n.ticks % _TICKS_PER_BAR in residues
        and governing_chord(trace, n.ticks) is not None
    )
    assert measured == expected


def test_l2_1_jazz_comping_is_measured_at_all() -> None:
    """The sharpest edge of F1: at document grain jazz comping had **zero**
    strong-beat notes in every one of 12 sampled renders, so L2-1 never applied
    its threshold to it. At stage-6 grain the denominator is large and real."""
    trace = generate_trace(_JAZZ)
    assert _doc_strong_beat_count(trace, "comping") == 0
    assert _stage6_measured_count(trace, "comping") > 100


def test_l2_1_document_mutation_does_not_move_the_check() -> None:
    """Grain pin, from the other side: corrupting every comping strong-beat note
    **in the document** leaves L2-1 silent, because the document is no longer its
    input. The identical corruption applied to `phrases_stage6` fires."""
    base = generate_trace(_POP)

    new_tracks = []
    for track in base.document.tracks:
        if track.role != "comping":
            new_tracks.append(track)
            continue
        notes = [
            n.model_copy(update={"midi": nm})
            if n.midi is not None
            and (nm := _out_of_set_midi(base, n.midi, n.ticks)) is not None
            else n
            for n in track.notes
        ]
        new_tracks.append(track.model_copy(update={"notes": notes}))
    doc_corrupted = replace(
        base, document=base.document.model_copy(update={"tracks": new_tracks})
    )

    assert layer2_failures(doc_corrupted.document, doc_corrupted) == []

    stage6_corrupted, flipped = _flip_role_strong_beats(
        base, "comping", _BEAT_1 | _BEAT_3
    )
    assert flipped > 0
    assert _l2_1_fired(layer2_failures(stage6_corrupted.document, stage6_corrupted))


# C-29's re-measurement assignment is discharged here (S23-8). The claim under
# test: at the corrected stage-6 grain the four pre-existing packs measure a
# chord-tone ratio of exactly 1.0000, identically under the narrow (pre-C-29:
# tones ∪ scale) and the widened (tones ∪ scale ∪ §6.4-legal alterations)
# allowed sets — so the S22-13 widening is provably *inert* on them and cannot
# have eroded any margin. Verified offline over 4 packs × all moods × 12 seeds ×
# 2 lengths = 1740 measured (track, role) rows: every row 1.0000, and **0 rows**
# where the widened numerator differed from the narrow one. This test pins a
# bounded sample of that surface into the default gate.
_C29_PACKS = ("pop_rock", "jazz", "chill_lofi", "blues")


@pytest.mark.parametrize("pack", _C29_PACKS)
def test_l2_1_four_packs_measure_exactly_one_at_corrected_grain(pack: str) -> None:
    """The four pre-existing packs sit at ratio 1.0000 at the corrected grain,
    for every measured role, under BOTH the widened and the narrow allowed set.

    Not a tautology: the denominators are large (hundreds of notes per role), so
    a single retargeting or voicing regression anywhere in bass/comping drops the
    ratio off 1.0 and fails this immediately."""
    seen_roles = set()
    for seed in ("1ps9wxb", "7kq2mzt"):
        trace = generate_trace(
            {
                "styleFamily": pack,
                "maxLengthSec": 180,
                "seed": seed,
            }
        )
        measurements = measure_l2_1(trace)
        assert measurements, f"{pack}: L2-1 measured no track at all"
        for m in measurements:
            assert m.total > 0, (
                f"{pack}/{m.track_id}: empty L2-1 denominator at stage-6 grain"
            )
            seen_roles.add(m.role)
            assert m.in_set == m.total, (
                f"{pack}/{m.track_id} (role={m.role}) ratio "
                f"{m.in_set / m.total:.4f} != 1.0000 ({m.in_set}/{m.total})"
            )

        # ...and the widening is inert: the narrow (pre-C-29) reader admits the
        # very same notes, so there is no margin the widening could be hiding.
        narrow_in_set = 0
        narrow_total = 0
        for ph in trace.phrases_stage6:
            residues = (
                _BEAT_1
                if ph.role == "bass"
                else (_BEAT_1 | _BEAT_3)
                if ph.role == "comping"
                else None
            )
            if residues is None:
                continue
            for n in ph.notes:
                if n.midi is None or n.ticks % _TICKS_PER_BAR not in residues:
                    continue
                chord = governing_chord(trace, n.ticks)
                if chord is None:
                    continue
                narrow_total += 1
                narrow_allowed = set(chord_tones(chord.chord)) | set(
                    scale_pcs(chord.scale.root_pc, chord.scale.name)
                )
                if n.midi % 12 in narrow_allowed:
                    narrow_in_set += 1
        assert narrow_total == sum(m.total for m in measurements)
        assert narrow_in_set == narrow_total, (
            f"{pack}: narrow reader admits {narrow_in_set}/{narrow_total} — the "
            f"S22-13 widening is NOT inert on this pack"
        )

    assert seen_roles == {"bass", "comping"}, (
        f"{pack}: expected both L2-1 roles measured, saw {sorted(seen_roles)}"
    )


# ---------------------------------------------------------------------------
# L2-1 — the empty denominator is LOUD, never silent (S23-1)
# ---------------------------------------------------------------------------


def _blank_role_notes(trace: GenerationTrace, role: str) -> GenerationTrace:
    """Drop every note of `role` from `phrases_stage6` — the role's phrases still
    exist but carry nothing, so L2-1 has nothing at all to measure."""
    return replace(
        trace,
        phrases_stage6=[
            ph.model_copy(update={"notes": []}) if ph.role == role else ph
            for ph in trace.phrases_stage6
        ],
    )


def _move_role_off_strong_beats(trace: GenerationTrace, role: str) -> GenerationTrace:
    """Nudge every `role` note one tick off its onset, so none lands on a strong
    beat. The role still sounds plenty of notes — L2-1 simply cannot measure any
    of them. This is the exact shape of the F1 defect, reproduced deliberately."""
    new_phrases = []
    for ph in trace.phrases_stage6:
        if ph.role != role:
            new_phrases.append(ph)
            continue
        notes = [
            n.model_copy(update={"ticks": n.ticks + 1})
            if n.ticks % _TICKS_PER_BAR in (_BEAT_1 | _BEAT_3)
            else n
            for n in ph.notes
        ]
        new_phrases.append(ph.model_copy(update={"notes": notes}))
    return replace(trace, phrases_stage6=new_phrases)


def test_l2_1_unmeasurable_role_is_reported_not_silent() -> None:
    """A role that sounds notes but lands none on a strong beat must be REPORTED.

    This is the defect class S23-1 repairs: the old reader hit `total == 0` and
    `continue`d, so two packs' comping was gated by a check measuring nothing and
    no caller could tell. The diagnostic carries its own `L2-1-SKIP:` prefix,
    distinct from `L2-1:`, so "failed" and "never checked" are not conflated."""
    base = generate_trace(_POP)
    trace = _move_role_off_strong_beats(base, "comping")

    # Precondition: the role still has notes, but none is measurable.
    comping = [m for m in measure_l2_1(trace) if m.role == "comping"]
    assert comping and all(m.total == 0 and m.pitched > 0 for m in comping)

    diagnostics = layer2_skip_diagnostics(trace.document, trace)
    assert _l2_1_skipped(diagnostics)
    assert any("role=comping" in m for m in diagnostics)
    # It is a diagnostic, NOT a failure message.
    assert not _l2_1_fired(diagnostics)


def test_l2_1_unmeasurable_role_does_not_gate_the_render() -> None:
    """Loud, but not fatal: the skip surfaces in `pipeline_warnings` and never in
    the `validate_pipeline` gate. A pack that legitimately never sounds a role
    must not be red-lined by a check that could not run."""
    base = generate_trace(_POP)
    trace = _move_role_off_strong_beats(base, "comping")

    warnings = pipeline_warnings(trace.document, trace)
    assert _l2_1_skipped(warnings)
    assert not _l2_1_skipped(validate_pipeline(trace.document, trace))
    assert layer2_failures(trace.document, trace) == []


def test_l2_1_role_with_no_notes_at_all_is_not_reported() -> None:
    """The diagnostic is scoped to *vacuous measurement*, not to absence. A role
    that emitted no pitched note has nothing to measure and nothing to say about
    it — reporting that would be noise on every pack lacking a role."""
    base = generate_trace(_POP)
    trace = _blank_role_notes(base, "comping")

    assert all(m.pitched == 0 for m in measure_l2_1(trace) if m.role == "comping")
    assert _check_l2_1_unmeasurable(trace.document, trace) == []


def test_l2_1_skip_diagnostic_names_the_track_and_population() -> None:
    """The message must be actionable — it names the track, the role, and how many
    pitched notes went unmeasured, so a reader can tell a dead role from a
    mis-grained check."""
    base = generate_trace(_POP)
    trace = _move_role_off_strong_beats(base, "bass")

    diagnostics = layer2_skip_diagnostics(trace.document, trace)
    assert diagnostics
    pitched = sum(m.pitched for m in measure_l2_1(trace) if m.role == "bass")
    assert any(
        m.startswith("L2-1-SKIP:") and "role=bass" in m and f"{pitched} pitched" in m
        for m in diagnostics
    )


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_no_skip_diagnostic_on_a_real_render(params: dict[str, object]) -> None:
    """The corrected grain leaves nothing unmeasured on a real render — the
    diagnostic is silent precisely where the old reader was silently vacuous."""
    trace = generate_trace(params)
    assert layer2_skip_diagnostics(trace.document, trace) == []


# ---------------------------------------------------------------------------
# L2-1 — altered tensions in the allowed set (S22-13)
# ---------------------------------------------------------------------------

# F as a root: the fusion_jazz majority auto-resolved key, and the chord over
# which a quartal comping voicing ([0, 5, 10, 15] — `theory/voicing.py`) sounds
# its top voice a minor tenth up, i.e. the ♯9.
_F = 5
_QUARTAL_TOP = 15


def _pc(root_pc: int, semitones: int) -> int:
    return (root_pc + semitones) % 12


def _retune(
    trace: GenerationTrace,
    quality: ChordQuality,
    symbol: str,
    scale_name: str,
    comping_pc: int,
) -> GenerationTrace:
    """Put every chord event on `F<quality>`/`F <scale_name>`, and every comping
    strong-beat note onto pitch class `comping_pc`.

    Gives L2-1 a comping part that is 100% one pitch class over one known
    quality, so the ratio is exactly 1.0 or 0.0 — the check's verdict is then a
    direct read of whether that pitch class is in the allowed set."""
    chords = [
        event.model_copy(
            update={
                "chord": ChordSpec(
                    root_pc=_F, quality=quality, extensions=[], symbol=symbol
                ),
                "scale": EventScale(root_pc=_F, name=scale_name),
            }
        )
        for event in trace.harmony.chords
    ]
    harmony = trace.harmony.model_copy(update={"chords": chords})

    new_phrases = []
    for phrase in trace.phrases_stage6:
        if phrase.role != "comping":
            new_phrases.append(phrase)
            continue
        notes = [
            note.model_copy(update={"midi": note.midi - (note.midi % 12) + comping_pc})
            if note.midi is not None
            and note.ticks % _TICKS_PER_BAR in (_BEAT_1 | _BEAT_3)
            else note
            for note in phrase.notes
        ]
        new_phrases.append(phrase.model_copy(update={"notes": notes}))
    return replace(trace, harmony=harmony, phrases_stage6=new_phrases)


def _comping_failed(trace: GenerationTrace) -> bool:
    return any(
        m.startswith("L2-1:") and "role=comping" in m
        for m in layer2_failures(trace.document, trace)
    )


def test_l2_1_quartal_sharp9_over_dom7_is_in_set() -> None:
    """S22-13 — the motivating case. A comping part built entirely from the ♯9
    that a quartal voicing puts on top of a dom7 passes L2-1, even though that
    pitch class is neither a chord tone nor in the chord-scale: ♯9 is a §6.4
    legal tension for dom7 (the Hendrix chord).

    Discriminating: under L2-1's pre-S22-13 allowed set (tones ∪ scale only)
    this ratio is 0.000 and the check fires — asserted directly below."""
    base = generate_trace(_POP)
    trace = _retune(base, "dom7", "F7", "mixolydian", _pc(_F, _QUARTAL_TOP))

    assert not _comping_failed(trace)

    # The pre-widening set really did exclude it, so this test fails on revert.
    old_allowed = {
        pc
        for event in trace.harmony.chords
        for pc in set(chord_tones(event.chord))
        | set(scale_pcs(event.scale.root_pc, event.scale.name))
    }
    assert _pc(_F, _QUARTAL_TOP) not in old_allowed
    # ...and it is admitted *because* §6.4 declares it legal for this quality.
    assert "#9" in legal_extensions("dom7")


def test_l2_1_still_fails_on_a_pitch_no_rule_admits() -> None:
    """The widening is not a blanket pass. The major 7th over a dom7 is not a
    chord tone, is not in F mixolydian, and is not a §6.4-legal dom7 tension —
    it is the one pitch class no term admits, and L2-1 still fails on it."""
    natural_7 = _pc(_F, 11)
    base = generate_trace(_POP)
    trace = _retune(base, "dom7", "F7", "mixolydian", natural_7)

    assert natural_7 not in allowed_pitch_classes(trace.harmony.chords[0])
    assert natural_7 not in {
        _pc(_F, EXTENSION_OFFSETS[ext]) for ext in legal_extensions("dom7")
    }
    assert _comping_failed(trace)


def test_l2_1_extension_legality_is_quality_specific() -> None:
    """Legality is read per quality, not pooled. The very pitch class that passes
    over dom7 above (♯9) is rejected over maj7, whose §6.4 set is {9, ♯11, 13} —
    so the widening cannot launder a tension across qualities."""
    sharp_9 = _pc(_F, _QUARTAL_TOP)
    assert "#9" not in legal_extensions("maj7")

    base = generate_trace(_POP)
    trace = _retune(base, "maj7", "Fmaj7", "ionian", sharp_9)

    assert sharp_9 not in allowed_pitch_classes(trace.harmony.chords[0])
    assert _comping_failed(trace)


def test_allowed_pitch_classes_is_strictly_additive() -> None:
    """Additivity, over every (quality, scale) pair the theory module defines:
    the S22-13 allowed set is always a superset of the old tones ∪ scale set, so
    no note that passed L2-1 before can fail it now."""
    from trackgen.theory.chords import QUALITY_INTERVALS, SCALE_INTERVALS

    base = generate_trace(_POP)
    event = base.harmony.chords[0]
    for quality in QUALITY_INTERVALS:
        for scale_name in SCALE_INTERVALS:
            for root in range(12):
                probe = event.model_copy(
                    update={
                        "chord": ChordSpec(
                            root_pc=root, quality=quality, extensions=[], symbol="X"
                        ),
                        "scale": EventScale(root_pc=root, name=scale_name),
                    }
                )
                old = set(chord_tones(probe.chord)) | set(
                    scale_pcs(probe.scale.root_pc, probe.scale.name)
                )
                assert old <= allowed_pitch_classes(probe)


# ---------------------------------------------------------------------------
# L2-1 — the allowed-set memo is equivalent to the uncached lookup
# ---------------------------------------------------------------------------

# `measure_l2_1` memoizes `allowed_pitch_classes` on a key built from the chord
# identity, so a wrong key silently serves one chord's allowed set for another.
# These tests are the memo's only guard: L2-1's *verdict* does not expose the
# fault (a collided set still happens to admit every note a clean render plays),
# so nothing else in this module would notice a key losing a field.


def _probe(
    event: ChordEvent,
    root: int,
    quality: ChordQuality,
    scale_name: str,
    exts: list[str],
) -> ChordEvent:
    return event.model_copy(
        update={
            "chord": ChordSpec(
                root_pc=root, quality=quality, extensions=exts, symbol="X"
            ),
            "scale": EventScale(root_pc=root, name=scale_name),
        }
    )


def test_allowed_pitch_class_memo_matches_uncached_lookup() -> None:
    """The memoized lookup returns exactly `allowed_pitch_classes(chord)` for every
    chord in a full `root × quality × scale × extensions` sweep, sharing ONE cache
    across the whole sweep.

    The shared cache is the point: it is what turns an incomplete key into an
    observable wrong answer. Any field dropped from the key makes some later probe
    read back an earlier, differently-shaped chord's set, and the equality below
    fails. Verified to kill a key missing the scale identity, a key missing the
    chord quality, and a key missing `extensions`.

    Chosen over sampling real traces because a sweep is *exhaustive over the key
    space* rather than over whichever handful of chord identities a render happens
    to emit — real packs never sound an extension their quality does not declare
    legal, which is precisely the `extensions` collision a trace-based test would
    miss."""
    from trackgen.theory.chords import QUALITY_INTERVALS, SCALE_INTERVALS

    base = generate_trace(_POP)
    event = base.harmony.chords[0]
    cache: dict[tuple[int, str, tuple[str, ...], int, str], set[int]] = {}

    checked = 0
    for root in range(12):
        for quality in QUALITY_INTERVALS:
            for scale_name in SCALE_INTERVALS:
                for exts in ([], ["b9"], ["#11"], ["b13"]):
                    probe = _probe(event, root, quality, scale_name, exts)
                    assert _memoized_allowed_pitch_classes(
                        cache, probe
                    ) == allowed_pitch_classes(probe), (
                        f"memo served a wrong allowed set for root={root} "
                        f"quality={quality} scale={scale_name} extensions={exts}"
                    )
                    checked += 1

    # Non-vacuity: the sweep really did exercise every key field, and the cache
    # really was reused (far fewer distinct keys than probes would mean the memo
    # never fired; as many keys as probes would mean it never collided-by-design).
    assert checked == 12 * len(QUALITY_INTERVALS) * len(SCALE_INTERVALS) * 4
    assert len(cache) == checked, "every probe is a distinct chord identity"


@pytest.mark.parametrize(
    "pack", ["pop_rock", "jazz", "chill_lofi", "blues", "fusion_jazz"]
)
def test_allowed_pitch_class_memo_matches_uncached_lookup_on_real_traces(
    pack: str,
) -> None:
    """The same equivalence over the chord identities real packs actually emit —
    the key space `measure_l2_1` walks in production, sharing one cache across the
    whole trace exactly as the measurement does."""
    trace = generate_trace(
        {"styleFamily": pack, "maxLengthSec": 180, "seed": "1ps9wxb"}
    )
    cache: dict[tuple[int, str, tuple[str, ...], int, str], set[int]] = {}

    for chord in trace.harmony.chords:
        assert _memoized_allowed_pitch_classes(cache, chord) == allowed_pitch_classes(
            chord
        )

    # The memo is doing real work on this trace: many chord events, few identities.
    assert len(trace.harmony.chords) > len(cache) > 0


def test_allowed_pitch_class_memo_distinguishes_illegal_extensions() -> None:
    """The narrow case that motivated putting `extensions` in the key at all.

    `extensions ⊆ legal_extensions(quality)` holds on every shipped pack, and there
    the extension's pitch class is already inside the tension term, so the memo key
    could omit `extensions` and stay inert. But `allowed_pitch_classes` is public
    and takes any `ChordEvent`: a hand-built Fmaj7 carrying a ♭9 (not a §6.4-legal
    maj7 tension) has a strictly larger allowed set than the same chord without it,
    and would collide under an `extensions`-free key."""
    base = generate_trace(_POP)
    event = base.harmony.chords[0]
    plain = _probe(event, _F, "maj7", "ionian", [])
    with_b9 = _probe(event, _F, "maj7", "ionian", ["b9"])

    assert "b9" not in legal_extensions("maj7")
    assert allowed_pitch_classes(plain) != allowed_pitch_classes(with_b9)

    cache: dict[tuple[int, str, tuple[str, ...], int, str], set[int]] = {}
    assert _memoized_allowed_pitch_classes(cache, plain) == allowed_pitch_classes(plain)
    assert _memoized_allowed_pitch_classes(cache, with_b9) == allowed_pitch_classes(
        with_b9
    )


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
