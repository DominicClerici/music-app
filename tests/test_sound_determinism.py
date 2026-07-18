"""PHASE_7 §13.5 sound-stage determinism (DoD 5).

Two proofs, over the two §9 worked examples:

1. **Zero-draw on the `sound` stream.** The sound-design stage is a pure
   lookup+evaluate (D3, §3.4): `rng` — the reserved `sound` seed stream — is
   accepted for interface uniformity and never drawn from (ROADMAP inv. 5). A
   `CountingRng` (a `random.Random` subclass counting every primitive draw —
   `random()` and `getrandbits()`, through which every stdlib RNG method routes)
   is passed to `sound_design`; the draw count is exactly 0 for both examples.
   This is asserted at the real pipeline seam: `generate_plan` → `resolve_pack`
   → `sound_design(plan, pack.timbres, CountingRng(0))`, exactly the call the
   orchestrator makes with `stream_rng(..., "sound")`.

2. **Repeated-run identity.** `generate_track(params)` twice yields byte-identical
   documents (`model_dump(by_alias=True, exclude_none=True)` equal) — the whole
   pipeline, sound stage included, is deterministic. (The whole-pipeline draw
   totals are pinned separately in `test_pipeline_determinism.py`; this test's
   job is the sound-stage's own zero-draw + the end-to-end reproducibility that
   its determinism underwrites.)
"""

from __future__ import annotations

import random

import pytest

from trackgen.interpreter.stage import generate_plan
from trackgen.packs import resolve_pack
from trackgen.pipeline import generate_track
from trackgen.sound.stage import sound_design

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {
    "styleFamily": "jazz",
    "mood": "melancholic",
    "maxLengthSec": 240,
    "seed": "1ps9wxb",
}
_EXAMPLES: dict[str, dict[str, object]] = {"pop": _POP, "jazz": _JAZZ}


class CountingRng(random.Random):
    """A `random.Random` that counts every draw. Overriding the two C-level
    primitives (`random`, `getrandbits`) catches all entropy consumption: every
    stdlib RNG method — `randrange`, `randint`, `choice`, `shuffle`, … — bottoms
    out in one of them."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.draws = 0

    def random(self) -> float:
        self.draws += 1
        return super().random()

    def getrandbits(self, k: int) -> int:
        self.draws += 1
        return super().getrandbits(k)


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_sound_stream_zero_draws(params: dict[str, object]) -> None:
    """DoD 5 — the sound stage consumes zero draws from its `sound` stream."""
    style_family = params["styleFamily"]
    assert isinstance(style_family, str)
    plan = generate_plan(params)
    pack = resolve_pack(style_family)
    assert pack is not None and pack.timbres is not None

    rng = CountingRng(0)
    sound_design(plan, pack.timbres, rng)
    assert rng.draws == 0, (style_family, rng.draws)


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop", "jazz"])
def test_repeated_run_identity(params: dict[str, object]) -> None:
    """DoD 5 — the full pipeline (sound stage included) is bit-identical across
    repeated runs."""
    first = generate_track(params).model_dump(by_alias=True, exclude_none=True)
    second = generate_track(params).model_dump(by_alias=True, exclude_none=True)
    assert first == second
