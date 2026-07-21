# SESSION_20 — Phase 8, Chunk 6: `chill_lofi` (the first new pack)

**Scope:** author `styles/chill_lofi/` in full per `plans/PHASE_8.md` §4 and the §9.4 checklist;
land it atomically with its tests; verify the five dormant-machinery first-uses; calibrate;
run the formal §8.4 listening pass (creating `listening/log.jsonl`); extend the golden corpus
to 36 cells (first capture); whole-chunk review + close-out. DoD targets: **§14.3 (lofi)**,
**§14.8 (lofi slice: error-spotting pass)**, **§14.10 (lofi listening checklist)**.

**Explicitly out of scope:** `tests/test_smoke_matrix.py` extension (five-pack surface, C9 per
DoD §14.9); the reference-pack formal listening item left OPEN by C5 (carried to C9); blues /
fusion_jazz (C7/C8); any engine change not forced by a verified chill_lofi first-use bug.

**Environment:** `uv` / Python 3.12. Four gates: `uv run pytest -n auto` · `uv run ruff check .`
· `uv run ruff format --check .` · `uv run mypy`. Baseline (orchestrator-verified 2026-07-20):
**6052 passed / 1 skipped**, all gates green. `_GENERATOR_VERSION` 0.1.3
(`src/trackgen/pipeline/serialize.py:38`). Never `git push`.

---

## Binding constraints (from scoping, 2 opus agents, 2026-07-20)

1. **Atomic landing.** `loader.registered_styles()` discovers any `styles/*/manifest.yaml`.
   The instant the manifest exists, `tests/test_interpreter_pack.py:114`
   (`registered_styles() == {"pop_rock","jazz"}`) fails and `tests/test_interpreter.py:301-303`
   (dynamic pack×mood matrix) calls `resolve_pack("chill_lofi")` — a partial pack raises
   `PackLoadError`. Therefore T1–T5 work stays uncommitted until the whole pack + test updates
   are green; **commit 1 is the complete pack**.
2. **Mode ordering (decision S20-1).** `MODE_LADDER = (major, mixolydian, dorian, minor,
   phrygian)` (`src/trackgen/interpreter/moods.py:36`); interpreter Rule 3 requires the pack's
   `modes` to be a ladder-ordered subsequence. PHASE_8 §4.1's printed `modes: [minor, dorian,
   major]` cannot load. Author `modes: [major, dorian, minor]` (same set, same semantics — mode
   selection is ladder-distance-based, list order is validation-only) and amend §4.1 per
   arbitration rule 2, **after user sign-off**.
3. **Variety lint has no escape** (`packs/lint.py::_warn_variety_coverage`): every role needs
   **≥2 candidates surviving all gates at every supported (mood, tempo)** for each slot in
   {main rung 1, 2, 3, 4, intro, ending} — rung 4 included, even though it is unreachable
   (energy ceiling 0.60 → max rung 3). Fills are not variety-checked (PT12 needs ≥1 ungated
   drum fill). Co-author sibling pairs with the 3/2 weight convention (C5 handoff item 3).
4. **Unreachable-content marker:** a comment containing `expected-unreachable` anywhere in a
   `patterns/<role>.yaml` silences that file's unreachable-content warnings
   (`packs/lint.py:88,445-454`). Rung-4 mains are unreachable for **all four roles** → the
   marker goes in all four pattern files. DoD §14.3 requires no *unannotated* warnings.
5. **PT5/PT12 completeness (patterns-mode pack):** per role in {drums, bass, comping, pads}:
   ungated main at rungs 1–4 + ungated intro + ungated ending; drums additionally ≥1 ungated
   fill. Comping/pads need a `voicing:` block (classes covering rungs 1–4) + bank `retarget`;
   bass needs `mode: patterns`; drums file carries `layeringOrder: [drums, bass, comping, pads]`.
6. **TB1 cross-file:** `timbres.yaml` flavor ids per role must exactly equal `interpreter.yaml`
   `flavors` — all **8** flavors need full recipes (`dusty_kit`, `boombap_kit`, `warm_sub`,
   `round_pick`, `ep_mellow`, `piano_felt`, `tape_strings`, `warm_wash`), not just the 4 §4.6
   defining entries. Master chain must end with `Limiter` (TB4). `Vibrato: [frequency, depth,
   wet]`, `StereoWidener: [width]`, `Distortion`, `Chorus`, `Compressor`, `Limiter` are all
   allowlisted (`sound/allowlist.yaml`).
7. **P7 open-ending:** the single `loop` harmonyTag serves `intro`, so every `loop` pool entry's
   final chord must NOT be degree-1-rooted. The §4.3 pins are pre-rotated compliant — author
   them verbatim; do not "fix" the rotations.
8. **C-21:** comping/pads register control for `degree: chord` events is the arrangement lane
   (`arrangement/lanes.yaml`: comping [48,71], pads [43,71], bias-shifted), NOT the pattern
   `retarget` window. §4.4's retarget windows (bass {28,45}, comping {50,69}, pads {45,64}) are
   the pattern-fold windows only; all satisfy PT9 span ≥12.
9. **C-12 verified safe:** crash velocity lo 0.30 > 0 and chill_lofi's reachable energy floor is
   0.25 (envelope min) — no zero-velocity crash path.
10. **Corpus (T9, after listening per §8.1 bootstrap order):** extreme pair = (happy,
    melancholic), default nostalgic does not collide → `corpus_moods` will not raise; triple =
    **(nostalgic, happy, melancholic)**, 12 new cells, corpus 24 → 36. First capture ⇒ **no
    generatorVersion bump** unless an engine code change lands first (contingency below).
11. **First-use machinery (highest bug risk, verified nowhere end-to-end today):** (a) `dropout`
    device on breakdown entry + the arrangement 2-layer breakdown cap (`arrangement/arrange.py`
    ~:112); (b) `close: fade` (HOLD alias) from a real pack; (c) `feelTable: laidback`;
    (d) `swing16` + pack `swingRatio: 0.57` override; (e) one `loop` tag serving all section
    types. T5's tests and T6's grid pass must each exercise these explicitly.
12. **Contingency — engine fix forced by a first-use bug:** any engine change that alters
    pop_rock/jazz output triggers the full bless collateral (generatorVersion bump per
    `bless.py` docstring; `tests/test_serialize.py:307` + `tests/test_milestone_fixture.py:43`
    literals; milestone fixtures regen via `tests/_regen_milestone_fixtures.py` + hand-stamp
    `fixtures/milestone.trackdoc.json`). Escalate to the user before applying any such fix.

---

## Decision items — USER APPROVAL GATE

- **S20-1 (arbitration rule 2):** amend PHASE_8 §4.1's `modes: [minor, dorian, major]` →
  `[major, dorian, minor]` (loader Rule 3 ladder order; set/semantics unchanged). The amendment
  commit annotates the doc. **Recommended: approve.**
- **S20-2 (listening formality):** run the **formal** §8.4 error-spotting pass for chill_lofi
  this session — fixed checklist, entries logged to a new `listening/log.jsonl`
  (`{params, seed, time-in-track, category, note}`), every entry fixed or filed — plus the
  §14.10 lofi playground checklist (laid-back swung groove; dropout sections audibly strip;
  fade-close rings out; nothing exuberant). This is the DoD §14.8 lofi slice; C5's informal
  precedent left a debt we should not repeat on a *new* pack. The C5 reference-pack listening
  item stays OPEN → C9. **Recommended: formal pass now, reference-pack item to C9.**
- **S20-3 (smoke matrix):** leave `tests/test_smoke_matrix.py` at 2 packs; extending it is the
  DoD §14.9 five-pack surface pinned to C9 (would also require new per-pack ceiling floors).
  **Recommended: defer to C9.**
- **S20-4 (pack version):** manifest lands at `version: 0.1.0` per §4.1; the §9.4 step-10
  "stamp version" is satisfied by 0.1.0 for a first release (no bump-from-anything).
  **Recommended: 0.1.0.**

---

## Task list (all subagents opus; parallel only on disjoint files)

### T1 — config quintet (opus)
**Files:** `styles/chill_lofi/manifest.yaml`, `interpreter.yaml`, `forms.yaml`,
`progressions.yaml`, `transitions.yaml`.
Author verbatim from PHASE_8 §4.1–§4.3 + §4.5, with exactly one deviation: `modes: [major,
dorian, minor]` (S20-1). `feelTable: laidback`, `feel: swing16`, `swingRatio: 0.57`,
`close: fade`, `stop: {enabled: false}`, `turnarounds: []` are all schema-valid (verified in
scoping). **Verification (no full load possible yet):** scratch script model-validating each
file (`Manifest`, `InterpreterConfig`, `FormsConfig`, `ProgressionsConfig`, `TransitionsSpec`
from `trackgen.packs.models`), plus explicit checks: R3 mode order, P6 per-mode unconditional
coverage (loop pool + finals over major/dorian/minor), P7 open-endings on all 5 loop entries,
F13, TR2/TR3. Report: files written, checks run, any §4 text ambiguity found (escalate, don't
resolve).
**No commit** (constraint 1). Review: opus, diff-scoped.

### T2 — drums + bass banks (opus, parallel with T3/T4)
**Files:** `styles/chill_lofi/patterns/drums.yaml`, `patterns/bass.yaml`.
Per §4.4 conventions: drums rung 1 half-time / rung 2 boom-bap (defining entry **`lf_dr_2`
verbatim** from §4.4, weight 3; co-author its sibling at weight 2) / rung 3 +16th hats +
`perc` shaker (minDensity-gated) / rung 4 marginally-fuller rung-3 variant; 2 quiet snare-roll
fills; thinned intro/ending entries. Bass `mode: patterns`, retarget `{28, 45, retrigger}`:
rung 1 whole-note roots / rung 2 root+fifth halves / rung 3 sparse syncopated root 8ths + one
octave lift / rung 4 +gated ghost 16th. **Every (kind, rung) slot × 2 candidates** (constraint
3), ungated where PT5 requires; velocities ≤ ~0.85; straight/16th grid only (grid-mixing lint);
`layeringOrder` once in drums.yaml; `# expected-unreachable` marker in both files. Id
convention `lf_dr_*` / `lf_bs_*` (`b`-suffix siblings; intro `i/ib`, ending `e/eb`, fills
`f1/f2`). Pad ladders monotone rule applies to any b-variant (C5 T7 lesson: siblings must not
invert the rung's density ordering).
**Verification:** scratch model-validation (`DrumsBank`, `BassBank`), PT1/PT2/PT3/PT5/PT9/PT12
checks, velocity/grid sweeps. No commit. Review: opus.

### T3 — comping + pads banks (opus, parallel with T2/T4)
**Files:** `styles/chill_lofi/patterns/comping.yaml`, `patterns/pads.yaml`.
Comping per §4.4: rungs 1–2 sustained whole/half `chord` hits, rung 3 offbeat-stab variant
with an and-of-4 `push`, rung 4 completeness variant; voicing classes `{1: [shell3,
triad_close], 2: [rootless_a, rootless_b], 3: [rootless_a, rootless_b], 4: [rootless_a,
rootless_b]}`; retarget `{50, 69, retrigger}`. Pads: `{1–4: [fifths]}`, whole notes, low
velocity, retarget `{45, 64, retrigger}`; **pad ladders monotone across rungs** (C5 T7).
2 candidates per slot incl. intro/ending; `# expected-unreachable` markers; `lf_cp_*` /
`lf_pd_*` ids. Remember C-21: do NOT try to enforce a register floor via `retarget` — lanes
own chord-voicing registers.
**Verification:** scratch model-validation (`VoicedBank`), PT5/PT7/PT9 checks. No commit.
Review: opus.

### T4 — timbres (opus, parallel with T2/T3)
**File:** `styles/chill_lofi/timbres.yaml`.
All **8** flavors (constraint 6): the four §4.6 defining entries verbatim (dusty_kit warm_sub
ep_mellow tape_strings, incl. per-flavor `mod` overrides: snare `noise.playbackRate` 0.8–2.0,
hats `resonance` 1500–3500, ep `modulationIndex` 2–8) + four §4.1-declared siblings authored
in-idiom (`boombap_kit` punchier kick/brighter snare than dusty; `round_pick` MonoSynth
triangle/lowpassed pick bass; `piano_felt` soft felt-piano FM/subtractive; `warm_wash` softer
non-widened pad). Bus `reverb {decay: [1.2, 3.5], preDelay: [0.02, 0.04], returnFilterHz:
300}`; master `[Compressor {threshold: -18, ratio: 3, attack: 0.02, release: 0.3}, Limiter
{threshold: -1}]`. TB1–TB9 compliant (TB7 base-XOR-mod for every mapped param; NoiseSynth
voices omit `midi` per TB5; kit voices otherwise carry `midi`).
**Verification:** scratch `TimbresConfig.model_validate` + allowlist dry-run over every
emitted path (mirror `tests/test_timbres_*` patterns). No commit. Review: opus.

### T5 — integration + chill_lofi test suite → **commit 1** (opus)
**Files:** `tests/test_interpreter_pack.py` (line 114 set + any 2-pack literals),
new `tests/test_chill_lofi_pack.py` (+ split files if size warrants; disjoint from reference
tests).
1. First full `resolve_pack("chill_lofi")` + `trackgen lint styles/chill_lofi/` → drive to
   **0 errors / 0 unannotated warnings** (fix loop with T2/T3/T4 scopes as needed — same
   session, bounded).
2. Author tests: bank-inventory pins (candidate counts per slot, C5 M1 convention);
   **`lf_dr_2` verbatim golden** (the §4.4 anchor); variety/selection tests per the C5
   convention (each golden-blind candidate gets a locked seed under which it wins the
   production draw — see `tests/test_pop_rock_variety.py` for the pattern); **first-use
   machinery pins** (constraint 11): breakdown section renders with ≤2 layers and a dropout
   entry; `close: fade` produces the HOLD ending shape with no ritard tempo events; humanizer
   output shows laidback offsets (e.g. comping +12 ms class shift vs straight); plan carries
   `swing {ratio: 0.57, subdivision: "16"}`; one progression draw serves all sections (loop
   tag identity); plus an end-to-end property slice: default params + the two (V,A) extremes
   × 2 lengths × ≥5 seeds → serialize, `validate_document == []`, `validate_pipeline == []`
   (Layer 1 + L2 at engine defaults per §8.1 bootstrap).
3. Four gates green → **commit 1** (pack + tests + literal updates, one commit).
Review: opus, whole-T1–T5 diff (this is the chunk's biggest review; verify content against §4
clause-by-clause, tests non-vacuous).

### T6 — full-grid audition + first-use verification pass (opus, report-only)
§9.4 step 7. Render the whole supported grid — 8 moods × both templates (force via seeds
as needed) × 2+ seeds, plus `--explain` on a sample — through `generate_trace`; run
`validate_pipeline` + `pipeline_warnings` on every render; specifically confirm each
constraint-11 first-use behaves musically (dropout actually strips audibly in note terms;
fade ending rings; laidback offsets present in stage-7 output; swing16 positions at 0.57;
lane/voicing registers ≤ 71). Report anomalies with evidence; substantive findings → fix
agents (bounded, 2 cycles), gates re-run; content fixes fold into the pack (pre-calibration,
so no bless churn).

### T7 — calibrate → **commit 2** (orchestrator + opus artifact check)
§9.4 step 8. `uv run trackgen calibrate styles/chill_lofi/` → `styles/chill_lofi/
calibration.yaml` (first batch: L2 thresholds = engine defaults by design, §8.1 bootstrap;
L3 bands zero-width on deterministic metrics — known-latent, C5 precedent). Independent opus
artifact check (C5 T6's five checks: shape, L2-reader activation, band sanity, mood coverage
8/8, byte-identical re-run). Tempo-band section reads steady tempo (82679f8); `close: fade`
should produce no ritard tail lines. Gates → commit.

### T8 — USER listening gate (user + orchestrator)
§9.4 steps 7b–9 / DoD §14.8+§14.10 lofi slices (per S20-2): playground audition of the
§14.10 lofi checklist + formal error-spotting pass over fresh seeds (per supported mood at
minimum one cell), entries logged to **new `listening/log.jsonl`**; every entry fixed (fix
agent + gates + re-calibrate if content changed) or filed (PROGRESS/CAVEATS as appropriate).
**Hard stop for user participation.** No corpus capture until this passes (§8.1 bootstrap
order).

### T9 — corpus extension + first capture → **commit 3** (orchestrator)
§9.4 step 10. Extend `src/trackgen/tooling/corpus.py:105` `_CORPUS_PACKS` += `"chill_lofi"`;
update literals: `tests/test_corpus.py` (`:169-172` pinned-triples + `_PACKS` + `:219,222,237`
counts 24→36), `tests/test_bless.py` (`:763` scoped-run string, `:893-895`, `:913` counts).
`uv run trackgen bless --approve` (unscoped) → 12 first-capture cells under
`fixtures/goldens/chill_lofi/**` (~8–9 MB expected), 24 reference cells verified no-divergence.
**No generatorVersion bump** (first capture; contingency 12 if an engine fix landed). Gates →
dedicated bless commit (D11).

### T10 — whole-chunk 3-lens review + close-out (opus ×3 + fix agent)
Fresh opus reviewers over the whole chunk: (a) content correctness vs §4 clause-by-clause +
first-use machinery; (b) contract/DoD compliance (§14.3/§14.8/§14.10 lofi slices, honest
ledger); (c) test quality/coverage (non-vacuous, discriminating, golden-blind slots covered
by selection locks). Validation agents on findings; fix loop ≤2 cycles; gates. Close-out:
PROGRESS.md (statuses, session log row, fresh handoff for C7 blues), CAVEATS entries for any
deviation, final commit.

---

## DoD ledger (closed out 2026-07-21; verdicts from T10 lens B, independently reproduced)

- [x] **§14.3 (lofi): MET.** Full banks per §4 conventions (52 entries, 2 candidates/slot, 3/2
      weights); `lf_dr_2` + all 4 defining timbres byte-verbatim (lens A); PT5/PT12/P6 + all
      loader rules enforced at load; lint **0 errors / 0 warnings** (the one warning-class hit,
      rung-4 unreachable, is annotated via `expected-unreachable` markers).
- [x] **§14.8 (lofi slice): MET.** Formal §8.4 error-spotting pass, user-confirmed 2026-07-21:
      all 8 moods, zero entries → nothing to fix or file. `listening/log.jsonl` created with
      the structured pass record (the evidence collector now exists).
- [x] **§14.10 (lofi): MET.** nostalgic/happy/melancholic × 2 lengths × 5 seeds validate
      Layers 1–2 clean (30 cells, in-suite); §14.10 checklist confirmed by ear (laid-back
      groove, breakdown strips, fade rings, nothing exuberant). Note: "dropout sections
      audibly strip" is delivered by the arrangement 2-layer cap; the dropout *device* is a
      structural no-op on bar-quantized banks (T5/T6, honest).
- [x] **Corpus 36/60** (C-17 progresses; closes at C8). 12 first-capture cells, 24 reference
      cells zero-divergence, no generatorVersion bump.
- **New caveat: C-22** (rung 3/pads dormancy, accepted S20-5, + blind-set postscript 34/50).
- **Review: lens A CLEAN / lens B COMPLIANT / lens C PROVEN-WITH-GAPS** (gaps = the accepted
  C-20/C-22 class; zero blockers/majors; only inline doc-hygiene fixes).
