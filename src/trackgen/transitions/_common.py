"""Shared mechanics for stage 6 sub-passes (PHASE_6 §3).

Phrases are frozen (`ir.py` `ConfigDict(frozen=True)`), so stage 6 cannot edit
in place: every sub-pass works on a mutable `Builder` list (one per (track,
section), mirroring the generator granularity — PHASE_5 §8.2 / SESSION_10 §2.2)
and rebuilds frozen `Phrase`s at the end (`to_phrases`), dropping any that end
up empty and re-sorting each note list with the `(ticks, midi|-1)` key.

No randomness / clock here (ROADMAP invariant 5); the RNG is owned by
`devices.py` and passed to the fill selector.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trackgen.packs.models import DrumEvent, DrumVoice, StylePack
from trackgen.parts.dynamics import apply_velocity
from trackgen.parts.generators import (
    _DEFAULT_DUR,
    _TRACK_ORDER,
    _VOICE_TRACK,
    _note_sort_key,
)
from trackgen.schema.document import Role
from trackgen.schema.ir import FormSection, GenerationPlan, Phrase, PhraseNote

BAR = 1920
BEAT = 480

# Canonical emit order: within a section (shared `start_tick`) drums come first
# in `_TRACK_ORDER` (now incl. `crash`), then the pitched roles.
_ROLE_RANK: dict[Role, int] = {"drums": 0, "bass": 1, "comping": 2, "pads": 3}
_TRACK_RANK: dict[str, int] = {track: i for i, track in enumerate(_TRACK_ORDER)}


@dataclass
class Builder:
    """A mutable (track, section) note bucket rebuilt into a `Phrase` at emit."""

    track_id: str
    role: Role
    start_tick: int
    end_tick: int
    notes: list[PhraseNote] = field(default_factory=list)


def to_builders(phrases: list[Phrase]) -> list[Builder]:
    return [
        Builder(p.track_id, p.role, p.start_tick, p.end_tick, list(p.notes))
        for p in phrases
    ]


def to_phrases(builders: list[Builder]) -> list[Phrase]:
    """Rebuild frozen `Phrase`s, dropping empties and re-sorting notes (§3)."""
    out: list[Phrase] = []
    for b in builders:
        if not b.notes:
            continue
        out.append(
            Phrase(
                track_id=b.track_id,
                role=b.role,
                start_tick=b.start_tick,
                end_tick=b.end_tick,
                notes=sorted(b.notes, key=_note_sort_key),
            )
        )
    out.sort(
        key=lambda p: (p.start_tick, _ROLE_RANK[p.role], _TRACK_RANK.get(p.track_id, 0))
    )
    return out


def section_span(section: FormSection) -> tuple[int, int]:
    start = section.start_bar * BAR
    return start, start + section.length_bars * BAR


def section_containing(form_sections: list[FormSection], tick: int) -> FormSection:
    """The section whose bar-span contains `tick` (there is exactly one)."""
    for section in form_sections:
        start, end = section_span(section)
        if start <= tick < end:
            return section
    raise ValueError(f"no section contains tick {tick}")


def get_or_create_drum_builder(
    builders: list[Builder], span: tuple[int, int], track_id: str
) -> Builder:
    """The section's drum `Builder` for `track_id`, created empty if the groove
    lacked that voice-track (a fill may introduce toms; the crash track never
    exists until stage 6 adds it) — §3.3 / §3.7."""
    for b in builders:
        if b.role == "drums" and b.track_id == track_id and b.start_tick == span[0]:
            return b
    created = Builder(track_id, "drums", span[0], span[1], [])
    builders.append(created)
    return created


def instantiate_fill_event(
    event: DrumEvent, bar_start: int, plan: GenerationPlan
) -> tuple[str, PhraseNote]:
    """A fill `DrumEvent` → its `(track_id, PhraseNote)`, exactly as
    `_generate_drums` instantiates a groove hit (velocity shift applied — §3.3),
    then tagged `"fill"`. `midi=None`; Phase-7 timbres supply the trigger pitch."""
    voice: DrumVoice = event.voice
    dur = event.dur if event.dur is not None else _DEFAULT_DUR[voice]
    note = PhraseNote(
        ticks=bar_start + event.pos,
        duration_ticks=dur,
        midi=None,
        velocity=apply_velocity(event.velocity, plan.budgets.dynamics_base),
        tags=["fill"],
    )
    return _VOICE_TRACK[voice], note


def crash_velocity(pack: StylePack, energy: float) -> float:
    """§3.7 entry-crash velocity: `round3(lo + energy × (hi − lo))`, absolute
    (the §3.4 mood shift is *not* applied — the pack range encodes loudness)."""
    assert pack.transitions is not None
    lo, hi = pack.transitions.crash.velocity
    return round(lo + energy * (hi - lo), 3)


def add_crash_and_kick(
    builders: list[Builder],
    section: FormSection,
    tick: int,
    velocity: float,
    tag: str,
    *,
    guard_existing_kick: bool,
) -> None:
    """Add a `crash` (dur 1440) and — subject to the double-hit guard — a `kick`
    at `tick`, both at `velocity` (absolute) with `tag`. §3.7 (entry, guarded)
    and §3.6 (HOLD, unguarded, drums already cleared). Crash → `crash` track,
    kick → `kick` track; both created if absent."""
    span = section_span(section)
    crash_bld = get_or_create_drum_builder(builders, span, "crash")
    crash_bld.notes.append(
        PhraseNote(
            ticks=tick,
            duration_ticks=_DEFAULT_DUR["crash"],
            midi=None,
            velocity=velocity,
            tags=[tag],
        )
    )
    kick_bld = get_or_create_drum_builder(builders, span, "kick")
    if guard_existing_kick and any(n.ticks == tick for n in kick_bld.notes):
        return
    kick_bld.notes.append(
        PhraseNote(
            ticks=tick,
            duration_ticks=_DEFAULT_DUR["kick"],
            midi=None,
            velocity=velocity,
            tags=[tag],
        )
    )
