# SESSION_21 — Phase 8, Chunk 7: `blues` (the second new pack)

**Scope:** author `styles/blues/` in full per `plans/PHASE_8.md` §5 and the §9.4 checklist;
land it atomically with its tests; verify the blues first-uses (authored `(#9)` extensions,
triplet-grid content through W7, tempo-gated eligibility); calibrate; run the formal §8.4
listening pass (appending to `listening/log.jsonl`); extend the golden corpus to 48 cells
(first capture). Whole-chunk review + close-out. DoD targets: **§14.3 (blues)**, **§14.8
(blues slice: error-spotting pass)**, **§14.10 (blues listening checklist)**.

**Explicitly out of scope:** `tests/test_smoke_matrix.py` extension (five-pack surface, C9 per
S20-3 precedent); the reference-pack formal listening item (C5 debt, carried to C9);
fusion_jazz (C8); any engine change not forced by a verified blues first-use bug
(contingency 13 below).

**Environment:** `uv` / Python 3.12. Four gates: `uv run pytest -n auto` · `uv run ruff check .`
· `uv run ruff format --check .` · `uv run mypy`. Baseline (orchestrator-verified 2026-07-21):
**6183 passed / 1 skipped**, all gates green at `7500f24`. `_GENERATOR_VERSION` 0.1.3.
Corpus **36/60** cells. Never `git push`.

---

## Binding constraints (from scoping, 2 opus agents, 2026-07-21)

1. **Atomic landing.** `loader.registered_styles()` discovers any `styles/*/manifest.yaml`;
   the instant `styles/blues/manifest.yaml` exists, `tests/test_interpreter_pack.py:114`
   (3-pack set) fails and `tests/test_interpreter.py:301-308`'s dynamic pack×mood matrix
   calls `resolve_pack("blues")` at collection — a partial pack raises `PackLoadError`.
   Additionally `tests/test_interpreter_pack.py:117-118` uses `resolve_pack("blues") is None`
   as its *unregistered-style example* — repoint that test to a still-nonexistent id
   (e.g. `"fusion_jazz"`). T1–T5 stay uncommitted until the whole pack + tests are green;
   **commit 1 is the complete pack**.
2. **Manifest (decision S21-1).** `Manifest` requires `formatVersion: int` + `engine: str`;
   the §5.1 printed snippet omits both (confirmed `ValidationError`). Author
   `formatVersion: 1` and `engine: ">=0.1"` (the value all three sibling manifests use)
   and amend §5.1 per arbitration rule 2 after sign-off.
3. **Rung reachability (decision S21-2 — the C-22 lesson, computed BEFORE authoring).**
   `main`-kind patterns render **only in `solo` sections** (`parts/selection.py:64-71`:
   intro→intro-kind, outro→ending-kind, everything else→main; rung matching applies to
   main only). Blues' form is all-solo; the R2 solo arch (`form/energy.py`: base
   0.60 + 0.30·index/total, + 0.10·arousal, envelope [0.15, 0.95]) puts **every solo at
   energy ≥ 0.624** — rung 3 minimum, and the final solo at rung 4 for all 8 moods
   (0.834–0.934). **Rung-1 and rung-2 mains never render, grid-wide**, for every role.
   The §5.4 ladder as printed would leave the slow-blues 12/8 showcase (rung 1) and the
   Chicago shuffle (rung 2) dormant, and `eligibility.tempoBpm: [50, 75]` would never gate
   a rendered pattern. Lint cannot see this (`_reachable_rungs` reads the envelope only —
   the C-22 gap). The S21-2 ruling below pins the response; T2/T3 authoring follows it.
4. **Variety lint (no escape):** ≥2 candidates surviving **all gates at every supported
   (mood, tempo) cell** per (role, kind, rung) slot in {main r1–4, intro, ending} — so
   each rung needs **≥2 UNGATED candidates**; the tempo-gated [50, 75] slow-blues patterns
   do NOT count toward variety at energetic/aggressive cells (~131–150 BPM). Co-author
   sibling pairs with the 3/2 weight convention. Fills are not variety-checked (PT12
   needs ≥1 ungated drum fill).
5. **NO `expected-unreachable` markers.** The envelope [0.15, 0.95] makes rungs 1–4 all
   lint-reachable, so no unreachable-content warning fires (unlike chill_lofi) — markers
   would be dead text. The S21-2 dormancy is recorded in the caveat, not lint annotations.
6. **Tempo-gate reachability:** per-mood auto tempo range ∩ [50, 150] gives melancholic
   [61, 75] (band always active) and dark [72, 88] (active when the draw lands ≤ 75); no
   other mood reaches [50, 75]. `_warn_dangling_gates` passes (band ∩ mood-window overlap
   exists). Slow-blues gated content must sit at a **reachable rung** (S21-2) to ever render.
7. **Triplet grid mechanics:** authored triplet onsets per beat are `pos_in_beat ∈
   {0, 160, 320}` (0 is grid-neutral); swing8 repositions only `pos % 480 == 240`
   (`humanize/swing.py:22,52`) so triplet events are untouched; W7 enforces per-phrase grid
   homogeneity on stage-6 output (`quality/layer1.py:442-483`); loader-time grid-mixing
   lint exists (`packs/lint.py:405-433`). One grid per pattern, strictly (§3.1).
8. **Timbre traps (TB7/TB1):** `Tremolo [frequency, depth, spread, wet]` and Distortion
   `oversample` ARE allowlisted — no allowlist gap anywhere in §5.6. But: **organ_drawbar
   AND organ_swell (both AMSynth) must fully override `mod.brightness` → `harmonicity`**
   (the role-default brightness path `filterEnvelope.baseFrequency` is illegal on AMSynth;
   §5.6 documents this for drawbar only — organ_swell is the silent trap). `warm_strings`
   should be PolySynth/**MonoSynth** (keeps default brightness legal); StereoWidener takes
   `width` ONLY. Comping/pads flavors must not author a fixed `mix.sends.reverb` (space-XOR).
   All **8** flavors need full recipes (TB1): blues_kit, roadhouse_kit, electric_round,
   upright_soft, crunch_guitar, organ_drawbar, organ_swell, warm_strings — `upright_soft`
   has no §5.6 recipe (author in-idiom from the jazz `upright` precedent), `roadhouse_kit`
   only "darker/drier". Master = pop_rock-style `[Compressor, Limiter]` (TB4 Limiter-last).
   NoiseSynth voices omit `midi` (TB5).
9. **Kit voices:** each kit flavor defines exactly the 9 `KIT_VOICE_IDS` (kick, snare, hats,
   ride, crash, tom_low, tom_mid, tom_high, perc). Cross-stick is not a schema voice —
   author it as **`perc`** (the chill_lofi rim→perc §3.6 precedent); rung-4 tom runs use
   tom_low/mid/high.
10. **PT9 retargets:** bass/comping/pads banks each need a bank-level `retarget` (span
    ≥ 12); §5.4 prints none for blues — author bass `{28, 45, retrigger}`, comping
    `{50, 69, retrigger}`, pads `{45, 64, retrigger}` (the chill_lofi values). Per C-21
    the comping/pads windows are inert for `degree: chord` events (arrangement lanes own
    chord-voicing registers) but PT9 requires them structurally.
11. **NOT first-uses (risk downgraded by scoping):** `stop: enabled` (pop_rock ships
    `[1, 4]` odds; device is golden-covered production path — blues just fires it more
    often at `[1, 3]`); swing8-table-no-override at ≤ 90 BPM (jazz already clamps at 0.722,
    e.g. melancholic 68); unbounded repeat max (`jazz forms.yaml:20` ships `[1, null]`;
    blues reaches the 480 s bucket like jazz, no C-19 ceiling). **Real first-uses:**
    authored paren extensions `I7(#9)`/`V7(#9)` (first pack ever — P11 legality verified,
    `#9` legal on dom7; pin the draw-free dressing skip); triplet-grid pattern content
    (first anywhere — W7's triplet branch gets its first production exerciser); a
    `finals`-only `bII7` (parse-only; see S21-3).
12. **Corpus (T9, after listening per §8.1 bootstrap):** triple = **(energetic, aggressive,
    romantic)** — `extreme_mood_pair` returns (aggressive, romantic) via a deterministic
    tie-break at d=1.57 vs (energetic, melancholic); default energetic ∉ pair, so
    `corpus_moods` does not raise. 12 new cells, corpus 36 → 48. First capture ⇒ **no
    generatorVersion bump** unless an engine change lands first (contingency 13).
    **Plan shape:** blues' `GenerationPlan` is fully populated (swing resolved from the
    table → concrete `{ratio, subdivision: "8"}`; `feelTable: straight` authored) — extend
    `tests/test_corpus.py:301`'s zero-null branch to `("chill_lofi", "blues")` knowingly.
13. **Contingency — engine fix forced by a first-use bug:** any engine change that alters
    pop_rock/jazz/chill_lofi output triggers the full bless collateral (generatorVersion
    bump per `bless.py` docstring; serialize/milestone literals; milestone fixture regen).
    **Escalate to the user before applying any such fix.**
14. **C-12 verified safe:** crash velocity lo 0.45 → minimum rendered crash 0.518 at the
    0.15 energy floor; no zero-velocity path.
15. **Collateral literals (T5/T9):** `tests/test_interpreter_pack.py:114` set + `:117-118`
    repoint (T5); `src/trackgen/tooling/corpus.py:105` `_CORPUS_PACKS` += blues,
    `tests/test_corpus.py` `_PACKS`/pinned-triples/counts 36→48/zero-null branch,
    `tests/test_bless.py` counts 36→48 + CLI strings ("12 of 48" / "the other 36") +
    stale comments (T9). `tests/test_interpreter.py`'s dynamic matrix needs no edit.

---

## Decision items — USER APPROVAL GATE

- **S21-1 (arbitration rule 2):** §5.1's printed manifest omits the required
  `formatVersion` + `engine` fields. Author `formatVersion: 1` / `engine: ">=0.1"`
  (sibling-verbatim) and amend §5.1 in the landing commit. **Recommended: approve.**
- **S21-2 (the headline ruling — §5.4 rung re-map):** solos only ever render rungs 3–4
  (constraint 3), so §5.4's printed ladder would leave the slow-blues 12/8 showcase and
  the Chicago shuffle permanently dormant — and a melancholic 68 BPM "slow blues" would
  render only Texas/double-shuffle content, which fails DoD §14.10's own listening
  checklist ("shuffle locks at three tempo tiers"). **Recommended: re-map the authored
  ladder onto the reachable band** — rung 3 carries the workhorse shuffles (Chicago
  family + the tempo-gated [50, 75] slow-blues 12/8 triplet patterns), rung 4 carries
  Texas/double-shuffle (the hat→ride energy lever moves to the 3→4 boundary, which the
  rising solo arch actually crosses mid-jam); rungs 1–2 are authored as sparser
  completeness variants (PT5 + variety still require 2 ungated candidates each; honest
  dormant content, caveat-recorded — the C-22 pattern). Bass/comping ladders re-map
  equivalently (box/boogie at 3, full boogie/pushes at 4; gated triplet-roll and
  triplet-arpeggio variants at 3–4 so the slow tier keeps its 12/8 feel). Amends §5.4's
  rung assignments per arbitration (the energy formulas and §5.2's all-solo form are both
  pinned; the printed rung expectations are the derived samples that don't survive them).
  **Alternative (not recommended):** author §5.4 as printed and accept full rung-1/2 +
  slow-blues dormancy — musically wrong at the slow tier and likely to fail T8 listening.
- **S21-3 (C-03 record correction):** scoping refuted the C6 handoff's "C-03 goes LIVE at
  C7" — all five §5.3 turnarounds end on plain V7 (P8's ordinary D-function branch) and
  the `tritone` final's `bII7` is validated for parseability only (P9 checks the final
  I7); nothing routes through `_relaunches_as_dominant`'s SubV branch. **Recommended:
  author §5.3 exactly as pinned and record honestly that C-03's admission stays
  unexercised in v1** (CAVEATS C-03 impact note + PROGRESS correction). Alternative: amend
  `jazz_turn` to end `bII7` to exercise SubV live — a §5.3 data change with no
  design-text support; not recommended.
- **S21-4 (derived-sample annotation):** §5.1's comment "(0.722 slow → ~0.58 fast)" and
  §3.1's "uptempo 58–62 %" are unreachable — the PHASE_2 §6.4 table yields 0.655 at
  blues' 150 ceiling (0.722 flat ≤ 90). Feel-model behavior is identical to jazz's
  existing path; only the printed ratio claim is wrong. **Recommended: one-line §5.1
  annotation in the amendment commit** (no behavior change).
- **S21-5 (pack version):** manifest lands at `version: 0.1.0` per §5.1 (S20-4 precedent).
  **Recommended: 0.1.0.**

---

## Task list (all subagents opus; parallel only on disjoint files)

### T1 — config quintet (opus)
**Files:** `styles/blues/manifest.yaml`, `interpreter.yaml`, `forms.yaml`,
`progressions.yaml`, `transitions.yaml`.
Author verbatim from PHASE_8 §5.1–§5.3 + §5.5 with exactly one deviation: the manifest
adds `formatVersion: 1` + `engine: ">=0.1"` (S21-1). Scoping pre-validated every printed
snippet: R3 `[major, minor]` legal; P4/P6/P7/P8/P9 all pass; `I7(#9)`/`V7(#9)` parse and
are P11-legal; per-bar-count harmonyTag maps `{12: blues_12, 8: blues_8, 16: blues_16}`
schema-valid; `repeat {count: [3, null]}` legal; turnaround/final 2-chord bars are not
density-filtered; TR1–TR3 pass. **Verification:** scratch script model-validating each
file + re-running the cross-file checks (mirror `scope_b` scripts). Report: files written,
checks run, any §5 ambiguity found (escalate, don't resolve).
**No commit** (constraint 1). Review: opus, diff-scoped.

### T2 — drums + bass banks (opus, parallel with T3/T4)
**Files:** `styles/blues/patterns/drums.yaml`, `patterns/bass.yaml`.
Per §5.4 conventions **under the S21-2 re-map**: drums — rung 3 mains = Chicago-family
shuffle pair (defining entry **`bl_dr_2` verbatim from §5.4 but placed per the ruling**;
see note below) + tempo-gated [50, 75] slow-blues 12/8 triplet patterns (ride triplets
pos 0/160/320 per beat, cross-stick→perc 2/4, kick 1 + pickup into 3); rung 4 mains =
Texas (four-on-floor, straight-quarter ride, `minDensity`-gated shuffled-snare ghosts) +
double-shuffle (swung ride 8ths, hardest 2/4, gated ghost layer); rungs 1–2 = sparser
completeness variants (rung 1 sparse shuffle/cross-stick, rung 2 lighter Chicago);
fills = triplet-grid snare/tom figures + a tom-run variant (≥1 ungated, 1920 t, event ≥
pos 960); thinned intro/ending entries. **`bl_dr_2` placement:** §5.4 prints it at
`energyLevel: 2`; under S21-2 the Chicago content it anchors moves to rung 3 — author the
verbatim event list at the ruling's rung with the id/weight preserved, and note the
placement in the §5.4 amendment. Bass — `mode: patterns`, retarget `{28, 45, retrigger}`:
rung 3 = the box (root/fifth/seventh/octave quarters) + **`bl_bs_3` verbatim** (the 2-bar
boogie cell, 3840 t) + tempo-gated sparse triplet arpeggios; rung 4 = shuffled-8th boogie
(straight-8th authoring, swing renders) with a `push`-flagged bar-end root; rungs 1–2 =
root halves / sparser box completeness variants. **Every (kind, rung) slot ≥2 ungated
candidates** (constraint 4), 3/2 weights; one grid per pattern (constraint 7); velocities
per §5.4's printed bands; `layeringOrder: [drums, bass, comping, pads]` once in
drums.yaml. Ids `bl_dr_*` / `bl_bs_*` (siblings `b`, intro `i/ib`, ending `e/eb`, fills
`f1/f2`); ladders monotone (C5 T7 lesson).
**Verification:** scratch model-validation (PT1/PT2/PT3/PT5/PT9/PT12), grid-purity sweep
(every pattern's pos set ⊆ straight-grid or ⊆ triplet-grid), velocity sweep. No commit.
Review: opus.

### T3 — comping + pads banks (opus, parallel with T2/T4)
**Files:** `styles/blues/patterns/comping.yaml`, `patterns/pads.yaml`.
Comping per §5.4 under S21-2: rung 3 = the chank (2 & 4 stabs) + Charleston/gap-stab pair
+ tempo-gated triplet-roll pattern; rung 4 = driving stabs with pushes; rungs 1–2 =
sustained/sparser completeness variants; voicing classes `{1: [shell2, triad_open],
2: [shell3, rootless_a], 3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}`
(printed §5.4 map unchanged — classes are per-rung config, not dormant content); retarget
`{50, 69, retrigger}`. Pads: organ footballs, `{1–4: [triad_open, fifths]}`, whole notes,
low velocity, retarget `{45, 64, retrigger}`; ladders monotone. ≥2 ungated candidates per
slot incl. intro/ending; `bl_cp_*` / `bl_pd_*` ids. C-21: do NOT try to enforce a register
floor via retarget — lanes own chord-voicing registers.
**Verification:** scratch model-validation (PT5/PT7/PT9), grid purity. No commit.
Review: opus.

### T4 — timbres (opus, parallel with T2/T3)
**File:** `styles/blues/timbres.yaml`.
All **8** flavors (constraint 8): the §5.6 defining entries verbatim (blues_kit roomy
MembraneSynth kick decay 0.45 / cracky white NoiseSynth snare decay 0.11 / prominent
MetalSynth ride; electric_round MonoSynth triangle, rolloff −12, attackHardness override
0.06→0.004, dry; crunch_guitar sawtooth + Distortion {0.3, "2x", wet 0.6}; organ_drawbar
AMSynth sine + Tremolo {5.2, 0.4, 90, 0.5} + light Distortion, **brightness fully
overridden → harmonicity 1.0–2.0**; organ_swell AMSynth swell + Tremolo, **brightness
override REQUIRED — the silent §5.6 trap**; warm_strings PolySynth/MonoSynth fatsawtooth
+ StereoWidener width-only) + roadhouse_kit (darker/drier sibling) + upright_soft
(in-idiom from the jazz upright precedent). Kit flavors define all 9 voices; NoiseSynth
voices omit midi; no fixed `mix.sends.reverb` on comping/pads (space-XOR). Bus reverb
`{decay: [0.8, 2.5], preDelay: [0.01, 0.03], returnFilterHz: 350}`; master =
pop_rock-style `[Compressor, Limiter]`.
**Verification:** scratch `TimbresConfig.model_validate` + allowlist dry-run over every
emitted path. No commit. Review: opus.

### T5 — integration + blues test suite → **commit 1** (opus)
**Files:** `tests/test_interpreter_pack.py` (line 114 set + :117-118 repoint), new
`tests/test_blues_pack.py` + `tests/test_blues_variety.py` (disjoint from reference tests).
1. First full `resolve_pack("blues")` + `trackgen lint styles/blues/` → drive to
   **0 errors / 0 unannotated warnings** (fix loop with T2/T3/T4 scopes, bounded).
2. Author tests: bank-inventory pins (M1 convention); **`bl_dr_2` + `bl_bs_3` verbatim
   goldens** (§5.4 anchors, at their S21-2 rungs); variety/selection locks per the C5/C6
   convention (every golden-blind candidate gets a locked seed winning the production
   draw); **first-use pins**: an authored-extension slot consumes ZERO dressing draws and
   `ChordSpec.extensions` carries `#9` verbatim (hendrix pool entry, forced via seed/mood);
   triplet-grid patterns survive swing8 untouched (stage-7 positions still on
   {0, 160, 320}) and pass W7; tempo-gated eligibility: melancholic render selects
   slow-blues content at a [50, 75]-drawn tempo, energetic render never does; stop device
   fires at [1, 3] odds on some locked seed; plan shape fully populated (swing
   `{ratio: 0.722@≤90 or table value, subdivision: "8"}`, feelTable straight); plus the
   end-to-end property slice: default params + (V, A) extremes × 2 lengths × ≥5 seeds →
   serialize, `validate_document == []`, `validate_pipeline == []`.
3. Four gates green → **commit 1** (pack + tests + literal updates + §5 amendments per
   S21-1/S21-2/S21-3/S21-4, one commit).
Review: opus, whole-T1–T5 diff (biggest review: content vs §5 clause-by-clause under the
S21-2 ruling, tests non-vacuous).

### T6 — full-grid audition + first-use verification pass (opus, report-only)
§9.4 step 7. Render the whole supported grid — 8 moods × both length classes × 2+ seeds,
`--explain` samples — via `generate_trace`; `validate_pipeline` + `pipeline_warnings` on
every render; confirm empirically: rung-3 content in early solos → rung-4 in final solos
(the arch crossing 0.80); slow-blues 12/8 content actually renders at melancholic (and
dark ≤ 75 draws); hendrix/jazz_turn/tritone gated entries reachable at their
valence/dissonance corners; turnarounds relaunch at chorus boundaries; stop lands when
drawn; no W7 grid violations; registers ≤ 71. Report anomalies with evidence; substantive
findings → fix agents (≤2 cycles), gates re-run.

### T7 — calibrate → **commit 2** (orchestrator + opus artifact check)
§9.4 step 8. `uv run trackgen calibrate styles/blues/` → `styles/blues/calibration.yaml`
(first batch: L2 thresholds = engine defaults, §8.1 bootstrap; zero-width L3 bands
known-latent). Independent opus artifact check (shape, L2-reader activation, band sanity,
mood coverage 8/8, byte-identical re-run). `close: cold` → no ritard-tail lines expected
(constraint 11/E4). Gates → commit.

### T8 — USER listening gate (user + orchestrator)
§9.4 steps 7b–9 / DoD §14.8 + §14.10 blues slices: playground audition of the §14.10
checklist (shuffle locks at three tempo tiers — verify the slow tier renders 12/8 feel
under S21-2; boogie bass outlines the changes; turnarounds relaunch every chorus; stop
lands when drawn) + formal error-spotting pass over fresh seeds (≥1 cell per supported
mood), entries appended to `listening/log.jsonl`; every entry fixed (fix agent + gates +
re-calibrate if content changed) or filed. **Hard stop for user participation.** No corpus
capture until this passes (§8.1 bootstrap order).

### T9 — corpus extension + first capture → **commit 3** (orchestrator)
§9.4 step 10. `_CORPUS_PACKS` += `"blues"`; literals per constraint 15; unscoped
`uv run trackgen bless --approve` → 12 first-capture cells under `fixtures/goldens/blues/**`,
36 existing cells verified zero-divergence. **No generatorVersion bump** (first capture;
contingency 13 if an engine fix landed). Gates → dedicated bless commit (D11).

### T10 — whole-chunk 3-lens review + close-out (opus ×3 + fix agent)
Fresh opus reviewers over the whole chunk: (a) content correctness vs §5-as-amended
clause-by-clause + first-use verification; (b) contract/DoD compliance (§14.3/§14.8/§14.10
blues slices, honest ledger); (c) test quality/coverage (non-vacuous, discriminating,
golden-blind slots selection-locked; measure the blues blind set for the C-20/C-22 record).
Validation agents on findings; fix loop ≤2 cycles; gates. Close-out: PROGRESS.md
(statuses, session log row, fresh handoff for C8 fusion_jazz — including the corrected
C-03 record per S21-3), CAVEATS entries (the S21-2 dormancy caveat + C-03 impact note),
final commit.

---

## DoD ledger (closed out 2026-07-21; verdicts from T10 lens B, independently reproduced)

- [x] **§14.3 (blues): MET.** Full banks per §5-as-amended (55 pattern entries — drums 16 /
      bass 14 / comping 13 / pads 12 — + 8 timbre
      flavors; ≥2 ungated candidates/slot; 3/2 weights with the two documented pinned-weight
      exceptions); `bl_dr_2` + `bl_bs_3` + all §5.6 defining values byte-verbatim (lenses
      A+B independently); PT5/PT12/P6 + all loader rules proven enforced (break-a-copy);
      lint **0 errors / 0 warnings**, zero `expected-unreachable` markers (none needed —
      all rungs envelope-reachable; the S21-2 dormancy is caveat-recorded, C-23).
- [x] **§14.8 (blues slice): MET.** Formal §8.4 error-spotting pass, user-confirmed
      2026-07-21 (explicitly confirmed as a real listen): all 8 moods, zero entries →
      nothing to fix or file. Session-21 pass record appended to `listening/log.jsonl`.
- [x] **§14.10 (blues): MET.** energetic/aggressive/romantic × 2 lengths validate Layers
      1–2 clean (lens B re-ran); three tempo tiers reachable and confirmed by ear (the
      slow tier renders 12/8 under the S21-2 re-map); boogie bass outlines changes;
      turnarounds relaunch every chorus (both pool paths); stop lands when drawn (T6:
      303 firings / 1340 eligible boundaries).
- [x] **Corpus 48/60** (C-17 progresses; closes at C8). 12 first-capture cells, 36
      pre-existing cells zero-divergence + spot-verified byte-identical vs `7500f24`,
      no generatorVersion bump.
- **New caveats: C-23** (rung-1/2 dormancy re-map, S21-2), **C-24** (triplet fill vs W7,
  resolved with signed-off §5.4 amendment), **C-25** (hendrix auto-dormancy, S21-6).
- **Review: lens A CLEAN / lens B COMPLIANT / lens C PROVEN-WITH-GAPS** (gaps = the
  accepted C-20-class blind-entry validity + calibration-artifact zero regression
  coverage, both cross-pack latents → C9; **zero blockers/majors; no fix loop**).
