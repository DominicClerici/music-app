"""Self-tests for the shared matrix dimensions (`tests/_packmatrix.py`).

These pin the *dimensions* themselves, so a silent shrink of the pack, mood,
length or seed axis fails here rather than quietly reducing every property
suite's coverage (PHASE_8 §14 item 9; ROADMAP §3's no-silent-caps discipline).
"""

from __future__ import annotations

import pytest

from _packmatrix import (
    LENGTHS_PLAN,
    LENGTHS_RENDER,
    PACKS,
    SEEDS_25,
    build_plan,
    cached_pack,
    pack_mood_pairs,
    supported_moods,
)
from trackgen.packs import registered_styles, resolve_pack
from trackgen.seeds import to_base36

# The five v1 packs. Pinned here as a *cross-check* on the derived `PACKS`, not
# as its source — `PACKS` reads the registry, so a sixth pack fails only this
# assertion (a deliberate "did you mean to?" gate) and no property suite.
_EXPECTED_PACKS = ("blues", "chill_lofi", "fusion_jazz", "jazz", "pop_rock")

# Declared mood counts per pack, read off each `styles/*/interpreter.yaml`.
_EXPECTED_MOOD_COUNTS = {
    "blues": 8,
    "chill_lofi": 8,
    "fusion_jazz": 8,
    "jazz": 10,
    "pop_rock": 11,
}


def test_packs_are_the_five_v1_packs() -> None:
    assert PACKS == _EXPECTED_PACKS


def test_packs_are_derived_from_the_registry_not_hardcoded() -> None:
    """The pack dimension must follow the registry, so a new pack joins every
    §14.9 property suite without a test edit."""
    assert PACKS == tuple(sorted(registered_styles()))


@pytest.mark.parametrize("pack_id", PACKS)
def test_supported_moods_match_the_pack_declaration(pack_id: str) -> None:
    pack = resolve_pack(pack_id)
    assert pack is not None and pack.interpreter is not None
    assert supported_moods(pack_id) == tuple(sorted(pack.interpreter.supported_moods))
    assert len(supported_moods(pack_id)) == _EXPECTED_MOOD_COUNTS[pack_id]


def test_pack_mood_pairs_is_the_full_cross_product() -> None:
    pairs = pack_mood_pairs()
    assert len(pairs) == sum(_EXPECTED_MOOD_COUNTS.values()) == 45
    assert len(set(pairs)) == len(pairs)
    assert {p for p, _ in pairs} == set(PACKS)


def test_seeds_are_25_unique_literals() -> None:
    assert len(SEEDS_25) == 25
    assert len(set(SEEDS_25)) == 25


def test_seeds_reproduce_the_previous_in_module_formula() -> None:
    """The pinned literals are byte-identical to the generator expression the
    three duplicated sites used, so T5's widening moves no existing cell."""
    assert SEEDS_25 == tuple(
        to_base36(((i + 1) * 2654435761) % (2**63)) for i in range(25)
    )


def test_length_dimensions() -> None:
    assert LENGTHS_PLAN == tuple(range(30, 601, 15))
    assert len(LENGTHS_PLAN) == 39
    assert LENGTHS_RENDER == (None, 180, 240)
    assert len(LENGTHS_RENDER) == 3


def test_cached_pack_is_identity_stable() -> None:
    """Memoization hands back the same object, so callers may cache-key on it."""
    assert cached_pack("pop_rock") is cached_pack("pop_rock")
    assert cached_pack("pop_rock") is not cached_pack("jazz")


@pytest.mark.parametrize(
    ("pack_id", "mood"), [(p, supported_moods(p)[0]) for p in PACKS]
)
def test_build_plan_runs_for_every_pack(pack_id: str, mood: str) -> None:
    plan = build_plan(pack_id, mood, 180, SEEDS_25[0])
    assert plan.style_pack.id == pack_id
    assert plan.max_length_ticks == 180 * plan.tempo_bpm * 8
    # Determinism: the same cell rebuilds byte-identically.
    assert plan.model_dump() == build_plan(pack_id, mood, 180, SEEDS_25[0]).model_dump()
