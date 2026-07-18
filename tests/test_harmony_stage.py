"""Mechanism unit tests for the Harmony stage (PHASE_4 §5.1, SESSION_05 T2).

These exercise each §5.1 mechanism on small SYNTHETIC inputs — not the §10
worked-example goldens (a later task). Where a mechanism is proven via draw
accounting, a counting RNG shim (one `randrange` per `weighted_choice`) makes
the "draw iff >= 2" rule observable.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from trackgen.harmony.stage import _dress_slot, harmony
from trackgen.packs.models import ProgressionsConfig
from trackgen.schema.ir import (
    Budgets,
    ChordEvent,
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
from trackgen.theory import extensions_legal

_TPB = 1920


# --- fixture builders --------------------------------------------------------


class _CountingRandom(random.Random):
    """A seeded RNG that counts `randrange` calls — one per `weighted_choice`,
    hence one per draw. `getrandbits` (called internally by `randrange`) is not
    separately counted."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


def _counting_rng(seed: int = 12345) -> _CountingRandom:
    rng = _CountingRandom(seed)
    rng.draws = 0
    return rng


def _plan(
    *,
    mode: str = "major",
    tonic_pc: int = 0,
    dissonance: float = 0.1,
    valence: float = 0.0,
    hrb: float = 1.0,
    numerator: int = 4,
) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="synthetic", version="1"),
        seed=SeedSpec(master=1),
        key=Key(tonic_pc=tonic_pc, mode=mode),
        tempo_bpm=120.0,
        time_signature=TimeSignature(numerator=numerator, denominator=4),
        max_length_ticks=200 * _TPB,
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


def _progressions(config: dict[str, Any]) -> ProgressionsConfig:
    return ProgressionsConfig.model_validate(config)


# A minimal single-entry, single-candidate finals per mode (triad body → zero
# dressing draws at tier 0, single candidate → zero select draws).
_FINALS_MAJOR = [{"id": "fin", "weight": 1, "modes": ["major"], "bars": [["I"]]}]
_FINALS_MINOR = [{"id": "fin", "weight": 1, "modes": ["minor"], "bars": [["i"]]}]


def _events_of(plan_out: HarmonicPlan, section_id: str) -> list[ChordEvent]:
    return [e for e in plan_out.chords if e.section_id == section_id]


# --- gate filtering ----------------------------------------------------------


def test_mode_gate_excludes_wrong_mode_entry() -> None:
    progs = _progressions(
        {
            "pools": {
                "t": [
                    {
                        "id": "maj_one",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    },
                    {
                        "id": "min_one",
                        "weight": 1,
                        "modes": ["minor"],
                        "phrases": {"a": [["i"], ["bVI"], ["i"], ["bVI"]]},
                    },
                ]
            },
            "finals": _FINALS_MAJOR,
        }
    )
    form = _form([_section("s1", "t", 0, [("a", 4)], ending=True)])
    out = harmony(_plan(mode="major"), form, progs, _counting_rng())
    assert out.pool_selections["t"] == "maj_one"  # min_one gated out by mode


def test_valence_gate_excludes_out_of_band_entry() -> None:
    progs = _progressions(
        {
            "pools": {
                "t": [
                    {
                        "id": "always",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    },
                    {
                        "id": "bright",
                        "weight": 1,
                        "modes": ["major"],
                        "valence": [0.5, 1.0],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["IV"]]},
                    },
                ]
            },
            "finals": _FINALS_MAJOR,
        }
    )
    form = _form([_section("s1", "t", 0, [("a", 4)], ending=True)])
    # valence 0.0 excludes `bright` → only `always` eligible (no draw).
    out = harmony(_plan(valence=0.0), form, progs, _counting_rng())
    assert out.pool_selections["t"] == "always"


def test_dissonance_gate_excludes_out_of_band_entry() -> None:
    progs = _progressions(
        {
            "pools": {
                "t": [
                    {
                        "id": "always",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    },
                    {
                        "id": "spicy",
                        "weight": 1,
                        "modes": ["major"],
                        "dissonance": [0.5, 1.0],
                        "phrases": {"a": [["I"], ["vi"], ["IV"], ["IV"]]},
                    },
                ]
            },
            "finals": _FINALS_MAJOR,
        }
    )
    form = _form([_section("s1", "t", 0, [("a", 4)], ending=True)])
    out = harmony(_plan(dissonance=0.1), form, progs, _counting_rng())
    assert out.pool_selections["t"] == "always"


# --- density filter §5.2 -----------------------------------------------------

_SPARSE = {
    "id": "sparse",
    "weight": 1,
    "modes": ["major"],
    "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
}  # density 1.0
_DENSE = {
    "id": "dense",
    "weight": 1,
    "modes": ["major"],
    "phrases": {"a": [["I", "IV"], ["I", "IV"], ["I", "IV"], ["I", "IV"]]},
}  # 2.0
_DENSE2 = {
    "id": "dense2",
    "weight": 1,
    "modes": ["major"],
    "phrases": {"a": [["IV", "I"], ["IV", "I"], ["IV", "I"], ["IV", "I"]]},
}  # 2.0


def _density_form() -> SongForm:
    return _form([_section("s1", "t", 0, [("a", 4)], ending=True)])


def test_density_filter_restricts_when_subset_nonempty() -> None:
    # base 0.5 + mixed pool → restrict to density <= 1.0 = {sparse}: 1 candidate,
    # zero draws (and finals is single-candidate at tier 0 → zero draws too).
    progs = _progressions({"pools": {"t": [_DENSE, _SPARSE]}, "finals": _FINALS_MAJOR})
    rng = _counting_rng()
    out = harmony(_plan(hrb=0.5), _density_form(), progs, rng)
    assert out.pool_selections["t"] == "sparse"
    assert rng.draws == 0


def test_density_filter_inert_when_restriction_would_empty() -> None:
    # base 0.5 but every entry density > 1.0 → restriction empty → inert →
    # both eligible → exactly one select draw.
    progs = _progressions({"pools": {"t": [_DENSE, _DENSE2]}, "finals": _FINALS_MAJOR})
    rng = _counting_rng()
    harmony(_plan(hrb=0.5), _density_form(), progs, rng)
    assert rng.draws == 1


def test_density_filter_inert_at_base_one() -> None:
    # base 1.0 → no restriction → both eligible → one select draw.
    progs = _progressions({"pools": {"t": [_DENSE, _SPARSE]}, "finals": _FINALS_MAJOR})
    rng = _counting_rng()
    harmony(_plan(hrb=1.0), _density_form(), progs, rng)
    assert rng.draws == 1


# --- one draw per distinct tag (identical bodies) ----------------------------


def test_same_tag_sections_get_identical_bodies() -> None:
    progs = _progressions(
        {
            "pools": {
                "verse": [
                    {
                        "id": "v1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["V"]]},
                    },
                    {
                        "id": "v2",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["V"], ["vi"], ["IV"]]},
                    },
                ],
                "bridge": [
                    {
                        "id": "b1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["vi"], ["IV"], ["I"], ["V"]]},
                    },
                ],
                "chorus": [
                    {
                        "id": "c1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["V"], ["vi"], ["IV"]]},
                    },
                ],
            },
            "finals": _FINALS_MAJOR,
        }
    )
    # verse sections are non-adjacent (bridge between) → no boundary transform.
    form = _form(
        [
            _section("verse-1", "verse", 0, [("a", 4)]),
            _section("bridge-1", "bridge", 4, [("a", 4)]),
            _section("verse-2", "verse", 8, [("a", 4)]),
            _section("chorus-1", "chorus", 12, [("a", 4)], ending=True),
        ]
    )
    out = harmony(_plan(), form, progs, _counting_rng())
    v1 = [
        (e.chord.symbol, e.chord.quality, e.function)
        for e in _events_of(out, "verse-1")
    ]
    v2 = [
        (e.chord.symbol, e.chord.quality, e.function)
        for e in _events_of(out, "verse-2")
    ]
    assert v1 == v2 and len(v1) == 4


# --- hold-merge within a phrase; re-statement across instances ---------------


def test_hold_merges_within_instance_but_restates_across_instances() -> None:
    progs = _progressions(
        {
            "pools": {
                "hold": [
                    {
                        "id": "h1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["~"]]},
                    },
                ],
                "tail": [
                    {
                        "id": "t1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    },
                ],
            },
            "finals": _FINALS_MAJOR,
        }
    )
    form = _form(
        [
            _section("s1", "hold", 0, [("a", 2), ("a", 2)]),
            _section("s2", "tail", 4, [("a", 4)], ending=True),
        ]
    )
    out = harmony(_plan(), form, progs, _counting_rng())
    s1 = _events_of(out, "s1")
    # Two separate I events (one per phrase instance), each hold-extended to a
    # full 2 bars: the `~` merged within the instance, the repeat re-stated.
    assert [(e.start_tick, e.duration_ticks) for e in s1] == [
        (0, 2 * _TPB),
        (2 * _TPB, 2 * _TPB),
    ]


# --- terminal-tonic run + turnaround swap ------------------------------------


def test_turnaround_replaces_terminal_tonic_run() -> None:
    progs = _progressions(
        {
            "pools": {
                "blues": [
                    {
                        "id": "bl",
                        "weight": 1,
                        "modes": ["minor"],
                        "phrases": {"a": [["iv7"], ["V7"], ["i7"], ["~"]]},
                    },
                ]
            },
            "turnarounds": [
                {
                    "id": "turn",
                    "weight": 1,
                    "modes": ["minor"],
                    "bars": [["i7"], ["iiø7", "V7"]],
                },
            ],
            "finals": _FINALS_MINOR,
        }
    )
    form = _form(
        [
            _section("head-1", "blues", 0, [("a", 4)], section_type="head"),
            _section(
                "head-2", "blues", 4, [("a", 4)], section_type="head", ending=True
            ),
        ]
    )
    out = harmony(_plan(mode="minor"), form, progs, _counting_rng())
    s1 = _events_of(out, "head-1")
    # iv7 (bar0), V7 (bar1) untouched; the 2-bar terminal i7 run (bars 2-3)
    # replaced by the turnaround: i7 | iiø7 V7.
    assert [e.tags for e in s1] == [
        [],
        [],
        ["turnaround"],
        ["turnaround"],
        ["turnaround"],
    ]
    tail = s1[2:]
    assert [e.start_tick for e in tail] == [2 * _TPB, 3 * _TPB, 3 * _TPB + 960]
    assert out.pool_selections["turnaround:head-1"] == "turn"


# --- deceptive fallback (dormant rule) ---------------------------------------


@pytest.mark.parametrize(
    ("mode", "tonic_pc", "finals", "exp_quality", "exp_root"),
    [
        ("major", 0, _FINALS_MAJOR, "min7", 9),  # vi min7 → Am7
        ("minor", 0, _FINALS_MINOR, "maj", 8),  # bVI maj → Ab
    ],
)
def test_deceptive_fallback_no_turnaround(
    mode: str,
    tonic_pc: int,
    finals: list[dict[str, Any]],
    exp_quality: str,
    exp_root: int,
) -> None:
    tonic_token = "I" if mode == "major" else "i"
    sub = "IV" if mode == "major" else "iv"
    progs = _progressions(
        {
            "pools": {
                "t": [
                    # subdominant (not V) so no D-offset dressing draw occurs;
                    # ends degree-1-rooted so the deceptive path triggers.
                    {
                        "id": "p1",
                        "weight": 1,
                        "modes": [mode],
                        "phrases": {"a": [[tonic_token], [sub], [sub], [tonic_token]]},
                    },
                ]
            },
            "turnarounds": [],  # empty → deceptive path
            "finals": finals,
        }
    )
    form = _form(
        [
            _section("s1", "t", 0, [("a", 4)]),
            _section("s2", "t", 4, [("a", 4)], ending=True),
        ]
    )
    rng = _counting_rng()
    out = harmony(_plan(mode=mode, tonic_pc=tonic_pc), form, progs, rng)
    last = _events_of(out, "s1")[-1]
    assert last.chord.quality == exp_quality
    assert last.chord.root_pc == exp_root
    assert last.tags == ["deceptive"]
    # Single candidate everywhere + tier 0 → the ONLY draws possible are none;
    # the deceptive substitution consumes zero.
    assert rng.draws == 0


# --- final close -------------------------------------------------------------


def test_final_close_replaces_final_bars_and_is_idempotent() -> None:
    progs = _progressions(
        {
            "pools": {
                "verse": [
                    {
                        "id": "v1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["V"]]},
                    },
                ]
            },
            "finals": [
                {
                    "id": "authentic",
                    "weight": 1,
                    "modes": ["major"],
                    "bars": [["V"], ["I"]],
                },
            ],
        }
    )
    form = _form([_section("v", "verse", 0, [("a", 4)], ending=True)])
    out1 = harmony(_plan(), form, progs, _counting_rng())
    v = _events_of(out1, "v")
    assert [e.tags for e in v] == [[], [], ["final"], ["final"]]
    assert out1.pool_selections["finals"] == "authentic"
    # deterministic re-run → identical plan.
    out2 = harmony(_plan(), form, progs, _counting_rng())
    assert out1 == out2


# --- §3.5 authored-extension pin: dressing is draw-free ----------------------


def test_authored_extension_slot_consumes_zero_dressing_draws() -> None:
    # §3.5 / DoD §14.1: an authored extension fully pins the slot — dressing
    # yields a single option, so `_dress_slot` makes NO `weighted_choice` draw.
    # At base tier 4 a *plain* V7 (D-function → effective tier 5) has >= 2
    # options and WOULD draw (see the contrast test below); the `#9` pin removes
    # that draw. Were the dressing guard removed, `draws` here would be 1.
    key = Key(tonic_pc=0, mode="major")
    rng = _counting_rng()
    spec = _dress_slot("V7(#9)", key, base_tier=4, rng=rng)
    assert spec.extensions == ["#9"]
    assert spec.quality == "dom7"
    assert rng.draws == 0


def test_unextensioned_dom7_draws_at_same_tier_for_contrast() -> None:
    # The discriminator for the pin test: an *un-extensioned* V7 at the identical
    # tier/function DOES draw exactly once (>= 2 dressing options).
    key = Key(tonic_pc=0, mode="major")
    rng = _counting_rng()
    _dress_slot("V7", key, base_tier=4, rng=rng)
    assert rng.draws == 1


# --- structural invariants ---------------------------------------------------


def _rich_setup() -> tuple[GenerationPlan, SongForm, ProgressionsConfig]:
    progs = _progressions(
        {
            "pools": {
                "verse": [
                    {
                        "id": "v1",
                        "weight": 3,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["V"]]},
                    },
                    {
                        "id": "v2",
                        "weight": 2,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["V"], ["vi"], ["IV"]]},
                    },
                ],
                "chorus": [
                    {
                        "id": "c1",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["V"], ["vi"], ["IV"]]},
                    },
                ],
            },
            "finals": [
                {
                    "id": "authentic",
                    "weight": 1,
                    "modes": ["major"],
                    "bars": [["V"], ["I"]],
                },
                {
                    "id": "plagal",
                    "weight": 1,
                    "modes": ["major"],
                    "bars": [["IV"], ["I"]],
                },
            ],
        }
    )
    form = _form(
        [
            _section("verse-1", "verse", 0, [("a", 4), ("a", 4)]),
            _section("chorus-1", "chorus", 8, [("a", 4)]),
            _section("verse-2", "verse", 12, [("a", 4)]),
            _section("chorus-2", "chorus", 16, [("a", 4)], ending=True),
        ]
    )
    # tier 2 dissonance so bare triads dress (dressing draws happen).
    return _plan(dissonance=0.4), form, progs


def test_events_tile_song_with_scale_and_function() -> None:
    plan, form, progs = _rich_setup()
    out = harmony(plan, form, progs, _counting_rng())
    cursor = 0
    for e in out.chords:
        assert e.start_tick == cursor  # no gaps / overlaps, ascending
        cursor += e.duration_ticks
        assert e.scale is not None and e.function in ("T", "S", "D", "O")
        assert extensions_legal(e.chord.quality, e.chord.extensions)
    assert cursor == form.total_bars * _TPB


def test_keys_is_single_region_at_tick_zero() -> None:
    plan, form, progs = _rich_setup()
    out = harmony(plan, form, progs, _counting_rng())
    assert out.keys == [
        KeyRegion(start_tick=0, tonic_pc=plan.key.tonic_pc, mode=plan.key.mode)
    ]


def test_determinism_same_inputs_same_plan() -> None:
    plan, form, progs = _rich_setup()
    assert harmony(plan, form, progs, _counting_rng(7)) == harmony(
        plan, form, progs, _counting_rng(7)
    )


# --- guards ------------------------------------------------------------------


def test_rejects_non_four_four() -> None:
    progs = _progressions(
        {
            "pools": {
                "t": [
                    {
                        "id": "p",
                        "weight": 1,
                        "modes": ["major"],
                        "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
                    }
                ]
            },
            "finals": _FINALS_MAJOR,
        }
    )
    form = _form([_section("s1", "t", 0, [("a", 4)], ending=True)])
    with pytest.raises(ValueError, match="4/4"):
        harmony(_plan(numerator=3), form, progs, _counting_rng())
