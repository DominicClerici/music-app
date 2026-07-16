"""Tests for the `progressions.yaml` pack extension (PHASE_4 §4)."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trackgen.packs import (
    FinalEntry,
    PoolEntry,
    ProgressionsConfig,
    TurnaroundEntry,
    load_pack,
    resolve_pack,
)
from trackgen.packs.loader import PackLoadError, _forms_tag_usage

STYLES_ROOT = Path(__file__).resolve().parent.parent / "styles"
POP_ROCK_PACK = STYLES_ROOT / "pop_rock"
JAZZ_PACK = STYLES_ROOT / "jazz"


# A minimal valid progressions config for the single-file model rules
# (P2/P3/P5/P8/P9/P10); not derived from either reference pack.
MINIMAL_PROGRESSIONS: dict[str, Any] = {
    "pools": {
        "intro": [
            {
                "id": "i1",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
            }
        ],
    },
    "turnarounds": [
        {"id": "t1", "weight": 1, "modes": ["major"], "bars": [["ii7", "V7"]]},
    ],
    "finals": [
        {"id": "f1", "weight": 1, "modes": ["major"], "bars": [["V"], ["I"]]},
    ],
}


def test_valid_minimal_progressions_config_loads() -> None:
    cfg = ProgressionsConfig.model_validate(MINIMAL_PROGRESSIONS)
    assert cfg.pools["intro"][0].id == "i1"
    assert cfg.turnarounds[0].id == "t1"
    assert cfg.finals[0].id == "f1"


# --- §4.2 density (holds excluded) ------------------------------------------


def test_density_excludes_holds() -> None:
    """§4.2 density = totalTokens / totalBars across all phrase labels; holds
    (`~`) are excluded from the token count."""
    entry = PoolEntry.model_validate(
        {
            "id": "d",
            "weight": 1,
            "modes": ["minor"],
            # a: 3 tokens / 4 bars ; b: 2 / 4 ; c: 3 / 4  -> 8 / 12
            "phrases": {
                "a": [["i7"], ["iv7"], ["i7"], [None]],
                "b": [["iv7"], [None], ["i7"], [None]],
                "c": [["bVI7"], ["V7"], ["i7"], [None]],
            },
        }
    )
    assert entry.density == 8 / 12


def test_density_matches_reference_minor_quick() -> None:
    pack = load_pack(JAZZ_PACK)
    assert pack.progressions is not None
    minor_quick = next(
        e for e in pack.progressions.pools["blues_12"] if e.id == "minor_quick"
    )
    assert minor_quick.density == 8 / 12


# --- Reference packs load clean (DoD §14.1) ---------------------------------


def test_pop_rock_progressions_load_clean() -> None:
    pack = load_pack(POP_ROCK_PACK)
    assert pack.progressions is not None
    p = pack.progressions
    assert set(p.pools) == {"intro", "verse", "prechorus", "chorus", "bridge", "outro"}
    assert p.turnarounds == ()  # pop ships no turnarounds (v1)
    assert [f.id for f in p.finals] == [
        "authentic",
        "plagal",
        "minor_authentic",
        "minor_plagal",
    ]


def test_jazz_progressions_load_clean() -> None:
    pack = load_pack(JAZZ_PACK)
    assert pack.progressions is not None
    p = pack.progressions
    assert set(p.pools) == {"intro", "aaba_32", "blues_12", "outro"}
    assert len(p.turnarounds) == 7
    # tritone_turn ends on bII7 (SubV) — admitted by P8 as a dominant relaunch.
    assert any(t.id == "tritone_turn" for t in p.turnarounds)
    assert [f.id for f in p.finals] == [
        "two_five_close",
        "backdoor_close",
        "minor_close",
        "minor_plagal_close",
    ]


def test_resolve_pack_exposes_progressions() -> None:
    for name in ("pop_rock", "jazz"):
        pack = resolve_pack(name)
        assert pack is not None
        assert pack.progressions is not None


# --- P1/P4 cross-file checks demonstrably cover the reference forms ----------


def test_reference_served_tags_exactly_covered_by_pools() -> None:
    """P1 — every harmonyTag any forms bar option serves has a non-empty pool
    (checked against the real PHASE_3 forms.yaml)."""
    for pack_dir in (POP_ROCK_PACK, JAZZ_PACK):
        pack = load_pack(pack_dir)
        assert pack.forms is not None and pack.progressions is not None
        served, _reqs, _types = _forms_tag_usage(pack.forms)
        for tag in served:
            assert pack.progressions.pools.get(tag), tag
        # unused pools are legal, but the reference packs happen to use each.
        assert set(pack.progressions.pools) == served


# --- Single-file rule rejection fixtures (P2/P3/P5/P8/P9/P10) ----------------


def test_p2_rejects_duplicate_ids_in_pool() -> None:
    """P2 — entry ids unique per pool."""
    bad = deepcopy(MINIMAL_PROGRESSIONS)
    bad["pools"]["intro"].append(deepcopy(bad["pools"]["intro"][0]))
    with pytest.raises(ValidationError, match="duplicate entry id"):
        ProgressionsConfig.model_validate(bad)


def test_p2_rejects_zero_weight() -> None:
    """P2 — weight must be an int >= 1."""
    with pytest.raises(ValidationError):
        PoolEntry.model_validate(
            {"id": "x", "weight": 0, "modes": ["major"], "phrases": {"a": [["I"]]}}
        )


def test_p2_rejects_empty_modes() -> None:
    """P2 — modes must be non-empty."""
    with pytest.raises(ValidationError):
        PoolEntry.model_validate(
            {"id": "x", "weight": 1, "modes": [], "phrases": {"a": [["I"]]}}
        )


def test_p2_rejects_mode_outside_ladder() -> None:
    """P2 — modes must be a subset of the engine mode vocabulary."""
    with pytest.raises(ValidationError, match="P2"):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["lydian"],  # not in MODE_LADDER
                "phrases": {"a": [["I"]]},
            }
        )


def test_p3_rejects_valence_out_of_range() -> None:
    """P3 — valence band within [-1, 1]."""
    with pytest.raises(ValidationError, match="P3"):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "valence": [-2.0, 0.0],
                "phrases": {"a": [["I"]]},
            }
        )


def test_p3_rejects_reversed_dissonance_band() -> None:
    """P3 — dissonance band must satisfy lo <= hi."""
    with pytest.raises(ValidationError, match="P3"):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "dissonance": [0.8, 0.2],
                "phrases": {"a": [["I"]]},
            }
        )


def test_p5_rejects_three_token_bar() -> None:
    """P5 — a bar must have 1, 2, or 4 tokens."""
    with pytest.raises(ValidationError, match="P5"):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["I", "IV", "V"]]},
            }
        )


def test_p5_rejects_unparseable_token() -> None:
    """P5 — every token must parse per the §3.1 grammar."""
    with pytest.raises(ValidationError, match="P5"):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["I"], ["Q9"]]},
            }
        )


def test_p5_rejects_hold_in_first_bar() -> None:
    """P5 — `~` may never be a phrase's first bar."""
    with pytest.raises(ValidationError, match="first bar"):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [[None], ["I"], ["I"], ["I"]]},
            }
        )


def test_p5_rejects_hold_in_turnaround() -> None:
    """P5 — holds are never allowed in turnarounds/finals."""
    with pytest.raises(ValidationError, match="not allowed"):
        TurnaroundEntry.model_validate(
            {"id": "x", "weight": 1, "modes": ["major"], "bars": [["V7"], [None]]}
        )


def test_p8_rejects_non_dominant_turnaround_final() -> None:
    """P8 — a turnaround's final chord must be dominant-functioning."""
    with pytest.raises(ValidationError, match="P8"):
        TurnaroundEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "bars": [["ii7"], ["Imaj7"]],  # ends on tonic, not dominant
            }
        )


def test_p8_admits_tritone_substitute() -> None:
    """P8 — a bII dominant (SubV) is admitted as a dominant relaunch."""
    entry = TurnaroundEntry.model_validate(
        {"id": "x", "weight": 1, "modes": ["major"], "bars": [["ii7", "bII7"]]}
    )
    assert entry.bars[0][-1] == "bII7"


def test_p8_rejects_more_than_two_bars() -> None:
    """P8 — turnarounds are 1–2 bars."""
    with pytest.raises(ValidationError):
        TurnaroundEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "bars": [["V7"], ["V7"], ["V7"]],
            }
        )


def test_p9_rejects_non_degree1_final() -> None:
    """P9 — a finals entry's final chord must be rooted on degree 1."""
    with pytest.raises(ValidationError, match="P9"):
        FinalEntry.model_validate(
            {"id": "x", "weight": 1, "modes": ["major"], "bars": [["IV"], ["V"]]}
        )


def test_p9_rejects_empty_finals() -> None:
    """P9 — finals is required and non-empty."""
    bad = deepcopy(MINIMAL_PROGRESSIONS)
    bad["finals"] = []
    with pytest.raises(ValidationError):
        ProgressionsConfig.model_validate(bad)


def test_p10_rejects_unknown_key() -> None:
    """P10 — strict schema; unknown keys rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        PoolEntry.model_validate(
            {
                "id": "x",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["I"]]},
                "mood": "happy",  # not a schema field
            }
        )


# --- Cross-file rule rejection fixtures (P1/P4/P6/P7) via load_pack ----------


FORMS_MIN: dict[str, Any] = {
    "energyRange": [0.0, 1.0],
    "sections": {
        "intro": {"bars": [[4, 1]], "phrases": {4: ["a"]}, "harmonyTag": {4: "intro"}},
        "verse": {
            "bars": [[8, 1]],
            "phrases": {8: ["a", "a"]},
            "harmonyTag": {8: "verse"},
        },
        "prechorus": {
            "bars": [[4, 1]],
            "phrases": {4: ["a"]},
            "harmonyTag": {4: "prechorus"},
        },
    },
    "templates": [
        {
            "id": "simple",
            "weight": 1,
            "spine": [
                {"section": "intro"},
                {"section": "verse"},
                {"section": "prechorus"},
            ],
            "ending": {"tagBars": 0, "close": "cold"},
            "degrade": [],
            "fallback": {"section": "verse", "bars": 8},
        }
    ],
}

INTERP_MIN: dict[str, Any] = {
    "supportedMoods": ["happy"],
    "defaultMood": "happy",
    "modes": ["major"],
    "tonics": {"major": ["C"]},
    "feel": "straight8",
    "expressionRanges": {"density": [0.2, 0.85], "dissonance": [0.05, 0.4]},
    "flavors": {"drums": ["d"], "bass": ["b"], "comping": ["c"], "pads": ["p"]},
    "ensembles": {"default": {"drums": "d", "bass": "b", "comping": "c", "pads": "p"}},
}

PROG_MIN: dict[str, Any] = {
    "pools": {
        "intro": [
            {
                "id": "i1",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["I"], ["IV"], ["I"], ["IV"]]},
            }
        ],
        "verse": [
            {
                "id": "v1",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["I"], ["IV"], ["I"], ["V"]]},
            }
        ],
        "prechorus": [
            {
                "id": "p1",
                "weight": 1,
                "modes": ["major"],
                "phrases": {"a": [["IV"], ["V"], ["IV"], ["V"]]},
            }
        ],
    },
    "turnarounds": [],
    "finals": [{"id": "f1", "weight": 1, "modes": ["major"], "bars": [["V"], ["I"]]}],
}


def _write_full_pack(
    root: Path,
    *,
    forms: dict[str, Any],
    interpreter: dict[str, Any],
    progressions: dict[str, Any],
) -> Path:
    manifest = {
        "formatVersion": 1,
        "id": "_x",
        "name": "X",
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
    (root / "forms.yaml").write_text(yaml.safe_dump(forms))
    (root / "interpreter.yaml").write_text(yaml.safe_dump(interpreter))
    (root / "progressions.yaml").write_text(yaml.safe_dump(progressions))
    return root


def test_cross_file_valid_pack_loads(tmp_path: Path) -> None:
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=INTERP_MIN, progressions=PROG_MIN
    )
    pack = load_pack(pack_dir)
    assert pack.progressions is not None


def test_p1_rejects_forms_tag_without_pool(tmp_path: Path) -> None:
    """P1 (cross-file) — a harmonyTag used by forms must have a non-empty pool."""
    prog = deepcopy(PROG_MIN)
    del prog["pools"]["verse"]  # forms still uses the `verse` tag
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=INTERP_MIN, progressions=prog
    )
    with pytest.raises(PackLoadError, match="P1"):
        load_pack(pack_dir)


def test_p4_rejects_wrong_phrase_length(tmp_path: Path) -> None:
    """P4 (cross-file) — a pool entry must supply each label at the option's
    phrase length in bars."""
    prog = deepcopy(PROG_MIN)
    prog["pools"]["verse"][0]["phrases"]["a"] = [["I"], ["IV"], ["V"]]  # 3 bars, not 4
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=INTERP_MIN, progressions=prog
    )
    with pytest.raises(PackLoadError, match="P4"):
        load_pack(pack_dir)


def test_p4_rejects_wrong_phrase_labels(tmp_path: Path) -> None:
    """P4 (cross-file) — a pool entry must supply exactly the option's labels."""
    prog = deepcopy(PROG_MIN)
    prog["pools"]["verse"][0]["phrases"] = {"b": [["I"], ["IV"], ["I"], ["V"]]}
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=INTERP_MIN, progressions=prog
    )
    with pytest.raises(PackLoadError, match="P4"):
        load_pack(pack_dir)


def test_p6_rejects_uncovered_mode(tmp_path: Path) -> None:
    """P6 (cross-file) — every interpreter mode needs a band-free entry in
    every pool + finals."""
    interp = deepcopy(INTERP_MIN)
    interp["modes"] = ["major", "minor"]
    interp["tonics"]["minor"] = ["A"]
    # PROG_MIN carries only `major` entries → `minor` is uncovered.
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=interp, progressions=PROG_MIN
    )
    with pytest.raises(PackLoadError, match="P6"):
        load_pack(pack_dir)


def test_p7_rejects_non_open_intro_pool(tmp_path: Path) -> None:
    """P7 (cross-file) — an intro/verse pool's entries must not end degree-1
    rooted (must be open)."""
    prog = deepcopy(PROG_MIN)
    prog["pools"]["intro"][0]["phrases"]["a"] = [["IV"], ["I"], ["IV"], ["I"]]
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=INTERP_MIN, progressions=prog
    )
    with pytest.raises(PackLoadError, match="P7"):
        load_pack(pack_dir)


def test_p7_rejects_non_dominant_prechorus_pool(tmp_path: Path) -> None:
    """P7 (cross-file) — a prechorus/bridge pool's entries must end D-function."""
    prog = deepcopy(PROG_MIN)
    prog["pools"]["prechorus"][0]["phrases"]["a"] = [["IV"], ["V"], ["IV"], ["I"]]
    pack_dir = _write_full_pack(
        tmp_path, forms=FORMS_MIN, interpreter=INTERP_MIN, progressions=prog
    )
    with pytest.raises(PackLoadError, match="P7"):
        load_pack(pack_dir)
