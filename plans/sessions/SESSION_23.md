# SESSION_23 — Phase 8, Chunk 9: validator & coverage close-out

**Status:** APPROVED (S23-0…S23-10 ratified 2026-07-21) — IN PROGRESS.

### Task ledger

| Task | Status | Commit | Note |
|---|---|---|---|
| T8 CI | **done** | `33eb3fd` | real CI run unverified until the user pushes |
| T3 Part B artifacts | **done** | `a1fcdd0` | pop_rock 20 / jazz 18 leaves regenerated |
| T3 Part A byte-repro | **done** | `7a59a9d` | all 5 packs reproduce |
| T4 `_packmatrix` | **done** | `2835e4b` | drop-in proven over 1890 plan cells |
| T1 L2-1 grain | **done** | `5c28790` | APPROVE-WITH-NITS + 1 fix cycle; 2 memo mutants killed |
| T5+T6 §14.9 + suppression | **done** | `f0e…` | APPROVE-WITH-NITS + 1 fix cycle; 3/3 mutants killed |
| **T2 quartal widening** | **done** | `899a0b9` | **S23-2 resolved as option D — see §3a-FINAL.** APPROVE-WITH-NITS, **0 mutation survivors**; C-30 RESOLVED, C-32 added |
| T7 smoke matrix ×5 | **done** | `b99a61b` | **§14.6 MET both clauses**; 3 green runs, no flakiness; **C-33 NEW** |
| T9 doc debt | **done** | (this commit) | **C-31 created** (the reserved gap); C-19/C-30/C-33 resolved; §8.1 + §13 fixed |
| T10 chunk review | pending | — | 3 lenses |

Gates green at every commit; suite **6513 → 11018**.

**S23-12 (orchestrator ruling, user-authorized 2026-07-21): ACCEPT chill_lofi's length ceiling.**
Same question S19-3 answered for pop_rock (C-19): lo-fi is loop music, a ~3-minute ceiling is
in-genre, and raising `forms.yaml` repeat bounds to force 8-minute lo-fi tracks would amend
pinned data against the pack's character — the reasoning C-22 used when accepting the pads
dormancy rather than raising the energy ceiling. C-33 resolved.

**Three orchestrator errors corrected at T9 — recorded, not tidied away:**
1. **C-31 was reserved and never written.** The number was verbally assigned to T1's grain fix,
   then two later agents were told "do not create C-31" — so the sequence ran C-29, C-30, C-32,
   C-33 with a hole, and **the F1 deviation had no caveat at all**. Concretely harmful:
   `measure_l2_1`'s docstring already cited "S23-1, C-31", i.e. **code referencing a caveat that
   did not exist**. A reserved number with no entry is exactly as lost as an unlogged deviation.
2. **The 8.11 % exposure figure did not reproduce.** It came from T2's review, was passed on by
   the orchestrator unverified, and reached a binding doc. Three sweeps now disagree: **6.01 %**
   (orchestrator, 118 123 measured notes — the largest sample), 8.11 % (T2 review), 12.74 % (T9,
   10 270 notes). §8.1 now states the spread and instructs re-measurement rather than citing a
   number. **The 0 % on the other four packs is exact, structural, and reproduced in all three**
   — that is the load-bearing claim.
3. **"0 differing rows in 1750" was a transcription slip** in this plan's S23-8; the commit and
   `tests/test_quality_layer2.py:387` both say **1740**. Corrected throughout.

**Pre-existing, recorded so it is not rediscovered as new** (T2 review, no action): a pushed hit
sounds the *next* chord's voicing while `governing_chord(note.ticks)` returns the current one, so
in principle a pushed hit's widening decision uses the wrong section. Pre-existing property of
L2-1's allowed-set model, and pushes are anticipations landing *off* the `{0, 960}` residues
L2-1 measures.

**Phase:** 8 (Quality, evaluation & pack expansion). **Chunk:** 9 of a proposed 10.
**Baseline at session start:** `e849aa8`, four gates green — **6513 passed, 1 skipped**;
ruff check clean; 151 files formatted; mypy clean on 151 source files.

> **Baseline correction for the record:** the suite runs **~45 s**, not the ~34 s carried in
> PROGRESS.md's handoff block. Measured twice this session (45.07 s by the scoping agent on an
> idle machine; 88 s under three concurrent subagents). PROGRESS.md is corrected at close-out.

---

## 0. Why this chunk splits

The C8 handoff pinned C9 as the final chunk, scoped as: five-pack property tests, milestone
rubric, A/B harness demo, §13 amendment audit, whole-phase 4-lens review, final DoD sweep.
Scoping found that scope to be **two sessions of work, with a natural seam**, for three reasons:

1. **Three previously-unknown defects surfaced**, all in the validator/coverage surface this
   chunk was meant to *certify* (§1 below). Repairing them is prerequisite to any honest DoD
   claim, and none was in the C8 handoff's list.
2. **The listening obligations need tooling that does not exist.** DoD §14.8 wants "the A/B
   harness demonstrated on one real change" — there is no A/B harness anywhere in the repo
   (zero matches for `a/b`, `pairwise`, `blinded`, `binomial` across `src/` and `tests/`). The
   milestone rubric has no anchor text, no schema, and no capture format. Both must be *built*
   before the user can *do* anything.
3. **The human listening block is 3.5–5 hours** across five obligations (§5), and its quality
   degrades badly if crammed — the rubric especially.

**Proposed seam:** C9 (this session) takes everything machine-verifiable and lands DoD §14.6 +
§14.9. C10 (session 24) takes coverage depth, the listening tooling, the user listening block,
the whole-phase 4-lens review, and the final DoD sweep. **This split needs user ratification
(decision S23-0) — it changes the pinned chunk plan.**

---

## 1. Findings that reframe this chunk

Three defects were found at scoping, each verified independently by the orchestrator after the
reporting agent raised it. All three sit in the surface Phase 8's DoD is about to certify.

### F1 — L2-1 measures the wrong grain, and is vacuous for 2 of 5 packs (**NEW, unlogged**)

`quality/layer2.py:141-158` iterates `doc.tracks` — the **post-humanizer** document — and keeps
only notes where `note.ticks % 1920 in strong`. The humanizer has already displaced those
onsets, so the filter discards most of the population. When nothing survives, `total == 0`
triggers a silent `continue` (`:158`) — a **vacuous pass**, not a skip that anyone can see.

Orchestrator-measured, 12 renders per pack (4 moods × 3 seeds, 180 s), strong-beat notes
surviving into the document vs present at stage 6:

| pack | role | doc | stage 6 | retained | renders where the check is skipped |
|---|---|---|---|---|---|
| pop_rock | bass | 100 | 767 | 13.0 % | 0/12 |
| pop_rock | comping | 207 | 3111 | 6.7 % | 0/12 |
| jazz | bass | 107 | 808 | 13.2 % | 0/12 |
| **jazz** | **comping** | **0** | **1740** | **0.0 %** | **12/12** |
| **chill_lofi** | **comping** | **0** | **2846** | **0.0 %** | **12/12** |
| chill_lofi | bass | 33 | 668 | 4.9 % | 0/12 |
| blues | bass | 125 | 914 | 13.7 % | 0/12 |
| blues | comping | 115 | 2021 | 5.7 % | 0/12 |
| fusion_jazz | bass | 161 | 876 | 18.4 % | 0/12 |
| fusion_jazz | comping | 158 | 2076 | 7.6 % | 0/12 |

§8.1 calls L2-1 "the highest-signal single metric for retargeting/voicing bugs." It reads
**5–18 %** of the notes it is defined over, and **zero** for jazz and chill_lofi comping.
Layer 1's W7 handles this correctly by reading `phrases_stage6` (`quality/layer1.py:442`);
L2-1 simply never got the same treatment. Same defect class as C-29 — the gate under-modelling
its own subject. **DoD §14.4b must not be recorded PROVEN until this is resolved.**

### F2 — the smoke matrix never grew past 2 packs (**DoD §14.6 fails on content, not just venue**)

`tests/test_smoke_matrix.py:62` still reads `_PACKS = ("pop_rock", "jazz")`. Its own comment at
`:61` says *"The three new packs land in C6-C8 and join this matrix then; `_PACKS` is the only
edit that needs."* **That edit was never made in C6, C7, or C8.** Worse, `:312`'s
`assert len(_PACKS) == 2` — written to catch a silent *shrink* — froze the expansion and made
three chunks of drift invisible.

Consequence: **CAVEATS C-18's claim that "the matrix's *content* is fully pinned-compliant;
only its venue is not" (CAVEATS.md:126) is false** and must be corrected. §14.6 is unmet on
both clauses. Found independently by two scoping agents.

### F3 — pop_rock's and jazz's calibration artifacts have already drifted (**GAP-2 is not hypothetical**)

`trackgen calibrate` is byte-reproducible. Orchestrator-verified by regenerating all five
artifacts to a scratch path and comparing:

| pack | reproduces? | differing leaves |
|---|---|---|
| pop_rock | **NO** | 20 |
| jazz | **NO** | 18 |
| chill_lofi | yes | 0 |
| blues | yes | 0 |
| fusion_jazz | yes | 0 |

Every differing leaf is the **`pads` role** (`noteDensity` + `meanIoi` bands) in
happy/energetic/triumphant/tense/aggressive. Traced: both artifacts were blessed at `ef9f410`
(generatorVersion 0.1.2); commit `9661d06` ("pad ladders monotone", gv **0.1.3**) changed pads
content and re-blessed 8 pads-only golden cells, but never regenerated the calibration
artifacts. The bless workflow's generatorVersion check covers the **corpus**; `calibration.yaml`
is not in the corpus, so it went stale silently — exactly the failure GAP-2 predicted, already
shipped.

---

## 2. Session scope

**In scope (this session):**

- Repair F1, F2, F3.
- DoD **§14.9** — five-pack property tests.
- DoD **§14.6** — smoke matrix at five packs **and** in CI.
- Discharge C-29's re-measurement assignment; rule C-30.
- Doc debt: C-19's §8.2 annotation, the §13 audit's one wording nit, CAVEATS corrections.

**Explicitly out of scope (→ C10, session 24):**

- GAP-1 dormant-content dry-render (3 tasks + open-ended triage).
- The reachability lint (C-22/C-23 modelling + `# expected-unreachable` markers across 4 packs).
- A/B harness build; milestone rubric anchors + capture format.
- The **user listening block**: T1 levels, T2 FM-piano, A/B demo, rubric pass, C5 reference-pack
  error-spotting pass.
- Whole-phase 4-lens review across all chunks; final §14 DoD 1–11 sweep; phase close-out.

**Not in scope at all (recorded, not built):** C-25's mode × pool-gate lint modelling and
C-28's arrangement-layer-cap ("role dormancy") lint class — both deferred with reasoning in
§4 R5; and fill coverage in the GAP-1 harness (fills are a stage-6 device path emitting no
`PatternRecord`, so they need a different seam).

---

## 3. Decisions requiring ratification at the gate

Ratify individually. Each states the recommendation and the rejected alternative.

| # | Decision | Recommendation | Rejected |
|---|---|---|---|
| **S23-0** | **Split C9 into C9 + C10** (§0) | **Split.** ~18–20 tasks otherwise, and the listening block is human-gated on tooling that doesn't exist yet. | One mega-session (prior chunks ran ~10 tasks; this would be the largest by 2×, with a 4-lens review at the end when fatigue is highest) |
| **S23-1** | **F1: fix L2-1's grain** — read `trace.phrases_stage6`, mirroring W7 | **Fix.** A gate reading 0 % of two packs' comping cannot support a PROVEN DoD claim. `quality/` is off the generation path → no golden moves, **no `generatorVersion` bump**. New caveat **C-31**. | Accept + caveat (would record §14.4b PROVEN on a knowingly vacuous gate — against this project's "never round up" discipline, held at C4/C5/C8) |
| **S23-2** | **C-30 disposition**, re-posed at the corrected grain | **Set fusion comping threshold to 0.97** in `styles/fusion_jazz/calibration.yaml` (per-pack data edit, legitimate under D10/§12 Q4). At stage-6 grain fusion's min ratio is **0.9760** and the residual is 5/192; 0.97 leaves the gate strong (at N≈234 it tolerates 7 bad notes, not 33). | (a) Hand-set 0.857 on the *current* grain — guts the gate (tolerates 14 % bad notes at N=100). (c) Derive from the blessed batch — **disproven by measurement: the 3-seed batch derives 1.0000, i.e. *stricter* than 0.98**, and even at 120 renders/mood ±2.5 SD leaves an 18/960 residual |
| **S23-3** | **§14.9's "× lengths" reading** | **Each prior phase's own pinned length dimension** (PHASE_6 §11.9 already pins 3), not a uniform 39-value grid. Yields ~10,500 tests / ~90 s. | Uniform 39-grid on render-level suites = 43,875 full renders ≈ **4.5 min wall for one module**. Arbitration-adjacent, so flagged for explicit sign-off rather than assumed |
| **S23-4** | **25-seed depth placement** | **Default gate**, no marker tier. ~90 s keeps the four-gate loop fast. | A marker tier is a tier that silently stops running — against ROADMAP §3's no-silent-caps discipline |
| **S23-5** | **F2: widen smoke matrix to 5 packs** + correct C-18's false content claim | **Widen.** Must land **after** S23-1/S23-2 — its `_gate` asserts `validate_pipeline == []` hard, so widening before the L2-1 question is settled yields an intermittently red gate (fusion's residual is seed-set sensitive, 0.5–3.1 %). | Widen first and tune later (ships a flaky gate on `main`) |
| **S23-6** | **Crash-suppression branch** (`test_phase6_property.py:116`) | Replace `== set()` with a **per-pack pinned dict** (`chill_lofi`/`fusion_jazz` → `{"breakdown"}`, other three → `∅`), asserted for **equality**, and make the suppression branch assert for real. Widening makes the current assertion fail **by its own design** — this is the one genuine work item inside §14.9. | `⊇` assertions (vacuous in one direction); deleting the test (loses §11.9 check 3 entirely) |
| **S23-7** | **F3: GAP-2 coverage shape** | **Byte-reproduction test** per pack: `calibrate → tmp`, assert bytes equal the committed artifact. Not brittle — a legitimate re-bless regenerates the file, so the test follows automatically. **Plus regenerate pop_rock's and jazz's artifacts** (a real content change → own commit). | Exact value pins (brittle, duplicate the artifact); tolerance pins (**unpinnable** — band scales differ by 4 orders of magnitude across roles and several are negative at n=3); content hashing (same power, unreadable failure) |
| **S23-8** | **C-29 closure** | **Resolved-and-verified.** Measured 5 packs × all moods × 12 seeds × 2 lengths: the four pre-existing packs sit at ratio **1.0000 under both readers**, with **0 differing rows in 1740** — the widening is provably inert on them, so no margin can erode. Record that this was only answerable at the corrected grain. | Leave open (the assignment is discharged; leaving it open misrepresents the evidence) |
| **S23-9** | **C-18: add CI** | **Add `.github/workflows/gates.yml`** running the four gates on push+PR with `uv sync --locked`. ~2–3 min/run. Keep the 300-seed sweep inline (stricter than §8.2's pinned "periodically"); record that as C-18's resolution note. | Defer again (cheapest DoD item on the list — ~15 lines of YAML closes §14.6's venue clause) |
| **S23-10** | **C-19's §8.2 annotation** | Insert the drafted line at `PHASE_8.md:833`; flip C-19 to fully resolved. | — (trivial, owed since C5) |
| **S23-11** | **`calibrate()` must PRESERVE a committed artifact's `l2Thresholds`** — ruled by the orchestrator 2026-07-21, raised by T3 | **Preserve.** See rationale below. Expands **T2's scope** to carry the `tooling/calibrate.py` change. | Regenerate thresholds from engine defaults (the status quo — structurally incompatible with both S23-2 and S23-7, and a silent-drift bug in its own right) |

## 3a-FINAL. S23-2 RESOLVED as option D (2026-07-21) — read this before the history below

**Ruling: widen L2-1's allowed set to admit the natural 11 where the quartal voicing class is in
play; DROP the minimum-denominator guard.** User sign-off given 2026-07-21.

**Why option C (the guard) was abandoned after being ruled and implemented.** Depth measurement
(80 seeds × 8 moods × 5 lengths, 2963 comping rows) showed **two disjoint failure classes**:

| class | N | bad notes | ratio | count | guard removes? |
|---|---|---|---|---|---|
| (a) | < 50 | 1 | ~0.9375 | 7 | **yes** |
| (b) | 91–316 | **2–7** | 0.9732–0.9792 | 20 (**densest at length 120**) | **no** |

*Counts are per-sweep and differ between them — this orchestrator sweep (80 seeds × 5 lengths)
found 7 + 20 = 27 failing rows; T2's independent sweep found 10 + 20 = 30. Both are internally
consistent; the difference is the seed set. **Do not treat either count as the population.***

*[corrected 2026-07-21 after T2's review: this table first read "**all** at length 120". A third
independent 40-seed sweep found a class-(b)-shaped failure at length **180** (N=176, 4 out-of-set
notes, ratio 0.9773 — inside class (b)'s own band). The absolute "all" was another over-firm
claim of exactly the kind this section exists to warn about, falsified by the very next sweep to
look. **The operative rule is unaffected**: 120 is where class (b) is densest and is the bucket
earlier sweeps omitted, so no sweep of this pack may omit it.]*

Class (b) is dominant, is pure quartal-11 content, and no denominator reasoning touches it. The
guard fixed a minor artifact while costing ~25 % of L2-1's coverage at smoke lengths.

**Why not a threshold.** Every deeper sample found cells the previous one missed — the tail is
not bounded by sampling, so no threshold is stably determined. Chasing one is precisely the
"tune toward a printed number" antipattern ROADMAP §3 forbids.

**Why D is principled.** PHASE_8 §6.4 pins `quartal` as fusion's signature comping voicing;
`theory/voicing.py:185` resolves it to `[[0, 5, 10, 15]]`, whose offset 5 is the natural 11.
The pack's own pinned voicing table systematically produces notes its own validator counts as
wrong — the same shape as **C-29**, which widened this same allowed set to admit quartal's ♯9.
D fixes the cause, not the symptom, and keeps 0.98 strong on the other four packs. The widening
must be **narrow** (§6.4 excludes 11 over dom7 for sound theoretical reasons — a global widening
would blind the gate everywhere) and **strictly additive**.

### Orchestrator measurement failures on this decision — recorded, not buried

Four numbers reached the user and/or this plan file and were wrong. All four came from the
orchestrator sampling narrowly and reporting firmly:

| # | Claim | Reality |
|---|---|---|
| 1 | fusion floor **0.9760** (scoping, 192 renders) | not the floor |
| 2 | fusion floor **0.9375** | only class (a); class (b) sits at 0.9732–0.9792 |
| 3 | "the floor's exact value is insensitive across the distributional gap" | false — floor 20 skips 4.0 % of comping rows, floor 50 skips 16.2 % (4×) |
| 4 | guard coverage cost **3.56 %** | a 12-seed, 2-length artifact; really 5.62 % at corpus lengths and **24.98 %** at smoke lengths (T2's figure, orchestrator-unverified) |

**Root cause in every case: sweeps omitted length 120**, the only bucket where class (b) appears.
**Standing rule for the rest of Phase 8: any L2-1 claim must be measured at ≥ 80 seeds × all
supported moods × ≥ 5 lengths including 120, or stated as provisional.** This is the third
session in which a confidently-reported wrong number about C-30 had to be retracted (see C-30's
own text on seed-set sensitivity, and C8's lens-A correction) — the discipline is written here
because remembering it has repeatedly failed.

---

## 3a. S23-2's SUSPENSION (historical — superseded by 3a-FINAL above)

**The premise was wrong.** S23-2 was ratified on "fusion's stage-6 min ratio is **0.9760**, so a
0.97 per-pack threshold clears it with margin" — scoping's figure from a 192-render sweep.
Orchestrator re-measured at depth after T1 landed (480 comping rows: 8 moods × 30 seeds × 2
lengths): **the true floor is 0.9375**, and 0.97 would NOT clear fusion. This is the exact
failure mode C-30 itself warns about ("the rate is seed-set sensitive … plan against the top of
the range, not the mean") — the orchestrator under-sampled and reported the result as firmer
than it was. Recorded here rather than quietly re-tuned, per the C8 lesson.

**What depth actually revealed — the structure matters more than the number:**

- **60 of 480 comping rows (12.5 %) carry ≥ 1 out-of-set strong-beat note.** The musical fact is
  widespread, not rare.
- **Only 4 rows fail.** Median denominator is **N = 232**, where one bad note gives 0.9957 and
  passes 0.98 comfortably. **All four failures have N = 16**, where one bad note gives exactly
  0.9375.
- Therefore the gate is not measuring *how much* out-of-set content a render has. It is
  measuring **how small the denominator happened to be when a bad note occurred.** Two renders
  with identical musical content — one quartal 11th on a strong beat — pass or fail on
  denominator size alone.

**Threshold sweep (of 480 rows):** 0.98 → 4 fail · 0.97 → 4 · 0.95 → 4 · 0.94 → 4 · **0.9375 → 0**
· 0.93 → 0. There is **no discrimination anywhere between 0.94 and 0.98** — the gate is a cliff at
the N=16 boundary. Setting 0.93 does not make it "slightly more permissive"; it relocates the
cliff, and a future cell with N=8 fails at 0.875.

**Options put to the user (awaiting ruling; T2 and T7 held):**

| | Option | Assessment |
|---|---|---|
| **A** | Accept permanently (C-30 option b) — no threshold edit, §6.4/§8.1 note + CAVEATS | Zero risk, fully honest. But leaves 4-in-480 renders failing a **hard** gate, so T7's five-pack smoke matrix goes intermittently red — precisely what S23-5's ordering exists to prevent. Forces T7 to exclude fusion or de-harden the gate. |
| **B** | Set fusion comping to 0.93 | Clears today's sweep. Arbitrary, fragile, addresses no mechanism. **Not recommended.** |
| **C** | **Minimum-denominator guard** (orchestrator's recommendation) | Don't evaluate L2-1 below an N floor; route sub-floor groups to the `L2-1-SKIP:` channel **T1 just built**, so it cannot go silently vacuous the way F1 did. Keeps 0.98 where the measurement is meaningful. A ratio from 16 samples is not a meaningful rate — the same reasoning that makes the n=3 calibration bands untrustworthy. **This is an §8.1 amendment** (the doc pins L2-1 as a ratio against a threshold, with no denominator condition) → needs sign-off + a CAVEATS entry, and the floor should be derived from the observed N distribution, not picked. |

**Measured N distribution (fusion comping, 480 rows), for deriving a floor under option C:**
min **12** · p10 **122** · median **232** · max **715**. Bad-note counts among the 60 affected
rows: 48 rows with exactly 1, 6 with 4, 4 with 3, 2 with 2.

### S23-11 — ruling detail (raised by T3, ruled by orchestrator, no PHASE-doc deviation)

**The conflict.** `calibrate()` has no `l2_thresholds` parameter; `compute_bands` falls back to
`DEFAULT_L2_THRESHOLDS` (`quality/calibration.py:174`), so a regenerated artifact **always**
writes `{bass: 0.95, comping: 0.98}`. That is why fusion reproduces today. The moment S23-2/T2
hand-sets fusion's comping to **0.97**, S23-7/T3's byte-reproduction test goes red — the
regenerated file would say 0.98. Byte-reproduction and hand-tuned per-pack thresholds are
structurally incompatible as the tool stands.

**Ruling: `calibrate()` preserves the existing committed artifact's `l2Thresholds` when one is
present**, passing them through to `compute_bands`; bands stay fully derived.

**Why this is a fix within pinned intent, not a deviation.** §8.1's bootstrap note and **D10**
distinguish the two kinds of data living in `calibration.yaml`: bands are *derived* from the
blessed batch ("regenerate-on-bless keeps them honest"), while L2 thresholds are *tunable style
data* (§12 Q4 pins them as "data (`calibration.yaml`), tunable without design change").
Regenerating a deliberate threshold edit away is therefore contrary to D10's own division —
clobbering authored data with an engine default. No PHASE doc says thresholds are derived; C-30
already records that `calibrate` "never derives L2 thresholds from data".

**It also fixes a latent second drift bug.** Today, anyone re-running `calibrate` on a pack whose
threshold had been hand-tuned would silently revert it — the same class of silent drift as GAP-2
(F3), which this session exists partly to close. Leaving it would mean shipping the fix for one
instance of a bug while leaving its twin armed.

**Scope consequence:** T2 carries the `src/trackgen/tooling/calibrate.py` + `quality/calibration.py`
change, plus a test proving a hand-set threshold **survives** a re-calibrate. T3's Part A test is
the thing that would have caught this, which is the argument for it.

---

## 4. Task list

Serial unless marked ‖. Every dispatch sets `model` explicitly (PROMPT §"Subagent model rules").

| # | Task | Files (scope) | Model | Verification |
|---|---|---|---|---|
| **T1** | **L2-1 grain fix (S23-1).** Swap the note source to `trace.phrases_stage6`, mirroring W7's approach at `layer1.py:442`. Thread the stage-6 snapshot into the L2-1 reader. Preserve the `total == 0` guard but make it **loud** — a skipped check must be visible, not silent. Tests: grain pin (stage-6 counts, not doc counts), the four packs pinned at 1.0000 under both narrow and widened readers (folds in S23-8's regression evidence), and a discriminating fixture. | `src/trackgen/quality/layer2.py`, `tests/test_quality_layer2.py` | opus | 4 gates; the F1 table's zero-rows become non-zero; no golden moves; **no gv bump** |
| **T2** | **C-30 threshold (S23-2).** Set fusion comping to 0.97 in `styles/fusion_jazz/calibration.yaml`; test reads it back and asserts it is pack-specific (not the engine default). Amend CAVEATS C-30 with the corrected-grain numbers + the disproof of the derive-from-batch option. | `styles/fusion_jazz/calibration.yaml`, `tests/test_fusion_jazz_pack.py`, `plans/CAVEATS.md` | opus | fusion clean across a ≥960-render sweep at the new grain |
| **T3** | **GAP-2 (S23-7).** Byte-reproduction test over all five packs. **Separate commit:** regenerate pop_rock + jazz artifacts, noting the correction of post-0.1.3 pads drift. Check whether any L3 band warning changes as a result. | `tests/test_calibration_artifacts.py` (new), `styles/{pop_rock,jazz}/calibration.yaml` | opus | all 5 reproduce byte-identically; ~4.6 s added |
| **T4** | **`tests/_packmatrix.py` helper.** Export `PACKS` (5), `supported_moods()`, `pack_mood_pairs()`, `SEEDS_25`, `LENGTHS_PLAN`, `LENGTHS_RENDER`, `cached_pack()`, `build_plan()`. Deduplicates `_cached_pack`/`_build_plan`/`_LENGTHS`/`_SEEDS`, currently **triplicated verbatim** across `test_form.py:331-352`, `test_arrange.py:436-455`, `test_harmony_goldens.py:740-753`. Makes the pack dimension a one-line edit in one file. | `tests/_packmatrix.py` (new) | opus | imports clean; no behavior change yet |
| **T5** | **§14.9 widening (S23-3/S23-4).** Widen the 5 hardcoded pack tuples to consume T4's helper: `test_form.py:356`, `test_harmony_goldens.py:759`, `test_arrange.py:458`, `test_transitions_determinism.py:198`, `test_phase7_property.py:60`. Each keeps a `test_matrix_non_vacuous` recomputing dimensions from pack data. Record PHASE_5 §13.5's walker suite as **permanently jazz-only** (`bass_mode`: jazz `walking`, other four `patterns`) rather than leaving a silent one-pack suite. Update `test_phase7_property.py`'s pinned `344` → **728**. | the 5 modules above | opus | 4 gates; test count ≈ 10,500; wall ≈ 90 s |
| **T6** | **Crash suppression (S23-6).** Per-pack `_ENTERED_SUPPRESS_TYPES` dict, equality-asserted; make the suppression branch assert for real on chill_lofi + fusion_jazz. | `tests/test_phase6_property.py` | opus | the previously-dead branch executes and discriminates |
| **T7** | **Smoke matrix → 5 packs (S23-5).** `_PACKS` widened; `assert len(_PACKS) == 2` → `== 5`; per-pack floors extended (`_CEILING_FLOOR_SEC` pattern). **Correct CAVEATS C-18's false content claim.** Expect ~800 new cells. | `tests/test_smoke_matrix.py`, `plans/CAVEATS.md` | opus | 4 gates; **must be green across ≥3 consecutive runs** (flakiness check, given C-30's seed sensitivity) |
| **T8** | **CI (S23-9).** `.github/workflows/gates.yml` per the drafted shape; `uv sync --locked`; four gates. | `.github/workflows/gates.yml` (new) | sonnet | YAML valid; **user pushes a branch to confirm a real run** (orchestrator never pushes) |
| **T9** | **Doc debt (S23-10).** C-19's §8.2 annotation at `PHASE_8.md:833`; flip C-19 resolved; §13 item 4's "Q2 closed" wording nit; CAVEATS C-29 closure + new **C-31** (L2-1 grain). | `plans/PHASE_8.md`, `plans/CAVEATS.md` | opus | cross-refs resolve; no contradictions |
| **T10** | **Chunk review** — 3 lenses in parallel over the whole C9 diff: correctness/determinism · contract compliance vs §8.1/§14 · test quality & non-vacuity (mutation-test the new assertions). | read-only | opus ×3 | zero blockers; ≤2 fix cycles |

Per-task: implement → orchestrator runs 4 gates → opus review scoped to that task's diff →
bounded fix loop (max 2) → commit + PROGRESS.md update. **T1 → T2 → T7 is a hard ordering**
(S23-5's rationale). T3, T4, T8, T9 are independent of that chain and may run ‖ where file
scopes are disjoint. T5 depends on T4; T6 is independent.

---

## 5. Carried to C10 (session 24) — recorded here so the seam is lossless

| Item | Why it needs C10 | Est. |
|---|---|---|
| **GAP-1 dry-render** (C-20/C-22/C-23/C-28, 4× motivated) | Seam exists — `generate()` takes `SelectionResult` as a plain parameter (`parts/generators.py:111`), and `tests/test_generators.py:261` already hand-builds one, so a substituted selection yields a **real full `GenerationTrace`** and `layer1_checks`/`validate_document` run **unmodified**. ~70+ blind ids across 5 packs have never been routed; C-24's precedent says grid/Phrase faults hide exactly there. Triage is open-ended. | 3 tasks + triage |
| **Reachability lint** (C-22 + C-23 scoped; C-25 & layer cap deferred) | `lint.py:436` reads only the envelope. It already imports `load_moods`/`derived_defaults`/`intensity` and (via `quality.layer1`) the render pipeline — so a direct `section_energy` call is available with no new machinery. Will fire warnings on 4 packs, each then needing an `# expected-unreachable` marker citing its caveat — converting 4 prose caveats into enforced annotations. | 2 tasks |
| **A/B harness** | **Does not exist.** §14.8d cannot be demonstrated without building it: render pair at identical seed, blinded presentation order, forced choice, ~20 trials → binomial. | 1–2 tasks |
| **Milestone rubric tooling** | No anchor text, no schema, no capture format. §8.4 pins 5-point scales × 4 axes (musicality, groove, style-fit, soloist space); the anchor descriptions have never been written. | 1 task |
| **User listening block** | Human-only; orchestrator cannot self-certify. C5 reference-pack pass **60–90 min** · T1 levels **45–90 min** · T2 FM-piano **20–30 min** · A/B demo **25–40 min** · rubric **60–90 min**. **Total 3.5–5 h**, best split across sittings. | user |
| **Whole-phase 4-lens review + final §14 DoD 1–11 sweep + close-out** | Must run last, over all nine chunks together (PROMPT §3). | 4 + orchestrator |

### F4 — W2 is blind to a fill at a suppressed boundary (**NEW, found by T5+T6's review**)

`quality/layer1.py:359-361` runs `legal_fill_bars.add(outgoing.start_bar + outgoing.length_bars - 1)`
for **every** boundary — *including* suppressed ones — before the
`if entered.type not in _SUPPRESSION_TYPES` guard on line 362. So W2's fill check is an
**only-if** (a fill only lands in *a* legal fill bar) and permits a fill in a suppressed
boundary's fill bar, which §3.2's device policy forbids.

**Confirmed empirically, not just by reading.** The reviewer rendered a fill at a `breakdown`
boundary under mutation and Layer 1 reported: `happy W2: NONE | total: 0`, `calm W2: NONE |
total: 0` — completely silent.

This is the **same defect family as F1**: a pinned check that does not see what it is defined
over. It is now covered *from the test side* by T6's new assertion (b), which is why the mutant
died — but **the validator itself remains blind**, so any render path not exercised by that test
is unprotected.

**Deliberately NOT fixed in C9.** Changing W2 is a Layer-1 behavior change against a §8.1-pinned
check, mid-chunk, after scope was already ratified — PROMPT's escalation rule on scope growth
applies. **Carried to C10** as a scoped candidate (exclude suppressed boundaries from
`legal_fill_bars`), where it belongs alongside the other validator-coverage work. Logged here so
it cannot be lost.

### T10 three-lens review — two mutation survivors worth carrying to C10

Lens C ran 21 mutants against **production** code and killed **19**. Both survivors are
coverage-boundary findings rather than broken tests, and both bound what this session's green
gate actually proves:

**Survivor M17 — the five-pack smoke matrix does NOT exercise the C-32 quartal widening.**
Removing the widening entirely leaves all 129 fusion_jazz smoke tests green. Measured cause: over
the 120 fusion smoke cells the **narrow** (un-widened) reader's minimum comping ratio is
**0.9809**, clearing the 0.98 threshold by 0.0009, so no cell fails either way. Two consequences,
pulling opposite ways:
- *Reassuring:* the hard gate has real headroom on fusion at its pinned seeds — with the widening
  in place the worst ratio is **1.0000** on both roles. S23-5's ordering caution was right in
  principle, but the chosen seeds are nowhere near a knife-edge. This is why three consecutive
  runs showed zero variation.
- *Bounding:* the widening's only genuine protection is `tests/test_quality_layer2.py`.
  **§14.6's greenness must not be read as covering §14.4b** — those 675 cells are insensitive to
  the L2-1/C-32 question. State this in C10's DoD record rather than letting one imply the other.

**Survivor M16 — byte-reproduction is structurally blind to `l2Thresholds`.** Since S23-11 made
`calibrate()` *preserve* committed thresholds, a corrupted threshold reproduces perfectly.
**GAP-2 is closed for bands only.** The backstop is thin: `test_load_l2_thresholds_reads_blessed_
artifact` asserts only `0.0 < bass <= 1.0` (passes at 0.5) and covers pop_rock/jazz only — and it
is *pre-existing* (C5/`ef9f410`), not added here. **C10 should add a direct per-pack pin of the
committed threshold values** — which is exactly what S23-11's own "silent-drift twin" argument
implies, now demonstrated rather than hypothesised.

### Performance attribution — THRICE measured, still unresolved. Do not inherit a number.

| source | render-level pair | plan-level trio | verdict |
|---|---|---|---|
| T5 (implementer) | "the cost" | — | render pair dominates |
| T5's reviewer | 237.8 s / 46.4 % | 270.3 s / 52.8 % | plan trio dominates |
| T10 lens C | **242.7 s / 50.8 %** | **235.0 s / 49.2 %** | effectively tied, render pair leads |

**The orchestrator's "correction" below was itself unreproducible** — a third independent
measurement reverses it again, and the two are within ~3 % of each other, i.e. tied within noise.
Per this session's own standing rule about firm numbers from single sweeps, **C10 must re-measure
before optimizing either module** rather than inherit any of the three orderings.

Also: **`test_smoke_matrix` is absent from the attribution table entirely**, and lens C measures
it at **123.8 s / 18.3 %** — the second-largest module in the suite and the largest single thing
T7 added. Any optimization pass should start by looking there, not at the trio-vs-pair question.

**Settled facts** (all three sweeps agree): wall ~102–104 s idle; **no single test sets the
parallel floor** (longest 4.91 s against a ~102 s wall — T6's per-pack split worked); zero
flakiness across three consecutive runs.

### Correction to T5's performance attribution (SUPERSEDED — see the table directly above)

T5 reported the added cost as "the two Phase-6 render-level modules". **That is inverted.**
Measured per-module CPU by the reviewer:

| module | wall (isolated) | Σ CPU | share |
|---|---|---|---|
| `test_phase6_property` | 18.62 s | 176.6 s | 34.5 % |
| `test_harmony_goldens` | 11.62 s | 112.0 s | 21.9 % |
| `test_arrange` | 7.66 s | 79.6 s | 15.5 % |
| `test_form` | 7.26 s | 78.7 s | 15.4 % |
| `test_transitions_determinism` | 6.51 s | 61.2 s | 12.0 % |
| `test_phase7_property` | 3.70 s | 4.1 s | 0.8 % |

The render-level pair is 237.8 s CPU (46.4 %); the **plan-level trio is 270.3 s (52.8 %) —
larger**. That follows directly from S23-3: the plan trio keeps the 39-length × 25-seed grid, so
its 45 cells build 43,875 plans. **C10 must not optimize the wrong module.**

**S23-4's premise is recorded as measured-and-exceeded, not silently carried:** the decision put
25-seed depth in the default gate on an estimated "~90 s". Measured wall is **114–141 s**
depending on machine load — 25–55 % over. Still acceptable (the four-gate loop stays ~3 min, and
a marker tier is a tier that stops running), but the estimate was optimistic and the record says
so, in the same spirit as this session's 45 s baseline correction.

### Findings raised mid-session, carried to C10's DoD sweep (not blockers now)

- **Nothing consumes the Layer-3 bands.** T3 measured it: `load_calibration` is called from
  exactly one site (`quality/layer2.py:80`) and reads only `l2Thresholds`. `layer3.py` computes
  metrics, but **no code compares them against the bands** — §8.1's "batch-only, warn-only" L3
  warner has never been built. DoD §14.4c's literal text ("L3 metrics + band computation") is
  satisfied, so this is not a §14.4 failure; but the bands are currently a written-and-never-read
  artifact, and C10's sweep should record that honestly rather than implying L3 is live.
- **The n=3 calibration batch produces under-dispersed bands.** `calibrate` batches 3 seeds
  (`calibrate.py:45`) and `compute_bands` takes `pstdev` over them, so several bands are tight
  enough that a fair share of unseen seeds fall outside. Concrete: after T3's regeneration,
  pop_rock happy `noteDensity` puts **5 of 15** probe seeds outside its band (0 of 15 under the
  stale band); jazz happy `scaleConsistency` was **already** outside on 6 of 15 before any change.
  Pre-existing property of §8.1's pinned batch size, not introduced by T3 — but it means an L3
  warner wired up naively would fire constantly. Relevant to §12 Q4.
- **T3 found a third drifted metric beyond the scoping brief:** jazz's stale bands also covered
  `scaleConsistency`, not just `noteDensity`/`meanIoi`. The F3 table in §1 undercounted the
  affected metrics (not the leaf counts, which were right).

**Note for T5 (from T4):** `cached_pack()` returns a real `StylePack`, so the existing
`# type: ignore[arg-type]` at `test_form.py:352` / `test_arrange.py:455` and
`# type: ignore[attr-defined]` at `test_form.py:394` become **unused** — mypy runs strict with
`warn_unused_ignores`, so they must be deleted as part of the swap. Keep the
`assert forms is not None` narrowing (`pack.forms` is still `Forms | None`). Also expect existing
form/arrange/harmony **test ids to be reordered** (the helper sorts moods; the local versions used
pack-declared order) — the cell *set* is identical, nothing added or lost.

**Listening-record note for C10:** `listening/log.jsonl` holds 3 `session_pass` records (sessions
20/21/22, all `entries: 0`). **Zero individual error-spotting entries have ever been logged** —
the §8.4 `{params, seed, timeInTrack, category, note}` shape has never been instantiated. Only
`listening/session22/` committed fixtures; sessions 20–21's passes are unreproducible from disk.

---

## 6. Audit results carried into the DoD record

The §13 amendment audit (DoD §14.11) **ran this session and passed: 8 of 8 items APPLIED**,
verified by reading each target document rather than trusting §13's own summary. One wording
nit: §13 item 4 says PHASE_4 §12 **Q2** was "closed not-needed", but the target doc annotates it
as *still unexercised* with `Post-v1` in the resolves column. The target doc agrees with §3.8's
authoritative row — **§13's summary word is the loose one**. T9 fixes the wording. §14.11 is MET.

Full per-item evidence tables (DoD sweep, §13 audit, listening inventory) are in the scoping
agent reports; the DoD sweep is re-run fresh at C10 as the phase's final sign-off.
