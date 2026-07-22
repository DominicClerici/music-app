"""Anchored milestone rubric (PHASE_8 §8.4, instrument 3 / DoD §14.8).

Covers the 20 written anchors, the 15 cells resolving from pack data at the
pinned coordinate, the capture-record schema and its 1..5 score validation, and
the mechanism-from-I/O split: `run_rubric` with an injected `score` is
deterministic and appends one well-formed record per cell. Tests NEVER write the
committed `listening/log.jsonl` — the append path is proven against a tmp log.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.schema.document import TrackDocument
from trackgen.tooling import corpus
from trackgen.tooling.rubric import (
    ANCHORS,
    AXES,
    RUBRIC_LENGTH_SEC,
    RUBRIC_SEED,
    CellScore,
    rubric_cells,
    rubric_record,
    run_rubric,
    validate_scores,
)

runner = CliRunner()

# The exact mood triple each pack resolves to via `corpus_moods` (default + the
# two V/A extremes). Pinned here so a change to any pack's mood data that shifts
# a rubric cell is caught, not silently accepted.
_EXPECTED_MOODS: dict[str, set[str]] = {
    "pop_rock": {"happy", "aggressive", "calm"},
    "jazz": {"nostalgic", "energetic", "melancholic"},
    "chill_lofi": {"nostalgic", "happy", "melancholic"},
    "blues": {"energetic", "aggressive", "romantic"},
    "fusion_jazz": {"energetic", "calm", "tense"},
}


def _valid_score(pack: str, mood: str, doc: TrackDocument) -> CellScore:
    return CellScore(scores=dict.fromkeys(AXES, 3), notes="")


# --- the anchors (the substantive deliverable) ------------------------------


def test_four_axes_named_exactly() -> None:
    assert AXES == ("musicality", "groove", "styleFit", "soloistSpace")
    assert set(ANCHORS) == set(AXES)


def test_twenty_anchors_all_present_and_nonempty() -> None:
    """4 axes × 5 points = 20 anchors, each a non-empty distinct string."""
    seen: set[str] = set()
    for axis in AXES:
        assert set(ANCHORS[axis]) == {1, 2, 3, 4, 5}
        for point in range(1, 6):
            text = ANCHORS[axis][point]
            assert isinstance(text, str) and text.strip()
            seen.add(text)
    assert len(seen) == 20, "every anchor must be a distinct description"


# --- the 15 cells -----------------------------------------------------------


def test_fifteen_cells_at_pinned_coordinate() -> None:
    cells = rubric_cells()
    assert len(cells) == 15
    assert {c.pack for c in cells} == set(_EXPECTED_MOODS)
    for cell in cells:
        assert cell.length_sec == RUBRIC_LENGTH_SEC
        assert cell.seed == RUBRIC_SEED


def test_cells_reuse_corpus_mood_triples() -> None:
    """Each pack's three cells are exactly `corpus_moods(pack)` — 1:1 with corpus."""
    by_pack: dict[str, set[str]] = {}
    for cell in rubric_cells():
        by_pack.setdefault(cell.pack, set()).add(cell.mood)
    for pack, expected in _EXPECTED_MOODS.items():
        assert by_pack[pack] == expected
        assert by_pack[pack] == set(corpus.corpus_moods(pack))


def test_pinned_coordinate_matches_first_corpus_cell() -> None:
    assert RUBRIC_SEED == corpus._CORPUS_SEEDS[0]
    assert RUBRIC_LENGTH_SEC == corpus._CORPUS_LENGTHS_SEC[0]


# --- schema + score validation ----------------------------------------------


def test_record_round_trips_through_json() -> None:
    cell = rubric_cells()[0]
    score = CellScore(
        scores={"musicality": 4, "groove": 5, "styleFit": 3, "soloistSpace": 4},
        notes="locked pocket, comping a touch busy",
    )
    record = rubric_record(cell, score, date="2026-07-21")
    restored = json.loads(json.dumps(record))
    assert restored == record
    assert restored["type"] == "rubric"
    assert restored["date"] == "2026-07-21"
    assert restored["pack"] == cell.pack
    assert restored["mood"] == cell.mood
    assert restored["seed"] == cell.seed
    assert restored["length"] == cell.length_sec
    assert restored["scores"] == score.scores
    assert restored["notes"] == "locked pocket, comping a touch busy"


def test_validate_scores_accepts_full_range() -> None:
    scores = {"musicality": 1, "groove": 5, "styleFit": 3, "soloistSpace": 2}
    assert validate_scores(scores) == scores


@pytest.mark.parametrize("bad", [0, 6, -1, 100])
def test_validate_scores_rejects_off_scale(bad: int) -> None:
    scores = {"musicality": bad, "groove": 3, "styleFit": 3, "soloistSpace": 3}
    with pytest.raises(ValueError):
        validate_scores(scores)


def test_validate_scores_rejects_missing_and_extra_axes() -> None:
    with pytest.raises(ValueError):
        validate_scores({"musicality": 3, "groove": 3, "styleFit": 3})
    with pytest.raises(ValueError):
        validate_scores(
            {
                "musicality": 3,
                "groove": 3,
                "styleFit": 3,
                "soloistSpace": 3,
                "vibe": 3,
            }
        )


def test_validate_scores_rejects_bool() -> None:
    with pytest.raises(ValueError):
        validate_scores(
            {"musicality": True, "groove": 3, "styleFit": 3, "soloistSpace": 3}
        )


def test_rubric_record_validates_scores() -> None:
    cell = rubric_cells()[0]
    with pytest.raises(ValueError):
        rubric_record(cell, CellScore(scores=dict.fromkeys(AXES, 6)), date="2026-07-21")


# --- run_rubric core (mechanism split from I/O) -----------------------------


def test_run_rubric_one_record_per_cell_well_formed() -> None:
    cells = rubric_cells()
    records = run_rubric(cells, _valid_score, date="2026-07-21")
    assert len(records) == len(cells)
    for cell, record in zip(cells, records, strict=True):
        assert record["type"] == "rubric"
        assert record["date"] == "2026-07-21"
        assert record["pack"] == cell.pack
        assert record["mood"] == cell.mood
        assert record["seed"] == RUBRIC_SEED
        assert record["length"] == RUBRIC_LENGTH_SEC
        scores = record["scores"]
        assert isinstance(scores, dict)
        assert set(scores) == set(AXES)
        assert "notes" in record


def test_run_rubric_is_deterministic() -> None:
    cells = rubric_cells()
    assert run_rubric(cells, _valid_score, date="2026-07-21") == run_rubric(
        cells, _valid_score, date="2026-07-21"
    )


def test_run_rubric_passes_rendered_doc_to_score() -> None:
    """The injected score receives the cell's rendered `TrackDocument`."""
    seen: list[tuple[str, str, bool]] = []

    def spy(pack: str, mood: str, doc: TrackDocument) -> CellScore:
        seen.append((pack, mood, bool(doc.tracks)))
        return CellScore(scores=dict.fromkeys(AXES, 3))

    run_rubric(rubric_cells()[:2], spy, date="2026-07-21")
    assert len(seen) == 2
    assert all(has_tracks for _, _, has_tracks in seen)


def test_run_rubric_date_is_passed_in_not_clocked() -> None:
    records = run_rubric(rubric_cells()[:1], _valid_score, date="1999-01-01")
    assert records[0]["date"] == "1999-01-01"


# --- append path (tmp log only; committed log is never touched) -------------


def test_stub_score_append_writes_tmp_log(tmp_path: Path) -> None:
    log = tmp_path / "nested" / "log.jsonl"
    cells = rubric_cells()[:3]
    records = run_rubric(cells, _valid_score, date="2026-07-21")

    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert all(json.loads(line)["type"] == "rubric" for line in lines)


# --- CLI wiring (stubbed prompts + tmp log) ---------------------------------


def test_cli_rubric_writes_records_to_tmp_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `rubric` command drives the 15 cells and appends 15 records.

    Prompts are stubbed by kind: score prompts (`type=int`) return 4, the notes
    prompt (a string default) returns a sentinel string — so the record's notes
    field is captured as a real `str`, exercising that path. `open_playground` is
    neutered so no browser opens. The log is a tmp path — the committed
    `listening/log.jsonl` is never written by tests.
    """

    def _stub_prompt(*args: object, **kwargs: object) -> object:
        return 4 if kwargs.get("type") is int else "locks in nicely"

    monkeypatch.setattr("trackgen.cli.open_playground", lambda rendered: None)
    monkeypatch.setattr("trackgen.cli.typer.prompt", _stub_prompt)

    log = tmp_path / "log.jsonl"
    result = runner.invoke(app, ["rubric", "--date", "2026-07-21", "--log", str(log)])
    assert result.exit_code == 0, result.output

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 15
    records = [json.loads(line) for line in lines]
    assert all(r["type"] == "rubric" for r in records)
    assert all(r["date"] == "2026-07-21" for r in records)
    assert all(r["scores"] == dict.fromkeys(AXES, 4) for r in records)
    assert all(r["notes"] == "locks in nicely" for r in records)
    # The 15 (pack, mood) coordinates match the corpus triples.
    got = {(r["pack"], r["mood"]) for r in records}
    expected = {
        (pack, mood) for pack, moods in _EXPECTED_MOODS.items() for mood in moods
    }
    assert got == expected


def test_cli_rubric_requires_date() -> None:
    result = runner.invoke(app, ["rubric"])
    assert result.exit_code != 0
