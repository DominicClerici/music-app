"""Golden + property tests for the voicing / voice-leading algorithms
(PHASE_4 §8.4/§8.5/§8.6; DoD §14.2 — voicing portion).

The PHASE_4 formulas are normative: if the implementation disagrees, the
implementation is wrong (ROADMAP §3). The ii–V–I optimal paths below are
computed by hand (see the module docstring in the test for the derivation) and
asserted exactly; the register-drift paths are likewise hand-derived.

All costs are integers — no floats anywhere in candidate generation or the DP
(PHASE_4 D16). The final test asserts that invariant directly.
"""

from __future__ import annotations

from collections.abc import Callable

from trackgen.schema.ir import ChordSpec
from trackgen.theory import (
    Lane,
    VoicingWeights,
    optimal_voicing_path,
    vl_distance,
    voicing_candidates,
)

# ii–V–I in C major (no extensions): Dm7 → G7 → Cmaj7.
DM7 = ChordSpec(root_pc=2, quality="min7", symbol="Dm7")
G7 = ChordSpec(root_pc=7, quality="dom7", symbol="G7")
CMAJ7 = ChordSpec(root_pc=0, quality="maj7", symbol="Cmaj7")

DEFAULTS = VoicingWeights()  # move=4, top=4, common=3, drift=1


# --- §8.4 candidate generation & lane pruning --------------------------------


def test_defaults_are_pinned() -> None:
    assert DEFAULTS == (4, 4, 3, 1)
    assert DEFAULTS.move == 4
    assert DEFAULTS.top == 4
    assert DEFAULTS.common == 3
    assert DEFAULTS.drift == 1


def test_shell3_candidates_and_ascending_octave_order() -> None:
    # shell3 = {root, 3rd, 7th}. Cmaj7 offsets [0, 4, 11] on root pc 0.
    cands = voicing_candidates(CMAJ7, "shell3", Lane(36, 72))
    assert cands == [[36, 40, 47], [48, 52, 59], [60, 64, 71]]
    # Single-shape class ⇒ generation order is strictly ascending octave.
    bottoms = [v[0] for v in cands]
    assert bottoms == sorted(bottoms)


def test_lane_ceiling_hard_prune_at_71() -> None:
    # C5 ceiling: a high ≤ 71 lane must emit nothing above MIDI 71 (§4.4).
    lane = Lane(48, 71)
    for cls in (
        "shell2",
        "shell3",
        "rootless_a",
        "rootless_b",
        "drop2",
        "triad_close",
        "triad_open",
        "quartal",
        "fifths",
    ):
        for spec in (DM7, G7, CMAJ7):
            for voicing in voicing_candidates(spec, cls, lane):
                assert voicing[0] >= 48
                assert voicing[-1] <= 71
                assert max(voicing) <= 71


def test_shell2_is_guide_tones_for_sevenths() -> None:
    # shell2 = {3rd, 7th}. G7: 3rd=B(11 → +4), 7th=F(5 → +10) ⇒ offsets [4, 10].
    cands = voicing_candidates(G7, "shell2", Lane(36, 84))
    # every candidate is the 3rd/7th pair transposed by octaves
    for v in cands:
        assert len(v) == 2
        assert [p % 12 for p in v] == [11, 5]  # B, F


def test_fifths_is_third_omitted_stack() -> None:
    cands = voicing_candidates(CMAJ7, "fifths", Lane(48, 84))
    # {root, root+7, root+12}; C at some octave ⇒ [C, G, C]
    for v in cands:
        assert [p - v[0] for p in v] == [0, 7, 12]
        assert v[0] % 12 == 0  # root is C


def test_triad_close_has_three_inversions_per_octave() -> None:
    # triad_close emits root position + 2 inversions (formula order), each
    # octave-placed; shapes come before octaves.
    cands = voicing_candidates(CMAJ7, "triad_close", Lane(48, 84))
    assert cands  # non-empty
    for v in cands:
        assert len(v) == 3
        assert set(p % 12 for p in v) == {0, 4, 7}  # C E G


# --- §8.5 vl_distance --------------------------------------------------------


def test_vl_distance_formula() -> None:
    a = [50, 53, 60]
    b = [43, 47, 53]
    # move·Σ|Δ| = 4·(7+6+7) = 80; top·|60-53| = 4·7 = 28; common {53} ⇒ -3·1.
    assert vl_distance(a, b, DEFAULTS) == 80 + 28 - 3
    assert vl_distance(a, b, DEFAULTS) == 105


def test_vl_distance_is_symmetric_in_magnitude() -> None:
    a, b = [40, 44, 48], [45, 49, 53]
    assert vl_distance(a, b, DEFAULTS) == vl_distance(b, a, DEFAULTS)


def test_vl_distance_common_reward() -> None:
    # Identical voicings: move 0, top 0, common = 3 pitches ⇒ -3·3 = -9.
    v = [48, 52, 55]
    assert vl_distance(v, v, DEFAULTS) == -9


# --- §8.6 ii–V–I golden paths (hand-verified) --------------------------------
#
# Lane (36, 72), default weights, anchor = lane midpoint = 54.
#
# shell3 candidates (index order):
#   Dm7:  [38,41,48] [50,53,60] [62,65,72]
#   G7:   [43,47,53] [55,59,65]
#   Cmaj7:[36,40,47] [48,52,59] [60,64,71]
# Viterbi (emit = |top-54|; trans = 4·Σ|Δ| + 4·|topΔ| - 3·common):
#   best gives optimal path Dm7[0] → G7[0] → Cmaj7[1], total cost 184.


def test_ii_v_i_shell3_optimal_path() -> None:
    lane = Lane(36, 72)

    def cands(spec: ChordSpec) -> list[list[int]]:
        return voicing_candidates(spec, "shell3", lane)

    path = optimal_voicing_path([DM7, G7, CMAJ7], cands, DEFAULTS, anchor=54)
    assert path == [[38, 41, 48], [43, 47, 53], [48, 52, 59]]


def test_ii_v_i_rootless_a_optimal_path() -> None:
    # rootless_a with no 9 ⇒ 3-5-7 stack.
    #   Dm7:  [41,45,48] [53,57,60] [65,69,72]
    #   G7:   [47,50,53] [59,62,65]
    #   Cmaj7:[40,43,47] [52,55,59] [64,67,71]
    # Optimal: Dm7[0] → G7[0] → Cmaj7[1], total cost 184.
    lane = Lane(36, 72)

    def cands(spec: ChordSpec) -> list[list[int]]:
        return voicing_candidates(spec, "rootless_a", lane)

    path = optimal_voicing_path([DM7, G7, CMAJ7], cands, DEFAULTS, anchor=54)
    assert path == [[41, 45, 48], [47, 50, 53], [52, 55, 59]]


def test_default_anchor_recovers_lane_midpoint_when_lane_filled() -> None:
    # The shell3 candidates fill lane (36,72): min note 36, max note 72 ⇒
    # derived anchor = (36+72)//2 = 54 = the explicit anchor above.
    lane = Lane(36, 72)

    def cands(spec: ChordSpec) -> list[list[int]]:
        return voicing_candidates(spec, "shell3", lane)

    explicit = optimal_voicing_path([DM7, G7, CMAJ7], cands, DEFAULTS, anchor=54)
    derived = optimal_voicing_path([DM7, G7, CMAJ7], cands, DEFAULTS)
    assert derived == explicit


# --- §8.6 register-drift: the anchor term prevents downward marching ---------
#
# Synthetic candidates, 3 stages, anchor = 60. Each stage offers two voicings:
#   index0 "low"  = [10+t, 20+t, 30+t]  (tops 30,31,32 — far below anchor)
#   index1 "high" = [40+t, 50+t, 60+t]  (tops 60,61,62 — at the anchor)
# Internal transitions are symmetric (each note +1 per stage ⇒ trans 16 either
# chain), so WITHOUT the drift term the two chains tie and the lowest-index
# (low) chain wins — the path sits far below the anchor. WITH drift the low
# chain pays |top-60| ≈ 28-30 per stage, so the high (anchor) chain wins.


_DRIFT_SPECS = [CMAJ7, CMAJ7, CMAJ7]  # placeholders; the fn ignores their content


def _drift_candidates_fn() -> Callable[[ChordSpec], list[list[int]]]:
    """Per-stage candidates keyed by call order: index0 far below the anchor,
    index1 at the anchor, both drifting +1/stage so transitions are symmetric."""
    counter = {"t": 0}

    def fn(spec: ChordSpec) -> list[list[int]]:
        t = counter["t"]
        counter["t"] += 1
        return [[10 + t, 20 + t, 30 + t], [40 + t, 50 + t, 60 + t]]

    return fn


def test_drift_term_pulls_path_to_anchor() -> None:
    path = optimal_voicing_path(
        _DRIFT_SPECS, _drift_candidates_fn(), DEFAULTS, anchor=60
    )
    assert path == [[40, 50, 60], [41, 51, 61], [42, 52, 62]]
    # every top is within 2 semitones of the anchor
    assert all(abs(v[-1] - 60) <= 2 for v in path)


def test_without_drift_path_marches_far_from_anchor() -> None:
    no_drift = VoicingWeights(move=4, top=4, common=3, drift=0)
    path = optimal_voicing_path(
        _DRIFT_SPECS, _drift_candidates_fn(), no_drift, anchor=60
    )
    # drift=0 ⇒ symmetric chains tie ⇒ lowest-index (low) chain wins.
    assert path == [[10, 20, 30], [11, 21, 31], [12, 22, 32]]
    # ... and its tops are far below the anchor (proves drift did the anchoring).
    assert all(v[-1] <= 32 for v in path)


# --- integer-cost property + determinism -------------------------------------


def test_all_costs_are_int() -> None:
    lane = Lane(36, 84)
    specs = [DM7, G7, CMAJ7]
    voicings: list[list[int]] = []
    for spec in specs:
        voicings.extend(voicing_candidates(spec, "shell3", lane))
    for a in voicings:
        for b in voicings:
            d = vl_distance(a, b, DEFAULTS)
            assert type(d) is int  # not bool, not float
    # default-anchor derivation is integer too
    mid = (36 + 84) // 2
    assert type(mid) is int


def test_optimal_path_is_deterministic() -> None:
    lane = Lane(36, 72)

    def cands(spec: ChordSpec) -> list[list[int]]:
        return voicing_candidates(spec, "shell3", lane)

    p1 = optimal_voicing_path([DM7, G7, CMAJ7], cands, DEFAULTS, anchor=54)
    p2 = optimal_voicing_path([DM7, G7, CMAJ7], cands, DEFAULTS, anchor=54)
    assert p1 == p2


def test_voicing_candidates_is_deterministic() -> None:
    lane = Lane(36, 72)
    assert voicing_candidates(DM7, "drop2", lane) == voicing_candidates(
        DM7, "drop2", lane
    )
