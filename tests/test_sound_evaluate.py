"""Tests for the Phase 7 patch-evaluation model (PHASE_7 §3; SESSION_13 T2, DoD 3).

Covers curve evaluation (both curves, endpoints/midpoint, inverted ranges),
`round3` half-even rounding, the per-directive-key merge (replace, empty-list
disable, absent-key keep, drum per-`(directive, voice)` key), the base-XOR-mod
check (§3.3), and `apply_directives` (fixed order, nested-path landing, mix-block
routing). Closes with a §9.1 evaluator-sanity anchor (not a golden — that is C2).
"""

import pytest

from trackgen.sound.evaluate import (
    apply_directives,
    assert_base_xor_mod,
    evaluate_mapping,
    get_by_path,
    merge_mod,
    round3,
)
from trackgen.sound.models import Curve, MappingEntry


def _entry(param: str, lo: float, hi: float, curve: Curve) -> MappingEntry:
    return MappingEntry(param=param, min=lo, max=hi, curve=curve)


# --- curve evaluation (§3.1) ------------------------------------------------


def test_linear_endpoints_and_midpoint() -> None:
    entry = _entry("noise.playbackRate", 2.0, 4.0, "linear")
    assert evaluate_mapping(entry, 0.0) == 2.0
    assert evaluate_mapping(entry, 1.0) == 4.0
    assert evaluate_mapping(entry, 0.5) == 3.0


def test_exp_endpoints_and_midpoint() -> None:
    entry = _entry("filterEnvelope.baseFrequency", 120.0, 2500.0, "exp")
    assert evaluate_mapping(entry, 0.0) == 120.0
    assert evaluate_mapping(entry, 1.0) == 2500.0
    # Geometric-mean midpoint: 120·(2500/120)^0.5.
    assert evaluate_mapping(entry, 0.5) == 547.723


def test_inverted_linear_range_decreases() -> None:
    # attackHardness: slow→fast as d rises (§3.1), min > max is legal.
    entry = _entry("envelope.attack", 0.12, 0.001, "linear")
    assert evaluate_mapping(entry, 0.0) == 0.12
    assert evaluate_mapping(entry, 1.0) == 0.001
    assert evaluate_mapping(entry, 0.3) > evaluate_mapping(entry, 0.7)


def test_inverted_exp_range_decreases() -> None:
    entry = _entry("envelope.attack", 0.12, 0.001, "exp")
    assert evaluate_mapping(entry, 0.0) == 0.12
    assert evaluate_mapping(entry, 1.0) == 0.001
    assert evaluate_mapping(entry, 0.3) > evaluate_mapping(entry, 0.7)


# --- round3 half-even (§3.1) ------------------------------------------------


def test_round3_is_half_even_at_ties() -> None:
    # 0.0625 and 0.1875 are exactly float-representable (1/16, 3/16), so the
    # 4th-decimal ties are genuine: half-even rounds each toward the even digit
    # (down to …062, up to …188), matching Python's banker's `round`.
    assert round3(0.0625) == 0.062
    assert round3(0.1875) == 0.188
    assert round3(0.0625) == round(0.0625, 3)
    assert round3(0.1875) == round(0.1875, 3)


# --- merge_mod per-directive-key replacement (§3.2) -------------------------


def test_merge_mod_override_replaces_whole_list() -> None:
    d1 = _entry("filterEnvelope.baseFrequency", 120.0, 2500.0, "exp")
    d2 = _entry("mix.sends.reverb", -24.0, -9.0, "linear")
    o1 = _entry("modulationIndex", 4.0, 14.0, "exp")
    merged = merge_mod({"brightness": [d1], "space": [d2]}, {"brightness": [o1]})
    assert merged["brightness"] == (o1,)  # replaced, not appended
    assert merged["space"] == (d2,)  # absent in override → default kept


def test_merge_mod_empty_list_disables_directive() -> None:
    d1 = _entry("mix.sends.reverb", -24.0, -9.0, "linear")
    merged = merge_mod({"space": [d1]}, {"space": []})
    assert merged["space"] == ()


def test_merge_mod_none_override_keeps_defaults() -> None:
    d1 = _entry("filterEnvelope.baseFrequency", 120.0, 2500.0, "exp")
    merged = merge_mod({"brightness": [d1]}, None)
    assert merged == {"brightness": (d1,)}


def test_merge_mod_drums_per_directive_voice_key() -> None:
    # Drums key by (directive, voice): a snare override replaces only that list.
    snare_b = _entry("noise.playbackRate", 2.0, 4.0, "linear")
    hats_b = _entry("resonance", 2000.0, 5500.0, "exp")
    snare_s = _entry("mix.sends.reverb", -18.0, -6.0, "linear")
    override_snare = _entry("noise.playbackRate", 0.4, 0.9, "linear")
    merged = merge_mod(
        {
            ("brightness", "snare"): [snare_b],
            ("brightness", "hats"): [hats_b],
            ("space", "snare"): [snare_s],
        },
        {("brightness", "snare"): [override_snare]},
    )
    assert merged[("brightness", "snare")] == (override_snare,)
    assert merged[("brightness", "hats")] == (hats_b,)  # untouched
    assert merged[("space", "snare")] == (snare_s,)  # untouched


# --- base XOR mod (§3.3) ----------------------------------------------------


def test_assert_base_xor_mod_raises_on_overlap() -> None:
    with pytest.raises(ValueError, match="base XOR mod"):
        assert_base_xor_mod({"filter.Q", "envelope.decay"}, {"filter.Q"})


def test_assert_base_xor_mod_passes_when_disjoint() -> None:
    # Disjoint sets must not raise (no return value to assert).
    assert_base_xor_mod({"envelope.decay"}, {"filterEnvelope.baseFrequency"})


# --- apply_directives (§3.4) ------------------------------------------------


def _const(param: str, value: float) -> MappingEntry:
    # A degenerate range (min == max) evaluates to a constant at any d, isolating
    # ordering behaviour from directive-value differences.
    return _entry(param, value, value, "linear")


def test_apply_directives_fixed_order() -> None:
    values = {"brightness": 0.5, "attackHardness": 0.5, "space": 0.5}
    # `pz` is targeted by all three directives; `pa` by the first two only.
    result = apply_directives(
        {"pz": 0.0, "pa": 0.0},
        {
            "brightness": [_const("pz", 2.0), _const("pa", 2.0)],
            "attackHardness": [_const("pz", 5.0), _const("pa", 5.0)],
            "space": [_const("pz", 9.0)],
        },
        values,
    )
    assert result["pz"] == 9.0  # space applied last
    assert result["pa"] == 5.0  # attackHardness applied after brightness


def test_apply_directives_lands_at_nested_path() -> None:
    base = {"filterEnvelope": {"baseFrequency": 0.0, "decay": 0.7}}
    entry = _entry("filterEnvelope.baseFrequency", 120.0, 2500.0, "exp")
    result = apply_directives(base, {"brightness": [entry]}, {"brightness": 0.835})
    assert result["filterEnvelope"]["baseFrequency"] == 1514.763
    assert result["filterEnvelope"]["decay"] == 0.7  # sibling untouched
    assert base["filterEnvelope"]["baseFrequency"] == 0.0  # input not mutated


def test_apply_directives_mix_send_routes_to_mix_block() -> None:
    base = {"filterEnvelope": {"decay": 0.7}, "mix": {"volumeDb": -13, "sends": {}}}
    entry = _entry("mix.sends.reverb", -24.0, -9.0, "linear")
    result = apply_directives(base, {"space": [entry]}, {"space": 0.36})
    assert get_by_path(result, "mix.sends.reverb") == -18.6
    assert "reverb" not in result  # written to the mix block, not the options


def test_apply_directives_autovivifies_missing_send() -> None:
    # A flavor whose base mix carries no fixed `sends` (§4.2: send omitted when a
    # `space` mapping targets it) — set_by_path must create the intermediate dict.
    base = {"filterEnvelope": {"decay": 0.7}, "mix": {"volumeDb": -13}}
    entry = _entry("mix.sends.reverb", -24.0, -9.0, "linear")
    result = apply_directives(base, {"space": [entry]}, {"space": 0.36})
    assert get_by_path(result, "mix.sends.reverb") == -18.6
    assert base["mix"] == {"volumeDb": -13}  # input untouched (deep copy)


# --- §9.1 evaluator-sanity anchors (NOT a golden — that is C2/§13.4) ---------


def test_evaluator_reproduces_phase7_9_1_anchors() -> None:
    # Pop snare brightness (linear): pinned §9.1 value 3.67.
    snare = _entry("noise.playbackRate", 2.0, 4.0, "linear")
    assert evaluate_mapping(snare, 0.835) == 3.67

    # Bass brightness baseFrequency (exp): §9.1 displays ≈1514.8 (1-decimal);
    # the round3 golden is 1514.763.
    bass_bf = _entry("filterEnvelope.baseFrequency", 120.0, 2500.0, "exp")
    evaluated = evaluate_mapping(bass_bf, 0.835)
    assert evaluated == round3(120.0 * (2500.0 / 120.0) ** 0.835)
    assert evaluated == 1514.763
    assert round(evaluated, 1) == 1514.8
