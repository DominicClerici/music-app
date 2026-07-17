"""Part-generator dispatcher (PHASE_5 §6 + §8.2).

`generate(role, …)` is the per-role entry point the Chunk-4 orchestrator (§8.1)
loops over `[drums, bass, comping, pads]`. It owns the §6 shared instantiation
loop — tile the selected pattern across each active section's phrases (§3.2),
gate on density (§3.5), retarget each event (§3.3), apply §3.4 velocity /
articulation — and dispatches the four role shapes:

- **drums** (§6.1): each `DrumEvent` → a trigger note on its §8.2 voice-track
  (`midi = None`, Phase-7 timbres supply the pitch); one `Phrase` per active
  voice-track per section.
- **bass** — on `pack.bass_mode`: `walking` routes to the T2 walker (§6.3);
  `patterns` instantiates the selected bass pattern (single-degree retarget).
- **comping/pads** (§6.4/§6.5): rhythm from `degree: chord` hits, pitches from
  the T1 voicing map; pads are articulation-exempt.

Draw-free for the pattern roles (selection already drew; the walker owns the
bass-walking draws). No `random`, no clock (ROADMAP invariant 5).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from trackgen.packs.models import (
    DrumEvent,
    DrumVoice,
    PatternEnvelope,
    PitchedEvent,
    StylePack,
)
from trackgen.parts.dynamics import (
    apply_articulation,
    apply_velocity,
    articulation_scales,
    is_event_active,
)
from trackgen.parts.retarget import VoicingFor, retarget_event
from trackgen.parts.selection import SelectionResult
from trackgen.parts.voicing import build_voicing_map
from trackgen.parts.walker import walk
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementEntry,
    ArrangementPlan,
    ChordEvent,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    PhraseNote,
    Register,
    SongForm,
)

_BAR = 1920

# §8.2 drum voice → track map (engine data, pinned). `crash` is Phase-6's — a
# main never authors it (a stray one stays dropped in `_generate_drums`), but
# stage 6 (transitions) is the first crash *producer*, so the voice→track and
# track-order entries live here (PHASE_6 §10.7 / SESSION_10 §2.4).
_VOICE_TRACK: dict[DrumVoice, str] = {
    "kick": "kick",
    "snare": "snare",
    "hat_closed": "hats",
    "hat_open": "hats",
    "ride": "ride",
    "crash": "crash",
    "tom_low": "tom_low",
    "tom_mid": "tom_mid",
    "tom_high": "tom_high",
    "perc": "perc",
}

# §8.2 default `durationTicks` per voice when the event authors none. The general
# default (kick/snare and the un-tabulated toms/perc) is 120; the tabulated
# exceptions are the metal/cymbal voices.
_DEFAULT_DUR: dict[DrumVoice, int] = {
    "kick": 120,
    "snare": 120,
    "hat_closed": 60,
    "hat_open": 360,
    "ride": 240,
    "tom_low": 120,
    "tom_mid": 120,
    "tom_high": 120,
    "perc": 120,
    # crash is emitted only by Phase-6 stage 6 (entry crashes + the HOLD final
    # hit); a main never authors it. Default dur 1440 per PHASE_6 §10.7 (added to
    # the §8.2 defaults) — single-sourced here for the transitions crash builder.
    "crash": 1440,
}

# Deterministic Phrase order for the drum voice-tracks a section emits. `crash`
# is only ever produced by stage 6 (entry/HOLD crashes) but is ordered here for
# a single source of truth (PHASE_6 §10.7).
_TRACK_ORDER: tuple[str, ...] = (
    "kick",
    "snare",
    "hats",
    "ride",
    "crash",
    "tom_low",
    "tom_mid",
    "tom_high",
    "perc",
)


def generate(
    role: Role,
    arrangement: ArrangementPlan,
    harmony: HarmonicPlan,
    form: SongForm,
    plan: GenerationPlan,
    pack: StylePack,
    selection: SelectionResult,
    *,
    master: int,
    overrides: dict[str, int],
    prior_phrases: Sequence[Phrase] = (),
) -> list[Phrase]:
    """The `role`'s Phrases across every active section (§6).

    One `Phrase` per (track, section): a pitched role emits a single-track Phrase
    per section; drums emit one per active voice-track. `prior_phrases` is the
    reserved §4.4 drums→bass→comping→pads handoff — accepted, not consumed in v1.
    """
    if role == "drums":
        return _generate_drums(arrangement, form, plan, selection)
    if role == "bass":
        if pack.bass_mode == "walking":
            return _generate_walking_bass(
                arrangement,
                harmony,
                form,
                plan,
                pack,
                master=master,
                overrides=overrides,
            )
        return _generate_instantiated(
            role, arrangement, harmony, form, plan, pack, selection, voicing_for=None
        )
    # comping / pads: voiced roles.
    chords = harmony.chords
    voicing_map = build_voicing_map(role, arrangement, chords, pack)

    def voicing_for(chord_event: ChordEvent) -> Sequence[int]:
        return voicing_map[chord_event.start_tick]

    return _generate_instantiated(
        role, arrangement, harmony, form, plan, pack, selection, voicing_for=voicing_for
    )


# --- shared tiling ------------------------------------------------------------


def _section_span(section: FormSection) -> tuple[int, int]:
    start = section.start_bar * _BAR
    return start, start + section.length_bars * _BAR


def _active_entries(
    arrangement: ArrangementPlan, role: Role
) -> dict[str, ArrangementEntry]:
    return {
        entry.section_id: entry
        for entry in arrangement.entries
        if entry.role == role and entry.active
    }


def _tile(
    section: FormSection, env: PatternEnvelope
) -> list[tuple[int, PitchedEvent | DrumEvent]]:
    """Tile `env` across the section's phrases (§3.2), returning `(abs_tick,
    event)` pairs in tick order.

    Tiling resets at each phrase start; a tile steps by `env.length_ticks` and an
    event landing at or past the phrase end is truncated. All reference patterns
    are 1–2 bars and phrases a multiple of 4 bars, so tiles fit exactly — the
    truncation guard only bites on synthetic mismatches.
    """
    tiled: list[tuple[int, PitchedEvent | DrumEvent]] = []
    phrase_start, _ = _section_span(section)
    for phrase in section.phrases:
        phrase_end = phrase_start + phrase.bars * _BAR
        tile_start = phrase_start
        while tile_start < phrase_end:
            for event in env.events:
                abs_tick = tile_start + event.pos
                if abs_tick >= phrase_end:
                    continue
                tiled.append((abs_tick, event))
            tile_start += env.length_ticks
        phrase_start = phrase_end
    tiled.sort(key=lambda pair: pair[0])
    return tiled


# --- drums (§6.1 + §8.2) ------------------------------------------------------


def _generate_drums(
    arrangement: ArrangementPlan,
    form: SongForm,
    plan: GenerationPlan,
    selection: SelectionResult,
) -> list[Phrase]:
    dynamics_base = plan.budgets.dynamics_base
    entries = _active_entries(arrangement, "drums")

    phrases: list[Phrase] = []
    for section in form.sections:
        entry = entries.get(section.id)
        if entry is None:
            continue
        env = selection.by_section[(section.id, "drums")]
        span = _section_span(section)

        by_track: dict[str, list[PhraseNote]] = defaultdict(list)
        for abs_tick, event in _tile(section, env):
            assert isinstance(event, DrumEvent)
            if not is_event_active(event.min_density, entry.density_budget):
                continue
            if event.voice == "crash":
                continue
            track = _VOICE_TRACK[event.voice]
            dur = event.dur if event.dur is not None else _DEFAULT_DUR[event.voice]
            # Internal engine-provenance tags (PHASE_6 §3.7 resolution): the
            # source `voice` (both hat voices collapse to the `hats` track, so
            # `hat_closed`/`hat_open` are otherwise indistinguishable) and an
            # `ornament` marker for `minDensity`-gated events (consumed at
            # instantiation, otherwise lost). Stage-6 mutation reads these;
            # serialize (`_to_event`) drops all tags, so they never reach the
            # `TrackDocument` contract (they are NOT §3.9 contributed tags).
            tags: list[str] = [event.voice]
            if event.min_density is not None:
                tags.append("ornament")
            by_track[track].append(
                PhraseNote(
                    ticks=abs_tick,
                    duration_ticks=dur,
                    midi=None,
                    velocity=apply_velocity(event.velocity, dynamics_base),
                    tags=tags,
                )
            )

        for track in _TRACK_ORDER:
            notes = by_track.get(track)
            if not notes:
                continue
            notes.sort(key=_note_sort_key)
            phrases.append(
                Phrase(
                    track_id=track,
                    role="drums",
                    start_tick=span[0],
                    end_tick=span[1],
                    notes=notes,
                )
            )
    return phrases


# --- bass: walking mode (§6.3 dispatch) ---------------------------------------


def _generate_walking_bass(
    arrangement: ArrangementPlan,
    harmony: HarmonicPlan,
    form: SongForm,
    plan: GenerationPlan,
    pack: StylePack,
    *,
    master: int,
    overrides: dict[str, int],
) -> list[Phrase]:
    dynamics_base = plan.budgets.dynamics_base
    walked = walk(
        arrangement, harmony, form, plan, pack, master=master, overrides=overrides
    )
    entries = _active_entries(arrangement, "bass")

    phrases: list[Phrase] = []
    for section in form.sections:
        if section.id not in entries:
            continue
        span = _section_span(section)
        # Walker is articulation-exempt: durations + tags pass through; only the
        # §3.4 velocity shift applies.
        notes = [
            PhraseNote(
                ticks=wn.ticks,
                duration_ticks=wn.duration_ticks,
                midi=wn.midi,
                velocity=apply_velocity(wn.velocity, dynamics_base),
                tags=list(wn.tags),
            )
            for wn in walked.get(section.id, [])
        ]
        notes.sort(key=_note_sort_key)
        phrases.append(
            Phrase(
                track_id="bass",
                role="bass",
                start_tick=span[0],
                end_tick=span[1],
                notes=notes,
            )
        )
    return phrases


# --- pitched instantiation: pattern-bass + comping + pads ---------------------


def _generate_instantiated(
    role: Role,
    arrangement: ArrangementPlan,
    harmony: HarmonicPlan,
    form: SongForm,
    plan: GenerationPlan,
    pack: StylePack,
    selection: SelectionResult,
    *,
    voicing_for: VoicingFor | None,
) -> list[Phrase]:
    """The shared §6 loop for the three pitched instantiation roles.

    `scale` (whether §3.4 articulation applies) is `articulation_scales(role)`:
    True for comping and pattern-mode bass, False for pads. When it applies, the
    authored duration is scaled then clamped to the gap to the same track's next
    *surviving* (post-gating) event; the clamped duration is what `retarget_event`
    splits for `onChordChange`. Velocity is the §3.4 mood shift on every note.
    """
    chords = harmony.chords
    dynamics_base = plan.budgets.dynamics_base
    legato = plan.budgets.articulation_legato
    scale = articulation_scales(role)
    entries = _active_entries(arrangement, role)

    phrases: list[Phrase] = []
    for section in form.sections:
        entry = entries.get(section.id)
        if entry is None:
            continue
        env = selection.by_section[(section.id, role)]
        assert env.retarget is not None  # PT9: pitched patterns carry retarget.
        pattern_register = Register(
            low_midi=env.retarget.register_low, high_midi=env.retarget.register_high
        )
        span = _section_span(section)

        active = [
            (abs_tick, event)
            for abs_tick, event in _tile(section, env)
            if is_event_active(event.min_density, entry.density_budget)
        ]

        notes: list[PhraseNote] = []
        for i, (abs_tick, event) in enumerate(active):
            assert isinstance(event, PitchedEvent)
            # Gap to the next surviving same-track event (None past the last, so it
            # rings out). `max(1, …)` guards the degenerate coincident-onset case
            # (two pitched hits at one pos): a 0 gap would clamp the duration to 0
            # and violate PhraseNote's `>= 1`. No reference pattern authors this;
            # purely defensive against synthetic/future banks.
            gap = (
                max(1, active[i + 1][0] - abs_tick)
                if scale and i + 1 < len(active)
                else None
            )
            dur = apply_articulation(event.dur, legato, scale=scale, gap_ticks=gap)
            velocity = apply_velocity(event.velocity, dynamics_base)
            for note in retarget_event(
                degree=event.degree,
                octave=event.octave,
                push=event.push,
                ticks=abs_tick,
                duration_ticks=dur,
                chords=chords,
                role=role,
                lane=entry.register,
                pattern_register=pattern_register,
                on_chord_change=env.retarget.on_chord_change,
                voicing_for=voicing_for,
            ):
                notes.append(
                    PhraseNote(
                        ticks=note.ticks,
                        duration_ticks=note.duration_ticks,
                        midi=note.midi,
                        velocity=velocity,
                        tags=list(note.tags),
                    )
                )

        notes.sort(key=_note_sort_key)
        phrases.append(
            Phrase(
                track_id=role,
                role=role,
                start_tick=span[0],
                end_tick=span[1],
                notes=notes,
            )
        )
    return phrases


def _note_sort_key(note: PhraseNote) -> tuple[int, int]:
    """§6 emit order: `(ticks, midi)`; a `None` (drum) pitch sorts first."""
    return (note.ticks, note.midi if note.midi is not None else -1)
