"""Walking-bass engine — the walker (PHASE_5 §6.3).

The bass part generator for `bass_mode == "walking"` packs. Where the pattern
banks author fixed degree cells, the walker *composes* a bass line per bar from
the harmony, an intensity-driven feel (two-feel / four-feel), and per-bar random
draws. Its only entropy is the §3.6 per-bar sub-stream; everything else is a pure
function of the harmony/arrangement/pack (ROADMAP invariant 5).

Output is one ordered `WalkNote` list per active-bass section, carrying the
*authored* (pre-§3.4) velocities and the fixed §6.3-tail durations. The generator
(Chunk 3) applies the mood velocity shift; the walker is articulation-exempt so
durations are final.

Draw discipline (§3.6, load-bearing for the §9.2 golden draw counts): draws go
only through `weighted_choice` and only when a candidate list has **≥ 2** entries
— a singleton or forced pick consumes *zero* draws. Candidate lists are
materialized in ascending pitch order before drawing, and within a bar the draw
order is fixed: beat-1 decay (if drawn) → beat 3 → beat 2 → approach type. Each
bar draws on its own RNG (`rng_factory(absBar)`), so bars are independently
reproducible and a changed draw in one bar can never shift another.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from trackgen.arrangement.intensity import intensity
from trackgen.packs.models import StylePack, WalkingConfig
from trackgen.schema.ir import (
    ArrangementPlan,
    ChordEvent,
    ChordSpec,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Register,
    SongForm,
)
from trackgen.seeds import Rng, derive, stream_seed, weighted_choice
from trackgen.theory import QUALITY_INTERVALS, chord_tones, scale_pcs

# --- grid + authored constants (§6.3 tail) -----------------------------------

_BAR = 1920
_BEAT = 480
_HALF = 960
_AND_OF_4 = 1680  # the eighth after beat 4 (beat 4 + a half-beat)

_V_FOUR_BEAT1 = 0.75
_V_FOUR_REST = 0.68
_V_TWO_BEAT1 = 0.72
_V_TWO_REST = 0.68  # beat 3 and the beat-4 approach
_V_FINAL = 0.75
_V_GHOST = 0.25

_DUR_TWO = 960
_DUR_FOUR = 480
_DUR_FINAL = 1920
_DUR_GHOST = 60

# Draw a section-start reference pitch from the lane floor: `nearest(pc, low)` is
# always the lowest in-lane placement of `pc`, which is where a walked section
# begins (§9.2 head-1/solo-1 both open on the lowest root).
_SECTION_START_REF = None


class WalkNote(NamedTuple):
    """One walked bass note, authored (pre-§3.4) velocity and fixed duration.

    `tags` carries the §6.3 vocabulary the generator forwards verbatim — only
    `("ghost",)` for the dead-note embellishment; every melodic note is untagged.
    """

    ticks: int
    duration_ticks: int
    midi: int
    velocity: float
    tags: tuple[str, ...]


# --- placement helpers --------------------------------------------------------


def _root_pc(chord: ChordSpec) -> int:
    """The bass note class: a slash `bass_pc` when present, else the chord root
    (the §3.3 bass-slash rule, applied to the walker's roots/targets)."""
    return chord.bass_pc if chord.bass_pc is not None else chord.root_pc


def _third_pc(chord: ChordSpec) -> int:
    return (chord.root_pc + QUALITY_INTERVALS[chord.quality][1]) % 12


def _fifth_pc(chord: ChordSpec) -> int:
    return (chord.root_pc + QUALITY_INTERVALS[chord.quality][2]) % 12


def nearest(pc: int, ref: int, lane: Register) -> int:
    """The in-lane pitch of class `pc` minimizing `(|p − ref|, p)` (§6.3).

    Ties resolve **downward** (the lower pitch wins), matching the Yamaha
    note-limit convention. Lanes span ≥ 12 semitones so an in-lane pitch of every
    class always exists.
    """
    candidates = [
        m for m in range(lane.low_midi, lane.high_midi + 1) if m % 12 == pc % 12
    ]
    return min(candidates, key=lambda p: (abs(p - ref), p))


def _fold_into_lane(midi: int, lane: Register) -> int:
    """Transpose `midi` by whole octaves to its nearest in-lane position, ties
    downward — the §6.3 "folded into the lane" step for approach pitches."""
    candidates = [
        midi + 12 * k
        for k in range(-12, 13)
        if lane.low_midi <= midi + 12 * k <= lane.high_midi
    ]
    return min(candidates, key=lambda p: (abs(p - midi), p))


def _chord_at(chords: list[ChordEvent], tick: int) -> ChordEvent:
    """The chord event governing `tick` — the last whose `start_tick ≤ tick`
    (the timeline tiles `[0, total)` gaplessly, so one always exists)."""
    governing = chords[0]
    for chord in chords:
        if chord.start_tick <= tick:
            governing = chord
        else:
            break
    return governing


def _draw_or_single[T](items: list[T], weights: list[int], rng: Rng) -> T:
    """§3.6 draw-iff-≥2: a singleton is taken with **zero** draws; a ≥2 list draws
    once via `weighted_choice`. `items` must already be in ascending-pitch order."""
    if len(items) == 1:
        return items[0]
    return weighted_choice(items, weights, rng)


# --- target + approach --------------------------------------------------------


def _next_target(
    bar_start: int,
    ref_midi: int,
    beat1_chord: ChordSpec,
    chords: list[ChordEvent],
    lane: Register,
    song_end: int,
) -> int:
    """The next bar's *target* — the root of the chord on the next downbeat,
    `nearest` to `ref_midi` (§6.3). At song end the current chord's root
    substitutes."""
    next_downbeat = bar_start + _BAR
    if next_downbeat >= song_end:
        target_pc = _root_pc(beat1_chord)
    else:
        target_pc = _root_pc(_chord_at(chords, next_downbeat).chord)
    return nearest(target_pc, ref_midi, lane)


def _draw_approach(
    target: int,
    scale: ChordEvent,
    walking: WalkingConfig,
    lane: Register,
    rng: Rng,
) -> int:
    """A beat-4 approach to `target`, its type drawn from `approachWeights`:
    `chromatic_below` → target−1, `dominant` → target+7, `diatonic` → first scale
    tone below the target. Each candidate is folded into the lane; the draw is
    over the (ascending-pitch) candidate set (§6.3 rule 5)."""
    scale_set = set(scale_pcs(scale.scale.root_pc, scale.scale.name))
    raw: dict[str, int] = {
        "chromatic_below": target - 1,
        "dominant": target + 7,
        "diatonic": _first_scale_tone_below(target, scale_set),
    }
    items: list[tuple[int, str, int]] = [
        (_fold_into_lane(raw[name], lane), name, weight)
        for name, weight in walking.approach_weights.items()
    ]
    items.sort(key=lambda t: (t[0], t[1]))
    midis = [t[0] for t in items]
    weights = [t[2] for t in items]
    return _draw_or_single(midis, weights, rng)


def _first_scale_tone_below(target: int, scale_set: set[int]) -> int:
    """The nearest pitch below `target` whose class is in `scale_set` (a scale
    has ≥ 5 classes, so one is found within an octave)."""
    for midi in range(target - 1, target - 13, -1):
        if midi % 12 in scale_set:
            return midi
    return target - 1


# --- four-feel inner beats ----------------------------------------------------


def _beat3(
    chord: ChordSpec,
    beat1: int,
    target: int,
    lane: Register,
    rng: Rng,
) -> int:
    """Beat 3, filled before beat 2 (strongest-first, §6.3 rule 3): in-lane
    chord-tone pitches within 7 of both beat 1 and the target, excluding both;
    weight 3 within 2 of the beat1↔target midpoint else 1. Empty → relax to
    within 12 of beat 1."""
    tone_pcs = set(chord_tones(chord))
    in_lane = [
        m for m in range(lane.low_midi, lane.high_midi + 1) if m % 12 in tone_pcs
    ]
    midpoint = (beat1 + target) / 2
    candidates = [
        m
        for m in in_lane
        if abs(m - beat1) <= 7 and abs(m - target) <= 7 and m != beat1 and m != target
    ]
    if not candidates:
        candidates = [
            m for m in in_lane if abs(m - beat1) <= 12 and m != beat1 and m != target
        ]
    if not candidates:
        # Degenerate lane/harmony: fall back to the nearest chord tone to beat 1.
        pool = [m for m in in_lane if m != beat1]
        return min(pool, key=lambda p: (abs(p - beat1), p)) if pool else beat1
    candidates.sort()
    weights = [3 if abs(m - midpoint) <= 2 else 1 for m in candidates]
    return _draw_or_single(candidates, weights, rng)


def _beat2(
    event: ChordEvent,
    beat1: int,
    beat3: int,
    lane: Register,
    rng: Rng,
) -> int:
    """Beat 2 (§6.3 rule 4): in-lane chord + scale tones 1–4 semitones from beat
    1, excluding beat 3; weight 3 if ≤ 2 (stepwise). Empty → relax to within 7."""
    pcs = set(chord_tones(event.chord)) | set(
        scale_pcs(event.scale.root_pc, event.scale.name)
    )
    in_lane = [m for m in range(lane.low_midi, lane.high_midi + 1) if m % 12 in pcs]
    candidates = [m for m in in_lane if 1 <= abs(m - beat1) <= 4 and m != beat3]
    if not candidates:
        candidates = [m for m in in_lane if 1 <= abs(m - beat1) <= 7 and m != beat3]
    if not candidates:
        pool = [m for m in in_lane if m != beat1 and m != beat3]
        return min(pool, key=lambda p: (abs(p - beat1), p)) if pool else beat1
    candidates.sort()
    weights = [3 if abs(m - beat1) <= 2 else 1 for m in candidates]
    return _draw_or_single(candidates, weights, rng)


def _beat1_decay(
    chord: ChordSpec,
    ref: int,
    walking: WalkingConfig,
    lane: Register,
    rng: Rng,
) -> int:
    """The 2nd+-consecutive-same-chord beat 1: degree drawn from
    `beat1RepeatWeights` (root-obligation decay, §6.3 rule 1), placed `nearest`
    to the previous pitch."""
    degree_pc = {
        "root": _root_pc(chord),
        "third": _third_pc(chord),
        "fifth": _fifth_pc(chord),
    }
    items: list[tuple[int, str, int]] = [
        (nearest(degree_pc[name], ref, lane), name, weight)
        for name, weight in walking.beat1_repeat_weights.items()
    ]
    items.sort(key=lambda t: (t[0], t[1]))
    midis = [t[0] for t in items]
    weights = [t[2] for t in items]
    return _draw_or_single(midis, weights, rng)


# --- per-bar composition ------------------------------------------------------


def _two_feel_bar(
    bar_start: int,
    beat1_chord: ChordEvent,
    prev: int | None,
    lane: Register,
    density: float,
    chords: list[ChordEvent],
    song_end: int,
    rng: Rng,
) -> tuple[list[WalkNote], int]:
    """A two-feel bar (half notes, dur 960): §6.3 rules 2–3. Returns the notes
    and the pitch to carry forward."""
    beat3_chord = _chord_at(chords, bar_start + _HALF)
    ref = lane.low_midi if prev is None else prev

    if beat3_chord is not beat1_chord:
        # Two chords: one half-note root each, stating each relaunch chord.
        b1 = nearest(_root_pc(beat1_chord.chord), ref, lane)
        b3 = nearest(_root_pc(beat3_chord.chord), b1, lane)
        return (
            [
                WalkNote(bar_start, _DUR_TWO, b1, _V_TWO_BEAT1, ()),
                WalkNote(bar_start + _HALF, _DUR_TWO, b3, _V_TWO_REST, ()),
            ],
            b3,
        )

    # One chord: beat-1 root, beat-3 fifth a P4 below or P5 above beat 1.
    b1 = nearest(_root_pc(beat1_chord.chord), ref, lane)
    below, above = b1 - 5, b1 + 7
    fits = [p for p in (below, above) if lane.low_midi <= p <= lane.high_midi]
    fits.sort()
    b3 = _draw_or_single(fits, [1] * len(fits), rng)
    notes = [
        WalkNote(bar_start, _DUR_TWO, b1, _V_TWO_BEAT1, ()),
        WalkNote(bar_start + _HALF, _DUR_TWO, b3, _V_TWO_REST, ()),
    ]
    last = b3

    # Beat-4 quarter approach when the next bar changes chord and density allows.
    next_downbeat = bar_start + _BAR
    changes = (
        next_downbeat < song_end
        and _chord_at(chords, next_downbeat).chord != beat1_chord.chord
    )
    if changes and density >= 0.55:
        target = _next_target(bar_start, b1, beat1_chord.chord, chords, lane, song_end)
        approach = _fold_into_lane(target - 1, lane)
        notes.append(
            WalkNote(bar_start + 3 * _BEAT, _DUR_FOUR, approach, _V_TWO_REST, ())
        )
        last = approach
    return notes, last


def _four_feel_bar(
    bar_start: int,
    bar_in_section: int,
    beat1_chord: ChordEvent,
    prev: int | None,
    lane: Register,
    density: float,
    tempo_bpm: float,
    decay: bool,
    chords: list[ChordEvent],
    song_end: int,
    walking: WalkingConfig,
    rng: Rng,
) -> tuple[list[WalkNote], int]:
    """A four-feel bar (quarter notes, dur 480): §6.3 rules 1–6. Draw order is
    fixed: beat-1 decay (if any) → beat 3 → beat 2 → approach."""
    beat3_chord = _chord_at(chords, bar_start + _HALF)
    ref = lane.low_midi if prev is None else prev
    pos = [bar_start + i * _BEAT for i in range(4)]

    if beat3_chord is not beat1_chord:
        # Two chords: root(1), approach(→c2 root), root(2), approach(→next target).
        b1 = nearest(_root_pc(beat1_chord.chord), ref, lane)
        target2 = nearest(_root_pc(beat3_chord.chord), b1, lane)
        b2 = _draw_approach(target2, beat1_chord, walking, lane, rng)
        b3 = nearest(_root_pc(beat3_chord.chord), b2, lane)
        target = _next_target(bar_start, b1, beat3_chord.chord, chords, lane, song_end)
        b4 = _draw_approach(target, beat3_chord, walking, lane, rng)
    else:
        # One chord: beat 1 (root or decay draw), then beat 3, beat 2, approach.
        if decay:
            b1 = _beat1_decay(beat1_chord.chord, ref, walking, lane, rng)
        else:
            b1 = nearest(_root_pc(beat1_chord.chord), ref, lane)
        target = _next_target(bar_start, b1, beat1_chord.chord, chords, lane, song_end)
        b3 = _beat3(beat1_chord.chord, b1, target, lane, rng)
        b2 = _beat2(beat1_chord, b1, b3, lane, rng)
        b4 = _draw_approach(target, beat1_chord, walking, lane, rng)

    notes = [
        WalkNote(pos[0], _DUR_FOUR, b1, _V_FOUR_BEAT1, ()),
        WalkNote(pos[1], _DUR_FOUR, b2, _V_FOUR_REST, ()),
        WalkNote(pos[2], _DUR_FOUR, b3, _V_FOUR_REST, ()),
        WalkNote(pos[3], _DUR_FOUR, b4, _V_FOUR_REST, ()),
    ]

    # Embellishment: a dead-note ghost on the and-of-4 repeating the beat-4 pitch.
    period = 4 if density < 0.55 else 2
    if bar_in_section % period == period - 1 and tempo_bpm <= 200:
        notes.append(
            WalkNote(bar_start + _AND_OF_4, _DUR_GHOST, b4, _V_GHOST, ("ghost",))
        )

    notes.sort(key=lambda w: (w.ticks, w.midi))
    return notes, b4


# --- section + entry point ----------------------------------------------------


def _walk_section(
    section: FormSection,
    feel: str,
    lane: Register,
    density: float,
    tempo_bpm: float,
    chords: list[ChordEvent],
    walking: WalkingConfig,
    rng_factory: Callable[[int], Rng],
    song_end: int,
    is_final_section: bool,
) -> list[WalkNote]:
    """Walk one active-bass section, threading pitch state (reset here) across
    its bars in absolute order."""
    notes: list[WalkNote] = []
    prev: int | None = _SECTION_START_REF
    prev_full_spec: ChordSpec | None = None
    same_run = 0

    for bar_in_section in range(section.length_bars):
        abs_bar = section.start_bar + bar_in_section
        bar_start = abs_bar * _BAR
        rng = rng_factory(abs_bar)
        beat1_chord = _chord_at(chords, bar_start)
        two_chords = _chord_at(chords, bar_start + _HALF) is not beat1_chord

        # Consecutive-same-chord run (single-chord bars only) → decay obligation.
        if not two_chords and beat1_chord.chord == prev_full_spec:
            same_run += 1
        else:
            same_run = 0 if two_chords else 1
        prev_full_spec = None if two_chords else beat1_chord.chord

        if feel == "two":
            if is_final_section and bar_in_section == section.length_bars - 1:
                # Final-bar rule: one whole-note root at the lowest in-lane pitch.
                midi = nearest(_root_pc(beat1_chord.chord), lane.low_midi, lane)
                notes.append(WalkNote(bar_start, _DUR_FINAL, midi, _V_FINAL, ()))
                break
            bar_notes, prev = _two_feel_bar(
                bar_start, beat1_chord, prev, lane, density, chords, song_end, rng
            )
        else:
            decay = not two_chords and same_run >= 2
            bar_notes, prev = _four_feel_bar(
                bar_start,
                bar_in_section,
                beat1_chord,
                prev,
                lane,
                density,
                tempo_bpm,
                decay,
                chords,
                song_end,
                walking,
                rng,
            )
        notes.extend(bar_notes)
    return notes


def walk(
    arrangement: ArrangementPlan,
    harmony: HarmonicPlan,
    form: SongForm,
    plan: GenerationPlan,
    pack: StylePack,
    *,
    master: int,
    overrides: dict[str, int],
    rng_factory: Callable[[int], Rng] | None = None,
) -> dict[str, list[WalkNote]]:
    """Walk the bass for every active-bass section (§6.3).

    Returns `{section_id: [WalkNote, …]}` for each section where the bass role is
    active, each list tick-ordered with authored (pre-§3.4) velocities. Only runs
    when `pack.bass_mode == "walking"`; otherwise returns an empty map.

    `master`/`overrides` derive the default per-bar RNGs
    (`Rng(derive(derive(stream_seed(master, overrides, "bass"), "walk"),
    f"bar:{absBar}"))`, §3.6). `rng_factory` overrides that derivation — it maps
    an absolute bar index to that bar's RNG, so tests can inject counting shims.
    """
    if pack.bass_mode != "walking" or pack.walking is None:
        return {}
    walking = pack.walking

    make_rng: Callable[[int], Rng]
    if rng_factory is None:
        walk_seed = derive(stream_seed(master, overrides, "bass"), "walk")

        def make_rng(abs_bar: int) -> Rng:
            return Rng(derive(walk_seed, f"bar:{abs_bar}"))

    else:
        make_rng = rng_factory

    chords = list(harmony.chords)
    song_end = form.total_bars * _BAR
    sections = list(form.sections)
    final_section = sections[-1] if sections else None

    bass_entries = {
        entry.section_id: entry for entry in arrangement.entries if entry.role == "bass"
    }

    result: dict[str, list[WalkNote]] = {}
    for section in sections:
        entry = bass_entries.get(section.id)
        if entry is None or not entry.active:
            continue
        rung = intensity(section.energy)
        feel = walking.feel_by_intensity[rung]
        result[section.id] = _walk_section(
            section,
            feel,
            entry.register,
            entry.density_budget,
            plan.tempo_bpm,
            chords,
            walking,
            make_rng,
            song_end,
            is_final_section=section is final_section,
        )
    return result
