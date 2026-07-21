"""fusion_jazz pack — config + bank-inventory pins, the `fu_dr_2` golden anchor,
the fusion first-use machinery pins, and the end-to-end validation slice
(SESSION_22 T5, PHASE_8 §6 under the S22-1…S22-15 rulings).

The fusion first-uses (SESSION_22 scope / DoD §14.3/§14.10):

- **quartal voicings go live** — the first pack to route `quartal` in production.
  Comping rungs 1-2 and pads rungs 1-4 declare it; comping rung 2 renders at
  calm/dreamy/nostalgic and pads rungs 3-4 at the 4-layer moods, and every
  resulting pitch must sit under C5 (MIDI 71, `arrange.py`'s hard lane ceiling).
- **the S22-4 rescue** — quartal's `[0, 5, 10, 15]` needs a 15-semitone span and
  the comping lane leaves only 7-9, so at lane low 50 both §6.4-as-printed
  classes come back EMPTY for `Bbm9` and `A7#9` and `parts/voicing.py` raises an
  uncaught `ValueError`. The authored map adds `rootless_b`, whose sole candidate
  at those lanes is the rescuing voicing pinned below.
- **authored paren extensions** `bVI7(#11)` / `V7(#9)` — the pinned slot consumes
  ZERO dressing draws and the emitted `ChordSpec` carries the group verbatim.
- **`feelTable: tight`** — the first outing of the tight offset profile.
- **swing16 resolved from the §6.4 tempo table** with NO pack `swingRatio`
  override (chill_lofi, the only prior swing16 pack, pins 0.57 directly).
- **`AutoFilter`** — the clav wah, reachable only through the `headhunters`
  ensemble preset (`default` comps on `rhodes`).
- **S22-3** — `vamp` serves main/breakdown/outro, so same-tag adjacency wakes
  PHASE_4 §5.1's draw-free deceptive fallback; the pool was re-rotated to end
  open so no vamp section can ever end on a substituted chord.

Companion module `test_fusion_jazz_variety.py` owns the per-candidate selection
locks (M1 convention) — load-bearing here, because S22-5 leaves rung 1 dead
grid-wide and rung 4 `tune`-only. Determinism (ROADMAP invariant 5): every seed
is a pinned literal; no `random`-for-entropy / `time` / `datetime` import
(TID251). The one `random` import is a *counting* RNG shim (the harmony-stage
draw-accounting seam), never an entropy source.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
import yaml

from trackgen.harmony.stage import _dress_slot
from trackgen.humanize.stage import _run, _ZeroJitter
from trackgen.humanize.swing import swing_phrase
from trackgen.interpreter.stage import generate_plan
from trackgen.packs.loader import resolve_pack
from trackgen.packs.models import DrumEvent, PatternEnvelope, PitchedEvent, StylePack
from trackgen.pipeline.explain import ExplainCollector, PatternRecord
from trackgen.pipeline.trace import generate_trace
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.ir import Key, Phrase, PhraseNote, SongForm
from trackgen.schema.validate import validate_document
from trackgen.theory.voicing import Lane, voicing_candidates

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "fusion_jazz"
BAR = 1920
C5_CEILING = 71  # ROADMAP invariant 4 / arrange.py: no non-drum pitch above this


def _pack() -> StylePack:
    pack = resolve_pack("fusion_jazz")
    assert pack is not None, "fusion_jazz did not resolve"
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


def _counts_by_rung(
    entries: list[PatternEnvelope], kind: str
) -> dict[int, list[tuple[str, int]]]:
    out: dict[int, list[tuple[str, int]]] = {}
    for e in entries:
        if e.kind == kind:
            out.setdefault(e.energy_level, []).append((e.id, e.weight))
    return {k: sorted(v) for k, v in out.items()}


def _params(mood: str, seed: str, length: int, **extra: Any) -> dict[str, Any]:
    return {
        "styleFamily": "fusion_jazz",
        "mood": mood,
        "seed": seed,
        "maxLengthSec": length,
        **extra,
    }


def _simultaneities(trace: Any, role: str) -> set[tuple[int, ...]]:
    """The distinct sets of pitches struck together by `role`, pre-humanizer."""
    by_tick: dict[int, set[int]] = defaultdict(set)
    for phrase in trace.phrases_stage6:
        if phrase.role != role:
            continue
        for note in phrase.notes:
            if note.midi is not None:
                by_tick[note.ticks].add(note.midi)
    return {tuple(sorted(v)) for v in by_tick.values() if len(v) >= 2}


def _is_quartal(voicing: tuple[int, ...]) -> bool:
    """Quartal is `[0, 5, 10, 15]` — four voices stacked in perfect fourths."""
    return len(voicing) == 4 and [voicing[i + 1] - voicing[i] for i in range(3)] == [
        5,
        5,
        5,
    ]


# --- (a1) manifest + interpreter config pins ---------------------------------


def test_manifest_fields() -> None:
    """S22-1: the manifest carries the two required fields §6.1's snippet omitted
    (`formatVersion: 1`, `engine: >=0.1`), version 0.1.0 (S22-9), and §6.1's
    tempo range / time signature."""
    m = _pack().manifest
    assert m.format_version == 1
    assert m.engine == ">=0.1"
    assert m.version == "0.1.0"
    assert m.tempo_range == (75, 145)
    assert m.time_signatures == [(4, 4)]


def test_interpreter_config() -> None:
    """§6.1, with the S22-2 modes re-ordering. `modes` MUST be a MODE_LADDER-
    ordered subsequence — §6.1's printed `[dorian, mixolydian, minor, major]` is
    a hard `PackLoadError`, so the authored order is the ladder order and the
    `tonics` map is reordered to match. Set and semantics unchanged."""
    i = _pack().interpreter
    assert i is not None
    assert i.supported_moods == [
        "energetic",
        "calm",
        "mysterious",
        "dreamy",
        "nostalgic",
        "triumphant",
        "happy",
        "tense",
    ]
    assert i.default_mood == "energetic"
    assert i.modes == ["major", "mixolydian", "dorian", "minor"]
    assert i.tonics == {
        "major": ["F", "C"],
        "mixolydian": ["F", "Bb"],
        "dorian": ["D", "G", "Bb"],
        "minor": ["C", "A"],
    }
    # swing16 with NO swingRatio override (the §6.4 table is the authority) —
    # the discriminator against chill_lofi, which pins 0.57 directly.
    assert i.feel == "swing16"
    assert i.swing_ratio is None
    assert i.feel_table == "tight"
    assert i.expression_ranges.density == (0.30, 0.90)
    assert i.expression_ranges.dissonance == (0.55, 0.90)
    assert i.flavors == {
        "drums": ["funk_kit", "fusion_ride_kit"],
        "bass": ["synth_moog", "electric_finger"],
        "comping": ["rhodes", "clav"],
        "pads": ["analog_poly", "glass_pad"],
    }
    # `clav` (and therefore AutoFilter) lives only on the headhunters preset.
    assert i.ensembles["default"]["comping"] == "rhodes"
    assert i.ensembles["headhunters"]["comping"] == "clav"
    assert set(i.ensembles) == {"default", "headhunters"}


def test_forms_two_template_shapes() -> None:
    """§6.2: the `tune` (head/solo/head, cold close, weight 60) and the `vamp`
    (groove vehicle with strip-down/rebuild, fade close, weight 40). The vamp's
    `breakdown -> main` tail is what DoD §14.10's strip-and-rebuild clause
    renders from, so its spine order is pinned."""
    f = _pack().forms
    assert f is not None
    assert f.energy_range == (0.20, 0.95)
    assert [(t.id, t.weight) for t in f.templates] == [("tune", 60), ("vamp", 40)]

    tune, vamp = (t.model_dump() for t in f.templates)
    assert tune["ending"] == {"tag_bars": 0, "close": "cold"}
    assert tune["fallback"] == {"section": "solo", "bars": 16}
    assert [s.get("section") for s in tune["spine"]] == [
        "intro",
        "head",
        None,  # the repeat block
        "head",
        "outro",
    ]
    assert tune["spine"][2]["repeat"]["count"] == (1, None)

    assert vamp["ending"] == {"tag_bars": 0, "close": "fade"}
    assert vamp["fallback"] == {"section": "main", "bars": 8}
    assert [s.get("section") for s in vamp["spine"]] == [
        "intro",
        None,  # repeat(count [2, null], main)
        "breakdown",
        "main",
        "outro",
    ]
    assert vamp["spine"][1]["repeat"]["count"] == (2, None)


def test_progressions_inventory() -> None:
    """The §6.3 pool/turnaround/final inventory. `turnarounds` is empty, which is
    exactly what wakes the deceptive fallback on same-tag adjacency (S22-3)."""
    pr = _pack().progressions
    assert pr is not None
    assert set(pr.pools) == {"tune_16", "modal_32", "vamp", "intro"}
    inventory = {
        tag: {(e.id, e.weight, tuple(e.modes)) for e in entries}
        for tag, entries in pr.pools.items()
    }
    assert inventory["tune_16"] == {
        ("cantaloupe_class", 60, ("minor", "dorian")),
        ("dominant_16", 40, ("mixolydian", "major")),
    }
    assert inventory["modal_32"] == {
        ("sus_chain", 100, ("dorian", "minor")),
        ("sus_chain_mixo", 100, ("mixolydian", "major")),
    }
    assert inventory["vamp"] == {
        ("dorian_funk", 40, ("dorian", "minor")),
        ("sus_pedal", 20, ("mixolydian", "major")),
        ("minor_launch", 20, ("minor", "dorian")),
        ("mixo_vamp", 20, ("mixolydian", "major")),
    }
    assert inventory["intro"] == {
        ("groove_in", 100, ("dorian", "minor")),
        ("mixo_groove_in", 100, ("mixolydian", "major")),
    }
    assert pr.turnarounds == ()
    assert {(e.id, e.weight) for e in pr.finals} == {
        ("dorian_plagal", 60),
        ("sharp_nine", 40),
        ("backdoor", 100),
    }


def test_vamp_pool_entries_all_end_open() -> None:
    """S22-3 authoring pin: every `vamp` entry's phrase ends on a NON-tonic chord.
    `dorian_funk`/`mixo_vamp` were already safe; `minor_launch` is a pure rotation
    of §6.3's printed `iiø7 | V7(#9) | i7 | ~` (all content preserved) and
    `sus_pedal` swaps its final tonic-pedal bar for the mixolydian bVII, because a
    one-chord pedal cannot be rotated open. Ending open is what keeps the
    deceptive fallback from firing at all (the render-level pin is below)."""
    pr = _pack().progressions
    assert pr is not None
    tonic_heads = ("i7", "I7", "i", "I")
    finals = {}
    for entry in pr.pools["vamp"]:
        (phrase,) = entry.phrases.values()
        last_bar = next(bar for bar in reversed(phrase) if bar != ("~",))
        finals[entry.id] = last_bar
    assert finals == {
        "dorian_funk": ("IV7",),
        "sus_pedal": ("bVII7",),
        "minor_launch": ("V7(#9)",),
        "mixo_vamp": ("bVII7",),
    }
    for entry_id, bar in finals.items():
        assert bar[0] not in tonic_heads, f"{entry_id} ends on a tonic"


def test_transitions_config() -> None:
    """§6.5: frequent fills ([1, 2]), the funk break `stop` at [1, 4], the §6.5
    crash band, and the drum mutation table carrying `hat_lift` — fusion is the
    first pack to combine `hat_lift` with a `breakdown` (S22-10)."""
    tr = _pack().transitions
    assert tr is not None
    assert tr.phrase_fill.odds == (1, 2)
    assert tr.stop.enabled is True
    assert tr.stop.odds == (1, 4)
    assert tr.crash.velocity == (0.45, 0.85)
    assert tr.mutation.drums == {
        "none": 6,
        "kick_pickup": 2,
        "drop_ornament": 2,
        "hat_lift": 1,
    }
    assert tr.mutation.comping == {"none": 3, "anticipate": 2, "drop_hit": 1}


# --- (a2) bank inventory pins (M1 convention: trips on any bank edit) ---------


def test_pack_loads_and_is_patterns_mode() -> None:
    pack = _pack()
    assert pack.bass_mode == "patterns"
    assert pack.layering_order == ("drums", "bass", "comping", "pads")


def test_candidate_counts_drums() -> None:
    """The §6.4 ladder as printed — NO re-map (S22-5): rung 1 sparse funk (dormant
    grid-wide), rung 2 the light-16th-funk workhorse carrying `fu_dr_2`, rung 3
    full funk + the displaced backbeat, rung 4 the `tune`-only ride drive. Three
    fills, one per rung 2/3/4."""
    drums = _pack().patterns["drums"]
    assert _counts_by_rung(drums, "main") == {
        1: [("fu_dr_1", 3), ("fu_dr_1b", 2)],
        2: [("fu_dr_2", 3), ("fu_dr_2b", 2)],
        3: [("fu_dr_3", 3), ("fu_dr_3b", 2)],
        4: [("fu_dr_4", 3), ("fu_dr_4b", 2)],
    }
    assert _counts_by_rung(drums, "intro") == {1: [("fu_dr_i", 3), ("fu_dr_ib", 2)]}
    assert _counts_by_rung(drums, "ending") == {1: [("fu_dr_e", 3), ("fu_dr_eb", 2)]}
    assert _counts_by_rung(drums, "fill") == {
        2: [("fu_dr_f1", 1)],
        3: [("fu_dr_f2", 1)],
        4: [("fu_dr_f3", 1)],
    }


@pytest.mark.parametrize(
    ("role", "prefix"),
    [("bass", "fu_bs"), ("comping", "fu_cp"), ("pads", "fu_pd")],
)
def test_candidate_counts_pitched_roles(role: str, prefix: str) -> None:
    pack = _pack()
    assert _counts_by_rung(pack.patterns[role], "main") == {
        1: [(f"{prefix}_1", 3), (f"{prefix}_1b", 2)],
        2: [(f"{prefix}_2", 3), (f"{prefix}_2b", 2)],
        3: [(f"{prefix}_3", 3), (f"{prefix}_3b", 2)],
        4: [(f"{prefix}_4", 3), (f"{prefix}_4b", 2)],
    }
    assert _counts_by_rung(pack.patterns[role], "intro") == {
        1: [(f"{prefix}_i", 3), (f"{prefix}_ib", 2)]
    }
    assert _counts_by_rung(pack.patterns[role], "ending") == {
        1: [(f"{prefix}_e", 3), (f"{prefix}_eb", 2)]
    }


def test_sibling_weights_are_3_2_every_slot() -> None:
    """Every variety-linted slot is a 3/2 weighted pair: primary 3, sibling 2."""
    pack = _pack()
    for role in ("drums", "bass", "comping", "pads"):
        for kind in ("main", "intro", "ending"):
            for _rung, pairs in _counts_by_rung(pack.patterns[role], kind).items():
                assert sorted(w for _, w in pairs) == [2, 3], f"{role}/{kind}: {pairs}"


def test_every_pattern_is_ungated() -> None:
    """fusion authors NO eligibility gate anywhere (unlike blues' [50, 75] slow
    band) — the variety floor is carried entirely by the 3/2 pairs, which is what
    lets `test_fusion_jazz_variety` lock every draw at a single tempo."""
    pack = _pack()
    gated = [
        e.id
        for role in ("drums", "bass", "comping", "pads")
        for e in pack.patterns[role]
        if e.eligibility.tempo_bpm is not None
    ]
    assert gated == []


def test_every_authored_position_is_on_the_straight_grid() -> None:
    """SESSION_22 constraint 11: fusion declares no triplet content anywhere, so
    every authored `pos` is a multiple of 120 (a 16th). W7 (§3.1 one-grid-per-
    Phrase) reads the PRE-humanizer IR, so this authoring property alone makes a
    grid violation unreachable from these banks — swing16 can neither create nor
    cure one. §6.1's "Purdie-shuffle territory" is a feel observation about the
    swing ratio, not an instruction to author 160/320 offsets (the C-24 lesson)."""
    pack = _pack()
    offenders = [
        (role, env.id, e.pos)
        for role in ("drums", "bass", "comping", "pads")
        for env in pack.patterns[role]
        for e in env.events
        if e.pos % 120 != 0
    ]
    assert offenders == []


def test_voicing_class_maps() -> None:
    """§6.4's classes under the S22-4 ruling: `rootless_b` is appended at comping
    rungs 1-2 (the crash rescue — see the dedicated pins below), quartal stays
    FIRST so it remains the pinned low-rung signature, and pads are quartal-only
    at every rung."""
    pack = _pack()
    assert pack.voicing["comping"].classes == {
        1: ("quartal", "rootless_a", "rootless_b"),
        2: ("quartal", "rootless_a", "rootless_b"),
        3: ("rootless_a", "rootless_b"),
        4: ("rootless_a", "rootless_b"),
    }
    assert pack.voicing["pads"].classes == {i: ("quartal",) for i in range(1, 5)}


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


# --- (b) verbatim golden anchor (§6.4:709-717) --------------------------------


def test_golden_fu_dr_2_verbatim() -> None:
    """§6.4's defining light-16th-funk entry, id + energyLevel + lengthTicks +
    weight + event list byte-verbatim (the only addition to the printed snippet
    is the required `role: drums`, the `bl_dr_2` precedent). The hard quarter
    accents §6.4 insists on are part of the pin: 0.58-0.62 on 0/480/960/1440 vs
    0.40-0.42 on the offbeats — the groove fails without them."""
    env = _entry(_pack(), "drums", "fu_dr_2")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        3,
        1920,
    )
    assert _drum_tuples(env) == [
        (0, "kick", 0.92, None, None),
        (720, "kick", 0.78, None, None),
        (1200, "kick", 0.72, None, 0.50),
        (480, "snare", 0.90, None, None),
        (1440, "snare", 0.88, None, None),
        (1080, "snare", 0.25, None, 0.60),
        (0, "hat_closed", 0.62, None, None),
        (240, "hat_closed", 0.40, None, None),
        (480, "hat_closed", 0.58, None, None),
        (720, "hat_closed", 0.40, None, None),
        (960, "hat_closed", 0.60, None, None),
        (1200, "hat_closed", 0.40, None, None),
        (1440, "hat_closed", 0.58, None, None),
        (1680, "hat_closed", 0.42, None, None),
    ]


def test_golden_fu_bs_2_is_the_literal_tresillo_cell() -> None:
    """S22-11: §6.4's rung-2 parenthetical is self-inconsistent — its prose pins a
    "tresillo skeleton (3+3+2 in 16ths)" (= 960 ticks) while its printed third
    duration 480 overruns the next cell onset by 240. Per ROADMAP §3 rule 1 the
    prose is the pinned data text, so the literal doubled 3+3+2 cell is the
    weight-3 anchor and the printed continuation survives as the weight-2 sibling.
    Both onset spacings are pinned: no note overruns its successor in EITHER."""
    pack = _pack()
    for entry_id, expected in (
        (
            "fu_bs_2",
            [(0, 360), (360, 360), (720, 240), (960, 360), (1320, 360), (1680, 240)],
        ),
        ("fu_bs_2b", [(0, 360), (360, 360), (720, 480), (1200, 360), (1560, 360)]),
    ):
        env = _entry(pack, "bass", entry_id)
        events = []
        for e in env.events:
            assert isinstance(e, PitchedEvent)
            events.append((e.pos, e.dur))
        assert events == expected, entry_id
        for (pos, dur), (next_pos, _) in zip(events, events[1:], strict=False):
            assert pos + dur <= next_pos, (
                f"{entry_id}: note at {pos} overruns {next_pos}"
            )
        last_pos, last_dur = events[-1]
        assert last_pos + last_dur <= env.length_ticks


# --- (c) timbre pins (§6.6 / TB1 / TB7 under the S22-7 rulings) ---------------


def _timbres_raw() -> dict[str, Any]:
    data = yaml.safe_load((_PACK_DIR / "timbres.yaml").read_text())
    assert isinstance(data, dict)
    return data


def test_all_eight_flavors_authored() -> None:
    """TB1: §6.1 declares 8 flavors while §6.6 prints only 7 recipes —
    `fusion_ride_kit` has none and is authored in-idiom (S22-7 fix 1)."""
    raw = _timbres_raw()
    got = {f for role in raw["flavors"].values() for f in role}
    assert got == {
        "funk_kit",
        "fusion_ride_kit",
        "synth_moog",
        "electric_finger",
        "rhodes",
        "clav",
        "analog_poly",
        "glass_pad",
    }


def test_synth_moog_keeps_base_q_and_overrides_brightness() -> None:
    """S22-7 fix 2 (base-XOR-mod): §6.6 pins the Moog's `filter.Q: 4` in base, but
    the bass role default maps brightness -> filter.Q as well. Q stays in base and
    brightness is overridden to emit ONLY filterEnvelope.baseFrequency."""
    moog = _timbres_raw()["flavors"]["bass"]["synth_moog"]
    assert moog["base"]["filter"]["Q"] == 4
    assert [m["param"] for m in moog["mod"]["brightness"]] == [
        "filterEnvelope.baseFrequency"
    ]


def test_clav_attack_is_a_mod_band_and_carries_the_autofilter() -> None:
    """S22-7 fix 3: §6.6's printed base `attack: 0.003` collides with the comping
    default attackHardness -> envelope.attack, so the attack moves to a narrow mod
    band (geometric centre 0.003). The AutoFilter wah (§3.7) is the insert whose
    reachability is pinned end-to-end below."""
    clav = _timbres_raw()["flavors"]["comping"]["clav"]
    assert "attack" not in clav["base"]["envelope"]
    band = clav["mod"]["attackHardness"]
    assert [m["param"] for m in band] == ["envelope.attack"]
    assert (band[0]["min"] * band[0]["max"]) ** 0.5 == pytest.approx(0.003)
    (effect,) = clav["effects"]
    assert effect["type"] == "AutoFilter"
    assert effect["options"] == {
        "frequency": 2.5,
        "baseFrequency": 350,
        "octaves": 2.5,
        "depth": 0.5,
        "wet": 0.4,
    }


def test_fm_flavors_override_brightness_to_modulation_index() -> None:
    """TB7 — the silent trap: BOTH FM flavors must fully override the role-default
    brightness path (`filterEnvelope.baseFrequency`, which FMSynth does not have).
    `rhodes` states its override in §6.6; `glass_pad` does NOT — §6.6 only calls
    it "a brighter FM alternative", the exact `organ_swell` trap from S21 (S22-7
    fix 4)."""
    raw = _timbres_raw()
    rhodes = raw["flavors"]["comping"]["rhodes"]
    glass = raw["flavors"]["pads"]["glass_pad"]
    for flavor in (rhodes, glass):
        assert flavor["engine"]["voice"] == "FMSynth"
        assert [m["param"] for m in flavor["mod"]["brightness"]] == ["modulationIndex"]
    # glass_pad is the "brighter" one — its band sits above rhodes'.
    assert glass["mod"]["brightness"][0]["max"] > rhodes["mod"]["brightness"][0]["max"]


def test_bus_is_the_driest_and_master_is_compressor_then_limiter() -> None:
    """§6.6's 70s damped-head room as data, and TB4 (Limiter last)."""
    raw = _timbres_raw()
    assert raw["bus"]["reverb"] == {
        "decay": [0.6, 1.8],
        "preDelay": [0.008, 0.02],
        "returnFilterHz": 400,
    }
    assert [d["type"] for d in raw["master"]] == ["Compressor", "Limiter"]


# --- (d) first-use machinery pins ---------------------------------------------

# The calm cell whose arrangement routes comping at `main` rung 2 — the ONLY
# rung where §6.4 declares quartal for comping and the arrangement actually
# renders it (S22-5: comping rung-2 content reaches `tune/head` + `vamp/main` at
# calm/dreamy/nostalgic only). Found by fixed enumeration.
_QUARTAL_COMPING_CELL = _params("calm", "0", 120)

# The energetic cell whose 4-layer arrangement routes pads at `main` rungs 3-4,
# where pads actually sound (pads are quartal at every rung). Found by fixed
# enumeration.
_QUARTAL_PADS_CELL = _params("energetic", "0", 120)


def test_quartal_comping_renders_and_sits_under_c5() -> None:
    """DoD §14.10 (first half): the quartal Rhodes actually renders and sits under
    C5. The cell selects comping `main` rung 2 (quartal's live comping rung), at
    least one struck comping simultaneity is literally `[0, 5, 10, 15]`-shaped,
    and no comping pitch exceeds MIDI 71."""
    col = ExplainCollector()
    trace = generate_trace(_QUARTAL_COMPING_CELL, explain=col)
    rungs = {
        r.rung
        for r in col.records
        if isinstance(r, PatternRecord) and r.role == "comping" and r.kind == "main"
    }
    assert 2 in rungs, f"cell did not route comping main rung 2 (got {sorted(rungs)})"

    voicings = _simultaneities(trace, "comping")
    quartal = [v for v in voicings if _is_quartal(v)]
    assert quartal, f"no quartal comping voicing rendered (got {sorted(voicings)})"
    top = max(v[-1] for v in voicings)
    assert top <= C5_CEILING, f"comping reached MIDI {top}, above C5"


def test_quartal_pads_render_and_sit_under_c5() -> None:
    """DoD §14.10 (second half): pads DO sound in fusion (unlike chill_lofi's
    dormant pads, C-22) — the 4-layer moods route pads at `main` rungs 3-4, where
    §6.4 declares quartal at every rung. EVERY struck pads simultaneity is
    quartal-shaped, and none exceeds MIDI 71."""
    col = ExplainCollector()
    trace = generate_trace(_QUARTAL_PADS_CELL, explain=col)
    rungs = {
        r.rung
        for r in col.records
        if isinstance(r, PatternRecord) and r.role == "pads" and r.kind == "main"
    }
    assert rungs and rungs <= {3, 4}, f"pads routed at unexpected rungs {sorted(rungs)}"

    voicings = _simultaneities(trace, "pads")
    assert voicings, "no pads chord rendered"
    non_quartal = [v for v in voicings if not _is_quartal(v)]
    assert non_quartal == [], f"non-quartal pads voicings: {non_quartal}"
    top = max(v[-1] for v in voicings)
    assert top <= C5_CEILING, f"pads reached MIDI {top}, above C5"


@pytest.mark.parametrize(
    "mood",
    [
        "energetic",
        "calm",
        "mysterious",
        "dreamy",
        "nostalgic",
        "triumphant",
        "happy",
        "tense",
    ],
)
def test_no_comping_or_pads_pitch_breaches_c5(mood: str) -> None:
    """The §14.10 ceiling clause across the whole supported mood grid, not just
    the two quartal cells — the lane ceiling holds for every voicing class the
    pack can route."""
    for seed in ("1ps9wxb", "2kq7f3z"):
        trace = generate_trace(_params(mood, seed, 180))
        pitches = [
            n.midi
            for ph in trace.phrases_stage7
            if ph.role in ("comping", "pads")
            for n in ph.notes
            if n.midi is not None
        ]
        assert pitches, f"{mood}/{seed} rendered no chordal pitches"
        assert max(pitches) <= C5_CEILING, f"{mood}/{seed} reached {max(pitches)}"


# The two (chord, lane) coordinates that crash under §6.4's PRINTED voicing map.
# `Bbm9` is i7+9 in Bb dorian — §6.1's pinned Chameleon key; `A7#9` is V7(#9) in
# D dorian (the `minor_launch` vamp's final chord). Comping lane low is 50 at
# registerBias >= +0.15, i.e. calm / triumphant / happy.
_CRASH_LANE = Lane(50, 71)
# Each case carries a locked (tonic, mood, seed) render that actually emits the
# chord, so the ChordSpec under test is the production one, not a hand-built
# stand-in. Found by fixed enumeration.
_S22_4_CASES: tuple[tuple[str, str, str, int, str, list[str], list[int]], ...] = (
    ("Bbm9", "Bb", "0", 10, "min7", ["9"], [56, 60, 61, 65]),
    ("A7#9", "D", "5", 9, "dom7", ["#9"], [55, 60, 61, 64]),
)


@pytest.mark.parametrize(
    ("symbol", "tonic", "seed", "root_pc", "quality", "extensions", "rescue"),
    _S22_4_CASES,
    ids=[c[0] for c in _S22_4_CASES],
)
def test_s22_4_rootless_b_is_the_sole_rescue_at_the_crash_lane(
    symbol: str,
    tonic: str,
    seed: str,
    root_pc: int,
    quality: str,
    extensions: list[str],
    rescue: list[int],
) -> None:
    """S22-4, at the exact seam: with §6.4's PRINTED comping classes
    `[quartal, rootless_a]`, both come back EMPTY for these two chords at lane low
    50 — quartal's `[0, 5, 10, 15]` needs a 15-semitone span and the lane leaves
    only 7-9 — and `parts/voicing.py` then raises an uncaught `ValueError`.

    `rootless_b` has EXACTLY ONE candidate at each coordinate, so pinning the
    literal voicing makes this test fail loudly if `rootless_b` is ever dropped
    from the authored map, and equally if the class formula moves."""
    pack = _pack()
    classes = pack.voicing["comping"].classes
    trace = generate_trace(
        _params("calm", seed, 180, key={"tonic": tonic, "mode": "dorian"})
    )
    spec = next(c.chord for c in trace.harmony.chords if c.chord.symbol == symbol)
    assert (spec.root_pc, spec.quality, spec.extensions) == (
        root_pc,
        quality,
        extensions,
    )

    # the printed map's two classes: both empty => the ValueError path
    assert voicing_candidates(spec, "quartal", _CRASH_LANE) == []
    assert voicing_candidates(spec, "rootless_a", _CRASH_LANE) == []
    # the authored map's third class: exactly one placement, the rescuing voicing
    assert voicing_candidates(spec, "rootless_b", _CRASH_LANE) == [rescue]
    for rung in (1, 2):
        assert "rootless_b" in classes[rung], (
            f"rung {rung} dropped rootless_b — {symbol} would crash again"
        )


@pytest.mark.parametrize("mood", ["calm", "triumphant", "happy"])
@pytest.mark.parametrize("tonic", ["Bb", "D"])
@pytest.mark.parametrize("seed", ["0", "1"])
def test_s22_4_override_matrix_raises_nothing(mood: str, tonic: str, seed: str) -> None:
    """The render-level form of the pin above: the full (lane-low-50 mood x
    dorian-key) override matrix — the 54-of-1152 crashing region scoping measured
    under the printed map — completes and validates under the authored one."""
    trace = generate_trace(
        _params(mood, seed, 180, key={"tonic": tonic, "mode": "dorian"})
    )
    assert validate_document(trace.document) == []


def test_authored_extension_emitted_verbatim_through_the_pipeline() -> None:
    """§3.5 / DoD §14.1: a full render emits `ChordSpec.extensions` carrying the
    authored group verbatim on every `bVI7(#11)` / `V7(#9)` slot, quality dom7
    (P11-legal). Both tokens live in dorian/minor-class pools, so the render
    forces `key.mode: dorian` to reach `cantaloupe_class` (bVI7(#11)) and
    `sharp_nine` / `minor_launch` (V7(#9)) — on locked seeds, since neither pool
    is drawn on every render."""
    seen: dict[str, list[str]] = {}
    for seed in ("0", "5"):
        trace = generate_trace(
            _params("calm", seed, 180, key={"tonic": "D", "mode": "dorian"})
        )
        for event in trace.harmony.chords:
            if "#11" in event.chord.extensions or "#9" in event.chord.extensions:
                seen[event.chord.symbol] = list(event.chord.extensions)
                assert event.chord.quality == "dom7"
    assert seen.get("Bb7#11") == ["#11"], seen  # bVI7(#11) in D dorian
    assert seen.get("A7#9") == ["#9"], seen  # V7(#9) in D dorian


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


@pytest.mark.parametrize("base_tier", [4, 5])
def test_authored_extension_slot_is_draw_free_with_discriminating_contrast(
    base_tier: int,
) -> None:
    """§3.5 draw-free pin: dressing an authored-extension slot makes NO
    `weighted_choice` draw (the pin removes all options), while an un-extensioned
    chord of the SAME quality at the identical tier DOES draw — the discriminator
    that proves the pin, not a vacuous zero.

    Tier 4 is `tier(0.685)` (energetic/calm/mysterious) and tier 5 is
    `tier(0.764)` (tense); D dorian is the pack's default dorian key."""
    key = Key(tonic_pc=2, mode="dorian")
    for pinned, extension in (("bVI7(#11)", "#11"), ("V7(#9)", "#9")):
        rng = _counting_rng()
        spec = _dress_slot(pinned, key, base_tier=base_tier, rng=rng)
        assert spec.extensions == [extension]
        assert spec.quality == "dom7"
        assert rng.draws == 0
    for dressable in ("I7", "IV7", "i7"):
        rng = _counting_rng()
        spec = _dress_slot(dressable, key, base_tier=base_tier, rng=rng)
        assert rng.draws == 1, f"{dressable} did not draw (pin test is vacuous)"
        assert spec.extensions != [], dressable


_S22_3_GRID = [
    (mood, seed, length)
    for mood in (
        "energetic",
        "calm",
        "mysterious",
        "dreamy",
        "nostalgic",
        "triumphant",
        "happy",
        "tense",
    )
    for seed in ("1ps9wxb", "2kq7f3z")
    for length in (120, 240)
]


def test_no_vamp_tagged_section_ever_ends_deceptive() -> None:
    """S22-3, the headline regression. §3.3 and PHASE_4 D6 claimed `turnarounds:
    []` keeps BOTH boundary transforms inert; that is false. PHASE_4 §5.1 step 5's
    normative text — which `harmony/stage.py` implements — fires a fixed,
    draw-free DECEPTIVE substitution on any same-tag boundary whose section ends
    tonic-rooted with `function == 'T'`. fusion's `vamp` tag serves
    main/breakdown/outro repeatedly, so the transform wakes up at nearly every
    boundary; scoping measured 249 vamp substitutions over 336 renders, producing
    `I7sus4 | vi | I7sus4 | vi ...` — a direct violation of DoD §14.10's "vamps
    loop without harmonic drift".

    The §6.3 re-rotations (every vamp entry now ends open) are what close it, and
    this is their executable guarantee across the whole supported grid."""
    offenders: list[str] = []
    for mood, seed, length in _S22_3_GRID:
        trace = generate_trace(_params(mood, seed, length))
        tags = {s.id: s.harmony_tag for s in trace.song_form.sections}
        by_section: dict[str, list[Any]] = defaultdict(list)
        for event in trace.harmony.chords:
            by_section[event.section_id].append(event)
        for section_id, events in by_section.items():
            if tags[section_id] != "vamp":
                continue
            last = max(events, key=lambda e: e.start_tick)
            if "deceptive" in last.tags:
                offenders.append(
                    f"{mood}/{seed}/{length}s {section_id}: {last.chord.symbol}"
                )
    assert offenders == [], (
        "vamp sections ending on a deceptive substitution:\n" + "\n".join(offenders)
    )


def test_tune_16_deceptive_substitutions_are_present_and_accepted() -> None:
    """The other half of S22-3: `tune_16` is left AS PRINTED and its head/solo
    chorus-boundary substitutions are accepted — that is precisely the relaunch
    device PHASE_4 D6 built, and a substituted chord at a chorus turnaround is
    idiomatic jazz. Asserted to EXIST rather than asserted away, so the test above
    cannot pass by the transform having been silently disabled engine-side."""
    total = 0
    for mood, seed, length in _S22_3_GRID:
        trace = generate_trace(_params(mood, seed, length))
        tags = {s.id: s.harmony_tag for s in trace.song_form.sections}
        by_section: dict[str, list[Any]] = defaultdict(list)
        for event in trace.harmony.chords:
            by_section[event.section_id].append(event)
        for section_id, events in by_section.items():
            if tags[section_id] != "tune_16":
                continue
            last = max(events, key=lambda e: e.start_tick)
            total += "deceptive" in last.tags
    assert total > 0, (
        "no tune_16 deceptive substitution fired — the deceptive fallback is dead, "
        "which would make the vamp regression test above vacuous"
    )


@pytest.mark.parametrize("tonic", ["Bb", "D"])
@pytest.mark.parametrize("mood", ["calm", "mysterious", "energetic"])
def test_explicit_dorian_renders_validate_and_exercise_the_core_idiom(
    tonic: str, mood: str
) -> None:
    """S22-6: §6.1 calls fusion "the first dorian-primary pack", but measured auto
    mode-resolution is major 6/8, dorian 1/8 (mysterious), minor 1/8 (tense) —
    and the pinned §8.2 corpus triple (energetic, calm, tense) captures ZERO
    dorian cells. So the pack's stated core idiom gets NO golden coverage and
    these explicit-`key.mode` renders are its only coverage anywhere.

    Bb dorian is §6.1's pinned Chameleon key (auto renders take `tonics[dorian][0]`
    = D, so Bb needs the explicit tonic). Both keys validate clean and draw the
    dorian-class pools — `cantaloupe_class` (the pack's pinned identity) or
    `dorian_funk` (Chameleon) — through the quartal comping/pads path."""
    drawn: set[str] = set()
    for seed in ("0", "1", "2"):
        trace = generate_trace(
            _params(mood, seed, 180, key={"tonic": tonic, "mode": "dorian"})
        )
        assert trace.plan.key.mode == "dorian"
        assert validate_document(trace.document) == []
        assert validate_pipeline(trace.document, trace) == []
        drawn |= set(trace.harmony.pool_selections.values())
    assert drawn & {"cantaloupe_class", "dorian_funk"}, (
        f"{tonic} dorian drew neither core-idiom pool: {sorted(drawn)}"
    )


def test_swing16_resolves_from_the_tempo_table_with_no_pack_override() -> None:
    """§6.1/§6.4: fusion authors `feel: swing16` and NO `swingRatio`, so the ratio
    is read from the §6.4 table at 2x tempo — the discriminator against
    chill_lofi, the only prior swing16 pack, which pins 0.57 flat. §6.1's own
    derived claims are the pins: ~58% at 100 BPM, straight by ~120+, and the slow
    edge reaching the low-to-mid 60s (S22-8 corrected the printed 63-66%)."""
    interp = _pack().interpreter
    assert interp is not None and interp.swing_ratio is None

    calm = generate_plan(
        {"styleFamily": "fusion_jazz", "mood": "calm", "seed": "1ps9wxb"}
    )
    energetic = generate_plan(
        {"styleFamily": "fusion_jazz", "mood": "energetic", "seed": "1ps9wxb"}
    )
    assert calm.swing is not None and energetic.swing is not None
    assert calm.swing.subdivision == energetic.swing.subdivision == "16"
    # slow edge: swung; fast edge: the table has already flattened to straight.
    assert (calm.tempo_bpm, calm.swing.ratio) == (83.0, 0.635)
    assert (energetic.tempo_bpm, energetic.swing.ratio) == (143.0, 0.5)
    assert calm.swing.ratio > energetic.swing.ratio  # tempo-dependent, not flat


def test_swing16_displaces_only_16th_offbeats() -> None:
    """swing16 repositions `pos % 240 == 120` onsets and NOTHING else, so §6.4's
    8th-grid ride line and every quarter/8th hit pass through untouched. Pinned on
    the isolated `swing_phrase` seam at the calm ratio, where the displacement is
    large enough to be unambiguous (120 -> 152)."""
    plan = generate_plan(
        {"styleFamily": "fusion_jazz", "mood": "calm", "seed": "1ps9wxb"}
    )
    grid = [0, 120, 240, 360, 480, 720, 960, 1200, 1440, 1680, 1800]
    notes = [
        PhraseNote(ticks=t, duration_ticks=120, midi=60, velocity=0.5) for t in grid
    ]
    swung = [start for start, _dur in swing_phrase(notes, plan.swing)]
    for original, moved in zip(grid, swung, strict=True):
        if original % 240 == 120:
            assert moved > original, f"16th offbeat {original} was not swung"
        else:
            assert moved == original, f"on-grid onset {original} moved to {moved}"
    assert swung[grid.index(120)] == 152  # the pinned calm-ratio displacement


def test_tight_feel_table_threads_to_the_humanizer() -> None:
    """`feelTable: tight` is fusion's first outing (§3.4). The discriminating
    end-to-end proof is a comping hit landing EARLIER than `straight` would place
    it — tight's comping offset is 3 ms against straight's 5 ms — isolated through
    the deterministic humanize transform (`_run` with `_ZeroJitter`, the §11.5
    seam). Tick 480 is a beat, so swing16 leaves it alone and the offset is the
    only thing moving it."""
    plan = generate_plan(
        {"styleFamily": "fusion_jazz", "mood": "energetic", "seed": "1ps9wxb"}
    )
    assert plan.feel_table == "tight"
    ticks_per_ms = 480 * plan.tempo_bpm / 60000
    form = SongForm(sections=[], total_bars=4, template_id="t")

    def tick(p: object) -> int:
        note = PhraseNote(ticks=480, duration_ticks=240, midi=60, velocity=0.5)
        phrase = Phrase(
            track_id="comping", role="comping", start_tick=0, end_tick=BAR, notes=[note]
        )
        out, _ = _run([phrase], form, p, _ZeroJitter())  # type: ignore[arg-type]
        return out[0].notes[0].ticks

    tight = tick(plan)
    straight = tick(plan.model_copy(update={"feel_table": "straight"}))
    assert tight == round(480 + 3 * ticks_per_ms)
    assert straight == round(480 + 5 * ticks_per_ms)
    assert tight < straight  # tight = closer to the grid


@pytest.mark.parametrize("mood", ["energetic", "calm"])
def test_autofilter_reaches_the_document_only_via_headhunters(mood: str) -> None:
    """§6.6/§3.7: the clav wah is the first `AutoFilter` in any pack. It is
    reachable ONLY through the `headhunters` ensemble preset — `default` comps on
    `rhodes` — so the pin asserts both directions, which is what makes it
    discriminating rather than a substring smoke test."""

    def has_autofilter(preset: str) -> bool:
        trace = generate_trace(_params(mood, "1ps9wxb", 120, ensemblePreset=preset))
        return "AutoFilter" in json.dumps(trace.document.model_dump(by_alias=True))

    assert has_autofilter("headhunters")
    assert not has_autofilter("default")


# The vamp-template cells whose form contains a breakdown followed by a rebuilt
# main (discovered by fixed enumeration).
_BREAKDOWN_CELLS = [_params("energetic", "1", 120), _params("tense", "1", 120)]


@pytest.mark.parametrize(
    "cell", _BREAKDOWN_CELLS, ids=[c["mood"] for c in _BREAKDOWN_CELLS]
)
def test_breakdown_strips_to_drums_bass_and_the_next_main_rebuilds(
    cell: dict[str, Any],
) -> None:
    """DoD §14.10's strip-and-rebuild clause. The §6.2 `vamp` template's
    `breakdown -> main` tail hits the §4.1 arrangement cap (2 layers), so the
    breakdown arranges exactly the first two of `layeringOrder` — and the
    following `main` must come back WIDER, which is the half that makes this a
    rebuild rather than just a strip."""
    trace = generate_trace(cell)
    sections = trace.song_form.sections

    def active(section_id: str) -> set[str]:
        return {
            e.role
            for e in trace.arrangement.entries
            if e.section_id == section_id and e.active
        }

    breakdowns = [(i, s) for i, s in enumerate(sections) if s.type == "breakdown"]
    assert breakdowns, "cell produced no breakdown section"
    for index, section in breakdowns:
        assert active(section.id) == {"drums", "bass"}
        following = sections[index + 1]
        assert following.type == "main", following.type
        assert active(following.id) > {"drums", "bass"}, (
            f"{following.id} did not rebuild: {sorted(active(following.id))}"
        )


def test_breakdown_entry_dropout_leaves_no_note_sustaining_across_it() -> None:
    """S22-10's regression surface. §3.5's dropout truncates every note crossing a
    breakdown entry at stage 6b — but 6c's `_hat_lift` (fusion's mutation table is
    the first to enable it alongside a breakdown) sets `duration_ticks = 360` on
    an offbeat 8th, and the last offbeat 8th of a bar is 1680, so an unclamped
    lift would re-introduce a 120-tick overhang past the boundary and W2 fires.
    Pinned on the post-transitions IR across every breakdown-bearing cell."""
    for cell in _BREAKDOWN_CELLS:
        trace = generate_trace(cell)
        for section in trace.song_form.sections:
            if section.type != "breakdown":
                continue
            entered = section.start_bar * BAR
            crossing = [
                (ph.role, n.ticks, n.duration_ticks)
                for ph in trace.phrases_stage6
                for n in ph.notes
                if n.ticks < entered < n.ticks + n.duration_ticks
            ]
            assert crossing == [], f"{cell['mood']} {section.id}: {crossing}"


def test_plan_shape_fully_populated() -> None:
    """SESSION_22 constraint 16 / §14.10 plan shape: `GenerationPlan`'s only
    nullable fields are `swing` and `feel_table`; `_resolve_swing` returns None
    only for straight8/straight16, so swing16 always yields a concrete `SwingSpec`,
    and `feelTable: tight` is authored — making fusion the THIRD fully-populated
    plan (after chill_lofi and blues)."""
    for mood in ("energetic", "calm", "tense"):
        plan = generate_plan(
            {"styleFamily": "fusion_jazz", "mood": mood, "seed": "1ps9wxb"}
        )
        assert plan.swing is not None
        assert plan.swing.subdivision == "16"
        assert plan.feel_table == "tight"
        nulls = [k for k, v in plan.model_dump().items() if v is None]
        assert nulls == [], f"{mood}: unexpected null plan fields: {nulls}"
        assert plan.role_flavors


# --- (e) end-to-end validation slice (Layer 1 + L2 at engine defaults) --------


@pytest.mark.parametrize("mood", ["energetic", "calm", "tense"])
@pytest.mark.parametrize("length", [120, 240])
@pytest.mark.parametrize("seed", ["1ps9wxb", "2kq7f3z"])
def test_end_to_end_validates_on_the_corpus_coordinates(
    mood: str, length: int, seed: str
) -> None:
    """The pinned §8.2 corpus matrix — the (energetic, calm, tense) triple x 2
    lengths x the two pinned seeds, i.e. exactly the 12 cells T9 will bless.

    These coordinates are asserted CLEAN on both layers. `validate_pipeline` is
    deliberately NOT asserted empty over arbitrary seeds: per S22-15 an accepted,
    caveated ~0.5% of fusion renders trip L2-1 on the single natural 11 that
    quartal's `[0, 5, 10, 15]` puts over a dominant chord (§6.4 excludes `11` on
    dom7 — a P4 over a dominant is the classic avoid note, which is why `7sus4`
    exists). The wider arbitrary-seed guarantee is the unconditional
    `validate_document` pin in `test_document_always_validates` below."""
    trace = generate_trace(_params(mood, seed, length))
    assert validate_document(trace.document) == []
    assert validate_pipeline(trace.document, trace) == []


@pytest.mark.parametrize(
    "mood",
    [
        "energetic",
        "calm",
        "mysterious",
        "dreamy",
        "nostalgic",
        "triumphant",
        "happy",
        "tense",
    ],
)
def test_document_always_validates(mood: str) -> None:
    """Layer 1 holds UNCONDITIONALLY — every supported mood, both length classes,
    arbitrary seeds. (The L2 pipeline suite is a QA report with a caveated ~0.5%
    fusion exception, S22-15; the schema contract has none.)"""
    for seed in ("0", "1", "2", "3", "4"):
        for length in (120, 240):
            trace = generate_trace(_params(mood, seed, length))
            assert validate_document(trace.document) == [], f"{mood}/{seed}/{length}s"
