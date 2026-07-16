"""Pattern selection — pipeline stage 5 groundwork (PHASE_5 §3.2, §3.6).

`select_patterns` resolves, for every **active, pattern-mode** `(section, role)`
pair, which authored `PatternEnvelope` a part generator (Chunk 3) tiles into that
section. Selection is cached at the pinned `(role, kind, rung)` granularity — one
decision per key per song (§3.2): the first section in form order that needs an
unfilled key draws; every later section sharing the key reuses that pattern
(verse 1 ≡ verse 2 at the same rung; a rung-3 chorus and a rung-4 final chorus
differ).

Section types map to pattern kinds: `intro` → `intro`, `outro` → `ending`,
everything else (incl. `breakdown`, which sits at its own low rung) → `main`. The
eligible set is the role's patterns of that kind passing the tempo-band gate —
plus, for `main`, `energyLevel == rung` (`intro`/`ending` ignore energy). A draw
happens through `weighted_choice` **iff ≥ 2 candidates survive** (PHASE_3 D13); a
singleton is taken with zero draws.

RNG discipline (§3.6): each role draws on its own `select` sub-stream,
`Rng(derive(stream_seed(master, overrides, role), "select"))`, one generator per
role reused across that role's draws in section order. A `mode: walking` bass is
exempt entirely (the walker serves every section/kind — §3.2); only active roles
select, so a role capped out of the arrangement (jazz pads under `layersMax` 3)
draws nothing. The loader already guarantees a non-empty eligible set at every
reachable key (§3.2 completeness), so selection never comes up empty here.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from trackgen.packs.models import Eligibility, PatternEnvelope, PatternKind, StylePack
from trackgen.schema.document import Role
from trackgen.schema.ir import ArrangementPlan, GenerationPlan, SongForm
from trackgen.seeds import Rng, derive, stream_seed, weighted_choice

# The cache key: the (role, kind, rung) granularity §3.2 pins one draw to.
SelectionKey = tuple[Role, PatternKind, int]

# A per-role factory for the `select` sub-stream. Injectable so draw-count tests
# (and the §9.1 goldens) can supply counting shims per role; the default builds
# the §3.6 stream. Called once per role, then the rng is reused across its draws.
RngFactory = Callable[[Role], Rng]


@dataclass(frozen=True)
class SelectionResult:
    """The outcome of `select_patterns`.

    - `by_section` — every active, pattern-mode `(section_id, role)` → its chosen
      pattern (what Chunk-3 generators consume).
    - `by_key` — the `(role, kind, rung)` cache, exposed so goldens can assert
      which pattern won each key (same object each same-key section reuses)."""

    by_section: dict[tuple[str, Role], PatternEnvelope]
    by_key: dict[SelectionKey, PatternEnvelope]


def section_kind(section_type: str) -> PatternKind:
    """§3.2 section-type → pattern-kind map: `intro`→`intro`, `outro`→`ending`,
    everything else (incl. `breakdown`) → `main`."""
    if section_type == "intro":
        return "intro"
    if section_type == "outro":
        return "ending"
    return "main"


def _tempo_eligible(eligibility: Eligibility, tempo_bpm: float) -> bool:
    """§3.2 eligibility: ungated patterns always pass; a gated one passes iff
    `lo ≤ tempo ≤ hi`."""
    band = eligibility.tempo_bpm
    if band is None:
        return True
    lo, hi = band
    return lo <= tempo_bpm <= hi


def _eligible_set(
    pack: StylePack, role: Role, kind: PatternKind, rung: int, tempo_bpm: float
) -> list[PatternEnvelope]:
    """§3.2 eligible set, in authored order: the role's patterns of `kind`
    passing the tempo gate — and, for `main` only, matching `energyLevel == rung`
    (`intro`/`ending` ignore energy)."""
    return [
        pattern
        for pattern in pack.patterns.get(role, [])
        if pattern.kind == kind
        and (kind != "main" or pattern.energy_level == rung)
        and _tempo_eligible(pattern.eligibility, tempo_bpm)
    ]


def _draw(eligible: list[PatternEnvelope], rng: Rng) -> PatternEnvelope:
    """PHASE_3 D13 draw-iff-≥2: a ≥2 set draws via `weighted_choice`; a singleton
    is the sole value with no draw (zero `randrange` calls)."""
    if len(eligible) >= 2:
        return weighted_choice(eligible, [p.weight for p in eligible], rng)
    return eligible[0]


def select_patterns(
    plan: GenerationPlan,
    form: SongForm,
    arrangement: ArrangementPlan,
    pack: StylePack,
    master: int,
    overrides: dict[str, int],
    *,
    rng_factory: RngFactory | None = None,
) -> SelectionResult:
    """Resolve the chosen pattern for every active, pattern-mode `(section, role)`.

    `arrangement` supplies `active` + `intensity` (the rung) per pair — consumed,
    not recomputed. `master`/`overrides` derive each role's `select` sub-stream
    (§3.6); `rng_factory` overrides that derivation for testing. Walking-mode bass
    is skipped (§3.2); inactive pairs contribute nothing.
    """

    def default_factory(role: Role) -> Rng:
        return Rng(derive(stream_seed(master, overrides, role), "select"))

    make_rng = rng_factory if rng_factory is not None else default_factory

    entries_by_section: dict[str, list[tuple[Role, int]]] = defaultdict(list)
    for entry in arrangement.entries:
        if entry.active:
            entries_by_section[entry.section_id].append((entry.role, entry.intensity))

    role_rngs: dict[Role, Rng] = {}

    def rng_for(role: Role) -> Rng:
        rng = role_rngs.get(role)
        if rng is None:
            rng = make_rng(role)
            role_rngs[role] = rng
        return rng

    by_section: dict[tuple[str, Role], PatternEnvelope] = {}
    by_key: dict[SelectionKey, PatternEnvelope] = {}

    for section in form.sections:
        kind = section_kind(section.type)
        for role, rung in entries_by_section.get(section.id, []):
            if role == "bass" and pack.bass_mode == "walking":
                continue
            key: SelectionKey = (role, kind, rung)
            pattern = by_key.get(key)
            if pattern is None:
                eligible = _eligible_set(pack, role, kind, rung, plan.tempo_bpm)
                pattern = _draw(eligible, rng_for(role))
                by_key[key] = pattern
            by_section[(section.id, role)] = pattern

    return SelectionResult(by_section=by_section, by_key=by_key)
