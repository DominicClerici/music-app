"""Style-pack structure (PHASE_1 §6, PHASE_5 §5).

Frozen pydantic v2 models for the pack manifest (§6.1), the shared pattern
envelope (§6.2), the event primitives (§6.3), and the per-role pattern-bank
shapes PHASE_5 §5 adds (`layeringOrder`, bass `mode`/`walking`, comping/pads
`voicing.classes`).

`degree` covers the §6.3 v1 core vocabulary plus PHASE_5 §3.3's additive
extensions `sixth` (blues boogie cell) and `chord` (comping/pads voicing hits).
Events also gain PHASE_5's `push` (pitched only) and `minDensity` fields.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from trackgen.schema.document import InstrumentPatch, Role

Degree = Literal[
    "root",
    "third",
    "fifth",
    "sixth",
    "seventh",
    "guide3",
    "guide7",
    "tension",
    "approach",
    "chord",
]

# PHASE_5 §5.4/§6.5 — the nine committed voicing-class names (PHASE_4 §8.4 ∪
# {`fifths`}), the exact set `theory.voicing` implements. Single source of
# truth for PT7's allowed `voicing.classes` names.
VOICING_CLASSES: tuple[str, ...] = (
    "shell2",
    "shell3",
    "rootless_a",
    "rootless_b",
    "drop2",
    "triad_close",
    "triad_open",
    "quartal",
    "fifths",
)

# PHASE_1: PPQ 480, 4/4 — one bar is 1920 ticks. v1 packs are 4/4 only, so
# PT1's "whole number of bars" is a multiple of this constant.
_TICKS_PER_BAR = 1920

# One quarter-note beat (PHASE_6 §3.3 `beatFloor` granularity).
_TICKS_PER_BEAT = 480

# PHASE_6 §3.7 — the closed mutation-operator vocabulary, per role. `none`
# (the heavy no-op bias) is always legal in a table; these are the drawable
# ops. Single source of truth for TR3's op-name check.
DRUM_MUTATION_OPS: tuple[str, ...] = ("hat_lift", "drop_ornament", "kick_pickup")
COMPING_MUTATION_OPS: tuple[str, ...] = ("anticipate", "drop_hit")

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

# PHASE_3 §3.1 — the closed, v1-complete section-type vocabulary. Single
# source of truth: `forms.yaml`'s `sections` keys and template `spine`
# `section` references are validated against this list (F1); nothing else in
# the codebase should re-list these eleven words.
SECTION_TYPES: tuple[str, ...] = (
    "intro",
    "verse",
    "prechorus",
    "chorus",
    "postchorus",
    "bridge",
    "head",
    "solo",
    "main",
    "breakdown",
    "outro",
)


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
    """§6.3 pitched-role event: rhythm + chord-degree, never a literal pitch.

    PHASE_5 additions: `push` (anticipation, §3.3), `minDensity` (density gate,
    §3.5), and `octave` is now optional/defaulted — §7 `degree: chord`
    comping/pads events author no octave (placement/anchor rules do not apply
    to voiced hits, §3.3)."""

    pos: int = Field(ge=0)
    dur: int = Field(ge=1)
    degree: Degree
    octave: int = 0
    velocity: float = Field(gt=0, le=1)
    push: bool = False
    min_density: float | None = Field(default=None, ge=0, le=1)  # PT8


class DrumEvent(PackModel):
    """§6.3 drum event: voice + velocity, no harmonic content.

    PHASE_5 additions: `dur` (optional, defaults per voice at render — §8.2)
    and `minDensity` (§3.5). Carries no `degree`/`push`/`octave` — PT3's drum/
    pitched split is enforced structurally by `extra="forbid"`."""

    pos: int = Field(ge=0)
    voice: DrumVoice
    velocity: float = Field(gt=0, le=1)
    dur: int | None = Field(default=None, ge=1)  # PT2 (dur >= 1 where present)
    min_density: float | None = Field(default=None, ge=0, le=1)  # PT8


class Retarget(PackModel):
    """§6.2 `retarget` — pinned envelope + event fields only."""

    register_low: int
    register_high: int
    on_chord_change: OnChordChange


class Eligibility(PackModel):
    """§6.2 `eligibility` — v1: optional `tempoBpm: [min, max]` only."""

    tempo_bpm: tuple[int, int] | None = None

    @model_validator(mode="after")
    def _check_tempo_band(self) -> "Eligibility":
        if self.tempo_bpm is not None:
            lo, hi = self.tempo_bpm
            if lo <= 0 or lo > hi:
                raise ValueError(
                    f"eligibility.tempoBpm must satisfy 0 < min <= max, "
                    f"got {self.tempo_bpm} (PT4)"
                )
        return self


class PatternEnvelope(PackModel):
    """§6.2 shared pattern envelope, carried by every entry in every bank.

    `retarget` is now optional: pitched-role patterns (bass/comping/pads) must
    carry it (PT9); drum patterns must not (§5.2). The `_check_envelope`
    validator enforces PT1 (lengthTicks whole bars, `fill` = 1 bar), PT2 (event
    `pos` in-range; authored order is authoritative, not required to be sorted),
    PT3 (drum vs pitched event split by role), and PT9 (retarget presence +
    span)."""

    id: str
    role: Role
    kind: PatternKind
    energy_level: int = Field(ge=1, le=4)
    length_ticks: int = Field(ge=1)
    weight: int = Field(ge=1)
    eligibility: Eligibility = Field(default_factory=Eligibility)
    events: list[PitchedEvent | DrumEvent]
    retarget: Retarget | None = None

    @property
    def is_gated(self) -> bool:
        """True iff an `eligibility.tempoBpm` gate is authored (PT5 reads this:
        completeness requires *ungated* mains/intro/ending)."""
        return self.eligibility.tempo_bpm is not None

    @model_validator(mode="after")
    def _check_envelope(self) -> "PatternEnvelope":
        # PT1: lengthTicks a positive whole number of bars; fill = exactly 1 bar.
        if self.length_ticks % _TICKS_PER_BAR != 0:
            raise ValueError(
                f"pattern {self.id!r}: lengthTicks ({self.length_ticks}) must be "
                f"a positive whole number of bars (multiple of {_TICKS_PER_BAR}) "
                f"(PT1)"
            )
        if self.kind == "fill" and self.length_ticks != _TICKS_PER_BAR:
            raise ValueError(
                f"pattern {self.id!r}: kind 'fill' must be exactly 1 bar "
                f"({_TICKS_PER_BAR} ticks), got {self.length_ticks} (PT1)"
            )

        # PT3: role dictates event type — drums carry `voice` events, pitched
        # roles carry `degree` events. (Field vocabulary itself is structural
        # via `extra="forbid"`; this pins the drum/pitched split by role.)
        is_drums = self.role == "drums"
        for event in self.events:
            if is_drums and not isinstance(event, DrumEvent):
                raise ValueError(
                    f"pattern {self.id!r}: role 'drums' must carry drum (voice) "
                    f"events, not a pitched degree event (PT3)"
                )
            if not is_drums and not isinstance(event, PitchedEvent):
                raise ValueError(
                    f"pattern {self.id!r}: pitched role {self.role!r} must carry "
                    f"degree events, not a drum (voice) event (PT3)"
                )

        # PT2: pos in [0, lengthTicks). Authored order is authoritative, not
        # required to be sorted — §7 reference patterns are authored
        # voice-grouped (pos decreases across voices) and generators sort at
        # emit time (§6), so authored pos values need not be non-decreasing.
        for event in self.events:
            if event.pos >= self.length_ticks:
                raise ValueError(
                    f"pattern {self.id!r}: event pos ({event.pos}) must be "
                    f"< lengthTicks ({self.length_ticks}) (PT2)"
                )

        # PT9: retarget present with span >= 12 for pitched roles; drums exempt
        # and must carry no retarget (§5.2).
        if is_drums:
            if self.retarget is not None:
                raise ValueError(
                    f"pattern {self.id!r}: drum patterns carry no retarget block "
                    f"(§5.2, PT9)"
                )
        else:
            if self.retarget is None:
                raise ValueError(
                    f"pattern {self.id!r}: pitched role {self.role!r} requires a "
                    f"retarget block (PT9)"
                )
            low, high = self.retarget.register_low, self.retarget.register_high
            if low >= high or high - low < 12:
                raise ValueError(
                    f"pattern {self.id!r}: retarget requires registerLow < "
                    f"registerHigh with span >= 12, got [{low}, {high}] (PT9)"
                )

        return self


def fill_window(env: PatternEnvelope) -> tuple[int, int]:
    """PHASE_6 §3.3 — a `kind: fill` pattern's content window
    `[beatFloor(first event pos), lengthTicks)`.

    `beatFloor` rounds the earliest authored event position down to its
    containing beat (480 ticks); `lengthTicks` (a fill is exactly 1 bar by PT1)
    is the exclusive end. Packs author fill size *as content* — a big fill
    opens at beat 1 (window = whole bar), a medium fill at beat 3. The loader
    computes and caches this per fill id (`StylePack.fill_windows`) at load,
    guarding TR6 (window non-empty) and TR7 (an event reaches the barline);
    stage 6 (T2) reads the cache. Events are not required to be sorted (PT2),
    so the earliest event is `min(pos)`, not the first authored entry."""
    first_pos = min(event.pos for event in env.events)
    start = (first_pos // _TICKS_PER_BEAT) * _TICKS_PER_BEAT
    return start, env.length_ticks


class WalkingConfig(PackModel):
    """§5.3 bass `walking:` block — the walker's per-rung feel + draw weights.

    Present iff `bass.yaml` declares `mode: walking` (the cross-check is
    loader-level, PT6). PT6 model rules: `feelByIntensity` covers rungs 1–4 with
    values `two|four`; both weight maps are non-empty with integer weights ≥ 1."""

    feel_by_intensity: dict[int, Literal["two", "four"]]
    approach_weights: dict[str, int]
    beat1_repeat_weights: dict[str, int]

    @model_validator(mode="after")
    def _check(self) -> "WalkingConfig":
        if set(self.feel_by_intensity) != {1, 2, 3, 4}:
            raise ValueError(
                f"walking.feelByIntensity must cover rungs 1-4, got "
                f"{sorted(self.feel_by_intensity)} (PT6)"
            )
        for name, weights in (
            ("approachWeights", self.approach_weights),
            ("beat1RepeatWeights", self.beat1_repeat_weights),
        ):
            if not weights:
                raise ValueError(f"walking.{name} must be non-empty (PT6)")
            for key, weight in weights.items():
                if weight < 1:
                    raise ValueError(
                        f"walking.{name}[{key!r}] weight ({weight}) must be >= 1 (PT6)"
                    )
        return self


class VoicingConfig(PackModel):
    """§5.4 comping/pads `voicing:` block — per-rung candidate voicing classes.

    PT7: `classes` covers rungs 1–4, each a non-empty ordered list of class
    names from `VOICING_CLASSES`."""

    classes: dict[int, tuple[str, ...]]

    @model_validator(mode="after")
    def _check(self) -> "VoicingConfig":
        if set(self.classes) != {1, 2, 3, 4}:
            raise ValueError(
                f"voicing.classes must cover rungs 1-4, got "
                f"{sorted(self.classes)} (PT7)"
            )
        for rung, names in self.classes.items():
            if not names:
                raise ValueError(
                    f"voicing.classes[{rung}] must be a non-empty list (PT7)"
                )
            unknown = [name for name in names if name not in VOICING_CLASSES]
            if unknown:
                raise ValueError(
                    f"voicing.classes[{rung}] has unknown class name(s) "
                    f"{unknown}; must be in {VOICING_CLASSES} (PT7)"
                )
        return self


class DrumsBank(PackModel):
    """§5.2 `drums.yaml` — envelope list carrying the pack-level `layeringOrder`
    (§5.1). `layeringOrder` is validated (presence + permutation) at loader
    level (PT10) since it is a pack-wide fact."""

    layering_order: tuple[Role, ...] | None = None
    patterns: list[PatternEnvelope] = Field(default_factory=list)


class BassBank(PackModel):
    """§5.3 `bass.yaml` — top-level `mode` + optional `walking:` block. The
    `mode`/`walking` cross-check and mode-presence (PT6) are loader-level.

    `retarget` is the §7 bank-level default the loader injects into every entry
    that omits its own (entries may override); it is not consumed here."""

    mode: Literal["patterns", "walking"] | None = None
    walking: WalkingConfig | None = None
    retarget: Retarget | None = None
    patterns: list[PatternEnvelope] = Field(default_factory=list)


class VoicedBank(PackModel):
    """§5.4 `comping.yaml` / `pads.yaml` — a `voicing:` block plus the envelope
    list. Voicing presence (PT7) is loader-level (needs the Phase-5 gate).

    `retarget` is the §7 bank-level default the loader injects into every entry
    that omits its own (entries may override); it is not consumed here."""

    voicing: VoicingConfig | None = None
    retarget: Retarget | None = None
    patterns: list[PatternEnvelope] = Field(default_factory=list)


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

        # Rule 8: swingRatio, when set, is the final long:short ratio consumed
        # by SwingSpec (ir.py, ge=0.5 le=0.75). Bound it here so an out-of-range
        # pack fails at load with a PackLoadError instead of crashing later as a
        # raw pydantic error inside interpret().
        if self.swing_ratio is not None and not (0.5 <= self.swing_ratio <= 0.75):
            raise ValueError(
                f"swingRatio ({self.swing_ratio}) must be within [0.5, 0.75]"
            )

        return self


# --- PHASE_3 §5.1 `forms.yaml` -----------------------------------------------


class SectionDef(PackModel):
    """§5.1 `sections.<type>` entry: either a full bar/phrase/harmonyTag def,
    or an `inherit` reference sharing another type's resolved def (jazz's
    `solo: {inherit: head}`, F2)."""

    inherit: str | None = None
    bars: tuple[tuple[int, int], ...] | None = None
    phrases: dict[int, tuple[str, ...]] | None = None
    harmony_tag: dict[int, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_single_option_shorthand(cls, data: Any) -> Any:
        """§5.1: `phrases`/`harmonyTag` may be authored as a bare scalar (a
        plain label list / a plain tag string) when `bars` declares exactly
        one option; normalize to the per-option-keyed dict form other rules
        (F3) expect. Neither reference pack uses the shorthand, but the
        schema text permits it, so both forms must load."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        bars_raw = data.get("bars")
        single_n: int | None = None
        if isinstance(bars_raw, list) and len(bars_raw) == 1:
            option = bars_raw[0]
            if isinstance(option, list | tuple) and len(option) == 2:
                single_n = option[0]

        if single_n is not None:
            phrases_raw = data.get("phrases")
            if isinstance(phrases_raw, list):
                data["phrases"] = {single_n: phrases_raw}
            for key in ("harmonyTag", "harmony_tag"):
                tag_raw = data.get(key)
                if isinstance(tag_raw, str):
                    data[key] = {single_n: tag_raw}
        return data

    @model_validator(mode="after")
    def _check_shape(self) -> "SectionDef":
        if self.inherit is not None:
            if (
                self.bars is not None
                or self.phrases is not None
                or self.harmony_tag is not None
            ):
                raise ValueError(
                    "sections entry with 'inherit' must not declare bars/"
                    "phrases/harmonyTag (F2)"
                )
            return self

        if not self.bars:
            raise ValueError("sections entry must declare 'bars' (or 'inherit') (F1)")
        for n, weight in self.bars:
            if n < 4 or n % 4 != 0:
                raise ValueError(
                    f"sections bar option {n} must be a multiple of 4 and >= 4 (F1)"
                )
            if weight < 1:
                raise ValueError(
                    f"sections bar option weight {weight} must be >= 1 (F1)"
                )

        bar_ns = {n for n, _ in self.bars}

        if self.phrases is None or set(self.phrases) != bar_ns:
            raise ValueError(
                f"phrases must have exactly one entry per bar option "
                f"{sorted(bar_ns)} (F3)"
            )
        for n, labels in self.phrases.items():
            if not labels or n % len(labels) != 0 or n // len(labels) < 4:
                raise ValueError(
                    f"phrases[{n}]: {len(labels)} label(s) must divide {n} "
                    f"bars with an integer quotient >= 4 (F3)"
                )

        if self.harmony_tag is None or set(self.harmony_tag) != bar_ns:
            raise ValueError(
                f"harmonyTag must have exactly one entry per bar option "
                f"{sorted(bar_ns)} (F3)"
            )

        return self

    def smallest_bars(self) -> int:
        assert self.bars is not None
        return min(n for n, _ in self.bars)


class TemplateEligibility(PackModel):
    """§5.1 template `eligibility` gate — v1: an inclusive `arousal` band."""

    arousal: tuple[float, float]

    @model_validator(mode="after")
    def _check_band_order(self) -> "TemplateEligibility":
        lo, hi = self.arousal
        if lo > hi:
            raise ValueError(
                f"eligibility.arousal band must satisfy lo <= hi, got {(lo, hi)}"
            )
        return self


class TemplateSlot(PackModel):
    """§5.1 a spine slot: a section occurrence, optionally gated/overridden."""

    section: str
    optional: tuple[int, int] | None = None
    energy: float | None = Field(default=None, ge=0, le=1)
    variant: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_optional_weights(self) -> "TemplateSlot":
        if self.optional is not None:
            inc, exc = self.optional
            if inc < 1 or exc < 1:
                raise ValueError(
                    f"slot optional weights must both be >= 1 (F6): {self.optional}"
                )
        return self


class RepeatBlockBody(PackModel):
    """§5.1 `repeat` block body: an arithmetic count range + inner slots."""

    count: tuple[int, int | None]
    slots: tuple[TemplateSlot, ...]

    @model_validator(mode="after")
    def _check(self) -> "RepeatBlockBody":
        min_count, max_count = self.count
        if min_count < 1:
            raise ValueError(f"repeat count.min ({min_count}) must be >= 1 (F4)")
        if max_count is not None and max_count < min_count:
            raise ValueError(
                f"repeat count.max ({max_count}) must be >= count.min "
                f"({min_count}) or null (F4)"
            )
        if not self.slots:
            raise ValueError("repeat block 'slots' must be non-empty (F4)")
        return self


class RepeatBlock(PackModel):
    """§5.1 a spine element that is a repeat block (the other half of the
    slot/repeat-block spine-element union)."""

    repeat: RepeatBlockBody


class FormEnding(PackModel):
    """§5.1 `ending` — same shape as `schema.ir.SectionEnding`, mirrored here
    since pack models and IR models are deliberately separate hierarchies."""

    tag_bars: Literal[0, 4, 8]
    close: Literal["ritard", "cold", "fade"]


class DegradeOp(PackModel):
    """§5.1 one `degrade` ladder rung: exactly one of drop/shrink/
    dropFromRepeat, naming the type it acts on."""

    drop: str | None = None
    shrink: str | None = None
    drop_from_repeat: str | None = None

    @model_validator(mode="after")
    def _check_single_op(self) -> "DegradeOp":
        present = [v for v in (self.drop, self.shrink, self.drop_from_repeat) if v]
        if len(present) != 1:
            raise ValueError(
                "degrade op must specify exactly one of drop/shrink/dropFromRepeat"
            )
        return self

    @property
    def target_type(self) -> str:
        value = self.drop or self.shrink or self.drop_from_repeat
        assert value is not None
        return value


class Fallback(PackModel):
    """§5.1 `fallback` — the minimal form of last resort."""

    section: str
    bars: int

    @model_validator(mode="after")
    def _check_bars(self) -> "Fallback":
        if self.bars < 4 or self.bars % 4 != 0:
            raise ValueError(
                f"fallback.bars ({self.bars}) must be a multiple of 4 and >= 4 (F9)"
            )
        return self


class FormTemplate(PackModel):
    """§5.1 a weighted, eligibility-gated form spine."""

    id: str
    weight: int = Field(ge=1)
    eligibility: TemplateEligibility | None = None
    spine: tuple[TemplateSlot | RepeatBlock, ...] = Field(min_length=1)
    ending: FormEnding
    degrade: tuple[DegradeOp, ...] = Field(default_factory=tuple)
    fallback: Fallback

    @model_validator(mode="after")
    def _check_single_repeat_block(self) -> "FormTemplate":
        repeat_blocks = [e for e in self.spine if isinstance(e, RepeatBlock)]
        if len(repeat_blocks) > 1:
            raise ValueError(
                f"template {self.id!r}: at most one repeat block allowed per "
                f"template (F4)"
            )
        return self

    def flattened_spine_slots(self) -> list[tuple[str, bool]]:
        """§7.1 step-3 walk order: repeat-block inner slots resolve at the
        block's position, once — the order F5/F8/F9 cross-checks key off.
        Pairs each type with whether its slot is `optional` (a `RepeatBlock`
        itself is never optional, only the slots inside it may be), so F8's
        ending-candidate walk can tell an excludable trailing slot from one
        that always survives fitting."""
        flat: list[tuple[str, bool]] = []
        for element in self.spine:
            if isinstance(element, RepeatBlock):
                flat.extend(
                    (slot.section, slot.optional is not None)
                    for slot in element.repeat.slots
                )
            else:
                flat.append((element.section, element.optional is not None))
        return flat

    def flattened_spine_types(self) -> list[str]:
        """§7.1 step-3 walk order: repeat-block inner slots resolve at the
        block's position, once — the order F5/F9 cross-checks key off."""
        return [type_name for type_name, _optional in self.flattened_spine_slots()]

    def repeat_block_types(self) -> set[str]:
        """Types declared inside this template's (at most one, F4) repeat
        block — the scope `dropFromRepeat` degrade ops must reference (F9)."""
        for element in self.spine:
            if isinstance(element, RepeatBlock):
                return {slot.section for slot in element.repeat.slots}
        return set()

    def ending_candidate_types(self) -> set[str]:
        """§7.1/§8 F8 — every section type that could survive fitting as the
        form's FINAL section, hence bounds `ending.tagBars`: walking the
        flattened spine from the end, every trailing `optional` slot (it may
        be excluded) plus the first non-optional slot reached (always
        present, since it can't be excluded and nothing after it survives to
        replace it) — union every type a top-level `drop` degrade op could
        remove (a `drop` anywhere in the spine can expose a new tail; this
        errs toward over-inclusion, which only makes F8 stricter, never
        under-strict)."""
        candidates: set[str] = set()
        for type_name, optional in reversed(self.flattened_spine_slots()):
            candidates.add(type_name)
            if not optional:
                break
        candidates.update(op.drop for op in self.degrade if op.drop is not None)
        return candidates


class FormsConfig(PackModel):
    """§5.1 `forms.yaml` — pack energy envelope + per-type section defaults +
    weighted templates."""

    energy_range: tuple[float, float]
    sections: dict[str, SectionDef]
    templates: tuple[FormTemplate, ...]

    @model_validator(mode="after")
    def _check_rules(self) -> "FormsConfig":
        lo, hi = self.energy_range
        if not (0 <= lo <= hi <= 1):
            raise ValueError(
                f"energyRange must satisfy 0 <= lo <= hi <= 1, got {(lo, hi)} (F10)"
            )

        # F1: sections non-empty; every key in the closed vocabulary.
        if not self.sections:
            raise ValueError("sections must be non-empty (F1)")
        unknown_types = set(self.sections) - set(SECTION_TYPES)
        if unknown_types:
            raise ValueError(
                f"sections contains type(s) outside the closed vocabulary "
                f"{SECTION_TYPES}: {sorted(unknown_types)} (F1)"
            )

        # F2: inherit target exists and does not itself inherit.
        for type_name, section_def in self.sections.items():
            if section_def.inherit is None:
                continue
            target = section_def.inherit
            if target not in self.sections:
                raise ValueError(
                    f"sections[{type_name!r}].inherit target {target!r} is not "
                    f"declared in sections (F2)"
                )
            if self.sections[target].inherit is not None:
                raise ValueError(
                    f"sections[{type_name!r}].inherit target {target!r} itself "
                    f"inherits; only a single inherit level is allowed (F2)"
                )

        # F4: templates non-empty; unique ids.
        if not self.templates:
            raise ValueError("templates must be non-empty (F4)")
        ids = [template.id for template in self.templates]
        if len(set(ids)) != len(ids):
            dupes = sorted({tid for tid in ids if ids.count(tid) > 1})
            raise ValueError(f"template ids must be unique; duplicate(s): {dupes} (F4)")

        # F13: at least one template with no arousal gate.
        if all(template.eligibility is not None for template in self.templates):
            raise ValueError(
                "at least one template must have no arousal gate, so every "
                "supported mood reaches a template (F13)"
            )

        for template in self.templates:
            self._check_template(template)

        return self

    def _resolved_section(self, type_name: str) -> SectionDef:
        section_def = self.sections[type_name]
        if section_def.inherit is not None:
            return self.sections[section_def.inherit]
        return section_def

    def _check_template(self, template: FormTemplate) -> None:
        flat = template.flattened_spine_types()
        spine_type_set = set(flat)

        # F4: every slot's section is declared in `sections`.
        for type_name in spine_type_set:
            if type_name not in self.sections:
                raise ValueError(
                    f"template {template.id!r}: spine section {type_name!r} is "
                    f"not declared in sections (F4)"
                )

        # F9: degrade ops + fallback reference types present in the spine.
        # `dropFromRepeat` is narrower: there is nothing to drop from the
        # repeat block unless the type actually occurs inside it (Fix 2).
        repeat_types = template.repeat_block_types()
        for op in template.degrade:
            if op.drop_from_repeat is not None:
                if op.drop_from_repeat not in repeat_types:
                    raise ValueError(
                        f"template {template.id!r}: dropFromRepeat op "
                        f"references type {op.drop_from_repeat!r} not present "
                        f"in the template's repeat block (F9)"
                    )
            elif op.target_type not in spine_type_set:
                raise ValueError(
                    f"template {template.id!r}: degrade op references type "
                    f"{op.target_type!r} not present in the spine (F9)"
                )
        if template.fallback.section not in spine_type_set:
            raise ValueError(
                f"template {template.id!r}: fallback.section "
                f"{template.fallback.section!r} is not used in the spine (F9)"
            )

        # F8: ending.tagBars must not exceed the smallest bar option of any
        # type that could survive fitting as the form's final section —
        # trailing optional slots, the first non-optional slot from the end,
        # every top-level `drop` degrade-op target, and the fallback type
        # (Fix 1; see FormTemplate.ending_candidate_types).
        ending_candidates = template.ending_candidate_types() | {
            template.fallback.section
        }
        for type_name in ending_candidates:
            smallest = self._resolved_section(type_name).smallest_bars()
            if template.ending.tag_bars > smallest:
                raise ValueError(
                    f"template {template.id!r}: ending.tagBars "
                    f"({template.ending.tag_bars}) exceeds the smallest bar "
                    f"option ({smallest}) of ending-candidate type "
                    f"{type_name!r} (F8)"
                )

        # F5: an inheriting type's first spine occurrence must come after its
        # inherit target's first spine occurrence (resolution order).
        for type_name, section_def in self.sections.items():
            if section_def.inherit is None or type_name not in flat:
                continue
            target = section_def.inherit
            first_self = flat.index(type_name)
            if target not in flat:
                raise ValueError(
                    f"template {template.id!r}: spine uses {type_name!r} "
                    f"(inherits {target!r}) but {target!r} never appears in "
                    f"the spine (F5)"
                )
            first_target = flat.index(target)
            if first_target > first_self:
                raise ValueError(
                    f"template {template.id!r}: {type_name!r} appears before "
                    f"its inherit target {target!r} in spine order (F5)"
                )


# --- PHASE_4 §4 `progressions.yaml` ------------------------------------------

# A bar is a list of 1/2/4 authored chord tokens, or the single-token hold
# `("~",)`. YAML authors holds as the bare `~`, which `yaml.safe_load` yields
# as `None`; the entry before-validators normalize `None` back to `"~"` so the
# rest of the code sees one hold sentinel.
Bar = tuple[str, ...]

_HOLD = "~"


class _NeutralKey:
    """A fixed, key-independent `KeyLike` used only to validate token GRAMMAR
    and read a token's degree/function at load time (§3.1/§3.2). Degrees are
    major-scale-relative and mode-independent, so any major-class mode over
    `tonic_pc 0` parses every legal token identically; spelling is discarded."""

    tonic_pc: int = 0
    mode: str = "major"


_NEUTRAL_KEY = _NeutralKey()


def _normalize_holds(value: Any) -> Any:
    """Recursively turn YAML `None` (authored `~`) into the `"~"` hold sentinel
    inside a bar-list / phrases structure, leaving everything else untouched."""
    if value is None:
        return _HOLD
    if isinstance(value, list):
        return [_normalize_holds(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_holds(item) for key, item in value.items()}
    return value


def _final_sounding_token(bars: tuple[Bar, ...]) -> str:
    """The last non-hold token across `bars` — the entry's cadential chord.
    Every legal bar list starts with a real chord (holds are barred from a
    phrase's first bar and from turnarounds/finals), so this always finds one."""
    for bar in reversed(bars):
        for token in reversed(bar):
            if token != _HOLD:
                return token
    raise ValueError("bar list has no sounding chord")


def _is_degree1_rooted(token: str) -> bool:
    """True iff `token`'s root is scale degree 1 with no accidental (§3.2).

    Resolved against the neutral key, degree-1-no-accidental is the unique
    token whose `root_pc` equals the tonic AND whose function is `T` (the other
    T-degrees b3/3/6 root elsewhere; an enharmonic `#VII` also lands on the
    tonic pc but is function `O`, so the conjunction pins degree 1 exactly)."""
    from trackgen.theory import chord_function, resolve_token

    spec = resolve_token(token, _NEUTRAL_KEY)
    return spec.root_pc == _NEUTRAL_KEY.tonic_pc and chord_function(token) == "T"


def _relaunches_as_dominant(token: str) -> bool:
    """True iff `token` is a dominant-functioning relaunch chord for P8.

    The §3.2 table's `D` degrees (V, bVII, VII), OR a tritone-substitute
    dominant (a bII with a dominant-seventh quality — the SubV that resolves to
    I exactly as V does). See the CAVEAT documented in the loader/report:
    §9.2's `tritone_turn` ends on `bII7`, which the §3.2 table labels `S`, yet
    §14 requires the reference pack to load clean, so P8 admits the SubV."""
    from trackgen.theory import chord_function, resolve_token

    if chord_function(token) == "D":
        return True
    spec = resolve_token(token, _NEUTRAL_KEY)
    return spec.root_pc == 1 and spec.quality in ("dom7", "dom7sus4")


class _ProgressionEntry(PackModel):
    """Shared selection metadata for pool/turnaround/final entries (§4.1)."""

    id: str
    weight: int = Field(ge=1)  # P2
    modes: tuple[str, ...] = Field(min_length=1)  # P2 (non-empty)
    valence: tuple[float, float] | None = None
    dissonance: tuple[float, float] | None = None

    @model_validator(mode="after")
    def _check_modes_and_bands(self) -> "_ProgressionEntry":
        # Lazy import (mirrors InterpreterConfig): `interpreter.moods` imports
        # PackModel from this module, so a top-level import would be circular.
        from trackgen.interpreter.moods import MODE_LADDER

        # P2: modes ⊆ the engine mode vocabulary.
        unknown = set(self.modes) - set(MODE_LADDER)
        if unknown:
            raise ValueError(
                f"entry {self.id!r}: modes contain unknown mode(s) {sorted(unknown)}; "
                f"must be ⊆ {MODE_LADDER} (P2)"
            )

        # P3: band ranges + ordering.
        for name, band, lo_bound, hi_bound in (
            ("valence", self.valence, -1.0, 1.0),
            ("dissonance", self.dissonance, 0.0, 1.0),
        ):
            if band is None:
                continue
            lo, hi = band
            if not (lo_bound <= lo <= hi_bound and lo_bound <= hi <= hi_bound):
                raise ValueError(
                    f"entry {self.id!r}: {name} band {band} must lie within "
                    f"[{lo_bound}, {hi_bound}] (P3)"
                )
            if lo > hi:
                raise ValueError(
                    f"entry {self.id!r}: {name} band {band} must satisfy lo <= hi (P3)"
                )
        return self


class PoolEntry(_ProgressionEntry):
    """§4.1 a per-`harmonyTag` pool entry: one progression per phrase LABEL."""

    phrases: dict[str, tuple[Bar, ...]] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and "phrases" in data:
            data = dict(data)
            data["phrases"] = _normalize_holds(data["phrases"])
        return data

    @model_validator(mode="after")
    def _check_bars(self) -> "PoolEntry":
        from trackgen.theory import TokenError, resolve_token

        for label, bars in self.phrases.items():
            if not bars:
                raise ValueError(
                    f"entry {self.id!r} phrase {label!r}: must have >= 1 bar (P5)"
                )
            for bar_index, bar in enumerate(bars):
                loc = f"entry {self.id!r} phrase {label!r} bar {bar_index}"
                if tuple(bar) == (_HOLD,):
                    # P5: `~` never in a phrase's FIRST bar.
                    if bar_index == 0:
                        raise ValueError(
                            f"{loc}: '~' must not be a phrase's first bar (P5)"
                        )
                    continue
                if _HOLD in bar:
                    raise ValueError(
                        f"{loc}: '~' may only appear as the sole token of a bar (P5)"
                    )
                if len(bar) not in (1, 2, 4):
                    raise ValueError(
                        f"{loc}: a bar must have 1, 2, or 4 tokens, got {len(bar)} (P5)"
                    )
                for token in bar:
                    try:
                        resolve_token(token, _NEUTRAL_KEY)
                    except TokenError as exc:
                        raise ValueError(
                            f"{loc}: token {token!r} does not parse (P5): {exc}"
                        ) from exc
        return self

    @property
    def density(self) -> float:
        """§4.2 `density = totalTokens / totalBars` across all phrase labels;
        holds (`~`) are excluded from the token count."""
        total_tokens = 0
        total_bars = 0
        for bars in self.phrases.values():
            for bar in bars:
                total_bars += 1
                total_tokens += sum(1 for token in bar if token != _HOLD)
        return total_tokens / total_bars

    def final_chord_token(self) -> str:
        """The cadential chord token — the last sounding token of the
        last-declared phrase label (unambiguous for the single-label pools the
        P7 cadence classes constrain in v1)."""
        last_label = next(reversed(self.phrases))
        return _final_sounding_token(self.phrases[last_label])


class _BarsEntry(_ProgressionEntry):
    """Shared shape for turnaround/final entries: a 1–2 bar chord list (§4.1).
    Holds are never legal here (P5); subclasses add the final-chord check."""

    bars: tuple[Bar, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and "bars" in data:
            data = dict(data)
            data["bars"] = _normalize_holds(data["bars"])
        return data

    @model_validator(mode="after")
    def _check_bars(self) -> "_BarsEntry":
        from trackgen.theory import TokenError, resolve_token

        for bar_index, bar in enumerate(self.bars):
            loc = f"entry {self.id!r} bar {bar_index}"
            if _HOLD in bar:
                raise ValueError(
                    f"{loc}: holds ('~') are not allowed in turnarounds/finals (P5)"
                )
            if len(bar) not in (1, 2, 4):
                raise ValueError(
                    f"{loc}: a bar must have 1, 2, or 4 tokens, got {len(bar)} (P5)"
                )
            for token in bar:
                try:
                    resolve_token(token, _NEUTRAL_KEY)
                except TokenError as exc:
                    raise ValueError(
                        f"{loc}: token {token!r} does not parse (P5): {exc}"
                    ) from exc
        return self


class TurnaroundEntry(_BarsEntry):
    """§4.1 a loop-back relaunch bar list (1–2 bars); final chord D-function."""

    @model_validator(mode="after")
    def _check_cadence(self) -> "TurnaroundEntry":
        final = _final_sounding_token(self.bars)
        if not _relaunches_as_dominant(final):
            raise ValueError(
                f"turnaround {self.id!r}: final chord {final!r} must be "
                f"dominant-functioning (P8)"
            )
        return self


class FinalEntry(_BarsEntry):
    """§4.1 a song-close bar list (1–2 bars); final chord rooted on degree 1."""

    @model_validator(mode="after")
    def _check_cadence(self) -> "FinalEntry":
        final = _final_sounding_token(self.bars)
        if not _is_degree1_rooted(final):
            raise ValueError(
                f"final {self.id!r}: final chord {final!r} must be rooted on "
                f"degree 1 (P9)"
            )
        return self


class ProgressionsConfig(PackModel):
    """§4.1 `progressions.yaml` — pools + turnarounds + (required) finals."""

    pools: dict[str, tuple[PoolEntry, ...]]
    turnarounds: tuple[TurnaroundEntry, ...] = ()
    finals: tuple[FinalEntry, ...] = Field(min_length=1)  # P9 non-empty

    @model_validator(mode="after")
    def _check_unique_ids(self) -> "ProgressionsConfig":
        # P2: ids unique within each pool, within turnarounds, within finals.
        groups: list[tuple[str, tuple[_ProgressionEntry, ...]]] = [
            *((f"pool {tag!r}", entries) for tag, entries in self.pools.items()),
            ("turnarounds", self.turnarounds),
            ("finals", self.finals),
        ]
        for label, entries in groups:
            ids = [entry.id for entry in entries]
            if len(set(ids)) != len(ids):
                dupes = sorted({i for i in ids if ids.count(i) > 1})
                raise ValueError(f"{label}: duplicate entry id(s) {dupes} (P2)")
        return self


# --- PHASE_5 §8.4 provisional `timbres.yaml` (Phase 7 owns the real schema) ---


class TrackTimbre(PackModel):
    """§8.4 one track's stub timbre: an `InstrumentPatch` plus an optional drum
    trigger `midi`. Pitched roles and NoiseSynth drums (snare) carry no `midi`
    (V5: the note supplies its own pitch, or none for NoiseSynth)."""

    midi: int | None = None
    instrument: InstrumentPatch


# A drum kit maps a drum-track id (kick/snare/hats/ride/tom_*/perc) → its timbre.
DrumKit = dict[str, TrackTimbre]


class TimbresConfig(PackModel):
    """§8.4 `timbres.yaml` — per role, each flavor id → a patch. Drums map a
    flavor id to a whole kit (per-drum-track timbre); pitched roles map a flavor
    id to a single timbre. Provisional stub: all flavors of a role reuse the
    same recipe in v1 (flavor differentiation is Phase 7)."""

    drums: dict[str, DrumKit]
    bass: dict[str, TrackTimbre]
    comping: dict[str, TrackTimbre]
    pads: dict[str, TrackTimbre]


# --- PHASE_6 §4.1 `transitions.yaml` -----------------------------------------


class PhraseFill(PackModel):
    """§4.1 `phraseFill` — interior phrase-boundary include/exclude odds."""

    odds: tuple[int, int]

    @model_validator(mode="after")
    def _check(self) -> "PhraseFill":
        # TR1: two ints >= 1 (exactly-two arity enforced by the tuple type).
        if any(weight < 1 for weight in self.odds):
            raise ValueError(
                f"phraseFill.odds must be two ints >= 1, got {list(self.odds)} (TR1)"
            )
        return self


class Stop(PackModel):
    """§4.1 `stop` — the shipped stop device's enable flag + draw odds."""

    enabled: bool
    odds: tuple[int, int] | None = None

    @model_validator(mode="after")
    def _check(self) -> "Stop":
        # TR2: odds present iff enabled; when present, two ints >= 1.
        if self.enabled:
            if self.odds is None:
                raise ValueError("stop.odds is required when stop.enabled (TR2)")
            if any(weight < 1 for weight in self.odds):
                raise ValueError(
                    f"stop.odds must be two ints >= 1, got {list(self.odds)} (TR2)"
                )
        elif self.odds is not None:
            raise ValueError(
                "stop.odds must be absent when stop.enabled is false (TR2)"
            )
        return self


class Crash(PackModel):
    """§4.1 `crash` — the entry-crash velocity range mapped over section energy."""

    velocity: tuple[float, float]

    @model_validator(mode="after")
    def _check(self) -> "Crash":
        # TR1: floats in [0, 1] with lo <= hi.
        lo, hi = self.velocity
        if not (0.0 <= lo <= hi <= 1.0):
            raise ValueError(
                f"crash.velocity must be floats with 0 <= lo <= hi <= 1, "
                f"got {list(self.velocity)} (TR1)"
            )
        return self


class Mutation(PackModel):
    """§4.1 `mutation` — per-role operator tables (authored order = draw order).

    Only `drums` and `comping` roles carry operators in v1 (§3.7); the closed
    field set plus `extra="forbid"` enforces TR3's "keys ⊆ {drums, comping}".
    Each present table must be non-empty, include `none`, weight every op with
    an int >= 1, and name only ops from that role's §3.7 vocabulary. A table
    absent means that role never mutates; a single-entry (`none` only) table is
    legal — the role draws nothing (§3.7)."""

    drums: dict[str, int] | None = None
    comping: dict[str, int] | None = None

    @model_validator(mode="after")
    def _check(self) -> "Mutation":
        for role, table, ops in (
            ("drums", self.drums, DRUM_MUTATION_OPS),
            ("comping", self.comping, COMPING_MUTATION_OPS),
        ):
            if table is None:
                continue
            if not table:
                raise ValueError(f"mutation.{role} table must be non-empty (TR3)")
            if "none" not in table:
                raise ValueError(
                    f"mutation.{role} table must include a 'none' weight (TR3)"
                )
            allowed = {"none", *ops}
            for name, weight in table.items():
                if name not in allowed:
                    raise ValueError(
                        f"mutation.{role} op {name!r} is not in the {role} "
                        f"vocabulary {sorted(allowed)} (TR3)"
                    )
                if weight < 1:
                    raise ValueError(
                        f"mutation.{role}[{name!r}] weight ({weight}) must be "
                        f">= 1 (TR3)"
                    )
        return self


class TransitionsSpec(PackModel):
    """§4.1 `transitions.yaml` — placement odds, stop gating, crash range, and
    per-role mutation tables. Strict (`extra="forbid"`) so TR4 rejects any
    stray key. Cross-file PT12/TR5 (an ungated drum `fill` exists) and the
    fill-window checks TR6/TR7 live in the loader, which needs the drum bank."""

    phrase_fill: PhraseFill
    stop: Stop
    crash: Crash
    mutation: Mutation


class StylePack(PackModel):
    """A loaded, validated style pack: manifest + per-role pattern banks.

    PHASE_5 exposes the per-role bank data later chunks consume:

    - `patterns[role]` — the envelope list per role (unchanged accessor).
    - `layering_order` — the §5.1 role permutation (`None` for legacy packs
      without Phase-5 banks).
    - `bass_mode` / `walking` — §5.3 bass mode + walker parameters.
    - `voicing[role]` — §5.4 comping/pads `VoicingConfig` (rung → classes);
      only populated for roles that declare a `voicing:` block."""

    manifest: Manifest
    patterns: dict[str, list[PatternEnvelope]]
    layering_order: tuple[Role, ...] | None = None
    bass_mode: Literal["patterns", "walking"] | None = None
    walking: WalkingConfig | None = None
    voicing: dict[Role, VoicingConfig] = Field(default_factory=dict)
    interpreter: InterpreterConfig | None = None
    forms: FormsConfig | None = None
    progressions: ProgressionsConfig | None = None
    timbres: TimbresConfig | None = None
    transitions: TransitionsSpec | None = None
    # PHASE_6 §3.3 — per-fill-id content windows `(start, end)` in ticks,
    # computed and cached at load (`None` field entry never appears; empty when
    # the drum bank has no fills). Stage 6 (T2) reads this by pattern id.
    fill_windows: dict[str, tuple[int, int]] = Field(default_factory=dict)
