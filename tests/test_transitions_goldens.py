"""PHASE_6 §7 stage-6 worked-example goldens (Task T4, DoD 3/4).

The **independent golden arbiter** for the Transition engine. Every asserted
value is transcribed from PHASE_6 **§7.1** (pop_rock/happy) or **§7.2**
(jazz/melancholic) — the pinned design text — NOT read back off the engine's
output (ROADMAP §3 golden-value arbitration). The engine is then driven on the
real chained pipeline (`_stage6_driver`) and asserted to reproduce them. On any
divergence the rule is: do NOT tune — mark `@pytest.mark.xfail(strict=True)` and
escalate to the orchestrator (the C-09 precedent). **This session: every §7
value reproduced; there is no xfail.**

Covered here:
- device narratives — the exact per-stream draw counts (pop 14 devices / 38 drums
  / 9 comping; jazz 10 / 32 / 11) via counting-RNG shims, and the fired-op lists
  verbatim including the documented no-ops (§11.3);
- rendering goldens — pop fill bar 3 note-for-note, crash+kick with/without an
  existing kick, one mutated unit per operator class, HOLD for both examples
  (§11.4).
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from _stage6_driver import (
    JAZZ,
    POP,
    Stage6Inputs,
    drive,
    role_window,
    stage6_final,
    stage6_passes,
    track_window,
)
from trackgen.seeds import derive, stream_seed
from trackgen.transitions import devices as devices_mod
from trackgen.transitions import mutation as mutation_mod
from trackgen.transitions._common import BAR

# =============================================================================
# instrumentation — counting-RNG shims + fired-op recorder
# =============================================================================


class _CountingRandom(random.Random):
    """A `random.Random` recording its construction seed and its `randrange`
    count. `weighted_choice`/`randrange` each issue exactly one `randrange`, so
    `.count` is the exact draw count on this sub-stream (mirrors the §9.1
    selection-golden and §11.7 determinism shims)."""

    def __init__(self, seed: Any = None) -> None:
        super().__init__(seed)
        self.seed_arg = seed
        self.count = 0

    def randrange(self, *args: Any, **kwargs: Any) -> int:
        self.count += 1
        return super().randrange(*args, **kwargs)


def _devices_draw_count(inp: Stage6Inputs, monkeypatch: pytest.MonkeyPatch) -> int:
    """Total draws on the single `derive(transitions, "devices")` RNG (§3.8)."""
    instances: list[_CountingRandom] = []

    def factory(seed: Any = None) -> _CountingRandom:
        rng = _CountingRandom(seed)
        instances.append(rng)
        return rng

    monkeypatch.setattr(devices_mod, "Rng", factory)
    stage6_passes(inp)  # runs 6a + 6b (mutation uses the real, unpatched Rng).
    monkeypatch.undo()
    assert len(instances) == 1  # exactly one devices RNG for the whole timeline.
    return instances[0].count


def _mutation_draw_counts(
    inp: Stage6Inputs, monkeypatch: pytest.MonkeyPatch
) -> tuple[int, int]:
    """`(drums, comping)` draw totals on the per-unit mutate sub-streams (§3.8),
    decomposed by re-deriving each role's unit seeds from `mutation._units`."""
    instances: list[_CountingRandom] = []

    def factory(seed: Any = None) -> _CountingRandom:
        rng = _CountingRandom(seed)
        instances.append(rng)
        return rng

    monkeypatch.setattr(mutation_mod, "Rng", factory)
    stage6_passes(inp)
    monkeypatch.undo()

    mutate_seed = derive(
        stream_seed(inp.plan.seed.master, inp.plan.seed.overrides, "transitions"),
        "mutate",
    )
    drums_seed = derive(mutate_seed, "drums")
    comping_seed = derive(mutate_seed, "comping")
    drum_units = list(
        mutation_mod._units(inp.sf, mutation_mod._active_sections(inp.ap, "drums"), 2)
    )
    comping_units = list(
        mutation_mod._units(inp.sf, mutation_mod._active_sections(inp.ap, "comping"), 8)
    )
    drum_seeds = {derive(drums_seed, f"bar:{ub}") for _s, ub, _lo, _hi in drum_units}
    comping_seeds = {
        derive(comping_seed, f"bar:{ub}") for _s, ub, _lo, _hi in comping_units
    }
    drums = sum(i.count for i in instances if i.seed_arg in drum_seeds)
    comping = sum(i.count for i in instances if i.seed_arg in comping_seeds)
    return drums, comping


def _fired_ops(
    inp: Stage6Inputs, monkeypatch: pytest.MonkeyPatch
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """`(drums, comping)` fired-op lists: `(unit_start_bar, op_name)` for every
    unit that drew (dispatched) a non-`none` operator — including operators that
    degrade to a no-op (they are still dispatched). A `none` draw dispatches
    nothing, so it never appears. Recorded by wrapping the operator dispatch
    tables the `mutate` driver reads."""
    fired: list[tuple[int, str]] = []

    def wrap(name: str, fn: Any) -> Any:
        def recorded(
            builders: Any, section: Any, u_lo: int, u_hi: int, fbt: int
        ) -> None:
            fired.append((u_lo // BAR, name))
            fn(builders, section, u_lo, u_hi, fbt)

        return recorded

    monkeypatch.setattr(
        mutation_mod,
        "_DRUM_OPS",
        {k: wrap(k, v) for k, v in mutation_mod._DRUM_OPS.items()},
    )
    monkeypatch.setattr(
        mutation_mod,
        "_COMPING_OPS",
        {k: wrap(k, v) for k, v in mutation_mod._COMPING_OPS.items()},
    )
    stage6_passes(inp)
    monkeypatch.undo()

    drum_ops = sorted(x for x in fired if x[1] in mutation_mod._DRUM_OPS)
    comping_ops = sorted(x for x in fired if x[1] in mutation_mod._COMPING_OPS)
    return drum_ops, comping_ops


# =============================================================================
# §7.1 — pop_rock / happy : device narrative (14 / 38 / 9)
# =============================================================================


def test_pop_device_draw_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    """§7.1 / §11.3: devices stream = 14 draws (2 stop-vs-fill at the rung-4
    rising chorus-2/chorus-3 entries + 12 interior phrase-fill include draws;
    every fill single-candidate → 0 selection draws). Mutation: 38 drums-unit +
    9 comping-unit draws."""
    inp = drive(POP)
    assert _devices_draw_count(inp, monkeypatch) == 14
    assert _mutation_draw_counts(inp, monkeypatch) == (38, 9)


def test_pop_fired_op_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """§7.1 fired-op lists **verbatim** (drawn non-`none` ops per unit). Drums —
    15 ops: `kick_pickup` @4/20/40/46/66/70, `hat_lift` @8/10/22/24/26/38/58,
    `drop_ornament` @54/68. Comping — 3 ops: `drop_hit` @20/36, `anticipate`
    @44."""
    drum_ops, comping_ops = _fired_ops(drive(POP), monkeypatch)
    assert drum_ops == sorted(
        [
            (4, "kick_pickup"),
            (20, "kick_pickup"),
            (40, "kick_pickup"),
            (46, "kick_pickup"),
            (66, "kick_pickup"),
            (70, "kick_pickup"),
            (8, "hat_lift"),
            (10, "hat_lift"),
            (22, "hat_lift"),
            (24, "hat_lift"),
            (26, "hat_lift"),
            (38, "hat_lift"),
            (58, "hat_lift"),
            (54, "drop_ornament"),
            (68, "drop_ornament"),
        ]
    )
    assert comping_ops == sorted(
        [(20, "drop_hit"), (36, "drop_hit"), (44, "anticipate")]
    )


def test_pop_drop_ornament_noop_and_fire() -> None:
    """§7.1: `drop_ornament` @54 (bridge rung-2 `pr_dr_2a`, no `minDensity`
    events) is a **no-op**; @68 (chorus-3 rung-4 `pr_dr_4`) **fires**, dropping
    one gated drum event in its unit. Verified by the drum-event count in each
    2-bar unit range across the mutation pass."""
    inp = drive(POP)
    post_6b, final = stage6_passes(inp)

    def drum_count(phrases: Any, unit_bar: int) -> int:
        lo, hi = unit_bar * BAR, (unit_bar + 2) * BAR
        return sum(
            1
            for p in phrases
            if p.role == "drums"
            for n in p.notes
            if lo <= n.ticks < hi
        )

    assert drum_count(final, 54) == drum_count(post_6b, 54)  # no-op.
    assert drum_count(final, 68) == drum_count(post_6b, 68) - 1  # fires (−1 event).


def test_pop_anticipate_at_44_degrades_to_noop() -> None:
    """§7.1 lists `anticipate` @44 among the drawn comping ops; on the real
    chorus-2 comp (a dense 240-grid pad) the −240 landing collides with an
    existing attack, so the §3.7 `[new, old)` guard degrades it to a **no-op**
    (the drawn-op list still reproduces; only its rendering is empty). Documented
    here so the divergence between "drawn" and "renders an edit" is explicit."""
    inp = drive(POP)
    post_6b, final = stage6_passes(inp)
    lo, hi = 44 * BAR, 52 * BAR
    before = sorted(
        (n.ticks, n.midi)
        for p in post_6b
        if p.role == "comping"
        for n in p.notes
        if lo <= n.ticks < hi
    )
    after = sorted(
        (n.ticks, n.midi)
        for p in final
        if p.role == "comping"
        for n in p.notes
        if lo <= n.ticks < hi
    )
    assert before == after


# =============================================================================
# §7.2 — jazz / melancholic : device narrative (10 / 32 / 11)
# =============================================================================


def test_jazz_device_draw_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    """§7.2 / §11.3: devices stream = 10 draws (all interior phrase-fill include
    draws; stop disabled; every section fill single-candidate). Mutation: 32
    drums-unit + 11 comping-unit draws."""
    inp = drive(JAZZ)
    assert _devices_draw_count(inp, monkeypatch) == 10
    assert _mutation_draw_counts(inp, monkeypatch) == (32, 11)


def test_jazz_fired_op_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """§7.2 fired-op lists **verbatim**. Drums — 4 ops, all `drop_ornament`:
    @4/@54 (rung-2 `jz_dr_2`, no ornaments → no-ops), @20/@40 (rung-3 `jz_dr_3a`
    → fire). Comping — 5 ops: `anticipate` @0/@8, `drop_hit` @20/36/48."""
    drum_ops, comping_ops = _fired_ops(drive(JAZZ), monkeypatch)
    assert drum_ops == sorted(
        [
            (4, "drop_ornament"),
            (54, "drop_ornament"),
            (20, "drop_ornament"),
            (40, "drop_ornament"),
        ]
    )
    assert comping_ops == sorted(
        [
            (0, "anticipate"),
            (8, "anticipate"),
            (20, "drop_hit"),
            (36, "drop_hit"),
            (48, "drop_hit"),
        ]
    )


def test_jazz_drop_ornament_noops_and_fires() -> None:
    """§7.2: `drop_ornament` @4/@54 are **no-ops** (rung-2 `jz_dr_2` carries no
    `minDensity` events); @20/@40 **fire** (rung-3 `jz_dr_3a` drops one gated
    drum event each)."""
    inp = drive(JAZZ)
    post_6b, final = stage6_passes(inp)

    def drum_count(phrases: Any, unit_bar: int) -> int:
        lo, hi = unit_bar * BAR, (unit_bar + 2) * BAR
        return sum(
            1
            for p in phrases
            if p.role == "drums"
            for n in p.notes
            if lo <= n.ticks < hi
        )

    assert drum_count(final, 4) == drum_count(post_6b, 4)  # no-op.
    assert drum_count(final, 54) == drum_count(post_6b, 54)  # no-op.
    assert drum_count(final, 20) == drum_count(post_6b, 20) - 1  # fires.
    assert drum_count(final, 40) == drum_count(post_6b, 40) - 1  # fires.


# =============================================================================
# §7.1 / §7.2 — fill placements + crash velocities
# =============================================================================


def _fill_bars(phrases: Any) -> list[int]:
    return sorted(
        {
            n.ticks // BAR
            for p in phrases
            if p.role == "drums"
            for n in p.notes
            if "fill" in n.tags
        }
    )


def test_pop_fill_placements_and_crashes() -> None:
    """§7.1: section fills into bars 3/11/27/35/51/59; interior phrase fills
    **included** at fill bars 19/55/67 (combined 3/11/19/27/35/51/55/59/67).
    Entry crashes (dur 1440, velocity `0.55 + energy·0.40`) at bars 4/12/28/36/
    52/60 = 0.746/0.866/0.766/0.886/0.726/0.950; **no kick added** (pop mains
    have a beat-1 kick)."""
    final = stage6_final(drive(POP))
    assert _fill_bars(final) == [3, 11, 19, 27, 35, 51, 55, 59, 67]

    expected = {4: 0.746, 12: 0.866, 28: 0.766, 36: 0.886, 52: 0.726, 60: 0.950}
    for bar, vel in expected.items():
        crash = track_window(final, "crash", bar * BAR, bar * BAR + 1)
        assert len(crash) == 1, bar
        assert crash[0].velocity == pytest.approx(vel), bar
        assert crash[0].duration_ticks == 1440
        assert crash[0].tags == ["crash"]
        # A groove beat-1 kick already attacks the entered downbeat: the §3.7
        # double-hit guard adds none — exactly one kick, and it is NOT crash-tagged.
        kicks = track_window(final, "kick", bar * BAR, bar * BAR + 1)
        assert len(kicks) == 1, bar
        assert kicks[0].tags == ["kick"], bar


def test_jazz_fill_placements_and_crashes() -> None:
    """§7.2: section fills into bars 11/23/35/47/59; interior phrase fills
    included at 3/31 (combined 3/11/23/31/35/47/59). Entry crashes (velocity
    `0.40 + energy·0.30`) at bars 12/24/36/48/60 = 0.587/0.611/0.635/0.539/0.503,
    each **with an added kick** (ride patterns have no beat-1 kick — the soft
    'bomb')."""
    final = stage6_final(drive(JAZZ))
    assert _fill_bars(final) == [3, 11, 23, 31, 35, 47, 59]

    expected = {12: 0.587, 24: 0.611, 36: 0.635, 48: 0.539, 60: 0.503}
    for bar, vel in expected.items():
        crash = track_window(final, "crash", bar * BAR, bar * BAR + 1)
        assert len(crash) == 1, bar
        assert crash[0].velocity == pytest.approx(vel), bar
        assert crash[0].tags == ["crash"]
        # No groove beat-1 kick → a soft kick is added at the entered downbeat,
        # crash-tagged, at the crash velocity.
        kicks = track_window(final, "kick", bar * BAR, bar * BAR + 1)
        assert len(kicks) == 1, bar
        assert kicks[0].tags == ["crash"], bar
        assert kicks[0].velocity == pytest.approx(vel), bar


# =============================================================================
# §7.1 — rendering: pop fill bar 3 note-for-note
# =============================================================================


def test_pop_fill_bar_3_note_for_note() -> None:
    """§7.1: fill bar 3 (intro `pr_dr_i` + `pr_dr_f1` window [960, 1920)). Hats
    at 960/1440 deleted; fill snares at 960/1200/1440/1680 velocities
    0.66/0.74/0.82/0.91 (the §3.4 +0.06 shift on authored 0.60/0.68/0.76/0.85 at
    pop-happy dynamicsBase) tag `fill`; kick@0 and hats@0/480 keep playing."""
    final = stage6_final(drive(POP))
    b3 = 3 * BAR

    snare = track_window(final, "snare", b3, b3 + BAR)
    assert [(n.ticks - b3, round(n.velocity, 3), tuple(n.tags)) for n in snare] == [
        (960, 0.66, ("fill",)),
        (1200, 0.74, ("fill",)),
        (1440, 0.82, ("fill",)),
        (1680, 0.91, ("fill",)),
    ]

    hats = track_window(final, "hats", b3, b3 + BAR)
    # groove hats inside the rendered window [960, 1920) deleted; 0/480 survive.
    assert [n.ticks - b3 for n in hats] == [0, 480]
    assert all("fill" not in n.tags for n in hats)

    kick = track_window(final, "kick", b3, b3 + BAR)
    assert [n.ticks - b3 for n in kick] == [0]  # intro beat-1 kick keeps playing.


# =============================================================================
# §7.1 / §7.2 — rendering: crash+kick with and without an existing kick
# =============================================================================


def test_crash_kick_with_existing_kick_pop_bar12() -> None:
    """§7.1: pop bar 12 entry — the verse-1 main has a beat-1 kick, so the §3.7
    guard adds NONE. Crash on the `crash` track (0.866); the single kick is the
    groove's own (not crash-tagged)."""
    final = stage6_final(drive(POP))
    entered = 12 * BAR
    crash = track_window(final, "crash", entered, entered + 1)
    assert len(crash) == 1 and crash[0].velocity == pytest.approx(0.866)
    kicks = track_window(final, "kick", entered, entered + 1)
    assert len(kicks) == 1 and kicks[0].tags == ["kick"]


def test_crash_kick_without_existing_kick_jazz_bar12() -> None:
    """§7.2: jazz bar 12 entry — the ride main has no beat-1 kick, so a kick IS
    added (crash-tagged, at the crash velocity 0.587), alongside the crash."""
    final = stage6_final(drive(JAZZ))
    entered = 12 * BAR
    crash = track_window(final, "crash", entered, entered + 1)
    assert len(crash) == 1 and crash[0].velocity == pytest.approx(0.587)
    kicks = track_window(final, "kick", entered, entered + 1)
    assert len(kicks) == 1
    assert kicks[0].tags == ["crash"] and kicks[0].velocity == pytest.approx(0.587)


# =============================================================================
# §7.1 / §7.2 — rendering: one mutated unit per operator class
# =============================================================================


def test_pop_kick_pickup_unit_at_4() -> None:
    """§7.1: unit @4 `kick_pickup` → a kick added in bar 5 at tick 720 (and-of-2),
    velocity `round3(0.94 × 0.85)` = 0.799, tag `var`."""
    final = stage6_final(drive(POP))
    added = [
        n for n in track_window(final, "kick", 5 * BAR, 6 * BAR) if "var" in n.tags
    ]
    assert len(added) == 1
    assert added[0].ticks - 5 * BAR == 720
    assert added[0].velocity == pytest.approx(0.799)
    assert added[0].midi is None
    assert set(added[0].tags) == {"kick", "var"}


def test_pop_hat_lift_unit_at_8() -> None:
    """§7.1: unit @8 `hat_lift` → bar 9's hat at 1680 (offbeat 8th) becomes
    `hat_open`, dur 360, tag `var`."""
    final = stage6_final(drive(POP))
    hats = track_window(final, "hats", 9 * BAR, 10 * BAR)
    lifted = [n for n in hats if "var" in n.tags]
    assert len(lifted) == 1
    assert lifted[0].ticks - 9 * BAR == 1680
    assert lifted[0].duration_ticks == 360
    assert "hat_open" in lifted[0].tags and "hat_closed" not in lifted[0].tags


def test_jazz_anticipate_preserves_pitches() -> None:
    """§7.2: unit @0 `anticipate` → head-1's bar-7 bar-start Charleston chord
    pulled −240 (to tick 13200) with **pitches unchanged** (F3+C4 = 53, 60), tag
    `var` — an anticipation sounds the incoming chord early (§3.7 preserves
    `midi`)."""
    inp = drive(JAZZ)
    post_6b, final = stage6_passes(inp)
    old = 7 * BAR  # 13440
    new = old - 240  # 13200

    # Pre-mutation: the chord attacks at the bar start with F3+C4.
    pre = sorted(
        n.midi
        for p in post_6b
        if p.role == "comping"
        for n in p.notes
        if n.ticks == old and n.midi is not None
    )
    assert pre == [53, 60]

    # Post-mutation: the same pitches, now attacking at new, tagged var; nothing
    # left at old.
    moved = sorted(
        n.midi
        for p in final
        if p.role == "comping"
        for n in p.notes
        if n.ticks == new and "var" in n.tags and n.midi is not None
    )
    assert moved == [53, 60]
    assert not any(
        n.ticks == old for p in final if p.role == "comping" for n in p.notes
    )


def test_jazz_drop_hit_unit_at_20_two_attack_guard() -> None:
    """§7.2: unit @20 `drop_hit` → the last comping attack in a bar holding ≥ 2
    attacks is deleted (the guard keeps every bar non-silent). One comping attack
    removed in the unit; the bar it came from still has ≥ 1 attack left."""
    inp = drive(JAZZ)
    post_6b, final = stage6_passes(inp)
    lo, hi = 20 * BAR, 28 * BAR  # solo-1 8-bar comping unit @20 (bars 20-23 short).
    pre = {
        n.ticks
        for p in post_6b
        if p.role == "comping"
        for n in p.notes
        if lo <= n.ticks < hi
    }
    post = {
        n.ticks
        for p in final
        if p.role == "comping"
        for n in p.notes
        if lo <= n.ticks < hi
    }
    removed = pre - post
    assert len(removed) == 1
    dropped = next(iter(removed))
    assert dropped % BAR != 0  # never a bar-1 anchor.
    # The bar it came from still holds a comping attack (no fully silent bar).
    dropped_bar = dropped // BAR
    assert any(n // BAR == dropped_bar for n in post)


# =============================================================================
# §7.1 / §7.2 — rendering: the HOLD ending (6a)
# =============================================================================


def test_pop_hold_ending() -> None:
    """§7.1: cold → HOLD at `T_last` = 144000 (bar 75). Pitched notes attacking
    there extend to 145920 (+0.05 velocity, tag `hold`); later attacks deleted;
    drums cleared from 144000; crash+kick added at 144000 velocity 1.000 (0.950
    final-chorus crash + 0.05, clamped)."""
    final = stage6_final(drive(POP))
    t_last = 144000
    end = 145920

    for role in ("bass", "comping", "pads"):
        held = role_window(final, role, t_last, end)
        assert held, role
        for n in held:
            assert "hold" in n.tags
            assert n.ticks == t_last
            assert n.ticks + n.duration_ticks == end
        # Nothing pitched attacks after T_last.
        assert not role_window(final, role, t_last + 1, 10**9)

    crash = track_window(final, "crash", t_last, end)
    assert len(crash) == 1
    assert crash[0].velocity == 1.0 and crash[0].duration_ticks == 1440
    assert crash[0].tags == ["hold"]
    kick = track_window(final, "kick", t_last, end)
    assert len(kick) == 1 and kick[0].velocity == 1.0 and kick[0].tags == ["hold"]
    # Drums cleared from T_last on (only the two HOLD hits remain there).
    assert not [
        n
        for p in final
        if p.role == "drums"
        for n in p.notes
        if n.ticks >= t_last and "hold" not in n.tags
    ]


def test_jazz_hold_ending() -> None:
    """§7.2: ritard + HOLD at `T_last` = bar 63 (120960, the finals' Dm7).
    Walker's D2 and the comping voicing extend to the outro end (122880) +0.05,
    tag `hold`; drums bar-63 cleared; crash+kick at velocity 0.553 (0.503 outro
    crash + 0.05). (The ritard tempo curve is Chunk 2 — not asserted here.)"""
    final = stage6_final(drive(JAZZ))
    t_last = 120960
    end = 122880

    bass = role_window(final, "bass", t_last, end)
    assert bass and all("hold" in n.tags for n in bass)
    assert 38 in {n.midi for n in bass}  # walker's D2 root.
    for n in bass:
        assert n.ticks == t_last and n.ticks + n.duration_ticks == end

    comping = role_window(final, "comping", t_last, end)
    assert comping and all("hold" in n.tags for n in comping)
    for n in comping:
        assert n.ticks + n.duration_ticks == end

    crash = track_window(final, "crash", t_last, end)
    assert len(crash) == 1 and crash[0].velocity == pytest.approx(0.553)
    assert crash[0].tags == ["hold"] and crash[0].duration_ticks == 1440
    kick = track_window(final, "kick", t_last, end)
    assert len(kick) == 1 and kick[0].velocity == pytest.approx(0.553)
    assert kick[0].tags == ["hold"]
