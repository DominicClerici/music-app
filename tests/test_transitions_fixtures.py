"""PHASE_6 §11.8 stage-6 synthetic fixtures (Task T4, DoD 8).

Minimal hand-built packs/forms exercising the device paths the two reference
worked examples do not reach:

- a **stop-heavy odds** pack driving §3.4 stop rendering end-to-end (all-role
  deletion in `[entered − 480, entered)`, sustains truncated, then crash);
- a **breakdown**-entered form driving §3.5 dropout (sustains truncated at the
  entered downbeat, no fill / no crash — the dormant device kept tested, the
  PHASE_4 deceptive-rule precedent);
- **rung-restricted fill banks** driving the §3.3 nearest-rung fallback chain in
  both directions (a rung-3 request falling down to a rung-1-only bank; a rung-2
  request falling down-then-up to a rung-4-only bank).

These drive the **real** `transitions(...)` on synthetic inputs (not the
reference packs), with a fixed master seed so the one drawn device (stop odds)
resolves deterministically.
"""

from __future__ import annotations

from typing import Any

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

BAR = 1920

_NONE_MUTATION = {"drums": {"none": 1}, "comping": {"none": 1}}


# --- factories ---------------------------------------------------------------


def _plan(master: int = 0) -> GenerationPlan:
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
            dynamics_base=0.5,  # identity velocity shift.
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


def _fill(fill_id: str, rung: int, events: list[dict[str, Any]]) -> PatternEnvelope:
    return PatternEnvelope.model_validate(
        {
            "id": fill_id,
            "role": "drums",
            "kind": "fill",
            "energyLevel": rung,
            "lengthTicks": 1920,
            "weight": 1,
            "events": events,
        }
    )


def _pack(fills: list[PatternEnvelope], spec: dict[str, Any]) -> StylePack:
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
    return StylePack(
        manifest=manifest,
        patterns={"drums": fills, "bass": [], "comping": [], "pads": []},
        transitions=TransitionsSpec.model_validate(spec),
        fill_windows={env.id: fill_window(env) for env in fills},
    )


def _section(
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


def _drum_entry(sid: str, intensity: int) -> ArrangementEntry:
    return ArrangementEntry(
        section_id=sid,
        role="drums",
        active=True,
        intensity=intensity,
        density_budget=1.0,
        register=Register(low_midi=0, high_midi=0),
    )


def _final_chord(bar: int, sid: str) -> HarmonicPlan:
    return HarmonicPlan(
        chords=[
            ChordEvent(
                start_tick=bar * BAR,
                duration_ticks=BAR,
                section_id=sid,
                chord=ChordSpec(root_pc=0, quality="maj", symbol="C"),
                scale=EventScale(root_pc=0, name="major"),
                function="T",
                tags=["final"],
            )
        ],
        keys=[],
    )


def _drum_phrase(
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


def _bass_phrase(
    span: tuple[int, int], notes: list[tuple[int, int, int, float]]
) -> Phrase:
    return Phrase(
        track_id="bass",
        role="bass",
        start_tick=span[0],
        end_tick=span[1],
        notes=[
            PhraseNote(ticks=t, duration_ticks=d, midi=m, velocity=v, tags=[])
            for t, d, m, v in notes
        ],
    )


# =============================================================================
# §3.4 — stop rendering end-to-end (stop-heavy odds)
# =============================================================================


def test_stop_device_renders_end_to_end() -> None:
    """A rung-4 rising entry with `stop.enabled` and stop-heavy odds `[50, 1]`
    resolves (deterministically at master 0) to a **stop**: across all roles,
    every note attacking in `[entered − 480, entered)` is deleted and any sustain
    into it is truncated to `entered − 480`; the fill is replaced entirely (no
    fill-tagged notes in the fill bar); the entered downbeat carries the crash."""
    entered = 8 * BAR
    cut = entered - 480  # 14880 (= bar 7, pos 1440).

    form = SongForm(
        template_id="t",
        total_bars=16,
        sections=[
            _section("A", "verse", 0, 8, 0.3, [8]),
            _section("B", "chorus", 8, 4, 0.9, [4]),
            _section("C", "outro", 12, 4, 0.95, [4]),
        ],
    )
    pack = _pack(
        [_fill("f4", 4, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])],
        {
            "phraseFill": {"odds": [1, 2]},
            "stop": {"enabled": True, "odds": [50, 1]},
            "crash": {"velocity": [0.55, 0.95]},
            "mutation": _NONE_MUTATION,
        },
    )
    arr = ArrangementPlan(
        entries=[_drum_entry("A", 4), _drum_entry("B", 4), _drum_entry("C", 4)]
    )
    chords = _final_chord(13, "C")

    # Section A phrases: a kick on beats 1/3, a snare on beats 2/4 (so bar 7's
    # beat-4 snare lands exactly at `cut`), plus a bass sustain crossing `cut`.
    a_span = (0, 8 * BAR)
    kick = _drum_phrase(
        "kick",
        a_span,
        [(bar * BAR + p, 0.9) for bar in range(8) for p in (0, 960)],
    )
    snare = _drum_phrase(
        "snare",
        a_span,
        [(bar * BAR + p, 0.7) for bar in range(8) for p in (480, 1440)],
    )
    bass = _bass_phrase(
        a_span,
        [(bar * BAR, 480, 40, 0.7) for bar in range(7)]
        + [(7 * BAR + 960, 800, 41, 0.7)],  # 14400 → ends 15200, crosses cut 14880.
    )
    b_span = (8 * BAR, 12 * BAR)
    b_kick = _drum_phrase("kick", b_span, [(8 * BAR, 0.9)])  # beat-1 kick at entry.
    phrases = [kick, snare, bass, b_kick]

    out = transitions(phrases, form, chords, arr, _plan(0), pack)

    # (1) All-role silence across the stop window [cut, entered).
    in_window = [
        (p.track_id, n.ticks) for p in out for n in p.notes if cut <= n.ticks < entered
    ]
    assert in_window == []

    # (2) The bass sustain truncated to end exactly at cut.
    bass_out = [n for p in out if p.role == "bass" for n in p.notes if n.ticks == 14400]
    assert len(bass_out) == 1
    assert bass_out[0].ticks + bass_out[0].duration_ticks == cut

    # (3) The fill is replaced — no fill-tagged notes in the A→B fill bar (7).
    assert not [
        n
        for p in out
        if p.role == "drums"
        for n in p.notes
        if "fill" in n.tags and 7 * BAR <= n.ticks < 8 * BAR
    ]

    # (4) The entered downbeat carries the crash (velocity 0.55 + 0.9·0.40 = 0.91).
    crash = [
        n for p in out if p.track_id == "crash" for n in p.notes if n.ticks == entered
    ]
    assert len(crash) == 1
    assert crash[0].velocity == 0.91 and crash[0].tags == ["crash"]


# =============================================================================
# §3.5 — dropout rendering end-to-end (breakdown entry)
# =============================================================================


def test_breakdown_entry_renders_dropout() -> None:
    """Entering a `breakdown` (§3.5): no fill, no crash; every role's sustain
    across the entered downbeat is truncated to it (a clean cut into the thinned
    texture)."""
    entered = 8 * BAR
    form = SongForm(
        template_id="t",
        total_bars=16,
        sections=[
            _section("A", "verse", 0, 8, 0.6, [8]),
            _section("B", "breakdown", 8, 4, 0.2, [4]),
            _section("C", "outro", 12, 4, 0.3, [4]),
        ],
    )
    pack = _pack(
        [_fill("f2", 2, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])],
        {
            "phraseFill": {"odds": [1, 2]},
            "stop": {"enabled": False},
            "crash": {"velocity": [0.55, 0.95]},
            "mutation": _NONE_MUTATION,
        },
    )
    arr = ArrangementPlan(
        entries=[_drum_entry("A", 2), _drum_entry("B", 2), _drum_entry("C", 2)]
    )
    chords = _final_chord(13, "C")

    a_span = (0, 8 * BAR)
    # A bass note in bar 7 sustaining across the bar-8 downbeat.
    bass = _bass_phrase(a_span, [(7 * BAR, 3000, 40, 0.7)])  # 13440 → ends 16440.
    kick = _drum_phrase("kick", a_span, [(bar * BAR, 0.9) for bar in range(8)])
    phrases = [bass, kick]

    out = transitions(phrases, form, chords, arr, _plan(0), pack)

    # No crash at the breakdown entry (bar 8).
    assert not [
        n for p in out if p.track_id == "crash" for n in p.notes if n.ticks == entered
    ]
    # No fill in the A→B fill bar (7).
    assert not [
        n
        for p in out
        if p.role == "drums"
        for n in p.notes
        if "fill" in n.tags and 7 * BAR <= n.ticks < 8 * BAR
    ]
    # The A bass sustain truncated to end at the entered downbeat.
    bass_out = [
        n for p in out if p.role == "bass" for n in p.notes if n.ticks == 7 * BAR
    ]
    assert len(bass_out) == 1
    assert bass_out[0].ticks + bass_out[0].duration_ticks == entered


# =============================================================================
# §3.3 — nearest-rung fill fallback, both directions
# =============================================================================


def _drive_single_fill_bank(bank_rung: int, entered_rung: int) -> list[Phrase]:
    """Drive `transitions()` on a 3-section form whose middle boundary enters a
    section at `entered_rung`, with a fill bank holding a single fill at
    `bank_rung`. Returns the output so a test can assert the fill resolved via
    the §3.3 fallback and rendered into the A→B fill bar (bar 3)."""
    form = SongForm(
        template_id="t",
        total_bars=12,
        sections=[
            _section("A", "verse", 0, 4, 0.3, [4]),
            _section("B", "chorus", 4, 4, 0.6, [4]),
            _section("C", "outro", 8, 4, 0.8, [4]),
        ],
    )
    pack = _pack(
        [_fill("f", bank_rung, [{"pos": 1200, "voice": "snare", "velocity": 0.6}])],
        {
            "phraseFill": {"odds": [1, 2]},
            "stop": {"enabled": False},
            "crash": {"velocity": [0.55, 0.95]},
            "mutation": _NONE_MUTATION,
        },
    )
    arr = ArrangementPlan(
        entries=[
            _drum_entry("A", 2),
            _drum_entry("B", entered_rung),
            _drum_entry("C", 2),
        ]
    )
    chords = _final_chord(9, "C")
    phrases: list[Phrase] = []
    for sec in form.sections:
        span = (sec.start_bar * BAR, (sec.start_bar + sec.length_bars) * BAR)
        phrases.append(
            _drum_phrase(
                "kick", span, [(span[0] + b * BAR, 0.9) for b in range(sec.length_bars)]
            )
        )
    return transitions(phrases, form, chords, arr, _plan(0), pack)


def test_fill_fallback_down_to_rung_1_only_bank() -> None:
    """§3.3 down-direction: a rung-3 section-boundary request against a
    rung-1-only bank falls 3→2→1 and resolves the rung-1 fill (rendered into the
    fill bar, tagged `fill`, at the authored pos 1200)."""
    out = _drive_single_fill_bank(bank_rung=1, entered_rung=3)
    fills = sorted(
        n.ticks - 3 * BAR
        for p in out
        if p.track_id == "snare"
        for n in p.notes
        if "fill" in n.tags and 3 * BAR <= n.ticks < 4 * BAR
    )
    assert fills == [1200]


def test_fill_fallback_no_fallback_needed_rung_1_request() -> None:
    """§3.3: a rung-1-only bank at a rung-1 request resolves directly (no
    fallback step needed)."""
    out = _drive_single_fill_bank(bank_rung=1, entered_rung=1)
    fills = sorted(
        n.ticks - 3 * BAR
        for p in out
        if p.track_id == "snare"
        for n in p.notes
        if "fill" in n.tags and 3 * BAR <= n.ticks < 4 * BAR
    )
    assert fills == [1200]


def test_fill_fallback_up_to_rung_4_only_bank() -> None:
    """§3.3 up-direction: a rung-2 request against a rung-4-only bank falls
    2→1 (miss), then up 3→4, resolving the rung-4 fill."""
    out = _drive_single_fill_bank(bank_rung=4, entered_rung=2)
    fills = sorted(
        n.ticks - 3 * BAR
        for p in out
        if p.track_id == "snare"
        for n in p.notes
        if "fill" in n.tags and 3 * BAR <= n.ticks < 4 * BAR
    )
    assert fills == [1200]


def test_fill_never_instantiates_a_crash_voice() -> None:
    """§3.7/D17 + N2: a fill authoring a `crash`-voice event never emits a
    `"fill"`-tagged crash — crash placement is contextual, and the renderer
    drops it exactly as `_generate_drums` drops a stray groove crash. The snare
    hit in the same fill still renders; the only crash-track notes are the
    entry crash (tagged `"crash"`, not `"fill"`)."""
    form = SongForm(
        template_id="t",
        total_bars=8,
        sections=[
            _section("A", "verse", 0, 4, 0.3, [4]),
            _section("B", "chorus", 4, 4, 0.6, [4]),
        ],
    )
    pack = _pack(
        [
            _fill(
                "f",
                2,
                [
                    {"pos": 960, "voice": "crash", "velocity": 0.9},
                    {"pos": 1200, "voice": "snare", "velocity": 0.6},
                ],
            )
        ],
        {
            "phraseFill": {"odds": [1, 2]},
            "stop": {"enabled": False},
            "crash": {"velocity": [0.55, 0.95]},
            "mutation": _NONE_MUTATION,
        },
    )
    arr = ArrangementPlan(entries=[_drum_entry("A", 2), _drum_entry("B", 2)])
    chords = _final_chord(5, "B")
    phrases: list[Phrase] = [
        _drum_phrase(
            "kick",
            (sec.start_bar * BAR, (sec.start_bar + sec.length_bars) * BAR),
            [(sec.start_bar * BAR + b * BAR, 0.9) for b in range(sec.length_bars)],
        )
        for sec in form.sections
    ]
    out = transitions(phrases, form, chords, arr, _plan(0), pack)

    # The fill's snare rendered into bar 3; the crash voice was dropped.
    snare_fills = [
        n.ticks - 3 * BAR
        for p in out
        if p.track_id == "snare"
        for n in p.notes
        if "fill" in n.tags
    ]
    assert snare_fills == [1200]
    crash_fill_notes = [
        n for p in out if p.track_id == "crash" for n in p.notes if "fill" in n.tags
    ]
    assert crash_fill_notes == []  # no fill-tagged crash ever emitted
