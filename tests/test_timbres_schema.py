"""Tests for the real ``timbres.yaml`` schema + TB1–TB9 (PHASE_7 §4; SESSION_13
T3, DoD 1 partial — validators + one rejection fixture per rule class + the TB1
function; "reference files load clean" is the wired Chunk-2 check).

The valid fixture transcribes a minimal one-flavor-per-role subset of the §8.1
pop_rock recipes (nine kit voices, a pitched flavor each, bus, master ending in
a Limiter). Each rejection fixture is OTHERWISE-VALID and trips ONLY its targeted
rule (non-vacuous), asserting on the rule's tag/text. A final test proves the
schema can express the §4.7 riser recipe. The real ``styles/*/timbres.yaml`` are
untouched (they stay stub-format through Chunk 1).
"""

from typing import Any

import pytest
from pydantic import ValidationError

from trackgen.sound.timbres import (
    KIT_VOICE_IDS,
    PitchedFlavor,
    TimbresConfig,
    check_flavor_completeness,
)

# --- valid fixture builders (fresh tree each call — safe to mutate) ----------


def _tom_patch() -> dict[str, Any]:
    return {
        "type": "MembraneSynth",
        "options": {
            "pitchDecay": 0.05,
            "octaves": 5,
            "oscillator": {"type": "sine"},
            "envelope": {"attack": 0.001, "decay": 0.35, "sustain": 0, "release": 0.3},
        },
    }


def _kit() -> dict[str, Any]:
    return {
        "kick": {
            "midi": 24,
            "patch": {
                "type": "MembraneSynth",
                "options": {
                    "pitchDecay": 0.05,
                    "octaves": 4,
                    "oscillator": {"type": "sine"},
                    "envelope": {
                        "attack": 0.001,
                        "decay": 0.4,
                        "sustain": 0.01,
                        "release": 1.4,
                        "attackCurve": "exponential",
                    },
                },
            },
            "mix": {"volumeDb": -9, "pan": 0},
        },
        "snare": {
            "patch": {
                "type": "NoiseSynth",
                "options": {
                    "volume": -4,
                    "noise": {"type": "pink"},
                    "envelope": {
                        "attack": 0.001,
                        "decay": 0.13,
                        "sustain": 0,
                        "release": 0.03,
                    },
                },
            },
            "mix": {"volumeDb": -10.5, "pan": 0},
        },
        "hats": {
            "midi": 80,
            "patch": {
                "type": "MetalSynth",
                "options": {
                    "volume": -12,
                    "frequency": 250,
                    "harmonicity": 5.1,
                    "modulationIndex": 32,
                    "octaves": 1.5,
                    "envelope": {"attack": 0.001, "decay": 0.05, "release": 0.01},
                },
            },
            "mix": {"volumeDb": -17, "pan": 0.3, "sends": {"reverb": -20}},
        },
        "ride": {
            "midi": 82,
            "patch": {
                "type": "MetalSynth",
                "options": {
                    "volume": -12,
                    "frequency": 400,
                    "harmonicity": 12,
                    "modulationIndex": 16,
                    "octaves": 1,
                    "envelope": {"attack": 0.001, "decay": 0.35, "release": 0.5},
                },
            },
            "mix": {"volumeDb": -19, "pan": -0.2, "sends": {"reverb": -18}},
        },
        "crash": {
            "midi": 84,
            "patch": {
                "type": "MetalSynth",
                "options": {
                    "volume": -12,
                    "frequency": 300,
                    "harmonicity": 5.1,
                    "modulationIndex": 32,
                    "octaves": 1.5,
                    "envelope": {"attack": 0.001, "decay": 1.5, "release": 1.5},
                },
            },
            "mix": {"volumeDb": -14, "pan": -0.35},
        },
        "tom_low": {
            "midi": 43,
            "patch": _tom_patch(),
            "mix": {"volumeDb": -13, "pan": -0.3},
        },
        "tom_mid": {
            "midi": 47,
            "patch": _tom_patch(),
            "mix": {"volumeDb": -13, "pan": -0.1},
        },
        "tom_high": {
            "midi": 50,
            "patch": _tom_patch(),
            "mix": {"volumeDb": -13, "pan": 0.15},
        },
        "perc": {
            "patch": {
                "type": "NoiseSynth",
                "options": {
                    "volume": -6,
                    "noise": {"type": "white"},
                    "envelope": {
                        "attack": 0.001,
                        "decay": 0.05,
                        "sustain": 0,
                        "release": 0.02,
                    },
                },
            },
            "mix": {"volumeDb": -16, "pan": 0.2},
        },
    }


def _bass() -> dict[str, Any]:
    return {
        "engine": {"type": "MonoSynth"},
        "base": {
            "oscillator": {"type": "square8"},
            "envelope": {"decay": 0.3, "sustain": 0.4, "release": 0.8},
            "filter": {"type": "lowpass", "rolloff": -12},
            "filterEnvelope": {
                "attack": 0.001,
                "decay": 0.7,
                "sustain": 0.1,
                "release": 0.8,
            },
        },
        "effects": [],
        "mix": {"volumeDb": -11, "pan": 0},
    }


def _comping() -> dict[str, Any]:
    return {
        "engine": {"type": "PolySynth", "voice": "MonoSynth", "maxPolyphony": 12},
        "base": {
            "oscillator": {"type": "triangle"},
            "envelope": {"decay": 0.5, "sustain": 0.3, "release": 0.6},
            "filter": {"type": "lowpass", "rolloff": -12, "Q": 1},
            "filterEnvelope": {
                "attack": 0.002,
                "decay": 0.4,
                "sustain": 0.4,
                "release": 0.6,
                "octaves": 2.2,
            },
        },
        "effects": [
            {
                "type": "Chorus",
                "options": {
                    "frequency": 1.5,
                    "delayTime": 3.5,
                    "depth": 0.4,
                    "wet": 0.3,
                },
            }
        ],
        "mix": {"volumeDb": -13, "pan": -0.3},
    }


def _pads() -> dict[str, Any]:
    return {
        "engine": {"type": "PolySynth", "voice": "MonoSynth", "maxPolyphony": 8},
        "base": {
            "oscillator": {"type": "fatsawtooth", "count": 3, "spread": 30},
            "envelope": {"decay": 0.6, "sustain": 0.5, "release": 1.6},
            "filter": {"type": "lowpass", "rolloff": -12, "Q": 1},
            "filterEnvelope": {
                "attack": 0.4,
                "decay": 0.8,
                "sustain": 0.6,
                "release": 1.6,
                "octaves": 2,
            },
        },
        "effects": [
            {
                "type": "Chorus",
                "options": {"frequency": 0.8, "delayTime": 4, "depth": 0.5, "wet": 0.3},
            },
            {"type": "StereoWidener", "options": {"width": 0.7}},
        ],
        "mix": {"volumeDb": -18, "pan": 0},
    }


def _valid_config_dict() -> dict[str, Any]:
    return {
        "flavors": {
            "drums": {"acoustic_kit": {"kit": _kit()}},
            "bass": {"electric_fingered": _bass()},
            "comping": {"clean_electric": _comping()},
            "pads": {"warm_analog": _pads()},
        },
        "bus": {
            "reverb": {
                "decay": [0.8, 3.0],
                "preDelay": [0.01, 0.03],
                "returnFilterHz": 350,
            }
        },
        "master": [
            {
                "type": "Compressor",
                "options": {
                    "threshold": -20,
                    "ratio": 2,
                    "attack": 0.03,
                    "release": 0.25,
                },
            },
            {"type": "Limiter", "options": {"threshold": -1}},
        ],
    }


def _declared() -> dict[str, set[str]]:
    return {
        "drums": {"acoustic_kit"},
        "bass": {"electric_fingered"},
        "comping": {"clean_electric"},
        "pads": {"warm_analog"},
    }


# --- valid fixture loads clean ----------------------------------------------


def test_valid_config_loads() -> None:
    config = TimbresConfig.model_validate(_valid_config_dict())
    assert set(config.flavors.drums["acoustic_kit"].kit) == set(KIT_VOICE_IDS)
    assert config.master[-1].type == "Limiter"


def test_flavor_completeness_passes_when_equal() -> None:
    config = TimbresConfig.model_validate(_valid_config_dict())
    # No raise when the timbres id set equals the declared set per role.
    check_flavor_completeness(config, _declared())


# --- TB1: cross-file completeness (standalone) ------------------------------


def test_tb1_rejects_dangling_declaration() -> None:
    # Declared id with no recipe in timbres.
    config = TimbresConfig.model_validate(_valid_config_dict())
    declared = _declared()
    declared["bass"] = {"electric_fingered", "electric_picked"}
    with pytest.raises(ValueError, match="TB1"):
        check_flavor_completeness(config, declared)


def test_tb1_rejects_orphan_recipe() -> None:
    # Recipe present in timbres but not declared.
    config = TimbresConfig.model_validate(_valid_config_dict())
    declared = _declared()
    declared["comping"] = set()
    with pytest.raises(ValueError, match="TB1"):
        check_flavor_completeness(config, declared)


# --- TB2: engine whitelist / PolySynth rules --------------------------------


def test_tb2_rejects_polysynth_missing_voice() -> None:
    cfg = _valid_config_dict()
    cfg["flavors"]["comping"]["clean_electric"]["engine"] = {
        "type": "PolySynth",
        "maxPolyphony": 12,
    }
    with pytest.raises(ValidationError, match="TB2"):
        TimbresConfig.model_validate(cfg)


# --- TB3: base option paths in the allowlist --------------------------------


def test_tb3_rejects_base_path_not_in_allowlist() -> None:
    cfg = _valid_config_dict()
    cfg["flavors"]["bass"]["electric_fingered"]["base"]["oscillator"]["bogusField"] = 5
    with pytest.raises(ValidationError, match="TB3"):
        TimbresConfig.model_validate(cfg)


# --- TB4: effect whitelist / paths / master ends in Limiter -----------------


def test_tb4_rejects_master_not_ending_in_limiter() -> None:
    cfg = _valid_config_dict()
    cfg["master"] = [
        {"type": "Limiter", "options": {"threshold": -1}},
        {
            "type": "Compressor",
            "options": {"threshold": -20, "ratio": 2, "attack": 0.03, "release": 0.25},
        },
    ]
    with pytest.raises(ValidationError, match="Limiter"):
        TimbresConfig.model_validate(cfg)


def test_tb4_rejects_insert_path_not_in_allowlist() -> None:
    cfg = _valid_config_dict()
    cfg["flavors"]["comping"]["clean_electric"]["effects"][0]["options"]["bogus"] = 1
    with pytest.raises(ValidationError, match="TB4"):
        TimbresConfig.model_validate(cfg)


# --- TB5: kit ids / midi presence -------------------------------------------


def test_tb5_rejects_missing_kit_voice() -> None:
    cfg = _valid_config_dict()
    del cfg["flavors"]["drums"]["acoustic_kit"]["kit"]["perc"]
    with pytest.raises(ValidationError, match="TB5"):
        TimbresConfig.model_validate(cfg)


def test_tb5_rejects_midi_on_noise_synth() -> None:
    cfg = _valid_config_dict()
    cfg["flavors"]["drums"]["acoustic_kit"]["kit"]["snare"]["midi"] = 60
    with pytest.raises(ValidationError, match="TB5"):
        TimbresConfig.model_validate(cfg)


# --- TB6: mix caps / declared-bus sends -------------------------------------


def test_tb6_rejects_volume_db_over_cap() -> None:
    cfg = _valid_config_dict()
    cfg["flavors"]["bass"]["electric_fingered"]["mix"]["volumeDb"] = 7
    with pytest.raises(ValidationError, match="less than or equal to 6"):
        TimbresConfig.model_validate(cfg)


def test_tb6_rejects_send_to_undeclared_bus() -> None:
    cfg = _valid_config_dict()
    cfg["flavors"]["comping"]["clean_electric"]["mix"]["sends"] = {"delay": -10}
    with pytest.raises(ValidationError, match="TB6"):
        TimbresConfig.model_validate(cfg)


# --- TB7: mod directive keys / effective legality / base XOR mod ------------


def test_tb7_rejects_base_and_mod_targeting_same_path() -> None:
    # A base path also targeted by an (inherited) default mapping: bass default
    # brightness maps filterEnvelope.baseFrequency, so authoring it in base too
    # violates base XOR mod (§3.3).
    cfg = _valid_config_dict()
    cfg["flavors"]["bass"]["electric_fingered"]["base"]["filterEnvelope"][
        "baseFrequency"
    ] = 500
    with pytest.raises(ValidationError, match="base XOR mod"):
        TimbresConfig.model_validate(cfg)


def test_tb7_rejects_fixed_send_with_space_mapping() -> None:
    # §4.2: the base mix.sends.reverb is omitted when a space mapping targets it.
    # comping inherits a space→mix.sends.reverb default, so authoring a fixed
    # reverb send too is two authorities for one value (base XOR mod, §3.3).
    cfg = _valid_config_dict()
    cfg["flavors"]["comping"]["clean_electric"]["mix"]["sends"] = {"reverb": -12}
    with pytest.raises(ValidationError, match="base XOR mod requires the fixed"):
        TimbresConfig.model_validate(cfg)


def test_tb7_rejects_drum_attack_hardness_mod() -> None:
    # D4: attackHardness never touches drums — the closed KitMod field set rejects
    # an authored `attackHardness` override as an extra key.
    cfg = _valid_config_dict()
    cfg["flavors"]["drums"]["acoustic_kit"]["mod"] = {
        "attackHardness": {
            "snare": [
                {"param": "envelope.attack", "min": 0.02, "max": 0.001, "curve": "exp"}
            ]
        }
    }
    with pytest.raises(ValidationError, match="Extra inputs"):
        TimbresConfig.model_validate(cfg)


def test_tb7_rejects_mod_param_illegal_for_engine_class() -> None:
    # modulationIndex is not a MonoSynth lever, so a bass brightness override
    # onto it is illegal for the engine class.
    cfg = _valid_config_dict()
    cfg["flavors"]["bass"]["electric_fingered"]["mod"] = {
        "brightness": [{"param": "modulationIndex", "min": 1, "max": 5, "curve": "exp"}]
    }
    with pytest.raises(ValidationError, match="TB7"):
        TimbresConfig.model_validate(cfg)


# --- TB8: reverb bus ranges -------------------------------------------------


def test_tb8_rejects_decay_lo_zero() -> None:
    cfg = _valid_config_dict()
    cfg["bus"]["reverb"]["decay"] = [0, 3.0]
    with pytest.raises(ValidationError, match="TB8"):
        TimbresConfig.model_validate(cfg)


# --- TB9: strict schema -----------------------------------------------------


def test_tb9_rejects_unknown_top_level_key() -> None:
    cfg = _valid_config_dict()
    cfg["bogus"] = 1
    with pytest.raises(ValidationError, match="Extra inputs"):
        TimbresConfig.model_validate(cfg)


# --- §4.7 riser expressibility (dormant; no reference pack touched) ---------


def test_schema_expresses_riser_recipe() -> None:
    """The §4.7 riser — a NoiseSynth swell (envelope-as-automation), a Filter
    highpass insert, and a hot reverb send — must be expressible. Placed as a
    synthetic off-class flavor whose `mod` disables the subtractive role defaults
    (§3.2: an off-class engine overrides the incompatible defaults), the whole
    config validates through TB3/TB4/TB6/TB7."""
    riser = {
        "engine": {"type": "NoiseSynth"},
        "base": {
            "noise": {"type": "white"},
            "envelope": {"attack": 2.0, "decay": 0.1, "sustain": 1.0, "release": 0.3},
            "volume": -10,
        },
        "effects": [
            {
                "type": "Filter",
                "options": {"type": "highpass", "frequency": 900, "Q": 1},
            }
        ],
        "mix": {"volumeDb": -10, "pan": 0, "sends": {"reverb": -3}},
        "mod": {"brightness": [], "attackHardness": [], "space": []},
    }
    # Standalone: the models accept the riser shape.
    flavor = PitchedFlavor.model_validate(riser)
    assert flavor.engine.type == "NoiseSynth"
    assert flavor.effects[0].type == "Filter"
    assert flavor.effects[0].options["type"] == "highpass"
    assert flavor.mix.sends is not None and flavor.mix.sends["reverb"] == -3

    # End-to-end: it also passes the cross-cutting checks inside a full config.
    cfg = _valid_config_dict()
    cfg["flavors"]["pads"] = {"riser": riser}
    config = TimbresConfig.model_validate(cfg)
    assert config.flavors.pads["riser"].engine.type == "NoiseSynth"
