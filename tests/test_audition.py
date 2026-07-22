"""Audition CLI core (PHASE_8 §9.1 / SESSION_17 T1).

Proves the edit->hear render + `--section`/`--solo`/`--mute` filters, the
production-path byte-identity (unfiltered == `generate_track`), and the CLI
wiring (`--out`, `--play`).
"""

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.pipeline import generate_track, to_json
from trackgen.schema.document import TrackDocument
from trackgen.tooling.audition import build_audition, parse_role_flavors

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {"styleFamily": "jazz", "seed": "1ps9wxb"}
# pop_rock/happy/7 carries §6 fill notes in its tom_low and snare tracks — the
# discriminating case for drum sub-track filtering by track_id (untagged fills).
_POP_FILLS: dict[str, object] = {
    "styleFamily": "pop_rock",
    "mood": "happy",
    "seed": "7",
}

runner = CliRunner()


def test_audition_reproducible() -> None:
    """Same (pack, mood, seed) -> byte-identical JSON across two calls."""
    first = to_json(build_audition(_POP))
    second = to_json(build_audition(_POP))
    assert first == second


def test_unfiltered_equals_generate_track() -> None:
    """The no-filter path adds no divergence over the production pipeline."""
    for params in (_POP, _JAZZ):
        assert to_json(build_audition(params)) == to_json(generate_track(params))


def test_section_keeps_only_span_notes() -> None:
    """`--section solo-2` keeps only notes inside that section's tick span."""
    # jazz/1ps9wxb has solo-1/solo-2/solo-3; solo-2 spans bars 24..36 -> ticks.
    doc = build_audition(_JAZZ, section="solo-2")
    ticks = [n.ticks for track in doc.tracks for n in track.notes]
    assert ticks, "solo-2 should retain notes"
    assert all(46080 <= t < 69120 for t in ticks)


def test_section_unknown_id_raises() -> None:
    with pytest.raises(typer.BadParameter) as exc:
        build_audition(_JAZZ, section="solo-99")
    # error lists the valid ids
    assert "solo-2" in str(exc.value)


def test_solo_role_keeps_only_that_role() -> None:
    doc = build_audition(_POP, solo="drums")
    assert {track.role for track in doc.tracks} == {"drums"}


def test_mute_role_drops_that_role() -> None:
    doc = build_audition(_POP, mute="pads")
    assert all(track.id != "pads" for track in doc.tracks)


def test_mute_last_reverb_sender_recomputes_buses() -> None:
    """Filtering upstream of serialize recomputes `buses` (§7 omission rule).

    Unfiltered pop_rock sends drums/comping/pads to `reverb`. `--solo bass`
    (bass sends nothing) removes every reverb sender, so the bus must vanish —
    a stale post-filter of `doc.tracks` would leave it behind.
    """
    unfiltered = build_audition(_POP)
    assert {b.id for b in unfiltered.buses} == {"reverb"}

    soloed = build_audition(_POP, solo="bass")
    assert [t.id for t in soloed.tracks] == ["bass"]
    assert {b.id for b in soloed.buses} == set()


def test_mute_hats_drops_only_hat_notes() -> None:
    """Drum sub-track mute drops the voice-tagged notes, keeping the drums."""
    doc = build_audition(_POP, mute="hats")
    drum_tracks = [t for t in doc.tracks if t.role == "drums"]
    assert drum_tracks, "drums should survive muting one sub-track"
    assert all(t.id != "hats" for t in doc.tracks)


def test_solo_hats_isolates_hat_subtrack() -> None:
    doc = build_audition(_POP, solo="hats")
    assert [t.id for t in doc.tracks] == ["hats"]


def _notes_in(doc: TrackDocument, track_id: str) -> int:
    return sum(len(t.notes) for t in doc.tracks if t.id == track_id)


def test_mute_tom_low_removes_fill_tagged_toms() -> None:
    """`--mute tom_low` removes the whole tom_low track — including its untagged
    §6 fill notes, which the old tag-matching filter left behind."""
    full = build_audition(_POP_FILLS)
    assert _notes_in(full, "tom_low") > 0, "seed must have tom_low fill notes"

    doc = build_audition(_POP_FILLS, mute="tom_low")
    assert all(t.id != "tom_low" for t in doc.tracks)
    assert _notes_in(doc, "tom_low") == 0


def test_solo_tom_low_isolates_track_with_its_notes() -> None:
    """`--solo tom_low` keeps exactly the tom_low track WITH its notes (fill notes
    included) — not silence, which the old tag-matching filter produced."""
    doc = build_audition(_POP_FILLS, solo="tom_low")
    assert [t.id for t in doc.tracks] == ["tom_low"]
    assert _notes_in(doc, "tom_low") > 0


def test_mute_snare_removes_fill_tagged_snares() -> None:
    """`--mute snare` removes every snare note, including the fill-tagged snares
    the old filter cross-contaminated back in."""
    full = build_audition(_POP_FILLS)
    assert _notes_in(full, "snare") > 0

    doc = build_audition(_POP_FILLS, mute="snare")
    assert all(t.id != "snare" for t in doc.tracks)
    assert _notes_in(doc, "snare") == 0


def test_unknown_target_raises() -> None:
    with pytest.raises(typer.BadParameter):
        build_audition(_POP, solo="cowbell")


def test_solo_then_mute_applied_in_order() -> None:
    """When both are given, solo runs first, then mute (§9.1)."""
    doc = build_audition(_POP, solo="drums", mute="hats")
    assert {t.role for t in doc.tracks} == {"drums"}
    assert all(t.id != "hats" for t in doc.tracks)


def test_cli_out_writes_file_and_creates_parents(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "audition.trackdoc.json"
    result = runner.invoke(
        app, ["audition", "--pack", "pop_rock", "--seed", "1ps9wxb", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tracks"]


def test_cli_default_echoes_json() -> None:
    result = runner.invoke(app, ["audition", "--pack", "pop_rock", "--seed", "1ps9wxb"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["tracks"]


def test_cli_requires_pack() -> None:
    result = runner.invoke(app, ["audition", "--seed", "1ps9wxb"])
    assert result.exit_code != 0


def _comping_instrument(doc: TrackDocument) -> object:
    for track in doc.tracks:
        if track.id == "comping":
            return track.instrument
    raise AssertionError("no comping track")


def test_role_flavors_changes_document() -> None:
    """A non-default comping flavor changes the rendered patch (flag is real)."""
    default = build_audition(_POP)
    flavored = build_audition({**_POP, "roleFlavors": {"comping": "piano"}})
    assert to_json(default) != to_json(flavored)
    assert _comping_instrument(default) != _comping_instrument(flavored)


def test_ensemble_preset_changes_document() -> None:
    default = build_audition(_POP)
    driven = build_audition({**_POP, "ensemblePreset": "driven"})
    assert to_json(default) != to_json(driven)


def test_parse_role_flavors_comma_and_repeat() -> None:
    assert parse_role_flavors(["comping=piano,drums=tight_kit"]) == {
        "comping": "piano",
        "drums": "tight_kit",
    }
    assert parse_role_flavors(["comping=piano", "drums=tight_kit"]) == {
        "comping": "piano",
        "drums": "tight_kit",
    }


def test_parse_role_flavors_rejects_malformed() -> None:
    with pytest.raises(typer.BadParameter):
        parse_role_flavors(["comping"])
    with pytest.raises(typer.BadParameter):
        parse_role_flavors(["=piano"])


def test_cli_role_flavors_flag_changes_render() -> None:
    default = runner.invoke(
        app, ["audition", "--pack", "pop_rock", "--seed", "1ps9wxb"]
    )
    flavored = runner.invoke(
        app,
        [
            "audition",
            "--pack",
            "pop_rock",
            "--seed",
            "1ps9wxb",
            "--role-flavors",
            "comping=piano",
        ],
    )
    assert default.exit_code == 0 and flavored.exit_code == 0, flavored.output
    assert json.loads(default.output) != json.loads(flavored.output)


def test_cli_ensemble_flag_changes_render() -> None:
    default = runner.invoke(
        app, ["audition", "--pack", "pop_rock", "--seed", "1ps9wxb"]
    )
    driven = runner.invoke(
        app,
        ["audition", "--pack", "pop_rock", "--seed", "1ps9wxb", "--ensemble", "driven"],
    )
    assert driven.exit_code == 0, driven.output
    assert json.loads(default.output) != json.loads(driven.output)


def test_cli_invalid_flavor_errors_cleanly() -> None:
    result = runner.invoke(
        app,
        [
            "audition",
            "--pack",
            "pop_rock",
            "--seed",
            "1ps9wxb",
            "--role-flavors",
            "comping=not_a_flavor",
        ],
    )
    assert result.exit_code != 0
    assert "FLAVOR_UNKNOWN" in result.output


def test_cli_invalid_ensemble_errors_cleanly() -> None:
    result = runner.invoke(
        app,
        [
            "audition",
            "--pack",
            "pop_rock",
            "--seed",
            "1ps9wxb",
            "--ensemble",
            "not_a_preset",
        ],
    )
    assert result.exit_code != 0
    assert "PRESET_UNKNOWN" in result.output


def test_cli_play_writes_playground_and_opens(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        "trackgen.tooling.audition.webbrowser.open", lambda url: opened.append(url)
    )
    result = runner.invoke(
        app, ["audition", "--pack", "pop_rock", "--seed", "1ps9wxb", "--play"]
    )
    assert result.exit_code == 0, result.output

    playground_doc = (
        Path(__file__).resolve().parents[1] / "playground" / "audition.trackdoc.json"
    )
    assert playground_doc.exists()
    assert json.loads(playground_doc.read_text(encoding="utf-8"))["tracks"]
    assert opened and "?doc=audition.trackdoc.json" in opened[0]
