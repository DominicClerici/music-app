"""§9.4 generator end-to-end normative goldens (PHASE_5 DoD 7, SESSION_08 T4).

The independent golden transcriber for the full part-generation loop. A test-only
thin driver loops `generate` over `[drums, bass, comping, pads]` for both worked
examples (this replicates the §8.1 orchestrator loop for testing — the real
orchestrator is Chunk 4 and is NOT built here). Every asserted value is
transcribed from PHASE_5 **§9.4** (post-§3.4 velocity + articulation) — never
read back off code output (ROADMAP §3 golden-value arbitration).

Velocity shift: pop +0.06, jazz −0.025. Articulation: pop ×0.904, jazz ×1.108
(clamped to gaps). §8.2 drum voice→track map, default durs.

ARBITRATED (golden-value arbitration, ROADMAP §3 — human sign-off): the pop
verse-1 bar-4 comping PITCHES were a wrong DERIVED doc value (no engine bug —
inherits the §9.3 pop-comping register). §9.4 and this golden were amended to the
engine's real output; the assertion below now pins the CORRECTED pitches
G♯3+B3+E4 (52,56,59 → 56,59,64). Durations/velocities/timing are voicing-
independent and unchanged.
  REPRODUCES unchanged: jazz head-1 bar 0 in full (ride/hats/bass/comping); pop
  verse-1 bar 4 drums (kick/snare/hats) + bass + the comping durations/
  velocities; and every whole-output invariant (sorted notes, within-span,
  velocities in (0,1], non-drum ≤ 71, push/ghost tags) + determinism + draws.
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
from trackgen.parts.generators import generate
from trackgen.parts.selection import select_patterns
from trackgen.parts.walker import walk
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementPlan,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    PhraseNote,
    SongForm,
)
from trackgen.seeds import Rng, derive, stream_rng, stream_seed

_BAR = 1920
_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")
_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


def _drive_full(
    params: dict[str, object],
) -> tuple[
    GenerationPlan, StylePack, SongForm, HarmonicPlan, ArrangementPlan, list[Phrase]
]:
    """Test-only orchestrator loop (§8.1) — NOT the Chunk-4 orchestrator."""
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
    sel = select_patterns(plan, sf, ap, pack, plan.seed.master, plan.seed.overrides)
    phrases: list[Phrase] = []
    for role in _ROLES:
        phrases += generate(
            role,
            ap,
            hp,
            sf,
            plan,
            pack,
            sel,
            master=plan.seed.master,
            overrides=plan.seed.overrides,
        )
    return plan, pack, sf, hp, ap, phrases


def _window(
    phrases: list[Phrase], track: str, start: int, end: int
) -> list[PhraseNote]:
    """Notes on `track` whose ticks fall in `[start, end)`, tick-sorted (local
    ticks are read via `n.ticks - start` at the call site)."""
    out: list[PhraseNote] = []
    for p in phrases:
        if p.track_id == track:
            out += [n for n in p.notes if start <= n.ticks < end]
    out.sort(key=lambda n: (n.ticks, n.midi if n.midi is not None else -1))
    return out


# =============================================================================
# §9.4 — JAZZ head-1 bar 0 (Dm9) — REPRODUCES IN FULL
# =============================================================================


def test_jazz_head1_bar0_full() -> None:
    """§9.4 jazz head-1 bar 0 (Dm9), post-§3.4 (velocity −0.025, articulation
    ×1.108 clamped): ride, hats, bass halves, Charleston comping F3+C4."""
    _plan, _pack, _sf, _hp, _ap, phrases = _drive_full(_JAZZ)

    ride = _window(phrases, "ride", 0, _BAR)
    assert [(n.ticks, n.velocity, n.duration_ticks) for n in ride] == [
        (0, 0.675, 240),
        (480, 0.695, 240),
        (720, 0.525, 240),
        (960, 0.675, 240),
        (1440, 0.695, 240),
        (1680, 0.525, 240),
    ]

    hats = _window(phrases, "hats", 0, _BAR)
    assert [(n.ticks, n.velocity) for n in hats] == [(480, 0.475), (1440, 0.475)]

    bass = _window(phrases, "bass", 0, _BAR)
    assert [(n.ticks, n.midi, n.velocity, n.duration_ticks) for n in bass] == [
        (0, 38, 0.695, 960),  # D2 root
        (960, 45, 0.655, 960),  # A2 fifth
    ]

    comping = _window(phrases, "comping", 0, _BAR)
    # Charleston F3+C4 @0 (dur 700×1.108=776 clamped to the 720 gap) and @720
    # (dur 400×1.108=443).
    assert [(n.ticks, n.midi, n.duration_ticks, n.velocity) for n in comping] == [
        (0, 53, 720, 0.595),  # F3
        (0, 60, 720, 0.595),  # C4
        (720, 53, 443, 0.525),
        (720, 60, 443, 0.525),
    ]


# =============================================================================
# §9.4 — POP verse-1 bar 4 (E) — drums + bass REPRODUCE
# =============================================================================


def test_pop_verse1_bar4_drums_and_bass() -> None:
    """§9.4 pop verse-1 bar 4 (ticks 7680-9600), governing chord E, post-§3.4
    (velocity +0.06, articulation ×0.904): kick/snare/hats/bass."""
    _plan, _pack, _sf, _hp, _ap, phrases = _drive_full(_POP)
    lo = 4 * _BAR  # 7680

    kick = _window(phrases, "kick", lo, lo + _BAR)
    assert [(n.ticks - lo, n.velocity) for n in kick] == [(0, 0.98), (960, 0.94)]

    snare = _window(phrases, "snare", lo, lo + _BAR)
    assert [(n.ticks - lo, n.velocity) for n in snare] == [(480, 0.91), (1440, 0.88)]

    hats = _window(phrases, "hats", lo, lo + _BAR)
    assert [n.velocity for n in hats] == [
        0.64,
        0.46,
        0.54,
        0.46,
        0.61,
        0.46,
        0.54,
        0.48,
    ]

    bass = _window(phrases, "bass", lo, lo + _BAR)
    # root quarters E2(40), dur 480×0.904 = 434.
    assert [(n.ticks - lo, n.midi, n.velocity, n.duration_ticks) for n in bass] == [
        (0, 40, 0.78, 434),
        (480, 40, 0.72, 434),
        (960, 40, 0.76, 434),
        (1440, 40, 0.72, 434),
    ]


def test_pop_verse1_bar4_comping_rhythm() -> None:
    """§9.4 pop verse-1 bar 4 comping RHYTHM — two hits @0 / @960, dur 814
    (900×0.904), velocities 0.68 / 0.64. (The pitches are the diverging value;
    see below.)"""
    _plan, _pack, _sf, _hp, _ap, phrases = _drive_full(_POP)
    lo = 4 * _BAR
    comping = _window(phrases, "comping", lo, lo + _BAR)
    onsets = sorted({(n.ticks - lo, n.duration_ticks, n.velocity) for n in comping})
    assert onsets == [(0, 814, 0.68), (960, 814, 0.64)]


def test_pop_verse1_bar4_comping_pitches() -> None:
    """§9.4 pop verse-1 bar 4 comping pitches G♯3+B3+E4 (56,59,64) — corrected
    golden (inherits the §9.3 pop-comping verse-1 E voicing)."""
    _plan, _pack, _sf, _hp, _ap, phrases = _drive_full(_POP)
    lo = 4 * _BAR
    comping = _window(phrases, "comping", lo, lo + _BAR)
    pitches = sorted({n.midi for n in comping if n.ticks == lo and n.midi is not None})
    assert pitches == [56, 59, 64]  # G♯3 B3 E4


# =============================================================================
# §8.2 — drum voice→track map + drum midi None — REPRODUCES
# =============================================================================


def test_drum_voice_track_map_and_null_midi() -> None:
    """§8.2 jazz drums: ride on the `ride` track, hats on `hats`; drum notes carry
    `midi = None` (Phase-7 timbres supply the trigger pitch)."""
    _plan, _pack, _sf, _hp, _ap, phrases = _drive_full(_JAZZ)
    drum_tracks = {p.track_id for p in phrases if p.role == "drums"}
    assert "ride" in drum_tracks and "hats" in drum_tracks
    for p in phrases:
        if p.role == "drums":
            for n in p.notes:
                assert n.midi is None


# =============================================================================
# Whole-output invariants (DoD 7) — REPRODUCES
# =============================================================================


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_whole_output_invariants(params: dict[str, object]) -> None:
    """PHASE_5 §13.7 — every Phrase's notes sorted `(ticks, midi)`; every note
    within its section span; velocities in (0, 1]; non-drum midi ≤ 71."""
    _plan, _pack, _sf, _hp, _ap, phrases = _drive_full(params)
    assert phrases
    for p in phrases:
        keys = [(n.ticks, n.midi if n.midi is not None else -1) for n in p.notes]
        assert keys == sorted(keys), (params, p.track_id)
        for n in p.notes:
            assert p.start_tick <= n.ticks < p.end_tick, (params, p.track_id, n.ticks)
            assert 0.0 < n.velocity <= 1.0, (params, p.track_id, n.velocity)
            if p.role != "drums":
                assert n.midi is not None and n.midi <= 71, (params, p.track_id, n)


def test_push_tags_present_where_expected() -> None:
    """DoD 7 — `push` tags on pushed comping hits (jazz jz_cp_3a 4& / pop pr_cp_3
    / pr_cp_4) and on the pushed pop bass hits (pr_bs_3 / pr_bs_4)."""
    _plan, _pack, _sf, _hp, _ap, jazz = _drive_full(_JAZZ)
    jazz_comp_push = [
        n for p in jazz if p.track_id == "comping" for n in p.notes if "push" in n.tags
    ]
    assert jazz_comp_push, "expected pushed jazz comping hits"

    _p2, _pk2, _sf2, _hp2, _ap2, pop = _drive_full(_POP)
    pop_comp_push = [
        n for p in pop if p.track_id == "comping" for n in p.notes if "push" in n.tags
    ]
    pop_bass_push = [
        n for p in pop if p.track_id == "bass" for n in p.notes if "push" in n.tags
    ]
    assert pop_comp_push, "expected pushed pop comping hits"
    assert pop_bass_push, "expected pushed pop bass hits"


def test_ghost_tags_present_on_walker_dead_notes() -> None:
    """DoD 7 — `ghost` tags on the jazz walker dead notes (§6.3 rule 6)."""
    _plan, _pack, _sf, _hp, _ap, jazz = _drive_full(_JAZZ)
    ghosts = [
        n for p in jazz if p.track_id == "bass" for n in p.notes if "ghost" in n.tags
    ]
    assert ghosts
    for n in ghosts:
        assert n.duration_ticks == 60


# =============================================================================
# Determinism + draw counts (DoD 7 / DoD 9)
# =============================================================================


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_generate_is_deterministic(params: dict[str, object]) -> None:
    """Repeated full generation is bit-identical."""
    a = _drive_full(params)[5]
    b = _drive_full(params)[5]
    assert a == b


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_generation_ignores_module_random_state(params: dict[str, object]) -> None:
    """DoD 9 — the pattern roles (drums / comping / pads / pattern-bass) consume
    ZERO generation draws and the walker draws only on its own seeded per-bar
    streams: perturbing the global `random` module state around generation cannot
    change the output."""
    random.seed(1)
    a = _drive_full(params)[5]
    random.seed(9_999_991)
    b = _drive_full(params)[5]
    assert a == b


class _CountingRandom(random.Random):
    def __init__(self, seed: int) -> None:
        super().__init__(seed)
        self.draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


def test_jazz_bass_walk_generation_draws_128() -> None:
    """DoD 7/9 — jazz bass generation routes to the walker, whose per-bar
    sub-streams draw exactly 128 times (the §9.2 total). `generate(bass)` invokes
    `walk` with the default factory over these same per-bar seeds, so this IS the
    generation-time bass draw count."""
    plan = generate_plan(_JAZZ)
    pack = resolve_pack("jazz")
    assert pack is not None and pack.forms is not None and pack.progressions is not None
    sf = form(plan, pack.forms)
    hp = harmony(
        plan,
        sf,
        pack.progressions,
        stream_rng(plan.seed.master, plan.seed.overrides, "harmony"),
    )
    ap = arrange(plan, sf, pack, Rng(0))

    walk_seed = derive(
        stream_seed(plan.seed.master, plan.seed.overrides, "bass"), "walk"
    )
    counters: list[_CountingRandom] = []

    def factory(abs_bar: int) -> Rng:
        shim = _CountingRandom(derive(walk_seed, f"bar:{abs_bar}"))
        counters.append(shim)
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
    assert sum(c.draws for c in counters) == 128
