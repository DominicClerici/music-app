"""Style-pack structure (PHASE_1 §6).

Frozen pydantic v2 models for the pack manifest (§6.1), the shared pattern
envelope (§6.2), and the event primitives (§6.3). Bank-specific fields owned
by later phases (progressions/forms/timbres/interpreter schemas, and any
role-specific envelope extensions) are deliberately NOT modeled here.

`degree` is restricted to the §6.3 v1 core vocabulary only: `root, third,
fifth, seventh, guide3, guide7, tension, approach`. Phase 5's later
extensions (`sixth`, `chord`, `push`, `minDensity`) are out of scope.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from trackgen.schema.document import Role

Degree = Literal[
    "root",
    "third",
    "fifth",
    "seventh",
    "guide3",
    "guide7",
    "tension",
    "approach",
]

DrumVoice = Literal[
    "kick",
    "snare",
    "hat_closed",
    "hat_open",
    "ride",
    "crash",
    "tom_low",
    "tom_mid",
    "tom_high",
    "perc",
]

PatternKind = Literal["main", "fill", "intro", "ending", "break"]

OnChordChange = Literal["hold", "retrigger", "stop"]


class PackModel(BaseModel):
    """Shared base: frozen, camelCase JSON aliases, alias-or-name construction."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Manifest(PackModel):
    """§6.1 `manifest.yaml` (pinned)."""

    format_version: int
    id: str
    name: str
    version: str
    engine: str
    time_signatures: list[tuple[int, int]]
    tempo_range: tuple[int, int]


class PitchedEvent(PackModel):
    """§6.3 pitched-role event: rhythm + chord-degree, never a literal pitch."""

    pos: int = Field(ge=0)
    dur: int = Field(ge=1)
    degree: Degree
    octave: int
    velocity: float = Field(gt=0, le=1)


class DrumEvent(PackModel):
    """§6.3 drum event: voice + velocity, no harmonic content."""

    pos: int = Field(ge=0)
    voice: DrumVoice
    velocity: float = Field(gt=0, le=1)


class Retarget(PackModel):
    """§6.2 `retarget` — pinned envelope + event fields only."""

    register_low: int
    register_high: int
    on_chord_change: OnChordChange


class Eligibility(PackModel):
    """§6.2 `eligibility` — v1: optional `tempoBpm: [min, max]` only."""

    tempo_bpm: tuple[int, int] | None = None


class PatternEnvelope(PackModel):
    """§6.2 shared pattern envelope, carried by every entry in every bank."""

    id: str
    role: Role
    kind: PatternKind
    energy_level: int = Field(ge=1, le=4)
    length_ticks: int = Field(ge=1)
    weight: int = Field(ge=1)
    eligibility: Eligibility = Field(default_factory=Eligibility)
    events: list[PitchedEvent | DrumEvent]
    retarget: Retarget


class ExpressionRanges(PackModel):
    """PHASE_2 §5.1 — style-relative floors/ceilings for the pack-scaled budgets."""

    density: tuple[float, float]
    dissonance: tuple[float, float]

    @model_validator(mode="after")
    def _check_ranges(self) -> "ExpressionRanges":
        for name, (lo, hi) in (
            ("density", self.density),
            ("dissonance", self.dissonance),
        ):
            if not (0 <= lo <= 1 and 0 <= hi <= 1):
                raise ValueError(
                    f"expressionRanges.{name} values must be within [0, 1], "
                    f"got {(lo, hi)}"
                )
            if lo > hi:
                raise ValueError(
                    f"expressionRanges.{name}: lo ({lo}) must be <= hi ({hi})"
                )
        return self


class InterpreterConfig(PackModel):
    """PHASE_2 §5.1 `interpreter.yaml` — style × mood interaction data."""

    supported_moods: list[str]
    default_mood: str
    modes: list[str]
    tonics: dict[str, list[str]]
    feel: Literal["straight8", "straight16", "swing8", "swing16"]
    swing_ratio: float | None = None
    feel_table: str | None = None
    expression_ranges: ExpressionRanges
    flavors: dict[Role, list[str]]
    ensembles: dict[str, dict[Role, str]]

    @model_validator(mode="after")
    def _check_rules(self) -> "InterpreterConfig":
        # Lazy import to break the import cycle: `trackgen.interpreter.moods`
        # imports `PackModel` from this module at module load time, so a
        # module-level import here would be circular. Deferring the import
        # into this validator body (only run at instance-construction time,
        # well after both modules have finished loading) breaks the cycle.
        from trackgen.interpreter.moods import MODE_LADDER, MOOD_VOCABULARY
        from trackgen.interpreter.params import parse_tonic

        mood_vocab = set(MOOD_VOCABULARY)

        # Rule 1: supportedMoods non-empty, subset of the 12-word vocabulary.
        if not self.supported_moods:
            raise ValueError("supportedMoods must be non-empty")
        unknown_moods = set(self.supported_moods) - mood_vocab
        if unknown_moods:
            raise ValueError(
                f"supportedMoods contains unknown mood word(s): {sorted(unknown_moods)}"
            )

        # Rule 2: defaultMood in supportedMoods.
        if self.default_mood not in self.supported_moods:
            raise ValueError(
                f"defaultMood {self.default_mood!r} must be in supportedMoods "
                f"{self.supported_moods}"
            )

        # Rule 3: modes non-empty, ordered subsequence of MODE_LADDER, no dupes.
        if not self.modes:
            raise ValueError("modes must be non-empty")
        unknown_modes = set(self.modes) - set(MODE_LADDER)
        if unknown_modes:
            raise ValueError(f"modes contains unknown mode(s): {sorted(unknown_modes)}")
        if len(set(self.modes)) != len(self.modes):
            raise ValueError(f"modes must not contain duplicates: {self.modes}")
        ladder_indices = [MODE_LADDER.index(mode) for mode in self.modes]
        if ladder_indices != sorted(ladder_indices):
            raise ValueError(
                f"modes must be in mode-ladder order {MODE_LADDER}; got {self.modes}"
            )

        # Rule 4: every mode has a non-empty tonics entry, and every tonic is a
        # parseable note name (the Interpreter takes tonics[mode][0] as the
        # auto-key root, so an unparseable entry must fail at pack load, not at
        # interpret time).
        for mode in self.modes:
            tonics = self.tonics.get(mode)
            if not tonics:
                raise ValueError(f"tonics[{mode!r}] must be a non-empty list")
            bad = [t for t in tonics if parse_tonic(t) is None]
            if bad:
                raise ValueError(
                    f"tonics[{mode!r}] has unparseable note name(s): {bad}"
                )

        # Rule 5 (expression_ranges [0,1] & lo<=hi) is enforced by
        # ExpressionRanges itself.

        # Rule 6: every Role present in flavors with >= 1 id.
        roles: tuple[Role, ...] = ("drums", "bass", "comping", "pads")
        for role in roles:
            if not self.flavors.get(role):
                raise ValueError(f"flavors[{role!r}] must be a non-empty list")

        # Rule 7: ensembles contains 'default'; every ensemble covers all
        # four roles; every value is a declared flavor id for that role.
        if "default" not in self.ensembles:
            raise ValueError("ensembles must contain a 'default' key")
        for ensemble_name, role_map in self.ensembles.items():
            missing_roles = set(roles) - set(role_map)
            if missing_roles:
                raise ValueError(
                    f"ensembles[{ensemble_name!r}] is missing role(s): "
                    f"{sorted(missing_roles)}"
                )
            for role, flavor_id in role_map.items():
                if flavor_id not in self.flavors.get(role, []):
                    raise ValueError(
                        f"ensembles[{ensemble_name!r}][{role!r}] = "
                        f"{flavor_id!r} is not a declared flavor id for {role!r}"
                    )

        return self


class StylePack(PackModel):
    """A loaded, validated style pack: manifest + per-role pattern banks."""

    manifest: Manifest
    patterns: dict[str, list[PatternEnvelope]]
    interpreter: InterpreterConfig | None = None
