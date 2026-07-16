# SESSION_07 — Phase 5, Chunk 2 (Arrangement planner + pattern selection)

Resume mid-phase (`@PROMPT.md - Phase 5`). Chunk 1 (session 06) is COMPLETE — loaders,
foundations, reference banks, DoD 1+2 proven, 735 tests green. This session builds the
**Arrangement planner** (`arrange()`, §4) and the **pattern-selection machinery** (§3.2),
proving **DoD 3** and **DoD 4**. Chunk 3 (generators/walker/voicing) and Chunk 4
(orchestrator/Serializer/milestone) come later.

## Scope

**In scope**

- `arrange(plan, form, pack, rng) → ArrangementPlan` — §4.1 role activation, §4.2 density
  budget, §4.3 register lanes + `registerBias` clamp/≤71 ceiling. Fully deterministic: the
  `rng` is accepted for interface uniformity and **never consumed** in v1 (the `arrangement`
  stream is reserved, zero draws — §3.6, §4).
- New engine data `src/trackgen/arrangement/lanes.yaml` (§4.3 lane table).
- Pattern-selection machinery (§3.2) — one draw per `(role, kind, rung)` per song, cached in
  form order; kind mapping (`intro`→`intro`, `outro`→`ending`, else→`main`); tempo-band
  eligibility; `weighted_choice` **draw-iff-≥2** on each role's `select` sub-stream (§3.6).
- Golden + property tests proving DoD 3 (§4.5 arrangement tables, zero-draw, property) and
  DoD 4 (§9.1 draw narratives — pop 1 / jazz 3, completeness property).

**Out of scope** (do not build; later chunks)

- Any part generator (drums/bass/comping/pads), the walker, the voicing Viterbi passes — Chunk 3.
- The orchestrator, Serializer, timbres, milestone fixtures, whole-document goldens — Chunk 4.
- Retargeting/velocity/gating (Chunk 1, already built in `parts/retarget.py` + `parts/dynamics.py`).
- Any change to `packs/`, `harmony/`, `form/`, `schema/` — those contracts are frozen for this chunk.

## Contracts consumed (all already built + committed)

- **Schema** (`schema/ir.py`, Phase 1 core — do NOT modify): `ArrangementPlan{entries:list}`,
  `ArrangementEntry{section_id, role, active, intensity(1–4), density_budget(0–1), register}`,
  `Register{low_midi, high_midi}`. `arrange()` populates exactly these fields.
  `GenerationPlan.tempo_bpm`; `GenerationPlan.budgets` → `Budgets{note_density, layers_max,
  register_bias, …}`. `SongForm.sections: list[FormSection{id, type, index, start_bar,
  length_bars, energy, phrases, …}]`.
- **Intensity** (`arrangement/intensity.py`, Chunk 1): `intensity(energy: float) -> int` (1–4),
  §3.1 thresholds 0.30/0.55/0.80. Reuse verbatim — do not reimplement the ladder.
- **Pack surface** (`packs/models.py::StylePack`, Chunk 1): `pack.layering_order: tuple[Role,…]|None`
  (§4.1 order; both reference packs `[drums, bass, comping, pads]`); `pack.patterns: dict[str,
  list[PatternEnvelope]]` keyed by role; `PatternEnvelope{.kind, .energy_level(1–4), .weight(≥1),
  .eligibility, .is_gated}` with `Eligibility.tempo_bpm: tuple[int,int]|None`;
  `pack.bass_mode: "patterns"|"walking"|None`. `PatternKind = "main"|"fill"|"intro"|"ending"|"break"`.
- **Seeds** (`seeds.py`): `stream_seed(master, overrides, name) -> int`, `stream_rng(...) ->
  Random`, `derive(parent:int, name:str) -> int`, `weighted_choice(items, weights, rng)`, `Rng =
  random.Random`. §3.6 draw discipline: the role's select stream is `derive(stream_seed(master,
  overrides, role), "select")` → `Rng(seed)` (confirm against §3.6 wording; follow the harmony
  stage's injected-rng convention — `harmony/stage.py` takes `rng` as a param, tests inject a shim).
- **Rounding convention**: 3-decimal half-even is Python's built-in `round(x, 3)`; integer
  half-even is built-in `round(x)`. `clamp01` lives in `interpreter/moods.py`. No `round3` symbol
  exists — use `round(...)` (see `parts/dynamics.py` docstring). `round(-1.5) == -2`,
  `round(2.256, 0)`→2 — banker's rounding, exactly what §4.3 needs.

## Golden anchors (orchestrator pre-verified — reproduce, do not tune)

Arrangement (§4.5), pop/happy (`noteDensity` 0.648, `layersMax` 4, `registerBias` +0.188):

| Section | energy | rung | count | densityBudget | active |
| --- | --- | --- | --- | --- | --- |
| intro-1 | 0.340 | 2 | 2 | 0.586 | drums, bass |
| verse-1 | 0.490 | 2 | 3 | 0.644 | drums, bass, comping |
| chorus-1 | 0.790 | 3 | 4 | 0.761 | + pads |
| verse-2 | 0.540 | 2 | 3 | 0.664 | drums, bass, comping |
| chorus-2 | 0.840 | 4 | 4 | 0.780 | + pads |
| bridge-1 | 0.440 | 2 | 3 | 0.625 | drums, bass, comping |
| chorus-3 | 1.000 | 4 | 4 | 0.842 | + pads |

Jazz/melancholic (`noteDensity` 0.505, `layersMax` 3, `registerBias` −0.125): head-1/head-2 rung 2
count 3 density 0.494; solo-1/2/3 rung 3 count 3 densities 0.543/0.567/0.591; outro-1 rung 2 count 3
density 0.458. Active everywhere: drums, bass, comping (pads capped out by `layersMax` — the trio).

- `densityBudget = round(clamp01(noteDensity × (0.7 + 0.6 × energy)), 3)`, uniform across a
  section's active roles (verified: 0.648×(0.7+0.6×0.340)=0.585792→0.586; …×1.0→0.842).
- `count = min(layersMax, baseCount[rung])`, `baseCount = {1:2, 2:3, 3:4, 4:4}`;
  `intro`: `count = max(1, count(next section) − 1)`; `breakdown`: `min(count, 2)`;
  `bridge`: `min(count, 3)`. `active` = first `count` roles of `layering_order`; **every**
  `(section, role)` pair emits an entry, inactive → `active: false`.
- Lanes (`lanes.yaml`): `drums` exempt 0–127, `bass` 28–55, `comping` 48–71, `pads` 43–71.
  `registerBias` shifts **comping + pads only** by `shift = round(bias × 12)`; apply to both ends,
  then cap `high_midi` at 71 (the C-06 ceiling), `low_midi` unclamped. bass/drums never shift.
  Verified: pop shift +2 → comping 50–71, pads 45–71; jazz shift −2 (round(−1.5) half-even) →
  comping 46–69, pads 41–69.

Selection draws (§9.1): **pop 1** (drums rung-2 draw {pr_dr_2a, pr_dr_2b}→`pr_dr_2a`; every other
role/kind/rung is a single candidate → 0 draws), **jazz 3** (drums rung-3 draw {jz_dr_3a w3, jz_dr_3b
w2}→`jz_dr_3a`; comping rung-2 draw {jz_cp_2a w3, jz_cp_2b w2}→`jz_cp_2a`; comping rung-3 draw {jz_cp_3a
w3, jz_cp_3b w2}→`jz_cp_3a`; drums rung-2/ending, comping ending single; jazz bass is `mode: walking`
→ **no** pattern selection; jazz pads dormant → never active → 0 pads draws).

## Tasks

T1 ‖ T2 in parallel (disjoint file sets). T3 after both.

### T1 — Arrangement planner + `lanes.yaml`  ·  model: **opus**  ·  proves **DoD 3**

**Files (create):** `src/trackgen/arrangement/arrange.py`, `src/trackgen/arrangement/lanes.yaml`,
`tests/test_arrange.py`. **May edit:** `src/trackgen/arrangement/__init__.py` (export `arrange`).
**Touch nothing else.**

**Implements:** PHASE_5 §4.1 (role activation), §4.2 (density budget), §4.3 (register lanes +
`registerBias` clamp/ceiling), §3.6 (arrangement stream reserved, zero draws). §4.5 is the golden.

**Requirements:**
- `arrange(plan: GenerationPlan, form: SongForm, pack: StylePack, rng: Rng) -> ArrangementPlan`.
  The `rng` is a parameter for interface uniformity and **must never be consumed** (no `.random`,
  `.randrange`, `weighted_choice`, etc. anywhere in `arrange`). The planner is pure arithmetic.
- `lanes.yaml` is engine-owned data loaded + validated once at import (mirror
  `arrangement/intensity.py`'s load/validate/frozen-model pattern): the four §4.3 lanes, each a
  `[low, high]` with `0 ≤ low < high ≤ 127` and `high − low ≥ 12` (the §3.3/D6 folding invariant);
  `drums` = 0–127. A missing/malformed file raises a clear load error.
- Role activation exactly per §4.1: compute each section's `rung = intensity(section.energy)` and
  `count`; apply the `intro`/`breakdown`/`bridge` modifiers. The `intro` rule needs the **next
  section's** count — compute base counts in a first pass, then resolve intro relative to its
  successor. Edge guard: an `intro` that is the last section (degenerate/fallback form) has no
  successor → fall back to its own base `count` (document the choice in a comment).
- Emit an `ArrangementEntry` for **every** `(section, role)` pair over `pack.layering_order`
  (`active` per §4.1); if `layering_order is None` raise a clear error (a Phase-5-capable pack must
  declare it — the reference packs do). `intensity` = the section rung; `density_budget` = §4.2
  (uniform across the section); `register` per §4.3 (drums exempt lane; comping/pads shifted+clamped).
- Section `type` values come from the form stage (`intro`, `verse`, `chorus`, `bridge`, `outro`,
  `head`, `solo`, `breakdown`, …). Only `intro`/`breakdown`/`bridge` trigger count modifiers; all
  other types use the base `count`. Read the reference `forms.yaml`/§4.5 to confirm the exact `type`
  strings before hard-coding them.

**Tests (`tests/test_arrange.py`) — DoD 3:**
- **§4.5 goldens field-for-field**: build both worked plans (pop_rock/happy, jazz/melancholic via
  the real interpreter→form pipeline at seed `1ps9wxb`, master 3735928559 — mirror how
  `tests/test_form.py`/`test_harmony_*` obtain the upstream IRs) and assert each section's rung,
  count, active-role set, `density_budget` (3-dp), and comping/pads `register` against the tables
  above. Assert every `(section, role)` pair is present with the right `active`.
- **Zero-draw**: pass a `_CountingRandom` shim (copy the one in `tests/test_harmony_goldens.py`,
  counts `randrange`) as `arrange`'s `rng`; assert the count is **0** after generating both plans.
- **Mechanism units**: `baseCount` per rung; the three type modifiers (incl. `breakdown` min-2,
  `bridge` min-3); intro-relative-to-successor incl. the no-successor edge; `registerBias` shift +
  ≤71 clamp at representative biases (incl. a large positive bias that forces the clamp, and a
  negative one); `density_budget` boundary/rounding (identity-ish + a half-even tie).
- **Property matrix** (mirror `test_form.py`'s matrix: pop_rock+jazz × supported moods × lengths ×
  25 seeds): for every plan — full section×role coverage (one entry per pair); active-role count ≤
  `layersMax` and ≤ `count`; `active` roles are exactly the first `count` of `layering_order`; every
  non-drum entry `high_midi ≤ 71` and `low_midi < high_midi`; `intro` count < successor count (when
  a successor exists); `density_budget ∈ [0,1]` at 3 dp; `intensity == intensity(energy)`.

**Verify:** four gates green; the two §4.5 tables reproduce with zero doc edits.

### T2 — Pattern-selection machinery  ·  model: **opus**  ·  builds toward **DoD 4**

**Files (create):** `src/trackgen/parts/selection.py`, `tests/test_selection.py`.
**May edit:** `src/trackgen/parts/__init__.py` (export the selection entry point).
**Touch nothing else.** (Disjoint from T1 — different package.)

**Implements:** PHASE_5 §3.2 (pattern selection), §3.6 (select sub-streams, draw discipline).
The loader already enforces the §3.2 completeness rules (Chunk 1) — this task consumes that
guarantee, it does not re-validate the bank.

**Requirements:**
- Provide a selection function, e.g. `select_patterns(plan, form, arrangement, pack, master,
  overrides) -> dict[tuple[str, Role], PatternEnvelope]` mapping `(section_id, role)` → the chosen
  pattern for every **active, pattern-mode** `(section, role)`. (Pick the exact signature/return
  shape; keep it minimal and Chunk-3-friendly. Consuming the `ArrangementPlan` gives you `active`
  + `intensity` per pair without recomputing — take `arrangement` as a param. You may also expose
  the `(role, kind, rung) → pattern` cache for golden assertions.)
- **Kind mapping** (§3.2): `intro`→`intro`, `outro`→`ending`, everything else→`main` (incl.
  `breakdown`, which uses `main` at its low rung). Cache key is the pinned `(role, kind, rung)`.
- **Cache-once, form order** (§3.2): iterate sections in form order; the first active `(section,
  role)` whose `(role, kind, rung)` key is unfilled performs the selection; later sections reuse it.
  Same-rung sections share their groove (verse-1 ≡ verse-2); rung-3 chorus vs rung-4 final chorus
  differ.
- **Eligible set** (§3.2): for `main` — role patterns with `kind == "main"` **and** `energy_level ==
  rung` **and** passing eligibility. For `intro`/`ending` — all role patterns of that kind passing
  eligibility (`energy_level` ignored). **Eligibility** = `eligibility.tempo_bpm is None` OR
  `lo ≤ plan.tempo_bpm ≤ hi`.
- **Selection = `weighted_choice`(eligible in authored order, `[p.weight]`, select-stream rng),
  draw-iff-≥2** (the PHASE_3 D13 idiom — see `harmony/stage.py`: `if len(xs) >= 2: weighted_choice(...)
  else xs[0]`, so a singleton consumes **zero** draws). Each role draws on its own `select`
  sub-stream (§3.6): `Rng(derive(stream_seed(master, overrides, role), "select"))`. One rng per
  role, reused across that role's draws in section order.
- **bass walking-mode exemption** (§3.2): when `pack.bass_mode == "walking"`, the bass role does
  **no** pattern selection (the walker serves every section/kind) — skip bass entirely. Pattern-mode
  bass selects normally.
- Only **active** roles select (an inactive `(section, role)` contributes nothing — this is why
  jazz pads, never active under `layersMax` 3, draw zero).

**Tests (`tests/test_selection.py`) — mechanisms + draw counting:**
- Kind mapping (all three branches incl. `breakdown`→main and `outro`→ending).
- Cache-once: two same-rung `main` sections resolve to the **same** pattern with a **single** draw;
  a different-rung section re-draws (own key).
- Eligibility: a tempo-gated pattern is excluded outside its band and included inside; `main`
  filters on `energy_level == rung`, `intro`/`ending` ignore `energy_level`.
- Draw discipline: singleton eligible set → **0** draws (counting shim on the role's select rng);
  a ≥2 set → exactly 1 draw and the `weighted_choice` winner matches an independent
  `Rng(derive(...))` replay.
- bass walking-mode → bass produces no selections and consumes no `bass/select` draws.
- Use small synthetic packs/forms and/or the real reference packs; construct `ArrangementPlan`
  inputs directly from the schema where that isolates the unit under test from `arrange()`.

**Verify:** four gates green.

### T3 — §9.1 selection goldens + completeness property  ·  model: **opus**  ·  proves **DoD 4**

**Files (create):** `tests/test_selection_goldens.py`. **Touch no source and no other test file.**
Depends on T1 (`arrange`) and T2 (`select_patterns`) — dispatch after both land + are committed.

**Implements the DoD-4 evidence:** the §9.1 draw narratives end-to-end over the real reference packs.

**Tests:**
- **Pop draw narrative**: run interpreter→form→`arrange`→`select_patterns` for pop_rock/happy at
  seed `1ps9wxb`. Assert selected patterns: drums intro `pr_dr_i`, rung-2 `pr_dr_2a` (the draw
  winner over {pr_dr_2a, pr_dr_2b}), rung-3 `pr_dr_3`, rung-4 `pr_dr_4`; bass/comping/pads single
  candidates. Assert **total pop select draws == 1** (counting shim summed across all four role
  select streams).
- **Jazz draw narrative**: same for jazz/melancholic. Assert drums rung-2 `jz_dr_2`, rung-3
  `jz_dr_3a` (winner over {jz_dr_3a w3, jz_dr_3b w2}), ending `jz_dr_e`; comping rung-2 `jz_cp_2a`
  (winner), rung-3 `jz_cp_3a` (winner), ending `jz_cp_e`; bass = no selection (walking); pads never
  active. Assert **total jazz select draws == 3**.
- **Completeness property** (DoD 4): for every pack (pop_rock, jazz) × supported mood × a spread of
  tempi covering each pack's `tempo_range` (and the eligibility bands present in §7): every
  reachable `(role, kind, rung)` — reachable = appears for an active, pattern-mode role in some
  section of that plan — **resolves to a pattern** (selection never comes up empty). This exercises
  the loader's completeness guarantee through the selection path.

**Verify:** four gates green; both draw narratives + counts reproduce with zero doc edits.

## Whole-chunk review (after T1–T3 committed)

Two fresh **opus** review lenses in parallel (per PROMPT §3), scoped to the chunk's whole diff:

1. **Correctness + contract compliance** — `arrange` matches §4.1–§4.3 (count rules, modifiers,
   density formula, lane shift/clamp) and selection matches §3.2/§3.6 (kind map, cache-once-in-order,
   eligibility, draw-iff-≥2, bass-walking exemption, active-only); the `arrangement` stream truly
   draws zero; no frozen contract (schema/pack/harmony/form) was touched.
2. **Test quality + DoD 3/4** — the §4.5 and §9.1 goldens are doc-transcribed (not tuned to code
   output) and non-vacuous; the property matrices are real (25-seed spread, genuine invariants); the
   counting shims prove the exact draw counts (0 / 1 / 3). Confirm DoD 3 and DoD 4 each provable
   item-by-item with named tests.

Validation agent before any fix; confirmed findings → fix agent + gate re-run (max 2 cycles/task).

## Definition of done — this chunk targets DoD 3 + 4

- [ ] **§13.3 Arrangement stage** — both §4.5 tables field-for-field; zero-draw (counting shim on the
  arrangement stream); property matrix (section×role coverage, `active ≤ layersMax`, lanes within
  ceilings, intro thinner than successor). Evidence: `tests/test_arrange.py`.
- [ ] **§13.4 Selection** — both §9.1 draw narratives (selections + exact counts pop 1 / jazz 3);
  completeness property (every reachable `(role, kind, rung)` resolves per pack × mood × tempo).
  Evidence: `tests/test_selection.py` + `tests/test_selection_goldens.py`.

## Verification (every task)

`uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy` — all green,
output read, before each commit. Never claim a gate passes without running it this session.

## Notes / caveat watch

- No design ambiguity is expected here; §4 and §3.2 are fully pinned and both worked examples are
  computed in §4.5/§9.1. If a printed §4.5/§9.1 sample diverges from the faithful algorithm, follow
  golden-value arbitration (ROADMAP §3): the algorithm text wins — escalate for sign-off before any
  doc amendment; never tune code to a printed number.
- The lane-shift ceiling is the C-06 handoff item ("Chunk 2's `arrange()` + `lanes.yaml` owns the
  ≤71 ceiling + registerBias clamp"). Retarget (Chunk 1) folds within whatever lane it is handed —
  the ceiling correctness lives here.
- Module placement (`arrangement/arrange.py`, `parts/selection.py`) and the `select_patterns`
  signature/return shape are orchestrator/implementer calls within scope — not design re-pins.
