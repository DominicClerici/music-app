"""Golden-corpus mechanics (PHASE_8 §8.2) — cell matrix, mood triple, encode/decode.

Nothing here writes into the committed `fixtures/` tree; every write goes to
`tmp_path`. The corpus baseline itself is captured by the `bless` tooling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trackgen.interpreter.moods import MOOD_VOCABULARY, MoodTable
from trackgen.pipeline.trace import GenerationTrace
from trackgen.tooling import corpus as corpus_module
from trackgen.tooling.corpus import (
    STAGES,
    Cell,
    cell_dir,
    corpus_cells,
    corpus_moods,
    decode_stage,
    encode_stage,
    extreme_mood_pair,
    read_cell,
    render_cell,
    write_cell,
)

_PACKS = ("pop_rock", "jazz", "chill_lofi", "blues", "fusion_jazz")

# The stage-name -> trace-attribute mapping, restated independently of the module
# under test so a typo there is caught rather than mirrored.
_EXPECTED_FIELDS: dict[str, str] = {
    "plan": "plan",
    "songform": "song_form",
    "harmony": "harmony",
    "arrangement": "arrangement",
    "phrases_stage5": "phrases_stage5",
    "phrases_stage6": "phrases_stage6",
    "phrases_stage7": "phrases_stage7",
    "tempo_events": "tempo_events",
    "sound_design": "sound_design",
    "document": "document",
}

_LIST_STAGES = {
    "phrases_stage5",
    "phrases_stage6",
    "phrases_stage7",
    "tempo_events",
}


def _expected_payload(trace: GenerationTrace, stage: str) -> object:
    """The dump the S18-2 convention says a stage file must contain.

    Deliberately recomputed here from the pinned rules rather than by calling the
    module's own helper: an encoder that leaked `by_alias` or `exclude_none` into
    the IR stages, or dropped them from `document`, produces a *different* dict
    and fails the round-trip assertion below.
    """
    value = getattr(trace, _EXPECTED_FIELDS[stage])
    if stage == "document":
        return value.model_dump(by_alias=True, exclude_none=True)
    if stage in _LIST_STAGES:
        return [model.model_dump() for model in value]
    return value.model_dump()


@pytest.fixture(scope="module")
def traces() -> dict[str, GenerationTrace]:
    """One rendered trace per reference pack, at that pack's default mood."""
    return {
        pack: render_cell(
            Cell(pack=pack, mood=corpus_moods(pack)[0], length_sec=120, seed="1ps9wxb")
        )
        for pack in _PACKS
    }


# --- mood triple (S18-3) ------------------------------------------------------


def _tied_table(first_pair: tuple[str, str], second_pair: tuple[str, str]) -> MoodTable:
    """A 12-mood table where two disjoint pairs sit at *exactly* the same maximum
    distance (opposite corners of the unit square) and every other mood is at the
    origin. Only the tie-break can decide the winner."""
    rows: dict[str, dict[str, float]] = {
        mood: {"valence": 0.0, "arousal": 0.0} for mood in MOOD_VOCABULARY
    }
    rows[first_pair[0]] = {"valence": -1.0, "arousal": -1.0}
    rows[first_pair[1]] = {"valence": 1.0, "arousal": 1.0}
    rows[second_pair[0]] = {"valence": -1.0, "arousal": 1.0}
    rows[second_pair[1]] = {"valence": 1.0, "arousal": -1.0}
    return MoodTable.model_validate({"moods": rows})


def test_extreme_pair_tie_break_is_alphabetical_and_order_independent() -> None:
    """A distance tie resolves identically whatever order the moods arrive in.

    `aggressive`/`calm` and `dark`/`energetic` are placed at opposite corners, so
    both pairs are at distance sqrt(8). The alphabetically-first pair must win for
    every permutation of the supported list.

    What this pins is *input-order independence* (including `set()` hash-order
    leakage) — not the presence of the explicit `(-distance, a, b)` sort. That
    sort is provably equivalent to a plain `max()`: `sorted(set(moods))` feeds
    `itertools.combinations`, which yields pairs lexicographically, and `max`
    returns the first maximal element — i.e. the same lexicographically-smallest
    tied pair. No test can separate the two implementations. Determinism rests on
    the `sorted(set(...))` normalization; the explicit sort is a deliberate,
    redundant restatement of that guarantee. Ranking the *raw* input order,
    however, does fail this test.
    """
    table = _tied_table(("aggressive", "calm"), ("dark", "energetic"))
    moods = ["aggressive", "calm", "dark", "energetic", "happy"]

    assert extreme_mood_pair(moods, table) == ("aggressive", "calm")
    assert extreme_mood_pair(list(reversed(moods)), table) == ("aggressive", "calm")
    assert extreme_mood_pair(["dark", "energetic", "calm", "aggressive"], table) == (
        "aggressive",
        "calm",
    )


def test_extreme_pair_tie_break_favors_no_particular_mood() -> None:
    """The same tie with the *other* pair alphabetically first flips the answer.

    Guards against a tie-break that accidentally hard-favors one mood name.
    """
    table = _tied_table(("melancholic", "nostalgic"), ("aggressive", "calm"))
    assert extreme_mood_pair(
        ["melancholic", "nostalgic", "aggressive", "calm"], table
    ) == ("aggressive", "calm")


def test_extreme_pair_is_always_returned_sorted() -> None:
    """`extreme_mood_pair`'s "always sorted" claim, asserted rather than assumed.

    The pair is consumed positionally (it becomes two of the three moods in the
    triple, and thence two `fixtures/goldens/<pack>/<mood>/` subtrees), so a
    silently reversed pair is a real corpus repoint. Nothing else tests it.
    """
    table = _tied_table(("aggressive", "calm"), ("dark", "energetic"))
    for moods in (
        ["aggressive", "calm", "dark", "energetic", "happy"],
        ["energetic", "dark", "happy", "calm", "aggressive"],
        ["melancholic", "nostalgic", "calm", "aggressive"],
    ):
        mood_a, mood_b = extreme_mood_pair(moods, table)
        assert mood_a < mood_b, moods

    for pack in _PACKS:
        _, mood_a, mood_b = corpus_moods(pack)
        assert mood_a < mood_b, pack


def test_extreme_pair_needs_two_moods() -> None:
    table = _tied_table(("aggressive", "calm"), ("dark", "energetic"))
    with pytest.raises(ValueError, match="at least 2 moods"):
        extreme_mood_pair(["happy", "happy"], table)


@pytest.mark.parametrize(
    ("pack", "expected"),
    [
        ("pop_rock", ("happy", "aggressive", "calm")),
        ("jazz", ("nostalgic", "energetic", "melancholic")),
        ("chill_lofi", ("nostalgic", "happy", "melancholic")),
        ("blues", ("energetic", "aggressive", "romantic")),
        ("fusion_jazz", ("energetic", "calm", "tense")),
    ],
)
def test_corpus_moods_pinned_triples(pack: str, expected: tuple[str, str, str]) -> None:
    """The derived triples for the corpus packs, pinned.

    pop_rock: aggressive (-0.60, 0.70) <-> calm (0.55, -0.65); jazz: energetic
    (0.45, 0.80) <-> melancholic (-0.50, -0.45); chill_lofi: happy (0.75, 0.40)
    <-> melancholic (-0.50, -0.45); blues: aggressive (-0.60, 0.70) <->
    romantic (0.60, -0.20) (an exact-distance tie with energetic/melancholic,
    broken lexicographically); fusion_jazz: calm (0.55, -0.65) <-> tense
    (-0.45, 0.50) at d = 1.5240, ahead of the calm/energetic runner-up at
    1.4534 (no tie). A change to `moods.yaml` or to a pack's
    `supportedMoods` repoints the corpus and must be a deliberate re-bless.
    """
    assert corpus_moods(pack) == expected


def test_corpus_moods_rejects_unknown_pack() -> None:
    with pytest.raises(ValueError, match="did not resolve"):
        corpus_moods("not_a_pack")


def test_corpus_moods_rejects_a_degenerate_triple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pack whose `default_mood` is also a (V, A) extreme must fail loudly.

    Otherwise the triple carries a duplicate — `('happy', 'calm', 'happy')` — and
    `corpus_cells()` silently yields fewer cells than the pinned matrix (e.g.
    56 instead of 60), with `bless`
    rendering and double-reporting the repeats. Neither reference pack hits this
    today, so the guard is exercised by repointing the *mood table* (pop_rock's
    real `defaultMood` is `happy`) rather than by editing any `styles/` data.
    """
    rows: dict[str, dict[str, float]] = {
        mood: {"valence": 0.0, "arousal": 0.0} for mood in MOOD_VOCABULARY
    }
    rows["happy"] = {"valence": -1.0, "arousal": -1.0}
    rows["calm"] = {"valence": 1.0, "arousal": 1.0}
    table = MoodTable.model_validate({"moods": rows})
    monkeypatch.setattr(corpus_module, "_mood_table", lambda: table)

    # Precondition of the test itself: the collision is real, not assumed.
    assert extreme_mood_pair(("happy", "calm", "dark"), table) == ("calm", "happy")

    with pytest.raises(ValueError, match="degenerate corpus mood triple"):
        corpus_moods("pop_rock")


# --- cell matrix --------------------------------------------------------------


def test_corpus_cells_is_the_pinned_60_cell_matrix() -> None:
    cells = corpus_cells()
    assert len(cells) == 60
    assert len(set(cells)) == 60

    assert {c.pack for c in cells} == {
        "pop_rock",
        "jazz",
        "chill_lofi",
        "blues",
        "fusion_jazz",
    }
    assert {c.length_sec for c in cells} == {120, 240}
    assert len({c.seed for c in cells}) == 2

    for pack in _PACKS:
        moods = {c.mood for c in cells if c.pack == pack}
        # Non-degenerate: the triple really is three distinct moods, not the
        # default repeated because the extremes collapsed onto it.
        assert len(moods) == 3, (pack, moods)
        assert len([c for c in cells if c.pack == pack]) == 12


def test_cell_dirs_are_all_distinct_and_shaped_per_8_2(tmp_path: Path) -> None:
    cells = corpus_cells()
    dirs = [cell_dir(c, root=tmp_path) for c in cells]
    assert len(set(dirs)) == 60

    cell = Cell(pack="pop_rock", mood="calm", length_sec=240, seed="1ps9wxb")
    assert cell_dir(cell, root=tmp_path) == (
        tmp_path / "pop_rock" / "calm" / "240-1ps9wxb"
    )


def test_corpus_seeds_are_valid_base36_u64() -> None:
    from trackgen.seeds import from_base36

    for seed in {c.seed for c in corpus_cells()}:
        assert 0 <= from_base36(seed) < (1 << 64)


def test_stages_are_the_ten_trace_boundaries() -> None:
    assert len(STAGES) == 10
    assert len(set(STAGES)) == 10
    assert set(STAGES) == set(_EXPECTED_FIELDS)
    # `selection` is deliberately not a boundary (S18-5).
    assert "selection" not in STAGES


# --- encode / decode ----------------------------------------------------------


@pytest.mark.parametrize("pack", _PACKS)
@pytest.mark.parametrize("stage", STAGES)
def test_stage_round_trip_is_exact(
    traces: dict[str, GenerationTrace], pack: str, stage: str
) -> None:
    """`decode(encode(x))` equals `x.model_dump()` for every stage, both packs.

    The expectation is rebuilt from the S18-2 rules (see `_expected_payload`), so
    an encoder that aliased the IRs, excluded their nulls, or stopped aliasing
    `document` would produce a structurally different dict and fail here — this
    is not a tautological `decode(encode(...)) == decode(encode(...))`.
    """
    trace = traces[pack]
    decoded = decode_stage(stage, encode_stage(trace, stage))
    assert decoded == _expected_payload(trace, stage)


@pytest.mark.parametrize("pack", _PACKS)
def test_ir_stages_are_compact_snake_case_with_nulls_kept(
    traces: dict[str, GenerationTrace], pack: str
) -> None:
    """S18-2's formatting contract for an IR stage file, asserted on the text."""
    text = encode_stage(traces[pack], "plan")
    assert text.endswith("\n")
    assert "\n" not in text[:-1], "IR stages are compact (no pretty-printing)"
    assert ", " not in text and '": ' not in text, "compact separators"
    assert '"style_pack"' in text, "IRs stay non-aliased snake_case"
    assert '"stylePack"' not in text
    # `exclude_none` must NOT be applied to IR stages: an explicit null is
    # informative (S18-2). pop_rock's plan nulls `swing` + `feel_table`, jazz's
    # (swing8) nulls only `feel_table`, so the keys are looked up, not hardcoded.
    # chill_lofi, blues and fusion_jazz all carry fully populated plans
    # (chill_lofi: swing override + feelTable; blues and fusion_jazz:
    # table-resolved swing + feelTable) — zero nulls is their expected shape, so
    # the retention property is asserted only where a null exists to observe.
    null_keys = [k for k, v in traces[pack].plan.model_dump().items() if v is None]
    if pack in ("chill_lofi", "blues", "fusion_jazz"):
        assert not null_keys, f"{pack}'s plan is expected fully populated"
    else:
        assert null_keys, "expected the plan to carry at least one null field"
    for key in null_keys:
        assert f'"{key}":null' in text


@pytest.mark.parametrize("pack", _PACKS)
def test_document_stage_keeps_the_pinned_serialize_convention(
    traces: dict[str, GenerationTrace], pack: str
) -> None:
    """`document.json` stays aliased / none-excluded / `indent=2` (§8.2)."""
    text = encode_stage(traces[pack], "document")
    assert text.endswith("\n")
    assert text.startswith("{\n  ")
    assert '"schemaVersion"' in text, "document is aliased camelCase"
    assert '"schema_version"' not in text
    assert json.loads(text) == traces[pack].document.model_dump(
        by_alias=True, exclude_none=True
    )


def test_encode_and_decode_reject_unknown_stage(
    traces: dict[str, GenerationTrace],
) -> None:
    with pytest.raises(ValueError, match="unknown corpus stage"):
        encode_stage(traces["pop_rock"], "selection")
    with pytest.raises(ValueError, match="unknown corpus stage"):
        decode_stage("selection", "{}")


@pytest.mark.parametrize(
    "cell",
    [
        Cell(pack="pop_rock", mood="happy", length_sec=120, seed="1ps9wxb"),
        Cell(pack="jazz", mood="energetic", length_sec=120, seed="2kq7f3z"),
    ],
    ids=lambda c: f"{c.pack}-{c.mood}",
)
def test_cell_encoding_is_byte_stable_across_renders(cell: Cell) -> None:
    """Two independent renders of a cell encode to identical bytes, every stage.

    Deliberately re-renders rather than re-encoding one trace: this covers the
    determinism the corpus depends on (ROADMAP invariant 5), not just the purity
    of `json.dumps`. Any unseeded draw or dict-ordering wobble in the pipeline
    shows up as a byte difference here.
    """
    first = render_cell(cell)
    second = render_cell(cell)
    for stage in STAGES:
        left = encode_stage(first, stage).encode("utf-8")
        right = encode_stage(second, stage).encode("utf-8")
        assert left == right, stage


# --- write / read -------------------------------------------------------------


def test_write_cell_then_read_cell_round_trips(tmp_path: Path) -> None:
    cell = Cell(pack="pop_rock", mood="happy", length_sec=120, seed="1ps9wxb")
    trace = render_cell(cell)

    target = write_cell(trace, cell, root=tmp_path)
    assert target == cell_dir(cell, root=tmp_path)

    written = sorted(p.name for p in target.iterdir())
    assert written == sorted(f"{stage}.json" for stage in STAGES)
    for path in target.iterdir():
        assert path.read_bytes().endswith(b"\n")

    parsed = read_cell(cell, root=tmp_path)
    assert set(parsed) == set(STAGES)
    for stage in STAGES:
        assert parsed[stage] == _expected_payload(trace, stage)


def test_write_cell_is_idempotent(tmp_path: Path) -> None:
    cell = Cell(pack="jazz", mood="nostalgic", length_sec=120, seed="1ps9wxb")
    trace = render_cell(cell)

    write_cell(trace, cell, root=tmp_path)
    before = {p.name: p.read_bytes() for p in cell_dir(cell, root=tmp_path).iterdir()}
    write_cell(render_cell(cell), cell, root=tmp_path)
    after = {p.name: p.read_bytes() for p in cell_dir(cell, root=tmp_path).iterdir()}

    assert before == after
