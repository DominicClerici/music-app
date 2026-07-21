# SESSION_22 — Phase 8, Chunk 8: `fusion_jazz` (the third and final new pack)

**Scope:** author `styles/fusion_jazz/` in full per `plans/PHASE_8.md` §6 and the §9.4
checklist; land it atomically with its tests; verify the fusion first-uses (quartal voicings
live, `feelTable: tight`, `AutoFilter`, swing16 table path, authored `(#11)`/`(#9)`
extensions); calibrate; run the formal §8.4 listening pass; **complete the golden corpus
48 → 60, closing C-17 and letting DoD §14.5 finally be marked PROVEN**. Whole-chunk review +
close-out. DoD targets: **§14.3 (fusion)**, **§14.8 (fusion slice)**, **§14.10 (fusion
listening checklist)**, **§14.5 (corpus completion)**.

**Explicitly out of scope:** `tests/test_smoke_matrix.py` five-pack extension (C9, per the
S20-3/S21 precedent); the reference-pack formal listening item (C5 debt, carried to C9); the
C9 close-out items (five-pack property tests, milestone rubric, A/B harness, §13 amendment
audit, whole-phase review); any engine change not forced by a verified first-use bug
(contingency 14 below).

**Environment:** `uv` / Python 3.12. Four gates: `uv run pytest -n auto` · `uv run ruff check .`
· `uv run ruff format --check .` · `uv run mypy`. Baseline (orchestrator-verified 2026-07-21):
**6327 passed / 1 skipped**, all four gates green at `c37e5bd`. `_GENERATOR_VERSION` 0.1.3.
Corpus **48/60**. Never `git push`.

---

## Binding constraints (from scoping, 2 opus agents, 2026-07-21; headline findings
independently reproduced by the orchestrator)

1. **Atomic landing.** `loader.registered_styles()` discovers any `styles/*/manifest.yaml`;
   the instant `styles/fusion_jazz/manifest.yaml` exists, `tests/test_interpreter_pack.py:114`
   (4-pack set) fails, and `tests/test_interpreter.py:301-308`'s dynamic pack×mood matrix
   calls `resolve_pack("fusion_jazz")` at collection — a partial pack raises `PackLoadError`.
   `tests/test_interpreter_pack.py:118` currently uses `resolve_pack("fusion_jazz") is None`
   as its *unregistered-style example* (S21 repointed it here) — repoint to the literal
   **`"not_a_pack_xyz"`** (precedent: `tests/test_corpus.py:190` uses `"not_a_pack"`).
   T1–T5 stay uncommitted until the whole pack + tests are green; **commit 1 is the
   complete pack.**
2. **Manifest (decision S22-1).** `Manifest` requires `formatVersion: int` + `engine: str`
   (`packs/models.py:118,122`); §6.1's printed snippet omits both (confirmed
   `ValidationError`). Author `formatVersion: 1` + `engine: ">=0.1"` (sibling-verbatim) and
   amend §6.1 per arbitration rule 2 after sign-off. *Exact S21-1 replay.*
3. **Modes ladder order (decision S22-2) — HARD LOAD FAILURE as printed.** §6.1 prints
   `modes: [dorian, mixolydian, minor, major]`; `packs/models.py:461-465` requires a
   ladder-ordered subsequence of `('major','mixolydian','dorian','minor','phrygian')` →
   `PackLoadError`. Author **`modes: [major, mixolydian, dorian, minor]`** (and reorder the
   `tonics:` map to match). **Behaviorally inert** — `_resolve_mode`
   (`interpreter/stage.py:98-113`) is set-based with a brighter-rung tie-break; verified to
   return the identical mode for all 8 fusion moods under both orderings. *S20-1 replay.*
4. **The deceptive-substitution finding (decision S22-3 — the headline).** §3.3 and PHASE_4
   D6 claim `turnarounds: []` makes *both* boundary transforms inert. **False.** PHASE_4's
   normative text (§5.1 step 5, and PHASE_4.md:207 verbatim — "None eligible (or empty run) →
   deceptive fallback") is what `harmony/stage.py:404-415` implements: on a same-tag boundary
   with no eligible turnaround, if the section's last event is tonic-rooted with
   `function == "T"`, a **fixed, draw-free** deceptive substitution fires unconditionally.
   D6's "both inert" parenthetical held in v1 only because **pop_rock has no same-tag
   adjacency** — which PHASE_4.md:209 states explicitly. Fusion's `vamp` tag serves
   `main`/`breakdown`/`outro` repeatedly and `tune_16` serves `head`/`solo`/`solo`/`head`, so
   the transform wakes up at nearly every boundary. Measured over 336 renders: **874
   deceptive substitutions** (`tune_16` 625, `vamp` 249). Orchestrator-reproduced render
   (calm, vamp, `sus_pedal`, `maxLengthSec` 180): `I7sus4 | vi | I7sus4 | vi | I7sus4 | vi |
   I7sus4 | vi | I7sus4 | vi | I7sus4(breakdown) | vi | I7sus4 …` — a one-chord pedal
   alternating with an unauthored `vi` for half the track. This **violates DoD §14.10's
   "vamps loop without harmonic drift"**. Affected §6.3 entries: `sus_pedal` (`I7sus4`),
   `minor_launch` (ends `i7`), `cantaloupe_class` (`d: i7`), `dominant_16` (`d: I7`). Already
   safe: `dorian_funk` (ends `IV7`), `mixo_vamp` (ends `bVII7`). The S22-3 ruling pins the
   response; T1 authoring follows it.
5. **Quartal empty-candidate hard crash (decision S22-4).** `theory/voicing.py:185-186`'s
   quartal `[0,5,10,15]` needs a 15-semitone span; the comping arrangement lane leaves only a
   7–9 semitone root window, so quartal yields zero candidates for 453/1296 (mood, key,
   token) combinations. Normally harmless (falls through to `rootless_a`) — but for **`Bbm9`**
   (i7+9 in **Bb dorian, §6.1's pinned Chameleon key**) and **`A7#9`** (V7(#9) in D dorian) at
   comping lane low = 50 (`registerBias ≥ +0.15` ⇒ calm/triumphant/happy), *both* §6.4
   rung-1/2 classes are empty and `parts/voicing.py:95-98` **raises `ValueError`** — an
   uncaught pipeline crash. Measured: **54 of 1152** explicit-`key.mode`-override renders
   crash. Unreachable under auto mood-resolution (dorian ← mysterious only, whose lane is
   47–70). `rootless_b` fits both (`[56,60,61,65]` / `[55,60,61,64]`). **Data fix, no engine
   change.**
6. **Rung reachability — the three-headed computation (C-22/C-23/C-25 lessons), measured.**
   Formula `energy = round(lo + clamp01(base + 0.10·A) · (hi−lo), 3)` over `[0.20, 0.95]`;
   rungs `<0.30`→1, `[0.30,0.55)`→2, `[0.55,0.80)`→3, `≥0.80`→4; `main`-kind only
   (`parts/selection.py:64-71,90-96`). Measured over 3 840 form fits:

   | template / section | kind | energy range | live rungs |
   | --- | --- | --- | --- |
   | tune / intro · outro | intro · ending | 0.376–0.485 · 0.414–0.522 | rung ignored |
   | tune / **head** | main | 0.526–0.635 | **2, 3** |
   | tune / **solo** | main | 0.676–0.935 | **3, 4** |
   | vamp / **main** | main | 0.526–0.710 | **2, 3** |
   | vamp / **breakdown** | main | 0.339–0.448 | **2 only** |
   | fallback / solo | main | 0.826–0.935 | **4 only** |

   **Rung 1 is DEAD grid-wide** (proof, not sampling: rung 1 needs pre-envelope `e < 0.1333`;
   the lowest base is breakdown 0.25 at the lowest arousal calm −0.65 ⇒ `e = 0.185`). **Rung 4
   is `tune`-only** (`vamp` maxes at 0.710) — §6.4's rung-4 ride drive is a tune-template
   device. **Breakdown is arrangement-capped to 2 layers** (`arrangement/arrange.py:105-117`)
   ⇒ drums+bass only, so rung-2 *comping/pads* content renders only in `tune/head` +
   `vamp/main` at calm/dreamy/nostalgic. Measured over 336 full renders: **no rung-1 key ever
   selected, any role**. Decision **S22-5** below.
7. **Pads DO sound** (unlike chill_lofi's C-22): `layersMax` 4 at energetic/triumphant/happy/
   tense × rung ≥ 3 ⇒ 4 active roles. Measured: pads selected at `main` rungs 3 and 4 only —
   never intro/ending, never rungs 1–2. **Quartal comping also renders** (comping main rung 2
   selected 84×/336 renders at calm/dreamy/nostalgic), so DoD §14.10's "quartal Rhodes sits
   under C5" is satisfiable — max measured comping/pads MIDI **70** (ceiling 71,
   `arrange.py:45`).
8. **No C-25 repeat: every §6.3 pool entry fires** (measured `pool_selections` over 336
   renders; `bVI7(#11)` 197×, `V7(#9)` 201×, `VIImaj7` 21×, `bVImaj7` 57×). But **`mixolydian`
   is dormant**: `_ideal_rung` (`interpreter/stage.py:85-96`) places mixolydian at
   V ∈ [0.00, 0.25) and no fusion mood lands there — 6 of 8 moods resolve **major**, 1 dorian
   (mysterious), 1 minor (tense). Decision **S22-6**.
9. **Variety lint (no escape):** `packs/lint.py:370-402` — for each active role (bass
   included; fusion is `mode: patterns`), slots `[(main,1..4),(intro,·),(ending,·)]`, warn
   when ≤ 1 candidate survives **all gates at any supported (mood, tempo) cell** ⇒ **≥2
   UNGATED candidates in each of 24 slots**. Measured mood tempo windows: energetic 126–145 ·
   calm 75–84 · mysterious 79–97 · dreamy 75–91 · nostalgic 78–95 · triumphant 113–138 ·
   happy 106–130 · tense 111–135. Fills are not variety-checked (PT12/TR5 needs ≥1 ungated
   drum fill, `loader.py:535-541`). **PT5 still requires an ungated `main` at rungs 1–4**, so
   the dead rung-1 bank must be authored regardless (blues precedent).
10. **NO `expected-unreachable` markers.** `_reachable_rungs` reads only the envelope
    (`intensity(0.20)=1`, `intensity(0.95)=4` → `{1,2,3,4}`), so no unreachable-content
    warning fires for the dead rung 1 — a marker would be inert text. Dormancy is
    caveat-recorded, not lint-annotated (identical to the C-23 disposition). Scratch-pack
    lint measured **0 errors / 0 warnings**.
11. **W7 / grid: fusion is the C-24-safe case.** `quality/layer1.py:441-483` reads
    `trace.phrases_stage6` (**pre-humanizer**); a Phrase violates if it carries both a
    straight-only (`{120,240,360}`) and a triplet-only (`{160,320}`) onset (`pos 0` neutral).
    §6.4 declares no triplet content anywhere; 16ths = 120 ticks ⊆ straight grid; `fu_dr_2`
    measured `pos_in_beat ∈ {0,120,240}`. **Authoring self-check: every authored `pos` must
    satisfy `pos % 120 == 0`.** Do NOT realize §6.1's "Purdie-shuffle territory" comment as
    triplet authoring — it is a feel observation. Because W7 reads pre-humanizer, swing16
    cannot create or cure a violation.
12. **Timbres (decision S22-7).** §6.1 declares **8** flavors; §6.6 prints **7** recipes —
    **`fusion_ride_kit` has none** (TB1 fails without it; author in-idiom as a ride-forward
    `funk_kit` sibling). Only `MonoSynth` keeps the role-default `mod` params legal for
    bass/comping/pads; three §6.6 recipes are defective as printed:
    - `synth_moog`: base `filter.Q: 4` collides with bass `brightness → filter.Q`
      (**base-XOR-mod**). Fix: keep `Q: 4`, add a `brightness` override emitting only
      `filterEnvelope.baseFrequency` (preserves §6.6's pinned Moog resonance).
    - `clav`: base `attack: 0.003` collides with comping `attackHardness → envelope.attack`.
      Fix: author `decay`/`sustain` in base, express the attack as a narrow `attackHardness`
      override band.
    - `glass_pad`: "brighter FM alternative" ⇒ FMSynth ⇒ pads `brightness →
      filterEnvelope.baseFrequency` is illegal; **needs a full per-flavor override**
      (`brightness → modulationIndex`) that §6.6 does not mention — the exact `organ_swell`
      silent-trap replay from S21. `rhodes` already states its override ✓.
    Also: kit flavors define exactly the 9 `KIT_VOICE_IDS` (`sound/timbres.py:54-64,161-173`);
    NoiseSynth voices omit `midi`; drum brightness defaults require MetalSynth for
    hats/ride/crash and NoiseSynth for snare; comping/pads must not author a fixed
    `mix.sends.reverb` (space-XOR, `timbres.py:336-346`); master ends in `Limiter` (TB4);
    StereoWidener takes `width` ONLY. **No allowlist gap anywhere in §6.6** — `AutoFilter
    {frequency, baseFrequency, octaves, depth, wet}` (`sound/allowlist.yaml:161-166`) matches
    §6.6's authored param set exactly.
13. **PT9/PT10 gaps in the printed doc:** §6.4 prints no bank-level `retarget`; PT9
    (`packs/models.py:251-270`) requires span ≥ 12 on bass/comping/pads. Author the
    sibling-identical values: bass `{28, 45, retrigger}`, comping `{50, 69, retrigger}`, pads
    `{45, 64, retrigger}`. Per C-21 the comping/pads windows are inert for `degree: chord`
    events but PT9 requires them structurally. `layeringOrder: [drums, bass, comping, pads]`
    once, in `patterns/drums.yaml` only (PT10, `loader.py:312-323`). §6.4's printed `fu_dr_2`
    omits `role: drums` — add it silently (S21 `bl_dr_2` precedent, no amendment).
14. **Contingency — engine fix forced by a first-use bug:** any engine change that alters
    pop_rock/jazz/chill_lofi/blues output triggers the full bless collateral (generatorVersion
    bump per `bless.py`, serialize/milestone literals, 48-cell re-bless). **Escalate before
    applying.** Zero engine changes landed at C6 and C7; S22-3/S22-4 are both designed as
    data-only fixes to keep that streak.
15. **C-12 verified safe:** `crash_velocity` = `0.45 + e·0.40`; min fusion section energy
    0.339 ⇒ floor 0.586; measured min over 3 722 crash notes **0.601**. C-12 stays latent.
16. **Corpus (T9, after listening per §8.1 bootstrap):** triple =
    **(energetic, calm, tense)** — orchestrator-verified independently: `extreme_mood_pair`
    returns `("calm","tense")` at d = 1.5240 (runner-up `("calm","energetic")` 1.4534, no tie),
    default `energetic` ∉ pair ⇒ `corpus_moods` does **not** raise. 12 new cells, corpus
    **48 → 60 — C-17 CLOSES**. First capture ⇒ **no generatorVersion bump** unless an engine
    change landed (contingency 14). **Plan shape:** `GenerationPlan`'s only nullable fields
    are `swing` + `feel_table` (`schema/ir.py:103-104`); `_resolve_swing`
    (`interpreter/stage.py:139-155`) returns `None` only for `straight8`/`straight16`, so
    swing16 always yields a concrete `SwingSpec`, and `feelTable: tight` is authored ⇒
    **fusion is a THIRD fully-populated plan**; extend `tests/test_corpus.py:300-305`'s
    zero-null branch to the 3-tuple knowingly.
17. **Collateral literals (T5/T9), verified at file:line:**
    T5 — `tests/test_interpreter_pack.py:114` (set += `fusion_jazz`), `:118` (repoint to
    `"not_a_pack_xyz"`). `tests/test_interpreter.py` needs **no** edit (matrix derives from
    `sorted(registered_styles())`).
    T9 — `src/trackgen/tooling/corpus.py:105` `_CORPUS_PACKS` += `fusion_jazz` and `:102-104`
    stale comment; `tests/test_corpus.py` `:31` `_PACKS`, `:172` pinned triple, `:178-182`
    rationale docstring, `:200` (`44 instead of 48` → `56 instead of 60`), `:223,225,226`
    (`pinned_48_cell_matrix` rename + `== 48` ×2 → 60), `:228` pack set, `:243` `== 48` → 60,
    `:300-305` zero-null branch; `tests/test_bless.py` `:50,253,541` counts, `:703`
    ("the other 36" → 48), `:763` ("12 of 48" → "12 of 60"), `:764` ("the other 36" → 48),
    `:893,894,895`, `:913` ("48 cell(s)" → 60). `tooling/bless.py:164` `_MAX_WRITTEN_ROWS = 60`
    already sized. Remaining `test_bless.py` counts are `len(_CELLS)`-derived and self-update.
18. **Observed but NOT actioned (recorded for C9):** every mood sees exactly **1** surviving
    candidate in `tune_16` / `modal_32` / `intro` (only `vamp` and the dorian/minor `finals`
    ever draw ≥2) — zero *pool* variety. The variety lint covers pattern banks only, so
    nothing fires. §6.3 is authored as pinned (D16: pools are the pinned defining content);
    this is an authoring-quality observation for the C9 ledger, not a C8 change.
    Also: `modal_32` reaches ~13 % of heads; the `tune` template under-fires at slow moods
    (52 minBars at 75–84 BPM needs ~170 s) and `maxLengthSec` ≤ 75 s renders the degenerate
    `{section: solo, bars: 16}` fallback ~53–97 % of the time.

---

## Decision items — USER APPROVAL GATE

> **RATIFIED 2026-07-21: S22-1 … S22-9 ALL approved as recommended** ("all as recommended").
> Every "Recommended:" option below is binding; every "Alternative" is rejected.

- **S22-1 (arbitration rule 2, routine):** §6.1's printed manifest omits the required
  `formatVersion` + `engine`. Author `formatVersion: 1` / `engine: ">=0.1"` and amend §6.1 in
  the landing commit. **Recommended: approve.** *(S21-1 replay.)*
- **S22-2 (arbitration rule 2, routine):** §6.1's `modes` order is a hard load failure.
  Author `[major, mixolydian, dorian, minor]`, reorder `tonics` to match, amend §6.1.
  Behaviorally inert (verified for all 8 moods). **Recommended: approve.** *(S20-1 replay.)*
- **S22-3 (THE HEADLINE — the deceptive substitution on tonic-ending pools):** constraint 4.
  The pinned §3.3 / PHASE_4-D6 claim that `turnarounds: []` keeps both transforms inert is a
  **wrong derived claim**; PHASE_4's normative algorithm text wins, and fusion's same-tag
  adjacency wakes the deceptive rule 874× per 336 renders. **Recommended (option A):**
   1. **Fix the `vamp` pool** so vamps genuinely loop (DoD §14.10): rotate `minor_launch` to
      end open — `a: [[i7], [~], [iiø7], [V7(#9)]]` (pure rotation, all content preserved,
      exactly §3.3's own lo-fi "author rotated to end open" rule); and amend `sus_pedal` to
      `a: [[I7sus4], [~], [~], [bVII7]]` (a one-chord tonic pedal *cannot* be rotated open —
      this keeps the pedal for 3 of 4 bars and ends on the mixolydian bVII, squarely in
      idiom). `dorian_funk` and `mixo_vamp` are already safe.
   2. **Leave `tune_16` as printed** and accept the deceptive substitution at head/solo
      chorus boundaries — this is precisely the relaunch device D6 built ("replace the
      terminal tonic to relaunch the form"), and a substituted chord at a chorus turnaround is
      idiomatic jazz. Recorded honestly in the caveat, with the known limitation that the
      substitution is **fixed and draw-free**, so every chorus relaunches with the same chord.
   3. **Amend** §3.3's "Vamps loop untouched by construction" / PHASE_4 D6's "both inert when
      the pack ships no turnarounds" to state the real rule: *both transforms are inert only
      absent same-tag adjacency; with same-tag adjacency and an empty `turnarounds` list, the
      deceptive fallback fires on any tonic-rooted T-function section ending.*
  **Alternative B (more conservative):** additionally re-rotate `cantaloupe_class`'s and
  `dominant_16`'s phrase `d` so tune heads never drift either — but `cantaloupe_class`'s
  `i7 | bVI7(#11) | vi7 | i7` shape is the pack's pinned identity and rotating it damages it.
  **Alternative C (not recommended):** accept all 874 substitutions and amend DoD §14.10's
  "vamps loop without harmonic drift" — the orchestrator-reproduced `I7sus4 | vi` alternation
  is a real musical defect, not a flavor.
  **Alternative D (not recommended):** gate the deceptive rule in the engine — contradicts
  PHASE_4 §5.1/§5.4 normative text, and breaks contingency 14's zero-engine-change streak.
- **S22-4 (quartal empty-candidate hard crash):** constraint 5. **Recommended:** amend §6.4's
  comping voicing classes to `{1: [quartal, rootless_a, rootless_b], 2: [quartal, rootless_a,
  rootless_b], 3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}` — a two-token data
  fix that closes an uncaught `ValueError` at the pack's own signature key (Bb dorian), keeps
  quartal as the pinned low-rung signature (it is tried first), and needs no engine change.
  **Alternative (not recommended):** accept + caveat — weak, because §6.1 pins Bb dorian as
  the Chameleon key and a crash is not a dormancy.
- **S22-5 (rung dormancy — the C-23 third instance):** constraint 6. Rung 1 is dead grid-wide;
  rung 4 is `tune`-only; breakdown renders drums+bass only. **Recommended: author §6.4's
  ladder exactly as printed — NO re-map** (unlike blues' S21-2). Reasons: rungs 2–4 are all
  genuinely live and carry §6.4's defining content (`fu_dr_2` sits at rung 2, which is live);
  PT5 + variety require a rung-1 bank regardless; and §6.4's rung-1 content (sparse funk,
  root/♭7 halves, footballs) is the ladder's least load-bearing tier. Record the measured
  dormancy as a caveat (**C-28** — renumbered from the draft's C-26, which S22-10 took when
  it was raised later at T1) with the per-template rung table, and annotate §6.4.
  **Alternative:** push rung-1 content up a tier as blues did — rejected here because it would
  displace live, correct content for no reachability gain.
- **S22-6 ("the first dorian-primary pack" — wrong derived claim):** constraint 8. Measured
  auto mode-resolution is major 6/8, dorian 1/8 (mysterious), minor 1/8 (tense); **mixolydian
  is unreachable** (no fusion mood sits in its V ∈ [0.00, 0.25) band), and the corpus triple
  (energetic, calm, tense) captures **zero dorian cells**. **Recommended: annotate §6.1** with
  the measured resolution table (arbitration rule 2), accept the mixolydian dormancy as a
  caveat (P6 requires the content regardless), and **compensate at the test layer** — pin
  explicit-`key.mode` dorian renders (Bb and D dorian, incl. the `cantaloupe_class` /
  `dorian_funk` / quartal paths) in `tests/test_fusion_jazz_pack.py`, since the pinned §8.2
  corpus matrix cannot cover them. **Alternative (not recommended):** amend §6.1's mood set or
  the §8.2 corpus mood rule — both are larger pinned-design changes for a coverage gap that
  tests close directly.
- **S22-7 (timbres defects):** constraint 12. **Recommended: approve all four** — invent
  `fusion_ride_kit` in-idiom (ride-forward `funk_kit` sibling; the §6.6 bus/master is
  pack-wide so it differs at voice level only); `synth_moog` keeps `Q: 4` + gains a
  `brightness → filterEnvelope.baseFrequency` override; `clav`'s attack moves to an
  `attackHardness` band; `glass_pad` gains a `brightness → modulationIndex` override. Annotate
  §6.6 for all four.
- **S22-8 (minor derived-sample annotations):** §6.1's "at the slow edge (75-90) it reaches
  63-66%" is wrong — measured 61.5–65.5 % (the "58% at 100 BPM" and "straight at ~120+" claims
  are both exact). §6.1's "`Bb dorian = Chameleon`" — auto renders take `tonics[mode][0]` = D;
  Bb needs an explicit `key.tonic`. §3.5's **`13sus` is not a legal token** (`unrecognized
  quality suffix`) and appears in prose only, never in §6.3's YAML — nearest legal spelling
  `I7sus4(13)`. **Recommended: three one-line annotations, no behavior change.**
- **S22-9 (pack version):** manifest lands at `version: 0.1.0` per §6.1 (S20-4/S21-5
  precedent). **Recommended: 0.1.0.**
- **S22-10 (RAISED AT T1, RULED 2026-07-21 — the first engine change of C6/C7/C8):**
  T1 found, and the orchestrator independently confirmed, a **stage-6 ordering defect**.
  Pinned order is `6a HOLD → 6b devices → 6c mutation` (`transitions/stage.py:4-6`); 6b's
  dropout truncates every note sustaining across a breakdown entry (`devices.py:166`, §3.5),
  then 6c's `_hat_lift` sets `duration_ticks = 360` on an offbeat-8th hat
  (`mutation.py:161`). The last offbeat 8th in a bar is pos 1680, so the lift extends to 2040
  — 120 ticks past the bar line — **re-introducing exactly the sustain the dropout removed**,
  and W2 (`quality/layer1.py:391-399`) correctly fires. Measured ~4 % of T1's 168 scratch
  renders. `_hat_lift` is the **only** operator that lengthens a note. This is not a fusion
  authoring choice: §6.2's `breakdown`, §6.5's `hat_lift: 1`, and §6.4's `fu_dr_2`
  `{pos: 1680, voice: hat_closed}` are all pinned verbatim. **fusion_jazz is the first pack to
  combine `hat_lift` with `breakdown`** (pop_rock ✓/✗, jazz ✗/✗, chill_lofi ✗/✓, blues ✓/✗) —
  which is why four prior packs never reached it. **User ruled: ENGINE FIX — clamp the lift**
  so it never sustains past a dropout-entered breakdown boundary, which is what §3.5 already
  mandates for every other note. **Provably a no-op for all four existing packs** (none
  combines the two ingredients); the no-op is **self-verifying** — all 6327 tests, every
  golden, and all 48 corpus cells must stay byte-identical. **If any golden moves, the fix is
  NOT a no-op: stop and re-escalate for the full contingency-14 bless collateral
  (generatorVersion bump, serialize/milestone literals, 48-cell re-bless).** Rejected:
  dropping `hat_lift` from §6.5 (leaves the defect live for the next pack), and
  accept-and-caveat (knowingly ships renders failing a hard Layer-1 validator).

- **S22-11 (RAISED AT T2, RULED 2026-07-21):** §6.4's bass rung-2 parenthetical is internally
  inconsistent. Prose "tresillo skeleton (3+3+2 in 16ths)" = 360+360+240 = **960 ticks**
  (2 cells/bar); the printed third duration **480** = 4 sixteenths overruns the next cell
  onset at 960 by **240 ticks**. The T2 reviewer confirmed nothing downstream truncates it
  (`retrigger` splits only at *chord* boundaries; there is no note-overlap validator), so the
  printed reading would emit **two simultaneously sounding bass notes** — refuting the
  "sustain deliberately exceeding its slot" reading. Per ROADMAP §3 rule 1 the **prose is the
  pinned data text** and the printed durations are the derived sample; T2's original authoring
  had the weights inverted. **User ruled: the literal 3+3+2 doubled cell is the weight-3
  anchor (`fu_bs_2`); the printed continuation is retained as the weight-2 sibling
  (`fu_bs_2b`)** — a valid whole-bar 3+3+4+3+3 ostinato, so both candidates are individually
  sound and the variety lint needs two anyway. Ids swapped so the anchor is unsuffixed.
  §6.4 annotated; `dur 480` recorded as a wrong printed sample.
- **S22-12 (RAISED AT THE E1 REVIEW, RULED 2026-07-21):** the E1 reviewer ruled that the
  S22-10 clamp requires a **logged deviation**, not silent absorption: PHASE_6 §3.7 pins
  `hat_lift` as "→ voice `hat_open`, **dur 360**", and 360 is an *algorithm-text constant*,
  not a derived worked-example sample — so ROADMAP §3's arbitration does not license changing
  it quietly. After the clamp, 360 is a **maximum**. **User ruled: annotate PHASE_6 §3.7's
  `hat_lift` row AND log caveat C-26**, recording the §3.5/§3.7 latent tension that the pinned
  6b→6c order creates, the currently-unreachable sub-60-tick no-op branch and its C-07-borrowed
  rationale, and the no-op evidence. Rejected: caveat-only with no §3.7 edit (a later reader of
  §3.7 would see "dur 360" flatly contradicted by the code with nothing pointing at the
  caveat — the exact failure the caveat log exists to prevent); and treating it as an ordinary
  bug fix requiring no record.
- **S22-13 (RAISED AT THE T3 REVIEW, RULED 2026-07-21):** §6.4 pins quartal as fusion's
  comping "low-rung signature", but quartal `[0, 5, 10, 15]`'s top voice is a **♯9**, which
  L2-1's allowed set (chord tones ∪ scale tones) rejects over fusion's majority
  auto-resolved key (F mixolydian, `I7` → F9). Measured: **19/192 renders fail**
  `validate_pipeline` (orchestrator); 71/448 (reviewer) — all six major-resolving moods,
  zero in mysterious/tense (dorian/minor already contain that ♭3). ♯9 over a dom7 is
  canonical funk/jazz vocabulary (the Hendrix chord), so **L2-1 was under-modelling altered
  tensions, failing correct music**. **User ruled: widen L2-1's allowed set to additionally
  admit the alterations PHASE_4 §6.4 already declares legal per chord quality** (dom7: 9, ♭9,
  ♯9, ♯11, 13, ♭13) — reusing the existing legality table, strictly additive.
  **Generation-neutral**: the orchestrator verified `quality/` is never imported anywhere in
  the generation path, so no golden moves, no re-bless, no `generatorVersion` bump — unlike
  S22-10. Rejected: dropping quartal from comping rungs 1–2 (measured 0/192 failures, but
  guts §6.4's pinned signature and makes DoD §14.10's "quartal **Rhodes** sits under C5"
  literally unsatisfiable, since rhodes is a *comping* flavor — quartal would live only on
  pads); reordering quartal last (measured **no effect**, 71/448 — the Viterbi cost is
  order-independent); deferring to T7 calibration (contradicts §8.1's bootstrap order, and
  T5's DoD slice requires `validate_pipeline == []` to land at all). §8.1 annotated; C-29.
- **S22-14 (RAISED AT THE T2 REVIEW, RULED 2026-07-21):** §6.4 pins "`approach` into changes"
  on rung-4 bass, authored as `{pos: 1680, dur: 240, degree: approach, push: true}`. The
  composition is broken: `push` advances the frame to the chord *after* the first boundary in
  span, so `_place_degree` resolves `approach` against `_next_chord(effective)` — the chord
  **two changes ahead**. ~~Orchestrator-measured over 48 renders: **0 of 399** approach events
  land a half-step below the chord arriving at the next barline. **The reviewer's claimed
  remedy was overstated** — it reported push-removal restoring 100%; two independent
  measurements (orchestrator 72/408 = 18%; fix agent 59/744-with-change = 16.5%) put it near
  **18%**, because the pattern tiles every bar while fusion's chords span 2–4 bars, so ~half
  of firings have no change to approach at all.~~ **User ruled: drop `push: true` from those two
  events, accept the residual, caveat it** ~~— the off-change firings are mostly benign
  (measured 56.5% land on the governing chord's root, 28.0% a perfect 5th)~~. Rejected:
  replacing `approach` with the blues chord-tone idiom on one or both siblings (a larger
  deviation from pinned §6.4 than the defect warrants). §6.4 annotated; flagged for the T8
  listening pass.
  **[CORRECTED 2026-07-21, T10 lens A — the ruling stands, the numbers and the rationale do
  not. Read this before citing anything struck above.**
  **(1) The retraction.** This block's sentence "**the reviewer's claimed remedy was
  overstated**" is **withdrawn**. The T2 reviewer was **right**: removing `push` restores
  approach correctness to **100 %**. It was the orchestrator's contradicting measurement that
  was **contaminated**, so the accusation of overstatement was itself the overstatement. The
  contamination: approach events were identified **positionally** as
  `ticks % 1920 == 1680 and duration_ticks == 240`, but **four** rung-4 bass events share that
  shape — `fifth` (vel 0.66, `fu_bs_2`), `root` (0.72, `fu_bs_3`), and the two genuine
  `approach` events (0.80 `fu_bs_4`, 0.82 `fu_bs_4b`). The `fifth` and `root` notes are
  essentially never a half-step below the arriving chord root, so they sat in the denominator
  and diluted the numerator; the "0 %", "18 %" and "16.5 %" figures are all artifacts of that
  bucket, not measurements of the device.
  **(2) The real numbers.** Isolating true approach notes **by velocity**: un-pushed on-change
  correctness is **16/16 = 100.0 %** (orchestrator re-measurement) and **580/580 = 100.0 %**
  (lens A, instrumented at the production `retarget_event` call site, larger sweep). Two
  independent methods, same answer.
  **(3) `push` is still correctly dropped — but not for the recorded reason.** The recorded
  mechanism (frame advanced two changes ahead) is not what usually happens:
  `apply_articulation` clamps the authored `dur: 240` to the gap (typically ~194 ticks), so the
  note generally ends *before* the barline, `_boundaries_in_span` comes back empty, and `push`
  silently falls through to the governing chord. `push` is thus **inert on the large majority
  of firings and actively wrong on the remainder** (lens A: wrong on 116 of 1328). Dropping it
  remains right; the "0 of 399" framing that justified it was not.
  **(4) The residual is real but differently shaped.** ~50 % of approach firings (orchestrator
  16/32; lens A 56.3 %) have **no chord change at the next barline**. In those bars the degree
  does **not** "fall back to the governing chord" — `resolve_degree_pc` returns
  `(root(next timeline chord) − 1) % 12`, i.e. a **leading tone to a chord that has not arrived
  yet**. Measured against the *sounding* chord: orchestrator found 12 of 16 off-change notes
  inside chord tones ∪ scale and **4 outside — 12.5 % of all approach firings**; lens A
  measured 25 % of off-change notes outside, i.e. **14.1 % of all firings**. The honest
  statement is **~12–14 % of approach firings are a short chromatic bass note against the
  sounding chord**. That is defensible for a ~194-tick bar-end pickup, but it is **not**
  "mostly benign / musically inert", and nothing about it lands on "56.5 % root / 28.0 % P5".
  The acceptance is unchanged; the grounds for it are now stated accurately.]**

- **S22-15 (RAISED AT THE S22-13 IMPLEMENTATION, RULED 2026-07-21):** the S22-13 widening did
  the bulk of the work but did **not** fully clear L2-1. Quartal `[0, 5, 10, 15]` carries
  **two** tensions over a dominant: the ♯9 (offset 15, now legal) **and a natural 11**
  (offset 5 = P4). §6.4 excludes `11` on dom7 (only `#11`) — correctly: a P4 over a dominant
  is the classic avoid note, which is why `7sus4` exists as a separate chord. (`min7` *does*
  admit `11`, which is exactly why mysterious/tense — dorian/minor — were always clean.)
  Measured after the widening: **2/400 renders fail**, each from a **single** offending note
  against the 0.98 threshold (ratios 0.970 on 33 notes, 0.929 on 14); the implementing agent
  measured 5/192 on its own seed set.
  **[CORRECTED 2026-07-21 — the "0.5 %" this ruling was originally granted against is
  superseded. Four independent measurements on different seed sets: orchestrator 2/400
  (0.50 %), implementing agent 5/192 (2.60 %), T6 audition sweep 7/384 (1.82 %), T10 lens B
  4/384 (1.04 %, ratios down to 0.867). The honest figure is **~1–2 %**, i.e. 2–4× the number
  in the original ruling. T6's corrected 1.82 % was restated to the user BEFORE the T8
  listening gate, so the acceptance is informed — see the `listening/log.jsonl` session-22
  entry. The accepted residual is caveated at **C-30**.]**
  **[SUPERSEDED 2026-07-21, T10 lens A — a **fifth** independent seed set measured 12/384
  (**3.12 %**), above all four figures above, so "~1–2 %" is now "**~1–3 %**". C-30 carries all
  five measurements (0.50 / 1.04 / 1.82 / 2.60 / 3.12 %) and is the authoritative record; the
  6× spread means the rate is seed-set sensitive and should be planned against at the top of
  the range. The ruling and the informed-acceptance argument above are unaffected.]**
  **All 12 actual fusion_jazz corpus cells validate
  clean** (verified: energetic/calm/tense × 120/240 s × both pinned seeds → 0/12), so T9 is
  unaffected. A clean A/B on the current pack: quartal at comping r1–2 → 2/400; quartal
  removed → 0/400. **User ruled: accept the residual, caveat it, and let T7 calibration set the
  real per-pack threshold.** Rationale: `validate_pipeline` is a QA report, not a generation
  path (nothing crashes); §8.1's own bootstrap order is defaults → listening → `calibrate`,
  and §12 Q4 pins the L2 thresholds as **data**, tunable per pack without design change — so
  a fusion comping threshold set from the blessed batch is the designed outcome, not a
  workaround. Preserves both §6.4's pinned quartal signature and DoD §14.10's "quartal
  **Rhodes** sits under C5". **If T8 listening dislikes the quartal-over-dominant sound,
  revisit then — with ears, not arithmetic.** Rejected: dropping quartal from comping r1–2
  (clean at 0/400 but costs the §6.4 signature and makes §14.10's clause unsatisfiable, since
  rhodes is a *comping* flavor); widening L2-1 again to admit natural 11 on dom7 (musically
  wrong, and would take dom7's allowed set to 12/12, eroding the gate for all five packs —
  the implementing agent measured the reached maximum at 11/12 and warned against this).
  **T5 consequence:** its end-to-end property slice must not assert `validate_pipeline == []`
  over arbitrary seeds — pin the corpus-clean coordinates, or assert the accepted rate
  explicitly rather than zero.

---

## Task list (all subagents opus; parallel only on disjoint files)

### T1 — config quintet (opus)
**Files:** `styles/fusion_jazz/manifest.yaml`, `interpreter.yaml`, `forms.yaml`,
`progressions.yaml`, `transitions.yaml`.
Author verbatim from PHASE_8 §6.1–§6.3 + §6.5 with exactly the ruled deviations: manifest
gains `formatVersion: 1` + `engine: ">=0.1"` (S22-1); `modes`/`tonics` in ladder order
(S22-2); the `vamp`-pool re-rotations (S22-3). Scoping pre-validated §6.2/§6.3/§6.5 as
otherwise **VALID** — F11 passes (tempo lo 75 → bar budget 9 ≥ 4); P1/P4/P5/P6/P7/P9/P11 all
pass; every token parses incl. `bVI7(#11)`, `iiø7`→min7b5, the five `7sus4` tokens,
`VIImaj7`, `bVImaj7`, `V7(#9)`; **P7 does NOT bite the shared `vamp` tag** (`loader.py:152-158`
gates `need_open` on `intro`/`verse` only — the handoff's P7 concern is unfounded; the real
hazard on that boundary was S22-3). **Verification:** scratch script model-validating each
file + re-running the cross-file checks, plus a render-level assertion that no `vamp`-tag
section ends with a `deceptive` tag. Report files written, checks run, any §6 ambiguity found
(escalate, don't resolve). **No commit** (constraint 1). Review: opus, diff-scoped.

### T2 — drums + bass banks (opus, parallel with T3/T4)
**Files:** `styles/fusion_jazz/patterns/drums.yaml`, `patterns/bass.yaml`.
Per §6.4 conventions, ladder as printed (S22-5). Drums (~15 entries): r1 sparse funk (kick 1,
cross-stick → **`perc`**, 8th hats); r2 light 16th funk with **hard quarter accents** —
**`fu_dr_2` verbatim from §6.4:709-717 plus `role: drums`**; r3 full funk (`minDensity`-gated
16th hats, ghost snares) **plus the second weighted displaced-backbeat entry (snare on the "a"
of 1, tick 360 — Chameleon's signature)**; r4 ride 8ths + busy kick; fills = 16th linear
figures (1920 ticks, ≥1 event at `pos ≥ 960` for TR7), ≥1 ungated. Bass (~12,
`mode: patterns`, retarget `{28, 45, retrigger}`): r1 root/♭7 (`seventh`) halves; r2 **tresillo
skeleton** (3+3+2 in 16ths — `root`@0 dur 360, `seventh`@360 dur 360, `root`@720 dur 480 …);
r3 16th funk, root/octave with `minDensity`-gated ghost 16ths on the e/a; r4 dense 16ths,
octave pops, `approach` into changes, pushes. **Every (kind, rung) slot ≥2 ungated candidates**
(constraint 9) incl. intro/ending, 3/2 sibling weights; **every `pos % 120 == 0`**
(constraint 11 — no triplet content anywhere); `layeringOrder: [drums, bass, comping, pads]`
once in drums.yaml. Ids `fu_dr_*` / `fu_bs_*` (siblings `b`, intro `i/ib`, ending `e/eb`, fills
`f1/f2`); ladders monotone (the C5 T7 lesson). **Verification:** scratch model-validation
(PT1/PT2/PT3/PT5/PT9/PT12), grid-purity sweep, velocity sweep. No commit. Review: opus.

### T3 — comping + pads banks (opus, parallel with T2/T4)
**Files:** `styles/fusion_jazz/patterns/comping.yaml`, `patterns/pads.yaml`.
Comping (~12) per §6.4: r1 footballs; r2 sparse syncopated stabs + and-of-4 `push`; r3 16th
anticipations; r4 clav-style stabby 16ths. Voicing classes **per the S22-4 ruling**
(`rootless_b` added at rungs 1–2). Pads (~12): `{1–4: [quartal]}`, sustained,
`onChordChange: retrigger`. Retargets `{50, 69}` / `{45, 64}` (constraint 13). ≥2 ungated
candidates per slot incl. intro/ending; ladders monotone; `fu_cp_*` / `fu_pd_*` ids; every
`pos % 120 == 0`. C-21: do NOT try to enforce a register floor via retarget — lanes own
chord-voicing registers. **Verification:** scratch model-validation (PT5/PT7/PT9), grid
purity, and a **quartal-emptiness sweep** re-running scoping's 1296 (mood, key, token) matrix
to confirm the S22-4 fix leaves zero raising combinations. No commit. Review: opus.

### T4 — timbres (opus, parallel with T2/T3)
**File:** `styles/fusion_jazz/timbres.yaml`.
All **8** flavors (constraint 12): the §6.6 defining entries verbatim except the three ruled
fixes (`synth_moog` Q-override, `clav` attack band, `glass_pad` brightness override) plus the
invented `fusion_ride_kit`. `rhodes` brightness → `modulationIndex` 3–14 + tine
`modulationEnvelope` + carrier decay 2.2 + light Chorus; `clav` MonoSynth saw + resonant
lowpass filterEnvelope + `AutoFilter {frequency: 2.5, baseFrequency: 350, octaves: 2.5,
depth: 0.5, wet: 0.4}`; `electric_finger` **must be authored MonoSynth**; `analog_poly`
fatsawtooth (count 3, spread 25) + StereoWidener (**`width` only**); `funk_kit` tight and dry
(kick decay 0.22, snare 0.12, sustain 0), bus `reverb {decay: [0.6, 1.8], preDelay:
[0.008, 0.02], returnFilterHz: 400}` — the driest of the five packs; master `[Compressor
{threshold: -20, ratio: 2, attack: 0.03, release: 0.25}, Limiter]`. Kit flavors define all 9
voices; NoiseSynth voices omit `midi`; no fixed `mix.sends.reverb` on comping/pads.
**Verification:** scratch `TimbresConfig.model_validate` + allowlist dry-run over every emitted
path + `assert_base_xor_mod` over every flavor. No commit. Review: opus.

### T5 — integration + fusion test suite → **commit 1** (opus)
**Files:** `tests/test_interpreter_pack.py` (`:114` set, `:118` repoint), new
`tests/test_fusion_jazz_pack.py` + `tests/test_fusion_jazz_variety.py`.
1. First full `resolve_pack("fusion_jazz")` + `trackgen lint styles/fusion_jazz/` → drive to
   **0 errors / 0 unannotated warnings** (bounded fix loop with T2/T3/T4 scopes).
2. Author tests: bank-inventory pins; **`fu_dr_2` verbatim golden**; variety/selection locks
   per the C5/C6/C7 convention (every golden-blind candidate gets a locked seed winning the
   production draw); **first-use pins** — quartal comping *and* pads render with all pitches
   ≤ 71 (§14.10); the S22-4 fix pins **no `ValueError`** across the full (mood, key, token)
   override matrix; an authored-extension slot consumes **ZERO** dressing draws and
   `ChordSpec.extensions` carries `#11`/`#9` verbatim; `feelTable: tight` threads to the
   humanizer; swing16 resolves from the table at fusion tempos (no override) and 8th-grid
   positions pass through untouched; `AutoFilter` reaches the document; **S22-3 regression —
   no `vamp`-tag section ever ends `deceptive`**; **S22-6 — explicit `key.mode: dorian`
   renders (Bb and D) validate clean and exercise `cantaloupe_class`/`dorian_funk`**;
   breakdown strips to drums+bass and the next main rebuilds; plan fully populated. Plus the
   end-to-end property slice: default params + (V,A) extremes × 2 lengths × ≥5 seeds →
   serialize, `validate_document == []`, `validate_pipeline == []`.
3. Four gates green → **commit 1** (pack + tests + literal updates + §3.3/§6 amendments per
   S22-1…S22-8, one commit).
Review: opus, whole-T1–T5 diff (content vs §6 clause-by-clause under the rulings; tests
non-vacuous).

### T6 — full-grid audition + first-use verification pass (opus, report-only)
§9.4 step 7. Render the whole supported grid — 8 moods × both length classes × 2+ seeds,
`--explain` samples — via `generate_trace`; `validate_pipeline` + `pipeline_warnings` on every
render. Confirm empirically: rung-2/3 content in heads/mains → rung-4 in late `tune` solos;
**zero deceptive tags on `vamp` sections** and the measured `tune_16` count recorded honestly;
pads enter at the 4-layer moods and breakdown strips to 2; quartal registers ≤ 71; the
displaced-backbeat entry fires; `stop` lands when drawn; no W7 grid violations; **zero
`ValueError`s across the explicit-key override matrix**. Report anomalies with evidence;
substantive findings → fix agents (≤2 cycles), gates re-run.

### T7 — calibrate → **commit 2** (orchestrator + opus artifact check)
§9.4 step 8. `uv run trackgen calibrate styles/fusion_jazz/` → `calibration.yaml` (first batch:
L2 thresholds = engine defaults, §8.1 bootstrap). Independent opus artifact check (shape,
L2-reader activation, band sanity, mood coverage 8/8, byte-identical re-run). Note the `vamp`
template's `close: fade` **will** produce ritard-tail lines (unlike blues' all-`cold` forms —
the C5/`82679f8` tail labeling applies). Gates → commit.

### T8 — USER listening gate (user + orchestrator)
§9.4 steps 7b–9 / DoD §14.8 + §14.10 fusion slices: playground audition of the §14.10
checklist — **16th pocket is tight** (the `tight` feelTable's first outing), **vamps loop
without harmonic drift** (the S22-3 fix, by ear), **quartal Rhodes sits under C5**,
**breakdown strips to drums+bass and rebuilds** — plus a formal error-spotting pass over fresh
seeds (≥1 cell per supported mood), entries appended to `listening/log.jsonl`; every entry
fixed (fix agent + gates + re-calibrate if content changed) or filed. **Hard stop for user
participation.** No corpus capture until this passes (§8.1 bootstrap order).

### T9 — corpus completion → **commit 3** (orchestrator)
§9.4 step 10. `_CORPUS_PACKS` += `"fusion_jazz"`; literals per constraint 17; unscoped
`uv run trackgen bless --approve` → 12 first-capture cells under
`fixtures/goldens/fusion_jazz/**`, **48 existing cells verified zero-divergence**. **Corpus
reaches 60/60 — C-17 closes and DoD §14.5 becomes markable PROVEN** (record it in the ledger
with evidence). No generatorVersion bump (first capture; contingency 14 otherwise). Expect
~42 MB total on disk (C-17's projection). Gates → dedicated bless commit (D11).

### T10 — whole-chunk 3-lens review + close-out (opus ×3 + fix agent)
Fresh opus reviewers over the whole chunk: (a) content correctness vs §6-as-amended
clause-by-clause + first-use verification; (b) contract/DoD compliance (§14.3/§14.8/§14.10
fusion slices **and §14.5's corpus clause**, honest ledger); (c) test quality/coverage
(non-vacuous, discriminating, golden-blind slots selection-locked; measure the fusion blind set
for the C-20/C-22/C-23 record). Validation agents on findings; fix loop ≤2 cycles; gates.
Close-out: PROGRESS.md (statuses, session log row, fresh handoff for **C9 — the Phase 8
close-out**), CAVEATS entries (S22-3 deceptive/§3.3+D6 amendment; C-28 rung-1 + mixolydian
dormancy; S22-4 quartal note; **C-17 status → resolved**), final commit.
