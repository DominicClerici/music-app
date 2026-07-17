"""PHASE_6 §4 `transitions.yaml` schema + loader validation (Chunk 1 T1).

One non-vacuous rejection fixture per rule class TR1–TR7 (§4.1): TR1–TR4 are
pydantic model rules checked by validating a model directly; TR5 (= PT12,
cross-file), TR6, and TR7 are loader-level rules checked through a temp pack /
the `_window_and_check_fills` guard. Also: both reference packs load with the
normative content (§4.2/§4.3) and the three reference fills compute to the
pinned windows (§3.3).
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trackgen.packs import (
    Crash,
    DrumEvent,
    DrumsBank,
    Mutation,
    PackLoadError,
    PatternEnvelope,
    PhraseFill,
    Stop,
    TransitionsSpec,
    fill_window,
    load_pack,
    resolve_pack,
)
from trackgen.packs.loader import _window_and_check_fills

VALID_MANIFEST: dict[str, object] = {
    "formatVersion": 1,
    "id": "_t6",
    "name": "T6",
    "version": "0.1.0",
    "engine": ">=0.1",
    "timeSignatures": [[4, 4]],
    "tempoRange": [80, 140],
}

_RETARGET = {
    "bass": {"registerLow": 28, "registerHigh": 45, "onChordChange": "retrigger"},
    "comping": {"registerLow": 52, "registerHigh": 67, "onChordChange": "retrigger"},
    "pads": {"registerLow": 45, "registerHigh": 64, "onChordChange": "retrigger"},
}
_DEGREE = {"bass": "root", "comping": "chord", "pads": "chord"}

_VALID_TRANSITIONS: dict[str, Any] = {
    "phraseFill": {"odds": [1, 2]},
    "stop": {"enabled": True, "odds": [1, 4]},
    "crash": {"velocity": [0.55, 0.95]},
    "mutation": {
        "drums": {"none": 10, "hat_lift": 2, "drop_ornament": 1, "kick_pickup": 2},
        "comping": {"none": 3, "anticipate": 2, "drop_hit": 1},
    },
}


def _event(role: str) -> dict[str, Any]:
    if role == "drums":
        return {"pos": 0, "voice": "kick", "velocity": 0.9}
    return {"pos": 0, "dur": 480, "degree": _DEGREE[role], "octave": 0, "velocity": 0.7}


def _complete_bank(role: str) -> list[dict[str, Any]]:
    """PT5-complete: an ungated `main` at each rung 1–4 plus `intro`/`ending`."""
    plan = [
        ("main", 1),
        ("main", 2),
        ("main", 3),
        ("main", 4),
        ("intro", 1),
        ("ending", 1),
    ]
    entries: list[dict[str, Any]] = []
    for i, (kind, rung) in enumerate(plan):
        entry: dict[str, Any] = {
            "id": f"{role}_{kind}_{i}",
            "role": role,
            "kind": kind,
            "energyLevel": rung,
            "lengthTicks": 1920,
            "weight": 1,
            "events": [_event(role)],
        }
        if role != "drums":
            entry["retarget"] = _RETARGET[role]
        entries.append(entry)
    return entries


def _drum_fill(
    fill_id: str, *, gated: bool = False, events: Any = None
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": fill_id,
        "role": "drums",
        "kind": "fill",
        "energyLevel": 2,
        "lengthTicks": 1920,
        "weight": 1,
        "events": events
        if events is not None
        else [
            {"pos": 960, "voice": "snare", "velocity": 0.60},
            {"pos": 1680, "voice": "snare", "velocity": 0.85},
        ],
    }
    if gated:
        entry["eligibility"] = {"tempoBpm": [60, 90]}
    return entry


def _valid_banks(
    drum_fills: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    classes_shell = {1: ["shell2"], 2: ["shell2"], 3: ["rootless_a"], 4: ["rootless_a"]}
    classes_fifths = {1: ["fifths"], 2: ["fifths"], 3: ["fifths"], 4: ["fifths"]}
    drums = _complete_bank("drums") + (drum_fills or [])
    return {
        "drums": {
            "layeringOrder": ["drums", "bass", "comping", "pads"],
            "patterns": drums,
        },
        "bass": {"mode": "patterns", "patterns": _complete_bank("bass")},
        "comping": {
            "voicing": {"classes": classes_shell},
            "patterns": _complete_bank("comping"),
        },
        "pads": {
            "voicing": {"classes": classes_fifths},
            "patterns": _complete_bank("pads"),
        },
    }


def _write_pack(
    root: Path,
    banks: dict[str, dict[str, Any]],
    transitions: dict[str, Any] | None = None,
) -> Path:
    (root / "patterns").mkdir(parents=True, exist_ok=True)
    (root / "manifest.yaml").write_text(yaml.safe_dump(VALID_MANIFEST))
    for role, bank in banks.items():
        (root / "patterns" / f"{role}.yaml").write_text(yaml.safe_dump(bank))
    if transitions is not None:
        (root / "transitions.yaml").write_text(yaml.safe_dump(transitions))
    return root


# --- TR1 ---------------------------------------------------------------------


def test_tr1_phrasefill_odds_below_one() -> None:
    with pytest.raises(ValidationError, match="TR1"):
        PhraseFill.model_validate({"odds": [0, 2]})


def test_tr1_crash_velocity_out_of_order() -> None:
    with pytest.raises(ValidationError, match="TR1"):
        Crash.model_validate({"velocity": [0.9, 0.5]})


def test_tr1_crash_velocity_above_one() -> None:
    with pytest.raises(ValidationError, match="TR1"):
        Crash.model_validate({"velocity": [0.5, 1.5]})


# --- TR2 ---------------------------------------------------------------------


def test_tr2_stop_enabled_requires_odds() -> None:
    with pytest.raises(ValidationError, match="TR2"):
        Stop.model_validate({"enabled": True})


def test_tr2_stop_disabled_forbids_odds() -> None:
    with pytest.raises(ValidationError, match="TR2"):
        Stop.model_validate({"enabled": False, "odds": [1, 4]})


def test_tr2_stop_odds_below_one() -> None:
    with pytest.raises(ValidationError, match="TR2"):
        Stop.model_validate({"enabled": True, "odds": [1, 0]})


# --- TR3 ---------------------------------------------------------------------


def test_tr3_op_not_in_role_vocabulary() -> None:
    # `anticipate` is a comping op — illegal under drums.
    with pytest.raises(ValidationError, match="TR3"):
        Mutation.model_validate({"drums": {"none": 1, "anticipate": 2}})


def test_tr3_table_missing_none() -> None:
    with pytest.raises(ValidationError, match="TR3"):
        Mutation.model_validate({"comping": {"anticipate": 2}})


def test_tr3_weight_below_one() -> None:
    with pytest.raises(ValidationError, match="TR3"):
        Mutation.model_validate({"drums": {"none": 1, "hat_lift": 0}})


def test_tr3_none_only_table_is_legal() -> None:
    # A single-entry (`none` only) table means the role never draws — legal.
    m = Mutation.model_validate({"drums": {"none": 1}})
    assert m.drums == {"none": 1}


# --- TR4 ---------------------------------------------------------------------


def test_tr4_unknown_top_level_key() -> None:
    bad = {**deepcopy(_VALID_TRANSITIONS), "stray": 1}
    with pytest.raises(ValidationError):
        TransitionsSpec.model_validate(bad)


def test_tr4_unknown_mutation_role_key() -> None:
    # `bass` has no operators in v1 — strict schema rejects the extra key.
    with pytest.raises(ValidationError):
        Mutation.model_validate({"drums": {"none": 1}, "bass": {"none": 1}})


# --- TR5 = PT12 (cross-file) -------------------------------------------------


def test_tr5_no_ungated_fill_rejected(tmp_path: Path) -> None:
    # Transitions present but the drum bank's only fill is tempo-gated → fill
    # resolution could come up empty → PT12/TR5.
    banks = _valid_banks(drum_fills=[_drum_fill("gated_fill", gated=True)])
    _write_pack(tmp_path, banks, transitions=_VALID_TRANSITIONS)
    with pytest.raises(PackLoadError, match="PT12"):
        load_pack(tmp_path)


def test_tr5_no_fill_at_all_rejected(tmp_path: Path) -> None:
    banks = _valid_banks(drum_fills=None)
    _write_pack(tmp_path, banks, transitions=_VALID_TRANSITIONS)
    with pytest.raises(PackLoadError, match="PT12"):
        load_pack(tmp_path)


# --- TR6 ---------------------------------------------------------------------


def test_tr6_empty_window_rejected() -> None:
    # A schema-valid fill can never yield an empty window (PT1 pins the length
    # to 1920, PT2 pins pos < 1920, so beatFloor(min pos) <= 1440 < 1920). TR6
    # is a defensive load-time guard; exercise it on a validation-bypassed
    # envelope whose window collapses to start == end.
    env = PatternEnvelope.model_construct(
        id="bad_fill",
        role="drums",
        kind="fill",
        energy_level=2,
        length_ticks=960,
        weight=1,
        events=[DrumEvent(pos=1440, voice="snare", velocity=0.6)],
        retarget=None,
    )
    bank = DrumsBank.model_construct(layering_order=None, patterns=[env])
    with pytest.raises(PackLoadError, match="TR6"):
        _window_and_check_fills(Path("/nonexistent"), bank)


def test_tr6_empty_events_fill_rejected() -> None:
    # A fill authored with no events is schema-valid (events may be []), so the
    # window is undefined. The loader must reject it with a PackLoadError, not
    # let an unwrapped ValueError escape load_pack's error contract.
    env = PatternEnvelope.model_construct(
        id="no_events_fill",
        role="drums",
        kind="fill",
        energy_level=2,
        length_ticks=1920,
        weight=1,
        events=[],
        retarget=None,
    )
    bank = DrumsBank.model_construct(layering_order=None, patterns=[env])
    with pytest.raises(PackLoadError, match="TR6"):
        _window_and_check_fills(Path("/nonexistent"), bank)


# --- TR7 ---------------------------------------------------------------------


def test_tr7_fill_not_reaching_barline_rejected(tmp_path: Path) -> None:
    # All events sit in the first half — none in the last 2 beats (>= 960).
    early = _drum_fill(
        "early_fill",
        events=[
            {"pos": 0, "voice": "snare", "velocity": 0.60},
            {"pos": 480, "voice": "snare", "velocity": 0.70},
        ],
    )
    banks = _valid_banks(drum_fills=[early])
    _write_pack(tmp_path, banks, transitions=_VALID_TRANSITIONS)
    with pytest.raises(PackLoadError, match="TR7"):
        load_pack(tmp_path)


# --- positive load -----------------------------------------------------------


def test_valid_transitions_pack_loads(tmp_path: Path) -> None:
    banks = _valid_banks(drum_fills=[_drum_fill("ok_fill")])
    _write_pack(tmp_path, banks, transitions=_VALID_TRANSITIONS)
    pack = load_pack(tmp_path)
    assert isinstance(pack.transitions, TransitionsSpec)
    assert pack.fill_windows["ok_fill"] == (960, 1920)


def test_pack_without_transitions_still_loads(tmp_path: Path) -> None:
    # A pack with fills but no transitions.yaml loads (PT12 is transitions-gated)
    # and still caches its fill windows.
    banks = _valid_banks(drum_fills=[_drum_fill("ok_fill")])
    _write_pack(tmp_path, banks, transitions=None)
    pack = load_pack(tmp_path)
    assert pack.transitions is None
    assert pack.fill_windows["ok_fill"] == (960, 1920)


# --- fill window helper ------------------------------------------------------


def test_fill_window_beat_floor() -> None:
    env = PatternEnvelope.model_validate(
        _drum_fill(
            "w",
            events=[
                {"pos": 1200, "voice": "snare", "velocity": 0.6},
                {"pos": 1680, "voice": "snare", "velocity": 0.8},
            ],
        )
    )
    # min pos 1200 floors to 960; end = lengthTicks 1920.
    assert fill_window(env) == (960, 1920)


# --- reference packs (normative §4.2 / §4.3) ---------------------------------


def test_pop_rock_reference_transitions() -> None:
    pack = resolve_pack("pop_rock")
    assert pack is not None
    spec = pack.transitions
    assert spec is not None
    assert spec.phrase_fill.odds == (1, 2)
    assert spec.stop.enabled is True
    assert spec.stop.odds == (1, 4)
    assert spec.crash.velocity == (0.55, 0.95)
    assert spec.mutation.drums == {
        "none": 10,
        "hat_lift": 2,
        "drop_ornament": 1,
        "kick_pickup": 2,
    }
    assert spec.mutation.comping == {"none": 3, "anticipate": 2, "drop_hit": 1}


def test_jazz_reference_transitions() -> None:
    pack = resolve_pack("jazz")
    assert pack is not None
    spec = pack.transitions
    assert spec is not None
    assert spec.phrase_fill.odds == (1, 3)
    assert spec.stop.enabled is False
    assert spec.stop.odds is None
    assert spec.crash.velocity == (0.40, 0.70)
    assert spec.mutation.drums == {"none": 6, "drop_ornament": 1}
    assert spec.mutation.comping == {"none": 4, "anticipate": 1, "drop_hit": 1}


def test_reference_fill_windows() -> None:
    pop = resolve_pack("pop_rock")
    jazz = resolve_pack("jazz")
    assert pop is not None and jazz is not None
    assert pop.fill_windows["pr_dr_f1"] == (960, 1920)
    assert pop.fill_windows["pr_dr_f2"] == (960, 1920)
    assert jazz.fill_windows["jz_dr_f1"] == (960, 1920)
