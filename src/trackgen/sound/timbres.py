"""The real ``timbres.yaml`` schema + TB1–TB9 validators (PHASE_7 §4).

The last pack file, owned by this phase. Three top-level parts (§4.1):
``flavors`` (per-role recipe maps), ``bus`` (the single shared reverb bus), and
``master`` (the master effect chain). Frozen pydantic models mirroring
``packs/models.py::PackModel`` (frozen, camelCase alias, ``extra="forbid"`` —
TB9's strict schema); intra-file caps TB2/TB5/TB6/TB8 live on their own models,
the cross-cutting path/mod checks TB3/TB4/TB6(sends)/TB7 run in the
``TimbresConfig`` validator against ``sound/allowlist.py`` + ``sound/mod_defaults.py``,
and TB1 (cross-file flavor completeness, PHASE_2 D14) is the standalone
``check_flavor_completeness`` — a function in Chunk 1, wired into ``resolve_pack``
in Chunk 2.

Unwired in Chunk 1: this module is exercised only by ``tests/test_timbres_schema.py``;
``packs/models.py::TimbresConfig`` (the stub) stays live for the stub loader.

Patch reuse: kit-voice patches reuse the PHASE_1 ``schema/document.InstrumentPatch``
(``{type, options}``) — the §8 kit recipes are exactly that shape; pitched flavors
split their patch into an ``engine`` sub-model (for the PolySynth voice/polyphony
rules, TB2) plus a freeform ``base`` options dict (§4.2), so they do not reuse
``InstrumentPatch``.
"""

from collections.abc import Iterator, Mapping
from typing import Any

from pydantic import Field, model_validator

from trackgen.packs.models import PackModel
from trackgen.schema.document import (
    EffectPatch,
    InstrumentPatch,
    InstrumentType,
    PolySynthVoice,
)
from trackgen.sound.allowlist import Allowlist, load_allowlist
from trackgen.sound.evaluate import assert_base_xor_mod, merge_mod
from trackgen.sound.mod_defaults import (
    ModDefaults,
    PitchedModDefaults,
    load_mod_defaults,
)
from trackgen.sound.models import MappingEntry

# The nine voice-track ids a kit must define (PHASE_7 §4.3 / D13; PHASE_5 §8.2).
# `hat_closed`/`hat_open` share the `hats` patch, so the track-id set is nine.
KIT_VOICE_IDS: tuple[str, ...] = (
    "kick",
    "snare",
    "hats",
    "ride",
    "crash",
    "tom_low",
    "tom_mid",
    "tom_high",
    "perc",
)

_PITCHED_ROLES: tuple[str, ...] = ("bass", "comping", "pads")
_ALL_ROLES: tuple[str, ...] = ("drums", *_PITCHED_ROLES)

# The one mix-block path a directive mapping may target instead of a patch
# option (§3.1): the reverb send. Exempt from the allowlist option-path check
# (TB7) because it addresses the mix block, not the patch `options` object.
_MIX_SEND_PARAM = "mix.sends.reverb"


# --- schema models ----------------------------------------------------------


class MixBlock(PackModel):
    """§4.2 per-track mix: musical balance level, pan, and optional bus sends.

    `volume_db`/`pan` caps are TB6; the `sends`-key-references-a-declared-bus
    half of TB6 is cross-cutting (needs the `bus` declaration) so it runs in
    `TimbresConfig`."""

    volume_db: float = Field(le=6)
    pan: float = Field(ge=-1, le=1)
    sends: dict[str, float] | None = None


class EngineSpec(PackModel):
    """§4.2 `engine` — the instrument class plus PolySynth-only voice/polyphony.

    TB2: `type` in the PHASE_1 instrument whitelist (structural, `InstrumentType`);
    `voice`+`maxPolyphony` present iff `type == PolySynth`; `voice` in the
    Monophonic whitelist (structural, `PolySynthVoice`); `maxPolyphony ∈ [1, 32]`."""

    type: InstrumentType
    voice: PolySynthVoice | None = None
    max_polyphony: int | None = Field(default=None, ge=1, le=32)

    @model_validator(mode="after")
    def _check_polyphony(self) -> "EngineSpec":
        is_poly = self.type == "PolySynth"
        has_voice = self.voice is not None
        has_polyphony = self.max_polyphony is not None
        if is_poly and not (has_voice and has_polyphony):
            raise ValueError(
                f"engine {self.type!r}: PolySynth requires both 'voice' and "
                f"'maxPolyphony' (1-32) (TB2)"
            )
        if not is_poly and (has_voice or has_polyphony):
            raise ValueError(
                f"engine {self.type!r}: only PolySynth may declare 'voice'/"
                f"'maxPolyphony' (TB2)"
            )
        return self


class KitVoice(PackModel):
    """§4.3 one kit voice: an `InstrumentPatch` + trigger `midi` + `mix`.

    TB5 (per voice): `midi` present iff the patch class ≠ NoiseSynth (unpitched
    voices carry none); `midi ∈ [0, 127]` (the field cap)."""

    midi: int | None = Field(default=None, ge=0, le=127)
    patch: InstrumentPatch
    mix: MixBlock

    @model_validator(mode="after")
    def _check_midi(self) -> "KitVoice":
        is_noise = self.patch.type == "NoiseSynth"
        if is_noise and self.midi is not None:
            raise ValueError(
                f"NoiseSynth kit voice is unpitched and must not declare 'midi', "
                f"got {self.midi} (TB5)"
            )
        if not is_noise and self.midi is None:
            raise ValueError(
                f"kit voice patch {self.patch.type!r} requires a trigger 'midi' (TB5)"
            )
        return self


class KitMod(PackModel):
    """§4.3 optional per-voice drum `mod` overrides, keyed directive → voice →
    list. Drums carry brightness + space ONLY — `attackHardness` is deliberately
    absent (D4: trigger envelopes *are* the kit's identity), so the closed field
    set (+ `extra="forbid"`) both rejects an authored `attackHardness` key and
    keeps directive keys ⊆ {brightness, attackHardness, space} (TB7)."""

    brightness: dict[str, tuple[MappingEntry, ...]] | None = None
    space: dict[str, tuple[MappingEntry, ...]] | None = None


class KitFlavor(PackModel):
    """§4.3 a drum-kit flavor: the nine voices + optional per-voice `mod`."""

    kit: dict[str, KitVoice]
    mod: KitMod | None = None

    @model_validator(mode="after")
    def _check_kit_ids(self) -> "KitFlavor":
        present = set(self.kit)
        expected = set(KIT_VOICE_IDS)
        if present != expected:
            missing = sorted(expected - present)
            unexpected = sorted(present - expected)
            raise ValueError(
                f"kit must define exactly the nine voice ids "
                f"{list(KIT_VOICE_IDS)}; missing={missing}, "
                f"unexpected={unexpected} (TB5)"
            )
        return self


class PitchedMod(PackModel):
    """§4.2 optional pitched-flavor `mod` overrides, per directive. The closed
    field set (+ `extra="forbid"`) enforces TB7's directive-keys constraint.

    `None` = directive absent (keep the role default); an empty list = disable
    (§3.2). The `attack_hardness` snake field aliases to `attackHardness`."""

    brightness: tuple[MappingEntry, ...] | None = None
    attack_hardness: tuple[MappingEntry, ...] | None = None
    space: tuple[MappingEntry, ...] | None = None


class PitchedFlavor(PackModel):
    """§4.2 a pitched-role flavor: engine + base options + inserts + mix + mod."""

    engine: EngineSpec
    base: dict[str, Any]
    effects: tuple[EffectPatch, ...] = ()
    mix: MixBlock
    mod: PitchedMod | None = None


class ReverbBus(PackModel):
    """§4.1 the shared reverb bus config: `space`-evaluated decay/preDelay ranges
    plus the return highpass. TB8: `0 < decay.lo ≤ decay.hi`; `0 ≤ preDelay.lo ≤
    preDelay.hi`; `returnFilterHz > 0`."""

    decay: tuple[float, float]
    pre_delay: tuple[float, float]
    return_filter_hz: float

    @model_validator(mode="after")
    def _check_ranges(self) -> "ReverbBus":
        d_lo, d_hi = self.decay
        if not (0 < d_lo <= d_hi):
            raise ValueError(
                f"bus.reverb.decay must satisfy 0 < lo <= hi, "
                f"got {list(self.decay)} (TB8)"
            )
        p_lo, p_hi = self.pre_delay
        if not (0 <= p_lo <= p_hi):
            raise ValueError(
                f"bus.reverb.preDelay must satisfy 0 <= lo <= hi, "
                f"got {list(self.pre_delay)} (TB8)"
            )
        if self.return_filter_hz <= 0:
            raise ValueError(
                f"bus.reverb.returnFilterHz must be > 0, "
                f"got {self.return_filter_hz} (TB8)"
            )
        return self


class BusConfig(PackModel):
    """§4.1 `bus` — the single shared reverb bus (D2). `reverb` is the only v1
    bus, so the declared-bus set TB6 checks sends against is exactly its
    fields."""

    reverb: ReverbBus


class FlavorsConfig(PackModel):
    """§4.1 `flavors` — per-role recipe maps (flavor id → recipe)."""

    drums: dict[str, KitFlavor]
    bass: dict[str, PitchedFlavor]
    comping: dict[str, PitchedFlavor]
    pads: dict[str, PitchedFlavor]


# §4.1 `master` — an EffectPatch chain copied verbatim into the document; TB4
# requires it to end with a `Limiter`.
MasterChain = tuple[EffectPatch, ...]


class TimbresConfig(PackModel):
    """§4.1 `timbres.yaml` — the real schema. Strict (TB9). The cross-cutting
    allowlist/mod checks (TB3/TB4/TB6-sends/TB7) run here against the engine
    data; the per-model caps (TB2/TB5/TB6/TB8) run on their own models. TB1
    (cross-file completeness) is the standalone `check_flavor_completeness`."""

    flavors: FlavorsConfig
    bus: BusConfig
    master: MasterChain

    @model_validator(mode="after")
    def _check(self) -> "TimbresConfig":
        allow = load_allowlist()
        defaults = load_mod_defaults()

        _check_master_chain(self.master, allow)

        role_defaults: dict[str, PitchedModDefaults] = {
            "bass": defaults.bass,
            "comping": defaults.comping,
            "pads": defaults.pads,
        }
        pitched_banks: list[tuple[str, dict[str, PitchedFlavor]]] = [
            ("bass", self.flavors.bass),
            ("comping", self.flavors.comping),
            ("pads", self.flavors.pads),
        ]
        for role, bank in pitched_banks:
            merged_defaults = _pitched_defaults(role_defaults[role])
            for flavor_id, flavor in bank.items():
                where = f"flavors.{role}.{flavor_id}"
                cls_name = _engine_class(flavor.engine)
                # TB3: every base option path legal for the engine class.
                _check_option_paths(
                    cls_name, flavor.base, allow, f"{where}.base", "TB3"
                )
                # TB4: every insert's option paths legal for its effect class.
                for index, effect in enumerate(flavor.effects):
                    _check_option_paths(
                        effect.type,
                        effect.options,
                        allow,
                        f"{where}.effects[{index}]",
                        "TB4",
                    )
                # TB7: effective (merged) mapping legality + base XOR mod.
                _check_pitched_mod(flavor, cls_name, allow, merged_defaults, where)

        drum_defaults = _drum_defaults(defaults)
        for flavor_id, kit_flavor in self.flavors.drums.items():
            where = f"flavors.drums.{flavor_id}"
            for voice, kit_voice in kit_flavor.kit.items():
                _check_option_paths(
                    kit_voice.patch.type,
                    kit_voice.patch.options,
                    allow,
                    f"{where}.kit.{voice}",
                    "TB3",
                )
            _check_drum_mod(kit_flavor, allow, drum_defaults, where)

        # TB6 (sends half): every send targets a declared bus.
        declared_buses = set(type(self.bus).model_fields)
        _check_sends(self, declared_buses)
        return self


# --- validation helpers -----------------------------------------------------


def _leaf_paths(options: Mapping[str, Any], prefix: str = "") -> Iterator[str]:
    """Enumerate the dotted leaf option paths of a nested options dict — a leaf
    is any value that is not itself a mapping (a list value, e.g.
    `oscillator.partials`, is a leaf whose path is the option path)."""
    for key, value in options.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            yield from _leaf_paths(value, f"{path}.")
        else:
            yield path


def _engine_class(engine: EngineSpec) -> str:
    """The synthesis class the base options + mod params are validated against:
    the PolySynth `voice` for a PolySynth engine, else the `type` itself. TB2
    guarantees a PolySynth carries a `voice`, so the fallback is unreachable for
    a PolySynth."""
    if engine.type == "PolySynth" and engine.voice is not None:
        return engine.voice
    return engine.type


def _check_option_paths(
    cls_name: str,
    options: Mapping[str, Any],
    allow: Allowlist,
    where: str,
    code: str,
) -> None:
    for path in _leaf_paths(options):
        if not allow.is_legal(cls_name, path):
            raise ValueError(
                f"{where}: option path {path!r} is not in the allowlist for "
                f"class {cls_name!r} ({code})"
            )


def _check_send_xor(maps_send: bool, mix: MixBlock, where: str) -> None:
    """§4.2/§3.3: base XOR mod for the reverb send. `assert_base_xor_mod` only
    inspects patch options, but the send's base authority lives in the mix block
    (`mix.sends.reverb`), so a fixed base send AND a space mapping targeting the
    send are two authorities for one value — reject both."""
    if maps_send and mix.sends is not None and "reverb" in mix.sends:
        raise ValueError(
            f"{where}: mix carries a fixed 'reverb' send while a space mapping "
            f"also targets mix.sends.reverb — base XOR mod requires the fixed "
            f"send be omitted when a mapping targets it (§4.2, TB7)"
        )


def _check_master_chain(master: MasterChain, allow: Allowlist) -> None:
    if not master:
        raise ValueError("master chain must be non-empty and end with a Limiter (TB4)")
    if master[-1].type != "Limiter":
        raise ValueError(
            f"master chain must end with a Limiter, got {master[-1].type!r} (TB4)"
        )
    for index, effect in enumerate(master):
        _check_option_paths(
            effect.type, effect.options, allow, f"master[{index}]", "TB4"
        )


def _pitched_defaults(
    role_md: PitchedModDefaults,
) -> dict[str, tuple[MappingEntry, ...]]:
    """The role's default mapping table in the directive-keyed shape `merge_mod`
    consumes (normalising the `attack_hardness` field name to `attackHardness`)."""
    return {
        "brightness": role_md.brightness,
        "attackHardness": role_md.attack_hardness,
        "space": role_md.space,
    }


def _pitched_override(
    mod: PitchedMod | None,
) -> dict[str, tuple[MappingEntry, ...]] | None:
    """The flavor's `mod` in `merge_mod` override shape: a directive appears iff
    the flavor authored it (`None` = absent = keep default; `[]` = disable)."""
    if mod is None:
        return None
    override: dict[str, tuple[MappingEntry, ...]] = {}
    if mod.brightness is not None:
        override["brightness"] = mod.brightness
    if mod.attack_hardness is not None:
        override["attackHardness"] = mod.attack_hardness
    if mod.space is not None:
        override["space"] = mod.space
    return override or None


def _check_pitched_mod(
    flavor: PitchedFlavor,
    cls_name: str,
    allow: Allowlist,
    defaults: dict[str, tuple[MappingEntry, ...]],
    where: str,
) -> None:
    """TB7 for a pitched flavor: every EFFECTIVE (defaults-merged-with-override)
    mapping param is legal for the engine class (or the mix send), and base XOR
    mod holds per path. Merging the defaults in is load-bearing: a flavor that
    overrides nothing still inherits the role defaults, whose params must be
    legal for its engine class — so an off-class engine (e.g. FM) that does not
    override a filter-cutoff default would be caught here (§3.2)."""
    merged = merge_mod(defaults, _pitched_override(flavor.mod))
    mapped_option_paths: set[str] = set()
    maps_send = False
    for entries in merged.values():
        for entry in entries:
            if entry.param == _MIX_SEND_PARAM:
                maps_send = True
                continue
            if not allow.is_legal(cls_name, entry.param):
                raise ValueError(
                    f"{where}: mod param {entry.param!r} is not legal for engine "
                    f"class {cls_name!r} (TB7)"
                )
            mapped_option_paths.add(entry.param)
    assert_base_xor_mod(set(_leaf_paths(flavor.base)), mapped_option_paths)
    # §4.2: the base `mix.sends.reverb` is omitted when a `space` mapping targets
    # it — a fixed send AND a send mapping are two authorities for one value, so
    # base XOR mod (§3.3) forbids both (the send authority lives in the mix
    # block, not `base`, so it needs this dedicated check).
    _check_send_xor(maps_send, flavor.mix, where)


def _drum_defaults(
    defaults: ModDefaults,
) -> dict[tuple[str, str], tuple[MappingEntry, ...]]:
    """The drum default table keyed by `(directive, voice)` — the shape
    `merge_mod` uses for drums (§3.2). Drums carry brightness + space only (D4)."""
    drums = defaults.drums
    out: dict[tuple[str, str], tuple[MappingEntry, ...]] = {}
    for voice, entries in drums.brightness.items():
        out[("brightness", voice)] = entries
    for voice, entries in drums.space.items():
        out[("space", voice)] = entries
    return out


def _drum_override(
    mod: KitMod | None,
) -> dict[tuple[str, str], tuple[MappingEntry, ...]] | None:
    if mod is None:
        return None
    out: dict[tuple[str, str], tuple[MappingEntry, ...]] = {}
    # Drums carry brightness + space only — attackHardness is barred (D4).
    for directive, table in (
        ("brightness", mod.brightness),
        ("space", mod.space),
    ):
        if table is None:
            continue
        for voice, entries in table.items():
            out[(directive, voice)] = entries
    return out or None


def _check_drum_mod(
    flavor: KitFlavor,
    allow: Allowlist,
    defaults: dict[tuple[str, str], tuple[MappingEntry, ...]],
    where: str,
) -> None:
    """TB7 for a kit flavor: per `(directive, voice)`, every effective mapping
    param is legal for THAT voice's patch class (or the mix send), and base XOR
    mod holds per voice."""
    merged = merge_mod(defaults, _drum_override(flavor.mod))
    mapped_by_voice: dict[str, set[str]] = {}
    send_mapped_voices: set[str] = set()
    for (directive, voice), entries in merged.items():
        kit_voice = flavor.kit.get(voice)
        if kit_voice is None:
            raise ValueError(
                f"{where}: mod references unknown kit voice {voice!r} "
                f"(directive {directive!r}) (TB7)"
            )
        cls_name = kit_voice.patch.type
        for entry in entries:
            if entry.param == _MIX_SEND_PARAM:
                send_mapped_voices.add(voice)
                continue
            if not allow.is_legal(cls_name, entry.param):
                raise ValueError(
                    f"{where}: mod param {entry.param!r} is not legal for kit "
                    f"voice {voice!r} class {cls_name!r} (TB7)"
                )
            mapped_by_voice.setdefault(voice, set()).add(entry.param)
    for voice, kit_voice in flavor.kit.items():
        assert_base_xor_mod(
            set(_leaf_paths(kit_voice.patch.options)),
            mapped_by_voice.get(voice, set()),
        )
        # §4.2 (see _check_pitched_mod): a fixed send in the voice mix and a space
        # mapping onto the send are two authorities for one value — forbid both.
        _check_send_xor(
            voice in send_mapped_voices, kit_voice.mix, f"{where}.kit.{voice}"
        )


def _check_sends(config: "TimbresConfig", declared_buses: set[str]) -> None:
    def check_mix(mix: MixBlock, where: str) -> None:
        if mix.sends is None:
            return
        for bus_id in mix.sends:
            if bus_id not in declared_buses:
                raise ValueError(
                    f"{where}: send targets undeclared bus {bus_id!r}; declared "
                    f"buses are {sorted(declared_buses)} (TB6)"
                )

    for role, bank in (
        ("bass", config.flavors.bass),
        ("comping", config.flavors.comping),
        ("pads", config.flavors.pads),
    ):
        for flavor_id, flavor in bank.items():
            check_mix(flavor.mix, f"flavors.{role}.{flavor_id}.mix")
    for flavor_id, kit_flavor in config.flavors.drums.items():
        for voice, kit_voice in kit_flavor.kit.items():
            check_mix(kit_voice.mix, f"flavors.drums.{flavor_id}.kit.{voice}.mix")


# --- TB1 (cross-file, standalone in Chunk 1) --------------------------------


def check_flavor_completeness(
    timbres: TimbresConfig, declared: dict[str, set[str]]
) -> None:
    """TB1 (PHASE_7 §4.5; resolves PHASE_2 D14): per role, the `timbres` flavor-id
    set must EQUAL the `interpreter.yaml`-declared set — no dangling declarations
    (declared but no recipe) and no orphan recipes (recipe but undeclared).

    Standalone in Chunk 1 (exercised with fixtures); the live call from
    `resolve_pack` against the reference `interpreter.yaml` files is Chunk 2."""
    present_by_role: dict[str, set[str]] = {
        "drums": set(timbres.flavors.drums),
        "bass": set(timbres.flavors.bass),
        "comping": set(timbres.flavors.comping),
        "pads": set(timbres.flavors.pads),
    }
    for role in _ALL_ROLES:
        present = present_by_role[role]
        wanted = declared.get(role, set())
        if present != wanted:
            dangling = sorted(wanted - present)
            orphan = sorted(present - wanted)
            raise ValueError(
                f"role {role!r}: timbres flavor ids must equal the "
                f"interpreter-declared ids; dangling (declared, no recipe)="
                f"{dangling}, orphan (recipe, undeclared)={orphan} (TB1)"
            )
