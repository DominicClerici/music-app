"""blues pack — config + bank-inventory pins, the `bl_dr_2` / `bl_bs_3` golden
anchors, the blues first-use machinery pins, and the end-to-end validation slice
(SESSION_21 T5, PHASE_8 §5 under the S21-2 rung re-map).

The blues first-uses (SESSION_21 constraint 11 / DoD §14.1/§14.3):

- **authored paren extensions** `I7(#9)`/`V7(#9)` — the first pack ever to author
  an extension group (§3.5); the pinned slot consumes ZERO dressing draws and the
  emitted `ChordSpec` carries `#9` verbatim.
- **triplet-grid pattern content** — the slow-blues 12/8 patterns are the first
  triplet-grid content anywhere; swing8 (which only touches `pos % 480 == 240`)
  leaves their `{0, 160, 320}` onsets alone, and W7 stays clean.
- **tempo-gated eligibility** — the `[50, 75]` slow-blues band renders only at the
  slow tier (melancholic), never at an energetic render.
- the `stop` device firing at the `[1, 3]` odds blues enables (a golden-covered
  production path, not a first-use — but exercised here on a locked seed).

Companion module `test_blues_variety.py` owns the per-candidate selection locks
(M1 convention). Determinism (ROADMAP invariant 5): every seed is a pinned
literal; no `random`-for-entropy / `time` / `datetime` import (TID251). The one
`random` import is a *counting* RNG shim (the harmony-stage draw-accounting seam),
never an entropy source.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytest
import yaml

from trackgen.harmony.stage import _dress_slot
from trackgen.humanize.stage import _run, _ZeroJitter
from trackgen.interpreter.stage import generate_plan
from trackgen.packs.loader import resolve_pack
from trackgen.packs.models import DrumEvent, PatternEnvelope, PitchedEvent, StylePack
from trackgen.pipeline.explain import (
    DeviceRecord,
    EntryRecord,
    ExplainCollector,
    PatternRecord,
    TempoRecord,
)
from trackgen.pipeline.trace import generate_trace
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.ir import Key
from trackgen.schema.validate import validate_document

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "blues"
BAR = 1920


def _pack() -> StylePack:
    pack = resolve_pack("blues")
    assert pack is not None, "blues did not resolve"
    return pack


def _entry(pack: StylePack, role: str, entry_id: str) -> PatternEnvelope:
    return next(e for e in pack.patterns[role] if e.id == entry_id)


def _drum_tuples(
    env: PatternEnvelope,
) -> list[tuple[int, str, float, int | None, float | None]]:
    """(pos, voice, velocity, dur, minDensity) per drum event, authored order."""
    out: list[tuple[int, str, float, int | None, float | None]] = []
    for e in env.events:
        assert isinstance(e, DrumEvent)
        out.append((e.pos, e.voice, e.velocity, e.dur, e.min_density))
    return out


def _pitched_tuples(
    env: PatternEnvelope,
) -> list[tuple[int, int, str, int, float, bool]]:
    """(pos, dur, degree, octave, velocity, push) per pitched event."""
    out: list[tuple[int, int, str, int, float, bool]] = []
    for e in env.events:
        assert isinstance(e, PitchedEvent)
        out.append((e.pos, e.dur, e.degree, e.octave, e.velocity, e.push))
    return out


def _counts_by_rung(
    entries: list[PatternEnvelope], kind: str
) -> dict[int, list[tuple[str, int]]]:
    out: dict[int, list[tuple[str, int]]] = {}
    for e in entries:
        if e.kind == kind:
            out.setdefault(e.energy_level, []).append((e.id, e.weight))
    return {k: sorted(v) for k, v in out.items()}


# --- (a1) manifest + interpreter config pins ---------------------------------


def test_manifest_fields() -> None:
    """S21-1: the manifest carries the two required fields the §5.1 snippet
    omitted (`formatVersion: 1`, `engine: >=0.1`), version 0.1.0 (S21-5), and the
    §5.1 tempo range / time signature."""
    m = _pack().manifest
    assert m.format_version == 1
    assert m.engine == ">=0.1"
    assert m.version == "0.1.0"
    assert m.tempo_range == (50, 150)
    assert m.time_signatures == [(4, 4)]


def test_interpreter_config() -> None:
    i = _pack().interpreter
    assert i is not None
    assert i.supported_moods == [
        "energetic",
        "nostalgic",
        "melancholic",
        "aggressive",
        "dark",
        "tense",
        "mysterious",
        "romantic",
    ]
    assert i.default_mood == "energetic"
    assert i.modes == ["major", "minor"]
    assert i.tonics == {"major": ["E", "A", "G", "C"], "minor": ["A", "E", "D"]}
    # swing8 with NO swingRatio override (S21-4: the §6.4 table is the authority).
    assert i.feel == "swing8"
    assert i.swing_ratio is None
    assert i.feel_table == "straight"
    assert i.expression_ranges.density == (0.25, 0.80)
    assert i.expression_ranges.dissonance == (0.50, 0.90)
    assert i.flavors == {
        "drums": ["blues_kit", "roadhouse_kit"],
        "bass": ["electric_round", "upright_soft"],
        "comping": ["crunch_guitar", "organ_drawbar"],
        "pads": ["organ_swell", "warm_strings"],
    }
    assert set(i.ensembles) == {"default", "lounge"}


def test_forms_jam_template_shape() -> None:
    """The all-solo jam form (§5.2): energy envelope [0.15, 0.95], one `jam`
    template whose spine is intro? + repeat(count [3, null]) of solo + outro?,
    closing `cold` with a 4-bar tag; degrade + fallback authored."""
    f = _pack().forms
    assert f is not None
    assert f.energy_range == (0.15, 0.95)
    assert [t.id for t in f.templates] == ["jam"]
    jam = f.templates[0].model_dump()
    assert jam["ending"] == {"tag_bars": 4, "close": "cold"}
    assert jam["fallback"] == {"section": "solo", "bars": 12}
    # spine: intro (optional [1,1]) -> repeat(count [3, null], solo) -> outro
    spine = jam["spine"]
    assert spine[0]["section"] == "intro" and spine[0]["optional"] == (1, 1)
    assert spine[1]["repeat"]["count"] == (3, None)
    assert spine[1]["repeat"]["slots"] == (
        {"section": "solo", "optional": None, "energy": None, "variant": None},
    )
    assert spine[2]["section"] == "outro" and spine[2]["optional"] == (2, 1)


def test_progressions_inventory_and_gate_bands() -> None:
    """The §5.3 pool/turnaround/final inventories, with the authored valence/
    dissonance gate bands (hendrix's aggressive corner, the jazz_turn and tritone
    dissonance floors) pinned."""
    pr = _pack().progressions
    assert pr is not None
    assert set(pr.pools) == {"blues_12", "blues_8", "blues_16", "intro", "outro"}
    b12 = {(e.id, e.weight, e.valence, e.dissonance) for e in pr.pools["blues_12"]}
    assert b12 == {
        ("quick_change", 60, None, None),
        ("plain", 25, None, None),
        ("hendrix", 15, (-1.0, -0.3), (0.70, 1.0)),
        ("minor_12", 100, None, None),
    }
    turns = {(e.id, e.weight, e.dissonance) for e in pr.turnarounds}
    assert turns == {
        ("v_four", 50, None),
        ("quick_v", 30, None),
        ("jazz_turn", 20, (0.60, 1.0)),
        ("minor_turn", 60, None),
        ("minor_quick", 40, None),
    }
    finals = {(e.id, e.weight, e.dissonance) for e in pr.finals}
    assert finals == {
        ("authentic", 40, None),
        ("plagal", 30, None),
        ("tritone", 30, (0.60, 1.0)),
        ("minor_auth", 60, None),
        ("minor_plagal", 40, None),
    }


def test_transitions_config() -> None:
    """§5.5: blues fills often ([1, 2]), enables the stop device at [1, 3], and a
    wide crash band."""
    tr = _pack().transitions
    assert tr is not None
    assert tr.phrase_fill.odds == (1, 2)
    assert tr.stop.enabled is True
    assert tr.stop.odds == (1, 3)
    assert tr.crash.velocity == (0.45, 0.90)


# --- (a2) bank inventory pins (M1 convention: trips on any bank edit) ---------


def test_pack_loads_and_is_patterns_mode() -> None:
    pack = _pack()
    assert pack.bass_mode == "patterns"
    assert pack.layering_order == ("drums", "bass", "comping", "pads")


def test_candidate_counts_drums() -> None:
    """Drums main ladder under the S21-2 re-map: rung 1 sparse shuffle, rung 2
    light-Chicago (bl_dr_lc/lcb — the pinned bl_dr_2 forced the rung-2 rename),
    rung 3 the workhorse Chicago pair PLUS the two tempo-gated slow-blues 12/8
    entries, rung 4 Texas/double-shuffle. Two fills (one per rung)."""
    drums = _pack().patterns["drums"]
    assert _counts_by_rung(drums, "main") == {
        1: [("bl_dr_1", 3), ("bl_dr_1b", 2)],
        2: [("bl_dr_lc", 3), ("bl_dr_lcb", 2)],
        3: [("bl_dr_2", 3), ("bl_dr_3b", 2), ("bl_dr_3s", 3), ("bl_dr_3sb", 2)],
        4: [("bl_dr_4", 3), ("bl_dr_4b", 2)],
    }
    assert _counts_by_rung(drums, "intro") == {1: [("bl_dr_i", 3), ("bl_dr_ib", 2)]}
    assert _counts_by_rung(drums, "ending") == {1: [("bl_dr_e", 3), ("bl_dr_eb", 2)]}
    # exactly two fills, singletons (PT12; not variety-linted). f1 straight-grid
    # snare buildup (T5 defect fix), f2 tom-run.
    assert _counts_by_rung(drums, "fill") == {
        3: [("bl_dr_f1", 1)],
        4: [("bl_dr_f2", 1)],
    }


def test_candidate_counts_bass() -> None:
    """Bass rung 3 is a 3/1 pair — the pinned `bl_bs_3` boogie cell (weight 1) +
    the box `bl_bs_3b` (weight 3) — plus the two tempo-gated slow-blues arpeggios;
    every other rung a plain 3/2 pair."""
    bass = _pack().patterns["bass"]
    assert _counts_by_rung(bass, "main") == {
        1: [("bl_bs_1", 3), ("bl_bs_1b", 2)],
        2: [("bl_bs_2", 3), ("bl_bs_2b", 2)],
        3: [("bl_bs_3", 1), ("bl_bs_3b", 3), ("bl_bs_3s", 3), ("bl_bs_3sb", 2)],
        4: [("bl_bs_4", 3), ("bl_bs_4b", 2)],
    }
    assert _counts_by_rung(bass, "intro") == {1: [("bl_bs_i", 3), ("bl_bs_ib", 2)]}
    assert _counts_by_rung(bass, "ending") == {1: [("bl_bs_e", 3), ("bl_bs_eb", 2)]}


def test_candidate_counts_comping() -> None:
    """Comping rung 3 carries the chank pair plus the tempo-gated triplet-roll."""
    comping = _pack().patterns["comping"]
    assert _counts_by_rung(comping, "main") == {
        1: [("bl_cp_1", 3), ("bl_cp_1b", 2)],
        2: [("bl_cp_2", 3), ("bl_cp_2b", 2)],
        3: [("bl_cp_3", 3), ("bl_cp_3b", 2), ("bl_cp_3s", 2)],
        4: [("bl_cp_4", 3), ("bl_cp_4b", 2)],
    }
    assert _counts_by_rung(comping, "intro") == {1: [("bl_cp_i", 3), ("bl_cp_ib", 2)]}
    assert _counts_by_rung(comping, "ending") == {1: [("bl_cp_e", 3), ("bl_cp_eb", 2)]}


def test_candidate_counts_pads() -> None:
    """Pads — a plain 3/2 pair at every rung (velocity ladder 0.30 -> 0.55)."""
    pads = _pack().patterns["pads"]
    assert _counts_by_rung(pads, "main") == {
        1: [("bl_pd_1", 3), ("bl_pd_1b", 2)],
        2: [("bl_pd_2", 3), ("bl_pd_2b", 2)],
        3: [("bl_pd_3", 3), ("bl_pd_3b", 2)],
        4: [("bl_pd_4", 3), ("bl_pd_4b", 2)],
    }
    assert _counts_by_rung(pads, "intro") == {1: [("bl_pd_i", 3), ("bl_pd_ib", 2)]}
    assert _counts_by_rung(pads, "ending") == {1: [("bl_pd_e", 3), ("bl_pd_eb", 2)]}


def test_gated_entries_carry_the_50_75_band() -> None:
    """The five slow-blues entries are tempo-gated to exactly [50, 75]; every
    other pattern is ungated (constraint 6)."""
    pack = _pack()
    gated = {
        e.id: e.eligibility.tempo_bpm
        for role in ("drums", "bass", "comping", "pads")
        for e in pack.patterns[role]
        if e.eligibility.tempo_bpm is not None
    }
    assert gated == {
        "bl_dr_3s": (50, 75),
        "bl_dr_3sb": (50, 75),
        "bl_bs_3s": (50, 75),
        "bl_bs_3sb": (50, 75),
        "bl_cp_3s": (50, 75),
    }


def test_voicing_class_maps() -> None:
    pack = _pack()
    assert pack.voicing["comping"].classes == {
        1: ("shell2", "triad_open"),
        2: ("shell3", "rootless_a"),
        3: ("rootless_a", "rootless_b"),
        4: ("rootless_a", "rootless_b"),
    }
    assert pack.voicing["pads"].classes == {
        i: ("triad_open", "fifths") for i in range(1, 5)
    }


def test_retarget_windows() -> None:
    pack = _pack()
    # bass {28,45}, comping {50,69}, pads {45,64} — bank defaults on every entry.
    for role, lo, hi in (("bass", 28, 45), ("comping", 50, 69), ("pads", 45, 64)):
        for env in pack.patterns[role]:
            assert env.retarget is not None, f"{role}/{env.id} missing retarget"
            assert (env.retarget.register_low, env.retarget.register_high) == (lo, hi)
            assert env.retarget.on_chord_change == "retrigger"
    # drums are lane-exempt — no retarget.
    for env in pack.patterns["drums"]:
        assert env.retarget is None


# --- (b) verbatim golden anchors (§5.4, byte-frozen at their S21-2 rungs) ------


def test_golden_bl_dr_2_verbatim() -> None:
    """The §5.4 defining Chicago-shuffle entry, id + events byte-verbatim; S21-2
    re-maps it from the printed energyLevel 2 to energyLevel 3 (the reachable
    rung the rising solo arch actually renders)."""
    env = _entry(_pack(), "drums", "bl_dr_2")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        3,
        3,
        1920,
    )
    assert _drum_tuples(env) == [
        (0, "kick", 0.90, None, None),
        (960, "kick", 0.86, None, None),
        (480, "snare", 0.88, None, None),
        (1440, "snare", 0.85, None, None),
        (0, "hat_closed", 0.60, None, None),
        (240, "hat_closed", 0.42, None, None),
        (480, "hat_closed", 0.52, None, None),
        (720, "hat_closed", 0.42, None, None),
        (960, "hat_closed", 0.56, None, None),
        (1200, "hat_closed", 0.42, None, None),
        (1440, "hat_closed", 0.52, None, None),
        (1680, "hat_closed", 0.44, None, None),
    ]


def test_golden_bl_bs_3_verbatim() -> None:
    """The §5.4 defining 2-bar boogie cell, id + events + energyLevel 3 + weight 1
    byte-verbatim (3840 ticks; resolves against the pinned dom7s to
    R-3-5-6-b7-6-5-3, the `sixth` degree's reserved purpose)."""
    env = _entry(_pack(), "bass", "bl_bs_3")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        3,
        1,
        3840,
    )
    assert _pitched_tuples(env) == [
        (0, 480, "root", 0, 0.76, False),
        (480, 480, "third", 0, 0.70, False),
        (960, 480, "fifth", 0, 0.72, False),
        (1440, 480, "sixth", 0, 0.70, False),
        (1920, 480, "seventh", 0, 0.74, False),
        (2400, 480, "sixth", 0, 0.70, False),
        (2880, 480, "fifth", 0, 0.72, False),
        (3360, 480, "third", 0, 0.70, False),
    ]


# --- (c) timbre pins (§5.6 / TB1 / TB7) ---------------------------------------


def _timbres_raw() -> dict[str, Any]:
    data = yaml.safe_load((_PACK_DIR / "timbres.yaml").read_text())
    assert isinstance(data, dict)
    return data


def test_all_eight_flavors_authored() -> None:
    """TB1: every one of the 8 interpreter-declared flavors has a full recipe."""
    raw = _timbres_raw()
    got = {f for role in raw["flavors"].values() for f in role}
    assert got == {
        "blues_kit",
        "roadhouse_kit",
        "electric_round",
        "upright_soft",
        "crunch_guitar",
        "organ_drawbar",
        "organ_swell",
        "warm_strings",
    }


def test_amsynth_organs_override_brightness_to_harmonicity() -> None:
    """TB7 — the silent trap: BOTH AMSynth organs (drawbar AND swell) must fully
    override the default brightness path (filterEnvelope.baseFrequency, illegal on
    AMSynth) to the harmonicity lever."""
    raw = _timbres_raw()
    drawbar = raw["flavors"]["comping"]["organ_drawbar"]
    swell = raw["flavors"]["pads"]["organ_swell"]
    for flavor in (drawbar, swell):
        bright = flavor["mod"]["brightness"]
        assert [m["param"] for m in bright] == ["harmonicity"]
        assert (bright[0]["min"], bright[0]["max"]) == (1.0, 2.0)


def test_upright_soft_fmsynth_full_override() -> None:
    """TB7 — upright_soft is an FMSynth: the bass default brightness/attack maps
    (filterEnvelope.*/filter.Q, none of which exist on FMSynth) are fully replaced
    by FM levers (modulationIndex + envelope.attack)."""
    raw = _timbres_raw()
    up = raw["flavors"]["bass"]["upright_soft"]
    assert up["engine"]["type"] == "FMSynth"
    assert [m["param"] for m in up["mod"]["brightness"]] == ["modulationIndex"]
    assert [m["param"] for m in up["mod"]["attackHardness"]] == ["envelope.attack"]


def test_blues_kit_kick_is_dry_and_master_is_compressor_then_limiter() -> None:
    """The kick is dry (no reverb send), and the master chain is the pop_rock-style
    [Compressor, Limiter] with the Limiter last (TB4)."""
    raw = _timbres_raw()
    kick_mix = raw["flavors"]["drums"]["blues_kit"]["kit"]["kick"]["mix"]
    assert "sends" not in kick_mix  # dry
    master = [d["type"] for d in raw["master"]]
    assert master == ["Compressor", "Limiter"]


# --- (d) first-use machinery pins ---------------------------------------------

# The (mood, seed) whose harmony draws the aggressive-gated `hendrix` pool entry:
# hendrix needs major mode AND valence [-1.0,-0.3] AND dissonance [0.70,1.0]. The
# negative-valence moods auto-resolve to MINOR, so the corner is reached by forcing
# `key.mode: major` on aggressive (valence -0.60, dissonance 0.774). Found on the
# first eligible seed (seed 1) by fixed enumeration.
_HENDRIX_PARAMS = {
    "styleFamily": "blues",
    "mood": "aggressive",
    "seed": "1",
    "maxLengthSec": 180,
    "key": {"mode": "major"},
}


def test_authored_extension_emitted_verbatim_through_the_pipeline() -> None:
    """§3.5 / DoD §14.1: a full render that draws the `hendrix` pool entry emits
    `ChordSpec.extensions == ['#9']` verbatim on every I7(#9)/V7(#9) slot, with
    the source token preserved in `roman` and quality dom7 (P11-legal)."""
    col = ExplainCollector()
    trace = generate_trace(_HENDRIX_PARAMS, explain=col)
    assert any(
        isinstance(r, EntryRecord) and r.chosen == "hendrix" for r in col.records
    ), "hendrix pool entry was not drawn"
    pinned = [
        c.chord for c in trace.harmony.chords if c.chord.roman in ("I7(#9)", "V7(#9)")
    ]
    assert pinned, "no authored-#9 slots emitted"
    for spec in pinned:
        assert spec.extensions == ["#9"]
        assert spec.quality == "dom7"


class _CountingRandom(random.Random):
    """A seeded RNG that counts `randrange` calls — one per `weighted_choice`,
    hence one per dressing draw (the harmony-stage draw-accounting seam)."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


def _counting_rng() -> _CountingRandom:
    rng = _CountingRandom(12345)
    rng.draws = 0
    return rng


def test_authored_extension_slot_is_draw_free_with_discriminating_contrast() -> None:
    """§3.5 draw-free pin: dressing an authored `#9` slot makes NO `weighted_choice`
    draw (the pin removes all options), while an un-extensioned dom7 at the identical
    tier DOES draw — the discriminator that proves the pin, not a vacuous zero.

    base_tier 5 is `tier(0.774)`, blues' aggressive dissonance (the hendrix corner);
    E major (tonic_pc 4) is the render's key."""
    key = Key(tonic_pc=4, mode="major")
    for pinned in ("I7(#9)", "V7(#9)"):
        rng = _counting_rng()
        spec = _dress_slot(pinned, key, base_tier=5, rng=rng)
        assert spec.extensions == ["#9"]
        assert spec.quality == "dom7"
        assert rng.draws == 0
    # contrast: the same degrees WITHOUT the authored group draw exactly once each
    # (>= 2 dressing options survive at this tier/function).
    for dressable in ("I7", "V7", "IV7"):
        rng = _counting_rng()
        _dress_slot(dressable, key, base_tier=5, rng=rng)
        assert rng.draws == 1, f"{dressable} did not draw (pin test is non-vacuous)"


# The melancholic cell whose selection picks a gated 12/8 drum pattern (bl_dr_3sb),
# drawn at a [50, 75]-band tempo (65 BPM). Found by fixed enumeration (seed 6).
_TRIPLET_CELL = {
    "styleFamily": "blues",
    "mood": "melancholic",
    "seed": "6",
    "maxLengthSec": 180,
}
_TRIPLET_GRID = {0, 160, 320}


def test_triplet_grid_survives_swing8_untouched() -> None:
    """A melancholic render selecting the slow-blues 12/8 drum pattern keeps its
    triplet onsets on `{0, 160, 320}` pos_in_beat: swing8 only repositions
    `pos % 480 == 240`, so the triplet grid is untouched. Proven by isolating the
    deterministic humanize transform (`_run` with `_ZeroJitter`, the §11.5 seam) on
    the render's triplet drum phrases — a swung straight-8th would have moved to
    ~347. `validate_pipeline` (incl. W7) is clean on the whole render."""
    trace = generate_trace(_TRIPLET_CELL)
    col = ExplainCollector()
    generate_trace(_TRIPLET_CELL, explain=col)
    assert any(
        isinstance(r, PatternRecord) and r.chosen in ("bl_dr_3s", "bl_dr_3sb")
        for r in col.records
    ), "cell did not select a gated slow-blues drum pattern"

    triplet_phrases = [
        p
        for p in trace.phrases_stage6
        if p.role == "drums" and any((n.ticks % 480) in (160, 320) for n in p.notes)
    ]
    assert triplet_phrases, "no triplet drum phrases at stage 6"
    # pre-humanize: purely triplet-grid (the authored content survived tiling).
    for p in triplet_phrases:
        for n in p.notes:
            assert n.ticks % 480 in _TRIPLET_GRID

    out, _ = _run(triplet_phrases, trace.song_form, trace.plan, _ZeroJitter())
    for p in out:
        for n in p.notes:
            assert n.ticks % 480 in _TRIPLET_GRID, (
                f"swing8/offset moved a triplet onset to pos {n.ticks % 480}"
            )

    assert validate_pipeline(trace.document, trace) == []


def test_tempo_gated_eligibility_slow_tier_only() -> None:
    """The [50, 75] slow-blues band renders only at the slow tier: melancholic
    (auto range [61, 75]) selects a gated pattern on a locked seed, while an
    energetic render (range [126, 150]) never selects one, across many seeds —
    asserted via the selection IR, not luck."""
    gated_ids = {"bl_dr_3s", "bl_dr_3sb", "bl_bs_3s", "bl_bs_3sb", "bl_cp_3s"}

    col = ExplainCollector()
    generate_trace(_TRIPLET_CELL, explain=col)
    mel_selected = {
        r.chosen for r in col.records if isinstance(r, PatternRecord)
    } & gated_ids
    tempos = [r.bpm for r in col.records if isinstance(r, TempoRecord)]
    assert mel_selected, "melancholic render selected no gated pattern"
    assert all(50 <= t <= 75 for t in tempos)

    for seed in range(24):
        ecol = ExplainCollector()
        generate_trace(
            {
                "styleFamily": "blues",
                "mood": "energetic",
                "seed": str(seed),
                "maxLengthSec": 180,
            },
            explain=ecol,
        )
        selected = {r.chosen for r in ecol.records if isinstance(r, PatternRecord)}
        assert not (selected & gated_ids), (
            f"energetic seed {seed} selected a gated slow-blues pattern"
        )


# The locked seed where a blues render fires the `stop` device (aggressive / seed 0
# / 240 s; stop lands into solo-6 and solo-7). Found by fixed enumeration.
_STOP_PARAMS = {
    "styleFamily": "blues",
    "mood": "aggressive",
    "seed": "0",
    "maxLengthSec": 240,
}


def test_stop_device_fires_and_carries_a_one_beat_silence() -> None:
    """§5.5 / §3.4: on a locked seed the blues stop device fires (`stop_vs_fill`
    -> `stop` in the device IR), and the entered section's `[enteredTick-480,
    enteredTick)` one-beat window is silent across ALL roles in the post-transitions
    IR (stage 6)."""
    col = ExplainCollector()
    trace = generate_trace(_STOP_PARAMS, explain=col)
    stops = [
        r
        for r in col.records
        if isinstance(r, DeviceRecord)
        and r.kind == "stop_vs_fill"
        and r.outcome == "stop"
    ]
    assert stops, "no stop device fired on the locked seed"

    sections = {s.id: s for s in trace.song_form.sections}
    for rec in stops:
        entered_id = rec.boundary.split("->")[1]
        entered_tick = sections[entered_id].start_bar * BAR
        cut = entered_tick - 480
        attacks = [
            (p.track_id, n.ticks)
            for p in trace.phrases_stage6
            for n in p.notes
            if cut <= n.ticks < entered_tick
        ]
        assert attacks == [], f"stop window not silent at {entered_id}: {attacks}"


def test_plan_shape_fully_populated() -> None:
    """§14.10 plan shape: blues' `GenerationPlan` is fully resolved — swing drawn
    to a concrete `{ratio, subdivision: '8'}` (0.722 flat at <= 90 BPM per the
    §6.4 table, S21-4), feelTable `straight`, and zero null top-level fields."""
    plan = generate_plan({"styleFamily": "blues", "mood": "melancholic", "seed": "6"})
    assert plan.tempo_bpm <= 90
    assert plan.swing is not None
    assert (plan.swing.ratio, plan.swing.subdivision) == (0.722, "8")
    assert plan.feel_table == "straight"
    # zero-null: every top-level plan field is populated (mirrors chill_lofi).
    dumped = plan.model_dump()
    nulls = [k for k, v in dumped.items() if v is None]
    assert nulls == [], f"unexpected null plan fields: {nulls}"
    assert plan.role_flavors  # non-empty flavor map


# --- (e) end-to-end validation slice (Layer 1 + L2 at engine defaults) --------


@pytest.mark.parametrize("mood", ["energetic", "aggressive", "romantic"])
@pytest.mark.parametrize("length", [120, 240])
@pytest.mark.parametrize("seed", ["0", "1", "2", "3", "4"])
def test_end_to_end_validates(mood: str, length: int, seed: str) -> None:
    """Default (energetic) + the two corpus (V, A) extremes (aggressive, romantic)
    x 2 lengths x 5 seeds serialize to a document passing schema validation
    (Layer 1) and the pipeline suite (L2 at engine defaults, no calibration)."""
    trace = generate_trace(
        {
            "styleFamily": "blues",
            "mood": mood,
            "seed": seed,
            "maxLengthSec": length,
        }
    )
    assert validate_document(trace.document) == []
    assert validate_pipeline(trace.document, trace) == []
