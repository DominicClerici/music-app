"""Hierarchical seed system (PHASE_1 §5).

The single entropy boundary of the pipeline. `os.urandom` and the `random`
module may be used *here and only here* (`seeds.py` is TID251-exempt in
``pyproject.toml``); everything downstream is a pure function of a seed.

A master u64 seed derives named, chained sub-seeds by SHA-256, so the same
``(params, seed)`` always produces the same track, streams can be rerolled
independently, and adding a stage never renumbers existing streams.
"""

from __future__ import annotations

import hashlib
import os
import random
from collections.abc import Sequence

__all__ = [
    "STREAMS",
    "derive",
    "fresh_master",
    "from_base36",
    "master_from_string",
    "stream_rng",
    "stream_seed",
    "to_base36",
    "weighted_choice",
]

_U64_BYTES = 8
_U64_MAX = (1 << 64) - 1

# Pinned top-level stream registry (PHASE_1 §5.2). Names, not indices: adding a
# stage never renumbers existing streams, so old seeds keep their song.
STREAMS: tuple[str, ...] = (
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


def master_from_string(s: str) -> int:
    """Hash any free string to a u64 master seed (PHASE_1 §5.1, `seedText`)."""
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    return int.from_bytes(digest[:_U64_BYTES], "big")


def derive(parent: int, name: str) -> int:
    """Derive a named child seed from a parent u64 (PHASE_1 §5.2).

    SHA-256 gives full avalanche, so there is no correlated-stream risk.
    Chain calls for hierarchy: ``derive(derive(M, "drums"), "fills")``.
    """
    payload = parent.to_bytes(_U64_BYTES, "big") + b"/" + name.encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:_U64_BYTES], "big")


def stream_seed(master: int, overrides: dict[str, int], name: str) -> int:
    """Resolve a stream's seed, honoring reroll overrides (PHASE_1 §5.4)."""
    return overrides.get(name, derive(master, name))


def stream_rng(master: int, overrides: dict[str, int], name: str) -> random.Random:
    """A `random.Random` seeded by this stream's resolved seed (PHASE_1 §5.3/§5.4).

    Constructing the RNG lives here so the `random`-module boundary stays inside
    `seeds.py`; downstream stages get their generator through this factory.
    """
    return random.Random(stream_seed(master, overrides, name))


def to_base36(n: int) -> str:
    """Encode a u64 as a lowercase base36 string (PHASE_1 §5.5)."""
    if n < 0 or n > _U64_MAX:
        raise ValueError(f"seed out of u64 range: {n}")
    if n == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out: list[str] = []
    while n:
        n, rem = divmod(n, 36)
        out.append(digits[rem])
    return "".join(reversed(out))


_BASE36_DIGITS = frozenset("0123456789abcdefghijklmnopqrstuvwxyz")


def from_base36(s: str) -> int:
    """Decode a base36 string to a u64 (case-insensitive; PHASE_1 §5.5).

    Only canonical base36 digits are accepted. Bare `int(s, 36)` would also
    swallow underscores (`"1_2"`), a sign prefix (`"+5"`), and surrounding
    whitespace, aliasing distinct strings to the same seed and loosening the
    `SEED_INVALID` contract."""
    if not s or any(c not in _BASE36_DIGITS for c in s.lower()):
        raise ValueError(f"not a canonical base36 string: {s!r}")
    n = int(s, 36)
    if n > _U64_MAX:
        raise ValueError(f"seed out of u64 range: {n}")
    return n


def weighted_choice[T](
    items: Sequence[T], weights: Sequence[int], rng: random.Random
) -> T:
    """Pick an item by integer weight (PHASE_1 §5.3).

    Integer weights and cumulative sums avoid the last-ulp pick flips floats can
    cause. Requires ``sum(weights) > 0``.
    """
    if len(items) != len(weights):
        raise ValueError("items and weights must have equal length")
    total = sum(weights)
    if total <= 0:
        raise ValueError("sum of weights must be positive")
    r = rng.randrange(total)
    acc = 0
    for item, w in zip(items, weights, strict=True):
        acc += w
        if r < acc:
            return item
    raise AssertionError("unreachable: r < total guarantees a pick")


def fresh_master() -> int:
    """Read 8 bytes of OS entropy into a u64 master seed (PHASE_1 §5.1).

    The single place entropy may enter the pipeline. No user seed given → a
    fresh song.
    """
    return int.from_bytes(os.urandom(_U64_BYTES), "big")
