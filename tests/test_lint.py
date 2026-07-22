"""Tests for the pack linter (PHASE_8 §9.2, SESSION_17 T2).

Fixtures are built by copying a reference pack into `tmp_path` and mutating one
file, so each warning-class fixture is discriminating: the mutation flips exactly
its target class relative to the un-mutated copy.
"""

from __future__ import annotations

import re
import shutil
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.packs.lint import (
    _UNREACHABLE_MARKER,
    LintError,
    LintWarning,
    _reachable_rungs,
    collect_pack_errors,
    collect_pack_warnings,
)
from trackgen.packs.loader import load_pack, resolve_pack

_ID_LINE_RE = re.compile(r"^(\s*-\s*id:\s*)(\S+)")

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


def _mark_id(path: Path, pid: str) -> None:
    """Append a per-id `# expected-unreachable` marker to `pid`'s declaration."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        m = _ID_LINE_RE.match(ln.rstrip("\n"))
        if m is not None and m.group(2) == pid:
            nl = "\n" if ln.endswith("\n") else ""
            lines[i] = f"{m.group(1)}{pid}  # {_UNREACHABLE_MARKER} — test{nl}"
            path.write_text("".join(lines), encoding="utf-8")
            return
    raise AssertionError(f"id {pid} not found in {path.name}")


def _unmark_id(path: Path, pid: str) -> None:
    """Strip the trailing marker comment from `pid`'s declaration line, leaving a
    bare `- id: {pid}` (so exactly that pattern stops being silenced)."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, ln in enumerate(lines):
        m = _ID_LINE_RE.match(ln.rstrip("\n"))
        if m is not None and m.group(2) == pid and _UNREACHABLE_MARKER in ln:
            nl = "\n" if ln.endswith("\n") else ""
            lines[i] = f"{m.group(1)}{pid}{nl}"
            path.write_text("".join(lines), encoding="utf-8")
            return
    raise AssertionError(f"marked id {pid} not found in {path.name}")


def _strip_markers(pack_dir: Path) -> None:
    """Drop every per-id `# expected-unreachable` marker in a copied pack, so its
    unreachable-content lint reflects raw reachability (the pre-annotation view)."""
    for role in ("drums", "bass", "comping", "pads"):
        path = pack_dir / "patterns" / f"{role}.yaml"
        if not path.is_file():
            continue
        out: list[str] = []
        for ln in path.read_text(encoding="utf-8").splitlines(keepends=True):
            body = ln.rstrip("\n")
            if _UNREACHABLE_MARKER in body and _ID_LINE_RE.match(body):
                body = body[: body.index("#")].rstrip()
                out.append(body + ("\n" if ln.endswith("\n") else ""))
            else:
                out.append(ln)
        path.write_text("".join(out), encoding="utf-8")


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
    """Report the reference-pack warnings. Reference packs must load, so warnings
    compute.

    The per-mood/section-kind reachability lint surfaces a genuine dormancy in
    BOTH reference packs: their `energyRange` floor (verse 0.45 / bridge 0.40
    base at the coldest supported arousal) keeps every body section at rung 2+,
    so the authored rung-1 `main` patterns (the C-20 golden-blind completeness
    tier: `pr_dr_1`/`jz_dr_1`/…, selection-locked only, never rendered) are
    unreachable. Session 24 (C10) annotated each dead rung-1 main per-id with a
    `# expected-unreachable` marker citing C-20, so the reference packs now lint
    completely clean — every warning class, unreachable-content included, is
    silent. The markers are load-bearing and per-id (see
    `test_per_id_marker_is_load_bearing_and_file_scoped`)."""
    pack = resolve_pack(name)
    assert pack is not None
    warnings = collect_pack_warnings(pack, _STYLES / name)
    counts = Counter(w.kind for w in warnings)
    with capsys.disabled():
        print(f"\n[{name}] warning counts: {dict(counts)} (total {len(warnings)})")
    assert warnings == [], f"{name} should lint completely clean, got {counts}"


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


def test_unreachable_content_tracks_energy_range(tmp_path: Path) -> None:
    """The unreachable tier moves with `energyRange`, proving the check reads the
    real per-mood/section-kind reachable set and is not a no-op.

    Base pop_rock [0, 1.0] → reachable {2,3,4}: the rung-1 mains are the dead
    tier (the C-20 dormancy). Compressing to [0, 0.6] pushes the low sections
    DOWN into rung 1 (reachable becomes {1,2,3}) and strands the rung-4 mains
    instead — so the dead tier flips from rung 1 to rung 4.

    Both copies have their shipped per-id `# expected-unreachable` markers
    stripped first, so this reads the RAW reachable set (what the annotations
    document) rather than the silenced view."""
    base = _copy_pack("pop_rock", tmp_path / "base")
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    _strip_markers(base)
    _strip_markers(mutated)
    _edit(
        mutated / "forms.yaml",
        "energyRange: [0.00, 1.00]",
        "energyRange: [0.00, 0.60]",
    )
    base_c, mut_c = _warn_counts(base), _warn_counts(mutated)
    for other in ("grid-mixing", "dangling-gate", "weight-degeneracy"):
        assert mut_c.get(other, 0) == base_c.get(other, 0)

    base_rungs = {
        w.message.split("rung ")[1][0]
        for w in _warns(base)
        if w.kind == "unreachable-content"
    }
    mut_rungs = {
        w.message.split("rung ")[1][0]
        for w in _warns(mutated)
        if w.kind == "unreachable-content"
    }
    assert base_rungs == {"1"}, base_rungs
    assert mut_rungs == {"4"}, mut_rungs


def test_expected_unreachable_marker_silences_per_id(tmp_path: Path) -> None:
    """A per-id marker silences exactly its own pattern. Compressing pop_rock's
    energyRange to [0, 0.6] makes rung 4 the dead tier (unmarked in the shipped
    pack); marking one rung-4 drum main silences only it — its sibling and the
    other banks' rung-4 mains keep firing."""
    mutated = _copy_pack("pop_rock", tmp_path / "mut")
    _strip_markers(mutated)  # start from the raw view (shipped markers are rung-1)
    _edit(
        mutated / "forms.yaml",
        "energyRange: [0.00, 1.00]",
        "energyRange: [0.00, 0.60]",
    )
    drums = mutated / "patterns" / "drums.yaml"
    before = {w.location for w in _warns(mutated) if w.kind == "unreachable-content"}
    assert "patterns/drums.yaml (pr_dr_4)" in before
    assert "patterns/drums.yaml (pr_dr_4b)" in before

    _mark_id(drums, "pr_dr_4")
    after = {w.location for w in _warns(mutated) if w.kind == "unreachable-content"}
    # Exactly pr_dr_4 goes silent; its unmarked sibling still fires.
    assert "patterns/drums.yaml (pr_dr_4)" not in after
    assert "patterns/drums.yaml (pr_dr_4b)" in after
    # Other banks' rung-4 mains still fire — silence is per id, not file-wide.
    assert any("comping.yaml" in loc or "pads.yaml" in loc for loc in after)


def test_per_id_marker_is_load_bearing_and_file_scoped(tmp_path: Path) -> None:
    """The per-id marker DISCRIMINATES and is scoped to its own pattern id, not
    the file — the whole point of the per-id convention.

    blues ships unreachable-clean: its rung-1/2 dormant tier (C-23: the all-solo
    R2 arch floors every body section at rung 3) is silenced by per-id
    `# expected-unreachable` markers on each dead main. Unmark ONE dead id and
    exactly that id re-warns while its still-marked dead siblings in the SAME
    file stay silent; unmark a second, and it warns too — proving silence is per
    id, so a genuinely-broken (unmarked) sibling is never hidden by a marked
    neighbour."""
    pack = _copy_pack("blues", tmp_path)
    drums = pack / "patterns" / "drums.yaml"

    def dead(pack_dir: Path) -> set[str]:
        return {
            w.location
            for w in _warns(pack_dir)
            if w.kind == "unreachable-content" and "drums.yaml" in w.location
        }

    # Fully annotated → unreachable-clean.
    assert dead(pack) == set()

    # Strip one dead id's marker: only it re-warns; marked siblings stay silent.
    _unmark_id(drums, "bl_dr_1")
    assert dead(pack) == {"patterns/drums.yaml (bl_dr_1)"}

    # Strip a DIFFERENT dead id (a rung-2 main): it warns too; bl_dr_1b and
    # bl_dr_lcb remain silenced — silence did not leak to the file's siblings.
    _unmark_id(drums, "bl_dr_lc")
    assert dead(pack) == {
        "patterns/drums.yaml (bl_dr_1)",
        "patterns/drums.yaml (bl_dr_lc)",
    }


def test_reachable_rungs_per_mood_and_section_kind() -> None:
    """The reachable set is the per-mood × per-section-kind × per-position union
    over the real energy model, NOT the envelope span (which the old check read,
    reporting {1,2,3,4} for all three below). Known cases:

    - blues (all-solo, R2 arch, envelope [0.15, 0.95]): the solo floor lands at
      rung 3, so only {3, 4} — rungs 1-2 never (C-23).
    - fusion_jazz (envelope [0.20, 0.95]): rung 1 is dead grid-wide → {2, 3, 4}
      (C-28).
    - pop_rock (envelope [0.00, 1.00]): the verse/bridge base energy keeps rung 1
      dead even at the full envelope → {2, 3, 4} (the reference-pack dormancy)."""
    assert _reachable_rungs(load_pack(_STYLES / "blues")) == {3, 4}
    assert _reachable_rungs(load_pack(_STYLES / "fusion_jazz")) == {2, 3, 4}
    assert _reachable_rungs(load_pack(_STYLES / "pop_rock")) == {2, 3, 4}


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
        # rung 2 is reachable in pop_rock, so this isolates the dangling-gate
        # class (a rung-1 main would also trip unreachable-content).
        "    energyLevel: 2\n"
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
