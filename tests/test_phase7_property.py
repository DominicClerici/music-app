"""PHASE_7 §13.6 whole-stage property matrix (DoD 6).

Drives the sound-design stage across **both reference packs × every supported
mood × every declared flavor combination** and asserts the full §13.6 invariant
set on every produced `SoundDesign`:

- every `instrument.type` is in the PHASE_1 instrument whitelist; every insert /
  bus / master effect `type` is in the effect whitelist;
- every instrument/effect option path is allowlist-legal for its class (the
  PolySynth `voice` is the class its options are validated against, §5.2/§3.6);
- PolySynth carries `voice` + `maxPolyphony` and non-PolySynth carries neither
  (V7);
- every send targets the `reverb` bus (the only v1 bus, D2);
- `channel.volumeDb ≤ 6`, `channel.pan ∈ [−1, 1]`;
- the `reverb` bus `decay`/`preDelay` fall inside the pack's authored ranges
  (§6.2 — both are monotone maps of `space ∈ [0, 1]` onto `[lo, hi]`, so the
  round-3 bounds are the tight, correct envelope);
- `master.effects` is non-empty and ends in a `Limiter` (TB4).

The matrix is **fully exhausted** — the entire flavor cross-product and every
supported mood, no sampling or capping (ROADMAP §3 no-silent-caps). Dimensions:

  pop_rock : 11 moods × (2 drums · 2 bass · 3 comping · 2 pads = 24 combos) = 264
  jazz     : 10 moods × (2 drums · 1 bass · 2 comping · 2 pads =  8 combos) =  80
  total    : 344 documents

Per (pack, mood) the plan is built once via the real `generate_plan` (so the
mood's brightness/attackHardness/space directives are the genuine interpreter
output) and the flavor combo is varied with `model_copy` — `GenerationPlan` is
frozen. Mood drives the directive-baked options and the space-mapped bus decay;
the flavor combo drives every per-role patch. `test_matrix_non_vacuous` asserts
the matrix is both the exact expected size and non-degenerate (≥2 distinct
instrument classes, ≥1 PolySynth, ≥1 send), so the invariant asserts above are
not vacuously passing on an empty or single-class set.
"""

from __future__ import annotations

import itertools
from typing import get_args

import pytest

from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.schema.document import (
    EffectPatch,
    EffectType,
    InstrumentPatch,
    InstrumentType,
)
from trackgen.schema.ir import GenerationPlan
from trackgen.seeds import Rng
from trackgen.sound._merge import leaf_paths
from trackgen.sound.allowlist import load_allowlist
from trackgen.sound.evaluate import round3
from trackgen.sound.stage import SoundDesign, sound_design
from trackgen.sound.timbres import TimbresConfig

_PACKS = ("pop_rock", "jazz")
# The four sound-design roles, in a fixed order for the cross-product (§7).
_ROLES = ("drums", "bass", "comping", "pads")
_SEED = "1ps9wxb"  # any fixed seed: the plan's seed never touches sound-design.

_INSTRUMENT_TYPES = frozenset(get_args(InstrumentType))
_EFFECT_TYPES = frozenset(get_args(EffectType))
_ALLOW = load_allowlist()


def _pack_ctx(pack: str) -> tuple[TimbresConfig, dict[str, list[str]]]:
    """The pack's real `timbres` config plus its interpreter-declared flavor-id
    lists per role (TB1 pins these equal to the timbres flavor sets)."""
    resolved = resolve_pack(pack)
    assert resolved is not None
    assert resolved.timbres is not None and resolved.interpreter is not None
    flavors = {str(role): ids for role, ids in resolved.interpreter.flavors.items()}
    return resolved.timbres, flavors


def _combos(flavors: dict[str, list[str]]) -> list[dict[str, str]]:
    """The full role-flavor cross-product for one pack (nothing sampled)."""
    return [
        dict(zip(_ROLES, values, strict=True))
        for values in itertools.product(*(flavors[role] for role in _ROLES))
    ]


def _build_matrix() -> list[tuple[str, str, dict[str, str]]]:
    out: list[tuple[str, str, dict[str, str]]] = []
    for pack in _PACKS:
        _, flavors = _pack_ctx(pack)
        combos = _combos(flavors)
        interp = resolve_pack(pack).interpreter  # type: ignore[union-attr]
        assert interp is not None
        for mood in interp.supported_moods:
            for combo in combos:
                out.append((pack, mood, combo))
    return out


_MATRIX = _build_matrix()

# Per-(pack, mood) plan cache: `generate_plan` runs the whole interpreter, so
# build it once and vary only `role_flavors` across the 24/8 combos.
_PLAN_CACHE: dict[tuple[str, str], GenerationPlan] = {}


def _plan_for(pack: str, mood: str) -> GenerationPlan:
    key = (pack, mood)
    if key not in _PLAN_CACHE:
        _PLAN_CACHE[key] = generate_plan(
            {"styleFamily": pack, "mood": mood, "seed": _SEED}
        )
    return _PLAN_CACHE[key]


def _design_for(
    pack: str, mood: str, combo: dict[str, str]
) -> tuple[SoundDesign, TimbresConfig]:
    plan = _plan_for(pack, mood)
    varied = plan.model_copy(update={"role_flavors": {**plan.role_flavors, **combo}})
    timbres, _ = _pack_ctx(pack)
    return sound_design(varied, timbres, Rng(0)), timbres


def _engine_class(instrument: InstrumentPatch) -> str:
    """The class an instrument's option paths are validated against: a PolySynth's
    inner `voice`, else its own type (§5.2/§3.6)."""
    if instrument.type == "PolySynth":
        assert instrument.voice is not None
        return instrument.voice
    return instrument.type


def _assert_instrument(instrument: InstrumentPatch, where: str) -> None:
    assert instrument.type in _INSTRUMENT_TYPES, (where, instrument.type)
    cls = _engine_class(instrument)
    for path in leaf_paths(instrument.options):
        assert _ALLOW.is_legal(cls, path), (where, "instr-path", cls, path)
    # V7: PolySynth <=> voice + maxPolyphony; every other class carries neither.
    if instrument.type == "PolySynth":
        assert instrument.voice is not None and instrument.max_polyphony is not None, (
            where,
            "polysynth-missing-voice",
        )
    else:
        assert instrument.voice is None and instrument.max_polyphony is None, (
            where,
            "non-polysynth-has-voice",
        )


def _assert_effect(effect: EffectPatch, where: str) -> None:
    assert effect.type in _EFFECT_TYPES, (where, effect.type)
    for path in leaf_paths(effect.options):
        assert _ALLOW.is_legal(effect.type, path), (
            where,
            "effect-path",
            effect.type,
            path,
        )


def _ids(case: tuple[str, str, dict[str, str]]) -> str:
    pack, mood, combo = case
    return f"{pack}-{mood}-" + "_".join(combo[role] for role in _ROLES)


@pytest.mark.parametrize("case", _MATRIX, ids=_ids)
def test_phase7_property_matrix(case: tuple[str, str, dict[str, str]]) -> None:
    """DoD 6 / §13.6 on one baked `SoundDesign` per (pack, mood, flavor-combo)."""
    pack, mood, combo = case
    design, timbres = _design_for(pack, mood, combo)

    for track_id, ts in design.track_sounds.items():
        where = f"{pack}/{mood}/{track_id}"
        _assert_instrument(ts.instrument, where)
        for effect in ts.effects:
            _assert_effect(effect, f"{where}.effect")
        assert ts.channel.volume_db <= 6, (where, "volumeDb", ts.channel.volume_db)
        assert -1 <= ts.channel.pan <= 1, (where, "pan", ts.channel.pan)
        for send in ts.sends:
            assert send.bus == "reverb", (where, "send-bus", send.bus)

    # ---- The shared reverb bus: only v1 bus, effects legal, ranges honored. ----
    reverb_bus = next((b for b in design.buses if b.id == "reverb"), None)
    assert reverb_bus is not None, (pack, mood, "no-reverb-bus")
    for effect in reverb_bus.effects:
        _assert_effect(effect, f"{pack}/{mood}/bus.reverb")

    reverb_effect = next(e for e in reverb_bus.effects if e.type == "Reverb")
    decay = reverb_effect.options["decay"]
    pre_delay = reverb_effect.options["preDelay"]
    d_lo, d_hi = timbres.bus.reverb.decay
    p_lo, p_hi = timbres.bus.reverb.pre_delay
    # decay = round3(lo·(hi/lo)^space), preDelay = round3(lo + space·(hi−lo));
    # both monotone in space ∈ [0, 1], so round3 of the endpoints is the tight
    # inclusive envelope every baked value must sit inside.
    assert round3(d_lo) <= decay <= round3(d_hi), (pack, mood, "decay", decay)
    assert round3(p_lo) <= pre_delay <= round3(p_hi), (
        pack,
        mood,
        "preDelay",
        pre_delay,
    )

    # ---- Master chain: non-empty, every effect legal, ends in a Limiter. -------
    for effect in design.master.effects:
        _assert_effect(effect, f"{pack}/{mood}/master")
    assert design.master.effects, (pack, mood, "master-empty")
    assert design.master.effects[-1].type == "Limiter", (
        pack,
        mood,
        "master-tail",
        design.master.effects[-1].type,
    )


def test_matrix_non_vacuous() -> None:
    """The matrix is the exact expected size and non-degenerate — so the per-doc
    invariant asserts are not passing vacuously on an empty/single-class set.

    Size is recomputed from the dimensions (fully exhausted: moods × the whole
    flavor cross-product, nothing sampled) and asserted against `len(_MATRIX)`."""
    expected = 0
    dims: list[tuple[str, int, int, int]] = []
    for pack in _PACKS:
        _, flavors = _pack_ctx(pack)
        interp = resolve_pack(pack).interpreter  # type: ignore[union-attr]
        assert interp is not None
        n_combo = 1
        for role in _ROLES:
            n_combo *= len(flavors[role])
        n_mood = len(interp.supported_moods)
        expected += n_mood * n_combo
        dims.append((pack, n_mood, n_combo, n_mood * n_combo))

    assert len(_MATRIX) == expected, (len(_MATRIX), expected)
    # A computed floor: the two packs alone exhaust to 344 docs; a silent shrink
    # of either dimension would drop below this.
    assert expected >= 300, expected

    classes: set[str] = set()
    polysynths = 0
    sends = 0
    for pack, mood, combo in _MATRIX:
        design, _ = _design_for(pack, mood, combo)
        for ts in design.track_sounds.values():
            classes.add(ts.instrument.type)
            if ts.instrument.type == "PolySynth":
                polysynths += 1
            sends += len(ts.sends)

    assert len(classes) >= 2, sorted(classes)
    assert polysynths >= 1, polysynths
    assert sends >= 1, sends

    print(
        "phase7 property matrix — per-pack (pack, moods, combos, docs):",
        dims,
        "| total docs:",
        expected,
        "| distinct instrument classes:",
        sorted(classes),
        "| PolySynth tracks:",
        polysynths,
        "| reverb sends:",
        sends,
    )
