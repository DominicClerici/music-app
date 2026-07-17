"""PHASE_6 §3.7 stage-6 mutation (6c) mechanism unit tests (Task T3).

The five constructive-safe operators are exercised directly on `Builder` lists
(deterministic, no draw) for their target rule + no-op path; the per-unit driver
(`mutate`) is exercised for the §3.8 draw discipline (draw-iff-≥2, per-unit RNG
construction + isolation) and the structural safety invariants. The §7
worked-example fired-op goldens are Task T4.

Provenance: drum notes carry the internal `voice`/`ornament` tags
`generators._generate_drums` now adds; these tests build phrases with those tags
to stand in for real generated drums.
"""

from __future__ import annotations

import random
from typing import Any

from trackgen.packs.models import Manifest, StylePack, TransitionsSpec
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
from trackgen.seeds import derive, stream_seed, weighted_choice
from trackgen.transitions._common import Builder, to_builders
from trackgen.transitions.mutation import (
    _anticipate,
    _drop_hit,
    _drop_ornament,
    _hat_lift,
    _kick_pickup,
    mutate,
)

BAR = 1920
_HUGE = 10_000_000  # a final-bar tick past everything (exclusion never bites).


# --- factories ---------------------------------------------------------------


def make_plan(master: int = 3735928559) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="t", version="0"),
        seed=SeedSpec(master=master, overrides={}),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=120.0,
        time_signature=TimeSignature(numerator=4, denominator=4),
        swing=None,
        max_length_ticks=1_000_000,
        role_flavors={},
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=0.5,
            dynamics_base=0.5,
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


def make_pack(mutation: dict[str, Any]) -> StylePack:
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
    spec = TransitionsSpec.model_validate(
        {
            "phraseFill": {"odds": [1, 2]},
            "stop": {"enabled": False},
            "crash": {"velocity": [0.55, 0.95]},
            "mutation": mutation,
        }
    )
    return StylePack(
        manifest=manifest,
        patterns={"drums": [], "bass": [], "comping": [], "pads": []},
        transitions=spec,
    )


def section(sid: str, start_bar: int, length_bars: int) -> FormSection:
    return FormSection(
        id=sid,
        type="verse",
        index=1,
        start_bar=start_bar,
        length_bars=length_bars,
        energy=0.5,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=length_bars)],
        harmony_tag="x",
    )


def note(tick: int, vel: float, tags: list[str], midi: int | None = None) -> PhraseNote:
    return PhraseNote(
        ticks=tick, duration_ticks=120, midi=midi, velocity=vel, tags=list(tags)
    )


def drum_builder(track_id: str, notes: list[PhraseNote], span_bars: int = 2) -> Builder:
    return Builder(track_id, "drums", 0, span_bars * BAR, notes)


def comping_builder(notes: list[PhraseNote], span_bars: int = 8) -> Builder:
    return Builder("comping", "comping", 0, span_bars * BAR, notes)


def entry(sid: str, role: str) -> ArrangementEntry:
    return ArrangementEntry(
        section_id=sid,
        role=role,  # type: ignore[arg-type]
        active=True,
        intensity=2,
        density_budget=1.0,
        register=Register(low_midi=0, high_midi=127),
    )


# =============================================================================
# hat_lift (drums)
# =============================================================================


def test_hat_lift_promotes_last_offbeat_hat_in_second_bar() -> None:
    sec = section("A", 0, 4)
    hats = drum_builder(
        "hats",
        [
            note(240, 0.5, ["hat_closed"]),  # first bar offbeat — not eligible
            note(BAR + 240, 0.5, ["hat_closed"]),  # 2nd bar offbeat (earlier)
            note(BAR + 720, 0.5, ["hat_closed"]),  # 2nd bar offbeat (LAST)
        ],
    )
    builders = [hats]
    _hat_lift(builders, sec, 0, 2 * BAR, _HUGE)
    lifted = next(n for n in hats.notes if n.ticks == BAR + 720)
    assert "hat_open" in lifted.tags and "hat_closed" not in lifted.tags
    assert "var" in lifted.tags and lifted.duration_ticks == 360
    # the earlier 2nd-bar hat and the first-bar hat are untouched.
    assert all("hat_open" not in n.tags for n in hats.notes if n.ticks != BAR + 720)


def test_hat_lift_no_op_without_offbeat_hat_closed() -> None:
    sec = section("A", 0, 4)
    # a 2nd-bar hat but on the beat (not pos%480==240), and an open hat.
    hats = drum_builder(
        "hats",
        [note(BAR, 0.5, ["hat_closed"]), note(BAR + 240, 0.5, ["hat_open"])],
    )
    before = [n.model_copy() for n in hats.notes]
    _hat_lift([hats], sec, 0, 2 * BAR, _HUGE)
    assert [n.model_dump() for n in hats.notes] == [n.model_dump() for n in before]


# =============================================================================
# drop_ornament (drums)
# =============================================================================


def test_drop_ornament_deletes_last_ornament_across_tracks() -> None:
    sec = section("A", 0, 4)
    hats = drum_builder("hats", [note(960, 0.4, ["hat_closed", "ornament"])])
    perc = drum_builder("perc", [note(1680, 0.4, ["perc", "ornament"])])  # LAST
    kick = drum_builder("kick", [note(0, 0.9, ["kick"])])  # non-ornament, safe
    builders = [hats, perc, kick]
    _drop_ornament(builders, sec, 0, 2 * BAR, _HUGE)
    assert perc.notes == []  # the latest ornament deleted
    assert len(hats.notes) == 1  # earlier ornament kept
    assert len(kick.notes) == 1  # non-ornament never removed


def test_drop_ornament_no_op_without_ornament() -> None:
    sec = section("A", 0, 4)
    kick = drum_builder("kick", [note(0, 0.9, ["kick"]), note(960, 0.8, ["kick"])])
    _drop_ornament([kick], sec, 0, 2 * BAR, _HUGE)
    assert len(kick.notes) == 2


# =============================================================================
# kick_pickup (drums)
# =============================================================================


def test_kick_pickup_adds_pickup_before_last_offbeat_kick() -> None:
    sec = section("A", 0, 4)
    kick = drum_builder(
        "kick",
        [
            note(0, 0.9, ["kick"]),  # bar start — excluded as target
            note(960, 0.9, ["kick"]),  # non-bar-start
            note(1440, 0.9, ["kick"]),  # non-bar-start (LAST) → pickup at 1200
        ],
    )
    _kick_pickup([kick], sec, 0, 2 * BAR, _HUGE)
    added = [n for n in kick.notes if "var" in n.tags]
    assert len(added) == 1
    assert added[0].ticks == 1200
    assert added[0].velocity == round(0.9 * 0.85, 3)  # 0.765


def test_kick_pickup_no_op_when_occupied() -> None:
    sec = section("A", 0, 4)
    kick = drum_builder(
        "kick",
        [note(1440, 0.9, ["kick"]), note(1200, 0.9, ["kick"])],  # 1200 occupied
    )
    _kick_pickup([kick], sec, 0, 2 * BAR, _HUGE)
    assert not any("var" in n.tags for n in kick.notes)


def test_kick_pickup_no_op_without_offbeat_target() -> None:
    sec = section("A", 0, 4)
    kick = drum_builder("kick", [note(0, 0.9, ["kick"]), note(BAR, 0.9, ["kick"])])
    _kick_pickup([kick], sec, 0, 2 * BAR, _HUGE)
    assert len(kick.notes) == 2 and not any("var" in n.tags for n in kick.notes)


# =============================================================================
# anticipate (comping)
# =============================================================================


def test_anticipate_shifts_barstart_chord_preserving_pitch() -> None:
    sec = section("A", 0, 8)
    comp = comping_builder(
        [
            note(0, 0.7, [], midi=60),  # first event — excluded
            PhraseNote(ticks=720, duration_ticks=1200, midi=64, velocity=0.7),  # prev
            note(BAR, 0.7, [], midi=60),  # bar-start chord tone 1 → target
            note(BAR, 0.7, [], midi=67),  # bar-start chord tone 2 → target
        ]
    )
    _anticipate([comp], sec, 0, 8 * BAR, _HUGE)
    moved = [n for n in comp.notes if "var" in n.tags]
    assert len(moved) == 2
    assert all(n.ticks == BAR - 240 for n in moved)
    assert sorted(n.midi for n in moved if n.midi is not None) == [60, 67]  # inv 2
    # previous note (720, dur 1200 → end 1920) truncated to the new start 1680.
    prev = next(n for n in comp.notes if n.ticks == 720)
    assert prev.duration_ticks == (BAR - 240) - 720


def test_anticipate_no_op_when_landing_occupied() -> None:
    sec = section("A", 0, 8)
    comp = comping_builder(
        [
            note(0, 0.7, [], midi=60),  # first event
            note(BAR - 120, 0.7, [], midi=62),  # attack inside [1680, 1920)
            note(BAR, 0.7, [], midi=64),  # bar-start target
        ]
    )
    before = [n.model_dump() for n in comp.notes]
    _anticipate([comp], sec, 0, 8 * BAR, _HUGE)
    assert [n.model_dump() for n in comp.notes] == before


# =============================================================================
# drop_hit (comping)
# =============================================================================


def test_drop_hit_removes_last_nonbeat1_attack_in_two_attack_bar() -> None:
    sec = section("A", 0, 8)
    comp = comping_builder(
        [
            note(0, 0.7, [], midi=60),  # bar0 beat1 (protected)
            note(720, 0.7, [], midi=64),  # bar0 and-of-2 → droppable (LAST)
            note(BAR, 0.7, [], midi=60),  # bar1 beat1 only — 1 attack, safe
        ]
    )
    _drop_hit([comp], sec, 0, 8 * BAR, _HUGE)
    assert sorted(n.ticks for n in comp.notes) == [0, BAR]  # 720 dropped, beat1s kept


def test_drop_hit_no_op_when_no_bar_has_two_attacks() -> None:
    sec = section("A", 0, 8)
    comp = comping_builder([note(0, 0.7, [], midi=60), note(BAR, 0.7, [], midi=60)])
    _drop_hit([comp], sec, 0, 8 * BAR, _HUGE)
    assert len(comp.notes) == 2


# =============================================================================
# exclusions (§3.7): fill / crash / hold / final-bar never targeted
# =============================================================================


def test_ornament_tagged_fill_not_dropped() -> None:
    sec = section("A", 0, 4)
    # a device (fill) event that also happens to carry an ornament tag: excluded.
    perc = drum_builder("perc", [note(1680, 0.4, ["perc", "ornament", "fill"])])
    _drop_ornament([perc], sec, 0, 2 * BAR, _HUGE)
    assert len(perc.notes) == 1  # fill-tagged event is off-limits


def test_final_bar_events_not_targeted() -> None:
    sec = section("A", 0, 4)
    kick = drum_builder(
        "kick", [note(0, 0.9, ["kick"]), note(1440, 0.9, ["kick"])], span_bars=2
    )
    # final chord bar starts at tick 960 → the 1440 kick is at/after it → excluded.
    _kick_pickup([kick], sec, 0, 2 * BAR, 960)
    assert not any("var" in n.tags for n in kick.notes)


# =============================================================================
# driver: draw discipline (§3.8) + isolation + determinism
# =============================================================================


def _predict_op(table: dict[str, int], role: str, master: int, unit_bar: int) -> str:
    names = list(table)
    weights = list(table.values())
    seed = derive(
        derive(derive(stream_seed(master, {}, "transitions"), "mutate"), role),
        f"bar:{unit_bar}",
    )
    rng = random.Random(seed)
    return weighted_choice(names, weights, rng) if len(names) >= 2 else names[0]


def _drum_form_2units() -> tuple[SongForm, ArrangementPlan]:
    # one 4-bar drums section → two 2-bar units at abs bars 0 and 2.
    form = SongForm(
        template_id="t",
        total_bars=8,
        sections=[section("A", 0, 4), section("B", 4, 4)],
    )
    arr = ArrangementPlan(entries=[entry("A", "drums")])  # only A active
    return form, arr


def test_single_entry_table_never_draws(monkeypatch: Any) -> None:
    from trackgen.transitions import mutation as mut

    form, arr = _drum_form_2units()
    chords = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=7 * BAR,
                duration_ticks=BAR,
                section_id="B",
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
                scale=EventScale(root_pc=0, name="major"),
                function="T",
                tags=["final"],
            )
        ],
        keys=[],
    )
    pack = make_pack({"drums": {"none": 1}, "comping": {"none": 1}})

    draws = {"n": 0}

    class Counting(random.Random):
        def randrange(self, *a: Any, **k: Any) -> int:
            draws["n"] += 1
            return super().randrange(*a, **k)

    monkeypatch.setattr(mut, "Rng", Counting)
    phrases = [
        Phrase(
            track_id="kick",
            role="drums",
            start_tick=0,
            end_tick=4 * BAR,
            notes=[note(0, 0.9, ["kick"])],
        )
    ]
    out = mutate(phrases, form, chords, arr, make_plan(), pack)
    assert draws["n"] == 0  # single-entry (none-only) table → no randrange
    # identity: the one kick survives untouched.
    assert [n.ticks for p in out for n in p.notes] == [0]


def test_two_entry_table_one_draw_per_active_unit(monkeypatch: Any) -> None:
    from trackgen.transitions import mutation as mut

    form, arr = _drum_form_2units()
    chords = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=7 * BAR,
                duration_ticks=BAR,
                section_id="B",
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
                scale=EventScale(root_pc=0, name="major"),
                function="T",
                tags=["final"],
            )
        ],
        keys=[],
    )
    pack = make_pack({"drums": {"none": 1, "kick_pickup": 1}, "comping": {"none": 1}})

    draws = {"n": 0}

    class Counting(random.Random):
        def randrange(self, *a: Any, **k: Any) -> int:
            draws["n"] += 1
            return super().randrange(*a, **k)

    monkeypatch.setattr(mut, "Rng", Counting)
    mutate([], form, chords, arr, make_plan(), pack)
    # section A active, 4 bars → two 2-bar drum units → two draws. B inactive.
    assert draws["n"] == 2


def test_per_unit_rng_matches_reconstruction_and_is_isolated() -> None:
    # A single 2-bar drums unit at abs bar 2 with a legal kick_pickup target.
    form = SongForm(template_id="t", total_bars=4, sections=[section("A", 0, 4)])
    arr = ArrangementPlan(entries=[entry("A", "drums")])
    chords = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=3 * BAR,
                duration_ticks=BAR,
                section_id="A",
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
                scale=EventScale(root_pc=0, name="major"),
                function="T",
                tags=["final"],
            )
        ],
        keys=[],
    )
    table = {"none": 1, "kick_pickup": 5}
    pack = make_pack({"drums": table, "comping": {"none": 1}})
    master = 3735928559

    # unit @ bar 2 has a non-bar-start kick at 2*BAR+1440 → pickup at 2*BAR+1200.
    kick_phrase = Phrase(
        track_id="kick",
        role="drums",
        start_tick=0,
        end_tick=4 * BAR,
        notes=[note(2 * BAR + 1440, 0.9, ["kick"])],
    )
    out = mutate([kick_phrase], form, chords, arr, make_plan(master), pack)
    added = [n for p in out for n in p.notes if "var" in n.tags]

    op0 = _predict_op(table, "drums", master, 0)  # unit @ bar 0 (no target → no-op)
    op2 = _predict_op(table, "drums", master, 2)  # unit @ bar 2
    if op2 == "kick_pickup":
        assert added and added[0].ticks == 2 * BAR + 1200
    else:
        assert added == []
    # unit @ bar 0 has no kick → whatever it draws, it cannot add a var note there.
    assert all(n.ticks >= 2 * BAR for n in added)
    assert op0 in table  # reconstruction well-formed


def test_mutate_deterministic_repeat() -> None:
    form, arr = _drum_form_2units()
    chords = HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=7 * BAR,
                duration_ticks=BAR,
                section_id="B",
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
                scale=EventScale(root_pc=0, name="major"),
                function="T",
                tags=["final"],
            )
        ],
        keys=[],
    )
    pack = make_pack({"drums": {"none": 1, "hat_lift": 1}, "comping": {"none": 1}})
    phrases = to_builders(
        [
            Phrase(
                track_id="hats",
                role="drums",
                start_tick=0,
                end_tick=4 * BAR,
                notes=[note(BAR + 240, 0.5, ["hat_closed"])],
            )
        ]
    )
    plist = [
        Phrase(
            track_id=b.track_id,
            role=b.role,
            start_tick=b.start_tick,
            end_tick=b.end_tick,
            notes=b.notes,
        )
        for b in phrases
    ]
    a = mutate(plist, form, chords, arr, make_plan(), pack)
    b = mutate(plist, form, chords, arr, make_plan(), pack)
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]


# =============================================================================
# safety invariants (§3.7)
# =============================================================================


def test_backbeat_snare_never_removed_by_mutation() -> None:
    # a snare backbeat (vel>=0.7 at back2/back4) carries no ornament tag, so no
    # drum operator can target it — even drop_ornament.
    sec = section("A", 0, 4)
    snare = drum_builder(
        "snare", [note(480, 0.9, ["snare"]), note(1440, 0.9, ["snare"])]
    )
    _drop_ornament([snare], sec, 0, 2 * BAR, _HUGE)
    assert len(snare.notes) == 2


def test_anticipate_leaves_midi_untouched() -> None:
    # invariant 2: anticipate shifts ticks only, never re-pitches.
    sec = section("A", 0, 8)
    comp = comping_builder([note(0, 0.7, [], midi=60), note(BAR, 0.7, [], midi=64)])
    midis_before = sorted(n.midi for n in comp.notes if n.midi is not None)
    _anticipate([comp], sec, 0, 8 * BAR, _HUGE)
    assert sorted(n.midi for n in comp.notes if n.midi is not None) == midis_before
