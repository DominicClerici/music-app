"""The Form generator — pipeline stage 2 (PHASE_3 §7).

`form(plan, forms) -> SongForm` implements the §7.1 normative algorithm
exactly: budget from the plan (D-S8), weighted template selection (§5.2),
feasibility-constrained slot resolution (D-S7), arithmetic repeat counts and
the degradation ladder (§7.3), a minimal fallback, and assembly with per-§3.3
labels and §6 energies.

RNG discipline (§7.2, D-S2/D-S11/D-S13): the single `form` stream is built
here via `stream_rng` (the `random`-module boundary stays in `seeds.py`);
draws happen only through `weighted_choice`, only when >= 2 feasible/eligible
candidates exist, in the fixed order template -> spine order (inclusion draw
before bar draw per slot). Ladder ops and repeat counts are arithmetic, never
drawn. Candidate lists are always iterated in authored order.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from trackgen.form.energy import section_energy
from trackgen.packs.models import (
    DegradeOp,
    FormsConfig,
    FormTemplate,
    RepeatBlock,
    SectionDef,
    TemplateSlot,
)
from trackgen.schema.ir import (
    FormSection,
    GenerationPlan,
    SectionEnding,
    SectionPhrase,
    SongForm,
)
from trackgen.seeds import stream_rng, weighted_choice

if TYPE_CHECKING:
    from trackgen.pipeline.explain import ExplainCollector

# A resolved section to emit: (type, length_bars, energy override, variant).
_RawSection = tuple[str, int, float | None, str | None]


def _slot_active(
    slot: TemplateSlot,
    slot_uid: int,
    dropped: set[int],
    optional_decision: dict[int, bool],
) -> bool:
    """A spine slot contributes bars iff it was not ladder-dropped and (when
    optional) was drawn in (§7.1 steps 3/5)."""
    if slot_uid in dropped:
        return False
    if slot.optional is not None and not optional_decision.get(slot_uid, False):
        return False
    return True


def _fit_and_degrade(
    *,
    degrade: tuple[DegradeOp, ...],
    top_level: list[tuple[TemplateSlot, int]],
    repeat_inner: list[tuple[TemplateSlot, int]],
    resolved_bars: dict[str, int],
    optional_decision: dict[int, bool],
    dropped_top: set[int],
    dropped_repeat: set[int],
    count_min: int,
    count_max: int | None,
    has_repeat: bool,
    bar_budget: int,
    rk: Callable[[str], str],
    smallest: Callable[[str], int],
) -> tuple[int, int]:
    """PHASE_3 §7.1 steps 4-5: the arithmetic repeat count + the degrade ladder.

    Mutates `resolved_bars` / `dropped_top` / `dropped_repeat` in place and
    returns `(count, total)`.

    The step-5 ladder (`while total > bar_budget`) is retained **defensive,
    unreachable** code: for any template *selected* by `form()`, the §5.2
    eligibility gate and the §7.1 step-3 feasibility filter already guarantee
    `total <= bar_budget`, so the loop body never runs through the public API
    (proof in CAVEATS C-02). It is kept for robustness against a future pack
    rule that could select an over-budget template, and its drop / shrink /
    dropFromRepeat semantics are locked by a direct white-box unit test
    (`tests/test_form.py`)."""

    def recompute() -> tuple[int, int]:
        fixed = sum(
            resolved_bars[rk(slot.section)]
            for slot, slot_uid in top_level
            if _slot_active(slot, slot_uid, dropped_top, optional_decision)
        )
        if not has_repeat:
            return 0, fixed
        block = sum(
            resolved_bars[rk(slot.section)]
            for slot, slot_uid in repeat_inner
            if _slot_active(slot, slot_uid, dropped_repeat, optional_decision)
        )
        if block == 0:
            return count_min, fixed
        raw = (bar_budget - fixed) // block
        count = max(count_min, raw)
        if count_max is not None:
            count = min(count, count_max)
        return count, fixed + count * block

    count, total = recompute()
    ladder = iter(degrade)
    while total > bar_budget:
        op = next(ladder, None)
        if op is None:
            break
        if op.drop is not None:
            dropped_top.update(
                slot_uid for slot, slot_uid in top_level if slot.section == op.drop
            )
        elif op.shrink is not None:
            resolved_bars[rk(op.shrink)] = smallest(op.shrink)
        else:  # drop_from_repeat
            dropped_repeat.update(
                slot_uid
                for slot, slot_uid in repeat_inner
                if slot.section == op.drop_from_repeat
            )
        count, total = recompute()
    return count, total


def form(
    plan: GenerationPlan,
    forms: FormsConfig,
    *,
    explain: ExplainCollector | None = None,
) -> SongForm:
    """PHASE_3 §7.1 — resolve a `GenerationPlan` into a `SongForm`."""
    if not forms:
        raise ValueError("form() requires a non-null FormsConfig (forms.yaml)")

    rng = stream_rng(plan.seed.master, plan.seed.overrides, "form")
    arousal = plan.mood_vector.arousal
    energy_range = forms.energy_range

    # --- Step 1: budget (D-S8) ------------------------------------------------
    ts = plan.time_signature
    ticks_per_bar = ts.numerator * (480 * 4 // ts.denominator)
    bar_budget = plan.max_length_ticks // ticks_per_bar

    # --- resolved-section / inherit helpers (D9) ------------------------------
    def def_of(type_name: str) -> SectionDef:
        sd = forms.sections[type_name]
        return forms.sections[sd.inherit] if sd.inherit is not None else sd

    def rk(type_name: str) -> str:
        """Resolution key: the inherit target if any (jazz solo -> head), so an
        inherit-target type and its inheritors share ONE bar-count resolution."""
        sd = forms.sections[type_name]
        return sd.inherit if sd.inherit is not None else type_name

    def smallest(type_name: str) -> int:
        return def_of(type_name).smallest_bars()

    # --- Step 2: template eligibility & selection (§5.2) -----------------------
    def min_bars(template: FormTemplate) -> int:
        """§5.2 minBars: all optionals excluded, every type at its smallest bar
        option, the repeat block at count.min."""
        total = 0
        for element in template.spine:
            if isinstance(element, RepeatBlock):
                block = sum(
                    0 if slot.optional is not None else smallest(slot.section)
                    for slot in element.repeat.slots
                )
                total += element.repeat.count[0] * block
            elif element.optional is None:
                total += smallest(element.section)
        return total

    def eligible(template: FormTemplate) -> bool:
        if template.eligibility is not None:
            lo, hi = template.eligibility.arousal
            if not (lo <= arousal <= hi):
                return False
        return min_bars(template) <= bar_budget

    eligible_templates = [t for t in forms.templates if eligible(t)]

    if not eligible_templates:
        # Nothing fits: emit the fallback form directly from templates[0].
        return _fallback_form(
            forms.templates[0], bar_budget, arousal, energy_range, def_of
        )

    if len(eligible_templates) >= 2:
        template = weighted_choice(
            eligible_templates, [t.weight for t in eligible_templates], rng
        )
    else:
        template = eligible_templates[0]

    if explain is not None:
        explain.add_template(
            template.id,
            [t.id for t in eligible_templates],
            [t.weight for t in eligible_templates],
        )

    # --- flatten the spine for the resolution walk (D-S7) ---------------------
    # Each entry: (slot, uid, in_repeat). Repeat-block inner slots resolve ONCE
    # at the block's position (NOT per repetition); uids track per-slot optional
    # decisions and ladder drops.
    has_repeat = any(isinstance(e, RepeatBlock) for e in template.spine)
    count_min: int = 0
    count_max: int | None = None
    flat_walk: list[tuple[TemplateSlot, int, bool]] = []
    top_level: list[tuple[TemplateSlot, int]] = []
    repeat_inner: list[tuple[TemplateSlot, int]] = []
    uid = 0
    for element in template.spine:
        if isinstance(element, RepeatBlock):
            count_min, count_max = element.repeat.count
            for slot in element.repeat.slots:
                flat_walk.append((slot, uid, True))
                repeat_inner.append((slot, uid))
                uid += 1
        else:
            flat_walk.append((element, uid, False))
            top_level.append((element, uid))
            uid += 1

    resolved_bars: dict[str, int] = {}
    optional_decision: dict[int, bool] = {}

    def minimal_total(
        assume_include_uid: int | None = None,
        override: tuple[str, int] | None = None,
    ) -> int:
        """§7.1 step 3 minimalTotal: excluded/undecided optionals = 0, unresolved
        types at their smallest option, the repeat block at count.min. Recomputed
        at every feasibility check. `assume_include_uid` force-includes one
        optional slot; `override` pins one resolution key to a candidate value."""
        total = 0
        for slot, slot_uid, in_repeat in flat_walk:
            if slot.optional is not None:
                included = optional_decision.get(slot_uid)
                if slot_uid == assume_include_uid:
                    included = True
                if included is not True:
                    continue
            key = rk(slot.section)
            if override is not None and override[0] == key:
                bars = override[1]
            elif key in resolved_bars:
                bars = resolved_bars[key]
            else:
                bars = smallest(slot.section)
            total += bars * (count_min if in_repeat else 1)
        return total

    # --- Step 3: slot resolution (D-S7) ---------------------------------------
    for slot, slot_uid, _in_repeat in flat_walk:
        if slot.optional is not None:
            if minimal_total(assume_include_uid=slot_uid) <= bar_budget:
                inc_w, exc_w = slot.optional
                choice = weighted_choice(["include", "exclude"], [inc_w, exc_w], rng)
                optional_decision[slot_uid] = choice == "include"
            else:
                optional_decision[slot_uid] = False
            if not optional_decision[slot_uid]:
                continue
        key = rk(slot.section)
        if key in resolved_bars:
            continue
        options = def_of(slot.section).bars
        assert options is not None
        feasible = [
            (n, w) for n, w in options if minimal_total(override=(key, n)) <= bar_budget
        ]
        if len(feasible) >= 2:
            resolved_bars[key] = weighted_choice(
                [n for n, _ in feasible], [w for _, w in feasible], rng
            )
        elif len(feasible) == 1:
            resolved_bars[key] = feasible[0][0]
        else:
            resolved_bars[key] = min(n for n, _ in options)

    # --- Steps 4 & 5: repeat count + degradation ladder (arithmetic) ----------
    dropped_top: set[int] = set()
    dropped_repeat: set[int] = set()
    count, total = _fit_and_degrade(
        degrade=template.degrade,
        top_level=top_level,
        repeat_inner=repeat_inner,
        resolved_bars=resolved_bars,
        optional_decision=optional_decision,
        dropped_top=dropped_top,
        dropped_repeat=dropped_repeat,
        count_min=count_min,
        count_max=count_max,
        has_repeat=has_repeat,
        bar_budget=bar_budget,
        rk=rk,
        smallest=smallest,
    )

    # --- Step 6: fallback when the ladder cannot fit it -----------------------
    if total > bar_budget:
        return _fallback_form(template, bar_budget, arousal, energy_range, def_of)

    # --- Step 7: assemble -----------------------------------------------------
    raw_sections: list[_RawSection] = []
    for element in template.spine:
        if isinstance(element, RepeatBlock):
            block_slots = [
                (slot, slot_uid)
                for slot, slot_uid in repeat_inner
                if _slot_active(slot, slot_uid, dropped_repeat, optional_decision)
            ]
            for _ in range(count):
                for slot, _slot_uid in block_slots:
                    raw_sections.append(
                        (
                            slot.section,
                            resolved_bars[rk(slot.section)],
                            slot.energy,
                            slot.variant,
                        )
                    )
        else:
            top_uid = next(u for s, u in top_level if s is element)
            if _slot_active(element, top_uid, dropped_top, optional_decision):
                raw_sections.append(
                    (
                        element.section,
                        resolved_bars[rk(element.section)],
                        element.energy,
                        element.variant,
                    )
                )

    return _assemble(raw_sections, template, arousal, energy_range, def_of)


def section_label(type_name: str, index: int, total: int, variant: str | None) -> str:
    """PHASE_3 §3.3 / D-S10 — the display label for a section.

    `SongForm` stores no label field; the label is a pure derivation from
    `(type, index, total_of_type, variant)`, computed here as the single source
    of truth for `TrackDocument.sections[].label` (the 1:1 mapping PHASE_1 §4.2
    promises) and for the golden/property tests."""
    if type_name == "chorus":
        if index == total and total >= 2:
            return "Final Chorus"
        return "Chorus" if total == 1 else f"Chorus {index}"
    if type_name == "head":
        if index == 1:
            return "Head In"
        if index == total:
            return "Head Out"
        return f"Head {index}"
    if type_name == "solo":
        return "Solo Chorus" if total == 1 else f"Solo Chorus {index}"
    if type_name == "main":
        return f"Part {variant}" if variant else f"Part {index}"
    base = {"prechorus": "Pre-Chorus", "postchorus": "Post-Chorus"}.get(
        type_name, type_name.title()
    )
    return f"{base} {index}" if total > 1 else base


def _phrases(section_def: SectionDef, bars: int) -> list[SectionPhrase]:
    """§4.1 — phrase substructure for the resolved bar option; the fallback
    path may pass a non-authored length, for which uniform 4-bar phrases labeled
    "a" cover the section (Sigma phrase.bars == length, every phrase >= 4)."""
    if section_def.phrases is not None and bars in section_def.phrases:
        labels = section_def.phrases[bars]
        phrase_len = bars // len(labels)
        return [SectionPhrase(label=label, bars=phrase_len) for label in labels]
    return [SectionPhrase(label="a", bars=4) for _ in range(bars // 4)]


def _harmony_tag(section_def: SectionDef, bars: int) -> str:
    if section_def.harmony_tag is not None and bars in section_def.harmony_tag:
        return section_def.harmony_tag[bars]
    assert section_def.harmony_tag is not None
    return section_def.harmony_tag[section_def.smallest_bars()]


def _assemble(
    raw_sections: list[_RawSection],
    template: FormTemplate,
    arousal: float,
    energy_range: tuple[float, float],
    def_of: Callable[[str], SectionDef],
    ending_tag_bars: Literal[0, 4, 8] | None = None,
) -> SongForm:
    """§7.1 step 7 — number, label, and lay out the resolved sections.

    `ending_tag_bars`, when given, overrides `template.ending.tag_bars` for the
    final section's `ending` (used only by the fallback path, which may need a
    value smaller than the template's authored `tagBars` — see
    `_fallback_form`). The normal-assembly path always passes `None`: F8
    already guarantees the template's authored `tagBars` fits every type that
    can end the form via that path."""
    totals: dict[str, int] = {}
    for type_name, _bars, _energy, _variant in raw_sections:
        totals[type_name] = totals.get(type_name, 0) + 1

    tag_bars = template.ending.tag_bars if ending_tag_bars is None else ending_tag_bars
    counters: dict[str, int] = {}
    sections: list[FormSection] = []
    start_bar = 0
    last = len(raw_sections) - 1
    for i, (type_name, bars, override, variant) in enumerate(raw_sections):
        counters[type_name] = counters.get(type_name, 0) + 1
        index = counters[type_name]
        total_of_type = totals[type_name]
        sd = def_of(type_name)
        ending = (
            SectionEnding(tag_bars=tag_bars, close=template.ending.close)
            if i == last
            else None
        )
        sections.append(
            FormSection(
                id=f"{type_name}-{index}",
                type=type_name,
                index=index,
                start_bar=start_bar,
                length_bars=bars,
                energy=section_energy(
                    type_name,
                    index,
                    total_of_type,
                    arousal,
                    energy_range,
                    override=override,
                ),
                total_of_type=total_of_type,
                phrases=_phrases(sd, bars),
                harmony_tag=_harmony_tag(sd, bars),
                variant=variant,
                ending=ending,
            )
        )
        start_bar += bars

    return SongForm(sections=sections, total_bars=start_bar, template_id=template.id)


def _fallback_form(
    template: FormTemplate,
    bar_budget: int,
    arousal: float,
    energy_range: tuple[float, float],
    def_of: Callable[[str], SectionDef],
) -> SongForm:
    """§7.1 step 6 — the minimal form of last resort: one `fallback.section`
    section, snapped to the 4-bar grid within the budget, the template ending
    attached. F11 guarantees bar_budget >= 4, so length_bars >= 4."""
    fb = template.fallback
    length = min(fb.bars, 4 * (bar_budget // 4))
    # F8 bounds template.ending.tag_bars by the fallback section's smallest
    # authored bar option, but this budget-clamped `length` can still be
    # smaller than that bound (e.g. tag_bars=8, length=4) — an unreachable
    # case for the two reference packs but latent for future ones. Clamp to
    # the largest legal {0, 4, 8} value that still fits the emitted section;
    # the normal-assembly path doesn't need this (F8 covers it there).
    tag_bars: Literal[0, 4, 8] = 8 if length >= 8 else 4 if length >= 4 else 0
    return _assemble(
        [(fb.section, length, None, None)],
        template,
        arousal,
        energy_range,
        def_of,
        ending_tag_bars=tag_bars,
    )
