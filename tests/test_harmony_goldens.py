"""Goldens / determinism / property / deceptive / seed vectors for the Harmony
stage (PHASE_4 §14 DoD 4/5/6/7/9, SESSION_05 T3).

Every expected chord / tick / scale / function / tag / pool_selection is
transcribed from PHASE_4 **§10** (the two worked examples) and **§5.6** (seed
vectors) — NEVER copied from code output (ROADMAP §3 golden-value arbitration).
`symbol` is asserted in ASCII: the §10 prose glyphs `C♯m`/`Eø7`/`A7♭13`/`B♭13`
become `C#m`/`Em7b5`/`A7b13`/`Bb13` (flats `b`, sharps `#`). A divergence between
a §10 value and the stage output is a bug/ambiguity to escalate, not to paper
over by tuning the expected value.

`source is frozen`: this file treats `harmony()` as a black box and never edits
`src/`.
"""

from __future__ import annotations

import random
from functools import cache
from typing import Any, get_args

import pytest

from trackgen.form.stage import form
from trackgen.harmony.stage import harmony
from trackgen.interpreter.params import Params
from trackgen.interpreter.stage import generate_plan, interpret
from trackgen.packs import resolve_pack
from trackgen.packs.models import ProgressionsConfig
from trackgen.schema.ir import (
    Budgets,
    ChordEvent,
    ChordQuality,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Key,
    KeyRegion,
    MoodVector,
    SectionEnding,
    SectionPhrase,
    SeedSpec,
    SongForm,
    StylePackRef,
    TimbreDirectives,
    TimeSignature,
)
from trackgen.seeds import derive, from_base36, stream_rng, to_base36
from trackgen.theory import extensions_legal

_TPB = 1920

# A golden chord: (symbol, root_pc, quality, extensions, scale_name, scale_root,
# function) — every field transcribed from §10.
_Chord = tuple[str, int, str, list[str], str, int, str]


def _harmony_rng(plan: GenerationPlan) -> random.Random:
    return stream_rng(plan.seed.master, plan.seed.overrides, "harmony")


def _assert_event(
    actual: ChordEvent, chord: _Chord, tick: int, dur: int, tags: list[str], sid: str
) -> None:
    symbol, root_pc, quality, extensions, scale_name, scale_root, function = chord
    assert actual.chord.symbol == symbol, (actual.chord.symbol, symbol, tick)
    assert actual.chord.root_pc == root_pc, (symbol, actual.chord.root_pc, root_pc)
    assert actual.chord.quality == quality, (symbol, actual.chord.quality, quality)
    assert list(actual.chord.extensions) == extensions, (
        symbol,
        actual.chord.extensions,
    )
    assert actual.scale.name == scale_name, (symbol, actual.scale.name, scale_name)
    assert actual.scale.root_pc == scale_root, (symbol, actual.scale.root_pc)
    assert actual.function == function, (symbol, actual.function, function)
    assert list(actual.tags) == tags, (symbol, actual.tags, tags, tick)
    assert actual.start_tick == tick, (symbol, actual.start_tick, tick)
    assert actual.duration_ticks == dur, (symbol, actual.duration_ticks, dur)
    assert actual.section_id == sid, (symbol, actual.section_id, sid)


# =============================================================================
# DoD 4 — Example 1: pop_rock / happy, E major (tonicPc 4), tier 0  (§10.1)
# =============================================================================

# §10.1 chords (E major). All at 1920 ticks/bar, tier 0 → triads except the V
# slot, dressed per-slot: verse/bridge V = maj (B), chorus V = dom7 (B7).
_E: _Chord = ("E", 4, "maj", [], "ionian", 4, "T")
_A: _Chord = ("A", 9, "maj", [], "lydian", 9, "S")
_B: _Chord = ("B", 11, "maj", [], "mixolydian", 11, "D")
_B7: _Chord = ("B7", 11, "dom7", [], "mixolydian", 11, "D")
_CSM: _Chord = ("C#m", 1, "min", [], "aeolian", 1, "T")

# §10.1 table (per 4-bar phrase), expanded to the 76-event timeline.
_EX1_INTRO = [_E, _A, _E, _A]  # intro-1: tonic_vamp I·IV·I·IV
_EX1_VERSE = [_E, _A, _E, _B] * 2  # verse: anchor I·IV·I·V (V→maj), ×2 phrases
_EX1_CHORUS = [_E, _B7, _CSM, _A] * 4  # chorus: axis I·V·vi·IV (V→dom7), ×4
_EX1_BRIDGE = [_CSM, _A, _E, _B] * 2  # bridge: depart_six vi·IV·I·V (V→maj), ×2
# chorus-3: (E·B7·C#m·A)×3, then E·B7, then finals `plagal` A·E (tags ["final"]).
_EX1_CHORUS3_BODY = [_E, _B7, _CSM, _A] * 3 + [_E, _B7]
_EX1_CHORUS3_FINAL = [_A, _E]

_EX1_CHORDS: list[_Chord] = (
    _EX1_INTRO
    + _EX1_VERSE
    + _EX1_CHORUS
    + _EX1_VERSE
    + _EX1_CHORUS
    + _EX1_BRIDGE
    + _EX1_CHORUS3_BODY
    + _EX1_CHORUS3_FINAL
)

_EX1_SIDS = (
    ["intro-1"] * 4
    + ["verse-1"] * 8
    + ["chorus-1"] * 16
    + ["verse-2"] * 8
    + ["chorus-2"] * 16
    + ["bridge-1"] * 8
    + ["chorus-3"] * 16
)


def _build_ex1() -> HarmonicPlan:
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.progressions is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    return harmony(plan, sf, pack.progressions, _harmony_rng(plan))


def test_golden_example_1_event_for_event() -> None:
    """PHASE_4 §10.1 — pop_rock/happy, E major, tier 0: the full 76-event
    timeline, field-for-field against the doc."""
    hp = _build_ex1()
    assert len(hp.chords) == 76
    assert len(_EX1_CHORDS) == 76 and len(_EX1_SIDS) == 76

    for i, (event, chord, sid) in enumerate(
        zip(hp.chords, _EX1_CHORDS, _EX1_SIDS, strict=True)
    ):
        tags = ["final"] if i >= 74 else []
        _assert_event(event, chord, i * _TPB, _TPB, tags, sid)

    # §10.1 sample event (chorus-1, bar 13): the doc prints roman "V" here too.
    sample = hp.chords[13]
    assert sample.start_tick == 24960
    assert sample.chord.root_pc == 11
    assert sample.chord.quality == "dom7"
    assert sample.chord.symbol == "B7"
    assert sample.chord.roman == "V"
    assert sample.scale.root_pc == 11 and sample.scale.name == "mixolydian"
    assert sample.function == "D"
    assert sample.tags == []

    assert hp.pool_selections == {
        "intro": "tonic_vamp",
        "verse": "anchor",
        "chorus": "axis",
        "bridge": "depart_six",
        "finals": "plagal",
    }
    assert hp.keys == [KeyRegion(start_tick=0, tonic_pc=4, mode="major")]


# =============================================================================
# DoD 4 — Example 2: jazz / melancholic, D minor (tonicPc 2), tier 4  (§10.2)
# =============================================================================

# §10.2 chords (D minor). Body dressed at tier 4 (T→3, D→5); min7b5 passthrough.
_DM9: _Chord = ("Dm9", 2, "min7", ["9"], "aeolian", 2, "T")
_GM9: _Chord = ("Gm9", 7, "min7", ["9"], "dorian", 7, "S")
_GM11: _Chord = ("Gm11", 7, "min7", ["11"], "dorian", 7, "S")
_BB13: _Chord = ("Bb13", 10, "dom7", ["13"], "lydian_dominant", 10, "S")
_A7B9: _Chord = ("A7b9", 9, "dom7", ["b9"], "half_whole_dim", 9, "D")
_DM7: _Chord = ("Dm7", 2, "min7", [], "aeolian", 2, "T")
_BB9: _Chord = ("Bb9", 10, "dom7", ["9"], "lydian_dominant", 10, "S")
_EM7B5: _Chord = ("Em7b5", 4, "min7b5", [], "locrian_nat2", 4, "S")
_A7B13: _Chord = ("A7b13", 9, "dom7", ["b13"], "mixolydian_b13", 9, "D")

# A §10.2 golden event: (chord, start_tick, duration_ticks, tags).
_Ev = tuple[_Chord, int, int, list[str]]


def _ex2_closed_body(start_bar: int) -> list[_Ev]:
    """The dressed 12-bar minor_quick body (§10.2 bar table), holds merged:
    Dm9·Gm9·Dm9(2bar)·Gm11(2bar)·Dm9(2bar)·Bb13·A7b9·Dm9(2bar)."""
    b = start_bar * _TPB
    return [
        (_DM9, b + 0, _TPB, []),
        (_GM9, b + _TPB, _TPB, []),
        (_DM9, b + 2 * _TPB, 2 * _TPB, []),
        (_GM11, b + 4 * _TPB, 2 * _TPB, []),
        (_DM9, b + 6 * _TPB, 2 * _TPB, []),
        (_BB13, b + 8 * _TPB, _TPB, []),
        (_A7B9, b + 9 * _TPB, _TPB, []),
        (_DM9, b + 10 * _TPB, 2 * _TPB, []),
    ]


def _ex2_kept7(start_bar: int) -> list[_Ev]:
    """The 7 body events kept when a 2-bar boundary transform replaces the
    2-bar terminal tonic run (bars 11–12)."""
    return _ex2_closed_body(start_bar)[:7]


_TA = ["turnaround"]
_FIN = ["final"]


def _build_ex2_events() -> list[tuple[_Ev, str]]:
    """The full §10.2 timeline as (event, section_id) pairs. Turnaround tails
    per the §10.2 per-boundary table; outro closed by finals `minor_close`."""
    events: list[tuple[_Ev, str]] = []

    # head-1 (bars 0–12): body kept 7 + minor_turn `Dm7 Bb9 · Em7b5 A7b13`.
    b = 10 * _TPB
    events += [(e, "head-1") for e in _ex2_kept7(0)]
    events += [
        ((_DM7, b + 0, 960, _TA), "head-1"),
        ((_BB9, b + 960, 960, _TA), "head-1"),
        ((_EM7B5, b + 1920, 960, _TA), "head-1"),
        ((_A7B13, b + 2880, 960, _TA), "head-1"),
    ]

    # solo-1 (bars 12–24): body kept 7 + minor_two_five `Dm9 · Em7b5 A7b9`.
    b = 22 * _TPB
    events += [(e, "solo-1") for e in _ex2_kept7(12)]
    events += [
        ((_DM9, b + 0, _TPB, _TA), "solo-1"),
        ((_EM7B5, b + _TPB, 960, _TA), "solo-1"),
        ((_A7B9, b + _TPB + 960, 960, _TA), "solo-1"),
    ]

    # solo-2 (bars 24–36): body kept 7 + minor_turn `Dm7 Bb13 · Em7b5 A7b13`.
    b = 34 * _TPB
    events += [(e, "solo-2") for e in _ex2_kept7(24)]
    events += [
        ((_DM7, b + 0, 960, _TA), "solo-2"),
        ((_BB13, b + 960, 960, _TA), "solo-2"),
        ((_EM7B5, b + 1920, 960, _TA), "solo-2"),
        ((_A7B13, b + 2880, 960, _TA), "solo-2"),
    ]

    # solo-3 (bars 36–48): body kept 7 + minor_turn `Dm7 Bb13 · Em7b5 A7b13`.
    b = 46 * _TPB
    events += [(e, "solo-3") for e in _ex2_kept7(36)]
    events += [
        ((_DM7, b + 0, 960, _TA), "solo-3"),
        ((_BB13, b + 960, 960, _TA), "solo-3"),
        ((_EM7B5, b + 1920, 960, _TA), "solo-3"),
        ((_A7B13, b + 2880, 960, _TA), "solo-3"),
    ]

    # head-2 (bars 48–60): closed — head out resolves, no turnaround.
    events += [(e, "head-2") for e in _ex2_closed_body(48)]

    # outro-1 (bars 60–64): minor_outro `Dm9·Gm11·Dm9` with finals `minor_close`
    # replacing bars 3–4 → `Dm9 · Gm11 · Em7b5 A7b13 · Dm7` (tags ["final"]).
    b = 60 * _TPB
    events += [
        ((_DM9, b + 0, _TPB, []), "outro-1"),
        ((_GM11, b + _TPB, _TPB, []), "outro-1"),
        ((_EM7B5, b + 2 * _TPB, 960, _FIN), "outro-1"),
        ((_A7B13, b + 2 * _TPB + 960, 960, _FIN), "outro-1"),
        ((_DM7, b + 3 * _TPB, _TPB, _FIN), "outro-1"),
    ]
    return events


_EX2_EVENTS = _build_ex2_events()


def _build_ex2() -> HarmonicPlan:
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack("jazz")
    assert pack is not None and pack.progressions is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    return harmony(plan, sf, pack.progressions, _harmony_rng(plan))


def test_golden_example_2_event_for_event() -> None:
    """PHASE_4 §10.2 — jazz/melancholic, D minor, tier 4: the full timeline,
    field-for-field. The §10.2 body has holds and 2-token bars, so the event
    count (56) is below the 64-bar length: 5×12 head/solo/head + 4 outro bars
    collapse under hold-merge (§3.1). 64 is the *bar* total, not the event
    total — see the report handoff."""
    hp = _build_ex2()
    assert len(hp.chords) == len(_EX2_EVENTS) == 56

    for event, ((chord, tick, dur, tags), sid) in zip(
        hp.chords, _EX2_EVENTS, strict=True
    ):
        _assert_event(event, chord, tick, dur, tags, sid)

    assert hp.pool_selections == {
        "blues_12": "minor_quick",
        "outro": "minor_outro",
        "turnaround:head-1": "minor_turn",
        "turnaround:solo-1": "minor_two_five",
        "turnaround:solo-2": "minor_turn",
        "turnaround:solo-3": "minor_turn",
        "finals": "minor_close",
    }
    assert hp.keys == [KeyRegion(start_tick=0, tonic_pc=2, mode="minor")]


# =============================================================================
# DoD 5 — seed vectors (§5.6)
# =============================================================================


def test_harmony_stream_seed_vectors() -> None:
    """PHASE_4 §5.6 — the harmony-stream RNG golden vectors (normative). The
    stage draws on exactly this stream (`stream_rng(master, overrides,
    "harmony")` seeds a `random.Random` with `derive(master, "harmony")`)."""
    seed = derive(3735928559, "harmony")
    assert seed == 226146634901021418

    r = random.Random(seed)
    assert [r.getrandbits(32) for _ in range(5)] == [
        1607822876,
        501707672,
        365345814,
        982234362,
        2945966636,
    ]
    r2 = random.Random(seed)
    assert [r2.randrange(100) for _ in range(5)] == [47, 14, 10, 29, 87]

    # The stage's own stream resolves to the same seed for master 1ps9wxb.
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    assert plan.seed.master == 3735928559
    assert stream_rng(plan.seed.master, plan.seed.overrides, "harmony").getstate() == (
        random.Random(226146634901021418).getstate()
    )


# =============================================================================
# DoD 6 — determinism + draw counts
# =============================================================================


class _CountingRandom(random.Random):
    """A seeded RNG counting `randrange` calls. `weighted_choice` issues exactly
    one `randrange` per draw, so the count is the exact number of draws.
    `getrandbits` is not separately counted — `randrange` calls it internally,
    so counting both would double-count past the `weighted_choice` total."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


def _counting_rng_for(plan: GenerationPlan) -> _CountingRandom:
    """A counting RNG in the identical state to the plan's harmony stream, so
    the count reflects the real (seeded) draw sequence."""
    base = stream_rng(plan.seed.master, plan.seed.overrides, "harmony")
    counting = _CountingRandom()
    counting.setstate(base.getstate())
    counting.draws = 0
    return counting


def test_determinism_identical_plans() -> None:
    """PHASE_4 §5.6 — same inputs → identical HarmonicPlan (both examples)."""
    assert _build_ex1() == _build_ex1()
    assert _build_ex2() == _build_ex2()


def test_draw_count_example_1_is_8() -> None:
    """§10.1 (`8 draws total`): intro select(1) + verse select+V-dress(2) +
    chorus select+V-dress(2) + bridge select+V-dress(2) + finals select(1) = 8;
    no boundary draws (pop turnarounds empty, no same-tag adjacency)."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.progressions is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    rng = _counting_rng_for(plan)
    harmony(plan, sf, pack.progressions, rng)
    assert rng.draws == 8


def test_draw_count_example_2_is_30() -> None:
    """§10.2 (`30 draws total`): blues_12 select(1)+dressing(8) + outro
    select(0)+dressing(3) + turnarounds head-1(1+3) solo-1(1+2) solo-2(1+3)
    solo-3(1+3) + finals select(1)+dressing(2) = 9+3+15+3 = 30."""
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack("jazz")
    assert pack is not None and pack.progressions is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    rng = _counting_rng_for(plan)
    harmony(plan, sf, pack.progressions, rng)
    assert rng.draws == 30


# --- synthetic fixtures for the remaining §5.6 determinism claims ------------


def _plan(
    *,
    mode: str = "major",
    tonic_pc: int = 0,
    dissonance: float = 0.1,
    valence: float = 0.0,
    hrb: float = 1.0,
) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="synthetic", version="1"),
        seed=SeedSpec(master=1),
        key=Key(tonic_pc=tonic_pc, mode=mode),
        tempo_bpm=120.0,
        time_signature=TimeSignature(numerator=4, denominator=4),
        max_length_ticks=400 * _TPB,
        mood_vector=MoodVector(valence=valence, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=dissonance,
            dynamics_base=0.5,
            dynamics_range=0.5,
            articulation_legato=0.5,
            layers_max=3,
            harmonic_rhythm_base=hrb,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def _section(
    section_id: str,
    tag: str,
    start_bar: int,
    phrases: list[tuple[str, int]],
    *,
    section_type: str = "verse",
    ending: bool = False,
) -> FormSection:
    length = sum(bars for _, bars in phrases)
    return FormSection(
        id=section_id,
        type=section_type,
        index=1,
        start_bar=start_bar,
        length_bars=length,
        energy=0.5,
        total_of_type=1,
        phrases=[SectionPhrase(label=label, bars=bars) for label, bars in phrases],
        harmony_tag=tag,
        ending=(SectionEnding(tag_bars=0, close="cold") if ending else None),
    )


def _form(sections: list[FormSection]) -> SongForm:
    total = max(s.start_bar + s.length_bars for s in sections)
    return SongForm(sections=sections, total_bars=total, template_id="synthetic")


def _progs(config: dict[str, Any]) -> ProgressionsConfig:
    return ProgressionsConfig.model_validate(config)


_FIN_MINOR = [
    {"id": "f", "weight": 1, "modes": ["minor"], "bars": [["iiø7", "V7"], ["i7"]]}
]


def test_singleton_candidate_form_consumes_zero_draws() -> None:
    """§5.6 — a pack where every tag has one eligible entry and every slot one
    dressing option (tier 0 bare majors/minors, T/S functions only) draws zero
    times: no select and no dressing ever sees >= 2 options."""
    progs = _progs(
        {
            "pools": {
                "verse": [
                    {
                        "id": "v",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["vi"], ["IV"]]},
                    }
                ],
                "chorus": [
                    {
                        "id": "c",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["vi"]]},
                    }
                ],
            },
            "turnarounds": [],
            "finals": [
                {"id": "f", "weight": 1, "modes": ["major"], "bars": [["IV"], ["I"]]}
            ],
        }
    )
    sf = _form(
        [
            _section("verse-1", "verse", 0, [("a", 4)]),
            _section("chorus-1", "chorus", 4, [("a", 4)], ending=True),
        ]
    )
    rng = _CountingRandom()
    rng.seed(99)
    rng.draws = 0
    harmony(_plan(), sf, progs, rng)
    assert rng.draws == 0


class _LoggingRandom(random.Random):
    """Records each `randrange` as ``(range_arg, result)`` — the seeded draw
    sequence, so an append-only prefix can be compared across related inputs."""

    def __init__(self, seed: int) -> None:
        super().__init__(seed)
        self.log: list[tuple[tuple[object, ...], int]] = []

    def randrange(self, *args: object, **kwargs: object) -> int:
        result = super().randrange(*args, **kwargs)  # type: ignore[arg-type]
        self.log.append((args, result))
        return result


def test_draw_sequence_is_append_only_under_added_section() -> None:
    """§5.6 (append-only) — inserting a section (a new tag) before the final
    section does not shift any draw that precedes the first divergent candidate
    set. Base form draws [intro_sel, verse_sel, finals_sel]; the extended form
    inserts a `bridge` tag → [intro_sel, verse_sel, bridge_sel, finals_sel].
    The shared prefix (intro_sel, verse_sel) is bit-identical; divergence only
    at the inserted draw. Tier 0 + T/S-only tokens ⇒ selects are the only
    draws, so the prefix comparison is clean."""
    progs = _progs(
        {
            "pools": {
                "intro": [
                    {
                        "id": "i1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    },
                    {
                        "id": "i2",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["vi"]]},
                    },
                ],
                "verse": [
                    {
                        "id": "v1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["vi"], ["IV"]]},
                    },
                    {
                        "id": "v2",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["I"]]},
                    },
                ],
                "bridge": [
                    {
                        "id": "b1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["vi"], ["IV"], ["I"], ["vi"]]},
                    },
                    {
                        "id": "b2",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["IV"], ["vi"], ["I"], ["IV"]]},
                    },
                ],
                "chorus": [
                    {
                        "id": "c1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["vi"]]},
                    },
                ],
            },
            "turnarounds": [],
            "finals": [
                {"id": "f1", "weight": 1, "modes": ["major"], "bars": [["IV"], ["I"]]},
                {"id": "f2", "weight": 1, "modes": ["major"], "bars": [["vi"], ["I"]]},
            ],
        }
    )
    base = _form(
        [
            _section("intro-1", "intro", 0, [("a", 4)], section_type="intro"),
            _section("verse-1", "verse", 4, [("a", 4)]),
            _section("chorus-1", "chorus", 8, [("a", 4)], ending=True),
        ]
    )
    extended = _form(
        [
            _section("intro-1", "intro", 0, [("a", 4)], section_type="intro"),
            _section("verse-1", "verse", 4, [("a", 4)]),
            _section("bridge-1", "bridge", 8, [("a", 4)], section_type="bridge"),
            _section("chorus-1", "chorus", 12, [("a", 4)], ending=True),
        ]
    )
    rng_a = _LoggingRandom(1234)
    harmony(_plan(), base, progs, rng_a)
    rng_b = _LoggingRandom(1234)
    harmony(_plan(), extended, progs, rng_b)

    # Append-only: the intro_sel + verse_sel draws precede the inserted `bridge`
    # candidate set, so they are bit-identical (arg AND result) across the two
    # runs — the inserted section shifted nothing before it. The extended run
    # has exactly one extra draw (the bridge select); the finals draw follows.
    assert rng_a.log[:2] == rng_b.log[:2]
    assert len(rng_b.log) == len(rng_a.log) + 1


def test_draw_sequence_is_append_only_under_budget_change() -> None:
    """§5.6 (append-only under a *budget* change; §14.6) — raising the plan's
    `dissonance` budget 0.10 → 0.12 (both tier 0, so §6 dressing is unchanged
    everywhere) flips one `chorus` pool entry OUT of eligibility through its
    per-entry dissonance gate [0.0, 0.11]. The `intro`/`verse` pools carry no
    dissonance gate, so their candidate sets — hence their select draws — are
    identical across both budgets; the first tag whose eligibility differs is
    `chorus`. Draw order is tag-first-appearance, so append-only discipline
    requires the two draws BEFORE the divergent `chorus` set to be bit-identical
    (same randrange arg AND result): the lower-dissonance run simply carries one
    extra draw (the chorus select, skipped by the higher-dissonance run since
    only one chorus entry survives). Tier 0 + T/S-only tokens ⇒ selects are the
    only draws, so the prefix comparison is clean."""
    progs = _progs(
        {
            "pools": {
                "intro": [
                    {
                        "id": "i1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    },
                    {
                        "id": "i2",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["vi"]]},
                    },
                ],
                "verse": [
                    {
                        "id": "v1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["vi"], ["IV"]]},
                    },
                    {
                        "id": "v2",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["I"]]},
                    },
                ],
                "chorus": [
                    {
                        "id": "c1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["vi"]]},
                    },
                    {
                        "id": "c2",
                        "weight": 1,
                        "modes": ["major"],
                        # eligible only while dissonance <= 0.11 — the lever.
                        "dissonance": [0.0, 0.11],
                        "phrases": {"a": [["vi"], ["IV"], ["I"], ["IV"]]},
                    },
                ],
            },
            "turnarounds": [],
            "finals": [
                {"id": "f1", "weight": 2, "modes": ["major"], "bars": [["IV"], ["I"]]},
                {"id": "f2", "weight": 1, "modes": ["major"], "bars": [["vi"], ["I"]]},
            ],
        }
    )
    sf = _form(
        [
            _section("intro-1", "intro", 0, [("a", 4)], section_type="intro"),
            _section("verse-1", "verse", 4, [("a", 4)]),
            _section("chorus-1", "chorus", 8, [("a", 4)], ending=True),
        ]
    )
    rng_lo = _LoggingRandom(1234)
    harmony(_plan(dissonance=0.10), sf, progs, rng_lo)
    rng_hi = _LoggingRandom(1234)
    harmony(_plan(dissonance=0.12), sf, progs, rng_hi)

    # intro_sel + verse_sel precede the divergent `chorus` candidate set and are
    # bit-identical (arg AND result) across the two budgets — the eligibility
    # shift did not move any draw before it. Index 2 genuinely diverges (chorus
    # select on randrange(2) at 0.10 vs the finals select on randrange(3) at
    # 0.12), so the prefix assertion is non-vacuous; the low run has exactly one
    # extra draw, the chorus select the high run skips.
    assert rng_lo.log[:2] == rng_hi.log[:2]
    assert rng_lo.log[2] != rng_hi.log[2]
    assert len(rng_lo.log) == len(rng_hi.log) + 1


# =============================================================================
# DoD 7 — property matrix
# =============================================================================

# The full grid: 2 packs × supported moods × 39 lengths × 25 seeds, matching the
# Phase-3 form property test (test_form.py) seed count and generation formula
# (§14.7 pins "× 25 seeds"). ~21 (pack×mood) × 39 lengths × 25 seeds ≈ 20k runs.
_LENGTHS = list(range(30, 601, 15))
_SEEDS = [to_base36(((i + 1) * 2654435761) % (2**63)) for i in range(25)]
_QUALITIES = frozenset(get_args(ChordQuality))


@cache
def _cached_pack(style: str) -> Any:
    return resolve_pack(style)


def _build_plan(style: str, mood: str, max_len_sec: int, seed: str) -> GenerationPlan:
    pack = _cached_pack(style)
    params = Params.model_validate(
        {"styleFamily": style, "mood": mood, "maxLengthSec": max_len_sec, "seed": seed}
    )
    return interpret(params, pack, from_base36(seed), {})


def _property_params() -> list[Any]:
    params: list[Any] = []
    for style in ("pop_rock", "jazz"):
        pack = resolve_pack(style)
        assert pack is not None and pack.interpreter is not None
        for mood in pack.interpreter.supported_moods:
            params.append(pytest.param(style, mood))
    return params


@pytest.mark.parametrize(("style", "mood"), _property_params())
def test_property_valid_harmonic_plan(style: str, mood: str) -> None:
    """PHASE_4 §14 DoD 7 — every pack × supported mood × length grid × 25 seeds
    yields a HarmonicPlan validating every §5/§7 structural invariant."""
    pack = _cached_pack(style)
    assert pack.forms is not None and pack.progressions is not None

    for max_len_sec in _LENGTHS:
        for seed in _SEEDS:
            plan = _build_plan(style, mood, max_len_sec, seed)
            sf = form(plan, pack.forms)
            rng = stream_rng(plan.seed.master, plan.seed.overrides, "harmony")
            hp = harmony(plan, sf, pack.progressions, rng)

            total = sf.total_bars * _TPB
            ctx = (style, mood, max_len_sec, seed)

            # chords tile [0, total) with no gaps/overlaps.
            cursor = 0
            for e in hp.chords:
                assert e.start_tick == cursor, ctx
                assert e.duration_ticks >= 1, ctx
                cursor += e.duration_ticks
            assert cursor == total, ctx
            assert hp.chords[0].start_tick == 0, ctx

            # per-section bounds + quality/extension/scale/function legality.
            section_by_id = {s.id: s for s in sf.sections}
            for e in hp.chords:
                sec = section_by_id[e.section_id]
                lo = sec.start_bar * _TPB
                hi = (sec.start_bar + sec.length_bars) * _TPB
                assert lo <= e.start_tick, ctx
                assert e.start_tick + e.duration_ticks <= hi, ctx
                assert e.chord.quality in _QUALITIES, ctx
                assert extensions_legal(e.chord.quality, e.chord.extensions), (
                    ctx,
                    e.chord,
                )
                assert e.scale.name, ctx
                assert e.function in ("T", "S", "D", "O"), ctx

            # final event of the whole song is degree-1-rooted.
            assert hp.chords[-1].chord.root_pc == plan.key.tonic_pc, ctx

            # keys: exactly one region at tick 0 echoing the plan key.
            assert hp.keys == [
                KeyRegion(start_tick=0, tonic_pc=plan.key.tonic_pc, mode=plan.key.mode)
            ], ctx

            # prechorus/bridge sections cadence on a D-function event (unless the
            # section is the final one, whose tail the final-close rewrote to T).
            ending_id = next(s.id for s in sf.sections if s.ending is not None)
            events_by_section: dict[str, list[ChordEvent]] = {}
            for e in hp.chords:
                events_by_section.setdefault(e.section_id, []).append(e)
            for sec in sf.sections:
                if sec.type in ("prechorus", "bridge") and sec.id != ending_id:
                    assert events_by_section[sec.id][-1].function == "D", (ctx, sec.id)

            # same-tag sections share identical bodies outside replaced (tagged)
            # bars: the leading untagged events match on the common prefix.
            untagged: dict[str, list[list[tuple[str, int, str, tuple[str, ...]]]]] = {}
            for sec in sf.sections:
                body: list[tuple[str, int, str, tuple[str, ...]]] = [
                    (
                        e.chord.symbol,
                        e.chord.root_pc,
                        e.chord.quality,
                        tuple(e.chord.extensions),
                    )
                    for e in events_by_section[sec.id]
                    if not e.tags
                ]
                untagged.setdefault(sec.harmony_tag, []).append(body)
            for bodies in untagged.values():
                first = bodies[0]
                for other in bodies[1:]:
                    k = min(len(first), len(other))
                    assert first[:k] == other[:k], ctx

            # pool_selections complete: every distinct tag + finals + each
            # boundary that actually swapped (turnaround:<sectionId>).
            tags = {s.harmony_tag for s in sf.sections}
            turnaround_keys = {
                f"turnaround:{e.section_id}"
                for e in hp.chords
                if "turnaround" in e.tags
            }
            assert set(hp.pool_selections) == tags | {"finals"} | turnaround_keys, ctx


# =============================================================================
# DoD 9 — deceptive fixture (the only exerciser of the dormant §5.4 rule, Q7)
# =============================================================================


@pytest.mark.parametrize(
    ("mode", "tonic_pc", "finals", "exp_symbol", "exp_root", "exp_quality"),
    [
        # major-class → `vi min7` (root = tonic+9); minor-class → `bVI maj`
        # (root = tonic+8). §5.4 fixed substitute, no draw.
        (
            "major",
            0,
            [{"id": "f", "weight": 1, "modes": ["major"], "bars": [["I"]]}],
            "Am7",
            9,
            "min7",
        ),
        (
            "minor",
            0,
            [{"id": "f", "weight": 1, "modes": ["minor"], "bars": [["i"]]}],
            "Ab",
            8,
            "maj",
        ),
    ],
)
def test_deceptive_substitute_end_to_end(
    mode: str,
    tonic_pc: int,
    finals: list[dict[str, Any]],
    exp_symbol: str,
    exp_root: int,
    exp_quality: str,
) -> None:
    """PHASE_4 §5.4 deceptive rule (dormant in v1, Q7) — a synthetic pack with
    an EMPTY `turnarounds` list and two adjacent same-tag sections whose first
    ends degree-1-rooted (function T) rewrites that boundary to the fixed
    substitute, tags it "deceptive", and consumes zero draws for the swap."""
    tonic = "I" if mode == "major" else "i"
    sub = "IV" if mode == "major" else "iv"  # S-function → no D-offset dressing
    progs = _progs(
        {
            "pools": {
                "t": [
                    {
                        "id": "p",
                        "weight": 1,
                        "modes": [mode],
                        "phrases": {"a": [[tonic], [sub], [sub], [tonic]]},
                    }
                ]
            },
            "turnarounds": [],
            "finals": finals,
        }
    )
    sf = _form(
        [
            _section("s1", "t", 0, [("a", 4)]),
            _section("s2", "t", 4, [("a", 4)], ending=True),
        ]
    )
    rng = _CountingRandom()
    rng.seed(7)
    rng.draws = 0
    hp = harmony(_plan(mode=mode, tonic_pc=tonic_pc), sf, progs, rng)

    boundary = [e for e in hp.chords if e.section_id == "s1"][-1]
    assert boundary.chord.symbol == exp_symbol
    assert boundary.chord.root_pc == exp_root
    assert boundary.chord.quality == exp_quality
    assert boundary.tags == ["deceptive"]
    # tier 0 + single candidate/option everywhere ⇒ the whole run, and the
    # deceptive swap in particular, draws zero times.
    assert rng.draws == 0


# =============================================================================
# §5.4 turnaround truncation — boundary-spanning hold event is clamped
# =============================================================================


def test_turnaround_shorter_than_hold_run_truncates() -> None:
    """A same-tag boundary whose terminal tonic run is a SINGLE 2-bar hold event
    (`i7 ~`) plus a drawn 1-bar turnaround (`[[iiø7, V7]]`, len 1 ≤ run 2). §5.4
    says replace only the run's last 1 bar, so the hold event is truncated to the
    first bar and the turnaround tiles the second — no overlap. Asserts the
    CORRECT tiling."""
    progs = _progs(
        {
            "pools": {
                "blues": [
                    {
                        "id": "b",
                        "weight": 1,
                        "modes": ["minor"],
                        # phrase ends on a 2-bar tonic hold (i7 ~): a single
                        # multi-bar terminal-tonic event.
                        "phrases": {"a": [["bVI7"], ["V7"], ["i7"], ["~"]]},
                    }
                ]
            },
            "turnarounds": [
                {
                    "id": "quick",
                    "weight": 1,
                    "modes": ["minor"],
                    "bars": [["iiø7", "V7"]],  # 1 bar
                }
            ],
            "finals": _FIN_MINOR,
        }
    )
    sf = _form(
        [
            _section("head-1", "blues", 0, [("a", 4)], section_type="head"),
            _section(
                "head-2", "blues", 4, [("a", 4)], section_type="head", ending=True
            ),
        ]
    )
    rng = _CountingRandom()
    rng.seed(3)
    hp = harmony(_plan(mode="minor", dissonance=0.65), sf, progs, rng)

    cursor = 0
    for e in hp.chords:
        assert e.start_tick == cursor  # fails on the overlapping turnaround event
        cursor += e.duration_ticks
    assert cursor == sf.total_bars * _TPB
