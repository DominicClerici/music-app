"""§9.3 voicing-pass normative goldens (PHASE_5 DoD 6, SESSION_08 T4).

The independent golden transcriber for the comping/pads voicing pass: drives the
REAL pipeline (interpret → form → harmony → arrange) for both worked examples at
seed `1ps9wxb` and asserts the PHASE_5 **§9.3** exact-MIDI spot-checks verbatim —
never read back off code output (ROADMAP §3 golden-value arbitration). The pass
is integer Viterbi: zero draws.

Each spot-check finds the event by chord `symbol` + section (the first such event
in that section) and asserts its mapped voicing.

ARBITRATED (golden-value arbitration, ROADMAP §3 — human sign-off): several §9.3
voicing samples were wrong DERIVED doc values (no engine bug — the frozen Viterbi
DP's true global minimum). §9.3 and these goldens were amended to the engine's
real output; the assertions below now pin the CORRECTED voicings:
   - jazz comping SOLO rootless (rung 3) settle an octave HIGH: Dm9 → C4 E4 F4
     A4, Gm9 → B♭3 D4 F4 A4, B♭13 → D4 F4 A♭4 (3 voices — no 9th, rootless falls
     back to 3-5-♭7), A7♭9 → G3 B♭3 D♭4 E4.
   - pop comping triads settle higher: verse-1 E → G♯3 B3 E4, A → A3 C♯4 E4;
     chorus E → G♯3 B3 E4, B7 → F♯3 B3 D♯4 (C♯m / A were already correct).
  REPRODUCES unchanged: jazz comping HEAD shells (rung 2), pop PADS `fifths`
  (chorus), and all structural invariants (tops ≤ 71, ascending, lane-fitting,
  deterministic).
"""

from __future__ import annotations

import pytest

from trackgen.arrangement import arrange
from trackgen.form.stage import form
from trackgen.harmony.stage import harmony
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.voicing import build_voicing_map
from trackgen.schema.document import Role
from trackgen.schema.ir import (
    ArrangementPlan,
    ChordEvent,
    GenerationPlan,
    HarmonicPlan,
    SongForm,
)
from trackgen.seeds import Rng, stream_rng

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


def _drive(
    params: dict[str, object],
) -> tuple[GenerationPlan, StylePack, SongForm, HarmonicPlan, ArrangementPlan]:
    plan = generate_plan(params)
    pack = resolve_pack(params["styleFamily"])  # type: ignore[arg-type]
    assert pack is not None and pack.forms is not None and pack.progressions is not None
    sf = form(plan, pack.forms)
    hp = harmony(
        plan,
        sf,
        pack.progressions,
        stream_rng(plan.seed.master, plan.seed.overrides, "harmony"),
    )
    ap = arrange(plan, sf, pack, Rng(0))
    return plan, pack, sf, hp, ap


def _voicing_of(
    vmap: dict[int, tuple[int, ...]],
    chords: list[ChordEvent],
    section_id: str,
    symbol: str,
) -> tuple[int, ...]:
    """The voicing of the FIRST event with `symbol` in `section_id`."""
    for ev in chords:
        if ev.section_id == section_id and ev.chord.symbol == symbol:
            return vmap[ev.start_tick]
    raise AssertionError(f"no {symbol!r} event in section {section_id!r}")


# =============================================================================
# §9.3 — jazz comping HEADS, rung 2 shells — REPRODUCES
# =============================================================================


def test_jazz_comping_head_shells() -> None:
    """§9.3 jazz comping heads (lane 46-69, anchor 63) voice shells:
    Dm9 → F3+C4, Gm9 → G3+B♭3+F4, B♭13 → D3+A♭3, A7♭9 → D♭3+G3."""
    _plan, pack, _sf, hp, ap = _drive(_JAZZ)
    chords = list(hp.chords)
    vmap = build_voicing_map("comping", ap, chords, pack)
    assert _voicing_of(vmap, chords, "head-1", "Dm9") == (53, 60)  # F3 C4
    assert _voicing_of(vmap, chords, "head-1", "Gm9") == (55, 58, 65)  # G3 B♭3 F4
    assert _voicing_of(vmap, chords, "head-1", "Bb13") == (50, 56)  # D3 A♭3
    assert _voicing_of(vmap, chords, "head-1", "A7b9") == (49, 55)  # D♭3 G3


# =============================================================================
# §9.3 — jazz comping SOLOS, rung 3 rootless — corrected golden (octave high)
# =============================================================================


def test_jazz_comping_solo_rootless() -> None:
    """§9.3 jazz comping solos (rung 3) rootless, corrected golden:
    Dm9 → C4 E4 F4 A4 (Type B), Gm9 → B♭3 D4 F4 A4 (Type A),
    B♭13 → D4 F4 A♭4 (3 voices — no 9th, 3-5-♭7), A7♭9 → G3 B♭3 D♭4 E4."""
    _plan, pack, _sf, hp, ap = _drive(_JAZZ)
    chords = list(hp.chords)
    vmap = build_voicing_map("comping", ap, chords, pack)
    assert _voicing_of(vmap, chords, "solo-1", "Dm9") == (60, 64, 65, 69)
    assert _voicing_of(vmap, chords, "solo-1", "Gm9") == (58, 62, 65, 69)
    assert _voicing_of(vmap, chords, "solo-1", "Bb13") == (62, 65, 68)
    assert _voicing_of(vmap, chords, "solo-1", "A7b9") == (55, 58, 61, 64)


# =============================================================================
# §9.3 — pop comping verse + chorus triads — corrected golden (register)
# =============================================================================


def test_pop_comping_verse1() -> None:
    """§9.3 pop comping verse-1 (lane 50-71, anchor 65), corrected golden:
    E → G♯3 B3 E4, A → A3 C♯4 E4."""
    _plan, pack, _sf, hp, ap = _drive(_POP)
    chords = list(hp.chords)
    vmap = build_voicing_map("comping", ap, chords, pack)
    assert _voicing_of(vmap, chords, "verse-1", "E") == (56, 59, 64)  # G♯3 B3 E4
    assert _voicing_of(vmap, chords, "verse-1", "A") == (57, 61, 64)  # A3 C♯4 E4


def test_pop_comping_chorus() -> None:
    """§9.3 pop comping chorus set, corrected golden:
    E → G♯3 B3 E4, B7 → F♯3 B3 D♯4, C♯m → G♯3 C♯4 E4, A → A3 C♯4 E4."""
    _plan, pack, _sf, hp, ap = _drive(_POP)
    chords = list(hp.chords)
    vmap = build_voicing_map("comping", ap, chords, pack)
    assert _voicing_of(vmap, chords, "chorus-1", "E") == (56, 59, 64)  # G♯3 B3 E4
    assert _voicing_of(vmap, chords, "chorus-1", "B7") == (54, 59, 63)  # F♯3 B3 D♯4
    assert _voicing_of(vmap, chords, "chorus-1", "C#m") == (56, 61, 64)  # G♯3 C♯4 E4
    assert _voicing_of(vmap, chords, "chorus-1", "A") == (57, 61, 64)  # A3 C♯4 E4


# =============================================================================
# §9.3 — pop pads chorus `fifths` — REPRODUCES
# =============================================================================


def test_pop_pads_chorus_fifths() -> None:
    """§9.3 pop pads (fifths, lane 45-71, stillness weights): chorus
    E → E3 B3 E4, B7 → B2 F♯3 B3, C♯m → C♯3 G♯3 C♯4, A → A2 E3 A3."""
    _plan, pack, _sf, hp, ap = _drive(_POP)
    chords = list(hp.chords)
    vmap = build_voicing_map("pads", ap, chords, pack)
    assert _voicing_of(vmap, chords, "chorus-1", "E") == (52, 59, 64)  # E3 B3 E4
    assert _voicing_of(vmap, chords, "chorus-1", "B7") == (47, 54, 59)  # B2 F♯3 B3
    assert _voicing_of(vmap, chords, "chorus-1", "C#m") == (49, 56, 61)  # C♯3 G♯3 C♯4
    assert _voicing_of(vmap, chords, "chorus-1", "A") == (45, 52, 57)  # A2 E3 A3


# =============================================================================
# §9.3 — all tops ≤ 71 (the C5 ceiling holds structurally) — REPRODUCES
# =============================================================================


def test_all_voicing_tops_below_c5() -> None:
    """§9.3 / ROADMAP invariant 4 — every voiced-role voicing tops out ≤ B4 (71)
    across both worked examples, comping and pads."""
    for params in (_POP, _JAZZ):
        _plan, pack, _sf, hp, ap = _drive(params)
        chords = list(hp.chords)
        for role in ("comping", "pads"):
            if role not in pack.voicing:
                continue
            vmap = build_voicing_map(role, ap, chords, pack)
            for voicing in vmap.values():
                assert voicing[-1] <= 71, (params, role, voicing)


# =============================================================================
# Property — deterministic, lane-fitting, top ≤ 71 over both packs × moods
# =============================================================================


def _voiced_lane(ap: ArrangementPlan, role: Role) -> tuple[int, int]:
    reg = next(e.register for e in ap.entries if e.role == role)
    return reg.low_midi, reg.high_midi


@pytest.mark.parametrize(
    ("style", "role"),
    [
        ("pop_rock", "comping"),
        ("pop_rock", "pads"),
        ("jazz", "comping"),
        ("jazz", "pads"),
    ],
)
def test_voicing_property_matrix(style: str, role: Role) -> None:
    """PHASE_5 §13.6 property — over the pack's supported moods, the voicing pass
    is deterministic (same inputs → identical map, integer Viterbi / zero draws)
    and every emitted voicing is ascending, lane-fitting, and tops ≤ 71."""
    pack = resolve_pack(style)
    assert pack is not None and pack.interpreter is not None
    if role not in pack.voicing:
        pytest.skip(f"{style} has no {role} voicing")

    for mood in pack.interpreter.supported_moods:
        params: dict[str, object] = {
            "styleFamily": style,
            "mood": mood,
            "seed": "1ps9wxb",
        }
        _plan, pk, _sf, hp, ap = _drive(params)
        chords = list(hp.chords)
        low, high = _voiced_lane(ap, role)
        a = build_voicing_map(role, ap, chords, pk)
        b = build_voicing_map(role, ap, chords, pk)
        assert a == b, (style, role, mood)  # deterministic
        for voicing in a.values():
            assert list(voicing) == sorted(voicing), (style, role, mood, voicing)
            assert voicing[0] >= low, (style, role, mood, voicing)
            assert voicing[-1] <= high <= 71, (style, role, mood, voicing)
