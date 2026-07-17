# Implementation Progress

Source of truth for implementation state across sessions. The orchestrator (see `PROMPT.md`) updates this file **immediately** at every task completion and step transition — never batched to session end. A new session must be able to resume losslessly from this file plus git log.

Statuses: `not started` · `planning` · `in progress` · `blocked` · `done`

## Handoff — next session starts here

> **Next:** **Phase 5, Chunk 3 — generators / walker / voicing** (`@PROMPT.md - Phase 5`, resume mid-phase). **Chunks 1+2 are COMPLETE** (sessions 06+07; DoD 1/2/3/4 PROVEN; 816 tests, four gates green; both chunks whole-review clean). **Session-08 plan WRITTEN — `plans/sessions/SESSION_08.md` — AWAITING USER APPROVAL; no implementation agent dispatched.** Plan: T1 voicing pass (`parts/voicing.py`, §6.4/§6.5, resolves C-04) ‖ T2 walker (`parts/walker.py`, §6.3), then T3 generators dispatcher (`parts/generators.py`, §6/§8.2), then T4 normative goldens (§9.2/§9.3/§9.4 + end-to-end, DoD 5/6/7), then T5 whole-chunk review + close-out. Read `PHASE_5.md` §6 + §3.3 + §9.2/§9.3/§9.4 in full; resolves **[C-04]** (voicing API). Proves **DoD 5** (walker §9.2), **DoD 6** (voicing §9.3), **DoD 7** (generators end-to-end). **Golden-value arbitration is the live risk** (§9.2 walker draw/note counts, §9.3 voicing MIDI are the docs' most intricate computed samples — faithful impl, escalate on divergence, never tune).
>
> **What Chunk 2 hands Chunk 3 (all committed, tested — commits `d52a00e`/`71ac7a7`/`cbfaa19`/`eecb17b`):**
>  - **`arrange(plan, form, pack, rng) -> ArrangementPlan`** (`trackgen.arrangement`) — one `ArrangementEntry` per `(section, role)`: `.active`, `.intensity` (the 1–4 rung), `.density_budget`, `.register` (the role's arrangement lane, already registerBias-shifted + ≤71-clamped). Chunk-3 generators consume: `.register` as the retarget/voicing lane (pass to `retarget_event`'s `lane` and as the voicing-candidate prune lane / `optimal_voicing_path` anchor `lane.high−6`), `.density_budget` for §3.5 gating + the walker's embellishment rate (§6.3), `.intensity` for walker feel-by-intensity + the voicing class per rung. `arrange` consumes **zero** draws (the `arrangement` stream stays reserved).
>  - **`select_patterns(plan, form, arrangement, pack, master, overrides, *, rng_factory=None) -> SelectionResult`** (`trackgen.parts`) — `.by_section[(section_id, role)] -> PatternEnvelope` is the chosen pattern for every **active, pattern-mode** `(section, role)`; `.by_key[(role, kind, rung)] -> PatternEnvelope` is the per-song cache. **Walking-mode bass has NO entry** (the walker serves every section/kind — bass generation reads `pack.walking`, not selection). Dormant/inactive roles (jazz pads) have no entry. Chunk-3 generators tile the selected pattern **per phrase** (§3.2 tiling; phrase starts are the pinned alignment points) and retarget each event via `parts/retarget.py`.
>  - **Non-reachable latent notes (not caveats — no pinned value changed):** (a) `arrange`'s intro rule reads the successor's *provisional* (pre-intro) count, so an intro **immediately followed by another intro** could read thicker-than-successor; unreachable because both reference form templates declare `intro` once as the first spine slot (the DoD-3 property matrix guards it). If Phase 8 form vocabulary ever admits adjacent/trailing intros, resolve counts right-to-left. (b) the registerBias lane shift re-checks only `≤71` post-shift (per §4.3 / PHASE_1 §4.4); at an extreme `|bias|→1.0` a comping/pads lane could narrow to span 11 (still covers 12 pcs, so §3.3 folding stays total) — unreachable because the interpreter bounds derived `registerBias = round(0.25×valence, 3)` to ±0.25 (max shift ±3 → span ≥20).
>
> **What Chunk 1 hands Chunk 2/3 (all committed, tested — commits `60c6289`/`4299062`/`095d0e1`/`4e131c2`/`5edb8d3`):**
>  - **Loaded pack surface** (`StylePack`, `packs/models.py`): `pack.layering_order: tuple[Role,...]|None` (§4.1 activation order), `pack.patterns[role]: list[PatternEnvelope]` with `.kind`/`.energy_level`/`.weight`/`.eligibility`/`is_gated` (selection filters per (role,kind,rung)), `pack.bass_mode` + `pack.walking: WalkingConfig` (`.feel_by_intensity`/`.approach_weights`/`.beat1_repeat_weights` — the walker, Chunk 3), `pack.voicing[role].classes[rung]` (comping/pads voicing pass, Chunk 3). Event vocab extended: `sixth`/`chord` degrees, `push`/`min_density` fields, `octave` now optional (`=0`).
>  - **`arrangement/intensity.py::intensity(energy) -> int` (1–4)** — §3.1 thresholds 0.30/0.55/0.80 as engine data. Selection matches `energy_level == intensity(section.energy)`; **`intensity()` (section-energy→rung) and the authored `energy_level` are distinct — keep them separate.**
>  - **`parts/retarget.py::retarget_event(...)` + `resolve_degree_pc(...)`** — §3.3 degree resolution, push, octave-fold, onChordChange. Chunk-3 generators call it per event. **Handoff notes:** (a) `retarget_event` takes `lane: Register` (from `ArrangementEntry.register`) and `pattern_register: Register` (built from `env.retarget.register_{low,high}`) as **separate** args. (b) `degree: chord` emits the injected `voicing_for(chord_event) -> Sequence[int]` **verbatim — no fold, no ≤71 cap**; inv-4 for voiced hits lives entirely in the Chunk-3 voicing pass (lane-prune + ceiling there). Key the voicing map by ChordEvent **identity/start_tick**, not root_pc. (c) pushed events with `pos+dur > lengthTicks` **overhang into the next tile by design** (anticipation doubling) — generators/serializer must tolerate overlapping notes, not dedup them. (d) C-07: a pitched note attacked <60 ticks before a boundary loses its attack (all sub-60 retrigger segments drop); reference banks' shortest pitched note is 120 ticks so none vanish, but stay mindful of short pushed hits near boundaries.
>  - **`parts/dynamics.py`** — `apply_velocity` (§3.4, round3 half-even + clamp), `apply_articulation` (comping + pattern-bass only — gate via `articulation_scales(role, bass_walking=...)`), `is_event_active` (§3.5 gating). Walker/drums/pads are articulation-exempt.
>  - **Reference banks** (`styles/{pop_rock,jazz}/patterns/*.yaml`) fully authored per §7; both load clean.
>
> **Open items for Chunk 2/3 (decide, don't re-pin):**
>  - **[C-04]** (open) — Chunk-3 voicing pass: confirm keyless `quartal`=perfect-4ths (or widen `voicing_candidates` to pass a key); pass the **real lane anchor** to `optimal_voicing_path` (§6.4 anchor = `lane.high−6`); candidate-class-per-role so triads never hit 4-note seventh-chord classes.
>  - **[C-06]** — Chunk 2's `arrange()` + `lanes.yaml` now owns the ≤71 ceiling + registerBias clamp (§4.3), enforced on every non-drum entry (`test_arrange.py`); retarget folds within whatever lane it is handed and trusts it. Marker-gating half of C-06 (loader PT enforcement) stays open.
>  - **Serializer (Chunk 4)** — dump `TrackDocument` with `exclude_none=True` (§3.5/§3.6 require absent midi/voice/maxPolyphony).
>
> **Phase 4 is COMPLETE** (sessions 04+05; §14 DoD 1–10 PROVEN; harmony stage committed). Env/gates unchanged: `uv`, four gates, TID251 determinism. **CAVEATS:** C-01…C-04 (prior), C-05 (PT2 order, resolved), C-06 (marker-gating, open), C-07 (§3.3 resolutions, open), C-08 (jazz ride band, open).
>
> **What Phase 4 hands Phase 5 (all committed, tested):**
>  - **`HarmonicPlan`** (`schema/ir.py`): `chords: [ChordEvent{start_tick, duration_ticks, section_id, chord: ChordSpec, scale: EventScale{root_pc,name}, function: "T"|"S"|"D"|"O", tags: [str]}]`, `keys: [KeyRegion{start_tick,tonic_pc,mode}]` (one region, tick 0, v1), `pool_selections: {str:str}`. Events tile `[0, total_bars×1920)` gaplessly; `scale` is the §7.4 hint Phase 5 uses for `tension`/`approach`/walking-bass passing tones; `function` drives comping/bass role logic.
>  - **Theory library** (`trackgen.theory`): `resolve_token`, `chord_function`, `chord_scale→ScaleHint`, `chord_symbol`, `chord_tones`/`guide_tones`, `scale_pcs`, `legal_extensions`/`extensions_legal`; **voicing** `voicing_candidates(spec, cls, lane)`, `vl_distance(a,b,w)`, `optimal_voicing_path(specs, candidates_fn, weights, *, anchor=None)`. Phase 5 owns *policy* over these (candidate-class-per-role, cost-weight tuning) per D11.
>  - **`harmony()`** takes its `rng` as a parameter (`seeds.Rng` alias); the pipeline orchestrator passes `stream_rng(master, overrides, "harmony")`. Follow the same injected-rng convention if Phase 5 stages need test-injected streams.
>
> **Open items Phase 5 must resolve (don't re-pin, decide):**
>  - **[C-04]** (open) — the voicing goldens land in **PHASE_5 §13.6**: confirm the keyless `quartal` = perfect-4ths reading (or widen `voicing_candidates` to pass a key/scale); pass the *real* lane anchor to `optimal_voicing_path`; decide candidate-class-per-role so triads never hit 4-note seventh-chord classes (`rootless_a/b`/`drop2` degrade on triads today).
>  - **[C-03]** (open) — P8 admits the SubV `bII7`; a future PHASE_4 §4.3 reword folds it into the plain check. The harmony stage does **not** re-derive dominant-functioning (it consumes P8-validated turnarounds), so nothing new for Phase 5 here.
>  - **Serializer (Phase 5)** must dump `TrackDocument` with `exclude_none=True` — document models emit `null` for absent `midi`/`voice`/`maxPolyphony`, but §3.5/§3.6 require those ABSENT.
>  - **Pack models enforce `extra="forbid"`** — Phase 5's new envelope/event fields (`push`/`minDensity`, degree tokens) must be added to `packs/models.py` explicitly.
>
> **Phase-4 review nits carried forward (non-blocking, NOT fixed — decide only if activated):**
>  - **Deceptive substitute function** — the dormant deceptive path emits `bVI`→function `S` in minor keys (vs `vi`→`T` in major); §5.4 pins only the substitute *chord*, not its function, so this is spec-consistent, but if **Phase 8** activates doubled final choruses (PHASE_3 Q2 / PHASE_4 Q7), decide whether the minor deceptive chord should read `T`.
>  - **P4 runtime guard** — the stage's assembly trusts loader-P4 (pool-entry per-label bar count == form bar-option length) with no runtime assertion; sufficient today, but a future *form-stage* regression would silently gap/overlap rather than fail loudly. Consider a guard if the form stage changes.
>  - **`final_index = next(...)`** raises a bare `StopIteration` if a form had no `ending` section (upstream guarantees exactly one; clarity-only).
>
> **Env / gates (unchanged):** `uv` manages Python 3.12.13; four gates green (`uv run pytest` · `ruff check` · `ruff format --check` · `mypy`); determinism enforced by TID251 (entropy only in `seeds.py`); integer weights + ordered candidate lists throughout. **CAVEATS:** C-01 (`PARAM_MALFORMED`), C-02 (form ladder unreachable, resolved), C-03 (SubV in P8, open), C-04 (voicing API, open). The turnaround-truncation fix in `abc447e` was own-code (not a caveat).

*(The orchestrator rewrites this block at every close-out — and mid-session on any pause — stating: current phase/chunk, last completed task + commit, and the exact next action.)*

## Phase status

| Phase | Scope | Status | Sessions | Notes |
| --- | --- | --- | --- | --- |
| 1 | Foundations & contracts | done¹ | 01 | ¹Code/automated DoD complete; §9.6 manual listening check awaits user audition of the playground |
| 2 | Parameter & mood model | done | 02 | All 8 DoD items proven; 245 tests green. Caveat C-01 (PARAM_MALFORMED) |
| 3 | Form & structure | done | 03 | All 8 DoD items proven; 339 tests green at 0122149. Caveat C-02 (ladder unreachable) resolved in post-review fix batch (349 tests) |
| 4 | Harmony engine | done | 04, 05 | All 10 DoD proven. Chunk 1 (SESSION_04: theory+dressing+loader; DoD 1/2/3/8). Chunk 2 (SESSION_05: stage+goldens; DoD 4/5/6/7/9/10). 4-lens whole-phase review clean. 644 tests. No new caveats (turnaround-truncation fix was own-code) |
| 5 | Rhythm-section part generators | in progress | 06, 07 | 4 chunks: loaders/foundations [06 DONE, DoD 1+2] → arrangement+selection [07 DONE, DoD 3+4, 816 tests] → generators/walker/voicing [next] → orchestrator+Serializer+milestone |
| 6 | Transitions, variation & humanization | not started | — | |
| 7 | Sound design | not started | — | |
| 8 | Quality, evaluation & pack expansion | not started | — | Multi-session, hard order: tooling → reference-pack refinement → chill_lofi → blues → fusion_jazz. Calibration bootstrap order per PHASE_8 §8.1 |

## Session log

One row per implementation session, appended at close-out. Session plan files live in `plans/sessions/SESSION_NN.md`.

| Session | Date | Phase / chunk | Outcome | Key commits |
| --- | --- | --- | --- | --- |
| 01 | 2026-07-14 | Phase 1 (all) | All 6 tasks built, reviewed, gates green (125 tests). DoD §9.1–§9.5 + §9.7 proven; §9.6 manual audition pending user. No CAVEATS (all §5.6 goldens reproduced exactly; no doc amendments). | e0643ee seeds · 5d32e8c schema · 41e3af8 packs · 7fc3a5f validator+export · 6fbaa7c fixture · cf2b490 playground · e27f704 review-fixes |
| 02 | 2026-07-15 | Phase 2 (all) | 6 tasks built, per-task + 4-lens whole-session review, gates green (245 tests). All §11 DoD 1–8 proven; both §6.5 goldens reproduce field-for-field; orchestrator pre-verified every load-bearing sample. Contract lens COMPLIANT. Review fixes: malformed-type wrapping (C-01), pack-tonic validation, mode-ladder dedupe, 3 test-coverage gaps closed. | 74e57b5 plan-fields · 2ab6997 moods · 8fe953f packs+refs · 2c0c602 params · 26f39a0 interpreter · eb00804 review-fixes |
| 07 | 2026-07-16 | Phase 5 chunk 2 (arrangement + selection) | 3 opus tasks (T1 arrange ‖ T2 selection, then T3 goldens) + 1 review fix. Per-task reviews all APPROVE / APPROVE-WITH-NITS. Whole-chunk 2-lens review (correctness/contract + test-quality/DoD): both APPROVE-WITH-NITS, **DoD 3+4 PROVEN**, no blockers, no frozen contract touched. Orchestrator verified four gates green (816 tests) + independently reproduced the §4.5 anchors (densities/rungs/registers) and §9.1 counts (pop 1 / jazz 3). One test gap closed (production `rng_factory=None` select path golden-locked to §9.1 winner ids — no divergence). Two correctness nits proven non-reachable in v1 (adjacent-intro count read; extreme-bias lane span) → handoff notes, no caveats. | d52a00e arrange+lanes · 71ac7a7 selection · cbfaa19 §9.1 goldens · eecb17b golden-lock fix |
| 06 | 2026-07-16 | Phase 5 chunk 1 (loaders + foundations) | 4 tasks + T1b (all opus): T1 schema/loader/PT1-11, T1b bank-retarget default, T3 foundations, T2 reference banks. Per-task + 2-lens whole-chunk review (contract/integration + test-quality/DoD — both APPROVE-WITH-NITS, **DoD 1+2 PROVEN**, no blockers). Two per-task blockers caught+fixed: T1 PT2 non-decreasing rejected the normative voice-grouped §7 banks (C-05); T2 pr_dr_3 rung-3 bar-2 groove dropout. Reviewers re-derived every §3.3 degree/fallback + the §9.4 E2=40 anchor + all §9.1 candidate counts. Orchestrator verified all 11 §12 amendments present (no edits). 4 caveats: C-05 (PT2, resolved), C-06 (marker-gating), C-07 (§3.3 resolutions), C-08 (jazz ride band). Gates green (735 tests). | 60c6289 schema · 4299062 retarget-default · 095d0e1 foundations · 4e131c2 banks · 5edb8d3 polish |
| 05 | 2026-07-16 | Phase 4 chunk 2 (stage + goldens) | 3 tasks (T1 schema opus, T2 stage opus, T3 goldens opus) + orchestrator §13 check. Per-task + 4-lens whole-phase review (correctness/contract/test-quality/code-quality) across both chunks — all clean/COMPLIANT/GOOD, zero confirmed bugs. **DoD 4/5/6/7/9/10 PROVEN**; full §14 DoD 1–10 complete. Gates green (644 tests). Orchestrator independently reproduced seed anchor + both §10 `pool_selections` + Ex1 sample event + final tags + ASCII symbols + event counts (76/56). T3 surfaced + fixed a real stage tiling bug (own-code, not a caveat); review-fixes brought DoD-7 matrix to the pinned 25 seeds + added DoD-6 budget append-only. §10.2 Ex2 = 56 events (64 bars hold-merged; §10.2 pins no event count). | 09335d9 schema · 35dccba stage · abc447e goldens+fix · 8f15843 review-fixes |
| 04 | 2026-07-16 | Phase 4 chunk 1 (theory+dressing+loader) | 4 tasks (T1 opus, then T2/T3/T4 parallel opus). Per-task + 2-lens whole-chunk review; both lenses APPROVE-WITH-NITS, DoD 1/2/3/8 PROVEN. Gates green (587 tests). Orchestrator reproduced §5.6 seed vectors + all 10 §10 per-chord facts exactly. Reviews: T1 sus-case fix; C-03 (SubV in P8, user-approved A); C-04 (voicing API); lane-prune non-emptiness fix. Chunk 2 (stage+goldens) remains. | 21ce323 theory-core · 6cc5907 voicing · ee7ddb6 dressing · bb7114e progressions |
| 03 | 2026-07-15 | Phase 3 (all) | 5 tasks (T1–T3 parallel, T4 opus integration, T5 docs). Per-task + deep-T4 + 2-lens whole-session review; both whole-session lenses "contract-clean, all DoD PROVEN". Gates green (339 tests). Orchestrator pre-verified every §7.4 sample (seed vectors, 13 energy cells, both fitting totals, full 8-draw/1-draw sequences) — no doc amendment. Review fixes: F8/F9/eligibility completeness (T2), energy-order discriminators (T3), fallback tag_bars clamp + property rigor (T4), F4 fixture + variant assert (0122149). Caveat C-02: ladder proven unreachable, §11.7 via substitute coverage. | 474c273 schema · 2d4f5a9 forms-loader · 66725bf energy · 5c47b75 form-stage · 0122149 review-fixes |

## Phase detail

When a phase enters `planning`, the orchestrator adds a `### Phase N` section here containing: the approved chunk plan (if split), the task checklist with per-task status and commit hashes, DoD checklist with evidence as items are proven, and links to relevant CAVEATS entries. Keep entries terse — evidence pointers, not narrative.

### Phase 5 — Rhythm-section part generators (chunk plan)

**Split into 4 chunks** (phase too large for one session; ROADMAP §4 seam; PHASE_5 §1). Seams:

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
| T5 | Whole-chunk 4-lens review + DoD 5/6/7 checklist + C-04 resolution + close-out | orchestrator | not started | — |

Targets **DoD 5** (§13.5 walker), **DoD 6** (§13.6 voicing), **DoD 7** (§13.7 generators
end-to-end). Resolves **C-04** (voicing API). Out of scope: orchestrator/Serializer/timbres/
milestone/whole-document goldens (Chunk 4, DoD 8/9/10).

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
