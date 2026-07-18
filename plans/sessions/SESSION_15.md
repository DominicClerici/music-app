# Session 15 — Phase 8, Chunk 1: pipeline trace + machinery amendments

**Phase 8** (Quality, evaluation & pack expansion) is multi-session with a hard ordering
(tooling → reference-pack refinement → chill_lofi → blues → fusion_jazz). This is the **first**
session — foundational engine work that unblocks everything downstream. It builds **no packs and no
tooling**; it lands (a) the production **trace orchestrator** that the validator suite, `--explain`,
the golden corpus, and `bless` all depend on, and (b) the three additive **machinery amendments**
(PHASE_8 §3.4 / §3.5 / §3.7) that the three new packs' content depends on.

Read this file as an implementer with **zero other context**. Every task points at exact files,
the exact PHASE-doc section it implements, the constraints, and what to return.

---

## Session scope

**In scope**
- **T1 — Pipeline trace orchestrator** (`generate_trace`): expose every IR boundary
  (GenerationPlan, SongForm, HarmonicPlan, ArrangementPlan, SelectionResult, phrases **post-5 /
  post-6 / post-7 separately**, tempo events, SoundDesign, TrackDocument) from a production entry
  point; refactor `generate_track` to delegate so the final document stays **byte-identical**.
- **T2 — Named feel profiles + `feelTable` selector** (PHASE_8 §3.4; amends PHASE_6 §5.3 / PHASE_2
  §5.1): add `laidback` and `tight` profiles to `feel.yaml`/`feel.py`; validate the pre-existing
  `feelTable` interpreter field against the profile menu; thread it through to profile selection.
- **T3 — Authored chord extensions + rule P11** (PHASE_8 §3.5; amends PHASE_4 §3.1): parse the
  parenthesized extension group in the token grammar; enforce §6.4 legality (P11); make an authored
  extension **fully pin** the token so dressing skips the slot **draw-free**.
- **T4 — Allowlist growth verification** (PHASE_8 §3.7): confirm the `Vibrato`/`AutoFilter` allowlist
  entries match §3.7 exactly (already present) and add a coverage test that would catch their removal.
- **T5 — Whole-chunk 2-lens review + DoD 1 + close-out** (orchestrator).

**Explicitly out of scope** (later chunks): the validator layers W1–W8 / L2 / L3 (C2); the audition
CLI, pack linter, `--explain` selection log, `calibrate` (C3); the golden corpus + `bless` + smoke
matrix (C4); reference-pack bank enumeration + calibration (C5); any new pack (C6–C8). Do **not**
build a selection/draw trace log in T1 — only the IR-boundary capture. Do **not** author any
`(#11)`-style token into a shipped pack (that is pack content, C5+).

---

## Constraints (binding — apply to every task)

- **Determinism (ROADMAP invariant 5):** no wall-clock, no unseeded randomness outside
  `src/trackgen/seeds.py`. TID251 bans `random`/`os.urandom`/`time`/`datetime.now` at import; do not
  work around it. Same `(params, seed)` → identical `TrackDocument`.
- **Golden-value arbitration:** the PHASE docs' printed worked-example numbers are derived samples —
  the algorithm/data text wins on divergence; never tune code to a printed number. (No §-goldens are
  reblessed this session; this only matters if a printed sample is hit.)
- **Additive only.** Every change here is additive: pop_rock and jazz must produce **byte-identical**
  humanized output and byte-identical whole-document goldens after this session. Prove it, don't
  assume it.
- **Gates (all four must be green before a commit):**
  `uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy`
  (full suite ~11m; run pytest with an extended timeout). Use `uv` for everything, never bare python.
- **Comments explain _why_, not _what_** (project rule). No comment restating the code.

---

## Task list (ordered; parallelism noted)

Model policy: T1/T2/T3 are **opus** (real judgment — infra refactor, schema plumbing, grammar/loader/
dressing). T4 is **sonnet** (trivial: verify pre-existing data + a transcription test). T5 is the
orchestrator.

**Parallelism:** T1 (touches only `pipeline/`) is disjoint from T2 and T4 → may run concurrently.
T2 and T3 **both edit `src/trackgen/packs/models.py`** (different classes) → **serialize T3 after
T2**. T4 (touches only `sound/` + a new test) is disjoint from all → may run any time. Suggested
wave: **T1 ‖ T2 ‖ T4**, then **T3**, then **T5**.

---

### T1 — Pipeline trace orchestrator (`opus`)

**Implements:** PHASE_8 §8.2 (golden corpus stores every IR boundary) and §9.3 (`--explain`); it is
the shared substrate for the C2 validators (W7 needs pre-humanizer phrases; W8 needs post-6 vs post-7
counts) and the C4 corpus. **No behavior change to `generate_track`.**

**Files (scope):**
- `src/trackgen/pipeline/trace.py` — **new**.
- `src/trackgen/pipeline/orchestrator.py` — refactor `generate_track` to delegate.
- `src/trackgen/pipeline/__init__.py` — export `generate_trace`, `GenerationTrace`.
- `tests/test_trace.py` — **new**.

**What exists (from scoping):** `generate_track(raw_params) -> TrackDocument`
(`pipeline/orchestrator.py`) runs the nine stages and returns only the final doc, discarding every
intermediate. The exact stage chain and IR types already exist as a **test-only** driver
`_drive_full` (`tests/test_orchestrator.py`), copy-pasted across ~7 test files, but it (a) collapses
the three phrase snapshots into only post-7 and (b) omits SoundDesign / HarmonicPlan / ArrangementPlan
/ SelectionResult. The IR models live in `src/trackgen/schema/ir.py`; `SoundDesign` in
`src/trackgen/sound/stage.py`.

**Build:**
1. A frozen dataclass (or frozen pydantic model — match the codebase's IR convention)
   `GenerationTrace` in `pipeline/trace.py` holding **every** boundary:
   `plan: GenerationPlan`, `song_form: SongForm`, `harmony: HarmonicPlan`,
   `arrangement: ArrangementPlan`, `selection: SelectionResult`,
   `phrases_stage5: list[Phrase]`, `phrases_stage6: list[Phrase]`, `phrases_stage7: list[Phrase]`,
   `tempo_events: list[Tempo]`, `sound_design: SoundDesign`, `document: TrackDocument`.
   (Use the exact stage-output types; capture phrases at each stage by keeping the intermediate lists
   rather than mutating in place.)
2. `generate_trace(raw_params: dict[str, object]) -> GenerationTrace` running the identical stage
   chain as today's `generate_track` (same call order, same rng streams, same arguments — do not
   change any draw order).
3. Refactor `generate_track` to call `generate_trace(...).document` (or share a private helper) so the
   returned document is **provably unchanged**. The public `generate_track` signature/behavior is
   frozen.
4. Export both from `pipeline/__init__.py`.

**Tests (`tests/test_trace.py`):**
- `generate_trace(p).document` is **byte-identical** to `generate_track(p)` for both the pop_rock and
  jazz milestone param sets (reuse the param dicts from `tests/test_pipeline_determinism.py`).
- Every boundary field is present and of the correct type; `phrases_stage5`, `_stage6`, `_stage7` are
  **distinct** snapshots (assert stage-6 differs from stage-5 where transitions fire, and stage-7
  preserves stage-6 note counts per track — the PHASE_6 D1 contract, now assertable end-to-end).
- Determinism: two `generate_trace` calls on the same params yield equal documents.

**Also verify (do not necessarily fix):** the ~7 `_drive_full` copies can now collapse onto
`generate_trace`. Collapsing them is a **nice-to-have cleanup, not required** — if it is low-risk and
keeps all tests green, do it; otherwise leave a one-line note in your report for a later cleanup and
do **not** risk reddening the suite for it.

**Return:** new file paths, the `GenerationTrace` field list, confirmation `generate_track` is
byte-identical (with the test names proving it), and whether you collapsed the `_drive_full` copies.

---

### T2 — Named feel profiles + `feelTable` selector (`opus`)

**Implements:** PHASE_8 §3.4 (amends PHASE_6 §5.3 and PHASE_2 §5.1). **DoD §14.1** (feel profiles +
selection, both new tables matching §3.4 exactly, validator caps enforced).

**Files (scope):**
- `src/trackgen/humanize/feel.yaml` — add the two profiles.
- `src/trackgen/humanize/feel.py` — add the two `OffsetProfile` fields + a profile-name menu constant.
- `src/trackgen/humanize/stage.py` — the profile-selection line.
- `src/trackgen/schema/ir.py` — `GenerationPlan` gains `feel_table: str | None = None`.
- `src/trackgen/interpreter/stage.py` — set `feel_table` on the `GenerationPlan`.
- `src/trackgen/packs/models.py` — `InterpreterConfig._check_rules` validates the pre-existing
  `feel_table` field against the menu.
- `tests/test_feel.py`, `tests/test_interpreter_pack.py` — tests.

**What exists (from scoping):**
- `feel.yaml` `offsetsMs` is the **two-table** model with exactly `swung` and `straight` sub-maps
  (PHASE_6 §5.3). Rows are scalar or a per-beat-class map `{down, back2, beat3, back4, off}`.
- `feel.py`: `Offsets` hard-codes only `swung`/`straight` `OffsetProfile` fields. The **≤25 ms cap**
  is `OffsetProfile._check_offset_cap` (constant `_OFFSET_CAP_MS = 25`) and runs per `OffsetProfile`,
  so it **auto-covers** new profiles — no new cap validator needed. `FeelData.model_validate({...})`
  is directly constructable for over-cap rejection tests.
- Selection today (`humanize/stage.py`, in `_run()`):
  `profile = feel.offsets_ms.straight if plan.swing is None else feel.offsets_ms.swung`
  (there is a TODO comment there anticipating exactly this `feelTable` change).
- `InterpreterConfig` (`packs/models.py`) **already has** a `feel_table` field (added in Phase 2,
  unwired/unvalidated); its `_check_rules` validator does not check it. A lazy import inside the
  validator body avoids the `feel.py ↔ packs.models` import cycle (pattern already used in
  `_check_rules` for `interpreter.moods`).
- `pack.interpreter.feel_table` currently dead-ends — nothing reads it. `GenerationPlan`
  (`schema/ir.py`) carries `swing` but not `feel_table`; `humanize(phrases, form, plan)` receives only
  `plan`.

**Build:**
1. Add the `laidback` and `tight` profiles to `feel.yaml` `offsetsMs` **verbatim** from PHASE_8 §3.4
   (the two YAML blocks — `laidback` with the per-beat-class `snare` map, `tight` with scalar rows).
   Add the matching `OffsetProfile` fields to `feel.py`'s `Offsets`. Add an accessor,
   e.g. `Offsets.profile(name: str) -> OffsetProfile`, and a menu constant
   `FEEL_PROFILES = ("straight", "swung", "laidback", "tight")`.
2. Thread selection (mirror how `swing` already flows — the lighter of the two options the scoping
   flagged, and it keeps `humanize`'s signature unchanged):
   - `GenerationPlan` (`schema/ir.py`): add `feel_table: str | None = None`.
   - `interpreter/stage.py`: set `feel_table=pack.interpreter.feel_table` on the constructed
     `GenerationPlan` (beside `swing=...`).
   - `humanize/stage.py` selection: **if `plan.feel_table` is not None → the named profile; else the
     existing swing-derived default** (`straight` when `plan.swing is None`, else `swung`). Use the
     `Offsets.profile(...)` accessor.
3. `InterpreterConfig._check_rules` (`packs/models.py`): validate `feel_table ∈ FEEL_PROFILES` when
   present (lazy-import the constant from `humanize.feel` to avoid the cycle). Emit a clear error id
   consistent with the surrounding interpreter-rule convention.

**Tests:**
- `tests/test_feel.py`: the two new profiles load and match §3.4 field-for-field
  (`laidback.snare == {down:10, back2:16, beat3:12, back4:16, off:10}`, `laidback.comping == 12`,
  `tight.snare == 2`, `tight.hats == -2`, etc.); a `FeelData.model_validate` over-cap fixture for a
  new profile (e.g. `laidback.toms: 30`) is **rejected** by the ≤25 cap.
- `tests/test_interpreter_pack.py`: an interpreter config with `feelTable: bogus` is **rejected**; one
  with `feelTable: laidback` **loads clean**.
- **Additive proof (critical):** pop_rock and jazz have **no** `feelTable` → `feel_table=None` → the
  swing-derived default is preserved → humanized output byte-identical. Assert
  `tests/test_humanizer_goldens.py` and `tests/test_whole_document_goldens.py` **still pass unchanged**
  (run them; do not edit the fixtures). Add a direct test that `generate_track` output for pop_rock and
  jazz is unchanged by this task if a convenient hook exists; otherwise rely on the existing goldens.

**Return:** the exact §3.4 values you transcribed, the selection-rule diff, the validator error id,
and confirmation the two whole-doc goldens + humanizer goldens are green **without fixture edits**.

---

### T3 — Authored chord extensions + rule P11 (`opus`) — run **after** T2

**Implements:** PHASE_8 §3.5 (amends PHASE_4 §3.1; new loader rule P11). **DoD §14.1** (authored-
extension parsing with P11 rejection fixtures and pin-semantics: an authored-extension slot consumes
**zero** dressing draws).

**Files (scope):**
- `src/trackgen/theory/chords.py` — `resolve_token`: parse the extension group; grammar errors → P5;
  §6.4 legality → raise for P11 at the loader (see split below).
- `src/trackgen/packs/models.py` — P11 named check in the two progression-token validators
  (`PoolEntry._check_bars` and `_BarsEntry._check_bars`).
- `src/trackgen/harmony/dressing.py` — `_dressing_class` passthrough guard so an already-extensioned
  spec draws nothing.
- `tests/test_theory_chords.py`, `tests/test_progressions_pack.py`, and a zero-draw test (place in
  `tests/test_dressing.py` or `tests/test_harmony_stage.py`, whichever holds the dressing-draw shim).

**What exists (from scoping):**
- Grammar target: `token := degree quality extgroup? bass?`,
  `extgroup := "(" ext ("," ext)* ")"`, `ext ∈ {9, b9, #9, 11, #11, 13, b13}` (PHASE_4 §3.1 as
  amended). The seven names are the keys of `EXTENSION_OFFSETS` / `_EXTENSION_LADDER` in `chords.py`.
- `resolve_token(token, key)` (`theory/chords.py`) **currently rejects** any `(`/`)`
  (`raise TokenError(... "out of scope (Phase 8, §3.5/P11)")`) and hard-codes `extensions = []`. Flow:
  `main, _, bass = token.partition("/")` → `_parse_degree` → `_resolve_quality`. `symbol`/`roman`
  rendering (`_spell`, `_quality_ext_display`, `_TIDY_DISPLAY`) **already handles** an extensions list;
  `roman` echoes the token verbatim. `extensions_legal(quality, extensions)` already exists (encodes
  §6.4). `ChordSpec.extensions` already exists (`schema/ir.py`).
- Dressing: `harmony/stage.py::_token_is_bare` already treats a `(`-bearing token as non-bare.
  `harmony/dressing.py::_dressing_class` returns `spec.quality` for non-bare `{dom7,maj7,min7}` →
  which would draw **added** extensions onto an already-pinned token. The RNG draw happens in
  `harmony/stage.py::_dress_slot` **only when `dressing_options(...)` returns ≥ 2 options**; a
  single-option class → **no `weighted_choice` draw**.

**Build:**
1. In `resolve_token`, after `partition("/")`, split a trailing parenthesized group off `main`
   (grammar `degree quality extgroup? bass?`). Parse the comma-separated ext list.
   - **Grammar errors → `TokenError` (surfaces as P5):** an unknown ext name; a malformed group;
     **an extgroup after a bare (unsuffixed) degree** (§3.5: extensions legal "only after an explicit
     quality suffix" — reject `I(9)`).
   - Pass the parsed list into `_spell` and into `ChordSpec(..., extensions=...)`. Do **not** change
     `symbol`/`roman` logic — they already render extensions.
   - **§6.4 legality:** the design pins P11 as a **distinct loader rule**. Keep the theory-layer
     grammar checks as P5 (bad name / bare+extgroup); do the **quality-legality** check (`if not
     extensions_legal(quality, exts): raise ...`) at the **loader** as P11 (step 2). If it is cleaner
     to also gate legality inside `resolve_token`, ensure the loader still emits a P11-labelled error
     (the loader is where pack-authoring rules live).
2. In `packs/models.py`, add an explicit **P11** check to both `PoolEntry._check_bars` and
   `_BarsEntry._check_bars` (base of turnaround/final entries): after `resolve_token`, assert
   `extensions_legal(spec.quality, spec.extensions)` and raise `ValueError("... (P11)")` on failure.
   (These methods already loop tokens through `resolve_token` in a `try/except TokenError -> P5`.)
3. In `harmony/dressing.py::_dressing_class`, add a passthrough guard **before** the
   dom7/maj7/min7 branch: `if spec.extensions: return None` (or the codebase's "no dressing" sentinel
   for that function) so `dressing_options` returns a single `(spec, 1)` option → `_dress_slot` makes
   **no draw**. This fires only for authored-extension tokens (existing packs author none), so pop/jazz
   dressing is untouched.

**Tests:**
- `tests/test_theory_chords.py`: the existing block asserts `I7(#9)`, `bVI7(#11)`, `I(9)` all raise —
  **re-sort**: `I7(#9)` and `bVI7(#11)` now **resolve** (assert `extensions`, `symbol`, `roman`);
  `I(9)` (bare + extgroup) **still raises**; add a §6.4-illegal case that raises **at the loader**
  (e.g. `Imaj7(b9)` — b9 illegal on maj7 per §6.4). Verify `symbol`/`roman` render the §3.5 reference
  cases (`bVI7(#11)`, `V7(#9)`, `I7(#9)`).
- `tests/test_progressions_pack.py`: a pool/turnaround/final entry with an illegal-per-§6.4 extension
  is rejected with a **P11** error; a legal authored extension (e.g. `V7(#9)`) loads clean.
- **Zero-draw pin (critical, DoD §14.1):** drive `_dress_slot` (or the harmony stage) on a slot whose
  token carries an authored extension with the counting-RNG shim the harmony stage already supports,
  and assert **0 draws** consumed for that slot (contrast a bare dressable slot that draws). This is
  the pinned "authored-extension slot consumes zero dressing draws" proof.
- **Additive proof:** existing harmony goldens (`tests/test_harmony_goldens.py`) and the whole-doc
  goldens are **unchanged** — pop/jazz author no parenthesized tokens, so nothing shifts. Run them.

**Note C-03 (do not touch):** P8/P9 (turnaround/final function) read only the leading numeral and are
blind to extensions — do **not** modify `_relaunches_as_dominant` or the finals rule. Extension-bearing
cadence tokens (e.g. a future `V7(#9)` final) simply need `resolve_token` to parse the extgroup, after
which the existing function checks operate transparently.

**Return:** the re-sorted fixture list (accept vs reject with reasons), the P5-vs-P11 split you
implemented, the zero-draw test name + evidence, and confirmation harmony + whole-doc goldens are green.

---

### T4 — Allowlist growth verification (`sonnet`) — disjoint, runs any time

**Implements:** PHASE_8 §3.7 (amends PHASE_7 §5.2). **DoD §14.1** (allowlist additions).

**Files (scope):** `src/trackgen/sound/allowlist.yaml` (verify only — likely no edit),
`tests/test_sound_engine_data.py` (add a coverage test).

**What exists (from scoping):** `sound/allowlist.yaml` **already contains** (Phase 7 pre-seeded them):
`Vibrato: [frequency, depth, wet]` and
`AutoFilter: [frequency, baseFrequency, octaves, depth, wet]` — a flat top-level `ClassName: [paths]`
map; `allowlist.py::load_allowlist` builds `Allowlist.classes: dict[str, frozenset[str]]`; effect and
instrument classes share one flat namespace.

**Do:**
1. Confirm the two entries match PHASE_8 §3.7 **exactly** (path sets, order irrelevant since they
   become frozensets). If — and only if — they diverge, correct `allowlist.yaml` to §3.7.
2. Add a coverage test to `tests/test_sound_engine_data.py` asserting
   `load_allowlist().classes["Vibrato"] == frozenset({"frequency","depth","wet"})` and
   `load_allowlist().classes["AutoFilter"] == frozenset({"frequency","baseFrequency","octaves","depth","wet"})`
   — a guard that would fail if the entries were removed or altered. Follow the existing test file's
   style.

**Return:** confirmation the entries match §3.7 (or the one-line correction made), and the test name.

---

### T5 — Whole-chunk review + DoD 1 + close-out (orchestrator)

After T1–T4 are committed and gates green:
1. **Two-lens review** (fresh **opus** agents, in parallel — disjoint lenses over the whole chunk's
   diff, not per-task): (a) **correctness/contract** — does the trace faithfully mirror
   `generate_track` (no draw-order change)? do the feel/extension/allowlist changes match §3.4/§3.5/
   §3.7 exactly, additive, with pop/jazz byte-identical? is the P5-vs-P11 split faithful and C-03
   untouched? (b) **test-quality/DoD** — are the rejection fixtures non-vacuous and discriminating? is
   the zero-draw pin real (would it fail if the guard were removed)? are the ≤25 cap tests genuine?
2. For each confirmed finding: a **validation** agent confirms it's real, then a fix agent + gate
   re-run (max 2 cycles per finding; escalate if a finding survives).
3. **DoD §14.1 checklist** with evidence (test names): feel profiles + `feelTable` selection (both new
   tables match §3.4, caps enforced); authored-extension parsing with P11 rejection fixtures +
   zero-draw pin-semantics; allowlist additions confirmed.
4. **Close out:** update PROGRESS.md (task statuses + commits, session-log row, fresh handoff block
   pointing at C2); add any CAVEATS entry if a deviation occurred (none anticipated — all additive);
   commit the doc updates. Report built / gate evidence / DoD status / next session (C2 validators).

---

## Verification each task must pass (recap)

- Four gates green (`pytest` · `ruff check` · `ruff format --check` · `mypy`) — run and read output.
- **Additive invariant proven:** the two whole-document milestone goldens
  (`fixtures/{pop_rock,jazz}.milestone.trackdoc.json`) and the humanizer/harmony goldens pass
  **without fixture edits**. If any golden shifts, **stop and escalate** — an additive change should
  never move them.
- Determinism intact (no new entropy sources; `generate_trace` preserves draw order).
