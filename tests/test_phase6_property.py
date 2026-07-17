"""PHASE_6 §11.9 whole-phase property matrix (DoD 9, Task T3).

Drives the **fully-wired** pipeline — stage-6 Transitions **and** stage-7
Humanizer, then serialize -> `TrackDocument` — across the pinned §11.9 matrix
(both packs x every supported mood x lengths `[None, 180, 240]` x 25 seeds =
1575 documents) and asserts every §11.9 invariant on every produced document:

1. Fills appear only in legal fill bars.
2. No drum groove event survives inside a rendered fill window.
3. Crash suppression honored for `postchorus`/`breakdown` entries (and a crash
   IS present at every other section entry — the non-vacuous placement path).
4. No note before tick 0 or past song end (doc level, V8-adjacent).
5. Non-drum `midi` untouched by both stages (C5 ceiling: no non-drum note is
   re-pitched or `> 71`; the emitted pitched-midi multiset is a sub-multiset of
   the pre-stage-6 one).
6. Backbeat-class snares (velocity >= 0.7 at back2/back4) never removed/moved.
7. Every document passes V1-V8 (`validate_document == []`).

Plus the two escalation-watch confirmations made **explicit and non-vacuous**:

- **P1 latent (§3.2)** — every rendered fill/crash lands in a section where the
  `drums` role is active. §3.2 places section-boundary devices unconditionally by
  entered type; this asserts no combo injects a fill/crash where drums is
  inactive. A trip is a §3.2 amendment (sign-off), not a silent fix.
- **C-10 (V3 double-hit)** — check 7 runs `validate_document`, whose V3 rule
  catches coincident same-voice drum triggers; the matrix passing V1-V8 is the
  proof that stage-6's crash+kick double-hit guard keeps C-10 unreachable.

The tag-bearing invariants (1/2/3/6 and P1) are asserted on the stage-6 phrase
output (fill/crash *placement* is inherently a stage-6 property, and the C-11
`fill`/`crash` provenance tags are serialize-dropped). Invariant 5 is asserted
on both the stage-6 output and the final doc; the doc-level invariants (4/5/7)
run on the real `TrackDocument`. `_wired()` composes exactly what `generate_track`
does (proven identical in `test_wired_matches_generate_track`) while exposing the
intermediates the phrase-level checks need.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from _stage6_driver import (
    JAZZ,
    POP,
    Stage6Inputs,
    drive,
    stage6_passes,
    track_window,
)
from test_transitions_determinism import (
    _GROOVE_EXCLUDE,
    _LENGTHS,
    _SEEDS,
    _legal_fill_bars,
    _matrix,
)
from trackgen.form.stage import form
from trackgen.humanize.stage import humanize
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.pipeline import generate_track
from trackgen.pipeline.serialize import serialize
from trackgen.pipeline.stubs import sound_design
from trackgen.schema.document import TrackDocument
from trackgen.schema.ir import Phrase
from trackgen.schema.validate import validate_document
from trackgen.transitions._common import BAR
from trackgen.transitions.ending import find_t_last

# Bind the shared matrix knobs so a drift in the stage-6 subset test surfaces
# here rather than silently diverging (§11.9 pins 25 seeds x 3 lengths).
assert len(_SEEDS) == 25
assert _LENGTHS == [None, 180, 240]
# Both reference packs present with a non-empty mood set — guards against a
# silent matrix shrink (§11.9 pins "every pack x every supported mood").
assert {p["styleFamily"] for p in _matrix()} == {"pop_rock", "jazz"}

_PITCHED_ROLES = ("bass", "comping", "pads")
_C5_CEILING = 71  # PHASE_1 D14 / ROADMAP invariant 4: soloist owns above ~C5.


def _wired(
    params: dict[str, object],
) -> tuple[Stage6Inputs, list[Phrase], list[Phrase], TrackDocument]:
    """Run the fully-wired pipeline, exposing the intermediates §11.9 needs.

    Composes exactly `generate_track`'s body (transitions -> humanize ->
    sound_design -> serialize; see `test_wired_matches_generate_track`) while
    returning `(inputs, post_6b, stage6_final, document)` so the tag-bearing
    checks can inspect the pre-serialize phrases and the doc-level checks the
    real `TrackDocument`.
    """
    inp = drive(params)
    post_6b, final = stage6_passes(inp)
    humanized, tempo_events = humanize(final, inp.sf, inp.plan)
    patches = sound_design(inp.plan, inp.pack)
    doc = serialize(
        inp.plan, inp.sf, humanized, patches, tempo_events=tempo_events, params=params
    )
    return inp, post_6b, final, doc


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_wired_matches_generate_track(params: dict[str, object]) -> None:
    """`_wired()` reproduces `generate_track` byte-for-byte, so every doc-level
    §11.9 assertion below is an assertion on the fully-wired pipeline output."""
    _, _, _, doc = _wired(params)
    assert doc.model_dump() == generate_track(params).model_dump()


def test_crash_suppression_class_absent_in_v1_forms() -> None:
    """§11.9 check 3 reachability, made explicit (non-vacuous N/A).

    The crash-suppression classes (`postchorus`/`breakdown`) never appear as an
    entered section in either v1 reference pack across the whole matrix, so the
    suppression branch of `test_phase6_property_matrix` is N/A — its crash
    coverage rides entirely on the *crash-present-at-every-other-entry* branch.
    This scan asserts that fact loudly: if a future form ever introduces one of
    those entered types, this fails and forces the suppression path to be
    exercised for real rather than silently skipped.
    """
    entered_suppress_types: set[str] = set()
    for params in _matrix():
        plan = generate_plan(params)
        style_family = params["styleFamily"]
        assert isinstance(style_family, str)
        pack = resolve_pack(style_family)
        assert pack is not None and pack.forms is not None
        sf = form(plan, pack.forms)
        for idx, sec in enumerate(sf.sections):
            if idx > 0 and sec.type in ("postchorus", "breakdown"):
                entered_suppress_types.add(sec.type)
    assert entered_suppress_types == set(), (
        "postchorus/breakdown appeared as an entered section — crash suppression "
        "is now reachable and must be asserted, not treated as N/A: "
        f"{sorted(entered_suppress_types)}"
    )


def _section_of_bar(sf: Any, bar: int) -> Any:
    for s in sf.sections:
        if s.start_bar <= bar < s.start_bar + s.length_bars:
            return s
    return None


@pytest.mark.parametrize(
    "params",
    _matrix(),
    ids=lambda p: (
        f"{p['styleFamily']}-{p.get('mood')}-{p.get('maxLengthSec')}-{p['seed']}"
    ),
)
def test_phase6_property_matrix(params: dict[str, object]) -> None:
    """DoD 9 / §11.9 over the whole fully-wired pipeline, one document per combo."""
    inp, post_6b, final, doc = _wired(params)
    sf = inp.sf
    legal = _legal_fill_bars(sf)
    t_last_bar = find_t_last(inp.hp) // BAR
    drums_active = {
        e.section_id for e in inp.ap.entries if e.role == "drums" and e.active
    }

    # ---- (1) Fills only in legal fill bars (phrase level; tags intact). --------
    for p in final:
        if p.role != "drums":
            continue
        for n in p.notes:
            if "fill" in n.tags:
                assert n.ticks // BAR in legal, (params, "fill-bar", n.ticks)

    # ---- (2) No groove drum event inside a rendered fill window. ---------------
    # In any bar holding a fill, every groove (non fill/var/crash/hold) hit falls
    # before the window (beat-floor of the earliest fill event in that bar).
    for p in final:
        if p.role != "drums":
            continue
        by_bar: dict[int, list[Any]] = {}
        for n in p.notes:
            by_bar.setdefault(n.ticks // BAR, []).append(n)
        for notes in by_bar.values():
            fill_pos = [n.ticks % BAR for n in notes if "fill" in n.tags]
            if not fill_pos:
                continue
            window_lo = (min(fill_pos) // 480) * 480
            for n in notes:
                if not (_GROOVE_EXCLUDE & set(n.tags)):
                    assert n.ticks % BAR < window_lo, (
                        params,
                        "groove-in-window",
                        p.track_id,
                        n.ticks,
                    )

    # ---- (3) Crash suppression for postchorus/breakdown; present elsewhere. ----
    secs = sf.sections
    for i in range(len(secs) - 1):
        entered = secs[i + 1]
        tick = entered.start_bar * BAR
        crash_here = track_window(final, "crash", tick, tick + 1)
        if entered.type in ("postchorus", "breakdown"):
            assert crash_here == [], (params, "crash-suppress", entered.id)
        elif entered.start_bar < t_last_bar:
            assert len(crash_here) == 1, (params, "crash-present", entered.id)

    # ---- (P1 latent, §3.2) Every rendered fill/crash sits where drums active. --
    for p in final:
        if p.role != "drums":
            continue
        for n in p.notes:
            if "fill" in n.tags or "crash" in n.tags:
                sec = _section_of_bar(sf, n.ticks // BAR)
                assert sec is not None, (params, "P1-no-section", n.ticks)
                assert sec.id in drums_active, (
                    params,
                    "P1-drums-inactive",
                    sec.id,
                    n.tags,
                )

    # ---- (4) No note before tick 0 or past song end (doc level, V8-adjacent). --
    song_end = doc.sections[-1].end_tick
    for track in doc.tracks:
        for ev in track.notes:
            assert ev.ticks >= 0, (params, "note<0", track.id, ev.ticks)
            assert ev.ticks + ev.duration_ticks <= song_end, (
                params,
                "note-past-end",
                track.id,
                ev.ticks,
            )

    # ---- (5) Non-drum midi untouched by both stages (C5 ceiling). --------------
    # The pitched-midi multiset never re-pitches or gains pitch across EITHER
    # stage. Assert it against the pre-stage-6 generator output at three points:
    # the stage-6 output (transitions), and the final `TrackDocument` (transitions
    # AND humanize AND serialize), each a sub-multiset of the original. The final
    # doc check closes the "both stages" clause directly rather than leaning on
    # humanize's separately-proven midi invariance (DoD 7).
    for role in _PITCHED_ROLES:
        initial = Counter(
            n.midi for p in inp.phrases if p.role == role for n in p.notes
        )
        stage6_emitted = Counter(
            n.midi for p in final if p.role == role for n in p.notes
        )
        doc_emitted = Counter(
            ev.midi for t in doc.tracks if t.role == role for ev in t.notes
        )
        for label, emitted in (("stage6", stage6_emitted), ("doc", doc_emitted)):
            for midi, count in emitted.items():
                assert midi is not None and midi <= _C5_CEILING, (
                    params,
                    "C5-ceiling",
                    label,
                    role,
                    midi,
                )
                assert initial[midi] >= count, (
                    params,
                    "not-submultiset",
                    label,
                    role,
                    midi,
                )

    # ---- (6) Backbeat-class snares never removed or moved by mutation. ---------
    def backbeats(phrases: list[Phrase]) -> set[tuple[int, float]]:
        return {
            (n.ticks, round(n.velocity, 3))
            for p in phrases
            if p.track_id == "snare"
            for n in p.notes
            if n.velocity >= 0.7
            and n.ticks % BAR in (480, 1440)
            and not (_GROOVE_EXCLUDE & set(n.tags))
        }

    assert backbeats(post_6b) <= backbeats(final), (params, "backbeat-moved")

    # ---- (7) Every document passes V1-V8 (C-10: V3 double-hit stays clean). ----
    assert validate_document(doc) == [], (params, "validate")
