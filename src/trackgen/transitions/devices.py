"""6b — boundary devices (PHASE_6 §3.1-§3.5, §3.7 head).

The boundary taxonomy (§3.1), deterministic device assignment by entered-section
type (§3.2), fill selection/sizing/rendering (§3.3), the `stop` (§3.4) and
`dropout` (§3.5, dormant) devices, and the entered-downbeat crash+kick rule
(§3.7 head). One RNG (`derive(transitions, "devices")`) is consumed in boundary
timeline order; per boundary: `[stop-vs-fill iff eligible]`, `[include iff
phrase boundary]`, `[fill selection iff ≥ 2 candidates]` (§3.8). 6a and the
crash rule are draw-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from trackgen.packs.models import DrumEvent, PatternEnvelope, StylePack
from trackgen.parts.selection import _draw, _tempo_eligible
from trackgen.schema.ir import (
    ArrangementPlan,
    FormSection,
    GenerationPlan,
    SongForm,
)
from trackgen.seeds import Rng, derive, stream_seed, weighted_choice
from trackgen.transitions._common import (
    BAR,
    Builder,
    add_crash_and_kick,
    crash_velocity,
    get_or_create_drum_builder,
    instantiate_fill_event,
    section_span,
)

if TYPE_CHECKING:
    from trackgen.pipeline.explain import ExplainCollector

_FILL_TAIL = 960  # phrase-boundary fills render only the last 2 beats (§3.3).


@dataclass(frozen=True)
class Boundary:
    """A placement site (§3.1). `kind` is `"section"` (adjacent-pair) or
    `"phrase"` (interior). `fill_bar` is the absolute bar the device renders drums
    into; `entered_tick` the downbeat the entered section / phrase begins on."""

    kind: str
    fill_bar: int
    entered_tick: int
    outgoing: FormSection
    entered: FormSection


def _boundaries(form: SongForm) -> list[Boundary]:
    """Enumerate every boundary, then order by the §3.8 boundary timeline
    (ascending `fill_bar`; sections before interiors on a tie — §3.1 guarantees
    section and interior fill bars never actually collide)."""
    out: list[Boundary] = []
    sections = form.sections
    for i in range(len(sections) - 1):
        outgoing, entered = sections[i], sections[i + 1]
        out.append(
            Boundary(
                kind="section",
                fill_bar=outgoing.start_bar + outgoing.length_bars - 1,
                entered_tick=entered.start_bar * BAR,
                outgoing=outgoing,
                entered=entered,
            )
        )
    for section in sections:
        bar = section.start_bar
        for idx, phrase in enumerate(section.phrases):
            if idx > 0:  # every phrase start except the section's first.
                out.append(
                    Boundary(
                        kind="phrase",
                        fill_bar=bar - 1,
                        entered_tick=bar * BAR,
                        outgoing=section,
                        entered=section,
                    )
                )
            bar += phrase.bars
    out.sort(key=lambda b: (b.fill_bar, 0 if b.kind == "section" else 1))
    return out


def _fallback_order(rung: int) -> list[int]:
    """§3.3 nearest-rung fallback: down one at a time to 1, then up to 4."""
    return [rung, *range(rung - 1, 0, -1), *range(rung + 1, 5)]


def _select_fill(
    pack: StylePack, plan: GenerationPlan, rung: int, rng: Rng
) -> PatternEnvelope:
    """§3.3 selection: tempo-eligible `kind: fill` patterns at the resolved rung
    (nearest-rung fallback); `weighted_choice` iff ≥ 2 (PHASE_3 D13)."""
    fills = [
        env
        for env in pack.patterns.get("drums", [])
        if env.kind == "fill" and _tempo_eligible(env.eligibility, plan.tempo_bpm)
    ]
    for candidate_rung in _fallback_order(rung):
        cands = [env for env in fills if env.energy_level == candidate_rung]
        if cands:
            return _draw(cands, rng)
    raise ValueError("no fill pattern resolves (PT12 guarantees ≥ 1)")


def _render_fill(
    builders: list[Builder],
    boundary: Boundary,
    rung: int,
    plan: GenerationPlan,
    pack: StylePack,
    rng: Rng,
) -> None:
    """§3.3 sizing + rendering: pick a fill, window it (full for a section
    boundary, last-2-beats for a phrase boundary), then on the drums role only
    delete groove events inside the rendered window and instantiate the fill's
    events there (tag `"fill"`). Other roles untouched."""
    pattern = _select_fill(pack, plan, rung, rng)
    lo, hi = pack.fill_windows[pattern.id]
    if boundary.kind == "phrase":
        lo = max(lo, pattern.length_ticks - _FILL_TAIL)

    span = section_span(boundary.outgoing)
    bar_start = boundary.fill_bar * BAR

    for b in builders:
        if b.role != "drums" or not (b.start_tick <= bar_start < b.end_tick):
            continue
        b.notes = [n for n in b.notes if not (lo <= n.ticks - bar_start < hi)]

    for event in pattern.events:
        if not (lo <= event.pos < hi):
            continue
        assert isinstance(event, DrumEvent)  # a fill is a drum pattern (PT3).
        # Fills never author crash — crash placement is contextual (§3.7, D17);
        # a stray one is dropped here exactly as `_generate_drums` drops it.
        if event.voice == "crash":
            continue
        track_id, note = instantiate_fill_event(event, bar_start, plan)
        get_or_create_drum_builder(builders, span, track_id).notes.append(note)


def _apply_stop(builders: list[Builder], entered_tick: int) -> None:
    """§3.4 stop: across ALL roles, delete notes attacking in
    `[enteredTick − 480, enteredTick)` and truncate sustains into that window."""
    cut = entered_tick - 480
    for b in builders:
        kept = []
        for n in b.notes:
            if cut <= n.ticks < entered_tick:
                continue
            if n.ticks < cut < n.ticks + n.duration_ticks:
                kept.append(n.model_copy(update={"duration_ticks": cut - n.ticks}))
            else:
                kept.append(n)
        b.notes = kept


def _apply_dropout(builders: list[Builder], entered_tick: int) -> None:
    """§3.5 dropout: truncate every role's note sustaining across `enteredTick`
    to end at it (no fill, no crash)."""
    for b in builders:
        b.notes = [
            n.model_copy(update={"duration_ticks": entered_tick - n.ticks})
            if n.ticks < entered_tick < n.ticks + n.duration_ticks
            else n
            for n in b.notes
        ]


def _stop_eligible(
    boundary: Boundary, drum_rung: dict[str, int], pack: StylePack
) -> bool:
    """§3.4: entered drums rung == 4 AND entered energy > outgoing energy AND
    the pack enables stop."""
    assert pack.transitions is not None
    if not pack.transitions.stop.enabled:
        return False
    return (
        drum_rung.get(boundary.entered.id) == 4
        and boundary.entered.energy > boundary.outgoing.energy
    )


def apply_devices(
    builders: list[Builder],
    form: SongForm,
    arr: ArrangementPlan,
    plan: GenerationPlan,
    pack: StylePack,
    t_last_bar: int,
    *,
    explain: ExplainCollector | None = None,
) -> None:
    """Run 6b in place: enumerate boundaries, then per boundary draw + render in
    §3.8 order on a single `derive(transitions, "devices")` RNG."""
    assert pack.transitions is not None
    spec = pack.transitions
    rng = Rng(
        derive(
            stream_seed(plan.seed.master, plan.seed.overrides, "transitions"), "devices"
        )
    )
    drum_rung = {e.section_id: e.intensity for e in arr.entries if e.role == "drums"}

    for boundary in _boundaries(form):
        # 6a owns bars at/after T_last's bar — such a boundary is not a real
        # placement site (draw-free skip; never triggers on the §7 forms).
        if boundary.fill_bar >= t_last_bar:
            continue

        if boundary.kind == "phrase":
            included = weighted_choice(
                ["include", "exclude"], spec.phrase_fill.odds, rng
            )
            if explain is not None:
                explain.add_device(
                    "phrase_fill",
                    f"phrase@bar{boundary.fill_bar}",
                    included,
                    fired=included == "include",
                )
            if included == "include":
                _render_fill(
                    builders, boundary, drum_rung[boundary.outgoing.id], plan, pack, rng
                )
            continue

        entered_type = boundary.entered.type
        if entered_type == "breakdown":
            _apply_dropout(builders, boundary.entered_tick)
            continue
        if entered_type == "postchorus":
            continue  # smooth continuation — no device, no crash, no draw.

        device = "fill"
        if _stop_eligible(boundary, drum_rung, pack):
            assert spec.stop.odds is not None
            device = weighted_choice(["stop", "fill"], spec.stop.odds, rng)
            if explain is not None:
                explain.add_device(
                    "stop_vs_fill",
                    f"section {boundary.outgoing.id}->{boundary.entered.id}",
                    device,
                    fired=True,  # both stop and fill are audible devices
                )

        if device == "stop":
            _apply_stop(builders, boundary.entered_tick)
        else:
            _render_fill(
                builders, boundary, drum_rung[boundary.entered.id], plan, pack, rng
            )

        # §3.7 crash rule (draw-free): after a section-boundary fill or stop.
        if boundary.entered_tick // BAR < t_last_bar:
            add_crash_and_kick(
                builders,
                boundary.entered,
                boundary.entered_tick,
                crash_velocity(pack, boundary.entered.energy),
                "crash",
                guard_existing_kick=True,
            )
