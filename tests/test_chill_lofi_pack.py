"""chill_lofi pack — bank inventory, the `lf_dr_2` golden anchor, first-use
machinery pins, and the end-to-end validation slice (SESSION_20 T5, PHASE_8 §4).

This is the first pack that exercises five dormant engine paths end-to-end
(SESSION_20 constraint 11): the `dropout` device on a breakdown entry + the
2-layer breakdown cap, `close: fade` (the HOLD alias), the `laidback` feel
profile, `swing16` at the pack override ratio 0.57, and one `loop` progression
draw serving every section. Each gets an explicit, discriminating pin here.

Companion module `test_chill_lofi_variety.py` owns the per-candidate selection
locks (M1 convention). Determinism (ROADMAP invariant 5): every seed is a pinned
literal; no `random`/`time`/`datetime` import (TID251).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trackgen.humanize.stage import _run, _ZeroJitter
from trackgen.interpreter.stage import generate_plan
from trackgen.packs.loader import resolve_pack
from trackgen.packs.models import DrumEvent, PatternEnvelope, StylePack
from trackgen.pipeline.explain import EntryRecord, ExplainCollector
from trackgen.pipeline.trace import generate_trace
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.ir import Phrase, PhraseNote, SongForm
from trackgen.schema.validate import validate_document
from trackgen.transitions._common import Builder
from trackgen.transitions.devices import _apply_dropout

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "chill_lofi"
BAR = 1920


def _pack() -> StylePack:
    pack = resolve_pack("chill_lofi")
    assert pack is not None, "chill_lofi did not resolve"
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


# --- (a) bank inventory pins (M1 convention: trips on any bank edit) ----------


def test_pack_loads_and_is_patterns_mode() -> None:
    pack = _pack()
    assert pack.bass_mode == "patterns"
    assert pack.layering_order == ("drums", "bass", "comping", "pads")


def test_candidate_counts_drums() -> None:
    by_rung = _counts_by_rung(_pack().patterns["drums"], "main")
    assert by_rung == {
        1: [("lf_dr_1", 3), ("lf_dr_1b", 2)],
        2: [("lf_dr_2", 3), ("lf_dr_2b", 2)],
        3: [("lf_dr_3", 3), ("lf_dr_3b", 2)],
        4: [("lf_dr_4", 3), ("lf_dr_4b", 2)],
    }
    drums = _pack().patterns["drums"]
    assert _counts_by_rung(drums, "intro") == {1: [("lf_dr_i", 3), ("lf_dr_ib", 2)]}
    assert _counts_by_rung(drums, "ending") == {1: [("lf_dr_e", 3), ("lf_dr_eb", 2)]}
    # exactly two fills, one per rung, ungated singletons (PT12; not variety-linted)
    assert _counts_by_rung(drums, "fill") == {
        2: [("lf_dr_f1", 1)],
        3: [("lf_dr_f2", 1)],
    }


@pytest.mark.parametrize(
    ("role", "prefix"),
    [("bass", "lf_bs"), ("comping", "lf_cp"), ("pads", "lf_pd")],
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
    """Every variety-linted slot is a 3/2 weighted pair: primary 3, sibling 2
    (C5 handoff convention). Sorted-by-id => (…, 3) then (…b, 2)."""
    pack = _pack()
    for role in ("drums", "bass", "comping", "pads"):
        for kind in ("main", "intro", "ending"):
            for _rung, pairs in _counts_by_rung(pack.patterns[role], kind).items():
                weights = sorted(w for _, w in pairs)
                assert weights == [2, 3], f"{role}/{kind}: {pairs}"


def test_voicing_class_maps() -> None:
    pack = _pack()
    assert pack.voicing["comping"].classes == {
        1: ("shell3", "triad_close"),
        2: ("rootless_a", "rootless_b"),
        3: ("rootless_a", "rootless_b"),
        4: ("rootless_a", "rootless_b"),
    }
    assert pack.voicing["pads"].classes == {i: ("fifths",) for i in (1, 2, 3, 4)}


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


# --- (b) lf_dr_2 verbatim golden (§4.4 anchor, byte-frozen) -------------------


def test_golden_lf_dr_2_verbatim() -> None:
    env = _entry(_pack(), "drums", "lf_dr_2")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        3,
        1920,
    )
    assert _drum_tuples(env) == [
        (0, "kick", 0.80, None, None),
        (840, "kick", 0.60, None, 0.45),  # swung ghost kick, minDensity-gated
        (480, "snare", 0.72, None, None),
        (1440, "snare", 0.70, None, None),
        (0, "hat_closed", 0.42, None, None),
        (240, "hat_closed", 0.30, None, None),
        (480, "hat_closed", 0.36, None, None),
        (720, "hat_closed", 0.28, None, None),
        (960, "hat_closed", 0.40, None, None),
        (1200, "hat_closed", 0.30, None, None),
        (1440, "hat_closed", 0.36, None, None),
        (1680, "hat_closed", 0.32, None, None),
    ]


# --- (d) first-use machinery pins (SESSION_20 constraint 11) ------------------


def test_plan_carries_swing16_at_057() -> None:
    plan = generate_plan(
        {"styleFamily": "chill_lofi", "mood": "nostalgic", "seed": "1"}
    )
    assert plan.swing is not None
    assert (plan.swing.ratio, plan.swing.subdivision) == (0.57, "16")


def test_plan_selects_laidback_feel() -> None:
    plan = generate_plan(
        {"styleFamily": "chill_lofi", "mood": "nostalgic", "seed": "1"}
    )
    assert plan.feel_table == "laidback"


def test_laidback_humanizer_shifts_comping_late() -> None:
    """The `laidback` profile lands a comping hit ~12 ms late vs `straight`'s
    ~5 ms — the discriminating end-to-end proof the pack's feelTable is applied
    (comping row: laidback 12 ms scalar, straight 5 ms scalar; §5.3 feel.yaml)."""
    plan = generate_plan(
        {"styleFamily": "chill_lofi", "mood": "nostalgic", "seed": "1"}
    )
    tpm = 480 * plan.tempo_bpm / 60000
    # a beat-2 comping hit (tick 480): a beat, so swing16 leaves it untouched;
    # ZeroJitter isolates the deterministic swing+offset transform (§11.5 seam).
    note = PhraseNote(ticks=480, duration_ticks=240, midi=60, velocity=0.44)
    form = SongForm(sections=[], total_bars=4, template_id="t")

    def tick(p: object) -> int:
        phrase = Phrase(
            track_id="comping", role="comping", start_tick=0, end_tick=BAR, notes=[note]
        )
        out, _ = _run([phrase], form, p, _ZeroJitter())  # type: ignore[arg-type]
        return out[0].notes[0].ticks

    laidback = tick(plan)
    straight = tick(plan.model_copy(update={"feel_table": "straight"}))
    assert laidback == round(480 + 12 * tpm)
    assert straight == round(480 + 5 * tpm)
    assert laidback > straight  # laid back = later


def test_one_loop_draw_serves_every_section() -> None:
    """The single `loop` harmonyTag is drawn ONCE from the pool and reused by
    every section (P7 open-ending: one pool pick per track)."""
    col = ExplainCollector()
    trace = generate_trace(
        {
            "styleFamily": "chill_lofi",
            "mood": "nostalgic",
            "seed": "1",
            "maxLengthSec": 180,
        },
        explain=col,
    )
    tags = {s.harmony_tag for s in trace.song_form.sections}
    assert tags == {"loop"}
    pool_picks = [
        r for r in col.records if isinstance(r, EntryRecord) and r.kind == "pool"
    ]
    assert len(pool_picks) == 1
    assert pool_picks[0].tag == "loop"


def test_close_fade_yields_hold_shape_no_ritard() -> None:
    """`close: fade` (HOLD alias, PHASE_6 D7): the final chord notes carry the
    `hold` tag and extend to the section end, with ZERO ritard tempo events."""
    trace = generate_trace(
        {
            "styleFamily": "chill_lofi",
            "mood": "nostalgic",
            "seed": "1",
            "maxLengthSec": 180,
        }
    )
    final = trace.song_form.sections[-1]
    assert final.ending is not None and final.ending.close == "fade"
    # fade emits no ritard curve (§5.7 — only `ritard` closes do).
    assert trace.tempo_events == []
    hold_notes = [
        n for ph in trace.phrases_stage7 for n in ph.notes if "hold" in n.tags
    ]
    assert hold_notes, "HOLD shape did not fire on the fade close"
    # the pitched final-chord notes (bass/comping/pads) sustain to the section
    # end; the struck crash+kick are also `hold`-tagged but do not sustain.
    final_end = (final.start_bar + final.length_bars) * BAR
    pitched_holds = [n for n in hold_notes if n.midi is not None]
    assert pitched_holds, "no sustained pitched HOLD note"
    for n in pitched_holds:
        assert n.ticks + n.duration_ticks == final_end


# The first breakdown-producing cell (discovered by fixed enumeration).
_BREAKDOWN_CELL = {
    "styleFamily": "chill_lofi",
    "mood": "nostalgic",
    "seed": "0",
    "maxLengthSec": 90,
}


def test_breakdown_caps_at_two_layers() -> None:
    """A breakdown section arranges exactly 2 layers — the first two of the
    layeringOrder (drums, bass) — via the §4.1 breakdown cap (arrange.py:112)."""
    trace = generate_trace(_BREAKDOWN_CELL)
    breakdowns = [s for s in trace.song_form.sections if s.type == "breakdown"]
    assert breakdowns, "cell produced no breakdown section"
    for section in breakdowns:
        active = {
            e.role
            for e in trace.arrangement.entries
            if e.section_id == section.id and e.active
        }
        assert active == {"drums", "bass"}, active


def test_breakdown_entry_dropout_invariant_holds() -> None:
    """The breakdown entry routes through the `dropout` device: no note sustains
    strictly across the breakdown's entered tick in the post-transitions IR."""
    trace = generate_trace(_BREAKDOWN_CELL)
    breakdowns = [s for s in trace.song_form.sections if s.type == "breakdown"]
    assert breakdowns
    for section in breakdowns:
        entered = section.start_bar * BAR
        crossing = [
            (ph.role, n.ticks, n.duration_ticks)
            for ph in trace.phrases_stage6
            for n in ph.notes
            if n.ticks < entered < n.ticks + n.duration_ticks
        ]
        assert crossing == [], crossing


def test_dropout_device_truncates_a_crossing_note() -> None:
    """The `dropout` device truncates a note sustaining across the entered tick
    to end exactly at it, leaving non-crossing notes untouched (§3.5). The pack's
    bar-quantized banks never actually cross a breakdown boundary (hence the
    in-render device is a structural no-op), so the truncation itself is proven
    on a synthetic crossing note through the real device."""
    builder = Builder(
        track_id="bass",
        role="bass",
        start_tick=0,
        end_tick=2 * BAR,
        notes=[
            PhraseNote(
                ticks=1440, duration_ticks=960, midi=40, velocity=0.6
            ),  # crosses 1920
            PhraseNote(
                ticks=480, duration_ticks=240, midi=40, velocity=0.6
            ),  # ends 720
        ],
    )
    _apply_dropout([builder], BAR)
    assert [(n.ticks, n.duration_ticks) for n in builder.notes] == [
        (1440, 480),  # truncated to end at 1920
        (480, 240),  # untouched
    ]


# --- (e) end-to-end validation slice (Layer 1 + L2 at engine defaults) --------


def test_calibration_yaml_blessed() -> None:
    """§8.1 bootstrap completed at S20 T7: the first blessed calibration.yaml
    exists and covers every supported mood (first-batch L2 thresholds are the
    engine defaults by design; the slice below asserts renders stay clean
    under the pack's own thresholds)."""
    path = _PACK_DIR / "calibration.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    interp = _pack().interpreter
    assert interp is not None
    assert set(data["moods"]) == set(interp.supported_moods)


@pytest.mark.parametrize("mood", ["nostalgic", "happy", "melancholic"])
@pytest.mark.parametrize("length", [120, 240])
@pytest.mark.parametrize("seed", ["0", "1", "2", "3", "4"])
def test_end_to_end_validates(mood: str, length: int, seed: str) -> None:
    """Default (nostalgic) + the two corpus extremes (happy, melancholic) x 2
    lengths x 5 seeds each serialize to a document passing schema validation
    (Layer 1) and the pipeline suite (L2 at engine defaults, no calibration)."""
    trace = generate_trace(
        {
            "styleFamily": "chill_lofi",
            "mood": mood,
            "seed": seed,
            "maxLengthSec": length,
        }
    )
    assert validate_document(trace.document) == []
    assert validate_pipeline(trace.document, trace) == []
