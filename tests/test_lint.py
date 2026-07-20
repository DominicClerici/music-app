"""Tests for the pack linter (PHASE_8 §9.2, SESSION_17 T2).

Fixtures are built by copying a reference pack into `tmp_path` and mutating one
file, so each warning-class fixture is discriminating: the mutation flips exactly
its target class relative to the un-mutated copy.
"""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.packs.lint import (
    LintError,
    LintWarning,
    collect_pack_errors,
    collect_pack_warnings,
)
from trackgen.packs.loader import load_pack, resolve_pack

_STYLES = Path(__file__).resolve().parents[1] / "styles"
_REFERENCE_PACKS = ("pop_rock", "jazz")


def _copy_pack(name: str, dst: Path) -> Path:
    out = dst / name
    shutil.copytree(_STYLES / name, out)
    return out


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"anchor not found in {path.name}: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _append_pattern(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block + "\n", encoding="utf-8")


def _remove_pattern(path: Path, pid: str) -> None:
    """Delete the `- id: {pid}` list item block from a pattern bank file."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(
        (i for i, ln in enumerate(lines) if ln.strip() == f"- id: {pid}"), None
    )
    assert start is not None, f"pattern {pid} not found in {path.name}"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].lstrip()
        indent = len(lines[j]) - len(stripped)
        if lines[j].strip() and (indent < 2 or stripped.startswith("- ")):
            end = j
            break
    path.write_text("".join(lines[:start] + lines[end:]), encoding="utf-8")


def _warn_counts(pack_dir: Path) -> Counter[str]:
    pack = load_pack(pack_dir)
    return Counter(w.kind for w in collect_pack_warnings(pack, pack_dir))


def _warns(pack_dir: Path) -> list[LintWarning]:
    return collect_pack_warnings(load_pack(pack_dir), pack_dir)


# --- reference packs ----------------------------------------------------------


@pytest.mark.parametrize("name", _REFERENCE_PACKS)
def test_reference_pack_has_no_errors(name: str) -> None:
    """DoD-1: the reference packs load clean — zero lint errors."""
    assert collect_pack_errors(_STYLES / name) == []


@pytest.mark.parametrize("name", _REFERENCE_PACKS)
def test_reference_pack_still_resolves(name: str) -> None:
    """The linter does not alter loading — `resolve_pack` still succeeds."""
    assert resolve_pack(name) is not None


@pytest.mark.parametrize("name", _REFERENCE_PACKS)
def test_reference_pack_warnings_snapshot(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Report (do NOT assert clean) the reference-pack warnings — cleanliness is
    a later chunk's job. Reference packs must load, so warnings compute."""
    pack = resolve_pack(name)
    assert pack is not None
    warnings = collect_pack_warnings(pack, _STYLES / name)
    counts = Counter(w.kind for w in warnings)
    with capsys.disabled():
        print(f"\n[{name}] warning counts: {dict(counts)} (total {len(warnings)})")
    # Only the reroll-variety class is expected to speak on the raw reference
    # packs; the other four are structural and clean here.
    assert counts.get("grid-mixing", 0) == 0
    assert counts.get("unreachable-content", 0) == 0
    assert counts.get("dangling-gate", 0) == 0
    assert counts.get("weight-degeneracy", 0) == 0


# --- errors tier --------------------------------------------------------------


def test_multi_field_validation_surfaces_multiple_errors(tmp_path: Path) -> None:
    """A model with 2+ independent field errors surfaces >=2 LintErrors in one
    pass (the pydantic `.errors()` aggregation collect-mode relies on)."""
    pack = _copy_pack("pop_rock", tmp_path)
    _edit(pack / "manifest.yaml", "formatVersion: 1", "formatVersion: notanint")
    _edit(pack / "manifest.yaml", "tempoRange: [70, 180]", "tempoRange: notalist")

    errors = collect_pack_errors(pack)
    manifest_errors = [e for e in errors if e.file.endswith("manifest.yaml")]
    assert len(manifest_errors) >= 2


def test_malformed_pattern_reports_file_and_rule_tag(tmp_path: Path) -> None:
    """A malformed pattern surfaces a LintError with the correct file + parsed
    rule tag (PT1: lengthTicks must be a whole number of bars)."""
    pack = _copy_pack("pop_rock", tmp_path)
    _append_pattern(
        pack / "patterns" / "drums.yaml",
        "  - id: pr_dr_bad\n"
        "    role: drums\n"
        "    kind: main\n"
        "    energyLevel: 1\n"
        "    lengthTicks: 1000\n"
        "    weight: 1\n"
        "    events:\n"
        "      - { pos: 0, voice: kick, velocity: 0.9 }",
    )
    errors = collect_pack_errors(pack)
    pt1 = [e for e in errors if e.rule == "PT1" and e.file.endswith("drums.yaml")]
    assert pt1, f"expected a PT1 error on drums.yaml, got {errors}"


def test_clean_pack_returns_no_errors(tmp_path: Path) -> None:
    pack = _copy_pack("pop_rock", tmp_path)
    assert collect_pack_errors(pack) == []


# --- warnings tier: one discriminating fixture per class ----------------------


def test_variety_coverage_fires_when_slot_loses_reroll(tmp_path: Path) -> None:
    base = _copy_pack("pop_rock", tmp_path / "base")
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    # pr_dr_2b is the second rung-2 drum main; removing it collapses that slot
    # from 2 candidates to 1 (zero reroll variety).
    _remove_pattern(mutated / "patterns" / "drums.yaml", "pr_dr_2b")

    def rung2_fired(pack_dir: Path) -> bool:
        return any(
            w.kind == "variety-coverage" and "drums main rung 2" in w.location
            for w in _warns(pack_dir)
        )

    assert not rung2_fired(base)
    assert rung2_fired(mutated)


def test_grid_mixing_fires_only_grid_mixing(tmp_path: Path) -> None:
    base = _copy_pack("pop_rock", tmp_path / "base")
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    # A pattern authored with a straight-grid-only pos (240) AND a triplet-grid-
    # only pos (160): grid mixing (§3.1).
    _append_pattern(
        mutated / "patterns" / "drums.yaml",
        "  - id: pr_dr_mix\n"
        "    role: drums\n"
        "    kind: main\n"
        "    energyLevel: 2\n"
        "    lengthTicks: 1920\n"
        "    weight: 1\n"
        "    events:\n"
        "      - { pos: 240, voice: hat_closed, velocity: 0.5 }\n"
        "      - { pos: 160, voice: hat_open, velocity: 0.5 }",
    )
    base_c, mut_c = _warn_counts(base), _warn_counts(mutated)
    assert base_c.get("grid-mixing", 0) == 0
    assert mut_c["grid-mixing"] == 1
    for other in ("unreachable-content", "dangling-gate", "weight-degeneracy"):
        assert mut_c.get(other, 0) == base_c.get(other, 0)
    assert any(
        w.kind == "grid-mixing" and "pr_dr_mix" in w.location for w in _warns(mutated)
    )


def test_unreachable_content_fires_when_energy_range_shrinks(tmp_path: Path) -> None:
    base = _copy_pack("pop_rock", tmp_path / "base")
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    # energyRange [0, 0.6] -> reachable rungs {1,2,3}; rung-4 mains unreachable.
    _edit(
        mutated / "forms.yaml",
        "energyRange: [0.00, 1.00]",
        "energyRange: [0.00, 0.60]",
    )
    base_c, mut_c = _warn_counts(base), _warn_counts(mutated)
    assert base_c.get("unreachable-content", 0) == 0
    assert mut_c["unreachable-content"] >= 1
    for other in ("grid-mixing", "dangling-gate", "weight-degeneracy"):
        assert mut_c.get(other, 0) == base_c.get(other, 0)
    assert all(
        "rung 4" in w.message
        for w in _warns(mutated)
        if w.kind == "unreachable-content"
    )


def test_expected_unreachable_marker_silences_the_file(tmp_path: Path) -> None:
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    _edit(
        mutated / "forms.yaml",
        "energyRange: [0.00, 1.00]",
        "energyRange: [0.00, 0.60]",
    )
    drums = mutated / "patterns" / "drums.yaml"
    before = {w.location for w in _warns(mutated) if w.kind == "unreachable-content"}
    assert any("drums.yaml" in loc for loc in before)

    _edit(drums, "layeringOrder:", "# expected-unreachable\nlayeringOrder:")
    after = [w for w in _warns(mutated) if w.kind == "unreachable-content"]
    assert all("drums.yaml" not in w.location for w in after)
    # Other banks' rung-4 mains still fire — silence is file-scoped.
    assert any("comping.yaml" in w.location or "pads.yaml" in w.location for w in after)


def test_dangling_gate_fires_for_unenterable_tempo_band(tmp_path: Path) -> None:
    base = _copy_pack("pop_rock", tmp_path / "base")
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    # A gated pattern whose tempoBpm band [10, 20] no supported (mood, tempo)
    # cell can enter (pop_rock tempoRange is [70, 180]).
    _append_pattern(
        mutated / "patterns" / "drums.yaml",
        "  - id: pr_dr_dangle\n"
        "    role: drums\n"
        "    kind: main\n"
        "    energyLevel: 1\n"
        "    lengthTicks: 1920\n"
        "    weight: 1\n"
        "    eligibility: { tempoBpm: [10, 20] }\n"
        "    events:\n"
        "      - { pos: 0, voice: kick, velocity: 0.9 }",
    )
    base_c, mut_c = _warn_counts(base), _warn_counts(mutated)
    assert base_c.get("dangling-gate", 0) == 0
    assert mut_c["dangling-gate"] == 1
    for other in ("grid-mixing", "unreachable-content", "weight-degeneracy"):
        assert mut_c.get(other, 0) == base_c.get(other, 0)
    assert any(
        w.kind == "dangling-gate" and "pr_dr_dangle" in w.location
        for w in _warns(mutated)
    )


def test_weight_degeneracy_fires_for_dominant_entry(tmp_path: Path) -> None:
    base = _copy_pack("pop_rock", tmp_path / "base")
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    # none:100 vs {2,1,2} -> 100/105 = 95% > 90% of the mutation pool.
    _edit(
        mutated / "transitions.yaml",
        "drums:   { none: 10,",
        "drums:   { none: 100,",
    )
    base_c, mut_c = _warn_counts(base), _warn_counts(mutated)
    assert base_c.get("weight-degeneracy", 0) == 0
    assert mut_c["weight-degeneracy"] == 1
    for other in ("grid-mixing", "unreachable-content", "dangling-gate"):
        assert mut_c.get(other, 0) == base_c.get(other, 0)
    assert any(
        w.kind == "weight-degeneracy" and "mutation.drums" in w.location
        for w in _warns(mutated)
    )


# --- CLI ----------------------------------------------------------------------


def test_cli_clean_pack_exits_zero() -> None:
    result = CliRunner().invoke(app, ["lint", str(_STYLES / "pop_rock")])
    assert result.exit_code == 0
    assert "errors: none" in result.stdout


def test_cli_error_pack_exits_nonzero(tmp_path: Path) -> None:
    pack = _copy_pack("pop_rock", tmp_path)
    _append_pattern(
        pack / "patterns" / "drums.yaml",
        "  - id: pr_dr_bad\n"
        "    role: drums\n"
        "    kind: main\n"
        "    energyLevel: 1\n"
        "    lengthTicks: 1000\n"
        "    weight: 1\n"
        "    events:\n"
        "      - { pos: 0, voice: kick, velocity: 0.9 }",
    )
    result = CliRunner().invoke(app, ["lint", str(pack)])
    assert result.exit_code == 1
    assert "PT1" in result.stdout


def test_error_dataclass_shapes() -> None:
    err = LintError(file="f", rule="PT1", message="m")
    warn = LintWarning(kind="grid-mixing", location="l", message="m")
    assert (err.file, err.rule) == ("f", "PT1")
    assert (warn.kind, warn.location) == ("grid-mixing", "l")
