"""Pack linter CLI formatter (PHASE_8 §9.2).

Thin presentation layer over `packs.lint`: prints the errors tier then the
warnings tier (grouped by class, counted) and returns a process exit code that
is non-zero **iff** any error fired — warnings never fail the command.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import typer

from trackgen.packs.lint import (
    LintError,
    LintWarning,
    collect_pack_errors,
    collect_pack_warnings,
)
from trackgen.packs.loader import PackLoadError, load_pack

_WARNING_ORDER = (
    "variety-coverage",
    "grid-mixing",
    "unreachable-content",
    "dangling-gate",
    "weight-degeneracy",
)


def format_errors(errors: list[LintError]) -> list[str]:
    if not errors:
        return ["errors: none"]
    lines = [f"errors: {len(errors)}"]
    for err in errors:
        lines.append(f"  [{err.rule}] {err.file}: {err.message}")
    return lines


def format_warnings(warnings: list[LintWarning]) -> list[str]:
    if not warnings:
        return ["warnings: none"]
    by_kind: dict[str, list[LintWarning]] = defaultdict(list)
    for warn in warnings:
        by_kind[warn.kind].append(warn)
    lines = [f"warnings: {len(warnings)}"]
    ordered = [k for k in _WARNING_ORDER if k in by_kind]
    ordered += sorted(k for k in by_kind if k not in _WARNING_ORDER)
    for kind in ordered:
        group = by_kind[kind]
        lines.append(f"  {kind} ({len(group)}):")
        for warn in group:
            lines.append(f"    {warn.location}: {warn.message}")
    return lines


def run_lint(pack_dir: Path) -> int:
    """Lint `pack_dir`, echo the report, and return the exit code (non-zero iff
    any error)."""
    errors = collect_pack_errors(pack_dir)

    warnings: list[LintWarning] = []
    if not errors:
        # A pack with errors may not load; only compute warnings on a clean load.
        try:
            pack = load_pack(pack_dir)
        except PackLoadError:
            pack = None
        if pack is not None:
            warnings = collect_pack_warnings(pack, pack_dir)

    for line in format_errors(errors):
        typer.echo(line)
    for line in format_warnings(warnings):
        typer.echo(line)

    return 1 if errors else 0
