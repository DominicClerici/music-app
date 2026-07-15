"""Style-pack structure (PHASE_1 §6).

Frozen pydantic v2 models for the pack manifest (§6.1), the shared pattern
envelope (§6.2), and the event primitives (§6.3). Bank-specific fields owned
by later phases (progressions/forms/timbres/interpreter schemas, and any
role-specific envelope extensions) are deliberately NOT modeled here.

`degree` is restricted to the §6.3 v1 core vocabulary only: `root, third,
fifth, seventh, guide3, guide7, tension, approach`. Phase 5's later
extensions (`sixth`, `chord`, `push`, `minDensity`) are out of scope.
"""

from typing import Any, Literal

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


class StylePack(PackModel):
    """A loaded, validated style pack: manifest + per-role pattern banks."""

    manifest: Manifest
    patterns: dict[str, list[PatternEnvelope]]
    interpreter: InterpreterConfig | None = None
    forms: FormsConfig | None = None
