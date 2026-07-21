"""PHASE_6 §11.9 whole-phase property matrix (DoD 9, Task T3).

Drives the **fully-wired** pipeline — stage-6 Transitions **and** stage-7
Humanizer, then serialize -> `TrackDocument` — across the pinned §11.9 matrix
(**every registered pack** x every supported mood x lengths `[None, 180, 240]` x
25 seeds = 3375 documents; PHASE_8 §14.9 widened the pack dimension from the two
reference packs to all five) and asserts every §11.9 invariant on every produced
document:

1. Fills appear only in legal fill bars.
2. No drum groove event survives inside a rendered fill window.
3. The §3.2 device policy honored at `postchorus`/`breakdown` entries — no entry
   crash, no fill in the boundary's fill bar, and (for `breakdown`) the §3.5
   dropout truncation — and a crash IS present at every other section entry (the
   non-vacuous placement path). Both branches now run for real: `chill_lofi` and
   `fusion_jazz` enter `breakdown`, which the two v1 reference packs never did.
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

from _packmatrix import LENGTHS_RENDER, PACKS, SEEDS_25
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
    _legal_fill_bars,
    _matrix,
)
from trackgen.form.stage import form
from trackgen.humanize.stage import humanize
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.pipeline import generate_track
from trackgen.pipeline.serialize import serialize
from trackgen.schema.document import TrackDocument
from trackgen.schema.ir import Phrase
from trackgen.schema.validate import validate_document
from trackgen.seeds import Rng
from trackgen.sound.stage import sound_design
from trackgen.transitions._common import BAR
from trackgen.transitions.ending import find_t_last

# Bind the shared matrix knobs so a drift in the stage-6 subset test surfaces
# here rather than silently diverging (§11.9 pins 25 seeds x 3 lengths).
assert len(SEEDS_25) == 25
assert LENGTHS_RENDER == (None, 180, 240)
# Every registered pack present with a non-empty mood set — guards against a
# silent matrix shrink (§11.9 pins "every pack x every supported mood", widened
# from the two reference packs to all five by PHASE_8 §14.9).
assert {p["styleFamily"] for p in _matrix()} == set(PACKS)

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
    assert inp.pack.timbres is not None
    design = sound_design(inp.plan, inp.pack.timbres, Rng(0))
    doc = serialize(
        inp.plan, inp.sf, humanized, design, tempo_events=tempo_events, params=params
    )
    return inp, post_6b, final, doc


@pytest.mark.parametrize("params", [POP, JAZZ], ids=["pop", "jazz"])
def test_wired_matches_generate_track(params: dict[str, object]) -> None:
    """`_wired()` reproduces `generate_track` byte-for-byte, so every doc-level
    §11.9 assertion below is an assertion on the fully-wired pipeline output."""
    _, _, _, doc = _wired(params)
    assert doc.model_dump() == generate_track(params).model_dump()


# --- §3.2 crash-suppression reachability, pinned per pack ---------------------

_SUPPRESS_TYPES = ("postchorus", "breakdown")

_ENTERED_SUPPRESS_TYPES: dict[str, frozenset[str]] = {
    "pop_rock": frozenset(),
    "jazz": frozenset(),
    "blues": frozenset(),
    "chill_lofi": frozenset({"breakdown"}),
    "fusion_jazz": frozenset({"breakdown"}),
}
"""Which §3.2 suppression classes each pack actually *enters*, measured.

Pinned per pack and asserted for **equality**, never `>=`/`<=` — the set is
load-bearing in both directions. A pack gaining an entered suppression type must
route through the suppression branch below (and be recorded here); a pack losing
one means its coverage of that branch silently evaporated.

Three of the five packs reach no suppression class at all, so their §11.9 check-3
coverage rides entirely on the *crash-present-at-every-other-entry* branch (the
original v1 situation). `chill_lofi` and `fusion_jazz` both enter `breakdown` —
`postchorus` remains entered by no registered form, so the §3.5 dropout path is
the only suppression device v1 exercises for real. Per-pack sets rather than a
universal, per CAVEATS C-22/C-23/C-25/C-28: structural unreachability is normal
and legitimate here, so a universal ("every pack enters a suppression class")
would fail on three packs by design.
"""


def test_entered_suppression_pins_cover_exactly_the_registry() -> None:
    """The per-pack pin table and the pack registry name the same packs.

    The scan below is parameterized per pack, so a pack missing from the table
    would `KeyError` — but a *stale* entry for a de-registered pack would go
    unnoticed. This closes that direction; the two together are the dict
    equality the single-body version used to assert."""
    assert set(_ENTERED_SUPPRESS_TYPES) == set(PACKS), (
        sorted(_ENTERED_SUPPRESS_TYPES),
        PACKS,
    )


@pytest.mark.parametrize("pack_id", PACKS)
def test_entered_suppression_classes_are_pinned_per_pack(pack_id: str) -> None:
    """§11.9 check 3 reachability, measured per pack and pinned.

    Until PHASE_8's pack expansion no registered form entered a `postchorus` or
    `breakdown`, so the suppression branch of `test_phase6_property_matrix` was
    genuinely N/A and this scan asserted the empty set. `chill_lofi` and
    `fusion_jazz` changed that: both enter `breakdown`, so the branch is live and
    asserts for real (see `_assert_suppressed_entry`). Equality here keeps the
    fact honest in both directions — a new entered type fails loudly and forces
    the same treatment, and a vanished one fails rather than quietly dropping the
    only coverage the suppression branch has.

    Parameterized per pack rather than scanning all 3375 cells in one body: the
    single-body version was the slowest test in the suite, and under `pytest
    -n auto` the gate's wall time can never fall below its longest single test.
    Splitting is semantics-preserving — each pack's entered set is derived only
    from that pack's own cells, and equality per pack over a key set proved
    exhaustive above is the same assertion as equality over the whole dict.
    """
    entered: set[str] = set()
    for params in _matrix():
        if params["styleFamily"] != pack_id:
            continue
        pack = resolve_pack(pack_id)
        assert pack is not None and pack.forms is not None
        sf = form(generate_plan(params), pack.forms)
        for idx, sec in enumerate(sf.sections):
            if idx > 0 and sec.type in _SUPPRESS_TYPES:
                entered.add(sec.type)

    assert frozenset(entered) == _ENTERED_SUPPRESS_TYPES[pack_id], (
        pack_id,
        sorted(entered),
        sorted(_ENTERED_SUPPRESS_TYPES[pack_id]),
        "entered suppression classes diverged from the pinned per-pack set — a "
        "class newly entered must be asserted through the suppression branch, "
        "and one no longer entered means that branch lost its only coverage",
    )


def _assert_suppressed_entry(
    params: dict[str, object],
    final: list[Phrase],
    outgoing: Any,
    entered: Any,
) -> None:
    """The §3.2 device policy for an entered suppression class, asserted in full.

    §3.2's table gives `breakdown` the `dropout` device and `postchorus` no
    device at all — both with "crash+kick on entered downbeat: no". So the
    boundary must show *three* things, not just the missing crash the pre-C9
    version of this test checked:

    1. no entry crash on the entered downbeat (§3.2, both classes);
    2. no fill in the boundary's fill bar — the last bar of the outgoing section
       (§3.1). The device is `dropout`/none, so the `fill`-or-`stop` row of the
       table does not apply and nothing may be rendered there. This is the
       direction Layer-1's W2 cannot cover: W2 asserts a fill only lands in *a*
       fill bar (an only-if), never that *this* fill bar stays empty;
    3. for `breakdown` only, the §3.5 dropout truncation — no note of any role
       sustains across the entered downbeat ("clean cut into the thinned
       texture"). `postchorus` is explicitly a *smooth continuation*, so notes
       sustaining across it are correct and must not be asserted away.

       Unlike (2), this one *is* logically the same assertion as Layer-1 W2's
       third clause — same predicate, and the same grain: W2 reads
       `trace.phrases_stage6` and `final` here is the stage-6 output too (the
       humanizer runs after `_wired` returns it). The duplication is deliberate
       and is about venue, not strength: W2 fires only where a quality trace is
       produced, whereas this runs on the §11.9 matrix in the default pytest
       gate, over every registered pack × mood × length × seed. Keep both; do not
       "de-duplicate" this one by deferring to W2.

    Non-vacuity is measured, not assumed: across `chill_lofi` + `fusion_jazz` the
    non-suppressed boundaries carry a fill-bar fill in 781 of 781 cases and a
    note sustaining across the entered downbeat in 90 of 781, so both (2) and (3)
    discriminate rather than passing on an empty population.
    """
    tick = entered.start_bar * BAR
    ctx = (params, entered.type, entered.id)

    # (1) no entry crash.
    assert track_window(final, "crash", tick, tick + 1) == [], ("crash-suppress", ctx)

    # (2) no fill rendered in the boundary's fill bar.
    fill_bar = outgoing.start_bar + outgoing.length_bars - 1
    for phrase in final:
        if phrase.role != "drums":
            continue
        for note in phrase.notes:
            assert not ("fill" in note.tags and note.ticks // BAR == fill_bar), (
                "suppressed-boundary-fill",
                ctx,
                note.ticks,
            )

    # (3) §3.5 dropout: nothing sustains into a breakdown.
    if entered.type == "breakdown":
        for phrase in final:
            for note in phrase.notes:
                assert not (note.ticks < tick < note.ticks + note.duration_ticks), (
                    "dropout-not-truncated",
                    ctx,
                    phrase.track_id,
                    note.ticks,
                    note.duration_ticks,
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
        if entered.type in _SUPPRESS_TYPES:
            # Live on chill_lofi + fusion_jazz (both enter `breakdown`); N/A on
            # the other three packs, per `_ENTERED_SUPPRESS_TYPES`.
            _assert_suppressed_entry(params, final, secs[i], entered)
        elif entered.start_bar < t_last_bar:
            crash_here = track_window(final, "crash", tick, tick + 1)
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
