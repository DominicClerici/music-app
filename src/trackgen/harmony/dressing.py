"""The dissonance-dressing ladder (PHASE_4 §6).

Maps `budgets.dissonance` (via a tier) plus a chord's function and bareness onto
the concrete color options the Harmony stage draws over. This module is the
**pure selection surface**: it computes tiers, applies the §6.2 function offset,
looks up the §6.3 option tables (loaded from `dressing.yaml`), and returns the
ordered list of candidate dressed `ChordSpec`s with their integer weights. It
performs **no draws** — the `weighted_choice` over these options happens later
in the harmony stage (§5.1 step 3d / 5). No randomness, no clock (ROADMAP
invariant 5): this module imports none of `random`/`secrets`/`uuid`/`time`.

The §6.3 printed tables are authoritative (ROADMAP §3 golden-value arbitration);
`dressing.yaml` transcribes them verbatim and this module never tunes them.

Ambiguities resolved (documented per the task brief):

* **Pinned dom7/maj7/min7 are indexed by *effective* tier.** The §6.2 offset
  applies to the base tier via the chord's function, then the §6.3 pinned
  extension tables are read at that effective tier — e.g. a pinned `V7`
  (D-function) at base tier 4 dresses at effective tier 5. This is the reading
  the §10.2 worked example confirms (V7 → A7b9 at base tier 4; iv7 → Gm9/Gm11 at
  base tier 4; bVI7 → Bb13 at base tier 4).
* **Bare major, function O** (altered degrees, e.g. `#IV`) uses the T/S table.
  §6.3 splits bare-major dressing into a D table and a "T/S" table; the D table
  carries the dominant tension, so every non-D function (T, S, and O, which all
  share offset 0/-1 and never take a dominant color) reads the T/S table. No v1
  pack produces a bare-major-O chord, so this only fixes determinism.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from trackgen.schema.ir import ChordQuality, ChordSpec
from trackgen.theory import Function, KeyLike, chord_symbol, extensions_legal

# PHASE_4 §6.1 — the seven-tier ceilings. tier(d) is the index of the first
# ceiling d falls *below*; d at or above the last ceiling is tier 6. Boundaries
# are half-open on the low side: tier k covers [ceiling[k-1], ceiling[k]), so an
# exact boundary value belongs to the higher tier it opens. This reproduces the
# printed bands' endpoints — tier 0 is strictly "< 0.15" and tier 6 is "≥ 0.90"
# — and the §10 anchors (0.132 → 0, 0.653 → 4). Using the same float literals as
# comparands keeps exact-boundary inputs (0.15, 0.30, …) deterministic.
_TIER_CEILINGS: tuple[float, ...] = (0.15, 0.30, 0.45, 0.60, 0.75, 0.90)
_MAX_TIER = 6

# PHASE_4 §6.2 — function → effective-tier offset. Tension lives on the
# dominant; tonics stay coolest.
_FUNCTION_OFFSET: dict[Function, int] = {"D": 1, "T": -1, "S": 0, "O": 0}

# The six dressable classes (§6.3). Everything else is passthrough (never
# dressed in v1).
_CLASS_NAMES: frozenset[str] = frozenset(
    {"bare_maj_ts", "bare_maj_d", "bare_min", "dom7", "maj7", "min7"}
)
_REQUIRED_TIERS: frozenset[int] = frozenset(range(_MAX_TIER + 1))


class DressingLoadError(Exception):
    """Raised when `dressing.yaml` is missing, malformed, or fails validation."""


class _DressingModel(BaseModel):
    """Shared base: frozen, strict (unknown keys rejected)."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class DressingOption(_DressingModel):
    """One §6.3 option: a resulting quality + extensions and its integer weight."""

    quality: ChordQuality
    extensions: list[str] = Field(default_factory=list)
    weight: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_legal(self) -> DressingOption:
        # §6.4 hard filter — every constructed option must be legal for its
        # quality (the document validator re-checks every emitted ChordSpec).
        if not extensions_legal(self.quality, self.extensions):
            raise ValueError(
                f"option {self.quality}+{self.extensions} violates the §6.4 "
                f"extension-availability filter"
            )
        return self


class DressingTable(_DressingModel):
    """The full §6.3 table: class → effective tier (0-6) → ordered options."""

    classes: dict[str, dict[int, list[DressingOption]]]

    @model_validator(mode="after")
    def _check_shape(self) -> DressingTable:
        keys = set(self.classes)
        unknown = keys - _CLASS_NAMES
        if unknown:
            raise ValueError(f"unknown dressing class(es) {sorted(unknown)}")
        missing = _CLASS_NAMES - keys
        if missing:
            raise ValueError(f"missing dressing class(es) {sorted(missing)}")
        for name, rows in self.classes.items():
            tiers = set(rows)
            if tiers != _REQUIRED_TIERS:
                raise ValueError(
                    f"class {name!r} must cover tiers 0-6 exactly, got {sorted(tiers)}"
                )
            for tier_index, options in rows.items():
                if not options:
                    raise ValueError(f"class {name!r} tier {tier_index} has no options")
        return self


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise DressingLoadError(
            f"{path}: could not read dressing file ({exc})"
        ) from exc
    except yaml.YAMLError as exc:
        raise DressingLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_dressing_table() -> DressingTable:
    """Load and validate `dressing.yaml` into a `DressingTable`."""
    path = Path(__file__).parent / "dressing.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise DressingLoadError(f"{path}: dressing file must be a mapping")
    try:
        return DressingTable.model_validate(raw)
    except ValidationError as exc:
        raise DressingLoadError(f"{path}: invalid dressing table\n{exc}") from exc


_dressing_table_cache: DressingTable | None = None


def _default_table() -> DressingTable:
    global _dressing_table_cache
    if _dressing_table_cache is None:
        _dressing_table_cache = load_dressing_table()
    return _dressing_table_cache


def tier(dissonance: float) -> int:
    """PHASE_4 §6.1 — the dissonance tier (0-6) for a pack-scaled dissonance.

    Half-open low-closed bands: tier k covers ``[ceiling[k-1], ceiling[k])`` so a
    value landing exactly on a ceiling belongs to the higher tier it opens
    (tier 0 is strictly ``< 0.15``; tier 6 is ``>= 0.90``). §10 anchors:
    0.132 → 0, 0.653 → 4.
    """
    for index, ceiling in enumerate(_TIER_CEILINGS):
        if dissonance < ceiling:
            return index
    return _MAX_TIER


def effective_tier(base_tier: int, function: Function) -> int:
    """PHASE_4 §6.2 — ``clamp(base_tier + offset, 0, 6)`` (D:+1, T:−1, S/O:0)."""
    shifted = base_tier + _FUNCTION_OFFSET[function]
    return max(0, min(_MAX_TIER, shifted))


def _dressing_class(spec: ChordSpec, was_bare: bool, function: Function) -> str | None:
    """The §6.3 dressing class for a chord slot, or ``None`` for passthrough.

    Bare tokens (no quality suffix) are always `maj` or `min` (case-derived,
    §3.1) → the bare tables, with a bare major split by function (D vs the
    T/S/O default). Suffixed tokens are pinned: only `dom7`/`maj7`/`min7` are
    dressable (extensions only); every other suffixed quality is passthrough.
    """
    if was_bare:
        if spec.quality == "maj":
            return "bare_maj_d" if function == "D" else "bare_maj_ts"
        if spec.quality == "min":
            return "bare_min"
        return None  # defensive: a bare token resolves only to maj/min
    if spec.quality in ("dom7", "maj7", "min7"):
        return spec.quality
    return None


def dressing_options(
    spec: ChordSpec,
    was_bare: bool,
    function: Function,
    base_tier: int,
    key: KeyLike,
    table: DressingTable | None = None,
) -> list[tuple[ChordSpec, int]]:
    """The §6.3/§6.4 dressing options for one chord slot — the pure draw surface.

    Given the parsed `spec`, whether the source token was **bare** (dressable) or
    suffixed (pinned), the chord's `function` (§3.2), and the song's `base_tier`
    (`tier(budgets.dissonance)`), return the ordered list of candidate dressed
    `ChordSpec`s and their integer weights, in §6.3 authored order. The caller
    picks one via `weighted_choice` (draw iff ≥ 2 options); this function draws
    nothing and is a pure function of its inputs.

    Passthrough classes (dim, dim7, aug, sus*, maj6, min6, minMaj7, min7b5, and
    any bare non-triad) return the single unchanged spec — one option, no draw.

    Each produced spec keeps the original root/bass/roman, takes the option's
    quality + extensions, and has its `symbol` re-derived via
    `chord_symbol` (§3.3). Every option is asserted §6.4-legal.
    """
    cls = _dressing_class(spec, was_bare, function)
    if cls is None:
        return [(spec, 1)]

    if table is None:
        table = _default_table()

    eff = effective_tier(base_tier, function)
    options = table.classes[cls][eff]

    result: list[tuple[ChordSpec, int]] = []
    for option in options:
        if not extensions_legal(option.quality, option.extensions):
            raise AssertionError(
                f"§6.4 violation for {option.quality}+{option.extensions} "
                f"(class {cls!r}, tier {eff})"
            )
        draft = ChordSpec(
            root_pc=spec.root_pc,
            quality=option.quality,
            extensions=list(option.extensions),
            bass_pc=spec.bass_pc,
            symbol="",
            roman=spec.roman,
        )
        dressed = draft.model_copy(update={"symbol": chord_symbol(draft, key)})
        result.append((dressed, option.weight))
    return result
