"""Reroll-variety coverage for the pop_rock reference bank (SESSION_19 T1, §9.2).

Chunk 5 authored a 2nd candidate in each of the 23 pop_rock slots that formerly
warned `variety-coverage` in `trackgen lint`. This module locks that work down
with three executable guarantees:

`test_every_slot_has_two_eligible_candidates` — the executable form of the lint
warning being *clear*: every `(role, kind, rung)` slot has >= 2 candidates
surviving all selection gates at **every** supported `(mood, tempo)` cell, using
the exact primitives the lint's `_warn_variety_coverage` uses.

`test_render_reachable_candidate_wins` / `test_blind_slot_draw_selects_candidate`
— per new pattern id, a locked seed under which that candidate actually *wins*
its selection draw. The 15 candidates the arrangement can route are pinned to a
concrete full-render `(mood, seed, length)` and proven via `--explain` +
`validate_pipeline == []`. The 8 golden-blind slots (all rung-1 mains, the
low-rung / intro / ending pads, the comping intro — caveat C-20: the 24-cell
corpus never selects them, pads are layer-capped off, rung-1 mains are never
routed) get their *only* mechanical coverage here, exercised through the exact
production draw primitive `_draw(_eligible_set(...), select-stream rng)`.

`test_no_preexisting_pattern_removed_or_altered` — the additive-only contract:
every pre-session pattern id still present, and its authored YAML byte-identical
to the HEAD baseline (frozen sha256 prefixes).

Determinism (ROADMAP invariant 5): every seed is a pinned literal and all RNG
flows through `trackgen.seeds`; no `random`/`time`/`datetime` import (TID251).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest
import yaml

from trackgen.packs import resolve_pack
from trackgen.packs.lint import _active_roles, _mood_windows
from trackgen.packs.loader import load_pack
from trackgen.packs.models import PatternKind
from trackgen.parts.selection import _draw, _eligible_set
from trackgen.pipeline.explain import ExplainCollector, PatternRecord
from trackgen.pipeline.trace import generate_trace
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.document import Role
from trackgen.seeds import Rng, derive, stream_seed

_PACK_DIR = Path(__file__).resolve().parents[1] / "styles" / "pop_rock"

# The six variety-linted slots per role (fills are Phase-6-owned, not linted).
_SLOTS: tuple[tuple[str, int], ...] = (
    ("main", 1),
    ("main", 2),
    ("main", 3),
    ("main", 4),
    ("intro", 1),
    ("ending", 1),
)


# --- (a) every slot clears the variety floor at every (mood, tempo) cell ------


def test_every_slot_has_two_eligible_candidates() -> None:
    """The executable form of the (now-cleared) `variety-coverage` warning:
    >= 2 candidates survive every gate at every supported `(mood, tempo)` cell,
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


# --- (b1) render-reachable new candidates: locked full-render seed that wins ---

# Each row: new id -> the pinned (mood, seed, length_sec) whose full render
# selects it (discovered by seed sweep; stable — selection is upstream of the
# serializer version T4a bumps). Proven via --explain + validate_pipeline.
_RENDER_REACHABLE: dict[str, tuple[str, str, int]] = {
    "pr_dr_3b": ("aggressive", "1", 60),
    "pr_dr_4b": ("aggressive", "1", 180),
    "pr_dr_ib": ("aggressive", "3", 60),
    "pr_dr_eb": ("calm", "1", 480),
    "pr_bs_2b": ("energetic", "4", 60),
    "pr_bs_3b": ("aggressive", "3", 60),
    "pr_bs_4b": ("calm", "1", 180),
    "pr_bs_ib": ("aggressive", "4", 60),
    "pr_bs_eb": ("aggressive", "1", 60),
    "pr_cp_2b": ("aggressive", "1", 60),
    "pr_cp_3b": ("aggressive", "1", 180),
    "pr_cp_4b": ("tense", "1", 60),
    "pr_cp_eb": ("aggressive", "6", 180),
    "pr_pd_3b": ("aggressive", "2", 180),
    "pr_pd_4b": ("aggressive", "2", 60),
}


@pytest.mark.parametrize("new_id", sorted(_RENDER_REACHABLE))
def test_render_reachable_candidate_wins(new_id: str) -> None:
    """Each routable new candidate is actually selected by a locked full render,
    and that render passes the Layer-1/L2-1 gate (`validate_pipeline == []`)."""
    mood, seed, length = _RENDER_REACHABLE[new_id]
    params = {
        "styleFamily": "pop_rock",
        "mood": mood,
        "seed": seed,
        "maxLengthSec": length,
    }
    col = ExplainCollector()
    trace = generate_trace(params, explain=col)

    chosen = {rec.chosen for rec in col.records if isinstance(rec, PatternRecord)}
    assert new_id in chosen, (
        f"{new_id} not selected at {params}; chose {sorted(chosen)}"
    )
    assert validate_pipeline(trace.document, trace) == []


# --- (b2) golden-blind slots: locked select-stream seed that wins the draw -----

# Each row: (role, kind, rung, master_seed_int, new_id). The arrangement never
# routes these slots (rung-1 mains, layer-capped pads, comping intro — C-20), so
# the production draw primitive is their only mechanical coverage. The rng is the
# exact §3.6 select sub-stream: Rng(derive(stream_seed(master, {}, role), "select")).
_BLIND_DRAWS: tuple[tuple[str, str, int, int, str], ...] = (
    ("drums", "main", 1, 3, "pr_dr_1b"),
    ("bass", "main", 1, 4, "pr_bs_1b"),
    ("comping", "main", 1, 1, "pr_cp_1b"),
    ("comping", "intro", 1, 1, "pr_cp_ib"),
    ("pads", "main", 1, 2, "pr_pd_1b"),
    ("pads", "main", 2, 2, "pr_pd_2b"),
    ("pads", "intro", 1, 2, "pr_pd_ib"),
    ("pads", "ending", 1, 2, "pr_pd_eb"),
)

# The lint worst cell: mood='happy', tempo=106.
_WORST_TEMPO = 106.0


@pytest.mark.parametrize(
    ("role", "kind", "rung", "master", "new_id"),
    _BLIND_DRAWS,
    ids=[row[4] for row in _BLIND_DRAWS],
)
def test_blind_slot_draw_selects_candidate(
    role: str, kind: str, rung: int, master: int, new_id: str
) -> None:
    """A golden-blind slot's production selection draw picks the new candidate
    under a locked select-stream master seed — the exact `_draw`/`_eligible_set`
    path selection uses, at the lint worst cell (happy / 106)."""
    pack = load_pack(str(_PACK_DIR))
    eligible = _eligible_set(
        pack, cast(Role, role), cast(PatternKind, kind), rung, _WORST_TEMPO
    )
    assert len(eligible) >= 2, f"{role}/{kind}/rung{rung} is not a real draw"

    rng = Rng(derive(stream_seed(master, {}, role), "select"))
    chosen = _draw(eligible, rng)
    assert chosen.id == new_id, (
        f"{role}/{kind}/rung{rung} @ master {master} chose {chosen.id}, "
        f"expected {new_id} (candidates {[p.id for p in eligible]})"
    )


# --- (c) additive-only: no pre-existing pattern removed or altered -------------

# Frozen sha256[:16] of each pre-session pattern's authored YAML entry
# (json.dumps(entry, sort_keys=True)), computed from git HEAD before authoring.
_FROZEN_PREEXISTING_HASHES: dict[str, str] = {
    "pr_bs_1": "edea60e2d3471d2d",
    "pr_bs_2": "01c2c83a0fc3e038",
    "pr_bs_3": "370ab6800aed615c",
    "pr_bs_4": "fdc98757acdab2e1",
    "pr_bs_e": "18f0c0c46a024fbd",
    "pr_bs_i": "802086d6eca2448e",
    "pr_cp_1": "27dbe3674b99b9b2",
    "pr_cp_2": "87d3c8b840924267",
    "pr_cp_3": "4f0973c170fcc643",
    "pr_cp_4": "3c0aafaf461106e5",
    "pr_cp_e": "1ae3b110692d686f",
    "pr_cp_i": "925b5d852952fad9",
    "pr_dr_1": "8d90249d0f307903",
    "pr_dr_2a": "1fdbd3b2e375bf50",
    "pr_dr_2b": "f146b48adb14298f",
    "pr_dr_3": "039abf199d092ec7",
    "pr_dr_4": "407d4fd3ee6ecde9",
    "pr_dr_e": "fae02909d5762718",
    "pr_dr_f1": "772a8dec8499cc0e",
    "pr_dr_f2": "2a137978613d87b6",
    "pr_dr_i": "a8fa692e73ec9988",
    "pr_pd_1": "d40c4a65f20d70e7",
    "pr_pd_2": "1d88c024be2350ca",
    "pr_pd_3": "41c3fe2766c10bb3",
    "pr_pd_4": "8b0dff61561ad6f5",
    "pr_pd_e": "c39d052d684a269b",
    "pr_pd_i": "aa0d5684f1c66ea7",
}

_BANK_FILES = ("drums", "bass", "comping", "pads")


def _authored_entry_hashes() -> dict[str, str]:
    """sha256[:16] of each pattern's authored YAML entry, keyed by id — the same
    canonical form the frozen baseline was computed with."""
    out: dict[str, str] = {}
    for name in _BANK_FILES:
        data = yaml.safe_load((_PACK_DIR / "patterns" / f"{name}.yaml").read_text())
        for entry in data["patterns"]:
            digest = hashlib.sha256(
                json.dumps(entry, sort_keys=True).encode()
            ).hexdigest()[:16]
            out[entry["id"]] = digest
    return out


def test_no_preexisting_pattern_removed_or_altered() -> None:
    """Every pre-session id still present and byte-identical to HEAD (additive
    only — `pr_bs_2`, `pr_dr_2a`, and the rest are golden anchors)."""
    current = _authored_entry_hashes()
    for pid, expected in _FROZEN_PREEXISTING_HASHES.items():
        assert pid in current, f"pre-existing pattern {pid} was removed"
        assert current[pid] == expected, (
            f"pre-existing pattern {pid} was altered "
            f"(hash {current[pid]} != frozen {expected})"
        )


def test_pack_gained_exactly_the_23_new_ids() -> None:
    """The pack's id set is the 27 frozen entries plus exactly the 23 new
    candidates — no accidental extra or missing addition."""
    expected_new = set(_RENDER_REACHABLE) | {row[4] for row in _BLIND_DRAWS}
    assert len(expected_new) == 23
    pack = resolve_pack("pop_rock")
    assert pack is not None
    current_ids = {p.id for pats in pack.patterns.values() for p in pats}
    assert current_ids == set(_FROZEN_PREEXISTING_HASHES) | expected_new
