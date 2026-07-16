"""Voicing & voice-leading — the §8.4/§8.5/§8.6 theory algorithms (T2).

Pure, deterministic, **integer-cost** functions of their inputs — no randomness,
no clock, no float comparisons anywhere in candidate generation or the DP
(ROADMAP invariant 5; PHASE_4 D16). Every cost is a semitone count times an
integer weight. The pinned formulas (§8.4 candidate classes, §8.5 `vl_distance`,
§8.6 Viterbi `optimal_voicing_path`) are normative; on divergence from a printed
worked-example number the algorithm text wins (ROADMAP §3).

Built on the committed T1 resolution core (`trackgen.theory.chords`): quality
interval stacks, guide tones, extension offsets.

Two design gaps in the pinned surface are resolved here and flagged for review:

- **`quartal` and §7.4.** §8.4 says `quartal` stacks fourths "from the scale
  (§7.4)", but the pinned §8.3 signature `voicing_candidates(spec, cls, lane)`
  carries no key, and §7.4's chord-scale hint needs one. With no key reachable,
  the diatonic snap is impossible, so `quartal` stacks *perfect* fourths
  (5 semitones) from the root (a chord tone): offsets `[0, 5, 10, 15]` — three
  stacked fourths, four voices. A reviewer/Phase-8 author who wants the diatonic
  version must widen the signature to pass a key.

- **`optimal_voicing_path` anchor.** §8.6 defines the drift term against
  "the lane's register anchor (default: lane midpoint)", but the pinned path
  signature carries neither lane nor anchor. A keyword-only `anchor` is added
  (default `None`). Phase 5 knows its lane and passes `anchor=lane_midpoint`
  explicitly. When omitted, the anchor is derived as the midpoint of the
  candidate pitch range across all stages — which recovers the lane midpoint
  exactly when the candidates fill the lane (the common case), but is only a
  heuristic otherwise, so callers with a known lane should pass it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple, Protocol

from trackgen.schema.ir import ChordSpec
from trackgen.theory.chords import (
    EXTENSION_OFFSETS,
    QUALITY_INTERVALS,
    guide_tones,
)

# The nine §8.4 candidate-class names (fifths added by PHASE_5 §6.5).
VoicingClass = str

_NINTH_EXTENSIONS = ("9", "b9", "#9")


class LaneLike(Protocol):
    """A register lane — `low`/`high` MIDI bounds (§8.3 `lane = {low, high}`).

    The C5 ceiling is structural: non-drum lanes have `high ≤ 71` (§4.4). A
    `schema.ir.Register` uses `low_midi`/`high_midi`, not `low`/`high`; adapt it
    with `Lane(reg.low_midi, reg.high_midi)` at the call site. Members are
    read-only so a `Lane` `NamedTuple` (immutable) satisfies the protocol.
    """

    @property
    def low(self) -> int: ...

    @property
    def high(self) -> int: ...


class Lane(NamedTuple):
    """Concrete `LaneLike`: a `{low, high}` MIDI register lane."""

    low: int
    high: int


class VoicingWeights(NamedTuple):
    """Integer voice-leading weights (§8.5/§8.6).

    Pinned defaults (§8.6): `move 4, top 4, common 3, drift 1`. Phase 5 passes
    its own per-role weights; these defaults are the tested reference.
    """

    move: int = 4
    top: int = 4
    common: int = 3
    drift: int = 1


class _Members(NamedTuple):
    """Chord-tone semitone offsets from the root (root at 0).

    `third` / `seventh` / `ninth` are `None` when the quality lacks that member;
    `third_or` substitutes `base[1]` (e.g. the sus 2nd/4th) when there is no
    third, so triad-shaped classes always have a middle voice.
    """

    third: int | None
    third_or: int
    fifth: int
    seventh: int | None
    ninth: int | None
    core: tuple[int, ...]


def _members(spec: ChordSpec) -> _Members:
    base = QUALITY_INTERVALS[spec.quality]
    fifth = base[2]
    gt = guide_tones(spec)
    third = None if gt.third is None else (gt.third - spec.root_pc) % 12
    seventh = None if gt.seventh is None else (gt.seventh - spec.root_pc) % 12
    third_or = base[1] if third is None else third
    ninth: int | None = None
    for ext in spec.extensions:
        if ext in _NINTH_EXTENSIONS:
            ninth = EXTENSION_OFFSETS[ext]
            break
    return _Members(third, third_or, fifth, seventh, ninth, base)


def _ascending_inversion(core: tuple[int, ...], inv: int) -> list[int]:
    """A close-position inversion of `core` (offsets), ascending, starting at
    `core[inv]` and lifting each wrapped tone into the next octave."""
    n = len(core)
    rotated = [core[(inv + k) % n] for k in range(n)]
    stack = [rotated[0]]
    for off in rotated[1:]:
        val = off
        while val <= stack[-1]:
            val += 12
        stack.append(val)
    return stack


def _class_shapes(spec: ChordSpec, cls: VoicingClass) -> list[list[int]]:
    """The class's base voicing shapes as root-relative offsets (root at 0),
    each ascending-sorted, in §8.4 formula order (the tie-break order)."""
    m = _members(spec)

    if cls == "shell2":  # {3rd, 7th}; triads → {3rd, 5th}
        pair = (
            [m.third_or, m.seventh] if m.seventh is not None else [m.third_or, m.fifth]
        )
        return [sorted(pair)]

    if cls == "shell3":  # {root, 3rd, 7th}; triads → root-position close
        if m.seventh is not None:
            return [sorted([0, m.third_or, m.seventh])]
        return [sorted([0, m.third_or, m.fifth])]

    if cls == "rootless_a":  # 3-5-7-9 (9 from extensions else omitted → 3-5-7)
        stack = [m.third_or, m.fifth]
        if m.seventh is not None:
            stack.append(m.seventh)
            if m.ninth is not None:
                stack.append(m.ninth)
        return [sorted(stack)]

    if cls == "rootless_b":  # 7-9-3-5; falls back to 3-5-7 when no 9
        if m.seventh is not None and m.ninth is not None:
            return [sorted([m.seventh, m.ninth, m.third_or + 12, m.fifth + 12])]
        stack = [m.third_or, m.fifth]
        if m.seventh is not None:
            stack.append(m.seventh)
        return [sorted(stack)]

    if cls == "drop2":  # close stack (root pos + inversions), 2nd-from-top −8ve
        shapes: list[list[int]] = []
        for inv in range(len(m.core)):
            stack = _ascending_inversion(m.core, inv)
            stack[-2] -= 12
            shapes.append(sorted(stack))
        return shapes

    if cls == "triad_close":  # triad, root position + 2 inversions
        triad = m.core[:3]
        return [sorted(_ascending_inversion(triad, inv)) for inv in range(3)]

    if cls == "triad_open":  # triad_close with the middle voice −8ve
        triad = m.core[:3]
        shapes = []
        for inv in range(3):
            stack = _ascending_inversion(triad, inv)
            stack[1] -= 12
            shapes.append(sorted(stack))
        return shapes

    if cls == "quartal":  # three stacked perfect fourths from the root
        return [[0, 5, 10, 15]]

    if cls == "fifths":  # {root, root+7, root+12} — 3rd-omitted pad
        return [[0, 7, 12]]

    raise ValueError(f"unknown voicing class {cls!r}")


def voicing_candidates(
    spec: ChordSpec, cls: VoicingClass, lane: LaneLike
) -> list[list[int]]:
    """Every octave placement of class `cls` for `spec` that fits `lane` (§8.4).

    Candidates are ascending-sorted MIDI lists. A placement is kept iff
    `bottom ≥ lane.low` and `top ≤ lane.high` — the lane ceiling is a hard prune
    (nothing above `lane.high`; non-drum lanes have `high ≤ 71`, the C5 ceiling,
    ROADMAP invariant 4). Generation order — class-formula order, then ascending
    octave — is the deterministic tie-break order the DP relies on.
    """
    out: list[list[int]] = []
    for shape in _class_shapes(spec, cls):
        for octave in range(0, 11):
            root_midi = spec.root_pc + 12 * octave
            voicing = [root_midi + off for off in shape]
            if voicing[0] >= lane.low and voicing[-1] <= lane.high:
                out.append(voicing)
    return out


def vl_distance(a: list[int], b: list[int], weights: VoicingWeights) -> int:
    """Integer voice-leading distance between two voicings (§8.5).

    `w.move · Σ|aᵢ−bᵢ| + w.top · |a_top − b_top| − w.common · |pitches in both|`.
    Inputs are equal-cardinality, ascending-sorted MIDI lists; pad/truncate is
    the caller's concern (§8.5) — no padding happens here. `common` counts exact
    shared MIDI pitches. Returns a plain `int`.
    """
    move_sum = sum(abs(x - y) for x, y in zip(a, b, strict=True))
    top = abs(a[-1] - b[-1])
    common = len(set(a) & set(b))
    return weights.move * move_sum + weights.top * top - weights.common * common


def _pad_to_equal(a: list[int], b: list[int]) -> tuple[list[int], list[int]]:
    """Pad the shorter voicing with its own top pitch (PHASE_5 §6.4 policy) so
    `vl_distance` sees equal cardinality; keeps both ascending-sorted."""
    if len(a) < len(b):
        return a + [a[-1]] * (len(b) - len(a)), b
    if len(b) < len(a):
        return a, b + [b[-1]] * (len(a) - len(b))
    return a, b


def optimal_voicing_path(
    specs: list[ChordSpec],
    candidates_fn: Callable[[ChordSpec], list[list[int]]],
    weights: VoicingWeights,
    *,
    anchor: int | None = None,
) -> list[list[int]]:
    """The minimum-cost voicing path over `specs` (§8.6 Viterbi DP).

    `cost = Σₜ vl_distance(vₜ₋₁, vₜ) + Σₜ w.drift · |top(vₜ) − anchor|`. Each
    stage's candidates come from `candidates_fn(spec) -> [voicing]`. All costs
    are integers; ties break to the lowest candidate index (the `min` scans in
    generation order and keeps the first). Complexity O(N·K²).

    `anchor` defaults to the midpoint of the candidate pitch range across all
    stages (recovers the lane midpoint when candidates fill the lane); pass it
    explicitly when the true lane anchor is known (Phase 5 does).
    """
    stages: list[list[list[int]]] = [candidates_fn(s) for s in specs]
    if not stages:
        return []
    for t, cands in enumerate(stages):
        if not cands:
            raise ValueError(f"stage {t} has no candidate voicings")

    if anchor is None:
        notes = [n for cands in stages for v in cands for n in v]
        anchor = (min(notes) + max(notes)) // 2
    anchor_i: int = anchor

    def emit(voicing: list[int]) -> int:
        return weights.drift * abs(voicing[-1] - anchor_i)

    def trans(prev: list[int], cur: list[int]) -> int:
        pa, pb = _pad_to_equal(prev, cur)
        return vl_distance(pa, pb, weights)

    best = [emit(v) for v in stages[0]]
    parents: list[list[int]] = [[-1] * len(stages[0])]

    for t in range(1, len(stages)):
        prev_cands = stages[t - 1]
        cur_cands = stages[t]
        new_best: list[int] = []
        row_parents: list[int] = []
        for cur in cur_cands:
            best_i = 0
            best_cost = best[0] + trans(prev_cands[0], cur)
            for i in range(1, len(prev_cands)):
                cost = best[i] + trans(prev_cands[i], cur)
                if cost < best_cost:  # strict → lowest index wins ties
                    best_cost = cost
                    best_i = i
            new_best.append(emit(cur) + best_cost)
            row_parents.append(best_i)
        best = new_best
        parents.append(row_parents)

    final_j = 0
    for j in range(1, len(best)):
        if best[j] < best[final_j]:
            final_j = j

    idx = [0] * len(stages)
    idx[-1] = final_j
    for t in range(len(stages) - 1, 0, -1):
        idx[t - 1] = parents[t][idx[t]]

    return [stages[t][idx[t]] for t in range(len(stages))]
