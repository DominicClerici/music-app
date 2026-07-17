"""Property tests for the ritard tempo-curve renderer (PHASE_6 §5.7, §11.6).

Asserts the §11.6 properties of the curve — monotone decreasing, floored well
above zero, confined to the tag, and the cold/fade zero-event alias — plus the
integration through `humanize`'s second return. The exact 39-value §7.2 table is
Task T4's golden; nothing here hardcodes a count or a bpm value.
"""

from __future__ import annotations

from trackgen.humanize.ritard import _sample_rels, ritard_events
from trackgen.humanize.stage import humanize
from trackgen.schema.ir import (
    Budgets,
    FormSection,
    GenerationPlan,
    Key,
    MoodVector,
    SectionEnding,
    SectionPhrase,
    SeedSpec,
    SongForm,
    StylePackRef,
    SwingSpec,
    TimbreDirectives,
    TimeSignature,
)

BAR = 1920
_MASTER = 3735928559  # seed `1ps9wxb` (PHASE_6 §7).


# --- fixtures -----------------------------------------------------------------


def _plan(*, tempo_bpm: float = 69.0, swing: SwingSpec | None = None) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="test", version="1.0.0"),
        seed=SeedSpec(master=_MASTER, overrides={}),
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
            dynamics_range=0.21,
            articulation_legato=0.8,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def _form(
    *,
    close: str | None,
    tag_bars: int = 4,
    start_bar: int = 48,
    length_bars: int = 16,
) -> SongForm:
    ending = (
        None if close is None else SectionEnding(tag_bars=tag_bars, close=close)  # type: ignore[arg-type]
    )
    section = FormSection(
        id="outro",
        type="outro",
        index=1,
        start_bar=start_bar,
        length_bars=length_bars,
        energy=0.5,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=length_bars)],
        harmony_tag="x",
        ending=ending,
    )
    return SongForm(
        sections=[section], total_bars=start_bar + length_bars, template_id="test"
    )


# jazz-like reference: 69 BPM, 4-bar tag (bars 60-64), end_tick 122880.
_JAZZ_PLAN = _plan(tempo_bpm=69.0, swing=SwingSpec(ratio=0.722, subdivision="8"))
_JAZZ_END_TICK = (48 + 16) * BAR
_JAZZ_TAG_START = _JAZZ_END_TICK - 4 * BAR


# --- properties (§11.6) -------------------------------------------------------


def test_monotone_strictly_decreasing() -> None:
    events = ritard_events(_form(close="ritard"), _JAZZ_PLAN)
    assert len(events) > 1
    bpms = [e.bpm for e in events]
    assert all(a > b for a, b in zip(bpms, bpms[1:], strict=False))


def test_never_below_half_base() -> None:
    events = ritard_events(_form(close="ritard"), _JAZZ_PLAN)
    floor = 0.5 * _JAZZ_PLAN.tempo_bpm
    assert all(e.bpm > floor for e in events)


def test_first_event_after_tag_start_and_positive() -> None:
    events = ritard_events(_form(close="ritard"), _JAZZ_PLAN)
    assert events[0].ticks > _JAZZ_TAG_START
    assert events[0].ticks > 0


def test_no_event_at_or_after_release_downbeat() -> None:
    events = ritard_events(_form(close="ritard"), _JAZZ_PLAN)
    assert all(_JAZZ_TAG_START < e.ticks < _JAZZ_END_TICK for e in events)


def test_ticks_absolute_and_ascending() -> None:
    events = ritard_events(_form(close="ritard"), _JAZZ_PLAN)
    ticks = [e.ticks for e in events]
    assert ticks == sorted(ticks)
    assert len(set(ticks)) == len(ticks)
    assert ticks[0] >= _JAZZ_TAG_START


def test_density_increases_in_final_bar() -> None:
    """Per-8th (240) elsewhere, per-16th (120) across the final tag bar (§5.7)."""
    tag_length = 4 * BAR
    rels = _sample_rels(tag_length)
    final_bar_start = tag_length - BAR
    final_bar = [r for r in rels if r >= final_bar_start]
    prior_bar = [r for r in rels if 0 <= r < BAR]
    assert len(final_bar) == BAR // 120
    assert len(prior_bar) == BAR // 240
    assert len(final_bar) > len(prior_bar)
    final_steps = {b - a for a, b in zip(final_bar, final_bar[1:], strict=False)}
    assert final_steps == {120}


def test_tag_bars_zero_uses_last_bar_all_16ths() -> None:
    plan = _plan(tempo_bpm=69.0)
    events = ritard_events(_form(close="ritard", tag_bars=0), plan)
    end_tick = (48 + 16) * BAR
    tag_start = end_tick - BAR
    assert len(events) > 1
    assert all(tag_start < e.ticks < end_tick for e in events)
    # rel-0 base sample dropped, so the first emitted event is the +120 sample.
    assert events[0].ticks == tag_start + 120
    bpms = [e.bpm for e in events]
    assert all(a > b for a, b in zip(bpms, bpms[1:], strict=False))


# --- cold / fade zero-event alias (D7) ----------------------------------------


def test_cold_emits_no_events() -> None:
    assert ritard_events(_form(close="cold"), _JAZZ_PLAN) == []


def test_fade_emits_no_events() -> None:
    assert ritard_events(_form(close="fade"), _JAZZ_PLAN) == []


def test_fade_renders_identically_to_cold() -> None:
    assert ritard_events(_form(close="fade"), _JAZZ_PLAN) == ritard_events(
        _form(close="cold"), _JAZZ_PLAN
    )


def test_no_ending_emits_no_events() -> None:
    assert ritard_events(_form(close=None), _JAZZ_PLAN) == []


def test_empty_form_emits_no_events() -> None:
    empty = SongForm(sections=[], total_bars=0, template_id="test")
    assert ritard_events(empty, _JAZZ_PLAN) == []


# --- integration through the public entry (§6) --------------------------------


def test_humanize_second_return_is_ritard_for_ritard_ending() -> None:
    _phrases, tempos = humanize([], _form(close="ritard"), _JAZZ_PLAN)
    assert tempos == ritard_events(_form(close="ritard"), _JAZZ_PLAN)
    assert len(tempos) > 1


def test_humanize_second_return_is_empty_for_cold_ending() -> None:
    _phrases, tempos = humanize([], _form(close="cold"), _JAZZ_PLAN)
    assert tempos == []
