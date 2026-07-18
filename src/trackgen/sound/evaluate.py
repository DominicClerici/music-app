"""Patch-evaluation model (PHASE_7 §3).

Pure functions that bake a flavor's base patch plus its merged directive
mappings into concrete Tone.js constructor options, once per song. No RNG and no
wall-clock (D3, ROADMAP inv. 5): every value is a deterministic function of the
mapping ranges and the three directive scalars, rounded 3-decimal half-even
(§3.1).

Consumed by the sound-design stage (§7: ``merge_mod`` then ``apply_directives``)
and by the ``timbres.yaml`` TB7 validator (``assert_base_xor_mod`` on the merged
mapping targets vs the base paths, §3.3). The signatures are deliberately plain
so both callers can adapt their pydantic models into them:

- ``merge_mod`` is generic over the mapping key so one per-key replacement rule
  serves both flavor shapes (§3.2): pitched flavors key by directive name
  (``str``); drum kits key by ``(directive, voice)`` (a ``tuple``). Callers key
  pitched mods by the camelCase directive names ``brightness`` /
  ``attackHardness`` / ``space`` (matching ``timbreDirectives`` and the §4.2
  schema ``mod`` keys), normalising the ``PitchedModDefaults.attack_hardness``
  field name at the boundary.
- ``apply_directives`` works on a single mutable dict where the patch options
  sit at the top level and the flavor mix block sits under a ``mix`` key, so an
  options path like ``filterEnvelope.baseFrequency`` and a mix path like
  ``mix.sends.reverb`` (§3.1) are both plain dotted-path writes — the ``mix.``
  prefix alone routes a value into the mix block. The stage assembles that dict
  as ``{**base_options, "mix": mix_block}`` and splits it back out afterwards.

``get_by_path`` / ``set_by_path`` are exposed for reuse by the TB3/TB4/TB7
allowlist path checks.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from trackgen.sound.models import MappingEntry

# Fixed evaluation order (§3.4). Load-bearing only for pathological same-path
# authoring, but pinned so that case is still deterministic.
_DIRECTIVE_ORDER: tuple[str, str, str] = ("brightness", "attackHardness", "space")


def round3(x: float) -> float:
    """3-decimal half-even rounding (§3.1) — the repo idiom ``round(x, 3)``."""
    return round(x, 3)


def evaluate_mapping(entry: MappingEntry, d: float) -> float:
    """Evaluate one mapping at directive value ``d ∈ [0, 1]`` (§3.1).

    ``linear``: ``min + d(max − min)``; ``exp``: ``min·(max/min)^d``. Inverted
    ranges (``min > max``) fall out of the same formulas unchanged —
    ``attackHardness`` maps slow→fast that way (§3.1). ``exp`` positivity is
    already guaranteed by ``MappingEntry`` (§3.1), so the ratio is well-defined.
    """
    if entry.curve == "exp":
        value = entry.min * (entry.max / entry.min) ** d
    else:
        value = entry.min + d * (entry.max - entry.min)
    return round3(value)


def merge_mod[KeyT](
    defaults: Mapping[KeyT, Sequence[MappingEntry]],
    override: Mapping[KeyT, Sequence[MappingEntry]] | None,
) -> dict[KeyT, tuple[MappingEntry, ...]]:
    """Per-directive-key replacement merge (§3.2).

    A present override list replaces the whole default list for its key; an empty
    override list explicitly disables that key (kept as an empty tuple); an absent
    key keeps the default. There is no entry-level merging — whoever owns the key
    owns the whole list. Generic over the key type so pitched (key = directive)
    and drum (key = ``(directive, voice)``) tables share one rule.
    """
    merged: dict[KeyT, tuple[MappingEntry, ...]] = {
        key: tuple(entries) for key, entries in defaults.items()
    }
    if override is not None:
        for key, entries in override.items():
            merged[key] = tuple(entries)
    return merged


def assert_base_xor_mod(base_paths: set[str], mapped_paths: set[str]) -> None:
    """Raise if any param path is set by both ``base`` and a mapping (§3.3).

    A mapped parameter must be the single authority for its value — absent from
    ``base`` — so the "which value wins" ambiguity cannot arise. TB7 calls this
    after ``merge_mod`` with the merged mapping targets vs the base leaf paths.
    """
    conflicts = base_paths & mapped_paths
    if conflicts:
        joined = ", ".join(sorted(conflicts))
        raise ValueError(
            f"base XOR mod violated (§3.3): {joined} set by both the base patch "
            f"and a directive mapping; a mapped param must be absent from base"
        )


def apply_directives(
    base: dict[str, Any],
    mod: Mapping[str, Sequence[MappingEntry]],
    directive_values: Mapping[str, float],
) -> dict[str, Any]:
    """Bake the directives into a deep copy of ``base`` (§3.4).

    Applies the fixed order ``brightness → attackHardness → space``, each mapping
    list in authored order, writing each evaluated value into the copy by dotted
    path. Paths route by prefix: ``mix.sends.reverb`` lands in the ``mix``
    sub-dict, options paths land in the options tree. Zero RNG.
    """
    result = copy.deepcopy(base)
    for directive in _DIRECTIVE_ORDER:
        entries = mod.get(directive)
        if not entries:
            continue
        d = directive_values[directive]
        for entry in entries:
            set_by_path(result, entry.param, evaluate_mapping(entry, d))
    return result


def set_by_path(root: dict[str, Any], path: str, value: Any) -> None:
    """Set ``value`` at a dotted ``path`` in ``root``, creating missing
    intermediate dicts (e.g. ``mix.sends`` when a base carries no fixed send)."""
    segments = path.split(".")
    node = root
    for seg in segments[:-1]:
        child = node.get(seg)
        if not isinstance(child, dict):
            # Base XOR mod (§3.3) guarantees a mapped leaf is absent from base;
            # only genuinely-missing intermediates (an omitted `sends`) are
            # created here — a real nested object already present is descended.
            child = {}
            node[seg] = child
        node = child
    node[segments[-1]] = value


def get_by_path(root: Mapping[str, Any], path: str) -> Any:
    """Read the value at a dotted ``path`` in ``root`` (raises ``KeyError`` if
    absent)."""
    node: Any = root
    for seg in path.split("."):
        node = node[seg]
    return node
