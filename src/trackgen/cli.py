"""Typer CLI entry point (PHASE_1 §2)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from trackgen.pipeline import generate_track, to_json
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


@app.command("generate")
def generate_command(
    style_family: Annotated[
        str | None,
        typer.Option("--style-family", help="Style pack id, e.g. pop_rock or jazz."),
    ] = None,
    mood: Annotated[
        str | None, typer.Option("--mood", help="Mood id, e.g. happy or melancholic.")
    ] = None,
    seed: Annotated[
        str | None, typer.Option("--seed", help="Base36 u64 master seed.")
    ] = None,
    tempo_bpm: Annotated[
        int | None, typer.Option("--tempo-bpm", help="Override the tempo (BPM).")
    ] = None,
    tonic: Annotated[
        str | None, typer.Option("--tonic", help="Key tonic note, e.g. C or F#.")
    ] = None,
    mode: Annotated[
        str | None, typer.Option("--mode", help="Key mode, e.g. major or dorian.")
    ] = None,
    max_length_sec: Annotated[
        int | None,
        typer.Option("--max-length-sec", help="Target maximum length in seconds."),
    ] = None,
    params_file: Annotated[
        Path | None,
        typer.Option(
            "--params",
            help="Path to a JSON file of raw params; explicit flags override its keys.",
        ),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option(
            "--out", help="Write the TrackDocument JSON here (default stdout)."
        ),
    ] = None,
) -> None:
    """Generate a `TrackDocument` and write it as contract JSON (camelCase)."""
    raw_params: dict[str, object] = {}
    if params_file is not None:
        loaded = json.loads(params_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise typer.BadParameter("--params file must contain a JSON object")
        raw_params.update(loaded)

    if style_family is not None:
        raw_params["styleFamily"] = style_family
    if mood is not None:
        raw_params["mood"] = mood
    if seed is not None:
        raw_params["seed"] = seed
    if tempo_bpm is not None:
        raw_params["tempoBpm"] = tempo_bpm
    if max_length_sec is not None:
        raw_params["maxLengthSec"] = max_length_sec
    if tonic is not None or mode is not None:
        key: dict[str, str] = {}
        if tonic is not None:
            key["tonic"] = tonic
        if mode is not None:
            key["mode"] = mode
        raw_params["key"] = key

    if "styleFamily" not in raw_params:
        raise typer.BadParameter(
            "--style-family is required (or provide it via --params)"
        )

    doc = generate_track(raw_params)
    rendered = to_json(doc)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Wrote track to {out}")
    else:
        typer.echo(rendered)


if __name__ == "__main__":
    app()
