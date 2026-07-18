"""The pipeline orchestrator (PHASE_5 §8.1, SESSION_09 T3).

`generate_track(raw_params)` wires the nine pipeline stages end to end and
returns a serialized `TrackDocument`. It follows the authoritative code chain
(SESSION_09 "Authoritative wiring facts" — the §8.1 pseudocode is stale): the
same interpret -> form -> harmony -> arrange -> select_patterns -> generate x4
loop the test-only `_drive_full` driver uses, then the real stages
transitions -> humanize (Phase 6) -> sound_design (Phase 7) -> serialize.

The orchestrator itself makes **no** RNG draws: `generate_plan` is the entropy
boundary (it derives the master seed), and every downstream stage receives its
seed material explicitly. No `random`/wall-clock import here (invariant 5).
"""

from trackgen.arrangement import arrange
from trackgen.form.stage import form
from trackgen.harmony.stage import harmony
from trackgen.humanize.stage import humanize
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.parts.generators import generate
from trackgen.parts.selection import select_patterns
from trackgen.pipeline.serialize import serialize
from trackgen.schema.document import Role, TrackDocument
from trackgen.schema.ir import Phrase
from trackgen.seeds import Rng, stream_rng
from trackgen.sound.stage import sound_design
from trackgen.transitions import transitions

_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")


def generate_track(raw_params: dict[str, object]) -> TrackDocument:
    """Run the full pipeline for `raw_params` and return a `TrackDocument`.

    `raw_params` is the public client dict (camelCase keys, `styleFamily`
    required). It is threaded verbatim into `meta.params` (round-trip
    reproducibility, DoD 9), so an emitted document can be regenerated from
    its own metadata.
    """
    plan = generate_plan(raw_params)

    style_family = raw_params["styleFamily"]
    assert isinstance(style_family, str)
    pack = resolve_pack(style_family)
    if (
        pack is None
        or pack.forms is None
        or pack.progressions is None
        or pack.timbres is None
    ):
        raise ValueError(
            f"styleFamily {style_family!r} did not resolve to a pack with forms, "
            f"progressions, and timbres (pack={pack!r})"
        )

    sf = form(plan, pack.forms)
    hp = harmony(
        plan,
        sf,
        pack.progressions,
        stream_rng(plan.seed.master, plan.seed.overrides, "harmony"),
    )
    ap = arrange(plan, sf, pack, Rng(0))
    sel = select_patterns(plan, sf, ap, pack, plan.seed.master, plan.seed.overrides)

    phrases: list[Phrase] = []
    for role in _ROLES:
        phrases += generate(
            role,
            ap,
            hp,
            sf,
            plan,
            pack,
            sel,
            master=plan.seed.master,
            overrides=plan.seed.overrides,
            prior_phrases=phrases,
        )

    phrases = transitions(phrases, sf, hp, ap, plan, pack)
    phrases, tempo_events = humanize(phrases, sf, plan)
    design = sound_design(
        plan, pack.timbres, stream_rng(plan.seed.master, plan.seed.overrides, "sound")
    )

    return serialize(
        plan, sf, phrases, design, tempo_events=tempo_events, params=raw_params
    )
