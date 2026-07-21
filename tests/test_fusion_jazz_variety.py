"""fusion_jazz reroll-variety coverage (SESSION_22 T5, §9.2, C5/C6/C7 M1
convention).

Every `(role, kind, rung)` slot the arrangement can route is a >= 2-candidate
draw. The S22-5 dormancy makes a large share of the bank golden-blind:

- **rung 1 is dead grid-wide** — the lowest reachable pre-envelope energy is
  0.185, above rung 1's 0.1333 ceiling, so no rung-1 key is ever selected for
  any role in any render;
- **rung 4 is `tune`-template-only** (`vamp` maxes at energy 0.710);
- intro/ending and every weight-2 sibling are blind to the pinned §8.2 corpus
  triple.

None of that is lint-visible (`_reachable_rungs` reads only the [0.20, 0.95]
envelope, so all four rungs look reachable), so the production draw primitive
`_draw(_eligible_set(...), select-stream rng)` is these candidates' ONLY
mechanical selection coverage. That is what this module supplies.

Three executable guarantees:

`test_every_slot_has_two_ungated_candidates` / `test_every_slot_clears_variety_floor`
— the executable form of the (never-raised, because the pack was authored thick)
`variety-coverage` lint: >= 2 UNGATED candidates per slot, and >= 2 candidates
surviving every gate at every supported `(mood, tempo)` cell.

`test_candidate_wins_its_draw` — per candidate id, a locked master seed under
which the exact production draw selects it. fusion authors NO tempo gate
anywhere (unlike blues' [50, 75] slow band), so a single locked tempo inside
every mood window suffices.

Determinism (ROADMAP invariant 5): every seed is a pinned literal found by fixed
enumeration; all RNG flows through `trackgen.seeds`; no `random`/`time`/
`datetime` import (TID251).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from trackgen.packs.lint import _active_roles, _mood_windows
from trackgen.packs.loader import load_pack
from trackgen.packs.models import PatternKind
from trackgen.parts.selection import _draw, _eligible_set
from trackgen.schema.document import Role
from trackgen.seeds import Rng, derive, stream_seed

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "fusion_jazz"

# The six variety-linted slots per role (fills are Phase-6-owned, not linted).
_SLOTS: tuple[tuple[str, int], ...] = (
    ("main", 1),
    ("main", 2),
    ("main", 3),
    ("main", 4),
    ("intro", 1),
    ("ending", 1),
)

# Inside every fusion mood window (energetic 126-145 · calm 75-84 · mysterious
# 79-97 · dreamy 75-91 · nostalgic 78-95 · triumphant 113-138 · happy 106-130 ·
# tense 111-135). Every entry is ungated, so the eligible set is tempo-invariant
# and this value only has to be a legal tempo.
_TEMPO = 120.0


# --- (a) variety floors -------------------------------------------------------


def test_every_slot_has_two_ungated_candidates() -> None:
    """The fusion variety contract (SESSION_22 constraint 9): every
    `(role, kind, rung)` slot has >= 2 UNGATED candidates, `bass` included
    (fusion is `mode: patterns`, so bass is a linted role)."""
    pack = load_pack(str(_PACK_DIR))
    thin: list[str] = []
    for role in ("drums", "bass", "comping", "pads"):
        for kind, rung in _SLOTS:
            ungated = [
                e
                for e in pack.patterns[role]
                if e.kind == kind
                and (kind != "main" or e.energy_level == rung)
                and e.eligibility.tempo_bpm is None
            ]
            if len(ungated) < 2:
                thin.append(f"{role}/{kind}/rung{rung}: {[e.id for e in ungated]}")
    assert not thin, "slots below the ungated variety floor:\n" + "\n".join(thin)


def test_every_slot_clears_variety_floor() -> None:
    """>= 2 candidates survive every gate at every supported `(mood, tempo)` cell,
    for every `(role, kind, rung)` slot — mirroring `_warn_variety_coverage`."""
    pack = load_pack(str(_PACK_DIR))
    windows = _mood_windows(pack)
    assert windows, "no supported (mood, tempo) windows resolved"

    thin: list[str] = []
    for role in _active_roles(pack):
        for kind, rung in _SLOTS:
            for mood, lo, hi in windows:
                for tempo in range(lo, hi + 1):
                    survivors = len(
                        _eligible_set(pack, role, cast(PatternKind, kind), rung, tempo)
                    )
                    if survivors < 2:
                        thin.append(
                            f"{role}/{kind}/rung{rung} @ mood={mood} tempo={tempo}: "
                            f"{survivors}"
                        )
    assert not thin, "slots below the variety floor:\n" + "\n".join(thin)


# --- (b) per-candidate locked draw-winner seed --------------------------------

# (role, kind, rung, target_id, master_seed). Discovered by fixed enumeration of
# the `select` sub-stream. Every candidate id in the four banks' main/intro/
# ending slots is covered — including the whole dormant rung-1 tier and the
# `tune`-only rung 4, which no corpus cell can reach.
_DRAW_CASES: tuple[tuple[str, str, int, str, int], ...] = (
    # bass
    ("bass", "ending", 1, "fu_bs_e", 0),
    ("bass", "ending", 1, "fu_bs_eb", 6),
    ("bass", "intro", 1, "fu_bs_i", 0),
    ("bass", "intro", 1, "fu_bs_ib", 6),
    ("bass", "main", 1, "fu_bs_1", 0),
    ("bass", "main", 1, "fu_bs_1b", 6),
    ("bass", "main", 2, "fu_bs_2", 0),  # the S22-11 tresillo anchor
    ("bass", "main", 2, "fu_bs_2b", 6),  # the S22-11 printed-continuation sibling
    ("bass", "main", 3, "fu_bs_3", 0),
    ("bass", "main", 3, "fu_bs_3b", 6),
    ("bass", "main", 4, "fu_bs_4", 0),
    ("bass", "main", 4, "fu_bs_4b", 6),
    # comping
    ("comping", "ending", 1, "fu_cp_e", 0),
    ("comping", "ending", 1, "fu_cp_eb", 4),
    ("comping", "intro", 1, "fu_cp_i", 0),
    ("comping", "intro", 1, "fu_cp_ib", 4),
    ("comping", "main", 1, "fu_cp_1", 0),
    ("comping", "main", 1, "fu_cp_1b", 4),
    ("comping", "main", 2, "fu_cp_2", 0),
    ("comping", "main", 2, "fu_cp_2b", 4),
    ("comping", "main", 3, "fu_cp_3", 0),
    ("comping", "main", 3, "fu_cp_3b", 4),
    ("comping", "main", 4, "fu_cp_4", 0),
    ("comping", "main", 4, "fu_cp_4b", 4),
    # drums
    ("drums", "ending", 1, "fu_dr_e", 0),
    ("drums", "ending", 1, "fu_dr_eb", 10),
    ("drums", "intro", 1, "fu_dr_i", 0),
    ("drums", "intro", 1, "fu_dr_ib", 10),
    ("drums", "main", 1, "fu_dr_1", 0),
    ("drums", "main", 1, "fu_dr_1b", 10),
    ("drums", "main", 2, "fu_dr_2", 0),  # the §6.4 defining entry
    ("drums", "main", 2, "fu_dr_2b", 10),
    ("drums", "main", 3, "fu_dr_3", 0),
    ("drums", "main", 3, "fu_dr_3b", 10),  # the displaced backbeat
    ("drums", "main", 4, "fu_dr_4", 0),
    ("drums", "main", 4, "fu_dr_4b", 10),
    # pads
    ("pads", "ending", 1, "fu_pd_e", 1),
    ("pads", "ending", 1, "fu_pd_eb", 0),
    ("pads", "intro", 1, "fu_pd_i", 1),
    ("pads", "intro", 1, "fu_pd_ib", 0),
    ("pads", "main", 1, "fu_pd_1", 1),
    ("pads", "main", 1, "fu_pd_1b", 0),
    ("pads", "main", 2, "fu_pd_2", 1),
    ("pads", "main", 2, "fu_pd_2b", 0),
    ("pads", "main", 3, "fu_pd_3", 1),
    ("pads", "main", 3, "fu_pd_3b", 0),
    ("pads", "main", 4, "fu_pd_4", 1),
    ("pads", "main", 4, "fu_pd_4b", 0),
)


@pytest.mark.parametrize(
    ("role", "kind", "rung", "target_id", "master"),
    _DRAW_CASES,
    ids=[c[3] for c in _DRAW_CASES],
)
def test_candidate_wins_its_draw(
    role: str, kind: str, rung: int, target_id: str, master: int
) -> None:
    """The production draw primitive selects `target_id` under a locked master
    seed — the exact `_draw`/`_eligible_set` path `select_patterns` uses, on the
    role's `select` sub-stream `Rng(derive(stream_seed(master, {}, role), sel))`."""
    pack = load_pack(str(_PACK_DIR))
    eligible = _eligible_set(
        pack, cast(Role, role), cast(PatternKind, kind), rung, _TEMPO
    )
    assert len(eligible) >= 2, f"{role}/{kind}/rung{rung} is not a real draw"
    assert target_id in {p.id for p in eligible}, (
        f"{target_id} not eligible at {role}/{kind}/rung{rung}@{_TEMPO}: "
        f"{[p.id for p in eligible]}"
    )
    rng = Rng(derive(stream_seed(master, {}, role), "select"))
    chosen = _draw(eligible, rng)
    assert chosen.id == target_id, (
        f"{role}/{kind}/rung{rung} @ master {master} chose {chosen.id}, "
        f"expected {target_id} (candidates {[p.id for p in eligible]})"
    )


def test_draw_cases_cover_every_bank_candidate() -> None:
    """The parametrization covers exactly the 48 main/intro/ending candidate ids
    across the four banks — both members of all 24 variety pairs — nothing
    missing or duplicated (fills excluded: Phase-6-owned, not variety-linted)."""
    covered = [c[3] for c in _DRAW_CASES]
    assert len(covered) == len(set(covered)) == 48

    pack = load_pack(str(_PACK_DIR))
    bank_ids = {
        e.id
        for role in ("drums", "bass", "comping", "pads")
        for e in pack.patterns[role]
        if e.kind in ("main", "intro", "ending")
    }
    assert set(covered) == bank_ids
