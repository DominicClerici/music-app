"""Tests for the Phase 7 engine data (PHASE_7 §5.1, §5.2; SESSION_13 T1, DoD 2).

Covers the §5.1 `mod_defaults.yaml` field-for-field transcription (the guard
against a typo or a §5.1 arbitration flag), the `allowlist.yaml` load +
`is_legal` behaviour, the load-bearing allowlist-coverage assertion (every
mod_defaults param is legal for its role's reference engine class), and the
`MappingEntry` well-formedness caps (§3.1)."""

import pytest
from pydantic import ValidationError

from trackgen.sound.allowlist import Allowlist, load_allowlist
from trackgen.sound.mod_defaults import (
    DrumModDefaults,
    load_mod_defaults,
)
from trackgen.sound.models import MappingEntry


def _entry_tuple(entry: MappingEntry) -> tuple[str, float, float, str]:
    return (entry.param, entry.min, entry.max, entry.curve)


# --- §5.1 field-for-field transcription -------------------------------------


def test_mod_defaults_bass_field_for_field() -> None:
    bass = load_mod_defaults().bass
    assert [_entry_tuple(e) for e in bass.brightness] == [
        ("filterEnvelope.baseFrequency", 120, 2500, "exp"),
        ("filter.Q", 0.8, 2.0, "linear"),
    ]
    assert [_entry_tuple(e) for e in bass.attack_hardness] == [
        ("envelope.attack", 0.12, 0.001, "exp"),
        ("filterEnvelope.octaves", 1.5, 3.5, "linear"),
    ]
    assert bass.space == ()


def test_mod_defaults_comping_field_for_field() -> None:
    comping = load_mod_defaults().comping
    assert [_entry_tuple(e) for e in comping.brightness] == [
        ("filterEnvelope.baseFrequency", 400, 8000, "exp"),
    ]
    assert [_entry_tuple(e) for e in comping.attack_hardness] == [
        ("envelope.attack", 0.08, 0.001, "exp"),
    ]
    assert [_entry_tuple(e) for e in comping.space] == [
        ("mix.sends.reverb", -24, -9, "linear"),
    ]


def test_mod_defaults_pads_field_for_field() -> None:
    pads = load_mod_defaults().pads
    assert [_entry_tuple(e) for e in pads.brightness] == [
        ("filterEnvelope.baseFrequency", 350, 9000, "exp"),
    ]
    assert [_entry_tuple(e) for e in pads.attack_hardness] == [
        ("envelope.attack", 1.2, 0.005, "exp"),
    ]
    assert [_entry_tuple(e) for e in pads.space] == [
        ("mix.sends.reverb", -18, -6, "linear"),
    ]


def test_mod_defaults_drums_field_for_field() -> None:
    drums = load_mod_defaults().drums
    brightness = {
        v: [_entry_tuple(e) for e in es] for v, es in drums.brightness.items()
    }
    assert brightness == {
        "hats": [("resonance", 2000, 5500, "exp")],
        "ride": [("resonance", 3500, 7000, "exp")],
        "crash": [("resonance", 2500, 5000, "exp")],
        "snare": [("noise.playbackRate", 2.0, 4.0, "linear")],
    }
    space = {v: [_entry_tuple(e) for e in es] for v, es in drums.space.items()}
    assert space == {
        "snare": [("mix.sends.reverb", -18, -6, "linear")],
        "tom_low": [("mix.sends.reverb", -16, -8, "linear")],
        "tom_mid": [("mix.sends.reverb", -16, -8, "linear")],
        "tom_high": [("mix.sends.reverb", -16, -8, "linear")],
        "crash": [("mix.sends.reverb", -14, -8, "linear")],
    }


def test_bass_space_is_empty() -> None:
    # D4/§5.1: bass stays dry regardless of `space`.
    assert load_mod_defaults().bass.space == ()


def test_drums_have_no_attack_hardness() -> None:
    # D4: attackHardness never touches drums. Structural: not a field, and
    # `extra="forbid"` rejects any authored attackHardness table.
    assert set(DrumModDefaults.model_fields) == {"brightness", "space"}
    with pytest.raises(ValidationError):
        DrumModDefaults.model_validate(
            {
                "brightness": {"snare": []},
                "space": {"snare": []},
                "attackHardness": {"snare": []},
            }
        )


# --- allowlist load + is_legal ----------------------------------------------


def test_allowlist_loads() -> None:
    allow = load_allowlist()
    assert isinstance(allow, Allowlist)
    assert "MonoSynth" in allow.classes


def test_is_legal_positive_samples() -> None:
    allow = load_allowlist()
    assert allow.is_legal("MonoSynth", "filterEnvelope.baseFrequency")
    assert allow.is_legal("MonoSynth", "filter.Q")
    assert allow.is_legal("MonoSynth", "envelope.attackCurve")
    assert allow.is_legal("MetalSynth", "resonance")
    assert allow.is_legal("NoiseSynth", "noise.playbackRate")
    assert allow.is_legal("FMSynth", "modulationIndex")
    assert allow.is_legal("FMSynth", "modulationEnvelope.release")
    assert allow.is_legal("MembraneSynth", "pitchDecay")
    assert allow.is_legal("Reverb", "decay")
    assert allow.is_legal("Reverb", "preDelay")
    assert allow.is_legal("Compressor", "threshold")
    assert allow.is_legal("Limiter", "threshold")
    assert allow.is_legal("Filter", "frequency")
    assert allow.is_legal("StereoWidener", "width")


def test_is_legal_negatives() -> None:
    allow = load_allowlist()
    # Un-seeded path on a known class.
    assert not allow.is_legal("MonoSynth", "bogus.path")
    assert not allow.is_legal("MetalSynth", "filterEnvelope.baseFrequency")
    # Unknown class (not in the allowlist) is illegal, not an error.
    assert not allow.is_legal("DuoSynth", "volume")
    assert not allow.is_legal("PluckSynth", "attackNoise")


# --- PHASE_8 §3.7 allowlist growth (Vibrato / AutoFilter) -------------------


def test_allowlist_growth_vibrato_autofilter() -> None:
    """PHASE_8 §3.7 (amends PHASE_7 §5.2): Vibrato/AutoFilter allowlist paths,
    pre-seeded in Phase 7. Guards against removal or alteration of either
    entry."""
    allow = load_allowlist()
    assert allow.classes["Vibrato"] == frozenset({"frequency", "depth", "wet"})
    assert allow.classes["AutoFilter"] == frozenset(
        {"frequency", "baseFrequency", "octaves", "depth", "wet"}
    )


# --- coverage: every mod_defaults param is legal for its reference class -----

_PITCHED_REFERENCE_CLASS = {
    "bass": "MonoSynth",
    "comping": "MonoSynth",
    "pads": "MonoSynth",
}
_DRUM_BRIGHTNESS_CLASS = {
    "hats": "MetalSynth",
    "ride": "MetalSynth",
    "crash": "MetalSynth",
    "snare": "NoiseSynth",
}


def test_mod_defaults_params_legal_for_reference_class() -> None:
    """Load-bearing (SESSION_13 T1): every param any mod_defaults mapping targets
    is `is_legal` for that role's reference engine class — or is the `mix.sends`
    block path (routed to the mix block, not the options object, so exempt from
    the allowlist). Proves the allowlist seed covers §5.1."""
    allow = load_allowlist()
    mod = load_mod_defaults()

    for role, cls in _PITCHED_REFERENCE_CLASS.items():
        role_mod = getattr(mod, role)
        for directive in ("brightness", "attack_hardness", "space"):
            for entry in getattr(role_mod, directive):
                if entry.param.startswith("mix."):
                    continue
                assert allow.is_legal(cls, entry.param), (
                    f"{role}.{directive}: {entry.param} not legal for {cls}"
                )

    for voice, entries in mod.drums.brightness.items():
        cls = _DRUM_BRIGHTNESS_CLASS[voice]
        for entry in entries:
            assert allow.is_legal(cls, entry.param), (
                f"drums.brightness[{voice}]: {entry.param} not legal for {cls}"
            )

    # Drum space maps are all reverb sends (mix-block paths), never option paths.
    for entries in mod.drums.space.values():
        for entry in entries:
            assert entry.param == "mix.sends.reverb"


# --- MappingEntry well-formedness caps (§3.1) -------------------------------


def test_mapping_entry_rejects_bad_curve() -> None:
    with pytest.raises(ValidationError):
        MappingEntry.model_validate(
            {"param": "filter.Q", "min": 1.0, "max": 2.0, "curve": "log"}
        )


def test_mapping_entry_rejects_exp_min_zero() -> None:
    with pytest.raises(ValidationError):
        MappingEntry.model_validate(
            {
                "param": "filterEnvelope.baseFrequency",
                "min": 0,
                "max": 2500,
                "curve": "exp",
            }
        )


def test_mapping_entry_rejects_exp_max_nonpositive() -> None:
    with pytest.raises(ValidationError):
        MappingEntry.model_validate(
            {"param": "resonance", "min": 100, "max": 0, "curve": "exp"}
        )
    with pytest.raises(ValidationError):
        MappingEntry.model_validate(
            {"param": "resonance", "min": 100, "max": -5, "curve": "exp"}
        )


def test_mapping_entry_accepts_inverted_linear_range() -> None:
    # Inverted ranges (min > max) are legal (§3.1); a linear one needs no
    # positivity, so it must construct even with a zero/negative endpoint.
    entry = MappingEntry.model_validate(
        {"param": "envelope.attack", "min": 0.12, "max": 0.001, "curve": "linear"}
    )
    assert entry.min > entry.max
