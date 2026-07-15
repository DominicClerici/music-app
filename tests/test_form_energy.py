"""Tests for the energy model (PHASE_3 §6, worked examples §7.4).

Asserts `section_energy` reproduces all 13 sections' energy columns from
both §7.4 worked examples exactly, and that `load_energy_table()` loads a
valid, complete §6.1 base table.
"""

import pytest

from trackgen.form.energy import load_energy_table, section_energy
from trackgen.packs.models import SECTION_TYPES

# PHASE_3 §7.4 Example 1 — pop_rock / happy, arousal +0.40, energyRange (0, 1).
# normative — do not edit to match code
EXAMPLE_1 = [
    ("intro", 1, 1, 0.340),
    ("verse", 1, 2, 0.490),
    ("chorus", 1, 3, 0.790),
    ("verse", 2, 2, 0.540),
    ("chorus", 2, 3, 0.840),
    ("bridge", 1, 1, 0.440),
    ("chorus", 3, 3, 1.000),
]

# PHASE_3 §7.4 Example 2 — jazz / melancholic, arousal -0.45, energyRange (0.10, 0.90).
# normative — do not edit to match code
EXAMPLE_2 = [
    ("head", 1, 2, 0.464),
    ("solo", 1, 3, 0.624),
    ("solo", 2, 3, 0.704),
    ("solo", 3, 3, 0.784),
    ("head", 2, 2, 0.464),
    ("outro", 1, 1, 0.344),
]


@pytest.mark.parametrize(
    ("section_type", "index", "total_of_type", "expected"),
    EXAMPLE_1,
)
def test_example_1_energy_columns(
    section_type: str, index: int, total_of_type: int, expected: float
) -> None:
    """PHASE_3 §7.4 Example 1 (pop_rock/happy) — energy column, 7 sections."""
    assert (
        section_energy(
            section_type,
            index,
            total_of_type,
            arousal=0.40,
            energy_range=(0.0, 1.0),
        )
        == expected
    )


@pytest.mark.parametrize(
    ("section_type", "index", "total_of_type", "expected"),
    EXAMPLE_2,
)
def test_example_2_energy_columns(
    section_type: str, index: int, total_of_type: int, expected: float
) -> None:
    """PHASE_3 §7.4 Example 2 (jazz/melancholic) — energy column, 6 sections."""
    assert (
        section_energy(
            section_type,
            index,
            total_of_type,
            arousal=-0.45,
            energy_range=(0.10, 0.90),
        )
        == expected
    )


def test_load_energy_table_covers_all_types() -> None:
    """PHASE_3 §6.1 — `energy.yaml` loads and covers all 11 section types."""
    table = load_energy_table()
    assert set(table.base) == set(SECTION_TYPES)
    assert len(SECTION_TYPES) == 11


def test_load_energy_table_base_values_exact() -> None:
    """PHASE_3 §6.1 — the loaded base table matches the printed table exactly
    for all 11 types (a typo in `energy.yaml` would pass the §7.4 worked
    examples alone, since those exercise only 5 of the 11 base values).
    """
    table = load_energy_table()
    assert table.base == {
        "intro": 0.30,
        "verse": 0.45,
        "prechorus": 0.60,
        "chorus": 0.75,
        "postchorus": 0.65,
        "bridge": 0.40,
        "head": 0.50,
        "solo": 0.60,
        "main": 0.50,
        "breakdown": 0.25,
        "outro": 0.35,
    }


def test_clamp_before_envelope_not_after() -> None:
    """PHASE_3 §6.2->§6.3->§6.4 — the pinned order clamps to [0,1] (§6.3)
    *before* applying the pack envelope (§6.4), not after. The two §7.4
    worked examples both use near-identity `energyRange`s where a buggy
    envelope-before-clamp ordering happens to reproduce the same rounded
    result, so they cannot catch a reordering bug. This case uses a
    compressed, non-identity range with a pre-clamp value > 1.0 so the two
    orderings diverge.

    chorus, index=3, total_of_type=3, arousal=0.40, energy_range=(0.0, 0.9):
      base .75; R1 += 0.05*min(3-1,2) = +0.10 -> .85;
      R3 (final chorus, total>=2) += 0.15 -> e = 1.00 (pre-arousal)
      pinned order:
        clamp01(1.00 + 0.10*0.40) = clamp01(1.04) = 1.0                (§6.3)
        round(0.0 + 1.0 * (0.9 - 0.0), 3) = 0.900                      (§6.4)
      wrong order (envelope applied to the unclamped arousal-modulated e,
      i.e. clamp01 skipped/moved after the envelope):
        round(0.0 + 1.04 * (0.9 - 0.0), 3) = round(0.936, 3) = 0.936
      0.900 != 0.936, so this input distinguishes the two orderings.
    """
    assert (
        section_energy(
            "chorus",
            index=3,
            total_of_type=3,
            arousal=0.40,
            energy_range=(0.0, 0.9),
        )
        == 0.900
    )


def test_r4_override_is_arousal_modulated_and_enveloped() -> None:
    """PHASE_3 §6.2 R4 — a slot `energy:` override replaces base + R1-R3
    outright but is still arousal-modulated (§6.3) and enveloped (§6.4); no
    §7.4 worked example exercises the override path.

    chorus, index=1, total_of_type=3, arousal=0.40, energy_range=(0.0, 1.0),
    override=0.65:
      e = 0.65 (override replaces base+R1-R3 entirely)
      clamp01(0.65 + 0.10*0.40) = clamp01(0.69) = 0.69                 (§6.3)
      round(0.0 + 0.69 * (1.0 - 0.0), 3) = 0.690       (§6.4, identity range)
    """
    assert (
        section_energy(
            "chorus",
            index=1,
            total_of_type=3,
            arousal=0.40,
            energy_range=(0.0, 1.0),
            override=0.65,
        )
        == 0.690
    )
