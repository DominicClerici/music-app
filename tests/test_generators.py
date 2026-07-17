"""Generator-dispatcher mechanisms (PHASE_5 §6 + §8.2) — the T3 surface.

Mechanism + structure over small synthetic inputs (and the voicing pass for the
voiced roles). The full §9.4 / end-to-end goldens are T4's; here we prove the
shared instantiation loop (tiling, gating), the four role shapes (drums voice→
track map, pattern-bass retarget + articulation, walking-bass dispatch, comping/
pads voicing hits), and the whole-output invariants.
"""

from __future__ import annotations

from trackgen.packs.models import (
    DrumEvent,
    Manifest,
    PatternEnvelope,
    PitchedEvent,
    Retarget,
    StylePack,
    VoicingConfig,
    WalkingConfig,
)
from trackgen.parts.generators import generate
from trackgen.parts.selection import SelectionResult
from trackgen.parts.voicing import build_voicing_map
from trackgen.parts.walker import walk
from trackgen.schema.document import Role
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
    KeyRegion,
    MoodVector,
    Phrase,
    PhraseNote,
    Register,
    SectionEnding,
    SectionPhrase,
    SeedSpec,
    SongForm,
    StylePackRef,
    TimbreDirectives,
    TimeSignature,
)

_BAR = 1920
_MASTER = 3735928559
_OVERRIDES: dict[str, int] = {}

_Scenario = tuple[ArrangementPlan, HarmonicPlan, SongForm, GenerationPlan, StylePack]

_BASS_LANE = Register(low_midi=28, high_midi=55)
_COMP_LANE = Register(low_midi=50, high_midi=71)
_PAD_LANE = Register(low_midi=45, high_midi=71)

_WALKING = WalkingConfig(
    feel_by_intensity={1: "two", 2: "two", 3: "four", 4: "four"},
    approach_weights={"chromatic_below": 2, "diatonic": 1, "dominant": 1},
    beat1_repeat_weights={"fifth": 2, "third": 1, "root": 1},
)


# --- fixture builders --------------------------------------------------------


def _spec(root_pc: int, quality: str, symbol: str) -> ChordSpec:
    return ChordSpec(root_pc=root_pc, quality=quality, symbol=symbol)  # type: ignore[arg-type]


def _c() -> ChordSpec:
    return _spec(0, "maj", "C")


def _g() -> ChordSpec:
    return _spec(7, "maj", "G")


def _cev(start: int, dur: int, spec: ChordSpec, section_id: str = "s") -> ChordEvent:
    return ChordEvent(
        start_tick=start,
        duration_ticks=dur,
        section_id=section_id,
        chord=spec,
        scale=EventScale(root_pc=spec.root_pc, name="ionian"),
        function="T",
    )


def _harmony(events: list[ChordEvent]) -> HarmonicPlan:
    return HarmonicPlan(
        chords=events, keys=[KeyRegion(start_tick=0, tonic_pc=0, mode="major")]
    )


def _cgcg(section_id: str = "s") -> HarmonicPlan:
    return _harmony(
        [
            _cev(0, _BAR, _c(), section_id),
            _cev(_BAR, _BAR, _g(), section_id),
            _cev(2 * _BAR, _BAR, _c(), section_id),
            _cev(3 * _BAR, _BAR, _g(), section_id),
        ]
    )


def _section(
    sid: str,
    start_bar: int,
    length: int,
    *,
    energy: float = 0.5,
    phrases: list[SectionPhrase] | None = None,
    final: bool = False,
) -> FormSection:
    return FormSection(
        id=sid,
        type="outro" if final else "verse",
        index=1,
        start_bar=start_bar,
        length_bars=length,
        energy=energy,
        total_of_type=1,
        phrases=phrases or [SectionPhrase(label="a", bars=length)],
        harmony_tag="x",
        ending=SectionEnding(tag_bars=0, close="cold") if final else None,
    )


def _form(sections: list[FormSection]) -> SongForm:
    total = max(s.start_bar + s.length_bars for s in sections)
    return SongForm(sections=sections, total_bars=total, template_id="syn")


def _entry(
    role: Role,
    sid: str,
    *,
    active: bool = True,
    intensity: int = 2,
    density: float = 0.5,
    register: Register | None = None,
) -> ArrangementEntry:
    return ArrangementEntry(
        section_id=sid,
        role=role,
        active=active,
        intensity=intensity,
        density_budget=density,
        register=register or _BASS_LANE,
    )


def _plan(
    *, tempo: float = 120.0, dynamics_base: float = 0.5, legato: float = 0.5
) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="syn", version="1"),
        seed=SeedSpec(master=_MASTER),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=tempo,
        time_signature=TimeSignature(numerator=4, denominator=4),
        max_length_ticks=200 * _BAR,
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=0.1,
            dynamics_base=dynamics_base,
            dynamics_range=0.5,
            articulation_legato=legato,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def _pack(
    *,
    bass_mode: str | None = None,
    walking: WalkingConfig | None = None,
    voicing: dict[Role, VoicingConfig] | None = None,
) -> StylePack:
    return StylePack(
        manifest=Manifest(
            format_version=1,
            id="syn",
            name="Synthetic",
            version="1",
            engine="trackgen",
            time_signatures=[(4, 4)],
            tempo_range=(60, 300),
        ),
        patterns={},
        layering_order=("drums", "bass", "comping", "pads"),
        bass_mode=bass_mode,  # type: ignore[arg-type]
        walking=walking,
        voicing=voicing or {},
    )


def _drum_pattern(
    events: list[DrumEvent], *, length: int = _BAR, energy: int = 2
) -> PatternEnvelope:
    return PatternEnvelope(
        id="dr",
        role="drums",
        kind="main",
        energy_level=energy,
        length_ticks=length,
        weight=1,
        events=events,  # type: ignore[arg-type]
    )


def _bass_pattern(events: list[PitchedEvent], *, length: int = _BAR) -> PatternEnvelope:
    return PatternEnvelope(
        id="ba",
        role="bass",
        kind="main",
        energy_level=2,
        length_ticks=length,
        weight=1,
        events=events,  # type: ignore[arg-type]
        retarget=Retarget(
            register_low=28, register_high=45, on_chord_change="retrigger"
        ),
    )


def _voiced_pattern(
    role: Role, events: list[PitchedEvent], *, length: int = _BAR
) -> PatternEnvelope:
    low, high = (52, 67) if role == "comping" else (45, 64)
    return PatternEnvelope(
        id=role[:2],
        role=role,
        kind="main",
        energy_level=2,
        length_ticks=length,
        weight=1,
        events=events,  # type: ignore[arg-type]
        retarget=Retarget(
            register_low=low, register_high=high, on_chord_change="retrigger"
        ),
    )


def _voicing_cfg(cls: str) -> VoicingConfig:
    return VoicingConfig(classes={1: (cls,), 2: (cls,), 3: (cls,), 4: (cls,)})


def _selection(
    mapping: dict[tuple[str, Role], PatternEnvelope],
) -> SelectionResult:
    return SelectionResult(by_section=mapping, by_key={})


def _midis_at(notes: list[PhraseNote], tick: int) -> list[int]:
    """Ascending pitches at `tick` (asserting each is a real pitched note)."""
    pitches: list[int] = []
    for note in notes:
        if note.ticks == tick:
            assert note.midi is not None
            pitches.append(note.midi)
    return sorted(pitches)


# =============================================================================
# Tiling (§6 / §3.2)
# =============================================================================


def _kick_ticks(
    phrases: list[FormSection], env: PatternEnvelope, entry: ArrangementEntry
) -> list[int]:
    result = generate(
        "drums",
        ArrangementPlan(entries=[entry]),
        _harmony([_cev(0, _BAR, _c())]),
        _form(phrases),
        _plan(),
        _pack(),
        _selection({(entry.section_id, "drums"): env}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    kick = next(p for p in result if p.track_id == "kick")
    return [n.ticks for n in kick.notes]


def test_tiling_one_bar_over_four_bar_phrase() -> None:
    env = _drum_pattern([DrumEvent(pos=0, voice="kick", velocity=0.9)])
    ticks = _kick_ticks([_section("s", 0, 4)], env, _entry("drums", "s"))
    assert ticks == [0, 1920, 3840, 5760]


def test_tiling_two_bar_over_four_bar_phrase() -> None:
    env = _drum_pattern([DrumEvent(pos=0, voice="kick", velocity=0.9)], length=2 * _BAR)
    ticks = _kick_ticks([_section("s", 0, 4)], env, _entry("drums", "s"))
    assert ticks == [0, 3840]


def test_tiling_truncates_past_phrase_end() -> None:
    # 2-bar pattern with a 2nd-bar kick, first phrase only 1 bar → the pos-2880
    # kick lands past the phrase end and is truncated.
    env = _drum_pattern(
        [
            DrumEvent(pos=0, voice="kick", velocity=0.9),
            DrumEvent(pos=2880, voice="kick", velocity=0.9),
        ],
        length=2 * _BAR,
    )
    section = _section(
        "s",
        0,
        4,
        phrases=[SectionPhrase(label="a", bars=1), SectionPhrase(label="b", bars=3)],
    )
    ticks = _kick_ticks([section], env, _entry("drums", "s"))
    # Phrase a (bar 0): only the pos-0 kick survives. Phrase b (bars 1-3) tiles
    # the 2-bar pattern from tick 1920: kicks at 1920, 4800 (pos-0) + 4800...,
    assert 2880 not in ticks  # the truncated first-phrase 2nd-bar kick
    assert ticks[0] == 0


def test_tiling_phrase_start_alignment() -> None:
    # A section starting at bar 4 tiles from tick 7680, not 0.
    env = _drum_pattern([DrumEvent(pos=0, voice="kick", velocity=0.9)])
    ticks = _kick_ticks([_section("s", 4, 4)], env, _entry("drums", "s"))
    assert ticks == [7680, 9600, 11520, 13440]


# =============================================================================
# Density gating (§3.5)
# =============================================================================


def test_gating_drops_above_budget_keeps_below() -> None:
    env = _drum_pattern(
        [
            DrumEvent(pos=0, voice="kick", velocity=0.9, min_density=0.3),
            DrumEvent(pos=480, voice="snare", velocity=0.8, min_density=0.8),
        ]
    )
    entry = _entry("drums", "s", density=0.5)
    result = generate(
        "drums",
        ArrangementPlan(entries=[entry]),
        _harmony([_cev(0, _BAR, _c())]),
        _form([_section("s", 0, 4)]),
        _plan(),
        _pack(),
        _selection({("s", "drums"): env}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    tracks = {p.track_id for p in result}
    assert "kick" in tracks  # min_density 0.3 <= budget 0.5 → kept
    assert "snare" not in tracks  # min_density 0.8 > 0.5 → dropped everywhere


# =============================================================================
# Drums (§6.1 + §8.2)
# =============================================================================


def _drum_phrases() -> list[Phrase]:
    env = _drum_pattern(
        [
            DrumEvent(pos=0, voice="kick", velocity=0.9),
            DrumEvent(pos=480, voice="snare", velocity=0.8),
            DrumEvent(pos=0, voice="hat_closed", velocity=0.5),
            DrumEvent(pos=960, voice="hat_open", velocity=0.5),
            DrumEvent(pos=1440, voice="ride", velocity=0.7),
        ]
    )
    return generate(
        "drums",
        ArrangementPlan(entries=[_entry("drums", "s")]),
        _harmony([_cev(0, _BAR, _c())]),
        _form([_section("s", 0, 4)]),
        _plan(dynamics_base=0.65),
        _pack(),
        _selection({("s", "drums"): env}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )


def test_drums_voice_track_map_merges_hats() -> None:
    tracks = {p.track_id for p in _drum_phrases()}
    assert tracks == {"kick", "snare", "hats", "ride"}


def test_drums_hats_track_holds_both_closed_and_open() -> None:
    hats = next(p for p in _drum_phrases() if p.track_id == "hats")
    # closed default dur 60, open default dur 360 — both land on the shared track.
    assert {n.duration_ticks for n in hats.notes} == {60, 360}


def test_drums_default_durations_per_voice() -> None:
    phrases = {p.track_id: p for p in _drum_phrases()}
    assert phrases["kick"].notes[0].duration_ticks == 120
    assert phrases["snare"].notes[0].duration_ticks == 120
    assert phrases["ride"].notes[0].duration_ticks == 240


def test_drums_midi_is_none_and_velocity_shifted() -> None:
    kick = next(p for p in _drum_phrases() if p.track_id == "kick")
    note = kick.notes[0]
    assert note.midi is None
    assert note.velocity == 0.96  # 0.9 + 0.4*(0.65-0.5)


def test_drums_authored_duration_respected() -> None:
    env = _drum_pattern([DrumEvent(pos=0, voice="kick", velocity=0.9, dur=200)])
    result = generate(
        "drums",
        ArrangementPlan(entries=[_entry("drums", "s")]),
        _harmony([_cev(0, _BAR, _c())]),
        _form([_section("s", 0, 4)]),
        _plan(),
        _pack(),
        _selection({("s", "drums"): env}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    kick = next(p for p in result if p.track_id == "kick")
    assert kick.notes[0].duration_ticks == 200


# =============================================================================
# Pattern-bass (§6.2)
# =============================================================================


def _bass_notes(pattern: PatternEnvelope, *, legato: float = 0.5) -> list[PhraseNote]:
    result = generate(
        "bass",
        ArrangementPlan(entries=[_entry("bass", "s", register=_BASS_LANE)]),
        _cgcg(),
        _form([_section("s", 0, 4)]),
        _plan(legato=legato),
        _pack(bass_mode="patterns"),
        _selection({("s", "bass"): pattern}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    assert len(result) == 1
    return result[0].notes


def test_pattern_bass_degree_retargets_into_lane() -> None:
    pattern = _bass_pattern([PitchedEvent(pos=0, dur=480, degree="root", velocity=0.7)])
    notes = _bass_notes(pattern)
    # Roots of C (pc0) then G (pc7), each in the 28-55 bass lane.
    first = notes[0]
    assert first.ticks == 0
    assert first.midi is not None and first.midi % 12 == 0  # C
    assert _BASS_LANE.low_midi <= first.midi <= _BASS_LANE.high_midi
    g_note = next(n for n in notes if n.ticks == _BAR)
    assert g_note.midi is not None and g_note.midi % 12 == 7  # G


def test_pattern_bass_articulation_scales_up() -> None:
    # legato 1.0 → x1.3; dur 480 → 624, well within the 1920 gap (no clamp).
    pattern = _bass_pattern([PitchedEvent(pos=0, dur=480, degree="root", velocity=0.7)])
    notes = _bass_notes(pattern, legato=1.0)
    assert notes[0].duration_ticks == 624


def test_pattern_bass_gap_clamp() -> None:
    # Two hits a beat-and-a-half apart; identity articulation; the long first
    # note is clamped to the 960-tick gap to the next hit.
    pattern = _bass_pattern(
        [
            PitchedEvent(pos=0, dur=1000, degree="root", velocity=0.7),
            PitchedEvent(pos=960, dur=200, degree="root", velocity=0.7),
        ]
    )
    notes = _bass_notes(pattern, legato=0.5)
    first = notes[0]
    assert first.ticks == 0
    assert first.duration_ticks == 960  # 1000 clamped to the gap


def test_pattern_bass_velocity_shift() -> None:
    pattern = _bass_pattern([PitchedEvent(pos=0, dur=480, degree="root", velocity=0.7)])
    result = generate(
        "bass",
        ArrangementPlan(entries=[_entry("bass", "s", register=_BASS_LANE)]),
        _cgcg(),
        _form([_section("s", 0, 4)]),
        _plan(dynamics_base=0.65),
        _pack(bass_mode="patterns"),
        _selection({("s", "bass"): pattern}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    assert result[0].notes[0].velocity == 0.76  # 0.7 + 0.06


# =============================================================================
# Walking-bass dispatch (§6.3)
# =============================================================================


def _walking_scenario() -> _Scenario:
    arr = ArrangementPlan(entries=[_entry("bass", "s", register=_BASS_LANE)])
    harmony = _cgcg()
    form = _form([_section("s", 0, 4)])
    plan = _plan(dynamics_base=0.65)
    pack = _pack(bass_mode="walking", walking=_WALKING)
    return arr, harmony, form, plan, pack


def test_walking_dispatch_routes_to_walker() -> None:
    arr, harmony, form, plan, pack = _walking_scenario()
    phrases = generate(
        "bass",
        arr,
        harmony,
        form,
        plan,
        pack,
        _selection({}),  # walking bass has no by_section entry
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    assert len(phrases) == 1
    walked = walk(arr, harmony, form, plan, pack, master=_MASTER, overrides=_OVERRIDES)[
        "s"
    ]
    # Same pitches + (unscaled) durations as the walker, velocity shifted +0.06.
    gen_notes = phrases[0].notes
    assert len(gen_notes) == len(walked)
    assert {n.duration_ticks for n in gen_notes} <= {960, 480, 1920, 60}
    by_tick = {(wn.ticks, wn.midi): wn for wn in walked}
    for n in gen_notes:
        assert n.midi is not None
        wn = by_tick[(n.ticks, n.midi)]
        assert n.duration_ticks == wn.duration_ticks  # unscaled
        assert n.velocity == round(wn.velocity + 0.06, 3)


def test_walking_forwards_ghost_tags() -> None:
    # A four-feel section (rung 3) produces and-of-4 ghosts; the tag survives.
    arr = ArrangementPlan(
        entries=[_entry("bass", "s", intensity=3, density=0.6, register=_BASS_LANE)]
    )
    harmony = _cgcg()
    form = _form([_section("s", 0, 4, energy=0.7)])
    plan = _plan()
    pack = _pack(bass_mode="walking", walking=_WALKING)
    phrases = generate(
        "bass",
        arr,
        harmony,
        form,
        plan,
        pack,
        _selection({}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    walked = walk(arr, harmony, form, plan, pack, master=_MASTER, overrides=_OVERRIDES)[
        "s"
    ]
    gen_ghosts = [n for n in phrases[0].notes if "ghost" in n.tags]
    walk_ghosts = [wn for wn in walked if "ghost" in wn.tags]
    assert len(gen_ghosts) == len(walk_ghosts)


# =============================================================================
# Comping / pads (§6.4 / §6.5)
# =============================================================================


def _comp_setup(
    role: Role, cls: str, lane: Register, *, legato: float = 0.5
) -> _Scenario:
    arr = ArrangementPlan(entries=[_entry(role, "s", register=lane)])
    harmony = _cgcg()
    form = _form([_section("s", 0, 4)])
    plan = _plan(legato=legato)
    pack = _pack(voicing={role: _voicing_cfg(cls)})
    return arr, harmony, form, plan, pack


def test_comping_hits_emit_voicing_map_pitches() -> None:
    arr, harmony, form, plan, pack = _comp_setup("comping", "triad_close", _COMP_LANE)
    pattern = _voiced_pattern(
        "comping", [PitchedEvent(pos=0, dur=900, degree="chord", velocity=0.7)]
    )
    phrases = generate(
        "comping",
        arr,
        harmony,
        form,
        plan,
        pack,
        _selection({("s", "comping"): pattern}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    vmap = build_voicing_map("comping", arr, harmony.chords, pack)
    notes = phrases[0].notes
    assert _midis_at(notes, 0) == sorted(vmap[0])  # C's voicing
    assert _midis_at(notes, _BAR) == sorted(vmap[_BAR])  # G's voicing


def test_comping_tops_within_lane() -> None:
    arr, harmony, form, plan, pack = _comp_setup("comping", "triad_close", _COMP_LANE)
    pattern = _voiced_pattern(
        "comping", [PitchedEvent(pos=0, dur=900, degree="chord", velocity=0.7)]
    )
    phrases = generate(
        "comping",
        arr,
        harmony,
        form,
        plan,
        pack,
        _selection({("s", "comping"): pattern}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    for n in phrases[0].notes:
        assert n.midi is not None and n.midi <= _COMP_LANE.high_midi


def test_comping_scales_pads_exempt() -> None:
    # legato 1.0: comping dur 900 → 1170 (scaled, no clamp); pads dur 900 stays.
    comp_arr, harmony, form, plan, comp_pack = _comp_setup(
        "comping", "triad_close", _COMP_LANE, legato=1.0
    )
    comp_pat = _voiced_pattern(
        "comping", [PitchedEvent(pos=0, dur=900, degree="chord", velocity=0.7)]
    )
    comp = generate(
        "comping",
        comp_arr,
        harmony,
        form,
        plan,
        comp_pack,
        _selection({("s", "comping"): comp_pat}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    assert comp[0].notes[0].duration_ticks == 1170

    pad_arr, harmony2, form2, plan2, pad_pack = _comp_setup(
        "pads", "fifths", _PAD_LANE, legato=1.0
    )
    pad_pat = _voiced_pattern(
        "pads", [PitchedEvent(pos=0, dur=900, degree="chord", velocity=0.5)]
    )
    pads = generate(
        "pads",
        pad_arr,
        harmony2,
        form2,
        plan2,
        pad_pack,
        _selection({("s", "pads"): pad_pat}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    assert pads[0].notes[0].duration_ticks == 900  # articulation-exempt


def test_pushed_comping_hit_sounds_next_chord_voicing() -> None:
    arr, harmony, form, plan, pack = _comp_setup("comping", "triad_close", _COMP_LANE)
    # A push hit late in C's bar (pos 1440, dur 480 → span crosses into G's bar).
    pattern = _voiced_pattern(
        "comping",
        [PitchedEvent(pos=1440, dur=480, degree="chord", velocity=0.7, push=True)],
    )
    phrases = generate(
        "comping",
        arr,
        harmony,
        form,
        plan,
        pack,
        _selection({("s", "comping"): pattern}),
        master=_MASTER,
        overrides=_OVERRIDES,
    )
    vmap = build_voicing_map("comping", arr, harmony.chords, pack)
    assert _midis_at(phrases[0].notes, 1440) == sorted(vmap[_BAR])  # G's, not C's
    pushed = [n for n in phrases[0].notes if n.ticks == 1440]
    assert all("push" in n.tags for n in pushed)


# =============================================================================
# Whole-output invariants
# =============================================================================


def _full_scenario() -> tuple[
    ArrangementPlan, HarmonicPlan, SongForm, GenerationPlan, StylePack, SelectionResult
]:
    arr = ArrangementPlan(
        entries=[
            _entry("drums", "s"),
            _entry("bass", "s", register=_BASS_LANE),
            _entry("comping", "s", register=_COMP_LANE),
            _entry("pads", "s", register=_PAD_LANE),
        ]
    )
    harmony = _cgcg()
    form = _form([_section("s", 0, 4)])
    plan = _plan(dynamics_base=0.6, legato=0.7)
    pack = _pack(
        bass_mode="patterns",
        voicing={
            "comping": _voicing_cfg("triad_close"),
            "pads": _voicing_cfg("fifths"),
        },
    )
    selection = _selection(
        {
            ("s", "drums"): _drum_pattern(
                [
                    DrumEvent(pos=0, voice="kick", velocity=0.9),
                    DrumEvent(pos=480, voice="snare", velocity=0.8),
                ]
            ),
            ("s", "bass"): _bass_pattern(
                [PitchedEvent(pos=0, dur=480, degree="root", velocity=0.7)]
            ),
            ("s", "comping"): _voiced_pattern(
                "comping", [PitchedEvent(pos=0, dur=900, degree="chord", velocity=0.7)]
            ),
            ("s", "pads"): _voiced_pattern(
                "pads", [PitchedEvent(pos=0, dur=1920, degree="chord", velocity=0.5)]
            ),
        }
    )
    return arr, harmony, form, plan, pack, selection


def _all_phrases() -> list[Phrase]:
    arr, harmony, form, plan, pack, selection = _full_scenario()
    phrases = []
    for role in ("drums", "bass", "comping", "pads"):
        phrases.extend(
            generate(
                role,
                arr,
                harmony,
                form,
                plan,
                pack,
                selection,
                master=_MASTER,
                overrides=_OVERRIDES,
            )
        )
    return phrases


def test_notes_sorted_by_ticks_then_midi() -> None:
    for phrase in _all_phrases():
        keys = [(n.ticks, n.midi if n.midi is not None else -1) for n in phrase.notes]
        assert keys == sorted(keys)


def test_velocities_in_unit_interval() -> None:
    for phrase in _all_phrases():
        for n in phrase.notes:
            assert 0.0 < n.velocity <= 1.0


def test_non_drum_midi_within_ceiling() -> None:
    for phrase in _all_phrases():
        if phrase.role == "drums":
            continue
        for n in phrase.notes:
            assert n.midi is not None and n.midi <= 71


def test_phrase_spans_the_section() -> None:
    for phrase in _all_phrases():
        assert phrase.start_tick == 0
        assert phrase.end_tick == 4 * _BAR


def test_drum_notes_carry_no_midi() -> None:
    for phrase in _all_phrases():
        if phrase.role != "drums":
            continue
        assert all(n.midi is None for n in phrase.notes)


def test_generate_is_deterministic() -> None:
    a = _all_phrases()
    b = _all_phrases()
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]
