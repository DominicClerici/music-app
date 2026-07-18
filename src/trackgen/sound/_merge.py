"""Shared mod-merge + option-path helpers (PHASE_7 §3.2).

Extracted from ``sound/timbres.py`` so the two callers that need one source of
truth for the ``attack_hardness`` → ``attackHardness`` normalization and the drum
``(directive, voice)`` keying share it: the ``timbres.yaml`` TB7 validator (which
checks the *effective* merged mappings) and the ``sound_design`` stage (which
evaluates them). Both feed the merged tables into ``evaluate.merge_mod`` /
``evaluate.apply_directives``.

The schema-model type hints (``EngineSpec`` / ``PitchedMod`` / ``KitMod``) are
``TYPE_CHECKING``-only imports: ``timbres.py`` imports *this* module at load
time, so importing those models back at runtime would be circular. The helpers
never construct them — they only read attributes — so string annotations plus
duck typing suffice.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any

from trackgen.sound.mod_defaults import ModDefaults, PitchedModDefaults
from trackgen.sound.models import MappingEntry

if TYPE_CHECKING:
    from trackgen.sound.timbres import EngineSpec, KitMod, PitchedMod


def leaf_paths(options: Mapping[str, Any], prefix: str = "") -> Iterator[str]:
    """Enumerate the dotted leaf option paths of a nested options dict — a leaf
    is any value that is not itself a mapping (a list value, e.g.
    ``oscillator.partials``, is a leaf whose path is the option path)."""
    for key, value in options.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            yield from leaf_paths(value, f"{path}.")
        else:
            yield path


def engine_class(engine: EngineSpec) -> str:
    """The synthesis class the base options + mod params are validated/evaluated
    against: the PolySynth ``voice`` for a PolySynth engine, else the ``type``
    itself. TB2 guarantees a PolySynth carries a ``voice``, so the fallback is
    unreachable for a PolySynth."""
    if engine.type == "PolySynth" and engine.voice is not None:
        return engine.voice
    return engine.type


def pitched_defaults(
    role_md: PitchedModDefaults,
) -> dict[str, tuple[MappingEntry, ...]]:
    """The role's default mapping table in the directive-keyed shape ``merge_mod``
    consumes (normalising the ``attack_hardness`` field name to
    ``attackHardness``)."""
    return {
        "brightness": role_md.brightness,
        "attackHardness": role_md.attack_hardness,
        "space": role_md.space,
    }


def pitched_override(
    mod: PitchedMod | None,
) -> dict[str, tuple[MappingEntry, ...]] | None:
    """The flavor's ``mod`` in ``merge_mod`` override shape: a directive appears
    iff the flavor authored it (``None`` = absent = keep default; ``[]`` =
    disable)."""
    if mod is None:
        return None
    override: dict[str, tuple[MappingEntry, ...]] = {}
    if mod.brightness is not None:
        override["brightness"] = mod.brightness
    if mod.attack_hardness is not None:
        override["attackHardness"] = mod.attack_hardness
    if mod.space is not None:
        override["space"] = mod.space
    return override or None


def drum_defaults(
    defaults: ModDefaults,
) -> dict[tuple[str, str], tuple[MappingEntry, ...]]:
    """The drum default table keyed by ``(directive, voice)`` — the shape
    ``merge_mod`` uses for drums (§3.2). Drums carry brightness + space only
    (D4)."""
    drums = defaults.drums
    out: dict[tuple[str, str], tuple[MappingEntry, ...]] = {}
    for voice, entries in drums.brightness.items():
        out[("brightness", voice)] = entries
    for voice, entries in drums.space.items():
        out[("space", voice)] = entries
    return out


def drum_override(
    mod: KitMod | None,
) -> dict[tuple[str, str], tuple[MappingEntry, ...]] | None:
    if mod is None:
        return None
    out: dict[tuple[str, str], tuple[MappingEntry, ...]] = {}
    # Drums carry brightness + space only — attackHardness is barred (D4).
    for directive, table in (
        ("brightness", mod.brightness),
        ("space", mod.space),
    ):
        if table is None:
            continue
        for voice, entries in table.items():
            out[(directive, voice)] = entries
    return out or None
