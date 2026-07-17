"""Stage 7 — the note-count-preserving Humanizer (PHASE_6 §5).

`humanize(phrases, form, plan) -> (Phrase[], Tempo[])` renders performance feel
onto the note-structural output of stage 6 **without adding or removing a note**:
it only adjusts `ticks`, `duration_ticks`, and `velocity`; `midi` and `tags`
pass through untouched. Per-note operation order (D9):

    swing -> offset -> timing jitter -> velocity accent -> velocity jitter -> duration

All timing math runs in float ms/ticks and rounds to integer ticks exactly once,
at emit (half-even). The deterministic sub-passes (swing §5.2, offset §5.3,
accent §5.5, bass legato §5.6) consume no RNG; only the two jitter passes draw,
on per-`(role, absBar)` sub-streams (§5.8).

The stochastic jitter is applied through an injectable strategy so the
deterministic transform is observable through the real production path (a
zero-jitter strategy yields the §7.2 pre-jitter positions without touching any
RNG). Production composes the deterministic pass with `_TriangularJitter`.

The second return value is the ritard tempo curve (§5.7): a `ritard` close emits
the sampled Friberg-Sundberg tempo events; `cold`/`fade` emit `[]`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from trackgen.humanize.feel import FeelData, OffsetProfile, load_feel
from trackgen.humanize.ritard import ritard_events
from trackgen.humanize.swing import swing_phrase
from trackgen.parts.generators import _note_sort_key
from trackgen.schema.document import Tempo
from trackgen.schema.ir import GenerationPlan, Phrase, PhraseNote, SongForm
from trackgen.seeds import Rng, derive, stream_seed

BAR = 1920
BEAT = 480

_TOM_TRACKS = frozenset({"tom_low", "tom_mid", "tom_high"})
_BASS_LEGATO_GAP = 60


# --- the pinned triangular helper (§5.4) --------------------------------------


def tri(rng: Rng, w: int) -> int:
    """Triangular integer jitter on `[-w, +w]`, SD ~ w/2.45 (§5.4).

    Two `randrange` draws; the caller guards `w == 0` (a zero-width call still
    consumes RNG state via `randrange(1)`, so the draw-skip lives at the call
    site — see `_TriangularJitter`).
    """
    return rng.randrange(w + 1) + rng.randrange(w + 1) - w


class _Jitter(Protocol):
    """Strategy for the two stochastic passes (§5.4/§5.5).

    `timing`/`velocity` own the `w >= 1` / `W >= 1` draw-skip so a zero-width
    call consumes no RNG.
    """

    def timing(self, rng: Rng, w: int) -> int: ...

    def velocity(self, rng: Rng, width: int) -> float: ...


class _TriangularJitter:
    """Production jitter: `tri` at `w >= 1`, no draw otherwise (§5.4/§5.5)."""

    def timing(self, rng: Rng, w: int) -> int:
        return tri(rng, w) if w >= 1 else 0

    def velocity(self, rng: Rng, width: int) -> float:
        return tri(rng, width) / 1000 if width >= 1 else 0.0


class _ZeroJitter:
    """The testability seam: applies no jitter and draws nothing, so the real
    production path yields the §7.2 pre-jitter positions (§11.5, DoD 5)."""

    def timing(self, rng: Rng, w: int) -> int:
        return 0

    def velocity(self, rng: Rng, width: int) -> float:
        return 0.0


_PRODUCTION_JITTER: _Jitter = _TriangularJitter()


def _vel_jitter_width(base: float, range_scale: float, dynamics_range: float) -> int:
    """The velocity-jitter width in thousandths (§5.5): `round(1000 × (base +
    rangeScale × dynamicsRange))` (0.21 → 57, 0.35 → 68)."""
    return round(1000 * (base + range_scale * dynamics_range))


# --- per-note working record --------------------------------------------------


@dataclass
class _Rec:
    phrase_idx: int
    src: PhraseNote
    grid_tick: int
    abs_bar: int
    voice: str
    role: str
    track_id: str
    sort_midi: int
    pos: float
    dur: int
    vel: float


def _beat_class(grid_tick: int) -> str:
    pos = grid_tick % BAR
    if pos == 0:
        return "down"
    if pos == BEAT:
        return "back2"
    if pos == 2 * BEAT:
        return "beat3"
    if pos == 3 * BEAT:
        return "back4"
    return "off"


def _voice_of(phrase: Phrase) -> str:
    """The feel voice/role a note keys by (§5.3, integration fact 2): drums by
    `track_id` (toms collapse to one row), pitched roles by `role`."""
    if phrase.role == "drums":
        return "toms" if phrase.track_id in _TOM_TRACKS else phrase.track_id
    return phrase.role


# --- the engine ---------------------------------------------------------------


def humanize(
    phrases: list[Phrase], form: SongForm, plan: GenerationPlan
) -> tuple[list[Phrase], list[Tempo]]:
    """Render performance feel onto `phrases` (§5); note-count-preserving.

    Returns the humanized phrases and the ritard tempo events (§5.7 — empty
    unless `ending.close == "ritard"`).
    """
    return _run(phrases, form, plan, _PRODUCTION_JITTER)


def _run(
    phrases: list[Phrase],
    form: SongForm,
    plan: GenerationPlan,
    jitter: _Jitter,
) -> tuple[list[Phrase], list[Tempo]]:
    feel = load_feel()
    ticks_per_ms = 480 * plan.tempo_bpm / 60000
    song_end = form.total_bars * BAR
    profile = feel.offsets_ms.straight if plan.swing is None else feel.offsets_ms.swung
    # A future PHASE_8 `feelTable` pack selector would replace this swing-derived
    # default and require threading the pack into this signature (out of scope).

    records = _deterministic_pass(phrases, plan, feel, profile, ticks_per_ms)
    _jitter_pass(records, plan, feel, ticks_per_ms, jitter)
    out = _emit(phrases, records, song_end)
    return out, _ritard(form, plan)


def _deterministic_pass(
    phrases: list[Phrase],
    plan: GenerationPlan,
    feel: FeelData,
    profile: OffsetProfile,
    ticks_per_ms: float,
) -> list[_Rec]:
    """Swing (§5.2) -> offset (§5.3) -> accent (§5.5 step 1) -> bass legato
    (§5.6). Draws nothing; the beat class is fixed from the pre-swing grid tick."""
    records: list[_Rec] = []
    for pi, phrase in enumerate(phrases):
        voice = _voice_of(phrase)
        swung = swing_phrase(phrase.notes, plan.swing)
        for note, (new_start, new_dur) in zip(phrase.notes, swung, strict=True):
            beat_class = _beat_class(note.ticks)
            offset_ms = profile.offset(voice, beat_class)
            records.append(
                _Rec(
                    phrase_idx=pi,
                    src=note,
                    grid_tick=note.ticks,
                    abs_bar=note.ticks // BAR,
                    voice=voice,
                    role=phrase.role,
                    track_id=phrase.track_id,
                    sort_midi=note.midi if note.midi is not None else -1,
                    pos=new_start + offset_ms * ticks_per_ms,
                    dur=new_dur,
                    vel=note.velocity + feel.accent.at(beat_class),
                )
            )
    # Bass legato is TRACK-level (§5.6): the next-attack search spans every bass
    # phrase in grid order, so only the single globally-final bass note is exempt.
    _apply_bass_legato([r for r in records if r.role == "bass"], feel.bass_legato)
    return records


def _apply_bass_legato(recs: list[_Rec], bass_legato: float) -> None:
    """§5.6 — stretch a bass note to ~`bassLegato` of the grid IOI when it abuts
    the same track's next attack (`gap <= 60`); the globally-final bass note (no
    successor) is untouched. `recs` is the whole bass track across all phrases."""
    grid_ticks = sorted({r.grid_tick for r in recs})
    next_of = {g: nxt for g, nxt in zip(grid_ticks, grid_ticks[1:], strict=False)}
    for r in recs:
        nxt = next_of.get(r.grid_tick)
        if nxt is None:
            continue
        ioi = nxt - r.grid_tick
        if ioi - r.dur <= _BASS_LEGATO_GAP:
            r.dur = round(bass_legato * ioi)


def _jitter_pass(
    records: list[_Rec],
    plan: GenerationPlan,
    feel: FeelData,
    ticks_per_ms: float,
    jitter: _Jitter,
) -> None:
    """The two stochastic passes (§5.4/§5.5), one RNG per `(role, absBar)`.

    The `drums` role covers all its voice-tracks — every drum note of a bar is
    gathered into one stream and processed in `(gridTicks, trackId, midi|-1)`
    order; per note, timing draws (2 iff `w >= 1`) then velocity draws (2 iff
    `W >= 1`). Pads are exempt from both jitters (accent already applied)."""
    vel_width = _vel_jitter_width(
        feel.vel_jitter.base, feel.vel_jitter.range_scale, plan.budgets.dynamics_range
    )
    base_seed = stream_seed(plan.seed.master, plan.seed.overrides, "humanize")

    by_group: dict[tuple[str, int], list[_Rec]] = defaultdict(list)
    for r in records:
        by_group[(r.role, r.abs_bar)].append(r)

    role_seeds: dict[str, int] = {}
    for (role, abs_bar), group in by_group.items():
        if role not in role_seeds:
            role_seeds[role] = derive(base_seed, role)
        rng = Rng(derive(role_seeds[role], f"bar:{abs_bar}"))
        group.sort(key=lambda r: (r.grid_tick, r.track_id, r.sort_midi))
        for r in group:
            if r.role == "pads":
                continue
            w = round(feel.jitter_ms.at(r.voice) * ticks_per_ms)
            r.pos += jitter.timing(rng, w)
            r.vel += jitter.velocity(rng, vel_width)


def _emit(phrases: list[Phrase], records: list[_Rec], song_end: int) -> list[Phrase]:
    """Terminal single half-even rounding, `ticks >= 0` / `ticks + dur <= song
    end` clamps (§5), then re-sort each phrase's notes by `(ticks, midi)`."""
    by_phrase: dict[int, list[PhraseNote]] = defaultdict(list)
    for r in records:
        ticks = max(0, round(r.pos))
        dur = r.dur
        if ticks + dur > song_end:
            dur = max(1, song_end - ticks)
        velocity = round(min(1.0, max(0.05, r.vel)), 3)
        by_phrase[r.phrase_idx].append(
            r.src.model_copy(
                update={"ticks": ticks, "duration_ticks": dur, "velocity": velocity}
            )
        )

    out: list[Phrase] = []
    for pi, phrase in enumerate(phrases):
        notes = sorted(by_phrase[pi], key=_note_sort_key)
        out.append(phrase.model_copy(update={"notes": notes}))
    return out


def _ritard(form: SongForm, plan: GenerationPlan) -> list[Tempo]:
    """Ritard tempo curve seam (§5.7): delegates to the pure renderer."""
    return ritard_events(form, plan)
