# Implementation Progress

Source of truth for implementation state across sessions. The orchestrator (see `PROMPT.md`) updates this file **immediately** at every task completion and step transition — never batched to session end. A new session must be able to resume losslessly from this file plus git log.

Statuses: `not started` · `planning` · `in progress` · `blocked` · `done`

## Handoff — next session starts here

> **Next:** Phase 4 (Harmony engine), fresh phase. Phase 3 is **complete** (session 03, all 8 DoD items proven). No chunk plans exist yet. A **post-Phase-3 code review** (2026-07-15) of Phases 1–3 landed a review-fix batch (349 tests, all four gates green): C-02 resolved (ladder kept + white-box tested + PHASE_3 §7.3 doc note); V2 validator now catches backwards/zero-length sections; pack `swingRatio` bounds moved to load-time; determinism hardening (`from_base36` canonical-only + TID251 bans on `secrets`/`uuid`/extra `datetime` clocks). No open items block Phase 4.
> **Phase 4 builds on (now-pinned) Phase 3 contracts:** the Form generator `form(plan, forms) -> SongForm` (`src/trackgen/form/stage.py`) emits a complete `SongForm` — `sections[{id, type, index, total_of_type, start_bar, length_bars, energy, phrases:[{label,bars}], harmony_tag, variant, ending}]`, `total_bars`, `template_id`. Phase 4 (Harmony engine) consumes `SongForm` → produces `HarmonicPlan` (pinned core already in `schema/ir.py`: `ChordEvent`/`ChordSpec`). **Key hooks:** `harmony_tag` is the key into the pack's Phase-4 progression pools (PHASE_3 §4.1); same phrase `label` ⇒ same harmonic material; the §3.2 semantics table (PHASE_3) documents the cadence tendencies Phase 4 must implement (verses open on V, choruses close on I, deceptive before repeated final chorus); `ending.tag_bars` marks where Phase 4 places the tag cadence; `SongForm` carries **no cadence field** by design (D8 — Phase 4 owns all cadence logic). Read `PHASE_4.md` in full + PHASE_3 §3.2 (semantics table) + §4 (SongForm fields).
> **Pack `progressions.yaml` schema is owned by Phase 4** (PHASE_1 §6 layout; not yet created — `load_pack` treats it as absent today, mirror the optional `forms.yaml`/`interpreter.yaml` pattern). The deferred cross-file check lands here: every `SongForm.harmony_tag` (and every `forms.yaml` `harmonyTag`) must be served by a pool in `progressions.yaml` — wire this into Phase 4's loader (PHASE_2 D14 pattern). Reference packs `styles/{pop_rock,jazz}/` now have `manifest.yaml` + `interpreter.yaml` + `forms.yaml` + empty pattern banks; they will need `progressions.yaml` in Phase 4.
> **Phase 4 also owns the shared theory library** (chord symbol → pitches, voicing candidates, integer-cost Viterbi voice-leading) used by Phase 5 part generators (ROADMAP §4, PHASE_4 §? — read the doc). `src/trackgen/theory/` exists as an empty package.
> **Carry-forward for later phases (unchanged from Phase 2):** Phase 5 Serializer must dump documents with `exclude_none=True`; pack models enforce `extra="forbid"` (new fields must be added explicitly); env `uv` manages Python 3.12.13, all four gates green.
> **Orchestrator golden pre-verification method (reuse in Phase 4):** before the plan gate, independently reproduce every load-bearing printed sample (the seed `1ps9wxb` chains PHASE_2 §6.5 → PHASE_3 §7.4 → **PHASE_4 §10** → …). In Phase 3 all samples reproduced exactly with no amendment. The pinned `weighted_choice(items=["include","exclude"], weights=[incW,excW])` ordering (SESSION_03 D-S2) reproduced the form draws.
> **Phase 3 builds on (now-pinned) Phase 2 contracts:** the Interpreter emits a complete `GenerationPlan` (`src/trackgen/interpreter/stage.py::interpret` / `generate_plan`) with `mood_vector` (raw anchor V/A), `budgets` (incl. `layers_max`, `harmonic_rhythm_base`, `register_bias`), `timbre_directives`, resolved `key`/`tempo_bpm`/`swing`/`time_signature`/`max_length_ticks`/`role_flavors`. Phase 3 (Form generator) consumes `GenerationPlan` → produces `SongForm` (pinned core already in `schema/ir.py`). Read `PHASE_3.md` in full + `PHASE_2.md` §7 (budget semantics: `moodVector.arousal` drives section energy; `layersMax` caps layering) + PHASE_1 §4.2 (`SongForm`). Pack `forms.yaml` schema is owned by Phase 3 (PHASE_1 §6 layout; not yet created — `load_pack` treats it as absent today, mirror the optional `interpreter.yaml` pattern D-S1 if extending the loader).
> **Reference packs:** `styles/pop_rock/` and `styles/jazz/` exist with `manifest.yaml` + `interpreter.yaml` + empty pattern banks; they will need `forms.yaml` added in Phase 3.
> **New this session — read before extending:** [C-01](CAVEATS.md) — `generate_plan` emits a 15th structural error code `PARAM_MALFORMED` (beyond the §3.1 semantic catalog) for malformed field types; a future client-contract layer must enumerate it.
> **Phase 2 builds on (now-pinned) Phase 1 contracts:** `GenerationPlan` pinned core + its extension points `moodVector`/`budgets`/`timbreDirectives` (Phase 2 owns these — add them inside `src/trackgen/schema/ir.py`'s `GenerationPlan` without touching pinned fields); `meta.params` opaque dict becomes Phase 2's parameter schema; stream registry already includes `interpreter`. Read `PHASE_2.md` in full + `PHASE_1.md` §4.1.
> **Carry-forward notes for later phases:**
>  - **Phase 5 serializer:** document models' `model_dump` currently emits `null` for absent `midi`/`voice`/`maxPolyphony`; §3.5/§3.6 require these ABSENT. The Phase 5 Serializer must dump with `exclude_none=True` (or per-field exclusion) so emitted `TrackDocument` JSON matches the contract. (Latent now — no document serializer ships in Phase 1; the hand fixture has no nulls.)
>  - **Pack models enforce `extra="forbid"`:** later phases adding envelope/event fields (e.g. Phase 5's `push`/`minDensity`, `sixth`/`chord` degrees) must add them to the pydantic models in `packs/models.py` explicitly — unknown YAML keys are rejected by design.
>  - **Env:** `uv` at `C:\Users\Dominic\scoop\shims` (not on PATH — prepend it); `uv` manages Python 3.12.13. All four gates green.

*(The orchestrator rewrites this block at every close-out — and mid-session on any pause — stating: current phase/chunk, last completed task + commit, and the exact next action.)*

## Phase status

| Phase | Scope | Status | Sessions | Notes |
| --- | --- | --- | --- | --- |
| 1 | Foundations & contracts | done¹ | 01 | ¹Code/automated DoD complete; §9.6 manual listening check awaits user audition of the playground |
| 2 | Parameter & mood model | done | 02 | All 8 DoD items proven; 245 tests green. Caveat C-01 (PARAM_MALFORMED) |
| 3 | Form & structure | done | 03 | All 8 DoD items proven; 339 tests green at 0122149. Caveat C-02 (ladder unreachable) resolved in post-review fix batch (349 tests) |
| 4 | Harmony engine | planning | — | Split into 2 chunks (SESSION_04 theory+dressing+loader; SESSION_05 stage+goldens). Includes shared theory library used by Phase 5 |
| 5 | Rhythm-section part generators | not started | — | Expect ~4 chunks: loaders/foundations → arrangement → generators/walker/voicing → orchestrator+Serializer+milestone |
| 6 | Transitions, variation & humanization | not started | — | |
| 7 | Sound design | not started | — | |
| 8 | Quality, evaluation & pack expansion | not started | — | Multi-session, hard order: tooling → reference-pack refinement → chill_lofi → blues → fusion_jazz. Calibration bootstrap order per PHASE_8 §8.1 |

## Session log

One row per implementation session, appended at close-out. Session plan files live in `plans/sessions/SESSION_NN.md`.

| Session | Date | Phase / chunk | Outcome | Key commits |
| --- | --- | --- | --- | --- |
| 01 | 2026-07-14 | Phase 1 (all) | All 6 tasks built, reviewed, gates green (125 tests). DoD §9.1–§9.5 + §9.7 proven; §9.6 manual audition pending user. No CAVEATS (all §5.6 goldens reproduced exactly; no doc amendments). | e0643ee seeds · 5d32e8c schema · 41e3af8 packs · 7fc3a5f validator+export · 6fbaa7c fixture · cf2b490 playground · e27f704 review-fixes |
| 02 | 2026-07-15 | Phase 2 (all) | 6 tasks built, per-task + 4-lens whole-session review, gates green (245 tests). All §11 DoD 1–8 proven; both §6.5 goldens reproduce field-for-field; orchestrator pre-verified every load-bearing sample. Contract lens COMPLIANT. Review fixes: malformed-type wrapping (C-01), pack-tonic validation, mode-ladder dedupe, 3 test-coverage gaps closed. | 74e57b5 plan-fields · 2ab6997 moods · 8fe953f packs+refs · 2c0c602 params · 26f39a0 interpreter · eb00804 review-fixes |
| 03 | 2026-07-15 | Phase 3 (all) | 5 tasks (T1–T3 parallel, T4 opus integration, T5 docs). Per-task + deep-T4 + 2-lens whole-session review; both whole-session lenses "contract-clean, all DoD PROVEN". Gates green (339 tests). Orchestrator pre-verified every §7.4 sample (seed vectors, 13 energy cells, both fitting totals, full 8-draw/1-draw sequences) — no doc amendment. Review fixes: F8/F9/eligibility completeness (T2), energy-order discriminators (T3), fallback tag_bars clamp + property rigor (T4), F4 fixture + variant assert (0122149). Caveat C-02: ladder proven unreachable, §11.7 via substitute coverage. | 474c273 schema · 2d4f5a9 forms-loader · 66725bf energy · 5c47b75 form-stage · 0122149 review-fixes |

## Phase detail

When a phase enters `planning`, the orchestrator adds a `### Phase N` section here containing: the approved chunk plan (if split), the task checklist with per-task status and commit hashes, DoD checklist with evidence as items are proven, and links to relevant CAVEATS entries. Keep entries terse — evidence pointers, not narrative.

### Phase 4 — Harmony engine (chunk plan)

**Split into 2 chunks** (phase too large for one session; seam = "pieces vs. assembly"):

- **Chunk 1 — SESSION_04** (`plans/sessions/SESSION_04.md`): theory library + dressing ladder + `progressions.yaml` loader/reference packs. **Proves DoD 1, 2, 3, 8.** Tasks (all opus): T1 theory resolution core (`theory/chords.py`) → then parallel T2 voicing/VL (`theory/voicing.py`), T3 dressing ladder (`harmony/dressing.*`), T4 progressions schema+loader+reference packs (`packs/*` + `styles/*`).
- **Chunk 2 — SESSION_05** (plan TBD): `HarmonicPlan` §7 schema extension (`schema/ir.py`) + harmony stage (`harmony/stage.py`) §5.1 + 3 boundary transforms + §10 golden chains (76+64 events) + §5.6 seed goldens + determinism (8/30 draws) + property matrix + deceptive fixture + §13 amendments. **Proves DoD 4, 5, 6, 7, 9, 10.**

Golden anchor pre-verified: `derive(3735928559,"harmony")==226146634901021418`; §5.6 getrandbits/randrange vectors match exactly.

#### Phase 4 — Chunk 1 — session 04 (`plans/sessions/SESSION_04.md`)

**Awaiting approval — no task dispatched.** Task list:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Theory resolution core (`theory/chords.py`): §8.1/§8.2 tables, `resolve_token` (§3.1/§3.2/§3.3), §7.4 scale-hint, chord/guide tones, §6.4 helper; music21 cross-val | opus | done | 21ce323 |
| T2 | Voicing & voice-leading (`theory/voicing.py`): §8.4 candidates incl. `fifths`, §8.5 `vl_distance`, §8.6 Viterbi | opus | done | 6cc5907 |
| T3 | Dressing ladder (`harmony/dressing.yaml`+`.py`): §6.1 tiers, §6.2 offsets, §6.3 tables, §6.4 filter | opus | done | ee7ddb6 |
| T4 | `progressions.yaml` schema (`packs/models.py`) + loader P1–P10/density (`packs/loader.py`) + `styles/{pop_rock,jazz}/progressions.yaml` (§9.1/§9.2) | opus | done | bb7114e |

Per-task reviews (opus, T2/T3/T4 parallel): **T3 APPROVE**; **T2 APPROVE-WITH-NITS** (reviewer hand-re-derived the ii–V–I Viterbi DP → asserted path genuinely optimal; tie-break + drift proof real); **T4 APPROVE-WITH-NITS** (all P1–P10 reject correctly; reference packs verbatim; C-03 confirmed honest & scoped). No blockers/majors. **C-03 user-signed-off: Option A** (widen P8 to admit the SubV `bII7`; keep code; C-03 open, PHASE_4 §4.3 reword deferred). New caveat **C-04** (T2 voicing API: keyless `voicing_candidates` → perfect-4th quartal reading; additive `anchor` kw on `optimal_voicing_path`; deferred to PHASE_5 §13.6). Accepted nits (DoD met, tests can't pass for wrong reason — carried to Chunk-2/Phase-5 handoff, not fixed): T2 rootless/drop2 triad-cardinality degradation (Phase 5 class-per-role policy); T4 `_relaunches_as_dominant` keys on pc 1 (admits `#I7` enharmonic — harmless); T4 `final_chord_token` last-declared-label (v1 single-label pools only); a few T4 rejection tests omit `match=`.

T1 review: opus APPROVE-WITH-NITS (every §8.1/§8.2/§6.4/§3.2/§3.3/§7.4 table verified cell-by-cell; music21 cross-val real). One nit fixed: sus suffixes now require the shown (upper) numeral case per §3.1 (`21ce323`). T1 public surface: `resolve_token`, `chord_function`, `chord_scale`→`ScaleHint`, `legal_extensions`/`extensions_legal`, `chord_symbol` (re-derive after dressing), `chord_intervals`/`chord_tones`/`guide_tones`→`GuideTones`/`scale_pcs`; consts `QUALITY_INTERVALS`/`EXTENSION_OFFSETS`/`SCALE_INTERVALS`; types `Function`/`KeyLike`(Protocol)/`ScaleHint`/`GuideTones`/`TokenError`.

DoD (§14) — Chunk 1 targets 1, 2, 3, 8:
- [ ] §14.1 progressions loader P1–P10 (P11 → Phase 8) + one rejection fixture per rule class; both reference files load clean; P1/P4 cross-file vs reference `forms.yaml` — T4.
- [ ] §14.2 theory module: `resolve_token` goldens (suffixes/alterations/case errors/slash), §8.1/§8.2 tables, spelling goldens (12 tonics × 2 classes), chord/guide tones, voicing candidates + lane pruning, `vl_distance`/`optimal_voicing_path` on ii–V–I + register-drift, integer-cost property; `fifths` class ships — T1+T2.
- [ ] §14.3 `dressing.yaml` matches §6.3; tier-boundary/offset/clamp unit tests; every option §6.4-legal — T3.
- [ ] §14.8 `chord_tones` vs music21 `harmony.ChordSymbol` cross-validation (documented exclusions; version pinned) — T1.
- (§14.4/5/6/7/9/10 → Chunk 2.)

### Phase 3 — session 03 (plan: `plans/sessions/SESSION_03.md`)

Not split into chunks (single session). **Awaiting approval — no task dispatched.** Task list:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | `SongForm` extension fields (`total_of_type`/`phrases`/`harmony_tag`/`variant`/`ending`/`template_id`) | sonnet | done | 474c273 |
| T2 | `forms.yaml` schema + F1–F13 loader + `pop_rock`/`jazz` reference files + rejection fixtures | sonnet | done | 2d4f5a9 |
| T3 | Energy model (`form/energy.yaml` §6.1 + §6.2–§6.4 rules) + energy-column test | sonnet | done | 66725bf |
| T4 | Form generator stage (§7.1) + goldens/determinism/property/ladder tests | opus | done | 5c47b75 |
| T5 | §10 doc-amendment consistency check | orchestrator | done | (no edits — all 6 already present) |

Per-task reviews (opus) done for T1–T4 + a deep T4 algorithm review + a 2-lens whole-session review; fixes applied and committed: T2 F8 ending-candidate set widened, F9 `dropFromRepeat` scoped to the repeat block, `eligibility.arousal` order guard; T3 test discrimination (clamp-before-envelope, full base-table, R4 override); T1 positive `SectionEnding` path; T4 fallback `tag_bars` clamp (latent invalid-form guard) + property-test label/tag-vs-length/variant checks; review-fixes commit 0122149 (F4 undeclared-section rejection fixture + golden `variant` assertion). Final gates green: **339 tests**, ruff/format/mypy clean.

DoD (§11) — **all 8 items PROVEN** (both whole-session lenses graded 1–7 PROVEN; §11.8 verified):
- [x] §11.1 `forms.yaml` F1–F13 loader; one rejection fixture per rule class + F4 undeclared-section; both reference files load clean — `tests/test_forms_pack.py` (2d4f5a9, 0122149).
- [x] §11.2 `form/energy.yaml` §6.1 base table; §6.1–§6.4 reproduce both examples' 13 energy columns exactly; full base-table value check; clamp-order + R4 discriminators — `tests/test_form_energy.py` (66725bf).
- [x] §11.3 Form stage §7.1; both §7.4 SongForms field-for-field (incl. variant) — `tests/test_form.py::test_golden_example_{1,2}_field_for_field` (5c47b75, 0122149); orchestrator reproduced both plans independently.
- [x] §11.4 §7.2 form-stream RNG vectors asserted exactly — `test_form_stream_seed_vectors` (5c47b75).
- [x] §11.5 same plan → identical form; counting-RNG shim asserts 8 / 1 / 0 draws; budget-shift (90→8, 55→4) proves draws-only-when-≥2-feasible — `tests/test_form.py` (5c47b75).
- [x] §11.6 property matrix pop_rock/jazz × supported moods × maxLengthSec {30..600 step 15} × 25 seeds (~20k forms); all invariants incl. contiguity, 4-bar grid, hard ceiling, energies∈[0,1]@3dp, phrases-sum, index/total, ending-on-final-only, labels (independent §3.3 reimpl), variant None, tag≤length — `test_property_valid_songform` (5c47b75, 0122149).
- [x] §11.7 ladder & fallback: 30s@tempoRange.lo valid ≥4-bar form (both packs); tiny-budget fallback validates; degrade-op-class + D11 order asserted at config level; ladder-never-fires regression guard. **Ladder proven unreachable — see [C-02](../CAVEATS.md) (resolved); §11.7 satisfied via substitute coverage + post-review white-box tests on `_fit_and_degrade` (`test_ladder_*`).**
- [x] §11.8 §10 amendments verified present in PHASE_1 §3.4/§4.2/§7 Q4, PHASE_2 §9 Q4, ROADMAP §2/§4 (no edits needed).

CAVEATS: [C-02](../CAVEATS.md) — degradation ladder unreachable under pinned §5.2+§7.1 rules (**resolved** post-review: ladder kept as defensive code + white-box tested + §7.3 doc note).

### Phase 2 — session 02 (plan: `plans/sessions/SESSION_02.md`)

Not split into chunks (single session). **Awaiting approval — no task dispatched.** Task list:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | GenerationPlan extension (moodVector/budgets/timbreDirectives) | sonnet | done | 74e57b5 |
| T2 | Mood model + `moods.yaml` + §4.4 derived-table test | sonnet | done | 2ab6997 |
| T3 | Pack `interpreter.yaml` extension + `pop_rock`/`jazz` reference packs | sonnet | done | 8fe953f |
| T4 | Params model + §3.1 validation catalog + `params.schema.json` | sonnet | done | 2c0c602 |
| T5 | Interpreter stage (`interpret()`) + goldens/determinism/property | opus | done | 26f39a0 |
| T6 | §10 doc-amendment consistency check | orchestrator | done | (no edits) |

DoD (§11) — **all 8 items PROVEN** (final gates: 245 tests, ruff/format/mypy green at eb00804):
- [x] §11.1 params model + full §3.1 catalog (14 stable codes, full-list, not first-failure) + `docs/schema/params.schema.json` drift-guard — `tests/test_params.py` (2c0c602).
- [x] §11.2 `moods.yaml` (12 anchors + §4.3 overrides) frozen models; §4.4 table asserted exactly (12 moods × 12 cols, literal doc transcription) — `tests/test_moods.py::test_derived_defaults_match_phase2_table` (2ab6997); review hand-recomputed 3 override rows.
- [x] §11.3 `interpreter.yaml` parsing + §5.1 rules (incl. ensemble completeness + flavor referential + tonic-parse) ; `pop_rock`/`jazz` reference packs; per-rule rejection tests — `tests/test_interpreter_pack.py` (8fe953f, tonic test eb00804).
- [x] §11.4 Interpreter §6 exact; both §6.5 examples field-for-field + seed vector — `tests/test_interpreter.py` (26f39a0); orchestrator independently reproduced both plans.
- [x] §11.5 determinism: same-params→same-plan; zero draws when tempoBpm given (counting-RNG shim, factory==0); exactly one draw auto path; user-key/tempo bypass; degenerate window no-draw — `tests/test_interpreter.py` (26f39a0, eb00804).
- [x] §11.6 property tests: pop_rock/jazz × every supported mood → valid plan honoring tempoRange/modes/**expression-ranges**/swing∈[0.5,0.75] + Hypothesis over u64 seeds; `_resolve_mode` nearest-rung + tie-break — `tests/test_interpreter.py` (26f39a0, eb00804).
- [x] §11.7 one failing fixture per §3.1 code (14; code+field asserted) — `tests/test_params.py` (2c0c602).
- [x] §11.8 §10 amendments consistent: PHASE_1 §5.2 registry (L412), §5.6 golden vector (L457), §6 pack layout "schema owned by Phase 2" (L482-483), §7 Q1 resolved (L554), ROADMAP §2 style×mood row (L36). All present from the PHASE_2 design session; no edits needed.

CAVEATS: [C-01](../CAVEATS.md) — `PARAM_MALFORMED` structural code added beyond §3.1 (resolved).

### Phase 1 — session 01 (plan: `plans/sessions/SESSION_01.md`)

Not split into chunks (single session). Task status — awaiting approval, none dispatched:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| 1 | Seed system (`seeds.py`) + golden/determinism tests | opus | done | e0643ee |
| 2 | Schema models: TrackDocument + 5 IR cores | sonnet | done | 5d32e8c |
| 3 | Document validator V1–V8 + JSON Schema export | sonnet | done | 7fc3a5f |
| 4 | Pack loader + `styles/_stub/` + violation tests | sonnet | done | 41e3af8 |
| 5 | Milestone fixture + validation test | opus | done | 6fbaa7c |
| 6 | Playground Tone.js player (`playground/index.html`) | opus | done | cf2b490 |

DoD (§9) evidence collected as tasks land:
- §9.2 seed module — golden-vector + determinism tests green (`tests/test_seeds.py`, commit e0643ee); every §5.6 value independently recomputed by review.
- §9.7 determinism guard — two-RNG-same-seed test in `tests/test_seeds.py`; Ruff TID251 rule live in `pyproject.toml`.
- §9.1 schema package — frozen models for TrackDocument + 5 IR cores (`src/trackgen/schema/`, commit 5d32e8c); §3.8 validator V1–V8 + committed `docs/schema/trackdocument.schema.json` with drift-guard test (commit 7fc3a5f).
- §9.3 pack loader — stub pack loads, all 8 envelope-violation classes rejected (`tests/test_packs.py`, commit 41e3af8).
- §9.4 milestone fixture — `fixtures/milestone.trackdoc.json` validates with zero violations, exercises every schema feature; test pins concrete facts (commit 6fbaa7c). Independently re-validated by review.
- §9.5 playground — `playground/index.html` implements the §3.7 six-step contract; tone@15.1.22 pinned (Q9 resolved, major 15 covered by fixture `^15.1.0`); tempo scheduled on the transport timeline so it survives replay/reload (commit cf2b490). Per-task review found + fixed the AudioContext-time tempo bug.
- §9.6 listening checklist — **MANUAL, pending user.** The six audio checks require the user to open the playground and audition the milestone fixture. Not automatable.
- §9.7 determinism guard — two-RNG-same-seed test (`tests/test_seeds.py`) + Ruff TID251 banned-api rule verified firing on `random`/`time`/`os.urandom`/`datetime.now` outside `seeds.py` (probe confirmed at close-out).
- Whole-session review (4 opus lenses) found no blocking defects; 5 confirmed minor/major findings fixed in e27f704 (loader error-wrapping, dead-code/duplicate-whitelist removal in validator, `ppq` Literal pin, test gaps).
- Q9 resolved: tone@15.1.22 (major 15). Q10: package `trackgen` confirmed. music21 pinned 10.5.0 in uv.lock.
