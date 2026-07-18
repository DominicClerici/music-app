"""Unit tests for the sound-design stage (PHASE_7 §7; SESSION_14 T1).

Exercises the stage's evaluation paths against the real reference
`styles/{pack}/timbres.yaml` content (the single source of truth after the C2
flip): the pitched + drum evaluation paths, the PolySynth
`{type, voice, maxPolyphony, options}` emission, the reverb-send present/absent
branch, the §6.2 bus evaluation at both endpoints and a midpoint, master-verbatim,
and repeated-run identity. Field-for-field §9.1/§9.2 goldens live in
`test_sound_stage_goldens.py`.
"""

from pathlib import Path
from typing import Any

import yaml

from trackgen.interpreter.stage import generate_plan
from trackgen.schema.ir import GenerationPlan, TimbreDirectives
from trackgen.seeds import Rng
from trackgen.sound.evaluate import round3
from trackgen.sound.stage import SoundDesign, sound_design
from trackgen.sound.timbres import KIT_VOICE_IDS, TimbresConfig

_STYLES = Path(__file__).resolve().parents[1] / "styles"

# The reserved `sound` seed stream: `sound_design` accepts it for interface
# uniformity and never draws (D3), so any Rng gives identical output.
_RNG = Rng(0)


def _timbres(pack: str) -> TimbresConfig:
    raw: Any = yaml.safe_load((_STYLES / pack / "timbres.yaml").read_text())
    return TimbresConfig.model_validate(raw)


def _pop_plan() -> GenerationPlan:
    return generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})


def _with_directives(
    plan: GenerationPlan, brightness: float, attack: float, space: float
) -> GenerationPlan:
    return plan.model_copy(
        update={
            "timbre_directives": TimbreDirectives(
                brightness=brightness, attack_hardness=attack, space=space
            )
        }
    )


# --- pitched-role evaluation -------------------------------------------------


def test_pitched_evaluation_bakes_mapped_params() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    bass = sd.track_sounds["bass"].instrument.options
    # electric_fingered has no `mod`; the MonoSynth bass defaults evaluate at
    # brightness 0.835 / attackHardness 0.66.
    assert bass["filterEnvelope"]["baseFrequency"] == round3(
        120 * (2500 / 120) ** 0.835
    )
    assert bass["filter"]["Q"] == round3(0.8 + 0.835 * (2.0 - 0.8))
    assert bass["envelope"]["attack"] == round3(0.12 * (0.001 / 0.12) ** 0.66)
    assert bass["filterEnvelope"]["octaves"] == round3(1.5 + 0.66 * (3.5 - 1.5))
    # An unmapped base subfield of a mapped object survives untouched.
    assert bass["filterEnvelope"]["decay"] == 0.7
    assert bass["oscillator"]["type"] == "square8"


def test_drum_evaluation_bakes_mapped_voice_params() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    # snare carries the default brightness mapping (noise.playbackRate, linear).
    snare = sd.track_sounds["snare"].instrument.options
    assert snare["noise"]["playbackRate"] == round3(2.0 + 0.835 * (4.0 - 2.0))
    assert snare["noise"]["type"] == "pink"
    # kick has no mappings at all — base passes through verbatim.
    kick = sd.track_sounds["kick"].instrument.options
    assert kick["pitchDecay"] == 0.05
    assert "resonance" not in kick


def test_drum_voice_carries_kit_midi_pitched_role_none() -> None:
    """§7/D13 — each drum voice's `TrackSound.midi` is its kit trigger pitch (the
    Serializer stamps it onto the voice's notes); a NoiseSynth voice and every
    pitched role carry `None`."""
    plan = _pop_plan()
    ts = sound_design(plan, _timbres("pop_rock"), _RNG).track_sounds
    assert ts["kick"].midi == 24
    assert ts["hats"].midi == 80
    assert ts["ride"].midi == 82
    assert ts["snare"].midi is None  # NoiseSynth (V5)
    for role in ("bass", "comping", "pads"):
        assert ts[role].midi is None


def test_all_nine_kit_voices_emitted() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    for voice in KIT_VOICE_IDS:
        assert voice in sd.track_sounds
    # Plus the three pitched roles.
    for role in ("bass", "comping", "pads"):
        assert role in sd.track_sounds


# --- PolySynth emission ------------------------------------------------------


def test_polysynth_emits_voice_and_polyphony() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    comping = sd.track_sounds["comping"].instrument
    assert comping.type == "PolySynth"
    assert comping.voice == "MonoSynth"
    assert comping.max_polyphony == 12
    assert comping.options  # the evaluated voice options


def test_non_polysynth_omits_voice_and_polyphony() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    bass = sd.track_sounds["bass"].instrument
    assert bass.type == "MonoSynth"
    assert bass.voice is None
    assert bass.max_polyphony is None
    # Drum kit voices are plain {type, options} too.
    kick = sd.track_sounds["kick"].instrument
    assert kick.type == "MembraneSynth"
    assert kick.voice is None


# --- reverb-send present vs absent -------------------------------------------


def test_send_present_when_mix_carries_reverb() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    # comping inherits the space→mix.sends.reverb default (send evaluated).
    comping_sends = sd.track_sounds["comping"].sends
    assert len(comping_sends) == 1
    assert comping_sends[0].bus == "reverb"
    assert comping_sends[0].gain_db == round3(-24 + 0.36 * (-9 - -24))
    # hats carry a FIXED base send (no mapping) — it survives verbatim.
    hats_sends = sd.track_sounds["hats"].sends
    assert len(hats_sends) == 1
    assert hats_sends[0].gain_db == -20


def test_send_absent_when_dry() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    # bass: space defaults are empty (dry) and no fixed send → no send.
    assert sd.track_sounds["bass"].sends == []
    # kick: no fixed send, no mapping → dry.
    assert sd.track_sounds["kick"].sends == []


# --- bus evaluation by space (§6.2) ------------------------------------------


def test_bus_endpoints_and_midpoint() -> None:
    plan = _pop_plan()
    timbres = _timbres("pop_rock")
    lo, hi = 0.8, 3.0  # pop_rock decay range
    p_lo, p_hi = 0.01, 0.03

    def _bus(space: float) -> tuple[float, float, float]:
        sd = sound_design(_with_directives(plan, 0.5, 0.5, space), timbres, _RNG)
        reverb = sd.buses[0].effects[0].options
        hpf = sd.buses[0].effects[1].options
        return reverb["decay"], reverb["preDelay"], hpf["frequency"]

    # space = 0 → decay = lo, preDelay = p_lo.
    decay0, pre0, hz0 = _bus(0.0)
    assert decay0 == round3(lo) == 0.8
    assert pre0 == round3(p_lo) == 0.01
    assert hz0 == 350
    # space = 1 → decay = hi, preDelay = p_hi.
    decay1, pre1, _ = _bus(1.0)
    assert decay1 == round3(hi) == 3.0
    assert pre1 == round3(p_hi) == 0.03
    # space = 0.5 → the exp/linear midpoints.
    decay_mid, pre_mid, _ = _bus(0.5)
    assert decay_mid == round3(lo * (hi / lo) ** 0.5)
    assert pre_mid == round3(p_lo + 0.5 * (p_hi - p_lo))


def test_bus_always_carries_reverb_then_highpass() -> None:
    plan = _pop_plan()
    sd = sound_design(plan, _timbres("pop_rock"), _RNG)
    assert len(sd.buses) == 1
    bus = sd.buses[0]
    assert bus.id == "reverb"
    assert bus.effects[0].type == "Reverb"
    assert bus.effects[0].options["wet"] == 1.0
    assert bus.effects[1].type == "Filter"
    assert bus.effects[1].options["type"] == "highpass"
    assert bus.effects[1].options["Q"] == 0.5


# --- master verbatim ---------------------------------------------------------


def test_master_is_pack_chain_verbatim() -> None:
    timbres = _timbres("pop_rock")
    sd = sound_design(_pop_plan(), timbres, _RNG)
    assert sd.master.effects == list(timbres.master)
    assert sd.master.effects[-1].type == "Limiter"


# --- determinism -------------------------------------------------------------


def test_repeated_run_identity() -> None:
    plan = _pop_plan()
    timbres = _timbres("pop_rock")
    first = sound_design(plan, timbres, _RNG)
    second = sound_design(plan, timbres, _RNG)
    assert isinstance(first, SoundDesign)
    assert first == second


def test_repeated_run_identity_jazz() -> None:
    plan = generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )
    timbres = _timbres("jazz")
    assert sound_design(plan, timbres, _RNG) == sound_design(plan, timbres, _RNG)
