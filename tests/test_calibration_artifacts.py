"""Byte-reproduction pin for the committed `calibration.yaml` artifacts (GAP-2).

`styles/<pack>/calibration.yaml` is a *generated, committed* artifact (PHASE_8
§9.3): `trackgen calibrate` batch-renders the pack over its supported moods x a
fixed seed set and writes the Layer-2 thresholds + Layer-3 bands. Because it is
generated from the generator, it goes stale whenever generator content changes —
and unlike the golden corpus it has no `generatorVersion` guard, because it is
not a corpus cell. That is exactly how pop_rock's and jazz's artifacts drifted
silently at `9661d06` ("pad ladders monotone", gv 0.1.3), which re-blessed eight
pads-only golden cells but never re-ran `calibrate` (SESSION_23 F3).

This module closes that hole by regenerating each pack's artifact into `tmp_path`
and asserting the bytes equal what is committed. The shape is deliberate
(S23-7): a legitimate re-bless *regenerates* the file, so this test follows
along with nothing to hand-update and cannot rot into a rubber stamp.

**Scope — GAP-2 is closed for BANDS ONLY, not for thresholds.** This docstring
claimed "drift in any band, threshold, mood, or key ordering" until SESSION_23
T10 (lens C), which disproved the threshold half by mutation: setting fusion's
`comping` threshold to 0.5 **survives** this test. The reason is S23-11 — to make
byte-reproduction and hand-tuned per-pack thresholds compatible, `calibrate()`
now *preserves* a committed artifact's `l2Thresholds` rather than regenerating
them. A preserved value reproduces itself trivially, so a corrupted threshold is
structurally invisible here. Bands, moods and key ordering are all still fully
covered: those remain derived from the batch render.

The remaining backstop for thresholds is weak and known: `test_quality_layer2.py
::test_load_l2_thresholds_reads_blessed_artifact` asserts only `0.0 < bass <= 1.0`
(which 0.5 satisfies) over pop_rock and jazz. A real per-pack threshold pin is
C10 work, tracked there rather than bolted on here — this module's subject is
reproduction, and a value that is preserved by design cannot be pinned by a
reproduction test.

Cost is ~0.4-1.2 s CPU per pack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from trackgen.packs.loader import STYLES_ROOT
from trackgen.tooling.calibrate import calibrate

_PACKS: tuple[str, ...] = ("pop_rock", "jazz", "chill_lofi", "blues", "fusion_jazz")


def _leaves(node: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a parsed calibration doc to `dotted.path -> leaf` for diffing."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            out.update(_leaves(value, f"{prefix}.{key}" if prefix else str(key)))
        return out
    return {prefix: node}


def _explain(pack: str, committed: Path, regenerated: Path) -> str:
    """An actionable failure message: what differs, where, and how to diff it."""
    header = (
        f"{pack}: styles/{pack}/calibration.yaml does not reproduce.\n"
        f"  committed:   {committed}\n"
        f"  regenerated: {regenerated}\n"
        f"  diff them:   diff {committed} {regenerated}\n"
    )

    try:
        old = _leaves(yaml.safe_load(committed.read_text(encoding="utf-8")))
        new = _leaves(yaml.safe_load(regenerated.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:  # pragma: no cover - malformed artifact
        return header + f"  (could not parse for a structural diff: {exc})"

    only_committed = sorted(set(old) - set(new))
    only_regenerated = sorted(set(new) - set(old))
    changed = sorted(key for key in set(old) & set(new) if old[key] != new[key])

    lines = [
        header,
        f"  {len(changed)} changed leaf/leaves, "
        f"{len(only_committed)} removed, {len(only_regenerated)} added.",
    ]
    if changed:
        first = changed[0]
        lines.append(f"  first difference at `{first}`:")
        lines.append(f"    committed:   {old[first]!r}")
        lines.append(f"    regenerated: {new[first]!r}")
        if len(changed) > 1:
            rest = changed[1:6]
            lines.append(f"  also changed: {', '.join(rest)}")
            if len(changed) > 6:
                lines.append(f"  ... and {len(changed) - 6} more")
    if only_committed:
        lines.append(f"  only in committed:   {only_committed[:5]}")
    if only_regenerated:
        lines.append(f"  only in regenerated: {only_regenerated[:5]}")
    if not (changed or only_committed or only_regenerated):
        lines.append(
            "  parsed content is identical — the difference is byte-level only "
            "(key ordering, float repr, or trailing whitespace)."
        )
    lines.append(
        "  If the generator legitimately changed, re-run "
        f"`uv run trackgen calibrate {pack}` and commit the regenerated artifact."
    )
    return "\n".join(lines)


@pytest.mark.parametrize("pack", _PACKS)
def test_calibration_artifact_reproduces(pack: str, tmp_path: Path) -> None:
    """The committed artifact is byte-identical to a fresh `calibrate` run.

    Guards GAP-2: `calibration.yaml` is generator-derived but sits outside the
    corpus, so nothing else notices when generator content moves under it.
    """
    committed = STYLES_ROOT / pack / "calibration.yaml"
    assert committed.exists(), f"{pack}: no committed calibration.yaml"

    regenerated = tmp_path / pack / "calibration.yaml"
    calibrate(pack, out_path=regenerated)

    if regenerated.read_bytes() != committed.read_bytes():
        pytest.fail(_explain(pack, committed, regenerated), pytrace=False)
