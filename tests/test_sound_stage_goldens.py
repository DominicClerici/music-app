"""§9.1 / §9.2 worked-example goldens for the sound-design stage (PHASE_7 §9;
SESSION_14 T1, DoD 4).

Each example is asserted **field-for-field**: every evaluated patch's FULL options
object (not only the mapped params), every channel `{volumeDb, pan}`, every send
`gainDb`, the reverb bus (`decay`/`preDelay`/`returnFilterHz`), and the master
chain. Expected values are recomputed here from the §9 mapping ranges + the plan's
directive scalars with `round3` — never pasted from the §9 printed digits (those
display at 1 decimal). The full-options expectations start from the authored
`base`/patch options (read from the loaded fixture) with the mapped paths overwritten,
so the golden also proves the stage preserves every unmapped base field and adds no
stray key.

GOLDEN-VALUE ARBITRATION (ROADMAP §3, resolved — see CAVEAT C-13): §9.2's printed
jazz `upright` `envelope.attack` "0.05×0.04^0.333 ≈ 0.0171" used the *brightness*
scalar 0.333 as the exponent, but the param maps `attackHardness` (=0.32 for this
plan), giving the faithful round3 = **0.018**. User signed off (2026-07-18) that the
printed sample is the derived-sample error; §9.2 amended to `0.05×0.04^0.32 ≈ 0.018`,
engine unchanged. The main golden below asserts the faithful 0.018.
"""

import copy
from pathlib import Path
from typing import Any

import yaml

from trackgen.interpreter.stage import generate_plan
from trackgen.schema.ir import GenerationPlan
from trackgen.seeds import Rng
from trackgen.sound.evaluate import round3
from trackgen.sound.stage import sound_design
from trackgen.sound.timbres import TimbresConfig

_STYLES = Path(__file__).resolve().parents[1] / "styles"

# The reserved `sound` seed stream: `sound_design` never draws (D3), so any Rng
# gives identical output.
_RNG = Rng(0)


def _timbres(pack: str) -> TimbresConfig:
    raw: Any = yaml.safe_load((_STYLES / pack / "timbres.yaml").read_text())
    return TimbresConfig.model_validate(raw)


def _exp(mn: float, mx: float, d: float) -> float:
    """Independent reimplementation of the §3.1 exp map (log-perceptual)."""
    return round3(mn * (mx / mn) ** d)


def _lin(mn: float, mx: float, d: float) -> float:
    """Independent reimplementation of the §3.1 linear map."""
    return round3(mn + d * (mx - mn))


def _set(root: dict[str, Any], path: str, value: Any) -> None:
    node = root
    segments = path.split(".")
    for seg in segments[:-1]:
        node = node[seg]
    node[segments[-1]] = value


def _opts(base: dict[str, Any], mapped: dict[str, Any]) -> dict[str, Any]:
    """The expected evaluated options: the authored base with the mapped paths
    overwritten by their recomputed values."""
    out = copy.deepcopy(dict(base))
    for path, value in mapped.items():
        _set(out, path, value)
    return out


def _pop_plan() -> GenerationPlan:
    return generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})


def _jazz_plan() -> GenerationPlan:
    return generate_plan(
        {
            "styleFamily": "jazz",
            "mood": "melancholic",
            "maxLengthSec": 240,
            "seed": "1ps9wxb",
        }
    )


def _chan(track: Any) -> tuple[float, float, bool]:
    return track.channel.volume_db, track.channel.pan, track.channel.mute


# --- §9.1 pop_rock / happy ---------------------------------------------------


def test_pop_9_1_field_for_field() -> None:
    plan = _pop_plan()
    assert plan.timbre_directives.brightness == 0.835
    assert plan.timbre_directives.attack_hardness == 0.66
    assert plan.timbre_directives.space == 0.36
    b, a, s = 0.835, 0.66, 0.36

    t = _timbres("pop_rock")
    ts = sound_design(plan, t, _RNG).track_sounds

    kit = t.flavors.drums["acoustic_kit"].kit
    assert ts["kick"].instrument.options == _opts(kit["kick"].patch.options, {})
    assert ts["snare"].instrument.options == _opts(
        kit["snare"].patch.options, {"noise.playbackRate": _lin(2.0, 4.0, b)}
    )
    assert ts["hats"].instrument.options == _opts(
        kit["hats"].patch.options, {"resonance": _exp(2000, 5500, b)}
    )
    assert ts["ride"].instrument.options == _opts(
        kit["ride"].patch.options, {"resonance": _exp(3500, 7000, b)}
    )
    assert ts["crash"].instrument.options == _opts(
        kit["crash"].patch.options, {"resonance": _exp(2500, 5000, b)}
    )
    for voice in ("tom_low", "tom_mid", "tom_high", "perc"):
        assert ts[voice].instrument.options == _opts(kit[voice].patch.options, {})

    bass = t.flavors.bass["electric_fingered"].base
    assert ts["bass"].instrument.options == _opts(
        bass,
        {
            "filterEnvelope.baseFrequency": _exp(120, 2500, b),
            "filter.Q": _lin(0.8, 2.0, b),
            "envelope.attack": _exp(0.12, 0.001, a),
            "filterEnvelope.octaves": _lin(1.5, 3.5, a),
        },
    )
    comping = t.flavors.comping["clean_electric"].base
    assert ts["comping"].instrument.options == _opts(
        comping,
        {
            "filterEnvelope.baseFrequency": _exp(400, 8000, b),
            "envelope.attack": _exp(0.08, 0.001, a),
        },
    )
    pads = t.flavors.pads["warm_analog"].base
    assert ts["pads"].instrument.options == _opts(
        pads,
        {
            "filterEnvelope.baseFrequency": _exp(350, 9000, b),
            "envelope.attack": _exp(1.2, 0.005, a),
        },
    )

    # PolySynth emission.
    assert (
        ts["comping"].instrument.type,
        ts["comping"].instrument.voice,
        ts["comping"].instrument.max_polyphony,
    ) == ("PolySynth", "MonoSynth", 12)
    assert (
        ts["pads"].instrument.type,
        ts["pads"].instrument.voice,
        ts["pads"].instrument.max_polyphony,
    ) == ("PolySynth", "MonoSynth", 8)

    # Channels (§6.3 pop_rock).
    channels = {
        "kick": (-9, 0),
        "snare": (-10.5, 0),
        "hats": (-17, 0.3),
        "ride": (-19, -0.2),
        "crash": (-14, -0.35),
        "tom_low": (-13, -0.3),
        "tom_mid": (-13, -0.1),
        "tom_high": (-13, 0.15),
        "perc": (-16, 0.2),
        "bass": (-11, 0),
        "comping": (-13, -0.3),
        "pads": (-18, 0),
    }
    for tid, (vol, pan) in channels.items():
        assert _chan(ts[tid]) == (vol, pan, False)

    # Sends.
    assert ts["snare"].sends[0].gain_db == _lin(-18, -6, s)
    assert ts["hats"].sends[0].gain_db == -20
    assert ts["ride"].sends[0].gain_db == -18
    assert ts["crash"].sends[0].gain_db == _lin(-14, -8, s)
    for voice in ("tom_low", "tom_mid", "tom_high"):
        assert ts[voice].sends[0].gain_db == _lin(-16, -8, s)
    assert ts["comping"].sends[0].gain_db == _lin(-24, -9, s)
    assert ts["pads"].sends[0].gain_db == _lin(-18, -6, s)
    for dry in ("kick", "bass", "perc"):
        assert ts[dry].sends == []

    # Bus + master.
    sd = sound_design(plan, t, _RNG)
    assert sd.buses[0].effects[0].options == {
        "decay": _exp(0.8, 3.0, s),
        "preDelay": _lin(0.01, 0.03, s),
        "wet": 1.0,
    }
    assert sd.buses[0].effects[1].options == {
        "type": "highpass",
        "frequency": 350,
        "Q": 0.5,
    }
    assert [(e.type, e.options) for e in sd.master.effects] == [
        ("Compressor", {"threshold": -20, "ratio": 2, "attack": 0.03, "release": 0.25}),
        ("Limiter", {"threshold": -1}),
    ]

    # §9.1 well-known anchors.
    assert ts["snare"].instrument.options["noise"]["playbackRate"] == 3.67
    assert ts["bass"].instrument.options["filterEnvelope"]["baseFrequency"] == 1514.763
    assert ts["bass"].instrument.options["filter"]["Q"] == 1.802
    # §9.1 prints "0.0051" — a >3-decimal display of round3 = 0.005, not a divergence.
    assert ts["bass"].instrument.options["envelope"]["attack"] == 0.005
    assert ts["bass"].instrument.options["filterEnvelope"]["octaves"] == 2.82
    assert (
        ts["comping"].instrument.options["filterEnvelope"]["baseFrequency"] == 4880.002
    )
    assert sd.buses[0].effects[0].options["decay"] == 1.287


# --- §9.2 jazz / melancholic -------------------------------------------------


def test_jazz_9_2_field_for_field() -> None:
    plan = _jazz_plan()
    assert plan.timbre_directives.brightness == 0.333
    assert plan.timbre_directives.attack_hardness == 0.32
    assert plan.timbre_directives.space == 0.657
    b, a, s = 0.333, 0.32, 0.657

    t = _timbres("jazz")
    ts = sound_design(plan, t, _RNG).track_sounds

    kit = t.flavors.drums["brush_kit"].kit
    assert ts["kick"].instrument.options == _opts(kit["kick"].patch.options, {})
    assert ts["snare"].instrument.options == _opts(
        kit["snare"].patch.options, {"noise.playbackRate": _lin(0.4, 0.9, b)}
    )
    assert ts["hats"].instrument.options == _opts(
        kit["hats"].patch.options, {"resonance": _exp(2000, 5500, b)}
    )
    assert ts["ride"].instrument.options == _opts(
        kit["ride"].patch.options, {"resonance": _exp(3500, 7000, b)}
    )
    assert ts["crash"].instrument.options == _opts(
        kit["crash"].patch.options, {"resonance": _exp(2500, 5000, b)}
    )
    for voice in ("tom_low", "tom_mid", "tom_high", "perc"):
        assert ts[voice].instrument.options == _opts(kit[voice].patch.options, {})

    # bass upright (FM): faithful attack uses attackHardness=0.32 → 0.018 (C-13).
    bass = t.flavors.bass["upright"].base
    assert ts["bass"].instrument.options == _opts(
        bass,
        {
            "modulationIndex": _exp(1.5, 6, b),
            "envelope.attack": _exp(0.05, 0.002, a),
        },
    )
    comping = t.flavors.comping["piano"].base
    assert ts["comping"].instrument.options == _opts(
        comping,
        {
            "modulationIndex": _exp(4, 14, b),
            "envelope.attack": _exp(0.08, 0.001, a),
        },
    )
    # pads (airy_strings) — emitted even though §9.2 has no pads track to fill.
    pads = t.flavors.pads["airy_strings"].base
    assert ts["pads"].instrument.options == _opts(
        pads,
        {
            "filterEnvelope.baseFrequency": _exp(350, 9000, b),
            "envelope.attack": _exp(1.2, 0.005, a),
        },
    )

    # PolySynth emission (jazz piano is FM-voiced).
    assert (
        ts["comping"].instrument.type,
        ts["comping"].instrument.voice,
        ts["comping"].instrument.max_polyphony,
    ) == ("PolySynth", "FMSynth", 12)

    # Channels (§6.3 jazz).
    channels = {
        "kick": (-12, 0),
        "snare": (-12, 0),
        "hats": (-16, 0.25),
        "ride": (-13, -0.2),
        "crash": (-15, -0.3),
        "tom_low": (-14, -0.25),
        "tom_mid": (-14, -0.05),
        "tom_high": (-14, 0.15),
        "perc": (-18, 0.2),
        "bass": (-10, 0),
        "comping": (-12, -0.25),
        "pads": (-20, 0),
    }
    for tid, (vol, pan) in channels.items():
        assert _chan(ts[tid]) == (vol, pan, False)

    # Sends — jazz kick/hats/ride carry fixed room sends; snare/crash/toms mapped.
    assert ts["kick"].sends[0].gain_db == -18
    assert ts["hats"].sends[0].gain_db == -15
    assert ts["ride"].sends[0].gain_db == -12
    assert ts["snare"].sends[0].gain_db == _lin(-18, -6, s)
    assert ts["crash"].sends[0].gain_db == _lin(-14, -8, s)
    for voice in ("tom_low", "tom_mid", "tom_high"):
        assert ts[voice].sends[0].gain_db == _lin(-16, -8, s)
    assert ts["comping"].sends[0].gain_db == _lin(-24, -9, s)
    assert ts["pads"].sends[0].gain_db == _lin(-18, -6, s)
    for dry in ("bass", "perc"):
        assert ts[dry].sends == []

    # Bus + master.
    sd = sound_design(plan, t, _RNG)
    assert sd.buses[0].effects[0].options == {
        "decay": _exp(0.7, 2.2, s),
        "preDelay": _lin(0.01, 0.03, s),
        "wet": 1.0,
    }
    assert sd.buses[0].effects[1].options == {
        "type": "highpass",
        "frequency": 400,
        "Q": 0.5,
    }
    assert [(e.type, e.options) for e in sd.master.effects] == [
        (
            "Compressor",
            {"threshold": -18, "ratio": 1.5, "attack": 0.03, "release": 0.4},
        ),
        ("Limiter", {"threshold": -1}),
    ]

    # §9.2 well-known anchors.
    assert ts["snare"].instrument.options["noise"]["playbackRate"] == 0.567
    assert ts["bass"].instrument.options["modulationIndex"] == 2.38
    # Faithful attack uses attackHardness=0.32 → 0.018 (§9.2 amended from the
    # printed 0.0171, which mis-used brightness 0.333 as the exponent — C-13).
    assert ts["bass"].instrument.options["envelope"]["attack"] == 0.018
    assert sd.buses[0].effects[0].options["decay"] == 1.485
