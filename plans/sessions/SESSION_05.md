# SESSION_05 — Phase 4 Harmony engine, Chunk 2 (the stage + goldens)

**Status: awaiting approval — no implementation agent dispatched.**

This is the **final session of Phase 4**. Chunk 1 (SESSION_04) built the pieces —
theory library, dressing ladder, `progressions.yaml` loader + reference packs — and
proved DoD 1/2/3/8. Chunk 2 assembles them into the Harmony **stage** and proves the
remaining DoD items **4, 5, 6, 7, 9, 10**. Per PROMPT §3, the whole-implementation
review at the end runs across **both chunks together** and completes the full §14 DoD.

Read alongside this file: `PHASE_4.md` §5 (generator), §5.1 (normative algorithm),
§5.2 (density filter), §5.4/§5.5 (transforms), §5.6 (RNG), §7 (extension points),
§7.4 (scale table), §10 (both worked examples — the golden fixtures), §14 (DoD);
`ROADMAP.md` §3 (golden-value arbitration); `CAVEATS.md` C-03/C-04.

---

## Scope

**In scope (this session):**
- The `HarmonicPlan` §7 schema extension in `src/trackgen/schema/ir.py` (additive to the
  pinned core): plan-level `keys` + `pool_selections`; per-event `scale` / `function` / `tags`.
- The Harmony stage `harmony(plan, form, progressions, rng) -> HarmonicPlan` in
  `src/trackgen/harmony/stage.py`, implementing §5.1 **exactly**: gate → density filter →
  per-tag selection + per-slot dressing → timeline assembly with hold-merge → the three
  boundary transforms (turnaround / deceptive / final close) → emit.
- The full golden/determinism/property/deceptive test surface for DoD 4/5/6/7/9.
- The §13 amendment-consistency check (DoD 10) — orchestrator-run.

**Explicitly out of scope:**
- Any change to the Chunk-1 modules (`theory/*`, `harmony/dressing.*`, `packs/*`,
  `styles/*/progressions.yaml`). They are settled contracts this session **consumes**.
  A change there means a bug was found — STOP and escalate, don't edit in-line.
- P11 / parenthesized extension groups (Phase 8 — `resolve_token` already rejects them).
- Voicing goldens (`quartal`/`fifths`, C-04) — PHASE_5 §13.6.
- Any note emission, modulation (only one `keys` region in v1), or repeat-instance
  harmonic variation (identical bodies by design, D7).

**Model policy (binding, PROMPT §"Subagent model rules"):** every dispatch sets `model`
explicitly. T1/T2/T3 are non-trivial (schema contract, the stage algorithm, doc-normative
goldens) → **opus**. T4 is an orchestrator doc-verification pass (no agent).

---

## Ready-made building blocks (Chunk 1, already committed — import, don't reimplement)

- `trackgen.seeds`: `stream_rng(master, overrides, "harmony") -> random.Random`;
  `weighted_choice(items, weights, rng)` (draw surface; **integer weights**).
- `trackgen.theory`: `resolve_token(token, key) -> ChordSpec`;
  `chord_function(token) -> "T"|"S"|"D"|"O"`; `chord_scale(spec, key) -> ScaleHint(root_pc, name)`;
  `chord_symbol(spec, key) -> str` (**re-derive after dressing mutates quality/extensions**);
  `extensions_legal(quality, extensions) -> bool`.
- `trackgen.harmony.dressing`: `tier(dissonance) -> int` (baseTier); `effective_tier(base, fn)`;
  `dressing_options(spec, was_bare, function, base_tier, key) -> [(ChordSpec, weight)]`
  — returns the ordered option list **and applies the function offset internally**; **the
  stage performs the draw** (`weighted_choice` iff ≥ 2 options; else take the sole option, 0 draws).
- `trackgen.packs.models`: `ProgressionsConfig{pools: {tag: (PoolEntry,...)}, turnarounds, finals}`;
  `PoolEntry.phrases: {label: (Bar,...)}`, `.density` (cached §4.2), `.final_chord_token()`;
  `TurnaroundEntry/FinalEntry.bars`; a `Bar` is a `tuple[str,...]`; a hold bar is `("~",)`.
  Loader already enforced P1–P10 + cross-file P1/P4/P6/P7, so pool content is well-formed.
- `SongForm` (Phase 3): `sections[FormSection{id, type, index, start_bar, length_bars,
  energy, phrases:[{label,bars}], harmony_tag, variant, ending}]`, `total_bars`, `template_id`.
  `start_bar` × `ticks_per_bar` = section startTick.

---

## Tick / assembly facts (pin these; wrong ticks fail DoD 4)

- 4/4, PPQ 480 ⇒ **1920 ticks/bar** (`plan.time_signature` + PHASE_1 PPQ). A bar of `n` tokens
  (n ∈ {1,2,4}) splits its 1920 ticks **evenly**: each token event = `1920 // n` ticks.
- A `("~",)` bar **extends the previous event's `duration_ticks` by 1920** — no new event —
  **only within one phrase instance**. Phrase- and section-boundary events are never merged:
  a repeated phrase re-states its first chord as a fresh event (§3.1 last bullet). The loader
  guarantees `~` is never a phrase's first bar, so a hold always has a predecessor in-phrase.
- Events tile `[0, total_bars × 1920)` with no gaps/overlaps; each event's tick range lies
  inside its section's `[start_bar×1920, (start_bar+length_bars)×1920)`.

---

## Task list (ordered; T1 → T2 → T3 serial — each imports the previous; T4 = orchestrator)

### T1 — `HarmonicPlan` §7 schema extension — **opus**
**Files:** `src/trackgen/schema/ir.py`; tests in `tests/test_schema.py` (or a focused new test).
**Implements:** PHASE_4 §7.1/§7.2/§7.3 (the extension points PHASE_1 §4.3 reserved).
**Do (additive only — never touch the pinned `{start_tick, duration_ticks, section_id, chord}`
core or any other IR):**
- New IR model `KeyRegion{start_tick: int≥0, tonic_pc: int 0–11, mode: str}` (§7.1).
- Extend `ChordEvent` with: `scale: ScaleHint-shaped {root_pc: int 0–11, name: str}` (required),
  `function: Literal["T","S","D","O"]` (required), `tags: list[str]` (default `[]`).
  Model the scale as a small frozen IR model (e.g. `EventScale`), **not** the theory
  `ScaleHint` NamedTuple (IR models are pydantic; keep the module boundary clean). Field
  names stay **snake_case** (IR models are internal, never serialized — see the `ir.py` header).
- Extend `HarmonicPlan` with: `keys: list[KeyRegion]` (v1: exactly one entry at tick 0),
  `pool_selections: dict[str, str]` (default `{}`) — §7.3 provenance.
**Constraints:** frozen models (`IRModel`); additive fields only; no behavior. If any pinned
field would change type/name, STOP.
**Return report:** the exact new/changed model definitions; confirmation the pinned core is
untouched; the test names added; gate status.
**Verification (T1):** a test constructs a `HarmonicPlan` with `keys` + `pool_selections` and a
`ChordEvent` carrying `scale`/`function`/`tags`; asserts defaults (`tags == []`,
`pool_selections == {}`) and that the model is frozen. Four gates green.

### T2 — The Harmony stage (§5.1) — **opus**
**Files:** `src/trackgen/harmony/stage.py` (new); export from `src/trackgen/harmony/__init__.py`;
mechanism unit tests in `tests/test_harmony_stage.py` (new).
**Implements:** PHASE_4 §5.1 (normative order), §5.2 (density filter, resolves Q3), §5.3
(one draw per distinct tag), §5.4 (turnaround), §5.5 (final close), §5.6 (RNG discipline),
§7.2/§7.4 (per-event scale/function/tags), §7.1 (keys), §7.3 (pool_selections).
**Signature:** `harmony(plan: GenerationPlan, form: SongForm, progressions: ProgressionsConfig,
rng: random.Random) -> HarmonicPlan`. The caller builds `rng = stream_rng(master, overrides,
"harmony")`; the stage takes the rng (mirrors how `form()` is structured — but note `form()`
builds its own rng; match whichever the reviewer/orchestrator confirms is the established
convention. **Decision: take `rng` as a parameter** so tests can inject a counting shim; the
pipeline wiring passes `stream_rng(...)`. Document this in the docstring.).

**Algorithm — implement §5.1 in this exact order (draw order is load-bearing for DoD 6):**
1. `d = plan.budgets.dissonance`; `base_tier = tier(d)`; `V = plan.mood_vector.valence`;
   `key = plan.key`. `ticks_per_bar = 1920` (assert 4/4 numerator/denominator match PPQ).
2. `tags` = distinct `section.harmony_tag` in **first-appearance order** over `form.sections`.
3. **Per tag** (in that order): (a) `eligible` = pool entries passing mode (`key.mode ∈ modes`),
   valence (`V ∈ band` if present), dissonance (`d ∈ band` if present) gates. (b) Apply the
   **density filter §5.2**: if `plan.budgets.harmonic_rhythm_base == 0.5`, restrict `eligible`
   to entries with `density ≤ 1.0` **iff that subset is non-empty**, else leave `eligible`
   unchanged; otherwise (incl. `== 1.0`) no restriction. (Faithful reading: only 0.5 triggers
   the filter; every other authored value is inert — the two reference moods give 1.0 and 0.5.)
   (c) `entry = weighted_choice(eligible, [e.weight...], rng)` **iff `len(eligible) ≥ 2`**, else
   the sole entry (0 draws). (d) **Dress** the entry: for each phrase label (authored order),
   each bar (order), each **non-hold** token (order), build the slot's `ChordSpec` via
   `resolve_token`, then `opts = dressing_options(spec, was_bare, chord_function(token),
   base_tier, key)`; `dressed = weighted_choice([s for s,_ in opts], [w for _,w in opts], rng)`
   **iff `len(opts) ≥ 2`**, else `opts[0][0]` (0 draws). `was_bare` = token had no quality suffix.
   Record `pool_selections[tag] = entry.id`. Cache the dressed progression per tag (D7: reused
   by every section sharing the tag — **one draw per distinct tag**, never per instance).
4. **Assemble** the timeline: per section (form order), walk `section.phrases`; for each phrase
   instance instantiate the tag's dressed `phrases[label]`; emit a `ChordEvent` per non-hold
   token with `start_tick`, `duration_ticks` (even split), `section_id`, `chord` (dressed spec,
   `chord_symbol` re-derived), `scale = chord_scale(dressed, key)`, `function =
   chord_function(token)`, `tags = []`. **Merge holds within the phrase instance** (extend the
   previous event's duration). Boundary/first-bar events are never merged across phrase instances.
5. **TURNAROUND §5.4** — for each boundary where `sections[i]` and `sections[i+1]` share a
   `harmony_tag`, **in timeline order**: find section i's **terminal tonic run** (maximal
   trailing whole bars whose events are degree-1-rooted **and** function `T`); `eligible`
   turnaround entries = gates pass **and** `len(bars) ≤ run_bars`; if any: draw iff ≥ 2, dress
   its chords (same per-slot rule, draws continue the append-only sequence), **replace** the
   run's last `len(bars)` bars, set replaced events' `tags = ["turnaround"]`, record
   `pool_selections["turnaround:<section_i.id>"] = entry.id`. Else if the section's last event is
   degree-1-rooted → **DECEPTIVE** (dormant in v1): replace that chord with the fixed substitute
   (major-class modes → `vi min7`; minor-class → `bVI maj`), **no draw**, `tags = ["deceptive"]`.
   (Mode class: major/mixolydian/lydian = major-class; minor/dorian/phrygian = minor-class.)
6. **FINAL CLOSE §5.5** — draw a `finals` entry (gates; draw iff ≥ 2); dress; **replace the last
   `len(bars)` bars of the final section** (the section carrying `ending`); replaced events
   `tags = ["final"]`; `pool_selections["finals"] = entry.id`. Unconditional/idempotent.
7. **Emit** `HarmonicPlan(keys=[KeyRegion(start_tick=0, tonic_pc=key.tonic_pc, mode=key.mode)],
   chords=[...], pool_selections=...)`.

**RNG discipline §5.6 (must match exactly):** all draws via `weighted_choice` on the passed
`rng`, in the §5.1 order — per-tag `[select, dressing…]` (tag first-appearance order) →
per-boundary `[select, dressing…]` (timeline order) → finals `[select, dressing…]`. **Draw only
when ≥ 2 candidates/options.** Ladder/table lookups and the deceptive rule never draw. Append-only.

**Turnaround/deceptive dominant-functioning note (C-03):** the loader already guarantees every
turnaround entry ends dominant-functioning (P8, incl. the SubV `bII7`); the stage does **not**
re-derive that. Terminal-tonic-run detection uses `chord_function == "T"` **and** root pc ==
`key.tonic_pc` (degree-1). Reuse `chord_function`/the resolved root — do not add a second
function implementation.

**Constraints:** determinism (no wall-clock/unseeded randomness — all entropy via the passed
rng); integer weights only; every emitted `ChordSpec` must satisfy `extensions_legal` (assert in
a test); the pinned `ChordSpec` shape is produced exactly. Do not modify any Chunk-1 file.

**Return report:** the stage's public surface + `__init__` export; the precise draw-order
implementation (which lines draw); how hold-merge and the terminal-tonic run are computed; how
the density filter's "non-empty else inert" branch is coded; the mechanism-test names; gate status.

**Verification (T2):** `tests/test_harmony_stage.py` unit-tests each mechanism on **small
synthetic** inputs (not the §10 goldens — those are T3): mode/valence/dissonance gate filtering;
density filter both branches (restrict when non-empty; inert when the restriction would empty the
set; inert at base 1.0); one draw per distinct tag (two same-tag sections share the identical
dressed body); hold-merge within a phrase (a `("~",)` bar extends duration, emits no event) vs a
repeated phrase re-stating its first chord; terminal-tonic-run detection + turnaround swap +
`tags`/`pool_selections`; deceptive fallback (synthetic same-tag adjacency, no eligible
turnaround) picks `vi min7` / `bVI maj` with 0 draws; final-close replacement + idempotence;
every emitted spec `extensions_legal`; `keys == [{0, tonic_pc, mode}]`. Four gates green.

### T3 — Goldens, determinism, property, deceptive, seed vectors — **opus**
**Files:** `tests/test_harmony_goldens.py` (new). **Source is frozen** — this agent must NOT edit
`src/`; it treats `harmony()` as a black box and asserts doc-normative expectations.
**Implements DoD 4 (goldens half), 5, 6, 7, 9.**
**Golden-value discipline (ROADMAP §3):** every expected value is **transcribed from PHASE_4 §10 /
§5.6 (the doc)** — never copied from code output. If the stage diverges from a §10 value, **STOP
and report** (it is an implementation bug or a genuine doc ambiguity for arbitration) — do **not**
adjust the expected value to match code, and do **not** touch `src/`.
**Do:**
- **DoD 4 — event-for-event goldens.** Chain from PHASE_2 §6.5 GenerationPlans + PHASE_3 §7.4
  SongForms (seed `1ps9wxb`, master 3735928559, harmony stream seed 226146634901021418). Build
  both plans the way the existing interpreter/form golden tests build theirs (reuse those
  fixtures/helpers). Assert **Example 1** (pop_rock/happy, E major, tier 0): **76 events**, the
  §10.1 chord table (E·A·E·A intro; E·A·E·B verses; E·B7·C♯m·A choruses; C♯m·A·E·B bridge;
  chorus-3 tail …E·B7·**A·E** from `plagal`), ticks (all 1920, startTicks per `start_bar`),
  scales (E ionian, A **lydian**, B/B7 mixolydian, C♯m aeolian), functions (E=T,A=S,B=D,C♯m=T),
  `tags` (`["final"]` on chorus-3's last two events, `[]` elsewhere),
  `pool_selections == {intro: tonic_vamp, verse: anchor, chorus: axis, bridge: depart_six,
  finals: plagal}`, the §10.1 sample event (chorus-1 bar 13 = `B7`, startTick 24960). Assert
  **Example 2** (jazz/melancholic, D minor, tier 4): **56 events** (64 bars: 5×12 head/solo/head + 4 outro, minus hold-merges per §3.1 — §10.2 pins no event count),
  the §10.2 dressed 12-bar body (Dm9·Gm9·Dm9·Gm11·Dm9·B♭13·A7♭9·Dm9…), the four per-boundary
  turnaround tails (§10.2 table: head-1 minor_turn, solo-1 minor_two_five, solo-2/solo-3
  minor_turn), head-2 closed, outro-1 = Dm9·Gm11·Eø7 A7♭13·Dm7 (finals minor_close on bars 3–4),
  scales/functions per §10.2, `tags` (`turnaround`/`final`), the full §10.2 `pool_selections`.
  **`symbol` is ASCII** (`B7`, `Em7b5`, `A7b13` — not `Eø7`/`A7♭13` prose glyphs; assert ASCII).
- **DoD 5 — seed vectors §5.6.** Assert `derive(3735928559,"harmony") == 226146634901021418`;
  a fresh `random.Random` on that seed gives `getrandbits(32)` first-five
  `[1607822876, 501707672, 365345814, 982234362, 2945966636]` and `randrange(100)` first-five
  `[47,14,10,29,87]` **in the stage draw sequence** (i.e. these are the same stream the stage draws on).
- **DoD 6 — determinism.** Same inputs → identical `HarmonicPlan` (run twice, assert equal).
  A **counting-RNG shim** (wrap `random.Random`, count `randrange`/`getrandbits`/`weighted_choice`
  entries) asserts **8 draws** for Example 1 and **30 draws** for Example 2. A **singleton-candidate**
  fixture (a form/pack where every tag has one eligible entry and every slot one option) consumes
  **0 draws**. An **append-only** check: a form/budget change that adds a section shifts no draw
  before its first divergent candidate set (the earlier draws reproduce identically).
- **DoD 7 — property matrix.** For each reference pack × each supported mood × `max_length_sec ∈
  {30,45,…,600}` × 25 seeds: run interpret→form→harmony, assert the plan validates —
  chords tile `[0, total_bars×1920)` no gaps/overlaps; every event inside its section's tick
  range; every `ChordSpec.quality` in the PHASE_1 enum with §6.4-legal extensions; every event
  carries `scale` + `function`; **final event of the song is degree-1-rooted**; prechorus/bridge
  sections end **D-function**; `keys == [{0, tonic_pc, mode}]`; same-tag sections have **identical
  bodies outside replaced bars**; `pool_selections` complete (a key per distinct tag + each swapped
  boundary + `finals`). (Reuse the Phase 3 property-test harness shape.)
- **DoD 9 — deceptive fixture.** A **synthetic** same-tag adjacency with **no eligible turnaround**
  (e.g. a hand-built pack with an empty `turnarounds` list + a form with two adjacent same-tag
  sections whose first ends degree-1-rooted) exercises the deceptive rule end-to-end: the boundary
  event becomes `vi min7` (major class) / `bVI maj` (minor class), `tags == ["deceptive"]`, **0 draws**
  for the substitution. (This is the only exerciser of the dormant rule — Q7.)
**Return report:** which §10 rows/events were asserted; the exact 8/30 draw accounting reproduced
independently from the packs + §5.1 (so the reviewer can check it); any divergence found (with the
doc value vs the code value) escalated rather than papered over; gate status.
**Verification (T3):** `uv run pytest tests/test_harmony_goldens.py` green; four gates green.

### T4 — §13 amendment-consistency check (DoD 10) — **orchestrator (no agent)**
Verify the seven §13 amendments are present and consistent in the referenced docs (PHASE_1 §7 Q4/Q6
+ §4.3; PHASE_2 §7.2 + §9 Q3; ROADMAP §2 + §4). These were "applied in the same commit as PHASE_4"
per §13, so expect **no edits** (mirrors Phase 2 T6 / Phase 3 T5). Record the line-anchored evidence
in PROGRESS.md's DoD checklist. If any amendment is missing/inconsistent, escalate (arbitration).

---

## Per-task loop (PROMPT §2, applied to each of T1–T3)

1. Dispatch the implementer (opus, self-contained prompt pointing at this file + the named
   PHASE_4 sections + the exact source files + the building-block imports above).
2. **Gates** (orchestrator runs, reads output): `uv run pytest` · `uv run ruff check .` ·
   `uv run ruff format --check .` · `uv run mypy`.
3. **Review** (opus, scoped to this task's diff): tests real/meaningful (not vacuous, not tuned
   to pass — for T3 especially: are the expected values the DOC's, and is the draw accounting
   independently reconstructed?); code matches the pinned §-section; no contract violated; no
   Chunk-1 file edited.
4. **Fix loop** (max 2 cycles/task): dispatch fix agent per confirmed finding, re-gate, re-review.
   Survive-past-2 → escalate with evidence.
5. **Commit** at the verified gate; update PROGRESS.md immediately (task done, hash).

## Whole-implementation review (final session of the phase — PROMPT §3, across BOTH chunks)

After T1–T4: dispatch **fresh** opus review lenses in parallel over the **entire Phase 4
implementation** (Chunk 1 + Chunk 2) — (a) correctness/logic (stage algorithm + transforms +
tick math + draw order); (b) contract compliance vs PHASE_4 (every §-section, both worked
examples, all extension points); (c) test quality & DoD coverage (are 1–10 genuinely proven,
goldens doc-sourced, property invariants complete); (d) code quality/simplification. Each finding
→ validation agent (confirm real) → fix agent + gate re-run (2-cycle bound). Then walk the **full
§14 DoD 1–10** with evidence (test names, fixture paths, command output); re-attest 1/2/3/8 from
Chunk 1 with pointers, prove 4/5/6/7/9/10 fresh. **Orchestrator pre-gate obligation (handoff):**
independently reproduce the full **8-draw (Ex1)** and **30-draw (Ex2)** sequences from the packs +
§5.1, and spot-check §10 per-chord facts, before accepting the goldens. Finish all gates green; commit.

## Close-out (PROMPT §4)

Update PROGRESS.md (Phase 4 → **done**, session-05 log row, DoD 1–10 all proven, fresh handoff
block pointing at **Phase 5** — the largest phase, ~4 chunks: loaders/foundations → arrangement →
generators/walker/voicing → orchestrator+Serializer+milestone; note the reserved C-04 voicing
decisions land in PHASE_5 §13.6). Add CAVEATS entries for any Chunk-2 deviation (e.g. if the §5.2
"other harmonic_rhythm_base values inert" reading needs recording, or any §10 sample found wrong
under arbitration). Report to me: what was built, gate evidence, DoD status, caveats, next session.

---

## Risks / watch-items

- **Draw order is the fragile contract.** Ex1=8 / Ex2=30 only hold if the per-tag
  `[select, dressing…]` → per-boundary → finals order and the "draw iff ≥ 2" rule are exact.
  Anchor (Ex1): intro 1 (select; slots single-option) + verse 2 (select + V@effTier1 two-option)
  + chorus 2 (select + V dom7) + bridge 2 (select + V) + finals 1 = **8**; 0 boundary draws
  (pop turnarounds empty, no same-tag adjacency). The reviewer/orchestrator must re-derive both.
- **`symbol` ASCII vs §10 prose glyphs** (handoff): assert `Em7b5`/`A7b13`, not `Eø7`/`A7♭13`.
- **Secondary dominants cool, not heat** (handoff, §3.2): `VI7`/`III7`→T, `II7`/`bII7`→S; dressing
  offset applies to the §3.2 function, correct-by-design. Don't "fix" this in the stage.
- **Hold-merge scope**: within a phrase instance only; never across phrase/section boundaries.
- **Density filter edge**: the restriction applies **iff non-empty**, else inert — an easy off-by.
- **Do not edit Chunk-1 files.** A needed change there = a found bug = escalate.
