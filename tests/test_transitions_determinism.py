"""PHASE_6 §11.7 determinism + DoD-9 stage-6 property subset (Task T4).

Two proofs plus a property matrix over the **real** stage-6 pipeline:

1. **Repeated-run bit-identity** — same params → identical `Phrase[]` through
   stage 6 (the definitive reproducibility proof).
2. **Sub-stream isolation** — every per-unit mutation draw is a pure function of
   that unit's own `derive(derive(derive(transitions,"mutate"),role),
   f"bar:{unitStartAbsBar}")` seed: independently re-deriving each unit's seed
   and replaying its `weighted_choice` reproduces exactly the operator the engine
   dispatched (the PHASE_5 walker per-bar-seed precedent). The devices stream is
   a single timeline-ordered RNG (§3.8), so its reproducibility is the run-to-run
   identity of (1) plus the re-derivable devices seed asserted here.
3. **Property subset** (DoD 9, stage-6 slice) across **every registered pack** ×
   supported moods × lengths × seeds (PHASE_8 §14.9): fills only in legal fill
   bars; no groove drum event inside a rendered fill window; crash suppression
   for postchorus/breakdown (and a crash present at every other section entry);
   non-drum `midi` untouched
   (sub-multiset, ≤ 71 ceiling); backbeat-class snares never removed/moved by
   mutation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from _packmatrix import (
    LENGTHS_RENDER,
    PACKS,
    SEEDS_25,
    supported_moods,
    total_moods,
)
from _stage6_driver import (
    JAZZ,
    POP,
    Stage6Inputs,
    drive,
    stage6_final,
    stage6_passes,
    track_window,
)
from trackgen.seeds import (
    Rng,
    derive,
    stream_seed,
    weighted_choice,
)
from trackgen.transitions import mutation as mutation_mod
from trackgen.transitions._common import BAR
from trackgen.transitions.ending import find_t_last

_GROOVE_EXCLUDE = frozenset({"fill", "var", "crash", "hold"})


# =============================================================================
# 1 — repeated-run bit-identity through stage 6
# =============================================================================


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_stage6_repeated_run_identity(params: dict[str, object]) -> None:
    """§11.7: two independent drives + real stage-6 runs are bit-identical."""
    a = [p.model_dump() for p in stage6_final(drive(params))]
    b = [p.model_dump() for p in stage6_final(drive(params))]
    assert a == b


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_stage6_rerun_on_same_inputs_identity(params: dict[str, object]) -> None:
    """§11.7: stage 6 is a pure function of its inputs — running it twice on the
    same generated `Phrase[]` yields identical output (and leaves the input
    untouched, since frozen Phrases are rebuilt, never mutated)."""
    inp = drive(params)
    before = [p.model_dump() for p in inp.phrases]
    a = [p.model_dump() for p in stage6_final(inp)]
    b = [p.model_dump() for p in stage6_final(inp)]
    assert a == b
    assert [p.model_dump() for p in inp.phrases] == before  # input not mutated.


# =============================================================================
# 2 — per-unit sub-stream isolation
# =============================================================================


def _independent_unit_draws(
    inp: Stage6Inputs,
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Re-derive every mutation unit's own sub-stream seed and replay its draw
    (§3.8) using only that seed + the pack table — no engine dispatch. Returns
    the `(drums, comping)` lists of `(unit_start_bar, op)` for non-`none` draws."""
    assert inp.pack.transitions is not None
    mutate_seed = derive(
        stream_seed(inp.plan.seed.master, inp.plan.seed.overrides, "transitions"),
        "mutate",
    )
    out: dict[str, list[tuple[int, str]]] = {"drums": [], "comping": []}
    for role, table, unit_bars in (
        ("drums", inp.pack.transitions.mutation.drums, 2),
        ("comping", inp.pack.transitions.mutation.comping, 8),
    ):
        if table is None:
            continue
        names = list(table.keys())
        weights = list(table.values())
        role_seed = derive(mutate_seed, role)
        for _sec, ub, _lo, _hi in mutation_mod._units(
            inp.sf, mutation_mod._active_sections(inp.ap, role), unit_bars
        ):
            rng = Rng(derive(role_seed, f"bar:{ub}"))
            op = weighted_choice(names, weights, rng) if len(names) >= 2 else names[0]
            if op != "none":
                out[role].append((ub, op))
    return sorted(out["drums"]), sorted(out["comping"])


def _engine_dispatched_ops(
    inp: Stage6Inputs,
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """The ops the engine actually dispatched per unit, captured by wrapping the
    operator tables the `mutate` driver reads (manual save/restore)."""
    fired: list[tuple[int, str]] = []

    def wrap(name: str, fn: Any) -> Any:
        def recorded(b: Any, s: Any, lo: int, hi: int, fbt: int, *rest: Any) -> None:
            fired.append((lo // BAR, name))
            fn(b, s, lo, hi, fbt, *rest)

        return recorded

    orig_drum = mutation_mod._DRUM_OPS
    orig_comp = mutation_mod._COMPING_OPS
    mutation_mod._DRUM_OPS = {k: wrap(k, v) for k, v in orig_drum.items()}
    mutation_mod._COMPING_OPS = {k: wrap(k, v) for k, v in orig_comp.items()}
    try:
        stage6_passes(inp)
    finally:
        mutation_mod._DRUM_OPS = orig_drum
        mutation_mod._COMPING_OPS = orig_comp
    drums = sorted(x for x in fired if x[1] in orig_drum)
    comping = sorted(x for x in fired if x[1] in orig_comp)
    return drums, comping


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_per_unit_substream_isolation(params: dict[str, object]) -> None:
    """§11.7: the engine's per-unit dispatch equals the independently-reconstructed
    per-unit draws — each unit's operator is a pure function of only its own
    sub-stream seed, so a skipped/no-op unit can never shift another's outcome."""
    inp = drive(params)
    assert _engine_dispatched_ops(inp) == _independent_unit_draws(inp)


def test_single_unit_seed_reproduces_in_isolation() -> None:
    """§11.7: regenerating a single unit's RNG in isolation reproduces its draw
    (bit-for-bit) — the per-unit seed derivation is stable and standalone."""
    inp = drive(POP)
    assert inp.pack.transitions is not None
    table = inp.pack.transitions.mutation.drums
    assert table is not None
    names, weights = list(table.keys()), list(table.values())
    mutate_seed = derive(
        stream_seed(inp.plan.seed.master, inp.plan.seed.overrides, "transitions"),
        "mutate",
    )
    role_seed = derive(mutate_seed, "drums")
    # Unit @8 (pop) draws hat_lift (§7.1); reconstructing it twice agrees.
    seed = derive(role_seed, "bar:8")
    first = weighted_choice(names, weights, Rng(seed))
    second = weighted_choice(names, weights, Rng(seed))
    assert first == second == "hat_lift"


def test_devices_seed_is_rederivable() -> None:
    """§3.8: the devices stream seed is `derive(derive(transitions_seed,
    "devices"))` — pinning it here documents the single-stream anchor whose
    timeline-ordered replay (with run-to-run identity) is the devices
    reproducibility guarantee."""
    inp = drive(POP)
    transitions_seed = stream_seed(
        inp.plan.seed.master, inp.plan.seed.overrides, "transitions"
    )
    # The PHASE_1 §5.6 / §3.8 pinned golden vectors.
    assert transitions_seed == 17897360909067852929
    assert derive(transitions_seed, "devices") == 11162692426947704816
    assert derive(transitions_seed, "mutate") == 2353238394870311228
    assert derive(derive(transitions_seed, "mutate"), "drums") == 10947905152221053268


# =============================================================================
# 3 — property subset (DoD 9, stage-6 slice)
# =============================================================================


def _matrix() -> list[dict[str, object]]:
    """Every registered pack × supported moods × PHASE_6 §11.9's 3 lengths ×
    25 seeds (PHASE_8 §14.9). Dimensions come from `_packmatrix`, the single
    place the pack dimension is defined; §14.9's "× lengths" is each phase's own
    pinned dimension (S23-3), so the render-level suites keep `LENGTHS_RENDER`
    rather than the 39-value plan grid."""
    out: list[dict[str, object]] = []
    for style in PACKS:
        for mood in supported_moods(style):
            for length in LENGTHS_RENDER:
                for seed in SEEDS_25:
                    params: dict[str, object] = {
                        "styleFamily": style,
                        "mood": mood,
                        "seed": seed,
                    }
                    if length is not None:
                        params["maxLengthSec"] = length
                    out.append(params)
    return out


def _legal_fill_bars(sf: Any) -> set[int]:
    """§3.1: section fill bars (last bar of each non-final section) ∪ interior
    phrase fill bars (the bar before each non-first phrase start)."""
    bars: set[int] = set()
    secs = sf.sections
    for i in range(len(secs) - 1):
        bars.add(secs[i].start_bar + secs[i].length_bars - 1)
    for section in secs:
        bar = section.start_bar
        for idx, phrase in enumerate(section.phrases):
            if idx > 0:
                bars.add(bar - 1)
            bar += phrase.bars
    return bars


@pytest.mark.parametrize(
    "params",
    _matrix(),
    ids=lambda p: (
        f"{p['styleFamily']}-{p.get('mood')}-{p.get('maxLengthSec')}-{p['seed']}"
    ),
)
def test_stage6_property_subset(params: dict[str, object]) -> None:
    """DoD 9 (stage-6 slice) over the pack × mood × length × seed matrix."""
    inp = drive(params)
    post_6b, final = stage6_passes(inp)
    sf = inp.sf
    legal = _legal_fill_bars(sf)
    t_last_bar = find_t_last(inp.hp) // BAR

    # (A) Every fill-tagged drum note sits in a legal fill bar.
    for p in final:
        if p.role == "drums":
            for n in p.notes:
                if "fill" in n.tags:
                    assert n.ticks // BAR in legal, (params, n.ticks)

    # (B) No groove drum event survives inside a rendered fill window: in any bar
    # holding a fill, every groove (non fill/var/crash/hold) hit is before the
    # window (beat-floor of the earliest fill event in that bar).
    for p in final:
        if p.role != "drums":
            continue
        by_bar: dict[int, list[Any]] = {}
        for n in p.notes:
            by_bar.setdefault(n.ticks // BAR, []).append(n)
        for notes in by_bar.values():
            fill_pos = [n.ticks % BAR for n in notes if "fill" in n.tags]
            if not fill_pos:
                continue
            window_lo = (min(fill_pos) // 480) * 480
            for n in notes:
                if not (_GROOVE_EXCLUDE & set(n.tags)):
                    assert n.ticks % BAR < window_lo, (params, p.track_id, n.ticks)

    # (C) Crash suppression: no crash at a postchorus/breakdown entry; a crash IS
    # present at every other section entry before T_last (non-vacuous where the
    # reference forms have no suppression class).
    secs = sf.sections
    for i in range(len(secs) - 1):
        entered = secs[i + 1]
        tick = entered.start_bar * BAR
        crash_here = track_window(final, "crash", tick, tick + 1)
        if entered.type in ("postchorus", "breakdown"):
            assert crash_here == [], (params, entered.id)
        elif entered.start_bar < t_last_bar:
            assert len(crash_here) == 1, (params, entered.id)

    # (D) Non-drum midi untouched: the final pitched-track midi multiset is a
    # sub-multiset of the pre-stage-6 one (no re-pitch, no new pitch), ≤ 71.
    for role in ("bass", "comping", "pads"):
        initial = Counter(
            n.midi for p in inp.phrases if p.role == role for n in p.notes
        )
        emitted = Counter(n.midi for p in final if p.role == role for n in p.notes)
        for midi, count in emitted.items():
            assert midi is not None and midi <= 71, (params, role, midi)
            assert initial[midi] >= count, (params, role, midi)

    # (E) Mutation never removes or moves a backbeat-class snare (velocity ≥ 0.7
    # at in-bar back2/back4): every such hit after 6b survives 6c unchanged.
    def backbeats(phrases: list[Any]) -> set[tuple[int, float]]:
        return {
            (n.ticks, round(n.velocity, 3))
            for p in phrases
            if p.track_id == "snare"
            for n in p.notes
            if n.velocity >= 0.7
            and n.ticks % BAR in (480, 1440)
            and not (_GROOVE_EXCLUDE & set(n.tags))
        }

    assert backbeats(post_6b) <= backbeats(final), params


def test_matrix_non_vacuous() -> None:
    """The stage-6 subset matrix is the exact expected size and covers every
    pack.

    Dimensions are recomputed from pack data (not restated), so a silent shrink
    — a pack dropped from the registry, a mood lost, a length bucket or seed
    truncated — fails loudly rather than quietly narrowing coverage (ROADMAP §3).
    `test_phase6_property.py` parameterizes off this same `_matrix()`, so this
    guards both Phase-6 suites."""
    assert len(PACKS) >= 5, PACKS
    assert LENGTHS_RENDER == (None, 180, 240), LENGTHS_RENDER
    assert len(SEEDS_25) == len(set(SEEDS_25)) == 25, SEEDS_25

    expected = total_moods() * len(LENGTHS_RENDER) * len(SEEDS_25)

    matrix = _matrix()
    assert len(matrix) == expected, (len(matrix), expected)
    assert {p["styleFamily"] for p in matrix} == set(PACKS)
    keys = {tuple(sorted(p.items(), key=str)) for p in matrix}
    assert len(keys) == len(matrix), "duplicate matrix cell"
