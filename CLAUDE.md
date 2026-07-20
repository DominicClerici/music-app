# trackgen — working notes

`trackgen` is a deterministic Python pipeline that composes complete instrumental
backing tracks from structured parameters and emits a Tone.js-oriented `TrackDocument`
JSON. Nine pipeline stages, each with a pinned intermediate representation.

This file holds *how to work in this repo*. The *what to build* is pinned elsewhere —
don't restate it here.

## Authoritative docs (read these, don't duplicate them)

- **`plans/PROMPT.md`** — the session workflow. Implementation runs as an orchestrator
  dispatching subagents; you build exactly what the design pins, you do not redesign.
- **`plans/ROADMAP.md`** — vision, the 9-stage pipeline, and the binding invariants (§3).
- **`plans/PHASE_1.md`–`PHASE_8.md`** — the pinned per-phase design. Binding.
- **`plans/PROGRESS.md`** — live source of truth for implementation state. A new session
  resumes from this file + `git log`, so it's kept current, never trusted to memory.
- **`plans/CAVEATS.md`** — logged deviations from the pinned design.

## Gates (run all four; they must be green before committing)

```sh
uv run pytest -n auto           # -n auto: pytest-xdist, parallel across cores
uv run ruff check .
uv run ruff format --check .   # --check matters: verifies formatting, doesn't rewrite
uv run mypy
```

Always use `-n auto` for the pytest gate — style packs load through a cached loader
(`trackgen.packs.loader.load_pack`), so the suite is parallel-safe and runs in seconds
instead of minutes.

Use `uv` for everything — never bare `python`/`pip`. `uv sync` installs from the
committed `uv.lock`. Never claim a gate passes without having run it and read the output.

## Determinism is enforced, not aspirational (ROADMAP invariant 5)

No wall-clock and no unseeded randomness anywhere outside `src/trackgen/seeds.py` — the
single entropy boundary. Ruff TID251 bans `random`, `os.urandom`, `time`, and
`datetime.now` at the import layer; **don't work around it.** A master seed derives named
sub-seeds (form, harmony, drums, …); same params + same seed → identical `TrackDocument`.

## Repo map

- `src/trackgen/` — the pipeline, by stage (`schema/`, `theory/`, `pipeline/`, `packs/`,
  `seeds.py`, `cli.py`).
- `tests/` — pytest + Hypothesis.
- `styles/` — style packs. **Data, not code** (ROADMAP invariant 1): adding a style is
  authoring YAML, not engineering.
- `fixtures/` — committed golden JSON; the regression surface once a fixture lands.
- `docs/schema/` — exported JSON Schema (the client contract).
- `playground/` — throwaway experiments (e.g. the Phase 1 Tone.js test page).

## Conventions & gotchas

- Exact dependency pins live in `uv.lock`; a version bump is a deliberate, reviewed
  re-lock, not a casual change.
- Rhythm is stored separately from pitch and retargeted to real chords at render time —
  never store literal notes and transpose naively (ROADMAP invariant 2).
- **Golden-value arbitration** (ROADMAP §3): the PHASE docs' printed worked-example
  numbers are derived samples. On divergence, the algorithm/data *text* wins — never tune
  code to reproduce a printed number; fix the doc sample instead (with sign-off).
- Never `git push` (that's the human's). Commit freely at verified gates.
