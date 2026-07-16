"""Comping/pads voicing pass (PHASE_5 §6.4/§6.5).

Runs the committed PHASE_4 Viterbi optimizer (`theory.voicing.optimal_voicing_path`)
once per voiced role over the *entire* chord timeline, producing a per-role map
`ChordEvent.start_tick -> voicing MIDI`. The generator (Chunk 3) injects this map
as `retarget_event`'s `voicing_for` hook (keyed by the governing chord's
`start_tick`), so every hit — including a pushed hit that sounds the *next*
chord's voicing — has a pre-computed voicing to emit.

Integer Viterbi only: no draws, no `random`, no clock (ROADMAP invariant 5).

C-04 resolution (confirms committed `theory/voicing.py`; no signature change):

1. **Keyless `quartal` = perfect fourths** `[0, 5, 10, 15]`. `voicing_candidates`
   already stacks perfect (not diatonic) fourths — the only key-free reading, since
   the pinned `(spec, cls, lane)` signature carries no key. Only jazz pads use
   `quartal`, and they are dormant in v1 (`layersMax` 3, the trio), so no §9.3
   golden exercises it; a diatonic widening is deferred to Phase 8.
2. **Anchor = `lane.high − 6`**, passed explicitly to `optimal_voicing_path`
   (top voices settle in the C4–C5 research zone). Verified against §9.3's stated
   anchors: jazz comping lane 46–69 → 63; pop comping lane 50–71 → 65.
3. **Candidate class per role via pack data** (`voicing.classes[rung]`). The
   authored classes never route a triad into a 4-note seventh-chord class (pop
   comping uses `triad_close/triad_open/shell3`; jazz uses `shell2/shell3/
   rootless_*`), so no engine change is needed.
"""

from __future__ import annotations

from trackgen.packs.models import StylePack
from trackgen.schema.document import Role
from trackgen.schema.ir import ArrangementPlan, ChordEvent, ChordSpec
from trackgen.theory.voicing import (
    Lane,
    VoicingWeights,
    optimal_voicing_path,
    voicing_candidates,
)

# §6.4/§6.5 per-role voice-leading weights. Comping favours a settled top voice
# (top 4); pads trade that for stillness — held common tones (common 5) over a
# mobile top (top 2).
_WEIGHTS: dict[Role, VoicingWeights] = {
    "comping": VoicingWeights(move=4, top=4, common=3, drift=1),
    "pads": VoicingWeights(move=4, top=2, common=5, drift=1),
}


def build_voicing_map(
    role: Role,
    arrangement: ArrangementPlan,
    chords: list[ChordEvent],
    pack: StylePack,
) -> dict[int, tuple[int, ...]]:
    """The role's voicing for every chord event, keyed by `start_tick`.

    One `optimal_voicing_path` over the whole `chords` timeline in order (active
    sections or not — keeps the DP indices aligned with the plan). Per-event
    candidates = the in-order concatenation of `voicing_candidates(chord, cls,
    lane)` over each class in `pack.voicing[role].classes[rung]`, where `rung` is
    the intensity of the event's section. Lane = the role's bias-shifted
    arrangement register; anchor = `lane.high − 6`.
    """
    if role not in _WEIGHTS:
        raise ValueError(f"voicing pass only serves comping/pads, not {role!r}")
    if role not in pack.voicing:
        raise ValueError(f"pack declares no voicing.classes for role {role!r}")
    classes = pack.voicing[role].classes

    role_entries = [e for e in arrangement.entries if e.role == role]
    if not role_entries:
        raise ValueError(f"arrangement has no entry for role {role!r}")
    # Lane is uniform across sections for a role (§4.4) — take the first entry.
    reg = role_entries[0].register
    lane = Lane(reg.low_midi, reg.high_midi)
    anchor = lane.high - 6

    section_rung = {e.section_id: e.intensity for e in role_entries}

    # Candidates depend on the event's section rung, not the ChordSpec alone (two
    # events may share a spelling across sections of different intensity), so they
    # are precomputed per event and fed positionally in timeline order — the order
    # `optimal_voicing_path` builds its stages in.
    stages: list[list[list[int]]] = []
    for event in chords:
        rung = section_rung.get(event.section_id)
        if rung is None:
            raise ValueError(
                f"no {role!r} arrangement entry for section {event.section_id!r}"
            )
        cands: list[list[int]] = []
        for cls in classes[rung]:
            cands.extend(voicing_candidates(event.chord, cls, lane))
        if not cands:
            raise ValueError(
                f"no lane-fitting voicing for {event.chord.symbol!r} at "
                f"{event.start_tick} (role {role!r}, rung {rung}, classes "
                f"{classes[rung]}, lane {lane})"
            )
        stages.append(cands)

    stage_iter = iter(stages)

    def candidates_fn(_spec: ChordSpec) -> list[list[int]]:
        return next(stage_iter)

    path = optimal_voicing_path(
        [event.chord for event in chords],
        candidates_fn,
        _WEIGHTS[role],
        anchor=anchor,
    )
    return {
        event.start_tick: tuple(voicing)
        for event, voicing in zip(chords, path, strict=True)
    }
