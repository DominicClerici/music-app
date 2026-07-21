"""blues reroll-variety coverage (SESSION_21 T5, §9.2, C5/C6 M1 convention).

Every `(role, kind, rung)` slot the arrangement can route is a >= 2-candidate
draw; the S21-2 dormancy makes the rung-1/rung-2 mains and the intro/ending/
sibling slots golden-blind (never selected by a rendered corpus cell), so the
production draw primitive `_draw(_eligible_set(...), select-stream rng)` is their
only mechanical selection coverage.

Three executable guarantees:

`test_every_slot_has_two_ungated_candidates` / `test_every_slot_clears_variety_floor`
— the executable form of the (never-raised, because the pack was authored thick)
`variety-coverage` lint: >= 2 UNGATED candidates per slot, and >= 2 candidates
surviving every gate at every supported `(mood, tempo)` cell.

`test_candidate_wins_its_draw` — per candidate id (primary, sibling, AND the five
tempo-gated slow-blues bonus entries), a locked master seed under which the exact
production draw selects it. Ungated candidates are locked at 130 BPM (the gated
band is excluded there, giving the clean variety pair); the gated bonus entries
are locked at 70 BPM (inside the [50, 75] band, where they join the eligible set).

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

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "blues"

# The six variety-linted slots per role (fills are Phase-6-owned, not linted).
_SLOTS: tuple[tuple[str, int], ...] = (
    ("main", 1),
    ("main", 2),
    ("main", 3),
    ("main", 4),
    ("intro", 1),
    ("ending", 1),
)

# A tempo outside the [50, 75] gated band: the eligible set here is the pair of
# ungated variety candidates (the gated slow-blues entries are excluded).
_UNGATED_TEMPO = 130.0
# A tempo inside the [50, 75] gated band: the eligible set grows to include the
# gated bonus entries.
_GATED_TEMPO = 70.0


# --- (a) variety floors -------------------------------------------------------


def test_every_slot_has_two_ungated_candidates() -> None:
    """The blues variety contract (constraint 4): every `(role, kind, rung)` slot
    has >= 2 UNGATED candidates — the tempo-gated slow-blues entries are bonus and
    do NOT count toward variety at the energetic/aggressive cells where they gate
    out."""
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

# (role, kind, rung, target_id, tempo, master_seed). Discovered by fixed
# enumeration of the `select` sub-stream. Every candidate id in the four banks'
# main/intro/ending slots is covered, including the five tempo-gated bonus entries
# (locked at 70 BPM, inside the [50, 75] band).
_DRAW_CASES: tuple[tuple[str, str, int, str, float, int], ...] = (
    # bass
    ("bass", "ending", 1, "bl_bs_e", _UNGATED_TEMPO, 0),
    ("bass", "ending", 1, "bl_bs_eb", _UNGATED_TEMPO, 6),
    ("bass", "intro", 1, "bl_bs_i", _UNGATED_TEMPO, 0),
    ("bass", "intro", 1, "bl_bs_ib", _UNGATED_TEMPO, 6),
    ("bass", "main", 1, "bl_bs_1", _UNGATED_TEMPO, 0),
    ("bass", "main", 1, "bl_bs_1b", _UNGATED_TEMPO, 6),
    ("bass", "main", 2, "bl_bs_2", _UNGATED_TEMPO, 0),
    ("bass", "main", 2, "bl_bs_2b", _UNGATED_TEMPO, 6),
    ("bass", "main", 3, "bl_bs_3", _UNGATED_TEMPO, 13),  # pinned boogie (weight 1)
    ("bass", "main", 3, "bl_bs_3b", _UNGATED_TEMPO, 0),  # box (weight 3)
    ("bass", "main", 3, "bl_bs_3s", _GATED_TEMPO, 0),  # gated triplet arpeggio
    ("bass", "main", 3, "bl_bs_3sb", _GATED_TEMPO, 9),  # gated triplet arpeggio
    ("bass", "main", 4, "bl_bs_4", _UNGATED_TEMPO, 0),
    ("bass", "main", 4, "bl_bs_4b", _UNGATED_TEMPO, 6),
    # comping
    ("comping", "ending", 1, "bl_cp_e", _UNGATED_TEMPO, 0),
    ("comping", "ending", 1, "bl_cp_eb", _UNGATED_TEMPO, 4),
    ("comping", "intro", 1, "bl_cp_i", _UNGATED_TEMPO, 0),
    ("comping", "intro", 1, "bl_cp_ib", _UNGATED_TEMPO, 4),
    ("comping", "main", 1, "bl_cp_1", _UNGATED_TEMPO, 0),
    ("comping", "main", 1, "bl_cp_1b", _UNGATED_TEMPO, 4),
    ("comping", "main", 2, "bl_cp_2", _UNGATED_TEMPO, 0),
    ("comping", "main", 2, "bl_cp_2b", _UNGATED_TEMPO, 4),
    ("comping", "main", 3, "bl_cp_3", _UNGATED_TEMPO, 0),
    ("comping", "main", 3, "bl_cp_3b", _UNGATED_TEMPO, 4),
    ("comping", "main", 3, "bl_cp_3s", _GATED_TEMPO, 0),  # gated triplet-roll
    ("comping", "main", 4, "bl_cp_4", _UNGATED_TEMPO, 0),
    ("comping", "main", 4, "bl_cp_4b", _UNGATED_TEMPO, 4),
    # drums
    ("drums", "ending", 1, "bl_dr_e", _UNGATED_TEMPO, 0),
    ("drums", "ending", 1, "bl_dr_eb", _UNGATED_TEMPO, 10),
    ("drums", "intro", 1, "bl_dr_i", _UNGATED_TEMPO, 0),
    ("drums", "intro", 1, "bl_dr_ib", _UNGATED_TEMPO, 10),
    ("drums", "main", 1, "bl_dr_1", _UNGATED_TEMPO, 0),
    ("drums", "main", 1, "bl_dr_1b", _UNGATED_TEMPO, 10),
    ("drums", "main", 2, "bl_dr_lc", _UNGATED_TEMPO, 0),
    ("drums", "main", 2, "bl_dr_lcb", _UNGATED_TEMPO, 10),
    ("drums", "main", 3, "bl_dr_2", _UNGATED_TEMPO, 0),  # pinned Chicago shuffle
    ("drums", "main", 3, "bl_dr_3b", _UNGATED_TEMPO, 10),
    ("drums", "main", 3, "bl_dr_3s", _GATED_TEMPO, 8),  # gated slow-blues 12/8
    ("drums", "main", 3, "bl_dr_3sb", _GATED_TEMPO, 11),  # gated slow-blues 12/8
    ("drums", "main", 4, "bl_dr_4", _UNGATED_TEMPO, 0),
    ("drums", "main", 4, "bl_dr_4b", _UNGATED_TEMPO, 10),
    # pads
    ("pads", "ending", 1, "bl_pd_e", _UNGATED_TEMPO, 1),
    ("pads", "ending", 1, "bl_pd_eb", _UNGATED_TEMPO, 0),
    ("pads", "intro", 1, "bl_pd_i", _UNGATED_TEMPO, 1),
    ("pads", "intro", 1, "bl_pd_ib", _UNGATED_TEMPO, 0),
    ("pads", "main", 1, "bl_pd_1", _UNGATED_TEMPO, 1),
    ("pads", "main", 1, "bl_pd_1b", _UNGATED_TEMPO, 0),
    ("pads", "main", 2, "bl_pd_2", _UNGATED_TEMPO, 1),
    ("pads", "main", 2, "bl_pd_2b", _UNGATED_TEMPO, 0),
    ("pads", "main", 3, "bl_pd_3", _UNGATED_TEMPO, 1),
    ("pads", "main", 3, "bl_pd_3b", _UNGATED_TEMPO, 0),
    ("pads", "main", 4, "bl_pd_4", _UNGATED_TEMPO, 1),
    ("pads", "main", 4, "bl_pd_4b", _UNGATED_TEMPO, 0),
)


@pytest.mark.parametrize(
    ("role", "kind", "rung", "target_id", "tempo", "master"),
    _DRAW_CASES,
    ids=[c[3] for c in _DRAW_CASES],
)
def test_candidate_wins_its_draw(
    role: str, kind: str, rung: int, target_id: str, tempo: float, master: int
) -> None:
    """The production draw primitive selects `target_id` under a locked master
    seed — the exact `_draw`/`_eligible_set` path `select_patterns` uses, on the
    role's `select` sub-stream `Rng(derive(stream_seed(master, {}, role), sel))`."""
    pack = load_pack(str(_PACK_DIR))
    eligible = _eligible_set(
        pack, cast(Role, role), cast(PatternKind, kind), rung, tempo
    )
    assert len(eligible) >= 2, f"{role}/{kind}/rung{rung} is not a real draw"
    assert target_id in {p.id for p in eligible}, (
        f"{target_id} not eligible at {role}/{kind}/rung{rung}@{tempo}: "
        f"{[p.id for p in eligible]}"
    )
    rng = Rng(derive(stream_seed(master, {}, role), "select"))
    chosen = _draw(eligible, rng)
    assert chosen.id == target_id, (
        f"{role}/{kind}/rung{rung} @ master {master} chose {chosen.id}, "
        f"expected {target_id} (candidates {[p.id for p in eligible]})"
    )


def test_draw_cases_cover_every_bank_candidate() -> None:
    """The parametrization covers exactly the 53 main/intro/ending candidate ids
    across the four banks — both members of every variety pair plus the five
    tempo-gated bonus entries — nothing missing or duplicated (fills excluded:
    Phase-6-owned, not variety-linted)."""
    covered = [c[3] for c in _DRAW_CASES]
    assert len(covered) == len(set(covered)) == 53

    pack = load_pack(str(_PACK_DIR))
    bank_ids = {
        e.id
        for role in ("drums", "bass", "comping", "pads")
        for e in pack.patterns[role]
        if e.kind in ("main", "intro", "ending")
    }
    assert set(covered) == bank_ids
