"""The sound-design stage — pipeline stage 8 (PHASE_7 §7).

``sound_design(plan, timbres) → SoundDesign``: a pure lookup+evaluate (D3, D6).
For each role it selects the plan's flavor, merges the engine mod defaults with
the flavor's overrides (§3.2), bakes the three directives into concrete Tone.js
options (§3.4), and assembles per-track instrument/effects/channel/sends plus the
shared reverb bus (§6.2) and the pack master chain. Zero RNG and no wall-clock
(ROADMAP inv. 5): every value is a deterministic function of ``(plan, timbres)``.

Unwired here: the T2 Serializer consumes ``SoundDesign`` and selects the tracks
that have phrases (it omits the reverb bus when nothing sends to it, §7). This
stage always emits the full role map and the bus — that selection is not its
concern.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from trackgen.schema.document import (
    Bus,
    Channel,
    EffectPatch,
    InstrumentPatch,
    Master,
    Send,
)
from trackgen.schema.ir import GenerationPlan
from trackgen.sound._merge import (
    drum_defaults,
    drum_override,
    pitched_defaults,
    pitched_override,
)
from trackgen.sound.evaluate import apply_directives, merge_mod, round3
from trackgen.sound.mod_defaults import PitchedModDefaults, load_mod_defaults
from trackgen.sound.models import MappingEntry
from trackgen.sound.timbres import (
    KIT_VOICE_IDS,
    KitFlavor,
    MixBlock,
    PitchedFlavor,
    TimbresConfig,
)


class _SoundModel(BaseModel):
    """Shared base: frozen, camelCase JSON aliases, alias-or-name construction —
    the ``schema/document.py`` convention (the stage output feeds the document)."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TrackSound(_SoundModel):
    """§7 one track's baked sound: the evaluated instrument patch, its identity
    inserts, the channel strip, and its bus sends."""

    instrument: InstrumentPatch
    effects: list[EffectPatch] = Field(default_factory=list)
    channel: Channel
    sends: list[Send] = Field(default_factory=list)


class SoundDesign(_SoundModel):
    """§7 the stage output: per-track sounds keyed by track id (role name for
    pitched roles, voice id for drum voices), the shared buses, and the master
    chain."""

    track_sounds: dict[str, TrackSound]
    buses: list[Bus] = Field(default_factory=list)
    master: Master


def _evaluate_track(
    base_options: dict[str, Any],
    mix: MixBlock,
    mod: Mapping[str, Sequence[MappingEntry]],
    directive_values: Mapping[str, float],
) -> tuple[dict[str, Any], Channel, list[Send]]:
    """Bake one track (§3.4): evaluate ``base_options`` + the flavor mix block
    under the merged mappings, then split the two back out. The working dict
    puts the patch options at the top level and the mix block under a reserved
    ``mix`` key, so an options path and ``mix.sends.reverb`` are both plain
    dotted writes (§3.1); ``volumeDb``/``pan`` are never mapped, so they pass
    straight through from the mix block."""
    mix_block: dict[str, Any] = {"sends": dict(mix.sends)} if mix.sends else {}
    result = apply_directives({**base_options, "mix": mix_block}, mod, directive_values)
    evaluated_mix = result.pop("mix")
    channel = Channel(volume_db=mix.volume_db, pan=mix.pan, mute=False)
    reverb_gain = evaluated_mix.get("sends", {}).get("reverb")
    sends = [Send(bus="reverb", gain_db=reverb_gain)] if reverb_gain is not None else []
    return result, channel, sends


def _pitched_track(
    flavor: PitchedFlavor,
    role_defaults: dict[str, tuple[MappingEntry, ...]],
    directive_values: Mapping[str, float],
) -> TrackSound:
    """§7 step 3 — evaluate a pitched-role flavor into one ``TrackSound``. A
    PolySynth engine emits ``{type, voice, maxPolyphony, options}`` (V7); any
    other class emits ``{type, options}``."""
    mod = merge_mod(role_defaults, pitched_override(flavor.mod))
    options, channel, sends = _evaluate_track(
        dict(flavor.base), flavor.mix, mod, directive_values
    )
    engine = flavor.engine
    if engine.type == "PolySynth":
        instrument = InstrumentPatch(
            type=engine.type,
            voice=engine.voice,
            max_polyphony=engine.max_polyphony,
            options=options,
        )
    else:
        instrument = InstrumentPatch(type=engine.type, options=options)
    return TrackSound(
        instrument=instrument,
        effects=list(flavor.effects),
        channel=channel,
        sends=sends,
    )


def _drum_tracks(
    flavor: KitFlavor,
    drum_table: dict[tuple[str, str], tuple[MappingEntry, ...]],
    directive_values: Mapping[str, float],
) -> dict[str, TrackSound]:
    """§7 step 3 (drums) — one ``TrackSound`` per kit voice. The merged
    ``(directive, voice)`` table is sliced to each voice's directive-keyed
    mappings before evaluation; kit voices carry no inserts (identity FX are a
    pitched-flavor concern)."""
    merged = merge_mod(drum_table, drum_override(flavor.mod))
    out: dict[str, TrackSound] = {}
    for voice in KIT_VOICE_IDS:
        kit_voice = flavor.kit[voice]
        voice_mod = {
            directive: entries
            for (directive, mapped_voice), entries in merged.items()
            if mapped_voice == voice
        }
        options, channel, sends = _evaluate_track(
            dict(kit_voice.patch.options), kit_voice.mix, voice_mod, directive_values
        )
        instrument = InstrumentPatch(type=kit_voice.patch.type, options=options)
        out[voice] = TrackSound(
            instrument=instrument, effects=[], channel=channel, sends=sends
        )
    return out


def sound_design(plan: GenerationPlan, timbres: TimbresConfig) -> SoundDesign:
    """PHASE_7 §7 — bake ``(plan, timbres)`` into the ``SoundDesign``. Pure, zero
    draws (D3): the ``sound`` seed stream stays reserved."""
    d = plan.timbre_directives
    directive_values: dict[str, float] = {
        "brightness": d.brightness,
        "attackHardness": d.attack_hardness,
        "space": d.space,
    }

    defaults = load_mod_defaults()
    track_sounds: dict[str, TrackSound] = {}

    drums_flavor = timbres.flavors.drums[plan.role_flavors["drums"]]
    track_sounds.update(
        _drum_tracks(drums_flavor, drum_defaults(defaults), directive_values)
    )

    pitched_banks: tuple[
        tuple[str, dict[str, PitchedFlavor], PitchedModDefaults], ...
    ] = (
        ("bass", timbres.flavors.bass, defaults.bass),
        ("comping", timbres.flavors.comping, defaults.comping),
        ("pads", timbres.flavors.pads, defaults.pads),
    )
    for role, bank, role_md in pitched_banks:
        flavor = bank[plan.role_flavors[role]]
        track_sounds[role] = _pitched_track(
            flavor, pitched_defaults(role_md), directive_values
        )

    reverb = timbres.bus.reverb
    lo, hi = reverb.decay
    decay = round3(lo * (hi / lo) ** d.space)
    p_lo, p_hi = reverb.pre_delay
    pre_delay = round3(p_lo + d.space * (p_hi - p_lo))
    buses = [
        Bus(
            id="reverb",
            effects=[
                EffectPatch(
                    type="Reverb",
                    options={"decay": decay, "preDelay": pre_delay, "wet": 1.0},
                ),
                EffectPatch(
                    type="Filter",
                    options={
                        "type": "highpass",
                        "frequency": reverb.return_filter_hz,
                        "Q": 0.5,
                    },
                ),
            ],
        )
    ]

    master = Master(effects=list(timbres.master))
    return SoundDesign(track_sounds=track_sounds, buses=buses, master=master)
