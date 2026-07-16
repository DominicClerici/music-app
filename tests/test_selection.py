"""Pattern-selection mechanisms + draw counting (PHASE_5 §3.2/§3.6, SESSION_07 T2).

Unit-level proof of the selection machinery: the section-type→kind map,
cache-once-in-form-order, the tempo/energy eligible-set, draw-iff-≥2 discipline
(counting shim on the role's `select` stream), and the walking-bass exemption.
The end-to-end §9.1 draw narratives (pop 1 / jazz 3) are T3's charter.

Draws happen only through `weighted_choice`, so a `_CountingRandom` counting
`randrange` is the exact draw count for a role's select stream.
"""

from __future__ import annotations

import random

from trackgen.packs.models import (
    DrumEvent,
    Eligibility,
    Manifest,
    PatternEnvelope,
    PatternKind,
    PitchedEvent,
    Retarget,
    StylePack,
)
from trackgen.parts.selection import (
    RngFactory,
    SelectionKey,
    section_kind,
    select_patterns,
)
from trackgen.parts.selection import _eligible_set as eligible_set
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementEntry,
    ArrangementPlan,
    Budgets,
    FormSection,
    GenerationPlan,
    Key,
    MoodVector,
    Register,
    SectionEnding,
    SectionPhrase,
    SeedSpec,
    SongForm,
    StylePackRef,
    TimbreDirectives,
    TimeSignature,
)
from trackgen.seeds import Rng, derive, stream_seed, weighted_choice

_TPB = 1920
_MASTER = 3735928559
_OVERRIDES: dict[str, int] = {}


# --- fixture builders --------------------------------------------------------


class _CountingRandom(random.Random):
    """A seeded RNG counting `randrange` calls — one per `weighted_choice`, hence
    one per draw (mirrors the harmony goldens' shim)."""

    draws = 0

    def randrange(self, *args: object, **kwargs: object) -> int:
        self.draws += 1
        return super().randrange(*args, **kwargs)  # type: ignore[arg-type]


def _select_seed(role: Role) -> int:
    return derive(stream_seed(_MASTER, _OVERRIDES, role), "select")


def _drum(
    pattern_id: str,
    kind: PatternKind,
    energy: int,
    *,
    weight: int = 1,
    tempo: tuple[int, int] | None = None,
) -> PatternEnvelope:
    return PatternEnvelope(
        id=pattern_id,
        role="drums",
        kind=kind,
        energy_level=energy,
        length_ticks=_TPB,
        weight=weight,
        eligibility=Eligibility(tempo_bpm=tempo),
        events=[DrumEvent(pos=0, voice="kick", velocity=0.8)],
    )


def _pitched(
    pattern_id: str,
    role: Role,
    kind: PatternKind,
    energy: int,
    *,
    weight: int = 1,
    tempo: tuple[int, int] | None = None,
) -> PatternEnvelope:
    return PatternEnvelope(
        id=pattern_id,
        role=role,
        kind=kind,
        energy_level=energy,
        length_ticks=_TPB,
        weight=weight,
        eligibility=Eligibility(tempo_bpm=tempo),
        events=[PitchedEvent(pos=0, dur=480, degree="root", velocity=0.8)],
        retarget=Retarget(
            register_low=40, register_high=60, on_chord_change="retrigger"
        ),
    )


def _pack(
    patterns: dict[str, list[PatternEnvelope]],
    *,
    bass_mode: str = "patterns",
) -> StylePack:
    return StylePack(
        manifest=Manifest(
            format_version=1,
            id="syn",
            name="Synthetic",
            version="1",
            engine="trackgen",
            time_signatures=[(4, 4)],
            tempo_range=(60, 200),
        ),
        patterns=patterns,
        layering_order=("drums", "bass", "comping", "pads"),
        bass_mode=bass_mode,  # type: ignore[arg-type]
    )


def _section(section_id: str, section_type: str, start_bar: int) -> FormSection:
    return FormSection(
        id=section_id,
        type=section_type,
        index=1,
        start_bar=start_bar,
        length_bars=8,
        energy=0.5,
        total_of_type=1,
        phrases=[SectionPhrase(label="a", bars=8)],
        harmony_tag=section_type,
        ending=(
            SectionEnding(tag_bars=0, close="cold") if section_type == "outro" else None
        ),
    )


def _form(sections: list[FormSection]) -> SongForm:
    total = max(s.start_bar + s.length_bars for s in sections)
    return SongForm(sections=sections, total_bars=total, template_id="syn")


def _entry(section_id: str, role: Role, active: bool, rung: int) -> ArrangementEntry:
    return ArrangementEntry(
        section_id=section_id,
        role=role,
        active=active,
        intensity=rung,
        density_budget=0.5,
        register=Register(low_midi=40, high_midi=60),
    )


def _plan(tempo: float = 120.0) -> GenerationPlan:
    return GenerationPlan(
        style_pack=StylePackRef(id="syn", version="1"),
        seed=SeedSpec(master=_MASTER),
        key=Key(tonic_pc=0, mode="major"),
        tempo_bpm=tempo,
        time_signature=TimeSignature(numerator=4, denominator=4),
        max_length_ticks=200 * _TPB,
        mood_vector=MoodVector(valence=0.0, arousal=0.0),
        budgets=Budgets(
            note_density=0.5,
            dissonance=0.1,
            dynamics_base=0.5,
            dynamics_range=0.5,
            articulation_legato=0.5,
            layers_max=4,
            harmonic_rhythm_base=1.0,
            register_bias=0.0,
        ),
        timbre_directives=TimbreDirectives(
            brightness=0.5, attack_hardness=0.5, space=0.5
        ),
    )


def _shims() -> tuple[dict[Role, _CountingRandom], RngFactory]:
    """A per-role rng_factory yielding counting shims (seeded at the real §3.6
    select stream so draw outcomes match production) plus the dict collecting
    them, so a test can read each role's `.draws`."""
    collected: dict[Role, _CountingRandom] = {}

    def factory(role: Role) -> Rng:
        shim = _CountingRandom(_select_seed(role))
        shim.draws = 0
        collected[role] = shim
        return shim

    return collected, factory


# --- kind mapping ------------------------------------------------------------


def test_section_kind_intro() -> None:
    assert section_kind("intro") == "intro"


def test_section_kind_outro_maps_to_ending() -> None:
    assert section_kind("outro") == "ending"


def test_section_kind_breakdown_maps_to_main() -> None:
    assert section_kind("breakdown") == "main"


def test_section_kind_other_types_map_to_main() -> None:
    for section_type in ("verse", "chorus", "bridge", "head", "solo", "prechorus"):
        assert section_kind(section_type) == "main"


def test_kind_mapping_end_to_end_picks_the_right_bank() -> None:
    """intro→intro, outro→ending, breakdown→main banks are each consulted."""
    pack = _pack(
        {
            "drums": [
                _drum("dr_intro", "intro", 1),
                _drum("dr_end", "ending", 1),
                _drum("dr_main2", "main", 2),
            ]
        }
    )
    sections = [
        _section("intro-1", "intro", 0),
        _section("breakdown-1", "breakdown", 8),
        _section("outro-1", "outro", 16),
    ]
    arr = ArrangementPlan(
        entries=[
            _entry("intro-1", "drums", True, 2),
            _entry("breakdown-1", "drums", True, 2),
            _entry("outro-1", "drums", True, 2),
        ]
    )
    result = select_patterns(_plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES)
    assert result.by_section[("intro-1", "drums")].id == "dr_intro"
    assert result.by_section[("breakdown-1", "drums")].id == "dr_main2"
    assert result.by_section[("outro-1", "drums")].id == "dr_end"


# --- cache-once, form order --------------------------------------------------


def test_same_rung_sections_share_one_pattern_and_one_draw() -> None:
    """verse-1 ≡ verse-2 at the same rung: identical pattern, a single draw."""
    pack = _pack(
        {"drums": [_drum("dr_2a", "main", 2, weight=1), _drum("dr_2b", "main", 2)]}
    )
    sections = [_section("verse-1", "verse", 0), _section("verse-2", "verse", 8)]
    arr = ArrangementPlan(
        entries=[
            _entry("verse-1", "drums", True, 2),
            _entry("verse-2", "drums", True, 2),
        ]
    )
    shims, factory = _shims()
    result = select_patterns(
        _plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES, rng_factory=factory
    )
    assert (
        result.by_section[("verse-1", "drums")]
        is result.by_section[("verse-2", "drums")]
    )
    assert shims["drums"].draws == 1


def test_different_rung_section_redraws_its_own_key() -> None:
    """rung-3 chorus vs rung-2 verse resolve to distinct keys (a fresh draw)."""
    pack = _pack(
        {
            "drums": [
                _drum("dr_2a", "main", 2),
                _drum("dr_2b", "main", 2),
                _drum("dr_3a", "main", 3),
                _drum("dr_3b", "main", 3),
            ]
        }
    )
    sections = [_section("verse-1", "verse", 0), _section("chorus-1", "chorus", 8)]
    arr = ArrangementPlan(
        entries=[
            _entry("verse-1", "drums", True, 2),
            _entry("chorus-1", "drums", True, 3),
        ]
    )
    shims, factory = _shims()
    result = select_patterns(
        _plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES, rng_factory=factory
    )
    key2: SelectionKey = ("drums", "main", 2)
    key3: SelectionKey = ("drums", "main", 3)
    assert key2 in result.by_key and key3 in result.by_key
    assert result.by_key[key2].energy_level == 2
    assert result.by_key[key3].energy_level == 3
    assert shims["drums"].draws == 2


# --- eligible set ------------------------------------------------------------


def test_main_eligible_set_filters_on_energy_level() -> None:
    pack = _pack(
        {
            "drums": [
                _drum("dr_1", "main", 1),
                _drum("dr_2", "main", 2),
                _drum("dr_3", "main", 3),
            ]
        }
    )
    eligible = eligible_set(pack, "drums", "main", 2, 120.0)
    assert [p.id for p in eligible] == ["dr_2"]


def test_intro_ending_eligible_set_ignores_energy_level() -> None:
    pack = _pack(
        {
            "drums": [
                _drum("dr_i_lo", "intro", 1),
                _drum("dr_i_hi", "intro", 4),
                _drum("dr_e", "ending", 2),
            ]
        }
    )
    intro = eligible_set(pack, "drums", "intro", 2, 120.0)
    assert [p.id for p in intro] == ["dr_i_lo", "dr_i_hi"]
    ending = eligible_set(pack, "drums", "ending", 3, 120.0)
    assert [p.id for p in ending] == ["dr_e"]


def test_tempo_gate_excludes_outside_band_includes_inside() -> None:
    pack = _pack(
        {
            "drums": [
                _drum("dr_open", "main", 2),
                _drum("dr_fast", "main", 2, tempo=(130, 180)),
            ]
        }
    )
    slow = eligible_set(pack, "drums", "main", 2, 120.0)
    assert [p.id for p in slow] == ["dr_open"]
    fast = eligible_set(pack, "drums", "main", 2, 150.0)
    assert [p.id for p in fast] == ["dr_open", "dr_fast"]
    # Boundary is inclusive on both ends.
    assert len(eligible_set(pack, "drums", "main", 2, 130.0)) == 2
    assert len(eligible_set(pack, "drums", "main", 2, 180.0)) == 2


def test_tempo_gated_pattern_excluded_from_selection_outside_band() -> None:
    """A rung with one ungated + one gated main resolves to the ungated pattern
    when the tempo is outside the gate — with no draw (singleton eligible)."""
    pack = _pack(
        {
            "drums": [
                _drum("dr_open", "main", 2),
                _drum("dr_fast", "main", 2, tempo=(130, 180)),
            ]
        }
    )
    sections = [_section("verse-1", "verse", 0)]
    arr = ArrangementPlan(entries=[_entry("verse-1", "drums", True, 2)])
    shims, factory = _shims()
    result = select_patterns(
        _plan(tempo=120.0),
        _form(sections),
        arr,
        pack,
        _MASTER,
        _OVERRIDES,
        rng_factory=factory,
    )
    assert result.by_section[("verse-1", "drums")].id == "dr_open"
    assert shims["drums"].draws == 0


# --- draw discipline ---------------------------------------------------------


def test_singleton_eligible_set_consumes_zero_draws() -> None:
    pack = _pack({"drums": [_drum("dr_only", "main", 2)]})
    sections = [_section("verse-1", "verse", 0)]
    arr = ArrangementPlan(entries=[_entry("verse-1", "drums", True, 2)])
    shims, factory = _shims()
    result = select_patterns(
        _plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES, rng_factory=factory
    )
    assert result.by_section[("verse-1", "drums")].id == "dr_only"
    assert shims["drums"].draws == 0


def test_two_candidate_set_draws_once_and_matches_independent_replay() -> None:
    pack = _pack(
        {
            "drums": [
                _drum("dr_2a", "main", 2, weight=3),
                _drum("dr_2b", "main", 2, weight=2),
            ]
        }
    )
    sections = [_section("verse-1", "verse", 0)]
    arr = ArrangementPlan(entries=[_entry("verse-1", "drums", True, 2)])
    shims, factory = _shims()
    result = select_patterns(
        _plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES, rng_factory=factory
    )
    assert shims["drums"].draws == 1

    # Independent replay of the same draw over the same eligible set.
    eligible = eligible_set(pack, "drums", "main", 2, 120.0)
    replay = Rng(_select_seed("drums"))
    winner = weighted_choice(eligible, [p.weight for p in eligible], replay)
    assert result.by_section[("verse-1", "drums")].id == winner.id


# --- bass walking-mode exemption + active-only -------------------------------


def test_walking_bass_produces_no_selection_and_no_draws() -> None:
    pack = _pack(
        {"drums": [_drum("dr_2", "main", 2)]},  # walking bass carries no patterns
        bass_mode="walking",
    )
    sections = [_section("verse-1", "verse", 0)]
    arr = ArrangementPlan(
        entries=[
            _entry("verse-1", "drums", True, 2),
            _entry("verse-1", "bass", True, 2),
        ]
    )
    shims, factory = _shims()
    result = select_patterns(
        _plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES, rng_factory=factory
    )
    assert ("verse-1", "bass") not in result.by_section
    assert ("bass", "main", 2) not in result.by_key
    assert "bass" not in shims  # its select stream was never even constructed
    assert result.by_section[("verse-1", "drums")].id == "dr_2"


def test_pattern_mode_bass_selects_normally() -> None:
    pack = _pack(
        {
            "drums": [_drum("dr_2", "main", 2)],
            "bass": [_pitched("ba_2", "bass", "main", 2)],
        },
        bass_mode="patterns",
    )
    sections = [_section("verse-1", "verse", 0)]
    arr = ArrangementPlan(
        entries=[
            _entry("verse-1", "drums", True, 2),
            _entry("verse-1", "bass", True, 2),
        ]
    )
    result = select_patterns(_plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES)
    assert result.by_section[("verse-1", "bass")].id == "ba_2"


def test_inactive_role_contributes_no_selection() -> None:
    pack = _pack(
        {
            "drums": [_drum("dr_2", "main", 2)],
            "pads": [_pitched("pa_2", "pads", "main", 2)],
        }
    )
    sections = [_section("verse-1", "verse", 0)]
    arr = ArrangementPlan(
        entries=[
            _entry("verse-1", "drums", True, 2),
            _entry("verse-1", "pads", False, 2),  # capped out by layersMax
        ]
    )
    shims, factory = _shims()
    result = select_patterns(
        _plan(), _form(sections), arr, pack, _MASTER, _OVERRIDES, rng_factory=factory
    )
    assert ("verse-1", "pads") not in result.by_section
    assert "pads" not in shims
    assert result.by_section[("verse-1", "drums")].id == "dr_2"
