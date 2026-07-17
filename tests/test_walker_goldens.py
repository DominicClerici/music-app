"""§9.2 walker normative goldens (PHASE_5 DoD 5, SESSION_08 T4).

The independent golden transcriber: drives the REAL chained pipeline
(interpret → form → harmony → arrange → walk) for jazz/melancholic at seed
`1ps9wxb` (master 3735928559) and asserts the PHASE_5 **§9.2** printed values
verbatim — never read back off code output (ROADMAP §3 golden-value arbitration).

Draw counts are summed from a counting `random.Random` injected per absolute bar
via the walker's `rng_factory`, seeded at the REAL §3.6 per-bar seed
(`derive(derive(stream_seed(master, overrides, "bass"), "walk"), f"bar:{absBar}")`)
so outcomes match production; bars are mapped to sections through the form's
section bar ranges and the counts summed per section.

Pop bass is `mode: patterns` — the walker does not run for pop; the property
matrix therefore runs on jazz only (asserted).

ARBITRATED (golden-value arbitration, ROADMAP §3 — human sign-off): three §9.2
samples were wrong DERIVED doc values (no engine bug — the engine faithfully
implements the pinned §3.6/§6.3 text). §9.2 and these goldens were amended to
the engine's real output; the assertions below now pin the CORRECTED values:
   1. Solo note counts are 51/54/54 (not 50/53/53) — the §6.3 rule-6
      embellishment fires on each solo's final bar too (barInSection ≡ N−1),
      one extra dead-note ghost per section. Head/outro counts (24/24/7) hold.
   2. solo-1 bar-13 beat-4 approach is D♭2 (chromatic → D2), per §3.6 ascending
      approach-candidate ordering. Beats 1-3 hold.
   3. solo-1 bar-15 beat-4 approach is F1 (diatonic), and the and-of-4 ghost
      repeats F1. Beats 1-3 hold.
"""

from __future__ import annotations

import random

import pytest

from trackgen.arrangement import arrange
from trackgen.form.stage import form
from trackgen.harmony.stage import harmony
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.walker import (
    WalkNote,
    _chord_at,
    _first_scale_tone_below,
    _fold_into_lane,
    _next_target,
    walk,
)
from trackgen.schema.ir import (
    ArrangementPlan,
    ChordEvent,
    GenerationPlan,
    HarmonicPlan,
    SongForm,
)
from trackgen.seeds import Rng, derive, stream_rng, stream_seed, to_base36
from trackgen.theory import chord_tones, scale_pcs

_BAR = 1920
_BASS_LANE_LOW, _BASS_LANE_HIGH = 28, 55

_JAZZ_PARAMS: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


# --- note-name → MIDI (MIDI 60 = C4; D2 = 38) --------------------------------

_PC = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}  # fmt: skip


def _m(name: str) -> int:
    """`"D2"` → 38, `"Bb1"` → 34, `"Gb2"` → 42 (MIDI 60 = C4)."""
    i = len(name)
    while name[i - 1].isdigit():
        i -= 1
    return (int(name[i:]) + 1) * 12 + _PC[name[:i]]


# --- draw-counting shim (mirrors test_harmony_goldens / test_selection) -------


class _CountingRandom(random.Random):
    """Counts `randrange` calls — one per `weighted_choice`, hence one per draw."""

    def __init__(self, seed: int) -> None:
        super().__init__(seed)
        self.draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


# --- pipeline driver ----------------------------------------------------------


def _drive(
    params: dict[str, object],
) -> tuple[GenerationPlan, StylePack, SongForm, HarmonicPlan, ArrangementPlan]:
    plan = generate_plan(params)
    pack = resolve_pack(params["styleFamily"])  # type: ignore[arg-type]
    assert pack is not None and pack.forms is not None and pack.progressions is not None
    sf = form(plan, pack.forms)
    hp = harmony(
        plan,
        sf,
        pack.progressions,
        stream_rng(plan.seed.master, plan.seed.overrides, "harmony"),
    )
    ap = arrange(plan, sf, pack, Rng(0))
    return plan, pack, sf, hp, ap


def _walk_jazz() -> tuple[
    dict[str, list[WalkNote]], SongForm, HarmonicPlan, ArrangementPlan, GenerationPlan
]:
    plan, pack, sf, hp, ap = _drive(_JAZZ_PARAMS)
    walked = walk(
        ap, hp, sf, plan, pack, master=plan.seed.master, overrides=plan.seed.overrides
    )
    return walked, sf, hp, ap, plan


def _bar_to_section(sf: SongForm) -> dict[int, str]:
    out: dict[int, str] = {}
    for s in sf.sections:
        for b in range(s.start_bar, s.start_bar + s.length_bars):
            out[b] = s.id
    return out


def _at(notes: list[WalkNote], tick: int) -> int:
    """The (single melodic) note MIDI at exactly `tick` — excludes ghosts."""
    hits = [n.midi for n in notes if n.ticks == tick and "ghost" not in n.tags]
    assert len(hits) == 1, (tick, hits)
    return hits[0]


# =============================================================================
# §9.2 — per-section DRAW COUNTS (9/38/37/36/7/1, total 128) — REPRODUCES
# =============================================================================


def test_walker_draw_counts_per_section() -> None:
    """§9.2 golden per-section walker draw counts — a counting RNG per bar seeded
    at the real §3.6 per-bar seed, summed per section. Total 128."""
    plan, pack, sf, hp, ap = _drive(_JAZZ_PARAMS)
    walk_seed = derive(
        stream_seed(plan.seed.master, plan.seed.overrides, "bass"), "walk"
    )
    counters: dict[int, _CountingRandom] = {}

    def factory(abs_bar: int) -> Rng:
        shim = _CountingRandom(derive(walk_seed, f"bar:{abs_bar}"))
        counters[abs_bar] = shim
        return shim

    walk(
        ap,
        hp,
        sf,
        plan,
        pack,
        master=plan.seed.master,
        overrides=plan.seed.overrides,
        rng_factory=factory,
    )

    b2s = _bar_to_section(sf)
    per_section: dict[str, int] = {}
    for abs_bar, shim in counters.items():
        sid = b2s[abs_bar]
        per_section[sid] = per_section.get(sid, 0) + shim.draws

    assert per_section == {
        "head-1": 9,
        "solo-1": 38,
        "solo-2": 37,
        "solo-3": 36,
        "head-2": 7,
        "outro-1": 1,
    }
    assert sum(per_section.values()) == 128


# =============================================================================
# §9.2 — per-section NOTE COUNTS (24/51/54/54/24/7; solos corrected per C-09)
# =============================================================================


def test_walker_note_counts_reproducing_sections() -> None:
    """§9.2 note counts for head-1/head-2/outro-1 (24/24/7) — reproduce."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    assert len(walked["head-1"]) == 24
    assert len(walked["head-2"]) == 24
    assert len(walked["outro-1"]) == 7


def test_walker_note_counts_solos() -> None:
    """§9.2 solo-1/2/3 note counts 51/54/54 (corrected golden) — the §6.3 rule-6
    embellishment fires on each solo's final bar (barInSection ≡ N−1) too."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    assert [len(walked["solo-1"]), len(walked["solo-2"]), len(walked["solo-3"])] == [
        51,
        54,
        54,
    ]


# =============================================================================
# §9.2 — HEAD-1 excerpt (two-feel, bars 0-3) — REPRODUCES
# =============================================================================


def test_head1_bars_0_3_beat1_beat3() -> None:
    """§9.2 head-1 bars 0-3 beat-1 / beat-3: D2/A2 · G2/D2 · D2/A2 · D3/A2."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    h1 = walked["head-1"]
    expected = [
        ("D2", "A2"),
        ("G2", "D2"),
        ("D2", "A2"),
        ("D3", "A2"),
    ]
    for bar, (b1, b3) in enumerate(expected):
        assert _at(h1, bar * _BAR) == _m(b1), (bar, "beat1")
        assert _at(h1, bar * _BAR + 960) == _m(b3), (bar, "beat3")


def test_head1_turnaround_bars_10_11() -> None:
    """§9.2 turnaround bars 10-11 (2 chords/bar): root halves D3·B♭2 | E2·A2."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    h1 = walked["head-1"]
    assert _at(h1, 10 * _BAR) == _m("D3")
    assert _at(h1, 10 * _BAR + 960) == _m("Bb2")
    assert _at(h1, 11 * _BAR) == _m("E2")
    assert _at(h1, 11 * _BAR + 960) == _m("A2")


# =============================================================================
# §9.2 — SOLO-1 four-feel grid (bars 12-15)
# =============================================================================


def _four_feel(notes: list[WalkNote], bar: int) -> list[int]:
    return [_at(notes, bar * _BAR + b * 480) for b in range(4)]


def test_solo1_bar12_grid() -> None:
    """§9.2 solo-1 bar 12: D2 · E2(scale) · F2(chord) · G♭2(chromatic→G2)."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    assert _four_feel(walked["solo-1"], 12) == [_m("D2"), _m("E2"), _m("F2"), _m("Gb2")]


def test_solo1_bar14_grid() -> None:
    """§9.2 solo-1 bar 14: D2 · B♭1 · C2 · D♭2(chromatic→D2)."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    assert _four_feel(walked["solo-1"], 14) == [
        _m("D2"),
        _m("Bb1"),
        _m("C2"),
        _m("Db2"),
    ]


def test_solo1_bar13_beats_1_3() -> None:
    """§9.2 solo-1 bar 13 beats 1-3: G2 · A2 · F2 — reproduce."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    s1 = walked["solo-1"]
    assert [_at(s1, 13 * _BAR + b * 480) for b in range(3)] == [
        _m("G2"),
        _m("A2"),
        _m("F2"),
    ]


def test_solo1_bar13_beat4() -> None:
    """§9.2 solo-1 bar 13 beat 4 = D♭2 (chromatic → D2), corrected golden."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    assert _at(walked["solo-1"], 13 * _BAR + 1440) == _m("Db2")


def test_solo1_bar15_beats_1_3_and_decay_draw() -> None:
    """§9.2 solo-1 bar 15 beats 1-3: A1(fifth decay draw) · B♭1 · F1 — reproduce.
    The bar-15 beat-1 decay draw fires because bars 14-15 share Dm9."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    s1 = walked["solo-1"]
    assert [_at(s1, 15 * _BAR + b * 480) for b in range(3)] == [
        _m("A1"),
        _m("Bb1"),
        _m("F1"),
    ]


def test_solo1_bar15_beat4_and_ghost() -> None:
    """§9.2 solo-1 bar 15 beat 4 = F1 (diatonic) + and-of-4 dead-note ghost
    (tag "ghost") repeating the beat-4 pitch F1 — corrected golden."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    s1 = walked["solo-1"]
    assert _at(s1, 15 * _BAR + 1440) == _m("F1")
    ghost = [n for n in s1 if n.ticks == 15 * _BAR + 1680 and "ghost" in n.tags]
    assert len(ghost) == 1
    assert ghost[0].midi == _m("F1")


def test_solo1_bar15_has_ghost_on_and_of_4() -> None:
    """§9.2: the bar-15 embellishment lands on the and-of-4 (barInSection % 4 == 3,
    density 0.543 < 0.55 → N = 4). The ghost TAG + placement reproduce (its pitch
    is the diverging value covered above)."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    ghost = [
        n for n in walked["solo-1"] if n.ticks == 15 * _BAR + 1680 and "ghost" in n.tags
    ]
    assert len(ghost) == 1
    assert ghost[0].duration_ticks == 60
    assert ghost[0].velocity == 0.25


# =============================================================================
# §9.2 — OUTRO-1 (two-feel, final; final-bar rule) — REPRODUCES
# =============================================================================


def test_outro1_excerpt_and_final_bar_rule() -> None:
    """§9.2 outro-1: D2·A1 | G1·D2 | E2·A2 (2/bar) | D2 whole-note (final-bar
    rule, lowest in-lane placement)."""
    walked, _sf, _hp, _ap, _plan = _walk_jazz()
    o1 = walked["outro-1"]
    assert _at(o1, 60 * _BAR) == _m("D2")
    assert _at(o1, 60 * _BAR + 960) == _m("A1")
    assert _at(o1, 61 * _BAR) == _m("G1")
    assert _at(o1, 61 * _BAR + 960) == _m("D2")
    assert _at(o1, 62 * _BAR) == _m("E2")
    assert _at(o1, 62 * _BAR + 960) == _m("A2")
    # Final bar 63: one whole-note low D, lowest in-lane root, dur 1920.
    final_bar = [n for n in o1 if n.ticks >= 63 * _BAR]
    assert len(final_bar) == 1
    note = final_bar[0]
    assert note.ticks == 63 * _BAR
    assert note.midi == _m("D2")
    assert note.duration_ticks == 1920
    assert note.velocity == 0.75


# =============================================================================
# Property matrix — jazz × supported moods × seed/length spread (pop is patterns)
# =============================================================================

_SEEDS = [to_base36(((i + 1) * 2654435761) % (2**63)) for i in range(5)]
_LENGTHS = [120, 240, 360]


def test_pop_bass_is_patterns_walker_silent() -> None:
    """Pop bass is `mode: patterns` → the walker does not run (returns {})."""
    pop_params: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
    plan, pack, sf, hp, ap = _drive(pop_params)
    assert pack.bass_mode == "patterns"
    walked = walk(
        ap, hp, sf, plan, pack, master=plan.seed.master, overrides=plan.seed.overrides
    )
    assert walked == {}


def _governing(chords: list[ChordEvent], tick: int) -> ChordEvent:
    return _chord_at(chords, tick)


@pytest.mark.parametrize("mood", resolve_pack("jazz").interpreter.supported_moods)  # type: ignore[union-attr]
def test_walker_property_matrix_jazz(mood: str) -> None:
    """PHASE_5 §13.5 property — over jazz × supported mood × seed × length spread:
    every walker note in the bass lane; every bar's beat-1 is a chord tone
    (beat-1 root / decay rule); four-feel beat-4 approaches are half-step-below /
    scale-tone-below / dominant of the next target; the final-bar rule fires only
    on the song's final section (exactly one whole-note there, none elsewhere)."""
    from trackgen.arrangement.intensity import intensity

    lane_low, lane_high = _BASS_LANE_LOW, _BASS_LANE_HIGH

    for length in _LENGTHS:
        for seed in _SEEDS:
            params = {
                "styleFamily": "jazz",
                "mood": mood,
                "maxLengthSec": length,
                "seed": seed,
            }
            plan, pack, sf, hp, ap = _drive(params)
            assert pack.walking is not None
            walked = walk(
                ap,
                hp,
                sf,
                plan,
                pack,
                master=plan.seed.master,
                overrides=plan.seed.overrides,
            )
            chords = list(hp.chords)
            song_end = sf.total_bars * _BAR
            final_section = sf.sections[-1].id
            ctx = (mood, length, seed)

            whole_notes: list[tuple[str, int]] = []
            for sid, notes in walked.items():
                sec = next(s for s in sf.sections if s.id == sid)
                feel = pack.walking.feel_by_intensity[intensity(sec.energy)]
                for n in notes:
                    assert lane_low <= n.midi <= lane_high, (ctx, sid, n)
                    assert 0.0 < n.velocity <= 1.0, (ctx, sid, n)
                    if n.duration_ticks == 1920:
                        whole_notes.append((sid, n.ticks))

                # beat-1 of every bar is a governing chord tone.
                for n in notes:
                    if n.ticks % _BAR == 0 and "ghost" not in n.tags:
                        gov = _governing(chords, n.ticks)
                        assert n.midi % 12 in set(chord_tones(gov.chord)), (ctx, sid, n)

                # four-feel beat-4 approaches: one of the three §6.3-rule-5 folds.
                lane = _reg(lane_low, lane_high)
                if feel == "four":
                    for n in notes:
                        if n.ticks % _BAR != 1440 or "ghost" in n.tags:
                            continue
                        bar_start = (n.ticks // _BAR) * _BAR
                        gov = _governing(chords, bar_start)
                        if _governing(chords, bar_start + 960) is not gov:
                            continue  # two-chord bar: beat-4 keys off the 2nd chord
                        b1 = _at(notes, bar_start)
                        target = _next_target(
                            bar_start, b1, gov.chord, chords, lane, song_end
                        )
                        scale_set = set(scale_pcs(gov.scale.root_pc, gov.scale.name))
                        allowed = {
                            _fold_into_lane(target - 1, lane),
                            _fold_into_lane(
                                _first_scale_tone_below(target, scale_set), lane
                            ),
                            _fold_into_lane(target + 7, lane),
                        }
                        assert n.midi in allowed, (ctx, sid, n.ticks, n.midi, allowed)

            # final-bar rule: whole notes only in the final section (≤ 1).
            for sid, _tick in whole_notes:
                assert sid == final_section, (ctx, sid)
            assert len(whole_notes) <= 1, ctx


def _reg(low: int, high: int):  # type: ignore[no-untyped-def]
    from trackgen.schema.ir import Register

    return Register(low_midi=low, high_midi=high)
