# Session 19 — Phase 8, Chunk 5: reference-pack refinement (shakedown, §7)

Orchestrated per `plans/PROMPT.md`. Implements PHASE_8 §7 + §9.4 (the authoring checklist run
on pop_rock and jazz as the workflow's shakedown) toward DoD §14.2. Consumes the C1–C4 tooling:
`generate_trace` (C1), the `quality/` validator suite (C2), `audition`/`lint`/`calibrate`/
`--explain` (C3), and `corpus`/`blessdiff`/`bless` (C4).

## Scoping ground truth (verified 2026-07-20, two read-only opus agents)

1. **Zero `# …`-abridged or absent bank entries remain in either pack.** Every entry PHASE_5 §7
   / PHASE_7 §8 sketches is fully authored; every bank's id set matches the design exactly
   (pop_rock 27 patterns, jazz 22 — C-20's 49). The PHASE_5 §13.1 / PHASE_7 §13.1 enumeration
   DoD was discharged by those phases. DoD §14.2's "all abridged entries enumerated" clause is
   satisfied by **verification + record**, not new typing.
2. **The binding remaining §14.2 work is "lint clean" including the warning tier**: 38
   variety-coverage warnings (pop_rock 23, jazz 15), the ONLY warning class firing. Each names a
   `(role, kind, rung)` slot with exactly 1 surviving candidate at the worst cell — always
   **mood='happy', tempo=106**. Clearing one warning = authoring a 2nd candidate that survives
   all selection gates at that cell (a tempo-gated-away candidate does not count). There is NO
   annotation mechanism for this class (`# expected-unreachable` silences only
   unreachable-content, file-wide), so warnings are cleared by real content only.
   - pop_rock warned slots (23): drums main r1/r3/r4 + intro + ending (main r2 already has 2);
     bass main r1–r4 + intro + ending; comping main r1–r4 + intro + ending; pads main r1–r4 +
     intro + ending.
   - jazz warned slots (15): drums main r1/r2/r4 + intro + ending (r3 has 2); comping main
     r1/r4 + intro + ending (r2/r3 have 2); pads main r1–r4 + intro + ending. Jazz bass is
     `mode: walking` — variety-exempt, never linted.
   - Fills (`pr_dr_f1/f2`, `jz_dr_f1`) are singletons but NOT surfaced by variety-coverage
     (fill selection is Phase-6-owned). No fill authoring is required this session.
3. **C-20 coverage classes** (binding on verification strategy): every rung-1 slot and every
   pads slot is **GOLDEN-BLIND** — the 24-cell corpus never selects them, so new content there
   gets NO bless regression. Blind slots must be verified by the C2 validator suite + the C3
   audition/`--explain` loop + listening. Rung-2/3/4 drums/bass/comping slots are
   GOLDEN-COVERED.
4. **Baseline is green**: 5983 passed / 1 skipped (~50 s), ruff check/format clean, mypy clean,
   `trackgen bless` → "24 cell(s), no divergence" (1.9 s). `_GENERATOR_VERSION = "0.1.0"`
   (`src/trackgen/pipeline/serialize.py:38`).
5. **Version-bump collateral** (from `bless.py`'s docstring, test-guarded): a bump breaks
   exactly 3 things outside `bless` — `tests/test_whole_document_goldens.py::
   test_fixture_reserializes_identically` (×2 packs) and the `"0.1.0"` literal at
   `tests/test_serialize.py:307`; fixed by regenerating the three
   `fixtures/*.milestone.trackdoc.json` (helper: `tests/_regen_milestone_fixtures.py`) and
   editing the literal. Procedure: edit → `bless --approve` (UNSCOPED — never `--pack` as the
   final approve) → regen fixtures → update literal → four gates → ONE bless commit.
6. **Calibrate ground truth**: `trackgen calibrate` runs clean on both packs and WRITES
   `styles/<pack>/calibration.yaml` as a side effect of running. pop_rock: zero tempo-band
   violations; stable per-track levels; density monotone with energy. **jazz: tempo-band
   violations in 7 of 11 moods** — observed floors melancholic 40.2 / calm 45.5 / dark 47.4 /
   dreamy 49.4 / nostalgic 51.4 / mysterious 52.0 / romantic 53.4 vs manifest floor 60.
   Each observed floor ≈ 0.65 × the mood's low tempo — exactly the Friberg–Sundberg ritard's
   `v_end = 0.65` — so the leading hypothesis is that calibrate counts ritard-tail tempo
   *events* against the band (a reporting-grain issue), not that jazz draws out-of-band tempos.
   **Unproven; T3 diagnoses before anything is changed.**
7. **C-19 lever confirmed**: `styles/pop_rock/forms.yaml` — `verse_chorus_bridge` and
   `verse_chorus` both `repeat.count: [2, 3]`, `chorus_first` fixed `[2, 2]`. Raising the two
   maxima to ~5 would lift the 104-bar ceiling toward 480 s. Decision item S19-3.
8. **L2-2 lever confirmed**: jazz comping `retarget.registerLow: 52`
   (`styles/jazz/patterns/comping.yaml:11`), yet crossings observe comping midi 49 — voicings
   land below the authored floor into the walking-bass range. Bass register is not pack-tunable
   (walker-owned). Warn-only; remedy is comping register/voicing-class data.

## Decisions ratified at the approval gate (S19-1 … S19-5)

> **All five ratified as recommended by the user at the approval gate, 2026-07-20.**

- **S19-1 — Scope of "enumerated":** already discharged; C5 records the verification and
  redefines its authoring surface as the 38 variety slots. (Recommended: yes.)
- **S19-2 — Pads slots (12 of 38 warnings):** author real 2nd pad candidates even though pads
  are dormant at `layersMax: 3` (keeps §9.2 untouched, no tooling deviation, future-proof).
  Alternative rejected: extending lint annotation to the variety class (a §9.2 design change
  needing sign-off, and it would rubber-stamp thin banks).
- **S19-3 — C-19 pop_rock 480 s:** accept ~6 min as pop_rock's genre-appropriate ceiling; do
  NOT raise `forms.yaml` repeat bounds; update C-19 to resolved-accepted + flag the §8.2 note.
  (An 8-minute pop_rock form is out of style; the smoke-matrix floor 340.0 already encodes the
  real ceiling.)
- **S19-4 — jazz tempo-band violations:** T3 diagnoses first (ritard-tail hypothesis). If it is
  calibrate's reporting grain, fix the report (tooling, non-design); if jazz genuinely draws
  out-of-band tempos, escalate to the user before touching manifest or interpreter data.
- **S19-5 — L2-2 jazz comping floor:** in scope for T2 as pack-data polish (raise/reconcile the
  comping register window so co-attack crossings clear); zero crossings is the target, not a
  gate.

## Out of scope

- The three new packs (C6–C8) and any §4–§6 content.
- Any change to the corpus matrix / mood triple (C-20's remedies are C9 decision material).
- CI substrate (C-18), fill authoring, `variant` machinery, 12/8 — all deferred per the docs.
- Engine code changes, except where T3's diagnosis lands in `tooling/calibrate.py` reporting.

## Blast radius (why T0 exists)

Adding a 2nd candidate to a slot changes the selection pool — and therefore possibly the
per-slot draw outcome and RNG stream consumption — in every render that reaches that slot.
Expected consequences: most of the 24 corpus cells diverge (the handoff predicts this — "C5 is
the golden corpus's first production re-bless"); the 2 whole-document milestone goldens change;
and an unknown set of pinned-value tests that drive the real packs (selection goldens pinning
§9.1 candidate counts, generator/transition/humanizer goldens pinning exact notes) break. T0
maps this empirically BEFORE authoring lands, so T1/T2's verification lists are exact, not
guessed.

## Task list (ordered; parallel only where file scopes are disjoint)

### T0 — Blast-radius map (opus, read-only + scratch experiment)

- **Files**: read-only across `tests/`, `src/trackgen/parts/selection.py`; scratch edits on a
  throwaway branch/worktree only, reverted.
- **Task**: determine empirically what breaks when a slot gains a 2nd candidate. Method: on a
  scratch worktree, append one minimal dummy pattern to one GOLDEN-COVERED pop_rock slot (e.g.
  drums main r3) and one GOLDEN-BLIND slot (e.g. pads main r2); run `uv run pytest -n auto`
  and `uv run trackgen bless`; record exactly which tests fail and which corpus cells diverge
  in each case. Also answer: does a singleton pool consume a draw (does adding a candidate
  shift the RNG stream even when the incumbent wins)? Deliver: the exact list of
  pinned-value tests T4's bless commits must update, and the §9.1-candidate-count tests whose
  printed-sample basis changes (golden-value arbitration rule 2 applies — flag any PHASE_5 §9.1
  doc samples that go stale for orchestrator/user sign-off, never tune).
- **Verify**: scratch tree fully reverted; report only.

### T3 — Jazz tempo-band diagnosis (opus; parallel with T0 — disjoint files)

- **Files**: read `src/trackgen/tooling/calibrate.py`, `src/trackgen/humanize/` (ritard),
  `styles/jazz/{manifest,interpreter}.yaml`; edit at most `tooling/calibrate.py` + its tests.
- **Task**: prove or refute the ritard-tail hypothesis (observed floors ≈ 0.65 × mood tempo
  low). Reproduce one violating render with `generate_trace`, inspect `tempo_events`, and
  attribute every sub-60 observation. If ALL violations are ritard tails: amend calibrate's
  tempo-band check to evaluate the base tempo (or report ritard tails separately, clearly
  labeled) — a C3-tooling reporting fix, with a discriminating test (a genuinely out-of-band
  base tempo must still violate). Explain why pop_rock reports clean (its floors don't
  cross 60 even scaled?) — the asymmetry must be understood, not assumed. If any violation is
  NOT a ritard tail: STOP, report to the orchestrator for user escalation (manifest/interpreter
  data is pinned PHASE_2 surface).
- **Verify**: four gates; calibrate on both packs re-run — jazz tempo section either clean or
  correctly attributing; report explains the pop/jazz asymmetry.

### T1 — pop_rock bank thickening (opus)

- **Files**: `styles/pop_rock/patterns/{drums,bass,comping,pads}.yaml` ONLY. Tests may be added
  under `tests/` but no pinned-value test updates here (they move in T4a).
- **Task**: author the 23 second candidates (drums main r1/r3/r4 + intro + ending; bass main
  r1–r4 + intro + ending; comping main r1–r4 + intro + ending; pads main r1–r4 + intro +
  ending), per PHASE_5 §5 conventions and the §6.1/§6.2/§6.4/§6.5 rung ladders (rhythm +
  degree roles only — ROADMAP invariant 2; no literal transposition). Each new candidate: same
  rung/kind/eligibility envelope as its sibling so it survives at happy/106; distinct musical
  content (a *variant*, not a copy — the lint warning exists to create reroll variety);
  weights per §5 conventions; ids follow the existing scheme (suggest `pr_dr_1b` style).
  Respect C-12 (keep any authored `crash.velocity` lo > 0) and grid purity (§3.1 one-grid rule).
- **Verify** (task-local; corpus/golden updates deferred to T4a): `uv run trackgen lint
  styles/pop_rock/` → 0 warnings; `load_pack` clean; C2 suite green on fresh renders across
  all 11 moods (`validate_pipeline == []`); `--explain` shows 2 surviving candidates at every
  formerly-warned slot at happy/106; new-slot draws exercised (a seed sweep that selects each
  new candidate at least once — GOLDEN-BLIND slots get their only mechanical coverage here).
  Expected-fail set from T0 acknowledged in the report, not "fixed" ad hoc.

### T2 — jazz bank thickening + L2-2 register reconcile (opus; parallel with T1 — disjoint)

- **Files**: `styles/jazz/patterns/{drums,comping,pads}.yaml` ONLY (+ new tests as in T1).
- **Task**: author the 15 second candidates (drums main r1/r2/r4 + intro + ending; comping
  main r1/r4 + intro + ending; pads main r1–r4 + intro + ending), per PHASE_5 §6/§7 jazz
  conventions (ride-led swing vocabulary; C-08 note — ride skip notes may sit below the §5.2
  band, that is the golden-anchored idiom). Plus S19-5: reconcile the comping register window
  (`retarget.registerLow: 52` vs observed voicing floor 49) so L2-2 co-attack crossings go to
  zero on the reference sweep — investigate WHY voicings land below the authored floor before
  moving the number (if the retarget/voicing pass legitimately emits below `registerLow`, that
  finding goes to the orchestrator — it may be an engine-behavior question, not data).
- **Verify**: `uv run trackgen lint styles/jazz/` → 0 warnings; C2 suite green across all 11
  moods; `pipeline_warnings` L2-2 crossings 0 across a ≥300-cell jazz sweep (was 42/915);
  `--explain` 2-candidate evidence as in T1; same expected-fail discipline.

### T4a — Re-bless cycle 1 (orchestrator, mechanical per `bless.py` docstring)

- **Files**: `src/trackgen/pipeline/serialize.py` (version), `fixtures/goldens/**`,
  `fixtures/*.milestone.trackdoc.json`, `tests/test_serialize.py:307`, plus the exact
  pinned-value test/fixture updates T0 mapped (each recomputed, never hand-tuned; any stale
  PHASE-doc printed sample amended only with user sign-off per arbitration rule 2).
- **Task**: bump `_GENERATOR_VERSION` 0.1.0 → 0.1.1; run `uv run trackgen bless` and READ the
  whole semantic-diff report (expect most of 24 cells; first divergent stage should be
  `selection`-adjacent/phrases, never plan/form/harmony — investigate any earlier divergence
  before approving); UNSCOPED `bless --approve`; regen the 3 milestone fixtures; update the
  version literal; apply T0's collateral updates; four gates green. Commit T1+T2+T4a as the
  bless commits (per-pack if separable given T0's map, else one).
- **Verify**: four gates; a follow-up `trackgen bless` reports no divergence; report excerpt
  archived in PROGRESS.
- **Note (C-20)**: rung-1/pads content will show NO corpus divergence — that is the blind spot,
  not evidence of inertness. T1/T2's seed-sweep tests are the mechanical coverage.

### T5 — USER LISTENING BLOCK (§9.4 steps 7–9; user + orchestrator)

1. **Full-grid audition** (step 7): `trackgen audition --play` per (mood × pack) across the
   supported grid, biased toward seeds that select the NEW candidates (from `--explain`) and
   the GOLDEN-BLIND slots — rung-1 sections, pads-audible cells if any, intro/ending.
2. **T1 level pass** (step 8 / PHASE_7 Q1 / §8.4): judge the summed reference-track balance;
   adjust pack mix data (never code); log the outcome.
3. **§8.4 error-spotting pass** (step 9): per supported mood on both packs, fixed checklist
   (wrong-pitch · groove stumble · dead/abrupt transition · register clash/mud · ending
   failure · "would I solo over this?"), every entry logged to `listening/log.jsonl` as
   `{params, seed, time-in-track, category, note}`; each entry fixed (fix agent) or filed.
4. Any content change here = pack-version bump under the normal bless workflow → **T4b
   re-bless cycle 2** (orchestrator, same procedure, 0.1.1 → 0.1.2) if and only if edits
   landed.

### T6 — Calibration capture + pack version stamp (orchestrator + small opus check)

- After content settles: `uv run trackgen calibrate styles/pop_rock/` and `styles/jazz/`;
  commit both first blessed `calibration.yaml` files (activating pack-specific L2 thresholds +
  L3 bands per §8.1's bootstrap — the batch is listening-blessed by T5, L3-unvalidated by
  construction, expected). Stamp each pack's manifest `version` (§9.4 step 10). Dispatch a
  small opus check that `load_calibration` reads both files and the L2 reader reconciliation
  holds (C3 machinery, first production artifacts).
- **Verify**: four gates (calibration.yaml committed must not break the suite); lint still
  0 warnings; `bless` no divergence.

### T7 — Whole-chunk review + close-out (3 fresh opus lenses + orchestrator)

- Lenses over the whole C5 diff: (a) musical/content quality + convention compliance of the
  38 new patterns against PHASE_5 §5–§7 (incl. invariant-2 discipline — degrees, not literal
  notes); (b) contract/DoD §14.2 with evidence per clause + caveat hygiene (C-19 update, any
  new caveats); (c) test quality — are the new seed-sweep tests discriminating (do they
  actually select the new candidates), no golden hand-tuning, collateral updates recomputed.
- Findings → validation agent → fix agent, max 2 cycles, then escalate.
- DoD §14.2 checklist with evidence; PROGRESS/CAVEATS/handoff updates; final gates; commit.

## DoD §14.2 mapping

| Clause | Where proven |
| --- | --- |
| all abridged PHASE_5/PHASE_7 entries enumerated | T0-adjacent verification record (already discharged by Phases 5/7; this session re-verified: zero markers, id sets match §7/§8) |
| lint clean | T1/T2 (0 errors, 0 warnings both packs) re-checked at T6/T7 |
| calibrated (T1 executed) | T5.2 log + T6 artifacts |
| goldens + `calibration.yaml` captured | T4a/(T4b) bless commits + T6 |

## Session risks

- The blast radius (T0) may be larger than the milestone+literal set — budget T4a accordingly;
  if the pinned-sample fallout implicates PHASE-doc §9 printed values, that is arbitration
  rule 2 territory (user sign-off, doc amended with the recomputed fixture, never code tuned).
- T3 may refute the ritard hypothesis → user escalation, and T6's jazz calibrate capture
  blocks on the resolution.
- 38 patterns is real authoring volume; if either T1 or T2 balloons, the seam is per-pack
  (T1+T4a-pop first, jazz next session) — flag before overrunning, per PROMPT escalation.
