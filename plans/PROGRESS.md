# Implementation Progress

Source of truth for implementation state across sessions. The orchestrator (see `PROMPT.md`) updates this file **immediately** at every task completion and step transition — never batched to session end. A new session must be able to resume losslessly from this file plus git log.

Statuses: `not started` · `planning` · `in progress` · `blocked` · `done`

## Handoff — next session starts here

> **Next:** **Phase 8, Chunk 8 (Session 22) — fusion_jazz (PHASE_8 §6), the third and last
> new pack. FRESH CHUNK — run PROMPT step 0/1 (orient → scope → `plans/sessions/
> SESSION_22.md` → USER APPROVAL GATE) before dispatching.** C8 authors the full pack per
> §9.4, DoD §14.3 + §14.8/§14.10 (fusion slices). **C8 completes the corpus (48→60) —
> closing C-17 and letting §14.5 finally be marked PROVEN.**
>
> **C7 (S21) DONE — blues; DoD §14.3/§14.8/§14.10 blues slices ALL MET.** Commits:
> `6e58e7a` plan · `b8bd5f2` T1–T5 pack+tests (atomic) · `7e7d3c3` T7 calibration +
> C-25/C-24 · `5e56ce7` T8 listening · `f2e6408` T9 bless (48 cells) · close-out this
> commit. Four gates green (**6327 tests**, from 6183); lint 0/0; 3-lens review
> CLEAN/COMPLIANT/PROVEN-WITH-GAPS, zero blockers; **zero engine changes** (corpus tuple
> only).
>
> **What C8 must know from C7:**
>  1. **Reachability scoping is now THREE-headed (compute ALL before authoring rung/pool
>     expectations):** (a) per-mood max section energy vs rungs (C-22, arousal ceiling);
>     (b) **section-kind floors** (C-23 — `parts/selection.py` maps every non-intro/outro
>     section type to `main` kind, and each section type's energy BASE bounds its rung
>     range: blues' all-solo form floored at 0.624 → rungs 1/2 dead). Fusion's `tune`
>     (head/solo) and `vamp` (main/breakdown) templates ALL route to main-kind — compute
>     each section type's energy band vs the 0.30/0.55/0.80 rungs; breakdown base 0.25
>     may make HIGH rungs dormant in vamp sections while solo sections skip LOW rungs —
>     the ladder may need per-section-type thinking, not one re-map; (c) **pool-gate ×
>     mode-resolution intersections** (C-25 — check every gated §6.3 pool entry's
>     modes×valence×dissonance corner is actually occupied by a supported mood under
>     auto-resolution; hendrix proved a gate can be structurally empty).
>  2. **The C-24 grid rule for fills:** W7 enforces grid homogeneity per (section, track)
>     Phrase, and fill tiling is grid-blind — a fill must sit on the same grid as every
>     pattern that can share its track's Phrase. Fusion is swing16/straight-16th; any
>     triplet-flavored content is a W7 risk to check at scoping.
>  3. **Atomic landing collateral moved:** `tests/test_interpreter_pack.py:117-118`'s
>     unregistered-style example now uses **`fusion_jazz`** (T5 repointed it from blues) —
>     C8's landing must repoint it again (e.g. to a literal like `"not_a_pack_xyz"`;
>     nothing else remains unbuilt). Line 114's set gains `"fusion_jazz"`. The dynamic
>     interpreter matrix auto-loads any registered pack — whole pack + literals in ONE
>     commit, as C6/C7.
>  4. **Fusion first-uses to pin (C7's constraint-11 analogue):** `feelTable: tight`
>     (§3.4 — third profile, first user); `bVI7(#11)`/`13sus`/slot-pinned `7#9` authored
>     extensions (P11 legality for #11; the 13sus quality token — verify `resolve_token`
>     handles it at scoping); **quartal voicings go LIVE** (C-04's keyless perfect-4ths
>     reading `[0,5,10,15]` has NO golden and NO production exerciser — jazz pads are
>     dormant; fusion Rhodes comping is its first real user, and §14.10 wants "quartal
>     Rhodes sits under C5"); `AutoFilter` allowlist entry (clav wah, first user);
>     `dropout`/breakdown second user (chill_lofi precedent: the dropout device is a
>     structural no-op on bar-quantized banks — the 2-layer cap does the stripping);
>     `turnarounds: []` + D6 inertness on tonic-ending vamps (the Cantaloupe case);
>     16th-grid swing16 at the tempo-table path (no ratio override per §6.1 — verify
>     table values at fusion tempos like C7 did, incl. the §6.4 note that swing16
>     displaces only pos%240==120 so 8th-grid ride lines pass straight).
>  5. **Corpus completion collateral:** `_CORPUS_PACKS` + literal updates (test_corpus
>     counts 48→60, pinned triple for fusion — compute `corpus_moods("fusion_jazz")` at
>     scoping incl. the default-vs-extremes collision check; fusion's mood set gains
>     triumphant, drops romantic/dark/melancholic per D8). Plan-null branch: fusion
>     (swing16 table + feelTable tight) is likely a THIRD fully-populated plan — extend
>     `test_corpus.py:301`'s branch knowingly. Closing C-17 also means updating its
>     CAVEATS status and the §14.5 DoD record.
>  6. **Zero engine changes for two consecutive pack chunks** — if a fusion first-use
>     (quartal! 13sus!) forces an engine fix, full bless collateral applies
>     (generatorVersion bump, serialize/milestone literals, 48-cell re-bless) — escalate
>     before applying (C6/C7 contingency clause, still unexercised).
>  7. **Scrub §6's printed YAML at scoping** (three-for-three precedent: §4.1 modes order
>     S20-1, §5.1 manifest fields S21-1 — expect §6.1's manifest snippet to omit
>     formatVersion/engine too, and check §6 prose claims against loader rules before the
>     approval gate).
>
> **OPEN items carried forward to C9:** formal reference-pack listening (C5 debt; the
> chill_lofi/blues passes are the template). C-18 (no CI). C-20 (+ C-22/C-23 postscripts;
> lens C's dormant-content dry-render idea, now twice-recommended — GAP-1). **NEW: GAP-2
> (lens C M13): calibration.yaml band values have zero regression coverage in any pack —
> a drifted band ships silently; weigh a calibration-artifact pin at C9.** C-19 §8.2
> annotation. L2-2 jazz crossings (C-21 structural; blues measured 1.8× jazz's rate,
> warn-only). Lint reachability blind to all three dormancy mechanisms (C-22/C-23/C-25)
> — a per-mood/per-section-kind/per-gate reachability lint is thrice-motivated at C9.
> C-03 remains unexercised by any pack (S21-3 corrected the C6 claim; fusion ships
> `turnarounds: []` so it stays synthetic-only through v1).
>
> **Env / gates:** `uv` / Python 3.12; four gates (`uv run pytest -n auto` · `ruff check`
> · `ruff format --check` · `mypy`); suite **6327 tests / ~43 s**. `_GENERATOR_VERSION`
> **0.1.3** (unchanged since C5 — C6+C7 were pure data). Pack versions: pop_rock/jazz
> 0.2.0, chill_lofi 0.1.0, blues 0.1.0. Corpus **48/60** (C-17; completes at C8).
> Determinism TID251. Never `git push`. Note: commit `ca67d3d` ("push override DON'T UNDO
> THIS CLAUDE") is the user's own commit of session status text — leave it alone.
>
> **CAVEATS (open):** **C-25 (NEW** — hendrix auto-dormancy, S21-6), **C-23 (NEW** —
> blues rung-1/2 dormancy re-map, S21-2; read items 1–2 above before C8 scoping**)**,
> C-22, C-21, C-20, C-18, C-17 (48/60, closes at C8), C-15, C-14, C-12 (check fusion
> crash.velocity lo at scoping — §6.5), C-11, C-10, C-08, C-07, C-06, C-03 (stays
> unexercised, see OPEN items). Resolved this session: **C-24** (triplet fill vs W7 —
> content fixed T5, §5.4 wording amended with sign-off).
>
> **C6 (S20) DONE — chill_lofi, the first new pack; DoD §14.3/§14.8/§14.10 lofi slices ALL
> MET.** Commits: `9e86b5a` plan · `51da4a0` T1–T5 pack+tests (atomic) · `be3c246` T7
> calibration + C-22 · `151fa45` T8 listening · `d95a043` T9 bless (36 cells) · close-out
> this commit. Four gates green (**6183 tests**, from 6052); lint 0/0; 3-lens review
> CLEAN/COMPLIANT/PROVEN-WITH-GAPS, zero blockers.
>
> **What C7 must know from C6:**
>  1. **Check mood-arousal reachability BEFORE authoring rung expectations (the C-22
>     lesson):** chill_lofi's §4.2/§10 prose promised rung-3/pads reachability, but the
>     supported moods' max arousal capped energy at 0.474 < the 0.55 rung-3 threshold —
>     pads never sound (34/50 pattern ids blind). At scoping, compute per-mood max section
>     energy for blues' mood set vs the 0.30/0.55/0.80 rungs and reconcile against §5's
>     authored-bank expectations FIRST. Blues keeps energetic/aggressive, so rung 3/4
>     should be genuinely live — verify, don't assume.
>  2. **The C6 workflow held end-to-end and is the template:** atomic landing (manifest
>     triggers discovery — `test_interpreter_pack.py` set + dynamic interpreter matrix);
>     2 candidates/slot incl. unreachable rungs (variety lint has NO escape;
>     `expected-unreachable` marker is file-level, silences unreachable-content only);
>     3/2 sibling weights co-authored; timbres must cover EVERY declared flavor id (TB1);
>     §9.4 order calibrate→listening→goldens; corpus extension = `_CORPUS_PACKS` + literal
>     updates (test_corpus/test_bless counts 36→48, "12 of 36"→"12 of 48", scoped-other
>     24→36) + unscoped `bless --approve` (first capture, NO version bump unless engine
>     changes — escalate those). Verify blues' `corpus_moods` default-vs-extremes at
>     scoping (raises on collision).
>  3. **Blues-specific first-uses to pin (C6's constraint-11 analogue):** swing8 from the
>     tempo table (NO ratio override — first pack on the table path at slow tempos);
>     explicit triplet-grid authoring + the one-grid-per-pattern lint (§3.1 — first
>     triplet content anywhere); `stop` device ENABLED (first pack; TR2 wants odds
>     present); tempo-gated eligibility bands (slow-blues 12/8-feel patterns; check
>     dangling-gates lint vs the mood tempo tiers); `close` variants incl. ritard
>     (calibrate labels ritard tails separately, 82679f8); C-03's SubV P8 path. The §5
>     printed YAML may carry doc bugs like §4.1's modes-order (S20-1) — scoping should
>     scrub §5 against loader rules before the approval gate.
>  4. **Plan-null collateral:** chill_lofi is the first fully-populated GenerationPlan
>     (swing + feelTable both set) — `test_corpus.py`'s null-retention test is now
>     conditional per pack. Blues (no feelTable? §5 says feelTable straight — CHECK: §3.4
>     says blues → straight explicitly, so its plan may also be fully populated or carry
>     nulls depending on schema) — extend the test's expectation knowingly, not by luck.
>  5. **Chunk 6 landed ZERO engine changes** (only the corpus tuple). If a blues first-use
>     forces an engine fix, the full bless collateral applies (generatorVersion bump,
>     serialize/milestone literals, reference re-bless) — escalate before applying.
>
> **OPEN items carried forward:** formal reference-pack listening (C5 debt → C9's rubric
> pass; chill_lofi's is DONE and is the template). C-18 (no CI). C-20 (+ C-22 postscript:
> lens C's G-1 dormant-content dry-render idea — weigh at C9). C-19 §8.2 annotation at C9.
> L2-2 jazz crossings (72/400, warn-only, C-21 structural). C-12 stays latent (blues crash
> lo? — check §5.5's crash range at scoping). C-03 LIVE at C7.
>
> **Env / gates:** `uv` / Python 3.12; four gates (`uv run pytest -n auto` · `ruff check` ·
> `ruff format --check` · `mypy`); suite **6183 tests / ~43 s**. `_GENERATOR_VERSION`
> **0.1.3** (unchanged — C6 was pure data). Pack versions: pop_rock/jazz 0.2.0,
> chill_lofi 0.1.0. Corpus **36/60** (C-17; completes at C8). Determinism TID251. Never
> `git push`. Note: commit `ca67d3d` ("push override DON'T UNDO THIS CLAUDE") is the
> user's own commit of session status text — leave it alone.
>
> **CAVEATS (open):** **C-22 (NEW** — chill_lofi rung-3/pads dormancy accepted + 34/50
> blind set; read postscript before C9 coverage decisions**)**, C-21, C-20, C-18, C-17
> (36/60), C-15, C-14, C-12 (**check blues crash.velocity lo at scoping**), C-11, C-10,
> C-08, C-07, C-06, C-03 (**goes live at C7**). C6 authors the full pack per the §9.4 checklist (manifest/interpreter
> → forms → progressions → banks rung-by-rung with audition → transitions → timbres → full-grid →
> calibrate → error-spotting → goldens+bands+version), DoD §14.3 + §14.8/§14.10 (lofi slices).
> *(Historical note: this C6 block's "C-03 goes live at C7" was refuted at S21 scoping — see
> the C7 section above and S21-3.)*

*(The orchestrator rewrites this block at every close-out — and mid-session on any pause — stating: current phase/chunk, last completed task + commit, and the exact next action.)*

## Phase status

| Phase | Scope | Status | Sessions | Notes |
| --- | --- | --- | --- | --- |
| 1 | Foundations & contracts | done¹ | 01 | ¹Code/automated DoD complete; §9.6 manual listening check awaits user audition of the playground |
| 2 | Parameter & mood model | done | 02 | All 8 DoD items proven; 245 tests green. Caveat C-01 (PARAM_MALFORMED) |
| 3 | Form & structure | done | 03 | All 8 DoD items proven; 339 tests green at 0122149. Caveat C-02 (ladder unreachable) resolved in post-review fix batch (349 tests) |
| 4 | Harmony engine | done | 04, 05 | All 10 DoD proven. Chunk 1 (SESSION_04: theory+dressing+loader; DoD 1/2/3/8). Chunk 2 (SESSION_05: stage+goldens; DoD 4/5/6/7/9/10). 4-lens whole-phase review clean. 644 tests. No new caveats (turnaround-truncation fix was own-code) |
| 5 | Rhythm-section part generators | done | 06, 07, 08, 09 | All §13 DoD 1–11 PROVEN; 990 tests, four gates. 4 chunks: loaders/foundations [06, DoD 1+2] → arrangement+selection [07, DoD 3+4] → generators/walker/voicing [08, DoD 5+6+7, C-04 resolved, C-09 arbitration] → orchestrator+Serializer+milestone [09, DoD 8+9+10, whole-phase review CLEAN/COMPLIANT/PROVEN/GOOD, C-10 latent logged]. §9.5 listening checklist CLOSED (user-confirmed 2026-07-17) |
| 6 | Transitions, variation & humanization | done | 10, 11, 12 | 3-chunk split (D1 seam). C1 stage-6 Transitions (10: DoD 1+3+4+8; C-11) → C2 stage-7 Humanizer (11: DoD 2+5+6) → C3 wiring+milestone+whole-phase (12: DoD 9+10+11). All §11 DoD 1–11 proven; 4-lens whole-phase review no blocker/major; **4315 tests**, four gates. Caveats C-11, C-12 (both latent/open). §11.10 listening checklist CLOSED (user-confirmed 2026-07-18) |
| 7 | Sound design | done | 13, 14 | **2-chunk split** (flip seam). C1 (13): new `sound/` package — engine data + evaluation + real `timbres.yaml` schema/TB1–TB9, unwired; DoD 2/3 + DoD 1(C1). C2 (14): the atomic flip — real `sound_design → SoundDesign` stage wired end to end, both `styles/*/timbres.yaml` authored, stubs deleted, goldens re-blessed (notes byte-identical), §9 field-for-field, 344-doc property matrix, zero-draw. Whole-phase 4-lens review **CLEAN/COMPLIANT/PROVEN/GOOD-WITH-NITS**; full §13 DoD 1–9 PROVEN; **4725 tests**. Caveats C-13 (§9.2 sample, resolved), C-14/C-15 (open, latent/prose). DoD 8 listening checklist CLOSED (user-confirmed 2026-07-18) |
| 8 | Quality, evaluation & pack expansion | in progress | 15, 16, 17… | Multi-session (~9-chunk plan below). Hard order: foundations → validators → tooling → golden/bless → reference refinement → chill_lofi → blues → fusion_jazz → close-out. **C1 (S15) DONE** — trace orchestrator + machinery amendments; DoD §14.1 PROVEN; 2-lens review CLEAN/PROVEN; no caveats. **C2 (S16) DONE** — 3-layer validator suite (`quality/` W1–W8 hard / L2-1 fail + L2-2 warn / L3 metrics+bands), warn/fail suite split; DoD §14.4 PROVEN; 2-lens review CLEAN/PROVEN; C-16 (L2-2 co-attack grain, user-ratified). **C3 (S17) DONE** — authoring tooling (audition CLI, pack linter+5 warnings, `--explain` selection log, `calibrate`→`calibration.yaml` + L2-reader reconciliation); DoD §14.7 PROVEN; 3-lens review found+fixed one blocker (audition drum sub-track filter); no new caveats. **C4 (S18) DONE** — golden corpus (24/60 cells at every IR boundary) + `trackgen bless` semantic diff + generatorVersion refusal + smoke matrix (315 cells) + 300-seed sweep (600 cells); 3-lens review APPROVE-WITH-NITS/COMPLIANT-WITH-DEVIATIONS/GOOD-WITH-NITS, no blockers; **5983 tests**. DoD §14.5 mechanism PROVEN but corpus **24/60 → completes at C8**; **§14.6 "in CI" NOT MET** (no CI substrate exists). Four new caveats **C-17** (2/5 packs), **C-18** (no CI), **C-19** (pop_rock cannot reach the 480 s bucket), **C-20** (corpus never selects 18/49 patterns — a 37 % blind spot that does NOT heal at five packs). **C5 (S19) DONE** — reference-pack refinement: zero abridged entries remained (already discharged); 38 second-candidate patterns cleared all 38 variety warnings (lint 0/0 both packs); calibrate tempo-band fix (ritard tails); first THREE production bless cycles (0.1.1 content / 0.1.2 stamps / 0.1.3 review fixes), pack versions 0.2.0; first blessed `calibration.yaml` ×2; 3-lens review CLEAN/COMPLIANT-WITH-DEVIATIONS/PROVEN, zero blockers. **DoD §14.2 met, listening clause PARTIAL (informal user pass, honest).** New caveat **C-21** (retarget window inert for chord voicings); **C-19 resolved** (ceiling accepted). 6052 tests. **C6 (S20) DONE** — chill_lofi authored full (52 pattern entries, 8 timbre flavors) + 86 tests; lint 0/0; first blessed calibration.yaml; formal listening pass (`listening/log.jsonl` created — the §8.4 collector now exists); corpus 24→36 (first capture, no version bump); five machinery first-uses verified end-to-end (dropout/breakdown cap, fade-HOLD, laidback, swing16+ratio override, single loop tag); 3-lens review CLEAN/COMPLIANT/PROVEN-WITH-GAPS, zero blockers; DoD §14.3/§14.8/§14.10 lofi slices MET. New caveat **C-22** (rung 3 + pads dormant grid-wide — arousal ceiling, accepted S20-5; blind set 34/50 ids). 6183 tests. **C7 (S21) DONE** — blues authored full (55 pattern entries, 8 timbre flavors) + 111 tests; **S21-2 rung re-map** (all-solo form → rungs 1/2 dormant, C-23); lint 0/0; first blessed calibration.yaml; formal listening pass (log.jsonl appended); corpus 36→48 (first capture, no version bump); first-uses verified (authored `(#9)` extensions draw-free, triplet-grid content through W7, tempo-gated [50,75] eligibility, stop at [1,3]); 3-lens review CLEAN/COMPLIANT/PROVEN-WITH-GAPS, zero blockers; DoD §14.3/§14.8/§14.10 blues slices MET. New caveats **C-23** (rung-1/2 dormancy, S21-2), **C-24** (triplet fill vs W7, resolved), **C-25** (hendrix auto-dormancy, S21-6). Zero engine changes. 6327 tests. **Next: C8 (S22) fusion_jazz — completes the corpus (60/60, closes C-17).** |

## Session log

One row per implementation session, appended at close-out. Session plan files live in `plans/sessions/SESSION_NN.md`.

| Session | Date | Phase / chunk | Outcome | Key commits |
| --- | --- | --- | --- | --- |
| 21 | 2026-07-21 | Phase 8 chunk 7 (blues, §5) — second NEW pack | 2 opus scoping agents (headline: **S21-2** — main-kind renders only in solo sections, R2 arch floors solo energy at 0.624 → §5.4's rung-1/2 ladder dormant grid-wide; also refuted the C6 handoff's "C-03 live at C7" claim — all turnarounds end plain V7; §5.1 manifest field omission; no allowlist gaps) → USER APPROVAL GATE (S21-1…S21-5 ratified as recommended) → T1 config (20/20 checks; review APPROVE zero findings) → T2 ‖ T3 ‖ T4 banks+timbres (reviews CHANGES-REQUIRED→fixed / APPROVE-WITH-NITS / APPROVE; T2's MAJOR was a comment containing the literal `expected-unreachable` token silently silencing the drums lint file — reworded, `_silenced_files()==set()` re-verified) → T5 integration (lint 0/0; 111 tests; **found+fixed the chunk's one real defect: §5.4's triplet snare fill unrealizable under W7 (fill tiling mixes grids per Phrase, 190/192 cells) → straight-grid re-author → C-24**; whole-landing review APPROVE-WITH-NITS, 3 mutations killed) → T6 full-grid (528 renders ZERO failures; rung arch 100%; blind set 20; **A1 ESCALATED: hendrix pool mode×valence gates mutually exclusive under auto mood-resolution → user ruled S21-6 accept+caveat → C-25**) → T7 first blessed calibration.yaml (artifact check PASS ×6) → T8 **formal listening pass** (user-confirmed real listen, all 8 moods, zero entries) → T9 corpus 36→48 (12 first-capture cells 12 MB; 36 cells zero-divergence; NO version bump; blues = second fully-populated plan → zero-null branch extended) → T10 3-lens review **CLEAN / COMPLIANT / PROVEN-WITH-GAPS** (13/14 fresh mutation kills; zero blockers; gaps = accepted C-20-class + calibration-band no-coverage → C9). Suite 6183 → **6327**; four gates green throughout; zero engine changes (corpus tuple only). DoD §14.3/§14.8/§14.10 blues slices **MET**. | 6e58e7a plan · b8bd5f2 T1–T5 · 7e7d3c3 T7 · 5e56ce7 T8 · f2e6408 T9 · (close-out this commit) |
| 20 | 2026-07-20/21 | Phase 8 chunk 6 (chill_lofi, §4) — first NEW pack | 2 opus scoping agents (corpus triple computed safe; atomic-landing constraint; variety-lint no-escape; five first-use risks mapped; §4.1 modes-order doc bug found by orchestrator) → USER APPROVAL GATE (S20-1…S20-4 ratified as recommended) → T1 config (29/29 checks; review APPROVE zero findings) → T2 ‖ T3 ‖ T4 banks+timbres (reviews APPROVE-WITH-NITS ×2 / APPROVE; batched fix: 3/2 weights pack-wide, pad ladder widened to perceptible 0.05 deltas with non-overlapping bands, dead rung-3 ornament gates 0.55–0.65 → 0.42/0.44 per reviewer's density-budget proof) → T5 integration (lint 0/0 on FIRST full load; 86 tests incl. five first-use pins + 48 selection locks; atomic commit; review APPROVE, mutation-verified) → T6 full-grid (64+ renders + 1200-render sweep clean; §10 arithmetic 12/12 exact; **A1 ESCALATED: rung 3 unreachable grid-wide → pads never sound; user ruled S20-5 accept+amend → C-22**) → T7 first blessed calibration.yaml (artifact check PASS ×6, byte-identical; §4.2/§10 amendments + C-22 same commit) → T8 **formal listening pass** (user-confirmed clean, all 8 moods; `listening/log.jsonl` CREATED) → T9 corpus 24→36 (12 first-capture cells 3.4 MB; 24 reference cells zero-divergence; NO version bump; chill_lofi = first fully-populated plan → null-retention test made conditional) → T10 3-lens review **CLEAN / COMPLIANT / PROVEN-WITH-GAPS** (15/15 mutation kills; zero blockers; blind set measured 34/50 → C-22 postscript). Suite 6052 → **6183**; four gates green throughout. DoD §14.3/§14.8/§14.10 lofi slices **MET**. | 9e86b5a plan · 51da4a0 T1–T5 · be3c246 T7 · 151fa45 T8 · d95a043 T9 · (close-out this commit) |
| 19 | 2026-07-20 | Phase 8 chunk 5 (reference-pack refinement, §7) | 2 opus scoping agents (headline: ZERO abridged entries remain — the real surface was the 38 variety-coverage warnings) → USER APPROVAL GATE (S19-1…5 all ratified as recommended: enumeration=verify-only · pads authored real · C-19 ceiling accepted · T3 diagnose-first · L2-2 in T2 scope) → T0 blast-radius (worktree probe; singleton pools consume ZERO draws, M1–M5 collateral map; caveat: its snapshot predated C4) ‖ T3 (ritard-tail hypothesis CONFIRMED — all 7 jazz sub-60 "violations" were 0.65×base tails, pop_rock clean because all forms author `close: cold`; calibrate band check now reads steady tempo, tails labeled; review APPROVE-WITH-NITS) → T1 ‖ T2 bank thickening (38 second candidates `*b`, additive-only, weight-1 50/50; reviews APPROVE / APPROVE-WITH-NITS; **S19-5 ESCALATED+CONFIRMED: `retarget.registerLow` inert for chord-degree voicings → user ruled accept+caveat → C-21**) → T4a first production re-bless (0.1.1; 22/24 cells first-divergent `phrases_stage5`; 15 pinned tests recomputed from engine — draw totals pop 10277→10561 / jazz 5304→5315; PHASE_5 §9.1/§9.4/§7.4/§12 + PHASE_2 §6.5 recompute+annotate per user rulings) → T5 informal user listening (playground used, "sounds good"; formal §8.4/T1-verdict OPEN, not rounded up) → T6 calibration.yaml ×2 + pack stamps 0.2.0 (second bless cycle 0.1.2, 24 cells first-divergent `plan`, zero notes; artifact check PASS ×5) → T7 3-lens whole-chunk review (CLEAN / COMPLIANT-WITH-DEVIATIONS / PROVEN, zero blockers; pads NOT dormant at high arousal — both packs' b-pad ladders made monotone; jazz tests brought to pop parity; third bless cycle 0.1.3, 8 pads-only cells; fix re-review APPROVE). Suite 5983 → **6052**; four gates green throughout; lint 0/0 both packs. **DoD §14.2: 3 clauses MET, listening clause PARTIAL (honest).** New caveat C-21; C-19 RESOLVED (accepted ceiling); C-20 postscript (blind set narrowed). | 5552b1a plan · 82679f8 T3 · 2125b75 T1+T2+T4a · ef9f410 T6 · 9661d06 T7 · (close-out this commit) |
| 18 | 2026-07-20 | Phase 8 chunk 4 (golden corpus + bless + smoke matrix) | 2 opus scoping agents → USER APPROVAL GATE (4 decisions ratified: S18-1 pytest-module-not-CI · S18-2 compact IR separators · S18-3 diagonal (V,A) mood triple · S18-4 300 seeds × 2 packs) → 4 opus implementer tasks (**T1 corpus ‖ T4 smoke matrix** → T2 diff → T3 CLI+capture) + per-task opus reviews + **T5 orchestrator-run rehearsal** + **T6 3-lens whole-chunk review**. New `src/trackgen/tooling/{corpus,blessdiff,bless}.py` + `trackgen bless [--approve] [--pack]` + **`fixtures/goldens/**` (240 files, 17 MB)**. Suite 4858 → **5983**. **Golden-value arbitration applied once**: the session plan printed the smoke matrix as `2×(11+10)×3×5 = 630`, double-counting the pack dimension; the T4 agent followed §8.2's dimension text over the printed total and built **315** — orchestrator confirmed independently and corrected the plan (ROADMAP §3, subagent-initiated). **Per-task reviews:** T1 APPROVE-WITH-NITS (the tie-break claim was **overstated** — determinism rests on `sorted(set(moods))`, over which the explicit rank is provably equivalent to `max()`; corrected + degenerate-triple guard added), T4 APPROVE-WITH-NITS (8 non-vacuity mutants all killed), T2 **CHANGES-REQUIRED** (elision unranked — a 69-note bucket elided while a 2-note one showed; a pure section rename reported "350 notes implicated" on a **byte-identical document**; L3 deltas silently omitted — all fixed), T3 APPROVE-WITH-NITS (**three degrade-open gaps**: a partial baseline masqueraded as a first capture and bypassed the version check entirely; the empty `SelectionResult` made **W4 pass vacuously**; a baseline missing `generatorVersion` was approvable — all now fail closed). **T5 rehearsal earned its DoD slot** — found (a) the version-stamp refresh gap (`--approve` left the corpus on mixed stamps while reporting "no divergence" — the tool asserting the corpus was fine when it was provably not byte-reproducible) and (b) **C-20**, discovered because the rehearsal's first attempt edited a pattern the corpus never reaches. **T6 3-lens** (correctness **APPROVE-WITH-NITS** — all 24 cells × 10 stages verified byte-reproducible under `PYTHONHASHSEED=random`; contract **COMPLIANT-WITH-DEVIATIONS** — V1–V8 and the milestone fixtures byte-untouched; test-quality **GOOD-WITH-NITS** — 36 mutations, 28 killed) → 2 fail-open edges + the **unprotected `note_affecting` conjunct** (orchestrator reproduced independently: mutate it and all 67 tests still pass) + untested metric elision + the 480 s bucket never asserting the engine responded to it. All fixed. **Four caveats C-17…C-20.** **DoD recorded honestly, not rounded up:** §14.5 mechanism PROVEN / corpus 24-of-60; §14.6 **"in CI" NOT MET**. Four gates green. | 38ebf7b plan · 1ae12f6 T1 corpus · 31e1575 T4 smoke · 4ed99d2 T2 diff · 4e13da8 T3 CLI+corpus · 9865079 T5 rehearsal fix · 40481c6 T6 review fixes |
| 17 | 2026-07-20 | Phase 8 chunk 3 (authoring tooling) | 4 opus implementer tasks (T1 audition → T2 linter → T3 --explain → T4 calibrate, serial) + T5 3-lens whole-chunk review + review-fix + close-out. New `src/trackgen/tooling/{audition,lint,calibrate}.py` + `packs/lint.py` + `pipeline/explain.py`; CLI `audition`/`lint`/`calibrate` + `--explain` on `generate`/`audition`. **DoD §14.7 PROVEN.** Everything additive — `--explain` threads an opt-in `explain=None` collector through the §9.3 draw sites (byte-identical default path, zero fixture edits); calibrate's L2-reader reconciliation is off the `generate` path. **3-lens whole-chunk review** (correctness/determinism · contract/DoD · test/code-quality): **one BLOCKER** — audition `--solo`/`--mute` on a drum sub-track filtered by note voice-tags and missed the untagged §6 fill/crash/hold notes (empirical repro: mute tom_low no-op, solo tom_low silence, mute snare 181→29) → **fixed** to filter by `phrase.track_id` (drum gen partitions per voice) + 3 discriminating tests; three minor fixes (calibrate report smoke test, dead `lint_pack` removed, keyword-only `explain`). **NO new CAVEATS** (L2 reconciliation is a fix *toward* §8.1, both lenses agreed). Process note: `REFERENCE.md` auto-committed by the T1 subagent unprompted (`0217217`) — kept + refreshed, flagged to user. Four gates green (**4858 tests**). | fb4f5d9 audition · 86e9e35 linter · d47d305 explain · 1d1fa59 calibrate · 1954de9 review-fix |
| 16 | 2026-07-18 | Phase 8 chunk 2 (validator suite W1–W8 / L2 / L3) | 4 opus implementer waves + reconciliation + review-fix + 2-lens whole-chunk review. New `src/trackgen/quality/` package (PHASE_8 §8.1), reads the C1 `GenerationTrace`; **`schema/validate.py` V1–V8 byte-unchanged.** Waves: **T1** foundation (`_common` helpers + Layer-1 W1/W3/W4/W6/W8 + `suite.validate_pipeline`) → **T2 ‖ T3 ‖ T4** (W2/W5/W7 · Layer-2 L2-1/L2-2 · Layer-3 metrics+`calibration.py` bands, disjoint files) → reconciliation (**warn/fail split**: `validate_pipeline`=failures V+W+L2-1, `pipeline_warnings`=L2-2; Layer-3 batch-only) → T5. Per-task reviews + fixes: **T1** APPROVE-WITH-NITS → W3 HOLD-note identification switched from document onset-proximity band to the `"hold"` tag on `phrases_stage7` (reviewer reproduced a false-fire on −5-tick negative humanizer displacement; regression test added). **Whole-chunk 2-lens (fresh opus, full C2 diff): correctness/contract CLEAN** (every W/L2/L3 check traced load-bearing — tick math, governing chord, lane lookup, C-11 strip; V1–V8 frozen; determinism/TID251; no import cycle; only stdlib `statistics`+pinned `pyyaml`), **test/DoD PROVEN-WITH-GAPS → PROVEN** (all violating fixtures discriminating incl. W6 C-11-strip, W7 stage6-vs-7, L2-1 beat-set asymmetry, `compute_bands` mean±2.5SD exact; 2 gaps closed by review-fix — W2 dropout+fill-outside-fill-bar branch fixtures now assert their specific messages, calibration `.yaml` read-back round-trip + L2 threshold-override tests). **L2-2 grain decision: user-ratified CO-ATTACK** over the literal sustain-overlap (jazz walking-bass sustain = 44 noise-warns, 0 co-attack crossings) → **C-16** (warn-only, non-gating; doc-wording clarification deferred). **DoD §14.4 PROVEN.** Four gates green (**4806 tests**). | 6283f58 plan · 2f2f5ca T1 · 177afec Wave B · (close-out this commit) |
| 15 | 2026-07-18 | Phase 8 chunk 1 (foundations: pipeline trace + machinery amendments) | 3 opus + 1 sonnet implementer tasks (T1 trace alone → T2 feel ‖ T4 allowlist → T3 extensions) + T5 whole-chunk 2-lens review + close-out. Foundational engine work, **no packs / no tooling; everything additive** (pop_rock/jazz byte-identical — whole-doc + humanizer + harmony goldens pass with NO fixture edits). **T1** `pipeline/trace.py` `generate_trace → GenerationTrace` exposes every IR boundary (phrases post-5/6/7 SEPARATELY + plan/sf/harmony/arr/selection/tempo/sound/doc); `generate_track` delegates, doc byte-identical — the substrate for C2 validators (W7/W8) / C3 `--explain` / C4 golden corpus / bless. **T2** `laidback`/`tight` feel profiles (§3.4 verbatim) + `feelTable` validated & threaded `GenerationPlan → interpreter → humanize` (mirrors `swing`). **T3** authored chord extensions (§3.5): `resolve_token` extgroup parse (grammar→P5, §6.4→P11 at loader), dressing passthrough guard makes an authored ext **draw-free** (discriminating zero-draw pin). **T4** allowlist Vibrato/AutoFilter already pre-seeded (Phase 7) — matched §3.7, added coverage test. Per-task reviews all APPROVE; **whole-chunk 2-lens: correctness CLEAN / test-DoD PROVEN** (one gap — positive feelTable selection — closed by a discriminating `_run`-path test, monkeypatch-verified). **DoD §14.1 PROVEN. No new CAVEATS** (all additive, no deviation). C-03 untouched (P8/P9 blind to extensions). Four gates green (**4758 tests**). | 3e93514 trace · dcdbd2b feel+feelTable · d64b0f7 allowlist · 0386b25 extensions+P11 · 68720e6 review-fix |
| 14 | 2026-07-18 | Phase 7 chunk 2 (the flip + integration + whole-phase) — **Phase 7 COMPLETE** | 4 opus tasks (T1 stage+content+§9 goldens unwired → T2 the atomic flip → T3 re-bless ‖ T4 property+determinism) + T5 whole-phase 4-lens review + close-out. Per-task opus reviews (T1 APPROVE-WITH-NITS, T2 APPROVE); **whole-PHASE 4-lens review (C1+C2): correctness CLEAN / contract COMPLIANT / test-DoD PROVEN / code-quality GOOD-WITH-NITS — no blocker, no major**. The pipeline now runs the real stage 8 end to end (real `sound_design → SoundDesign`, both `styles/*/timbres.yaml` authored, all stubs deleted). **Full §13 DoD 1–9 PROVEN** (DoD 8 listening checklist CLOSED, user-confirmed 2026-07-18). T3 re-bless: notes byte-identical to pre-flip (pop 2790/jazz 1275; V1–V8 clean; §9 sound anchors verified; invariant 2 held). T4: 344-doc property matrix (both packs × all moods × full flavor cross-product, non-vacuous) + 0 `sound`-stream draws + repeated-run identity. §12 amendment audit: all 6 present+consistent. **Arbitration C-13** (user sign-off): §9.2 upright attack sample mis-used brightness as the exp exponent → faithful 0.018, engine unchanged, §9.2 amended. New caveats **C-14** (TrackSound.midi fills §7's unspecified trigger-pitch delivery), **C-15** (§5.2 envelope.* prose imprecision, allowlist-resolved). Four gates green (**4725 tests**). | fa18869 stage+content · f773bb1 flip · 0b56ad9 re-bless · ab7292e property+determinism · (close-out this commit) |
| 13 | 2026-07-17 | Phase 7 chunk 1 (foundations) | 3 opus tasks (T1 engine data → T2 evaluation model → T3 real timbres schema/TB1–TB9, serial) + T4 whole-chunk 2-lens review. New `src/trackgen/sound/` package, **all unwired** (`resolve_pack`/`pipeline/`/reference `timbres.yaml` untouched; pipeline still runs the stub). **DoD 2, 3 PROVEN full; DoD 1 PROVEN (C1 slice).** Per-task + whole-chunk review. Whole-chunk 2-lens (correctness/contract + test-quality/DoD): **both CLEAN** — correctness traced TB7 **live** through `TimbresConfig.model_validate` for the off-class §8 flavors (FM piano/upright, AM organ_soft) confirming §8 will validate in C2 with no false rejection + illegal params rejected; §5.1 faithful (zero arbitration flags); allowlist covers §8 by full dry-run. Test lens PROVEN (no vacuous tests; half-even ties on 1/16 & 3/16, effective-mapping base-XOR-mod discriminating). 2 review fixes, both **tighten-to-design** (D4 drum-attackHardness bar; §4.2 send base-XOR-mod) — **no new caveats.** Four gates green (**4364 tests**). C2 = the flip. | b86be4e engine-data · aeaf047 evaluate · acd87f4 timbres+TB · 8715ded review-fix(send-XOR) |
| 12 | 2026-07-17 | Phase 6 chunk 3 (wiring + milestone + whole-phase) — **Phase 6 COMPLETE** | T1 wire real stages 6/7 + thread `tempoEvents` + crash serialize (`_STUB_MIX`/timbre midi 84/guard) + re-pin draw totals (pop 10277 / jazz 5304, decomposed against per-stage goldens) → then T2 ‖ T3 → T4 (audition) → T5 (whole-phase review + close-out). Per-task + **4-lens whole-phase review** (correctness / contract / test-DoD / code-quality across all 3 chunks): **no blocker, no major** — all clean/COMPLIANT/PROVEN/GOOD-WITH-NITS. **Full §11 DoD 1–11 PROVEN**; **DoD 11 §10 amendment audit** confirmed all 10 amendments present+consistent (ROADMAP §2/§3/§4, PHASE_1 §4/§4.5/Q5/§6, PHASE_5 PT12/§8.2/§8.1/§8.3, PHASE_2 §7.2). T2 re-blessed both whole-doc goldens (dedicated commit; 29/29 arbiter checks, jazz 40-entry tempo map, no §7 divergence). T3 property matrix = **1575 fully-wired docs** all §11.9-clean; P1-latent 0 trips, C-10 0 V3. Review fixes: stale mid-chunk docstrings refreshed, `BEAT` single-sourced, **C-12** logged (entry-crash velocity-0 latent). **DoD 10 §11.10 listening checklist CLOSED** (user-confirmed 2026-07-18; all automated DoD complete). Four gates green (**4315 tests**). | 6c05caf wire · c6e81fc re-bless · 373cfdc+8fa46ac property · b3756ba review-fixes+C-12 |
| 11 | 2026-07-17 | Phase 6 chunk 2 (stage-7 Humanizer) | 4 opus tasks (T1 feel loader → T2 engine → T3 ritard → T4 goldens, serial) + T5 2-lens whole-chunk review. Per-task + whole-chunk review; four gates green (**2734 tests**). **DoD 2+5+6 + humanizer slice of 7 PROVEN.** New `src/trackgen/humanize/` implements PHASE_6 §5 exactly (`feel.yaml`+loader/validator §5.3 → engine §5.1–§5.6/§5.8 → ritard §5.7); `humanize(phrases, form, plan) → (Phrase[], tempoEvents)`. **T4 arbiter: ZERO divergences** — every §7.2 value verbatim (head-1 bar-0 pre-jitter via the `_ZeroJitter` seam; full 39-event ritard table incl. all 11 anchors 68.5…45.5 + endpoints; two-feel legato 960→912) → no §7 amendment. Whole-chunk 2-lens review: correctness/contract **APPROVE** (engine matches §5 clause-by-clause; two reviewers independently recomputed RNG anchors + the full ritard curve), test-quality/DoD **APPROVE-WITH-NITS**. Fixes: T2-review made bass legato **track-level** (§5.6); T5 replaced a non-discriminating isolation test with the literal "regenerate-one-bar-in-isolation" test (empirically verified to fail a per-role RNG) + a direct §5.8 seed-anchor test + dropped a redundant golden. **No new caveats.** | 0ad958d feel · b46a08f engine · 8f0193a ritard · ec2cccf goldens · f71dffa review-fixes |
| 10 | 2026-07-17 | Phase 6 chunk 1 (stage-6 Transition engine) | 4 opus tasks (T1 loader → T2 6a HOLD + 6b devices → T3 6c mutation → T4 goldens, serial) + T5 2-lens whole-chunk review. Per-task + whole-chunk review; four gates green (**2667 tests**, 25-seed property matrix). **DoD 1+3+4+8 + stage-6 slices of 7+9 PROVEN.** New `src/trackgen/transitions/` package implements PHASE_6 §3/§4 exactly (6a HOLD → 6b fill/stop/dropout/crash → 6c five mutation operators; `transitions.yaml` loader + fill windows). **T4 (independent arbiter): ZERO divergences** — every §7 sample reproduced verbatim (pop 14/38/9 & jazz 10/32/11 draws, fired-op lists incl. 4 no-ops, crash velocities, fill bar 3, HOLD both) → no §7 amendment (unlike C-09). Whole-chunk review: correctness/contract APPROVE-WITH-NITS (10/10 clauses CONFIRM), test-quality/DoD PROVEN-WITH-GAPS. Fixes: N1 crash-default 1440 pinned in `_DEFAULT_DUR` (§10.7); N2 fill drops stray crash voice; N3 `drop_ornament` beat-1 protection structural; property matrix 4→**25 seeds** (§11.9). **C-11 logged** (internal voice/ornament provenance tags, serialize-invisible). | 22bd551 loader · 9218e14 devices+HOLD · 7623216 mutation · 492935f goldens · (close-out this commit) |
| 01 | 2026-07-14 | Phase 1 (all) | All 6 tasks built, reviewed, gates green (125 tests). DoD §9.1–§9.5 + §9.7 proven; §9.6 manual audition pending user. No CAVEATS (all §5.6 goldens reproduced exactly; no doc amendments). | e0643ee seeds · 5d32e8c schema · 41e3af8 packs · 7fc3a5f validator+export · 6fbaa7c fixture · cf2b490 playground · e27f704 review-fixes |
| 02 | 2026-07-15 | Phase 2 (all) | 6 tasks built, per-task + 4-lens whole-session review, gates green (245 tests). All §11 DoD 1–8 proven; both §6.5 goldens reproduce field-for-field; orchestrator pre-verified every load-bearing sample. Contract lens COMPLIANT. Review fixes: malformed-type wrapping (C-01), pack-tonic validation, mode-ladder dedupe, 3 test-coverage gaps closed. | 74e57b5 plan-fields · 2ab6997 moods · 8fe953f packs+refs · 2c0c602 params · 26f39a0 interpreter · eb00804 review-fixes |
| 09 | 2026-07-17 | Phase 5 chunk 4 (orchestrator + Serializer + milestone) — **Phase 5 COMPLETE** | 4 opus tasks (T1 timbres+stubs → T2 Serializer → T3 orchestrator+CLI → T4 fixtures+goldens+determinism, serial) + T5 whole-phase review. Per-task opus reviews all APPROVE-WITH-NITS. **DoD 8+9+10 PROVEN; full §13 DoD 1–11 complete.** Real orchestrator = the proven `_drive_full` chain incl. `select_patterns` (§8.1 pseudocode is stale). Both milestone `TrackDocument`s committed as the first whole-document goldens (engine-blessed; `validate_document == []`; re-serialize structure-identically). Determinism: repeated-run identity + total-draw shim (pop 18 / jazz 163) decomposed against every per-stream golden. Whole-phase 4-lens review: **correctness CLEAN** (720-doc fuzz all V1–V8), **contract COMPLIANT** (frozen paths clean; additive timbres), **test-DoD PROVEN** (1–11), **code-quality GOOD-WITH-NITS**. §9.4 anchors match C-09-corrected prose (no divergence). Orchestrator independently verified four gates + reproduced both fixtures. **C-10** logged (latent drum-dedup V3 edge, unreachable in v1). §9.5 listening checklist CLOSED (user-confirmed 2026-07-17, sounded correct). | e477484 timbres+stubs · 1de5e9c serializer · 055ff8b orchestrator+CLI · 6f69717 fixtures+goldens+determinism · 843e16c review-fixes+C-10 |
| 08 | 2026-07-16 | Phase 5 chunk 3 (generators / walker / voicing) | 4 opus tasks (T1 voicing ‖ T2 walker, then T3 generators, then T4 goldens) + investigation + amendment + T5. Per-task reviews all APPROVE-WITH-NITS. **Golden-value arbitration triggered:** T4 (independent transcriber) found 7 PHASE_5 §9.2/§9.3/§9.4/§13.5 samples diverged; did NOT tune (strict xfail + escalate). Deep investigation (trace + DP-cost) confirmed **all 7 are wrong derived doc samples, NO engine bug**; user signed off + ruled RC2 (ascending-pitch ordering authoritative). Amended docs + recomputed fixtures in one commit (C-09); engine unchanged. Whole-chunk 4-lens review: correctness APPROVE / contract COMPLIANT / test-DoD APPROVE-WITH-NITS / code-quality GOOD-WITH-NITS. **DoD 5+6+7 PROVEN; C-04 resolved.** 2 nits fixed (padding-value golden, zero-gap guard). Engine's hardest goldens reproduced unchanged (128 walker draws, all invariants). Gates green (941 tests). | b9eb7aa voicing · a93c1a6 walker · fa00f51 generators · 13c6c02 goldens+C-09 · 28d4695 review-fixes |
| 07 | 2026-07-16 | Phase 5 chunk 2 (arrangement + selection) | 3 opus tasks (T1 arrange ‖ T2 selection, then T3 goldens) + 1 review fix. Per-task reviews all APPROVE / APPROVE-WITH-NITS. Whole-chunk 2-lens review (correctness/contract + test-quality/DoD): both APPROVE-WITH-NITS, **DoD 3+4 PROVEN**, no blockers, no frozen contract touched. Orchestrator verified four gates green (816 tests) + independently reproduced the §4.5 anchors (densities/rungs/registers) and §9.1 counts (pop 1 / jazz 3). One test gap closed (production `rng_factory=None` select path golden-locked to §9.1 winner ids — no divergence). Two correctness nits proven non-reachable in v1 (adjacent-intro count read; extreme-bias lane span) → handoff notes, no caveats. | d52a00e arrange+lanes · 71ac7a7 selection · cbfaa19 §9.1 goldens · eecb17b golden-lock fix |
| 06 | 2026-07-16 | Phase 5 chunk 1 (loaders + foundations) | 4 tasks + T1b (all opus): T1 schema/loader/PT1-11, T1b bank-retarget default, T3 foundations, T2 reference banks. Per-task + 2-lens whole-chunk review (contract/integration + test-quality/DoD — both APPROVE-WITH-NITS, **DoD 1+2 PROVEN**, no blockers). Two per-task blockers caught+fixed: T1 PT2 non-decreasing rejected the normative voice-grouped §7 banks (C-05); T2 pr_dr_3 rung-3 bar-2 groove dropout. Reviewers re-derived every §3.3 degree/fallback + the §9.4 E2=40 anchor + all §9.1 candidate counts. Orchestrator verified all 11 §12 amendments present (no edits). 4 caveats: C-05 (PT2, resolved), C-06 (marker-gating), C-07 (§3.3 resolutions), C-08 (jazz ride band). Gates green (735 tests). | 60c6289 schema · 4299062 retarget-default · 095d0e1 foundations · 4e131c2 banks · 5edb8d3 polish |
| 05 | 2026-07-16 | Phase 4 chunk 2 (stage + goldens) | 3 tasks (T1 schema opus, T2 stage opus, T3 goldens opus) + orchestrator §13 check. Per-task + 4-lens whole-phase review (correctness/contract/test-quality/code-quality) across both chunks — all clean/COMPLIANT/GOOD, zero confirmed bugs. **DoD 4/5/6/7/9/10 PROVEN**; full §14 DoD 1–10 complete. Gates green (644 tests). Orchestrator independently reproduced seed anchor + both §10 `pool_selections` + Ex1 sample event + final tags + ASCII symbols + event counts (76/56). T3 surfaced + fixed a real stage tiling bug (own-code, not a caveat); review-fixes brought DoD-7 matrix to the pinned 25 seeds + added DoD-6 budget append-only. §10.2 Ex2 = 56 events (64 bars hold-merged; §10.2 pins no event count). | 09335d9 schema · 35dccba stage · abc447e goldens+fix · 8f15843 review-fixes |
| 04 | 2026-07-16 | Phase 4 chunk 1 (theory+dressing+loader) | 4 tasks (T1 opus, then T2/T3/T4 parallel opus). Per-task + 2-lens whole-chunk review; both lenses APPROVE-WITH-NITS, DoD 1/2/3/8 PROVEN. Gates green (587 tests). Orchestrator reproduced §5.6 seed vectors + all 10 §10 per-chord facts exactly. Reviews: T1 sus-case fix; C-03 (SubV in P8, user-approved A); C-04 (voicing API); lane-prune non-emptiness fix. Chunk 2 (stage+goldens) remains. | 21ce323 theory-core · 6cc5907 voicing · ee7ddb6 dressing · bb7114e progressions |
| 03 | 2026-07-15 | Phase 3 (all) | 5 tasks (T1–T3 parallel, T4 opus integration, T5 docs). Per-task + deep-T4 + 2-lens whole-session review; both whole-session lenses "contract-clean, all DoD PROVEN". Gates green (339 tests). Orchestrator pre-verified every §7.4 sample (seed vectors, 13 energy cells, both fitting totals, full 8-draw/1-draw sequences) — no doc amendment. Review fixes: F8/F9/eligibility completeness (T2), energy-order discriminators (T3), fallback tag_bars clamp + property rigor (T4), F4 fixture + variant assert (0122149). Caveat C-02: ladder proven unreachable, §11.7 via substitute coverage. | 474c273 schema · 2d4f5a9 forms-loader · 66725bf energy · 5c47b75 form-stage · 0122149 review-fixes |

## Phase detail

When a phase enters `planning`, the orchestrator adds a `### Phase N` section here containing: the approved chunk plan (if split), the task checklist with per-task status and commit hashes, DoD checklist with evidence as items are proven, and links to relevant CAVEATS entries. Keep entries terse — evidence pointers, not narrative.

### Phase 8 — Quality, evaluation & pack expansion (chunk plan)

**Multi-session (~9 chunks).** Phase 8 adds **no new pipeline stage or IR** — it consumes the
Phases 1–7 contracts and validates the whole, then triples the pack count. Hard ordering (PHASE_8
§9.4 / D13): foundations → validators → tooling → golden/bless → reference refinement → new packs
(**chill_lofi → blues → fusion_jazz**, simplest first) → close-out. Calibration bootstrap per §8.1
(Layer-1 + L2-defaults gate first renders → listening-blessed first batch → `calibrate` writes
`calibration.yaml` → then goldens). Session count may flex (tooling/new-pack chunks may split).

**Recommended chunk plan (pinned seams):**

| Chunk | Session(s) | Scope | DoD (§14) |
| --- | --- | --- | --- |
| C1 | 15 | **Foundations:** pipeline trace orchestrator (`generate_trace`) + machinery amendments (§3.4 feel profiles+feelTable, §3.5 authored extensions+P11, §3.7 allowlist verify) | 1 |
| C2 | 16 | **Validator suite:** Layer-1 W1–W8 (each violating fixture, subsumes V1–V8), Layer-2 L2-1/L2-2, Layer-3 L3 metrics + band computation | 4 |
| C3 | 17 | **Authoring tooling:** audition CLI (`--section`/`--solo`/`--mute`/`--play`), pack linter (errors + 5 warning classes), `--explain` selection log, `trackgen calibrate → calibration.yaml` | 7 |
| C4 | 18 ✅ | **Golden corpus + bless + smoke matrix:** matrix at every IR boundary (**24/60 cells — 2 packs; fills out C6–C8, C-17**), `bless` semantic-diff report + generatorVersion-bump check, smoke matrix **as a pytest module — NOT in CI, no substrate exists (C-18)**, 300-seed reference sweep | 5 (partial), 6 (partial) |
| C5 | 19 | **Reference-pack refinement (shakedown, §7):** enumerate abridged pop_rock/jazz banks; lint clean; calibrate (T1 level pass); capture goldens + `calibration.yaml`; error-spotting pass | 2 |
| C6 | 20 ✅ | **chill_lofi** (§4) — full pack per checklist §9.4; lint 0/0; calibrated; 12 corpus cells (36/60); formal listening pass (log.jsonl created); C-22 dormancy accepted | 3/8/9/10 (lofi) **MET** |
| C7 | 21 ✅ | **blues** (§5) — full pack per checklist (S21-2 rung re-map); lint 0/0; calibrated; 12 corpus cells (48/60); formal listening pass; C-23/C-24/C-25 | 3/8/9/10 (blues) **MET** |
| C8 | 22 | **fusion_jazz** (§6) — full pack per checklist | 3/8/9/10 (fusion) |
| C9 | 23 | **Close-out:** five-pack property tests, milestone rubric pass, A/B harness demo, final DoD sweep, §13 amendment audit, whole-phase 4-lens review | 9, 11 |

**New-module layout (from session-15 scoping):** `src/trackgen/quality/{layer1,layer2,layer3,
calibration}.py` (validators subsume V1–V8, read `(doc, trace)`); `src/trackgen/pipeline/trace.py`
(`GenerationTrace` + `generate_trace`); `src/trackgen/tooling/{audition,lint,calibrate,bless}.py`
(thin CLI wrappers); `src/trackgen/packs/lint.py` (collect-mode loader-rule runner + 5 warning
analyses); `fixtures/goldens/<pack>/<mood>/<len>-<seed>/<stage>.json`; `listening/log.jsonl` (data).

**Scoping facts carried forward (session 15, 2 opus agents):**
- **Intermediate IRs are not reachable today** — `generate_track` returns only the final doc. The IR
  chain exists only as the test-only `_drive_full`, copy-pasted across ~7 test files. A production
  `generate_trace` (C1 T1) is the prerequisite for W7/W8 (pre-humanizer + post-6/post-7 phrases),
  `--explain`, the golden corpus, and bless.
- **No draw/selection log exists** — the only draw sites are `weighted_choice` + one interpreter
  `randrange`, so `--explain` (C3) is tractable by instrumenting those.
- **Loader rules raise-on-first** (`PackLoadError`/`ValueError`), file-level context only (no line
  numbers — `yaml.safe_load` drops positions). Lint (C3) needs a **collect** variant, not `load_pack`.
- **Amendments are pre-scaffolded:** allowlist Vibrato/AutoFilter already present (`b86be4e`);
  `InterpreterConfig.feel_table` field exists (unvalidated/unwired); `ChordSpec.extensions` + the
  theory extension path exist (only `resolve_token`'s paren entry is stubbed to reject). C-amendments
  are wiring+validation, not new machinery. **C-03 orthogonal** (P8/P9 blind to extensions).
- **feelTable threading:** add `feel_table` to `GenerationPlan` (additive null field) mirrors how
  `swing` flows; changes the plan-IR JSON that C4's corpus will capture natively (bless it fresh).

#### Phase 8 — Chunk 8 — session 22 (`plans/sessions/SESSION_22.md`)

**Status: in progress — S22-1…S22-9 ALL USER-RATIFIED as recommended (2026-07-21).**
Baseline orchestrator-verified 2026-07-21 at `c37e5bd`: 6327 passed / 1 skipped, four gates
green. Scoping by 2 opus agents; the two headline findings were independently reproduced by
the orchestrator. Key facts pinned in the plan's Binding constraints:
**S22-3 (headline)** — §3.3/PHASE_4-D6's "`turnarounds: []` makes both boundary transforms
inert" is a wrong derived claim; PHASE_4 §5.1 step 5 / :207 normative text wins and
`harmony/stage.py:404-415` fires a fixed deceptive substitution on every same-tag boundary
ending tonic+T. Measured 874 substitutions / 336 renders; orchestrator reproduced a calm
`sus_pedal` vamp rendering `I7sus4 | vi | I7sus4 | vi …` — violates DoD §14.10 "vamps loop
without harmonic drift". **S22-4** — quartal's 15-semitone span leaves both §6.4 rung-1/2
comping classes empty for `Bbm9`/`A7#9` at comping lane low 50, and `parts/voicing.py:95-98`
**raises** (54/1152 explicit-key renders crash, incl. §6.1's pinned Bb-dorian Chameleon key).
**S22-2** — §6.1's `modes` order is a hard load failure (ladder-order rule).
**S22-1** — manifest omits required `formatVersion`/`engine` (S21-1 replay).
**S22-5** — rung 1 dead grid-wide (proof, not sampling), rung 4 `tune`-only, breakdown
2-layer-capped; recommended accept-as-printed, no re-map. **S22-6** — "first dorian-primary
pack" is wrong: 6/8 moods resolve major, mixolydian unreachable, corpus triple has zero
dorian cells. **S22-7** — 3 §6.6 recipes defective (base-XOR-mod ×2, `glass_pad` FM brightness
trap) + `fusion_ride_kit` has no recipe at all. Corpus triple **(energetic, calm, tense)**
verified non-colliding, 48 → **60 (C-17 closes)**; fusion is a third fully-populated plan.
Pads and quartal comping both genuinely render (unlike chill_lofi's C-22). No C-25 repeat —
every §6.3 pool entry fires. Fusion is C-24-safe (no triplet content; every `pos % 120 == 0`).

#### Phase 8 — Chunk 7 — session 21 (`plans/sessions/SESSION_21.md`)

**Status: in progress — S21-1…S21-5 ALL USER-RATIFIED as recommended (2026-07-21).**
Scoping complete (2 opus agents, 2026-07-21; baseline 6183/1 verified at `7500f24`). Key facts pinned in the plan's Binding constraints: solo-only form → rungs 3/4
live, rung-1/2 mains dormant (S21-2 ruling required); manifest formatVersion/engine omission
(S21-1); C-03 claim refuted (S21-3); swing-comment derived-sample stale (S21-4); no
allowlist gaps (Tremolo/oversample present); AMSynth brightness override required for BOTH
organ flavors; no `expected-unreachable` markers needed; corpus triple (energetic,
aggressive, romantic) safe, 36→48; C-12 safe (crash lo 0.45 → min 0.518).

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Config quintet (manifest+S21-1 / interpreter / forms / progressions / transitions) — 20/20 scratch checks; review **APPROVE** (zero findings; byte-fidelity sweep + independent loader verification incl. P7/P8/P9/P11); uncommitted until T5 (atomic) | opus | done | (commit 1) |
| T2 | Drums + bass banks — 30 patterns (16 dr / 14 bs); both §5.4 anchors byte-verbatim at re-mapped rung 3 (`bl_dr_2` w3, `bl_bs_3` w1 preserved); gated [50,75] 12/8 pairs beside ungated slots; ghost gates 0.60/0.62 recomputed live-not-dead by reviewer; review **CHANGES-REQUIRED → fixed**: 1 MAJOR — drums header comment contained the literal `expected-unreachable` token, silencing the file's unreachable-content lint via the substring scan (latent; orchestrator reworded both banks' headers, re-verified `_silenced_files() == set()`); 2 NITs fixed/accepted. Reviewer confirmed full pack loads + lint 0/0 | opus | done (fix verified) | (commit 1) |
| T3 | Comping + pads banks — 26 entries; triplet-roll re-located to rung 3 (gated); pads ladder non-overlapping bands; review **APPROVE-WITH-NITS** (comment imprecision fixed inline by orchestrator; pad 0.04 sibling delta reviewer-accepted) | opus | done (fix verified) | (commit 1) |
| T4 | timbres.yaml — all 8 flavors; THREE full TB7 overrides (organ_drawbar, organ_swell, upright_soft/FMSynth); kick-dry adjudicated vs PHASE_7 D2 (correct); review **APPROVE** (78 allowlist pairs / 0 illegal; §5.6 fidelity line-by-line) | opus | done | (commit 1) |
| T5 | Integration + blues tests — lint 0/0; 111 new tests (55 pack incl. 6 first-use pin groups + 56 variety with 53 locked-seed draws); 2 literal edits (`test_interpreter_pack.py:114` set, unregistered-example → fusion_jazz); 4 PHASE_8 §5 amendments (S21-1/S21-2+C-23/S21-3/S21-4); **one real defect found+fixed: triplet snare fill `bl_dr_f1` tripped W7 on 190/192 cells (grid-blind fill tiling) → re-authored straight-grid → C-24** (§5.4 fills wording fix pending sign-off); gates orchestrator-verified 6302/1 | opus | done | (commit 1) |
| T6 | Full-grid audition + first-use verification — **528 renders, 0 validation failures**; rung arch confirmed all 8 moods (early solos rung 3 → final rung 4, 100%); blind set 20 ids (16 rung-1/2 mains per C-23 + 4 pads intro/ending, C-22 class); all 5 first-uses verified musically (303 stops fired; triplet grid survives post-humanizer; swing 0.722/0.668 exact; 0 ritards; #9 voiced pc-verified); L2-2 warn profile 171 (C-21 class, 1.8× jazz); --explain coherent ×2. **A1 (MODERATE, ESCALATED → S21-6): hendrix pool structurally unreachable in auto generation (mode×valence gates mutually exclusive) — user ruled accept+caveat → C-25**; whole-landing review (b8bd5f2) APPROVE-WITH-NITS (3 mutations killed; C-24 count softened) | opus | done | — |
| T7 | Calibrate → first blessed `styles/blues/calibration.yaml` (487 lines; 8/8 moods; L2 = bootstrap defaults 0.95/0.98; 18/135 zero-width L3 bands, known-latent) — independent artifact check **PASS ×6** incl. byte-identical re-run, exact band recomputes, L2-reader sentinel proof, cold-close (0 tempo events, no ritard tails); S21-6 (§5.3 hendrix note + C-25) + C-24 wording amendment same commit | orchestrator+opus | done | 7e7d3c3 |
| T8 | USER listening gate — **FORMAL CLEAN PASS, user-confirmed 2026-07-21** (explicitly asked-and-confirmed real listen, not a greenlight; all 8 moods; three tempo tiers / boogie / turnaround-relaunch / stop focus checks; ZERO §8.4 entries). Session-21 pass record appended to `listening/log.jsonl` | user | done | 5e56ce7 |
| T9 | Corpus 36→48 + bless first capture — `_CORPUS_PACKS` += blues; triple (energetic, aggressive, romantic); unscoped `bless --approve`: **36 reference cells CLEAN (zero divergence), 12 blues first-capture cells (12 MB)**; NO generatorVersion bump (zero engine changes); literals test_corpus/test_bless 36→48 + blues pinned triple + zero-null branch extended to blues. Gates 6327/1 | orchestrator | done | f2e6408 |
| T10 | Whole-chunk 3-lens review + close-out — lens A (content) **CLEAN** (§5 byte-fidelity re-swept on final tree; 5 ROADMAP invariants held incl. 3 corpus cells re-rendered byte-identical from meta; C-23's 0.624 floor reproduced exactly over 480 renders; 1 NIT: stale interpreter.yaml swing comment → fixed inline by orchestrator). Lens B (contract/DoD) **COMPLIANT** (four gates independently reproduced 6327/1; §14.3/§14.8/§14.10 blues ledgers MET; §9.4 order + §8.2 bless discipline verified from git; loader rules proven by break-a-copy; zero out-of-scope creep). Lens C (tests) **PROVEN-WITH-GAPS** (13/14 fresh mutation kills — the survivor M13 is the calibration-band no-coverage latent, GAP-2; 53 selection locks production-path-proven; blind set reconciled to exactly 20 = C-23's record; blind entries structurally subsets of rendered siblings, lowering GAP-1 risk vs chill_lofi; T9 literals clean; no flakiness). **ZERO blockers/majors — no fix loop.** GAP-1/GAP-2 → C9 | opus ×3 | done | (close-out commit) |

#### Phase 8 — Chunk 6 — session 20 (`plans/sessions/SESSION_20.md`)

**Status: CHUNK 6 COMPLETE (2026-07-21).** All decisions user-ratified: S20-1 modes-order
amendment · S20-2 formal listening + log.jsonl · S20-3 smoke matrix → C9 · S20-4 version
0.1.0 · **S20-5 rung-3/pads dormancy accepted (T6 escalation → C-22)**. DoD §14.3/§14.8/
§14.10 lofi slices **all MET** (ledger in SESSION_20.md); corpus 36/60; 3-lens review
CLEAN / COMPLIANT / PROVEN-WITH-GAPS, zero blockers. Commits: 9e86b5a plan · 51da4a0 T1–T5
pack+tests · be3c246 T7 calibration+C-22 · 151fa45 T8 listening · d95a043 T9 bless ·
close-out this commit.

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Config quintet (manifest/interpreter/forms/progressions/transitions) — 29/29 scratch checks; review **APPROVE** (zero findings; reviewer re-ran model_validate + cross-file P6/P7 + budget arithmetic); uncommitted until T5 (atomic constraint) | opus | done | (commit 1) |
| T2 | Drums + bass banks — 28 entries (lf_dr_2 §4.4-verbatim w3; rim→perc per §3.6; monotone ladders; all ungated) — review **APPROVE-WITH-NITS**: 1 MINOR, rung-3 gated ornaments dead (max reachable budget 0.452 < gates 0.55–0.65 → rung 3 ≡ rung 2 audibly); FIXED: gates → 0.42/0.44 (authoring latitude, D16; lf_dr_2's pinned 0.45 untouched; verified live only for happy-at-ceiling, closed at defaults) | opus | done (fix verified) | (commit 1) |
| T3 | Comping + pads banks — 24 entries (flat-density pads, velocity-carried monotone rise) — review **APPROVE-WITH-NITS**: N1 pad sibling 0.02-vel delta inaudible + N2 1/1 weights vs 3/2 convention — FIXED: pad ladder 0.25/0.30/0.31/0.36/0.37/0.42/0.43/0.48 (non-overlapping bands), 3/2 weights all four files (fix agent verified: model-validate, lf_dr_2 intact, monotone holds) | opus | done (fix verified) | (commit 1) |
| T4 | timbres.yaml — all 8 flavors + bus/master (ep_mellow brightness override load-bearing vs FMSynth; space-mapped-send XOR per jazz precedent) — review **APPROVE** (merge trap traced in code, kit completeness vs banks confirmed, 1 advisory nit no-change) | opus | done | (commit 1) |
| T5 | Integration + chill_lofi tests — lint 0/0 on FIRST load (no pack edits needed); 1 literal (`test_interpreter_pack.py:114`); 86 new tests (38 pack + 48+2 variety; first-use pins incl. dropout-noop-invariant + synthetic-truncation proof, fade-HOLD zero ritard, laidback shift, breakdown 2-layer cap); gates orchestrator-verified 6158/1; T5 review **APPROVE** (mutation-verified discriminating; production-path draw locks confirmed; dropout disclosure honest; 1 nit comment fixed inline, rides with T7 commit) | opus | done | 51da4a0 |
| T6 | Full-grid audition + first-use verification — 64+ renders + 1200-render energy sweep, ZERO validation failures/warnings; §10 arithmetic exact (12/12); all five first-uses behave (breakdown strips ~30%, fade-HOLD clean, laidback offsets measured, swing16 137/240=0.5708, single loop draw + diversity); --explain coherent. **A1 (MEDIUM, ESCALATED → S20-5): rung 3 unreachable grid-wide (max energy 0.474 < 0.55) → pads NEVER sound, rung-3 banks dormant; §4.2/§10 pad-reachability prose wrong (root cause: chill_lofi drops energetic, max arousal = happy +0.40).** A2 happy kick 0.937 post-humanizer (engine dynamics, flag to T8 ear). A3 info | opus | done — awaiting S20-5 ruling | — |
| T7 | Calibrate → first blessed `styles/chill_lofi/calibration.yaml` (442 lines; 8/8 moods; NO pads entries per C-22; L2 thresholds = engine defaults 0.95/0.98 §8.1-bootstrap; 34/120 zero-width L3 bands, known-latent C5 pattern) — independent artifact check **PASS ×6** incl. byte-identical determinism + exact band recompute; bootstrap test flipped to `test_calibration_yaml_blessed`; S20-5 doc amendments (§4.2/§10) + C-22 in same commit | orchestrator+opus | done | (this commit) |
| T8 | USER listening gate — **FORMAL CLEAN PASS, user-confirmed 2026-07-21** (all 8 moods; breakdown/ending/happy-kick focus checks; ZERO §8.4 error entries; A2 acceptable under master glue). `listening/log.jsonl` CREATED with the structured pass record — the §8.4 evidence collector now exists. DoD §14.8 lofi slice: error-spotting pass executed, nothing to fix or file | user | done | (T9 commit) |
| T9 | Corpus 24→36 + bless first capture — `_CORPUS_PACKS` += chill_lofi; triple (nostalgic, happy, melancholic) as scoped; unscoped `bless --approve`: **24 reference cells CLEAN (zero divergence), 12 chill_lofi first-capture cells written (3.4 MB)**; NO generatorVersion bump (first capture, no engine change). Literal updates: test_corpus.py (triples/counts/_PACKS/docstrings), test_bless.py (12-of-36, 36-cell counts, scoped-run 24). One real finding: chill_lofi is the FIRST fully-populated plan (swing+feelTable set, zero nulls) — null-retention test made conditional, chill_lofi's zero-null shape asserted explicitly. Gates 6183/1 | orchestrator | done | (this commit) |
| T10 | Whole-chunk 3-lens review + close-out — lens B (contract/DoD) **COMPLIANT, zero findings** (gates/lint/§14.10 cells/engine-probe independently reproduced; §9.4 order + §8.2 bless discipline verified; §14.3/§14.8/§14.10 ledgers all MET with honest partials; 3 close-out bookkeeping observations). Lens C (tests) **PROVEN-WITH-GAPS**: 15/15 mutation kills (incl. engine-side breakdown-cap + corpus-cell-drop); no flakiness; null-retention edit proven discriminating; C-1 three stale "24" comments fixed inline by orchestrator; G-1..G-3 = the accepted C-20/C-22 blind class, measured precisely: **34/50 chill_lofi pattern ids never render** (also rung-1 mains, both fills, comping intro — broader than C-22's prose; postscript at close-out). Lens A (content) **CLEAN**: §4 byte-fidelity sweep verbatim; 5 ROADMAP invariants held (comping max midi exactly 71; 2 corpus cells byte-identical re-render); first-uses re-verified on a 400-render sweep; C-22 dormancy confirmed (max energy 0.474, max rung 2, pads never active); NITs only (rim→perc documented; stale-pyc environment artifact — cleared, final gates run from clean compile). **ZERO blockers/majors across all three lenses — no fix loop.** Close-out: C-22 postscript (blind set 34/50), SESSION_20 DoD ledger closed all-MET, handoff rewritten | opus ×3 | done | (close-out commit) |

#### Phase 8 — Chunk 5 — session 19 (`plans/sessions/SESSION_19.md`)

**Status: planning — session plan written, AWAITING USER APPROVAL (decision items S19-1…S19-5).**

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T0 | Blast-radius map: what breaks when a slot gains a 2nd candidate (scratch experiment) | opus | done (report only) | — |
| T3 | Jazz tempo-band diagnosis → CONFIRMED ritard-tail artifact; calibrate fixed, review APPROVE-WITH-NITS | opus | done | 82679f8 |
| T1 | pop_rock bank thickening — 23 second candidates (`pr_*b` ids) + `tests/test_pop_rock_variety.py` (26 tests). Review **APPROVE** (scratch-mutation-verified additive lock; 1 nit → T5: `pr_pd_1b` mild ladder compression) | opus | done | (bless commit) |
| T2 | jazz bank thickening — 15 second candidates (`jz_*b`) + `tests/test_jazz_variety.py` (35 tests). Review **APPROVE-WITH-NITS**; **S19-5 escalation CONFIRMED by reviewer** (`retarget.registerLow` dead data for chord-degree voicings — lane-pruned only, floor 46–50; no pack edit can clear L2-2; user ruling pending). Nits: land atomically with T4a; append `jz_dr_4b` 0.62 to C-08's enumeration. Weight-1 50/50 ruled optimal-under-additive-only by both reviewers | opus | done | (bless commit) |
| T4a | Re-bless cycle 1: generatorVersion 0.1.0→0.1.1; unscoped `bless --approve` (22 cells rewritten, all first-divergent `phrases_stage5`; 2 restamped); 3 milestone fixtures regen + 2 version literals; 15 pinned-value tests recomputed from the engine (draw totals pop 10277→10561 / jazz 5304→5315; winner flips incl. jazz head `jz_dr_2→jz_dr_2b`, pop verse bass `pr_bs_2→pr_bs_2b`; jazz bar-48 crash-kick suppression structural, §3.7-legitimate); PHASE_5 §9.1/§9.4/§7.4/§12 amended per user-ratified recompute+annotate; C-21 logged + C-08 appended | orchestrator | done | (bless commit) |
| T5 | USER listening block — user auditioned via playground (their port tweaks evidence use) and said "sounds good, proceed"; ZERO error-spotting entries filed; T4b not needed (no edits). Recorded honestly: informal pass, formal §8.4 per-mood checklist + explicit T1 level-pass verdict remain OPEN (close explicitly or carry to C9) | user+orchestrator | informal pass, formal items open |
| T6 | Calibration capture — first blessed `calibration.yaml` ×2 (independent opus check PASS ×5: shape, L2-reader activation, band sanity, coverage 11/10 moods, byte-identical determinism re-run); pack stamps 0.2.0 → second bless cycle (generatorVersion 0.1.2, 24 cells first-divergent `plan`, zero notes); C2-era absence tests updated; PHASE_2 §6.5 stamps annotated. Observations for T7 lens (b): blessed L2 thresholds == engine defaults in all 21 (pack,mood) cells; several zero-width L3 bands (latent — no per-render band consumer exists) | orchestrator | done | ef9f410 |
| T7 | Whole-chunk 3-lens review: content **CLEAN** / contract **COMPLIANT-WITH-DEVIATIONS** / tests **PROVEN** (lens C independently recomputed 8 pin groups from the live engine — all exact) — ZERO blockers/majors. Fix batch (2 MINOR + 2 NIT content, 2 MINOR test-parity) applied + re-review **APPROVE**; third bless cycle 0.1.3 (8 pads-only cells, first-divergent `phrases_stage5`) | opus ×3 + fix agent | done | 9661d06 |

**Post-T1/T2 state (orchestrator-verified 2026-07-20):** both packs lint **0 errors / 0 warnings**
(was 23+15); ruff check/format/mypy clean; pytest **44 failed / 6003 passed / 1 skipped** with every
failure in the expected collateral classes (27 `test_bless` corpus · 4 M1 `test_reference_banks` ·
2 M2 `test_selection_goldens` · 2 M3 `test_pipeline_determinism` · 2 M4 `test_whole_document_goldens` ·
2 M5 `test_generator_goldens` · 2 `test_transitions_goldens` · 3 `test_humanizer_goldens`) — zero
validation failures. T1 empirical note: pop_rock pads are NOT uniformly dormant — aggressive-class
moods route pads at rungs 3/4, so only 8 slots across both packs are truly golden-blind. Weight
convention: all new siblings weight 1 → 50/50 pools (additive-only precludes 3:2 incumbent-dominant;
flagged to T7). T4a checkpoint items for the USER: arbitration sign-off on stale PHASE_5 §9.1
narrative/count samples + §7.1/§7.4 inventories + §9.4 head-1 bar-0 sample; S19-5 registerLow ruling.

**T0 blast-radius findings (binding on T1/T2/T4a):** a singleton pool consumes ZERO draws
(`selection.py::_draw`, draw-iff-≥2 — verified in the current tree); adding a 2nd candidate flips
the slot to one `weighted_choice` draw and shifts every LATER same-role draw's RNG input
(cross-rung winner-flip is live risk — re-verify winners empirically, never assume "incumbent
holds"). Collateral mechanisms: **M1** static candidate-count pins in `tests/test_reference_banks.py`
(4 tests — trip for EVERY slot incl. golden-blind); **M2** `tests/test_selection_goldens.py` draw
narratives; **M3** `_TOTAL_DRAWS` pins in `tests/test_pipeline_determinism.py` (pop 10277 / jazz
5304 — recompute, measured pins not arbitration); **M4** whole-doc goldens + 3 milestone fixtures
(regen via `tests/_regen_milestone_fixtures.py`); **M5** per-bar anchor goldens (confirmed:
`test_generator_goldens.py::test_jazz_head1_bar0_full`; audit siblings for comping/bass slots);
plus (post-C4 surface, from C4's own handoff): the 24-cell corpus re-bless (unscoped `--approve`)
+ the 3 generatorVersion collateral tests. Golden-blind slots trip ONLY M1. Arbitration-rule-2
sign-off needed for stale printed samples: PHASE_5 §9.1 (draw narrative + count table), §7.1/§7.4
(bank inventories gain siblings), §9.4 (jazz head-1 bar-0 sample) — user sign-off at T4a before
doc edits. **T0 caveat: its worktree snapshot predated C4** (4858-test baseline; no corpus/bless
probes) — M1–M5 verified against pre-C4 tests, all unchanged since; corpus divergence gets read
directly from the T4a semantic-diff report instead.

**DoD §14.2 ledger (C5 close-out, recorded honestly):**
- [x] **All abridged PHASE_5/PHASE_7 entries enumerated — MET** (independently re-verified by T7 lens B: zero abridgement markers; id sets match §7/§8; the enumeration was discharged by Phases 5/7, and C5's §7.4 note records the 38 added second-candidate ids).
- [x] **Lint clean — MET** (0 errors / 0 warnings both packs, was 23+15 variety warnings; no annotation escape used — all cleared by real content).
- [~] **Calibrated (T1 executed) — PARTIAL.** `trackgen calibrate` run + first blessed `calibration.yaml` ×2 committed (independent check PASS ×5, byte-identical re-run). BUT the listening half was an INFORMAL user pass ("sounds good, proceed"; playground demonstrably used; ZERO §8.4 error-spotting entries; no explicit T1 level verdict; `listening/log.jsonl` does not exist). NOT rounded up — close explicitly or fold into C9's rubric pass.
- [x] **Goldens + calibration.yaml captured — MET** (corpus byte-reproducible at generatorVersion 0.1.3 across three bless cycles, every approve unscoped; both calibration artifacts committed at ef9f410).

#### Phase 8 — Chunk 4 — session 18 (`plans/sessions/SESSION_18.md`)

**Chunk 4 COMPLETE.** The golden corpus, the bless workflow, and the smoke matrix. Waves: **T1 ‖ T4**
(file-disjoint) → T2 → T3 → T5 (orchestrator) → T6. Suite 4858 → **5983**; four gates green,
orchestrator-verified after every task. **DoD §14.5 mechanism PROVEN (corpus 24/60); §14.6 content
PROVEN, "in CI" NOT MET.**

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Corpus module (`tooling/corpus.py`): `STAGES` ×10, `corpus_moods` (S18-3), 24-cell matrix, encode/decode per S18-2 | opus | done | 1ae12f6 |
| T4 | Smoke matrix (315 cells) + 300-seed sweep (600 cells), Layers 1–2 | opus | done | 31e1575 |
| T2 | Semantic diff (`tooling/blessdiff.py`): first-divergent-stage, note add/remove/move, L3 deltas | opus | done | 4ed99d2 |
| T3 | `trackgen bless` CLI + S18-8 refusal + the committed 24-cell corpus (240 files, 17 MB) | opus | done | 4e13da8 |
| T5 | Deliberate-change rehearsal (DoD §14.5) + the version-stamp-refresh fix it found | orchestrator | done | 9865079 |
| T6 | 3-lens whole-chunk review + fixes + close-out | orchestrator | done | 40481c6 |

**Scope decisions ratified at the approval gate:** S18-1 pytest-module-not-CI · S18-2 compact IR
separators (`document.json` keeps indent=2) · S18-3 mood triple = default + the (V,A)-farthest pair ·
S18-4 sweep = 300 seeds × 2 packs at default params. Plus S18-5 (no `selection.json`), S18-6 (move
rule), S18-7 (`FormSection.id` attribution), S18-8 (bump check reads the baseline document).

**Two extensions beyond §8.2's printed text — assessed by two independent reviewers as ADDITIVE
GAP-FILLS, not deviations (no caveat, no sign-off needed):** a fourth **`changed`** counter for
velocity-only edits (without it such a change renders `notes — none`, the exact shape §8.2's report
format exists to stop being rubber-stamped) and **exact-onset cancellation** before move-pairing
(S18-6 leaves the order of its move rule and multiset difference unstated; cancelling first is the
only coherent order). Recorded here because a reader comparing §8.2's three counters against four
output columns needs the trail.

**What the reviews caught that the implementers did not** (every one a case of something failing
*permissive* or claiming more than it proved):
- **T2:** elision was unranked (a 69-note bucket elided while a 2-note one showed); a pure section
  rename reported "350 notes implicated" on a **byte-identical document** — the likely shape of C5's
  re-bless; L3 deltas silently omitted when unavailable.
- **T3:** three **degrade-open** gaps — a partial baseline masqueraded as a first capture and bypassed
  the version check entirely (and a plain `bless` over deleted goldens exited 0, so the regression
  surface could shrink while CI stayed green); the synthesized empty `SelectionResult` made
  `quality/layer1.py`'s **W4 pass vacuously** (live 23 entries vs rebuilt 0); a baseline missing
  `meta.generatorVersion` was approvable without a bump.
- **T6:** a baseline stamped *newer* than the code was approved and then **silently downgraded**;
  `--approve --pack X` left the unselected half byte-non-reproducible while reporting clean; the
  **`note_affecting` document conjunct was wholly untested** (mutate it → all 67 tests still pass,
  reproduced by the orchestrator in the real repo); metric elision untested; the 480 s bucket never
  asserted the engine responded to it (a silent cap would have left all 916 cells green).

**DoD §14.5 / §14.6 — recorded honestly, not rounded up:**
- [~] **Corpus at every IR boundary — PARTIAL.** All 10 boundaries per cell at the pinned path shape;
  **24 of 60 cells** (2 packs). Mechanism PROVEN; completes at C8. **C-17.**
- [x] **`bless` + semantic diff report — PROVEN.** first-divergent-stage · note add/remove/move · L3
  metric deltas · never raw JSON (test-enforced, `test_report_never_emits_raw_json_for_a_large_diff`).
  Localizer proven discriminating (`test_first_divergent_stage_localizes_to_harmony_not_the_document`
  asserts the documents are equal *first*, so a document-differ fails it).
- [x] **generatorVersion-bump check — PROVEN.** Refusal reproduced empirically with zero writes; five
  fail-closed cases; accept-after-bump also asserted.
- [x] **Deliberate-change rehearsal documented — PROVEN.** Full record in the handoff block.
- [~] **Smoke matrix — content PROVEN (315 cells, Layers 1–2), "in CI" NOT MET.** No CI substrate
  exists in the repo. **C-18.**
- [x] **300-seed reference sweep clean — PROVEN.** 600 cells, default params.

**New caveats: C-17** (corpus 2/5 packs) · **C-18** (no CI; §14.6 unmet as written) · **C-19**
(pop_rock cannot reach the 480 s bucket — 356.57 s vs jazz's exact 480.00 s) · **C-20** (the corpus
never selects 18 of 49 patterns; **does not heal at five packs** — the cause is the pinned mood triple
plus `layersMax`, not the pack count). C-19 and C-20 both follow the **C-02 precedent**: a pinned
mechanism proven unreachable under other pinned rules.

#### Phase 8 — Chunk 1 — session 15 (`plans/sessions/SESSION_15.md`)

**Chunk 1 COMPLETE.** Foundational engine work, no packs / no tooling; **everything additive**
(pop_rock/jazz byte-identical — all whole-doc + humanizer + harmony goldens pass with NO fixture
edits). Waves: T1 (structural, alone) → T2 ‖ T4 → T3 → T5. Four gates green (**4758 tests**;
orchestrator-verified full suite after each task). **DoD §14.1 PROVEN.**

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Pipeline trace orchestrator `pipeline/trace.py` (`generate_trace → GenerationTrace`, every IR boundary incl. phrases post-5/6/7 separately); `generate_track` delegates, doc byte-identical | opus | done | 3e93514 |
| T2 | Feel profiles + `feelTable` (§3.4): `laidback`/`tight` in `feel.yaml`/`feel.py`; validate `InterpreterConfig.feel_table`; thread via `GenerationPlan → interpreter/stage → humanize` selection | opus | done | dcdbd2b |
| T3 | Authored extensions + P11 (§3.5): `resolve_token` extgroup parse (grammar→P5, §6.4→P11 loader); dressing passthrough guard (authored ext = draw-free); re-sort chord fixtures + zero-draw pin | opus | done | 0386b25 |
| T4 | Allowlist verify (§3.7): confirm Vibrato/AutoFilter match §3.7 (already present) + coverage test | sonnet | done | d64b0f7 |
| T5 | Whole-chunk 2-lens review + DoD 1 + close-out (→ C2) | orchestrator | done | 68720e6 |

**Per-task opus reviews** all APPROVE (T1 draw-order fidelity + byte-identity confirmed; T2 §3.4
verbatim + byte-identity; T3 P5/P11 split faithful + zero-draw pin discriminating + C-03 orthogonal;
T4 trivial). **Whole-chunk 2-lens review (fresh opus, C1 diff):** correctness/contract **CLEAN**
(additive/byte-identical, T1+T2 compose cleanly, determinism intact, `_split_extgroup` edge-cases
sound, C-03 untouched — one non-blocking nit: snapshot object-independence proven only for *changed*
phrases, harmless since frozen+read-only); test/DoD **PROVEN-WITH-GAPS → PROVEN** (one real gap: the
positive `feelTable` selection path was untested end-to-end — **closed** by T5 review-fix `68720e6`,
a discriminating `_run`-path test empirically verified to fail if selection were broken). **No new
CAVEATS** — every change is additive with no deviation from the pinned design.

**DoD §14.1 — PROVEN:**
- [x] **Feel profiles + `feelTable` selection** — `test_feel.py` `laidback`/`tight` field-for-field vs
  §3.4 (incl. the `laidback.snare` beat-class map); ≤25 ms cap fires on the new profiles
  (`test_new_profile_offset_over_cap_rejected`, non-vacuous); validation both directions
  (`test_interpreter_pack.py::test_{accepts_valid,rejects_unknown}_feel_table`); **selection proven
  end-to-end** (`test_humanizer.py::test_feel_table_selects_named_profile_over_swing_default`).
- [x] **Authored-extension parsing + P11 + pin-semantics** — `test_theory_chords.py` accept
  (`I7(#9)`/`bVI7(#11)`/multi-ext, with rendered symbol/roman) vs reject (bare+extgroup, malformed);
  P11 rejection fixtures P11-labelled on a genuinely §6.4-illegal `b9`-on-`maj7`
  (`test_progressions_pack.py`); **zero-draw pin** (`test_harmony_stage.py::test_authored_extension_
  slot_consumes_zero_dressing_draws` + the discriminating `_unextensioned_dom7_draws...` contrast).
- [x] **Allowlist additions** — Vibrato/AutoFilter match §3.7 exactly (pre-seeded Phase 7); pinned by
  `test_sound_engine_data.py::test_allowlist_growth_vibrato_autofilter`.

**Foundational deliverable for C2+:** `generate_trace → GenerationTrace` exposes every IR boundary
(phrases post-5/6/7 as separate snapshots, plus plan/song_form/harmony/arrangement/selection/
tempo_events/sound_design/document) — the substrate the C2 validators (W7 pre-humanizer grid, W8
note-count preservation), the C3 `--explain` log, the C4 golden corpus, and `bless` all consume.

**Deferred (low-priority, not blocking):** collapse the ~7 copy-pasted `_drive_full` test drivers onto
`generate_trace` (T1 left them — signatures differ; a later cleanup). Snapshot per-track object
independence for *unchanged* tracks is not asserted (harmless; revisit only if a future consumer
mutates a snapshot in place). `_split_extgroup` permits duplicate extensions (`I7(9,9)`) — §6.4 does
not forbid it; reference packs won't author it.

#### Phase 8 — Chunk 2 — session 16 (`plans/sessions/SESSION_16.md`)

**Chunk 2 COMPLETE.** The 3-layer validator suite (PHASE_8 §8.1), reading the C1 `GenerationTrace`.
New `src/trackgen/quality/` package only — **no packs, no CLI, no `calibration.yaml` on disk**;
`schema/validate.py` (V1–V8) byte-unchanged. Waves: T1 (foundation, alone) → T2 ‖ T3 ‖ T4 (disjoint
files) → warn/fail reconciliation → T5. **DoD §14.4 PROVEN.**

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | `quality/_common.py` helpers + Layer-1 mechanical **W1/W3/W4/W6/W8** + `layer2.py` stub + `suite.py::validate_pipeline` | opus | done | 2f2f5ca |
| T2 | Layer-1 substantial **W2** (device-policy evidence) / **W5** (regenerate, skippable) / **W7** (grid legality) into `layer1.py` | opus | done | 177afec |
| T3 | Layer-2 **L2-1** (chord-tone ratio, fail) / **L2-2** (voice crossing, warn) + `load_l2_thresholds` hook | opus | done | 177afec |
| T4 | Layer-3 `layer3.py` six metrics + `calibration.py` (`compute_bands` mean±2.5·pstdev, `calibration.yaml` shape, `load_calibration`) | opus | done | 177afec |
| — | **Warn/fail split** reconciliation: `validate_pipeline`=failures (V+W+L2-1), `pipeline_warnings`=L2-2; Layer-3 batch-only | opus | done | 177afec |
| T5 | Whole-chunk 2-lens review + review-fix (W2 branch fixtures + calibration read-back tests) + DoD 4 + close-out | orchestrator | done | (this commit) |

**Per-task + whole-chunk reviews.** T1 opus review APPROVE-WITH-NITS → **W3 rewrite** (HOLD notes
identified by the `"hold"` tag on `phrases_stage7`, exact, replacing a document onset-proximity band a
reviewer reproduced false-firing on −5-tick negative humanizer displacement; +regression test). T2/T3/T4
verified green in isolation; T2 flagged the L2-2/subsumption interaction that drove the warn/fail split.
**Whole-chunk 2-lens (fresh opus, full C2 diff): correctness/contract CLEAN, test/DoD PROVEN-WITH-GAPS →
PROVEN** — 2 gaps closed (W2 dropout + fill-outside-fill-bar branch fixtures now assert their specific
messages; calibration `.yaml` round-trip + L2 threshold-override tests). **L2-2 grain: user-ratified
CO-ATTACK** → **C-16** (warn-only). Four gates green.

**DoD §14.4 — PROVEN:**
- [x] **W1–W8 each with one violating fixture** (`test_quality_layer1.py`, all discriminating — fire own
  rule only, real pop/jazz trace clean): W1 lane (`_fires_only_w1`, midi≤71 so V4 stays clean) · W2
  device-policy — all four branches covered: crash-suppression, stray-midsection-crash, `breakdown`
  dropout-truncation (`_breakdown_dropout_truncation_fires_w2`, asserts the specific dropout message),
  fill-outside-fill-bar · W3 ending (non-degree-1 final, missing `final` tag, + `_negative_hold_
  displacement_does_not_fire` regression) · W4 density (`_starved_ornament`) · W5 determinism
  (`_disabled_by_default` + `_mismatch_fires_only_w5_when_enabled`) · W6 tag-vocab (`_stray_tag` +
  `_c11_provenance_tags_do_not_fire`, proves the strip is load-bearing) · W7 grid (`_offgrid_stage6` +
  `_reads_stage6_not_stage7`) · W8 note-count (`_note_count_mismatch`).
- [x] **L2-1 / L2-2 with per-pack thresholds from `calibration.yaml`** (`test_quality_layer2.py`): L2-1
  fail below 0.95/0.98 + beat-set asymmetry (bass beat-1 only vs comping beats 1&3), threshold-override
  via a temp `calibration.yaml`; L2-2 co-attack crossing warn + non-gating separation (in
  `pipeline_warnings`, absent from `validate_pipeline`). Bootstrap order §8.1: defaults gate in C2, the
  file is written by C3's `calibrate`.
- [x] **L3 metrics + band computation** (`test_quality_layer3.py`): `compute_metrics` six metrics
  (hand-checked note-density = notes/bars exact); `compute_bands` = mean±2.5·pstdev exact
  (`[2,4,4,6]→4±2.5√2`); `calibration.yaml` round-trip; **Layer 3 not wired into `suite.py`** (batch-only,
  asserted).
- [x] **V1–V8 unchanged and passing everywhere** — `git diff` on `schema/validate.py` empty;
  `validate_pipeline` subsumes `validate_document` (both `[]` on real traces); `test_validate.py` +
  every V-caller green in the full suite.

**Deliverables C3 consumes:** the warn/fail suite (`validate_pipeline` gate / `pipeline_warnings`), the
`Calibration`/`compute_bands` core + `calibration.yaml` shape (C3's `calibrate` writes it), `compute_
metrics`, and `load_l2_thresholds`/`load_calibration` (None→defaults today). See the handoff block.

**Deferred (low-priority, not blocking):** W2 fill-window is assumed ≤1 bar (`ticks//1920 == fill_bar`) —
safe for both reference packs; a multi-bar authored fill would need a spillover guard (latent, C-10
pattern). W3 drum-count sub-branches (missing kick / unexpected HOLD drum track) are logic-reviewed but
not fixtured. `_TICKS_PER_BAR = 1920` is hardcoded per-file (v1 4/4); fold into `_common` if it's touched
again. L3 folds all drum voice-tracks into one `drums` role band (intended per the `calibration.yaml`
shape). The sustain-overlap L2-2 sweep could be restored behind the warn/fail split (C-16; §8.1 Q4).

#### Phase 8 — Chunk 3 — session 17 (`plans/sessions/SESSION_17.md`)

**PLANNING — plan written, AWAITING USER APPROVAL; no implementation agent dispatched.** Authoring
tooling (PHASE_8 §9, proves DoD §14.7), all additive on the C1 trace + C2 quality suite. Serial task
order (D13-pinned: audition → linter → `--explain` → calibrate); all `opus`:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Audition CLI core (§9.1): `tooling/audition.py` + `@app.command("audition")`; `--section`/`--solo`/`--mute`/`--tempo`/`--out`/`--play`; filter upstream of `serialize`; minimal playground `?doc=` loader | opus | done | fb4f5d9 |
| T2 | Pack linter (§9.2): `packs/lint.py` collect-mode errors + 5 warning classes (variety/grid/unreachable/dangling/degeneracy) + `tooling/lint.py` + `@app.command("lint")` | opus | done | 86e9e35 |
| T3 | `--explain` selection log (§9.3): `pipeline/explain.py` collector + thread `explain=None` through the §9.3 draw sites; `--explain` flag on `audition`/`generate`; **byte-identity proof** | opus | done | d47d305 |
| T4 | `trackgen calibrate` (§9.3): `tooling/calibrate.py` batch → `compute_bands` → write `calibration.yaml`; reconcile the `load_l2_thresholds` shape mismatch (escalation valve); ref packs NOT committed | opus | done | 1d1fa59 |
| T5 | Whole-chunk 3-lens review + DoD §14.7 + close-out (→ C4) | orchestrator | done | 1954de9 |

Scope boundaries (out): golden corpus/`bless`/smoke matrix (C4); reference-pack refinement + listening
+ committing blessed `calibration.yaml` (C5); the three new packs (C6–C8). The two flagged risk points
both resolved cleanly: T2 collect-mode (accumulate what's cheap — reviewer confirmed all 13 `load_pack`
check sites mirrored, no fabrication/omission beyond the documented one-error-per-`model_validator`
limit); T4 L2-reconciliation (bounded local reader swap, no escalation, no C2 ripple, no CAVEAT).

**Whole-chunk 3-lens review** (fresh opus, full C3 diff): **correctness/determinism** — one BLOCKER
(audition drum sub-track filter, empirically reproduced) + `--explain` byte-identity, calibrate
determinism, L2 fallback, linter parity all verified CLEAN; **contract/DoD** — DoD §14.7 all four items
PROVEN, no C4/C5 creep, no CAVEAT; **test/code-quality** — tests discriminating, blocker + 3 minor
findings. Blocker + minors fixed in one cycle (`1954de9`), gates re-run green.

**DoD §14.7 — PROVEN:**
- [x] **Audition CLI** with `--section`/`--solo`/`--mute`/`--play` — `tooling/audition.py` +
  `cli.py audition`; filters the phrase list upstream of `serialize` (buses recompute); `--section`
  = `FormSection.id` tick span; `--solo`/`--mute` role-first then **drum sub-track by `phrase.track_id`**
  (blocker-fixed). Evidence (`test_audition.py`, 17): `test_unfiltered_equals_generate_track` (production
  byte-identity pop+jazz), `test_mute_last_reverb_sender_recomputes_buses` (discriminating bus recompute),
  `test_mute_tom_low_removes_fill_tagged_toms`/`test_solo_tom_low_isolates_track_with_its_notes`/
  `test_mute_snare_removes_fill_tagged_snares` (the blocker regression tests), `--play` monkeypatched.
- [x] **Pack linter** errors + all five warnings — `packs/lint.py::collect_pack_errors` (collect-mode,
  mirrors `load_pack`) + `collect_pack_warnings` (variety/grid/unreachable/dangling/degeneracy) +
  `tooling/lint.py` + `cli.py lint`. Evidence (`test_lint.py`): one discriminating base-vs-mutated
  fixture per warning class; multi-field error aggregation; `# expected-unreachable` silence; reference
  packs error-clean (variety-only warnings pop 23/jazz 15, reported not asserted-clean — C5 boundary).
- [x] **`--explain` selection log** — `pipeline/explain.py` (`ExplainCollector` + 7 records +
  `render_explain`) threaded `explain=None` through the §9.3 draw sites (template/pool-turnaround-final
  +survivors/dressing/pattern+survivors/device+no-ops/mutation-incl-none/tempo); walker per-tick + form
  optional/bar-count excluded (docstring-noted). Evidence (`test_explain.py`): byte-identity pop+jazz +
  2 discriminating forced-outcome tests; CLI stderr/stdout split. **Full suite green, zero fixture edits.**
- [x] **`trackgen calibrate` producing `calibration.yaml`** — `tooling/calibrate.py` batch →
  `pack_and_mood` group → `compute_bands` → `calibration_to_yaml_dict` + `safe_dump`; written shape
  matches §8.1 per-`(pack,mood)` `l2Thresholds`+`bands`. L2 reader reconciled (`load_l2_thresholds` →
  `load_calibration`, keyed by doc mood). Evidence (`test_calibrate.py`): round-trip via
  `load_calibration`, documented-shape spot-asserts, determinism, **reconciliation round-trip**
  (non-default threshold read by L2-1 end-to-end), report smoke test. Ref-pack `calibration.yaml` NOT
  committed (§8.1 bootstrap → C5).

**Deferred (low-priority, not blocking):** §9.3 calibrate report is observed-only (no vs-intent/budget
comparison — report-only, DoD met by the artifact); `--section` stale `start_tick`/`end_tick` +
empty-note phrases (spec-intended absolute-tick windowing; section×bus interaction untested); linter
one-error-per-`model_validator` (documented tool limit); `--explain` draw-free devices unlogged (feed-
bless consideration for C4); shared helpers not extracted (`tempo_window` dup, `_TICKS_PER_BAR` dup).

### Phase 7 — Sound design (chunk plan)

**Split into 2 chunks** (flip seam). The real `timbres.yaml` **schema**, its reference **content**,
the **stage** that reads `pack.timbres`, and the Serializer mix must all land in one commit — each
is strict and invalid under the other's schema, so swapping any one alone reddens `resolve_pack` +
the whole-document goldens (~4315 tests). Everything upstream of that flip (engine data, evaluation
model, new schema+validators) is new code wired to nothing and can be built + fully unit-tested in
isolation. Seam = **foundations (C1) vs the atomic flip + integration + whole-phase review (C2)**;
same shape as Phase 4 (theory+loader → stage+goldens+review).

#### Phase 7 — Chunk 1 — session 13 (`plans/sessions/SESSION_13.md`)

**Planning — plan written, AWAITING USER APPROVAL; no task dispatched.** New
`src/trackgen/sound/` package, all **unwired** (no `packs/`/`pipeline/`/reference-content edits;
four gates green throughout). Task list (T1 → T2 → T3 serial [T1/T2 share `sound/models.py`], then T4):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Engine data: `sound/allowlist.yaml` (fully expanded, D12) + `sound/mod_defaults.yaml` (§5.1 verbatim) + loaders + shared `MappingEntry` (curve enum, `exp⇒min,max>0`; inverted ranges legal) + tests | opus | done | b86be4e |
| T2 | Patch-evaluation model `sound/evaluate.py` (§3): linear/exp + `round3` half-even + inverted; `merge_mod` per-directive-key replacement (drums per-(directive,voice), empty-list disable); base-XOR-mod check; fixed brightness→attackHardness→space order + tests | opus | done | aeaf047 |
| T3 | Real `timbres.yaml` schema `sound/timbres.py` (`PitchedFlavor`/`KitFlavor`/`MixBlock`/`ReverbBus`/`MasterChain`) + TB1(standalone fn)–TB9 validators + one rejection fixture per rule class; **unwired** (stub `TimbresConfig`/`resolve_pack` untouched) | opus | done | acd87f4 |
| T4 | Whole-chunk 2-lens review (correctness/contract + test-quality/DoD) + DoD 2/3 + DoD 1 (C1 slice) + close-out (→ C2) | orchestrator | done | 8715ded |

**Chunk 1 COMPLETE.** 3 opus implementer tasks (T1→T2→T3 serial) + T4 whole-chunk 2-lens review;
per-task + whole-chunk review; four gates green (**4364 tests**). New `src/trackgen/sound/` package —
engine data + evaluation model + real `timbres.yaml` schema/TB1–TB9 — **all unwired** (`resolve_pack`,
`StylePack.timbres`, stub `packs/models.py::TimbresConfig`, `pipeline/`, and `styles/*/timbres.yaml`
untouched; the pipeline still runs the stub `sound_design` + `_STUB_MIX`). **DoD 2, 3 PROVEN in full;
DoD 1 PROVEN for its C1 slice** (validators + TB1 function + one rejection fixture per rule class).

**Whole-chunk 2-lens review (fresh opus): both CLEAN, no blocker/major.** Correctness/contract
**CONFIRM** — traced TB7 end-to-end LIVE through `TimbresConfig.model_validate` for the off-class §8
flavors (FM `piano`/`upright`, AM `organ_soft`): the `_engine_class` PolySynth→voice resolution +
allowlist + mod_defaults reshape all line up, so **§8 content will validate in C2 with no false
rejection AND a genuinely-illegal param is rejected**; §5.1 faithful (zero arbitration flags);
allowlist covers §8 by full dry-run; determinism + unwired-boundary confirmed. Test-quality/DoD
**PROVEN** (DoD 1-C1/2/3) — no vacuous tests; the load-bearing proofs (§5.1 transcription,
allowlist-covers-§5.1, half-even ties on 1/16 & 3/16, per-key/empty-list merge, fixed order, and the
**effective-mapping** base-XOR-mod) all present and discriminating.

**Review fixes (2 cycles, both tighten-to-design — NO caveats):** (1) **D4** — `KitMod` closed to
`{brightness, space}`; a drum `attackHardness` override now rejects (`extra="forbid"`), honoring D4
literally while still ⊆ TB7's set (+`test_tb7_rejects_drum_attack_hardness_mod`). (2) **§4.2 send-XOR
(`8715ded`)** — `mix.sends.reverb` was exempt from base-XOR-mod (only from the allowlist path check);
new `_check_send_xor` rejects a flavor/voice carrying BOTH a fixed `reverb` send and a space mapping
onto that path, per §4.2 ("base send omitted when a mapping targets it"), on both the pitched and
per-voice drum paths (+`test_tb7_rejects_fixed_send_with_space_mapping`). §8-safe.

**No new CAVEATS.** Both fixes honor the pinned design (D4, §4.2/§3.3) rather than deviate from it.

**DoD (§13) — Chunk 1 targets 2, 3 (full) + 1 (C1 slice) — all PROVEN:**
- [x] §13.2 **Engine data PROVEN** (T1, `b86be4e`) — `sound/mod_defaults.yaml` transcribes §5.1
  field-for-field (`test_sound_engine_data.py`: `_{bass,comping,pads,drums}_field_for_field` assert
  every `{param,min,max,curve}`); `sound/allowlist.yaml` (D12) seeded fully-expanded and
  coverage-proven (`test_mod_defaults_params_legal_for_reference_class` — every mapped param legal for
  its reference class; a dropped path flips it) + spot-verified against §8 recipes + all 3 committed
  fixtures; MappingEntry caps (curve enum; `exp⇒min,max>0`; inverted legal) with rejection fixtures.
- [x] §13.3 **Evaluation PROVEN** (T2, `aeaf047`) — `sound/evaluate.py`: both curves
  (endpoints/midpoint/inverted), `round3` half-even (genuine 1/16 & 3/16 ties), per-directive-key
  `merge_mod` (replace / empty-list-disable / absent-keeps-default / drum per-`(directive,voice)`),
  `assert_base_xor_mod`, fixed brightness→attackHardness→space order + mix-block routing + autovivify;
  reproduces the §9.1 anchors (snare 3.67; bass 1514.763). 16 tests.
- [x] §13.1 **Loader validators + rejection fixtures PROVEN for the C1 slice** (T3, `acd87f4` +
  review fix `8715ded`) — `sound/timbres.py` real schema (`PitchedFlavor`/`KitFlavor`/`KitVoice`/
  `MixBlock`/`ReverbBus`/`MasterChain`/`TimbresConfig`, frozen+strict) + **TB1–TB9**, one non-vacuous
  rejection fixture per rule class (`test_timbres_schema.py`, 19); TB1 = standalone
  `check_flavor_completeness` (dangling + orphan); TB7 checks the **effective** (defaults-merged)
  mapping incl. the send-XOR. **The wired "both reference files load clean" + live TB1 vs
  `interpreter.yaml` is C2.**

**C2 handoff notes** (verified, carry forward):
- **Reuse, don't re-derive:** the C2 `sound_design` stage needs the identical directive-name
  normalization (`attack_hardness`→`attackHardness`) + drum `(directive,voice)` keying that live as
  module-private helpers in `sound/timbres.py` (`_pitched_override`/`_pitched_defaults`/
  `_drum_defaults`/`_drum_override`) — reuse them (extract to a shared spot) to avoid divergence. The
  `apply_directives` `directive_values` keys already match `timbreDirectives` camelCase (pre-aligned).
- **`apply_directives` working-dict convention:** the stage builds `{**options, "mix": mix_block}`,
  runs `apply_directives`, then splits back via `result.pop("mix")`; top-level `"mix"` is reserved
  (no whitelisted class emits an option named `mix` — safe).
- **InstrumentPatch extra-key (Q9a, acceptable):** kit/pitched patches reuse the PHASE_1
  `InstrumentPatch` (a `DocumentModel`, `extra="ignore"`), so a stray top-level patch key is silently
  dropped (not applied) — non-semantic, no TB rule mis-fires. C2 may optionally wrap it with
  `extra="forbid"` at the timbres boundary; not required.
- **round3 vs §9 display:** pop bass `envelope.attack` golden is `round3=0.005` (§9.1's "0.0051" is a
  >3-decimal readability display — §9 fixtures assert full round3).



**T1 done** (`b86be4e`): `src/trackgen/sound/` package created — `models.py` (`MappingEntry`),
`allowlist.py`+`allowlist.yaml`, `mod_defaults.py`+`mod_defaults.yaml` (§5.1 verbatim), 14 tests. All
unwired; four gates green (**4329 tests**). Per-task opus review: no blockers — §5.1 transcribed
field-for-field (zero arbitration flags); allowlist coverage **programmatically verified** against
§5.1 + §8.1/§8.2 recipes + all three committed fixtures + the §4.7 riser recipe (zero missing paths
→ C2's TB3/TB4/TB7 won't false-reject); rejection fixtures non-vacuous. Envelope-expansion decision
(handoff, confirmed intended per §5.2/D12): `envelope.*`→attack/decay/sustain/release/attackCurve,
`modulationEnvelope.*`→attack/decay/sustain/release; classes seeded = the 18 §5.2 names only
(DuoSynth/PluckSynth/unused effects enter by amendment when first used).

**T2 done** (`aeaf047`): `sound/evaluate.py` — `round3`/`evaluate_mapping`/`merge_mod`/
`assert_base_xor_mod`/`apply_directives` + `get_by_path`/`set_by_path`; 16 tests. Reproduces the
§9.1 anchors (snare `noise.playbackRate` **3.67**; bass `filterEnvelope.baseFrequency` **1514.763**,
matching §9.1's 1-decimal 1514.8). Per-task opus review clean; added an autovivify test (omitted
`sends` → `set_by_path` creates it). Four gates green at commit (fast gates + T2 file; full suite
agent-verified **4344**, re-confirmed at T3). **C2 handoff notes:** (a) the stage converts the
T1 `ModDefaults`/flavor `mod` pydantic models to the dict shapes `merge_mod` expects — rename
`PitchedModDefaults.attack_hardness`→`"attackHardness"`, flatten drums to `(directive,voice)` keys,
then per drum voice slice `{d: merged[(d,voice)]}` before `apply_directives` (which is `str`-directive
keyed); (b) `apply_directives` uses a single working dict `{**options, "mix": mix_block}` — split back
via `result.pop("mix")`; the top-level `"mix"` key is reserved (no whitelisted class emits an option
named `mix` — safe, noted); (c) pop bass `envelope.attack` golden is `round3=0.005` (§9.1's "0.0051"
is a >3-decimal readability display, not a divergence — the §9 fixtures assert full round3).

**Targets DoD 2, 3** (full) + **DoD 1** (partial: validators + TB1 function + one rejection fixture
per rule class; "both reference files load clean" is the wired check → C2). **Out of scope:** any
`resolve_pack`/`StylePack.timbres`/stub-`TimbresConfig`/`pipeline/`/reference-`timbres.yaml` edit;
the real `sound_design` stage + `SoundDesign` type; §9 stage goldens; property matrix; zero-draw
determinism; whole-doc re-bless; riser content/wiring (schema only expresses it, §4.7 dormant).

#### Phase 7 — Chunk 2 — session 14 (the flip + integration + whole-phase)

Author the full real `styles/{pop_rock,jazz}/timbres.yaml` (complete §8 abridged entries); swap
`resolve_pack` to the new loader (TB1 live vs `interpreter.yaml`) + retype `StylePack.timbres`;
write the real `sound_design(plan, pack) → SoundDesign` stage (§7); wire orchestrator + Serializer
(consume `SoundDesign` for channel/sends/`buses`/`master`; **delete** `_STUB_MIX`/`_MASTER_EFFECTS`/
stub-`buses` + `pipeline/stubs.py::sound_design` + the stub `TimbresConfig`); re-bless both
whole-document goldens (**dedicated commit**, arbitration rule 3); §9.1/§9.2 stage goldens
field-for-field (every evaluated patch/channel/send/bus/master vs full-precision recomputation);
zero-draw determinism (`sound` stream shim = 0 draws, repeated-run identity); property matrix (both
packs × supported moods × every declared flavor combo → whitelist/allowlist/V7/sends→reverb/
volumeDb≤6/pan∈[−1,1]/bus-decay-in-range/master-ends-Limiter); whole-PHASE 4-lens review; **full
DoD 1(complete)/4/5/6/7/8(user audition)/9** + §12 amendment audit. **DoD 1, 4, 5, 6, 7, 8, 9.**

**Plan approved (`plans/sessions/SESSION_14.md`); T1+T2 done — next is T3 (re-bless) then T4.** Task
list (T1 → T2 → T3 → T4 → T5; T3/T4 run serially not parallel — shared working tree + the re-bless is
a dedicated-commit checkpoint); all implementer tasks `opus` (none trivial):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Stage `sound/stage.py` (`sound_design → SoundDesign`) + shared-helper extraction (`sound/_merge.py`) + real reference content authored as a **test fixture** (`tests/fixtures/timbres/*.yaml`) + §9.1/§9.2 stage goldens — **all unwired, green** | opus | done | fa18869 |
| T2 | The atomic flip: content → `styles/`; `resolve_pack`→real `TimbresConfig` + TB1 live + `StylePack.timbres` retype; orchestrator + Serializer consume `SoundDesign`; delete `_STUB_MIX`/`_MASTER_EFFECTS`/stub-`buses`/`stubs.py::sound_design`/stub `TimbresConfig`; **xfail** the 2 whole-doc reserialize goldens | opus | done | f773bb1 |
| T3 | Re-bless both whole-document goldens (**dedicated commit**, arbitration rule 3); remove xfails; independent-arbiter verify V1–V8 + §9 sound anchors + note/timing byte-invariance | opus | done | 0b56ad9 |
| T4 | DoD-6 property matrix (`test_phase7_property.py`) + zero-draw pipeline determinism (`test_sound_determinism.py`) | opus | done | ab7292e |
| T5 | Whole-**phase** 4-lens review (C1+C2) + full DoD 1/4/5/6/7/8/9 + §12 amendment audit + close-out (→ Phase 8) | orchestrator | done | (close-out) |

**Chunk 2 COMPLETE — Phase 7 COMPLETE.** T1 (stage+content+§9 goldens, unwired) → T2 (the atomic
flip) → T3 (re-bless, dedicated) ‖ T4 (property+determinism) → T5 (whole-phase review + close-out).
The pipeline now runs the **real** stage 8 (sound design) end to end; only note/timing content is
unchanged (invariant 2). Four gates green (**4725 tests**, 0 xfailed; orchestrator-verified full suite
+ each per-task gate). **DoD 1(complete)/4/5/6/7/8/9 PROVEN — full §13 DoD complete.**

**Whole-PHASE 4-lens review (fresh opus, C1+C2 together) — no blocker, no major:**
- **Correctness CLEAN** — reproduced both §9 examples field-for-field by running `sound_design`; zero
  `sound`-stream draws; no shared-mutable-state bug across the matrix (`apply_directives` deep-copies,
  `dict(mix.sends)` copied); both packs regenerate V1–V8 clean; validators fire on crafted malformed
  timbres (base-XOR, send-XOR, exp-positivity, off-class default, TB4/TB5).
- **Contract COMPLIANT** — every schema field/whitelist/TB rule/evaluation semantic/stage shape/engine
  file/§8 value matches pinned text; **all six §12 amendments present + consistent** (audited below);
  only deviations are the logged caveats (C-13, C-14, C-15).
- **Test/DoD PROVEN** — full DoD table: every item 1–7,9 has a discriminating proving test (independent
  §9 recompute; genuine half-even ties; 344-doc exhausted matrix with a non-vacuity guard; counting-RNG
  zero-draw shim at the real seam; per-rule discriminating rejection fixtures + live TB1).
- **Code-quality GOOD-WITH-NITS** — `_merge.py` extraction clean (single-sourced), stub fully removed,
  import-cycle handling minimal/idiomatic, comments explain *why*.

**Review fixes (orchestrator, trivial/doc — 0 code-behavior change):** (1) `evaluate.py` module
docstring corrected (it named `get_by_path`/`set_by_path` as used by the TB path checks — they use
`leaf_paths`+allowlist instead). (2) **C-15** logged (§5.2's `envelope.*` "five fields" prose is
self-contradictory; `allowlist.yaml` resolves it to the concrete ADSR+attackCurve set — a doc-prose
imprecision, C-08 pattern). **No correctness/contract finding rose to a fix** (all lenses CLEAN/
COMPLIANT/PROVEN). **New caveats this phase: C-13 (§9.2 sample, resolved-with-signoff), C-14
(TrackSound.midi gap-fill, open), C-15 (§5.2 envelope.* prose, open).**

**Deferred notes (low priority, logged for a future session / Phase 8 — NOT blocking):**
- **Perf:** `TimbresConfig._check` calls `load_allowlist()`/`load_mod_defaults()` (YAML reads) on every
  validation, and `sound_design` reloads `mod_defaults` per call — a module-level cache would remove
  redundant reads across the 344-doc matrix. Correctness-neutral.
- **Coverage:** TB2/TB8 have one rejection fixture each (DoD-1 satisfied) but untested sub-clauses
  (TB2 non-PolySynth-carries-voice, voice-whitelist, maxPolyphony range; TB8 `returnFilterHz>0`,
  preDelay ordering) — cheap per-clause fixtures could be added.
- **Simplification:** the pitched role→bank triple is re-listed across `timbres._check` / `_check_sends`
  / `stage.sound_design`; `_check_sends` could fold into `_check` (defensible as-is under the
  one-helper-per-TB-rule convention).

**DoD (§13) — full checklist:**
- [x] **1 Loader** (C1 slice `acdf...`→C2 complete) — `test_timbres_schema.py` one discriminating
  rejection fixture per TB1–TB9; `test_timbres.py` both reference `styles/*/timbres.yaml` load clean via
  `resolve_pack`; **TB1 live** vs `interpreter.yaml` (declared==recipe sets, both directions rejected).
- [x] **2 Engine data** (C1, `b86be4e`) — `sound/mod_defaults.yaml` §5.1 field-for-field; `sound/allowlist.yaml`
  fully expanded (D12), coverage-proven; MappingEntry caps + validator rejections.
- [x] **3 Evaluation** (C1, `aeaf047`) — `test_sound_evaluate.py`: both curves endpoints/midpoint/inverted;
  round3 genuine half-even ties; per-key merge (empty-disable + drum `(directive,voice)`); base-XOR reject;
  fixed brightness→attackHardness→space order.
- [x] **4 Stage goldens** (C2, `fa18869`) — `test_sound_stage_goldens.py`: both §9 examples field-for-field
  vs in-test full-precision recompute (full options objects + channels/sends/bus/master).
- [x] **5 Determinism** (C2, `ab7292e`) — `test_sound_determinism.py`: `CountingRng` → 0 `sound`-stream draws
  both examples; `generate_track` repeated-run byte-identity.
- [x] **6 Property matrix** (C2, `ab7292e`) — `test_phase7_property.py`: **344 docs** (pop 11 moods × 24 combos
  + jazz 10 × 8), full flavor cross-product exhausted; whitelist/allowlist/V7/send→reverb/volumeDb≤6/
  pan∈[−1,1]/bus-decay-in-range/master-ends-Limiter; non-vacuity guard (6 classes/688 PolySynth/3176 sends).
- [x] **7 Serializer integration** (C2, `f773bb1`+`0b56ad9`) — stubs deleted; both milestone docs re-blessed
  through the real Phases 2–7, V1–V8 clean, notes byte-identical (pop 2790/jazz 1275); committed goldens.
- [x] **8 Listening checklist** — **CLOSED (user-confirmed 2026-07-18)**. Automated portion proven: both
  docs load in the Phase-1 playground, all tracks present, kick/snare/bass centered, cymbals off-center,
  pads wide, reverb on snare/comping/pads, kick/bass dry, master ends in Limiter (no clip guaranteed
  structurally by −1 dBFS limiter). User audition confirmed the Q1 loudness/mix ear-check and the mood
  A/B (brightness/space) read as intended.
- [x] **9 Amendments** (§12) — all six present + consistent (audit below).

**§12 amendment audit (all present + consistent):** (1) PHASE_1 §7 Q4 `timbres.yaml` schema resolved;
(2) PHASE_1 §3.6 allowlist annotation (D12/§5.2); (3) PHASE_2 §7.3 directive-consumption annotations;
(4) PHASE_5 §8.3/§8.4 Serializer/stub replacement — **stubs actually deleted** (`_STUB_MIX`/`_MASTER_EFFECTS`/
`pipeline/stubs.py`/stub `TimbresConfig` gone, grep-clean); (5) PHASE_6 §9 Q2 riser recipe pinned §4.7
(dormant, no v1 pack opts in); (6) ROADMAP §2 decisions-log row for the Phase-7 model.

**T1 done** (`fa18869`): new `sound/stage.py` (`sound_design(plan, timbres) → SoundDesign`, §7) +
shared helpers extracted to `sound/_merge.py` (re-imported by `timbres.py`, behavior byte-identical) +
full real reference content authored as **test fixtures** (`tests/fixtures/timbres/{pop_rock,jazz}.timbres.yaml`,
TB1–TB9 clean, every declared flavor) + §9.1/§9.2 field-for-field stage goldens (in-test full-precision
recompute). **All unwired** — `resolve_pack`/`pipeline`/`styles/*/timbres.yaml` untouched; four gates
green (**4377 tests**). Per-task opus review **APPROVE-WITH-NITS** (stage faithful to §7/§3; extraction
behavior-preserving; content matches §8; goldens real & discriminating). **Arbitration C-13** (user
sign-off 2026-07-18): §9.2 jazz upright `envelope.attack` printed sample mis-used brightness 0.333 as
the exp exponent (param maps attackHardness 0.32) → faithful **0.018**; §9.2 amended, engine unchanged.
**Review nit carried to T2:** `sound_design(plan, timbres)` omits the reserved `sound` seed stream that
§3.4/DoD-5 reference — T2 wiring resolves how the DoD-5 zero-draw shim asserts against it (thread a
counting-injectable `sound` Rng, or assert at stream construction). **C2 handoff facts** for T2: content
files are authored to move **verbatim** into `styles/`; the extracted `_merge.py` public helpers
(`pitched_defaults`/`pitched_override`/`drum_defaults`/`drum_override`/`engine_class`/`leaf_paths`) are
the stage's + loader's shared normalization.

Seam rationale: the flip is a single-file-set knot (real content is invalid under the stub loader and
vice-versa; swapping the loader breaks the stub `sound_design` + whole-doc goldens), so T2 is atomic
and lands with the 2 reserialize goldens xfailed, re-blessed in the dedicated T3 commit (Phase-6-C3
precedent). T1 stays green by keeping the content in a **test fixture** (not `styles/`) so
`resolve_pack` is untouched until T2. T3 ‖ T4 touch disjoint files, both depend only on T2.
**§9 tables are an arbitration-risk surface** (C-09 precedent): T1/T3 recompute field-for-field and
xfail+escalate on any divergence beyond the known pop-bass `0.005`/`0.0051` display case.

### Phase 6 — Transitions, variation & humanization (chunk plan)

**Split into 3 chunks** (phase too large for one session; PHASE_6 D1 stage seam = note-structural vs
performance-rendering). Seams:

#### Phase 6 — Chunk 3 — session 12 (`plans/sessions/SESSION_12.md`)

**Planning — plan written, AWAITING USER APPROVAL; no task dispatched.** FINAL chunk of Phase 6:
wiring + milestone + whole-phase. The stage-6 (`transitions/`) and stage-7 (`humanize/`) engines exist
and are tested but are **not yet wired** into the pipeline. Task list (T1 → then T2 ‖ T3 → T4 → T5):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Wire real stages into orchestrator (delete `transitions`/`humanize` stubs) + thread `tempoEvents` → serialize (`header.tempos=[base]+events`) + crash `_STUB_MIX`/stub-timbre (midi 84)/guard removal + unit tests; **xfail** the whole-doc goldens for T2 | opus | done | 6c05caf |
| T2 | Re-bless both whole-document goldens (**dedicated commit**) via `_regen_milestone_fixtures.py`; verify V1–V8 + §9.4 anchors + §7.3 facts + jazz **40-entry** tempo map; independent-arbiter posture | opus | done | c6e81fc |
| T3 | Whole-phase property matrix (DoD 9): both packs × supported moods × [None,180,240] × 25 seeds through the wired pipeline → §11.9 checks + confirm P1-latent & C-10 unreachable | opus | done | 373cfdc, 8fa46ac |
| T4 | Milestone regen + Phase-1 playground audition + §11.10 checklist (**USER AUDITION GATE**, DoD 10) | opus | done | — |
| T5 | Whole-PHASE 4-lens review (all 3 chunks) + full §11 DoD 1–11 + DoD 11/§10 amendment audit + close-out (→ Phase 7) | orchestrator | done | b3756ba |

**Chunk 3 COMPLETE — Phase 6 COMPLETE.** T1 (wire) → T2 ‖ T3 → T4 (audition) → T5 (review + close-out).
Fixtures re-blessed through the real stages 6+7; the pipeline runs the real Transition engine +
Humanizer end to end (only `sound_design` remains a stub → Phase 7). **4-lens whole-phase review across
all 3 chunks — no blocker, no major.** Four gates green (**4315 tests**).

**T4 (DoD 10) — CLOSED.** Both re-blessed fixtures load in the Phase-1 playground (all instruments
whitelisted incl. the new `crash`=MetalSynth; the 40-event jazz ritard schedules as a real tempo ramp
via the tick→seconds walk). Automated portion PROVEN (stubs deleted, real stages wired, fixtures
re-serialize identically). The §11.10 ear-check (fills→crash, ritard reads as slowing, pop ending
rings+releases, no byte-identical bar, swing survives ritard) — user-confirmed 2026-07-18.

**DoD (§11) — full 1–11 PROVEN** (chunks 1–3 together):
- [x] **1 Loader** (C1, `22bd551`) — `test_transitions_pack.py`: TR1–TR7 each with a code-matched
  rejection fixture; both reference packs load clean; fill windows cached; PT12 enforced.
- [x] **2 Feel data** (C2, `0ad958d`) — `test_feel.py`: `feel.yaml` field-for-field §5.3; the three
  validator caps (offset ≤25 / jitter ≤10 / |accent| ≤0.05) each with a code-matched rejection.
- [x] **3 Device narratives** (C1, `492935f`) — `test_transitions_goldens.py`: exact draw counts pop
  14/38/9 & jazz 10/32/11 via counting shims; fired-op lists verbatim incl. the 4 no-ops.
- [x] **4 Rendering goldens** (C1, `492935f`) — pop fill bar 3 note-for-note; crash+kick with/without an
  existing kick; one mutated unit per operator class; HOLD both examples.
- [x] **5 Humanizer** (C2, `b46a08f`/`ec2cccf`) — `test_humanizer.py` swing/offset/tri/accent/width/legato;
  `test_humanizer_goldens.py` jazz head-1 bar-0 pre-jitter excerpt exact.
- [x] **6 Ritard** (C2, `8f0193a`/`ec2cccf`) — `test_ritard_goldens.py` 39-event table (11 anchors +
  endpoints exact); `test_ritard.py` monotone/floor/tag-bounds/cold-fade-zero/fade==cold alias.
- [x] **7 Determinism** (C1+C2, `492935f`/`ec2cccf`) — repeated-run identity through both stages;
  counting-shim per-stream/sub-stream draw counts; per-unit + per-bar isolation; humanizer note-count
  preservation both examples. Whole-pipeline total re-pinned pop **10277** / jazz **5304** (C3 `6c05caf`,
  decomposed against every per-stage golden).
- [x] **8 Synthetic fixtures** (C1, `492935f`) — `test_transitions_fixtures.py`: stop-heavy odds pack
  (§3.4), breakdown form (§3.5 dropout), rung-restricted fill banks (§3.3 fallback both directions).
- [x] **9 Property matrix** (C3, `373cfdc`+`8fa46ac`) — `test_phase6_property.py`: **1575 fully-wired
  documents** (2 packs × 21 pack-moods × 3 lengths × 25 seeds) — all 7 §11.9 invariants (fills in legal
  bars, no groove in rendered window, crash suppression [N/A — postchorus/breakdown never entered, asserted
  explicitly], no note <0/past-end, non-drum midi untouched by BOTH stages, backbeat snare protected,
  V1–V8). **P1 latent: 0 trips** (drums active at every device site); **C-10: 0 V3 violations**.
- [x] **10 Milestone** (C3) — automated portion PROVEN (`c6e81fc` re-bless; `test_whole_document_goldens.py`
  re-serialize identically; stubs deleted; playground-loadable verified). **§11.10 listening checklist
  CLOSED** (user-confirmed 2026-07-18).
- [x] **11 Amendments** (C3, this session) — all 10 §10 amendments verified present + consistent (ROADMAP
  §2/§3/§4; PHASE_1 §4 recap / §4.5 tags / Q5 / §6 layout; PHASE_5 PT12 / §8.2 crash-1440 / §8.1 stub
  replacement / §8.3 tempoEvents; PHASE_2 §7.2 dynamicsRange).

**New CAVEATS this session:** **C-12** (§3.7 entry-crash velocity has no floor → latent velocity-0
`PhraseNote` when a pack sets `crash.velocity` lo=0 entering an energy-0 section; unreachable in v1 —
reference packs lo 0.55/0.40; closing it changes pinned §3.7/TR1, sign-off). C-11 (C1) unchanged/open.

**T1 done** (`6c05caf`): real stages 6/7 wired into `orchestrator.py`; `tempoEvents` threaded
`humanize → serialize` (`header.tempos=[base]+events`); crash serializes (`_STUB_MIX["crash"]`, crash
timbre midi 84 in both packs, `sound_design` guard removed); `test_total_draw_count` re-pinned
pop 18→**10277** (18 base + 61 stage-6 + 10198 stage-7) / jazz 163→**5304** (163 + 53 + 5088), each
summand cross-checked against a committed per-stage golden. Per-task opus review clean (no blockers).
**T2 done** (`c6e81fc`, dedicated re-bless): both `fixtures/*.milestone.trackdoc.json` regenerated
through the wired stages; T1 xfails removed; four §9.4/§9.5 anchors updated to the humanized values
(each documents why). Independent-arbiter verified: 29/29 checks — V1–V8 clean both docs; pop 1-entry
tempo map (cold); jazz **40-entry** map (base 69 + 39 ritard, first (115440,68.5), last (122760,45.5),
monotone non-increasing, no anchor divergence from §7.2); C5 ceiling intact; HOLD endings present;
no byte-identical repeated section. Fixture deltas: tracks pop 7→11 / jazz 6→8 (fills add tom/crash
voices), notes pop 2856→2790 / jazz 1288→1275 (mutation + fill windows + HOLD). **T3 done**
(`373cfdc` + nit-fix `8fa46ac`): `tests/test_phase6_property.py` drives the fully-wired `generate_track`
across **1575 documents** (2 packs × 21 pack-moods × 3 lengths × 25 seeds) + 3 sanity/reachability
tests; all §11.9 invariants hold. **P1 latent: 0 trips** (drums active at every device site);
**C-10: 1575 docs, 0 V3 violations**. Crash suppression N/A (postchorus/breakdown never entered) —
asserted explicitly and non-vacuously. Per-task opus review: no blockers, non-vacuousness
empirically re-probed across all 1575 docs; nit-fix closes the DoD-9 both-stages midi check directly.

Ordering: **T1 → (T2 ‖ T3) → T4 → T5** (T2 fixtures & T3 new property test are disjoint files, both
depend only on T1's wiring). **Targets DoD 9, 10, 11** + full §11 1–11 sign-off. Out of scope: any
stage-6/stage-7 internal change (frozen; C1/C2 goldens must stay green), `sound_design` mix (Phase 7).

- **Chunk 1 — SESSION_10** (`plans/sessions/SESSION_10.md`): **stage 6, the Transition engine.**
  `transitions.yaml` schema/loader (TR1–TR7) + PT12 + reference content + fill windows (§4); the full
  §3 stage — 6a HOLD ending, 6b boundary taxonomy/device-assignment/fill-select-size-render/stop/
  dropout/crash, 6c mutation (5 operators); device+rendering+mutation goldens (§7.1/§7.2), synthetic
  fixtures, stage-6 determinism + property subset. Adds tags `fill`/`crash`/`var`/`hold`; adds `crash`
  to the producer-side voice→track map + drum track order. **Targets DoD 1, 3, 4, 8** + stage-6 slices
  of 7/9. Out of scope: all of stage 7; pipeline wiring; Serializer crash emit/mix + stub crash timbre;
  whole-doc re-bless; full property matrix + DoD 1–11 sign-off (C2/C3).
- **Chunk 2** — stage 7, the Humanizer: `feel.yaml` data+loader+validator (§5.3), the §5 engine (swing
  §5.2, offset maps §5.3, `tri` timing jitter §5.4, velocity accent+jitter §5.5, bass legato §5.6),
  ritard tempo curve §5.7 (Friberg–Sundberg, 39-event jazz golden), RNG §5.8; humanizer units + jazz
  head-1 pre-jitter excerpt golden + note-count-preservation. **DoD 2, 5, 6** + humanizer slice of 7.
- **Chunk 3** — wiring + milestone + whole-phase: thread `tempoEvents` orchestrator→serializer
  (`header.tempos = [base] + tempoEvents`), delete the stubs + call the real stages, add `crash` to
  Serializer `_EMIT_ORDER`/`_STUB_MIX` + a stub-timbres `crash` entry, re-bless both whole-document
  goldens (fills/crashes/humanization/jazz 40-entry tempo map now change the output), the §11.10
  milestone listening check, the whole-phase property matrix (DoD 9: V1–V8, crash suppression, C5
  ceiling under both stages, backbeat protection), whole-PHASE 4-lens review, full §11 DoD 1–11, DoD 11
  amendment audit (§10). **DoD 9, 10, 11.**

#### Phase 6 — Chunk 2 — session 11 (`plans/sessions/SESSION_11.md`)

**Planning — plan written, AWAITING USER APPROVAL; no task dispatched.** Stage 7, the
note-count-preserving Humanizer (`humanize(phrases, form, plan) → (Phrase[], tempoEvents)`).
Task list (T1→T2→T3→T4 serial, then T5); all implementation opus, disjoint from stage 6 / pipeline:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | `humanize/feel.yaml` (§5.3 exact) + loader + validator (caps offsets ≤25ms / jitter ≤10ms / \|accent\| ≤0.05, rejection fixture per class) | opus | done | 0ad958d |
| T2 | Humanizer engine (§5.1–§5.6, §5.8): beat classes, swing, offset maps, `tri` timing jitter, velocity accent+jitter, bass legato, op order + terminal rounding + clamps + re-sort, per-(role,bar) RNG | opus | done | b46a08f |
| T3 | Ritard renderer (§5.7): Friberg–Sundberg curve → sampled/dedup'd `Tempo[]` (humanize 2nd return); cold/fade → []; fade aliases cold | opus | done | 8f0193a |
| T4 | Goldens (independent arbiter): jazz head-1 bar-0 pre-jitter excerpt §7.2 + 39-event ritard table §7.2 + stage-7 determinism/draw-counts + note-count preservation. **Ritard table = arbitration-risk surface (xfail+escalate, C-09 precedent).** | opus | done | ec2cccf |
| T5 | Whole-chunk 2-lens review + DoD 2/5/6 + humanizer slice of 7 + close-out | orchestrator | done | f71dffa |

**Chunk 2 COMPLETE.** 4 opus tasks (T1→T2→T3→T4 serial) + T5 whole-chunk 2-lens review; per-task
+ whole-chunk review; four gates green (**2734 tests**). **DoD 2+5+6 + humanizer slice of 7 PROVEN.**
New `src/trackgen/humanize/` package implements PHASE_6 §5 exactly: `humanize(phrases, form, plan) →
(Phrase[], tempoEvents)` (feel loader/validator §5.3 → engine §5.1–§5.6/§5.8 → ritard §5.7). **T4
(independent arbiter): ZERO divergences** — every §7.2 value reproduced verbatim (head-1 bar-0
pre-jitter, full 39-event ritard table incl. all 11 anchors 68.5…45.5, endpoints; bass legato
960→912) → no §7 amendment (like C1's T4; unlike C-09). Whole-chunk 2-lens review: correctness/contract
**APPROVE** (engine matches §5 clause-by-clause; two reviewers independently recomputed RNG anchors +
the full ritard curve; invariants 2/4/5 hold), test-quality/DoD **APPROVE-WITH-NITS** (DoD 2/5/6
PROVEN; DoD-7 slice had a non-discriminating isolation test). Review fixes (f71dffa): the isolation
test replaced with the literal DoD-7 "regenerate one bar in isolation" test — **empirically verified
to discriminate** (a per-role RNG fails the bar-N-isolated == bar-N-full equality; the pinned
per-(role,absBar) seeding passes it); + a direct §5.8 seed-anchor test; + deleted a redundant
and-of-4 test.

**No new CAVEATS.** Two design points resolved (decisions, not deviations — no §5 value changed):
(1) **bass legato is track-level** (§5.6 "same track's next attack" + "the final whole note (no
successor)" — spans all bass phrases; only the globally-final bass note exempt; caught + fixed in T2
review). (2) **feel-table selection uses the swing-derived default** (`plan.swing` → straight/swung)
since `humanize(phrases, form, plan)` takes no pack and no v1 pack declares the PHASE_8 `feelTable`;
a future `feelTable` selector would need a signature change (noted in `humanize/stage.py`).

**DoD (§11) — Chunk 2 targets 2, 5, 6 + humanizer slice of 7 — all PROVEN:**
- [x] §11.2 **Feel data PROVEN** — `humanize/feel.yaml` matches §5.3 field-for-field; validator caps
  (offsets ≤25ms / jitter ≤10ms / |accent| ≤0.05) each with a non-vacuous rejection fixture +
  load-wrapper tests (`tests/test_feel.py`, 13). Commit `0ad958d`.
- [x] §11.5 **Humanizer PROVEN** — swing (offbeat-only, both subdivisions, gap-preserving stretch both
  directions, straight no-op), offset (both tables, ms→tick both tempi), `tri` bounds + `w==0`/`W==0`
  draw-skip (both timing & velocity), accent map, `W` width (57/68), bass legato (both feels +
  final-note exempt + track-level) (`tests/test_humanizer.py`, 21); jazz head-1 bar-0 **pre-jitter**
  excerpt via the `_ZeroJitter` seam — ride 0/480/827/960/1440/1787, hats 478/1438, comping 10/828,
  bass D2→0/A2→959, two-feel legato 960→912 (`tests/test_humanizer_goldens.py`). Commits `b46a08f`,
  `ec2cccf`, `f71dffa`.
- [x] §11.6 **Ritard PROVEN** — 39-event jazz table (11 §7.2 anchors + endpoints + full-39 fixture,
  tag_start 115200 from geometry) (`tests/test_ritard_goldens.py`); monotone/floor/first>tag-start/
  none-past-release + cold/fade zero + fade==cold alias + tag_bars:0 (`tests/test_ritard.py`, 14).
  Commits `8f0193a`, `ec2cccf`.
- [x] §11.7 **Determinism (humanizer slice) PROVEN** — repeated-run bit-identity; note-count
  preservation (midi/tags multisets) both examples; exact draw counts via counting-RNG shim ==
  independent structural computation (pop **10198** / jazz **5088**); per-(role,bar) isolation
  (regenerate-one-bar, empirically discriminating) + direct §5.8 seed anchor
  (`tests/test_humanizer_goldens.py`). Commit `ec2cccf`, `f71dffa`. (Full DoD-9 V1–V8 + combined-stage
  matrix is C3.)

**Deferred to Chunk 3 (unchanged):** all pipeline wiring (thread `tempoEvents` orchestrator→serializer
`header.tempos = [base] + tempoEvents`, delete the stubs, call the real stages, add `crash` to
Serializer `_EMIT_ORDER`/`_STUB_MIX` + a stub-timbres `crash` entry), whole-document golden re-bless,
milestone listening (§11.10), whole-phase property matrix (DoD 9: V1–V8, crash suppression, C5 ceiling
under **both** stages, backbeat protection), whole-PHASE 4-lens review, full DoD 1–11 + §10 amendment
audit (DoD 9, 10, 11).

**T1 DONE** (0ad958d) — feel data + loader + validator (`src/trackgen/humanize/{feel.py,feel.yaml}`);
§5.3 values field-for-field, three cap classes each with a non-vacuous rejection fixture; per-task
opus review APPROVE-WITH-NITS (§5.3 fidelity confirmed number-by-number; nit closed with 2 wrapper
tests). **T2 DONE** — humanizer engine (`humanize/{stage.py,swing.py}`): `humanize(phrases, form,
plan) → (Phrase[], [])` (ritard is T3). Op order swing→offset→timing jitter→accent→vel jitter→
duration; float math + single terminal half-even round; per-(role,absBar) RNG (drums cover all
voice-tracks, within-bar (grid,track,midi|-1) order); **injectable-jitter seam** exposes the
deterministic pre-jitter transform through the one production path (T4 asserts §7.2 pre-jitter).
Per-task opus review APPROVE-WITH-NITS: all §7.2 spot-checks reproduced through production, seed
anchor exact; **fix cycle 1** made bass legato **track-level** (§5.6 "same track"/"final whole note"
— was per-phrase, would drop legato at every interior section boundary; affects C3 jazz re-bless) +
removed a dead field + test symmetry (+ a track-level boundary test). Four gates green (**2701
tests**). Next: **T3** (ritard). Handoff note for T4/C3: no §7 golden distinguishes phrase-vs-track
legato — resolved to track-level on §5.6 prose (not arbitration). **T3 DONE** — ritard renderer
(`humanize/ritard.py`, wired via the 2-line `_ritard` seam): §5.7 Friberg–Sundberg curve
`v(x)=(1+(v_end³−1)x)^(1/3)` (v_end 0.65), per-8th→per-16th sampling (release downbeat unsampled),
`round(bpm,1)`, prevailing-tempo dedupe; `cold`/`fade` → `[]` (D7 alias). Per-task opus review
**APPROVE** (zero findings) — reviewer independently reproduced all 11 §7.2 table values (68.5…45.5)
+ the 39-event count exactly, de-risking T4. Four gates green (**2715 tests**). **T4 DONE** — goldens
(independent arbiter) over the real seed-`1ps9wxb` chained pipeline via `_stage6_driver` +
`humanize`: **ZERO divergences** — every §7.2 value reproduced verbatim (head-1 bar-0 pre-jitter
ride/hats/comping/bass/and-of-4 via the `_ZeroJitter` seam; the full **39-event** ritard table incl.
all 11 printed anchors 68.5…45.5, endpoints, tag_start 115200; bass legato two-feel 960→912).
Determinism: repeated-run identity, note-count preservation (midi/tags multisets), exact draw counts
(counting shim == structural: **pop 10198 / jazz 5088**), per-(role,bar) isolation. No doc amendment,
no arbitration escalation (like C1's T4). Four gates green (**2734 tests**). Next: **T5** (whole-chunk
2-lens review + DoD 2/5/6 + close-out).

Live-verified this session: §5.8 humanize RNG anchors reproduce exactly (`derive(master,"humanize")`
= 3899203291477031323; first-five `randrange(100)` = [58,79,50,70,90]; `derive(derive(humanize,
"drums"),"bar:0")` = 6949714659275352449); no `feelTable` in v1 packs → swing-derived default
(pop→straight, jazz swing8→swung); ritard curve confirmed (rel 240 → 68.47 → 68.5). **Targets DoD
2, 5, 6 + humanizer slice of 7.** Out of scope: all wiring, whole-phase matrix, DoD 9/10/11 (Chunk 3).

#### Phase 6 — Chunk 1 — session 10 (`plans/sessions/SESSION_10.md`)

**Planning — plan written, AWAITING USER APPROVAL; no task dispatched.** Task list (T1→T2→T3→T4
serial, then T5):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | `transitions.yaml` schema (`packs/models.py`) + loader (`packs/loader.py`) + both `styles/*/transitions.yaml` + fill windows + TR1–TR7/PT12 | opus | done | 22bd551 |
| T2 | Stage-6 engine: 6a HOLD (`transitions/ending.py`) + 6b devices (`transitions/devices.py`) + `stage.py` + crash voice→track plumbing (`generators`) | opus | done | 9218e14 |
| T3 | Mutation pass 6c (`transitions/mutation.py`) — five operators + per-unit sub-streams + no-op degradation | opus | done | (this commit) |
| T4 | Goldens (independent arbiter): §7.1/§7.2 device narratives + rendering + synthetic fixtures + stage-6 determinism/property subset | opus | done | 492935f |
| T5 | Whole-chunk 2-lens review + DoD 1/3/4/8 + close-out | orchestrator | done | (this commit) |

**Chunk 1 COMPLETE.** 4 opus tasks (T1→T2→T3→T4 serial) + T5 whole-chunk review; per-task + 2-lens
whole-chunk review; four gates green (**2667 tests**, 25-seed property matrix). **DoD 1+3+4+8 PROVEN
+ stage-6 slices of 7+9.** The stage-6 Transition engine (`src/trackgen/transitions/`) implements
PHASE_6 §3/§4 exactly: 6a HOLD → 6b boundary devices (fill select/size/render, stop, dormant dropout,
crash+kick) → 6c mutation (five constructive-safe operators), draw-iff-≥2 on the `transitions` stream
(devices) + per-(role,unit) `mutate` sub-streams.

**T4 arbitration result: ZERO divergences** — the engine reproduced **every** PHASE_6 §7 worked-example
sample verbatim (pop 14/38/9 & jazz 10/32/11 draw counts, fired-op lists incl. the four documented
no-ops, crash velocities, pop fill bar 3 note-for-note, HOLD both examples). No doc amendment, no
C-09-style sample correction needed — the §7 samples are engine-faithful.

Whole-chunk 2-lens review (fresh opus): **correctness/contract APPROVE-WITH-NITS** (all 10 clause-checks
CONFIRM; no blocker/major; sub-pass ordering, `T_last` guard, RNG streams, provenance tags, crash
plumbing all sound), **test-quality/DoD PROVEN-WITH-GAPS** (§7 goldens confirmed doc-transcribed not
snapshotted; one must-fix = property matrix 4→25 seeds). Review fixes (this commit): **N1** crash
default 1440 pinned in `_DEFAULT_DUR` per §10.7 (was hardcoded) + single-sourced; **N2** fill renderer
drops a stray `crash` voice (matches `_generate_drums`; +test); **N3** `drop_ornament` beat-1 protection
made structural (`ticks % BAR != 0`; +2 tests); **25-seed** property matrix (§11.9). **C-11 logged**
(internal drum voice/`ornament` provenance tags beyond §3.9's four — serialize-invisible; the mutation
needs provenance the `PhraseNote` IR lacks).

**Non-caveat observations (handoff notes):**
- **pop `anticipate`@44** is *drawn* (so the count-9 reproduces) but legally renders as a **no-op** — the
  §3.7 `[new, old)` collision guard fires on the dense chorus-2 comp. Consistent with §7.1 ("3 ops" = 3
  non-`none` draws; §7.1 shows no @44 rendering sample). Covered by `test_pop_anticipate_at_44_degrades_to_noop`.
  Not a deviation — engine and doc agree.
- **P1 (latent):** §3.2 places section-boundary devices (fill/crash) **unconditionally by entered type** —
  the engine is faithful to the pinned text. If a v1 form ever had `drums` inactive at a device site, the
  fill/crash would inject drum events there. Unreachable in the two reference forms (drums active at every
  device site; goldens pass). Flagged for C3's whole-phase property matrix to confirm; if the design wants
  device placement gated on `drums`-active, that is a §3.2 amendment (sign-off), not an implementation fix.

**DoD (§11) — Chunk 1 targets 1, 3, 4, 8 + stage-6 slices of 7, 9 — all PROVEN:**
- [x] §11.1 **Loader PROVEN** — `transitions.yaml` → frozen `TransitionsSpec`; **TR1–TR7 each with ≥1
  non-vacuous rejection fixture** (`tests/test_transitions_pack.py`, 24 tests, rule-code matched); both
  reference files load clean via `resolve_pack`; fill windows computed+cached `(960,1920)` for all three
  reference fills; **PT12** (=TR5) enforced on both packs. Commit `22bd551`.
- [x] §11.3 **Device narratives PROVEN** — exact draw counts pop **14/38/9** & jazz **10/32/11** via
  per-sub-stream counting shims (devices single-instance; mutate decomposed drums-vs-comping by seed
  identity); fired-op lists asserted as **full lists incl. the four no-ops** (`tests/test_transitions_goldens.py`,
  `tests/test_transitions_determinism.py`). Crash velocities exact (pop no-kick / jazz +kick). Commit `492935f`.
- [x] §11.4 **Rendering goldens PROVEN** — pop fill bar 3 note-for-note (snares 0.66/0.74/0.82/0.91 tag
  `fill`; hats@960/1440 deleted; kick@0/hats@0/480 survive); crash+kick with (pop bar 12) and without
  (jazz bar 12, kick added) an existing kick; one mutated unit per operator class incl. pitch-preserved
  `anticipate` and the ≥2-attack `drop_hit` guard; HOLD both (pop crash 1.000, jazz 0.553). Commit `492935f`.
- [x] §11.8 **Synthetic fixtures PROVEN** — stop-heavy odds pack (§3.4 all-role deletion+truncation+crash
  end-to-end), `breakdown` form (§3.5 dropout, no fill/crash), rung-restricted fill banks (§3.3 fallback
  both directions) (`tests/test_transitions_fixtures.py`). Commit `492935f`.
- [x] §11.7 **Determinism (stage-6 slice) PROVEN** — repeated-run bit-identity + input-immutability;
  counting-RNG shims for exact per-stream/sub-stream counts; per-unit + per-boundary sub-stream isolation
  (dispatch == independent replay); §3.8 golden seed vectors asserted (`derive(transitions,"devices")` =
  11162692426947704816 etc.). `tests/test_transitions_determinism.py`. Commit `492935f`.
- [x] §11.9 **Property subset (stage-6 slice) PROVEN** — pop_rock+jazz × supported moods × {default,180,240}
  × **25 seeds**: fills only in legal fill bars; no drum groove event inside a rendered window; crash
  suppression for postchorus/breakdown; non-drum `midi` a sub-multiset of pre-stage-6 (no re-pitch, ≤71);
  backbeat-class snare (vel≥0.7 at back2/back4) never removed/moved by mutation. `test_stage6_property_subset`.
  Commit `492935f` + 25-seed bump this commit. (Full DoD-9 incl. V1–V8 + no-note-past-end is C3.)

**Deferred to Chunk 2 / Chunk 3 (unchanged from the chunk plan):** all of stage 7 (C2); pipeline wiring
(thread `tempoEvents` orchestrator→serializer, delete stubs, call real stages), Serializer `_EMIT_ORDER`/
`_STUB_MIX` crash entry + a stub-timbres `crash` timbre, whole-document golden re-bless, milestone
listening, full §11.9 matrix + V1–V8, full DoD 1–11 sign-off, §10 amendment audit (C3).

### Phase 5 — Rhythm-section part generators (chunk plan)

**Split into 4 chunks** (phase too large for one session; ROADMAP §4 seam; PHASE_5 §1). Seams:

#### Phase 5 — Chunk 4 — session 09 (`plans/sessions/SESSION_09.md`)

**Planning — plan written, AWAITING USER APPROVAL; no task dispatched.** Final chunk of Phase 5.
Task list (T1→T2→T3→T4 serial, then T5):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Timbres stub schema + loader + both `styles/*/timbres.yaml` + `pipeline/stubs.py` (identity transitions/humanize + `sound_design`) | opus | done | e477484 |
| T2 | Serializer `pipeline/serialize.py` (§8.3 thin, V1–V8) + unit tests | opus | done | 1de5e9c |
| T3 | Orchestrator `pipeline/orchestrator.py` (§8.1 real chain incl. `select_patterns`) + `pipeline/__init__` + CLI `generate` | opus | done | 055ff8b |
| T4 | Milestone fixtures + whole-document goldens + full-pipeline determinism (DoD 8/9/10) | opus | done | 6f69717 |
| T5 | Whole-PHASE 4-lens review (all 4 chunks) + full §13 DoD 1–11 + close-out | orchestrator | done | 843e16c |

**Chunk 4 COMPLETE — Phase 5 COMPLETE.** 4 opus tasks (T1→T2→T3→T4 serial) + T5 whole-phase
review; per-task + 4-lens whole-phase review; gates green (**990 tests**). **DoD 8+9+10 PROVEN;
full §13 DoD 1–11 complete.** The real orchestrator follows the proven `_drive_full` chain
(interpret→form→harmony→arrange→**select_patterns**→generate×[drums,bass,comping,pads]→stub
transitions/humanize/sound_design→serialize), NOT the stale §8.1 pseudocode (which omits
`select_patterns`). Emits the §8.3 **stub** mix (kick −2/drums −4/bass −3/comping −6/pads −10; no
buses; Compressor+Limiter master) — NOT the PHASE_7 supersession, per the pinned handoff. Both
milestone `TrackDocument`s committed as engine-blessed whole-document goldens (pop 7 tracks/7
sections/2856 notes; jazz trio 6 tracks/6 sections/1288 notes; both `validate_document == []`).

Whole-phase 4-lens review (fresh opus, across all four chunks): **correctness CLEAN** (720-document
fuzz — both packs × 6 moods × 5 lengths × 12 seeds, incl. shortest form + jazz-trio — all V1–V8
clean; every seam verified: orchestrator rng derivation, voicing-DP iterator alignment, push
resolution, walker in-lane guarantees, serializer V8/truncation), **contract COMPLIANT** (every
load-bearing §3–§8 clause matches code; invariants 1/2/4/5 hold; frozen `schema/theory/interpreter/
form/harmony` zero changes across all of Phase 5, `arrangement/parts` untouched in Chunk 4, packs
timbres change genuinely additive; C-09 amendments consistent with committed goldens), **test-DoD
PROVEN** (all §13 DoD 1–11 backed by real doc/fixture-anchored tests; DoD 1–7 re-attested — all
chunk-1/2/3 goldens still pass), **code-quality GOOD-WITH-NITS** (single-sourced stub mix/master/
drum-ids; one net-new duplicate literal fixed). Review fixes (`843e16c`): stubs single-source drum
ids; **C-10** logged (latent: thin Serializer no coincident-same-voice-drum de-dup → V3 edge,
unreachable in v1). **Deferred (recommend defer):** the `_fold_into_lane`/`_third_pc`/`_fifth_pc`
dedup between `walker.py`/`retarget.py` (touches frozen `theory/` + both parts modules for zero
behavior change; natural Phase-6 seam). **§9.5 milestone listening checklist: CLOSED** — user
auditioned both fixtures in the playground and confirmed the track sounded correct (2026-07-17).

**DoD (§13) — Chunk 4 targets 8, 9, 10 — all PROVEN; full 1–11 complete:**
- [x] §13.8 **Serializer + milestone PROVEN** — `serialize` unit-asserts every V-rule edge (V5 snare
  midi=None / kick·hats·ride trigger inject 24/80/82; V4 ≤71; V8 truncate + drop-at-end; dur clamp;
  sections 1:1; single tempo; meta seed echo; §8.3 stub mix; master Compressor+Limiter; buses=[];
  track order; tags dropped) — `tests/test_serialize.py` (13). Both examples end-to-end
  `validate_document == []` + CLI smoke — `tests/test_orchestrator.py`. Both fixtures committed
  (`fixtures/{pop_rock,jazz}.milestone.trackdoc.json`) + validated — `tests/test_whole_document_goldens.py`.
  §9.5 listening checklist CLOSED (user-confirmed 2026-07-17). Commits `1de5e9c`, `055ff8b`, `6f69717`.
- [x] §13.9 **Determinism PROVEN** — repeated-run bit-identity; total-draw counting shim (class-level
  `randrange`, the sole entropy path — catches `weighted_choice` + the interpreter auto-tempo draw)
  pins **pop 18 / jazz 163**, decomposed against each independently-pinned per-stream golden (form
  8/1 · harmony 8/30 · selection 1/3 · walker 0/128 · arrange 0 · stubs 0 · interpreter 1/1);
  module-random-state immunity; AST scan proves `pipeline/{orchestrator,serialize,stubs}.py`
  import no entropy source — `tests/test_pipeline_determinism.py` (9). Commit `6f69717`.
- [x] §13.10 **Whole-document goldens PROVEN** — a fresh `generate_track` re-serializes
  structure-identically to each committed fixture (the first whole-doc regression surface, ROADMAP
  Phase-8 mechanism seeded here); + V1–V8, whole-doc invariant sweep (no non-drum note >71), and
  §9.4/§9.5 anchor cross-checks (pop verse-1 bar-4 comping `[56,59,64]`; jazz Charleston `[53,60]`;
  head-in 24 bass notes; ending D2 whole note) — all matching the C-09-corrected prose (no
  divergence) — `tests/test_whole_document_goldens.py` (12). Commit `6f69717`.
- [x] §13.1–§13.7 **re-attested** (chunks 1–3) — loaders/foundations/arrange/selection/walker/
  voicing/generators goldens all still pass in the 990-test suite; chunk 4's only frozen-surface
  touch (additive `StylePack.timbres`) disturbed no pinned value.
- [x] §13.11 **amendments** — all 11 §12 amendments verified present + consistent in Chunk 1
  (orchestrator-verified, no edits), re-attested here.

#### Phase 5 — chunk seams

**Seams:**

- **Chunk 1 — SESSION_06** (`plans/sessions/SESSION_06.md`): pattern-bank schemas (§5) + loader PT1–PT11 + reference banks §7 (fully enumerated) + foundation transforms (§3.1 intensity, §3.3 retargeting, §3.4 velocity/articulation, §3.5 gating) + §12 amendment check. **Proves DoD 1, 2** (DoD 11 attested).
- **Chunk 2** — `arrange()` (§4) + pattern-selection machinery (§3.2). DoD 3, 4.
- **Chunk 3** — drums / pattern-bass / walking-bass engine (§6.3) / comping+pads voicing passes (§6.4/§6.5); resolves C-04. DoD 5, 6, 7.
- **Chunk 4** — orchestrator (§8.1) + Serializer (§8.3) + stub timbres (§8.4) + drum→track map (§8.2) + both milestone fixtures + whole-document goldens + determinism shims + whole-phase review + full §13 DoD. DoD 8, 9, 10.

#### Phase 5 — Chunk 3 — session 08 (`plans/sessions/SESSION_08.md`)

**Planning — plan written, AWAITING USER APPROVAL; no task dispatched.** Task list
(T1 ‖ T2, then T3, then T4, then T5):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Voicing pass `parts/voicing.py` (§6.4/§6.5 — full-timeline Viterbi per voiced role, classes-per-rung, comping/pads weights, `lane.high−6` anchor, cardinality-pad) + mechanism units. **Resolves C-04.** | opus | done | b9eb7aa |
| T2 | Walking-bass engine `parts/walker.py` (§6.3 — two/four-feel, per-bar sub-streams, nearest, final-bar/two-chord rules, beat3-before-beat2, approach types, decay, embellishment, draw-iff-≥2) + mechanism/draw-order units | opus | done | a93c1a6 |
| T3 | Generators dispatcher `parts/generators.py` (§6 shared loop + §6.1 drums/§8.2 voice→track map + §6.2 pattern-bass + §6.4/§6.5 comping/pads + bass-mode dispatch) + generator units | opus | done | fa00f51 |
| T4 | Normative goldens: §9.2 walker (DoD 5) + §9.3 voicing (DoD 6) + §9.4 excerpts / end-to-end / determinism (DoD 7), independent transcriber over the real seed-`1ps9wxb` pipeline | opus | done | 13c6c02 |
| T5 | Whole-chunk 4-lens review + DoD 5/6/7 checklist + C-04 resolution + close-out | orchestrator | done | 28d4695 |

Targets **DoD 5** (§13.5 walker), **DoD 6** (§13.6 voicing), **DoD 7** (§13.7 generators
end-to-end). Resolves **C-04** (voicing API). Out of scope: orchestrator/Serializer/timbres/
milestone/whole-document goldens (Chunk 4, DoD 8/9/10).

**Chunk 3 COMPLETE** — 4 opus tasks (T1 ‖ T2, then T3, then T4) + investigation + amendment + T5
whole-chunk review; per-task + 4-lens whole-chunk review; gates green (**941 tests**). **DoD 5+6+7
PROVEN; C-04 resolved; C-09 logged.** Whole-chunk 4-lens review (fresh opus): **correctness APPROVE**
(all integration seams — voicing↔`voicing_for` incl. pushed hits, Viterbi stage alignment,
walker→generate, tiling, determinism, register — verified; no bug), **contract COMPLIANT** (frozen
modules untouched via empty `git diff`; every §6.3/§6.4/§6.5/§8.2/§3.6 clause holds; C-09 amendment
internally consistent), **test-DoD APPROVE-WITH-NITS** (DoD 5/6/7 each PROVEN with named tests;
goldens doc-transcribed not code-snapshotted), **code-quality GOOD-WITH-NITS** (DRY duplication only).
Two nits fixed (`28d4695`): DoD-6 `_pad_to_equal` value now directly asserted; zero-gap→dur-0 latent
crash hardened. **Deferred to a future cleanup (handoff):** consolidate `_fold_into_lane` +
`_third_pc`/`_fifth_pc` shared verbatim between `parts/walker.py` and the frozen `parts/retarget.py`
(behavior-identical; would touch frozen modules) — a natural `theory/chords.py` + shared-placement
extraction. **Latent non-reachable edges (documented, no fix):** section-local gap clamp lets the last
pitched hit ring past the section (intended); C-07's sub-60-tick retrigger drop (already logged).

**DoD (§13) — Chunk 3 targets 5, 6, 7 — all PROVEN:**
- [x] §13.5 **Walker PROVEN** — §9.2 excerpt notes exactly (head-1 bars 0–3, turnaround 10–11,
  solo-1 bars 12–15 incl. bar-15 decay-draw A1 + and-of-4 ghost, outro-1 + final-bar rule); per-section
  **draw counts 9/38/37/36/7/1 = 128** via a counting-RNG-per-bar shim at the real §3.6 per-bar seed;
  **note counts 24/51/54/54/24/7** (solos corrected per C-09); per-bar sub-stream independence;
  property matrix (jazz × moods × seeds: lane containment, beat-1 chord-tone, approach = one of the
  three folds, final-bar rule) — `tests/test_walker.py` + `tests/test_walker_goldens.py`. Commits
  `a93c1a6`, `13c6c02`.
- [x] §13.6 **Voicing PROVEN** — §9.3 exact MIDI (jazz head shells + solo rootless octave-up per C-09,
  pop comping, pop pads `fifths`); all tops ≤ 71; deterministic zero-draw property over both packs;
  cardinality-padding value directly asserted (`_pad_to_equal` pads with own top pitch); **C-04
  resolved** (quartal perfect-4ths, `lane.high−6` anchor, class-per-role) — `tests/test_voicing_pass.py`
  + `tests/test_voicing_goldens.py`. Commits `b9eb7aa`, `13c6c02`, `28d4695`.
- [x] §13.7 **Generators end-to-end PROVEN** — both worked examples through the `generate` loop:
  §9.4 excerpts (pop verse-1 bar 4, jazz head-1 bar 0, post-§3.4); whole-output invariants (sorted
  `(ticks,midi)`, within section span, velocities ∈ (0,1], non-drum midi ≤ 71); `push` tags (jazz+pop
  comping, pop bass) + `ghost` tags (walker); determinism + module-random independence + 0 generation
  draws for pattern roles / 128 for the jazz walk — `tests/test_generators.py` +
  `tests/test_generator_goldens.py`. Commit `fa00f51`, `13c6c02`.

**T1+T2 DONE** — both opus, per-task opus review **APPROVE-WITH-NITS** (no blockers/majors),
four gates green (866 tests). Orchestrator verified gates independently + read both modules.
T1 (voicing, `b9eb7aa`): reviewer re-derived Dm9 shell2 = F3+C4 (§9.3), confirmed positional
stage-iterator safe + `theory/voicing.py` unmodified + C-04's three readings. Nits (optional):
test-helper `id()`-keying, register-uniformity assert. T2 (walker, `a93c1a6`): reviewer
reproduced head-1 = **9** draws by hand, confirmed resolutions 3a–3d correct §6.3 readings and
the **128** total safe. **T4 watch (carried into T4 dispatch):** `_beat3` includes chord
extensions via `chord_tones` — a defensible §6.3 reading, but the first suspect if a solo draw
count (38/37/36) diverges; T4 is the golden arbiter and escalates on divergence. Other nits
cosmetic (final-bar-two-feel-only; sus positional interval). No CAVEATS (C-04 resolves at T5).

**T3 DONE** (`fa00f51`) — generators dispatcher, per-task opus review **APPROVE-WITH-NITS** (no
blockers; reviewer confirmed frozen contracts unmodified via empty `git diff`, re-derived §9.4
sanity 814/720/443 + velocities, judged the two composition ambiguities unpinned-but-reasonable).
Orchestrator verified four gates green (892 tests) + independently read the module. Design
resolutions (documented, unpinned by any §9 golden): **gap-clamp is to the next *surviving*
(post-gating) same-track event**; **articulation applied to authored dur then passed to retarget,
so `retrigger` splits the articulated length** (no §9 golden pins a comping/bass hit crossing a
chord boundary — the excerpts are single-chord bars). **T5-polish candidate (non-reachable nit):**
two same-tick pitched events → `gap 0` → `duration_ticks 0` (schema `≥1` violation); no reference
pattern authors this. Next: **T4** (normative goldens §9.2/§9.3/§9.4 + end-to-end, DoD 5/6/7).

**T4 DONE** (`13c6c02`) — DoD 5/6/7 goldens over the real seed-`1ps9wxb` pipeline. **Golden-value
arbitration triggered + resolved (user signed off).** T4 (independent transcriber) drove the real
pipeline and found **7 printed §9.2/§9.3/§9.4/§13.5 samples diverged**; it did NOT tune — marked
them `strict xfail` and escalated. A deep investigation (trace scripts + DP-cost enumeration)
confirmed **all 7 are wrong DERIVED doc samples, NO engine bug** — the frozen walker/voicing/
generators are faithful to §6.3/§6.4/§6.5/§3.6/§8.6. The engine's hardest goldens reproduced
unchanged: **128 walker draws** (9/38/37/36/7/1), all invariants, determinism, jazz head shells,
pop pads. Amendments (PHASE_5 + recomputed fixtures in one commit, arbitration rule 2; **CAVEATS
C-09**): RC1 solo note counts 50/53/53→**51/54/54** (rule-6 ghost fires on the section's final bar;
draw-free); RC2 §9.2 approach C2/G♭1→**D♭2/F1** (ascending-pitch candidate order §3.6 — **user ruled**
engine authoritative); RC3 jazz solo rootless + pop comping an octave up (frozen Viterbi global min,
low octaves cost +371/+1526 more), B♭13→**3-voice D4 F4 A♭4**, §9.4 pop bar-4→**G♯3+B3+E4** cascade.
Four gates green (940 tests, zero xfail). **DoD 5+6+7 PROVEN** against the corrected goldens. Next:
**T5** (whole-chunk 4-lens review over the corrected goldens + DoD checklist + C-04 resolution + close-out).

#### Phase 5 — Chunk 2 — session 07 (`plans/sessions/SESSION_07.md`)

**COMPLETE** — 3 opus tasks (T1 ‖ T2, then T3) + 1 whole-chunk review fix; per-task + 2-lens
whole-chunk review; gates green (816 tests). **DoD 3+4 PROVEN.** Task list:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Arrangement planner `arrangement/arrange.py` + `arrangement/lanes.yaml` (§4.1 activation, §4.2 density, §4.3 lanes+bias/≤71, zero-draw) + §4.5 goldens/property (DoD 3) | opus | done | d52a00e |
| T2 | Selection machinery `parts/selection.py` (§3.2 kind-map/cache-once/eligibility/draw-iff-≥2 on `select` sub-streams, bass-walking exempt, active-only) + mechanism/draw-count units | opus | done | 71ac7a7 |
| T3 | §9.1 draw-narrative goldens (pop 1 / jazz 3) + completeness property, end-to-end over both reference packs (`tests/test_selection_goldens.py`) (DoD 4) | opus | done | cbfaa19 |

Per-task reviews (opus): T1 APPROVE-WITH-NITS (reviewer hand-recomputed pop chorus-3 0.842 /
intro-1 count 2 / jazz solo-3 0.591 / all four bias-shifted registers — doc=test=arithmetic; two
optional non-reachable nits); T2 APPROVE-WITH-NITS (verified draw-iff-≥2 exact, sub-stream
derivation `Rng(derive(stream_seed(role),"select"))`, walking-bass stream never constructed; two
cosmetic nits); T3 APPROVE (goldens doc-transcribed, per-role counting shims prove pop 1 / jazz 3,
bass/pads no-selection positively asserted). Whole-chunk review (2 fresh opus lenses):
**correctness/contract APPROVE-WITH-NITS** (arrange↔selection compose; rung written by arrange ==
rung read by selection; ≤71 ceiling on every non-drum entry; zero arrangement draws; no frozen
contract touched — `git diff 00f0315..HEAD` clean on schema/packs/intensity/seeds; two non-reachable
nits) and **test-quality/DoD APPROVE-WITH-NITS** (DoD 3+4 PROVEN; one low gap: default select path
not golden-locked → fixed `eecb17b`, no divergence). Orchestrator independently reproduced all §4.5
anchors + §9.1 counts; ran four gates. No CAVEATS (both correctness nits are non-reachable latent
edges changing no pinned value — logged as handoff notes).

DoD (§13) — Chunk 2 targets 3, 4 — **both PROVEN**:
- [x] §13.3 **Arrangement stage PROVEN** — both §4.5 tables field-for-field (real interpreter→form
  pipeline @ seed `1ps9wxb`; every `(section, role)` incl. inactive: `intensity`/`density_budget`
  3dp/`active`/`register`) — `test_arrange.py::test_{pop,jazz}_arrangement_golden_field_for_field`;
  zero-draw counting shim (`test_arrange_consumes_zero_draws`) + structural (arrange imports no
  `random`, TID251); property matrix pop_rock+jazz × supported moods × lengths {30..600 step 15} ×
  25 seeds (`test_property_valid_arrangement`: full section×role coverage, `active` contiguous prefix
  ≤ `layersMax`, non-drum `high≤71` & `low<high`, intro < resolved-successor count,
  `intensity==intensity(energy)`, density∈[0,1]@3dp). Mechanism units: baseCount/layersMax cap,
  breakdown-min-2 / bridge-min-3, intro thinning + `max(1,·)` floor + no-successor edge, bias
  shift+ceiling-clamp (incl. bias 0.9 forcing the cap) + negative shift + half-even ties, lanes.yaml
  validation. Commit `d52a00e`. Resolves the arrangement half of **C-06**.
- [x] §13.4 **Selection PROVEN** — both §9.1 draw narratives with exact draw counts summed from
  per-role counting shims (**pop 1**, **jazz 3**), winner ids at the right `by_key` keys, walking-bass
  + dormant-pads **positively** asserted as no-selection, and the production `rng_factory=None` path
  golden-locked to the same winner ids — `test_selection_goldens.py::test_{pop,jazz}_selection_draw_narrative`;
  completeness property (every reachable `(section, role)` resolves, no extras) over pop_rock+jazz ×
  21 moods × 5 tempi × 5 seeds — `test_selection_completeness`; 16 mechanism units
  (`test_selection.py`: kind map incl. breakdown→main/outro→ending, cache-once `is`-identity +
  reuse-not-redraw, different-rung redraw, `main` energy-filter, intro/ending energy-ignored, inclusive
  tempo band, singleton 0-draw, ≥2 draws-once + independent replay, walking-bass exempt, inactive-role
  nothing). Commits `71ac7a7`, `cbfaa19`, `eecb17b`.

#### Phase 5 — Chunk 1 — session 06 (`plans/sessions/SESSION_06.md`)

**Planning — awaiting approval; no task dispatched.** Task list (T2 ‖ T3 after T1):

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Pattern-bank schema (`packs/models.py`) + loader (`packs/loader.py`) + PT1–PT11 + one rejection fixture per class (event vocab `sixth`/`chord`/`push`/`minDensity`; bass mode/walking; comping/pads voicing.classes; manifest layeringOrder; §3.2 completeness) | opus | done | 60c6289 |
| T1b | Bank-level `retarget` default support (§7 "shown once") — BassBank/VoicedBank + loader injection | opus | done | 4299062 |
| T2 | Reference banks §7.1–§7.4 fully enumerated (8 YAML, complete the abridged entries) + load-clean/anchor test | opus | done | 4e131c2 |
| T3 | Foundation transforms §3.1 intensity + §3.3 retargeting + §3.4 velocity/articulation + §3.5 gating + DoD-2 unit tests | opus | done | 095d0e1 |
| T4 | §12 amendment-consistency check + whole-chunk review + close-out | orchestrator | done | 5edb8d3 |

**Chunk 1 COMPLETE** — 4 tasks (+T1b) built, per-task + 2-lens whole-chunk reviewed, gates green (735 tests). Per-task reviews: T1 CHANGES-REQUIRED→fixed (PT2 non-decreasing blocker, C-05); T3 APPROVE-WITH-NITS (reviewer re-derived every degree/fallback + §9.4 E2=40; C-07); T2 CHANGES-REQUIRED→fixed (pr_dr_3 bar-2 groove-dropout blocker; C-08). Whole-chunk review (2 fresh opus lenses — contract/integration + test-quality/DoD): **both APPROVE-WITH-NITS, no blockers, DoD 1+2 PROVEN**, all four caveats (C-05/06/07/08) verified accurate; two nits closed (approach e2e test + `OnChordChange` type, 5edb8d3). Orchestrator independently verified all 11 §12 amendments present + consistent (no edits), reproduced the §9.4 E2=40 anchor, and confirmed pr_dr_3 = 26 events with bar-2 backbone. Commits: T1 `60c6289`, T1b `4299062`, T3 `095d0e1`, T2 `4e131c2`, polish `5edb8d3`.

DoD (§13) — Chunk 1 targets 1, 2 (11 attested):
- [x] §13.1 **loaders PROVEN** — four `patterns/*.yaml` schemas → frozen `DrumsBank`/`BassBank`/`VoicedBank×2`; PT1–PT11 each with ≥1 non-vacuous rejection fixture (`tests/test_patterns_pack.py`, 26 tests); both reference packs `resolve_pack` clean, fully enumerated §7, through the enforced PT5/6/7/10 path (`tests/test_reference_banks.py`, 19 tests: golden anchors event-for-event, §9.1 candidate counts/weights, voicing maps, layeringOrder, walking block, bank-level retarget). C-05 (PT2 order), C-06 (marker-gating), C-08 (ride band) logged.
- [x] §13.2 **foundations PROVEN** — §3.1 thresholds (boundary-exact), §3.3 every degree × qualities × ≥2 dressing tiers hitting every fallback + `push` boundary/no-boundary/song-end + octave folding at both lane edges tie-down + `onChordChange` hold/retrigger/stop incl. <60 drop + approach e2e placement, §3.4 identity/clamp/exempt, §3.5 gating </=/> (`tests/test_foundations.py`, 47 tests). C-07 (§3.3 resolutions) logged.
- [x] §13.11 §12 amendments present + consistent — PHASE_1 §7 Q2/Q3 + §4.4/§4.5/§6.2/§6.3; PHASE_2 §7.2; PHASE_3 §6.5; PHASE_4 §8.4/§8.5; ROADMAP §2 (orchestrator-verified, no edits needed).

### Phase 4 — Harmony engine (chunk plan)

**Split into 2 chunks** (phase too large for one session; seam = "pieces vs. assembly"):

- **Chunk 1 — SESSION_04** (`plans/sessions/SESSION_04.md`): theory library + dressing ladder + `progressions.yaml` loader/reference packs. **Proves DoD 1, 2, 3, 8.** Tasks (all opus): T1 theory resolution core (`theory/chords.py`) → then parallel T2 voicing/VL (`theory/voicing.py`), T3 dressing ladder (`harmony/dressing.*`), T4 progressions schema+loader+reference packs (`packs/*` + `styles/*`).
- **Chunk 2 — SESSION_05** (plan TBD): `HarmonicPlan` §7 schema extension (`schema/ir.py`) + harmony stage (`harmony/stage.py`) §5.1 + 3 boundary transforms + §10 golden chains (76+64 events) + §5.6 seed goldens + determinism (8/30 draws) + property matrix + deceptive fixture + §13 amendments. **Proves DoD 4, 5, 6, 7, 9, 10.**

Golden anchor pre-verified: `derive(3735928559,"harmony")==226146634901021418`; §5.6 getrandbits/randrange vectors match exactly.

#### Phase 4 — Chunk 2 — session 05 (`plans/sessions/SESSION_05.md`)

**COMPLETE** — 3 opus tasks + orchestrator §13 check; per-task + 4-lens whole-phase review across both
chunks; gates green (644 tests). DoD 4/5/6/7/9/10 PROVEN. Task list:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | `HarmonicPlan` §7 schema extension (`schema/ir.py`): `KeyRegion`/`EventScale` + `keys`/`pool_selections` + per-event `scale`/`function`/`tags` (additive to pinned core) | opus | done | 09335d9 |
| T2 | Harmony stage (`harmony/stage.py`) §5.1 exactly — gate→density§5.2→per-tag select+dress→assembly+hold-merge→turnaround/deceptive/final transforms→emit; 15 mechanism unit tests | opus | done | 35dccba |
| T3 | Goldens/determinism/property/deceptive (`tests/test_harmony_goldens.py`): §10 Ex1 76ev/Ex2 56ev event-for-event, §5.6 seed vectors, 8/30-draw counting shim + singleton-0 + append-only, DoD-7 property matrix, DoD-9 synthetic deceptive | opus | done | abc447e |
| T4 | §13 amendment-consistency check (DoD 10) + whole-phase review + close-out | orchestrator | done | 8f15843 |

Per-task reviews (opus): T1 APPROVE-WITH-NITS (keys-cardinality deferred to the stage invariant); T2
APPROVE-WITH-NITS (reviewer **independently reconstructed both 8/30 draw totals** from the reference
packs — exact; caught the `min7b5` passthrough subtlety). **T3 surfaced a real stage tiling bug and
escalated it** (boundary transforms kept a hold-merged terminal-tonic event whole when a shorter-in-bars
turnaround/finals started mid-event → overlapping events, reachable in jazz `minor_basic`+`quick_two_five`;
repro jazz/tense/75s/9r725xk). Fixed via shared `_truncate_to()` clamp (own-code bug, not a caveat); draw
sequence untouched (8/30 pins green). Whole-phase review (4 fresh opus lenses across chunks 1+2): all
**clean/COMPLIANT/GOOD, zero confirmed bugs**; two DoD-coverage gaps found + fixed (DoD-7 matrix 8→**25
seeds** per pinned §14.7; DoD-6 **budget** append-only added beside the form case). Non-blocking nits
carried to Phase-5/8 handoff (minor-key deceptive `S`-function on dormant path; P4 runtime guard;
StopIteration clarity). Orchestrator pre-gate independently reproduced: seed anchor
`226146634901021418`; both `pool_selections` char-for-char vs §10; Ex1 sample event @24960; final-two
`["final"]`; ASCII symbols; event counts (Ex1 76, Ex2 56). **Note:** §10.2 pins no event count — "64" is
the *bar* total; hold-merge (§3.1) yields **56 events**, which the golden asserts (not a PHASE_4 amendment).

DoD (§14) — **all 10 items PROVEN** (Chunk 1 proved 1/2/3/8, re-attested; Chunk 2 proves 4/5/6/7/9/10):
- [x] §14.1 loader P1–P10 + cross-file P1/P4 — `tests/test_progressions_pack.py` (bb7114e, Chunk 1). C-03 (SubV/P8) logged.
- [x] §14.2 theory `resolve_token`/spelling/scale/chord+guide tones/voicing — `tests/test_theory_chords.py`+`test_theory_voicing.py` (21ce323, 6cc5907, Chunk 1).
- [x] §14.3 dressing `dressing.yaml`==§6.3, tiers/offsets/clamp, §6.4-legal — `tests/test_dressing.py` (ee7ddb6, Chunk 1).
- [x] §14.4 goldens — both §10 examples **event-for-event** (ticks/durations/sectionIds/full ChordSpec incl. symbol+roman/scale/function/tags/keys/pool_selections): Ex1 76 events, Ex2 56 events — `test_golden_example_{1,2}_event_for_event` (abc447e). Test-quality lens confirmed values are **doc-transcribed** (the head-1 `Bb9` vs solo-2/3 `Bb13` per-boundary asymmetry under one `minor_turn` id is the tell); orchestrator reproduced all §10 anchor facts.
- [x] §14.5 seed vectors §5.6 asserted exactly + tied to the stage stream — `test_harmony_stream_seed_vectors` (abc447e).
- [x] §14.6 determinism: same→identical; counting-RNG shim **8 draws** Ex1 / **30 draws** Ex2 (non-vacuous — `weighted_choice`→`randrange` is the sole entropy consumer, guarded by ≥2); singleton→0 draws; append-only under **form** and **budget** change — `test_draw_count_example_{1,2}`, `test_singleton_candidate_form_consumes_zero_draws`, `test_draw_sequence_is_append_only_under_{added_section,budget_change}`, `test_determinism_identical_plans` (abc447e, 8f15843).
- [x] §14.7 property matrix — pop_rock+jazz × supported moods × maxLengthSec {30…600 step 15} × **25 seeds** (~20k plans); all 10 invariants (gapless tiling, per-section bounds, quality∈enum + §6.4-legal ext, scale+function present, final degree-1-rooted, prechorus/bridge D-function, `keys==[{0,tonic,mode}]`, same-tag identical bodies outside replaced bars, `pool_selections` complete) — `test_property_valid_harmonic_plan` (8f15843, 25 seeds mirror test_form.py).
- [x] §14.8 `chord_tones` vs music21 `harmony.ChordSymbol` (documented exclusions; music21 10.5.0 pinned) — `tests/test_theory_chords.py` (21ce323, Chunk 1).
- [x] §14.9 deceptive fixture — synthetic same-tag/no-turnaround, end-to-end through `harmony()`: `vi min7` (major) / `bVI maj` (minor), `tags==["deceptive"]`, 0 draws — `test_deceptive_substitute_end_to_end` (abc447e).
- [x] §14.10 §13 amendments present + consistent (no edits) — PHASE_1 §7 Q4/Q6 + §4.3; PHASE_2 §7.2 + §9 Q3; ROADMAP §2 + §4 (orchestrator-verified).

#### Phase 4 — Chunk 1 — session 04 (`plans/sessions/SESSION_04.md`)

**COMPLETE** — all four tasks built, per-task + 2-lens whole-chunk reviewed, gates green (587 tests). DoD 1/2/3/8 PROVEN. Task list:

| # | Task | Model | Status | Commit |
| --- | --- | --- | --- | --- |
| T1 | Theory resolution core (`theory/chords.py`): §8.1/§8.2 tables, `resolve_token` (§3.1/§3.2/§3.3), §7.4 scale-hint, chord/guide tones, §6.4 helper; music21 cross-val | opus | done | 21ce323 |
| T2 | Voicing & voice-leading (`theory/voicing.py`): §8.4 candidates incl. `fifths`, §8.5 `vl_distance`, §8.6 Viterbi | opus | done | 6cc5907 |
| T3 | Dressing ladder (`harmony/dressing.yaml`+`.py`): §6.1 tiers, §6.2 offsets, §6.3 tables, §6.4 filter | opus | done | ee7ddb6 |
| T4 | `progressions.yaml` schema (`packs/models.py`) + loader P1–P10/density (`packs/loader.py`) + `styles/{pop_rock,jazz}/progressions.yaml` (§9.1/§9.2) | opus | done | bb7114e |

Per-task reviews (opus, T2/T3/T4 parallel): **T3 APPROVE**; **T2 APPROVE-WITH-NITS** (reviewer hand-re-derived the ii–V–I Viterbi DP → asserted path genuinely optimal; tie-break + drift proof real); **T4 APPROVE-WITH-NITS** (all P1–P10 reject correctly; reference packs verbatim; C-03 confirmed honest & scoped). No blockers/majors. **C-03 user-signed-off: Option A** (widen P8 to admit the SubV `bII7`; keep code; C-03 open, PHASE_4 §4.3 reword deferred). New caveat **C-04** (T2 voicing API: keyless `voicing_candidates` → perfect-4th quartal reading; additive `anchor` kw on `optimal_voicing_path`; deferred to PHASE_5 §13.6). Accepted nits (DoD met, tests can't pass for wrong reason — carried to Chunk-2/Phase-5 handoff, not fixed): T2 rootless/drop2 triad-cardinality degradation (Phase 5 class-per-role policy); T4 `_relaunches_as_dominant` keys on pc 1 (admits `#I7` enharmonic — harmless); T4 `final_chord_token` last-declared-label (v1 single-label pools only); a few T4 rejection tests omit `match=`.

T1 review: opus APPROVE-WITH-NITS (every §8.1/§8.2/§6.4/§3.2/§3.3/§7.4 table verified cell-by-cell; music21 cross-val real). One nit fixed: sus suffixes now require the shown (upper) numeral case per §3.1 (`21ce323`). T1 public surface: `resolve_token`, `chord_function`, `chord_scale`→`ScaleHint`, `legal_extensions`/`extensions_legal`, `chord_symbol` (re-derive after dressing), `chord_intervals`/`chord_tones`/`guide_tones`→`GuideTones`/`scale_pcs`; consts `QUALITY_INTERVALS`/`EXTENSION_OFFSETS`/`SCALE_INTERVALS`; types `Function`/`KeyLike`(Protocol)/`ScaleHint`/`GuideTones`/`TokenError`.

Whole-chunk review (2 fresh opus lenses, both **APPROVE-WITH-NITS**): (A) integration/contract — the three modules compose; every §10 per-chord fact reproduces end-to-end via `resolve_token→chord_function→dressing_options→chord_symbol`; `chord_function`/degree math single-sourced (no divergent 2nd impl); `extensions_legal` enforced on every dressed spec. (B) DoD/simplification — DoD 1/2/3/8 all PROVEN (music21 cross-val is a real pc-set comparison; `dressing.yaml` asserted against an independent literal §6.3 transcription; per-suffix/12-tonic/per-rule-class coverage complete). Orchestrator independently reproduced all 10 §10 spot-check chords (symbol/function/eff-tier/scale) — exact. **Fix applied post-review:** lane-prune test now asserts per-class non-emptiness (guards the ceiling assertions against a future empty-candidate class). No blockers/majors. Remaining items are Chunk-2/Phase-5 **handoff notes**, not defects (see handoff block).

DoD (§14) — Chunk 1 targets 1, 2, 3, 8 — **all PROVEN**:
- [x] §14.1 progressions loader P1–P10 (P11 → Phase 8); one rejection fixture per rule class (P1/P2×4/P3×2/P4×2/P5×4/P6/P7×2/P8×2/P9×2/P10); both reference files load clean; P1/P4 cross-file run vs reference `forms.yaml` — `tests/test_progressions_pack.py` (bb7114e). `resolve_token` rejects extension groups.
- [x] §14.2 theory: `_SUFFIX_GOLDENS` (all 15 qualities+aliases), alterations/case-errors/holds/ext-groups/slash rejections, §8.1/§8.2 tables exact, spelling 12 tonics × 2 classes + "B♭7-in-Dm" flat-side, chord/guide tones, lane-prune all 9 classes (non-empty guarded), hand-verified ii–V–I `shell3`+`rootless_a` DP paths + drift/no-drift pair, integer-cost property, `fifths` ships — `tests/test_theory_chords.py`+`test_theory_voicing.py` (21ce323, 6cc5907, +lane fix).
- [x] §14.3 `dressing.yaml` == §6.3 field-for-field (independent literal `EXPECTED_TABLE`); tier boundaries (incl. §10 anchors 0.132→0/0.653→4) + offset + clamp; every table & produced option §6.4-legal — `tests/test_dressing.py` (ee7ddb6).
- [x] §14.8 `chord_tones` vs music21 `harmony.ChordSymbol` over an 18-token resolvable subset (pc-set equality); `minMaj7` exclusion guarded live; music21==10.5.0 pinned in `uv.lock` — `tests/test_theory_chords.py` (21ce323).
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
