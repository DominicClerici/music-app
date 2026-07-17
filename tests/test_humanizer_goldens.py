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
    """§7.2: ride bar 0 → 0/480/**827**/960/1440/**1787** — downbeats unmoved, the
    two offbeats (720, 1680) swung, 0 offset."""
    zj = _jazz_zero_jitter()
    ride = track_window(zj, "ride", 0, BAR)
    assert [n.ticks for n in ride] == [0, 480, 827, 960, 1440, 1787]


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


def test_jazz_head1_bar0_and_of_4_swing() -> None:
    """§7.2: the and-of-4 (grid 1680) swings to **1787** ("walker ghosts at
    and-of-4 swing to 1787"). Bar 0 of head-1 is a two-feel bar (bass halves at
    0/960), so its and-of-4 is carried by the ride; the identical 1680→1787 swing
    mapping the doc pins is asserted here on the zero-jitter output."""
    zj = _jazz_zero_jitter()
    at_1787 = [(p.role, p.track_id) for p in zj for n in p.notes if n.ticks == 1787]
    assert at_1787, "and-of-4 grid 1680 must land at 1787"


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
    "params,expected", [(POP, 10198), (JAZZ, 5088)], ids=["pop", "jazz"]
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


def test_per_role_bar_isolation() -> None:
    """§5.8: a bar's humanized output depends only on its own `(role, absBar)`
    sub-stream. Perturbing a drum note in a **different** bar changes that bar's
    output but leaves the target bar (drums bar 5) byte-identical — its RNG is
    self-seeded `derive(derive(humanize, role), f"bar:{absBar}")`."""
    inp = drive(JAZZ)
    s6 = stage6_final(inp)

    def drum_bar(phrases: Any, bar: int) -> list[tuple[Any, ...]]:
        lo, hi = bar * BAR, (bar + 1) * BAR
        return sorted(
            (p.track_id, n.ticks, n.midi, n.duration_ticks, n.velocity, tuple(n.tags))
            for p in phrases
            if p.role == "drums"
            for n in p.notes
            if lo <= n.ticks < hi
        )

    base_out, _ = humanize(s6, inp.sf, inp.plan)

    # Perturb one drum note's velocity in bar 30, keeping the note (and its grid
    # tick) — so no note is added/removed and only that bar's stream is touched.
    perturbed: list[Any] = []
    changed = False
    for phrase in s6:
        if phrase.role == "drums" and not changed:
            new_notes = []
            for note in phrase.notes:
                if not changed and 30 * BAR <= note.ticks < 31 * BAR:
                    new_notes.append(
                        note.model_copy(
                            update={
                                "velocity": round(
                                    min(1.0, note.velocity * 0.5 + 0.01), 3
                                )
                            }
                        )
                    )
                    changed = True
                else:
                    new_notes.append(note)
            perturbed.append(phrase.model_copy(update={"notes": new_notes}))
        else:
            perturbed.append(phrase)
    assert changed, "expected a drum note in bar 30 to perturb"

    pert_out, _ = humanize(perturbed, inp.sf, inp.plan)

    # The perturbation genuinely moved its own bar (non-vacuous) …
    assert drum_bar(base_out, 30) != drum_bar(pert_out, 30)
    # … but the target bar 5 is untouched (self-seeded per-bar stream).
    assert drum_bar(base_out, 5) == drum_bar(pert_out, 5)
