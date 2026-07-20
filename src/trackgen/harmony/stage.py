"""The Harmony generator — pipeline stage 3 (PHASE_4 §5).

`harmony(plan, form, progressions, rng) -> HarmonicPlan` implements the §5.1
normative algorithm exactly: dissonance tier from the plan (§6.1), one draw per
distinct `harmonyTag` (§5.3) with per-slot dressing (§6), timeline assembly with
within-phrase hold-merge (§3.1), then the three boundary transforms in append
order — turnaround / deceptive (§5.4) and final close (§5.5) — and emission of
the §7 extension points (`keys`, per-event `scale`/`function`/`tags`,
`poolSelections`).

RNG discipline (§5.6): the stage takes its `rng` as a parameter (the pipeline
caller passes `stream_rng(plan.seed.master, plan.seed.overrides, "harmony")`;
tests inject a counting shim). Every draw goes through `weighted_choice` on that
one stream, in the fixed §5.1 order — per-tag `[select, dressing…]` in tag
first-appearance order → per-boundary `[select, dressing…]` in timeline order →
finals `[select, dressing…]`. A draw happens only when >= 2 candidates/options
survive; single-candidate selection and single-option dressing take the sole
value with no draw. Table/ladder lookups and the deceptive substitution never
draw. Order is append-only, so rerolling `harmony` alone re-colors the song.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trackgen.harmony.dressing import dressing_options, tier
from trackgen.packs.models import (
    Bar,
    FinalEntry,
    PoolEntry,
    ProgressionsConfig,
    TurnaroundEntry,
)
from trackgen.schema.ir import (
    ChordEvent,
    ChordSpec,
    EventScale,
    GenerationPlan,
    HarmonicPlan,
    KeyRegion,
    SongForm,
)
from trackgen.seeds import Rng, weighted_choice
from trackgen.theory import (
    KeyLike,
    chord_function,
    chord_scale,
    chord_symbol,
    resolve_token,
)

if TYPE_CHECKING:
    from trackgen.pipeline.explain import ExplainCollector

# 4/4, PPQ 480 → 1920 ticks/bar (PHASE_1 PPQ + §5 tick facts). v1 ships 4/4 only.
_TICKS_PER_BAR = 1920

_HOLD = "~"

# §3.3 rule 1 — the deceptive substitute's mode class (major: major/mixolydian/
# lydian → `vi min7`; minor: minor/dorian/phrygian → `bVI maj`).
_MAJOR_CLASS_MODES = frozenset({"major", "mixolydian", "lydian"})

# §3.1 roman numerals — a token is *bare* (dressable) iff it is `(accidental?)`
# `numeral` with no quality suffix and no slash bass (suffixed tokens are pinned,
# §6.5). Mirrors the grammar's numeral set; the parser owns validation.
_ROMAN_NUMERALS = frozenset(
    {"I", "II", "III", "IV", "V", "VI", "VII", "i", "ii", "iii", "iv", "v", "vi", "vii"}
)

# A dressed slot keeps the source token alongside the dressed spec: the token
# drives §3.2 function and is the event's provenance. A `None` bar is a hold.
_DressedSlot = tuple[ChordSpec, str]
_DressedBar = list[_DressedSlot] | None


def _token_is_bare(token: str) -> bool:
    """§3.1 — a bare token (dressable base triad) is `(accidental?)(numeral)`
    with no quality suffix and no bass; suffixed tokens are pinned."""
    if "/" in token:
        return False
    body = token[1:] if token[:1] in ("b", "#") else token
    return body in _ROMAN_NUMERALS


def _entry_eligible(
    entry: PoolEntry | TurnaroundEntry | FinalEntry,
    key: KeyLike,
    valence: float,
    dissonance: float,
) -> bool:
    """§5.1 step 3a — the mode / valence / dissonance eligibility gates."""
    if key.mode not in entry.modes:
        return False
    if entry.valence is not None and not (
        entry.valence[0] <= valence <= entry.valence[1]
    ):
        return False
    if entry.dissonance is not None and not (
        entry.dissonance[0] <= dissonance <= entry.dissonance[1]
    ):
        return False
    return True


def _select[T: (PoolEntry, TurnaroundEntry, FinalEntry)](
    entries: list[T], rng: Rng
) -> T:
    """Draw one entry by integer weight, but only when >= 2 survive gating
    (§5.3 / PHASE_3 D13). A sole candidate is taken with no draw."""
    if len(entries) >= 2:
        return weighted_choice(entries, [e.weight for e in entries], rng)
    return entries[0]


def _dress_slot(
    token: str,
    key: KeyLike,
    base_tier: int,
    rng: Rng,
    *,
    explain: ExplainCollector | None = None,
) -> ChordSpec:
    """Resolve `token`, look up its §6.3 dressing options, and draw one (iff
    >= 2 options; else the sole option, no draw). The returned spec already
    carries the re-derived `symbol` (dressing_options handles that)."""
    spec = resolve_token(token, key)
    opts = dressing_options(
        spec, _token_is_bare(token), chord_function(token), base_tier, key
    )
    if len(opts) >= 2:
        chosen = weighted_choice([s for s, _ in opts], [w for _, w in opts], rng)
    else:
        chosen = opts[0][0]
    if explain is not None:
        explain.add_dressing(token, base_tier, chosen.symbol)
    return chosen


def _event(
    spec: ChordSpec,
    token: str,
    start_tick: int,
    duration_ticks: int,
    section_id: str,
    key: KeyLike,
    tags: list[str],
) -> ChordEvent:
    """Build one `ChordEvent` with its §7.4 scale and §3.2 function attached."""
    hint = chord_scale(spec, key)
    return ChordEvent(
        start_tick=start_tick,
        duration_ticks=duration_ticks,
        section_id=section_id,
        chord=spec,
        scale=EventScale(root_pc=hint.root_pc, name=hint.name),
        function=chord_function(token),
        tags=tags,
    )


def _emit_phrase_instance(
    dressed_bars: list[_DressedBar], start_bar: int, section_id: str, key: KeyLike
) -> list[ChordEvent]:
    """Instantiate one phrase occurrence's dressed bars into events (§4 assembly).

    A `("~",)` hold bar extends the previous event's `duration_ticks` by one bar
    and emits no event — but only *within this instance*, so a repeated phrase
    re-states its first chord as a fresh event (§3.1 last bullet). Each real bar
    of `n` tokens splits its 1920 ticks evenly (`1920 // n`)."""
    events: list[ChordEvent] = []
    bar = start_bar
    for dressed_bar in dressed_bars:
        bar_tick = bar * _TICKS_PER_BAR
        if dressed_bar is None:  # hold — merge into the in-instance predecessor
            prev = events[-1]
            events[-1] = prev.model_copy(
                update={"duration_ticks": prev.duration_ticks + _TICKS_PER_BAR}
            )
        else:
            dur = _TICKS_PER_BAR // len(dressed_bar)
            for slot_index, (spec, token) in enumerate(dressed_bar):
                events.append(
                    _event(
                        spec,
                        token,
                        bar_tick + slot_index * dur,
                        dur,
                        section_id,
                        key,
                        [],
                    )
                )
        bar += 1
    return events


def _dress_and_emit_bars(
    bars: tuple[Bar, ...],
    start_tick: int,
    section_id: str,
    key: KeyLike,
    base_tier: int,
    rng: Rng,
    tags: list[str],
    *,
    explain: ExplainCollector | None = None,
) -> list[ChordEvent]:
    """Dress a turnaround/finals bar list at its own draw point and tile it over
    `[start_tick, …)` (§5.4/§5.5). These lists never contain holds (loader P5),
    so there is no merge; the dressing draws continue the append-only sequence."""
    events: list[ChordEvent] = []
    tick = start_tick
    for bar in bars:
        dur = _TICKS_PER_BAR // len(bar)
        for token in bar:
            spec = _dress_slot(token, key, base_tier, rng, explain=explain)
            events.append(_event(spec, token, tick, dur, section_id, key, list(tags)))
            tick += dur
    return events


def _truncate_to(events: list[ChordEvent], replace_start: int) -> list[ChordEvent]:
    """Retain the events preceding a boundary replacement at `replace_start`,
    truncating a straddling event to end exactly at the boundary. A shorter-than-
    run turnaround/finals (§5.4/§5.5) can start mid-way through a hold-merged
    tonic event, so the retained tonic must be clamped or it overlaps the
    replacement and breaks the §5 tiling contract."""
    kept: list[ChordEvent] = []
    for e in events:
        if e.start_tick + e.duration_ticks <= replace_start:
            kept.append(e)
        elif e.start_tick < replace_start:
            kept.append(
                e.model_copy(update={"duration_ticks": replace_start - e.start_tick})
            )
    return kept


def _terminal_tonic_run(
    section_events: list[ChordEvent], start_bar: int, end_bar: int, tonic_pc: int
) -> int:
    """§5.4 — the maximal trailing run (in whole bars) of section events that are
    degree-1-rooted **and** function T. A bar counts iff every event overlapping
    it qualifies (a hold-extended tonic covers several bars; a multi-token bar
    must have all its slots qualify)."""
    run = 0
    for bar in range(end_bar - 1, start_bar - 1, -1):
        lo = bar * _TICKS_PER_BAR
        hi = lo + _TICKS_PER_BAR
        overlapping = [
            e
            for e in section_events
            if e.start_tick < hi and e.start_tick + e.duration_ticks > lo
        ]
        if overlapping and all(
            e.chord.root_pc == tonic_pc and e.function == "T" for e in overlapping
        ):
            run += 1
        else:
            break
    return run


def _deceptive_chord(key: KeyLike) -> tuple[ChordSpec, str]:
    """§5.4 deceptive substitute (dormant in v1): `vi min7` for major-class
    modes, `bVI maj` for minor-class. Returns the spec and its source token (for
    function/provenance). No draw."""
    if key.mode in _MAJOR_CLASS_MODES:
        token = "vi"
        base = resolve_token(token, key)  # bare min triad → pin to min7
        spec = base.model_copy(update={"quality": "min7"})
        spec = spec.model_copy(update={"symbol": chord_symbol(spec, key)})
    else:
        token = "bVI"
        spec = resolve_token(token, key)  # already the major triad
    return spec, token


def harmony(
    plan: GenerationPlan,
    form: SongForm,
    progressions: ProgressionsConfig,
    rng: Rng,
    *,
    explain: ExplainCollector | None = None,
) -> HarmonicPlan:
    """PHASE_4 §5.1 — resolve a `SongForm` into a `HarmonicPlan`.

    `rng` is the caller-owned `harmony` stream (see module docstring); all draws
    go through it via `weighted_choice`, in the §5.1 order, only when >= 2
    candidates/options survive.
    """
    ts = plan.time_signature
    if ts.numerator != 4 or ts.denominator != 4:
        raise ValueError(
            f"harmony() v1 supports 4/4 only, got {ts.numerator}/{ts.denominator}"
        )

    dissonance = plan.budgets.dissonance
    base_tier = tier(dissonance)
    valence = plan.mood_vector.valence
    key = plan.key

    pool_selections: dict[str, str] = {}

    # --- Step 2/3: select + dress one entry per DISTINCT tag (first-appearance
    # order). Cached and reused by every section sharing the tag (D7) — one draw
    # per distinct tag, never per instance.
    dressed_by_tag: dict[str, dict[str, list[_DressedBar]]] = {}
    for section in form.sections:
        tag = section.harmony_tag
        if tag in dressed_by_tag:
            continue
        eligible = [
            entry
            for entry in progressions.pools[tag]
            if _entry_eligible(entry, key, valence, dissonance)
        ]
        # §5.2 density filter: at harmonicRhythmBase == 0.5, prefer entries with
        # density <= 1.0 — but only when that subset is non-empty, else inert.
        # Every other value (incl. 1.0) is inert (D9: only 0.5 triggers it).
        if plan.budgets.harmonic_rhythm_base == 0.5:
            restricted = [entry for entry in eligible if entry.density <= 1.0]
            if restricted:
                eligible = restricted
        entry = _select(eligible, rng)
        pool_selections[tag] = entry.id
        if explain is not None:
            explain.add_entry("pool", tag, entry.id, len(eligible))

        dressed: dict[str, list[_DressedBar]] = {}
        for label, bars in entry.phrases.items():
            dressed_bars: list[_DressedBar] = []
            for bar in bars:
                if tuple(bar) == (_HOLD,):
                    dressed_bars.append(None)
                    continue
                dressed_bars.append(
                    [
                        (
                            _dress_slot(token, key, base_tier, rng, explain=explain),
                            token,
                        )
                        for token in bar
                    ]
                )
            dressed[label] = dressed_bars
        dressed_by_tag[tag] = dressed

    # --- Step 4: assemble the per-section timelines (identical bodies for
    # same-tag sections, before boundary replacements).
    section_events: list[list[ChordEvent]] = []
    for section in form.sections:
        dressed = dressed_by_tag[section.harmony_tag]
        events: list[ChordEvent] = []
        bar_cursor = section.start_bar
        for phrase in section.phrases:
            events.extend(
                _emit_phrase_instance(
                    dressed[phrase.label], bar_cursor, section.id, key
                )
            )
            bar_cursor += phrase.bars
        section_events.append(events)

    # --- Step 5: TURNAROUND / DECEPTIVE, per same-tag boundary in timeline order.
    for i in range(len(form.sections) - 1):
        section = form.sections[i]
        if section.harmony_tag != form.sections[i + 1].harmony_tag:
            continue
        events = section_events[i]
        end_bar = section.start_bar + section.length_bars
        run_bars = _terminal_tonic_run(events, section.start_bar, end_bar, key.tonic_pc)
        eligible_ta = [
            entry
            for entry in progressions.turnarounds
            if _entry_eligible(entry, key, valence, dissonance)
            and len(entry.bars) <= run_bars
        ]
        if eligible_ta:
            ta_entry = _select(eligible_ta, rng)
            if explain is not None:
                explain.add_entry(
                    "turnaround",
                    f"turnaround:{section.id}",
                    ta_entry.id,
                    len(eligible_ta),
                )
            replace_start = (end_bar - len(ta_entry.bars)) * _TICKS_PER_BAR
            kept = _truncate_to(events, replace_start)
            section_events[i] = kept + _dress_and_emit_bars(
                ta_entry.bars,
                replace_start,
                section.id,
                key,
                base_tier,
                rng,
                ["turnaround"],
                explain=explain,
            )
            pool_selections[f"turnaround:{section.id}"] = ta_entry.id
        else:
            last = events[-1]
            if last.chord.root_pc == key.tonic_pc and last.function == "T":
                spec, token = _deceptive_chord(key)
                hint = chord_scale(spec, key)
                events[-1] = last.model_copy(
                    update={
                        "chord": spec,
                        "function": chord_function(token),
                        "scale": EventScale(root_pc=hint.root_pc, name=hint.name),
                        "tags": ["deceptive"],
                    }
                )

    # --- Step 6: FINAL CLOSE on the section carrying `ending` (unconditional).
    final_index = next(i for i, s in enumerate(form.sections) if s.ending is not None)
    final_section = form.sections[final_index]
    finals = [
        entry
        for entry in progressions.finals
        if _entry_eligible(entry, key, valence, dissonance)
    ]
    final_entry = _select(finals, rng)
    if explain is not None:
        explain.add_entry("final", "finals", final_entry.id, len(finals))
    end_bar = final_section.start_bar + final_section.length_bars
    replace_start = (end_bar - len(final_entry.bars)) * _TICKS_PER_BAR
    events = section_events[final_index]
    kept = _truncate_to(events, replace_start)
    section_events[final_index] = kept + _dress_and_emit_bars(
        final_entry.bars,
        replace_start,
        final_section.id,
        key,
        base_tier,
        rng,
        ["final"],
        explain=explain,
    )
    pool_selections["finals"] = final_entry.id

    # --- Step 7: emit.
    chords = [event for events in section_events for event in events]
    return HarmonicPlan(
        chords=chords,
        keys=[KeyRegion(start_tick=0, tonic_pc=key.tonic_pc, mode=key.mode)],
        pool_selections=pool_selections,
    )
