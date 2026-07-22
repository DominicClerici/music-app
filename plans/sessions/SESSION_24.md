# SESSION_24 — Phase 8, Chunk 10: the final chunk (coverage depth, listening tooling, phase close-out)

**Status:** **APPROVED 2026-07-21** (S24-0…S24-5 all ratified as recommended) — IN PROGRESS.
Fresh chunk (C9→C10 split ratified S23-0).

> **User ruling on the listening block (2026-07-21): "minimal now, rest later."** Build **and
> demonstrate** the A/B harness (T5) and rubric tooling (T6) this session — enough to satisfy
> §14.8d's *tooling* clause (the harness demonstrated on one real change, mechanism-level) — but
> **defer the multi-hour human listening obligations** (full rubric pass over 5×3, the C5
> reference-pack error-spotting pass, T1 levels, T2 FM-piano) to a later sitting. **Phase 8 closes
> this session as "built, listening-pending," not fully "done."** T9 shrinks accordingly (no
> 3.5–5 h package is pre-rendered now); T10 stamps "built" and records the deferred obligations as
> an explicit, reproducible checklist for whenever the user runs them.

This is **the last chunk of Phase 8 and of the roadmap.** With it complete, all eight phases
are built: `generate(params, seed) → TrackDocument` stands across five style families.

### Task ledger

| Task | Status | Commit | Note |
|---|---|---|---|
| plan | **done** | `86df32c` | S24-0…S24-5 ratified; listening "minimal now, rest later" |
| T1 W2 blind-fill fix | **done** | `e4927cc` | APPROVE-WITH-NITS + docstring nit fixed; latent-not-live confirmed |
| T2 threshold pin | **done** | `0cdcd02` | APPROVE; exact (0.95,0.98) ×5, proven to discriminate |
| T3 reachability lint | **done** | `af2a4bf` | APPROVE-WITH-NITS (3 latent nits fixed/documented); per-id markers; all 5 packs lint clean; **C-20 rung-1 dormancy on both reference packs, annotated** |
| T4 GAP-1 dry-render | **done** | `03bfe8b` | APPROVE-WITH-NITS (both fixed); **233 candidates, 0 latent bugs**; seam generation-neutral (bless 60/60, no gv bump); 12 chill_lofi pads unroutable (pinned skips, C-22 extreme) |
| T5 A/B harness + audition flags | **done** | `019cdba` | APPROVE-WITH-NITS; binomial + unblinding verified; A3 closed |
| T6 rubric tooling | **done** | `9cf5f2d` | APPROVE-WITH-NITS (notes-capture test hardened); 20 anchors; 15 cells 1:1 with corpus |
| T7 whole-phase 4-lens review | **in progress** | — | 4 lenses over all 9 chunks + C10 diff |
| T8 §14 DoD sweep | not started | — | |
| T9 A/B demo + listening runbook | not started | — | |
| T10 close-out | not started | — | |

**T3 finding (verified):** the faithful reachability lint reveals both reference packs have dead
rung-1 mains (pop_rock ×8, jazz ×6) — same section-kind-floor mechanism as blues C-23, already
documented in **C-20** (open). User ruled **per-id markers** (not file-level, which over-silences).
T3b refactors lint silencing to per-pattern-id, migrates chill_lofi/blues/fusion markers, annotates
the 14 reference ids, reworks fixtures, notes C-20's lint remedy delivered.

**Baseline at session start:** `a838b3d`, four gates green — suite ~11053 tests / ~100 s;
`_GENERATOR_VERSION` **0.1.3**; corpus 60/60; ruff clean; mypy clean. Never `git push`.

---

## 0. The structural fact that shapes this session

C10 mixes **buildable, machine-verifiable tooling** (which I drive to green and commit) with a
**3.5–5 h human listening block** (which only the user can perform — an orchestrator cannot
self-certify subjective quality). Therefore this session **cannot stamp Phase 8 "done" on its
own.** Its honest arc is:

1. **Build phase** (T1–T6) — all remaining tooling and validator-coverage work, each gated + reviewed + committed.
2. **Machine review + DoD** (T7–T8) — whole-phase 4-lens review across all nine chunks; the full §14 DoD 1–11 sweep for every *machine-checkable* clause.
3. **Human handoff** (T9) — a guided listening package (pre-rendered cells, A/B trials, rubric runbook, reference-pack error-spotting seeds). **Session pauses here.**
4. **Close-out** (T10) — after the user completes the listening block and reports results, the final PROGRESS/CAVEATS/session-log updates and the phase-done stamp.

The listening clauses of DoD §14.8 and §14.10 stay **PENDING-USER** until step 4.

---

## 1. Scope

**In scope (build, this session):**

- **GAP-1 dormant-content dry-render** (§14.4/§14.10 coverage honesty; closes/advances C-20, C-22, C-23, C-28).
- **Reachability lint** (§14.7 linter completeness; converts C-22/C-23/C-28 prose caveats into enforced `# expected-unreachable` markers).
- **A/B harness** (§14.8d) + the audition `--ensemble`/`--role-flavors` flags (closes session-22 anomaly A3).
- **Milestone rubric tooling** (§14.8): 4-axis × 5-point anchor text + schema + capture command.
- **F4 — W2 blind-fill fix** (§14.4 validator correctness).
- **Per-pack `l2Thresholds` pin** (§14.4; survivor M16).
- **Whole-phase 4-lens review** across all nine chunks; **full §14 DoD 1–11 sweep**.
- **Listening package** prepared and handed to the user.

**Out of scope (recorded, not built):**

- **Blind-fill coverage in GAP-1** — fills are a stage-6 device path emitting no `PatternRecord`
  (`transitions/devices.py:95-109`), so they need a *different* seam than the `SelectionResult`
  injection GAP-1 uses. Deferred (SESSION_23 §2 "not in scope at all"). Main/intro/ending bank
  candidates only.
- **The L3 warn-only warner** — §8.1's batch-only band warner was never built; `suite.py:17`
  deliberately excludes it, and the n=3 batch yields under-dispersed bands a naive warner would
  fire on constantly. DoD §14.4c's literal text ("L3 metrics + band computation") is satisfied by
  the existing `layer3.py` + `calibration.py`. **Recorded as a known, out-of-literal-DoD gap in
  the sweep, not built** (S24-3).
- **C-25 (mode × pool-gate) and the arrangement-layer-cap reachability classes** — deferred with
  reasoning at SESSION_23 §4 R5; the reachability lint models C-22 (arousal) + C-23 (section-kind
  floor) only.
- The **human listening block itself** — user-only; T9 packages it.

---

## 2. Decisions requiring ratification at the gate

Ratify individually. Each states the recommendation and the rejected alternative.

| # | Decision | Recommendation | Rejected |
|---|---|---|---|
| **S24-0** | **C10 = build + machine-review + DoD this session; human listening + phase-done stamp is the tail** (§0) | **Accept the two-step arc.** The listening block is human-gated and async; the build is one coherent unit. Phase "done" is stamped at T10 after the user listens. | Pretend the phase can be self-certified this session (would record listening-gated DoD clauses PROVEN with no listener — against this project's "never round up" discipline) |
| **S24-1** | **GAP-1 seam** — add an optional forced-`SelectionResult` injection to `generate_trace` (`trace.py:102`), default `None` = today's behavior; harness enumerates every main/intro/ending bank candidate per pack, forces each through retarget→voicing→serialize, runs `validate_pipeline`, asserts clean (any genuine failure → fix or caveat) | **Proceed.** The `generate()` seam alone returns stage-5 phrases, not a trace — full W1–W8 + document coverage needs the trace path. The injection is **generation-neutral** (default no-op, no golden moves, no gv bump). Enumeration template: `test_fusion_jazz_variety.py:213-218`, generalized to 5 packs. | (a) "Win-the-draw" params per id (today's approach — cannot reach the ~70 structurally-dormant ids *by construction*, which is the whole point). (b) Inject at `generate()` (too low — no document, no Layer-1) |
| **S24-2** | **A/B demo axis** = `roleFlavors`/`ensemblePreset` at a fixed `(pack, mood, seed, length)` | **Use the flavor axis.** Already first-class validated params (`params.py:209,316`), needs no code change to produce two distinct docs at one seed, and building the harness **closes A3** (audition has no flavor flag today). Natural demonstrator: fusion `funk_kit` vs `fusion_ride_kit`, or `rhodes` vs `clav` (the session-22 09a/09b/10 fixtures already probe these). | A before/after *code-state* A/B (also supported by the same harness across a git checkout, but heavier and not needed to satisfy "one real change") |
| **S24-3** | **L3 warn-only warner NOT built**; recorded as a known gap in the DoD sweep | **Record, don't build** (§1 rationale). | Build it now (out of literal §14.4c scope; needs a dispersion-floor design the n=3 batch makes non-trivial; would balloon the final chunk) |
| **S24-4** | **Reachability lint** models per-mood arousal × per-section-kind energy floor (C-22 + C-23); marker granularity stays **file-level** (the existing convention) unless a pack needs mixed reachable/unreachable content in one role file — then refine to per-id | **Proceed, file-level default.** All machinery is present (`section_energy` is a one-line import; `load_moods`/`derived_defaults`/`intensity`/`supported_moods` already imported). Refine granularity only where a real pack forces it. | Per-id refactor up front (speculative complexity — decide from what actually fires) |
| **S24-5** | **Fusion comping threshold = 0.98** confirmed; per-pack pin asserts **(bass 0.95, comping 0.98)** for all five packs | **Pin 0.98.** S23-2 resolved as **option D** (widen L2-1's allowed set, C-32) — **no threshold edit was ever made**; the committed artifact is 0.98 everywhere (verified). The "0.97" in the superseded S23-2 plan row is dead. | Pin 0.97 (would encode a value that was never committed and was explicitly abandoned by §3a-FINAL) |

---

## 3. Task list

Serial unless marked ‖. Every dispatch sets `model` explicitly (PROMPT §"Subagent model rules").
Per-task loop: implement → orchestrator runs 4 gates → opus review scoped to that task's diff →
bounded fix loop (max 2) → commit + PROGRESS.md update.

### Build phase

| # | Task | Files (scope) | Model | Verification |
|---|---|---|---|---|
| **T1 ‖** | **F4 — W2 blind-fill fix (S24 / SESSION_23 §5 F4).** Move `legal_fill_bars.add(...)` **inside** the `if entered.type not in _SUPPRESSION_TYPES` guard at `layer1.py:361-362`. Add a violating fixture: a `"fill"`-tagged stage-6 note in a suppressed (`breakdown`) boundary's fill bar that now fires W2. Mirror the helper recompute in `test_quality_layer1.py:466-513`. Confirm no current render regresses (devices.py:239-245 `continue`s before the fill path for both suppression types — the leniency is latent). | `src/trackgen/quality/layer1.py`, `tests/test_quality_layer1.py` | opus | 4 gates; new fixture fires W2 and only W2; **no golden moves**; full suite still green |
| **T2 ‖** | **Per-pack `l2Thresholds` pin (S24-5 / M16).** Extend `test_quality_layer2.py::test_load_l2_thresholds_reads_blessed_artifact` from pop_rock/jazz-only, `0<x<=1` to **all 5 packs, exact equality** `(0.95, 0.98)` via `load_l2_thresholds`. Closes the byte-repro blind spot for thresholds (bands were already pinned by C9 T3). | `tests/test_quality_layer2.py` | opus | 4 gates; a corrupted committed threshold now fails a test |
| **T3 ‖** | **Reachability lint (S24-4).** Rewrite `_reachable_rungs` (`lint.py:436-442`) to union `intensity(section_energy(kind, i, total, arousal, energy_range, override))` over supported moods × section-kinds present in `pack.forms.templates`, instead of the envelope endpoints. Import `section_energy` from `trackgen.form`. Run against all 5 packs; add `# expected-unreachable` markers (existing convention, `lint.py:88`) to the pattern YAMLs the caveats C-22/C-23/C-28 predict (chill_lofi already blanket-silences its 4 role files). Each new marker cites its caveat in a comment. | `src/trackgen/packs/lint.py`, `styles/*/patterns/*.yaml` (markers), `tests/test_lint.py` | opus | 4 gates; the lint now *fires* on the caveated dormancies pre-marker and is clean post-marker; a `test_reachability_non_vacuous` proving the warning discriminates (unmark → fires) |
| **T4** | **GAP-1 dry-render harness (S24-1).** Add an optional `selection` override to `generate_trace` (`trace.py:66,102`): when provided, skip `select_patterns` and use it; default `None` preserves today's path (assert byte-identical output for a sample cell). New `tests/test_dry_render_coverage.py`: enumerate every `main`/`intro`/`ending` bank candidate per pack (generalize `test_fusion_jazz_variety.py:213-218`), force each via a `SelectionResult`, render a full trace, run `validate_pipeline`, assert **zero W1–W8 / L2 failures** across all ~70 blind ids × 5 packs. Any genuine failure found → escalate (it would be a real latent bug the "win-the-draw" tests never reached). | `src/trackgen/pipeline/trace.py`, `tests/test_dry_render_coverage.py` | opus | 4 gates; default path proven unchanged (no golden moves, **no gv bump**); every blind id validates clean or a real defect is surfaced |
| **T5** | **Audition flavor flags + A/B harness (S24-2; §14.8d, A3).** (i) Add `--ensemble`/`--role-flavors` to the `audition` CLI (`tooling/audition.py`, `cli.py`) — wires into `roleFlavors`/`ensemblePreset` raw-params. (ii) New `tooling/ab.py` + `trackgen ab` command: render two variants at a fixed `(pack, mood, seed, length)`, blinded presentation order via `stream_rng(master_from_string(...), {}, "listening_ab")` (**no `random` import** — TID251), forced-choice loop (~20 trials), exact binomial p-value via stdlib `math.comb` (no scipy dep), append an `{type: "ab", ...}` record to `listening/log.jsonl`. | `src/trackgen/tooling/audition.py`, `src/trackgen/tooling/ab.py` (new), `src/trackgen/cli.py`, `tests/test_ab.py`, `tests/test_audition.py` | opus | 4 gates; A3 flags round-trip a flavor swap into distinct docs; binomial math unit-tested; blinding reproducible from the presentation seed |
| **T6** | **Milestone rubric tooling (§14.8).** Author the 4-axis × 5-point **anchor text** (musicality, groove, style-fit, soloist space — 20 written anchors), a capture schema (`{type: "rubric", date, pack, mood, seed, scores{...}, notes}`), and `trackgen rubric`: iterate the 15 cells (`corpus_moods(pack)` → default + 2 V/A extremes per pack), render+open each via `open_playground`, echo the anchors, prompt 1–5 per axis, append to `listening/log.jsonl`. Pin the cells to fixed corpus seed/length so rubric renders are goldens. | `src/trackgen/tooling/rubric.py` (new), `src/trackgen/cli.py`, `tests/test_rubric.py`, a rubric-anchors data file | opus | 4 gates; the 15 cells resolve from pack data; schema round-trips; anchor text committed |

**Parallelism:** T1, T2, T3 have disjoint file scopes → dispatch ‖. T4 touches the generation
path (`trace.py`) — dispatch after/independent of T1–T3, watch it closely. T5 and T6 both edit
`cli.py` → **serialize T5 → T6**.

### Review, DoD, handoff, close-out

| # | Task | Model | Verification |
|---|---|---|---|
| **T7** | **Whole-phase 4-lens review** over all nine chunks (not per-task diffs) — parallel lenses: (A) correctness/determinism (TID251, seed purity, no wall-clock), (B) contract compliance vs PHASE_8 §8.1/§14 + the caveat ledger, (C) test quality & non-vacuity (mutation-probe the new C10 assertions), (D) code quality/simplification. Each finding → a **validation** agent confirms it's real before any fix; confirmed → fix agent + gate re-run, 2-cycle bound. | opus ×4 (review) + opus (validate/fix) | zero surviving blockers; findings validated-before-fixed |
| **T8** | **Full §14 DoD 1–11 sweep** with evidence (test names, fixture paths, command output) for every clause. Record honestly: L3 warner absent (S24-3), M17 (§14.6 green ≠ §14.4b coverage), the listening clauses PENDING-USER, F4 latent-not-live. | opus (assemble) + orchestrator (verify) | every machine clause has cited evidence; the pending clauses are named, not glossed |
| **T9** | **Demonstrate the A/B harness + write the deferred-listening runbook** (per the "minimal now" ruling). (i) Run the `ab` harness end-to-end on one real change (a `roleFlavors` swap) with a scripted decision sequence, proving the mechanism (blinded order, forced choice, binomial) — satisfies §14.8d's *tooling-demonstrated* clause. (ii) Write `listening/SESSION_24_RUNBOOK.md`: the exact commands + rubric anchors + §14.10 per-pack checklists + reference-pack/T1/T2 seeds, so the **deferred** human obligations are reproducible whenever the user runs them. **No 3.5–5 h package is pre-rendered now.** | opus (draft) + orchestrator | harness demo committed + reproducible; runbook self-contained; deferred obligations enumerated, not glossed |
| **T10** | **Phase close-out ("built, listening-pending").** Final §14 DoD record: every machine clause PROVEN with evidence; the human listening clauses (§14.8 rubric/T1/T2/error-spotting, §14.10 listening) marked **DEFERRED-BY-USER** with the T9 runbook as the discharge path. Final PROGRESS handoff, CAVEATS entries, session-log; **stamp Phase 8 built.** Roadmap machinery complete; only the human listening pass remains outstanding. | orchestrator | all four gates green; DoD 1–11 machine clauses complete; deferred clauses named + reproducible |

---

## 4. Contracts consumed / produced

- **Consumes:** the pinned validator suite (`quality/`), the generation path (`pipeline/trace.py`,
  `parts/generators.py`, `parts/selection.py`), the corpus/audition tooling
  (`tooling/corpus.py`, `tooling/audition.py`, `seeds.py`), the five committed packs.
- **Produces:** two new CLI commands (`ab`, `rubric`) + two audition flags; one generation-neutral
  seam (`generate_trace(selection=...)`); a stronger lint; two validator-coverage fixes; the
  listening artifacts; the phase-close DoD record.
- **Generation-neutral guarantee:** nothing in T1–T6 changes a rendered `TrackDocument`. The
  `generate_trace` injection defaults to no-op; `quality/`, `tooling/`, and `lint.py` are off the
  generation path. **No `generatorVersion` bump; `bless` must still report 60 cells, no divergence.**

## 5. Standing rules carried from C9 (binding here)

- **Any L2-1 claim** must be measured at ≥ 80 seeds × all supported moods × ≥ 5 lengths **including
  120 s**, or stated as provisional (SESSION_23 §3a-FINAL). Relevant if T4/T7 re-measure anything.
- **A caveat number reserved and never written is as lost as an unlogged deviation** — write CAVEATS
  entries in the same commit as the code that cites them.
- **Verify a reviewer's numbers (and your own) before acting** — five numbers were retracted in C9.
- **No silent caps.** Any bounded coverage (top-N, sampled) must `log`/comment what was dropped.
