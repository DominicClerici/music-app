"""6c — anti-repetition mutation (PHASE_6 §3.7 mutation / §3.8 mutate stream).

Five constructive-safe operators, one heavily `none`-biased draw per unit on a
per-unit sub-stream:

- **drums** — 2-bar units from each section start: `hat_lift`, `drop_ornament`,
  `kick_pickup`.
- **comping** — 8-bar units from each section start (last may be short):
  `anticipate`, `drop_hit`.

Units exist only where the role is `active` in that section (§3.7). Each unit
draws one operator from `pack.transitions.mutation.<role>` (authored order;
`weighted_choice` iff the table has ≥ 2 entries, else the sole entry — no draw)
on `Rng(derive(derive(derive(stream_seed(.., "transitions"), "mutate"), role),
f"bar:{unitStartAbsBar}"))`. A drawn `none`, or an op with no legal target,
leaves the note set unchanged (form-invariant draw counts).

The provenance the operators need — a drum note's source `voice`
(`hat_closed`/`hat_open`/…) and whether it came from a `minDensity` (ornament)
event — is lost once drum events collapse to voice-tracks, so it is carried as
internal engine tags added at generation (`generators._generate_drums`) and
dropped at serialize (`pipeline/serialize.py` `_to_event` has no tags field).
`hat_lift`/`drop_ornament` read those; the other three key off the track id.

No operator targets an event tagged `"fill"`, `"crash"`, or `"hold"` (from
6a/6b) or at/after the final chord event's bar. Stop-window events need no
explicit exclusion: 6b already deletes every note in a stop window, so no
surviving event can be targeted there, and the only additive operator
(`kick_pickup`) places strictly earlier than any cleared window (see
`kick_pickup`). Frozen `Phrase`s are rebuilt via `_common`, never mutated.

6c runs *after* 6b, so it must also not undo 6b: `hat_lift` — the only operator
that lengthens a note — clamps its sustain at any §3.5 dropout-entered breakdown
6b truncated at (S22-10), which is why `mutate` takes `dropout_ticks`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from trackgen.packs.models import StylePack
from trackgen.parts.generators import _DEFAULT_DUR
from trackgen.schema.ir import (
    ArrangementPlan,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    PhraseNote,
    SongForm,
)
from trackgen.seeds import Rng, derive, stream_seed, weighted_choice
from trackgen.transitions._common import BAR, BEAT, Builder, to_builders, to_phrases
from trackgen.transitions.ending import find_t_last

if TYPE_CHECKING:
    from trackgen.pipeline.explain import ExplainCollector

_PICKUP = 240  # the pickup / anticipation displacement (§3.7).
_EXCLUDED_TAGS = frozenset({"fill", "crash", "hold"})
_DRUM_UNIT_BARS = 2
_COMPING_UNIT_BARS = 8
_HAT_LIFT_DUR = 360  # the open-hat sustain `hat_lift` writes (§3.7).
_MIN_AUDIBLE = 60  # sub-60-tick fragments are inaudible and dropped (C-07).


# --- unit enumeration ---------------------------------------------------------


def _active_sections(arr: ArrangementPlan, role: str) -> set[str]:
    return {e.section_id for e in arr.entries if e.role == role and e.active}


def _units(
    form: SongForm, active_ids: set[str], unit_bars: int
) -> Iterator[tuple[FormSection, int, int, int]]:
    """`(section, unitStartAbsBar, u_lo_tick, u_hi_tick)` for each unit of an
    active section — `unit_bars`-bar windows from the section start, the last
    clamped to the section end (§3.7; drums 2-bar always divide the ≥4-bar,
    multiple-of-4 sections evenly, so only comping's 8-bar units go short)."""
    for section in form.sections:
        if section.id not in active_ids:
            continue
        s_start = section.start_bar
        s_end = section.start_bar + section.length_bars
        bar = s_start
        while bar < s_end:
            u_end = min(bar + unit_bars, s_end)
            yield section, bar, bar * BAR, u_end * BAR
            bar += unit_bars


# --- builder / note helpers ---------------------------------------------------


def _drum_builders(builders: list[Builder], section: FormSection) -> list[Builder]:
    st = section.start_bar * BAR
    return [b for b in builders if b.role == "drums" and b.start_tick == st]


def _drum_builder(
    builders: list[Builder], section: FormSection, track_id: str
) -> Builder | None:
    st = section.start_bar * BAR
    for b in builders:
        if b.role == "drums" and b.track_id == track_id and b.start_tick == st:
            return b
    return None


def _comping_builder(builders: list[Builder], section: FormSection) -> Builder | None:
    st = section.start_bar * BAR
    for b in builders:
        if b.role == "comping" and b.track_id == "comping" and b.start_tick == st:
            return b
    return None


def _eligible(note: PhraseNote, final_bar_tick: int) -> bool:
    """A note the operators may touch: not a 6a/6b device event, and strictly
    before the final chord event's bar (§3.7 exclusions)."""
    return note.ticks < final_bar_tick and not (_EXCLUDED_TAGS & set(note.tags))


def _replace(builder: Builder, old: PhraseNote, new: PhraseNote) -> None:
    builder.notes = [new if n is old else n for n in builder.notes]


def _with_var(tags: list[str]) -> list[str]:
    return tags if "var" in tags else [*tags, "var"]


# --- drum operators -----------------------------------------------------------


def _lift_duration(tick: int, dropout_ticks: frozenset[int]) -> int | None:
    """The open-hat sustain for a lift at `tick`, clamped so it never crosses a
    §3.5 dropout-entered breakdown (S22-10). 6b truncated every sustain across
    that entry; 6c runs after it, so an unclamped 360-tick lift on the last
    offbeat 8th of a bar (pos 1680 → 2040) would silently re-introduce exactly
    the sustain the dropout removed and trip validator W2. `None` = no audible
    lift is possible, so the caller no-ops."""
    limits = [entered - tick for entered in dropout_ticks if entered > tick]
    duration = min([_HAT_LIFT_DUR, *limits])
    return duration if duration >= _MIN_AUDIBLE else None


def _hat_lift(
    builders: list[Builder],
    section: FormSection,
    u_lo: int,
    u_hi: int,
    final_bar_tick: int,
    dropout_ticks: frozenset[int] = frozenset(),
) -> None:
    """The **last** `hat_closed` at an offbeat-8th (`tick % 480 == 240`) in the
    unit's **second bar** → `hat_open`, dur 360 (clamped short of a dropout-
    entered breakdown), tag `"var"`. None → no-op."""
    hats = _drum_builder(builders, section, "hats")
    if hats is None:
        return
    second_lo = u_lo + BAR  # the 2-bar unit's later bar.
    cands = [
        n
        for n in hats.notes
        if second_lo <= n.ticks < u_hi
        and n.ticks % BEAT == 240
        and "hat_closed" in n.tags
        and _eligible(n, final_bar_tick)
    ]
    if not cands:
        return
    target = sorted(cands, key=lambda n: n.ticks)[-1]
    duration = _lift_duration(target.ticks, dropout_ticks)
    if duration is None:
        return
    tags = [t for t in target.tags if t != "hat_closed"]
    if "hat_open" not in tags:
        tags.append("hat_open")
    _replace(
        hats,
        target,
        target.model_copy(update={"duration_ticks": duration, "tags": _with_var(tags)}),
    )


def _drop_ornament(
    builders: list[Builder],
    section: FormSection,
    u_lo: int,
    u_hi: int,
    final_bar_tick: int,
    dropout_ticks: frozenset[int] = frozenset(),
) -> None:
    """Delete the **last** `minDensity` (ornament-tagged) event in the unit,
    across every drum voice-track. None → no-op. (Only ornament notes are
    droppable, so a backbeat/beat-1/non-ornament note is never removed.)"""
    cands: list[tuple[Builder, PhraseNote]] = []
    for b in _drum_builders(builders, section):
        for n in b.notes:
            if (
                u_lo <= n.ticks < u_hi
                and n.ticks % BAR != 0  # never remove a bar-start (beat-1) event
                and "ornament" in n.tags
                and _eligible(n, final_bar_tick)
            ):
                cands.append((b, n))
    if not cands:
        return
    # Last = latest tick; ties break to the last in (track-order, note-order).
    builder, target = sorted(cands, key=lambda bn: bn[1].ticks)[-1]
    builder.notes = [n for n in builder.notes if n is not target]


def _kick_pickup(
    builders: list[Builder],
    section: FormSection,
    u_lo: int,
    u_hi: int,
    final_bar_tick: int,
    dropout_ticks: frozenset[int] = frozenset(),
) -> None:
    """Target = **last** kick in the unit not at a bar start; add a kick at
    `target − 240` iff no kick lies within ±120 of that tick; velocity
    `round3(target.velocity × 0.85)`, tag `"var"`. No target / occupied → no-op.

    The addition can never land in a stop window: 6b deletes every kick in
    `[t − 480, t)`, so the last surviving non-bar-start kick sits before that
    window and `target − 240` sits earlier still."""
    kick = _drum_builder(builders, section, "kick")
    if kick is None:
        return
    cands = [
        n
        for n in kick.notes
        if u_lo <= n.ticks < u_hi
        and n.ticks % BAR != 0
        and _eligible(n, final_bar_tick)
    ]
    if not cands:
        return
    target = sorted(cands, key=lambda n: n.ticks)[-1]
    new_tick = target.ticks - _PICKUP
    if any(abs(n.ticks - new_tick) <= 120 for n in kick.notes):
        return
    kick.notes.append(
        PhraseNote(
            ticks=new_tick,
            duration_ticks=_DEFAULT_DUR["kick"],
            midi=None,
            velocity=round(target.velocity * 0.85, 3),
            tags=["kick", "var"],
        )
    )


# --- comping operators --------------------------------------------------------


def _anticipate(
    builders: list[Builder],
    section: FormSection,
    u_lo: int,
    u_hi: int,
    final_bar_tick: int,
    dropout_ticks: frozenset[int] = frozenset(),
) -> None:
    """Target = **last** comping attack at a bar start in the unit, excluding the
    unit's first attack; shift the whole chord (all notes at that tick) by −240,
    pitches unchanged, tag `"var"`; truncate the previous note if it overlaps the
    new start. No-op if any comping note attacks in `[new, old)`."""
    comp = _comping_builder(builders, section)
    if comp is None:
        return
    in_unit = [
        n for n in comp.notes if u_lo <= n.ticks < u_hi and _eligible(n, final_bar_tick)
    ]
    if not in_unit:
        return
    attack_ticks = sorted({n.ticks for n in in_unit})
    first_tick = attack_ticks[0]
    bar_starts = [t for t in attack_ticks if t % BAR == 0 and t != first_tick]
    if not bar_starts:
        return
    old = max(bar_starts)
    new = old - _PICKUP
    # Skip if the −240 landing would collide with an existing comping attack.
    if any(new <= n.ticks < old for n in comp.notes):
        return

    shifted = [
        n.model_copy(update={"ticks": new, "tags": _with_var(list(n.tags))})
        if n.ticks == old
        else n
        for n in comp.notes
    ]
    # Truncate any prior note now sustaining across the pulled-in attack.
    comp.notes = [
        n.model_copy(update={"duration_ticks": new - n.ticks})
        if n.ticks < new < n.ticks + n.duration_ticks
        else n
        for n in shifted
    ]


def _drop_hit(
    builders: list[Builder],
    section: FormSection,
    u_lo: int,
    u_hi: int,
    final_bar_tick: int,
    dropout_ticks: frozenset[int] = frozenset(),
) -> None:
    """Delete the **last** comping attack in the unit whose bar holds ≥ 2 comping
    attacks (the guard prevents a fully silent bar; the non-bar-start restriction
    keeps every bar's beat-1 anchor). None → no-op."""
    comp = _comping_builder(builders, section)
    if comp is None:
        return
    attacks_by_bar: dict[int, set[int]] = defaultdict(set)
    for n in comp.notes:
        if u_lo <= n.ticks < u_hi:
            attacks_by_bar[n.ticks // BAR].add(n.ticks)
    cand_ticks = {
        n.ticks
        for n in comp.notes
        if u_lo <= n.ticks < u_hi
        and n.ticks % BAR != 0
        and _eligible(n, final_bar_tick)
        and len(attacks_by_bar[n.ticks // BAR]) >= 2
    }
    if not cand_ticks:
        return
    drop_tick = max(cand_ticks)
    comp.notes = [n for n in comp.notes if n.ticks != drop_tick]


_Operator = Callable[[list[Builder], FormSection, int, int, int, frozenset[int]], None]

_DRUM_OPS: dict[str, _Operator] = {
    "hat_lift": _hat_lift,
    "drop_ornament": _drop_ornament,
    "kick_pickup": _kick_pickup,
}
_COMPING_OPS: dict[str, _Operator] = {
    "anticipate": _anticipate,
    "drop_hit": _drop_hit,
}


# --- per-unit driver ----------------------------------------------------------


def mutate(
    phrases: list[Phrase],
    form: SongForm,
    chords: HarmonicPlan,
    arr: ArrangementPlan,
    plan: GenerationPlan,
    pack: StylePack,
    *,
    explain: ExplainCollector | None = None,
    dropout_ticks: frozenset[int] = frozenset(),
) -> list[Phrase]:
    """6c: draw and apply one mutation per (role, unit) on its own sub-stream.

    `dropout_ticks` are the entered ticks 6b applied a §3.5 dropout at (see
    `devices.apply_devices`); the operators must not sustain a note across one."""
    assert pack.transitions is not None
    spec = pack.transitions
    final_bar_tick = (find_t_last(chords) // BAR) * BAR
    builders = to_builders(phrases)
    mutate_seed = derive(
        stream_seed(plan.seed.master, plan.seed.overrides, "transitions"), "mutate"
    )

    for role, table, unit_bars, ops in (
        ("drums", spec.mutation.drums, _DRUM_UNIT_BARS, _DRUM_OPS),
        ("comping", spec.mutation.comping, _COMPING_UNIT_BARS, _COMPING_OPS),
    ):
        if table is None:
            continue
        names = list(table.keys())
        weights = list(table.values())
        role_seed = derive(mutate_seed, role)
        active_ids = _active_sections(arr, role)
        for section, unit_start_bar, u_lo, u_hi in _units(form, active_ids, unit_bars):
            rng = Rng(derive(role_seed, f"bar:{unit_start_bar}"))
            op = weighted_choice(names, weights, rng) if len(names) >= 2 else names[0]
            if explain is not None:
                explain.add_mutation(
                    role, section.id, unit_start_bar, op, names, weights
                )
            if op == "none":
                continue
            ops[op](builders, section, u_lo, u_hi, final_bar_tick, dropout_ticks)

    return to_phrases(builders)
