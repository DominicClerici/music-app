"""Jazz reference-bank reroll variety (SESSION_19 T2; PHASE_5 §3.2, §9.2).

Locks the 15 second candidates T2 authored to clear every `variety-coverage`
warning on `styles/jazz/` — drums main r1/r2/r4 + intro + ending, comping main
r1/r4 + intro + ending, pads main r1-4 + intro + ending. Jazz bass is
`mode: walking` (variety-exempt) so it is not covered here.

Coverage strategy (C-20): rung-1 mains, most pads slots, and the intro/ending
slots are GOLDEN-BLIND — the 24-cell corpus never selects them, so these tests
are their only mechanical coverage. Render-reachable new ids are pinned to a
`(mood, seed)` that selects them in a full render whose `validate_pipeline` is
clean; render-unreachable (blind) ids are pinned to the `Rng` index at which
`weighted_choice` first draws them from their eligible set (the only mechanism
available when no render reaches the slot).

Deterministic / TID251-clean: fixed base36 seeds and integer `Rng` indices only
— no `random`, no clock.
"""

from __future__ import annotations

from typing import cast

import pytest

from trackgen.packs import resolve_pack
from trackgen.packs.lint import _warn_variety_coverage
from trackgen.packs.models import PatternEnvelope, PatternKind, StylePack
from trackgen.parts.selection import _draw, _eligible_set
from trackgen.pipeline.trace import generate_trace
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.document import Role
from trackgen.seeds import Rng

_PACK = "jazz"

# (role, kind, rung) -> the 2nd candidate T2 added. rung is a dummy 1 for
# intro/ending (energy-insensitive, §3.2).
_NEW_BY_SLOT: dict[tuple[str, str, int], str] = {
    ("drums", "main", 1): "jz_dr_1b",
    ("drums", "main", 2): "jz_dr_2b",
    ("drums", "main", 4): "jz_dr_4b",
    ("drums", "intro", 1): "jz_dr_ib",
    ("drums", "ending", 1): "jz_dr_eb",
    ("comping", "main", 1): "jz_cp_1b",
    ("comping", "main", 4): "jz_cp_4b",
    ("comping", "intro", 1): "jz_cp_ib",
    ("comping", "ending", 1): "jz_cp_eb",
    ("pads", "main", 1): "jz_pd_1b",
    ("pads", "main", 2): "jz_pd_2b",
    ("pads", "main", 3): "jz_pd_3b",
    ("pads", "main", 4): "jz_pd_4b",
    ("pads", "intro", 1): "jz_pd_ib",
    ("pads", "ending", 1): "jz_pd_eb",
}

# The pre-existing ids that must survive untouched (golden anchors incl. jz_dr_2,
# jz_cp_2a, jz_dr_3a/3b — never edited or renamed by T2). Per role.
_EXISTING: dict[str, frozenset[str]] = {
    "drums": frozenset(
        {
            "jz_dr_1",
            "jz_dr_2",
            "jz_dr_3a",
            "jz_dr_3b",
            "jz_dr_4",
            "jz_dr_i",
            "jz_dr_e",
            "jz_dr_f1",
        }
    ),
    "comping": frozenset(
        {
            "jz_cp_1",
            "jz_cp_2a",
            "jz_cp_2b",
            "jz_cp_3a",
            "jz_cp_3b",
            "jz_cp_4",
            "jz_cp_i",
            "jz_cp_e",
        }
    ),
    "pads": frozenset(
        {"jz_pd_1", "jz_pd_2", "jz_pd_3", "jz_pd_4", "jz_pd_i", "jz_pd_e"}
    ),
}

# Render-reachable new ids -> a locked (mood, seed) that selects the id in a full
# jazz render (used to also assert validate_pipeline is clean on that render).
_LOCKED_RENDER: dict[str, tuple[str, str]] = {
    "jz_dr_2b": ("calm", "3"),
    "jz_dr_4b": ("dark", "3"),
    "jz_dr_ib": ("calm", "5"),
    "jz_dr_eb": ("calm", "2"),
    "jz_cp_4b": ("dark", "4"),
    "jz_cp_ib": ("energetic", "1"),
    "jz_cp_eb": ("calm", "4"),
    "jz_pd_3b": ("energetic", "2"),
    "jz_pd_4b": ("energetic", "3"),
}

# GOLDEN-BLIND ids no jazz render reaches (rung-1 mains, low-rung / intro / ending
# pads). Their only mechanical coverage: weighted_choice draws them from the
# eligible set within a bounded Rng-index search.
_BLIND: frozenset[str] = frozenset(
    {"jz_dr_1b", "jz_cp_1b", "jz_pd_1b", "jz_pd_2b", "jz_pd_ib", "jz_pd_eb"}
)

# The lint "worst cell" (§9.2): jazz happy window opens at 106 bpm.
_WORST_TEMPO = 106.0


def _pack() -> StylePack:
    pack = resolve_pack(_PACK)
    assert pack is not None
    return pack


def test_new_and_blind_partition_is_total() -> None:
    """Every new id is classified exactly once as render-locked or blind."""
    new_ids = set(_NEW_BY_SLOT.values())
    assert set(_LOCKED_RENDER) | _BLIND == new_ids
    assert set(_LOCKED_RENDER) & _BLIND == set()


def test_no_variety_coverage_warnings() -> None:
    """The authoritative every-slot × every-supported-cell check: the lint's own
    variety-coverage pass fires on no jazz slot."""
    assert _warn_variety_coverage(_pack()) == []


@pytest.mark.parametrize(
    ("slot", "new_id"), list(_NEW_BY_SLOT.items()), ids=lambda v: str(v)
)
def test_slot_has_two_candidates_at_worst_cell(
    slot: tuple[str, str, int], new_id: str
) -> None:
    """Each formerly-warned slot has >= 2 surviving candidates at the lint worst
    cell (happy/106), and the new id is one of them."""
    role, kind, rung = slot
    eligible = _eligible_set(
        _pack(), cast(Role, role), cast(PatternKind, kind), rung, _WORST_TEMPO
    )
    ids = [p.id for p in eligible]
    assert len(eligible) >= 2, (slot, ids)
    assert new_id in ids, (slot, ids)


@pytest.mark.parametrize(
    ("new_id", "cell"), list(_LOCKED_RENDER.items()), ids=list(_LOCKED_RENDER)
)
def test_locked_render_selects_new_id(new_id: str, cell: tuple[str, str]) -> None:
    """A render-reachable new id is selected by its locked (mood, seed) and that
    render passes the Layers 1-2 gate (validate_pipeline == [])."""
    mood, seed = cell
    trace = generate_trace({"styleFamily": _PACK, "mood": mood, "seed": seed})
    chosen = {pat.id for pat in trace.selection.by_key.values()}
    assert new_id in chosen, (new_id, cell, sorted(chosen))
    assert validate_pipeline(trace.document, trace) == []


@pytest.mark.parametrize("new_id", sorted(_BLIND))
def test_blind_id_is_drawable(new_id: str) -> None:
    """A golden-blind new id (no render reaches its slot) is drawable from its
    eligible set: weighted_choice returns it at some bounded Rng index."""
    slot = next(s for s, i in _NEW_BY_SLOT.items() if i == new_id)
    role, kind, rung = slot
    eligible = _eligible_set(
        _pack(), cast(Role, role), cast(PatternKind, kind), rung, _WORST_TEMPO
    )
    assert len(eligible) >= 2
    drawn_ids = {_draw(eligible, Rng(idx)).id for idx in range(64)}
    assert new_id in drawn_ids, (new_id, slot, drawn_ids)


@pytest.mark.parametrize("role", ["drums", "comping", "pads"])
def test_existing_ids_preserved_and_new_added(role: str) -> None:
    """The exact id set per role is the untouched golden anchors plus only T2's
    additions — nothing renamed, removed, or duplicated."""
    patterns: list[PatternEnvelope] = _pack().patterns[role]
    ids = [p.id for p in patterns]
    assert len(ids) == len(set(ids)), ("duplicate id", role, ids)
    current = set(ids)
    added = {i for s, i in _NEW_BY_SLOT.items() if s[0] == role}
    assert _EXISTING[role] <= current, ("lost an existing id", role)
    assert current == _EXISTING[role] | added, (role, sorted(current))
