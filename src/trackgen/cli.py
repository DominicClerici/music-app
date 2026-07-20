"""Typer CLI entry point (PHASE_1 §2)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from trackgen.packs.loader import STYLES_ROOT
from trackgen.pipeline import generate_trace, to_json
from trackgen.pipeline.explain import ExplainCollector, render_explain
from trackgen.schema.export import DEFAULT_SCHEMA_PATH, export_schema
from trackgen.tooling.audition import build_audition, open_playground
from trackgen.tooling.calibrate import calibrate
from trackgen.tooling.lint import run_lint

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
    explain: Annotated[
        bool,
        typer.Option(
            "--explain", help="Print the per-slot selection log (§9.3) to stderr."
        ),
    ] = False,
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

    collector = ExplainCollector() if explain else None
    doc = generate_trace(raw_params, explain=collector).document
    rendered = to_json(doc)
    if collector is not None:
        typer.echo(render_explain(collector), err=True)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Wrote track to {out}")
    else:
        typer.echo(rendered)


@app.command("audition")
def audition_command(
    pack: Annotated[
        str, typer.Option("--pack", help="Style pack id (-> styleFamily), required.")
    ],
    mood: Annotated[
        str | None, typer.Option("--mood", help="Mood id, e.g. happy or melancholic.")
    ] = None,
    seed: Annotated[
        str | None, typer.Option("--seed", help="Base36 u64 master seed.")
    ] = None,
    tempo: Annotated[
        int | None, typer.Option("--tempo", help="Override the tempo (-> tempoBpm).")
    ] = None,
    section: Annotated[
        str | None,
        typer.Option("--section", help="Render one section's tick span, e.g. solo-2."),
    ] = None,
    solo: Annotated[
        str | None,
        typer.Option("--solo", help="Keep only this role or drum sub-track id."),
    ] = None,
    mute: Annotated[
        str | None,
        typer.Option("--mute", help="Drop this role or drum sub-track id."),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Write the TrackDocument JSON here."),
    ] = None,
    play: Annotated[
        bool,
        typer.Option("--play", help="Write into the playground and open it."),
    ] = False,
    explain: Annotated[
        bool,
        typer.Option(
            "--explain", help="Print the per-slot selection log (§9.3) to stderr."
        ),
    ] = False,
) -> None:
    """Render a track for the edit->hear loop, optionally filtered (§9.1)."""
    raw_params: dict[str, object] = {"styleFamily": pack}
    if mood is not None:
        raw_params["mood"] = mood
    if seed is not None:
        raw_params["seed"] = seed
    if tempo is not None:
        raw_params["tempoBpm"] = tempo

    collector = ExplainCollector() if explain else None
    doc = build_audition(
        raw_params, section=section, solo=solo, mute=mute, explain=collector
    )
    rendered = to_json(doc)
    if collector is not None:
        typer.echo(render_explain(collector), err=True)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Wrote track to {out}")
    if play:
        open_playground(rendered)
    if out is None and not play:
        typer.echo(rendered)


@app.command("lint")
def lint_command(
    pack_dir: Annotated[
        Path,
        typer.Argument(help="Style pack directory, e.g. styles/pop_rock/."),
    ],
) -> None:
    """Lint a style pack: loader-rule errors + authoring-quality warnings (§9.2).

    Exit code is non-zero iff any error fired; warnings never fail the command.
    """
    code = run_lint(pack_dir)
    raise typer.Exit(code)


@app.command("calibrate")
def calibrate_command(
    pack: Annotated[
        str,
        typer.Argument(help="Style pack dir or id, e.g. styles/pop_rock/ or pop_rock."),
    ],
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help="Write calibration.yaml here (default styles/<pack>/).",
        ),
    ] = None,
) -> None:
    """Batch-render a pack and write its `calibration.yaml` (§9.3).

    Accepts a pack directory or a bare pack id; the §9.3 report is printed and the
    write location is echoed.
    """
    pack_id = Path(pack).name
    calibrate(pack_id, out_path=out, report=True)
    target = out if out is not None else STYLES_ROOT / pack_id / "calibration.yaml"
    typer.echo(f"Wrote calibration to {target}")


if __name__ == "__main__":
    app()
