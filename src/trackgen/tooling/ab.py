"""Pairwise A/B listening harness (PHASE_8 §8.4, instrument 2).

Two variants differing only in the compared axis (e.g. a role's instrument
flavor) are rendered at the *same* seed for each of ~20 trials. The listener
hears them in a blinded presentation order and makes a forced "which sounds
better" choice; the tally is scored against chance with an exact two-sided
binomial test.

The module is split mechanism-from-I/O on purpose: `run_ab` is a deterministic
core that takes a `decide` callback and never touches a browser or a prompt, so
it is fully unit-testable, while the `trackgen ab` CLI wires `decide` to an
interactive prompt over the audition player.

**Blinding is itself reproducible.** The per-trial coin flip that decides
presentation order is drawn from a stream seeded by `blind_master` (recorded in
the log), so a session can be replayed exactly. Entropy stays behind
`trackgen.seeds` — this module never imports `random`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import comb

from trackgen.pipeline.trace import generate_trace
from trackgen.schema.document import TrackDocument
from trackgen.seeds import master_from_string, stream_rng, to_base36

# The §8.4 stream name for the blinding coin. A distinct name for the derived
# trial seeds so the two draws never share state.
_BLIND_STREAM = "listening_ab"
_TRIAL_SEED_STREAM = "listening_ab_seeds"

RawParams = Mapping[str, object]

# `decide(first_shown, second_shown) -> 0 | 1`: 0 prefers the first-shown doc,
# 1 the second-shown. The callback is blind to which variant is which — that is
# the whole point — so it may only judge on what it hears.
Decide = Callable[[TrackDocument, TrackDocument], int]


@dataclass(frozen=True)
class ABResult:
    """The scored outcome of a pairwise run (§8.4).

    `wins_a + wins_b == n`; `p_value` is the exact two-sided binomial p against a
    fair coin for `max(wins_a, wins_b)` successes in `n` trials.
    """

    n: int
    wins_a: int
    wins_b: int
    p_value: float


def binomial_two_sided_p(n: int, k: int) -> float:
    """Exact two-sided binomial p-value for `k` successes in `n` trials vs 0.5.

    The standard "sum of probabilities no larger than the observed" test: under
    Binomial(n, 0.5), sum P(X=i) over every i whose point probability is <= the
    point probability of the observed count. Stdlib-only (`math.comb`); no
    scipy/numpy. Known values: n=20,k=15 -> ~0.0414; n=10,k=5 -> 1.0;
    n=20,k=20 -> ~1.9e-6.
    """
    if not (0 <= k <= n):
        raise ValueError(f"k={k} out of range for n={n}")
    if n == 0:
        return 1.0
    total = float(1 << n)
    probs = [comb(n, i) / total for i in range(n + 1)]
    observed = probs[k]
    # A relative slack absorbs float wobble so the symmetric partner outcome
    # (which is equal in exact arithmetic) is never dropped by a last-ulp miss.
    threshold = observed * (1.0 + 1e-9)
    return sum(p for p in probs if p <= threshold)


def presentation_orders(blind_master: str, n: int) -> list[bool]:
    """The blinded per-trial order sequence for `blind_master` (reproducible).

    `True` means variant A is shown first in that trial. Derived from a single
    stream so the same `blind_master` always yields the same sequence and a
    different master (almost surely) yields a different one.
    """
    rng = stream_rng(master_from_string(blind_master), {}, _BLIND_STREAM)
    return [rng.random() < 0.5 for _ in range(n)]


def derive_trial_seeds(blind_master: str, n: int) -> list[str]:
    """`n` reproducible base36 u64 trial seeds derived from `blind_master`.

    A separate stream from the blinding coin, so choosing seeds and blinding the
    order are independent draws that cannot alias.
    """
    rng = stream_rng(master_from_string(blind_master), {}, _TRIAL_SEED_STREAM)
    return [to_base36(rng.getrandbits(64)) for _ in range(n)]


def _render(variant: RawParams, seed: str) -> TrackDocument:
    """Render `variant` at `seed` through the production chain."""
    return generate_trace({**variant, "seed": seed}).document


def run_ab(
    variant_a: RawParams,
    variant_b: RawParams,
    trial_seeds: Sequence[str],
    decide: Decide,
    *,
    blind_master: str,
) -> ABResult:
    """Score variant A vs B over `trial_seeds` under blinded presentation (§8.4).

    For each seed both variants are rendered at that seed; the coin from
    `blind_master` fixes which is shown first; `decide` returns 0 (first-shown)
    or 1 (second-shown); and the pick is mapped back through the known order to
    the variant that actually won. Fully deterministic in `(variants, seeds,
    decide, blind_master)`.
    """
    orders = presentation_orders(blind_master, len(trial_seeds))
    wins_a = 0
    for a_first, seed in zip(orders, trial_seeds, strict=True):
        doc_a = _render(variant_a, seed)
        doc_b = _render(variant_b, seed)
        first_shown, second_shown = (doc_a, doc_b) if a_first else (doc_b, doc_a)
        choice = decide(first_shown, second_shown)
        if choice not in (0, 1):
            raise ValueError(f"decide must return 0 or 1, got {choice!r}")
        chose_first = choice == 0
        if chose_first == a_first:
            wins_a += 1
    n = len(trial_seeds)
    wins_b = n - wins_a
    return ABResult(
        n=n,
        wins_a=wins_a,
        wins_b=wins_b,
        p_value=binomial_two_sided_p(n, max(wins_a, wins_b)),
    )
