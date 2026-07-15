"""Golden-vector + determinism tests for the seed system (PHASE_1 §5.6, §9.2/§9.7).

The §5.6 values are normative: if the implementation disagrees, the
implementation is wrong. Never edit an expected number to match code output.
"""

from __future__ import annotations

import random

import pytest

from trackgen.seeds import (
    STREAMS,
    derive,
    fresh_master,
    from_base36,
    master_from_string,
    stream_seed,
    to_base36,
    weighted_choice,
)

MASTER = 3735928559  # 0xDEADBEEF; base36 "1ps9wxb"

# PHASE_1 §5.6 table: derive(MASTER, name) -> (u64, base36).
STREAM_GOLDENS: dict[str, tuple[int, str]] = {
    "interpreter": (1597995742192405040, "c52i7pgxyq7k"),
    "form": (7567330889165579844, "1lhqyx6gblkjo"),
    "harmony": (226146634901021418, "1puqahumzht6"),
    "arrangement": (17905737752012141625, "3s1f2al1nfupl"),
    "drums": (13141849116576272873, "2rufwpmioicx5"),
    "bass": (12266082893315700426, "2l6wrhtnwz6bu"),
    "comping": (15485288006162947228, "39necguatbd7g"),
    "pads": (16576309723187015011, "3hxszdzu7hdgj"),
    "transitions": (17897360909067852929, "3rz4ky8iu33wh"),
    "humanize": (3899203291477031323, "tmh47jcjtpjv"),
    "sound": (11189761989562234097, "2d0ivksicdiwh"),
}


def test_master_from_string_banana() -> None:
    master = master_from_string("banana")
    assert master == 13011977409198548045
    assert to_base36(master) == "2qux517snxfm5"


def test_master_base36() -> None:
    assert to_base36(MASTER) == "1ps9wxb"
    assert from_base36("1ps9wxb") == MASTER


def test_stream_registry_pinned() -> None:
    assert STREAMS == (
        "interpreter",
        "form",
        "harmony",
        "arrangement",
        "drums",
        "bass",
        "comping",
        "pads",
        "transitions",
        "humanize",
        "sound",
    )
    # The golden table covers exactly the pinned registry.
    assert set(STREAM_GOLDENS) == set(STREAMS)


@pytest.mark.parametrize(("name", "expected"), STREAM_GOLDENS.items())
def test_derive_stream_goldens(name: str, expected: tuple[int, str]) -> None:
    value, b36 = expected
    got = derive(MASTER, name)
    assert got == value
    assert to_base36(got) == b36
    assert from_base36(b36) == value


def test_derive_chained() -> None:
    drums = derive(MASTER, "drums")
    fills = derive(drums, "fills")
    assert fills == 2174782555333666359
    assert derive(fills, "bar:17") == 1110592329615889969


def test_rng_getrandbits_golden() -> None:
    rng = random.Random(derive(MASTER, "drums"))
    draws = [rng.getrandbits(32) for _ in range(5)]
    assert draws == [2813930941, 3236345189, 575825508, 1551984896, 116936044]


def test_rng_randrange_golden() -> None:
    rng = random.Random(derive(MASTER, "drums"))
    draws = [rng.randrange(100) for _ in range(5)]
    assert draws == [83, 96, 17, 46, 3]


def test_base36_roundtrip() -> None:
    for n in (0, 1, 35, 36, MASTER, 13011977409198548045, (1 << 64) - 1):
        assert from_base36(to_base36(n)) == n


def test_from_base36_case_insensitive() -> None:
    assert from_base36("1PS9WXB") == MASTER
    assert from_base36("1Ps9WxB") == MASTER
    assert from_base36("2QUX517SNXFM5") == 13011977409198548045


def test_to_base36_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        to_base36(-1)
    with pytest.raises(ValueError):
        to_base36(1 << 64)


def test_from_base36_rejects_non_canonical() -> None:
    # int(s, 36) alone would accept underscores, sign prefixes, and whitespace,
    # aliasing distinct strings to the same seed; from_base36 must reject them.
    for bad in ("1_2", "+5", "-5", "  12  ", "12\n", "1.2", "", "ab$"):
        with pytest.raises(ValueError):
            from_base36(bad)


def test_from_base36_out_of_range_rejected() -> None:
    # 36 base36 'z's is far above u64 max.
    with pytest.raises(ValueError, match="out of u64 range"):
        from_base36("z" * 14)


def test_stream_seed_override_and_default() -> None:
    # No override -> derive(master, name).
    assert stream_seed(MASTER, {}, "drums") == derive(MASTER, "drums")
    # Override wins for the named stream, others still derived.
    overrides = {"drums": 42}
    assert stream_seed(MASTER, overrides, "drums") == 42
    assert stream_seed(MASTER, overrides, "bass") == derive(MASTER, "bass")


def test_determinism_guard_identical_draw_sequences() -> None:
    # §9.7: two RNGs from the same stream seed produce identical sequences.
    seed = stream_seed(MASTER, {}, "harmony")
    a = random.Random(seed)
    b = random.Random(seed)
    seq_a = [a.getrandbits(32) for _ in range(50)]
    seq_b = [b.getrandbits(32) for _ in range(50)]
    assert seq_a == seq_b


def test_weighted_choice_deterministic_specific_pick() -> None:
    items = ["a", "b", "c"]
    weights = [1, 1, 1]
    # Fixed seed -> a specific, reproducible pick (non-vacuous assertion).
    rng = random.Random(12345)
    first = weighted_choice(items, weights, rng)
    assert first == "b"
    # Same seed -> same pick.
    assert weighted_choice(items, weights, random.Random(12345)) == "b"


def test_weighted_choice_respects_lopsided_weights() -> None:
    items = ["rare", "common"]
    weights = [1, 999]
    rng = random.Random(7)
    picks = [weighted_choice(items, weights, rng) for _ in range(1000)]
    assert picks.count("common") > 950
    assert "rare" in picks or picks.count("common") == 1000


def test_weighted_choice_selects_only_positive_weight_item() -> None:
    items = ["zero", "all"]
    weights = [0, 5]
    rng = random.Random(3)
    assert all(weighted_choice(items, weights, rng) == "all" for _ in range(20))


def test_weighted_choice_rejects_nonpositive_total() -> None:
    rng = random.Random(0)
    with pytest.raises(ValueError):
        weighted_choice(["a", "b"], [0, 0], rng)
    with pytest.raises(ValueError):
        weighted_choice([], [], rng)


def test_weighted_choice_rejects_length_mismatch() -> None:
    rng = random.Random(0)
    with pytest.raises(ValueError):
        weighted_choice(["a", "b"], [1], rng)


def test_fresh_master_in_u64_range() -> None:
    for _ in range(20):
        m = fresh_master()
        assert 0 <= m <= (1 << 64) - 1
