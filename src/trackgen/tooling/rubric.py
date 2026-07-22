"""Anchored milestone rubric (PHASE_8 §8.4, instrument 3 / DoD §14.8).

A 5-point scale with *written anchor descriptions per point* on four axes —
musicality, groove, style-fit, soloist space — scored per pack × 3 moods (5
packs × 3 = 15 cells). The anchors are the substantive deliverable: they turn a
"how good is it" hunch into a discriminating, repeatable judgement, grounded in
ROADMAP §1's quality criteria (these are instrumental backing tracks a musician
plays *over*, so musical believability, groove, and soloist space are the top
criteria, and the soloist owns the register above ~C5).

Like the A/B harness (`ab.py`), the module is split mechanism-from-I/O:
`run_rubric` is a deterministic core that renders each cell and calls an injected
`score` callback, so it never touches a browser or a prompt and is fully
unit-testable, while the `trackgen rubric` CLI wires `score` to interactive
prompts over the audition player.

**The 15 cells reuse the golden-corpus coordinates.** Each pack's mood triple is
`corpus.corpus_moods` verbatim (default + the two V/A extremes), and every cell
is pinned to the first corpus seed and length, so a rubric render is the same
reproducible artifact as its golden-corpus sibling — the score always attaches to
a fixed coordinate, never a fresh random one. Entropy is never touched here: the
seed is a pinned literal sourced from `corpus`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from trackgen.schema.document import TrackDocument
from trackgen.tooling import corpus

# The four axes, in canonical order. Named exactly as they appear in a capture
# record's `scores` object (camelCase, matching the document contract).
AXES: tuple[str, ...] = ("musicality", "groove", "styleFit", "soloistSpace")

_MIN_SCORE = 1
_MAX_SCORE = 5

# The written anchor per point, per axis (1 = worst … 5 = best). This is the
# instrument: the descriptions must discriminate a 3 from a 4 in the ear, not
# just label the numbers. Grounded in ROADMAP §1 — the tracks exist to be
# soloed over, so "would I play on this?" is the through-line.
ANCHORS: dict[str, dict[int, str]] = {
    "musicality": {
        1: (
            "Wrong-sounding: pitches clash, chords fight the key, the harmony "
            "reads as mistakes rather than choices. You'd stop the track."
        ),
        2: (
            "In-key but lifeless: voice-leading lurches, phrases start and stop "
            "arbitrarily, nothing connects into a line you'd hum."
        ),
        3: (
            "Believable and correct: the changes make sense and the parts fit, "
            "but it's generic — a competent play-through with no moment that "
            "rewards a second listen."
        ),
        4: (
            "Musical and shapely: clear phrasing, purposeful voice-leading, "
            "tension and release land where a real player would place them, with "
            "a couple of genuinely nice touches."
        ),
        5: (
            "Sounds like real musicians committed to a take: every part has "
            "intent, the harmony breathes, and there are moments you'd rewind "
            "to hear again."
        ),
    },
    "groove": {
        1: (
            "Mechanical, no pocket: feels like a click track — onsets dead on the "
            "grid with no feel, or timing so loose it stumbles. Unplayable-over."
        ),
        2: (
            "Stiff: a pulse exists but it doesn't swing or breathe; kit and bass "
            "aren't locked, so the time feels shaky rather than intentional."
        ),
        3: (
            "Solid time: kick and bass agree and the beat is dependable, but it's "
            "flat — you could tap along but it doesn't move you."
        ),
        4: (
            "Good pocket: bass and drums lock, the swing/laid-back feel is "
            "idiomatic and consistent, and the groove has momentum you feel."
        ),
        5: (
            "Locked, breathing pocket you'd loop for hours: the microtiming feels "
            "human and deliberate, the section plays as one, and the groove alone "
            "makes you want to play over it."
        ),
    },
    "styleFit": {
        1: (
            "Wrong genre: an ear-test listener would name a different style — the "
            "instruments, feel, or harmonic language betray the pack entirely."
        ),
        2: (
            "In the neighborhood but full of tells: anachronistic voicings, a feel "
            "borrowed from another genre, or timbres no player of this style "
            "would reach for."
        ),
        3: (
            "Recognizably the genre but textbook: hits the obvious markers without "
            "the idiom's character — a stock example, not a convincing one."
        ),
        4: (
            "Idiomatic: the voicings, rhythms, instrumentation, and feel are what "
            "a player of this style actually does; it sits inside the tradition."
        ),
        5: (
            "Definitively this style at its best: the details a specialist would "
            "insist on are all present and the mood inflection reads correctly — "
            "named in a bar or two, with a nod."
        ),
    },
    "soloistSpace": {
        1: (
            "No room: the arrangement crowds the solo register (above ~C5), "
            "competes for the melody, and is too busy or loud to leave the "
            "soloist anywhere to go."
        ),
        2: (
            "Cramped: backing parts stray into the soloist's register or pile into "
            "the same frequency band, so you'd fight the track to be heard."
        ),
        3: (
            "Adequate space: the register above ~C5 is mostly clear and levels "
            "leave headroom, but the arrangement doesn't invite a solo — you can "
            "play over it, just not eagerly."
        ),
        4: (
            "Inviting: parts stay in their lane below the soloist, the texture "
            "leaves clear pockets, and the dynamics open up where a solo sits."
        ),
        5: (
            "Made to be soloed over: the register is deliberately clear, the parts "
            "frame and answer an imagined soloist, density and dynamics ebb to "
            "leave space, and you can't wait to play on top of it."
        ),
    },
}


# The pinned rubric coordinate, reused from the golden corpus (§8.2) so a rubric
# render matches its corpus sibling exactly. First seed, first length — pinned
# literals sourced from `corpus`, never derived.
RUBRIC_SEED: str = corpus._CORPUS_SEEDS[0]
RUBRIC_LENGTH_SEC: int = corpus._CORPUS_LENGTHS_SEC[0]


@dataclass(frozen=True)
class CellScore:
    """One listener's judgement of a cell: the four axis scores plus free notes.

    `scores` maps each axis in `AXES` to an int in 1..5; `notes` is an optional
    free-text comment. This is the single value the injected `score` callback
    returns, so the interactive prompts and any test stub agree on one shape.
    """

    scores: dict[str, int]
    notes: str = ""


# `score(pack, mood, doc) -> CellScore`: judge a rendered cell. The CLI wires
# this to prompts over the audition player; a test wires it to a stub.
Score = Callable[[str, str, TrackDocument], CellScore]


def validate_scores(scores: Mapping[str, int]) -> dict[str, int]:
    """Return `scores` as a plain dict, or raise if it is not a valid ballot.

    A valid ballot has exactly the `AXES` keys, each an `int` (not `bool`) in
    1..5. Rejecting 0 and 6 is the point — the scale is anchored end to end and
    an off-scale number has no anchor to mean anything.
    """
    keys = set(scores)
    if keys != set(AXES):
        missing = sorted(set(AXES) - keys)
        extra = sorted(keys - set(AXES))
        raise ValueError(
            f"scores must have exactly the axes {list(AXES)}; "
            f"missing={missing}, extra={extra}"
        )
    out: dict[str, int] = {}
    for axis in AXES:
        value = scores[axis]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"score for {axis!r} must be an int, got {value!r}")
        if not (_MIN_SCORE <= value <= _MAX_SCORE):
            raise ValueError(
                f"score for {axis!r} must be in {_MIN_SCORE}..{_MAX_SCORE}, got {value}"
            )
        out[axis] = value
    return out


def rubric_record(
    cell: corpus.Cell, score: CellScore, *, date: str
) -> dict[str, object]:
    """One `{"type": "rubric"}` capture record for `cell` (scores validated).

    `date` is passed in — wall-clock is banned (ROADMAP invariant 5), so the
    session date is always the caller's to supply.
    """
    return {
        "type": "rubric",
        "date": date,
        "pack": cell.pack,
        "mood": cell.mood,
        "seed": cell.seed,
        "length": cell.length_sec,
        "scores": validate_scores(score.scores),
        "notes": score.notes,
    }


def rubric_cells() -> list[corpus.Cell]:
    """The 15 rubric cells: the five corpus packs × their 3 moods, pinned coord.

    Moods are `corpus.corpus_moods` verbatim (default + the two V/A extremes) so
    the rubric's cells line up 1:1 with the golden-corpus coordinates; every cell
    takes the pinned `RUBRIC_SEED`/`RUBRIC_LENGTH_SEC`.
    """
    return [
        corpus.Cell(
            pack=pack, mood=mood, length_sec=RUBRIC_LENGTH_SEC, seed=RUBRIC_SEED
        )
        for pack in corpus._CORPUS_PACKS
        for mood in corpus.corpus_moods(pack)
    ]


def run_rubric(
    cells: list[corpus.Cell], score: Score, *, date: str
) -> list[dict[str, object]]:
    """Render each cell and score it through `score`; return one record per cell.

    Mechanism only: this renders through the production chain (`render_cell`) and
    hands the document to the injected `score` callback, which owns all I/O (the
    CLI opens the audition player and prompts; a test returns a stub). Fully
    deterministic in `(cells, score, date)`.
    """
    records: list[dict[str, object]] = []
    for cell in cells:
        document = corpus.render_cell(cell).document
        result = score(cell.pack, cell.mood, document)
        records.append(rubric_record(cell, result, date=date))
    return records
