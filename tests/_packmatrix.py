"""Shared pack × mood × length × seed matrix dimensions (SESSION_23 T4).

Not a test module (leading underscore — pytest does not collect it), imported by
bare name like `_stage6_driver`.

PHASE_8 §14 item 9 requires every prior phase's property suites to run
pack-parameterized over **all** registered packs. This module is the single
place the pack dimension is defined, so adding a sixth pack is a pack-registry
edit and *no* test edit at all — `PACKS` is derived from `registered_styles()`,
never a hardcoded literal (the rule `tests/test_smoke_matrix.py::_supported_moods`
and `tests/test_interpreter.py::_pack_mood_matrix` already established).

Two length dimensions, not one (SESSION_23 decision S23-3): §14.9's "× lengths"
means *each phase's own pinned dimension*, so plan-level suites (form, harmony,
arrangement) keep the 39-value grid while render-level suites keep PHASE_6
§11.9's 3-value one. A uniform 39-grid on the render-level suites would be
43,875 full renders — minutes of wall clock for a single module.
"""

from __future__ import annotations

from functools import cache

from trackgen.interpreter.params import Params
from trackgen.interpreter.stage import interpret
from trackgen.packs import registered_styles, resolve_pack
from trackgen.packs.models import StylePack
from trackgen.schema.ir import GenerationPlan
from trackgen.seeds import from_base36

# --- the pack dimension ------------------------------------------------------

PACKS: tuple[str, ...] = tuple(sorted(registered_styles()))
"""Every registered style pack, sorted for a stable matrix order.

Derived, not literal: a new pack joins every property suite by being registered.
"""


MOOD_COUNTS: dict[str, int] = {
    "blues": 8,
    "chill_lofi": 8,
    "fusion_jazz": 8,
    "jazz": 10,
    "pop_rock": 11,
}
"""How many moods each registered pack declares, pinned.

The mood dimension would otherwise be self-checked: a non-vacuity test that
computes its expected cell count from `supported_moods()` and then compares it
against cells *also* built from `supported_moods()` reads the same source on
both sides, so `pop_rock` could silently fall from 11 moods to 2 and every such
test would still pass. These literals are the independent side of that
comparison — `supported_moods()` asserts against them, so a truncated mood list
fails loudly the way a dropped pack already does.

Kept here rather than in the six property modules so `_packmatrix` stays the one
file a sixth pack has to touch: registering it and adding its count here is the
whole edit.
"""


@cache
def cached_pack(pack_id: str) -> StylePack:
    """`resolve_pack` memoized per process, so a 20k-cell matrix does not
    re-parse the pack YAML on every cell.

    Process-local by construction, which is what `pytest -n auto` needs: each
    xdist worker warms its own cache and nothing crosses process boundaries.
    `load_pack` is itself cached underneath; this keeps the `None` check off the
    hot path and hands back a non-optional `StylePack`.
    """
    pack = resolve_pack(pack_id)
    assert pack is not None, pack_id
    return pack


def supported_moods(pack_id: str) -> tuple[str, ...]:
    """The pack's declared supported moods, sorted for a stable matrix order.

    Read off the pack rather than hardcoded, so a pack that gains a mood gains
    matrix cells automatically — but checked against `MOOD_COUNTS`, so a pack
    that *loses* one cannot shrink the matrix silently.
    """
    pack = cached_pack(pack_id)
    assert pack.interpreter is not None, pack_id
    moods = tuple(sorted(pack.interpreter.supported_moods))
    pinned = MOOD_COUNTS.get(pack_id)
    assert pinned is not None, (
        f"pack {pack_id!r} has no pinned mood count — add it to "
        "`_packmatrix.MOOD_COUNTS`"
    )
    assert len(moods) == len(set(moods)) == pinned, (pack_id, pinned, moods)
    assert pinned >= 2, (pack_id, pinned)
    return moods


def assert_mood_dimension_pinned() -> None:
    """The mood dimension matches `MOOD_COUNTS` in both directions.

    Called by every property suite's `test_matrix_non_vacuous`: it pairs the
    pinned counts with the registry (no pack unpinned, no pin without a pack)
    and forces the per-pack check inside `supported_moods` to run for all of
    them. Expected cell counts are then summed from `MOOD_COUNTS` rather than
    from `supported_moods`, so the comparison has two independent sides.
    """
    assert set(MOOD_COUNTS) == set(PACKS), (sorted(MOOD_COUNTS), PACKS)
    for pack_id in PACKS:
        supported_moods(pack_id)


def total_moods() -> int:
    """The pinned total mood count across every registered pack."""
    assert_mood_dimension_pinned()
    return sum(MOOD_COUNTS[pack_id] for pack_id in PACKS)


def pack_mood_pairs() -> tuple[tuple[str, str], ...]:
    """The (pack, mood) cross product over every registered pack."""
    return tuple(
        (pack_id, mood) for pack_id in PACKS for mood in supported_moods(pack_id)
    )


# --- the length dimensions ---------------------------------------------------

LENGTHS_PLAN: tuple[int, ...] = tuple(range(30, 601, 15))
"""Plan-level length grid: 30, 45, ..., 600 s (39 values).

The dimension the form / harmony / arrangement property trio has always used.
"""

LENGTHS_RENDER: tuple[int | None, ...] = (None, 180, 240)
"""Render-level length dimension, pinned by PHASE_6 §11.9 (3 values).

`None` means "omit `maxLengthSec`", i.e. exercise the auto-length path.
"""

# --- the seed dimension ------------------------------------------------------

SEEDS_25: tuple[str, ...] = (
    "17wdrqp",
    "2fsrjhe",
    "3np5b83",
    "4vlj2ys",
    "63hwuph",
    "7beamg6",
    "8jaoe6v",
    "9r725xk",
    "az3fxo9",
    "c6ztpey",
    "dew7h5n",
    "emsl8wc",
    "fuoz0n1",
    "h2lcsdq",
    "iahqk4f",
    "jie4bv4",
    "kqai3lt",
    "ly6vvci",
    "n639n37",
    "odznetw",
    "plw16kl",
    "qtseyba",
    "s1osq1z",
    "t9l6hso",
    "uhhk9jd",
)
"""25 pinned base36 u64 seeds (§14.9 pins "× 25 seeds"; §14.7 is Tooling).

Literals rather than a generator expression, matching `_SMOKE_SEEDS` in
`tests/test_smoke_matrix.py`: the matrix is byte-stable forever and a failure is
reproducible from the test id alone. These are exactly the values the previous
in-module formula `to_base36(((i + 1) * 2654435761) % (2**63))` produced for
`i` in `range(25)`, so pinning them moves no test.
"""


# --- plan construction -------------------------------------------------------


def build_plan(style: str, mood: str, max_len_sec: int, seed: str) -> GenerationPlan:
    """A real Phase-2 chain (params -> `interpret`), with the pack cached so the
    matrix does not re-parse YAML on every cell."""
    pack = cached_pack(style)
    params = Params.model_validate(
        {
            "styleFamily": style,
            "mood": mood,
            "maxLengthSec": max_len_sec,
            "seed": seed,
        }
    )
    return interpret(params, pack, from_base36(seed), {})
