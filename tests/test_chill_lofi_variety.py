"""chill_lofi reroll-variety coverage (SESSION_20 T5, §9.2, C5 M1 convention).

Every one of the 24 variety-linted slots (drums/bass/comping/pads x {main 1-4,
intro, ending}) is a 3/2 weighted candidate pair. Two executable guarantees:

`test_every_slot_has_two_eligible_candidates` — the executable form of the (never
raised, because this pack was authored thick) `variety-coverage` warning: >= 2
candidates survive every gate at every supported `(mood, tempo)` cell, using the
exact `_eligible_set` primitive the lint's `_warn_variety_coverage` uses.

`test_candidate_wins_its_draw` — per candidate id (both the primary AND the
sibling, including the golden-blind rung-4 / intro / ending ones the 0.60 energy
ceiling or arrangement routing never reaches), a locked master seed under which
the exact production draw primitive `_draw(_eligible_set(...), select-stream rng)`
selects it. Rung-4 mains are unreachable in render (energy ceiling), so this is
their only mechanical selection coverage.

Determinism (ROADMAP invariant 5): every seed is a pinned literal found by fixed
enumeration; all RNG flows through `trackgen.seeds`; no `random`/`time`/`datetime`
import (TID251).
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

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "chill_lofi"

# The six variety-linted slots per role (fills are Phase-6-owned, not linted).
_SLOTS: tuple[tuple[str, int], ...] = (
    ("main", 1),
    ("main", 2),
    ("main", 3),
    ("main", 4),
    ("intro", 1),
    ("ending", 1),
)


# --- (c1) every slot clears the variety floor at every (mood, tempo) cell -----


def test_every_slot_has_two_eligible_candidates() -> None:
    """>= 2 candidates survive every gate at every supported `(mood, tempo)`
    cell, for every `(role, kind, rung)` slot — mirroring `_warn_variety_coverage`."""
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


# --- (c2) per-candidate locked draw-winner seed -------------------------------

# The draw is a `weighted_choice` over the authored `[primary, sibling]` pair with
# weights `[3, 2]` on the role's `select` sub-stream. The winning seed therefore
# depends only on `(role, winner-slot)`, not the (kind, rung) — but every id is
# pinned individually so any future bank reorder / id rename trips the suite
# (weight flips are guarded separately by test_sibling_weights_are_3_2_every_slot).
# Discovered by fixed enumeration (0..399).
_WINNER_SEED: dict[tuple[str, str], int] = {
    ("drums", "primary"): 0,
    ("drums", "sibling"): 10,
    ("bass", "primary"): 0,
    ("bass", "sibling"): 6,
    ("comping", "primary"): 0,
    ("comping", "sibling"): 4,
    ("pads", "primary"): 1,
    ("pads", "sibling"): 0,
}

_PREFIX: dict[str, str] = {
    "drums": "lf_dr",
    "bass": "lf_bs",
    "comping": "lf_cp",
    "pads": "lf_pd",
}

# All patterns are tempo-ungated, so any supported tempo yields the full pair.
_TEMPO = 82.0


def _slot_suffix(kind: str, rung: int) -> str:
    if kind == "main":
        return str(rung)
    if kind == "intro":
        return "i"
    return "e"  # ending


def _draw_cases() -> list[tuple[str, str, int, str, int]]:
    """(role, kind, rung, target_id, master_seed) for every candidate id."""
    cases: list[tuple[str, str, int, str, int]] = []
    for role, prefix in _PREFIX.items():
        for kind, rung in _SLOTS:
            base = f"{prefix}_{_slot_suffix(kind, rung)}"
            cases.append((role, kind, rung, base, _WINNER_SEED[(role, "primary")]))
            cases.append(
                (role, kind, rung, base + "b", _WINNER_SEED[(role, "sibling")])
            )
    return cases


_DRAW_CASES = _draw_cases()


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
    assert len(eligible) == 2, f"{role}/{kind}/rung{rung} is not a 2-candidate draw"
    rng = Rng(derive(stream_seed(master, {}, role), "select"))
    chosen = _draw(eligible, rng)
    assert chosen.id == target_id, (
        f"{role}/{kind}/rung{rung} @ master {master} chose {chosen.id}, "
        f"expected {target_id} (candidates {[p.id for p in eligible]})"
    )


def test_draw_cases_cover_all_48_candidate_ids() -> None:
    """The parametrization covers exactly the 48 variety-slot candidate ids —
    both members of all 24 slots, nothing missing or duplicated."""
    ids = [c[3] for c in _DRAW_CASES]
    assert len(ids) == len(set(ids)) == 48
