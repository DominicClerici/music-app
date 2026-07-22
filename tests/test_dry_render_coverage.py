"""GAP-1 blind-id dry-render coverage (caveats C-20, C-22, C-23, C-28).

Many authored `main`/`intro`/`ending` pattern ids are **structurally dormant**
in auto-generation: no reachable (mood × section-kind × energy) render ever
*selects* them, so no render ever routes them through
retarget -> voicing -> serialize. They carry "win-the-draw" *selection* coverage
(the variety suites prove a locked seed under which each would win a draw, via
`_draw` directly), but their Layer-1/Layer-2 **validity** is untested — a dormant
pattern that would trip a validator if ever routed passes the suite silently.

This module gives every bank candidate that missing coverage through the GAP-1
**dry-render seam**: `generate_trace(raw_params, selection=<forced>)` skips
`select_patterns` and runs the passed `SelectionResult` through the real
per-role `generate()` -> transitions -> humanize -> serialize chain, then asserts
`validate_pipeline(doc, trace) == []` (V1-V8 + W1-W8 + L2-1; empty == valid).

Fills (`kind == "fill"`) are excluded: they are a stage-6 device path with no
selection seam, out of scope here (matching the variety suites' fill exclusion).

## Reachability, forcing, and the seam's blind spot

The seam routes a candidate for role R only through sections where R is *active*
in the arrangement (`generate()` consumes `selection.by_section[(section_id, R)]`
only for active entries — `parts/generators.py:221,352`). A candidate's
`kind` (main/intro/ending) governs which sections *select* it in production, but
once routed its validity depends only on its own events/retarget/voicing, not on
the section kind. So a candidate is forced into the baseline's sections of its
own `kind` when R is active there (**native**), else into whatever sections R is
active in (**cross-kind**) — either way it flows through the exact validity
machinery GAP-1 leaves untested.

A full 25-seed × 6-length × all-mood sweep (run while authoring this module)
pins which `(role, kind)` pairs are *ever* active in any reachable render:

  * `pads` is active only in `main` sections on every pack, and **never active
    at all in `chill_lofi`** (its arrangement always culls pads). So pads
    `intro`/`ending` candidates (all packs) route cross-kind through `main`;
    and `chill_lofi` pads candidates (`main`+`intro`+`ending`) are **unroutable
    via the selection seam entirely** — no render activates pads there, so the
    seam cannot reach them. They are enumerated explicitly in
    `_UNROUTABLE` (no silent cap): this is the extreme GAP-1 case, a validity
    gap the *selection* seam structurally cannot close, reported as a finding.
  * `comping` `intro` is never active on `chill_lofi`/`pop_rock`; those route
    cross-kind through `main`.
  * `jazz` bass is walking-mode with an empty pattern bank, so it contributes
    zero bank candidates (nothing to force).

`_CROSS_KIND` pins the `(pack, role, kind)` cells that fall back to cross-kind
forcing, so a pack-data change that quietly moves a cell in or out of the
reachable set fails the classification assert rather than silently dropping or
weakening coverage.

## Determinism (ROADMAP invariant 5)

Everything is pinned literals: the two-seed baseline grid `_GRID_SEEDS` (verified
to natively reach every reachable `(role, kind)` on all five packs — the same
set the full sweep finds), moods derived from the pack, no length override. No
wall-clock, no unseeded RNG. The forced selection is derived from a real
`generate_trace` baseline, so section ids and arrangement rungs are authentic.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache

import pytest

from _packmatrix import PACKS, cached_pack, supported_moods
from trackgen.packs.models import PatternEnvelope
from trackgen.parts.selection import SelectionResult, section_kind
from trackgen.pipeline.serialize import to_json
from trackgen.pipeline.trace import generate_trace
from trackgen.quality.suite import validate_pipeline
from trackgen.schema.document import Role

_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")
_BANK_KINDS: frozenset[str] = frozenset({"main", "intro", "ending"})

# Two pinned base36 seeds. Combined with the pack's supported moods (no length
# override), this grid natively activates every `(role, kind)` pair that is
# reachable in *any* render on all five packs — verified against a full
# 25-seed × 6-length × all-mood sweep. Held to two seeds so the baseline set
# stays small; a pack-data change that needs a wider grid to stay native trips
# `_CROSS_KIND`'s classification assert rather than silently degrading.
_GRID_SEEDS: tuple[str, ...] = ("17wdrqp", "2fsrjhe")

# `(pack, role, kind)` cells whose role is never active in a section of that
# `kind` in any render, yet IS active in some other kind — so the candidate is
# forced cross-kind (through the sections R is active in, chiefly `main`) rather
# than natively. Pinned so a reachability change fails loudly (no silent cap).
_CROSS_KIND: frozenset[tuple[str, Role, str]] = frozenset(
    {
        # pads is active only in `main` on every pack that activates it at all,
        # so every pads intro/ending candidate routes through main.
        ("blues", "pads", "intro"),
        ("blues", "pads", "ending"),
        ("fusion_jazz", "pads", "intro"),
        ("fusion_jazz", "pads", "ending"),
        ("jazz", "pads", "intro"),
        ("jazz", "pads", "ending"),
        ("pop_rock", "pads", "intro"),
        ("pop_rock", "pads", "ending"),
        # comping is never active in an intro section on these two packs.
        ("chill_lofi", "comping", "intro"),
        ("pop_rock", "comping", "intro"),
    }
)

# `(pack, role)` whose role is never active in ANY section of ANY kind, so the
# selection seam cannot route its candidates at all — the extreme GAP-1 case.
# `chill_lofi` culls pads from every arrangement, so all 12 of its pads
# candidates (8 main + 2 intro + 2 ending) are unreachable through this seam.
# Enumerated explicitly (no silent cap); reported as a finding.
_UNROUTABLE: frozenset[tuple[str, Role]] = frozenset({("chill_lofi", "pads")})


@dataclass(frozen=True)
class _Candidate:
    pack: str
    role: Role
    kind: str
    env: PatternEnvelope

    @property
    def label(self) -> str:
        return f"{self.pack}-{self.role}-{self.kind}-{self.env.id}"


def _bank_candidates(pack_id: str) -> list[_Candidate]:
    """Every `main`/`intro`/`ending` bank envelope, per role, for one pack —
    the generalized form of the variety suites' candidate comprehension."""
    pack = cached_pack(pack_id)
    return [
        _Candidate(pack_id, role, env.kind, env)
        for role in _ROLES
        for env in pack.patterns.get(role, [])
        if env.kind in _BANK_KINDS
    ]


def _baseline_params(pack_id: str) -> tuple[dict[str, object], ...]:
    """The pinned baseline grid for a pack: supported moods × `_GRID_SEEDS`."""
    return tuple(
        {"styleFamily": pack_id, "mood": mood, "seed": seed}
        for mood in supported_moods(pack_id)
        for seed in _GRID_SEEDS
    )


@dataclass(frozen=True)
class _Baseline:
    params: dict[str, object]
    selection: SelectionResult
    # section_id -> pattern-kind, for every section in this render.
    section_kind: dict[str, str]
    # role -> {kinds it is active in}, and role -> active section ids.
    active_sections: dict[Role, tuple[str, ...]]


@cache
def _baselines(pack_id: str) -> tuple[_Baseline, ...]:
    """Real `generate_trace` baselines over the pinned grid, cached per process.

    Each carries its selection plus the arrangement facts the forcing needs —
    the section-kind map and, per role, the section ids where the role is
    active (i.e. present in `by_section`)."""
    out: list[_Baseline] = []
    for params in _baseline_params(pack_id):
        trace = generate_trace(params)
        sk: dict[str, str] = {
            s.id: section_kind(s.type) for s in trace.song_form.sections
        }
        active: dict[Role, list[str]] = {role: [] for role in _ROLES}
        for section_id, role in trace.selection.by_section:
            active[role].append(section_id)
        out.append(
            _Baseline(
                params=params,
                selection=trace.selection,
                section_kind=sk,
                active_sections={r: tuple(ids) for r, ids in active.items()},
            )
        )
    return tuple(out)


def _forced_selection(
    baseline: _Baseline, role: Role, target_ids: frozenset[str], env: PatternEnvelope
) -> SelectionResult:
    """`baseline`'s selection with `env` substituted for `role` in every
    `target_ids` section. Only `by_section` is consumed downstream (generators +
    the W4 validator read it; nothing reads `by_key`), so `by_key` is carried
    from the baseline unchanged — it stays a coherent cache of the *unforced*
    draw, never a value `generate()` acts on."""
    by_section = dict(baseline.selection.by_section)
    for section_id, entry_role in list(by_section):
        if entry_role == role and section_id in target_ids:
            by_section[(section_id, role)] = env
    return SelectionResult(by_section=by_section, by_key=baseline.selection.by_key)


@dataclass(frozen=True)
class _Forcing:
    params: dict[str, object]
    selection: SelectionResult
    native: bool


def _plan_forcing(cand: _Candidate) -> _Forcing | None:
    """Choose a baseline + target sections to route `cand` through, or `None`
    if its role is never active in any grid render (unroutable via the seam).

    Prefers a **native** baseline (role active in a section of the candidate's
    own kind), forcing into exactly those sections; falls back to a
    **cross-kind** baseline (role active in any kind), forcing into every section
    the role occupies there."""
    baselines = _baselines(cand.pack)

    # Native: role active in a section of the candidate's own kind.
    for base in baselines:
        native_ids = frozenset(
            sid
            for sid in base.active_sections[cand.role]
            if base.section_kind[sid] == cand.kind
        )
        if native_ids:
            return _Forcing(
                base.params,
                _forced_selection(base, cand.role, native_ids, cand.env),
                native=True,
            )

    # Cross-kind: any baseline where the role is active at all.
    for base in baselines:
        active = base.active_sections[cand.role]
        if active:
            return _Forcing(
                base.params,
                _forced_selection(base, cand.role, frozenset(active), cand.env),
                native=False,
            )

    return None


def _all_candidates() -> Iterator[_Candidate]:
    for pack_id in PACKS:
        yield from _bank_candidates(pack_id)


_CANDIDATES: tuple[_Candidate, ...] = tuple(_all_candidates())
_CANDIDATE_IDS: list[str] = [c.label for c in _CANDIDATES]


# --- the dry-render coverage assertion ---------------------------------------


@pytest.mark.parametrize("cand", _CANDIDATES, ids=_CANDIDATE_IDS)
def test_bank_candidate_dry_renders_clean(cand: _Candidate) -> None:
    """Forcing `cand` through the dry-render seam yields a render that passes the
    full Layers 1-2 gate (`validate_pipeline == []`).

    A failure here is real signal: either a **latent validity bug** in the
    dormant pattern (bad retarget/voicing/serialize output — the GAP-1 target),
    or a **forcing artifact** (an invalidity that only the artificial
    co-occurrence created). The two are distinguished in the report; artifacts
    are designed out of the harness rather than suppressed."""
    forcing = _plan_forcing(cand)
    if forcing is None:
        # Unroutable via the selection seam — must be one of the pinned,
        # explicitly-reasoned cells (chill_lofi pads). Never silently skipped.
        assert (cand.pack, cand.role) in _UNROUTABLE, (
            f"{cand.label} routes through no grid render but is not a pinned "
            f"_UNROUTABLE cell — coverage would be silently lost"
        )
        pytest.skip(f"{cand.label}: role never active — unroutable via selection seam")

    cell = (cand.pack, cand.role, cand.kind)
    if forcing.native:
        assert cell not in _CROSS_KIND, (
            f"{cand.label} forced natively but is pinned cross-kind in _CROSS_KIND"
        )
    else:
        assert cell in _CROSS_KIND, (
            f"{cand.label} fell back to cross-kind forcing but is not pinned in "
            f"_CROSS_KIND — an unexpected reachability change"
        )

    trace = generate_trace(forcing.params, selection=forcing.selection)
    failures = validate_pipeline(trace.document, trace)
    assert failures == [], (cand.label, forcing.native, failures)


# --- Part A: the injection seam is generation-neutral ------------------------

_NEUTRALITY_PARAMS: tuple[dict[str, object], ...] = (
    {"styleFamily": "pop_rock", "seed": "1ps9wxb"},
    {"styleFamily": "jazz", "mood": "melancholic", "maxLengthSec": 240, "seed": "1k3p"},
    {"styleFamily": "chill_lofi", "mood": "calm", "seed": "17wdrqp"},
)


@pytest.mark.parametrize(
    "params",
    _NEUTRALITY_PARAMS,
    ids=[str(p["styleFamily"]) for p in _NEUTRALITY_PARAMS],
)
def test_injection_reproduces_default_document(params: dict[str, object]) -> None:
    """Injecting the selection `select_patterns` *would* have produced yields a
    **byte-identical** document to the default `selection=None` path.

    The default baseline's `trace.selection` is exactly what `select_patterns`
    computed for these params, so feeding it back through the seam proves the
    injection is faithful — and, since the default path is unchanged code, that
    the seam is generation-neutral."""
    baseline = generate_trace(params)
    injected = generate_trace(params, selection=baseline.selection)
    assert to_json(injected.document) == to_json(baseline.document)


def test_injection_actually_changes_the_document() -> None:
    """Positive-wiring proof that `generate_trace`'s `selection=` param is
    genuinely *consumed*, not ignored.

    `test_injection_reproduces_default_document` shows the seam doesn't corrupt
    when fed the default pick — but it would still pass if a regression made
    `generate_trace` ignore `selection=` and always re-run `select_patterns`
    (the byte-identity would hold, and every forced-coverage test above would
    pass vacuously, silently re-rendering defaults). Here we inject a selection
    that *differs* from the default draw and assert the serialized document
    changes: that can only happen if the passed selection is actually honored.

    Concrete case — the blues `drums` main pattern `bl_dr_1`, forced natively
    into every `main` (`solo-*`) section of the `blues`/`aggressive`/`17wdrqp`
    baseline, where the draw itself picks `bl_dr_3b`/`bl_dr_4b` instead."""
    cand = next(c for c in _CANDIDATES if c.label == "blues-drums-main-bl_dr_1")
    forcing = _plan_forcing(cand)
    assert forcing is not None and forcing.native

    baseline = generate_trace(forcing.params)
    forced = generate_trace(forcing.params, selection=forcing.selection)

    # Guard against a degenerate (no-op) pick: the injected selection must in
    # fact differ from the default draw in at least one forced section, else a
    # doc match would prove nothing.
    changed = {
        key
        for key, env in forcing.selection.by_section.items()
        if env.id != baseline.selection.by_section[key].id
    }
    assert changed, "forced selection equals the default draw — test would be vacuous"

    # The payload: honoring the differing injected selection changes the output.
    assert to_json(forced.document) != to_json(baseline.document)


# --- non-vacuity: the harness cannot silently shrink -------------------------


def test_harness_covers_every_bank_candidate() -> None:
    """Recompute the full bank-candidate set from pack data and assert the
    parametrization exercises exactly it — no candidate missing, none duplicated
    (ROADMAP §3, no silent caps).

    Also pins the coverage partition: how many candidates route natively, how
    many cross-kind, how many are unroutable — so a reachability regression that
    quietly moves candidates between buckets fails here."""
    truth: set[tuple[str, Role, str, str]] = set()
    for pack_id in PACKS:
        pack = cached_pack(pack_id)
        for role in _ROLES:
            for env in pack.patterns.get(role, []):
                if env.kind in _BANK_KINDS:
                    truth.add((pack_id, role, env.kind, env.id))

    covered = {(c.pack, c.role, c.kind, c.env.id) for c in _CANDIDATES}
    assert covered == truth, truth ^ covered
    assert len(_CANDIDATES) == len(covered), "duplicate candidate ids"

    # Partition every candidate by how it routes, from the same forcing planner
    # the coverage test uses.
    native = cross = unroutable = 0
    unroutable_cells: set[tuple[str, Role]] = set()
    # Every cross-kind candidate's cell, collected in the same single pass — a
    # two-way check against _CROSS_KIND below.
    cross_cells: set[tuple[str, Role, str]] = set()
    for cand in _CANDIDATES:
        forcing = _plan_forcing(cand)
        if forcing is None:
            unroutable += 1
            unroutable_cells.add((cand.pack, cand.role))
        elif forcing.native:
            native += 1
        else:
            cross += 1
            cross_cells.add((cand.pack, cand.role, cand.kind))

    assert unroutable_cells == set(_UNROUTABLE), unroutable_cells
    # chill_lofi pads: 8 main + 2 intro + 2 ending = 12 unroutable candidates.
    assert unroutable == 12, unroutable
    assert native + cross + unroutable == len(_CANDIDATES)
    # Every cross-kind candidate belongs to a pinned _CROSS_KIND cell, and every
    # pinned cell is actually populated by candidates — a two-way check.
    assert cross_cells == set(_CROSS_KIND), cross_cells ^ set(_CROSS_KIND)

    print(
        f"dry-render coverage — {len(_CANDIDATES)} bank candidates: "
        f"{native} native, {cross} cross-kind, {unroutable} unroutable "
        f"(chill_lofi pads)"
    )
