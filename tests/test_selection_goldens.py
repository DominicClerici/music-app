"""§9.1 selection draw narratives + completeness property (PHASE_5 DoD 4).

The two §9.1 worked examples driven end-to-end over the real reference packs:
interpreter -> form -> `arrange` -> `select_patterns` at seed `1ps9wxb`. Every
selected pattern id and every draw count is transcribed from PHASE_5 **§9.1**
(pop 1 / jazz 3) — never read off code output (ROADMAP §3 golden-value
arbitration). A divergence between a §9.1 value and the stage output is a
bug/ambiguity to escalate, not to paper over by tuning the expected value.

Draws happen only through `weighted_choice`, so a `_CountingRandom` counting
`randrange` on each role's `select` sub-stream is the exact draw count; the
totals below sum those per-role counts. The completeness property exercises the
loader's §3.2 non-empty-eligible-set guarantee through the selection path.
"""

from __future__ import annotations

import random

import pytest

from _packmatrix import (
    PACKS,
    SEEDS_25,
    cached_pack,
    pack_mood_pairs,
    total_moods,
)
from trackgen.arrangement import arrange
from trackgen.form.stage import form
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.selection import RngFactory, SelectionResult, select_patterns
from trackgen.schema.document import Role
from trackgen.schema.ir import GenerationPlan, SongForm
from trackgen.seeds import Rng, derive, stream_seed


class _CountingRandom(random.Random):
    """A seeded RNG counting `randrange` calls — one per `weighted_choice`, hence
    one per draw (mirrors the harmony/form goldens' shim)."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


def _shims(
    master: int, overrides: dict[str, int]
) -> tuple[dict[Role, _CountingRandom], RngFactory]:
    """A per-role `rng_factory` yielding counting shims seeded at the real §3.6
    `select` stream (so draw outcomes match production), plus the dict collecting
    them so a test can sum each role's `.draws`."""
    collected: dict[Role, _CountingRandom] = {}

    def factory(role: Role) -> Rng:
        shim = _CountingRandom(derive(stream_seed(master, overrides, role), "select"))
        shim.draws = 0
        collected[role] = shim
        return shim

    return collected, factory


def _pipeline(params: dict[str, object]) -> tuple[GenerationPlan, SongForm, StylePack]:
    plan = generate_plan(params)
    style = params["styleFamily"]
    pack = resolve_pack(style)  # type: ignore[arg-type]
    assert pack is not None and pack.forms is not None
    sf = form(plan, pack.forms)
    return plan, sf, pack


def _select(
    params: dict[str, object],
) -> tuple[SelectionResult, dict[Role, _CountingRandom]]:
    plan, sf, pack = _pipeline(params)
    arrangement = arrange(plan, sf, pack, Rng(0))
    shims, factory = _shims(plan.seed.master, plan.seed.overrides)
    result = select_patterns(
        plan,
        sf,
        arrangement,
        pack,
        plan.seed.master,
        plan.seed.overrides,
        rng_factory=factory,
    )
    return result, shims


def _select_default(params: dict[str, object]) -> SelectionResult:
    """Selection over the same harness but on the PRODUCTION default path
    (`rng_factory=None`), so its `select` sub-stream derivation — not the shim's
    reconstruction — is what picks the winners. Pins that the module's own
    `default_factory` still reproduces the §9.1 ids."""
    plan, sf, pack = _pipeline(params)
    arrangement = arrange(plan, sf, pack, Rng(0))
    return select_patterns(
        plan,
        sf,
        arrangement,
        pack,
        plan.seed.master,
        plan.seed.overrides,
        rng_factory=None,
    )


# =============================================================================
# §9.1 — pop_rock / happy: 1 selection draw
# =============================================================================


def test_pop_selection_draw_narrative() -> None:
    """PHASE_5 §9.1 — pop_rock/happy at seed 1ps9wxb (C5 re-bless, session 19:
    every bank slot now holds 2 candidates, so every active slot draws once).
    Drums: intro draw {pr_dr_i, pr_dr_ib} -> `pr_dr_ib`, rung-2 draw
    {pr_dr_2a w3, pr_dr_2b w1} -> `pr_dr_2a`, rung-3 draw {pr_dr_3, pr_dr_3b} ->
    `pr_dr_3b`, rung-4 draw {pr_dr_4, pr_dr_4b} -> `pr_dr_4` (4 draws). Bass:
    intro -> `pr_bs_i`, rung-2 -> `pr_bs_2b`, rung-3 -> `pr_bs_3`, rung-4 ->
    `pr_bs_4` (4 draws). Comping rung-2/3/4 -> `pr_cp_2`/`pr_cp_3b`/`pr_cp_4`
    (3 draws). Pads rung-3/4 -> `pr_pd_3`/`pr_pd_4b` (2 draws). Thirteen draws
    total (4 + 4 + 3 + 2)."""
    result, shims = _select({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    by_section = result.by_section
    by_key = result.by_key

    # Drums: the §9.1 selections, keyed at (role, kind, rung).
    assert by_section[("intro-1", "drums")].id == "pr_dr_ib"  # intro draw winner
    assert by_key[("drums", "main", 2)].id == "pr_dr_2a"  # weighted_choice winner
    assert by_key[("drums", "main", 3)].id == "pr_dr_3b"  # rung-3 draw winner
    assert by_key[("drums", "main", 4)].id == "pr_dr_4"  # rung-4 draw winner
    # Same-rung sections share the groove (cache-once): verse-1 ≡ verse-2 ≡ bridge.
    assert by_section[("verse-1", "drums")].id == "pr_dr_2a"
    assert by_section[("verse-2", "drums")].id == "pr_dr_2a"
    assert by_section[("bridge-1", "drums")].id == "pr_dr_2a"
    assert by_section[("chorus-1", "drums")].id == "pr_dr_3b"
    assert by_section[("chorus-2", "drums")].id == "pr_dr_4"
    assert by_section[("chorus-3", "drums")].id == "pr_dr_4"

    # Bass/comping/pads: each slot now a 2-candidate draw.
    assert by_section[("intro-1", "bass")].id == "pr_bs_i"
    assert by_section[("verse-1", "bass")].id == "pr_bs_2b"
    assert by_section[("chorus-1", "bass")].id == "pr_bs_3"
    assert by_section[("chorus-2", "bass")].id == "pr_bs_4"
    assert by_section[("verse-1", "comping")].id == "pr_cp_2"
    assert by_section[("chorus-1", "comping")].id == "pr_cp_3b"
    assert by_section[("chorus-2", "comping")].id == "pr_cp_4"
    assert by_section[("chorus-1", "pads")].id == "pr_pd_3"
    assert by_section[("chorus-2", "pads")].id == "pr_pd_4b"

    # Thirteen selection draws: drums 4 + bass 4 + comping 3 + pads 2.
    assert sum(shim.draws for shim in shims.values()) == 13
    assert shims["drums"].draws == 4
    assert shims["bass"].draws == 4
    assert shims["comping"].draws == 3
    assert shims["pads"].draws == 2

    # Production default path (rng_factory=None) picks the same §9.1 winners:
    # golden-locks the module's own `select` derivation, not just the shim's.
    default = _select_default({"styleFamily": "pop_rock", "seed": "1ps9wxb"})
    assert default.by_section[("intro-1", "drums")].id == "pr_dr_ib"
    assert default.by_key[("drums", "main", 2)].id == "pr_dr_2a"
    assert default.by_key[("drums", "main", 3)].id == "pr_dr_3b"
    assert default.by_key[("drums", "main", 4)].id == "pr_dr_4"


# =============================================================================
# §9.1 — jazz / melancholic: 3 selection draws
# =============================================================================


def test_jazz_selection_draw_narrative() -> None:
    """PHASE_5 §9.1 — jazz/melancholic at seed 1ps9wxb (C5 re-bless, session 19:
    every bank slot now holds 2 candidates). Drums: rung-2 draw {jz_dr_2,
    jz_dr_2b} -> `jz_dr_2b`, rung-3 draw {jz_dr_3a w3, jz_dr_3b w2} -> `jz_dr_3a`,
    ending draw {jz_dr_e, jz_dr_eb} -> `jz_dr_eb` (3 draws). Comping: rung-2 draw
    {jz_cp_2a w3, jz_cp_2b w2} -> `jz_cp_2a`, rung-3 draw {jz_cp_3a w3, jz_cp_3b
    w2} -> `jz_cp_3a`, ending draw {jz_cp_e, jz_cp_eb} -> `jz_cp_e` (3 draws).
    Bass is walking (no selection); pads never active. Six draws total (drums 3 +
    comping 3)."""
    result, shims = _select(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    by_section = result.by_section
    by_key = result.by_key

    # Drums.
    assert by_key[("drums", "main", 2)].id == "jz_dr_2b"  # rung-2 draw winner
    assert by_key[("drums", "main", 3)].id == "jz_dr_3a"  # weighted_choice winner
    assert by_section[("outro-1", "drums")].id == "jz_dr_eb"  # kind: ending draw
    assert by_section[("head-1", "drums")].id == "jz_dr_2b"
    assert by_section[("solo-1", "drums")].id == "jz_dr_3a"
    assert by_section[("solo-2", "drums")].id == "jz_dr_3a"
    assert by_section[("solo-3", "drums")].id == "jz_dr_3a"
    assert by_section[("head-2", "drums")].id == "jz_dr_2b"

    # Comping.
    assert by_key[("comping", "main", 2)].id == "jz_cp_2a"  # Charleston winner
    assert by_key[("comping", "main", 3)].id == "jz_cp_3a"  # winner
    assert by_section[("outro-1", "comping")].id == "jz_cp_e"  # kind: ending draw
    assert by_section[("head-1", "comping")].id == "jz_cp_2a"
    assert by_section[("solo-1", "comping")].id == "jz_cp_3a"

    # Bass is walking-mode → no pattern selection, no bass/select stream built.
    assert not any(role == "bass" for (_sid, role) in by_section)
    assert not any(role == "bass" for (role, _k, _r) in by_key)
    assert "bass" not in shims

    # Pads never active under layersMax 3 (the trio) → no pads selection/stream.
    assert not any(role == "pads" for (_sid, role) in by_section)
    assert not any(role == "pads" for (role, _k, _r) in by_key)
    assert "pads" not in shims

    # Exactly six selection draws: drums 3 (rung 2, rung 3, ending) + comping 3
    # (rung 2, rung 3, ending).
    assert sum(shim.draws for shim in shims.values()) == 6
    assert shims["drums"].draws == 3
    assert shims["comping"].draws == 3

    # Production default path (rng_factory=None) picks the same §9.1 winners, and
    # walking-mode bass / dormant pads still yield no entries. Golden-locks the
    # module's own `select` derivation, not just the shim's reconstruction.
    default = _select_default(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    assert default.by_key[("drums", "main", 2)].id == "jz_dr_2b"
    assert default.by_key[("drums", "main", 3)].id == "jz_dr_3a"
    assert default.by_key[("comping", "main", 2)].id == "jz_cp_2a"
    assert default.by_key[("comping", "main", 3)].id == "jz_cp_3a"
    assert default.by_section[("outro-1", "drums")].id == "jz_dr_eb"
    assert default.by_section[("outro-1", "comping")].id == "jz_cp_e"
    assert not any(role == "bass" for (_sid, role) in default.by_section)
    assert not any(role == "bass" for (role, _k, _r) in default.by_key)
    assert not any(role == "pads" for (_sid, role) in default.by_section)
    assert not any(role == "pads" for (role, _k, _r) in default.by_key)


# =============================================================================
# DoD 4 — completeness property: every reachable key resolves
# =============================================================================

# The §14.9 pack × mood matrix, taken from `_packmatrix` so the pack dimension
# is derived from the registry rather than restated here. This module was written
# when only two packs existed and its comment said "mirror test_form.py's
# pack×mood matrix"; test_form.py was widened to five packs in SESSION_23 T5 and
# this module was missed, so the mirror broke silently and DoD §14.9 was unmet
# (SESSION_23 T10, lens B). A tempo spread covering each pack's tempoRange
# exercises the loader's §3.2 completeness guarantee through the selection path
# (no reference pattern is tempo-gated, so every reachable key must resolve at
# every tempo).
#
# Seeds: the full §14.9 25-seed set. Measured cost of the widening (2 packs × 5
# seeds → 5 packs × 25 seeds, i.e. 21 → 45 cells and 525 → 5625 pipelines):
# 0.9 s → 8.4 s serial, ~2 s under `pytest -n auto`. Affordable, so §14.9's seed
# depth is honoured rather than approximated.


def _tempo_spread(pack: StylePack) -> list[int]:
    """Five tempi evenly spanning the pack's tempoRange (endpoints included)."""
    lo, hi = pack.manifest.tempo_range
    return [round(lo + (hi - lo) * i / 4) for i in range(5)]


@pytest.mark.parametrize(("style", "mood"), pack_mood_pairs())
def test_selection_completeness(style: str, mood: str) -> None:
    """PHASE_5 DoD 4 — for every registered pack × supported mood × tempo across
    its range × the 25-seed spread, every reachable `(role, kind, rung)` (an
    active, pattern-mode `(section, role)`) resolves to a pattern:
    `select_patterns` populates a `by_section` entry for it and never comes up
    empty / never raises."""
    pack = cached_pack(style)
    assert pack.forms is not None
    walking_bass = pack.bass_mode == "walking"

    for tempo in _tempo_spread(pack):
        for seed in SEEDS_25:
            plan = generate_plan(
                {
                    "styleFamily": style,
                    "mood": mood,
                    "tempoBpm": tempo,
                    "seed": seed,
                }
            )
            sf = form(plan, pack.forms)
            arrangement = arrange(plan, sf, pack, Rng(0))
            result = select_patterns(
                plan,
                sf,
                arrangement,
                pack,
                plan.seed.master,
                plan.seed.overrides,
            )

            ctx = (style, mood, tempo, seed)
            reachable = {
                (entry.section_id, entry.role)
                for entry in arrangement.entries
                if entry.active and not (entry.role == "bass" and walking_bass)
            }
            # Every reachable pair resolves.
            assert reachable, ctx
            for pair in reachable:
                assert pair in result.by_section, (ctx, pair)
                assert result.by_section[pair] is not None, (ctx, pair)
            # No spurious selections beyond the reachable set.
            assert set(result.by_section) == reachable, ctx


def test_matrix_non_vacuous() -> None:
    """The DoD-4 completeness matrix is the exact expected size and covers every
    registered pack.

    Dimensions are recomputed from pack data (not restated), so a silent shrink —
    a pack dropped from the registry, a mood lost, a truncated seed list — fails
    loudly rather than quietly narrowing coverage (ROADMAP §3). This test exists
    because the shrink it guards against already happened once: the matrix sat at
    two packs for three chunks after `test_form.py` was widened to five."""
    assert len(PACKS) >= 5, PACKS
    assert len(SEEDS_25) == len(set(SEEDS_25)) == 25, SEEDS_25

    cells = list(pack_mood_pairs())
    assert len(cells) == total_moods(), (len(cells), total_moods())
    assert {style for style, _ in cells} == set(PACKS)
    assert len(cells) == len(set(cells)), "duplicate (pack, mood) cell"

    # The tempo dimension is real per pack: five distinct tempi spanning a
    # non-degenerate tempoRange, so "× tempo across its range" is not one value.
    for style in PACKS:
        spread = _tempo_spread(cached_pack(style))
        assert len(spread) == 5, (style, spread)
        assert len(set(spread)) == 5, (style, spread)
        assert spread[0] < spread[-1], (style, spread)

    # Both bass modes are exercised: walking bass takes a different completeness
    # path (no selection), and pinning the split here keeps a pack that silently
    # flips mode from narrowing what this property covers.
    modes = {style: cached_pack(style).bass_mode for style in PACKS}
    assert modes == {
        "blues": "patterns",
        "chill_lofi": "patterns",
        "fusion_jazz": "patterns",
        "jazz": "walking",
        "pop_rock": "patterns",
    }, modes
