"""Typer CLI entry point (PHASE_1 §2)."""

from pathlib import Path
from typing import Annotated

import typer

from trackgen.schema.export import DEFAULT_SCHEMA_PATH, export_schema

app = typer.Typer(help="trackgen: deterministic backing-track generation pipeline.")


@app.callback()
def main() -> None:
    """trackgen: deterministic backing-track generation pipeline."""


@app.command("export-schema")
def export_schema_command(
    out: Annotated[
        Path,
        typer.Option(
            "--out", help="Path to write the exported TrackDocument JSON Schema."
        ),
    ] = DEFAULT_SCHEMA_PATH,
) -> None:
    """Export the `TrackDocument` JSON Schema (the client contract) to disk."""
    written = export_schema(out)
    typer.echo(f"Wrote schema to {written}")


if __name__ == "__main__":
    app()
