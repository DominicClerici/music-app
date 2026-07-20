# trackgen — Command Reference

Every command you can run in this repo: project setup, the quality gates, and the
`trackgen` CLI itself. For *what* the project is, see `README.md`; for the pinned
design, see `plans/`.

## Project setup

| Command | What it does |
| --- | --- |
| `uv sync` | Creates the virtualenv and installs all dependencies from the committed `uv.lock` (exact pins — never resolves fresh). Run this once per checkout and after any `pyproject.toml`/`uv.lock` change. |

## Quality gates

All four must be green before committing (`CLAUDE.md`). Run with `uv run` so they execute inside the project's managed venv.

| Command | What it does |
| --- | --- |
| `uv run pytest` | Runs the full test suite (pytest + Hypothesis property tests). Currently ~4800 tests, ~11 minutes — use an extended timeout if running non-interactively. |
| `uv run ruff check .` | Lints the codebase, including the custom banned-API ruleset (`TID251`) that blocks `random`, `os.urandom`, `time`, `datetime.now`-family calls, `secrets`, and `uuid` outside `src/trackgen/seeds.py` (the determinism entropy boundary). |
| `uv run ruff format --check .` | Verifies formatting without rewriting files. Use plain `uv run ruff format .` (no `--check`) to actually reformat. |
| `uv run mypy` | Type-checks `src` and `tests` in strict mode. |

## `trackgen` CLI commands

Installed as a script entry point (`pyproject.toml` `[project.scripts]`); run via `uv run trackgen <command>` or, inside an activated venv, `trackgen <command>`. Two commands exist today (Phase 8 will add `audition`, `lint`, and `calibrate` — not yet built).

### `trackgen generate`

Runs the full 9-stage pipeline and writes a `TrackDocument` as contract JSON (camelCase keys).

Parameters can be supplied as flags, via `--params <file.json>` (a JSON object using the same camelCase keys the flags map to), or both — explicit flags always override a matching key from `--params`. Only `--style-family` is required; every other field either auto-derives from mood/pack data or falls back to a fixed default, matching the pipeline's "params (or auto)" design (`plans/ROADMAP.md` §3).

| Flag | Type | Default (if omitted) | Accepted values | What it does |
| --- | --- | --- | --- | --- |
| `--style-family` | string | *none — required* | Any pack under `styles/` with a `manifest.yaml`. Currently: `pop_rock`, `jazz`. (`styles/_stub` exists on disk but is explicitly excluded — not a valid value.) | Selects the style pack: its pattern vocabulary, progression pools, form tendencies, and timbre palette. Unknown value → `STYLE_UNKNOWN`. |
| `--mood` | string | The pack's declared default mood (`pop_rock` → `happy`, `jazz` → `nostalgic`). | One of the 12-word global vocabulary — `happy`, `energetic`, `triumphant`, `calm`, `dreamy`, `romantic`, `nostalgic`, `melancholic`, `dark`, `mysterious`, `tense`, `aggressive` — **intersected with the pack's `supportedMoods`.** `pop_rock` supports all but `mysterious`; `jazz` supports all but `triumphant` and `aggressive`. | Sets the valence/arousal anchor driving tempo, mode, density, dissonance, and timbre. A globally-valid mood the pack doesn't support → `MOOD_UNSUPPORTED`; not in the 12-word list at all → `MOOD_UNKNOWN`. |
| `--seed` | string | A fresh random seed drawn from OS entropy (`os.urandom`, the sole entropy boundary) — different every run. | A base36 string (digits `0-9a-z`, case-insensitive) decoding to an unsigned 64-bit integer (≤ 2⁶⁴−1). | The master seed all sub-seeds (form, harmony, drums, bass, …) derive from. Same params + same seed → byte-identical `TrackDocument`. Malformed → `SEED_INVALID`. Mutually exclusive with the params-file-only `seedText` field (`SEED_CONFLICT` if both set). |
| `--tempo-bpm` | integer | Auto-drawn: the mood's derived tempo center ±10%, clamped into the pack's tempo range, one seeded RNG draw picks the integer BPM. | Integer within the pack's declared `tempoRange`. `pop_rock`: 70–180. `jazz`: 60–220. | Overrides the song tempo outright — no RNG draw happens if you supply this. Out of the pack's range → `TEMPO_OUT_OF_RANGE`. |
| `--tonic` | string | The first tonic the pack declares for the resolved mode (e.g. `pop_rock` major → `E`, `jazz` major → `Bb`). | A note letter `A`–`G` (case-insensitive) plus an optional single accidental: `#` (sharp) or lowercase `b` (flat). No unicode ♯/♭, no double accidentals. | Sets the key's tonic pitch class. Unparseable → `KEY_TONIC_INVALID`. |
| `--mode` | string | The pack-menu mode closest to the mood's valence ("ideal rung": major ≥0.25, mixolydian ≥0, dorian ≥−0.30, minor ≥−0.65, else phrygian; ties break toward the brighter mode). | One of the pack's declared `modes` (subset of the engine's mode ladder `major`, `mixolydian`, `dorian`, `minor`, `phrygian` — Lydian excluded in v1). `pop_rock`: `major`, `minor`. `jazz`: `major`, `mixolydian`, `dorian`, `minor`. | Sets the key's mode. Not in the pack's menu → `MODE_UNSUPPORTED`. |
| `--max-length-sec` | integer | `180` | `30`–`600` inclusive. | Target maximum song length in seconds; the form generator fits section/repeat counts toward this ceiling, degrading (outro → intro-shrink → bridge) if it can't fit everything. Out of range → `LENGTH_OUT_OF_RANGE`. |
| `--params` | path | *(none)* | Path to a JSON file containing a JSON object of raw params (camelCase keys — `styleFamily`, `mood`, `tempoBpm`, `key: {tonic, mode}`, `maxLengthSec`, `seed`, plus params-file-only fields below). | Bulk-supplies params from a file; any flag also passed on the command line overrides that key from the file. |
| `--out` | path | *(none — writes to stdout)* | Any writable file path; parent directories are created automatically. | Writes the rendered `TrackDocument` JSON to this file (with a trailing newline) instead of printing it. |

**Params-file-only fields** (no dedicated CLI flag — set these via `--params`):

| Field | Type | Default | What it does |
| --- | --- | --- | --- |
| `roleFlavors` | object (`{role: flavorId}`) | `{}` (pack/ensemble-preset defaults) | Per-role sound flavor overrides (drums/bass/comping/pads). |
| `ensemblePreset` | string | The pack's `"default"` ensemble preset | Selects a named bundle of role flavors instead of setting each individually. |
| `seedText` | string | unused if absent | A free-text string hashed (SHA-256) into the master seed, as an alternative to `seed`. Mutually exclusive with `seed`. |
| `seedOverrides` | object (`{stream: seed}`) | `{}` (no reroll) | Rerolls individual named sub-seed streams (e.g. reroll just the drums) while keeping the rest of the song fixed. |
| `title` | string | none | A display title echoed back in the output; has no effect on generation. |

### `trackgen export-schema`

Exports the `TrackDocument` JSON Schema — the client contract the browser player codes against — derived from the pydantic model, camelCase-aliased, sorted keys, byte-stable across re-exports.

| Flag | Type | Default | Accepted values | What it does |
| --- | --- | --- | --- | --- |
| `--out` | path | `docs/schema/trackdocument.schema.json` | Any writable file path; parent directories are created automatically. | Writes the exported JSON Schema to this path. |
