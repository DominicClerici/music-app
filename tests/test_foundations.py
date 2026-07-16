"""PHASE_5 §3.1/§3.3/§3.4/§3.5 foundation transforms (DoD 2).

Isolated unit tests for the four pure cross-cutting transforms: energy->intensity
quantization, degree retargeting (every degree x representative qualities x
dressing tiers, all fallback rows, `push`, octave folding, `onChordChange`),
velocity/articulation, and density gating. Synthetic `ChordEvent`/`ChordSpec`/
`Register` fixtures are built in-test -- no dependency on the reference packs.
"""

from __future__ import annotations

import pytest

from trackgen.arrangement import intensity
from trackgen.parts import retarget as R
from trackgen.parts.dynamics import (
    apply_articulation,
    apply_velocity,
    articulation_scales,
    is_event_active,
)
from trackgen.parts.retarget import RetargetedNote, resolve_degree_pc, retarget_event
from trackgen.schema.ir import (
    ChordEvent,
    ChordQuality,
    ChordSpec,
    EventScale,
    Register,
)

# --- fixtures ----------------------------------------------------------------

BASS_LANE = Register(low_midi=28, high_midi=55)
BASS_REG = Register(low_midi=28, high_midi=45)
COMP_LANE = Register(low_midi=48, high_midi=71)
COMP_REG = Register(low_midi=52, high_midi=67)


def chord_event(
    root: int,
    quality: ChordQuality,
    *,
    extensions: tuple[str, ...] = (),
    bass_pc: int | None = None,
    scale: tuple[int, str] | None = None,
    start: int = 0,
    dur: int = 1920,
) -> ChordEvent:
    """A synthetic `ChordEvent`. `scale` defaults to ionian on the chord root."""
    scale_root, scale_name = scale or (root, "ionian")
    return ChordEvent(
        start_tick=start,
        duration_ticks=dur,
        section_id="s",
        chord=ChordSpec(
            root_pc=root,
            quality=quality,
            extensions=list(extensions),
            bass_pc=bass_pc,
            symbol="X",
        ),
        scale=EventScale(root_pc=scale_root, name=scale_name),
        function="T",
    )


# --- §3.1 intensity ----------------------------------------------------------


@pytest.mark.parametrize(
    ("energy", "rung"),
    [
        (0.0, 1),
        (0.29, 1),
        (0.30, 2),  # boundary opens rung 2
        (0.54, 2),
        (0.55, 3),  # boundary opens rung 3
        (0.79, 3),
        (0.80, 4),  # boundary opens rung 4
        (1.0, 4),
    ],
)
def test_intensity_boundaries(energy: float, rung: int) -> None:
    assert intensity(energy) == rung


def test_intensity_table_validates_ascending() -> None:
    from trackgen.arrangement.intensity import _IntensityTable

    with pytest.raises(ValueError, match="ascending"):
        _IntensityTable(thresholds=(0.55, 0.30, 0.80))
    with pytest.raises(ValueError, match="exactly 3"):
        _IntensityTable(thresholds=(0.30, 0.55))


# --- §3.3 degree resolution: every degree x representative qualities ---------
#
# The §3.3 degree table with its dressing-safe fallback column. A "dressing
# tier" is a chord quality the same authored pattern must resolve against as
# dressing changes qualities per mood -- so each degree is exercised against a
# bare triad, a 6th chord, a 7th chord, a half-diminished, a suspended chord,
# and an extended chord, hitting every fallback row.

C_TRIAD = chord_event(0, "maj")  # C: no 6th/7th slot -> fallbacks fire
C_MIN = chord_event(0, "min")
C_MAJ6 = chord_event(0, "maj6")
C_MIN6 = chord_event(0, "min6")
C_DOM7 = chord_event(0, "dom7")
C_MAJ7 = chord_event(0, "maj7")
D_HALFDIM = chord_event(2, "min7b5", scale=(2, "locrian_nat2"))
C_SUS4 = chord_event(0, "sus4")
C_SUS2 = chord_event(0, "sus2")
# extended: a dom7 carrying a real tension (b9), altered chord-scale
G_DOM7B9 = chord_event(7, "dom7", extensions=("b9",), scale=(7, "half_whole_dim"))


def test_degree_root_and_bass_slash() -> None:
    # non-bass roles root on rootPc; bass honors a slash bassPc (Yamaha NTT-Bass)
    slash = chord_event(0, "maj", bass_pc=4)  # C/E
    assert resolve_degree_pc("root", slash, "comping") == 0
    assert resolve_degree_pc("root", slash, "pads") == 0
    assert resolve_degree_pc("root", slash, "bass") == 4  # bass takes the slash
    assert resolve_degree_pc("root", C_TRIAD, "bass") == 0  # no slash -> rootPc


def test_degree_third_slot() -> None:
    assert resolve_degree_pc("third", C_TRIAD, "comping") == 4  # E
    assert resolve_degree_pc("third", C_MIN, "comping") == 3  # Eb
    assert resolve_degree_pc("third", C_SUS2, "comping") == 2  # sus2 -> 2nd
    assert resolve_degree_pc("third", C_SUS4, "comping") == 5  # sus4 -> 4th


def test_degree_fifth_slot() -> None:
    assert resolve_degree_pc("fifth", C_TRIAD, "comping") == 7  # G
    assert resolve_degree_pc("fifth", chord_event(0, "dim"), "comping") == 6  # b5
    assert resolve_degree_pc("fifth", chord_event(0, "aug"), "comping") == 8  # #5


def test_degree_sixth_and_fallback() -> None:
    # maj6/min6 carry a real 6th; a triad falls back to the chord-scale 6th
    assert resolve_degree_pc("sixth", C_MAJ6, "comping") == 9  # A
    assert resolve_degree_pc("sixth", C_MIN6, "comping") == 9  # A
    assert resolve_degree_pc("sixth", C_TRIAD, "comping") == 9  # ionian 6th = A
    # a min chord with a dorian scale -> dorian 6th degree = A natural
    c_dorian = chord_event(0, "min", scale=(0, "dorian"))
    assert resolve_degree_pc("sixth", c_dorian, "comping") == 9


def test_degree_seventh_and_fallbacks() -> None:
    assert resolve_degree_pc("seventh", C_DOM7, "comping") == 10  # Bb
    assert resolve_degree_pc("seventh", C_MAJ7, "comping") == 11  # B
    # maj6/min6 -> the 6th
    assert resolve_degree_pc("seventh", C_MAJ6, "comping") == 9
    assert resolve_degree_pc("seventh", C_MIN6, "comping") == 9
    # triads -> the fifth
    assert resolve_degree_pc("seventh", C_TRIAD, "comping") == 7
    assert resolve_degree_pc("seventh", C_SUS4, "comping") == 7


def test_degree_guide3_and_fallback() -> None:
    assert resolve_degree_pc("guide3", C_DOM7, "comping") == 4  # E
    assert resolve_degree_pc("guide3", C_MIN, "comping") == 3  # Eb
    # suspended chords have no guide third -> fall back to the third (sus) slot
    assert resolve_degree_pc("guide3", C_SUS4, "comping") == 5
    assert resolve_degree_pc("guide3", C_SUS2, "comping") == 2


def test_degree_guide7_and_fallback() -> None:
    assert resolve_degree_pc("guide7", C_DOM7, "comping") == 10  # Bb
    assert resolve_degree_pc("guide7", C_MAJ7, "comping") == 11  # B
    assert resolve_degree_pc("guide7", D_HALFDIM, "comping") == 0  # D+10 = C
    # triads (and 6th chords, no seventh guide tone) -> the fifth
    assert resolve_degree_pc("guide7", C_TRIAD, "comping") == 7
    assert resolve_degree_pc("guide7", C_MAJ6, "comping") == 7


def test_degree_tension_and_fallback() -> None:
    # first extensions entry via EXTENSION_OFFSETS: G dom7 b9 -> G+13 = Ab
    assert resolve_degree_pc("tension", G_DOM7B9, "comping") == 8
    # no extensions -> chord-scale 2nd degree (scale-correct 9th)
    assert resolve_degree_pc("tension", C_TRIAD, "comping") == 2  # ionian 2nd = D
    # altered scale over an extension-less dom7 -> the b9 (scale 2nd degree)
    g_alt = chord_event(7, "dom7", scale=(7, "altered"))
    assert resolve_degree_pc("tension", g_alt, "comping") == 8  # altered 2nd = Ab


def test_degree_approach_and_song_end_fallback() -> None:
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    # chromatic half-step below the NEXT event's root: below G(7) = F#(6)
    assert resolve_degree_pc("approach", c, "bass", g) == 6
    # bass honors the next event's slash bass as the target root
    g_slash = chord_event(7, "maj", bass_pc=2, start=960)  # G/D
    assert resolve_degree_pc("approach", c, "bass", g_slash) == 1  # below D(2) = Db
    # song end (no next chord) -> the governing chord's root
    assert resolve_degree_pc("approach", c, "bass", None) == 0


def test_resolve_degree_pc_rejects_chord() -> None:
    with pytest.raises(ValueError, match="voiced"):
        resolve_degree_pc("chord", C_TRIAD, "comping")


# --- §3.3 octave placement + lane folding ------------------------------------


def _one(notes: list[RetargetedNote]) -> RetargetedNote:
    assert len(notes) == 1
    return notes[0]


def test_placement_matches_worked_example() -> None:
    # PHASE_5 §9.4: pop verse-1 bass root over E major -> E2 (MIDI 40).
    e = chord_event(4, "maj")
    note = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=False,
            ticks=0,
            duration_ticks=480,
            chords=[e],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="retrigger",
        )
    )
    assert note.midi == 40


def test_octave_offset_applied() -> None:
    # pop bass rung-4 octave pop: octave=1 shifts the root up a register.
    e = chord_event(4, "maj")
    base = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=False,
            ticks=0,
            duration_ticks=240,
            chords=[e],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="retrigger",
        )
    ).midi
    popped = _one(
        retarget_event(
            degree="root",
            octave=1,
            push=False,
            ticks=0,
            duration_ticks=240,
            chords=[e],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="retrigger",
        )
    ).midi
    assert popped == base + 12


def test_octave_folding_to_low_lane_edge() -> None:
    # A pitch placed far below the lane folds up to the lowest in-lane octave.
    c = chord_event(0, "maj")
    note = _one(
        retarget_event(
            degree="root",
            octave=-4,
            push=False,
            ticks=0,
            duration_ticks=480,
            chords=[c],
            role="comping",
            lane=COMP_LANE,
            pattern_register=COMP_REG,
            on_chord_change="hold",
        )
    )
    assert COMP_LANE.low_midi <= note.midi <= COMP_LANE.high_midi
    assert note.midi == 48  # lowest C in [48, 71]


def test_octave_folding_to_high_lane_edge() -> None:
    # A pitch placed far above the lane folds down to the highest in-lane octave.
    b = chord_event(11, "maj")  # pc 11 = B; highest B in [48,71] is 71
    note = _one(
        retarget_event(
            degree="root",
            octave=4,
            push=False,
            ticks=0,
            duration_ticks=480,
            chords=[b],
            role="comping",
            lane=COMP_LANE,
            pattern_register=COMP_REG,
            on_chord_change="hold",
        )
    )
    assert COMP_LANE.low_midi <= note.midi <= COMP_LANE.high_midi
    assert note.midi == 71  # highest B (never above the C5 ceiling)


def test_fold_never_escapes_lane_soloist_ceiling() -> None:
    # Roadmap invariant 4: folding must not escape a lane (high <= 71).
    for pc in range(12):
        c = chord_event(pc, "maj")
        for octv in (-3, 0, 3):
            note = _one(
                retarget_event(
                    degree="root",
                    octave=octv,
                    push=False,
                    ticks=0,
                    duration_ticks=240,
                    chords=[c],
                    role="comping",
                    lane=COMP_LANE,
                    pattern_register=COMP_REG,
                    on_chord_change="hold",
                )
            )
            assert COMP_LANE.low_midi <= note.midi <= COMP_LANE.high_midi


def test_fold_tie_break_is_downward_and_deterministic() -> None:
    # The Yamaha note-limit fold picks the in-lane octave NEAREST the placed
    # pitch; its tie-break key `(abs(p - midi), p)` resolves ties downward. A
    # strict distance tie is unreachable through normal placement (a same-residue
    # pitch's in-lane octaves are 12 apart, so one is always strictly nearest --
    # documented in the T3 report), so this pins the helper's determinism at both
    # edges and asserts the downward tie-break directly.
    lane = Register(low_midi=48, high_midi=72)
    assert R._fold_into_lane(60, lane) == 60  # in lane already (dist 0)
    assert R._fold_into_lane(36, lane) == 48  # below lane -> lowest C
    assert R._fold_into_lane(84, lane) == 72  # above lane -> highest C
    # the tie-break key itself, exercised on a manufactured equidistant pair
    assert min([48, 72], key=lambda p: (abs(p - 60), p)) == 48  # ties resolve down


# --- §3.3 push ---------------------------------------------------------------


def test_push_resolves_to_incoming_chord() -> None:
    # Anticipation: a boundary at 960 within (720, 1200] -> sound the G chord.
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    note = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=True,
            ticks=720,
            duration_ticks=480,
            chords=[c, g],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="retrigger",
        )
    )
    assert note.midi % 12 == 7  # G, the incoming chord's root
    assert note.tags == ("push",)
    assert note.duration_ticks == 480  # whole note sounds the one chord


def test_push_no_boundary_in_span_resolves_normally() -> None:
    # No boundary inside (0, 480] -> resolve against the governing chord, still
    # tagged "push".
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    note = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=True,
            ticks=0,
            duration_ticks=480,
            chords=[c, g],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="retrigger",
        )
    )
    assert note.midi % 12 == 0  # C, the governing chord
    assert note.tags == ("push",)


def test_push_chord_degree_sounds_next_voicing() -> None:
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)

    def voicing_for(cev: ChordEvent) -> list[int]:
        return {0: [48, 52, 55], 7: [55, 59, 62]}[cev.chord.root_pc]

    notes = retarget_event(
        degree="chord",
        octave=0,
        push=True,
        ticks=720,
        duration_ticks=480,
        chords=[c, g],
        role="comping",
        lane=COMP_LANE,
        pattern_register=COMP_REG,
        on_chord_change="retrigger",
        voicing_for=voicing_for,
    )
    assert [n.midi for n in notes] == [55, 59, 62]  # the G voicing
    assert all(n.tags == ("push",) for n in notes)


def test_push_song_end_no_boundary() -> None:
    c = chord_event(0, "maj")
    note = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=True,
            ticks=0,
            duration_ticks=480,
            chords=[c],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="retrigger",
        )
    )
    assert note.midi % 12 == 0
    assert note.tags == ("push",)


# --- §3.3 onChordChange ------------------------------------------------------


def test_on_chord_change_hold() -> None:
    # Note rings as attacked over the new chord: one note, full duration, old chord.
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    note = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=False,
            ticks=720,
            duration_ticks=480,
            chords=[c, g],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="hold",
        )
    )
    assert note.ticks == 720
    assert note.duration_ticks == 480
    assert note.midi % 12 == 0  # still the C (attack) chord


def test_on_chord_change_stop() -> None:
    # Note truncates at the boundary.
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    note = _one(
        retarget_event(
            degree="root",
            octave=0,
            push=False,
            ticks=720,
            duration_ticks=480,
            chords=[c, g],
            role="bass",
            lane=BASS_LANE,
            pattern_register=BASS_REG,
            on_chord_change="stop",
        )
    )
    assert note.ticks == 720
    assert note.duration_ticks == 240  # 960 - 720
    assert note.midi % 12 == 0


def test_on_chord_change_retrigger_splits_and_reresolves() -> None:
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    notes = retarget_event(
        degree="root",
        octave=0,
        push=False,
        ticks=720,
        duration_ticks=480,
        chords=[c, g],
        role="bass",
        lane=BASS_LANE,
        pattern_register=BASS_REG,
        on_chord_change="retrigger",
    )
    assert len(notes) == 2
    first, second = notes
    assert (first.ticks, first.duration_ticks, first.midi % 12) == (720, 240, 0)
    assert (second.ticks, second.duration_ticks, second.midi % 12) == (960, 240, 7)


def test_on_chord_change_retrigger_drops_short_remainder() -> None:
    # A re-triggered remainder shorter than 60 ticks is dropped.
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    notes = retarget_event(
        degree="root",
        octave=0,
        push=False,
        ticks=900,
        duration_ticks=100,
        chords=[c, g],
        role="bass",
        lane=BASS_LANE,
        pattern_register=BASS_REG,
        on_chord_change="retrigger",
    )
    # seg 900-960 = 60 ticks (kept, C); seg 960-1000 = 40 ticks (< 60, dropped)
    assert len(notes) == 1
    assert (notes[0].ticks, notes[0].duration_ticks, notes[0].midi % 12) == (
        900,
        60,
        0,
    )


def test_on_chord_change_retrigger_drops_all_short_segments() -> None:
    # C-07: the < 60-tick drop is applied to EVERY segment, not only the
    # trailing remainder. An 80-tick note straddling a boundary (40 + 40)
    # emits ZERO notes — the whole note vanishes. Latent edge (the reference
    # banks' shortest retargeted pitched note is 120 ticks), pinned here as
    # the intended behavior.
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)
    notes = retarget_event(
        degree="root",
        octave=0,
        push=False,
        ticks=920,
        duration_ticks=80,
        chords=[c, g],
        role="bass",
        lane=BASS_LANE,
        pattern_register=BASS_REG,
        on_chord_change="retrigger",
    )
    # seg 920-960 = 40 ticks (< 60, dropped); seg 960-1000 = 40 ticks (dropped)
    assert notes == []


def test_on_chord_change_retrigger_multi_boundary() -> None:
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=480)
    a = chord_event(9, "maj", start=960)
    notes = retarget_event(
        degree="root",
        octave=0,
        push=False,
        ticks=0,
        duration_ticks=1440,
        chords=[c, g, a],
        role="bass",
        lane=BASS_LANE,
        pattern_register=BASS_REG,
        on_chord_change="retrigger",
    )
    assert [(n.ticks, n.midi % 12) for n in notes] == [(0, 0), (480, 7), (960, 9)]


def test_approach_degree_placed_below_next_root() -> None:
    # §3.3 `approach`: chromatic half-step BELOW the next chord's effective root,
    # in the octave nearest that target's own placement. Governing chord C, next
    # chord G: the next root G (pc 7) places at MIDI 31 (G1) in the bass lane;
    # the approach note is a semitone below, MIDI 30 (F#1), and stays in-lane.
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=1920)
    notes = retarget_event(
        degree="approach",
        octave=0,
        push=False,
        ticks=1000,
        duration_ticks=480,
        chords=[c, g],
        role="bass",
        lane=BASS_LANE,
        pattern_register=BASS_REG,
        on_chord_change="retrigger",
    )
    assert len(notes) == 1
    assert notes[0].midi == 30
    assert BASS_LANE.low_midi <= notes[0].midi <= BASS_LANE.high_midi


def test_chord_degree_requires_voicing_hook() -> None:
    with pytest.raises(ValueError, match="voicing_for"):
        retarget_event(
            degree="chord",
            octave=0,
            push=False,
            ticks=0,
            duration_ticks=480,
            chords=[chord_event(0, "maj")],
            role="comping",
            lane=COMP_LANE,
            pattern_register=COMP_REG,
            on_chord_change="retrigger",
        )


def test_chord_degree_retrigger_reveals_each_voicing() -> None:
    c = chord_event(0, "maj")
    g = chord_event(7, "maj", start=960)

    def voicing_for(cev: ChordEvent) -> list[int]:
        return {0: [48, 52, 55], 7: [50, 55, 59]}[cev.chord.root_pc]

    notes = retarget_event(
        degree="chord",
        octave=0,
        push=False,
        ticks=720,
        duration_ticks=480,
        chords=[c, g],
        role="pads",
        lane=COMP_LANE,
        pattern_register=COMP_REG,
        on_chord_change="retrigger",
        voicing_for=voicing_for,
    )
    first = [n for n in notes if n.ticks == 720]
    second = [n for n in notes if n.ticks == 960]
    assert [n.midi for n in first] == [48, 52, 55]
    assert [n.duration_ticks for n in first] == [240, 240, 240]
    assert [n.midi for n in second] == [50, 55, 59]


# --- §3.4 velocity -----------------------------------------------------------


def test_velocity_identity_at_neutral() -> None:
    assert apply_velocity(0.62, 0.5) == 0.62
    assert apply_velocity(0.25, 0.5) == 0.25


def test_velocity_additive_shift() -> None:
    # +0.4 * (0.8 - 0.5) = +0.12
    assert apply_velocity(0.60, 0.8) == 0.72
    # -0.4 * (0.5 - 0.2)... base 0.2 -> shift -0.12
    assert apply_velocity(0.60, 0.2) == 0.48


def test_velocity_clamps() -> None:
    # ceiling 1.0
    assert apply_velocity(0.95, 1.0) == 1.0
    # floor 0.05: authored 0.05, base 0.0 -> 0.05 - 0.2 = -0.15 -> 0.05
    assert apply_velocity(0.05, 0.0) == 0.05


def test_velocity_rounds_half_even_to_three_decimals() -> None:
    # authored 0.2225 + 0.4*(0.5-0.5)=0.2225 -> round(0.2225,3) half-even
    assert apply_velocity(0.2225, 0.5) == round(0.2225, 3)
    assert isinstance(apply_velocity(0.333333, 0.5), float)


# --- §3.4 articulation + the exemption contract ------------------------------


def test_articulation_identity_and_range() -> None:
    # identity at legato 0.5: 0.7 + 0.6*0.5 = 1.0
    assert apply_articulation(480, 0.5, scale=True) == 480
    # staccato floor x0.7
    assert apply_articulation(480, 0.0, scale=True) == round(480 * 0.7)
    # legato ceiling x1.3
    assert apply_articulation(480, 1.0, scale=True) == round(480 * 1.3)


def test_articulation_clamped_to_gap() -> None:
    # x1.3 = 624, but the gap before the next event is 500 -> clamp to 500
    assert apply_articulation(480, 1.0, scale=True, gap_ticks=500) == 500
    # when the scaled value already fits, the gap does not shorten it
    assert apply_articulation(480, 0.5, scale=True, gap_ticks=900) == 480


def test_articulation_exemption_not_scaled() -> None:
    # drums / pads / walker (scale=False): authored duration passes through.
    assert apply_articulation(480, 1.0, scale=False) == 480
    assert apply_articulation(480, 0.0, scale=False) == 480
    # still clamped to a gap when supplied (a shorter gap truncates)
    assert apply_articulation(480, 0.0, scale=False, gap_ticks=300) == 300


def test_articulation_scales_contract() -> None:
    assert articulation_scales("comping") is True
    assert articulation_scales("bass") is True  # pattern-mode bass
    assert articulation_scales("bass", bass_walking=True) is False  # the walker
    assert articulation_scales("drums") is False
    assert articulation_scales("pads") is False


# --- §3.5 density gating -----------------------------------------------------


def test_density_gating() -> None:
    # ungated events always play
    assert is_event_active(None, 0.0) is True
    assert is_event_active(None, 1.0) is True
    # gated: dropped below threshold, kept at/above (the >= boundary)
    assert is_event_active(0.70, 0.69) is False
    assert is_event_active(0.70, 0.70) is True  # kept at threshold
    assert is_event_active(0.70, 0.71) is True
    assert is_event_active(0.60, 0.842) is True
