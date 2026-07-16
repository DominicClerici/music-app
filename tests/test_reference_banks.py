"""PHASE_5 §7 reference pattern banks (T2).

Proves the two reference packs (`pop_rock`, `jazz`) load clean through the
enforced PT1-PT11 + §3.2 completeness path (DoD-1), and pins the normative §7
golden anchors: the six fully-enumerated patterns event-for-event, per-rung
completeness, the §9.1 candidate counts/weights, the `voicing.classes` maps,
`layeringOrder`, the jazz walking block, and bank-level retarget inheritance.
"""

from trackgen.packs.loader import resolve_pack
from trackgen.packs.models import (
    DrumEvent,
    PatternEnvelope,
    PitchedEvent,
    StylePack,
)


def _pack(name: str) -> StylePack:
    pack = resolve_pack(name)
    assert pack is not None, f"{name} did not resolve"
    return pack


def _entry(pack: StylePack, role: str, entry_id: str) -> PatternEnvelope:
    return next(e for e in pack.patterns[role] if e.id == entry_id)


def _drum_tuples(env: PatternEnvelope) -> list[tuple[int, str, float, int | None]]:
    """(pos, voice, velocity, dur) per drum event, in authored order."""
    out: list[tuple[int, str, float, int | None]] = []
    for e in env.events:
        assert isinstance(e, DrumEvent)
        out.append((e.pos, e.voice, e.velocity, e.dur))
    return out


def _pitched_tuples(
    env: PatternEnvelope,
) -> list[tuple[int, str, int, float, int, bool]]:
    """(pos, degree, octave, velocity, dur, push) per pitched event."""
    out: list[tuple[int, str, int, float, int, bool]] = []
    for e in env.events:
        assert isinstance(e, PitchedEvent)
        out.append((e.pos, e.degree, e.octave, e.velocity, e.dur, e.push))
    return out


# --- DoD-1: both reference packs load clean ---------------------------------


def test_reference_packs_load_clean() -> None:
    # resolve_pack raising PackLoadError would fail here; it exercises the
    # enforced PT5/PT6/PT7/PT10 path since the packs declare Phase-5 markers.
    assert _pack("pop_rock") is not None
    assert _pack("jazz") is not None


# --- Verbatim golden anchors (§7, event-for-event) --------------------------


def test_anchor_pr_dr_2a() -> None:
    env = _entry(_pack("pop_rock"), "drums", "pr_dr_2a")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        3,
        1920,
    )
    assert _drum_tuples(env) == [
        (0, "kick", 0.92, None),
        (960, "kick", 0.88, None),
        (480, "snare", 0.85, None),
        (1440, "snare", 0.82, None),
        (0, "hat_closed", 0.58, None),
        (240, "hat_closed", 0.40, None),
        (480, "hat_closed", 0.48, None),
        (720, "hat_closed", 0.40, None),
        (960, "hat_closed", 0.55, None),
        (1200, "hat_closed", 0.40, None),
        (1440, "hat_closed", 0.48, None),
        (1680, "hat_closed", 0.42, None),
    ]


def test_pr_dr_3_bar2_carries_groove() -> None:
    # rung-3 bar 2 must carry the money-beat backbone (pr_dr_2a shifted +1920),
    # not just the three gated extras — a dropout would make rung 3 sparser than
    # rung 2. See PHASE_5 §7.1.
    env = _entry(_pack("pop_rock"), "drums", "pr_dr_3")
    tuples = _drum_tuples(env)
    # bar 1 = full pr_dr_2a (12) + shifted backbone (11) + 3 gated extras = 26
    assert len(tuples) == 26

    bar2 = [t for t in tuples if t[0] >= 1920]
    kicks = {t[0] for t in bar2 if t[1] == "kick"}
    snares = {t[0] for t in bar2 if t[1] == "snare"}
    hats_closed = [t for t in bar2 if t[1] == "hat_closed" and 1920 <= t[0] < 3600]
    hats_open = [t for t in bar2 if t[1] == "hat_open"]

    # backbone kicks (1 & 3) and snares (2 & 4), shifted into bar 2
    assert {1920, 2880}.issubset(kicks)
    assert {2400, 3360}.issubset(snares)
    # 8th-note hat backbone: at least 7 closed hats across the bar
    assert len(hats_closed) >= 7
    # the 4& open hat replaces the shifted 4& closed hat
    assert any(t[0] == 3600 for t in hats_open)
    # the two gated extras still present: ghost snare @3000, extra kick @3120
    assert 3000 in snares
    assert 3120 in kicks


def test_anchor_pr_dr_i() -> None:
    env = _entry(_pack("pop_rock"), "drums", "pr_dr_i")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "intro",
        1,
        1,
        1920,
    )
    assert _drum_tuples(env) == [
        (0, "kick", 0.85, None),
        (0, "hat_closed", 0.50, None),
        (480, "hat_closed", 0.40, None),
        (960, "hat_closed", 0.45, None),
        (1440, "hat_closed", 0.40, None),
    ]


def test_anchor_pr_bs_2() -> None:
    env = _entry(_pack("pop_rock"), "bass", "pr_bs_2")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        1,
        1920,
    )
    assert _pitched_tuples(env) == [
        (0, "root", 0, 0.72, 480, False),
        (480, "root", 0, 0.66, 480, False),
        (960, "root", 0, 0.70, 480, False),
        (1440, "root", 0, 0.66, 480, False),
    ]


def test_anchor_pr_cp_2() -> None:
    env = _entry(_pack("pop_rock"), "comping", "pr_cp_2")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        1,
        1920,
    )
    assert _pitched_tuples(env) == [
        (0, "chord", 0, 0.62, 900, False),
        (960, "chord", 0, 0.58, 900, False),
    ]


def test_anchor_jz_dr_2() -> None:
    env = _entry(_pack("jazz"), "drums", "jz_dr_2")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        1,
        1920,
    )
    assert _drum_tuples(env) == [
        (0, "ride", 0.70, None),
        (480, "ride", 0.72, None),
        (720, "ride", 0.55, None),
        (960, "ride", 0.70, None),
        (1440, "ride", 0.72, None),
        (1680, "ride", 0.55, None),
        (480, "hat_closed", 0.50, None),
        (1440, "hat_closed", 0.50, None),
    ]


def test_anchor_jz_cp_2a() -> None:
    env = _entry(_pack("jazz"), "comping", "jz_cp_2a")
    assert (env.kind, env.energy_level, env.weight, env.length_ticks) == (
        "main",
        2,
        3,
        1920,
    )
    assert _pitched_tuples(env) == [
        (0, "chord", 0, 0.62, 700, False),
        (720, "chord", 0, 0.55, 400, False),
    ]


# --- Per-rung completeness (§3.2 / PT5) -------------------------------------


def _has_ungated_main_each_rung(entries: list[PatternEnvelope]) -> bool:
    for rung in (1, 2, 3, 4):
        if not any(
            e.kind == "main" and e.energy_level == rung and not e.is_gated
            for e in entries
        ):
            return False
    return True


def _has_ungated(entries: list[PatternEnvelope], kind: str) -> bool:
    return any(e.kind == kind and not e.is_gated for e in entries)


def test_completeness_all_voiced_roles() -> None:
    pop = _pack("pop_rock")
    jazz = _pack("jazz")
    # drums/comping/pads in both packs, plus pop bass (mode: patterns).
    cases = (
        (pop, ("drums", "bass", "comping", "pads")),
        (jazz, ("drums", "comping", "pads")),
    )
    for pack, roles in cases:
        for role in roles:
            entries = pack.patterns[role]
            assert _has_ungated_main_each_rung(entries), f"{role}: rung gap"
            assert _has_ungated(entries, "intro"), f"{role}: no ungated intro"
            assert _has_ungated(entries, "ending"), f"{role}: no ungated ending"


def test_jazz_bass_is_walking_and_empty() -> None:
    jazz = _pack("jazz")
    assert jazz.bass_mode == "walking"
    # walking bass carries no patterns and is exempt from completeness.
    assert jazz.patterns["bass"] == []


# --- Candidate counts / weights (§9.1 draw-narrative premises) ---------------


def _counts_by_rung(
    entries: list[PatternEnvelope], kind: str
) -> dict[int, list[tuple[str, int]]]:
    out: dict[int, list[tuple[str, int]]] = {}
    for e in entries:
        if e.kind == kind:
            out.setdefault(e.energy_level, []).append((e.id, e.weight))
    return {k: sorted(v) for k, v in out.items()}


def test_candidate_counts_pop_drums_rung2() -> None:
    pop = _pack("pop_rock")
    by_rung = _counts_by_rung(pop.patterns["drums"], "main")
    assert sorted(by_rung[2]) == [("pr_dr_2a", 3), ("pr_dr_2b", 1)]
    # every other pop main rung is a single candidate
    for rung in (1, 3, 4):
        assert len(by_rung[rung]) == 1, f"pop drums rung {rung} not single"


def test_candidate_counts_pop_all_single_except_drums_r2() -> None:
    pop = _pack("pop_rock")
    for role in ("bass", "comping", "pads"):
        by_rung = _counts_by_rung(pop.patterns[role], "main")
        for rung in (1, 2, 3, 4):
            assert len(by_rung[rung]) == 1, f"pop {role} rung {rung} not single"


def test_candidate_counts_jazz_drums_rung3() -> None:
    jazz = _pack("jazz")
    by_rung = _counts_by_rung(jazz.patterns["drums"], "main")
    assert sorted(by_rung[3]) == [("jz_dr_3a", 3), ("jz_dr_3b", 2)]
    for rung in (1, 2, 4):
        assert len(by_rung[rung]) == 1, f"jazz drums rung {rung} not single"


def test_candidate_counts_jazz_comping_rung2_rung3() -> None:
    jazz = _pack("jazz")
    by_rung = _counts_by_rung(jazz.patterns["comping"], "main")
    assert sorted(by_rung[2]) == [("jz_cp_2a", 3), ("jz_cp_2b", 2)]
    assert sorted(by_rung[3]) == [("jz_cp_3a", 3), ("jz_cp_3b", 2)]
    for rung in (1, 4):
        assert len(by_rung[rung]) == 1, f"jazz comping rung {rung} not single"


# --- voicing.classes, layeringOrder, walking block --------------------------


def test_voicing_classes_maps() -> None:
    pop = _pack("pop_rock")
    jazz = _pack("jazz")
    assert pop.voicing["comping"].classes == {
        1: ("triad_close", "triad_open"),
        2: ("triad_close", "triad_open"),
        3: ("triad_close", "shell3"),
        4: ("triad_close", "shell3"),
    }
    assert pop.voicing["pads"].classes == {i: ("fifths",) for i in (1, 2, 3, 4)}
    assert jazz.voicing["comping"].classes == {
        1: ("shell2", "shell3"),
        2: ("shell2", "shell3"),
        3: ("rootless_a", "rootless_b"),
        4: ("rootless_a", "rootless_b"),
    }
    assert jazz.voicing["pads"].classes == {i: ("quartal",) for i in (1, 2, 3, 4)}


def test_layering_order_both_packs() -> None:
    for name in ("pop_rock", "jazz"):
        assert _pack(name).layering_order == ("drums", "bass", "comping", "pads")


def test_jazz_walking_block() -> None:
    walking = _pack("jazz").walking
    assert walking is not None
    assert walking.feel_by_intensity == {1: "two", 2: "two", 3: "four", 4: "four"}
    assert walking.approach_weights == {
        "chromatic_below": 2,
        "diatonic": 1,
        "dominant": 1,
    }
    assert walking.beat1_repeat_weights == {"fifth": 2, "third": 1, "root": 1}


# --- Bank-level retarget default inheritance (§7 / T1b) ----------------------


def test_bank_retarget_default_inherited() -> None:
    pop = _pack("pop_rock")
    # pop bass entries inherit {28, 45, retrigger}; none override.
    for env in pop.patterns["bass"]:
        assert env.retarget is not None
        assert env.retarget.register_low == 28
        assert env.retarget.register_high == 45
        assert env.retarget.on_chord_change == "retrigger"
    # pop comping inherits {52, 67, retrigger}; pads {45, 64, retrigger}.
    cp = _entry(pop, "comping", "pr_cp_1")
    assert cp.retarget is not None
    assert (cp.retarget.register_low, cp.retarget.register_high) == (52, 67)
    pd = _entry(pop, "pads", "pr_pd_1")
    assert pd.retarget is not None
    assert (pd.retarget.register_low, pd.retarget.register_high) == (45, 64)
    # drums carry no retarget (lane-exempt).
    assert _entry(pop, "drums", "pr_dr_1").retarget is None


def test_push_and_min_density_fields_present() -> None:
    # a pushed pop comping event and a gated pop bass pickup exercise PT8 fields.
    cp3 = _entry(_pack("pop_rock"), "comping", "pr_cp_3")
    pushed = [e for e in cp3.events if isinstance(e, PitchedEvent) and e.push]
    assert len(pushed) == 1 and pushed[0].pos == 1680
    bs4 = _entry(_pack("pop_rock"), "bass", "pr_bs_4")
    gated = [
        e
        for e in bs4.events
        if isinstance(e, PitchedEvent) and e.min_density is not None
    ]
    assert len(gated) == 1 and gated[0].min_density == 0.75
