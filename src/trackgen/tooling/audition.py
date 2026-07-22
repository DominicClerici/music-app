"""Audition core (PHASE_8 §9.1) — the edit->hear authoring loop.

`build_audition` renders a `TrackDocument` from `(pack, mood, seed)` and applies
the `--section`/`--solo`/`--mute` filters. Filtering happens on the **phrase
list** upstream of `serialize`, never on the emitted (frozen) document, so the
§7 reverb-bus omission rule and the rest of sound-design recompute from the
surviving tracks (a post-filter of `doc.tracks` would leave `buses` stale).

With no filters the phrase list is `trace.phrases_stage7` verbatim and `serialize`
is a pure function, so the output is byte-identical to
`to_json(generate_track(raw_params))` — audition adds no divergence on the
production path.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Sequence
from pathlib import Path

import typer

from trackgen.parts.generators import _TRACK_ORDER
from trackgen.pipeline import generate_trace, serialize
from trackgen.pipeline.explain import ExplainCollector
from trackgen.schema.document import TrackDocument
from trackgen.schema.ir import Phrase, SongForm

_TICKS_PER_BAR = 1920

_ROLES: frozenset[str] = frozenset({"drums", "bass", "comping", "pads"})
_DRUM_TRACK_IDS: frozenset[str] = frozenset(_TRACK_ORDER)

_PLAY_DOC_NAME = "audition.trackdoc.json"


def build_audition(
    raw_params: dict[str, object],
    *,
    section: str | None = None,
    solo: str | None = None,
    mute: str | None = None,
    explain: ExplainCollector | None = None,
) -> TrackDocument:
    """Render `raw_params` and apply the audition filters (§9.1).

    `--solo` and `--mute` are applied solo-then-mute when both are given.
    Filtering is upstream of `serialize` so `buses`/sound-design recompute. An
    `ExplainCollector`, when passed, is threaded into `generate_trace` to capture
    the §9.3 selection log.
    """
    trace = generate_trace(raw_params, explain=explain)
    phrases: list[Phrase] = trace.phrases_stage7

    if section is not None:
        phrases = _filter_section(phrases, trace.song_form, section)
    if solo is not None:
        phrases = _apply_target(phrases, solo, keep=True)
    if mute is not None:
        phrases = _apply_target(phrases, mute, keep=False)

    return serialize(
        trace.plan,
        trace.song_form,
        phrases,
        trace.sound_design,
        tempo_events=trace.tempo_events,
        params=raw_params,
    )


def _filter_section(
    phrases: list[Phrase], form: SongForm, section_id: str
) -> list[Phrase]:
    """Keep only phrase notes whose absolute tick lies in `section_id`'s span."""
    match = next((s for s in form.sections if s.id == section_id), None)
    if match is None:
        valid = ", ".join(s.id for s in form.sections)
        raise typer.BadParameter(
            f"unknown --section {section_id!r}; valid ids: {valid}"
        )
    start = match.start_bar * _TICKS_PER_BAR
    end = (match.start_bar + match.length_bars) * _TICKS_PER_BAR
    return [
        phrase.model_copy(
            update={"notes": [n for n in phrase.notes if start <= n.ticks < end]}
        )
        for phrase in phrases
    ]


def _apply_target(phrases: list[Phrase], target: str, *, keep: bool) -> list[Phrase]:
    """Solo (`keep=True`) or mute (`keep=False`) a role or drum sub-track id.

    Drum phrases are already partitioned one-per-voice-track (`track_id`), so a
    drum sub-track target filters whole phrases by `track_id`, exactly parallel
    to the role branch — this also carries the untagged §6 transition notes
    (fills/crashes/holds) that live in the right `track_id` phrase.
    """
    if target in _ROLES:
        return [p for p in phrases if (p.role == target) == keep]

    if target in _DRUM_TRACK_IDS:
        return [p for p in phrases if (p.track_id == target) == keep]

    valid = ", ".join(sorted(_ROLES) + sorted(_DRUM_TRACK_IDS))
    raise typer.BadParameter(f"unknown target {target!r}; valid: {valid}")


def parse_role_flavors(tokens: Sequence[str]) -> dict[str, str]:
    """Parse `role=flavor` tokens into a `roleFlavors` dict (last write wins).

    Each token may itself be a comma-separated list (`comping=piano,drums=tight_kit`),
    so a single `--role-flavors` string and repeated `--role-flavor` flags parse
    through the same path. Role/flavor names are not checked here — that is the
    §3.1 param validator's job downstream (`FLAVOR_UNKNOWN`/`ROLE_UNKNOWN`), which
    reports against pack data; this only enforces the `role=flavor` shape.
    """
    out: dict[str, str] = {}
    for token in tokens:
        for piece in token.split(","):
            piece = piece.strip()
            if not piece:
                continue
            if "=" not in piece:
                raise typer.BadParameter(
                    f"role-flavor entry {piece!r} must be of the form role=flavor"
                )
            role, flavor = (part.strip() for part in piece.split("=", 1))
            if not role or not flavor:
                raise typer.BadParameter(
                    f"role-flavor entry {piece!r} must be of the form role=flavor"
                )
            out[role] = flavor
    return out


def open_playground(rendered_json: str) -> None:
    """Write the doc into the playground and open it with a `?doc=` loader.

    A static server may be needed for the page's `fetch` (file:// is often
    blocked); we print the hint rather than manage a server process.
    """
    playground = Path(__file__).resolve().parents[3] / "playground"
    target = playground / _PLAY_DOC_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered_json + "\n", encoding="utf-8")

    url = (playground / "index.html").as_uri() + f"?doc={_PLAY_DOC_NAME}"
    typer.echo(
        "If the page can't fetch the doc (file:// is often blocked), serve it: "
        "`uv run python -m http.server 8012` from the playground dir, then open "
        f"http://localhost:8012/index.html?doc={_PLAY_DOC_NAME}"
    )
    webbrowser.open(url)
