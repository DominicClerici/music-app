"""Walker mechanism + structure tests (PHASE_5 §6.3, SESSION_08 T2).

Mechanism and structure over SMALL synthetic arrangements/chords — the §9.2
pipeline goldens (draw counts 9/38/37/36/7/1, note counts, excerpt pitches) are
deliberately NOT transcribed here; that is T4's independent charter. These tests
pin the algorithm's moving parts: `nearest`, lane containment, the two-feel /
four-feel rules, the fixed draw order + draw-iff-≥2 discipline, per-bar
sub-stream independence, and the authored §6.3-tail velocities/durations.

White-box helper calls (`_two_feel_bar`, `_four_feel_bar`, `_beat3`, `_beat2`,
`_beat1_decay`, `_draw_approach`) exercise the branch logic precisely; `walk` is
also driven end-to-end for the structural invariants. Some helper inputs are
intentionally contrived (e.g. an out-of-lane `beat1`) to force a defensive
branch — noted at each such test.
"""

from __future__ import annotations

import random

from trackgen.packs.models import (
    Manifest,
    StylePack,
    WalkingConfig,
)
from trackgen.parts.walker import (
    WalkNote,
    _beat1_decay,
    _beat2,
    _beat3,
    _draw_approach,
    _four_feel_bar,
    _two_feel_bar,
    nearest,
    walk,
)
from trackgen.schema.ir import (
    ArrangementEntry,
    ArrangementPlan,
    Budgets,
    ChordEvent,
    ChordSpec,
    EventScale,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Key,
    KeyRegion,
    MoodVector,
    Register,
    SectionEnding,
    SectionPhrase,
    SeedSpec,
    SongForm,
    StylePackRef,
    TimbreDirectives,
    TimeSignature,
)
from trackgen.seeds import Rng, derive, stream_seed

_MASTER = 3735928559
_OVERRIDES: dict[str, int] = {}
_BAR = 1920
_LANE = Register(low_midi=28, high_midi=55)

# Full jazz-style walking config (from styles/jazz/patterns/bass.yaml).
_WALKING = WalkingConfig(
    feel_by_intensity={1: "two", 2: "two", 3: "four", 4: "four"},
    approach_weights={"chromatic_below": 2, "diatonic": 1, "dominant": 1},
    beat1_repeat_weights={"fifth": 2, "third": 1, "root": 1},
)


# --- draw-counting / recording shims -----------------------------------------


class _CountingRandom(random.Random):
    """A seeded RNG counting `randrange` calls — one per `weighted_choice`, hence
    exactly one per draw."""

    def __init__(self, seed: int) -> None:
        super().__init__(seed)
        self.draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


class _RecordingRandom(random.Random):
    """Records the `total` (sum of weights) passed to each `randrange` and always
    returns 0 (picks the first / lowest-pitch candidate). The recorded sequence
    is the exact order draws were made in."""

    def __init__(self) -> None:
        super().__init__(0)
        self.totals: list[int] = []

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.totals.append(int(args[0]))  # type: ignore[call-overload]
        return 0


# --- fixture builders --------------------------------------------------------


def _chord(root_pc: int, quality: str, exts: list[str], symbol: str) -> ChordSpec:
    return ChordSpec(
        root_pc=root_pc,
        quality=quality,  # type: ignore[arg-type]
        extensions=exts,
        symbol=symbol,
    )


def _dm9() -> ChordSpec:
    return _chord(2, "min7", ["9"], "Dm9")


def _ev(
    start: int,
    dur: int,
    chord: ChordSpec,
    scale_root: int,
    scale_name: str,
    section_id: str = "s",
) -> ChordEvent:
    return ChordEvent(
        start_tick=start,
        duration_ticks=dur,
        section_id=section_id,
        chord=chord,
        scale=EventScale(root_pc=scale_root, name=scale_name),
        function="T",
    )


def _dm9_event(start: int, dur: int, section_id: str = "s") -> ChordEvent:
    return _ev(start, dur, _dm9(), 2, "dorian", section_id)


def _pack(
    *, bass_mode: str = "walking", walking: WalkingConfig | None = None
) -> StylePack:
    return StylePack(
        manifest=Manifest(
            format_version=1,
            id="syn",
            name="Synthetic",
            version="1",
            engine="trackgen",
            time_signatures=[(4, 4)],
            tempo_range=(60, 300),
        ),
        patterns={},
        layering_order=("drums", "bass", "comping", "pads"),
        bass_mode=bass_mode,  # type: ignore[arg-type]
        walking=walking if walking is not None else _WALKING,
    )


def _section(
    section_id: str,
    start_bar: int,
    length: int,
    energy: float,
    *,
    final: bool = False,
) -> FormSection:
    return FormSection(
        id=section_id,
        type="outro" if final else "verse",
        index=1,
        start_bar=start_bar,
        length_bars=length,
        energy=energy,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=length)],
        harmony_tag="x",
        ending=SectionEnding(tag_bars=0, close="cold") if final else None,
    )


def _entry(
    section_id: str,
    *,
    active: bool = True,
    intensity: int = 2,
    density: float = 0.5,
) -> ArrangementEntry:
    return ArrangementEntry(
        section_id=section_id,
        role="bass",
        active=active,
        intensity=intensity,
        density_budget=density,
        register=_LANE,
    )


def _plan(tempo: float = 120.0) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="syn", version="1"),
        seed=SeedSpec(master=_MASTER),
        key=Key(tonic_pc=2, mode="dorian"),
        tempo_bpm=tempo,
        time_signature=TimeSignature(numerator=4, denominator=4),
        max_length_ticks=200 * _BAR,
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=0.1,
            dynamics_base=0.5,
            dynamics_range=0.5,
            articulation_legato=0.5,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def _harmony(events: list[ChordEvent]) -> HarmonicPlan:
    return HarmonicPlan(
        chords=events,
        keys=[KeyRegion(start_tick=0, tonic_pc=2, mode="dorian")],
    )


def _rng(name: str) -> Rng:
    return Rng(derive(stream_seed(_MASTER, _OVERRIDES, "bass"), name))


# =============================================================================
# nearest + lane containment
# =============================================================================


def test_nearest_tiebreak_downward() -> None:
    # D2=38, D3=50 are equidistant from ref 44 -> the lower (38) wins.
    assert nearest(2, 44, _LANE) == 38
    # An exact-midpoint tie one octave up resolves down as well.
    assert nearest(2, 44, Register(low_midi=26, high_midi=62)) == 38


def test_nearest_always_in_lane() -> None:
    for pc in range(12):
        for ref in range(20, 70, 5):
            got = nearest(pc, ref, _LANE)
            assert _LANE.low_midi <= got <= _LANE.high_midi
            assert got % 12 == pc


def test_nearest_lowest_placement_at_lane_floor() -> None:
    # nearest(pc, lane.low) is always the lowest in-lane placement.
    assert nearest(2, _LANE.low_midi, _LANE) == 38  # lowest D in 28..55
    assert nearest(9, _LANE.low_midi, _LANE) == 33  # lowest A


# =============================================================================
# only runs for walking mode
# =============================================================================


def test_returns_empty_for_pattern_mode() -> None:
    pack = _pack(bass_mode="patterns")
    result = walk(
        ArrangementPlan(entries=[_entry("s")]),
        _harmony([_dm9_event(0, _BAR)]),
        _form_of([_section("s", 0, 4, 0.4)]),
        _plan(),
        pack,
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    assert result == {}


def _form_of(sections: list[FormSection]) -> SongForm:
    total = max(s.start_bar + s.length_bars for s in sections)
    return SongForm(sections=sections, total_bars=total, template_id="syn")


# =============================================================================
# two-feel
# =============================================================================


def test_two_feel_fifth_both_fit_draws_one() -> None:
    # Dm, section start -> beat1 = lowest D = D2 (38). Fifth below A1=33, above
    # A2=45 both in lane -> a 1:1 draw (exactly one randrange).
    rng = _CountingRandom(0)
    chords = [_dm9_event(0, _BAR)]
    notes, last = _two_feel_bar(0, chords[0], None, _LANE, 0.5, chords, 10 * _BAR, rng)
    assert notes[0].midi == 38
    assert notes[1].midi in (33, 45)
    assert last == notes[1].midi
    assert rng.draws == 1
    # Half notes, dur 960, authored two-feel velocities.
    assert [n.duration_ticks for n in notes] == [960, 960]
    assert notes[0].velocity == 0.72
    assert notes[1].velocity == 0.68


def test_two_feel_fifth_forced_no_draw() -> None:
    # Root F -> beat1 = lowest F = F1 (29). Fifth below C1=24 (out of lane),
    # above C2=36 (in) -> forced above, ZERO draws.
    rng = _CountingRandom(0)
    fmaj = _chord(5, "maj", [], "F")
    chords = [_ev(0, _BAR, fmaj, 5, "ionian")]
    notes, _ = _two_feel_bar(0, chords[0], None, _LANE, 0.5, chords, 10 * _BAR, rng)
    assert notes[0].midi == 29
    assert notes[1].midi == 36
    assert rng.draws == 0


def test_two_feel_two_chords_two_roots_no_draw() -> None:
    # A mid-bar chord change -> a half-note root for each chord, no draws.
    rng = _CountingRandom(0)
    dm = _dm9_event(0, 960)
    gm = _ev(960, 960, _chord(7, "min7", ["9"], "Gm9"), 7, "dorian")
    chords = [dm, gm]
    notes, last = _two_feel_bar(0, dm, None, _LANE, 0.5, chords, 10 * _BAR, rng)
    assert len(notes) == 2
    assert notes[0].ticks == 0 and notes[1].ticks == 960
    assert notes[0].midi % 12 == 2  # D root
    assert notes[1].midi % 12 == 7  # G root
    assert last == notes[1].midi
    assert rng.draws == 0


def test_two_feel_beat4_approach_gate() -> None:
    dm = _dm9_event(0, _BAR)
    gm = _ev(_BAR, _BAR, _chord(7, "min7", ["9"], "Gm9"), 7, "dorian")
    chords = [dm, gm]
    # density >= 0.55 AND chord changes next bar -> a beat-4 quarter approach.
    notes, _ = _two_feel_bar(0, dm, None, _LANE, 0.55, chords, 10 * _BAR, _rng("g"))
    assert len(notes) == 3
    approach = notes[2]
    assert approach.ticks == 3 * 480  # beat 4
    assert approach.duration_ticks == 480  # a quarter note
    assert approach.velocity == 0.68
    # density < 0.55 -> no approach.
    notes_lo, _ = _two_feel_bar(0, dm, None, _LANE, 0.54, chords, 10 * _BAR, _rng("g"))
    assert len(notes_lo) == 2
    # No chord change next bar -> no approach even at high density.
    same = [dm, _dm9_event(_BAR, _BAR)]
    notes_same, _ = _two_feel_bar(0, dm, None, _LANE, 0.9, same, 10 * _BAR, _rng("g"))
    assert len(notes_same) == 2


def test_two_feel_beat4_approach_is_chromatic_below_target() -> None:
    # Next bar root G -> target = nearest(G, beat1) ; approach = target-1 (folded).
    dm = _dm9_event(0, _BAR)
    gm = _ev(_BAR, _BAR, _chord(7, "min7", ["9"], "Gm9"), 7, "dorian")
    chords = [dm, gm]
    notes, _ = _two_feel_bar(0, dm, None, _LANE, 0.9, chords, 10 * _BAR, _rng("g"))
    beat1 = notes[0].midi  # 38 (D2)
    target = nearest(7, beat1, _LANE)  # nearest G to 38 = G2 = 43
    assert notes[2].midi == target - 1


# =============================================================================
# four-feel
# =============================================================================


def test_four_feel_structure_and_velocities() -> None:
    chords = [_dm9_event(0, 4 * _BAR)]
    notes, _ = _four_feel_bar(
        0,
        0,
        chords[0],
        None,
        _LANE,
        0.5,
        120.0,
        False,
        chords,
        10 * _BAR,
        _WALKING,
        _rng("a"),
    )
    assert [n.ticks for n in notes] == [0, 480, 960, 1440]
    assert [n.duration_ticks for n in notes] == [480, 480, 480, 480]
    assert notes[0].velocity == 0.75  # beat 1
    assert all(n.velocity == 0.68 for n in notes[1:])
    assert notes[0].midi % 12 == 2  # beat 1 = root D
    for n in notes:
        assert _LANE.low_midi <= n.midi <= _LANE.high_midi


def test_four_feel_beat1_root_vs_decay_draw() -> None:
    chords = [_dm9_event(0, 4 * _BAR)]
    # No decay -> beat 1 is the root.
    root_notes, _ = _four_feel_bar(
        0,
        0,
        chords[0],
        None,
        _LANE,
        0.5,
        120.0,
        False,
        chords,
        10 * _BAR,
        _WALKING,
        _rng("a"),
    )
    assert root_notes[0].midi % 12 == 2  # D
    # Decay with a single-weight config forcing `fifth` -> beat 1 is the fifth.
    only_fifth = WalkingConfig(
        feel_by_intensity=_WALKING.feel_by_intensity,
        approach_weights={"chromatic_below": 1},
        beat1_repeat_weights={"fifth": 1},
    )
    decay_notes, _ = _four_feel_bar(
        0,
        0,
        chords[0],
        None,
        _LANE,
        0.5,
        120.0,
        True,
        chords,
        10 * _BAR,
        only_fifth,
        _rng("a"),
    )
    assert decay_notes[0].midi % 12 == 9  # A = the fifth of Dm


def test_beat1_decay_single_weight_is_deterministic() -> None:
    dm = _dm9()
    for name, want_pc in (("root", 2), ("third", 5), ("fifth", 9)):
        cfg = WalkingConfig(
            feel_by_intensity=_WALKING.feel_by_intensity,
            approach_weights={"chromatic_below": 1},
            beat1_repeat_weights={name: 1},
        )
        rng = _CountingRandom(0)
        got = _beat1_decay(dm, _LANE.low_midi, cfg, _LANE, rng)
        assert got % 12 == want_pc
        assert rng.draws == 0  # singleton -> zero draws


def test_beat1_decay_multi_weight_draws_once() -> None:
    rng = _CountingRandom(0)
    _beat1_decay(_dm9(), _LANE.low_midi, _WALKING, _LANE, rng)
    assert rng.draws == 1


def test_beat3_candidates_within_seven_of_both() -> None:
    # Dm9, beat1=D2(38), target=G2(43): primary candidates are the in-lane Dm9
    # chord tones within 7 of both, excluding beat1/target.
    rng = _CountingRandom(0)
    got = _beat3(_dm9(), 38, 43, _LANE, rng)
    tones = {(2 + i) % 12 for i in (0, 3, 7, 10, 14)}  # D F A C E
    assert got % 12 in tones
    assert abs(got - 38) <= 7 and abs(got - 43) <= 7
    assert got not in (38, 43)


def test_beat3_singleton_no_draw() -> None:
    # A tight lane leaves exactly one in-lane Dm-triad tone within 7 of both.
    rng = _CountingRandom(0)
    lane = Register(low_midi=38, high_midi=44)
    dm = _chord(2, "min", [], "Dm")
    got = _beat3(dm, 38, 43, lane, rng)
    assert got == 41  # F2, the sole candidate
    assert rng.draws == 0


def test_beat3_relaxation_when_target_out_of_reach() -> None:
    # A far target empties the primary set -> relax to within 12 of beat 1.
    rng = _CountingRandom(0)
    got = _beat3(_dm9(), 38, 99, _LANE, rng)
    tones = {(2 + i) % 12 for i in (0, 3, 7, 10, 14)}
    assert got % 12 in tones
    assert abs(got - 38) <= 12
    assert got != 38


def test_beat2_stepwise_and_excludes_beat3() -> None:
    rng = _CountingRandom(0)
    got = _beat2(_dm9_event(0, _BAR), 38, 41, _LANE, rng)
    assert 1 <= abs(got - 38) <= 4
    assert got != 41


def test_beat2_relaxation_to_within_seven() -> None:
    # Contrived: beat1 below the lane floor so nothing sits within 1-4 in-lane;
    # relaxation to within 7 finds the sole scale/chord tone at distance 6.
    rng = _CountingRandom(0)
    lane = Register(low_midi=35, high_midi=55)
    cmaj = _chord(0, "maj", [], "C")
    event = _ev(0, _BAR, cmaj, 0, "whole_tone")
    got = _beat2(event, 30, 99, lane, rng)
    assert got == 36  # C2, distance 6 from the contrived beat1
    assert rng.draws == 0


def test_four_feel_approach_types() -> None:
    dm = _dm9_event(0, _BAR)
    target = 43  # G2
    cases = {
        "chromatic_below": target - 1,  # 42
        "dominant": target + 7,  # 50
    }
    for name, want in cases.items():
        cfg = WalkingConfig(
            feel_by_intensity=_WALKING.feel_by_intensity,
            approach_weights={name: 1},
            beat1_repeat_weights=_WALKING.beat1_repeat_weights,
        )
        rng = _CountingRandom(0)
        got = _draw_approach(target, dm, cfg, _LANE, rng)
        assert got == want
        assert rng.draws == 0  # singleton type -> zero draws
    # diatonic -> first D-dorian scale tone below the target (F2 = 41).
    cfg_dia = WalkingConfig(
        feel_by_intensity=_WALKING.feel_by_intensity,
        approach_weights={"diatonic": 1},
        beat1_repeat_weights=_WALKING.beat1_repeat_weights,
    )
    assert _draw_approach(target, dm, cfg_dia, _LANE, _CountingRandom(0)) == 41


def test_four_feel_two_chords_quartet() -> None:
    dm = _dm9_event(0, 960)
    gm = _ev(960, 960, _chord(7, "min7", ["9"], "Gm9"), 7, "dorian")
    chords = [dm, gm]
    notes, _ = _four_feel_bar(
        0, 0, dm, None, _LANE, 0.5, 120.0, False, chords, 10 * _BAR, _WALKING, _rng("a")
    )
    # Root(c1), approach, root(c2), approach — four quarters.
    assert [n.ticks for n in notes[:4]] == [0, 480, 960, 1440]
    assert notes[0].midi % 12 == 2  # D root
    assert notes[2].midi % 12 == 7  # G root


def test_four_feel_embellishment_placement_and_suppression() -> None:
    chords = [_dm9_event(0, 8 * _BAR)]

    def ghost_on(bar_in_section: int, density: float, tempo: float) -> bool:
        notes, _ = _four_feel_bar(
            bar_in_section * _BAR,
            bar_in_section,
            chords[0],
            None,
            _LANE,
            density,
            tempo,
            False,
            chords,
            100 * _BAR,
            _WALKING,
            _rng("a"),
        )
        return any("ghost" in n.tags for n in notes)

    # Low density -> N=4 -> ghost on barInSection % 4 == 3.
    assert ghost_on(3, 0.5, 120.0)
    assert not ghost_on(2, 0.5, 120.0)
    # High density -> N=2 -> ghost on barInSection % 2 == 1.
    assert ghost_on(1, 0.6, 120.0)
    assert not ghost_on(0, 0.6, 120.0)
    # tempo > 200 suppresses the embellishment.
    assert not ghost_on(3, 0.5, 201.0)


def test_ghost_note_shape() -> None:
    chords = [_dm9_event(0, 8 * _BAR)]
    notes, _ = _four_feel_bar(
        3 * _BAR,
        3,
        chords[0],
        None,
        _LANE,
        0.5,
        120.0,
        False,
        chords,
        100 * _BAR,
        _WALKING,
        _rng("a"),
    )
    beat4 = next(n for n in notes if n.ticks == 3 * _BAR + 1440)
    ghost = next(n for n in notes if "ghost" in n.tags)
    assert ghost.ticks == 3 * _BAR + 1680  # and-of-4
    assert ghost.duration_ticks == 60
    assert ghost.velocity == 0.25
    assert ghost.midi == beat4.midi  # repeats the beat-4 pitch


# =============================================================================
# draw discipline: fixed order + independence
# =============================================================================


def test_fixed_draw_order_beat3_beat2_approach() -> None:
    # A no-decay four-feel bar engineered so the three draws have DISTINCT
    # weight-totals, making the draw order beat 3 -> beat 2 -> approach (§3.6)
    # unambiguous from the recorded sequence. Dm9, beat1=D2(38), next root B
    # -> target=B1(35):
    #   beat3 candidates {A1,C2,E2,F2} weights [1,3,1,1] -> total 6
    #   beat2 candidates {B1,C2,E2,F2} weights [1,3,3,1] -> total 8
    #   approach 3 full types {2,1,1}                     -> total 4
    dm = _dm9_event(0, _BAR)
    bm = _ev(_BAR, _BAR, _chord(11, "min7", [], "Bm7"), 11, "dorian")
    chords = [dm, bm]
    rec = _RecordingRandom()
    _four_feel_bar(
        0, 0, dm, None, _LANE, 0.5, 120.0, False, chords, 10 * _BAR, _WALKING, rec
    )
    assert rec.totals == [6, 8, 4]  # distinct -> beat3, then beat2, then approach


def test_fixed_draw_order_decay_first() -> None:
    # With decay on, the beat-1 decay draw precedes the rest.
    chords = [_dm9_event(0, 4 * _BAR)]
    rec = _RecordingRandom()
    _four_feel_bar(
        0, 0, chords[0], 38, _LANE, 0.5, 120.0, True, chords, 10 * _BAR, _WALKING, rec
    )
    # First recorded draw is the decay draw (beat1RepeatWeights total 2+1+1 = 4).
    assert rec.totals[0] == 4


def test_per_bar_substream_independence() -> None:
    chords = [_dm9_event(b * _BAR, _BAR) for b in range(4)]
    arr = ArrangementPlan(entries=[_entry("s", intensity=3, density=0.5)])
    form = _form_of([_section("s", 0, 4, 0.6)])  # rung 3 -> four-feel

    def default_run() -> dict[str, list[WalkNote]]:
        return walk(
            arr,
            _harmony(chords),
            form,
            _plan(),
            _pack(),
            master=_MASTER,
            overrides=_OVERRIDES,
        )

    base = default_run()

    walk_seed = derive(stream_seed(_MASTER, _OVERRIDES, "bass"), "walk")

    # Injecting a factory that reproduces the §3.6 derivation matches the default.
    def faithful(abs_bar: int) -> Rng:
        return Rng(derive(walk_seed, f"bar:{abs_bar}"))

    mirrored = walk(
        arr,
        _harmony(chords),
        form,
        _plan(),
        _pack(),
        master=_MASTER,
        overrides=_OVERRIDES,
        rng_factory=faithful,
    )
    assert mirrored == base

    # Perturbing ONLY bar 0's rng must not shift any later bar's notes.
    def perturb_bar0(abs_bar: int) -> Rng:
        if abs_bar == 0:
            return Rng(derive(walk_seed, "PERTURBED"))
        return Rng(derive(walk_seed, f"bar:{abs_bar}"))

    perturbed = walk(
        arr,
        _harmony(chords),
        form,
        _plan(),
        _pack(),
        master=_MASTER,
        overrides=_OVERRIDES,
        rng_factory=perturb_bar0,
    )
    later = [n for n in perturbed["s"] if n.ticks >= _BAR]
    base_later = [n for n in base["s"] if n.ticks >= _BAR]
    assert later == base_later


def test_bar_rng_reproducible_in_isolation() -> None:
    # Regenerating a single bar's rng in isolation reproduces that bar's draws.
    # Alternating Dm/Gm so no consecutive-same-chord decay complicates bar 2.
    roots = [(2, "Dm9"), (7, "Gm9"), (2, "Dm9"), (7, "Gm9")]
    chords = [
        _ev(b * _BAR, _BAR, _chord(r, "min7", ["9"], sym), r, "dorian")
        for b, (r, sym) in enumerate(roots)
    ]
    arr = ArrangementPlan(entries=[_entry("s", intensity=3, density=0.5)])
    form = _form_of([_section("s", 0, 4, 0.6)])
    base = walk(
        arr,
        _harmony(chords),
        form,
        _plan(),
        _pack(),
        master=_MASTER,
        overrides=_OVERRIDES,
    )

    walk_seed = derive(stream_seed(_MASTER, _OVERRIDES, "bass"), "walk")
    # Recompute bar 2 alone via its exact derived rng and the same bar helper.
    rng = Rng(derive(walk_seed, "bar:2"))
    # prev pitch entering bar 2 = the last note emitted before tick 2*_BAR.
    before = [n for n in base["s"] if n.ticks < 2 * _BAR]
    prev = before[-1].midi
    isolated, _ = _four_feel_bar(
        2 * _BAR,
        2,
        chords[2],
        prev,
        _LANE,
        0.5,
        120.0,
        False,
        chords,
        4 * _BAR,
        _WALKING,
        rng,
    )
    in_base = [n for n in base["s"] if 2 * _BAR <= n.ticks < 3 * _BAR]
    assert isolated == in_base


# =============================================================================
# walk end-to-end structure
# =============================================================================


def _three_section_scenario() -> tuple[ArrangementPlan, HarmonicPlan, SongForm]:
    # head (two-feel), solo (four-feel), outro (two-feel, final); each 4 bars,
    # chords Dm9 Gm9 Dm9 Dm9 per section.
    def block(base_bar: int, section_id: str) -> list[ChordEvent]:
        roots = [(2, "Dm9"), (7, "Gm9"), (2, "Dm9"), (2, "Dm9")]
        out = []
        for i, (root, sym) in enumerate(roots):
            scale_root = root
            out.append(
                _ev(
                    (base_bar + i) * _BAR,
                    _BAR,
                    _chord(root, "min7", ["9"], sym),
                    scale_root,
                    "dorian",
                    section_id,
                )
            )
        return out

    chords = block(0, "head") + block(4, "solo") + block(8, "outro")
    arr = ArrangementPlan(
        entries=[
            _entry("head", intensity=2, density=0.5),
            _entry("solo", intensity=3, density=0.5),
            _entry("outro", intensity=2, density=0.5),
        ]
    )
    form = _form_of(
        [
            _section("head", 0, 4, 0.4),
            _section("solo", 4, 4, 0.6),
            _section("outro", 8, 4, 0.4, final=True),
        ]
    )
    return arr, _harmony(chords), form


def test_walk_feel_selection_and_lane_containment() -> None:
    arr, harmony, form = _three_section_scenario()
    result = walk(
        arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES
    )
    assert set(result) == {"head", "solo", "outro"}
    # Two-feel head bars carry <= 2 notes/bar; four-feel solo bars >= 4.
    head_bar0 = [n for n in result["head"] if n.ticks < _BAR]
    solo_bar0 = [n for n in result["solo"] if 4 * _BAR <= n.ticks < 5 * _BAR]
    assert len(head_bar0) <= 2
    assert len(solo_bar0) >= 4
    for notes in result.values():
        for n in notes:
            assert _LANE.low_midi <= n.midi <= _LANE.high_midi


def test_walk_pitch_state_resets_at_section_start() -> None:
    arr, harmony, form = _three_section_scenario()
    result = walk(
        arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES
    )
    # Both sections open on the lowest in-lane D (38), independent of prior state.
    assert result["head"][0].ticks == 0
    assert result["head"][0].midi == 38
    solo_first = min((n for n in result["solo"]), key=lambda n: n.ticks)
    assert solo_first.ticks == 4 * _BAR
    assert solo_first.midi == 38


def test_walk_final_bar_rule() -> None:
    arr, harmony, form = _three_section_scenario()
    result = walk(
        arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES
    )
    outro = result["outro"]
    final_bar = [n for n in outro if n.ticks >= 11 * _BAR]
    assert len(final_bar) == 1
    note = final_bar[0]
    assert note.ticks == 11 * _BAR
    assert note.duration_ticks == 1920  # whole note
    assert note.velocity == 0.75
    assert note.midi == nearest(2, _LANE.low_midi, _LANE)  # lowest in-lane root


def test_walk_is_deterministic() -> None:
    arr, harmony, form = _three_section_scenario()
    a = walk(arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES)
    b = walk(arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES)
    assert a == b


def test_walk_authored_velocities() -> None:
    arr, harmony, form = _three_section_scenario()
    result = walk(
        arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES
    )
    allowed = {0.72, 0.68, 0.75, 0.25}
    for notes in result.values():
        for n in notes:
            assert n.velocity in allowed
    # Every four-feel beat-1 (bar downbeat) is 0.75.
    for n in result["solo"]:
        if n.ticks % _BAR == 0:
            assert n.velocity == 0.75


def test_walk_skips_inactive_bass_section() -> None:
    arr = ArrangementPlan(entries=[_entry("head", active=False, intensity=2)])
    harmony = _harmony([_dm9_event(0, 4 * _BAR, "head")])
    form = _form_of([_section("head", 0, 4, 0.4)])
    result = walk(
        arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES
    )
    assert result == {}


def test_walk_notes_tick_ordered() -> None:
    arr, harmony, form = _three_section_scenario()
    result = walk(
        arr, harmony, form, _plan(), _pack(), master=_MASTER, overrides=_OVERRIDES
    )
    for notes in result.values():
        ticks = [n.ticks for n in notes]
        assert ticks == sorted(ticks)
