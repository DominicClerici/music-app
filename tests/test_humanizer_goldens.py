"""PHASE_6 §7 stage-7 Humanizer worked-example goldens (Task T4, DoD 5/7).

The **independent golden arbiter** for the Humanizer. The bar-0 pre-jitter
positions asserted here are transcribed from PHASE_6 **§7.2** (the "Humanizer
(swung table…)" paragraph) — the pinned design text — NOT read back off the
engine. The engine is then driven on the real chained pipeline (`_stage6_driver`,
seed `1ps9wxb`) and asserted to reproduce them. Pre-jitter positions are observed
through the real production path with the `_ZeroJitter` seam (swing + offset +
legato, no jitter, no RNG draws).

On any divergence the rule is: do NOT tune — mark `@pytest.mark.xfail(strict=True)`
and escalate (the C-09 precedent). **This session: every §7.2 position
reproduced; there is no xfail.**

Covered here:
- B. the jazz head-1 bar-0 pre-jitter excerpt (ride/hats/comping/bass/and-of-4
  swing + bass legato) — §7.2, DoD 5;
- C. stage-7 determinism (repeated-run identity, per-(role,bar) isolation, exact
  draw counts via a counting-RNG shim) and note-count preservation on both full
  worked examples — §5.8/§11.7, DoD 7 humanizer slice.
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
    track_window,
)
from trackgen.humanize import stage as stage_mod
from trackgen.humanize.feel import load_feel
from trackgen.humanize.stage import (
    _run,
    _vel_jitter_width,
    _voice_of,
    _ZeroJitter,
    humanize,
)
from trackgen.seeds import derive, stream_seed

BAR = 1920


# =============================================================================
# B. jazz head-1 bar-0 pre-jitter excerpt (§7.2, DoD 5)
# =============================================================================


def _jazz_zero_jitter() -> Any:
    """The JAZZ humanized output with jitter suppressed (the §7.2 pre-jitter
    positions): swing + offset + legato, no RNG draws, via the real path."""
    inp = drive(JAZZ)
    s6 = stage6_final(inp)
    phrases, _ = _run(s6, inp.sf, inp.plan, _ZeroJitter())
    return phrases


def test_jazz_head1_bar0_ride() -> None:
    """§7.2: ride bar 0 → 0/480/960/1440 — all four straight quarters, downbeats
    unmoved, 0 offset (no swing displacement). C5 (session 19): head-1 rung-2
    drums now select `jz_dr_2b`, whose ride carries no 720/1680 offbeat notes, so
    this excerpt no longer sounds the and-of-4 swing landing that `jz_dr_2` did
    (that swing math is still exercised on any grid-1680 note elsewhere)."""
    zj = _jazz_zero_jitter()
    ride = track_window(zj, "ride", 0, BAR)
    assert [n.ticks for n in ride] == [0, 480, 960, 1440]


def test_jazz_head1_bar0_hats() -> None:
    """§7.2: hats at 480 and 1440 → **478** and **1438** (−3 ms → −2 ticks at
    ticksPerMs 0.552; downbeats, so no swing)."""
    zj = _jazz_zero_jitter()
    hats = track_window(zj, "hats", 0, BAR)
    assert {n.ticks for n in hats} == {478, 1438}


def test_jazz_head1_bar0_comping() -> None:
    """§7.2: comping Charleston attack at grid 0 → **10** (down offset +18 ms →
    +10 ticks); the and-of-2 attack at grid 720 → **828** (swing 720→827, then
    off offset +2 ms → +1)."""
    zj = _jazz_zero_jitter()
    comping = role_window(zj, "comping", 0, BAR)
    starts = {n.ticks for n in comping}
    assert 10 in starts, "Charleston 0 → +10"
    assert 828 in starts, "and-of-2 720 → 827 (swing) + 1 (off offset)"


def test_jazz_head1_bar0_bass() -> None:
    """§7.2: bass D2 at beat 1 (grid 0) → **0** (−1 tick, then clamp ≥ 0); A2 at
    beat 3 (grid 960) → **959** (bass −2 ms → −1 tick)."""
    zj = _jazz_zero_jitter()
    bass = role_window(zj, "bass", 0, BAR)
    d2 = [n for n in bass if n.midi == 38]  # D2 root.
    a2 = [n for n in bass if n.midi == 45]  # A2.
    assert d2 and any(n.ticks == 0 for n in d2), "D2 −1 → clamp 0"
    assert a2 and any(n.ticks == 959 for n in a2), "A2 grid 960 → 959"


def test_jazz_head1_bass_legato_two_feel_halves() -> None:
    """§7.2: bass legato — two-feel halves 960 → **912** (`round(0.95 × 960)`).
    Bar 0 is a two-feel bar; every bass note is a stretched half. (The §7.1-style
    four-feel quarters 480 → 456 do not occur in this two-feel excerpt.)"""
    zj = _jazz_zero_jitter()
    bass = role_window(zj, "bass", 0, BAR)
    assert bass
    assert all(n.duration_ticks == 912 for n in bass), [n.duration_ticks for n in bass]


# =============================================================================
# C. determinism + note-count preservation (§5.8/§11.7, DoD 7 humanizer slice)
# =============================================================================


def _dump(phrases: Any) -> list[dict[str, Any]]:
    return [p.model_dump() for p in phrases]


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_humanize_repeated_run_identity(params: dict[str, object]) -> None:
    """§11.7: `humanize` is a pure function of `(phrases, form, plan)` — two runs
    yield byte-identical phrases and tempo events."""
    inp = drive(params)
    s6 = stage6_final(inp)
    out_a, tempos_a = humanize(s6, inp.sf, inp.plan)
    out_b, tempos_b = humanize(s6, inp.sf, inp.plan)
    assert _dump(out_a) == _dump(out_b)
    assert [t.model_dump() for t in tempos_a] == [t.model_dump() for t in tempos_b]


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_humanize_note_count_preservation(params: dict[str, object]) -> None:
    """§5 / §11.7: the Humanizer never adds or removes a note. Total and
    per-phrase counts match `s6`, and the `midi`/`tags` multisets are unchanged
    (only ticks/dur/velocity may change)."""
    inp = drive(params)
    s6 = stage6_final(inp)
    out, _ = humanize(s6, inp.sf, inp.plan)

    assert sum(len(p.notes) for p in out) == sum(len(p.notes) for p in s6)
    assert len(out) == len(s6)
    for src, hum in zip(s6, out, strict=True):
        assert hum.track_id == src.track_id and hum.role == src.role
        assert len(hum.notes) == len(src.notes)
        assert sorted(
            (n.midi if n.midi is not None else -1) for n in hum.notes
        ) == sorted((n.midi if n.midi is not None else -1) for n in src.notes)
        assert sorted(tuple(n.tags) for n in hum.notes) == sorted(
            tuple(n.tags) for n in src.notes
        )


class _CountingRandom(random.Random):
    """A `random.Random` counting its `randrange` calls — `tri` issues exactly
    two per draw pair, so `.count` is the exact draw total on the humanize
    sub-streams (mirrors the Chunk-1 goldens' shim)."""

    def __init__(self, seed: Any = None) -> None:
        super().__init__(seed)
        self.count = 0

    def randrange(self, *args: Any, **kwargs: Any) -> int:
        self.count += 1
        return super().randrange(*args, **kwargs)


def _counted_draws(inp: Stage6Inputs, monkeypatch: pytest.MonkeyPatch) -> int:
    """Total `randrange` draws during `humanize` (the sole entropy path is the
    per-`(role, absBar)` `Rng` constructed in `_jitter_pass`)."""
    instances: list[_CountingRandom] = []

    def factory(seed: Any = None) -> _CountingRandom:
        rng = _CountingRandom(seed)
        instances.append(rng)
        return rng

    monkeypatch.setattr(stage_mod, "Rng", factory)
    humanize(stage6_final(inp), inp.sf, inp.plan)
    monkeypatch.undo()
    return sum(i.count for i in instances)


def _structural_draws(s6: Any, inp: Stage6Inputs) -> int:
    """Independently computed expected draw total from the note structure (§5.8):
    per non-`pads` note, +2 timing draws iff `w = round(jitterMs[voice] ×
    ticksPerMs) ≥ 1`, and +2 velocity draws iff `W = round(1000 × (0.04 + 0.08 ×
    dynamicsRange)) ≥ 1`."""
    feel = load_feel()
    ticks_per_ms = 480 * inp.plan.tempo_bpm / 60000
    big_w = _vel_jitter_width(
        feel.vel_jitter.base,
        feel.vel_jitter.range_scale,
        inp.plan.budgets.dynamics_range,
    )
    total = 0
    for phrase in s6:
        if phrase.role == "pads":
            continue
        w = round(feel.jitter_ms.at(_voice_of(phrase)) * ticks_per_ms)
        per_note = (2 if w >= 1 else 0) + (2 if big_w >= 1 else 0)
        total += per_note * len(phrase.notes)
    return total


@pytest.mark.parametrize(
    "params,expected", [(POP, 10470), (JAZZ, 5096)], ids=["pop", "jazz"]
)
def test_humanize_draw_counts(
    params: dict[str, object], expected: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§5.8: the counted draw total (counting-RNG shim) equals the structurally
    computed expectation from the note set — proving the per-note draw discipline
    (timing 2 iff `w ≥ 1`, velocity 2 iff `W ≥ 1`) without a printed count."""
    inp = drive(params)
    s6 = stage6_final(inp)
    structural = _structural_draws(s6, inp)
    counted = _counted_draws(inp, monkeypatch)
    assert counted == structural == expected


def test_humanize_drums_bar0_seed_anchor() -> None:
    """§5.8 pinned vector: the drums bar-0 sub-stream is seeded
    `derive(derive(stream_seed(master, overrides, "humanize"), "drums"),
    "bar:0") == 6949714659275352449`. This locks the per-`(role, absBar)` seed
    derivation directly, so a seeding regression can't hide behind the
    behavioral isolation test below."""
    plan = drive(JAZZ).plan
    base = stream_seed(plan.seed.master, plan.seed.overrides, "humanize")
    assert derive(derive(base, "drums"), "bar:0") == 6949714659275352449


def test_per_role_bar_isolation() -> None:
    """§5.8 / DoD 7: "regenerating one bar reproduces its draws in isolation" —
    each `(role, absBar)` sub-stream is seeded `derive(derive(humanize, role),
    f"bar:{absBar}")`, independent of every other bar.

    We humanize the full JAZZ output, then humanize an input containing ONLY the
    drums notes of bar N (same track_ids / spans / absolute ticks, so absBar is
    unchanged), and assert bar N's humanized output is byte-identical. Drums have
    no cross-bar deterministic coupling (bass legato is the only track-global
    pass), so bar N's positions and its per-bar jitter draws depend solely on
    `bar:N`; isolating it changes nothing.

    This is the discriminator: under a (buggy) whole-role RNG consumed in bar
    order, bar N's draws would depend on the earlier bars now absent, so the
    isolated output would differ. Empirically verified — a per-role scheme fails
    this equality while the pinned per-`(role, absBar)` scheme passes it; a
    velocity-only or later-bar perturbation, by contrast, cannot discriminate the
    two."""
    inp = drive(JAZZ)
    s6 = stage6_final(inp)
    n_bar = 40  # a mid-song bar with active drums.
    lo, hi = n_bar * BAR, (n_bar + 1) * BAR

    def drum_bar(phrases: Any, bar: int) -> list[tuple[Any, ...]]:
        blo, bhi = bar * BAR, (bar + 1) * BAR
        return sorted(
            (p.track_id, n.ticks, n.midi, n.duration_ticks, n.velocity, tuple(n.tags))
            for p in phrases
            if p.role == "drums"
            for n in p.notes
            if blo <= n.ticks < bhi
        )

    full, _ = humanize(s6, inp.sf, inp.plan)

    # Isolate bar N's drum notes into their own phrases (identical track_id / role
    # / span / ticks — so each keeps absBar == N and its per-bar seed).
    isolated_in = [
        p.model_copy(update={"notes": [n for n in p.notes if lo <= n.ticks < hi]})
        for p in s6
        if p.role == "drums" and any(lo <= n.ticks < hi for n in p.notes)
    ]
    iso, _ = humanize(isolated_in, inp.sf, inp.plan)

    assert drum_bar(full, n_bar), "bar N must have drum notes (non-vacuous)"
    assert drum_bar(iso, n_bar) == drum_bar(full, n_bar)
