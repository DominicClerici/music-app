"""Tests for the `forms.yaml` pack extension (PHASE_3 §5.1)."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trackgen.packs import (
    Fallback,
    FormEnding,
    FormsConfig,
    PackLoadError,
    TemplateEligibility,
    TemplateSlot,
    load_pack,
    resolve_pack,
)

STYLES_ROOT = Path(__file__).resolve().parent.parent / "styles"
STUB_PACK = STYLES_ROOT / "_stub"
POP_ROCK_PACK = STYLES_ROOT / "pop_rock"
JAZZ_PACK = STYLES_ROOT / "jazz"


# A minimal valid forms config (not derived from either reference pack) used
# as the base for the per-rule rejection tests below (mirrors the
# `VALID_INTERPRETER` pattern in `tests/test_interpreter_pack.py`).
MINIMAL_FORMS: dict[str, Any] = {
    "energyRange": [0.0, 1.0],
    "sections": {
        "intro": {
            "bars": [[4, 1]],
            "phrases": {4: ["a"]},
            "harmonyTag": {4: "intro"},
        },
        "verse": {
            "bars": [[8, 1]],
            "phrases": {8: ["a", "a"]},
            "harmonyTag": {8: "verse"},
        },
    },
    "templates": [
        {
            "id": "simple",
            "weight": 1,
            "spine": [
                {"section": "intro"},
                {"section": "verse"},
            ],
            "ending": {"tagBars": 0, "close": "cold"},
            "degrade": [],
            "fallback": {"section": "verse", "bars": 8},
        }
    ],
}


def _mutated(**overrides: Any) -> dict[str, Any]:
    """Deep-copy `MINIMAL_FORMS` and apply top-level key overrides."""
    base = deepcopy(MINIMAL_FORMS)
    base.update(overrides)
    return base


def test_valid_minimal_forms_config_loads() -> None:
    FormsConfig.model_validate(MINIMAL_FORMS)


# --- pop_rock / jazz reference packs ---------------------------------------


def test_pop_rock_pack_loads_with_populated_forms() -> None:
    pack = load_pack(POP_ROCK_PACK)

    assert pack.forms is not None
    assert len(pack.forms.templates) == 3
    assert [t.id for t in pack.forms.templates] == [
        "verse_chorus_bridge",
        "verse_chorus",
        "chorus_first",
    ]
    assert pack.forms.energy_range == (0.0, 1.0)
    assert pack.forms.sections["verse"].bars == ((8, 3), (16, 1))


def test_jazz_pack_loads_with_populated_forms() -> None:
    pack = load_pack(JAZZ_PACK)

    assert pack.forms is not None
    assert len(pack.forms.templates) == 1
    assert pack.forms.templates[0].id == "head_solos_head"
    assert pack.forms.energy_range == (0.10, 0.90)
    assert pack.forms.sections["head"].bars == ((32, 3), (12, 1))
    assert pack.forms.sections["solo"].inherit == "head"


def test_pop_rock_via_resolve_pack_has_forms() -> None:
    pack = resolve_pack("pop_rock")
    assert pack is not None
    assert pack.forms is not None
    assert pack.forms.templates[2].id == "chorus_first"


def test_jazz_via_resolve_pack_has_forms() -> None:
    pack = resolve_pack("jazz")
    assert pack is not None
    assert pack.forms is not None
    assert pack.forms.templates[0].id == "head_solos_head"


def test_stub_pack_still_loads_with_no_forms() -> None:
    pack = load_pack(STUB_PACK)
    assert pack.forms is None


# --- §5.1 Rules: one rejection test per rule class ---------------------------


def test_rejects_unknown_section_type() -> None:
    """F1 — sections keys must be in the closed 11-type vocabulary (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["ambient"] = bad["sections"]["verse"]
    with pytest.raises(ValidationError, match="closed vocabulary"):
        FormsConfig.model_validate(bad)


def test_rejects_bar_option_not_multiple_of_four() -> None:
    """F1 — bar options must be ints, multiples of 4, >= 4 (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["intro"]["bars"] = [[5, 1]]
    with pytest.raises(ValidationError, match="multiple of 4"):
        FormsConfig.model_validate(bad)


def test_rejects_inherit_target_missing() -> None:
    """F2 — an inherit target must exist in sections (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["solo"] = {"inherit": "head"}  # 'head' not declared
    with pytest.raises(ValidationError, match="not declared in sections"):
        FormsConfig.model_validate(bad)


def test_rejects_inherit_with_sibling_fields() -> None:
    """F2 — an inheriting entry must declare no other fields (PHASE_3 §5.1)."""
    with pytest.raises(ValidationError, match="must not declare"):
        FormsConfig.model_validate(
            _mutated(
                sections={
                    **MINIMAL_FORMS["sections"],
                    "solo": {"inherit": "verse", "bars": [[4, 1]]},
                }
            )
        )


def test_rejects_two_level_inherit() -> None:
    """F2 — an inherit target must not itself inherit (single level, PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["solo"] = {"inherit": "head"}
    bad["sections"]["head"] = {"inherit": "verse"}
    with pytest.raises(ValidationError, match="only a single inherit level"):
        FormsConfig.model_validate(bad)


def test_rejects_missing_phrase_entry_for_bar_option() -> None:
    """F3 — phrases must have an entry for every bar option (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["intro"]["bars"] = [[4, 1], [8, 1]]  # phrases only covers 4
    with pytest.raises(ValidationError, match="one entry per bar option"):
        FormsConfig.model_validate(bad)


def test_rejects_phrase_labels_not_dividing_bars() -> None:
    """F3 — phrase label count must divide the bar option evenly (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["verse"]["phrases"] = {8: ["a", "a", "a"]}  # 3 doesn't divide 8
    with pytest.raises(ValidationError, match="must divide"):
        FormsConfig.model_validate(bad)


def test_rejects_phrase_quotient_below_four() -> None:
    """F3 — the phrase-label quotient (phrase length) must be >= 4 bars
    (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["verse"]["bars"] = [[8, 1]]
    bad["sections"]["verse"]["phrases"] = {8: ["a", "b", "c", "d"]}  # quotient 2
    with pytest.raises(ValidationError, match="integer quotient"):
        FormsConfig.model_validate(bad)


def test_rejects_duplicate_template_ids() -> None:
    """F4 — template ids must be unique (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"].append(deepcopy(bad["templates"][0]))
    with pytest.raises(ValidationError, match="unique"):
        FormsConfig.model_validate(bad)


def test_rejects_two_repeat_blocks_in_one_template() -> None:
    """F4 — at most one repeat block per template (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"][0]["spine"] = [
        {"section": "intro"},
        {"repeat": {"count": [1, 2], "slots": [{"section": "verse"}]}},
        {"repeat": {"count": [1, 2], "slots": [{"section": "verse"}]}},
    ]
    with pytest.raises(ValidationError, match="at most one repeat block"):
        FormsConfig.model_validate(bad)


def test_rejects_repeat_count_max_below_min() -> None:
    """F4 — repeat count.max must be >= count.min, or null (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"][0]["spine"] = [
        {"section": "intro"},
        {"repeat": {"count": [3, 2], "slots": [{"section": "verse"}]}},
    ]
    with pytest.raises(ValidationError, match="count.max"):
        FormsConfig.model_validate(bad)


def test_rejects_inherit_before_target_in_spine() -> None:
    """F5 — an inheriting type's first spine occurrence must come after its
    inherit target's first spine occurrence (resolution order, PHASE_3 §5.1)."""
    bad = _mutated()
    bad["sections"]["head"] = {
        "bars": [[12, 1]],
        "phrases": {12: ["a", "b", "c"]},
        "harmonyTag": {12: "blues_12"},
    }
    bad["sections"]["solo"] = {"inherit": "head"}
    bad["templates"][0]["spine"] = [
        {"section": "solo"},
        {"section": "head"},
    ]
    bad["templates"][0]["fallback"] = {"section": "head", "bars": 12}
    with pytest.raises(ValidationError, match="appears before its inherit target"):
        FormsConfig.model_validate(bad)


def test_rejects_bad_optional_weights() -> None:
    """F6 — slot `optional` weights must both be integers >= 1 (PHASE_3 §5.1)."""
    with pytest.raises(ValidationError, match="F6"):
        TemplateSlot.model_validate({"section": "intro", "optional": [0, 1]})


def test_rejects_energy_out_of_range_and_empty_variant() -> None:
    """F7 — slot `energy` override must be in [0, 1]; `variant` non-empty
    (PHASE_3 §5.1)."""
    with pytest.raises(ValidationError):
        TemplateSlot.model_validate({"section": "chorus", "energy": 1.5})
    with pytest.raises(ValidationError):
        TemplateSlot.model_validate({"section": "chorus", "variant": ""})


def test_rejects_bad_tag_bars_literal() -> None:
    """F8 — ending.tagBars must be one of {0, 4, 8} (PHASE_3 §5.1)."""
    with pytest.raises(ValidationError):
        FormEnding.model_validate({"tagBars": 6, "close": "cold"})


def test_rejects_tag_bars_exceeding_smallest_ending_option() -> None:
    """F8 — ending.tagBars must not exceed the smallest bar option of every
    type that can end the form (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"][0]["spine"] = [
        {"section": "verse"},
        {"section": "intro"},  # intro's smallest bar option is 4
    ]
    bad["templates"][0]["fallback"] = {"section": "intro", "bars": 4}
    bad["templates"][0]["ending"] = {"tagBars": 8, "close": "cold"}
    with pytest.raises(ValidationError, match="exceeds the smallest bar option"):
        FormsConfig.model_validate(bad)


def test_rejects_degrade_type_not_in_spine() -> None:
    """F9 — degrade ops must reference types present in the template's
    spine (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"][0]["degrade"] = [{"drop": "bridge"}]  # bridge not in spine
    with pytest.raises(ValidationError, match="not present in the spine"):
        FormsConfig.model_validate(bad)


def test_rejects_drop_from_repeat_type_outside_repeat_block() -> None:
    """F9 (Fix 2) — `dropFromRepeat` must reference a type that actually
    occurs inside the template's repeat block; a top-level-only type has
    nothing to drop from the repeat (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"][0]["spine"] = [
        {"section": "intro"},
        {"repeat": {"count": [1, 2], "slots": [{"section": "verse"}]}},
    ]
    bad["templates"][0]["degrade"] = [{"dropFromRepeat": "intro"}]  # top-level only
    bad["templates"][0]["fallback"] = {"section": "verse", "bars": 8}
    with pytest.raises(ValidationError, match="repeat block"):
        FormsConfig.model_validate(bad)


def test_rejects_tag_bars_exceeding_trailing_optional_slot_predecessor() -> None:
    """F8 (Fix 1) — the ending-candidate set must include a trailing
    optional slot's smaller-barred predecessor: if the optional tail slot
    is excluded, that predecessor becomes the form's final section, so
    ending.tagBars must not exceed its smallest bar option (PHASE_3 §5.1,
    §7.1 step 3a)."""
    bad = _mutated()
    bad["sections"]["intro"]["bars"] = [[4, 1]]  # smaller-barred predecessor
    bad["templates"][0]["spine"] = [
        {"section": "intro"},
        {"section": "verse", "optional": [1, 1]},  # trailing optional slot
    ]
    bad["templates"][0]["fallback"] = {"section": "intro", "bars": 4}
    bad["templates"][0]["ending"] = {"tagBars": 8, "close": "cold"}
    with pytest.raises(ValidationError, match="exceeds the smallest bar option"):
        FormsConfig.model_validate(bad)


def test_rejects_bad_fallback_bars() -> None:
    """F9 — fallback.bars must be a multiple of 4, >= 4 (PHASE_3 §5.1)."""
    with pytest.raises(ValidationError, match="F9"):
        Fallback.model_validate({"section": "verse", "bars": 6})


def test_rejects_bad_energy_range() -> None:
    """F10 — energyRange must satisfy 0 <= lo <= hi <= 1 (PHASE_3 §5.1)."""
    bad = _mutated(energyRange=[0.9, 0.2])
    with pytest.raises(ValidationError, match="F10"):
        FormsConfig.model_validate(bad)


def test_rejects_template_missing_fallback() -> None:
    """F12 — every template must declare a fallback (PHASE_3 §5.1)."""
    bad = _mutated()
    del bad["templates"][0]["fallback"]
    with pytest.raises(ValidationError, match="fallback"):
        FormsConfig.model_validate(bad)


def test_rejects_reversed_eligibility_arousal_band() -> None:
    """Fix 3 — `TemplateEligibility.arousal` must satisfy lo <= hi; a
    reversed band like [0.5, 0.2] must not load silently (PHASE_3 §5.1)."""
    with pytest.raises(ValidationError, match="lo <= hi"):
        TemplateEligibility.model_validate({"arousal": [0.5, 0.2]})


def test_rejects_all_templates_gated() -> None:
    """F13 — at least one template per pack must have no arousal gate (PHASE_3 §5.1)."""
    bad = _mutated()
    bad["templates"][0]["eligibility"] = {"arousal": [0.0, 1.0]}
    with pytest.raises(ValidationError, match="F13"):
        FormsConfig.model_validate(bad)


# --- F11 (loader cross-check) + end-to-end via load_pack (PackLoadError) ----


def _write_pack_with_forms(
    root: Path, forms: dict[str, Any], tempo_range: tuple[int, int] = (80, 140)
) -> Path:
    manifest = {
        "formatVersion": 1,
        "id": "_bad",
        "name": "Bad",
        "version": "0.1.0",
        "engine": ">=0.1",
        "timeSignatures": [[4, 4]],
        "tempoRange": list(tempo_range),
    }
    (root / "patterns").mkdir(parents=True, exist_ok=True)
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    for role in ("drums", "bass", "comping", "pads"):
        (root / "patterns" / f"{role}.yaml").write_text(
            yaml.safe_dump({"patterns": []})
        )
    (root / "forms.yaml").write_text(yaml.safe_dump(forms))
    return root


def test_f11_rejects_tempo_lo_too_low_for_thirty_second_floor(tmp_path: Path) -> None:
    """F11 — tempoRange.lo must yield a bar budget >= 4 at the 30s minimum
    length (loader cross-check, PHASE_3 §5.1, D-S12)."""
    pack_dir = _write_pack_with_forms(tmp_path, MINIMAL_FORMS, tempo_range=(20, 140))
    with pytest.raises(PackLoadError, match="F11"):
        load_pack(pack_dir)


def test_load_pack_wraps_forms_validation_error(tmp_path: Path) -> None:
    bad = _mutated()
    del bad["templates"][0]["fallback"]
    pack_dir = _write_pack_with_forms(tmp_path, bad)
    with pytest.raises(PackLoadError, match="forms.yaml"):
        load_pack(pack_dir)


def test_load_pack_accepts_valid_forms(tmp_path: Path) -> None:
    pack_dir = _write_pack_with_forms(tmp_path, MINIMAL_FORMS)
    pack = load_pack(pack_dir)
    assert pack.forms is not None
    assert pack.forms.templates[0].id == "simple"
