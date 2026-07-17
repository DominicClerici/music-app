"""Provisional pipeline stubs (PHASE_5 §8, D22) — Phases 6/7 replace them.

The milestone (Chunk 4) wires the full pipeline end to end but de-risks
generation, not sound design or expression. Three stages are therefore stubs:

- `transitions` — identity; real fills/entry-crashes are Phase 6.
- `humanize` — returns the phrases unchanged plus an empty tempo-event list;
  swing, jitter, and ritard tempo events are Phase 6.
- `sound_design` — reads the pack's provisional `timbres.yaml`, selects each
  role's active flavor from `plan.role_flavors`, and returns one `TrackSound`
  per track id (the eight drum tracks plus bass/comping/pads); the real
  sound-design stage (mix, sends, reverb bus) is Phase 7.

All three make **zero** RNG draws and import no `random`/wall-clock (invariant 5,
TID251): the reserved `transitions`/`humanize`/`sound` seed streams stay unused.
"""

from pydantic import BaseModel, ConfigDict

from trackgen.packs.models import StylePack
from trackgen.parts.generators import _TRACK_ORDER as _DRUM_TRACK_IDS
from trackgen.schema.document import EffectPatch, InstrumentPatch, Tempo
from trackgen.schema.ir import GenerationPlan, Phrase

# The eight drum track ids (single-sourced from `parts.generators._TRACK_ORDER`,
# as the Serializer also imports it) and the three pitched roles keyed by their
# own name. `sound_design` returns a `TrackSound` for every one — the Serializer
# emits only those with >= 1 note.
_PITCHED_ROLES: tuple[str, ...] = ("bass", "comping", "pads")


class TrackSound(BaseModel):
    """§8.3 the per-track sound the Serializer consumes: an instrument patch,
    an effects chain (empty in the stub), and an optional drum trigger `midi`
    (None for snare and for pitched tracks, whose notes carry their own midi)."""

    model_config = ConfigDict(frozen=True)

    instrument: InstrumentPatch
    effects: list[EffectPatch] = []
    midi: int | None = None


def transitions(phrases: list[Phrase]) -> list[Phrase]:
    """STUB (Phase 6): identity. Real transitions add fills / entry crashes."""
    return phrases


def humanize(phrases: list[Phrase]) -> tuple[list[Phrase], list[Tempo]]:
    """STUB (Phase 6): pass the phrases through unchanged with no tempo events.
    Swing, timing jitter, and ritard tempo events are the real Humanizer's."""
    return phrases, []


def sound_design(plan: GenerationPlan, pack: StylePack) -> dict[str, TrackSound]:
    """STUB (Phase 7): map each track id to a `TrackSound` from the pack's
    provisional `timbres.yaml`, selecting each role's active flavor via
    `plan.role_flavors`. Zero draws. Runs before serialize (does not see
    phrases), so it returns patches for every candidate track."""
    timbres = pack.timbres
    if timbres is None:
        raise ValueError(
            f"sound_design requires pack.timbres, but pack "
            f"{plan.style_pack.id!r} has none (author a timbres.yaml)"
        )

    sounds: dict[str, TrackSound] = {}

    drum_flavor = _flavor(plan, "drums")
    kit = timbres.drums.get(drum_flavor)
    if kit is None:
        raise ValueError(
            f"sound_design: drums flavor {drum_flavor!r} is not in timbres.drums "
            f"{sorted(timbres.drums)}"
        )
    for track_id in _DRUM_TRACK_IDS:
        timbre = kit.get(track_id)
        if timbre is None:
            raise ValueError(
                f"sound_design: drum kit {drum_flavor!r} is missing track "
                f"{track_id!r} (needs {list(_DRUM_TRACK_IDS)})"
            )
        sounds[track_id] = TrackSound(instrument=timbre.instrument, midi=timbre.midi)

    pitched_tables = {
        "bass": timbres.bass,
        "comping": timbres.comping,
        "pads": timbres.pads,
    }
    for role in _PITCHED_ROLES:
        flavor = _flavor(plan, role)
        table = pitched_tables[role]
        timbre = table.get(flavor)
        if timbre is None:
            raise ValueError(
                f"sound_design: {role} flavor {flavor!r} is not in timbres.{role} "
                f"{sorted(table)}"
            )
        sounds[role] = TrackSound(instrument=timbre.instrument, midi=timbre.midi)

    return sounds


def _flavor(plan: GenerationPlan, role: str) -> str:
    flavor = plan.role_flavors.get(role)
    if flavor is None:
        raise ValueError(
            f"sound_design: plan.role_flavors has no entry for role {role!r} "
            f"(has {sorted(plan.role_flavors)})"
        )
    return flavor
