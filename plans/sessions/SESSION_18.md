# SESSION 18 — Phase 8, Chunk 4: Golden corpus + `bless` + smoke matrix

**Status: PLAN — AWAITING USER APPROVAL. No implementation agent dispatched yet.**

Implements PHASE_8 **§8.2** (golden corpus & the bless workflow) and proves **DoD §14.5 + §14.6**.
Fresh chunk; the C1 pipeline trace, the C2 validator suite, and the C3 tooling conventions are the
substrate. Everything here is **additive** — a new `tooling/` module pair + a new CLI subcommand +
new fixtures + new tests — so the existing **4858-test** suite must stay green with **zero edits to
any existing fixture** (the C1/C2/C3 byte-identity discipline continues).

Orchestrator reads this file; implementer subagents are pointed at the specific task section below.

---

## 1. Session scope

1. **Golden corpus** (§8.2) — a matrix of cells captured at **every IR boundary** to
   `fixtures/goldens/<pack>/<mood>/<len>-<seed>/<stage>.json`, so a diff localizes to the **first
   divergent stage**.
2. **`trackgen bless`** (§8.2) — re-render the corpus and emit a **semantic diff report** (per track:
   first divergent stage · notes added/removed/moved per document track/section · Layer-3 metric
   deltas · **never raw JSON diffs**), plus `--approve` (rewrite baselines) and the
   **`generatorVersion`-bump check**.
3. **Smoke matrix** (§8.2) — packs × supported moods × 3 length buckets (60/180/480 s) × 5 seeds
   (**315 cells** at the two reference packs), gating on **Layers 1–2**.
4. **300-seed reference sweep** (§8.2) — run clean.
5. **Deliberate-change rehearsal** (DoD §14.5) — make a benign change, read the report, bless it in a
   **dedicated commit**; document the outcome.

### Scope decisions taken at the approval gate (user-ratified, session 18)

| # | Decision | Rationale |
| --- | --- | --- |
| S18-1 | **Smoke matrix ships as a pytest module**, not a CI workflow. DoD §14.6's literal "in CI" clause is **not** satisfied — logged as a caveat. | No CI substrate exists in the repo (no `.github/`, Makefile, tox, pre-commit, or scripts); committing to a provider is unpinned infrastructure. Precedent-consistent with the unmarked 1575-doc Phase 6 matrix. |
| S18-2 | **IR stage files use compact separators**; `document.json` keeps `indent=2`. | ~25 MiB → ~12 MiB at 24 cells (~60 MiB → ~30 MiB at five packs), churned per bless. §8.2 makes the *report* the reading surface ("never raw JSON diffs"), so stage-file hand-readability is not load-bearing; `document.json` stays pretty to match the existing `fixtures/*.milestone.trackdoc.json` convention. **All 9 boundaries are kept** — no §8.2 amendment. |
| S18-3 | **Mood triple = default + the two moods farthest apart in the combined (V, A) plane** (Euclidean), derived by one shared helper so all five packs resolve identically. | §8.2's "default + the supported set's V/A extremes" is under-determined (valence and arousal select different moods). The diagonal exercises the widest musical span in 3 cells. |
| S18-4 | **300-seed sweep = 300 seeds × 2 reference packs at default params** (600 renders, ~30 s), gated on Layers 1–2; a "cell" for the rule-of-three bound is `(pack, seed)`. | The plainest reading of §8.2's sentence; the exhaustive cross (~37,800 renders / ~28 min) has nowhere to run given S18-1. |

### Recommendations carried into the plan (flagged; overridable at the gate)

| # | Decision | Recommendation |
| --- | --- | --- |
| S18-5 | Is `selection` a corpus boundary? | **No — 9 stage files, no `selection.json`.** §8.2's boundary list enumerates exactly 9 and omits `SelectionResult`; it is also the only trace field that is not JSON-round-trippable (tuple-keyed `dict[tuple[str, Role], …]`). Adding it means inventing a key-flattening encoder for an unpinned boundary. |
| S18-6 | Note identity for add/removed/**moved** | `NoteEvent` (`schema/document.py:116`) has **no id**, and phrase tags are serialize-dropped, so "moved" needs an invented matching rule. **Pin: within a `(track_id, section_id)` bucket, notes matching on `(midi, duration_ticks)` and differing in `ticks` by ≤ 240 (an 8th) are one `moved`; everything else is `added`/`removed` by multiset difference.** Deterministic tie-break: pair by ascending `ticks`. |
| S18-7 | Section attribution key | **`FormSection.id`** (e.g. `solo-2`), read from the cell's `songform.json`. `doc.Section` carries only `label`/`type` with no id and no uniqueness guarantee (`quality/_common.py:36-39` warns validators off it). The corpus stores `songform.json` anyway, so the report is fully offline-derivable. |
| S18-8 | `generatorVersion` bump-check mechanism | Compare the **committed baseline** `document.json`'s `meta.generatorVersion` against the freshly-rendered value (`serialize._GENERATOR_VERSION`, currently the hardcoded `"0.1.0"`). If any cell shows a **note-affecting** divergence and the two versions are **equal**, `--approve` **refuses** with an actionable message. `meta.generatorVersion` is **excluded from diff reporting** so a bump does not itself report as a divergence in all cells. `pyproject.toml:version` is **not** coupled (they are independent strings today; coupling them is unpinned). |

### Explicitly OUT of scope (later chunks — do not build)

- **The three new packs** (chill_lofi/blues/fusion_jazz) → C6–C8. The corpus therefore covers the
  **two reference packs only** (2 packs × 3 moods × 2 lengths × 2 seeds = **24 cells**), not §8.2's
  60-track five-pack matrix. The fill-out lands per-pack as C6–C8 author them. **Caveat-logged.**
- **Reference-pack refinement, `calibration.yaml`, listening/error-spotting** → C5 (DoD 2). C5
  *enumerates the abridged pop_rock/jazz banks*, which **will change every render and invalidate every
  golden C4 captures**. This is expected and by the pinned hard ordering (§9.4 / D13): C4's re-bless in
  C5 is the workflow's first real exercise. See §5.3 — it is *not* the DoD-5 rehearsal, which C4 runs
  itself on a controlled change.
- **Layer-3 bands as a gate.** L3 is batch-only/warn-only (§8.1, §8.3) and `calibration.yaml` does not
  exist until C5, so the smoke matrix gates on `validate_pipeline` only. The bless report *displays*
  L3 metric deltas; it never fails on them.
- **Any CI provider config** (per S18-1).

---

## 2. Contracts consumed (all already built — verify before relying)

- **`pipeline/trace.py::generate_trace(raw_params, *, explain=None) -> GenerationTrace`** — frozen
  dataclass (`trace.py:44-66`); field order **is** stage order: `plan, song_form, harmony,
  arrangement, selection, phrases_stage5, phrases_stage6, phrases_stage7, tempo_events, sound_design,
  document`. `generate_track` delegates to it, so the trace is provably the production chain.
- **Every §8.2 boundary has a trace field**; the 9 corpus stages and their sources:

  | `<stage>.json` | trace field | type |
  | --- | --- | --- |
  | `plan` | `plan` | `GenerationPlan` (pydantic, `schema/ir.py:95`) |
  | `songform` | `song_form` | `SongForm` (`ir.py:143`) |
  | `harmony` | `harmony` | `HarmonicPlan` (`ir.py:189`) |
  | `arrangement` | `arrangement` | `ArrangementPlan` (`ir.py:220`) |
  | `phrases_stage5` | `phrases_stage5` | `list[Phrase]` (`ir.py:237`) |
  | `phrases_stage6` | `phrases_stage6` | `list[Phrase]` |
  | `phrases_stage7` | `phrases_stage7` | `list[Phrase]` |
  | `tempo_events` | `tempo_events` | `list[Tempo]` (`schema/document.py:84`) |
  | `sound_design` | `sound_design` | `SoundDesign` (`sound/stage.py:80`) |
  | `document` | `document` | `TrackDocument` (`schema/document.py:187`) |

  That is **10 files** (§8.2's 9 named boundaries, with `tempo_events` split out rather than folded
  into the phrases-7 file — it is a distinct pinned artifact and diffs independently).
- **Serialization convention** (`pipeline/serialize.py:177-179`, writer at
  `tests/_regen_milestone_fixtures.py:36`): `json.dumps(doc.model_dump(by_alias=True,
  exclude_none=True), indent=2)` + explicit trailing newline, utf-8. **The IRs are deliberately
  non-aliased snake_case** (`schema/ir.py:3-5`) — dump IR stage files **without** `by_alias`, and
  **without** `exclude_none` (an explicit `"swing": null` is informative). Per S18-2, IR stages use
  compact separators; `document.json` keeps `indent=2` + `by_alias=True, exclude_none=True`.
- **Comparison is on parsed dicts, not strings** (`tests/test_whole_document_goldens.py:68-75`) so
  formatting drift never causes a false diff. The *writer* still matches the pinned formatting.
- **`quality/suite.py`**: `validate_pipeline(doc, trace) -> list[str]` (hard failures: V1–V8 → W1–W8 →
  L2-1; **empty == valid**; the module docstring names it "the gate used by CI/smoke") and
  `pipeline_warnings(doc, trace) -> list[str]` (L2-2, non-gating).
- **`quality/layer3.py::compute_metrics(trace) -> Metrics`** — takes the **whole trace**, not the
  document (it needs `_common.governing_chord`). `Metrics` = `{n_bars: int, tracks: dict[str,
  TrackMetrics], groove_consistency: float | None}`; `TrackMetrics` = `{role, note_density, mean_ioi,
  pitch_range, empty_bar_rate, scale_consistency}`. **Nulls are meaningful, not zero** — a delta
  formatter must render `None`↔value transitions explicitly, never as `0`.
- **`quality/_common.py`**: `tick_to_section(trace)` → `tick -> FormSection | None`; `section_span()`.
  `FormSection.id = f"{type}-{index}"` (1-based per type). `_TICKS_PER_BAR = 1920` (v1 4/4).
- **Mood data**: `resolve_pack(pack_id).interpreter.supported_moods` / `.default_mood`
  (`packs/models.py:414`, `:447`); (V, A) anchors in `src/trackgen/interpreter/moods.yaml`
  (`MoodRow`, `interpreter/moods.py:63-68`). Actual lists — **pop_rock** default `happy`, 11 supported
  (no `mysterious`); **jazz** default `nostalgic`, 10 supported (no `triumphant`/`aggressive`).
- **`generatorVersion`**: `Meta.generator_version` (`schema/document.py:76`), set from
  `_GENERATOR_VERSION = "0.1.0"` (`pipeline/serialize.py:38`). Never bumped. Independent of
  `pyproject.toml:version`.
- **C3 tooling conventions** (`tooling/audition.py`, `calibrate.py`) — match them exactly: module
  docstring opens with tool name + pinned §-ref; one public core function with keyword-only options;
  `_UPPER_SNAKE` private constants; **report formatting split from the artifact write** as a pure
  public `format_*(...) -> str` (so tests assert on the string, never on captured stdout);
  `typer.BadParameter` for bad input; `raise typer.Exit(code)` to fail (the `lint` pattern);
  `Annotated[T, typer.Option("--flag", help=...)]` CLI registration in `cli.py`.

---

## 3. Task list

Waves: **T1 ‖ T4** (disjoint files) → **T2** → **T3** → **T5** (orchestrator) → **T6**.

### T1 — Corpus module: cell enumeration + stage encode/decode — `opus`

**Files:** `src/trackgen/tooling/corpus.py` (new), `tests/test_corpus.py` (new). **Writes no
fixtures.**

Implements §8.2's corpus mechanics as a pure library — no CLI, no diffing.

- `MOOD_TRIPLE` derivation per S18-3: a public helper `corpus_moods(pack_id) -> tuple[str, str, str]`
  = `(default, extreme_a, extreme_b)` where the two extremes are the supported-mood pair maximizing
  Euclidean distance in the (V, A) plane. **Deterministic tie-break required** (sort candidate pairs
  by `(-distance, mood_a, mood_b)`) — assert it in a test, since a tie would otherwise make the whole
  corpus non-reproducible.
- `CELLS` / `corpus_cells() -> list[Cell]` — the 24-cell matrix: 2 packs × the mood triple × lengths
  `(120, 240)` × 2 seeds. **Seeds are pinned literals in the module** (base36 u64 strings), not
  derived, so the corpus is stable forever.
- `cell_dir(cell) -> Path` → `fixtures/goldens/<pack>/<mood>/<len>-<seed>/`.
- `STAGES: tuple[str, ...]` — the 10 stage names in trace order (§2's table). This constant is the
  **shared contract T2 and T3 both import**; do not redefine it elsewhere.
- `render_cell(cell) -> GenerationTrace` — the literal `generate_trace({"styleFamily": …, "mood": …,
  "maxLengthSec": …, "seed": …})` call.
- `encode_stage(trace, stage) -> str` / `decode_stage(stage, text) -> object` — per S18-2 formatting.
  Round-trip must be **exact**: `decode(encode(x))` equals `x.model_dump()` for every stage on both
  packs. `phrases_*` and `tempo_events` are JSON arrays of model dumps.
- `write_cell(trace, cell)` / `read_cell(cell) -> dict[str, object]` (parsed dicts, per §2).

**Verification:** all four gates. Tests must include — the tie-break determinism assert; a
round-trip test per stage on **both** packs; a test that `corpus_cells()` has exactly 24 entries and
is non-degenerate (all 24 dirs distinct, moods actually differ per pack); a **byte-stability** test
that encoding the same cell twice is identical. **Do not commit any fixture** — write to `tmp_path`.

### T2 — Semantic diff report — `opus`

**Files:** `src/trackgen/tooling/blessdiff.py` (new), `tests/test_blessdiff.py` (new). Imports
`STAGES`/`read_cell` from T1's `corpus.py`; **does not edit it.**

Implements §8.2's report format. Pure functions over parsed dicts — no I/O beyond T1's readers, no
CLI.

- `first_divergent_stage(baseline: dict, fresh: dict) -> str | None` — walks `STAGES` in order,
  returns the first name whose parsed dict differs, else `None`.
- `note_deltas(baseline_doc, fresh_doc, songform) -> …` — per `(track_id, section_id)`, the
  **added / removed / moved** counts per S18-6. Section attribution per S18-7 (from the cell's
  `songform.json`, **not** `doc.sections`). Notes outside every section span must be counted, not
  silently dropped — bucket them under a explicit `"(unsectioned)"` key.
- `metric_deltas(baseline_metrics, fresh_metrics) -> …` — L3 deltas; **`None`↔value transitions
  rendered explicitly**, never coerced to `0`.
- `format_report(results) -> str` — the human-readable report. **Never emits raw JSON diffs** (§8.2's
  central constraint — the report exists to be small enough to actually read). Excludes
  `meta.generatorVersion` per S18-8. A clean corpus reports a one-line "no divergence".

**Verification:** all four gates. Tests must be **discriminating** — construct synthetic
baseline/fresh pairs where exactly one note moves by 120 ticks (→ 1 `moved`, 0 add/remove), one moves
by 480 ticks (→ 1 add + 1 remove, **not** moved), a stage-3 divergence with identical stage-9 output
(→ first-divergent-stage is `harmony`, proving the localizer), and a `None`→float metric transition.
Assert on the returned string from `format_report`, never on stdout.

### T3 — `trackgen bless` CLI + baseline capture + version check — `opus`

**Files:** `src/trackgen/tooling/bless.py` (new), `src/trackgen/cli.py` (edit: register the command),
`tests/test_bless.py` (new), **`fixtures/goldens/**` (the committed 24-cell baseline)**.

- `bless(*, approve: bool, cells=None) -> BlessResult` — re-render every cell, diff against the
  committed baseline via T2, return the structured result; `format_report` prints it.
- **`--approve`** rewrites baselines. Per S18-8: if any cell has a **note-affecting** divergence and
  the baseline's `meta.generatorVersion` equals the freshly-rendered `_GENERATOR_VERSION`,
  **refuse** with an actionable message naming the file to bump (`pipeline/serialize.py:38`). A
  first-capture (no baseline on disk) is not a divergence and is always allowed.
- Exit non-zero via `raise typer.Exit(1)` when a diff exists and `--approve` was not passed.
- **Capture the 24-cell baseline** and commit it. Per S18-2: ~12 MiB. Report the actual on-disk total
  in the task report.

**Verification:** all four gates, plus — `bless` on the freshly-captured corpus reports **no
divergence** and exits 0; a monkeypatched note-affecting change is detected, and `--approve` is
**refused** at equal `generatorVersion` then **accepted** once bumped (both asserted; this is the
DoD-5 mechanism and must not be vacuous). Confirm the committed corpus round-trips: re-reading every
committed file parses and equals a fresh render.

### T4 — Smoke matrix + 300-seed sweep — `opus`

**Files:** `tests/test_smoke_matrix.py` (new). **Touches no `src/` file** — disjoint from T1/T2/T3,
so it runs in parallel with T1.

- **Smoke matrix** (§8.2): both packs × **every supported mood** × lengths `(60, 180, 480)` × 5 seeds
  = (11 × 3 × 5) + (10 × 3 × 5) = **315 renders ≈ 27 s serial**, a few seconds under `-n auto`.
  *(Corrected during T4: the plan first printed `2 × (11+10) × 3 × 5 = 630`, which double-counts the
  pack dimension — the per-pack mood counts sum, they do not multiply by 2. The T4 agent followed the
  §8.2 dimension text rather than the wrong printed total, per ROADMAP §3 arbitration.)* Assert
  `validate_pipeline(doc, trace) == []` per cell; surface `pipeline_warnings` without failing.
- **300-seed sweep** per S18-4: 300 seeds × 2 packs at default params (600 renders, ~30 s), same gate.
- Follow the `tests/test_phase7_property.py` convention: build the matrix, `@pytest.mark.parametrize`
  with readable ids, and add a **`test_matrix_non_vacuous`** asserting the exact expected cell count
  and non-degeneracy — so a silent shrink fails loudly (ROADMAP §3 no-silent-caps). No pytest marks
  (repo has none; `pyproject.toml:76-78` sets only `testpaths`).
- **The 480 s bucket has never been rendered in this repo** (prior matrices top out at 240 s). If it
  surfaces a real failure, **stop and report** — do not paper over it; that is a genuine finding, not
  a test-authoring problem.

**Verification:** all four gates; report actual wall-clock for the new module and the total suite
count delta.

### T5 — Deliberate-change rehearsal (DoD §14.5) — **orchestrator**

Not a subagent task. On a scratch commit: make a **benign, note-affecting** change, run `trackgen
bless`, **read the report**, confirm it localizes correctly and is actually readable, then
`bless --approve` in a **dedicated commit** with the `generatorVersion` bumped — then revert the
whole rehearsal. Document the report excerpt and outcome in PROGRESS.md. This is the DoD item that
proves the workflow, not just the code.

### T6 — Whole-chunk review + DoD + close-out — **orchestrator**

Fresh `opus` review agents over the whole C4 diff, in parallel, separate lenses:
1. **Correctness/determinism** — corpus byte-stability, mood-triple tie-break, the move-matching rule's
   edge cases, version-check logic.
2. **Contract/DoD compliance** vs §8.2 + §14.5/§14.6 — including an honest verdict on the two
   deviations (2 packs not 5; no CI).
3. **Test quality** — are the diff tests genuinely discriminating, or would they pass against a
   broken matcher?

Each finding gets a validation agent before any fix; confirmed findings get a fix agent + gate re-run
(max 2 cycles). Then PROGRESS.md close-out + CAVEATS entries + commit.

---

## 4. Model assignment

| Task | Model | Why |
| --- | --- | --- |
| T1 corpus module | `opus` | Encoding/determinism judgment; the tie-break and byte-stability are subtle. |
| T2 semantic diff | `opus` | The move-matching rule and report design are the chunk's hardest judgment. |
| T3 CLI + capture + version check | `opus` | Refusal semantics + committing 12 MiB of baselines. |
| T4 smoke matrix + sweep | `opus` | Non-vacuity discipline + the untested 480 s bucket. |
| T5/T6 | orchestrator + `opus` reviewers | Per PROMPT §2/§3. |

No task clears the "truly trivial" bar, so **no `sonnet` dispatch this session**.

---

## 5. Risks & escalation triggers

1. **The 480 s length bucket is untested territory** (§3 T4). A failure there is a real finding —
   escalate, do not tune the test.
2. **Corpus churn is permanent.** Once `fixtures/goldens/**` is committed, every future pack-data or
   engine change rewrites it. S18-2 halves the cost; the C5 re-bless is the first real exercise.
3. **C5 will invalidate this corpus one session later** (it enumerates the abridged reference banks).
   Expected and by the pinned ordering — but it means C4's baselines are short-lived by construction.
   **This is not the DoD-5 rehearsal** (T5 runs that on a controlled change); it is the workflow's
   first production use.
4. **Escalate immediately if** the corpus proves non-byte-stable across runs, the `generatorVersion`
   check needs to couple to `pyproject.toml`, or the report cannot be made readable without raw JSON
   (that would contradict §8.2's central constraint and needs a doc amendment + sign-off).

---

## 6. DoD coverage map

| DoD item | Task | Note |
| --- | --- | --- |
| §14.5 corpus at every IR boundary | T1, T3 | **2 packs / 24 cells**, not 5 packs / 60 — caveat-logged; fills out in C6–C8. |
| §14.5 `bless` + semantic diff report | T2, T3 | first-divergent-stage · note add/remove/move · metric deltas. |
| §14.5 `generatorVersion`-bump check | T3 | Per S18-8. |
| §14.5 deliberate-change rehearsal documented | T5 | Orchestrator-run; PROGRESS.md evidence. |
| §14.6 smoke matrix (packs × moods × 3 lengths × 5 seeds, Layers 1–2) | T4 | **As a pytest module, not CI** (S18-1) — caveat-logged. |
| §14.6 300-seed reference sweep clean | T4 | Per S18-4. |

## 7. Expected CAVEATS entries

- **C-17** — C4's golden corpus covers **2 of 5 packs** (24 of 60 cells); the five-pack matrix fills
  out as C6–C8 author the packs. Scope moved between sessions, forced by the pinned hard ordering.
- **C-18** — DoD §14.6's "smoke matrix **in CI**" is satisfied as a pytest module in the four-gate
  suite; no CI substrate exists in the repo and choosing one is unpinned infrastructure (S18-1). The
  §8.2 "nightly/weekly" 300-seed cadence likewise has nowhere to run — the sweep runs in-suite.
- Plus any arbitration/ambiguity resolution T1–T4 surface (S18-5/6/7/8 are recorded here as plan
  decisions; if any turns out to contradict pinned text rather than fill a gap, it becomes a caveat).
