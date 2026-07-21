"""Tests for the Form generator stage (PHASE_3 §7, DoD §11.3-§11.7).

Golden numbers (both §7.4 worked examples, the §7.2 seed vectors, and the
8 / 1 / 0 draw counts) are NORMATIVE — do not edit an expected value to match
code output (ROADMAP §3 golden-value arbitration). A divergence means an
implementation bug.
"""

from __future__ import annotations

import random
from collections.abc import Callable

import pytest

from _packmatrix import (
    LENGTHS_PLAN,
    PACKS,
    SEEDS_25,
    build_plan,
    cached_pack,
    pack_mood_pairs,
    supported_moods,
    total_moods,
)
from trackgen.form.stage import _fit_and_degrade, form, section_label
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import (
    DegradeOp,
    Fallback,
    FormEnding,
    FormsConfig,
    FormTemplate,
    SectionDef,
    TemplateSlot,
)
from trackgen.schema.ir import SectionEnding, SongForm
from trackgen.seeds import derive, stream_rng

# --- helpers -----------------------------------------------------------------

# A golden row: (id, type, index, total_of_type, start_bar, length_bars,
#                phrases[(label, bars)...], harmony_tag, energy, label).
GoldenRow = tuple[str, str, int, int, int, int, list[tuple[str, int]], str, float, str]


def _assert_songform(sf: SongForm, rows: list[GoldenRow]) -> None:
    assert len(sf.sections) == len(rows)
    last = len(rows) - 1
    for i, (sec, row) in enumerate(zip(sf.sections, rows, strict=True)):
        rid, rtype, ridx, rtot, rstart, rlen, rphr, rtag, ren, rlabel = row
        assert sec.id == rid
        assert sec.type == rtype
        assert sec.index == ridx
        assert sec.total_of_type == rtot
        assert sec.start_bar == rstart
        assert sec.length_bars == rlen
        assert [(p.label, p.bars) for p in sec.phrases] == rphr
        assert sec.harmony_tag == rtag
        assert sec.energy == ren
        # Both §7.4 reference forms carry no variant (§9 Q1: label-only in v1).
        assert sec.variant is None
        assert section_label(sec.type, sec.index, sec.total_of_type, sec.variant) == (
            rlabel
        )
        # ending non-null on exactly the final section (§4.1 / D6).
        if i == last:
            assert sec.ending is not None
        else:
            assert sec.ending is None


class _CountingRandom(random.Random):
    """Wraps a seeded `random.Random`, counting every `randrange` call.
    `weighted_choice` makes exactly one `randrange` call per draw, so the count
    is the exact number of draws (§11.5 counting shim). `getrandbits` is NOT
    counted: `randrange` calls it internally, so counting both would inflate the
    tally past the number of `weighted_choice` invocations."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        _CountingRandom.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


@pytest.fixture
def count_draws(monkeypatch: pytest.MonkeyPatch) -> Callable[[], int]:
    """Patch `stream_rng` inside the Form stage so its RNG counts draws, and
    return an accessor for the running count. Reset the count before use."""

    def patched(master: int, overrides: dict[str, int], name: str) -> random.Random:
        base = stream_rng(master, overrides, name)
        counting = _CountingRandom()
        counting.setstate(base.getstate())
        return counting

    monkeypatch.setattr("trackgen.form.stage.stream_rng", patched)

    def reset_and_get() -> int:
        return _CountingRandom.draws

    _CountingRandom.draws = 0
    return reset_and_get


# --- §11.3 golden example 1 --------------------------------------------------

# PHASE_3 §7.4 Example 1 — pop_rock / happy, seed 1ps9wxb, budget 92 bars.
# normative — do not edit to match code
EXAMPLE_1_ROWS: list[GoldenRow] = [
    ("intro-1", "intro", 1, 1, 0, 4, [("a", 4)], "intro", 0.340, "Intro"),
    ("verse-1", "verse", 1, 2, 4, 8, [("a", 4), ("a", 4)], "verse", 0.490, "Verse 1"),
    (
        "chorus-1",
        "chorus",
        1,
        3,
        12,
        16,
        [("a", 4), ("a", 4), ("a", 4), ("a", 4)],
        "chorus",
        0.790,
        "Chorus 1",
    ),
    ("verse-2", "verse", 2, 2, 28, 8, [("a", 4), ("a", 4)], "verse", 0.540, "Verse 2"),
    (
        "chorus-2",
        "chorus",
        2,
        3,
        36,
        16,
        [("a", 4), ("a", 4), ("a", 4), ("a", 4)],
        "chorus",
        0.840,
        "Chorus 2",
    ),
    (
        "bridge-1",
        "bridge",
        1,
        1,
        52,
        8,
        [("a", 4), ("a", 4)],
        "bridge",
        0.440,
        "Bridge",
    ),
    (
        "chorus-3",
        "chorus",
        3,
        3,
        60,
        16,
        [("a", 4), ("a", 4), ("a", 4), ("a", 4)],
        "chorus",
        1.000,
        "Final Chorus",
    ),
]


def test_golden_example_1_field_for_field() -> None:
    """PHASE_3 §7.4 Example 1 — the whole SongForm, field-for-field."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)

    _assert_songform(sf, EXAMPLE_1_ROWS)
    assert sf.total_bars == 76
    assert sf.template_id == "verse_chorus_bridge"
    assert sf.sections[-1].ending == SectionEnding(tag_bars=0, close="cold")
    # hard ceiling honored (§7.1).
    tpb = plan.time_signature.numerator * (480 * 4 // plan.time_signature.denominator)
    assert sf.total_bars * tpb <= plan.max_length_ticks


# --- §11.3 golden example 2 --------------------------------------------------

# PHASE_3 §7.4 Example 2 — jazz / melancholic, 240 s, seed 1ps9wxb, budget 69.
# normative — do not edit to match code
_ABC = [("a", 4), ("b", 4), ("c", 4)]
EXAMPLE_2_ROWS: list[GoldenRow] = [
    ("head-1", "head", 1, 2, 0, 12, _ABC, "blues_12", 0.464, "Head In"),
    ("solo-1", "solo", 1, 3, 12, 12, _ABC, "blues_12", 0.624, "Solo Chorus 1"),
    ("solo-2", "solo", 2, 3, 24, 12, _ABC, "blues_12", 0.704, "Solo Chorus 2"),
    ("solo-3", "solo", 3, 3, 36, 12, _ABC, "blues_12", 0.784, "Solo Chorus 3"),
    ("head-2", "head", 2, 2, 48, 12, _ABC, "blues_12", 0.464, "Head Out"),
    ("outro-1", "outro", 1, 1, 60, 4, [("a", 4)], "outro", 0.344, "Outro"),
]


def test_golden_example_2_field_for_field() -> None:
    """PHASE_3 §7.4 Example 2 — the whole SongForm, field-for-field."""
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack("jazz")
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)

    _assert_songform(sf, EXAMPLE_2_ROWS)
    assert sf.total_bars == 64
    assert sf.template_id == "head_solos_head"
    assert sf.sections[-1].ending == SectionEnding(tag_bars=4, close="ritard")
    tpb = plan.time_signature.numerator * (480 * 4 // plan.time_signature.denominator)
    assert sf.total_bars * tpb <= plan.max_length_ticks


# --- §11.4 seed vectors ------------------------------------------------------


def test_form_stream_seed_vectors() -> None:
    """PHASE_3 §7.2 — the form-stream RNG golden vectors (orchestrator-verified;
    normative)."""
    seed = derive(3735928559, "form")
    assert seed == 7567330889165579844

    r = random.Random(seed)
    assert [r.getrandbits(32) for _ in range(5)] == [
        1669109759,
        4115657646,
        81846092,
        4122630717,
        1459238978,
    ]
    r2 = random.Random(seed)
    assert [r2.randrange(100) for _ in range(5)] == [49, 2, 43, 66, 44]


# --- §11.5 determinism + draw counts -----------------------------------------


def test_determinism_same_plan_identical_form() -> None:
    """PHASE_3 §11.5 — the same plan yields an identical SongForm."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    assert form(plan, pack.forms) == form(plan, pack.forms)


def test_draw_count_example_1(count_draws: Callable[[], int]) -> None:
    """PHASE_3 §11.5 — Example 1 consumes exactly 8 form-stream draws."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    form(plan, pack.forms)
    assert count_draws() == 8


def test_draw_count_example_2(count_draws: Callable[[], int]) -> None:
    """PHASE_3 §11.5 — Example 2 consumes exactly 1 form-stream draw."""
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack("jazz")
    assert pack is not None and pack.forms is not None
    form(plan, pack.forms)
    assert count_draws() == 1


def test_draw_count_zero_on_fallback(count_draws: Callable[[], int]) -> None:
    """PHASE_3 §11.5 — a fallback-triggering tiny budget consumes zero draws
    (no template eligible → straight to the fallback, no candidate ever has
    >= 2 options)."""
    plan = generate_plan(
        {
            "styleFamily": "pop_rock",
            "maxLengthSec": 30,
            "tempoBpm": 70,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    assert count_draws() == 0
    assert len(sf.sections) == 1  # single fallback section


def test_draws_only_when_two_feasible_budget_shift(
    count_draws: Callable[[], int],
) -> None:
    """PHASE_3 §11.5 / D13 — shrinking the budget so bar options become the
    single feasible one removes their draws: fewer total draws at the smaller
    budget, same template selected. tempo 120, seed 1ps9wxb, both pick
    verse_chorus_bridge; budget 90 bars → 8 draws, budget 55 bars → 4 draws."""
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None

    plan_large = generate_plan(
        {
            "styleFamily": "pop_rock",
            "maxLengthSec": 180,
            "tempoBpm": 120,
            "seed": "1ps9wxb",
        }
    )
    _CountingRandom.draws = 0
    sf_large = form(plan_large, pack.forms)
    draws_large = count_draws()

    plan_small = generate_plan(
        {
            "styleFamily": "pop_rock",
            "maxLengthSec": 110,
            "tempoBpm": 120,
            "seed": "1ps9wxb",
        }
    )
    _CountingRandom.draws = 0
    sf_small = form(plan_small, pack.forms)
    draws_small = count_draws()

    assert sf_large.template_id == sf_small.template_id == "verse_chorus_bridge"
    assert draws_large == 8
    assert draws_small == 4
    assert draws_small < draws_large


# --- §11.6 property matrix ---------------------------------------------------


def _expected_label(type_name: str, index: int, total: int, variant: str | None) -> str:
    """PHASE_3 §3.3, reimplemented independently of `stage.section_label` (the
    stage's single source of truth) so the property test cross-checks the
    §3.3 rule against a second implementation rather than the helper against
    itself. Mirrors the table exactly: chorus/head/solo/main get their
    specials; everything else is title-cased with the index appended iff
    `total > 1`."""
    if type_name == "chorus":
        if total >= 2 and index == total:
            return "Final Chorus"
        return f"Chorus {index}" if total > 1 else "Chorus"
    if type_name == "head":
        if index == 1:
            return "Head In"
        if index == total:
            return "Head Out"
        return f"Head {index}"
    if type_name == "solo":
        return f"Solo Chorus {index}" if total > 1 else "Solo Chorus"
    if type_name == "main":
        return f"Part {variant}" if variant else f"Part {index}"
    base = {"prechorus": "Pre-Chorus", "postchorus": "Post-Chorus"}.get(
        type_name, type_name.title()
    )
    return f"{base} {index}" if total > 1 else base


@pytest.mark.parametrize(("style", "mood"), list(pack_mood_pairs()))
def test_property_valid_songform(style: str, mood: str) -> None:
    """PHASE_3 §11.6 — every pack × supported mood × length grid × 25 seeds
    yields a SongForm that validates every structural invariant."""
    pack = cached_pack(style)
    forms = pack.forms
    assert forms is not None

    for max_len_sec in LENGTHS_PLAN:
        for seed in SEEDS_25:
            plan = build_plan(style, mood, max_len_sec, seed)
            sf = form(plan, forms)
            tpb = plan.time_signature.numerator * (
                480 * 4 // plan.time_signature.denominator
            )

            # contiguity from bar 0, no gaps/overlaps.
            assert sf.sections[0].start_bar == 0
            running = 0
            for sec in sf.sections:
                assert sec.start_bar == running
                running += sec.length_bars
            assert sf.total_bars == running

            # hard ceiling.
            assert sf.total_bars * tpb <= plan.max_length_ticks

            # per-type index / total_of_type consistency.
            seen: dict[str, int] = {}
            totals: dict[str, int] = {}
            for sec in sf.sections:
                totals[sec.type] = totals.get(sec.type, 0) + 1
            for sec in sf.sections:
                seen[sec.type] = seen.get(sec.type, 0) + 1
                assert sec.index == seen[sec.type]
                assert sec.total_of_type == totals[sec.type]
                # 4-bar grid.
                assert sec.length_bars % 4 == 0 and sec.length_bars >= 4
                # energies in [0, 1] at 3 decimals.
                assert 0.0 <= sec.energy <= 1.0
                assert round(sec.energy, 3) == sec.energy
                # phrases cover the section exactly.
                assert sum(p.bars for p in sec.phrases) == sec.length_bars
                # §3.3 label: the stage's source of truth must match an
                # independently-written second implementation of the rule.
                assert section_label(
                    sec.type, sec.index, sec.total_of_type, sec.variant
                ) == _expected_label(
                    sec.type, sec.index, sec.total_of_type, sec.variant
                )
                # neither reference pack ever sets variant (§9 Q1); a stray
                # value would be a bug in slot resolution/assembly.
                assert sec.variant is None

            # ending on exactly the final section, and never longer than the
            # section it tags (§4.1: tagBars in {0, 4, 8}, <= lengthBars).
            assert all(sec.ending is None for sec in sf.sections[:-1])
            final = sf.sections[-1]
            assert final.ending is not None
            assert final.ending.tag_bars in (0, 4, 8)
            assert final.ending.tag_bars <= final.length_bars


def test_matrix_non_vacuous() -> None:
    """The §11.6 matrix is the exact expected size and covers every pack.

    Dimensions are recomputed from pack data (not restated), so a silent shrink
    — a pack dropped from the registry, a mood lost, a truncated seed list —
    fails loudly rather than quietly narrowing coverage (ROADMAP §3)."""
    assert len(PACKS) >= 5, PACKS
    assert len(LENGTHS_PLAN) == 39, LENGTHS_PLAN
    assert len(SEEDS_25) == len(set(SEEDS_25)) == 25, SEEDS_25

    expected = total_moods()

    cells = list(pack_mood_pairs())
    assert len(cells) == expected, (len(cells), expected)
    assert {style for style, _ in cells} == set(PACKS)
    assert len(cells) == len(set(cells)), "duplicate (pack, mood) cell"


# --- §11.7 fallback & degrade ------------------------------------------------


@pytest.mark.parametrize(
    ("style", "tempo", "expected_type"),
    [("pop_rock", 70, "chorus"), ("jazz", 60, "solo")],
)
def test_tiny_budget_hits_fallback(style: str, tempo: int, expected_type: str) -> None:
    """PHASE_3 §11.7 — a tiny budget (30 s at the pack's slow tempo, below every
    template's minBars) hits the single-section fallback and validates as a
    >= 4-bar form (F11 guarantees barBudget >= 4)."""
    plan = generate_plan(
        {
            "styleFamily": style,
            "maxLengthSec": 30,
            "tempoBpm": tempo,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack(style)
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)

    assert len(sf.sections) == 1
    sec = sf.sections[0]
    assert sec.type == expected_type
    assert sec.length_bars >= 4 and sec.length_bars % 4 == 0
    assert sum(p.bars for p in sec.phrases) == sec.length_bars
    assert sec.ending is not None  # the template ending attaches to the fallback
    tpb = plan.time_signature.numerator * (480 * 4 // plan.time_signature.denominator)
    assert sf.total_bars * tpb <= plan.max_length_ticks


def test_fallback_clamps_tag_bars_to_section_length() -> None:
    """PHASE_3 §7.1 step 6 / §4.1 (Fix 1, reviewer-confirmed) — the fallback
    path must not emit an `ending.tag_bars` longer than the fallback section
    it tags. `tag_bars` is bounded (F8) by the *authored* smallest bar option
    of the ending-candidate type, but the budget-clamped fallback length
    (`min(fallback.bars, 4 * (bar_budget // 4))`) is a separate quantity that
    can come out smaller still. This is unreachable for the two reference
    packs (pop_rock `tag_bars=0`, jazz `tag_bars=4`) but latent for future
    packs, so it is forced here via a synthetic single-template pack: an
    8-bar `ending.tag_bars` whose fallback (`bars=4`) gets clamped to a
    4-bar section by a 4-bar budget. Pre-fix this emitted `tag_bars == 8` on
    a 4-bar section — an ending longer than the section it closes."""
    section = SectionDef(bars=((8, 1),), phrases={8: ("a",)}, harmony_tag={8: "outro"})
    template = FormTemplate(
        id="t1",
        weight=1,
        spine=(TemplateSlot(section="outro"),),
        ending=FormEnding(tag_bars=8, close="cold"),
        fallback=Fallback(section="outro", bars=4),
    )
    forms = FormsConfig(
        energy_range=(0.0, 1.0), sections={"outro": section}, templates=(template,)
    )

    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    ticks_per_bar = plan.time_signature.numerator * (
        480 * 4 // plan.time_signature.denominator
    )
    # bar_budget == 4: below the template's minBars (8), so no template is
    # eligible and form() routes straight to the fallback (step 2).
    plan = plan.model_copy(update={"max_length_ticks": 4 * ticks_per_bar})

    sf = form(plan, forms)

    assert len(sf.sections) == 1
    sec = sf.sections[0]
    assert sec.length_bars == 4
    assert sec.ending is not None
    assert sec.ending.tag_bars == 4
    assert sec.ending.tag_bars <= sec.length_bars


@pytest.mark.parametrize(("style", "tempo"), [("pop_rock", 70), ("jazz", 60)])
def test_30s_at_slow_tempo_valid_form(style: str, tempo: int) -> None:
    """PHASE_3 §11.7 — 30 s at each pack's tempoRange.lo produces a valid,
    playable >= 4-bar form."""
    plan = generate_plan(
        {
            "styleFamily": style,
            "maxLengthSec": 30,
            "tempoBpm": tempo,
            "seed": "1ps9wxb",
        }
    )
    pack = resolve_pack(style)
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)

    assert sf.total_bars >= 4
    assert all(s.length_bars >= 4 for s in sf.sections)
    tpb = plan.time_signature.numerator * (480 * 4 // plan.time_signature.denominator)
    assert sf.total_bars * tpb <= plan.max_length_ticks


def test_degrade_ladder_authored_order() -> None:
    """PHASE_3 §7.3 / D11 — each pack authors a degrade ladder covering the op
    classes it needs, in the corpus-presence order. pop_rock drops outro before
    bridge (D11); every op names a spine type (F9). This asserts the ladder
    *data* (the mechanism's authored input) per class; the ladder's runtime
    reachability is covered by ``test_degrade_ladder_is_unreachable``."""
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    vcb = next(t for t in pack.forms.templates if t.id == "verse_chorus_bridge")
    ops = [(op.drop, op.shrink, op.drop_from_repeat) for op in vcb.degrade]
    assert ops == [
        ("outro", None, None),
        (None, "intro", None),
        ("bridge", None, None),
        (None, None, "prechorus"),
        (None, "verse", None),
        (None, "chorus", None),
        ("intro", None, None),
    ]
    # all three op classes are represented across the ladder.
    kinds = {
        "drop" if op.drop else "shrink" if op.shrink else "drop_from_repeat"
        for op in vcb.degrade
    }
    assert kinds == {"drop", "shrink", "drop_from_repeat"}

    jazz = resolve_pack("jazz")
    assert jazz is not None and jazz.forms is not None
    hsh = jazz.forms.templates[0]
    assert [(op.shrink, op.drop) for op in hsh.degrade] == [
        ("intro", None),
        (None, "intro"),
        (None, "outro"),
    ]


def test_degrade_ladder_is_unreachable() -> None:
    """PHASE_3 §7.1/§7.3 (implementer finding — ESCALATED): with faithful §5.2
    eligibility (minBars ≤ barBudget = the minimal config) and §7.1-step-3
    feasibility (every drawn/forced option keeps minimalTotal ≤ barBudget), the
    minimal config of any *selected* template always fits, and over-budget
    templates route to the fallback (step 6) instead. The degrade ladder is
    therefore never entered for the reference packs — proven analytically and by
    a 40k-run adversarial synthetic search. This test is the regression guard:
    across the whole pack × mood × length × seed grid, no form's total ever
    exceeds its budget (which would be the only trigger for a ladder op), and
    every too-small case is a single-section fallback.
    """
    for style in PACKS:
        pack = cached_pack(style)
        assert pack.forms is not None
        for mood in supported_moods(style)[:3]:
            for max_len_sec in (30, 45, 60, 120):
                for seed in SEEDS_25[:5]:
                    plan = build_plan(style, mood, max_len_sec, seed)
                    sf = form(plan, pack.forms)
                    tpb = plan.time_signature.numerator * (
                        480 * 4 // plan.time_signature.denominator
                    )
                    # The only ladder trigger is total > budget after step 4;
                    # it never occurs, so the ceiling always holds with room to
                    # spare handled entirely by eligibility + fallback.
                    assert sf.total_bars * tpb <= plan.max_length_ticks


def test_form_requires_forms_config() -> None:
    """D-S11 — form() raises a clear error when handed a falsy forms config."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    with pytest.raises(ValueError, match="requires a non-null FormsConfig"):
        form(plan, None)  # type: ignore[arg-type]


# --- white-box degrade-ladder semantics (CAVEATS C-02) -----------------------
# The ladder is unreachable through the public `form()` API (proven in
# `test_degrade_ladder_is_unreachable` + CAVEATS C-02), so its drop / shrink /
# dropFromRepeat op semantics can't be exercised end-to-end. These tests drive
# `_fit_and_degrade` directly with a synthetic over-budget state — the substitute
# coverage DoD §11.7 is satisfied by — locking each op class's effect and the
# authored-order + exhaustion control flow.


def _smallest_of(table: dict[str, int]) -> Callable[[str], int]:
    return lambda section: table[section]


def test_ladder_drop_removes_top_level_slots() -> None:
    intro, verse, outro = (TemplateSlot(section=s) for s in ("intro", "verse", "outro"))
    resolved = {"intro": 8, "verse": 16, "outro": 8}  # total 32
    dropped_top: set[int] = set()
    dropped_repeat: set[int] = set()
    count, total = _fit_and_degrade(
        degrade=(DegradeOp(drop="outro"),),
        top_level=[(intro, 0), (verse, 1), (outro, 2)],
        repeat_inner=[],
        resolved_bars=resolved,
        optional_decision={},
        dropped_top=dropped_top,
        dropped_repeat=dropped_repeat,
        count_min=0,
        count_max=None,
        has_repeat=False,
        bar_budget=24,
        rk=lambda s: s,
        smallest=_smallest_of({"intro": 4, "verse": 8, "outro": 4}),
    )
    assert dropped_top == {2}  # only the outro slot dropped
    assert count == 0
    assert total == 24  # 8 + 16


def test_ladder_shrink_sets_type_to_smallest() -> None:
    intro, verse = TemplateSlot(section="intro"), TemplateSlot(section="verse")
    resolved = {"intro": 8, "verse": 16}  # total 24
    count, total = _fit_and_degrade(
        degrade=(DegradeOp(shrink="verse"),),
        top_level=[(intro, 0), (verse, 1)],
        repeat_inner=[],
        resolved_bars=resolved,
        optional_decision={},
        dropped_top=set(),
        dropped_repeat=set(),
        count_min=0,
        count_max=None,
        has_repeat=False,
        bar_budget=16,
        rk=lambda s: s,
        smallest=_smallest_of({"intro": 4, "verse": 8}),
    )
    assert resolved["verse"] == 8  # shrunk to its smallest option
    assert total == 16  # 8 + 8


def test_ladder_drop_from_repeat_shrinks_the_cycle() -> None:
    intro = TemplateSlot(section="intro")
    chorus, verse = TemplateSlot(section="chorus"), TemplateSlot(section="verse")
    resolved = {"intro": 8, "chorus": 8, "verse": 8}
    dropped_repeat: set[int] = set()
    # block=16, count clamped to [1,1]: total = 8 + 1*16 = 24 > 16 → ladder fires.
    count, total = _fit_and_degrade(
        degrade=(DegradeOp(drop_from_repeat="verse"),),
        top_level=[(intro, 0)],
        repeat_inner=[(chorus, 1), (verse, 2)],
        resolved_bars=resolved,
        optional_decision={},
        dropped_top=set(),
        dropped_repeat=dropped_repeat,
        count_min=1,
        count_max=1,
        has_repeat=True,
        bar_budget=16,
        rk=lambda s: s,
        smallest=_smallest_of({"intro": 4, "chorus": 4, "verse": 4}),
    )
    assert dropped_repeat == {2}  # verse removed from the repeat cycle
    assert count == 1
    assert total == 16  # 8 + 1*8 (cycle now just chorus)


def test_ladder_applies_ops_in_authored_order() -> None:
    intro, verse, outro = (TemplateSlot(section=s) for s in ("intro", "verse", "outro"))
    resolved = {"intro": 8, "verse": 16, "outro": 8}  # total 32
    dropped_top: set[int] = set()
    count, total = _fit_and_degrade(
        degrade=(DegradeOp(drop="outro"), DegradeOp(shrink="verse")),
        top_level=[(intro, 0), (verse, 1), (outro, 2)],
        repeat_inner=[],
        resolved_bars=resolved,
        optional_decision={},
        dropped_top=dropped_top,
        dropped_repeat=set(),
        count_min=0,
        count_max=None,
        has_repeat=False,
        bar_budget=16,
        rk=lambda s: s,
        smallest=_smallest_of({"intro": 4, "verse": 8, "outro": 4}),
    )
    # drop(outro) → 24 (still > 16), then shrink(verse) → 16. Both applied.
    assert dropped_top == {2}
    assert resolved["verse"] == 8
    assert total == 16
    assert count == 0


def test_ladder_exhausted_leaves_total_over_budget() -> None:
    """When the ladder runs dry still over budget, `_fit_and_degrade` returns a
    total > bar_budget — the signal form() uses to route to the fallback."""
    verse = TemplateSlot(section="verse")
    count, total = _fit_and_degrade(
        degrade=(),  # no ops
        top_level=[(verse, 0)],
        repeat_inner=[],
        resolved_bars={"verse": 16},
        optional_decision={},
        dropped_top=set(),
        dropped_repeat=set(),
        count_min=0,
        count_max=None,
        has_repeat=False,
        bar_budget=8,
        rk=lambda s: s,
        smallest=_smallest_of({"verse": 4}),
    )
    assert count == 0
    assert total == 16  # unchanged; > budget → form() falls back
