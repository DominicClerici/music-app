"""PHASE_8 §8.2 smoke matrix + 300-seed reference sweep (DoD §14.6; SESSION_18 T4).

Two independent matrices, both gating on **Layers 1-2** via
`quality/suite.py::validate_pipeline(doc, trace) == []` (empty == valid; the
module docstring names it "the gate used by CI/smoke"):

1. **Smoke matrix** (§8.2): both reference packs × **every supported mood** ×
   the three pinned length buckets (60 / 180 / 480 s) × 5 seeds.

     pop_rock : 11 moods × 3 lengths × 5 seeds = 165
     jazz     : 10 moods × 3 lengths × 5 seeds = 150
     total    : 315 cells

   (SESSION_18 §3 T4 prints this as "2 × (11+10) × 3 × 5 = 630", which
   double-counts the pack dimension — the mood counts are already per-pack, so
   they sum rather than multiply by 2. The *dimensions* are what §8.2 pins
   ("every pack × supported mood × 3 length buckets × 5 seeds"), and per the
   ROADMAP §3 golden-value arbitration rule the algorithm text wins over a
   printed sample number. The exhausted product is 315.)

2. **300-seed reference sweep** (§8.2, decision S18-4): 300 seeds × the 2
   reference packs at **default params** (no mood, no `maxLengthSec` — the pack
   and engine defaults apply) = 600 cells. §8.2 bounds per-cell failure below
   ~1 % by the rule of three; a "cell" here is `(pack, seed)`, so 300 clean
   seeds per pack is the interval the rule needs.

The moods are **derived from the pack** (`resolve_pack(...).interpreter
.supported_moods`), never hardcoded, so a pack gaining or losing a mood widens
or narrows the matrix automatically rather than silently under-testing.

`pipeline_warnings(doc, trace)` (Layer-2's warn-marked L2-2, plus its
`L2-1-SKIP:` unmeasurable-role diagnostics since S23-1) is **surfaced but
never gating** — PHASE_8 §8.1 pins Layer 2 as "warn by default, fail where
marked", and only the fail-marked L2-1 lives inside `validate_pipeline`. Layer 3
is batch-only / warn-only and `styles/<pack>/calibration.yaml` does not exist
yet (it lands in C5), so nothing here reads or gates on it.

Seeds are **pinned literals** (smoke) or a **pinned deterministic sequence**
(sweep) — never drawn, per ROADMAP invariant 5. The 480 s bucket is the longest
render this repo exercises anywhere; it is deliberately included at full width.

`test_matrix_non_vacuous` asserts both matrices' **exact** expected sizes,
recomputed from the pack-derived dimensions, plus non-degeneracy — so a silent
shrink of any dimension fails loudly (ROADMAP §3, no silent caps).

`test_long_bucket_expands_form` / `test_long_bucket_reaches_pack_ceiling` close
the complementary gap: the matrix above proves 480 s renders are *valid*, not
that the engine *responded* to `maxLengthSec=480` at all. A silent cap would
leave all 916 cells green. See those tests for the shape of the guard.
"""

from __future__ import annotations

import pytest

from trackgen.packs import resolve_pack
from trackgen.pipeline.trace import GenerationTrace, generate_trace
from trackgen.quality.suite import pipeline_warnings, validate_pipeline
from trackgen.seeds import to_base36

# The two reference packs (§8.2). The three new packs land in C6-C8 and join
# this matrix then; `_PACKS` is the only edit that needs.
_PACKS: tuple[str, ...] = ("pop_rock", "jazz")

# The three pinned length buckets (§8.2). 480 s is the longest render in the
# repo — kept at full width deliberately, not sampled.
_LENGTHS: tuple[int, ...] = (60, 180, 480)

# Five pinned base36 u64 seeds for the smoke matrix. Literals, so the matrix is
# byte-stable forever and a failure is reproducible from the test id alone.
_SMOKE_SEEDS: tuple[str, ...] = ("1", "7f", "z9q", "1k3p", "2mnq8h")

# The 300-seed sweep (S18-4). Deterministically derived from a pinned integer
# range rather than 300 literals; `stream_seed` hashes the master through
# SHA-256 per stream, so consecutive masters decorrelate completely.
_SWEEP_SEED_COUNT = 300
_SWEEP_SEEDS: tuple[str, ...] = tuple(
    to_base36(i) for i in range(1, _SWEEP_SEED_COUNT + 1)
)


# --- long-form response (the 480 s bucket) -----------------------------------
#
# The matched pair the long-form guard compares: every cell is rendered at both
# buckets with everything else held identical, so the only varying input is
# `maxLengthSec`. Both must be members of `_LENGTHS` (asserted below).
_LONG_SEC = 480
_REFERENCE_SEC = 180

# Every supported mood must have **at least this many** of the five pinned seeds
# render strictly more bars at 480 s than at 180 s. Measured floor: jazz grows on
# 5/5 seeds for all 10 moods; pop_rock grows on 5/5 for six moods and 1/5 for the
# five high-tempo ones (aggressive, energetic, happy, tense, triumphant), whose
# 180 s render already sits at the template's authored repeat ceiling. 1 is the
# observed minimum over all 21 (pack, mood) pairs — a floor, not an equality, so
# more growth is fine and less fails.
_MIN_GROWN_SEEDS = 1

# The pinned seed used for the per-pack ceiling probe. Of the five smoke seeds it
# is the one that drives both packs to their longest 480 s render, so it is the
# tightest single-seed witness available.
_CEILING_SEED = "1k3p"

# Per-pack floor (seconds) on the LONGEST 480 s render across every supported
# mood at `_CEILING_SEED`. Measured: pop_rock 356.6 s, jazz 480.0 s (exactly the
# budget). Floors carry ~4 % headroom below the measurement.
#
# **pop_rock cannot fill an 480 s budget and is not expected to.** Form length is
# bounded above by each form template's authored repeat counts, not by
# `maxLengthSec`, and pop_rock's templates top out at 104 bars. That is a pinned
# data property, not a silent cap — do not "fix" it and do not raise this floor
# to 480. Logged as a caveat.
_CEILING_FLOOR_SEC: dict[str, float] = {"pop_rock": 340.0, "jazz": 470.0}

_PPQ = 480


def _rendered_sec(trace: GenerationTrace) -> float:
    """Musical length of a rendered trace in seconds, from the form's bar count.

    Mirrors `form/stage.py`'s `ticks_per_bar` derivation (PPQ 480) and the
    interpreter's `max_length_ticks = floor(sec * bpm * 8)`, i.e. `bpm * 8`
    ticks per second. Read off `song_form`/`plan` rather than the document's
    note stream so an arrangement that leaves a tail silent still counts."""
    ts = trace.plan.time_signature
    ticks_per_bar = ts.numerator * (_PPQ * 4 // ts.denominator)
    return trace.song_form.total_bars * ticks_per_bar / (trace.plan.tempo_bpm * 8)


def _supported_moods(pack_id: str) -> tuple[str, ...]:
    """The pack's declared supported moods, sorted for a stable matrix order."""
    resolved = resolve_pack(pack_id)
    assert resolved is not None, pack_id
    assert resolved.interpreter is not None, pack_id
    return tuple(sorted(resolved.interpreter.supported_moods))


# --- matrix construction -----------------------------------------------------

_SmokeCell = tuple[str, str, int, str]
_SweepCell = tuple[str, str]

_SMOKE_MATRIX: tuple[_SmokeCell, ...] = tuple(
    (pack, mood, length, seed)
    for pack in _PACKS
    for mood in _supported_moods(pack)
    for length in _LENGTHS
    for seed in _SMOKE_SEEDS
)

_SWEEP_MATRIX: tuple[_SweepCell, ...] = tuple(
    (pack, seed) for pack in _PACKS for seed in _SWEEP_SEEDS
)

_MOOD_MATRIX: tuple[tuple[str, str], ...] = tuple(
    (pack, mood) for pack in _PACKS for mood in _supported_moods(pack)
)
_MOOD_IDS = [f"{pack}-{mood}" for pack, mood in _MOOD_MATRIX]

_SMOKE_IDS = [
    f"{pack}-{mood}-{length}s-{seed}" for pack, mood, length, seed in _SMOKE_MATRIX
]
_SWEEP_IDS = [f"{pack}-seed{seed}" for pack, seed in _SWEEP_MATRIX]


def _gate(params: dict[str, object], cell: object) -> list[str]:
    """Render `params`, assert the Layers 1-2 gate is clean, return the soft
    warnings (never gating). The returned list is the caller's to surface."""
    trace = generate_trace(params)
    failures = validate_pipeline(trace.document, trace)
    assert failures == [], (cell, failures)
    return pipeline_warnings(trace.document, trace)


# --- the smoke matrix --------------------------------------------------------


@pytest.mark.parametrize(
    ("pack", "mood", "length", "seed"), _SMOKE_MATRIX, ids=_SMOKE_IDS
)
def test_smoke_cell(pack: str, mood: str, length: int, seed: str) -> None:
    """Every (pack, supported mood, length bucket, seed) renders and passes the
    Layers 1-2 gate. Soft L2-2 warnings are printed, never failed on."""
    cell = (pack, mood, length, seed)
    warnings = _gate(
        {
            "styleFamily": pack,
            "mood": mood,
            "maxLengthSec": length,
            "seed": seed,
        },
        cell,
    )
    if warnings:
        print(f"smoke warnings {cell}: {warnings}")


# --- the 300-seed reference sweep --------------------------------------------


@pytest.mark.parametrize(("pack", "seed"), _SWEEP_MATRIX, ids=_SWEEP_IDS)
def test_reference_sweep_cell(pack: str, seed: str) -> None:
    """300 seeds × both reference packs at **default params** pass the same
    Layers 1-2 gate — §8.2's rule-of-three bound on per-cell failure.

    `mood` and `maxLengthSec` are omitted so the pack default mood and the
    engine default length apply; the seed is the only varying dimension."""
    cell = (pack, seed)
    warnings = _gate({"styleFamily": pack, "seed": seed}, cell)
    if warnings:
        print(f"sweep warnings {cell}: {warnings}")


# --- the 480 s bucket actually renders long form ------------------------------
#
# The smoke matrix asserts every 480 s cell is *valid*; it never asserts the
# engine *responded* to `maxLengthSec=480`. If long lengths were silently capped
# or ignored, all 916 cells above would stay green — `test_matrix_non_vacuous`
# guards the matrix's dimensions, not the engine's response to them. These two
# tests close that gap (ROADMAP §3, no silent caps).
#
# Why a *relative* comparison rather than a per-cell absolute length: a cell's
# achievable length is bounded above by its form template's authored repeat
# counts, so an absolute per-cell floor would be a pack-and-mood-specific
# golden table that fails on legitimate authoring changes. Comparing 480 s
# against 180 s at matched (pack, mood, seed) isolates `maxLengthSec` as the
# only varying input, and the per-pack ceiling probe below adds the one
# absolute measurement that a purely relative test cannot catch (a cap that
# scales *both* buckets down together).


@pytest.mark.parametrize(("pack", "mood"), _MOOD_MATRIX, ids=_MOOD_IDS)
def test_long_bucket_expands_form(pack: str, mood: str) -> None:
    """At matched (pack, mood, seed), the 480 s render is never shorter than the
    180 s one, and at least `_MIN_GROWN_SEEDS` of the five seeds is strictly
    longer — so a collapse of the 480 s bucket onto 180 s form sizes fails.

    Also asserts neither bucket overshoots its own budget, so the guard cannot
    be satisfied by an engine that simply ignores `maxLengthSec` upward."""
    grown = 0
    observed: list[tuple[str, int, int]] = []
    for seed in _SMOKE_SEEDS:
        base = {"styleFamily": pack, "mood": mood, "seed": seed}
        short = generate_trace({**base, "maxLengthSec": _REFERENCE_SEC})
        long = generate_trace({**base, "maxLengthSec": _LONG_SEC})
        cell = (pack, mood, seed)

        # The parameter reaches the plan at all (stage-1 arithmetic).
        assert long.plan.max_length_ticks > short.plan.max_length_ticks, cell

        short_bars = short.song_form.total_bars
        long_bars = long.song_form.total_bars
        # Monotonic in the budget: more time may never yield less music.
        assert long_bars >= short_bars, (cell, short_bars, long_bars)
        # Neither bucket exceeds the budget it was given.
        assert _rendered_sec(short) <= _REFERENCE_SEC, (cell, _rendered_sec(short))
        assert _rendered_sec(long) <= _LONG_SEC, (cell, _rendered_sec(long))

        if long_bars > short_bars:
            grown += 1
        observed.append((seed, short_bars, long_bars))

    assert grown >= _MIN_GROWN_SEEDS, (pack, mood, grown, observed)
    # The mood's best 480 s form strictly beats its best 180 s form — the same
    # claim stated on the maxima, so a mood whose growth all collapsed onto one
    # lucky seed still has to move the ceiling.
    assert max(o[2] for o in observed) > max(o[1] for o in observed), (
        pack,
        mood,
        observed,
    )


@pytest.mark.parametrize("pack", _PACKS, ids=list(_PACKS))
def test_long_bucket_reaches_pack_ceiling(pack: str) -> None:
    """The pack's longest 480 s render at the pinned ceiling seed clears a
    measured absolute floor — the check a purely relative comparison misses.

    Measured today: pop_rock 356.6 s, jazz 480.0 s (exactly the budget).
    pop_rock's shortfall is expected and pinned in `_CEILING_FLOOR_SEC`'s note:
    form length is capped by the templates' authored repeat counts, not by
    `maxLengthSec`."""
    lengths = {
        mood: _rendered_sec(
            generate_trace(
                {
                    "styleFamily": pack,
                    "mood": mood,
                    "maxLengthSec": _LONG_SEC,
                    "seed": _CEILING_SEED,
                }
            )
        )
        for mood in _supported_moods(pack)
    }
    longest = max(lengths.values())
    assert longest >= _CEILING_FLOOR_SEC[pack], (pack, longest, lengths)
    assert longest <= _LONG_SEC, (pack, longest, lengths)
    print(f"480 s ceiling — {pack}: longest {longest:.2f} s of {lengths}")


# --- non-vacuity -------------------------------------------------------------


def test_matrix_non_vacuous() -> None:
    """Both matrices are the exact expected size and non-degenerate.

    Sizes are recomputed from the pack-derived dimensions and asserted against
    the built matrices, so a silent shrink anywhere (a mood dropped from a pack,
    a length bucket removed, a seed list truncated) fails loudly rather than
    quietly shrinking coverage (ROADMAP §3)."""
    # --- dimensions are themselves non-degenerate ---------------------------
    assert len(_PACKS) == 2, _PACKS
    assert len(set(_PACKS)) == len(_PACKS), _PACKS
    assert _LENGTHS == (60, 180, 480), _LENGTHS
    assert len(_SMOKE_SEEDS) == 5, _SMOKE_SEEDS
    assert len(set(_SMOKE_SEEDS)) == 5, _SMOKE_SEEDS
    assert len(_SWEEP_SEEDS) == _SWEEP_SEED_COUNT == 300, len(_SWEEP_SEEDS)
    assert len(set(_SWEEP_SEEDS)) == 300, len(set(_SWEEP_SEEDS))

    # --- the smoke matrix ---------------------------------------------------
    per_pack: list[tuple[str, int, int]] = []
    expected_smoke = 0
    for pack in _PACKS:
        moods = _supported_moods(pack)
        assert len(moods) == len(set(moods)) >= 2, (pack, moods)
        cells = len(moods) * len(_LENGTHS) * len(_SMOKE_SEEDS)
        expected_smoke += cells
        per_pack.append((pack, len(moods), cells))

    # The pinned §8.2 dimensions today: pop_rock 11 moods, jazz 10 (S18 §2).
    assert per_pack == [("pop_rock", 11, 165), ("jazz", 10, 150)], per_pack
    assert expected_smoke == 315, expected_smoke
    assert len(_SMOKE_MATRIX) == expected_smoke, (len(_SMOKE_MATRIX), expected_smoke)
    assert len(set(_SMOKE_MATRIX)) == expected_smoke, len(set(_SMOKE_MATRIX))
    assert len(set(_SMOKE_IDS)) == expected_smoke, len(set(_SMOKE_IDS))

    # Every dimension is actually exercised by the built product.
    assert {c[0] for c in _SMOKE_MATRIX} == set(_PACKS)
    assert {c[2] for c in _SMOKE_MATRIX} == set(_LENGTHS)
    assert {c[3] for c in _SMOKE_MATRIX} == set(_SMOKE_SEEDS)
    for pack in _PACKS:
        assert {c[1] for c in _SMOKE_MATRIX if c[0] == pack} == set(
            _supported_moods(pack)
        ), pack
    # 480 s is the never-before-rendered bucket: assert it is present at full
    # width, so it can never be quietly dropped to make the suite pass.
    assert sum(1 for c in _SMOKE_MATRIX if c[2] == 480) == 105

    # --- the long-form guard ------------------------------------------------
    # Its dimensions are pinned too, so the guard cannot be quietly narrowed to
    # a mood or a pack that happens to grow.
    assert _LONG_SEC == 480 and _REFERENCE_SEC == 180, (_LONG_SEC, _REFERENCE_SEC)
    assert _LONG_SEC in _LENGTHS and _REFERENCE_SEC in _LENGTHS
    assert _CEILING_SEED in _SMOKE_SEEDS, _CEILING_SEED
    assert _MIN_GROWN_SEEDS >= 1, _MIN_GROWN_SEEDS
    assert set(_CEILING_FLOOR_SEC) == set(_PACKS), _CEILING_FLOOR_SEC
    assert all(0 < floor <= _LONG_SEC for floor in _CEILING_FLOOR_SEC.values())
    assert len(_MOOD_MATRIX) == len(set(_MOOD_MATRIX)) == 21, len(_MOOD_MATRIX)
    assert len(set(_MOOD_IDS)) == 21, len(set(_MOOD_IDS))
    assert {m[0] for m in _MOOD_MATRIX} == set(_PACKS)
    for pack in _PACKS:
        assert {m[1] for m in _MOOD_MATRIX if m[0] == pack} == set(
            _supported_moods(pack)
        ), pack

    # --- the 300-seed sweep -------------------------------------------------
    expected_sweep = len(_PACKS) * _SWEEP_SEED_COUNT
    assert expected_sweep == 600, expected_sweep
    assert len(_SWEEP_MATRIX) == expected_sweep, (len(_SWEEP_MATRIX), expected_sweep)
    assert len(set(_SWEEP_MATRIX)) == expected_sweep, len(set(_SWEEP_MATRIX))
    assert len(set(_SWEEP_IDS)) == expected_sweep, len(set(_SWEEP_IDS))
    for pack in _PACKS:
        assert sum(1 for c in _SWEEP_MATRIX if c[0] == pack) == 300, pack

    # Total renders the two matrices contribute to the suite.
    assert expected_smoke + expected_sweep == 915

    print(
        "smoke matrix — per-pack (pack, moods, cells):",
        per_pack,
        "| smoke cells:",
        expected_smoke,
        "| sweep cells:",
        expected_sweep,
        "| length buckets:",
        _LENGTHS,
    )
