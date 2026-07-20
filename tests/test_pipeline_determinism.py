"""Full-pipeline determinism (PHASE_5 DoD 9, SESSION_09 T4).

Three proofs over the real orchestrator `generate_track`:

1. Repeated-run identity — the definitive reproducibility proof: two runs of the
   same params dump bit-identical documents.
2. Total-draw counting shim — the whole pipeline consumes an EXACT, pinned number
   of RNG draws. Every draw is one `random.Random.randrange` call: `weighted_choice`
   issues exactly one `randrange` per pick (the sole entropy consumer for
   form/harmony/selection/walker), and the interpreter's auto-tempo pick is one
   direct `rng.randrange`. Counting `randrange` at the class level is therefore the
   true whole-pipeline total, robust to each stage's `from ... import
   weighted_choice` binding.

   Pinned totals (measured) and their decomposition against the independently
   pinned per-stream counts. SESSION_12 T1 wired the real stages 6 (transitions)
   and 7 (humanize), which draw from their own seed streams — the stale `stubs 0`
   summand is replaced by the two live `transitions` / `humanize` summands:

     pop  = 10561 = form 8 + harmony 8 + selection 13 + walker 0 + arrange 0
                 + interpreter (auto-tempo) 1 + transitions 61 + humanize 10470
     jazz =  5315 = form 1 + harmony 30 + selection 6 + walker 128 + arrange 0
                 + interpreter (auto-tempo) 1 + transitions 53 + humanize 5096

   Each summand is independently pinned by an existing chunk-1/2/3 golden, which
   this composed total cross-checks (non-vacuous):
     - form 8 / 1     : tests/test_form.py::test_draw_count_example_1/2 (PHASE_3 §11.5)
     - harmony 8 / 30 : tests/test_harmony_goldens.py::test_draw_count_example_1/2 (§10)
     - selection 13 / 6: tests/test_selection_goldens.py (§9.1; C5 thickened every
                         bank slot to ≥ 2 candidates → every active slot draws)
     - walker 0 / 128 : tests/test_generator_goldens.py + test_walker_goldens.py (§9.2)
     - arrange 0      : tests/test_arrange.py (zero-draw assertion)
     - transitions 61 / 53 : tests/test_transitions_goldens.py +
                             test_transitions_determinism.py (§3.8 device 14/10 +
                             drums-mutation 38/32 + comping-mutation 9/11)
     - humanize 10470 / 5096 : tests/test_humanizer_goldens.py (§5 counting-RNG shim)
   The interpreter auto-tempo draw is 1 for both examples (neither params dict
   pins a tempo, so `interpret` draws one tempo from the mood band).
3. Random-free pipeline modules — `pipeline/{orchestrator,serialize}.py` import no
   `random`/`time`/`datetime`/`secrets`/`uuid` (TID251 bans these at the import
   layer). The orchestrator itself makes no draws (it only wires stages); the
   draws counted in (2) all originate in the stages it calls — including the real
   transitions/humanize (whose own goldens pin their sub-totals) and the Phase-7
   sound-design stage, which draws zero (its own determinism test proves it).
"""

from __future__ import annotations

import ast
import random
from pathlib import Path

import pytest

from trackgen.pipeline import generate_track

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}

# Whole-pipeline total draw counts (measured; see module docstring decomposition).
_TOTAL_DRAWS: dict[str, tuple[dict[str, object], int]] = {
    "pop": (_POP, 10561),
    "jazz": (_JAZZ, 5315),
}

_SRC = Path(__file__).resolve().parents[1] / "src" / "trackgen" / "pipeline"
_PIPELINE_MODULES = ("orchestrator.py", "serialize.py")
_BANNED_IMPORTS = {"random", "time", "datetime", "secrets", "uuid"}


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_repeated_run_identity(params: dict[str, object]) -> None:
    """DoD 9 — the full pipeline is bit-identical across repeated runs."""
    first = generate_track(params).model_dump()
    second = generate_track(params).model_dump()
    assert first == second


@pytest.mark.parametrize("example", list(_TOTAL_DRAWS), ids=list(_TOTAL_DRAWS))
def test_total_draw_count(example: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD 9 — the whole pipeline consumes an EXACT pinned number of draws.

    `weighted_choice` calls `randrange` once per pick and the interpreter's
    tempo pick is one direct `randrange`, so counting `randrange` at the class
    level is the complete whole-pipeline total (see the module docstring for the
    per-stream decomposition, each summand cross-checked by an existing golden)."""
    params, expected = _TOTAL_DRAWS[example]
    real_randrange = random.Random.randrange
    calls = 0

    def counting(self: random.Random, *args: object, **kwargs: object) -> int:
        nonlocal calls
        calls += 1
        return real_randrange(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(random.Random, "randrange", counting)
    generate_track(params)
    monkeypatch.undo()

    assert calls == expected


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_generation_ignores_module_random_state(
    params: dict[str, object],
) -> None:
    """DoD 9 — every stage runs off its own seeded stream, so perturbing the
    global `random` module state around generation cannot change the output."""
    random.seed(1)
    first = generate_track(params).model_dump()
    random.seed(9_999_991)
    second = generate_track(params).model_dump()
    assert first == second


@pytest.mark.parametrize("module", _PIPELINE_MODULES)
def test_pipeline_modules_are_random_free(module: str) -> None:
    """DoD 9 — the new `pipeline/` modules import no `random`/wall-clock/entropy
    source (TID251 enforces this at the import layer; this asserts it directly so
    a regression is caught even if the lint config drifts). Combined with the
    total-draw shim, this confirms the orchestrator/serialize tail makes no draws
    of its own — every counted draw comes from a stage it calls."""
    tree = ast.parse((_SRC / module).read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".")[0])
    offending = imported_roots & _BANNED_IMPORTS
    assert not offending, (module, offending)
