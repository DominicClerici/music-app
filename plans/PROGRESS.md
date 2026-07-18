# Implementation Progress

Source of truth for implementation state across sessions. The orchestrator (see `PROMPT.md`) updates this file **immediately** at every task completion and step transition — never batched to session end. A new session must be able to resume losslessly from this file plus git log.

Statuses: `not started` · `planning` · `in progress` · `blocked` · `done`

## Handoff — next session starts here

> **Next:** **Phase 7 — Sound design, session 14 = Chunk 2 (the flip + integration + whole-phase).**
> Read `ROADMAP.md`, `PHASE_7.md` in full + this handoff; **Chunk 1 is COMPLETE** (session 13). C2 is
> the atomic flip — resume from the Phase-7 chunk plan below. **Get user approval on the C2 task plan
> before dispatching implementers** (PROMPT step 1) since C2 is a large integrated landing.
>
> **Phase 7 — Chunk 1: COMPLETE** (session 13). New `src/trackgen/sound/` package landed, **all
> unwired**; four gates green (**4364 tests**). **DoD 2, 3 PROVEN in full; DoD 1 PROVEN for its C1
> slice.** Whole-chunk 2-lens review CLEAN (no blocker/major). Two review fixes, both tighten-to-design
> (D4 drum-attackHardness bar; §4.2 send base-XOR-mod) — **no new CAVEATS.**
>
> **What C1 hands C2 (all committed, tested, UNWIRED):**
>  - `src/trackgen/sound/models.py` — `MappingEntry` (`{param,min,max,curve}`; curve enum; `exp⇒min,max>0`;
>    inverted ranges legal).
>  - `sound/allowlist.py` + `allowlist.yaml` (D12) — `load_allowlist()` → `is_legal(cls, path)`; seeded
>    fully-expanded, **coverage-proven against §5.1 + §8.1/§8.2 recipes + all 3 committed fixtures**, so
>    C2's TB3/TB4/TB7 will not false-reject the real content. (Un-seeded classes DuoSynth/PluckSynth +
>    unused effects enter by amendment when first used.)
>  - `sound/mod_defaults.py` + `mod_defaults.yaml` — §5.1 verbatim; `load_mod_defaults()`.
>  - `sound/evaluate.py` — `round3`/`evaluate_mapping`/`merge_mod`/`assert_base_xor_mod`/
>    `apply_directives` + `get_by_path`/`set_by_path`. Reproduces the §9.1 anchors.
>  - `sound/timbres.py` — the **real** `timbres.yaml` schema + TB1–TB9. TB1 is the standalone
>    `check_flavor_completeness(timbres, declared)`; TB7 checks the **effective** (defaults-merged)
>    mapping + the §4.2 send-XOR.
>
> **C2 must do (the flip, one integrated landing):** author the full real `styles/{pop_rock,jazz}/
> timbres.yaml` (complete the §8 abridged entries — every §9-depended value stated in §8/§9); swap
> `packs/loader.py::resolve_pack` to `sound.timbres.TimbresConfig` + wire TB1 live vs `interpreter.yaml`
> ("both reference files load clean") + retype `StylePack.timbres`; write `sound_design(plan, pack) →
> SoundDesign` (§7; `{trackSounds:{id:{instrument,effects,channel,sends}}, buses, master}`) **reusing
> the C1 private normalization/keying helpers** (handoff note above); wire orchestrator + Serializer to
> consume `SoundDesign` for `channel`/`sends`/`buses`/`master` and **delete** `_STUB_MIX`/
> `_MASTER_EFFECTS`/stub-`buses` + `pipeline/stubs.py::sound_design` + the stub `packs/models.py::
> TimbresConfig`; **re-bless both whole-document goldens (dedicated commit, arbitration rule 3)**; §9.1/
> §9.2 stage goldens field-for-field (full patches/channels/sends/bus/master vs full-precision recompute
> — note pop bass `envelope.attack` round3=**0.005**); zero-draw determinism (`sound` stream shim = 0
> draws + repeated-run identity); property matrix (both packs × supported moods × every declared flavor
> combo → whitelist/allowlist/V7/sends→reverb/volumeDb≤6/pan∈[−1,1]/bus-decay-in-range/master-ends-
> Limiter); whole-PHASE 4-lens review; **full DoD 1(complete)/4/5/6/7/8(user audition)/9** + §12
> amendment audit.
>
> **Env / gates:** `uv` manages Python 3.12; four gates (`uv run pytest` · `ruff check` · `ruff format
> --check` · `mypy`); full suite **~7m25s / 4364 tests** — run pytest with an extended timeout.
> Determinism enforced by TID251 (entropy only in `seeds.py`). **CAVEATS:** unchanged from Phase 6
> (C-01/02/04/05/09 resolved; C-03/06/07/08/10/11/12 open — all latent/prose, none block Phase 7).
> **Phase 6 §11.10 listening audition still pending user** (does not block Phase 7). **Phases 1–6
> COMPLETE**; their contracts consumed unchanged.
>
> **Phase 6 — Transitions, variation & humanization: COMPLETE** (sessions 10, 11, 12). Both stages are
> now **wired and live** in the pipeline. Full §11 DoD 1–11 proven (session-12 4-lens whole-phase review:
> correctness / contract / test-DoD / code-quality — **no blocker, no major**); **4315 tests**, four
> gates green. **DoD 10's §11.10 listening audition awaits user confirmation** (like PHASE_1 §9.6) — all
> code/automated DoD is complete; the human ear-check is the only open item and does not block Phase 7.
>
> **What Phase 6 hands Phase 7 (all committed, tested):**
>  - **The pipeline now runs the REAL stages 6 + 7:** `generate_track` chain is `generate_plan → form →
>    harmony → arrange → select_patterns → generate×4 → transitions(REAL) → humanize(REAL) →
>    sound_design(STUB) → serialize`. Only `sound_design` remains a stub — **that is Phase 7's job.**
>  - **The stub Phase 7 REPLACES:** `pipeline/stubs.py::sound_design(plan, pack) -> dict[str, TrackSound]`
>    — reads `pack.timbres` (provisional `timbres.yaml`), selects each role's flavor from
>    `plan.role_flavors`, returns one `TrackSound{instrument, effects=[], midi}` per track id. The
>    Serializer currently applies the **§8.3 stub mix** (`_STUB_MIX` in `pipeline/serialize.py`: kick −2 /
>    drums −4 / bass −3 / comping −6 / pads −10; pans; no buses; master Compressor+Limiter). PHASE_5
>    §8.3 is annotated "**Superseded by PHASE_7 §7**" — Phase 7 replaces the stub channel/mix/master with
>    the sound-design stage's per-track `channel`/`sends`, the `reverb` bus, and the pack master chain.
>  - **`crash` track now fully emitted:** stage 6 produces entry crashes + the HOLD final hit; the C3
>    wiring gave it a stub timbre (`crash` in both `styles/*/timbres.yaml`, **trigger midi 84**,
>    MetalSynth) + a `_STUB_MIX["crash"]` row. Phase 7's real `timbres.yaml` owns the crash patch.
>  - **`header.tempos` is now multi-event:** the jazz milestone carries **40 entries** (base 69 + 39
>    ritard). `serialize` gained an additive keyword `tempo_events`.
>  - **Reserved seed stream:** the `sound` stream is reserved, makes **zero** draws today; Phase 7 draws
>    on it if it needs entropy (append-only, draw-iff-≥2).
>  - **Tags** contributed so far: `"push"`, `"ghost"` (P5), `"fill"`, `"crash"`, `"var"`, `"hold"` (P6).
>    All are **serialize-dropped** — `NoteEvent` has no `tags` field (client contract untouched).
>
> **Regression surface:** the two committed whole-document goldens (`fixtures/{pop_rock,jazz}.milestone.
> trackdoc.json` + `tests/test_whole_document_goldens.py`) now reflect the REAL stages 6+7 output. Phase 7
> changes only `meta`/`instrument`/`effects`/`channel`/`buses`/`master` (sound), **not** the note-structural
> or timing content — but it WILL change the serialized instrument/mix fields, so **re-bless the two
> fixtures** in a dedicated commit when Phase 7 lands (ROADMAP §3 rule 3 bless-in-spirit), same discipline
> as C3's T2. The `test_phase6_property.py` matrix (1575 docs) and all stage-6/7 goldens are the note/timing
> regression guard — they must stay green through Phase 7.
>
> **Env / gates:** `uv` manages Python 3.12.13; four gates (`uv run pytest` · `ruff check` · `ruff format
> --check` · `mypy`); full suite **~7m20s / 4315 tests** — run pytest with an extended timeout. Determinism
> enforced by TID251 (entropy only in `seeds.py`); integer weights + ordered candidate lists throughout.
> **CAVEATS:** C-01 (resolved), C-02 (resolved), C-03 (SubV in P8, open), C-04 (resolved), C-05 (resolved),
> C-06 (marker-gating loader half, open), C-07 (§3.3 sub-60 drop, open — latent), C-08 (jazz ride band
> prose, open — no behavior impact), C-09 (resolved), C-10 (thin Serializer no coincident-same-voice-drum
> de-dup → latent V3, open — Phase-6 confirmed unreachable across the 1575-doc matrix; **a natural Phase-7
> Serializer guard point**), **C-11 (drum voice/`ornament` provenance tags, serialize-invisible, open)**,
> **C-12 (§3.7 entry-crash velocity has no floor → latent velocity-0 `PhraseNote` if a pack sets
> `crash.velocity` lo=0 entering an energy-0 section; unreachable in v1, open)**. **Deferred cleanup**
> (works in `parts/`, still open): consolidate `_fold_into_lane` + `_third_pc`/`_fifth_pc` duplicated
> between `parts/walker.py` and `parts/retarget.py`. **Phase-6 defer notes** (session-12 review, low
> priority): mutation.py magic literals (`_OFFBEAT_8TH`=240 / hat_open dur 360 / pickup tol 120), a shared
> builder-finder helper, the `drop_ornament` implicit tie-break comment, recomputing the ritard's 28
> interpolated events from the closed-form curve in-test, mechanizing the §11.10 byte-diff check.
> **Phases 1–5 COMPLETE**; their contracts are consumed unchanged.

*(The orchestrator rewrites this block at every close-out — and mid-session on any pause — stating: current phase/chunk, last completed task + commit, and the exact next action.)*

## Phase status

| Phase | Scope | Status | Sessions | Notes |
| --- | --- | --- | --- | --- |
| 1 | Foundations & contracts | done¹ | 01 | ¹Code/automated DoD complete; §9.6 manual listening check awaits user audition of the playground |
| 2 | Parameter & mood model | done | 02 | All 8 DoD items proven; 245 tests green. Caveat C-01 (PARAM_MALFORMED) |
| 3 | Form & structure | done | 03 | All 8 DoD items proven; 339 tests green at 0122149. Caveat C-02 (ladder unreachable) resolved in post-review fix batch (349 tests) |
| 4 | Harmony engine | done | 04, 05 | All 10 DoD proven. Chunk 1 (SESSION_04: theory+dressing+loader; DoD 1/2/3/8). Chunk 2 (SESSION_05: stage+goldens; DoD 4/5/6/7/9/10). 4-lens whole-phase review clean. 644 tests. No new caveats (turnaround-truncation fix was own-code) |
| 5 | Rhythm-section part generators | done | 06, 07, 08, 09 | All §13 DoD 1–11 PROVEN; 990 tests, four gates. 4 chunks: loaders/foundations [06, DoD 1+2] → arrangement+selection [07, DoD 3+4] → generators/walker/voicing [08, DoD 5+6+7, C-04 resolved, C-09 arbitration] → orchestrator+Serializer+milestone [09, DoD 8+9+10, whole-phase review CLEAN/COMPLIANT/PROVEN/GOOD, C-10 latent logged]. §9.5 listening checklist CLOSED (user-confirmed 2026-07-17) |
| 6 | Transitions, variation & humanization | done¹ | 10, 11, 12 | 3-chunk split (D1 seam). C1 stage-6 Transitions (10: DoD 1+3+4+8; C-11) → C2 stage-7 Humanizer (11: DoD 2+5+6) → C3 wiring+milestone+whole-phase (12: DoD 9+10+11). All §11 DoD 1–11 proven; 4-lens whole-phase review no blocker/major; **4315 tests**, four gates. Caveats C-11, C-12 (both latent/open). ¹§11.10 listening audition awaits user (like Phase 1 §9.6); all code/automated DoD complete |
| 7 | Sound design | in progress | 13 (C1) | **2-chunk split** (flip seam). **C1 DONE** (session 13): new `sound/` package — engine data + evaluation model + real `timbres.yaml` schema/TB1–TB9, all unwired; DoD 2/3 PROVEN + DoD 1 (C1 slice); whole-chunk review CLEAN; 2 tighten-to-design fixes, no caveats; 4364 tests. C2 (session 14): flip content+loader+stage+wire, re-bless goldens, §9 goldens, property matrix, whole-phase review (DoD 1-complete/4/5/6/7/8/9) |
| 8 | Quality, evaluation & pack expansion | not started | — | Multi-session, hard order: tooling → reference-pack refinement → chill_lofi → blues → fusion_jazz. Calibration bootstrap order per PHASE_8 §8.1 |

## Session log

One row per implementation session, appended at close-out. Session plan files live in `plans/sessions/SESSION_NN.md`.

| Session | Date | Phase / chunk | Outcome | Key commits |
| --- | --- | --- | --- | --- |
| 13 | 2026-07-17 | Phase 7 chunk 1 (foundations) | 3 opus tasks (T1 engine data → T2 evaluation model → T3 real timbres schema/TB1–TB9, serial) + T4 whole-chunk 2-lens review. New `src/trackgen/sound/` package, **all unwired** (`resolve_pack`/`pipeline/`/reference `timbres.yaml` untouched; pipeline still runs the stub). **DoD 2, 3 PROVEN full; DoD 1 PROVEN (C1 slice).** Per-task + whole-chunk review. Whole-chunk 2-lens (correctness/contract + test-quality/DoD): **both CLEAN** — correctness traced TB7 **live** through `TimbresConfig.model_validate` for the off-class §8 flavors (FM piano/upright, AM organ_soft) confirming §8 will validate in C2 with no false rejection + illegal params rejected; §5.1 faithful (zero arbitration flags); allowlist covers §8 by full dry-run. Test lens PROVEN (no vacuous tests; half-even ties on 1/16 & 3/16, effective-mapping base-XOR-mod discriminating). 2 review fixes, both **tighten-to-design** (D4 drum-attackHardness bar; §4.2 send base-XOR-mod) — **no new caveats.** Four gates green (**4364 tests**). C2 = the flip. | b86be4e engine-data · aeaf047 evaluate · acd87f4 timbres+TB · 8715ded review-fix(send-XOR) |
| 12 | 2026-07-17 | Phase 6 chunk 3 (wiring + milestone + whole-phase) — **Phase 6 COMPLETE** | T1 wire real stages 6/7 + thread `tempoEvents` + crash serialize (`_STUB_MIX`/timbre midi 84/guard) + re-pin draw totals (pop 10277 / jazz 5304, decomposed against per-stage goldens) → then T2 ‖ T3 → T4 (audition) → T5 (whole-phase review + close-out). Per-task + **4-lens whole-phase review** (correctness / contract / test-DoD / code-quality across all 3 chunks): **no blocker, no major** — all clean/COMPLIANT/PROVEN/GOOD-WITH-NITS. **Full §11 DoD 1–11 PROVEN**; **DoD 11 §10 amendment audit** confirmed all 10 amendments present+consistent (ROADMAP §2/§3/§4, PHASE_1 §4/§4.5/Q5/§6, PHASE_5 PT12/§8.2/§8.1/§8.3, PHASE_2 §7.2). T2 re-blessed both whole-doc goldens (dedicated commit; 29/29 arbiter checks, jazz 40-entry tempo map, no §7 divergence). T3 property matrix = **1575 fully-wired docs** all §11.9-clean; P1-latent 0 trips, C-10 0 V3. Review fixes: stale mid-chunk docstrings refreshed, `BEAT` single-sourced, **C-12** logged (entry-crash velocity-0 latent). **DoD 10 §11.10 listening audition pending user** (all automated DoD complete). Four gates green (**4315 tests**). | 6c05caf wire · c6e81fc re-bless · 373cfdc+8fa46ac property · b3756ba review-fixes+C-12 |
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
| T4 | Milestone regen + Phase-1 playground audition + §11.10 checklist (**USER AUDITION GATE**, DoD 10) | opus | awaiting user | — |
| T5 | Whole-PHASE 4-lens review (all 3 chunks) + full §11 DoD 1–11 + DoD 11/§10 amendment audit + close-out (→ Phase 7) | orchestrator | done | b3756ba |

**Chunk 3 COMPLETE — Phase 6 COMPLETE.** T1 (wire) → T2 ‖ T3 → T4 (audition) → T5 (review + close-out).
Fixtures re-blessed through the real stages 6+7; the pipeline runs the real Transition engine +
Humanizer end to end (only `sound_design` remains a stub → Phase 7). **4-lens whole-phase review across
all 3 chunks — no blocker, no major.** Four gates green (**4315 tests**).

**T4 (DoD 10) — playground-ready, listening audition PENDING USER.** Both re-blessed fixtures load in the
Phase-1 playground (all instruments whitelisted incl. the new `crash`=MetalSynth; the 40-event jazz
ritard schedules as a real tempo ramp via the tick→seconds walk). Automated portion PROVEN (stubs
deleted, real stages wired, fixtures re-serialize identically). The §11.10 ear-check (fills→crash, ritard
reads as slowing, pop ending rings+releases, no byte-identical bar, swing survives ritard) awaits user
confirmation — logged pending like PHASE_1 §9.6; does not block Phase 7.

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
- [~] **10 Milestone** (C3) — automated portion PROVEN (`c6e81fc` re-bless; `test_whole_document_goldens.py`
  re-serialize identically; stubs deleted; playground-loadable verified). **§11.10 listening audition
  pending user** (like PHASE_1 §9.6).
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
