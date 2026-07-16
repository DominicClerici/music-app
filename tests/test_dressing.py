"""Tests for the dissonance-dressing ladder (PHASE_4 §6; DoD §14.3).

The §6.1 tier bands, §6.2 function offsets, and §6.3 option tables are
normative: on divergence the PHASE_4 text wins (ROADMAP §3 golden-value
arbitration). `dressing.yaml` is asserted field-for-field against the printed
§6.3 tables; every table option is checked §6.4-legal; the §10 worked-example
dressings anchor the end-to-end selection.
"""

from __future__ import annotations

import pytest

from trackgen.harmony import (
    DressingTable,
    dressing_options,
    effective_tier,
    load_dressing_table,
    tier,
)
from trackgen.schema.ir import ChordSpec, Key
from trackgen.theory import Function, extensions_legal, resolve_token

E_MAJOR = Key(tonic_pc=4, mode="major")
D_MINOR = Key(tonic_pc=2, mode="minor")

_FUNCTIONS: tuple[Function, ...] = ("T", "S", "D", "O")


# --- §6.1 tier boundaries ----------------------------------------------------


# Each ceiling and the value just below it, plus the §10 anchors. Exact
# boundary values belong to the higher tier they open (low-closed bands).
@pytest.mark.parametrize(
    ("dissonance", "expected"),
    [
        (0.0, 0),
        (0.132, 0),  # §10.1 anchor
        (0.149, 0),
        (0.15, 1),  # exact boundary → higher tier
        (0.29, 1),
        (0.30, 2),
        (0.44, 2),
        (0.45, 3),
        (0.59, 3),
        (0.60, 4),
        (0.653, 4),  # §10.2 anchor
        (0.74, 4),
        (0.75, 5),
        (0.89, 5),
        (0.90, 6),
        (0.95, 6),
        (1.0, 6),
    ],
)
def test_tier_boundaries(dissonance: float, expected: int) -> None:
    assert tier(dissonance) == expected


def test_tier_every_ceiling_opens_higher_tier() -> None:
    # The seven bands: tier 0 strictly < 0.15, tier 6 >= 0.90.
    assert tier(0.15 - 1e-9) == 0
    for exact, opened in [
        (0.15, 1),
        (0.30, 2),
        (0.45, 3),
        (0.60, 4),
        (0.75, 5),
        (0.90, 6),
    ]:
        assert tier(exact) == opened


# --- §6.2 function offsets + clamp -------------------------------------------


def test_function_offsets() -> None:
    # D:+1, T:-1, S/O:0 at a mid tier.
    assert effective_tier(3, "D") == 4
    assert effective_tier(3, "T") == 2
    assert effective_tier(3, "S") == 3
    assert effective_tier(3, "O") == 3


def test_effective_tier_clamps() -> None:
    # tier-6 D stays <= 6; tier-0 T clamps to >= 0.
    assert effective_tier(6, "D") == 6
    assert effective_tier(0, "T") == 0
    assert effective_tier(0, "S") == 0
    assert effective_tier(0, "O") == 0
    assert effective_tier(6, "T") == 5


# --- §6.3 dressing.yaml field-for-field --------------------------------------

# The §6.3 printed tables, transcribed as (quality, extensions, weight) rows.
EXPECTED_TABLE: dict[str, dict[int, list[tuple[str, list[str], int]]]] = {
    "bare_maj_ts": {
        0: [("maj", [], 3)],
        1: [("maj", [], 2), ("maj", ["9"], 1), ("maj6", [], 1)],
        2: [("maj7", [], 2), ("maj", ["9"], 1)],
        3: [("maj7", ["9"], 2), ("maj7", [], 1)],
        4: [("maj7", ["9"], 2), ("maj6", ["9"], 1)],
        5: [("maj7", ["9"], 2), ("maj6", ["9"], 1)],
        6: [("maj7", ["9"], 2), ("maj6", ["9"], 1)],
    },
    "bare_maj_d": {
        0: [("maj", [], 3)],
        1: [("maj", [], 2), ("dom7", [], 1)],
        2: [("dom7", [], 1)],
        3: [("dom7", ["9"], 2), ("dom7", [], 1)],
        4: [("dom7", ["13"], 2), ("dom7", ["9"], 1)],
        5: [("dom7", ["b9"], 2), ("dom7", ["b13"], 1)],
        6: [("dom7", ["b9", "b13"], 2), ("dom7", ["#9"], 1)],
    },
    "bare_min": {
        0: [("min", [], 1)],
        1: [("min", [], 2), ("min", ["9"], 1)],
        2: [("min7", [], 2), ("min", [], 1)],
        3: [("min7", ["9"], 2), ("min7", [], 1)],
        4: [("min7", ["9"], 2), ("min7", ["11"], 1)],
        5: [("min7", ["9"], 2), ("min7", ["11"], 1)],
        6: [("min7", ["9"], 2), ("min7", ["11"], 1)],
    },
    "dom7": {
        0: [("dom7", [], 1)],
        1: [("dom7", [], 1)],
        2: [("dom7", [], 1)],
        3: [("dom7", ["9"], 2), ("dom7", [], 1)],
        4: [("dom7", ["13"], 2), ("dom7", ["9"], 1)],
        5: [("dom7", ["b9"], 2), ("dom7", ["b13"], 1)],
        6: [("dom7", ["b9", "b13"], 2), ("dom7", ["#9"], 1)],
    },
    "maj7": {
        0: [("maj7", [], 1)],
        1: [("maj7", [], 1)],
        2: [("maj7", [], 1)],
        3: [("maj7", ["9"], 2), ("maj7", [], 1)],
        4: [("maj7", ["9"], 1)],
        5: [("maj7", ["9"], 1)],
        6: [("maj7", ["9"], 1)],
    },
    "min7": {
        0: [("min7", [], 1)],
        1: [("min7", [], 1)],
        2: [("min7", [], 1)],
        3: [("min7", ["9"], 2), ("min7", [], 1)],
        4: [("min7", ["9"], 2), ("min7", ["11"], 1)],
        5: [("min7", ["9"], 2), ("min7", ["11"], 1)],
        6: [("min7", ["9"], 2), ("min7", ["11"], 1)],
    },
}


def test_dressing_yaml_matches_phase4_field_for_field() -> None:
    table = load_dressing_table()
    loaded = {
        name: {
            eff: [(o.quality, o.extensions, o.weight) for o in options]
            for eff, options in rows.items()
        }
        for name, rows in table.classes.items()
    }
    assert loaded == EXPECTED_TABLE


def test_every_table_option_is_phase4_6_4_legal() -> None:
    table = load_dressing_table()
    for name, rows in table.classes.items():
        for eff, options in rows.items():
            for option in options:
                assert extensions_legal(option.quality, option.extensions), (
                    f"{name} tier {eff}: {option.quality}+{option.extensions}"
                )


def test_table_covers_all_six_classes_and_seven_tiers() -> None:
    table = load_dressing_table()
    assert set(table.classes) == set(EXPECTED_TABLE)
    for rows in table.classes.values():
        assert set(rows) == set(range(7))


# --- passthrough classes (§6.3: never dressed in v1) -------------------------


@pytest.mark.parametrize(
    ("token", "key"),
    [
        ("iiø7", D_MINOR),  # min7b5
        ("I6", E_MAJOR),  # maj6
        ("i6", D_MINOR),  # min6
        ("V+", E_MAJOR),  # aug
        ("Vsus4", E_MAJOR),  # sus4
        ("Isus2", E_MAJOR),  # sus2
        ("V7sus4", E_MAJOR),  # dom7sus4
        ("v°", D_MINOR),  # dim
        ("v°7", D_MINOR),  # dim7
        ("imaj7", D_MINOR),  # minMaj7
    ],
)
def test_passthrough_classes_returned_unchanged(token: str, key: Key) -> None:
    spec = resolve_token(token, key)
    # Passthrough at the hottest tier and every function: still a single
    # unchanged option, no draw.
    for function in _FUNCTIONS:
        options = dressing_options(
            spec, was_bare=False, function=function, base_tier=6, key=key
        )
        assert options == [(spec, 1)]


# --- dressing_options selection (§10 worked-example anchors) ------------------


def _dressed_symbols(options: list[tuple[ChordSpec, int]]) -> list[tuple[str, int]]:
    return [(spec.symbol, w) for spec, w in options]


def test_example1_bare_dominant_dresses_to_b7_option() -> None:
    # §10.1: E major, dissonance 0.132 → base tier 0. Bare V (D-function) dresses
    # at effective tier 1: {maj (2), dom7 (1)} → E-major V is B/B7.
    spec = resolve_token("V", E_MAJOR)
    options = dressing_options(
        spec, was_bare=True, function="D", base_tier=0, key=E_MAJOR
    )
    assert _dressed_symbols(options) == [("B", 2), ("B7", 1)]


def test_example1_bare_tonic_and_subdominant_stay_triads() -> None:
    # base tier 0: I (T) → eff 0 pure triad; IV (S) → eff 0; vi (T) → eff 0.
    cases: list[tuple[str, Function, str]] = [
        ("I", "T", "E"),
        ("IV", "S", "A"),
        ("vi", "T", "C#m"),
    ]
    for token, function, symbol in cases:
        spec = resolve_token(token, E_MAJOR)
        options = dressing_options(
            spec, was_bare=True, function=function, base_tier=0, key=E_MAJOR
        )
        assert len(options) == 1
        assert options[0][0].symbol == symbol


def test_example2_pinned_sevenths_dress_by_effective_tier() -> None:
    # §10.2: D minor, dissonance 0.653 → base tier 4. Pinned min7/dom7 slots.
    # i7 (T) → eff 3: {Dm9 (2), Dm7 (1)}.
    i7 = resolve_token("i7", D_MINOR)
    opt = dressing_options(i7, was_bare=False, function="T", base_tier=4, key=D_MINOR)
    assert _dressed_symbols(opt) == [("Dm9", 2), ("Dm7", 1)]
    # iv7 (S) → eff 4: {Gm9 (2), Gm11 (1)}.
    iv7 = resolve_token("iv7", D_MINOR)
    opt = dressing_options(iv7, was_bare=False, function="S", base_tier=4, key=D_MINOR)
    assert _dressed_symbols(opt) == [("Gm9", 2), ("Gm11", 1)]
    # bVI7 (S) → eff 4: {Bb13 (2), Bb9 (1)}.
    bvi7 = resolve_token("bVI7", D_MINOR)
    opt = dressing_options(bvi7, was_bare=False, function="S", base_tier=4, key=D_MINOR)
    assert _dressed_symbols(opt) == [("Bb13", 2), ("Bb9", 1)]
    # V7 (D) → eff 5: {A7b9 (2), A7b13 (1)}.
    v7 = resolve_token("V7", D_MINOR)
    opt = dressing_options(v7, was_bare=False, function="D", base_tier=4, key=D_MINOR)
    assert _dressed_symbols(opt) == [("A7b9", 2), ("A7b13", 1)]


def test_dressed_specs_preserve_root_bass_roman() -> None:
    v7 = resolve_token("V7", D_MINOR)
    opt = dressing_options(v7, was_bare=False, function="D", base_tier=6, key=D_MINOR)
    for spec, _ in opt:
        assert spec.root_pc == v7.root_pc
        assert spec.roman == "V7"
        assert spec.bass_pc == v7.bass_pc


def test_all_produced_options_are_phase4_6_4_legal() -> None:
    # Every class × every base tier × every function: every produced spec legal.
    cases = [
        ("I", True, "maj"),
        ("V", True, "maj"),
        ("vi", True, "min"),
        ("I7", False, "dom7"),
        ("Imaj7", False, "maj7"),
        ("i7", False, "min7"),
    ]
    for token, was_bare, _q in cases:
        spec = resolve_token(token, D_MINOR if not was_bare else E_MAJOR)
        key = D_MINOR if not was_bare else E_MAJOR
        for base in range(7):
            for function in _FUNCTIONS:
                options = dressing_options(
                    spec, was_bare=was_bare, function=function, base_tier=base, key=key
                )
                for dressed, weight in options:
                    assert weight >= 1
                    assert extensions_legal(dressed.quality, dressed.extensions)


# --- purity / determinism ----------------------------------------------------


def test_dressing_options_is_deterministic() -> None:
    spec = resolve_token("V", E_MAJOR)
    first = dressing_options(
        spec, was_bare=True, function="D", base_tier=0, key=E_MAJOR
    )
    second = dressing_options(
        spec, was_bare=True, function="D", base_tier=0, key=E_MAJOR
    )
    assert first == second


def test_bare_major_o_function_uses_ts_table() -> None:
    # Documented reading: bare-major O-function reads the T/S table (non-D
    # default). #IV in E major is O-function; at base tier 2 → eff 2 →
    # {maj7 (2), maj+9 (1)} shape, not the dominant table.
    spec = resolve_token("#IV", E_MAJOR)
    opts_o = dressing_options(
        spec, was_bare=True, function="O", base_tier=3, key=E_MAJOR
    )
    # Same as an S-function bare major would produce at the same base tier.
    opts_s = dressing_options(
        spec, was_bare=True, function="S", base_tier=3, key=E_MAJOR
    )
    assert [(s.quality, s.extensions, w) for s, w in opts_o] == [
        (s.quality, s.extensions, w) for s, w in opts_s
    ]
    assert all(s.quality in ("maj7", "maj6") for s, _ in opts_o)


def test_injected_table_matches_default() -> None:
    table = load_dressing_table()
    assert isinstance(table, DressingTable)
    spec = resolve_token("i7", D_MINOR)
    with_default = dressing_options(
        spec, was_bare=False, function="T", base_tier=4, key=D_MINOR
    )
    with_injected = dressing_options(
        spec, was_bare=False, function="T", base_tier=4, key=D_MINOR, table=table
    )
    assert with_default == with_injected
