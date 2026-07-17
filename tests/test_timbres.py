"""Timbres substrate + stub-stage tests (PHASE_5 §8.4 / D-A / D-B, SESSION_09 T1).

Covers: both reference packs load with a non-None `.timbres`; every declared
flavor id (interpreter.yaml) is present in the loaded `TimbresConfig`;
`sound_design` returns the D-B track-id → `TrackSound` map with correct drum
trigger midis; the `transitions`/`humanize` stubs are identity; and
`sound_design` performs zero RNG draws (immune to global `random` state).
"""

from __future__ import annotations

import random
from pathlib import Path

from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack, TimbresConfig
from trackgen.pipeline.stubs import TrackSound, humanize, sound_design, transitions
from trackgen.schema.ir import GenerationPlan, Phrase, PhraseNote

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}

# The flavor ids each pack's interpreter.yaml declares (D-A completeness list).
_POP_FLAVORS: dict[str, set[str]] = {
    "drums": {"acoustic_kit", "tight_kit"},
    "bass": {"electric_fingered", "electric_picked"},
    "comping": {"clean_electric", "crunch_electric", "piano"},
    "pads": {"warm_analog", "airy_strings"},
}
_JAZZ_FLAVORS: dict[str, set[str]] = {
    "drums": {"brush_kit", "ride_kit"},
    "bass": {"upright"},
    "comping": {"piano", "guitar_hollow"},
    "pads": {"airy_strings", "organ_soft"},
}

_DRUM_TRACK_IDS = (
    "kick",
    "snare",
    "hats",
    "ride",
    "tom_low",
    "tom_mid",
    "tom_high",
    "perc",
)
# Expected drum trigger midis (D-A); snare (NoiseSynth) carries no midi (V5).
_EXPECTED_DRUM_MIDI: dict[str, int | None] = {
    "kick": 24,
    "snare": None,
    "hats": 80,
    "ride": 82,
    "tom_low": 43,
    "tom_mid": 47,
    "tom_high": 50,
    "perc": 39,
}


def _pack(style: str) -> StylePack:
    pack = resolve_pack(style)
    assert pack is not None
    return pack


def _plan(params: dict[str, object]) -> GenerationPlan:
    return generate_plan(params)


def test_both_packs_load_with_timbres() -> None:
    """Both reference packs load with a non-None `.timbres` (TimbresConfig)."""
    for style in ("pop_rock", "jazz"):
        pack = _pack(style)
        assert isinstance(pack.timbres, TimbresConfig)


def test_every_flavor_id_present() -> None:
    """Every declared flavor id (interpreter.yaml) is keyed in the loaded
    TimbresConfig for each role — drums as a kit, pitched roles as a timbre."""
    for style, expected in (("pop_rock", _POP_FLAVORS), ("jazz", _JAZZ_FLAVORS)):
        timbres = _pack(style).timbres
        assert timbres is not None
        assert set(timbres.drums) == expected["drums"]
        assert set(timbres.bass) == expected["bass"]
        assert set(timbres.comping) == expected["comping"]
        assert set(timbres.pads) == expected["pads"]
        # Each drum kit is complete (all eight tracks present).
        for kit in timbres.drums.values():
            assert set(kit) == set(_DRUM_TRACK_IDS)


def test_sound_design_returns_all_tracks() -> None:
    """`sound_design` returns a `TrackSound` for the eight drum track ids plus
    bass/comping/pads, for both worked examples (D-B)."""
    for params in (_POP, _JAZZ):
        sounds = sound_design(_plan(params), _pack(str(params["styleFamily"])))
        assert set(sounds) == set(_DRUM_TRACK_IDS) | {"bass", "comping", "pads"}
        for sound in sounds.values():
            assert isinstance(sound, TrackSound)
            assert sound.effects == []


def test_sound_design_drum_trigger_midi() -> None:
    """Drum trigger midis: snare None; kick/hats/ride 24/80/82;
    tom_low/mid/high 43/47/50; perc 39. Pitched roles carry midi None."""
    for params in (_POP, _JAZZ):
        sounds = sound_design(_plan(params), _pack(str(params["styleFamily"])))
        for track_id, expected_midi in _EXPECTED_DRUM_MIDI.items():
            assert sounds[track_id].midi == expected_midi, (params, track_id)
        assert sounds["snare"].midi is None
        for role in ("bass", "comping", "pads"):
            assert sounds[role].midi is None


def test_sound_design_is_zero_draw() -> None:
    """`sound_design` makes zero RNG draws: perturbing the global `random`
    module state around it cannot change the output (mirrors the DoD-9
    module-random-state pattern)."""
    plan = _plan(_POP)
    pack = _pack("pop_rock")
    random.seed(1)
    a = sound_design(plan, pack)
    random.seed(9_999_991)
    b = sound_design(plan, pack)
    assert a == b


def test_stubs_import_no_entropy_sources() -> None:
    """Structural: the stubs module imports no `random`/`time`/`datetime`
    (invariant 5 / TID251 — the reserved seed streams stay unused)."""
    src = Path(__file__).resolve().parents[1] / "src" / "trackgen" / "pipeline"
    text = (src / "stubs.py").read_text(encoding="utf-8")
    for banned in ("import random", "import time", "import datetime", "from datetime"):
        assert banned not in text, banned


def test_transitions_is_identity() -> None:
    """`transitions` returns its input phrases unchanged."""
    phrases = [
        Phrase(
            track_id="kick",
            role="drums",
            start_tick=0,
            end_tick=1920,
            notes=[PhraseNote(ticks=0, duration_ticks=120, velocity=0.9)],
        )
    ]
    assert transitions(phrases) is phrases


def test_humanize_returns_phrases_and_empty_tempo() -> None:
    """`humanize` returns the phrases unchanged and an empty tempo-event list."""
    phrases = [
        Phrase(
            track_id="bass",
            role="bass",
            start_tick=0,
            end_tick=1920,
            notes=[PhraseNote(ticks=0, duration_ticks=480, midi=40, velocity=0.8)],
        )
    ]
    out_phrases, tempo_events = humanize(phrases)
    assert out_phrases is phrases
    assert tempo_events == []
