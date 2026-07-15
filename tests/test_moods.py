"""Tests for the mood model (PHASE_2 §4)."""

import pytest

from trackgen.interpreter.moods import (
    DERIVED_KEYS,
    MODE_LADDER,
    MOOD_VOCABULARY,
    MoodLoadError,
    derived_defaults,
    load_moods,
)

# PHASE_2 §4.4 — normative; do not edit a number to match code output.
# mood -> (tmpC, densN, dissN, dynB, dynR, artic, layers, hRhy, regB, bright,
#          attack, space)
_Row = tuple[
    float, float, float, float, float, float, int, float, float, float, float, float
]
EXPECTED_TABLE: dict[str, _Row] = {
    "happy": (
        118.1,
        0.690,
        0.235,
        0.650,
        0.210,
        0.340,
        4,
        1.0,
        0.188,
        0.835,
        0.660,
        0.360,
    ),
    "energetic": (
        139.5,
        0.830,
        0.385,
        0.750,
        0.270,
        0.180,
        4,
        1.0,
        0.113,
        0.805,
        0.820,
        0.220,
    ),
    "triumphant": (
        125.7,
        0.743,
        0.243,
        0.688,
        0.232,
        0.280,
        4,
        1.0,
        0.200,
        0.873,
        0.720,
        0.307,
    ),
    "calm": (
        76.3,
        0.323,
        0.235,
        0.388,
        0.247,
        0.760,
        3,
        0.5,
        0.138,
        0.450,
        0.240,
        0.728,
    ),
    "dreamy": (
        82.9,
        0.393,
        0.295,
        0.438,
        0.217,
        0.680,
        3,
        0.5,
        0.087,
        0.588,
        0.320,
        0.850,
    ),
    "romantic": (
        90.1,
        0.463,
        0.205,
        0.488,
        0.188,
        0.600,
        3,
        1.0,
        0.163,
        0.450,
        0.400,
        0.588,
    ),
    "nostalgic": (
        86.5,
        0.428,
        0.310,
        0.463,
        0.202,
        0.640,
        3,
        1.0,
        0.075,
        0.588,
        0.360,
        0.622,
    ),
    "melancholic": (
        68.0,
        0.393,
        0.550,
        0.438,
        0.217,
        0.680,
        3,
        0.5,
        -0.125,
        0.333,
        0.320,
        0.657,
    ),
    "dark": (
        80.0,
        0.498,
        0.565,
        0.513,
        0.172,
        0.560,
        3,
        1.0,
        -0.138,
        0.362,
        0.440,
        0.552,
    ),
    "mysterious": (
        88.3,
        0.445,
        0.460,
        0.475,
        0.195,
        0.620,
        3,
        1.0,
        -0.050,
        0.445,
        0.380,
        0.605,
    ),
    "tense": (
        123.1,
        0.725,
        0.610,
        0.450,
        0.350,
        0.300,
        4,
        1.0,
        -0.113,
        0.490,
        0.700,
        0.325,
    ),
    "aggressive": (
        146.0,
        0.795,
        0.685,
        0.800,
        0.255,
        0.220,
        4,
        1.0,
        -0.150,
        0.750,
        0.780,
        0.255,
    ),
}

_COLUMNS = (
    "noteDensityNorm",
    "dissonanceNorm",
    "dynamicsBase",
    "dynamicsRange",
    "articulationLegato",
    "layersMax",
    "harmonicRhythmBase",
    "registerBias",
    "brightness",
    "attackHardness",
    "space",
)

# The 7 moods that carry overrides per PHASE_2 §4.3, and exactly which keys.
EXPECTED_OVERRIDE_KEYS = {
    "melancholic": {"tempoCenter"},
    "dark": {"tempoCenter"},
    "aggressive": {"tempoCenter", "brightness", "dynamicsBase"},
    "tense": {"dynamicsBase", "dynamicsRange"},
    "romantic": {"brightness"},
    "calm": {"brightness"},
    "dreamy": {"space"},
}


@pytest.mark.parametrize("mood", MOOD_VOCABULARY)
def test_derived_defaults_match_phase2_table(mood: str) -> None:
    table = load_moods()
    derived = derived_defaults(mood, table)
    expected = EXPECTED_TABLE[mood]

    assert round(derived["tempoCenter"], 1) == expected[0]
    for name, exp_val in zip(_COLUMNS, expected[1:], strict=True):
        assert derived[name] == pytest.approx(exp_val, abs=1e-9), name


def test_load_moods_succeeds_and_covers_vocabulary() -> None:
    table = load_moods()
    assert set(table.moods) == set(MOOD_VOCABULARY)
    assert len(table.moods) == 12


def test_all_anchors_in_valid_range() -> None:
    table = load_moods()
    for mood, row in table.moods.items():
        assert -1.0 <= row.valence <= 1.0, mood
        assert -1.0 <= row.arousal <= 1.0, mood


def test_override_bearing_moods_match_phase2_4_3() -> None:
    table = load_moods()
    for mood, row in table.moods.items():
        expected_keys = EXPECTED_OVERRIDE_KEYS.get(mood, set())
        assert set(row.overrides) == expected_keys, mood


def test_mood_vocabulary_has_12_entries() -> None:
    assert len(MOOD_VOCABULARY) == 12
    assert len(set(MOOD_VOCABULARY)) == 12


def test_mode_ladder() -> None:
    assert MODE_LADDER == ("major", "mixolydian", "dorian", "minor", "phrygian")


def test_derived_keys_are_the_overridable_names() -> None:
    # PHASE_2 §4.2 enumerates 12 concrete override-allowed names (the "13
    # derived values" prose count includes the non-overridable "tempo range"
    # row, which is not a standalone field).
    assert len(DERIVED_KEYS) == 12
    assert set(DERIVED_KEYS) == {
        "tempoCenter",
        "noteDensityNorm",
        "dissonanceNorm",
        "dynamicsBase",
        "dynamicsRange",
        "articulationLegato",
        "layersMax",
        "harmonicRhythmBase",
        "registerBias",
        "brightness",
        "attackHardness",
        "space",
    }


def test_load_moods_wraps_bad_yaml(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import trackgen.interpreter.moods as moods_module

    (tmp_path / "moods.yaml").write_text("not: [valid, yaml, :::")
    monkeypatch.setattr(moods_module, "__file__", str(tmp_path / "fake_module.py"))

    with pytest.raises(MoodLoadError):
        moods_module.load_moods()


def test_load_moods_wraps_validation_error(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import trackgen.interpreter.moods as moods_module

    (tmp_path / "moods.yaml").write_text("moods: {}\n")  # missing all 12 moods
    monkeypatch.setattr(moods_module, "__file__", str(tmp_path / "fake_module.py"))

    with pytest.raises(MoodLoadError):
        moods_module.load_moods()
