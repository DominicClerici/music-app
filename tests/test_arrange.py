"""Tests for the Arrangement planner (PHASE_5 §4, SESSION_07 T1, DoD §13.3).

The §4.5 golden tables (both worked arrangements), the register shifts, and the
zero-draw guarantee are NORMATIVE — every expected value here is transcribed
from PHASE_5 §4.5 / SESSION_07 §T1, never read back off code output (ROADMAP §3
golden-value arbitration). A divergence is an implementation bug to escalate.

`source is frozen`: this file treats `arrange()` as a black box for the goldens
and property matrix; the mechanism-unit tests additionally exercise the two
pure helpers (`_provisional_count`, `_register_for`) white-box.
"""

from __future__ import annotations

import random

import pytest

from _packmatrix import (
    LENGTHS_PLAN,
    PACKS,
    SEEDS_25,
    build_plan,
    cached_pack,
    pack_mood_pairs,
    total_moods,
)
from trackgen.arrangement.arrange import (
    _BASE_COUNT,
    _provisional_count,
    _register_for,
    arrange,
    load_lanes_table,
)
from trackgen.arrangement.intensity import intensity
from trackgen.form.stage import form
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementEntry,
    FormSection,
    GenerationPlan,
    Register,
    SectionPhrase,
    SongForm,
)
from trackgen.seeds import stream_rng

_ORDER: tuple[Role, ...] = ("drums", "bass", "comping", "pads")


# --- draw-counting shim (copied from tests/test_harmony_goldens.py) ----------


class _CountingRandom(random.Random):
    """Wraps a seeded `random.Random`, counting every `randrange` call.
    `weighted_choice` makes exactly one `randrange` per draw, so the count is
    the exact number of draws. `getrandbits` is not counted (randrange calls it
    internally)."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        _CountingRandom.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


# --- helpers -----------------------------------------------------------------


def _arrange_rng(plan: GenerationPlan) -> random.Random:
    return stream_rng(plan.seed.master, plan.seed.overrides, "arrangement")


def _by_pair(
    plan_entries: list[ArrangementEntry],
) -> dict[tuple[str, Role], ArrangementEntry]:
    out: dict[tuple[str, Role], ArrangementEntry] = {}
    for entry in plan_entries:
        key = (entry.section_id, entry.role)
        assert key not in out, f"duplicate entry for {key}"
        out[key] = entry
    return out


def _active_roles(
    by_pair: dict[tuple[str, Role], ArrangementEntry], sid: str
) -> set[Role]:
    return {role for role in _ORDER if by_pair[(sid, role)].active}


def _mk_section(
    type_name: str, energy: float, *, sid: str = "s", index: int = 1
) -> FormSection:
    return FormSection(
        id=sid,
        type=type_name,
        index=index,
        start_bar=0,
        length_bars=8,
        energy=energy,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=8)],
        harmony_tag=type_name,
    )


# =============================================================================
# §4.5 goldens — pop_rock / happy  (noteDensity 0.648, layersMax 4, bias +0.188)
# =============================================================================

# A golden row: (section_id, rung, count, densityBudget, active-role set).
# Transcribed from PHASE_5 §4.5 / SESSION_07 §T1 — NORMATIVE.
_POP_GOLDEN: list[tuple[str, int, int, float, set[Role]]] = [
    ("intro-1", 2, 2, 0.586, {"drums", "bass"}),
    ("verse-1", 2, 3, 0.644, {"drums", "bass", "comping"}),
    ("chorus-1", 3, 4, 0.761, {"drums", "bass", "comping", "pads"}),
    ("verse-2", 2, 3, 0.664, {"drums", "bass", "comping"}),
    ("chorus-2", 4, 4, 0.780, {"drums", "bass", "comping", "pads"}),
    ("bridge-1", 2, 3, 0.625, {"drums", "bass", "comping"}),
    ("chorus-3", 4, 4, 0.842, {"drums", "bass", "comping", "pads"}),
]

# §4.3 pop registers: bias +0.188 → shift round(2.256)=+2; comping 48-71 → 50-71
# (73 capped), pads 43-71 → 45-71. bass/drums unshifted.
_POP_REGISTERS: dict[Role, Register] = {
    "drums": Register(low_midi=0, high_midi=127),
    "bass": Register(low_midi=28, high_midi=55),
    "comping": Register(low_midi=50, high_midi=71),
    "pads": Register(low_midi=45, high_midi=71),
}


def test_pop_arrangement_golden_field_for_field() -> None:
    """PHASE_5 §4.5 — the pop_rock/happy arrangement, field-for-field."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)

    # Lock the §4.5 upstream anchors so the density/register goldens are exact.
    assert plan.budgets.note_density == 0.648
    assert plan.budgets.layers_max == 4
    assert plan.budgets.register_bias == 0.188

    ap = arrange(plan, sf, pack, _arrange_rng(plan))
    by_pair = _by_pair(ap.entries)

    # every (section, role) pair present exactly once.
    assert len(ap.entries) == len(_POP_GOLDEN) * 4

    for sid, rung, count, density, active in _POP_GOLDEN:
        for role in _ORDER:
            entry = by_pair[(sid, role)]
            assert entry.intensity == rung, (sid, role)
            assert entry.density_budget == density, (sid, role)
            assert entry.active == (role in active), (sid, role)
            assert entry.register == _POP_REGISTERS[role], (sid, role)
        assert _active_roles(by_pair, sid) == active
        assert len(active) == count


# =============================================================================
# §4.5 goldens — jazz / melancholic  (noteDensity 0.505, layersMax 3, bias −0.125)
# =============================================================================

# Transcribed from PHASE_5 §4.5 / SESSION_07 §T1 — NORMATIVE. Active everywhere:
# drums, bass, comping (pads capped out by layersMax 3 — the trio).
_JAZZ_TRIO: set[Role] = {"drums", "bass", "comping"}
_JAZZ_GOLDEN: list[tuple[str, int, int, float, set[Role]]] = [
    ("head-1", 2, 3, 0.494, _JAZZ_TRIO),
    ("solo-1", 3, 3, 0.543, _JAZZ_TRIO),
    ("solo-2", 3, 3, 0.567, _JAZZ_TRIO),
    ("solo-3", 3, 3, 0.591, _JAZZ_TRIO),
    ("head-2", 2, 3, 0.494, _JAZZ_TRIO),
    ("outro-1", 2, 3, 0.458, _JAZZ_TRIO),
]

# §4.3 jazz registers: bias −0.125 → shift round(−1.5)=−2 (half-even); comping
# 48-71 → 46-69, pads 43-71 → 41-69.
_JAZZ_REGISTERS: dict[Role, Register] = {
    "drums": Register(low_midi=0, high_midi=127),
    "bass": Register(low_midi=28, high_midi=55),
    "comping": Register(low_midi=46, high_midi=69),
    "pads": Register(low_midi=41, high_midi=69),
}


def test_jazz_arrangement_golden_field_for_field() -> None:
    """PHASE_5 §4.5 — the jazz/melancholic arrangement, field-for-field."""
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

    assert plan.budgets.note_density == 0.505
    assert plan.budgets.layers_max == 3
    assert plan.budgets.register_bias == -0.125

    ap = arrange(plan, sf, pack, _arrange_rng(plan))
    by_pair = _by_pair(ap.entries)

    assert len(ap.entries) == len(_JAZZ_GOLDEN) * 4

    for sid, rung, count, density, active in _JAZZ_GOLDEN:
        for role in _ORDER:
            entry = by_pair[(sid, role)]
            assert entry.intensity == rung, (sid, role)
            assert entry.density_budget == density, (sid, role)
            assert entry.active == (role in active), (sid, role)
            assert entry.register == _JAZZ_REGISTERS[role], (sid, role)
        assert _active_roles(by_pair, sid) == active
        assert len(active) == count
        # pads is emitted for every section but never active (layersMax 3).
        assert by_pair[(sid, "pads")].active is False


# =============================================================================
# Zero-draw — the `arrangement` stream is reserved (§3.6, §4)
# =============================================================================


def test_arrange_consumes_zero_draws() -> None:
    """PHASE_5 §3.6/§4 — `arrange()` never consumes its `rng`. A counting shim
    passed as the rng registers 0 draws across both worked plans."""
    counting = _CountingRandom(20260716)
    _CountingRandom.draws = 0

    pop_plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pop_pack = resolve_pack("pop_rock")
    assert pop_pack is not None and pop_pack.forms is not None
    arrange(pop_plan, form(pop_plan, pop_pack.forms), pop_pack, counting)

    jazz_plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    jazz_pack = resolve_pack("jazz")
    assert jazz_pack is not None and jazz_pack.forms is not None
    arrange(jazz_plan, form(jazz_plan, jazz_pack.forms), jazz_pack, counting)

    assert _CountingRandom.draws == 0


# =============================================================================
# Mechanism units
# =============================================================================


@pytest.mark.parametrize(
    ("energy", "expected_rung", "expected_base"),
    [(0.10, 1, 2), (0.40, 2, 3), (0.60, 3, 4), (0.90, 4, 4)],
)
def test_base_count_per_rung(
    energy: float, expected_rung: int, expected_base: int
) -> None:
    """§4.1 baseCount = {1:2, 2:3, 3:4, 4:4}; with layersMax 4 the base count is
    uncapped, so the provisional count is exactly baseCount[rung]."""
    assert intensity(energy) == expected_rung
    assert _BASE_COUNT[expected_rung] == expected_base
    assert _provisional_count(_mk_section("verse", energy), layers_max=4) == (
        expected_base
    )


def test_layers_max_caps_count() -> None:
    """§4.1 count = min(layersMax, baseCount[rung]): a rung-4 section under
    layersMax 3 caps at 3."""
    assert _provisional_count(_mk_section("chorus", 0.90), layers_max=3) == 3


def test_breakdown_modifier_min_2() -> None:
    """§4.1 breakdown: count = min(count, 2) — a rung-3 breakdown (base 4)
    thins to 2."""
    assert _provisional_count(_mk_section("breakdown", 0.60), layers_max=4) == 2


def test_bridge_modifier_min_3() -> None:
    """§4.1 bridge: count = min(count, 3) — a rung-4 bridge (base 4) thins to 3;
    a rung-2 bridge (base 3) is unchanged."""
    assert _provisional_count(_mk_section("bridge", 0.90), layers_max=4) == 3
    assert _provisional_count(_mk_section("bridge", 0.40), layers_max=4) == 3


def _arrange_synth(
    sections: list[FormSection],
    *,
    note_density: float = 0.6,
    layers_max: int = 4,
    register_bias: float = 0.0,
) -> dict[tuple[str, Role], ArrangementEntry]:
    """Run `arrange()` over a synthetic form, overriding the budgets that drive
    activation/density/registers on a real pop plan (which supplies a valid
    pack + the untouched rng interface)."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None
    budgets = plan.budgets.model_copy(
        update={
            "note_density": note_density,
            "layers_max": layers_max,
            "register_bias": register_bias,
        }
    )
    plan = plan.model_copy(update={"budgets": budgets})
    sf = SongForm(
        sections=sections,
        total_bars=sum(s.length_bars for s in sections),
        template_id="synthetic",
    )
    ap = arrange(plan, sf, pack, _arrange_rng(plan))
    return _by_pair(ap.entries)


def test_intro_is_one_thinner_than_successor() -> None:
    """§4.1 intro: count = max(1, count(next section) − 1). An intro before a
    rung-3 chorus (count 4) resolves to 3."""
    by_pair = _arrange_synth(
        [
            _mk_section("intro", 0.90, sid="intro-1"),  # base would be 4
            _mk_section("chorus", 0.60, sid="chorus-1"),  # count 4
        ]
    )
    assert len(_active_roles(by_pair, "intro-1")) == 3
    assert len(_active_roles(by_pair, "chorus-1")) == 4


def test_intro_max_1_floor_against_thin_successor() -> None:
    """§4.1 intro: the max(1, …) floor holds when the successor is a 2-layer
    section (a rung-1 verse), giving intro count 1."""
    by_pair = _arrange_synth(
        [
            _mk_section("intro", 0.90, sid="intro-1"),
            _mk_section("verse", 0.10, sid="verse-1"),  # rung 1 → count 2
        ]
    )
    assert len(_active_roles(by_pair, "verse-1")) == 2
    assert len(_active_roles(by_pair, "intro-1")) == 1
    assert _active_roles(by_pair, "intro-1") == {"drums"}


def test_intro_no_successor_falls_back_to_own_base() -> None:
    """§4.1 edge guard: a lone intro (degenerate/fallback form) has no successor
    and falls back to its own base count — rung 2 → base 3."""
    by_pair = _arrange_synth([_mk_section("intro", 0.40, sid="intro-1")])
    assert len(_active_roles(by_pair, "intro-1")) == 3


def test_register_bias_positive_shift_and_ceiling_clamp() -> None:
    """§4.3 a large positive bias forces the highMidi ceiling: bias 0.9 →
    shift round(10.8)=+11; comping 48-71 → 59-71 (82 capped to 71), pads
    43-71 → 54-71. lowMidi unclamped, highMidi pinned at 71."""
    assert _register_for("comping", 0.9) == Register(low_midi=59, high_midi=71)
    assert _register_for("pads", 0.9) == Register(low_midi=54, high_midi=71)


def test_register_bias_negative_shift() -> None:
    """§4.3 a negative bias shifts both ends down and never touches the ceiling:
    bias −0.5 → shift −6; comping 48-71 → 42-65, pads 43-71 → 37-65."""
    assert _register_for("comping", -0.5) == Register(low_midi=42, high_midi=65)
    assert _register_for("pads", -0.5) == Register(low_midi=37, high_midi=65)


def test_register_bias_half_even_tie() -> None:
    """§4.3 shift = round(bias × 12) is half-even: bias −0.125 → round(−1.5) =
    −2 (not −1), the jazz worked value; bias +0.125 → round(1.5) = 2."""
    assert _register_for("comping", -0.125) == Register(low_midi=46, high_midi=69)
    assert _register_for("comping", 0.125) == Register(low_midi=50, high_midi=71)


def test_bass_and_drums_never_shift() -> None:
    """§4.3 bass and drums use their lane unshifted at any bias."""
    for bias in (-0.9, 0.0, 0.9):
        assert _register_for("drums", bias) == Register(low_midi=0, high_midi=127)
        assert _register_for("bass", bias) == Register(low_midi=28, high_midi=55)


def test_density_budget_identity_and_clamp() -> None:
    """§4.2 densityBudget = round(clamp01(noteDensity × (0.7 + 0.6×energy)), 3).
    At energy 0.5 the factor is 1.0 (identity on noteDensity); at the top the
    clamp pins it to 1.0."""
    # energy 0.5 → factor 1.0, so the budget is noteDensity verbatim (0.5).
    ident = _arrange_synth([_mk_section("verse", 0.5, sid="mid")], note_density=0.5)
    assert ident[("mid", "drums")].density_budget == 0.5
    # energy 1.0 → factor 1.3; noteDensity 1.0 × 1.3 = 1.3, clamped to 1.0.
    clamped = _arrange_synth([_mk_section("chorus", 1.0, sid="top")], note_density=1.0)
    assert clamped[("top", "drums")].density_budget == 1.0


def test_density_budget_half_even_tie() -> None:
    """§4.2 the 3-dp round is half-even: noteDensity 0.5625 at energy 0.5 (factor
    1.0) is an exact tie 0.5625 → 0.562 (rounds to the even digit, not 0.563)."""
    by_pair = _arrange_synth([_mk_section("verse", 0.5, sid="s")], note_density=0.5625)
    assert by_pair[("s", "drums")].density_budget == 0.562


def test_missing_layering_order_raises() -> None:
    """§4.1 a pack without a layeringOrder cannot arrange — clear error."""
    plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    pack = resolve_pack("pop_rock")
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    bad_pack = pack.model_copy(update={"layering_order": None})
    with pytest.raises(ValueError, match="layeringOrder"):
        arrange(plan, sf, bad_pack, _arrange_rng(plan))


def test_lanes_yaml_loads_and_validates() -> None:
    """`lanes.yaml` loads to the §4.3 table; every lane satisfies the folding
    invariant (span ≥ 12, 0 ≤ low < high ≤ 127)."""
    table = load_lanes_table()
    assert table.lanes == {
        "drums": (0, 127),
        "bass": (28, 55),
        "comping": (48, 71),
        "pads": (43, 71),
    }
    for low, high in table.lanes.values():
        assert 0 <= low < high <= 127
        assert high - low >= 12


# =============================================================================
# Property matrix (mirrors tests/test_form.py: every registered pack × moods ×
# lengths × 25 seeds)
# =============================================================================


@pytest.mark.parametrize(("style", "mood"), list(pack_mood_pairs()))
def test_property_valid_arrangement(style: str, mood: str) -> None:
    """PHASE_5 §13.3 — every pack × supported mood × length grid × 25 seeds
    yields an ArrangementPlan satisfying every structural invariant."""
    pack = cached_pack(style)
    forms = pack.forms
    order = pack.layering_order
    # `order` is the pack's own layering order (§5.1 role permutation), used
    # as-is everywhere below — a pack with a different permutation is legal.
    # The pinned `_ORDER` equality lives in `test_matrix_non_vacuous`.
    assert forms is not None and order is not None

    for max_len_sec in LENGTHS_PLAN:
        for seed in SEEDS_25:
            plan = build_plan(style, mood, max_len_sec, seed)
            layers_max = plan.budgets.layers_max
            sf = form(plan, forms)
            ap = arrange(plan, sf, pack, _arrange_rng(plan))
            by_pair = _by_pair(ap.entries)

            # full section×role coverage: one entry per pair, nothing extra.
            assert len(ap.entries) == len(sf.sections) * len(order)

            active_count: dict[str, int] = {}
            for section in sf.sections:
                rung = intensity(section.energy)
                active_flags = [by_pair[(section.id, r)].active for r in order]
                k = sum(active_flags)
                active_count[section.id] = k

                # active roles are exactly the first `k` of the layering order
                # (a contiguous prefix).
                assert active_flags == [True] * k + [False] * (len(order) - k)
                # active count within budgets: 1 ≤ k ≤ layersMax.
                assert 1 <= k <= layers_max

                for role in order:
                    entry = by_pair[(section.id, role)]
                    assert entry.intensity == rung
                    assert 0.0 <= entry.density_budget <= 1.0
                    assert round(entry.density_budget, 3) == entry.density_budget
                    reg = entry.register
                    assert reg.low_midi < reg.high_midi
                    if role != "drums":
                        assert reg.high_midi <= 71

            # §4.1: an intro is thinner than the section that follows it.
            for i, section in enumerate(sf.sections):
                if section.type == "intro" and i + 1 < len(sf.sections):
                    succ = sf.sections[i + 1]
                    assert active_count[section.id] < active_count[succ.id]


def test_matrix_non_vacuous() -> None:
    """The §13.3 matrix is the exact expected size and covers every pack.

    Dimensions are recomputed from pack data (not restated), so a silent shrink
    — a pack dropped from the registry, a mood lost, a truncated seed list —
    fails loudly rather than quietly narrowing coverage (ROADMAP §3)."""
    assert len(PACKS) >= 5, PACKS
    assert len(LENGTHS_PLAN) == 39, LENGTHS_PLAN
    assert len(SEEDS_25) == len(set(SEEDS_25)) == 25, SEEDS_25

    expected = total_moods()
    for style in PACKS:
        # every pack shares the pinned layering order the matrix asserts on.
        assert cached_pack(style).layering_order == _ORDER, style

    cells = list(pack_mood_pairs())
    assert len(cells) == expected, (len(cells), expected)
    assert {style for style, _ in cells} == set(PACKS)
    assert len(cells) == len(set(cells)), "duplicate (pack, mood) cell"
