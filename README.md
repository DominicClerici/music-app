# trackgen

A backend pipeline that algorithmically composes complete, structured, instrumental
backing tracks from structured user parameters and emits them as a `TrackDocument` —
a Tone.js-oriented JSON document a browser client plays.

Tracks have real song structure (intro/verse/chorus/bridge/outro), a rhythm-section
arrangement (drums, bass, comping, pads) with fills and transitions, and synthesized
instrument tones matched to mood — deliberately leaving melodic space to play over.

The design is pinned across `plans/ROADMAP.md` and `plans/PHASE_1.md`–`PHASE_8.md`.
This repository is the implementation.

## Getting started

Requires [uv](https://docs.astral.sh/uv/). Python 3.12 is pinned via `.python-version`
and fetched automatically.

```sh
uv sync               # create the venv and install deps (from the committed uv.lock)
uv run pytest -n auto # run tests (parallel; style packs are cached, so this is fast)
uv run ruff check     # lint
uv run ruff format    # format
uv run mypy src       # type-check
```
