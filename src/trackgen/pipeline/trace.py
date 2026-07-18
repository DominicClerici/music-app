"""Trace orchestrator (PHASE_8 §8.2, §9.3; SESSION_15 T1).

`generate_trace(raw_params)` runs the identical nine-stage chain as
`generate_track` but retains every intermediate IR boundary in a
`GenerationTrace`, instead of discarding all but the final document. It is the
shared substrate for the golden corpus (§8.2 stores every boundary) and the
`--explain` log (§9.3), and for the C2 validators that need the pre-humanizer
phrases (W7) and the post-6 vs post-7 note counts (W8).

`generate_track` delegates to this module (`generate_trace(...).document`), so
the production entry point is provably behavior-preserving: same call order,
same rng streams, same arguments, same document. The three phrase snapshots are
kept as distinct lists (stages 5 -> 6 -> 7 each return a fresh list), so a
consumer can compare them without one stage having overwritten another.
"""

from dataclasses import dataclass

from trackgen.arrangement import arrange
from trackgen.form.stage import form
from trackgen.harmony.stage import harmony
from trackgen.humanize.stage import humanize
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.parts.generators import generate
from trackgen.parts.selection import SelectionResult, select_patterns
from trackgen.pipeline.serialize import serialize
from trackgen.schema.document import Role, Tempo, TrackDocument
from trackgen.schema.ir import (
    ArrangementPlan,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    SongForm,
)
from trackgen.seeds import Rng, stream_rng
from trackgen.sound.stage import SoundDesign, sound_design
from trackgen.transitions import transitions

_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")


@dataclass(frozen=True)
class GenerationTrace:
    """Every IR boundary of one pipeline run, in stage order.

    `phrases_stage5` is post part-generation, `phrases_stage6` post-transitions,
    `phrases_stage7` post-humanize — three separable snapshots, never the same
    list mutated in place. `document` is the exact `TrackDocument`
    `generate_track` returns for the same params."""

    plan: GenerationPlan
    song_form: SongForm
    harmony: HarmonicPlan
    arrangement: ArrangementPlan
    selection: SelectionResult
    phrases_stage5: list[Phrase]
    phrases_stage6: list[Phrase]
    phrases_stage7: list[Phrase]
    tempo_events: list[Tempo]
    sound_design: SoundDesign
    document: TrackDocument


def generate_trace(raw_params: dict[str, object]) -> GenerationTrace:
    """Run the full pipeline for `raw_params`, retaining every IR boundary.

    The stage chain, call order, rng streams, and arguments are identical to
    `generate_track`; only the intermediate results are kept rather than
    discarded.
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

    phrases_stage5: list[Phrase] = []
    for role in _ROLES:
        phrases_stage5 += generate(
            role,
            ap,
            hp,
            sf,
            plan,
            pack,
            sel,
            master=plan.seed.master,
            overrides=plan.seed.overrides,
            prior_phrases=phrases_stage5,
        )

    phrases_stage6 = transitions(phrases_stage5, sf, hp, ap, plan, pack)
    phrases_stage7, tempo_events = humanize(phrases_stage6, sf, plan)
    design = sound_design(
        plan, pack.timbres, stream_rng(plan.seed.master, plan.seed.overrides, "sound")
    )

    document = serialize(
        plan, sf, phrases_stage7, design, tempo_events=tempo_events, params=raw_params
    )

    return GenerationTrace(
        plan=plan,
        song_form=sf,
        harmony=hp,
        arrangement=ap,
        selection=sel,
        phrases_stage5=phrases_stage5,
        phrases_stage6=phrases_stage6,
        phrases_stage7=phrases_stage7,
        tempo_events=tempo_events,
        sound_design=design,
        document=document,
    )
