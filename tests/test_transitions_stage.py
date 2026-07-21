"""PHASE_6 §3 stage-6 mechanism unit tests (Task T2: 6a HOLD + 6b devices).

Small synthetic `Phrase`/`SongForm`/`HarmonicPlan`/`ArrangementPlan`/`StylePack`
inputs exercise each mechanism in isolation (the §7 worked-example goldens are
Task T4). Coverage: boundary taxonomy, device assignment by entered type, stop
eligibility, fill selection + nearest-rung fallback (both directions), window
sizing (section vs phrase), fill rendering (deletion + instantiation +
other-roles-untouched), stop rendering, dropout, crash±kick (double-hit guard),
the HOLD transform, the T_last-bar guard, and the devices-RNG draw order/count.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from trackgen.packs.models import (
    Manifest,
    PatternEnvelope,
    StylePack,
    TransitionsSpec,
    fill_window,
)
from trackgen.schema.ir import (
    ArrangementEntry,
    ArrangementPlan,
    Budgets,
    ChordEvent,
    ChordSpec,
    EventScale,
    FormSection,
    GenerationPlan,
    HarmonicPlan,
    Key,
    MoodVector,
    Phrase,
    PhraseNote,
    Register,
    SectionPhrase,
    SeedSpec,
    SongForm,
    StylePackRef,
    TimbreDirectives,
    TimeSignature,
)
from trackgen.transitions import transitions
from trackgen.transitions._common import to_builders, to_phrases
from trackgen.transitions.devices import (
    Boundary,
    _boundaries,
    _select_fill,
    _stop_eligible,
    apply_devices,
)
from trackgen.transitions.ending import find_t_last, hold_ending

BAR = 1920

_TRANSITIONS_POP: dict[str, Any] = {
    "phraseFill": {"odds": [1, 2]},
    "stop": {"enabled": True, "odds": [1, 4]},
    "crash": {"velocity": [0.55, 0.95]},
    "mutation": {"drums": {"none": 1}, "comping": {"none": 1}},
}


# --- factories ---------------------------------------------------------------


def make_plan(*, master: int = 123, tempo: float = 120.0) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="t", version="0"),
        seed=SeedSpec(master=master, overrides={}),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=tempo,
        time_signature=TimeSignature(numerator=4, denominator=4),
        swing=None,
        max_length_ticks=1_000_000,
        role_flavors={},
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=0.5,
            dynamics_base=0.5,  # identity velocity shift → authored = emitted.
            dynamics_range=0.2,
            articulation_legato=0.5,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def fill_env(
    fill_id: str, rung: int, events: list[dict[str, Any]], weight: int = 1
) -> PatternEnvelope:
    return PatternEnvelope.model_validate(
        {
            "id": fill_id,
            "role": "drums",
            "kind": "fill",
            "energyLevel": rung,
            "lengthTicks": 1920,
            "weight": weight,
            "events": events,
        }
    )


def make_pack(
    fills: list[PatternEnvelope], transitions_spec: dict[str, Any] | None = None
) -> StylePack:
    manifest = Manifest.model_validate(
        {
            "formatVersion": 1,
            "id": "t6",
            "name": "T6",
            "version": "0",
            "engine": ">=0",
            "timeSignatures": [[4, 4]],
            "tempoRange": [60, 200],
        }
    )
    spec = TransitionsSpec.model_validate(transitions_spec or _TRANSITIONS_POP)
    windows = {env.id: fill_window(env) for env in fills}
    return StylePack(
        manifest=manifest,
        patterns={"drums": fills, "bass": [], "comping": [], "pads": []},
        transitions=spec,
        fill_windows=windows,
    )


def section(
    sid: str,
    stype: str,
    start_bar: int,
    length_bars: int,
    energy: float,
    phrase_bars: list[int],
    ending: Any = None,
) -> FormSection:
    return FormSection(
        id=sid,
        type=stype,
        index=1,
        start_bar=start_bar,
        length_bars=length_bars,
        energy=energy,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=b) for b in phrase_bars],
        harmony_tag="x",
        ending=ending,
    )


def final_chord(tick: int, section_id: str) -> ChordEvent:
    return ChordEvent(
        start_tick=tick,
        duration_ticks=BAR,
        section_id=section_id,
        chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
        scale=EventScale(root_pc=0, name="major"),
        function="T",
        tags=["final"],
    )


def drum_entry(section_id: str, intensity: int) -> ArrangementEntry:
    return ArrangementEntry(
        section_id=section_id,
        role="drums",
        active=True,
        intensity=intensity,
        density_budget=1.0,
        register=Register(low_midi=0, high_midi=0),
    )


def drum_phrase(
    track_id: str, span: tuple[int, int], positions: list[tuple[int, float]]
) -> Phrase:
    return Phrase(
        track_id=track_id,
        role="drums",
        start_tick=span[0],
        end_tick=span[1],
        notes=[
            PhraseNote(ticks=t, duration_ticks=120, midi=None, velocity=v, tags=[])
            for t, v in positions
        ],
    )


def pitched_phrase(
    role: str, span: tuple[int, int], notes: list[tuple[int, int, int, float]]
) -> Phrase:
    return Phrase(
        track_id=role,
        role=role,  # type: ignore[arg-type]
        start_tick=span[0],
        end_tick=span[1],
        notes=[
            PhraseNote(ticks=t, duration_ticks=d, midi=m, velocity=v, tags=[])
            for t, d, m, v in notes
        ],
    )


# --- taxonomy (§3.1) ---------------------------------------------------------


def test_boundary_taxonomy_enumeration() -> None:
    form = SongForm(
        template_id="t",
        total_bars=20,
        sections=[
            section("A", "verse", 0, 8, 0.3, [4, 4]),
            section("B", "chorus", 8, 8, 0.6, [8]),
            section("C", "outro", 16, 4, 0.8, [4]),
        ],
    )
    bounds = _boundaries(form)
    # section pairs A→B, B→C; interior only in A (its 2nd phrase at bar 4).
    section_bounds = [(b.fill_bar, b.entered.id) for b in bounds if b.kind == "section"]
    phrase_bounds = [(b.fill_bar, b.entered_tick) for b in bounds if b.kind == "phrase"]
    assert section_bounds == [(7, "B"), (15, "C")]
    assert phrase_bounds == [(3, 4 * BAR)]
    # timeline order = ascending fill_bar.
    assert [b.fill_bar for b in bounds] == [3, 7, 15]


def test_interior_boundary_skips_first_phrase() -> None:
    # A section that is one whole phrase has no interior boundary.
    form = SongForm(
        template_id="t",
        total_bars=8,
        sections=[section("A", "verse", 0, 8, 0.3, [8])],
    )
    assert [b for b in _boundaries(form) if b.kind == "phrase"] == []


# --- fill selection + fallback (§3.3) ----------------------------------------


def test_fill_selection_exact_rung() -> None:
    pack = make_pack(
        [fill_env("f2", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    rng = random.Random(0)
    assert _select_fill(pack, make_plan(), 2, rng).id == "f2"


def test_fill_selection_fallback_down_then_up() -> None:
    # Only a rung-1 fill exists: rung 3 falls down 3→2→1 (down wins before up).
    pack = make_pack(
        [fill_env("f1", 1, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    assert _select_fill(pack, make_plan(), 3, random.Random(0)).id == "f1"
    assert _select_fill(pack, make_plan(), 4, random.Random(0)).id == "f1"


def test_fill_selection_fallback_up_when_only_higher_rung() -> None:
    # Only a rung-4 fill exists: rung 2 falls 2→1 (miss) then up 3→4.
    pack = make_pack(
        [fill_env("f4", 4, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    assert _select_fill(pack, make_plan(), 2, random.Random(0)).id == "f4"


def test_fill_selection_tempo_gate_excludes() -> None:
    gated = PatternEnvelope.model_validate(
        {
            "id": "fg",
            "role": "drums",
            "kind": "fill",
            "energyLevel": 2,
            "lengthTicks": 1920,
            "weight": 1,
            "eligibility": {"tempoBpm": [60, 90]},
            "events": [{"pos": 1200, "voice": "snare", "velocity": 0.6}],
        }
    )
    ungated = fill_env("fu", 3, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])
    pack = make_pack([gated, ungated])
    # At 120 BPM the gated rung-2 fill is out; rung-2 falls to rung-... up to 3.
    assert _select_fill(pack, make_plan(tempo=120), 2, random.Random(0)).id == "fu"


def test_fill_selection_draw_only_when_two() -> None:
    a = fill_env("fa", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}], weight=1)
    b = fill_env("fb", 2, [{"pos": 1440, "voice": "snare", "velocity": 0.6}], weight=1)
    pack = make_pack([a, b])

    class Counter(random.Random):
        n = 0

        def randrange(self, *args: Any, **kwargs: Any) -> int:
            Counter.n += 1
            return super().randrange(*args, **kwargs)

    rng = Counter(0)
    chosen = _select_fill(pack, make_plan(), 2, rng)
    assert chosen.id in {"fa", "fb"}
    assert Counter.n == 1  # ≥2 candidates → exactly one draw.


# --- window sizing (§3.3) ----------------------------------------------------


def _one_section_form(stype: str = "verse") -> SongForm:
    return SongForm(
        template_id="t",
        total_bars=8,
        sections=[
            section("A", "intro", 0, 4, 0.3, [4]),
            section("B", stype, 4, 4, 0.6, [4]),
            section("C", "outro", 8, 4, 0.8, [4]),
        ],
    )


def _fill_all_beats(fill_id: str, rung: int) -> PatternEnvelope:
    # events across the whole bar so R can be observed by which survive.
    return fill_env(
        fill_id,
        rung,
        [
            {"pos": 0, "voice": "snare", "velocity": 0.6},
            {"pos": 480, "voice": "snare", "velocity": 0.6},
            {"pos": 960, "voice": "snare", "velocity": 0.6},
            {"pos": 1440, "voice": "snare", "velocity": 0.6},
        ],
    )


def test_section_fill_full_window() -> None:
    # window of a beat-1 fill = [0, 1920): section boundary renders the whole bar.
    fill = _fill_all_beats("f", 2)
    pack = make_pack([fill])
    boundary = Boundary(
        kind="section",
        fill_bar=3,
        entered_tick=4 * BAR,
        outgoing=_one_section_form().sections[0],
        entered=_one_section_form().sections[1],
    )
    builders = to_builders([drum_phrase("snare", (0, 4 * BAR), [])])
    from trackgen.transitions.devices import _render_fill

    _render_fill(builders, boundary, 2, make_plan(), pack, random.Random(0))
    snare = next(b for b in builders if b.track_id == "snare")
    # all four fill events fall in the fill bar (bar 3 → 3*1920).
    assert sorted(n.ticks - 3 * BAR for n in snare.notes) == [0, 480, 960, 1440]


def test_phrase_fill_last_two_beats_only() -> None:
    fill = _fill_all_beats("f", 2)
    pack = make_pack([fill])
    sec = section("A", "verse", 0, 8, 0.3, [4, 4])
    boundary = Boundary(
        kind="phrase", fill_bar=3, entered_tick=4 * BAR, outgoing=sec, entered=sec
    )
    builders = to_builders([drum_phrase("snare", (0, 8 * BAR), [])])
    from trackgen.transitions.devices import _render_fill

    _render_fill(builders, boundary, 2, make_plan(), pack, random.Random(0))
    snare = next(b for b in builders if b.track_id == "snare")
    # phrase fill = window ∩ [960, 1920): only pos 960 and 1440 survive.
    assert sorted(n.ticks - 3 * BAR for n in snare.notes) == [960, 1440]


# --- rendering: deletion + instantiation + other roles (§3.3) ----------------


def test_fill_rendering_deletes_groove_in_window_keeps_before() -> None:
    fill = fill_env(
        "f",
        2,
        [
            {"pos": 960, "voice": "snare", "velocity": 0.6},
            {"pos": 1440, "voice": "snare", "velocity": 0.9},
        ],
    )
    pack = make_pack([fill])
    sec_out = section("A", "verse", 0, 4, 0.3, [4])
    sec_in = section("B", "verse", 4, 4, 0.6, [4])
    boundary = Boundary(
        kind="section",
        fill_bar=3,
        entered_tick=4 * BAR,
        outgoing=sec_out,
        entered=sec_in,
    )
    # groove hats at 0/480 (before window) and 960/1440 (inside window [960,1920)).
    hats = drum_phrase(
        "hats",
        (0, 4 * BAR),
        [(3 * BAR + p, 0.5) for p in (0, 480, 960, 1440)],
    )
    bass = pitched_phrase("bass", (0, 4 * BAR), [(3 * BAR, 1920, 40, 0.7)])
    builders = to_builders([hats, bass])
    from trackgen.transitions.devices import _render_fill

    _render_fill(builders, boundary, 2, make_plan(), pack, random.Random(0))

    hats_b = next(b for b in builders if b.track_id == "hats")
    # groove hats inside [960,1920) deleted; before-window survive.
    assert sorted(n.ticks - 3 * BAR for n in hats_b.notes) == [0, 480]
    snare_b = next(b for b in builders if b.track_id == "snare")
    fill_notes = [n for n in snare_b.notes if "fill" in n.tags]
    assert sorted((n.ticks - 3 * BAR, n.velocity) for n in fill_notes) == [
        (960, 0.6),
        (1440, 0.9),
    ]
    # bass (other role) untouched.
    bass_b = next(b for b in builders if b.role == "bass")
    assert bass_b.notes == bass.notes


def test_fill_introduces_new_voice_track() -> None:
    fill = fill_env(
        "f",
        2,
        [{"pos": 1200, "voice": "tom_low", "velocity": 0.7}],
    )
    pack = make_pack([fill])
    sec_out = section("A", "verse", 0, 4, 0.3, [4])
    sec_in = section("B", "verse", 4, 4, 0.6, [4])
    boundary = Boundary(
        kind="section",
        fill_bar=3,
        entered_tick=4 * BAR,
        outgoing=sec_out,
        entered=sec_in,
    )
    builders = to_builders([drum_phrase("snare", (0, 4 * BAR), [])])
    from trackgen.transitions.devices import _render_fill

    _render_fill(builders, boundary, 2, make_plan(), pack, random.Random(0))
    tom = next((b for b in builders if b.track_id == "tom_low"), None)
    assert tom is not None
    assert tom.start_tick == 0 and tom.end_tick == 4 * BAR
    assert [n.ticks - 3 * BAR for n in tom.notes] == [1200]


# --- stop rendering (§3.4) ---------------------------------------------------


def test_stop_deletes_and_truncates_window() -> None:
    from trackgen.transitions.devices import _apply_stop

    entered = 8 * BAR
    cut = entered - 480
    # note A attacks in the stop window (deleted); B sustains into it (truncated);
    # C attacks at enteredTick (kept).
    bass = pitched_phrase(
        "bass",
        (4 * BAR, 8 * BAR),
        [
            (cut + 100, 240, 40, 0.7),  # A: in [cut, entered) → deleted
            (cut - 400, 800, 41, 0.7),  # B: sustains past cut → truncate to cut
            (entered, 480, 42, 0.7),  # C: at enteredTick → kept
        ],
    )
    builders = to_builders([bass])
    _apply_stop(builders, entered)
    notes = sorted(
        next(b for b in builders if b.role == "bass").notes, key=lambda n: n.ticks
    )
    assert [n.ticks for n in notes] == [cut - 400, entered]
    assert notes[0].duration_ticks == cut - (cut - 400)  # truncated to end at cut.


# --- dropout (§3.5) ----------------------------------------------------------


def test_dropout_truncates_sustains_across_downbeat() -> None:
    from trackgen.transitions.devices import _apply_dropout

    entered = 8 * BAR
    bass = pitched_phrase(
        "bass",
        (4 * BAR, 8 * BAR),
        [
            (entered - 200, 800, 40, 0.7),  # sustains across → truncate to entered
            (entered - 500, 100, 41, 0.7),  # ends before → untouched
        ],
    )
    builders = to_builders([bass])
    _apply_dropout(builders, entered)
    notes = sorted(
        next(b for b in builders if b.role == "bass").notes, key=lambda n: n.ticks
    )
    assert notes[0].duration_ticks == 100  # ends before downbeat → untouched
    assert notes[1].duration_ticks == 200  # entered − (entered − 200) → truncated


# --- crash ± kick (§3.7) -----------------------------------------------------


def test_crash_adds_kick_when_absent() -> None:
    from trackgen.transitions._common import add_crash_and_kick

    sec = section("B", "chorus", 8, 4, 0.5, [4])
    entered = 8 * BAR
    builders = to_builders([drum_phrase("ride", (entered, 12 * BAR), [(entered, 0.6)])])
    add_crash_and_kick(builders, sec, entered, 0.75, "crash", guard_existing_kick=True)
    crash = next(b for b in builders if b.track_id == "crash")
    kick = next(b for b in builders if b.track_id == "kick")
    assert crash.notes[0].ticks == entered and crash.notes[0].duration_ticks == 1440
    assert crash.notes[0].tags == ["crash"]
    assert kick.notes[0].ticks == entered  # no groove kick → kick added.


def test_crash_suppresses_kick_when_present() -> None:
    from trackgen.transitions._common import add_crash_and_kick

    sec = section("B", "chorus", 8, 4, 0.5, [4])
    entered = 8 * BAR
    builders = to_builders([drum_phrase("kick", (entered, 12 * BAR), [(entered, 0.9)])])
    add_crash_and_kick(builders, sec, entered, 0.75, "crash", guard_existing_kick=True)
    kick = next(b for b in builders if b.track_id == "kick")
    assert len(kick.notes) == 1  # existing beat-1 kick → no double hit.
    assert kick.notes[0].velocity == 0.9  # the original, not the crash velocity.


def test_stop_eligibility_rules() -> None:
    pack = make_pack(
        [fill_env("f", 4, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    out_sec = section("A", "verse", 0, 4, 0.3, [4])
    in_sec = section("B", "chorus", 4, 4, 0.6, [4])
    b = Boundary(
        kind="section",
        fill_bar=3,
        entered_tick=4 * BAR,
        outgoing=out_sec,
        entered=in_sec,
    )
    assert _stop_eligible(b, {"B": 4}, pack) is True
    assert _stop_eligible(b, {"B": 3}, pack) is False  # rung not 4
    lower = Boundary(
        kind="section",
        fill_bar=3,
        entered_tick=4 * BAR,
        outgoing=in_sec,
        entered=out_sec,
    )
    assert _stop_eligible(lower, {"A": 4}, pack) is False  # energy not rising
    disabled = make_pack(
        [fill_env("f", 4, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])],
        {**_TRANSITIONS_POP, "stop": {"enabled": False}},
    )
    assert _stop_eligible(b, {"B": 4}, disabled) is False  # pack disables stop


# --- device assignment by entered type (§3.2) --------------------------------


def _drive(
    form: SongForm, pack: StylePack, arr: ArrangementPlan, chords: HarmonicPlan
) -> list[Phrase]:
    return transitions(_phrases_for(form), form, chords, arr, make_plan(), pack)


def _phrases_for(form: SongForm) -> list[Phrase]:
    phrases: list[Phrase] = []
    for sec in form.sections:
        span = (sec.start_bar * BAR, (sec.start_bar + sec.length_bars) * BAR)
        # a beat-1 kick per bar + a ride, plus a bass note per bar.
        kick_pos = [(span[0] + bar * BAR, 0.9) for bar in range(sec.length_bars)]
        phrases.append(drum_phrase("kick", span, kick_pos))
        phrases.append(
            drum_phrase(
                "ride",
                span,
                [(span[0] + bar * BAR, 0.6) for bar in range(sec.length_bars)],
            )
        )
        phrases.append(
            pitched_phrase(
                "bass",
                span,
                [(span[0] + bar * BAR, 480, 40, 0.7) for bar in range(sec.length_bars)],
            )
        )
    return phrases


def test_breakdown_entered_gets_dropout_no_crash() -> None:
    form = SongForm(
        template_id="t",
        total_bars=16,
        sections=[
            section("A", "verse", 0, 8, 0.5, [8]),
            section("B", "breakdown", 8, 4, 0.2, [4]),
            section("C", "outro", 12, 4, 0.3, [4]),
        ],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    arr = ArrangementPlan(entries=[drum_entry(s.id, 2) for s in form.sections])
    chords = HarmonicPlan(chords=[final_chord(13 * BAR, "C")], keys=[])
    out = _drive(form, pack, arr, chords)
    # entering breakdown at bar 8: no crash at 8*1920, and no fill in the A→B
    # fill bar (bar 7). (The B→C boundary into the outro still fills — separate.)
    crash_at_b = [
        n for p in out if p.track_id == "crash" for n in p.notes if n.ticks == 8 * BAR
    ]
    assert crash_at_b == []
    fill_snares_bar7 = [
        n
        for p in out
        if p.track_id == "snare"
        for n in p.notes
        if "fill" in n.tags and 7 * BAR <= n.ticks < 8 * BAR
    ]
    assert fill_snares_bar7 == []


def test_hat_lift_never_sustains_across_a_dropout_entered_breakdown() -> None:
    """S22-10 regression, end-to-end through the pinned 6a→6b→6c order.

    A pack combining `hat_lift` with a `breakdown` section (the combination no
    reference pack had before fusion_jazz): 6b truncates every sustain at the
    breakdown entry, then 6c must not re-introduce one by lifting the last
    offbeat 8th of the preceding bar (pos 1680 + 360 = 120 ticks past the entry).
    This is exactly what quality validator W2 checks."""
    form = SongForm(
        template_id="t",
        total_bars=16,
        sections=[
            section("A", "verse", 0, 8, 0.5, [8]),
            section("B", "breakdown", 8, 4, 0.2, [4]),
            section("C", "outro", 12, 4, 0.3, [4]),
        ],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])],
        {
            **_TRANSITIONS_POP,
            # TR3 requires a `none` weight; skew it so every drum unit lifts.
            "mutation": {
                "drums": {"none": 1, "hat_lift": 10_000},
                "comping": {"none": 1},
            },
        },
    )
    arr = ArrangementPlan(entries=[drum_entry(s.id, 2) for s in form.sections])
    chords = HarmonicPlan(chords=[final_chord(13 * BAR, "C")], keys=[])

    entry = 8 * BAR
    target = entry - 240  # the last offbeat 8th before the breakdown entry.
    phrases = [
        *_phrases_for(form),
        Phrase(
            track_id="hats",
            role="drums",
            start_tick=0,
            end_tick=8 * BAR,
            notes=[
                PhraseNote(
                    ticks=t,
                    duration_ticks=120,
                    midi=None,
                    velocity=0.5,
                    tags=["hat_closed"],
                )
                for t in range(240, 8 * BAR, 480)
            ],
        ),
    ]
    out = transitions(phrases, form, chords, arr, make_plan(), pack)

    lifted = [
        n for p in out if p.track_id == "hats" for n in p.notes if n.ticks == target
    ]
    assert len(lifted) == 1
    assert "hat_open" in lifted[0].tags  # the operator did fire on this unit
    assert lifted[0].ticks + lifted[0].duration_ticks <= entry
    # the W2 predicate itself: nothing sustains across the breakdown entry.
    crossing = [
        (p.track_id, n.ticks, n.duration_ticks)
        for p in out
        for n in p.notes
        if n.ticks < entry < n.ticks + n.duration_ticks
    ]
    assert crossing == []


def test_postchorus_entered_gets_none() -> None:
    form = SongForm(
        template_id="t",
        total_bars=16,
        sections=[
            section("A", "chorus", 0, 8, 0.6, [8]),
            section("B", "postchorus", 8, 4, 0.5, [4]),
            section("C", "outro", 12, 4, 0.4, [4]),
        ],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    arr = ArrangementPlan(entries=[drum_entry(s.id, 2) for s in form.sections])
    chords = HarmonicPlan(chords=[final_chord(13 * BAR, "C")], keys=[])
    out = _drive(form, pack, arr, chords)
    crash_at_b = [
        n for p in out if p.track_id == "crash" for n in p.notes if n.ticks == 8 * BAR
    ]
    assert crash_at_b == []  # postchorus entry is smooth (no crash).


def test_other_entered_gets_fill_and_crash() -> None:
    form = SongForm(
        template_id="t",
        total_bars=16,
        sections=[
            section("A", "verse", 0, 8, 0.3, [8]),
            section("B", "chorus", 8, 4, 0.6, [4]),
            section("C", "outro", 12, 4, 0.8, [4]),
        ],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    arr = ArrangementPlan(entries=[drum_entry(s.id, 2) for s in form.sections])
    chords = HarmonicPlan(chords=[final_chord(13 * BAR, "C")], keys=[])
    out = _drive(form, pack, arr, chords)
    # crash on entry to chorus B at bar 8; velocity 0.55 + 0.6*0.40 = 0.79.
    crash = [
        n for p in out if p.track_id == "crash" for n in p.notes if n.ticks == 8 * BAR
    ]
    assert len(crash) == 1 and crash[0].velocity == pytest.approx(0.79)
    # fill snares: fill bar 7 (into B) and fill bar 11 (into outro C), pos 1200.
    fill = sorted(
        n.ticks
        for p in out
        if p.track_id == "snare"
        for n in p.notes
        if "fill" in n.tags
    )
    assert fill == [7 * BAR + 1200, 11 * BAR + 1200]


# --- HOLD (§3.6) -------------------------------------------------------------


def test_hold_extends_at_deletes_after() -> None:
    form = SongForm(
        template_id="t",
        total_bars=8,
        sections=[section("A", "outro", 0, 8, 0.5, [8], ending=None)],
    )
    t_last = 4 * BAR
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    bass = pitched_phrase(
        "bass",
        (0, 8 * BAR),
        [
            (0, 480, 40, 0.7),  # before T_last → untouched
            (t_last, 480, 41, 0.8),  # at T_last → extend + bump
            (t_last + 480, 480, 42, 0.7),  # after T_last → deleted
        ],
    )
    ride = drum_phrase(
        "ride", (0, 8 * BAR), [(0, 0.6), (t_last, 0.6), (t_last + 480, 0.6)]
    )
    builders = to_builders([bass, ride])
    hold_ending(
        builders,
        form,
        HarmonicPlan(chords=[final_chord(t_last, "A")], keys=[]),
        make_plan(),
        pack,
        t_last,
    )

    bass_notes = sorted(
        next(b for b in builders if b.role == "bass").notes, key=lambda n: n.ticks
    )
    assert [n.ticks for n in bass_notes] == [0, t_last]
    held = bass_notes[1]
    assert held.duration_ticks == 8 * BAR - t_last
    assert held.velocity == pytest.approx(0.85)  # 0.8 + 0.05
    assert "hold" in held.tags

    ride_notes = next(b for b in builders if b.track_id == "ride").notes
    assert all(n.ticks < t_last for n in ride_notes)  # drums cleared at/after T_last

    crash = next(b for b in builders if b.track_id == "crash")
    kick = next(b for b in builders if b.track_id == "kick")
    # crash formula 0.55 + 0.5*0.40 = 0.75, +0.05 = 0.80.
    assert crash.notes[0].ticks == t_last and crash.notes[0].velocity == pytest.approx(
        0.80
    )
    assert crash.notes[0].duration_ticks == 1440 and crash.notes[0].tags == ["hold"]
    assert kick.notes[0].ticks == t_last and kick.notes[0].velocity == pytest.approx(
        0.80
    )


def test_hold_velocity_clamped_to_one() -> None:
    form = SongForm(
        template_id="t", total_bars=4, sections=[section("A", "outro", 0, 4, 1.0, [4])]
    )
    t_last = BAR
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    builders = to_builders([drum_phrase("ride", (0, 4 * BAR), [(0, 0.6)])])
    hold_ending(
        builders,
        form,
        HarmonicPlan(chords=[final_chord(t_last, "A")], keys=[]),
        make_plan(),
        pack,
        t_last,
    )
    crash = next(b for b in builders if b.track_id == "crash")
    # formula 0.55 + 1.0*0.40 = 0.95, +0.05 = 1.00 (clamped).
    assert crash.notes[0].velocity == 1.0


def test_find_t_last_uses_last_final() -> None:
    chords = HarmonicPlan(
        chords=[final_chord(BAR, "A"), final_chord(2 * BAR, "A")], keys=[]
    )
    assert find_t_last(chords) == 2 * BAR


# --- T_last-bar guard (§3.6/§3.7) --------------------------------------------


def test_devices_guard_skips_boundaries_at_or_after_t_last_bar() -> None:
    # A tiny form whose LAST interior boundary falls in the final section: it
    # must be skipped (6a owns those bars). Final section is a single 12-bar
    # chorus with an interior phrase at bar 4 and 8; T_last at bar 2.
    form = SongForm(
        template_id="t",
        total_bars=12,
        sections=[section("A", "chorus", 0, 12, 0.6, [4, 4, 4])],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    arr = ArrangementPlan(entries=[drum_entry("A", 2)])
    t_last = 2 * BAR  # bar 2 → interior fill bars 3 and 7 are >= T_last bar (2).
    builders = to_builders([drum_phrase("snare", (0, 12 * BAR), [])])
    apply_devices(builders, form, arr, make_plan(), pack, t_last // BAR)
    # both interior boundaries guarded away → no fill snares anywhere.
    assert all("fill" not in n.tags for b in builders for n in b.notes)


# --- devices-RNG draw order / count (§3.8) -----------------------------------


def test_devices_rng_draw_count(monkeypatch: pytest.MonkeyPatch) -> None:
    form = SongForm(
        template_id="t",
        total_bars=20,
        sections=[
            section("A", "verse", 0, 8, 0.3, [4, 4]),  # interior boundary @ bar4
            section("B", "chorus", 8, 8, 0.6, [8]),  # section entry, rung 4 → stop draw
            section("C", "outro", 16, 4, 0.8, [4]),  # section entry, rung 3 → no stop
        ],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    arr = ArrangementPlan(
        entries=[drum_entry("A", 2), drum_entry("B", 4), drum_entry("C", 3)]
    )
    chords = HarmonicPlan(chords=[final_chord(17 * BAR, "C")], keys=[])

    from trackgen.transitions import devices as devices_mod

    instances: list[Any] = []

    class CountingRandom(random.Random):
        def __init__(self, *a: Any, **k: Any) -> None:
            super().__init__(*a, **k)
            self.count = 0
            instances.append(self)

        def randrange(self, *a: Any, **k: Any) -> int:
            self.count += 1
            return super().randrange(*a, **k)

    monkeypatch.setattr(devices_mod, "Rng", CountingRandom)
    transitions(_phrases_for(form), form, chords, arr, make_plan(), pack)

    # 1 interior include draw + 1 stop-vs-fill draw (B rung4 rising) = 2.
    # C entry not stop-eligible (rung 3); fills single-candidate → 0 selection draws.
    assert len(instances) == 1
    assert instances[0].count == 2


def test_transitions_deterministic_repeat() -> None:
    form = SongForm(
        template_id="t",
        total_bars=20,
        sections=[
            section("A", "verse", 0, 8, 0.3, [4, 4]),
            section("B", "chorus", 8, 8, 0.6, [8]),
            section("C", "outro", 16, 4, 0.8, [4]),
        ],
    )
    pack = make_pack(
        [fill_env("f", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])]
    )
    arr = ArrangementPlan(
        entries=[drum_entry("A", 2), drum_entry("B", 4), drum_entry("C", 3)]
    )
    chords = HarmonicPlan(chords=[final_chord(17 * BAR, "C")], keys=[])
    phrases = _phrases_for(form)
    a = transitions(phrases, form, chords, arr, make_plan(), pack)
    b = transitions(phrases, form, chords, arr, make_plan(), pack)
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]


def test_to_phrases_drops_empty_and_sorts() -> None:
    builders = to_builders(
        [
            pitched_phrase("bass", (0, BAR), []),  # empty → dropped
            drum_phrase("snare", (0, BAR), [(0, 0.6)]),
            drum_phrase("kick", (0, BAR), [(0, 0.9)]),
        ]
    )
    out = to_phrases(builders)
    # empty bass dropped; kick sorts before snare (track order).
    assert [p.track_id for p in out] == ["kick", "snare"]
