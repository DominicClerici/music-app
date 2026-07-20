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

`pipeline_warnings(doc, trace)` (Layer-2's warn-marked L2-2) is **surfaced but
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
"""

from __future__ import annotations

import pytest

from trackgen.packs import resolve_pack
from trackgen.pipeline.trace import generate_trace
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
