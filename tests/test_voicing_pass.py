"""PHASE_5 §6.4/§6.5 comping/pads voicing pass (T1) — mechanism + invariants.

Proves the `build_voicing_map` machinery: candidate concatenation in class order,
the `lane.high − 6` anchor, per-role weights, `start_tick` keys, and the structural
invariants (ascending, lane-fitting, top ≤ lane.high). Also the C-04 confirmations
(keyless `quartal` = perfect fourths; triads never hit a 4-voice class) and the
cardinality-padding boundary. The exact §9.3 MIDI goldens are T4's independent job
and are deliberately NOT transcribed here.
"""

import pytest

from trackgen.packs.loader import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.voicing import build_voicing_map
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementEntry,
    ArrangementPlan,
    ChordEvent,
    ChordSpec,
    EventScale,
    Register,
)
from trackgen.theory.voicing import (
    Lane,
    VoicingWeights,
    _pad_to_equal,
    optimal_voicing_path,
    voicing_candidates,
)

_TICKS_PER_BAR = 1920


def _pack(name: str) -> StylePack:
    pack = resolve_pack(name)
    assert pack is not None, f"{name} did not resolve"
    return pack


def _spec(
    root_pc: int, quality: str, symbol: str, exts: list[str] | None = None
) -> ChordSpec:
    return ChordSpec(
        root_pc=root_pc,
        quality=quality,  # type: ignore[arg-type]
        extensions=exts or [],
        symbol=symbol,
    )


def _events(
    specs: list[ChordSpec], section_id: str = "A", start: int = 0
) -> list[ChordEvent]:
    """One bar-long event per spec, laid end to end in `section_id`."""
    out: list[ChordEvent] = []
    tick = start
    for spec in specs:
        out.append(
            ChordEvent(
                start_tick=tick,
                duration_ticks=_TICKS_PER_BAR,
                section_id=section_id,
                chord=spec,
                scale=EventScale(root_pc=spec.root_pc, name="dorian"),
                function="T",
            )
        )
        tick += _TICKS_PER_BAR
    return out


def _arrangement(
    role: Role, register: Register, section_rungs: dict[str, int]
) -> ArrangementPlan:
    return ArrangementPlan(
        entries=[
            ArrangementEntry(
                section_id=sid,
                role=role,
                active=True,
                intensity=rung,
                density_budget=0.6,
                register=register,
            )
            for sid, rung in section_rungs.items()
        ]
    )


def _manual_map(
    role: Role,
    arrangement: ArrangementPlan,
    chords: list[ChordEvent],
    pack: StylePack,
    weights: VoicingWeights,
    anchor: int,
) -> dict[int, tuple[int, ...]]:
    """Independent replica: concatenate `voicing_candidates` in class order per
    event, then run the committed optimizer with the given weights/anchor. Pins
    the weight tuple and anchor literals the module must use."""
    classes = pack.voicing[role].classes
    reg = next(e for e in arrangement.entries if e.role == role).register
    lane = Lane(reg.low_midi, reg.high_midi)
    rung_of = {e.section_id: e.intensity for e in arrangement.entries if e.role == role}
    stages: dict[int, list[list[int]]] = {}
    for ev in chords:
        cands: list[list[int]] = []
        for cls in classes[rung_of[ev.section_id]]:
            cands.extend(voicing_candidates(ev.chord, cls, lane))
        stages[id(ev.chord)] = cands

    def fn(s: ChordSpec) -> list[list[int]]:
        return stages[id(s)]

    path = optimal_voicing_path([e.chord for e in chords], fn, weights, anchor=anchor)
    return {e.start_tick: tuple(v) for e, v in zip(chords, path, strict=True)}


# The §9.3 jazz ii–V/turnaround specimens (used for mechanism, not for MIDI goldens).
_JAZZ = [
    _spec(2, "min7", "Dm9", ["9"]),
    _spec(7, "min7", "Gm9", ["9"]),
    _spec(10, "dom7", "Bb13", ["13"]),
    _spec(9, "dom7", "A7b9", ["b9"]),
]


# --- keys + reproduction (concatenation order, anchor, weights) ---------------


def test_map_keyed_by_start_tick() -> None:
    pack = _pack("jazz")
    chords = _events(_JAZZ)
    arr = _arrangement("comping", Register(low_midi=46, high_midi=69), {"A": 2})
    vmap = build_voicing_map("comping", arr, chords, pack)
    assert set(vmap) == {e.start_tick for e in chords}


def test_comping_reproduces_reference_dp() -> None:
    """Comping map = the optimizer over class-order-concatenated candidates with
    weights (4,4,3,1) and anchor lane.high−6."""
    pack = _pack("jazz")
    chords = _events(_JAZZ)
    reg = Register(low_midi=46, high_midi=69)
    arr = _arrangement("comping", reg, {"A": 2})
    got = build_voicing_map("comping", arr, chords, pack)
    want = _manual_map(
        "comping", arr, chords, pack, VoicingWeights(4, 4, 3, 1), reg.high_midi - 6
    )
    assert got == want


def test_pads_uses_pads_weights() -> None:
    """Pads map = the optimizer with the stillness weights (4,2,5,1)."""
    pack = _pack("pop_rock")
    chords = _events(
        [_spec(4, "maj", "E"), _spec(9, "maj", "A"), _spec(11, "dom7", "B7")]
    )
    reg = Register(low_midi=45, high_midi=71)
    arr = _arrangement("pads", reg, {"A": 3})
    got = build_voicing_map("pads", arr, chords, pack)
    want = _manual_map(
        "pads", arr, chords, pack, VoicingWeights(4, 2, 5, 1), reg.high_midi - 6
    )
    assert got == want


def test_anchor_is_lane_high_minus_6() -> None:
    """A wide lane where octave placement is anchor-driven: the pass settles the
    top near lane.high−6, differing from any lower-anchor run."""
    pack = _pack("pop_rock")
    chords = _events([_spec(0, "maj", "C")])  # triad_close at rung 1
    reg = Register(low_midi=48, high_midi=84)
    arr = _arrangement("comping", reg, {"A": 1})
    got = build_voicing_map("comping", arr, chords, pack)
    high = _manual_map("comping", arr, chords, pack, VoicingWeights(4, 4, 3, 1), 78)
    low = _manual_map("comping", arr, chords, pack, VoicingWeights(4, 4, 3, 1), 48)
    assert got == high  # anchor == lane.high − 6 == 78
    assert got != low  # a different anchor picks a different octave


def test_weights_tuple_is_non_vacuous() -> None:
    """The comping/pads weight tuples are not interchangeable: on a shared class
    they steer the optimizer to different voicings (so the per-role equalities
    above are meaningful, not coincidental)."""
    lane = Lane(40, 79)
    specs = [
        _spec(2, "min7", "Dm7"),
        _spec(7, "dom7", "G7"),
        _spec(0, "maj7", "Cmaj7"),
        _spec(9, "min7", "Am7"),
        _spec(5, "maj7", "Fmaj7"),
        _spec(11, "min7b5", "Bm7b5"),
        _spec(4, "dom7", "E7"),
    ]
    cands = {id(s): voicing_candidates(s, "rootless_a", lane) for s in specs}

    def fn(s: ChordSpec) -> list[list[int]]:
        return cands[id(s)]

    comping = optimal_voicing_path(specs, fn, VoicingWeights(4, 4, 3, 1), anchor=63)
    pads = optimal_voicing_path(specs, fn, VoicingWeights(4, 2, 5, 1), anchor=63)
    assert comping != pads


# --- structural invariants ----------------------------------------------------


def _assert_in_lane(vmap: dict[int, tuple[int, ...]], lane: Register) -> None:
    for voicing in vmap.values():
        assert list(voicing) == sorted(voicing), "voicing must be ascending"
        assert voicing[0] >= lane.low_midi
        assert voicing[-1] <= lane.high_midi


@pytest.mark.parametrize(
    ("pack_name", "role", "rung", "reg"),
    [
        ("jazz", "comping", 2, Register(low_midi=46, high_midi=69)),
        ("jazz", "comping", 3, Register(low_midi=46, high_midi=69)),
        ("pop_rock", "comping", 2, Register(low_midi=50, high_midi=71)),
        ("pop_rock", "pads", 3, Register(low_midi=45, high_midi=71)),
        ("jazz", "pads", 1, Register(low_midi=41, high_midi=69)),
    ],
)
def test_voicings_ascending_and_lane_fitting(
    pack_name: str, role: Role, rung: int, reg: Register
) -> None:
    """Every emitted voicing is ascending, within the lane, top ≤ lane.high
    (≤ 71 for the reference lanes — the C5 ceiling, ROADMAP invariant 4)."""
    pack = _pack(pack_name)
    chords = _events(_JAZZ + [_spec(0, "maj", "C"), _spec(4, "min7", "Em7")])
    arr = _arrangement(role, reg, {"A": rung})
    vmap = build_voicing_map(role, arr, chords, pack)
    _assert_in_lane(vmap, reg)
    assert max(v[-1] for v in vmap.values()) <= 71


def test_determinism_zero_draws() -> None:
    """Same inputs → identical map (integer Viterbi, no randomness)."""
    pack = _pack("jazz")
    chords = _events(_JAZZ)
    arr = _arrangement("comping", Register(low_midi=46, high_midi=69), {"A": 2})
    a = build_voicing_map("comping", arr, chords, pack)
    b = build_voicing_map("comping", arr, chords, pack)
    assert a == b


# --- section → rung resolution + cardinality padding --------------------------


def test_section_rung_drives_candidate_classes() -> None:
    """An event's rung comes from its section's intensity: the same chord in a
    rung-2 section (jazz shells, ≤ 3 voices) vs a rung-3 section (rootless, up to
    4 voices) draws from different classes."""
    pack = _pack("jazz")
    reg = Register(low_midi=46, high_midi=69)
    dm9 = _spec(2, "min7", "Dm9", ["9"])
    low = _events([dm9], section_id="A", start=0)
    high = _events([dm9], section_id="B", start=_TICKS_PER_BAR)
    chords = low + high
    arr = _arrangement("comping", reg, {"A": 2, "B": 3})
    vmap = build_voicing_map("comping", arr, chords, pack)
    assert len(vmap[low[0].start_tick]) <= 3  # shell2/shell3
    assert len(vmap[high[0].start_tick]) == 4  # rootless_a on a min9 → 3-5-7-9


def test_cardinality_padding_boundary() -> None:
    """A shell2 (2-voice) → rootless_a (4-voice) boundary across a section change:
    the padded transition is internal to the optimizer — assert only that the
    path exists and every voicing is in-lane."""
    pack = _pack("jazz")
    reg = Register(low_midi=46, high_midi=69)
    a = _events([_spec(2, "min7", "Dm9", ["9"])], section_id="A", start=0)
    b = _events([_spec(7, "min7", "Gm9", ["9"])], section_id="B", start=_TICKS_PER_BAR)
    chords = a + b
    arr = _arrangement("comping", reg, {"A": 2, "B": 3})
    vmap = build_voicing_map("comping", arr, chords, pack)
    assert len(vmap) == 2
    _assert_in_lane(vmap, reg)
    # rung 2 shell (2 voices) meets rung 3 rootless (4 voices) at the boundary.
    assert len(vmap[a[0].start_tick]) == 2
    assert len(vmap[b[0].start_tick]) == 4


def test_pad_to_equal_pads_with_own_top_pitch() -> None:
    """§6.4 caller policy (PHASE_5 amendment 10): the DP pads the shorter voicing
    with its own **top** pitch (not its bottom) so `vl_distance` sees equal
    cardinality. Pins the value directly — the §9.3 boundary goldens only
    constrain it indirectly. Flipping the pad to `a[0]` would fail this."""
    short, long = [60, 64], [58, 62, 65, 69]
    assert _pad_to_equal(short, long) == ([60, 64, 64, 64], [58, 62, 65, 69])
    # Symmetric: whichever side is shorter is padded with its own top.
    assert _pad_to_equal(long, short) == ([58, 62, 65, 69], [60, 64, 64, 64])
    # Equal cardinality is unchanged.
    assert _pad_to_equal([48, 55], [50, 57]) == ([48, 55], [50, 57])


# --- C-04 confirmations -------------------------------------------------------


def test_quartal_is_perfect_fourths() -> None:
    """C-04 #1: keyless `quartal` stacks perfect fourths [0,5,10,15]. Jazz pads
    are the only quartal user (dormant in v1, layersMax 3)."""
    pack = _pack("jazz")
    chords = _events(_JAZZ)
    reg = Register(low_midi=41, high_midi=69)
    arr = _arrangement("pads", reg, {"A": 2})
    vmap = build_voicing_map("pads", arr, chords, pack)
    for voicing in vmap.values():
        assert len(voicing) == 4
        root = voicing[0]
        assert list(voicing) == [root, root + 5, root + 10, root + 15]


def test_triad_never_yields_four_voices() -> None:
    """C-04 #3: pop comping's triad_close/triad_open/shell3 classes never route a
    triad into a 4-note seventh-chord class."""
    pack = _pack("pop_rock")
    triads = [_spec(4, "maj", "E"), _spec(9, "maj", "A"), _spec(1, "min", "C#m")]
    reg = Register(low_midi=50, high_midi=71)
    for rung in (1, 2, 3, 4):
        arr = _arrangement("comping", reg, {"A": rung})
        vmap = build_voicing_map("comping", arr, _events(triads), pack)
        for voicing in vmap.values():
            assert len(voicing) <= 3


# --- error surface ------------------------------------------------------------


def test_empty_candidates_raises() -> None:
    """The concatenation across classes must be non-empty; an impossible lane
    (too narrow for any placement) raises clearly rather than silently."""
    pack = _pack("pop_rock")
    chords = _events([_spec(0, "maj7", "Cmaj7")])  # shell3 span 11 > lane span 5
    arr = _arrangement("comping", Register(low_midi=48, high_midi=53), {"A": 4})
    with pytest.raises(ValueError):
        build_voicing_map("comping", arr, chords, pack)


def test_unknown_role_rejected() -> None:
    pack = _pack("pop_rock")
    chords = _events([_spec(0, "maj", "C")])
    arr = _arrangement("comping", Register(low_midi=50, high_midi=71), {"A": 2})
    with pytest.raises(ValueError):
        build_voicing_map("bass", arr, chords, pack)
