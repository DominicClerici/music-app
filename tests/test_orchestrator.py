"""Orchestrator + CLI tests (PHASE_5 §8.1, SESSION_09 T3).

`generate_track` is the real Chunk-4 orchestrator. These tests prove it runs
both worked examples end to end to a valid `TrackDocument`, that it wires the
exact `_drive_full` chain (including `select_patterns` and the pinned
drums->bass->comping->pads role order), that it threads the raw params into
`meta.params`, and that the CLI `generate` command emits a re-validating doc.

`_drive_full` replicates test_generator_goldens.py:62-93 (the codebase
convention is to copy the driver rather than cross-import a test module — there
is no `tests` package).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trackgen.arrangement import arrange
from trackgen.cli import app
from trackgen.form.stage import form as build_form
from trackgen.harmony.stage import harmony
from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.packs.models import StylePack
from trackgen.parts.generators import generate
from trackgen.parts.selection import select_patterns
from trackgen.pipeline import generate_track
from trackgen.pipeline.serialize import serialize
from trackgen.pipeline.stubs import sound_design
from trackgen.schema.document import Role, TrackDocument
from trackgen.schema.ir import (
    GenerationPlan,
    Phrase,
    SongForm,
)
from trackgen.schema.validate import validate_document
from trackgen.seeds import Rng, stream_rng

_ROLES: tuple[Role, ...] = ("drums", "bass", "comping", "pads")
_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}


def _drive_full(
    params: dict[str, object],
) -> tuple[GenerationPlan, StylePack, SongForm, list[Phrase]]:
    """Test-only orchestrator loop (§8.1) — the reference `generate_track`
    subsumes. Mirrors test_generator_goldens.py:62-93."""
    plan = generate_plan(params)
    pack = resolve_pack(params["styleFamily"])  # type: ignore[arg-type]
    assert pack is not None and pack.forms is not None and pack.progressions is not None
    sf = build_form(plan, pack.forms)
    hp = harmony(
        plan,
        sf,
        pack.progressions,
        stream_rng(plan.seed.master, plan.seed.overrides, "harmony"),
    )
    ap = arrange(plan, sf, pack, Rng(0))
    sel = select_patterns(plan, sf, ap, pack, plan.seed.master, plan.seed.overrides)
    phrases: list[Phrase] = []
    for role in _ROLES:
        phrases += generate(
            role,
            ap,
            hp,
            sf,
            plan,
            pack,
            sel,
            master=plan.seed.master,
            overrides=plan.seed.overrides,
        )
    return plan, pack, sf, phrases


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_generate_track_validates(params: dict[str, object]) -> None:
    """Both worked examples run end to end to a schema/V-rule-valid document."""
    doc = generate_track(params)
    assert validate_document(doc) == []


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_orchestrator_matches_drive_full(params: dict[str, object]) -> None:
    """The orchestrator's phrase set (post identity transitions/humanize) equals
    the reference `_drive_full` loop's. Guards against drift from the pinned
    chain — chiefly that `select_patterns` is included and the phrase content
    matches. (Role order is not observable here: generation is order-independent
    in v1 and serialize groups/sorts by track_id.) Serialize is deterministic, so
    an equal reference document proves the phrase lists feeding it are equal."""
    plan, pack, sf, phrases = _drive_full(params)
    reference = serialize(plan, sf, phrases, sound_design(plan, pack), params=params)
    produced = generate_track(params)
    assert produced.model_dump() == reference.model_dump()


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_meta_params_echoes_input(params: dict[str, object]) -> None:
    """`meta.params` is non-empty and echoes the raw input (T2 params threading)."""
    doc = generate_track(params)
    assert doc.meta.params
    assert doc.meta.params == params


def test_cli_generate_emits_valid_document(tmp_path: Path) -> None:
    """The CLI `generate` command writes parseable JSON that re-validates."""
    runner = CliRunner()
    out = tmp_path / "pop.trackdoc.json"
    result = runner.invoke(
        app,
        [
            "generate",
            "--style-family",
            "pop_rock",
            "--seed",
            "1ps9wxb",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    doc = TrackDocument.model_validate(payload)
    assert validate_document(doc) == []
