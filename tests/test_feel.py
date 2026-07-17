"""Tests for the engine feel data (PHASE_6 §5.3, DoD 2)."""

from copy import deepcopy
from typing import Any

import pytest

from trackgen.humanize import feel as feel_mod
from trackgen.humanize.feel import (
    BeatClassMap,
    FeelData,
    FeelLoadError,
    OffsetProfile,
    load_feel,
)


def _valid_feel_dict() -> dict[str, Any]:
    """The §5.3 feel data as a raw dict — the committed values, so mutating a
    single field yields an otherwise-valid over-cap fixture (non-vacuous)."""
    return {
        "offsetsMs": {
            "swung": {
                "kick": 0,
                "snare": 3,
                "hats": -3,
                "ride": 0,
                "toms": 0,
                "crash": 0,
                "perc": 0,
                "bass": -2,
                "comping": {"down": 18, "back2": 6, "beat3": 10, "back4": 4, "off": 2},
                "pads": 0,
            },
            "straight": {
                "kick": 0,
                "snare": {"down": 4, "back2": 8, "beat3": 4, "back4": 6, "off": 4},
                "hats": -2,
                "ride": 0,
                "toms": 0,
                "crash": 0,
                "perc": 0,
                "bass": 2,
                "comping": 5,
                "pads": 0,
            },
        },
        "jitterMs": {
            "kick": 4,
            "snare": 5,
            "hats": 5,
            "ride": 4,
            "toms": 5,
            "crash": 0,
            "perc": 5,
            "bass": 6,
            "comping": 8,
            "pads": 0,
        },
        "accent": {
            "down": 0.03,
            "back2": 0.0,
            "beat3": 0.015,
            "back4": 0.0,
            "off": -0.03,
        },
        "velJitter": {"base": 0.04, "rangeScale": 0.08},
        "bassLegato": 0.95,
    }


# --- load / values ----------------------------------------------------------


def test_load_feel_swung_offsets_field_for_field() -> None:
    feel = load_feel()
    swung = feel.offsets_ms.swung
    assert swung.kick == 0
    assert swung.snare == 3
    assert swung.hats == -3
    assert swung.ride == 0
    assert swung.toms == 0
    assert swung.crash == 0
    assert swung.perc == 0
    assert swung.bass == -2
    assert swung.pads == 0
    assert swung.comping == BeatClassMap(down=18, back2=6, beat3=10, back4=4, off=2)


def test_load_feel_straight_offsets_field_for_field() -> None:
    feel = load_feel()
    straight = feel.offsets_ms.straight
    assert straight.kick == 0
    assert straight.hats == -2
    assert straight.ride == 0
    assert straight.toms == 0
    assert straight.crash == 0
    assert straight.perc == 0
    assert straight.bass == 2
    assert straight.comping == 5
    assert straight.pads == 0
    assert straight.snare == BeatClassMap(down=4, back2=8, beat3=4, back4=6, off=4)


def test_load_feel_jitter_accent_veljitter_legato() -> None:
    feel = load_feel()
    jitter = feel.jitter_ms
    assert (jitter.kick, jitter.snare, jitter.hats, jitter.ride, jitter.toms) == (
        4,
        5,
        5,
        4,
        5,
    )
    assert (jitter.crash, jitter.perc, jitter.bass, jitter.comping, jitter.pads) == (
        0,
        5,
        6,
        8,
        0,
    )
    accent = feel.accent
    assert accent.down == 0.03
    assert accent.back2 == 0.0
    assert accent.beat3 == 0.015
    assert accent.back4 == 0.0
    assert accent.off == -0.03
    assert feel.vel_jitter.base == 0.04
    assert feel.vel_jitter.range_scale == 0.08
    assert feel.bass_legato == 0.95


def test_offset_accessor_scalar_vs_map() -> None:
    feel = load_feel()
    swung = feel.offsets_ms.swung
    # Scalar row: the same value for every beat class.
    for beat_class in ("down", "back2", "beat3", "back4", "off"):
        assert swung.offset("snare", beat_class) == 3
    # Map row: indexed per beat class.
    assert swung.offset("comping", "down") == 18
    assert swung.offset("comping", "back2") == 6
    assert swung.offset("comping", "beat3") == 10
    assert swung.offset("comping", "back4") == 4
    assert swung.offset("comping", "off") == 2
    # Straight snare is a map; comping a scalar — the mirror case.
    straight = feel.offsets_ms.straight
    assert straight.offset("snare", "back2") == 8
    assert straight.offset("comping", "off") == 5


def test_jitter_and_accent_accessors() -> None:
    feel = load_feel()
    assert feel.jitter_ms.at("comping") == 8
    assert feel.jitter_ms.at("pads") == 0
    assert feel.accent.at("down") == 0.03
    assert feel.accent.at("off") == -0.03


def test_valid_feel_dict_validates() -> None:
    # Guards the rejection fixtures: the base dict is otherwise valid, so each
    # single-field mutation below is the *only* reason validation fails.
    assert FeelData.model_validate(_valid_feel_dict()).bass_legato == 0.95


# --- rejection fixtures (one per cap class) ----------------------------------


def test_offset_over_cap_rejected() -> None:
    data = _valid_feel_dict()
    data["offsetsMs"]["swung"]["snare"] = 26  # otherwise-valid dict, one over-cap value
    with pytest.raises(ValueError, match="offset"):
        FeelData.model_validate(data)


def test_offset_map_entry_over_cap_rejected() -> None:
    # The cap covers map entries too, not just scalar rows.
    with pytest.raises(ValueError, match="offset"):
        OffsetProfile.model_validate(
            {
                "kick": 0,
                "snare": {"down": 26, "back2": 8, "beat3": 4, "back4": 6, "off": 4},
                "hats": -2,
                "ride": 0,
                "toms": 0,
                "crash": 0,
                "perc": 0,
                "bass": 2,
                "comping": 5,
                "pads": 0,
            }
        )


def test_jitter_over_cap_rejected() -> None:
    data = _valid_feel_dict()
    data["jitterMs"]["comping"] = 11  # otherwise-valid dict, one over-cap value
    with pytest.raises(ValueError, match="jitter"):
        FeelData.model_validate(data)


def test_accent_over_cap_rejected() -> None:
    data = _valid_feel_dict()
    data["accent"]["down"] = 0.06  # otherwise-valid dict, one over-cap value
    with pytest.raises(ValueError, match="accent"):
        FeelData.model_validate(data)


def test_unknown_key_rejected() -> None:
    data = deepcopy(_valid_feel_dict())
    data["offsetsMs"]["swung"]["cowbell"] = 0
    with pytest.raises(ValueError):
        FeelData.model_validate(data)


# --- load_feel() wrapper (moods.py-convention parity) ------------------------


def test_load_feel_wraps_non_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feel_mod, "_read_yaml", lambda _path: [1, 2, 3])
    with pytest.raises(FeelLoadError, match="must be a mapping"):
        load_feel()


def test_load_feel_wraps_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = _valid_feel_dict()
    bad["accent"]["down"] = 0.06  # over the |accent| <= 0.05 cap
    monkeypatch.setattr(feel_mod, "_read_yaml", lambda _path: bad)
    with pytest.raises(FeelLoadError, match="invalid feel data"):
        load_feel()
