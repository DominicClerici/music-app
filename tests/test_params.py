"""Tests for the public `params` schema and validation catalog (PHASE_2 §3, §3.1)."""

from typing import Any

from trackgen.interpreter.params import (
    DEFAULT_PARAMS_SCHEMA_PATH,
    Params,
    params_schema_json,
    parse_tonic,
    validate_params,
)
from trackgen.packs.loader import resolve_pack

POP_ROCK = resolve_pack("pop_rock")
JAZZ = resolve_pack("jazz")


def _codes(raw: dict[str, Any], pack: Any) -> set[str]:
    return {e.code for e in validate_params(raw, pack)}


def test_validate_params_is_crash_safe_on_malformed_types() -> None:
    """Malformed JSON field types must not crash the public catalog entrypoint;
    the typed `Params` model is the separate type gate (SESSION_02 D-S6)."""
    raw: dict[str, Any] = {
        "styleFamily": "jazz",
        "tempoBpm": "120",
        "maxLengthSec": "100",
        "title": 123,
        "roleFlavors": ["not", "a", "dict"],
        "seedOverrides": ["also", "not", "a", "dict"],
        "key": "C",
    }
    # Must return without raising; malformed fields simply skip their semantic
    # check (no spurious range/length codes emitted for wrong-typed values).
    codes = _codes(raw, JAZZ)
    assert "TEMPO_OUT_OF_RANGE" not in codes
    assert "LENGTH_OUT_OF_RANGE" not in codes
    assert "TITLE_TOO_LONG" not in codes


# ---------------------------------------------------------------------------
# One failing fixture per §3.1 code
# ---------------------------------------------------------------------------


def test_style_unknown() -> None:
    raw: dict[str, Any] = {"styleFamily": "not_a_real_style"}
    errors = validate_params(raw, resolve_pack("not_a_real_style"))
    assert any(e.code == "STYLE_UNKNOWN" and e.field == "styleFamily" for e in errors)


def test_mood_unknown() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "mood": "bogus_mood"}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "MOOD_UNKNOWN" and e.field == "mood" for e in errors)


def test_mood_unsupported() -> None:
    # pop_rock's supportedMoods excludes "mysterious" (PHASE_2 §5.1 example).
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "mood": "mysterious"}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "MOOD_UNSUPPORTED" and e.field == "mood" for e in errors)


def test_tempo_out_of_range() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "tempoBpm": 999}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "TEMPO_OUT_OF_RANGE" and e.field == "tempoBpm" for e in errors)


def test_key_tonic_invalid() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "key": {"tonic": "H"}}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "KEY_TONIC_INVALID" and e.field == "key.tonic" for e in errors)


def test_mode_unsupported() -> None:
    # jazz's modes menu is [major, mixolydian, dorian, minor] -> no phrygian.
    raw: dict[str, Any] = {"styleFamily": "jazz", "key": {"mode": "phrygian"}}
    errors = validate_params(raw, JAZZ)
    assert any(e.code == "MODE_UNSUPPORTED" and e.field == "key.mode" for e in errors)


def test_role_unknown() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "roleFlavors": {"lead": "x"}}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "ROLE_UNKNOWN" and e.field == "roleFlavors" for e in errors)


def test_flavor_unknown() -> None:
    raw: dict[str, Any] = {"styleFamily": "jazz", "roleFlavors": {"comping": "nope"}}
    errors = validate_params(raw, JAZZ)
    assert any(e.code == "FLAVOR_UNKNOWN" and e.field == "roleFlavors" for e in errors)


def test_preset_unknown() -> None:
    raw: dict[str, Any] = {"styleFamily": "jazz", "ensemblePreset": "nope"}
    errors = validate_params(raw, JAZZ)
    assert any(
        e.code == "PRESET_UNKNOWN" and e.field == "ensemblePreset" for e in errors
    )


def test_length_out_of_range() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "maxLengthSec": 10}
    errors = validate_params(raw, POP_ROCK)
    assert any(
        e.code == "LENGTH_OUT_OF_RANGE" and e.field == "maxLengthSec" for e in errors
    )


def test_seed_conflict() -> None:
    raw: dict[str, Any] = {
        "styleFamily": "pop_rock",
        "seed": "1ps9wxb",
        "seedText": "hello world",
    }
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "SEED_CONFLICT" and e.field == "seed" for e in errors)


def test_seed_invalid() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "seed": "!!!not-base36!!!"}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "SEED_INVALID" and e.field == "seed" for e in errors)


def test_stream_unknown() -> None:
    raw: dict[str, Any] = {
        "styleFamily": "pop_rock",
        "seedOverrides": {"not_a_stream": "1ps9wxb"},
    }
    errors = validate_params(raw, POP_ROCK)
    assert any(
        e.code == "STREAM_UNKNOWN" and e.field == "seedOverrides" for e in errors
    )


def test_title_too_long() -> None:
    raw: dict[str, Any] = {"styleFamily": "pop_rock", "title": "x" * 121}
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "TITLE_TOO_LONG" and e.field == "title" for e in errors)


# ---------------------------------------------------------------------------
# seedOverrides value invalid (SEED_INVALID reused, field seedOverrides)
# ---------------------------------------------------------------------------


def test_seed_overrides_value_invalid_reuses_seed_invalid() -> None:
    raw: dict[str, Any] = {
        "styleFamily": "pop_rock",
        "seedOverrides": {"drums": "!!!not-base36!!!"},
    }
    errors = validate_params(raw, POP_ROCK)
    assert any(e.code == "SEED_INVALID" and e.field == "seedOverrides" for e in errors)


# ---------------------------------------------------------------------------
# Valid maximal call
# ---------------------------------------------------------------------------


def test_valid_maximal_call_returns_no_errors() -> None:
    # Adapted from the PHASE_2 §3 maximal-call example, using a registered
    # style (jazz) so every pack-relative check has something to validate
    # against.
    raw: dict[str, Any] = {
        "styleFamily": "jazz",
        "mood": "melancholic",
        "tempoBpm": 72,
        "key": {"tonic": "D", "mode": "minor"},
        "ensemblePreset": "default",
        "roleFlavors": {"comping": "guitar_hollow"},
        "maxLengthSec": 240,
        "seed": "1ps9wxb",
        "seedOverrides": {},
        "title": "Late set",
    }
    errors = validate_params(raw, JAZZ)
    assert errors == []

    # Also round-trips through the Params model itself.
    params = Params.model_validate(raw)
    assert params.style_family == "jazz"
    assert params.key is not None
    assert params.key.tonic == "D"


# ---------------------------------------------------------------------------
# Full-list reporting (never first-failure)
# ---------------------------------------------------------------------------


def test_full_list_reports_all_independent_errors() -> None:
    raw: dict[str, Any] = {
        "styleFamily": "pop_rock",
        "seed": "!!!not-base36!!!",
        "title": "x" * 200,
        "maxLengthSec": 5,
    }
    codes = _codes(raw, POP_ROCK)
    assert codes == {"SEED_INVALID", "TITLE_TOO_LONG", "LENGTH_OUT_OF_RANGE"}


# ---------------------------------------------------------------------------
# STYLE_UNKNOWN + pack-independent interplay (D-S6 ordering rule)
# ---------------------------------------------------------------------------


def test_style_unknown_still_runs_pack_independent_checks() -> None:
    raw: dict[str, Any] = {
        "styleFamily": "not_a_real_style",
        "seed": "!!!not-base36!!!",
    }
    errors = validate_params(raw, resolve_pack("not_a_real_style"))
    codes = {e.code for e in errors}
    assert codes == {"STYLE_UNKNOWN", "SEED_INVALID"}


def test_style_unknown_skips_pack_relative_checks() -> None:
    # tempoBpm/mode/flavor/preset checks are all pack-relative; with no pack
    # resolved they must not fire even though the values would otherwise be
    # invalid against a real pack.
    raw: dict[str, Any] = {
        "styleFamily": "not_a_real_style",
        "tempoBpm": 999999,
        "mood": "mysterious",
        "key": {"mode": "phrygian"},
        "ensemblePreset": "nope",
    }
    errors = validate_params(raw, resolve_pack("not_a_real_style"))
    codes = {e.code for e in errors}
    pack_relative = {
        "MOOD_UNSUPPORTED",
        "TEMPO_OUT_OF_RANGE",
        "MODE_UNSUPPORTED",
        "FLAVOR_UNKNOWN",
        "PRESET_UNKNOWN",
    }
    assert codes.isdisjoint(pack_relative)
    assert "STYLE_UNKNOWN" in codes


# ---------------------------------------------------------------------------
# Tonic parser
# ---------------------------------------------------------------------------


def test_parse_tonic_natural() -> None:
    assert parse_tonic("C") == 0
    assert parse_tonic("a") == 9


def test_parse_tonic_sharp_and_flat() -> None:
    assert parse_tonic("C#") == 1
    assert parse_tonic("Db") == 1
    assert parse_tonic("Cb") == 11


def test_parse_tonic_invalid() -> None:
    assert parse_tonic("H") is None
    assert parse_tonic("C##") is None
    assert parse_tonic("") is None


# ---------------------------------------------------------------------------
# Schema export drift guard
# ---------------------------------------------------------------------------


def test_params_schema_export_matches_committed_artifact() -> None:
    committed = DEFAULT_PARAMS_SCHEMA_PATH.read_text(encoding="utf-8")
    assert params_schema_json() == committed
