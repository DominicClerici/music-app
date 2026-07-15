"""Tests for the `interpreter.yaml` pack extension (PHASE_2 §5.1)."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trackgen.packs import InterpreterConfig, PackLoadError, load_pack, resolve_pack
from trackgen.packs.loader import registered_styles

STYLES_ROOT = Path(__file__).resolve().parent.parent / "styles"
STUB_PACK = STYLES_ROOT / "_stub"
POP_ROCK_PACK = STYLES_ROOT / "pop_rock"
JAZZ_PACK = STYLES_ROOT / "jazz"


# A valid interpreter config (mirrors styles/pop_rock/interpreter.yaml,
# PHASE_2 §5.1) used as the base for the per-rule rejection tests below.
VALID_INTERPRETER: dict[str, Any] = {
    "supportedMoods": ["happy", "energetic", "triumphant", "calm", "dreamy"],
    "defaultMood": "happy",
    "modes": ["major", "minor"],
    "tonics": {"major": ["E", "A", "G", "C", "D"], "minor": ["A", "E", "B", "D"]},
    "feel": "straight8",
    "expressionRanges": {
        "density": [0.20, 0.85],
        "dissonance": [0.05, 0.40],
    },
    "flavors": {
        "drums": ["acoustic_kit", "tight_kit"],
        "bass": ["electric_fingered", "electric_picked"],
        "comping": ["clean_electric", "crunch_electric", "piano"],
        "pads": ["warm_analog", "airy_strings"],
    },
    "ensembles": {
        "default": {
            "drums": "acoustic_kit",
            "bass": "electric_fingered",
            "comping": "clean_electric",
            "pads": "warm_analog",
        },
        "driven": {
            "drums": "tight_kit",
            "bass": "electric_picked",
            "comping": "crunch_electric",
            "pads": "airy_strings",
        },
    },
}


def _mutated(**overrides: Any) -> dict[str, Any]:
    """Deep-copy `VALID_INTERPRETER` and apply top-level key overrides."""
    base: dict[str, Any] = yaml.safe_load(yaml.safe_dump(VALID_INTERPRETER))
    base.update(overrides)
    return base


def test_valid_interpreter_config_loads() -> None:
    InterpreterConfig.model_validate(VALID_INTERPRETER)


# --- pop_rock / jazz reference packs ---------------------------------------


def test_pop_rock_pack_loads_with_populated_interpreter() -> None:
    pack = load_pack(POP_ROCK_PACK)

    assert pack.interpreter is not None
    assert pack.interpreter.default_mood == "happy"
    assert pack.interpreter.feel == "straight8"
    assert pack.interpreter.expression_ranges.density == (0.20, 0.85)
    assert pack.interpreter.modes == ["major", "minor"]
    assert "mysterious" not in pack.interpreter.supported_moods


def test_jazz_pack_loads_with_populated_interpreter() -> None:
    pack = load_pack(JAZZ_PACK)

    assert pack.interpreter is not None
    assert pack.interpreter.default_mood == "nostalgic"
    assert pack.interpreter.feel == "swing8"
    assert pack.interpreter.expression_ranges.density == (0.25, 0.90)
    assert pack.interpreter.modes == ["major", "mixolydian", "dorian", "minor"]
    assert "triumphant" not in pack.interpreter.supported_moods
    assert "aggressive" not in pack.interpreter.supported_moods


def test_pop_rock_via_resolve_pack() -> None:
    pack = resolve_pack("pop_rock")
    assert pack is not None
    assert pack.interpreter is not None
    assert pack.interpreter.default_mood == "happy"


def test_jazz_via_resolve_pack() -> None:
    pack = resolve_pack("jazz")
    assert pack is not None
    assert pack.interpreter is not None
    assert pack.interpreter.default_mood == "nostalgic"


def test_stub_pack_still_loads_with_no_interpreter() -> None:
    pack = load_pack(STUB_PACK)
    assert pack.interpreter is None


# --- registry ----------------------------------------------------------------


def test_registered_styles_excludes_stub() -> None:
    assert registered_styles() == {"pop_rock", "jazz"}


def test_resolve_pack_unregistered_style_returns_none() -> None:
    assert resolve_pack("blues") is None


# --- §5.1 Rules: one rejection test per rule class ---------------------------


def test_rejects_empty_supported_moods() -> None:
    with pytest.raises(ValidationError, match="supportedMoods must be non-empty"):
        InterpreterConfig.model_validate(_mutated(supportedMoods=[]))


def test_rejects_mood_outside_vocabulary() -> None:
    with pytest.raises(ValidationError, match="unknown mood word"):
        InterpreterConfig.model_validate(_mutated(supportedMoods=["happy", "sleepy"]))


def test_rejects_default_mood_not_in_supported_moods() -> None:
    with pytest.raises(ValidationError, match="defaultMood"):
        InterpreterConfig.model_validate(_mutated(defaultMood="dark"))


def test_rejects_mode_not_in_ladder() -> None:
    with pytest.raises(ValidationError, match="unknown mode"):
        InterpreterConfig.model_validate(_mutated(modes=["major", "lydian"]))


def test_rejects_modes_out_of_ladder_order() -> None:
    with pytest.raises(ValidationError, match="ladder order"):
        InterpreterConfig.model_validate(_mutated(modes=["minor", "major"]))


def test_rejects_empty_modes() -> None:
    with pytest.raises(ValidationError, match="modes must be non-empty"):
        InterpreterConfig.model_validate(_mutated(modes=[]))


def test_rejects_duplicate_modes() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        InterpreterConfig.model_validate(_mutated(modes=["major", "major"]))


def test_rejects_mode_with_no_tonics_entry() -> None:
    bad = _mutated(modes=["major", "minor"])
    del bad["tonics"]["minor"]
    with pytest.raises(ValidationError, match="tonics"):
        InterpreterConfig.model_validate(bad)


def test_rejects_unparseable_tonic_name() -> None:
    bad = _mutated()
    bad["tonics"]["major"] = ["H"]  # not a note name A-G
    with pytest.raises(ValidationError, match="unparseable note name"):
        InterpreterConfig.model_validate(bad)


def test_rejects_expression_range_lo_greater_than_hi() -> None:
    bad = _mutated()
    bad["expressionRanges"]["density"] = [0.9, 0.2]
    with pytest.raises(ValidationError, match="lo .* must be <= hi"):
        InterpreterConfig.model_validate(bad)


def test_rejects_expression_range_value_out_of_unit_interval() -> None:
    bad = _mutated()
    bad["expressionRanges"]["dissonance"] = [0.1, 1.5]
    with pytest.raises(ValidationError, match=r"within \[0, 1\]"):
        InterpreterConfig.model_validate(bad)


def test_rejects_swing_ratio_out_of_range() -> None:
    # swingRatio feeds SwingSpec (ge=0.5 le=0.75); an out-of-range pack must
    # fail at load, not crash later inside interpret().
    with pytest.raises(ValidationError, match=r"swingRatio .* within \[0.5, 0.75\]"):
        InterpreterConfig.model_validate(_mutated(swingRatio=0.9))


def test_rejects_role_missing_from_flavors() -> None:
    bad = _mutated()
    del bad["flavors"]["pads"]
    with pytest.raises(ValidationError, match="flavors.*pads"):
        InterpreterConfig.model_validate(bad)


def test_rejects_ensembles_default_missing() -> None:
    bad = _mutated()
    bad["ensembles"] = {"driven": bad["ensembles"]["driven"]}
    with pytest.raises(ValidationError, match="'default' key"):
        InterpreterConfig.model_validate(bad)


def test_rejects_ensemble_not_covering_all_roles() -> None:
    bad = _mutated()
    del bad["ensembles"]["default"]["pads"]
    with pytest.raises(ValidationError, match="missing role"):
        InterpreterConfig.model_validate(bad)


def test_rejects_ensemble_value_not_a_declared_flavor() -> None:
    bad = _mutated()
    bad["ensembles"]["default"]["drums"] = "electronic_kit"
    with pytest.raises(ValidationError, match="not a declared flavor id"):
        InterpreterConfig.model_validate(bad)


# --- end-to-end via load_pack (PackLoadError wrapping) -----------------------


def _write_pack_with_interpreter(root: Path, interpreter: dict[str, Any]) -> Path:
    manifest = {
        "formatVersion": 1,
        "id": "_bad",
        "name": "Bad",
        "version": "0.1.0",
        "engine": ">=0.1",
        "timeSignatures": [[4, 4]],
        "tempoRange": [80, 140],
    }
    (root / "patterns").mkdir(parents=True, exist_ok=True)
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    for role in ("drums", "bass", "comping", "pads"):
        (root / "patterns" / f"{role}.yaml").write_text(
            yaml.safe_dump({"patterns": []})
        )
    (root / "interpreter.yaml").write_text(yaml.safe_dump(interpreter))
    return root


def test_load_pack_wraps_interpreter_validation_error(tmp_path: Path) -> None:
    bad = _mutated(supportedMoods=[])
    pack_dir = _write_pack_with_interpreter(tmp_path, bad)
    with pytest.raises(PackLoadError, match="interpreter.yaml"):
        load_pack(pack_dir)


def test_load_pack_accepts_valid_interpreter(tmp_path: Path) -> None:
    pack_dir = _write_pack_with_interpreter(tmp_path, VALID_INTERPRETER)
    pack = load_pack(pack_dir)
    assert pack.interpreter is not None
    assert pack.interpreter.default_mood == "happy"
