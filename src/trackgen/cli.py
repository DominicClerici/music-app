"""Typer CLI entry point (PHASE_1 §2)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from trackgen.interpreter.stage import ParamsInvalid
from trackgen.packs.loader import STYLES_ROOT
from trackgen.pipeline import generate_trace, to_json
from trackgen.pipeline.explain import ExplainCollector, render_explain
from trackgen.schema.document import TrackDocument
from trackgen.schema.export import DEFAULT_SCHEMA_PATH, export_schema
from trackgen.tooling import corpus
from trackgen.tooling.ab import derive_trial_seeds, run_ab
from trackgen.tooling.audition import (
    build_audition,
    open_playground,
    parse_role_flavors,
)
from trackgen.tooling.bless import bless, format_result
from trackgen.tooling.calibrate import calibrate
from trackgen.tooling.lint import run_lint

app = typer.Typer(help="trackgen: deterministic backing-track generation pipeline.")


@app.callback()
def main() -> None:
    """trackgen: deterministic backing-track generation pipeline."""


def _params_error(err: ParamsInvalid) -> typer.BadParameter:
    """Render a `ParamsInvalid` catalog as a single clean `BadParameter`."""
    lines = "; ".join(f"{e.code} ({e.field}): {e.message}" for e in err.errors)
    return typer.BadParameter(lines)


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
    ensemble: Annotated[
        str | None,
        typer.Option(
            "--ensemble", help="Ensemble preset id (-> ensemblePreset), e.g. driven."
        ),
    ] = None,
    role_flavors: Annotated[
        str | None,
        typer.Option(
            "--role-flavors",
            help="Comma list of role=flavor, e.g. comping=piano,drums=tight_kit.",
        ),
    ] = None,
    role_flavor: Annotated[
        list[str] | None,
        typer.Option(
            "--role-flavor",
            help="A single role=flavor; repeatable. Merges with --role-flavors.",
        ),
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
    if ensemble is not None:
        raw_params["ensemblePreset"] = ensemble
    tokens = ([role_flavors] if role_flavors is not None else []) + (role_flavor or [])
    if tokens:
        raw_params["roleFlavors"] = parse_role_flavors(tokens)

    collector = ExplainCollector() if explain else None
    try:
        doc = build_audition(
            raw_params, section=section, solo=solo, mute=mute, explain=collector
        )
    except ParamsInvalid as err:
        raise _params_error(err) from err
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


_LISTENING_LOG = Path(__file__).resolve().parents[2] / "listening" / "log.jsonl"


@app.command("ab")
def ab_command(
    pack: Annotated[
        str, typer.Option("--pack", help="Style pack id (-> styleFamily), required.")
    ],
    axis: Annotated[
        str,
        typer.Option(
            "--axis",
            help="Compared axis as role=flavorA:flavorB, e.g. bass=a:b.",
        ),
    ],
    date: Annotated[
        str,
        typer.Option(
            "--date",
            help="Session date, passed in (wall-clock is banned), e.g. 2026-07-21.",
        ),
    ],
    mood: Annotated[
        str | None, typer.Option("--mood", help="Mood id, e.g. happy or melancholic.")
    ] = None,
    trials: Annotated[
        int, typer.Option("--trials", help="Number of A/B trials (§8.4 uses ~20).")
    ] = 20,
    blind_master: Annotated[
        str,
        typer.Option(
            "--blind-master",
            help="Seed text for the blinding + trial-seed streams; logged for replay.",
        ),
    ] = "trackgen-ab",
    log: Annotated[
        Path | None,
        typer.Option(
            "--log",
            help="Append the result record here (default listening/log.jsonl).",
        ),
    ] = None,
) -> None:
    """Blinded pairwise A/B listening test over two flavors (§8.4, instrument 2).

    Renders identical seeds two ways (variant A vs B on `--axis`), plays each
    pair in a blinded order, forces a "which sounds better" choice per trial, and
    scores the tally with an exact two-sided binomial test. One `{"type": "ab"}`
    record is appended to the listening log on completion.
    """
    role, _, flavors = axis.partition("=")
    flavor_a, sep, flavor_b = flavors.partition(":")
    if not role or not sep or not flavor_a or not flavor_b:
        raise typer.BadParameter(
            "--axis must be role=flavorA:flavorB, e.g. comping=piano:crunch_electric"
        )

    base: dict[str, object] = {"styleFamily": pack}
    if mood is not None:
        base["mood"] = mood
    variant_a: dict[str, object] = {**base, "roleFlavors": {role: flavor_a}}
    variant_b: dict[str, object] = {**base, "roleFlavors": {role: flavor_b}}

    trial_seeds = derive_trial_seeds(blind_master, trials)

    def decide(first: TrackDocument, second: TrackDocument) -> int:
        typer.echo("Option 1:")
        open_playground(to_json(first))
        typer.prompt(
            "Press enter when you have heard option 1", default="", show_default=False
        )
        typer.echo("Option 2:")
        open_playground(to_json(second))
        pick = 0
        while pick not in (1, 2):
            pick = typer.prompt("Which sounds better - 1 or 2?", type=int)
        return pick - 1

    try:
        result = run_ab(
            variant_a, variant_b, trial_seeds, decide, blind_master=blind_master
        )
    except ParamsInvalid as err:
        raise _params_error(err) from err

    record = {
        "type": "ab",
        "date": date,
        "pack": pack,
        "mood": mood,
        "axis": axis,
        "variantA": variant_a,
        "variantB": variant_b,
        "blindMaster": blind_master,
        "trialSeeds": trial_seeds,
        "n": result.n,
        "winsA": result.wins_a,
        "winsB": result.wins_b,
        "pValue": result.p_value,
    }
    target = log if log is not None else _LISTENING_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    typer.echo(
        f"A/B complete: A={result.wins_a} B={result.wins_b} of {result.n}, "
        f"p={result.p_value:.4g}. Appended to {target}."
    )


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


@app.command("bless")
def bless_command(
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Rewrite the golden baselines (commit them on their own).",
        ),
    ] = False,
    pack: Annotated[
        str | None,
        typer.Option(
            "--pack",
            help="Only bless this pack's corpus cells, e.g. pop_rock (default: all).",
        ),
    ] = None,
) -> None:
    """Re-render the golden corpus and report its semantic diff (§8.2).

    Exit code is non-zero iff a divergence exists and `--approve` was not passed.
    `--approve` refuses when a note-affecting change is not accompanied by a
    `generatorVersion` bump; a first capture is never a divergence.

    `--pack` scopes the run to one pack, so investigating a pack-data change does
    not re-render and re-report every cell in the corpus.
    """
    cells: list[corpus.Cell] | None = None
    if pack is not None:
        all_cells = corpus.corpus_cells()
        known = sorted({cell.pack for cell in all_cells})
        if pack not in known:
            raise typer.BadParameter(
                f"unknown corpus pack {pack!r}; expected one of {', '.join(known)}",
                param_hint="--pack",
            )
        cells = [cell for cell in all_cells if cell.pack == pack]

    result = bless(approve=approve, cells=cells)
    typer.echo(format_result(result, approve=approve))
    if result.refusal is not None or (result.divergent and not approve):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
