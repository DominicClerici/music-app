"""Golden-corpus mechanics (PHASE_8 §8.2) — cell enumeration + stage encode/decode.

The §8.2 corpus stores **every IR boundary** of a render to
`fixtures/goldens/<pack>/<mood>/<len>-<seed>/<stage>.json`, so a golden diff
localizes to the *first divergent stage* rather than to one opaque document. This
module is the pure library half of that workflow: it enumerates the cell matrix,
renders a cell, and encodes/decodes each stage. It performs no diffing, exposes
no CLI, and writes nothing unless a caller asks it to.

`STAGES` is the shared stage-name contract — the bless report and the baseline
capture both import it from here rather than redefining the order.

**Mood triple (SESSION_18 S18-3).** §8.2 asks for "default + the supported set's
V/A extremes", which is under-determined (valence and arousal select different
moods). Resolved as: the supported-mood *pair* maximizing Euclidean distance in
the combined (valence, arousal) plane, ranked by `(-distance, mood_a, mood_b)` so
a distance tie resolves alphabetically. Determinism under a tie rests on
normalizing the candidate set to `sorted(set(moods))` before pairing; the
explicit rank key is a deliberate restatement of that guarantee, so the property
survives a future refactor of either half alone.

**Seeds are pinned literals**, never derived, so a cell's identity survives any
future change to the seed helpers. Cell coordinates are therefore fixed forever;
only the *contents* of a cell are allowed to move (and moving them is what
`bless` exists to review).

**Formatting (SESSION_18 S18-2).** IR stage files use compact separators — they
are machine-read by the diff report, and §8.2 makes the report, not the raw JSON,
the reading surface. `document.json` keeps `indent=2` with
`by_alias=True, exclude_none=True`, matching the existing
`fixtures/*.milestone.trackdoc.json` convention (`pipeline/serialize.py`). The IRs
are deliberately non-aliased snake_case, so IR stages dump **without** `by_alias`
and **without** `exclude_none`: an explicit `"swing": null` is informative.
Every file gets an explicit trailing newline, utf-8.
"""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from trackgen.interpreter.moods import MoodTable, load_moods
from trackgen.packs import resolve_pack
from trackgen.pipeline.trace import GenerationTrace, generate_trace

# `fixtures/goldens/` at the repo root: tooling -> trackgen -> src -> repo.
GOLDENS_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "goldens"

# The 10 corpus stages in `GenerationTrace` field order (SESSION_18 §2). §8.2
# names 9 boundaries; `tempo_events` is split out of the phrases-7 file because
# it is a distinct pinned artifact and diffs independently. `selection` is *not*
# a boundary (S18-5): §8.2 omits it, and `SelectionResult` is tuple-keyed and so
# not JSON-round-trippable without inventing a key-flattening encoder.
STAGES: tuple[str, ...] = (
    "plan",
    "songform",
    "harmony",
    "arrangement",
    "phrases_stage5",
    "phrases_stage6",
    "phrases_stage7",
    "tempo_events",
    "sound_design",
    "document",
)

# Stage name -> `GenerationTrace` attribute. Only `songform` diverges from its
# field name (the file is `songform.json`, the field is `song_form`).
_STAGE_FIELDS: dict[str, str] = {
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

# Stages whose trace field is a list of models rather than a single model.
_LIST_STAGES: frozenset[str] = frozenset(
    {"phrases_stage5", "phrases_stage6", "phrases_stage7", "tempo_events"}
)

# The one stage serialized with the pinned *document* convention (§8.2 /
# `pipeline/serialize.py`): aliased, none-excluded, pretty-printed.
_DOCUMENT_STAGE = "document"

_COMPACT_SEPARATORS = (",", ":")
_DOCUMENT_INDENT = 2

# --- the pinned cell matrix (§8.2, 24 cells) ---------------------------------
#
# The two *reference* packs only. §8.2's five-pack / 60-cell matrix fills out as
# C6-C8 author chill_lofi/blues/fusion_jazz; the coordinates below are a strict
# prefix of it, so the fill-out is additive.
_CORPUS_PACKS: tuple[str, ...] = ("pop_rock", "jazz")

_CORPUS_LENGTHS_SEC: tuple[int, ...] = (120, 240)

# Pinned base36 u64 seed literals. Never derived — a derived seed would silently
# repoint every cell if the derivation changed.
_CORPUS_SEEDS: tuple[str, ...] = ("1ps9wxb", "2kq7f3z")


@dataclass(frozen=True, order=True)
class Cell:
    """One corpus coordinate: `(pack, mood, length, seed)` (§8.2)."""

    pack: str
    mood: str
    length_sec: int
    seed: str


@lru_cache(maxsize=1)
def _mood_table() -> MoodTable:
    """The engine mood table, read once (`load_moods` re-parses the yaml)."""
    return load_moods()


def extreme_mood_pair(moods: Sequence[str], table: MoodTable) -> tuple[str, str]:
    """The (V, A)-farthest pair among `moods`, with the S18-3 tie-break.

    Candidate pairs are ranked by `(-distance, mood_a, mood_b)` and the first is
    returned, so an exact distance tie resolves alphabetically instead of by
    whatever order `moods` happened to arrive in. The returned pair is always
    sorted (`mood_a < mood_b`), and duplicate entries in `moods` are ignored.
    """
    # Load-bearing for determinism, not just tidiness: normalizing to a sorted,
    # de-duplicated list is what makes the result independent of the caller's
    # input order (including `set()` hash-order leakage). The `(-distance, a, b)`
    # rank below is a deliberate restatement of the same guarantee, NOT a
    # replacement for it -- over a sorted candidate list it is provably
    # equivalent to a plain `max()`. Removing this line silently reintroduces
    # input-order dependence that the rank key cannot recover.
    unique = sorted(set(moods))
    if len(unique) < 2:
        raise ValueError(f"need at least 2 moods to find an extreme pair, got {unique}")

    ranked = sorted(
        (
            -math.dist(
                (table.moods[a].valence, table.moods[a].arousal),
                (table.moods[b].valence, table.moods[b].arousal),
            ),
            a,
            b,
        )
        for a, b in itertools.combinations(unique, 2)
    )
    _, mood_a, mood_b = ranked[0]
    return mood_a, mood_b


def corpus_moods(pack_id: str) -> tuple[str, str, str]:
    """`(default, extreme_a, extreme_b)` for `pack_id` (§8.2 / S18-3).

    One shared helper so every pack resolves its triple identically; see the
    module docstring for why the "V/A extremes" phrasing needed resolving.

    Raises `ValueError` if the pack's `default_mood` is itself one of its two
    (V, A) extremes: the triple would then hold a duplicate and `corpus_cells()`
    would silently emit 20 cells instead of 24, with `bless` rendering and
    double-reporting the repeats. Neither reference pack hits this; a pack
    authored later can.
    """
    pack = resolve_pack(pack_id)
    if pack is None or pack.interpreter is None:
        raise ValueError(
            f"pack {pack_id!r} did not resolve to a pack with an interpreter"
        )
    default = pack.interpreter.default_mood
    mood_a, mood_b = extreme_mood_pair(pack.interpreter.supported_moods, _mood_table())
    if default in (mood_a, mood_b):
        # Precondition, not a redesign: S18-3 pins the triple as *default + the
        # two extremes*, so substituting the next-farthest mood is unpinned and
        # would need sign-off. Fail loudly and make the pack author choose.
        raise ValueError(
            f"pack {pack_id!r} has a degenerate corpus mood triple: its "
            f"default_mood {default!r} is also one of its (V, A) extremes "
            f"({mood_a!r}, {mood_b!r}), so the triple would collapse to 2 "
            f"distinct moods and the corpus would lose 4 cells per pack. "
            f"Fix the pack: change its defaultMood, or widen/adjust its "
            f"supportedMoods so the extremes do not include the default. "
            f"Do not substitute a replacement mood here -- the triple is "
            f"pinned by SESSION_18 S18-3 and changing it needs sign-off."
        )
    return (default, mood_a, mood_b)


def corpus_cells() -> list[Cell]:
    """The pinned 24-cell matrix: 2 packs × 3 moods × 2 lengths × 2 seeds (§8.2)."""
    return [
        Cell(pack=pack, mood=mood, length_sec=length_sec, seed=seed)
        for pack in _CORPUS_PACKS
        for mood in corpus_moods(pack)
        for length_sec in _CORPUS_LENGTHS_SEC
        for seed in _CORPUS_SEEDS
    ]


def cell_dir(cell: Cell, *, root: Path | None = None) -> Path:
    """`<root>/<pack>/<mood>/<len>-<seed>/` (§8.2), `root` defaulting to the corpus."""
    base = GOLDENS_ROOT if root is None else root
    return base / cell.pack / cell.mood / f"{cell.length_sec}-{cell.seed}"


def render_cell(cell: Cell) -> GenerationTrace:
    """Render `cell` through the production chain, retaining every IR boundary."""
    return generate_trace(
        {
            "styleFamily": cell.pack,
            "mood": cell.mood,
            "maxLengthSec": cell.length_sec,
            "seed": cell.seed,
        }
    )


def _stage_dump(trace: GenerationTrace, stage: str) -> Any:
    """The JSON-ready payload for `stage`, with that stage's dump convention."""
    if stage not in _STAGE_FIELDS:
        raise ValueError(f"unknown corpus stage {stage!r}; expected one of {STAGES}")

    value = getattr(trace, _STAGE_FIELDS[stage])
    if stage == _DOCUMENT_STAGE:
        return value.model_dump(by_alias=True, exclude_none=True)
    if stage in _LIST_STAGES:
        return [model.model_dump() for model in value]
    return value.model_dump()


def encode_stage(trace: GenerationTrace, stage: str) -> str:
    """Serialize one stage of `trace` to its pinned on-disk text (S18-2).

    `document` is aliased/none-excluded/`indent=2`; every IR stage is raw
    snake_case with nulls kept and compact separators. Always ends in a newline.
    """
    payload = _stage_dump(trace, stage)
    if stage == _DOCUMENT_STAGE:
        text = json.dumps(payload, indent=_DOCUMENT_INDENT)
    else:
        text = json.dumps(payload, separators=_COMPACT_SEPARATORS)
    return text + "\n"


def decode_stage(stage: str, text: str) -> Any:
    """Parse one stage file back to plain dicts/lists.

    Comparison across a bless run is on *parsed* structures, never on strings, so
    formatting drift can never present as a false divergence.
    """
    if stage not in _STAGE_FIELDS:
        raise ValueError(f"unknown corpus stage {stage!r}; expected one of {STAGES}")
    return json.loads(text)


def write_cell(trace: GenerationTrace, cell: Cell, *, root: Path | None = None) -> Path:
    """Write all `STAGES` of `trace` into `cell_dir(cell)`; return that directory."""
    target = cell_dir(cell, root=root)
    target.mkdir(parents=True, exist_ok=True)
    for stage in STAGES:
        (target / f"{stage}.json").write_text(
            encode_stage(trace, stage), encoding="utf-8"
        )
    return target


def read_cell(cell: Cell, *, root: Path | None = None) -> dict[str, Any]:
    """Read `cell`'s baseline back as `{stage: parsed}` for every stage in `STAGES`."""
    source = cell_dir(cell, root=root)
    return {
        stage: decode_stage(
            stage, (source / f"{stage}.json").read_text(encoding="utf-8")
        )
        for stage in STAGES
    }
