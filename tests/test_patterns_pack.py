"""PHASE_5 §5 pattern-bank schema + loader validation (T1).

One rejection fixture per PT1–PT11 rule class (§5.5), plus a positive load of a
Phase-5 pack exercising every new event/bank field. Model-level rules are
checked by validating a single model directly; whole-pack rules (PT1 id/role,
PT5 completeness, PT6/PT7/PT10 gating) go through `load_pack` on a temp pack.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trackgen.packs import (
    Eligibility,
    PackLoadError,
    PatternEnvelope,
    VoicingConfig,
    WalkingConfig,
    load_pack,
)

VALID_MANIFEST: dict[str, object] = {
    "formatVersion": 1,
    "id": "_p5",
    "name": "P5",
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


def _event(role: str) -> dict[str, Any]:
    if role == "drums":
        return {"pos": 0, "voice": "kick", "velocity": 0.9}
    return {"pos": 0, "dur": 480, "degree": _DEGREE[role], "octave": 0, "velocity": 0.7}


def _complete_bank(role: str) -> list[dict[str, Any]]:
    """Six ungated entries satisfying PT5 for one role: a `main` at each rung
    1–4 plus an `intro` and an `ending`."""
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


def _valid_banks() -> dict[str, dict[str, Any]]:
    """A complete, valid Phase-5 pack (bass in patterns mode) as raw bank dicts."""
    classes_shell = {1: ["shell2"], 2: ["shell2"], 3: ["rootless_a"], 4: ["rootless_a"]}
    classes_fifths = {1: ["fifths"], 2: ["fifths"], 3: ["fifths"], 4: ["fifths"]}
    return {
        "drums": {
            "layeringOrder": ["drums", "bass", "comping", "pads"],
            "patterns": _complete_bank("drums"),
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


def _write_pack(root: Path, banks: dict[str, dict[str, Any]]) -> Path:
    (root / "patterns").mkdir(parents=True, exist_ok=True)
    (root / "manifest.yaml").write_text(yaml.safe_dump(VALID_MANIFEST))
    for role, bank in banks.items():
        (root / "patterns" / f"{role}.yaml").write_text(yaml.safe_dump(bank))
    return root


# --- model-level rejection fixtures ------------------------------------------


def _pitched_env(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "e",
        "role": "bass",
        "kind": "main",
        "energyLevel": 2,
        "lengthTicks": 1920,
        "weight": 1,
        "events": [
            {"pos": 0, "dur": 480, "degree": "root", "octave": 0, "velocity": 0.7}
        ],
        "retarget": _RETARGET["bass"],
    }
    base.update(over)
    return base


def test_pt1_lengthticks_must_be_whole_bars() -> None:
    with pytest.raises(ValidationError, match="PT1"):
        PatternEnvelope.model_validate(_pitched_env(lengthTicks=1000))


def test_pt1_fill_must_be_one_bar() -> None:
    with pytest.raises(ValidationError, match="PT1"):
        PatternEnvelope.model_validate(_pitched_env(kind="fill", lengthTicks=3840))


def test_pt2_voice_grouped_events_load() -> None:
    # §7.1 `pr_dr_2a` is authored voice-grouped: pos decreases across voices
    # (kick 0,960 -> snare 480,1440 -> hats 0..1680). PT2 does not require
    # non-decreasing authored order, so the normative shape must validate.
    env = {
        "id": "pr_dr_2a",
        "role": "drums",
        "kind": "main",
        "energyLevel": 2,
        "lengthTicks": 1920,
        "weight": 3,
        "events": [
            {"pos": 0, "voice": "kick", "velocity": 0.92},
            {"pos": 960, "voice": "kick", "velocity": 0.88},
            {"pos": 480, "voice": "snare", "velocity": 0.85},
            {"pos": 1440, "voice": "snare", "velocity": 0.82},
            {"pos": 0, "voice": "hat_closed", "velocity": 0.58},
            {"pos": 240, "voice": "hat_closed", "velocity": 0.40},
            {"pos": 480, "voice": "hat_closed", "velocity": 0.48},
            {"pos": 720, "voice": "hat_closed", "velocity": 0.40},
            {"pos": 960, "voice": "hat_closed", "velocity": 0.55},
            {"pos": 1200, "voice": "hat_closed", "velocity": 0.40},
            {"pos": 1440, "voice": "hat_closed", "velocity": 0.48},
            {"pos": 1680, "voice": "hat_closed", "velocity": 0.42},
        ],
    }
    env_model = PatternEnvelope.model_validate(env)
    assert [e.pos for e in env_model.events] == [
        0,
        960,
        480,
        1440,
        0,
        240,
        480,
        720,
        960,
        1200,
        1440,
        1680,
    ]


def test_pt2_pos_beyond_length() -> None:
    env = _pitched_env(
        events=[
            {"pos": 1920, "dur": 240, "degree": "root", "octave": 0, "velocity": 0.7}
        ]
    )
    with pytest.raises(ValidationError, match="PT2"):
        PatternEnvelope.model_validate(env)


def test_pt3_drums_bank_rejects_pitched_event() -> None:
    env = {
        "id": "d",
        "role": "drums",
        "kind": "main",
        "energyLevel": 2,
        "lengthTicks": 1920,
        "weight": 1,
        "events": [
            {"pos": 0, "dur": 240, "degree": "root", "octave": 0, "velocity": 0.7}
        ],
    }
    with pytest.raises(ValidationError, match="PT3"):
        PatternEnvelope.model_validate(env)


def test_pt4_tempo_band_ordering() -> None:
    with pytest.raises(ValidationError, match="PT4"):
        Eligibility.model_validate({"tempoBpm": [140, 80]})


def test_pt6_feel_must_cover_all_rungs() -> None:
    with pytest.raises(ValidationError, match="PT6"):
        WalkingConfig.model_validate(
            {
                "feelByIntensity": {1: "two", 2: "two", 3: "four"},
                "approachWeights": {"chromatic_below": 2},
                "beat1RepeatWeights": {"root": 1},
            }
        )


def test_pt7_unknown_voicing_class() -> None:
    with pytest.raises(ValidationError, match="PT7"):
        VoicingConfig.model_validate(
            {"classes": {1: ["shell2"], 2: ["shell2"], 3: ["shell2"], 4: ["bogus"]}}
        )


def test_pt8_min_density_out_of_range() -> None:
    env = _pitched_env(
        events=[
            {
                "pos": 0,
                "dur": 240,
                "degree": "root",
                "octave": 0,
                "velocity": 0.7,
                "minDensity": 1.5,
            }
        ]
    )
    with pytest.raises(
        ValidationError, match="minDensity|min_density|less than or equal"
    ):
        PatternEnvelope.model_validate(env)


def test_pt8_push_only_on_pitched_events() -> None:
    # push on a drum event is rejected structurally (DrumEvent forbids it).
    env = {
        "id": "d",
        "role": "drums",
        "kind": "main",
        "energyLevel": 2,
        "lengthTicks": 1920,
        "weight": 1,
        "events": [{"pos": 0, "voice": "kick", "velocity": 0.9, "push": True}],
    }
    with pytest.raises(ValidationError, match="push|Extra inputs"):
        PatternEnvelope.model_validate(env)


def test_pt9_retarget_span_too_small() -> None:
    with pytest.raises(ValidationError, match="PT9"):
        PatternEnvelope.model_validate(
            _pitched_env(
                retarget={
                    "registerLow": 36,
                    "registerHigh": 40,
                    "onChordChange": "hold",
                }
            )
        )


def test_pt9_drums_reject_retarget() -> None:
    env = {
        "id": "d",
        "role": "drums",
        "kind": "main",
        "energyLevel": 2,
        "lengthTicks": 1920,
        "weight": 1,
        "events": [{"pos": 0, "voice": "kick", "velocity": 0.9}],
        "retarget": {"registerLow": 0, "registerHigh": 0, "onChordChange": "hold"},
    }
    with pytest.raises(ValidationError, match="PT9"):
        PatternEnvelope.model_validate(env)


def test_pt11_unknown_event_key_rejected() -> None:
    env = _pitched_env(
        events=[
            {
                "pos": 0,
                "dur": 240,
                "degree": "root",
                "octave": 0,
                "velocity": 0.7,
                "swing": True,
            }
        ]
    )
    with pytest.raises(ValidationError, match="swing|Extra inputs"):
        PatternEnvelope.model_validate(env)


# --- loader-level (whole-pack) rejection fixtures ----------------------------


def test_pt1_duplicate_id_across_pack(tmp_path: Path) -> None:
    banks = _valid_banks()
    # collide a bass id with a drums id.
    banks["bass"]["patterns"][0]["id"] = banks["drums"]["patterns"][0]["id"]
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT1"):
        load_pack(tmp_path)


def test_pt1_role_must_match_file(tmp_path: Path) -> None:
    banks = _valid_banks()
    banks["comping"]["patterns"][0]["role"] = "pads"
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT1"):
        load_pack(tmp_path)


def test_pt5_missing_rung_main(tmp_path: Path) -> None:
    banks = _valid_banks()
    # drop the rung-3 comping main -> completeness fails.
    banks["comping"]["patterns"] = [
        e for e in banks["comping"]["patterns"] if e["energyLevel"] != 3
    ]
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT5"):
        load_pack(tmp_path)


def test_pt6_walking_block_required(tmp_path: Path) -> None:
    banks = _valid_banks()
    banks["bass"] = {"mode": "walking", "patterns": []}
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT6"):
        load_pack(tmp_path)


def test_pt7_voicing_block_required(tmp_path: Path) -> None:
    banks = _valid_banks()
    del banks["comping"]["voicing"]
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT7"):
        load_pack(tmp_path)


def test_pt10_layering_order_not_a_permutation(tmp_path: Path) -> None:
    banks = _valid_banks()
    banks["drums"]["layeringOrder"] = ["drums", "bass", "comping", "comping"]
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT10"):
        load_pack(tmp_path)


def test_pt10_layering_order_missing(tmp_path: Path) -> None:
    banks = _valid_banks()
    # keep a Phase-5 marker (voicing) but drop layeringOrder.
    del banks["drums"]["layeringOrder"]
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT10"):
        load_pack(tmp_path)


# --- positive: every new field loads clean -----------------------------------


def test_phase5_pack_loads_clean_with_all_new_fields(tmp_path: Path) -> None:
    banks = _valid_banks()

    # bass in walking mode (completeness-exempt) with a full walking block.
    banks["bass"] = {
        "mode": "walking",
        "walking": {
            "feelByIntensity": {1: "two", 2: "two", 3: "four", 4: "four"},
            "approachWeights": {"chromatic_below": 2, "diatonic": 1, "dominant": 1},
            "beat1RepeatWeights": {"fifth": 2, "third": 1, "root": 1},
        },
    }

    # a drum main exercising `dur` + `minDensity` on drum events.
    drum_main = deepcopy(banks["drums"]["patterns"][0])
    drum_main["events"] = [
        {"pos": 0, "voice": "kick", "velocity": 0.9, "dur": 120, "minDensity": 0.5},
        {"pos": 960, "voice": "snare", "velocity": 0.8},
    ]
    banks["drums"]["patterns"][0] = drum_main

    # a comping main exercising `chord`, `sixth`, `push`, and pitched `minDensity`.
    comping_main = deepcopy(banks["comping"]["patterns"][0])
    comping_main["events"] = [
        {"pos": 0, "dur": 480, "degree": "chord", "velocity": 0.6},
        {
            "pos": 480,
            "dur": 240,
            "degree": "sixth",
            "octave": 0,
            "velocity": 0.5,
            "minDensity": 0.6,
        },
        {"pos": 960, "dur": 480, "degree": "chord", "velocity": 0.6, "push": True},
    ]
    banks["comping"]["patterns"][0] = comping_main

    _write_pack(tmp_path, banks)
    pack = load_pack(tmp_path)

    assert pack.layering_order == ("drums", "bass", "comping", "pads")
    assert pack.bass_mode == "walking"
    assert pack.walking is not None
    assert pack.walking.feel_by_intensity[3] == "four"
    assert pack.walking.approach_weights["chromatic_below"] == 2
    assert pack.voicing["comping"].classes[3] == ("rootless_a",)
    assert pack.voicing["pads"].classes[1] == ("fifths",)

    drum_ev = pack.patterns["drums"][0].events[0]
    assert drum_ev.dur == 120
    assert drum_ev.min_density == 0.5

    comp_events = pack.patterns["comping"][0].events
    assert comp_events[0].degree == "chord"  # type: ignore[union-attr]
    assert comp_events[0].octave == 0  # type: ignore[union-attr]  # default 0 (§6.3)
    assert comp_events[1].degree == "sixth"  # type: ignore[union-attr]
    assert comp_events[1].min_density == 0.6
    assert comp_events[2].push is True  # type: ignore[union-attr]


# --- PHASE_5 §7 bank-level `retarget` default --------------------------------


def test_bank_level_retarget_default_fills_entries(tmp_path: Path) -> None:
    # §7 authors one `retarget:` per pitched-role file; entries omit their own.
    banks = _valid_banks()
    for role in ("bass", "comping", "pads"):
        for entry in banks[role]["patterns"]:
            entry.pop("retarget", None)
        banks[role]["retarget"] = _RETARGET[role]
    _write_pack(tmp_path, banks)
    pack = load_pack(tmp_path)

    for role in ("bass", "comping", "pads"):
        want = _RETARGET[role]
        for env in pack.patterns[role]:
            assert env.retarget is not None
            assert env.retarget.register_low == want["registerLow"]
            assert env.retarget.register_high == want["registerHigh"]
            assert env.retarget.on_chord_change == want["onChordChange"]


def test_bank_level_retarget_entry_override_wins(tmp_path: Path) -> None:
    banks = _valid_banks()
    for entry in banks["bass"]["patterns"]:
        entry.pop("retarget", None)
    banks["bass"]["retarget"] = _RETARGET["bass"]
    override = {"registerLow": 30, "registerHigh": 50, "onChordChange": "hold"}
    banks["bass"]["patterns"][0]["retarget"] = override
    _write_pack(tmp_path, banks)
    pack = load_pack(tmp_path)

    first = pack.patterns["bass"][0]
    assert first.retarget is not None
    assert first.retarget.register_low == 30
    assert first.retarget.register_high == 50
    assert first.retarget.on_chord_change == "hold"

    # a sibling entry that omitted its own still inherits the bank default.
    sibling = pack.patterns["bass"][1]
    assert sibling.retarget is not None
    assert sibling.retarget.register_low == 28


def test_pitched_entry_without_any_retarget_still_fails_pt9(tmp_path: Path) -> None:
    # No bank-level default and no per-entry retarget -> PT9 still fires.
    banks = _valid_banks()
    banks["bass"]["patterns"][0].pop("retarget", None)
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="PT9"):
        load_pack(tmp_path)


def test_drums_bank_rejects_top_level_retarget(tmp_path: Path) -> None:
    # DrumsBank declares no `retarget` field; a bank-level one is not injected
    # and `extra="forbid"` rejects it (drums are retarget-exempt, §5.2).
    banks = _valid_banks()
    banks["drums"]["retarget"] = _RETARGET["bass"]
    _write_pack(tmp_path, banks)
    with pytest.raises(PackLoadError, match="Extra inputs"):
        load_pack(tmp_path)
