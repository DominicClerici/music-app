"""Real `timbres.yaml` loading + TB1-live tests (PHASE_7 §4/§4.5, SESSION_14 T2).

After the C2 flip, `resolve_pack` validates each pack's `timbres.yaml` with the
real `sound.timbres.TimbresConfig` and runs TB1 (flavor completeness) against the
pack's `interpreter.yaml`. These tests prove both reference packs load clean
(DoD 1), that the loaded flavor-id sets equal the interpreter-declared sets, and
that TB1 rejects a declared/recipe mismatch.
"""

from __future__ import annotations

import pytest

from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.sound.timbres import (
    KIT_VOICE_IDS,
    TimbresConfig,
    check_flavor_completeness,
)

# The flavor ids each pack's interpreter.yaml declares (TB1 must match exactly).
_POP_FLAVORS: dict[str, set[str]] = {
    "drums": {"acoustic_kit", "tight_kit"},
    "bass": {"electric_fingered", "electric_picked"},
    "comping": {"clean_electric", "crunch_electric", "piano"},
    "pads": {"warm_analog", "airy_strings"},
}
_JAZZ_FLAVORS: dict[str, set[str]] = {
    "drums": {"brush_kit", "ride_kit"},
    "bass": {"upright"},
    "comping": {"piano", "guitar_hollow"},
    "pads": {"airy_strings", "organ_soft"},
}


def _pack(style: str) -> StylePack:
    pack = resolve_pack(style)
    assert pack is not None
    return pack


def test_both_packs_load_with_real_timbres() -> None:
    """DoD 1 — both reference packs load clean with a real `TimbresConfig`
    (the loader validated TB1-TB9 + TB1-live without raising)."""
    for style in ("pop_rock", "jazz"):
        assert isinstance(_pack(style).timbres, TimbresConfig)


def test_loaded_flavor_ids_equal_declared() -> None:
    """The loaded timbres flavor ids per role equal the interpreter-declared set
    (TB1 is unconditional), and every drum kit defines the nine voices."""
    for style, expected in (("pop_rock", _POP_FLAVORS), ("jazz", _JAZZ_FLAVORS)):
        timbres = _pack(style).timbres
        assert timbres is not None
        assert set(timbres.flavors.drums) == expected["drums"]
        assert set(timbres.flavors.bass) == expected["bass"]
        assert set(timbres.flavors.comping) == expected["comping"]
        assert set(timbres.flavors.pads) == expected["pads"]
        for kit_flavor in timbres.flavors.drums.values():
            assert set(kit_flavor.kit) == set(KIT_VOICE_IDS)


def test_tb1_rejects_declared_recipe_mismatch() -> None:
    """TB1 fires on a dangling declaration (declared id with no recipe)."""
    timbres = _pack("pop_rock").timbres
    assert timbres is not None
    declared = {role: set(ids) for role, ids in _POP_FLAVORS.items()}
    declared["drums"] = declared["drums"] | {"phantom_kit"}
    with pytest.raises(ValueError, match="TB1"):
        check_flavor_completeness(timbres, declared)
