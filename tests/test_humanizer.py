"""Unit tests for the Humanizer engine (PHASE_6 §5, §11.5).

Covers swing (§5.2), offset maps (§5.3), the `tri` helper (§5.4), velocity
accent + jitter width (§5.5), bass legato (§5.6), and note-count preservation
(§5) — plus the pre-jitter testability seam (`_run` with `_ZeroJitter`, DoD 5).
"""

from __future__ import annotations

from trackgen.humanize.stage import (
    _run,
    _TriangularJitter,
    _vel_jitter_width,
    _ZeroJitter,
    humanize,
    tri,
)
from trackgen.humanize.swing import swing_phrase
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    Budgets,
    GenerationPlan,
    Key,
    MoodVector,
    Phrase,
    PhraseNote,
    SeedSpec,
    SongForm,
    StylePackRef,
    SwingSpec,
    TimbreDirectives,
    TimeSignature,
)
from trackgen.seeds import Rng

_MASTER = 3735928559  # seed `1ps9wxb` (PHASE_6 §7).


# --- fixtures -----------------------------------------------------------------


def _plan(
    *,
    tempo_bpm: float,
    swing: SwingSpec | None,
    dynamics_range: float = 0.21,
    master: int = _MASTER,
) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="test", version="1.0.0"),
        seed=SeedSpec(master=master, overrides={}),
        key=Key(tonic_pc=0, mode="ionian"),
        tempo_bpm=tempo_bpm,
        time_signature=TimeSignature(numerator=4, denominator=4),
        swing=swing,
        max_length_ticks=0,
        role_flavors={},
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=0.3,
            dynamics_base=0.7,
            dynamics_range=dynamics_range,
            articulation_legato=0.8,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def _form(total_bars: int) -> SongForm:
    return SongForm(sections=[], total_bars=total_bars, template_id="test")


def _note(
    ticks: int, dur: int = 120, midi: int | None = None, vel: float = 0.5
) -> PhraseNote:
    return PhraseNote(ticks=ticks, duration_ticks=dur, midi=midi, velocity=vel)


_SWING8 = SwingSpec(ratio=0.722, subdivision="8")
_SWING16 = SwingSpec(ratio=0.722, subdivision="16")


# --- §5.2 swing ---------------------------------------------------------------


def test_swing8_moves_offbeats_only_leaves_downbeats_and_16ths() -> None:
    notes = [_note(0), _note(120), _note(240), _note(480), _note(720), _note(960)]
    out = swing_phrase(notes, _SWING8)
    starts = [s for s, _ in out]
    # downbeats (0/480/960) and the 16th (120) are untouched; offbeats swing.
    assert starts == [0, 120, 347, 480, 827, 960]


def test_swing16_moves_16th_offbeats_only() -> None:
    notes = [_note(0), _note(120), _note(240), _note(360)]
    out = swing_phrase(notes, _SWING16)
    starts = [s for s, _ in out]
    disp = round(240 * 0.722)  # 173
    # 8ths at 0/240 unmoved; 16th offbeats at 120/360 swing.
    assert starts == [0, (120 - 120) + disp, 240, (360 - 120) + disp]


def test_straight_pack_swing_is_noop() -> None:
    notes = [_note(0), _note(240, dur=200), _note(720)]
    out = swing_phrase(notes, None)
    assert out == [(0, 120), (240, 200), (720, 120)]


def test_gap_preserving_stretch_earlier_note_reaches_swung_start() -> None:
    # A downbeat note ending exactly at the offbeat's original start is stretched
    # to the offbeat's new (delayed) start.
    down = _note(0, dur=240)  # ends at 240, abuts the offbeat at 240
    off = _note(240, dur=60)
    out = swing_phrase([down, off], _SWING8)
    (down_start, down_dur), (off_start, _off_dur) = out
    assert down_start == 0
    assert off_start == 347
    assert down_dur == 347  # stretched from 240 to the swung start


def test_gap_preserving_swung_note_shrinks_to_kept_end() -> None:
    # An offbeat note filling up to the next beat keeps that end; its start moved
    # later, so its duration shrinks (the swung short note).
    off = _note(240, dur=240)  # 240..480, abuts the next grid point (480)
    out = swing_phrase([off], _SWING8)
    (start, dur) = out[0]
    assert start == 347
    assert dur == 480 - 347  # 133 — end held at 480


# --- §5.3 offset maps ---------------------------------------------------------


def _single_tick(
    role: Role, track_id: str, note: PhraseNote, plan: GenerationPlan
) -> int:
    # Through the real path with the zero-jitter seam, so the position reflects
    # only the deterministic swing+offset transform (§11.5).
    phrase = Phrase(
        track_id=track_id, role=role, start_tick=0, end_tick=1920, notes=[note]
    )
    out, _ = _run([phrase], _form(4), plan, _ZeroJitter())
    return out[0].notes[0].ticks


def test_offset_straight_table_ms_to_tick_both_tempi() -> None:
    # straight bass offset = +2 ms scalar. 123 BPM: tpm 0.984; 69 BPM: 0.552.
    note = _note(480, midi=40)
    at123 = _single_tick("bass", "bass", note, _plan(tempo_bpm=123, swing=None))
    at69 = _single_tick("bass", "bass", note, _plan(tempo_bpm=69, swing=None))
    assert at123 == round(480 + 2 * 0.984)  # 482
    assert at69 == round(480 + 2 * 0.552)  # 481


def test_offset_swung_table_comping_downbeat_map_and_bass() -> None:
    # swung comping `down` offset = +18 ms; at 69 BPM -> +10 ticks (§7.2).
    comp = _note(0, midi=60)
    tick = _single_tick("comping", "comping", comp, _plan(tempo_bpm=69, swing=_SWING8))
    assert tick == round(0 + 18 * 0.552)  # 10
    # swung bass `beat3` note at 960 (offset -2 ms) -> 959 (§7.2).
    bass = _note(960, midi=45)
    btick = _single_tick("bass", "bass", bass, _plan(tempo_bpm=69, swing=_SWING8))
    assert btick == 959


def test_offset_drum_voice_keys_by_track_id_with_tom_collapse() -> None:
    # swung snare offset = +3 ms; toms collapse to the `toms` row (offset 0).
    plan = _plan(tempo_bpm=123, swing=_SWING8)
    snare_tick = _single_tick("drums", "snare", _note(480), plan)
    tom_tick = _single_tick("drums", "tom_mid", _note(480), plan)
    assert snare_tick == round(480 + 3 * 0.984)  # 483
    assert tom_tick == 480  # toms offset 0


# --- §5.4 the tri helper ------------------------------------------------------


def test_tri_bounds_stay_within_plus_minus_w() -> None:
    rng = Rng(12345)
    for w in (1, 3, 5, 8):
        for _ in range(2000):
            assert -w <= tri(rng, w) <= w


def test_tri_reaches_both_extremes() -> None:
    rng = Rng(7)
    w = 3
    seen = {tri(rng, w) for _ in range(5000)}
    assert -w in seen and w in seen


def test_timing_jitter_skips_draw_at_zero_width() -> None:
    jitter = _TriangularJitter()
    rng = Rng(99)
    before = rng.getstate()
    assert jitter.timing(rng, 0) == 0
    assert rng.getstate() == before  # RNG untouched when w == 0
    # a real width consumes state.
    assert -5 <= jitter.timing(rng, 5) <= 5
    assert rng.getstate() != before


def test_velocity_jitter_skips_draw_at_zero_width() -> None:
    jitter = _TriangularJitter()
    rng = Rng(99)
    before = rng.getstate()
    assert jitter.velocity(rng, 0) == 0.0
    assert rng.getstate() == before  # RNG untouched when width == 0
    # a real width consumes state.
    assert isinstance(jitter.velocity(rng, 57), float)
    assert rng.getstate() != before


# --- §5.5 accent map + velocity width -----------------------------------------


def _single_vel(beat_tick: int, plan: GenerationPlan) -> float:
    note = _note(beat_tick, midi=50, vel=0.5)
    phrase = Phrase(
        track_id="pads", role="pads", start_tick=0, end_tick=1920, notes=[note]
    )
    out, _ = humanize([phrase], _form(4), plan)
    return out[0].notes[0].velocity


def test_accent_map_delta_per_beat_class() -> None:
    plan = _plan(tempo_bpm=123, swing=None)  # pads: no jitter, accent applies
    assert _single_vel(0, plan) == 0.53  # down +0.03
    assert _single_vel(480, plan) == 0.5  # back2 +0.0
    assert _single_vel(960, plan) == 0.515  # beat3 +0.015
    assert _single_vel(1440, plan) == 0.5  # back4 +0.0
    assert _single_vel(720, plan) == 0.47  # off -0.03


def test_velocity_jitter_width_formula() -> None:
    assert _vel_jitter_width(0.04, 0.08, 0.21) == 57
    assert _vel_jitter_width(0.04, 0.08, 0.35) == 68


# --- §5.6 bass legato ---------------------------------------------------------


def _bass_durations(notes: list[PhraseNote], plan: GenerationPlan) -> list[int]:
    phrase = Phrase(
        track_id="bass", role="bass", start_tick=0, end_tick=3840, notes=notes
    )
    out, _ = humanize([phrase], _form(4), plan)
    return [n.duration_ticks for n in out[0].notes]


def test_bass_legato_straight_quarter_and_final_note_exempt() -> None:
    # IOI 480, abutting dur -> 0.95*480 = 456; final note (no successor) untouched.
    notes = [_note(0, dur=460, midi=40), _note(480, dur=460, midi=42)]
    durs = _bass_durations(notes, _plan(tempo_bpm=123, swing=None))
    assert durs == [456, 460]


def test_bass_legato_swung_two_feel_half() -> None:
    # IOI 960, abutting dur -> 0.95*960 = 912; final note untouched.
    notes = [_note(0, dur=920, midi=38), _note(960, dur=920, midi=41)]
    durs = _bass_durations(notes, _plan(tempo_bpm=69, swing=_SWING8))
    assert durs == [912, 920]


def test_bass_legato_not_applied_when_gap_exceeds_60() -> None:
    # gap = 480 - 400 = 80 > 60 -> duration passes through.
    notes = [_note(0, dur=400, midi=40), _note(480, dur=400, midi=42)]
    durs = _bass_durations(notes, _plan(tempo_bpm=123, swing=None))
    assert durs == [400, 400]


def test_bass_legato_is_track_level_across_phrase_boundary() -> None:
    # Two adjacent bass phrases (section 0 bars 0-3, section 1 bars 4-7). The
    # LAST note of phrase 0 (tick 7200, dur 434) abuts the FIRST attack of
    # phrase 1 (tick 7680) with gap 46 <= 60. The next-attack search is
    # TRACK-level (§5.6), so 7200's successor is found across the phrase seam and
    # it stretches to round(0.95*480) = 456; the per-phrase bug would leave 434.
    # Only the globally-final bass note (phrase 1's last, no successor) is exempt.
    p0 = Phrase(
        track_id="bass",
        role="bass",
        start_tick=0,
        end_tick=7680,
        notes=[_note(6720, dur=460, midi=39), _note(7200, dur=434, midi=40)],
    )
    p1 = Phrase(
        track_id="bass",
        role="bass",
        start_tick=7680,
        end_tick=15360,
        notes=[_note(7680, dur=434, midi=41), _note(8160, dur=920, midi=42)],
    )
    out, _ = humanize([p0, p1], _form(8), _plan(tempo_bpm=123, swing=None))
    dur_by_midi = {n.midi: n.duration_ticks for p in out for n in p.notes}
    # phrase-0 last note found its successor across the seam -> stretched.
    assert dur_by_midi[40] == 456
    # phrase-0 interior and phrase-1 first attack also stretch (abutting).
    assert dur_by_midi[39] == 456
    assert dur_by_midi[41] == 456
    # only the globally-final bass note is exempt.
    assert dur_by_midi[42] == 920


# --- the pre-jitter testability seam (DoD 5) ----------------------------------


def test_zero_jitter_seam_reproduces_prejitter_positions() -> None:
    plan = _plan(tempo_bpm=69, swing=_SWING8)
    ride = Phrase(
        track_id="ride",
        role="drums",
        start_tick=0,
        end_tick=1920,
        notes=[_note(720)],
    )
    comp = Phrase(
        track_id="comping",
        role="comping",
        start_tick=0,
        end_tick=1920,
        notes=[_note(0, midi=60)],
    )
    out, tempos = _run([ride, comp], _form(4), plan, _ZeroJitter())
    assert tempos == []
    ride_out = next(p for p in out if p.track_id == "ride")
    comp_out = next(p for p in out if p.track_id == "comping")
    assert ride_out.notes[0].ticks == 827  # swing, ride offset 0
    assert comp_out.notes[0].ticks == 10  # comping down +18 ms at 69 BPM


# --- note-count preservation (§5) ---------------------------------------------


def _multi_role_phrases() -> list[Phrase]:
    return [
        Phrase(
            track_id="kick",
            role="drums",
            start_tick=0,
            end_tick=3840,
            notes=[_note(0), _note(960), _note(1920), _note(2880)],
        ),
        Phrase(
            track_id="snare",
            role="drums",
            start_tick=0,
            end_tick=3840,
            notes=[_note(480), _note(1440), _note(2400), _note(3360)],
        ),
        Phrase(
            track_id="hats",
            role="drums",
            start_tick=0,
            end_tick=3840,
            notes=[_note(t) for t in range(0, 3840, 240)],
        ),
        Phrase(
            track_id="bass",
            role="bass",
            start_tick=0,
            end_tick=3840,
            notes=[
                _note(t, dur=460, midi=40 + (t // 480) % 5) for t in range(0, 3840, 480)
            ],
        ),
        Phrase(
            track_id="comping",
            role="comping",
            start_tick=0,
            end_tick=3840,
            notes=[_note(t, dur=440, midi=60, vel=0.6) for t in (0, 720, 1920, 2640)],
        ),
        Phrase(
            track_id="pads",
            role="pads",
            start_tick=0,
            end_tick=3840,
            notes=[_note(0, dur=1900, midi=55), _note(1920, dur=1900, midi=57)],
        ),
    ]


def test_note_count_preserved_and_midi_tags_untouched() -> None:
    phrases = _multi_role_phrases()
    plan = _plan(tempo_bpm=123, swing=_SWING8, dynamics_range=0.35)
    out, tempos = humanize(phrases, _form(2), plan)

    assert tempos == []
    assert len(out) == len(phrases)
    assert sum(len(p.notes) for p in out) == sum(len(p.notes) for p in phrases)
    for src, dst in zip(phrases, out, strict=True):
        assert len(src.notes) == len(dst.notes)
        # midi and tags pass through untouched (compared as multisets — the
        # per-phrase re-sort may reorder near-simultaneous notes).
        assert sorted(str(n.midi) for n in src.notes) == sorted(
            str(n.midi) for n in dst.notes
        )
        assert sorted(tuple(n.tags) for n in src.notes) == sorted(
            tuple(n.tags) for n in dst.notes
        )


def test_humanize_is_deterministic() -> None:
    phrases = _multi_role_phrases()
    plan = _plan(tempo_bpm=123, swing=_SWING8)
    first, _ = humanize(phrases, _form(2), plan)
    second, _ = humanize(phrases, _form(2), plan)
    assert first == second
