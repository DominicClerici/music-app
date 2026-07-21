"""Shared stage-6 driver for the T4 goldens (PHASE_6 §7, SESSION_10 §4 T4).

Not a test module (leading underscore — pytest does not collect it). It drives
the **real** chained pipeline at seed `1ps9wxb` (interpret -> form -> harmony ->
arrange -> select_patterns -> generate x4), exactly as the orchestrator does up
to the stage-6 call, then runs the **real** stage-6 sub-passes so a golden test
can inspect the note structure before and after each pass.

The two worked-example params are the committed milestone-fixture params
(`fixtures/{pop_rock,jazz}.milestone.trackdoc.json`), verified this session:

- pop  : 7-section form, 76 bars, 123 BPM, cold close.
- jazz : 6-section form, 64 bars, 69 BPM, ritard close.
"""

from __future__ import annotations

from dataclasses import dataclass

from trackgen.arrangement import arrange
from trackgen.form.stage import form
from trackgen.harmony.stage import harmony
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.generators import generate
from trackgen.parts.selection import select_patterns
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementPlan,
    GenerationPlan,
    HarmonicPlan,
    Phrase,
    PhraseNote,
    SongForm,
)
from trackgen.seeds import Rng, stream_rng
from trackgen.transitions import transitions
from trackgen.transitions._common import BAR, to_builders, to_phrases
from trackgen.transitions.devices import apply_devices
from trackgen.transitions.ending import find_t_last, hold_ending
from trackgen.transitions.mutation import mutate

_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")

POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


@dataclass(frozen=True)
class Stage6Inputs:
    """The generated inputs to stage 6, plus the pre-stage-6 `Phrase[]`."""

    params: dict[str, object]
    plan: GenerationPlan
    pack: StylePack
    sf: SongForm
    hp: HarmonicPlan
    ap: ArrangementPlan
    phrases: list[Phrase]  # post-generation, pre-stage-6.


def drive(params: dict[str, object]) -> Stage6Inputs:
    """Run interpret -> ... -> generate x4 (the orchestrator chain, pre-stage-6)."""
    plan = generate_plan(params)
    pack = resolve_pack(params["styleFamily"])  # type: ignore[arg-type]
    assert pack is not None and pack.forms is not None and pack.progressions is not None
    assert pack.transitions is not None  # T1 loaded the transitions.yaml.
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
    return Stage6Inputs(params, plan, pack, sf, hp, ap, phrases)


def stage6_final(inp: Stage6Inputs) -> list[Phrase]:
    """The real `transitions(...)` output (6a -> 6b -> 6c)."""
    return transitions(inp.phrases, inp.sf, inp.hp, inp.ap, inp.plan, inp.pack)


def stage6_passes(inp: Stage6Inputs) -> tuple[list[Phrase], list[Phrase]]:
    """`(post_6b, final)` — the note set after 6a+6b (pre-mutation) and after
    6c. Mirrors `transitions()`' internals exactly so a test can diff the
    mutation pass (no-op vs fired) on the real pipeline data."""
    t_last = find_t_last(inp.hp)
    builders = to_builders(inp.phrases)
    hold_ending(builders, inp.sf, inp.hp, inp.plan, inp.pack, t_last)
    dropout_ticks = apply_devices(
        builders, inp.sf, inp.ap, inp.plan, inp.pack, t_last // BAR
    )
    post_6b = to_phrases(builders)
    final = mutate(
        post_6b,
        inp.sf,
        inp.hp,
        inp.ap,
        inp.plan,
        inp.pack,
        dropout_ticks=dropout_ticks,
    )
    return post_6b, final


def track_window(
    phrases: list[Phrase], track_id: str, lo: int, hi: int
) -> list[PhraseNote]:
    """Notes on voice-track `track_id` with `lo <= ticks < hi`, `(ticks, midi)`
    sorted."""
    out: list[PhraseNote] = []
    for p in phrases:
        if p.track_id == track_id:
            out += [n for n in p.notes if lo <= n.ticks < hi]
    out.sort(key=lambda n: (n.ticks, n.midi if n.midi is not None else -1))
    return out


def role_window(phrases: list[Phrase], role: str, lo: int, hi: int) -> list[PhraseNote]:
    """Notes on `role` (across its voice-tracks) with `lo <= ticks < hi`,
    `(ticks, midi)` sorted."""
    out: list[PhraseNote] = []
    for p in phrases:
        if p.role == role:
            out += [n for n in p.notes if lo <= n.ticks < hi]
    out.sort(key=lambda n: (n.ticks, n.midi if n.midi is not None else -1))
    return out
