"""The `--explain` selection log (PHASE_8 §9.3, SESSION_17 T3).

An opt-in, per-slot decision trace of one pipeline run. A caller threads an
`ExplainCollector` through `generate_trace` and each stage appends a structured
record **after** its draw resolves; `render_explain` turns the collector into a
human-readable text trace (the `DrumAudioResults.txt` idea).

Determinism contract: the collector is **append-only** and never reads or
advances any RNG, never reorders a draw, and never changes a weight or candidate
list. With no collector passed (`explain=None`, the default everywhere) the
production path is byte-identical to today — that is the load-bearing property.

Slots logged (exactly the §9.3 list): the template draw (chosen id +
candidates/weights); each per-tag pool / turnaround / final entry pick (chosen +
surviving-candidate count); the dressing tier per slot (token + tier); each
per-`(role, kind, rung)` pattern pick (chosen + survivor count); device draws
**and** no-ops (phrase-fill include/exclude, stop-vs-fill, per boundary);
mutation draws **and** no-ops (`none` included); and the auto-path tempo draw
(chosen bpm + window).

Explicitly OUT of scope (would swamp the log, not in §9.3): the walker's
per-tick pitch draws (`parts/walker.py`) and the form per-slot optional /
bar-count draws. Those are intentionally not recorded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateRecord:
    """The stage-2 form-template selection: which template won, over which
    eligible candidate ids and their weights."""

    chosen: str
    candidates: tuple[str, ...]
    weights: tuple[int, ...]


@dataclass(frozen=True)
class EntryRecord:
    """A stage-3 progression pick — `kind` is `pool` / `turnaround` / `final`.
    `tag` is the slot identity (a harmony tag, `turnaround:<section>`, or
    `finals`); `survivors` is how many candidates passed gating."""

    kind: str
    tag: str
    chosen: str
    survivors: int


@dataclass(frozen=True)
class DressingRecord:
    """A stage-3 per-slot dressing draw: the source `token`, the dissonance
    `tier` it was dressed at, and the resulting chord `symbol`."""

    token: str
    tier: int
    chosen: str


@dataclass(frozen=True)
class PatternRecord:
    """A stage-5 pattern pick at the pinned `(role, kind, rung)` granularity:
    the chosen pattern id and the surviving-candidate count."""

    role: str
    kind: str
    rung: int
    chosen: str
    survivors: int


@dataclass(frozen=True)
class DeviceRecord:
    """A stage-6b boundary-device draw. `kind` is `phrase_fill` (include/exclude)
    or `stop_vs_fill`; `outcome` is the drawn label. `fired` is whether the draw
    produced an audible device: a phrase-fill `exclude` is the no-op (`fired` is
    False); a `stop_vs_fill` always fires (both stop and fill are audible)."""

    kind: str
    boundary: str
    outcome: str
    fired: bool


@dataclass(frozen=True)
class MutationRecord:
    """A stage-6c per-unit mutation draw, `none` (the no-op) included. `unit_bar`
    is the unit's absolute start bar; `candidates`/`weights` are the role's
    mutation table."""

    role: str
    section: str
    unit_bar: int
    op: str
    candidates: tuple[str, ...]
    weights: tuple[int, ...]


@dataclass(frozen=True)
class TempoRecord:
    """The stage-1 auto-path tempo draw: the chosen bpm and the `[lo, hi]`
    window it was drawn from."""

    bpm: int
    lo: int
    hi: int


ExplainRecord = (
    TemplateRecord
    | EntryRecord
    | DressingRecord
    | PatternRecord
    | DeviceRecord
    | MutationRecord
    | TempoRecord
)


@dataclass
class ExplainCollector:
    """Append-only sink for per-slot decision records (§9.3).

    Each `add_*` helper builds the matching frozen record and appends it. The
    collector holds no RNG and performs no draw, so passing one never changes the
    generated document."""

    records: list[ExplainRecord] = field(default_factory=list)

    def add_template(
        self, chosen: str, candidates: Sequence[str], weights: Sequence[int]
    ) -> None:
        self.records.append(TemplateRecord(chosen, tuple(candidates), tuple(weights)))

    def add_entry(self, kind: str, tag: str, chosen: str, survivors: int) -> None:
        self.records.append(EntryRecord(kind, tag, chosen, survivors))

    def add_dressing(self, token: str, tier: int, chosen: str) -> None:
        self.records.append(DressingRecord(token, tier, chosen))

    def add_pattern(
        self, role: str, kind: str, rung: int, chosen: str, survivors: int
    ) -> None:
        self.records.append(PatternRecord(role, kind, rung, chosen, survivors))

    def add_device(
        self, kind: str, boundary: str, outcome: str, *, fired: bool
    ) -> None:
        self.records.append(DeviceRecord(kind, boundary, outcome, fired))

    def add_mutation(
        self,
        role: str,
        section: str,
        unit_bar: int,
        op: str,
        candidates: Sequence[str],
        weights: Sequence[int],
    ) -> None:
        self.records.append(
            MutationRecord(
                role, section, unit_bar, op, tuple(candidates), tuple(weights)
            )
        )

    def add_tempo(self, bpm: int, lo: int, hi: int) -> None:
        self.records.append(TempoRecord(bpm, lo, hi))


def _weights_str(candidates: Sequence[str], weights: Sequence[int]) -> str:
    return ", ".join(f"{c}={w}" for c, w in zip(candidates, weights, strict=True))


def render_explain(collector: ExplainCollector) -> str:
    """Render a collector as a grouped, human-readable per-slot trace (§9.3).

    Sections appear in pipeline order; each groups its records and shows slot
    identity, chosen value, and candidate/survivor counts, no-ops included."""
    templates = [r for r in collector.records if isinstance(r, TemplateRecord)]
    tempos = [r for r in collector.records if isinstance(r, TempoRecord)]
    entries = [r for r in collector.records if isinstance(r, EntryRecord)]
    dressings = [r for r in collector.records if isinstance(r, DressingRecord)]
    patterns = [r for r in collector.records if isinstance(r, PatternRecord)]
    devices = [r for r in collector.records if isinstance(r, DeviceRecord)]
    mutations = [r for r in collector.records if isinstance(r, MutationRecord)]

    lines: list[str] = ["=== selection log (--explain) ==="]

    lines.append(f"\n-- tempo ({len(tempos)}) --")
    for t in tempos:
        lines.append(f"  {t.bpm} bpm  window [{t.lo}, {t.hi}]")

    lines.append(f"\n-- template ({len(templates)}) --")
    for tpl in templates:
        lines.append(
            f"  chose {tpl.chosen}  of {len(tpl.candidates)} "
            f"[{_weights_str(tpl.candidates, tpl.weights)}]"
        )

    lines.append(f"\n-- progressions ({len(entries)}) --")
    for e in entries:
        lines.append(f"  {e.kind} {e.tag}: chose {e.chosen}  ({e.survivors} survived)")

    lines.append(f"\n-- dressing ({len(dressings)}) --")
    for d in dressings:
        lines.append(f"  {d.token} @ tier {d.tier} -> {d.chosen}")

    lines.append(f"\n-- patterns ({len(patterns)}) --")
    for p in patterns:
        lines.append(
            f"  {p.role}/{p.kind}/rung{p.rung}: chose {p.chosen}  "
            f"({p.survivors} survived)"
        )

    lines.append(f"\n-- devices ({len(devices)}) --")
    for dev in devices:
        state = "fired" if dev.fired else "no-op"
        lines.append(f"  {dev.kind} @ {dev.boundary}: {dev.outcome} [{state}]")

    lines.append(f"\n-- mutations ({len(mutations)}) --")
    for m in mutations:
        state = "no-op" if m.op == "none" else "applied"
        lines.append(
            f"  {m.role} {m.section} bar{m.unit_bar}: {m.op} [{state}]  "
            f"[{_weights_str(m.candidates, m.weights)}]"
        )

    return "\n".join(lines) + "\n"
