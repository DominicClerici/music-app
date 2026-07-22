"""Pairwise A/B listening harness (PHASE_8 §8.4, instrument 2).

Covers the exact binomial math, the reproducible blinding, the critical
shown-position -> variant-identity bookkeeping (an always-prefer-A decider must
score `wins_a == n` regardless of blinded order), and end-to-end determinism.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.pipeline import to_json
from trackgen.pipeline.trace import generate_trace
from trackgen.schema.document import TrackDocument
from trackgen.tooling.ab import (
    binomial_two_sided_p,
    derive_trial_seeds,
    presentation_orders,
    run_ab,
)

runner = CliRunner()

# Two variants differing only on the comparison axis: pop_rock comping flavor.
# `piano` and `crunch_electric` render provably distinct documents.
_VARIANT_A: dict[str, object] = {
    "styleFamily": "pop_rock",
    "roleFlavors": {"comping": "piano"},
}
_VARIANT_B: dict[str, object] = {
    "styleFamily": "pop_rock",
    "roleFlavors": {"comping": "crunch_electric"},
}
_SEEDS: tuple[str, ...] = ("1ps9wxb", "2kq7f3z", "3", "42")


def _doc(variant: dict[str, object], seed: str) -> TrackDocument:
    return generate_trace({**variant, "seed": seed}).document


# --- exact binomial p-value -------------------------------------------------


def test_binomial_known_values() -> None:
    assert binomial_two_sided_p(20, 15) == pytest.approx(0.041389, abs=1e-5)
    assert binomial_two_sided_p(10, 5) == pytest.approx(1.0)
    assert binomial_two_sided_p(20, 20) == pytest.approx(1.907e-6, rel=1e-3)


def test_binomial_symmetry_and_bounds() -> None:
    for n in (0, 1, 7, 20):
        for k in range(n + 1):
            p = binomial_two_sided_p(n, k)
            assert 0.0 < p <= 1.0 + 1e-12
            assert p == pytest.approx(binomial_two_sided_p(n, n - k))
    assert binomial_two_sided_p(0, 0) == 1.0


def test_binomial_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        binomial_two_sided_p(5, 6)


# --- reproducible blinding --------------------------------------------------


def test_blinding_is_reproducible() -> None:
    first = presentation_orders("session-1", 20)
    second = presentation_orders("session-1", 20)
    assert first == second
    assert len(first) == 20


def test_blinding_differs_across_masters() -> None:
    assert presentation_orders("session-1", 20) != presentation_orders("session-2", 20)


def test_blinding_is_a_prefix() -> None:
    """The first k of an n-run equal a standalone k-run (single stream, in order)."""
    assert presentation_orders("m", 8) == presentation_orders("m", 12)[:8]


def test_trial_seeds_reproducible_and_distinct_stream() -> None:
    assert derive_trial_seeds("m", 6) == derive_trial_seeds("m", 6)
    assert derive_trial_seeds("m", 6) != derive_trial_seeds("other", 6)
    # Trial-seed draws and blinding draws come from different streams.
    assert derive_trial_seeds("m", 20) != [str(o) for o in presentation_orders("m", 20)]


# --- decision tally / the critical bookkeeping test -------------------------


def test_always_prefer_a_yields_wins_a_equals_n() -> None:
    """A decider that ALWAYS prefers variant A — no matter the shown order —
    must score `wins_a == n`. This proves shown-position is correctly mapped
    back to variant identity through the blinding."""
    a_docs = {to_json(_doc(_VARIANT_A, s)) for s in _SEEDS}
    b_docs = {to_json(_doc(_VARIANT_B, s)) for s in _SEEDS}
    assert a_docs.isdisjoint(b_docs), "variants must render distinctly"

    def decide_prefers_a(first: TrackDocument, second: TrackDocument) -> int:
        return 0 if to_json(first) in a_docs else 1

    for master in ("m1", "m2", "flip-the-order"):
        # Prove the shown-position -> variant remapping is exercised in BOTH
        # directions (not just by luck-of-the-seed): this master shows A first
        # in some trials and B first in others.
        orders = presentation_orders(master, len(_SEEDS))
        assert True in orders and False in orders
        result = run_ab(
            _VARIANT_A, _VARIANT_B, _SEEDS, decide_prefers_a, blind_master=master
        )
        assert result.wins_a == len(_SEEDS)
        assert result.wins_b == 0
        assert result.n == len(_SEEDS)


def test_always_prefer_b_yields_wins_b_equals_n() -> None:
    b_docs = {to_json(_doc(_VARIANT_B, s)) for s in _SEEDS}

    def decide_prefers_b(first: TrackDocument, second: TrackDocument) -> int:
        return 0 if to_json(first) in b_docs else 1

    orders = presentation_orders("m1", len(_SEEDS))
    assert True in orders and False in orders
    result = run_ab(_VARIANT_A, _VARIANT_B, _SEEDS, decide_prefers_b, blind_master="m1")
    assert result.wins_b == len(_SEEDS)
    assert result.wins_a == 0


def test_run_ab_is_deterministic() -> None:
    def decide_first(first: TrackDocument, second: TrackDocument) -> int:
        return 0

    a = run_ab(_VARIANT_A, _VARIANT_B, _SEEDS, decide_first, blind_master="m")
    b = run_ab(_VARIANT_A, _VARIANT_B, _SEEDS, decide_first, blind_master="m")
    assert a == b


def test_run_ab_rejects_bad_decision() -> None:
    def decide_bad(first: TrackDocument, second: TrackDocument) -> int:
        return 2

    with pytest.raises(ValueError):
        run_ab(_VARIANT_A, _VARIANT_B, ("1",), decide_bad, blind_master="m")


# --- CLI wiring (stubbed prompts + tmp log) ---------------------------------


def test_cli_ab_writes_one_record_to_tmp_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `ab` command parses `--axis`, drives the blinded trials, and appends
    exactly one `{"type": "ab"}` record.

    The pick prompt (`type=int`) is stubbed to always answer "1" (option 1 =
    first-shown), so every trial's win goes to whichever variant the blinding
    showed first. The tally is therefore fully predictable from
    `presentation_orders`: winsA is the count of A-shown-first trials. `master`
    and `--trials 7` are chosen so winsA != winsB, which is what makes this
    assertion kill a winsA/winsB-swap mutant. `open_playground` is neutered and
    the log is a tmp path — the committed `listening/log.jsonl` is never written.
    """
    master = "cli-ab-test"
    trials = 7
    orders = presentation_orders(master, trials)
    expected_wins_a = sum(orders)
    expected_wins_b = trials - expected_wins_a
    # Precondition that arms the swap-detection: an even split would let a
    # winsA<->winsB swap pass unnoticed.
    assert expected_wins_a != expected_wins_b

    def _stub_prompt(*args: object, **kwargs: object) -> object:
        return 1 if kwargs.get("type") is int else ""

    monkeypatch.setattr("trackgen.cli.open_playground", lambda rendered: None)
    monkeypatch.setattr("trackgen.cli.typer.prompt", _stub_prompt)

    log = tmp_path / "nested" / "log.jsonl"
    result = runner.invoke(
        app,
        [
            "ab",
            "--pack",
            "pop_rock",
            "--mood",
            "happy",
            "--axis",
            "comping=piano:crunch_electric",
            "--date",
            "2026-07-21",
            "--trials",
            str(trials),
            "--blind-master",
            master,
            "--log",
            str(log),
        ],
    )
    assert result.exit_code == 0, result.output

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])

    assert record["type"] == "ab"
    assert record["date"] == "2026-07-21"
    assert record["pack"] == "pop_rock"
    assert record["mood"] == "happy"
    assert record["axis"] == "comping=piano:crunch_electric"
    assert record["variantA"] == {
        "styleFamily": "pop_rock",
        "mood": "happy",
        "roleFlavors": {"comping": "piano"},
    }
    assert record["variantB"] == {
        "styleFamily": "pop_rock",
        "mood": "happy",
        "roleFlavors": {"comping": "crunch_electric"},
    }
    assert record["blindMaster"] == master
    assert record["trialSeeds"] == derive_trial_seeds(master, trials)
    assert record["n"] == trials
    assert record["winsA"] == expected_wins_a
    assert record["winsB"] == expected_wins_b
    assert record["winsA"] + record["winsB"] == trials
    assert record["pValue"] == pytest.approx(
        binomial_two_sided_p(trials, max(expected_wins_a, expected_wins_b))
    )


def test_cli_ab_malformed_axis_is_clean_bad_parameter() -> None:
    """A `--axis` missing its `=`/`:` structure exits non-zero with a clean
    `BadParameter` message (no traceback)."""
    result = runner.invoke(
        app,
        [
            "ab",
            "--pack",
            "pop_rock",
            "--axis",
            "not-a-valid-axis",
            "--date",
            "2026-07-21",
        ],
    )
    assert result.exit_code != 0
    assert not isinstance(result.exception, (KeyError, ValueError, TypeError))
    assert "role=flavorA:flavorB" in result.output
