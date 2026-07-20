# SESSION 17 — Phase 8, Chunk 3: Authoring tooling

**Status: PLAN — AWAITING USER APPROVAL. No implementation agent dispatched yet.**

Implements PHASE_8 **§9** (authoring workflow & tooling) + **§13.7 amendment path** and proves
**DoD §14.7**. Fresh chunk; the C1 pipeline trace and the C2 validator/calibration suite are the
substrate. Everything here is **additive** — new modules + new CLI subcommands + an opt-in
`explain` collector threaded as a defaulted-`None` param — so the existing 4806-test suite must stay
green with **zero fixture edits** (the C1/C2 byte-identity discipline continues).

Orchestrator reads this file; implementer subagents are pointed at the specific task section below.

---

## 1. Session scope

Build the four authoring tools of PHASE_8 §9, in the D13-pinned order (**audition → linter →
`--explain` → calibrate**):

1. **Audition CLI** (§9.1) — `trackgen audition --pack --mood [--seed] [--section] [--solo] [--mute]
   [--tempo] [--out|--play]`. The edit→hear loop; `--solo`/`--mute` filter tracks, `--section`
   renders one section's tick span, `--out` writes the fixture JSON, `--play` opens the playground.
2. **Pack linter** (§9.2) — `trackgen lint styles/<pack>/`: an **errors** tier (every loader rule,
   collect-mode, file-level context) + the **five warning classes** (variety coverage · grid mixing ·
   unreachable content · dangling gates · weight degeneracy).
3. **`--explain` selection log** (§9.3) — a per-slot decision trace on any render, instrumenting the
   §9.3-enumerated draw sites; surfaced as a `--explain` flag on `audition` and `generate`.
4. **`trackgen calibrate styles/<pack>/`** (§9.3) — batch-renders a pack across its moods, drives the
   C2 `compute_bands` core, and **writes `styles/<pack>/calibration.yaml`** (C2 built the compute core
   and the write-dict builders; C3 wires the emit + CLI and reconciles the L2-threshold reader).

### Explicitly OUT of scope (later chunks — do not build)

- **Golden corpus, `bless`, smoke matrix, 300-seed sweep** → C4 (DoD 5, 6). `--explain` must *feed*
  the future bless report (structured records available) but the bless report itself is C4.
- **Reference-pack refinement, listening/error-spotting, T1/T2 listening tasks, committing a
  *blessed* `calibration.yaml`** → C5 (DoD 2). Per the §8.1 bootstrap order, a pack's first
  `calibration.yaml` is written only *after* its batch is listening-blessed (C5 step 8). **C3 does NOT
  commit reference-pack `calibration.yaml` artifacts** — it proves `calibrate` works (tests write to
  `tmp_path`; round-trip via `load_calibration`).
- **The three new packs** (chill_lofi/blues/fusion_jazz) → C6–C8. C3's linter/audition/calibrate are
  proven on the reference packs + synthetic fixtures only; the reference packs are **not required to
  be warning-clean** here (that is a C5 deliverable).

---

## 2. Contracts consumed (all already built — verify before relying)

- **`pipeline/trace.py::generate_trace(raw_params: dict[str, object]) -> GenerationTrace`** — the
  single full-pipeline entry point. `GenerationTrace` (frozen) exposes `plan, song_form, harmony,
  arrangement, selection, phrases_stage5, phrases_stage6, phrases_stage7, tempo_events, sound_design,
  document`. `generate_track` = `generate_trace(...).document`. `raw_params` is a plain camelCase dict
  (`styleFamily` required; `mood`/`seed`/`tempoBpm` optional).
- **`pipeline/serialize.py::serialize(plan, form, phrases, design, *, tempo_events=None,
  params=None) -> TrackDocument`** and `to_json(doc) -> str`. Bus omission (§7 reverb rule) is computed
  **inside** `serialize` from the surviving tracks — so **filter phrases upstream of `serialize`**, do
  not post-filter `doc.tracks` (that would leave `buses` stale).
- **`FormSection.id = f"{type}-{index}"`** (1-based per type; e.g. `solo-2`), on the IR `FormSection`
  (`schema/ir.py`), **not** on the emitted document `Section`. Section tick span =
  `[start_bar*1920, (start_bar+length_bars)*1920)`. `_TICKS_PER_BAR = 1920` (v1 4/4).
- **`Track.id: str` + `Track.role: Role`** (`Role = Literal["drums","bass","comping","pads"]`). Drum
  sub-tracks (`kick,snare,hats,ride,crash,tom_low,tom_mid,tom_high,perc`) all carry `role="drums"`;
  `bass/comping/pads` are both an id and a role.
- **`seeds.py::weighted_choice(items, weights, rng)`** — the one shared draw primitive; **choice-
  agnostic** (no slot identity), so `--explain` instruments the *callers*, never this primitive.
- **Draw call sites** (from session-17 scoping — verify): template `form/stage.py:190`; pool/turn/final
  `harmony/stage.py:107` (`_select`); dressing tier `harmony/stage.py:120` (`_dress_slot`); pattern
  per-(role,kind,rung) `parts/selection.py:99` (`_draw`, survivors from `_eligible_set` at
  `selection.py:80`); mutation op `transitions/mutation.py:354`; phrase-fill / stop-vs-fill
  `transitions/devices.py:213`/`:232`; tempo `interpreter/stage.py:190` (`randrange`, auto-path only).
- **Loader**: `packs/loader.py` + `packs/models.py` — all rules **raise on first** (`PackLoadError`
  with file path + rule tag *in the message text only*, or `ValueError`/`ValidationError` from pydantic
  validators). No accumulate path exists. `yaml.safe_load` drops line numbers ⇒ **file-level context
  only**.
- **Reusable analysis helpers**: `parts/selection.py:80 _eligible_set(pack, role, kind, rung,
  tempo_bpm)` (variety survivors); `quality/layer1.py` grid constants `_STRAIGHT_GRID={0,120,240,360}`
  / `_TRIPLET_GRID={0,160,320}` + the W7 helper (grid mixing, but over authored `env.events`);
  `arrangement/intensity.py::intensity(energy)` (unreachable rungs); `Eligibility.tempo_bpm` /
  `TemplateEligibility.arousal` (dangling gates); `weight` fields on `PatternEnvelope` /
  `_ProgressionEntry` / `TemplateSpine` / mutation tables (degeneracy).
- **Quality/calibration API** (`quality/calibration.py`): `compute_bands(batch, l2_thresholds=None) ->
  PackMoodCalibration` (mean ± 2.5·pstdev); `pack_and_mood(trace) -> (pack, mood)`;
  `calibration_to_yaml_dict(Calibration) -> dict`; `load_calibration(pack) -> Calibration | None`;
  dataclasses `Band`/`PackMoodCalibration`/`Calibration`. `layer3.py::compute_metrics(trace) ->
  Metrics`. **`yaml.safe_dump` is permitted** (TID251 bans only random/time/datetime/os.urandom/uuid;
  `yaml` is used repo-wide).
- **Mood/tempo enumeration**: `pack.interpreter.supported_moods` / `default_mood`;
  `pack.manifest.tempo_range`; per-mood tempo center is *derived* —
  `interpreter/moods.py::formulas(v,a)["tempoCenter"] = 100*2**(0.6*a)`, then window
  `lo=max(round(0.9*center), range[0])`, `hi=min(round(1.1*center), range[1])`
  (`interpreter/stage.py:182`).

---

## 3. Cross-cutting constraints (every task)

- **Determinism / byte-identity**: the production path (no `--explain`, no filters) must be
  byte-identical to today. Thread the explain collector as `explain: ExplainCollector | None = None`
  (default `None` = current behavior). The collector only *appends after each draw returns* — it never
  reads/advances the RNG, so draw order is untouched. **Proof required**: full suite green, **zero
  fixture edits**. TID251 unchanged; no new banned imports.
- **Gates** (run all four, read output): `uv run pytest` (~11 min / 4806 tests — use an extended
  timeout) · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy`.
- **Frozen models**: `TrackDocument`/`Track`/`NoteEvent` are `frozen=True` — rebuild via reconstruction
  or filter upstream of `serialize` (preferred). Do not mutate in place.
- **No new caveats unless a pinned value is reinterpreted.** The two likely caveat/escalation points
  are called out in T2 (collect-mode granularity) and T4 (L2-threshold reader reconciliation).

---

## 4. Task list (serial; all `opus`)

All four tools touch `cli.py` (each adds a distinct `@app.command` / flag), and T3 edits
`tooling/audition.py`, so tasks run **serially** — no parallel dispatch. Each task: implement (+ tests)
→ four gates → task-scoped opus review → bounded fix loop → commit → update PROGRESS.md.

### T1 — Audition CLI core (§9.1) · `opus`

**Files (create/edit):** `src/trackgen/tooling/__init__.py`, `src/trackgen/tooling/audition.py`
(new); `src/trackgen/cli.py` (add `@app.command("audition")`); `playground/index.html` (minimal
`?doc=` auto-loader for `--play`); `tests/test_audition.py` (new).

**Implements:** PHASE_8 §9.1 + DoD §14.7 (audition slice).

**Behavior:**
- Flags per §9.1 verbatim: `--pack` (→ `styleFamily`), `--mood`, `--seed`, `--tempo` (→ `tempoBpm`),
  `--section` (e.g. `solo-2`), `--solo`, `--mute`, `--out PATH`, `--play`. (Distinct from `generate`'s
  `--style-family`/`--tempo-bpm`; both map to the same camelCase `raw_params` keys internally. This
  UX split is intentional — §9.1 pins the short names for the authoring command.)
- Pipeline: build `raw_params` (camelCase) → `trace = generate_trace(raw_params)` → derive filters →
  **re-`serialize` from filtered phrases** (so `buses`/sound-design recompute) → `to_json` → write/play.
- **`--section solo-2`**: resolve span from `trace.song_form` (`FormSection.id == "solo-2"` →
  `[start_bar*1920, (start_bar+length_bars)*1920)`). Keep phrase notes with `start_tick <= ticks <
  end_tick` (absolute ticks, no shifting). Unknown id → `typer.BadParameter` listing valid ids.
- **`--solo ROLE|ID` / `--mute ROLE|ID`**: match **role-first, id-fallback**. `--solo drums` keeps only
  the drums role; `--mute hats` drops the `hat_closed`/`hat_open` voice notes from the drum phrases.
  Filter at the **phrase level** (role → drop/keep whole phrases; drum sub-track id → drop matching
  voice-tagged notes, using the C-11 voice provenance tags on drum `PhraseNote`s). `--solo` and
  `--mute` are mutually exclusive-ish but if both given, apply solo then mute. Unknown target →
  `BadParameter`.
- **`--out PATH`**: write `to_json(doc) + "\n"` (mirror `generate`'s `--out`). Default (no `--out`/
  `--play`): echo JSON to stdout.
- **`--play`**: write the doc to `playground/audition.trackdoc.json`, then `webbrowser.open` the
  playground URL with a `?doc=audition.trackdoc.json` query param; add a **minimal** `?doc=` loader to
  `playground/index.html` (throwaway file — allowed). A static server may be needed for `fetch`; print
  a one-line hint (`uv run python -m http.server`) rather than managing a server process from the CLI.
  **Do not** block on a server. (If a robust auto-serve proves fiddly, fall back to: write the file +
  open the playground + print "load `audition.trackdoc.json` via the file picker" — the value is
  `--out`; `--play` is a convenience. Keep it small; no rabbit holes.)

**Verification (tests):**
- Reproducibility: same `(pack, mood, seed)` → identical JSON across two calls.
- `--section solo-2` yields only that section's notes (all `ticks` within span; a section with a known
  bar range asserted); unknown id raises.
- `--solo drums` → only `role=="drums"` tracks survive; `--mute pads` → no `pads` track, and `buses`
  recomputed (reverb bus omitted if pads was the only sender — assert the bus set changes, proving
  upstream filtering); `--mute hats` → drum track present but no hat notes.
- `--out` writes the file; parent dirs created. `--play` (monkeypatch `webbrowser.open`) writes
  `playground/audition.trackdoc.json` and calls open with the `?doc=` URL.
- The full unfiltered audition output equals `to_json(generate_track(raw_params))` (audition adds no
  divergence on the no-filter path).

### T2 — Pack linter: collect-mode errors + five warnings (§9.2) · `opus`

**Files (create/edit):** `src/trackgen/packs/lint.py` (new — `collect_pack_errors` + the five warning
analyses, returning structured `LintError`/`LintWarning` lists); `src/trackgen/tooling/lint.py` (new —
thin CLI-facing formatter); `src/trackgen/cli.py` (add `@app.command("lint")`); `tests/test_lint.py`
(new) + minimal synthetic pack fixtures under `tests/fixtures/lint_packs/` (or reuse `styles/_stub` +
tmp-copied bad packs).

**Implements:** PHASE_8 §9.2 + DoD §14.7 (linter slice).

**Behavior:**
- **Errors tier** — `collect_pack_errors(pack_dir) -> list[LintError]`: run the existing loader rules
  and report failures with **file-level context + rule tag** (parsed from the message; line numbers are
  unavailable — `yaml.safe_load` drops positions, per C1 scoping). **Collect-mode granularity
  (bounded — call out in review):** accumulate what is cheap — read the **full** `ValidationError
  .errors()` list from each pydantic `model_validate` (pydantic aggregates field-level errors), and
  wrap each **independent** loader cross-file check (`_check_f11`, `_check_progressions_cross_file`,
  `_check_pattern_banks`, `_check_completeness`, `_window_and_check_fills`, PT12…) in try/except that
  appends and continues. Accept the residual limit that two failures inside the *same* `model_validator`
  (which raises on first) surface one-at-a-time across re-runs — **document this in the module
  docstring**; a full validator refactor is out of scope (escalate if the reviewer judges it required
  for DoD §14.7). A clean pack returns `[]`.
- **Warnings tier** — `list[LintWarning]`, non-blocking, five classes (§9.2):
  - **variety coverage**: any `(role, kind, rung)` slot where `len(_eligible_set(...)) <= 1` for some
    supported `(mood, tempo)` cell (zero reroll variety). Enumerate cells via §2's mood/tempo
    derivation.
  - **grid mixing**: a pattern whose authored `env.events` contain both straight-grid and triplet-grid
    `pos` (reuse the `quality/layer1.py` grid constants; check over `env.events`, not rendered phrases).
  - **unreachable content**: a `main` rung no reachable section energy quantizes to
    (`arrangement/intensity.py::intensity`), against the pack's `forms.yaml` `energyRange`. Silenceable
    via an `# expected-unreachable` marker on the pattern (comments are dropped by `safe_load` — scan
    the raw bank-file text for the token to silence; coarse file-level silence is acceptable, note it).
  - **dangling gates**: an `Eligibility.tempo_bpm` band (or `TemplateEligibility.arousal` band) no
    supported `(mood, tempo/arousal)` cell can enter.
  - **weight degeneracy**: any pool (progression pools/turnarounds/finals, pattern banks, template
    spine, mutation tables) where `max(w)/sum(w) > 0.90`.
- **CLI**: `trackgen lint styles/<pack>/` prints errors then warnings (grouped, counted); exit code
  non-zero iff any error (warnings never fail the command).

**Verification (tests):**
- One synthetic pack per warning class fires **only** that warning (discriminating); a clean pack fires
  none of a given class.
- One synthetic malformed pack yields the expected `LintError`(s) with the right file + rule tag; the
  errors-collect reads a multi-field `ValidationError` as multiple `LintError`s.
- **Run against the two reference packs and snapshot the output** (report, do not assert clean —
  reference-pack warning-cleanliness is a C5 deliverable). Assert `resolve_pack` still loads them (the
  linter does not alter loading).
- `# expected-unreachable` silences the unreachable-content warning on the annotated pattern.

### T3 — `--explain` selection log (§9.3) · `opus`

**Files (create/edit):** `src/trackgen/pipeline/explain.py` (new — `ExplainCollector` append-only +
record dataclasses + `render_explain(collector) -> str` text formatter); instrumentation edits
threading `explain: ExplainCollector | None = None` through `pipeline/trace.py`, `form/stage.py`,
`harmony/stage.py`, `parts/selection.py`, `transitions/devices.py`, `transitions/mutation.py`,
`interpreter/stage.py`; `src/trackgen/cli.py` + `src/trackgen/tooling/audition.py` (add the `--explain`
flag to `audition` and `generate`); `tests/test_explain.py` (new).

**Implements:** PHASE_8 §9.3 (selection log) + D13.

**Behavior:**
- `generate_trace(raw_params, *, explain=None)`: when a collector is passed, each §9.3-enumerated draw
  site appends a structured record **after** its draw resolves. Records cover exactly the §9.3 list:
  **template** draw (chosen id + candidate ids/weights); **per-tag pool/turnaround/final picks**
  (chosen entry + **surviving candidate count**); **dressing tier per slot** (token + chosen tier);
  **per-(role,kind,rung) pattern picks** (chosen pattern id + survivor count from `_eligible_set`);
  **device draws + no-ops** (fill include/exclude, stop-vs-fill, per boundary); **mutation draws +
  no-ops** (`none` included); **tempo** draw (chosen bpm + window). **Explicitly OUT** (would swamp the
  log, not in §9.3): walker per-tick pitch draws, and the form per-slot optional / bar-count draws —
  note this exclusion in the module docstring.
- Determinism-safe: the collector is append-only and never touches the RNG; default `None` = the exact
  current code path.
- `--explain` on `audition`/`generate`: run with a collector, print `render_explain(collector)`
  (human-readable per-slot trace) to stderr (or a separate stream) so `--out`/piped JSON stays clean.
- Structured records are retained on the collector (list of dataclasses) for C4's bless report to
  consume later — but no bless integration here.

**Verification (tests):**
- **Byte-identity**: `generate_trace(p)` and `generate_trace(p, explain=Collector())` produce an
  **identical** `document`; the full suite is green with **zero fixture edits** (the load-bearing
  proof — like C1/C2's additivity).
- The collector records the expected slots on a real pop/jazz render: at least one template, ≥1 pool
  pick with a survivor count, ≥1 pattern pick per active role, ≥1 device no-op **and** ≥1 device fire,
  ≥1 mutation `none`, the tempo draw. A **discriminating** assertion (not vacuous): a render whose
  seed forces a specific device/mutation outcome logs the matching record (monkeypatch or seed-pinned).
- `render_explain` output contains the slot identities and counts (smoke-level string assertions).

### T4 — `trackgen calibrate` → `calibration.yaml` (§9.3) · `opus`

**Files (create/edit):** `src/trackgen/tooling/calibrate.py` (new — batch-render → group by
`pack_and_mood` → `compute_bands` → `Calibration` → `yaml.safe_dump(calibration_to_yaml_dict(...))`);
`src/trackgen/cli.py` (add `@app.command("calibrate")`); **possibly** `src/trackgen/quality/layer2.py`
(reconcile `load_l2_thresholds`); `tests/test_calibrate.py` (new).

**Implements:** PHASE_8 §9.3 (calibration report) + §8.1 (L2/L3 artifact) + DoD §14.7 (calibrate slice).

**Behavior:**
- `calibrate(pack_id, *, out_path=None, seeds=..., moods=None)`: for each supported mood × a small seed
  set, `generate_trace({"styleFamily": pack, "mood": m, "seed": s})`; group traces by
  `pack_and_mood`; `compute_bands` per group → assemble `Calibration(pack, {mood: PMC})` → write
  `styles/<pack>/calibration.yaml` (default) via `calibration_to_yaml_dict` + `yaml.safe_dump`
  (sorted keys off, `allow_unicode` per repo convention). Also emit the §9.3 human report (per-track
  velocity/level + per-section density vs budgets + tempo-band violations) to stdout — **report-only**,
  no gating.
- **⚠️ L2-threshold reader reconciliation (bounded — escalation valve):** `layer2.py::load_l2_
  thresholds(pack)` currently reads a top-level `data["l2"]["bass_strong_beat_ratio"]` shape that
  **does not match** what `calibration.py` writes/reads (per-`(pack,mood)`
  `moods.<mood>.l2Thresholds.{bass,comping}`). §8.1 pins the per-`(pack,mood)` shape as the artifact
  ("bands … also home of the L2 thresholds", per-`(pack,mood)`). Reconcile so a written
  `calibration.yaml`'s L2 thresholds are actually read: prefer routing L2-1's lookup through the
  existing correct reader `load_calibration(pack).moods[mood].l2_thresholds` (mood from
  `doc.meta.params["mood"]`/default), deprecating/rewriting `load_l2_thresholds`. **Keep
  `test_quality_layer2.py` green** (update deliberately, with justification, only if the reconciliation
  requires it). **If this reconciliation ripples into an L2-1 signature/contract change beyond a
  local reader swap, STOP and escalate** (do not silently reshape a C2 contract). If it changes any
  pinned §8.1 behavior, log a CAVEAT.
- **Do NOT commit reference-pack `styles/*/calibration.yaml`** (bootstrap order — C5 blesses+commits).
  Tests drive `calibrate(..., out_path=tmp_path/...)` and round-trip via `load_calibration`.

**Verification (tests):**
- `calibrate("pop_rock", out_path=tmp)` writes a `calibration.yaml` whose `load_calibration` round-trip
  reproduces the `Calibration` (bands + l2Thresholds present per supported mood).
- The written shape matches `calibration.py`'s documented yaml shape (spot-assert
  `moods.<mood>.bands.noteDensity.<role>` and `l2Thresholds.bass`).
- Reconciled `load_l2_thresholds`/`load_calibration` path: a written `calibration.yaml` with a
  non-default bass threshold is actually **read** by L2-1 (prove the round-trip connects, closing the
  C2 divergence). `test_quality_layer2.py` stays green.
- Determinism: repeated `calibrate` runs on the same pack/seeds produce an identical yaml.

### T5 — Whole-chunk review + DoD §14.7 + close-out · orchestrator

- Dispatch **fresh** `opus` review agents over the whole C3 diff (parallel, disjoint lenses):
  (a) correctness/determinism — filtering + bus recompute, explain byte-identity, collect-mode
  soundness, calibrate round-trip + the L2 reconciliation; (b) contract/§9 compliance — each tool
  matches its §9.1/§9.2/§9.3 clause, scope boundaries honored (no C4/C5 creep); (c) test quality/DoD —
  discriminating fixtures, no vacuous tests, DoD §14.7 items evidenced.
- Validate each finding before fixing; confirmed → fix agent + gate re-run (2-cycle bound).
- Check **DoD §14.7** item by item with evidence (test names, command output).
- Log CAVEATS for any deviation (candidate: the L2-threshold-shape reconciliation if it reinterprets
  §8.1; the collect-mode one-error-per-model_validator limitation is a documented tool limitation, not
  a design deviation → handoff note, not necessarily a caveat).
- Update PROGRESS.md (statuses, session-log row, fresh handoff block → C4), commit doc updates.

---

## 5. Decisions taken in this plan (flag at the approval gate)

1. **Audition flag names follow §9.1 verbatim** (`--pack`/`--tempo`), distinct from `generate`'s
   `--style-family`/`--tempo-bpm`. Both map to the same internal camelCase keys.
2. **Filtering happens upstream of `serialize`** (on the phrase list) so `buses`/sound-design
   recompute correctly, rather than post-filtering the frozen document.
3. **`--explain` scope = exactly the §9.3-enumerated slots** (+ tempo); walker per-tick and form
   optional/bar-count draws are excluded to keep the log readable.
4. **`--play` is intentionally minimal** (write fixture + open playground `?doc=` URL + hint; small
   playground edit; no CLI-managed server). Fallback to file-picker if auto-serve is fiddly.
5. **Collect-mode linter accumulates what is cheap** (pydantic `.errors()` + independent cross-file
   checks); residual one-error-per-`model_validator` limit documented, not refactored.
6. **calibrate reconciles the C2 `load_l2_thresholds` shape mismatch** (escalation valve if it ripples
   beyond a local reader swap); **reference-pack `calibration.yaml` is NOT committed** in C3.
7. **Everything additive / byte-identical on the default path** — full suite green, zero fixture edits,
   proven per task.

---

## 6. DoD §14.7 coverage map

| DoD §14.7 item | Task |
| --- | --- |
| Audition CLI with `--section`/`--solo`/`--mute`/`--play` | T1 (+ `--explain` flag T3) |
| Pack linter (errors + all five warning classes) | T2 |
| `--explain` selection log | T3 |
| `trackgen calibrate` producing `calibration.yaml` | T4 |

Whole-chunk review (T5) proves DoD §14.7 with evidence.
