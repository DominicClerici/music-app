"""PHASE_6 §7.2 jazz ritard-table golden (Task T4, DoD 6).

The **independent golden arbiter** for the stage-7 ritard curve. The eleven
printed anchors and the two endpoints are transcribed from PHASE_6 **§7.2** (the
"Ending (ritard + HOLD)" tempo table) — the pinned design text — NOT read back
off the engine. The engine (`ritard_events`, and `humanize`'s 2nd return) is then
driven on the real chained pipeline (`_stage6_driver`, seed `1ps9wxb`) and
asserted to reproduce them.

On any divergence the rule is: do NOT tune — mark `@pytest.mark.xfail(strict=True)`
and escalate to the orchestrator (the C-09 precedent; the §7.2 table is the
arbitration-risk surface). **This session: every §7.2 anchor reproduced; there is
no xfail.**

The doc prints only 11 of the 39 events; the 28 intermediate values are
engine-derived (curve samples between the printed anchors). Per ROADMAP §3
arbitration rule 3, the full 39-event list is pinned below as the committed
regression fixture — locked, not transcribed — while the 11 anchors + the
endpoints + the monotone/floor properties independently constrain it.
"""

from __future__ import annotations

from _stage6_driver import JAZZ, POP, drive, stage6_final
from trackgen.humanize.ritard import ritard_events
from trackgen.humanize.stage import humanize

BAR = 1920
_JAZZ_BASE_BPM = 69.0

# --- transcribed from PHASE_6 §7.2 -------------------------------------------

# The eleven printed (rel_tick -> bpm) anchors of the §7.2 tempo table.
_ANCHORS: dict[int, float] = {
    240: 68.5,
    480: 67.9,
    960: 66.8,
    1920: 64.5,
    2880: 62.1,
    3840: 59.4,
    4800: 56.4,
    5760: 53.1,
    6720: 49.3,
    7200: 47.2,
    7560: 45.5,
}
_FIRST = (240, 68.5)  # §7.2: first event `{+240, 68.5}`.
_LAST = (7560, 45.5)  # §7.2: reaches `{+7560, 45.5}` = 0.659 × 69.

# The full 39-event list the faithful engine emits, as (rel_tick, bpm). The 11
# §7.2-printed anchors appear verbatim; the other 28 are engine-derived curve
# samples, locked here as the committed regression fixture (ROADMAP §3 rule 3).
_FULL_RELS: list[tuple[int, float]] = [
    (240, 68.5),
    (480, 67.9),
    (720, 67.4),
    (960, 66.8),
    (1200, 66.3),
    (1440, 65.7),
    (1680, 65.1),
    (1920, 64.5),
    (2160, 63.9),
    (2400, 63.3),
    (2640, 62.7),
    (2880, 62.1),
    (3120, 61.4),
    (3360, 60.8),
    (3600, 60.1),
    (3840, 59.4),
    (4080, 58.7),
    (4320, 57.9),
    (4560, 57.2),
    (4800, 56.4),
    (5040, 55.6),
    (5280, 54.8),
    (5520, 54.0),
    (5760, 53.1),
    (5880, 52.7),
    (6000, 52.2),
    (6120, 51.8),
    (6240, 51.3),
    (6360, 50.8),
    (6480, 50.3),
    (6600, 49.8),
    (6720, 49.3),
    (6840, 48.8),
    (6960, 48.3),
    (7080, 47.7),
    (7200, 47.2),
    (7320, 46.6),
    (7440, 46.1),
    (7560, 45.5),
]


def _jazz_tag_start() -> int:
    """Derive the tag start from the form geometry (§5.7): `endTick − tagBars ×
    BAR` for the final section's ritard tag. Asserted == 115200 (bars 60–64)."""
    inp = drive(JAZZ)
    final = inp.sf.sections[-1]
    assert final.ending is not None and final.ending.close == "ritard"
    tag_bars = final.ending.tag_bars if final.ending.tag_bars > 0 else 1
    end_tick = (final.start_bar + final.length_bars) * BAR
    tag_start = end_tick - tag_bars * BAR
    assert tag_start == 115200  # §7.2: tag = bars 60–64 (ticks 115200–122880).
    return tag_start


def test_jazz_ritard_length_and_tag_start() -> None:
    """§7.2 / §5.7: the jazz ritard emits **39** events over the 4-bar tag; the
    tag starts at tick 115200 (bars 60–64), derived from the form geometry."""
    inp = drive(JAZZ)
    events = ritard_events(inp.sf, inp.plan)
    assert len(events) == 39
    assert _jazz_tag_start() == 115200


def test_jazz_ritard_printed_anchors() -> None:
    """§7.2: each of the eleven printed `(rel → bpm)` anchors reproduces exactly
    at absolute tick `tag_start + rel`."""
    inp = drive(JAZZ)
    tag_start = _jazz_tag_start()
    events = ritard_events(inp.sf, inp.plan)
    by_tick = {e.ticks: e.bpm for e in events}
    for rel, bpm in _ANCHORS.items():
        assert by_tick.get(tag_start + rel) == bpm, (rel, bpm, "§7.2 anchor")


def test_jazz_ritard_endpoints() -> None:
    """§7.2: first event `(+240, 68.5)`, last event `(+7560, 45.5)` (= 0.659 ×
    69, the tag's last 16th-note sample)."""
    inp = drive(JAZZ)
    tag_start = _jazz_tag_start()
    events = ritard_events(inp.sf, inp.plan)
    assert (events[0].ticks - tag_start, events[0].bpm) == _FIRST
    assert (events[-1].ticks - tag_start, events[-1].bpm) == _LAST


def test_jazz_ritard_monotone_and_floor() -> None:
    """§5.7 / §11.6: bpm strictly decreasing; every value stays above 0.5 × base
    (tempo never approaches 0 — the stop is the HOLD release)."""
    inp = drive(JAZZ)
    events = ritard_events(inp.sf, inp.plan)
    bpms = [e.bpm for e in events]
    assert all(a > b for a, b in zip(bpms, bpms[1:], strict=False))
    assert all(b > 0.5 * _JAZZ_BASE_BPM for b in bpms)


def test_jazz_ritard_full_list_fixture() -> None:
    """Regression lock: the full 39-event list (11 §7.2 anchors + 28
    engine-derived curve samples) at absolute ticks (ROADMAP §3 rule 3)."""
    inp = drive(JAZZ)
    tag_start = _jazz_tag_start()
    events = ritard_events(inp.sf, inp.plan)
    got = [(e.ticks, e.bpm) for e in events]
    expected = [(tag_start + rel, bpm) for rel, bpm in _FULL_RELS]
    assert got == expected


def test_humanize_returns_ritard_for_jazz_and_empty_for_pop() -> None:
    """§6 / §5.7: `humanize`'s 2nd return equals `ritard_events` for the jazz
    ritard close, and is `[]` for the pop cold close (no tempo events)."""
    jazz = drive(JAZZ)
    s6_jazz = stage6_final(jazz)
    _, tempos_jazz = humanize(s6_jazz, jazz.sf, jazz.plan)
    assert [(t.ticks, t.bpm) for t in tempos_jazz] == [
        (t.ticks, t.bpm) for t in ritard_events(jazz.sf, jazz.plan)
    ]

    pop = drive(POP)
    s6_pop = stage6_final(pop)
    _, tempos_pop = humanize(s6_pop, pop.sf, pop.plan)
    assert tempos_pop == []
