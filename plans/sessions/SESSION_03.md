# Session 03 — Phase 3: Form & Structure

**Status:** awaiting user approval (step-1 gate).
**Phase:** 3 (`plans/PHASE_3.md`). Fresh phase, single session, not split into chunks.
**Consumes:** PHASE_1/2 contracts — `GenerationPlan` (`max_length_ticks`, `time_signature`, `style_pack`, `mood_vector.arousal`) and the `SongForm` pinned core + its Phase-3 extension slots (`schema/ir.py`); the seed system (`seeds.py`, `form` stream already registered) + `weighted_choice`; the pack loader/models (`packs/`, the optional-`interpreter.yaml` pattern to mirror for `forms.yaml`); the `pop_rock`/`jazz` reference packs.
**Produces:** the `SongForm` extension fields; the `forms.yaml` pack schema + F1–F13 validation + reference `forms.yaml` for both packs; the engine energy model (`src/trackgen/form/energy.yaml`); and the Form generator stage (`form(plan, forms) → SongForm`) implementing PHASE_3 §7.1 exactly.

This file is written for implementer subagents with **zero prior context**. Each task lists the exact files to read, the exact files to touch, the constraints, and the verification it must pass.

---

## 0. Orientation for every subagent

Read first, always: `plans/PHASE_3.md` in full, `plans/ROADMAP.md` §3 (invariants + golden-value arbitration), and this file's task. Then the specific PHASE-doc sections named in your task.

**Binding invariants (ROADMAP §3):** style packs are data not code (templates, weights, gates, ladder order, envelopes are all YAML; the energy base table is engine data); determinism — no wall-clock, no unseeded randomness outside `src/trackgen/seeds.py` (Ruff TID251 enforces the import layer; never work around it); hierarchical seeds (draws come only from the `form` stream via `stream_rng(plan.seed.master, plan.seed.overrides, "form")`); soloist owns above ~C5 (this phase emits no notes and no register — untouched). Integer weights, ordered YAML lists, arithmetic fitting, 3-decimal half-even rounding for energies.

**Golden-value arbitration (ROADMAP §3):** the PHASE_3 printed sample numbers are derived samples; the algorithm/data *text* is authoritative. **However — the orchestrator has already independently recomputed every load-bearing sample this phase and they reproduce exactly:**
- Seed vectors (§7.2): `derive(3735928559, "form") = 7567330889165579844`; a fresh `random.Random` on it gives `getrandbits(32)[:5] = [1669109759, 4115657646, 81846092, 4122630717, 1459238978]` and `randrange(100)[:5] = [49, 2, 43, 66, 44]`.
- Example 1 (pop_rock/happy) — the **full 8-draw sequence** in §7.1 order: template→`verse_chorus_bridge`, intro-include, intro-bars 4, verse-bars 8, prechorus-**exclude**, chorus-bars 16, bridge-bars 8, outro-**exclude**; budget 92, total **76 bars**.
- Example 2 (jazz/melancholic) — **1 draw** total: intro-**exclude**; head forced to 12 (32 infeasible), 3 solos; total **64 bars**.
- All 13 energy cells across both examples (§7.4 tables) reproduce to 3 decimals.

**Pin these numbers as written; no amendment is expected.** If your faithful implementation nonetheless diverges, assume an implementation bug first; escalate to the orchestrator before touching any printed number.

**Gates (all four must be green; run and read output — never assume):**
```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

**Conventions established in Phases 1–2 (match them):**
- IR models (`schema/ir.py`) subclass `IRModel` (frozen; plain snake_case fields, **no** camelCase alias — IRs are never serialized into `TrackDocument`).
- Pack files that are part of the YAML contract subclass `PackModel` (`frozen=True, alias_generator=to_camel, populate_by_name=True, extra="forbid"` — see `packs/models.py`). `forms.yaml` models follow this exactly (like `InterpreterConfig`).
- Loaders read YAML via `yaml.safe_load`, wrap `OSError`/`YAMLError`/`ValidationError` into `PackLoadError` (see `packs/loader.py`); engine data (`energy.yaml`, like `moods.yaml`) loads by module-relative path into a frozen model.
- Draws only via `weighted_choice` (from `trackgen.seeds`) on the `form` stream; **only when ≥ 2 feasible candidates** (D13); append-only order (§7.2).
- Tests carry a docstring citing the PHASE section; golden numbers get a "normative — do not edit to match code" comment (see `tests/test_seeds.py`).

---

## 1. Session scope

**In scope (Phase 3 DoD §11 items 1–8):**
1. `forms.yaml` loader: frozen models + all §5.1 rules F1–F13; one rejection fixture per rule class; both reference files load clean.
2. Energy data (`src/trackgen/form/energy.yaml`, §6.1 base table) + a test asserting §6.1–§6.4 reproduce both worked examples' energy columns exactly (all 13 sections).
3. Form stage implementing §7.1 exactly; golden tests asserting both §7.4 SongForms **field-for-field**.
4. The §7.2 form-stream RNG vectors asserted exactly.
5. Determinism: same plan → identical SongForm; a counting-RNG shim asserting the exact draw count (8 for ex.1, 1 for ex.2) and zero draws on the fallback path; a draws-only-when-≥2-feasible budget-shift test.
6. Property tests: every pack × supported mood × `maxLengthSec ∈ {30,45,…,600}` × 25 seeds → a valid SongForm (contiguity, 4-bar grid, hard ceiling, energies, phrases sum, index/totalOfType, ending placement, labels).
7. Ladder & fallback: a fixture per degrade op class; 30 s at each pack's `tempoRange.lo` → valid ≥ 4-bar form; a tiny-budget fixture hits the fallback and still validates.
8. PHASE_3 §10 amendments applied and consistent.

**Explicitly out of scope:** harmony *content* (Phase 4 — this phase emits `harmony_tag` hooks only, no chords; no cadence field — D8); arrangement/pattern/fill/transition mapping (Phases 5/6 consume `energy` and the semantics table); pack *content* beyond the two reference `forms.yaml` files (Phase 8 authors chill_lofi/blues/fusion and exercises `main`/`breakdown`/`postchorus`/`variant`); wiring `form()` into a full pipeline run (Phase 5 orchestrator); cross-file `harmony_tag → progressions.yaml` referential check (deferred to Phase 4's loader, PHASE_2 D14 pattern).

---

## 2. Pinned scoping decisions (resolved by the orchestrator — do not relitigate)

These resolve ambiguities the PHASE doc leaves to implementation. Binding for this session.

- **D-S1 — `forms.yaml` is OPTIONAL in `load_pack`.** Mirror `interpreter.yaml` (session-02 D-S1): `load_pack` parses & validates `forms.yaml` into `StylePack.forms: FormsConfig | None` **when the file exists**; absent → `None` and the pack still loads (keeps `_stub` and all Phase-1/2 tests working untouched). `form()` requires a non-None `forms` and raises a clear error if absent.
- **D-S2 — `weighted_choice` item ordering (PINNED — orchestrator-verified to reproduce the §7.4 goldens).** Use `weighted_choice` from `trackgen.seeds` with these argument orders:
  - **optional inclusion draw:** `items = ["include", "exclude"]`, `weights = [incW, excW]` (the authored `optional: [incW, excW]` is include:exclude odds — include is the **first** item).
  - **bar-count draw:** `items` = the bar-count options in **authored order**; `weights` = their authored weights (e.g. `bars: [[4,3],[8,1]]` → `items=[4,8]`, `weights=[3,1]`).
  - **template draw:** `items` = eligible templates in **authored order**; `weights` = their `weight`s.
  This ordering reproduces Example 1's full 8-draw sequence and Example 2's single draw exactly. **Any other ordering silently breaks the goldens — do not change it without escalating.**
- **D-S3 — Energy data at `src/trackgen/form/energy.yaml`**, loaded module-relative (like `moods.yaml`) into a frozen `extra="forbid"` model. Content = the §6.1 base table for all 11 types. Engine-owned, recalibratable, internal.
- **D-S4 — Reference `forms.yaml` = the §5.3 (pop_rock) / §5.4 (jazz) content VERBATIM.** The §7.4 goldens depend on it exactly — weights, bar options, optional odds, `arousal` gate, `energy` override, degrade order, `ending`, `fallback`. Transcribe faithfully; do not "improve" the reference content.
- **D-S5 — `SongForm` extension fields are REQUIRED** (pinned by §4). See T1 for the exact field list. Any existing `FormSection`/`SongForm` construction site (e.g. in `tests/test_schema.py`) must be updated to supply them.
- **D-S6 — Avoid the `Phrase` name clash.** `schema/ir.py` already defines `Phrase` (§4.5, part-generator output). The per-section phrase-substructure item `{label, bars}` must use a **distinct** name — `SectionPhrase`. The ending directive submodel is `SectionEnding`.
- **D-S7 — `minimalTotal` / feasibility (pinned verbatim from §7.1 step 3).** `minimalTotal` = spine sum with excluded/undecided optionals counted as 0, unresolved types at their smallest bar option, the repeat block at `count.min`; recomputed at every feasibility check. An optional is drawn iff force-including it (at its type's smallest option) keeps `minimalTotal ≤ barBudget`, else excluded with no draw. A bar option is *feasible* iff choosing it keeps `minimalTotal ≤ barBudget`; ≥ 2 feasible → draw, exactly 1 → take it (no draw), 0 → take smallest authored (ladder repairs). Bar counts resolve **once per type** at the type's first included occurrence; inherit-target types share one resolution (D9). Repeat count and ladder ops are **arithmetic, never drawn**.
- **D-S8 — `ticksPerBar` from manifest `timeSignatures[0]` at PPQ 480.** `ticksPerBar = numerator × (480 × 4 // denominator)` (= 1920 in 4/4); `barBudget = maxLengthTicks // ticksPerBar`. Property `totalBars × ticksPerBar ≤ maxLengthTicks` must hold for every emitted form (hard ceiling).
- **D-S9 — Rounding.** Emitted `energy` = `round(value, 3)` (Python half-even), matching PHASE_2. All bar counts are integers; the 4-bar grid (multiple of 4, ≥ 4) holds for every `length_bars` including the fallback.
- **D-S10 — Labels per §3.3 (pinned specials).** `chorus`: `index == totalOfType and totalOfType ≥ 2` → `"Final Chorus"`, else `"Chorus {index}"` (no index if single). `head`: first → `"Head In"`, last → `"Head Out"`, middle → `"Head {index}"`. `solo`: `"Solo Chorus {index}"` (no index if single). `main`: `"Part {variant}"` if `variant` else `"Part {index}"`. All others: title-cased type, with `prechorus → "Pre-Chorus"` and `postchorus → "Post-Chorus"`; append `" {index}"` iff `totalOfType > 1`.
- **D-S11 — `form()` signature & seed boundary.** `form(plan: GenerationPlan, forms: FormsConfig) -> SongForm` constructs its own RNG internally via `stream_rng(plan.seed.master, plan.seed.overrides, "form")` (keeps the `random` boundary in `seeds.py`). It reads `plan.max_length_ticks`, `plan.time_signature`, and `plan.mood_vector.arousal`. The energy table loads once inside the stage (module-level cache like `load_moods()` is fine). Golden tests build `plan` by calling `generate_plan(...)` from Phase 2 (a real chain from §6.5), then call `form(plan, pack.forms)`.
- **D-S12 — F11 is a loader cross-check.** F11 (`tempoRange.lo` yields `barBudget ≥ 4` at `maxLengthSec = 30`; for `/4` signatures `tempoRange.lo ≥ 8 × numerator`) needs the manifest's `tempoRange` + `timeSignatures[0]`; run it in the loader's forms-loading branch (only when `forms.yaml` exists), not in a pure model validator. `maxLengthTicks(30 s) = floor(30 × tempoRange.lo × 8)`.

---

## 3. Task list (ordered; models per PROMPT §"Subagent model rules")

| # | Task | Model | Files (scope) | DoD |
| --- | --- | --- | --- | --- |
| T1 | `SongForm` extension fields | sonnet | `schema/ir.py`, `schema/__init__.py`, `tests/test_schema.py` | enables §11.3 |
| T2 | `forms.yaml` schema + F1–F13 loader + reference files + rejection fixtures | sonnet | `packs/models.py`, `packs/loader.py`, `packs/__init__.py`, `styles/pop_rock/forms.yaml`, `styles/jazz/forms.yaml`, `tests/test_forms_pack.py` | §11.1 |
| T3 | Energy model + data + energy-column test | sonnet | `src/trackgen/form/__init__.py`, `form/energy.py`, `form/energy.yaml`, `tests/test_form_energy.py` | §11.2 |
| T4 | Form generator stage + goldens/determinism/property/ladder tests | **opus** | `src/trackgen/form/stage.py`, `form/__init__.py` (append export), `tests/test_form.py` | §11.3–§11.7 |
| T5 | §10 doc-amendment consistency check | orchestrator (or sonnet) | `plans/PHASE_1.md` (verify/patch), `plans/PHASE_2.md` (verify), `plans/ROADMAP.md` (verify) | §11.8 |

**Parallelism:** **T1 ∥ T2 ∥ T3** run in parallel — fully disjoint file sets (`schema/*` vs `packs/*`+`styles/*` vs `form/energy.*`). **T4 depends on all three** and is serialized after them (it integrates the schema, the loaded `forms`, and the energy model; it also appends to `form/__init__.py` which T3 created — no conflict since T4 runs after T3). T5 runs during whole-session review.

Per PROMPT §2, each task: implement → run 4 gates → **opus** review of the task diff → bounded fix loop (max 2 cycles) → commit at the verified gate → update PROGRESS.md immediately.

---

## 4. Task details

### T1 — `SongForm` extension fields (sonnet)
**Read:** PHASE_3 §4 (all: §4.1 per-section fields, §4.2 document field, §4.4 worked fragment), current `schema/ir.py` (`IRModel`, `FormSection`, `SongForm`), `schema/__init__.py`.
**Do:** Extend the two IR models (frozen, snake_case, no alias). Add two new `IRModel` submodels:
- `SectionPhrase`: `label: str`, `bars: int` (`ge=1`).
- `SectionEnding`: `tag_bars: Literal[0, 4, 8]`, `close: Literal["ritard", "cold", "fade"]`.

Add to `FormSection` (after the pinned core `{id, type, index, start_bar, length_bars, energy}`):
- `total_of_type: int` (`ge=1`)
- `phrases: list[SectionPhrase]`
- `harmony_tag: str`
- `variant: str | None = None`
- `ending: SectionEnding | None = None`

Add to `SongForm`: `template_id: str`.

Export `SectionPhrase`, `SectionEnding` from `schema/__init__.py` (`__all__` + import). Update any existing `FormSection`/`SongForm` construction site (search `tests/test_schema.py` and elsewhere) to supply the new required fields with valid values. Add a test constructing a full `FormSection` + `SongForm` (mirroring the §4.4 fragment) asserting field access, and that `Σ phrases[].bars == length_bars` is *not* auto-enforced by the model (it is a stage/property-test invariant, not a schema constraint — do not add a validator that would reject partial test fixtures) — but DO assert `tag_bars=6` and `close="wrong"` raise `ValidationError`, and `total_of_type=0` raises.
**Verify:** 4 gates green; new schema test passes; existing `tests/test_schema.py` updated and green.

### T2 — `forms.yaml` schema + F1–F13 loader + reference files (sonnet)
**Read:** PHASE_3 §5 in full (§5.1 schema + F1–F13 Rules, §5.2 selection semantics, §5.3 pop_rock content, §5.4 jazz content), §3.1 (the 11-type vocabulary), current `packs/models.py` (`PackModel`, `InterpreterConfig` as the precedent) + `packs/loader.py` + `tests/test_interpreter_pack.py` (the rejection-test pattern).
**Do:**
- `packs/models.py`: add frozen `PackModel` subclasses for `forms.yaml`. Suggested shape (final names your call, but keep them clear): `SectionDef` (`bars: list[tuple[int,int]]` weighted options, `phrases: dict[int, list[str]]`, `harmony_tag: dict[int, str]`, OR `inherit: str`); `TemplateSlot` / `RepeatBlock` (a spine element is a slot or a repeat block — model the union); `FormTemplate` (`id`, `weight`, optional `eligibility.arousal: tuple[float,float]`, `spine`, `ending: SectionEnding`-shaped `{tag_bars, close}`, `degrade: list`, `fallback: {section, bars}`); `FormsConfig` (`energy_range: tuple[float,float]`, `sections: dict[str, SectionDef]`, `templates: list[FormTemplate]`). Reuse the §3.1 type vocabulary as a single source of truth — define `SECTION_TYPES` once (in `form/` or a shared module) and import it (do not duplicate the 11-word list). Add `forms: FormsConfig | None = None` to `StylePack`.
- Enforce **F1–F13** (§5.1). Pure-structural rules (types in vocabulary; bars multiple of 4 ≥ 4; weights ≥ 1; `inherit` single-level + no sibling fields; phrases entry per bar option with `len(labels)` dividing `n` at integer quotient ≥ 4; harmonyTag entry per option; template ids unique; ≤ 1 repeat block; `count.min ≥ 1`, `count.max ≥ min` or null; optional weights ints ≥ 1; slot `energy ∈ [0,1]`; `variant` non-empty; `ending.tag_bars ∈ {0,4,8}` and `close` enum and `tag_bars ≤` smallest bar option of every form-ending type; degrade ops reference spine types; `fallback` type in template + bars multiple of 4 ≥ 4; `energyRange` `0 ≤ lo ≤ hi ≤ 1`; every template `fallback` present F12; ≥ 1 template with no arousal gate F13; F5 inherit-ordering) go in model validators. **F11** (manifest cross-check) and **F5** if it needs the whole spine go in the loader / an after-validator with access to the needed context — see D-S12 for F11. Emit clear messages; wrap into `PackLoadError` in the loader (like the manifest path).
- `packs/loader.py`: after manifest + banks + interpreter, if `forms.yaml` exists, parse+validate into `StylePack.forms` (per D-S1; absent → `None`); run F11 there using the manifest.
- Reference content per **D-S4**: `styles/pop_rock/forms.yaml` = §5.3 verbatim; `styles/jazz/forms.yaml` = §5.4 verbatim.
- `tests/test_forms_pack.py`: `pop_rock` + `jazz` load with a populated `.forms`; **one rejection test per F-rule class** (F1 bad type / non-multiple-of-4 bars; F2 inherit target missing / inherit-with-sibling-fields / two-level inherit; F3 missing phrase entry / labels-don't-divide / quotient < 4; F4 duplicate ids / two repeat blocks / bad count; F5 inherit before target; F6 bad optional weights; F7 energy out of range / empty variant; F8 bad tag_bars / tag_bars > smallest ending option; F9 degrade type not in spine / bad fallback bars; F10 bad energyRange; F11 tempoRange.lo too low for the 30 s floor; F12 missing fallback; F13 all templates gated). Assert `_stub` still loads with `forms is None`.
**Constraints:** style packs are data — no per-pack logic in code; the vocabulary/ladder/weights all come from YAML. Preserve list order (authored order is load-bearing for draws).
**Verify:** 4 gates green; existing `tests/test_packs.py` + `tests/test_interpreter_pack.py` still green (unchanged behavior for `_stub` and interpreter loading).

### T3 — Energy model + data + energy-column test (sonnet)
**Read:** PHASE_3 §6 in full (§6.1 base table, §6.2 positional rules R1–R4, §6.3 arousal modulation, §6.4 pack envelope), §7.4 (both energy columns), `interpreter/moods.py` (the `load_moods()` + `clamp01` + `round(x,3)` precedent to mirror).
**Do:**
- `src/trackgen/form/energy.yaml`: the §6.1 base table — the 11 types with their base values (`intro 0.30, verse 0.45, prechorus 0.60, chorus 0.75, postchorus 0.65, bridge 0.40, head 0.50, solo 0.60, main 0.50, breakdown 0.25, outro 0.35`). Engine data.
- `src/trackgen/form/__init__.py`, `form/energy.py`: a frozen `EnergyTable` model (`base: dict[str, float]`, `extra="forbid"`, covers all 11 types) + `load_energy_table()` (module-relative path, like `load_moods`). A pure function `section_energy(section_type, index, total_of_type, arousal, energy_range, override=None, table=...) -> float` implementing §6.2 R1–R4 → §6.3 → §6.4 **in that order**:
  - R1 escalation (`verse/prechorus/chorus/postchorus/main`): `e += 0.05 × min(index-1, 2)`.
  - R2 solo arch (**replaces** base): `e = 0.60 + 0.30 × index / total_of_type`. `head` has no rule.
  - R3 final-chorus peak (`chorus`, `index == total and total ≥ 2`): `e += 0.15`.
  - R4 override: a slot's authored `energy` **replaces** base+R1–R3 (still modulated + enveloped below).
  - §6.3: `e = clamp01(e + 0.10 × arousal)`.
  - §6.4: `return round(lo + e × (hi - lo), 3)`.
  Reuse `clamp01` from `interpreter.moods` (or define locally — do not import `random`/`time`).
- `tests/test_form_energy.py`: assert `section_energy` reproduces **all 13 sections' energy columns** across both §7.4 examples exactly (ex.1: arousal `+0.40`, envelope `[0,1]`; ex.2: arousal `-0.45`, envelope `[0.10,0.90]`). Mark the numbers normative. Assert the energy table loads and covers all 11 types.
**Constraints:** pure function; only the ordered engine data; no wall-clock/RNG; 3-decimal half-even output.
**Verify:** 4 gates green; energy-column test passes with the doc's exact numbers (orchestrator has confirmed these reproduce).

### T4 — Form generator stage (opus)
**Read:** PHASE_3 §7 in full (§7.1 normative algorithm, §7.2 RNG discipline + seed vectors, §7.3 ladder & fallback, §7.4 both worked examples), §5.2 (selection/eligibility/`minBars`), §3.3 (labels), §4 (the fields to emit); T1's `SongForm`/`SectionPhrase`/`SectionEnding`, T2's `FormsConfig` + `resolve_pack`, T3's `section_energy`; `seeds.py` (`stream_rng`, `weighted_choice`); `interpreter/stage.py::generate_plan` (to build the golden input plans). Re-read D-S2, D-S7, D-S8, D-S10, D-S11 above — they pin the exact draw ordering, feasibility rule, ticks-per-bar, labels, and signature.
**Do:**
- `src/trackgen/form/stage.py`: `form(plan: GenerationPlan, forms: FormsConfig) -> SongForm` implementing §7.1 step-for-step:
  1. `ticks_per_bar` / `bar_budget` per D-S8.
  2. eligibility (§5.2: arousal gate contains `plan.mood_vector.arousal`; `minBars ≤ bar_budget`, `minBars` = all optionals excluded, every type smallest, repeat at `count.min`); `weighted_choice` over eligible in authored order (draw skipped iff exactly one); eligible empty → fallback (step 6).
  3. slot resolution walking the spine in order (repeat-block inner slots resolved once at the block's position): optional inclusion draws + per-type bar-count resolution with the feasibility filter (D-S7); inherit-target types share one resolution (D9).
  4. repeat count = `(bar_budget − fixedBars) // blockBars` clamped `[count.min, count.max]` (max null ⇒ unbounded) — arithmetic, no draw.
  5. degradation ladder while `total > bar_budget` (authored order, recompute count/total each op).
  6. fallback form when still over budget or nothing eligible: one `fallback.section` of `min(fallback.bars, 4 × (bar_budget // 4))` bars, energy per §6, template `ending` attached.
  7. assemble: expand repeat `count` times; `index` per type in appearance order; `total_of_type`; ids `"{type}-{index}"`; labels per §3.3 (D-S10); `phrases`/`harmony_tag` from the resolved bar option; `ending` on the **last** section only; energies via `section_energy` (passing the slot `energy` override when present); `start_bar` cumulative from 0; `total_bars = Σ length_bars`; `template_id`.
  Draws come **only** from `weighted_choice` on `stream_rng(plan.seed.master, plan.seed.overrides, "form")`, only when ≥ 2 feasible, in the D-S2 order.
- `tests/test_form.py`:
  - **§7.4 golden Example 1** — build `plan = generate_plan({"styleFamily": "pop_rock", "seed": "1ps9wxb"})`, `form(plan, resolve_pack("pop_rock").forms)`; assert the SongForm **field-for-field** against §7.4's table (7 sections: ids, types, index/totalOfType, startBar/lengthBars, phrases, harmonyTags, energies, labels), `total_bars == 76`, `template_id == "verse_chorus_bridge"`, `ending == {tag_bars: 0, close: "cold"}` on **chorus-3** only.
  - **§7.4 golden Example 2** — `generate_plan({"styleFamily": "jazz", "mood": "melancholic", "maxLengthSec": 240, "seed": "1ps9wxb"})`; assert the 6 sections field-for-field, `total_bars == 64`, `template_id == "head_solos_head"`, `ending == {tag_bars: 4, close: "ritard"}` on **outro-1**.
  - **Seed vector §7.2** — `derive(3735928559, "form") == 7567330889165579844`; a fresh `random.Random` on it yields `getrandbits(32)[:5]` and `randrange(100)[:5]` as pinned in §0. (May live in `test_seeds.py` instead — your call; assert it somewhere.)
  - **Determinism §11.5** — same plan → identical SongForm (run twice, assert equal); a counting-RNG shim (wrap `randrange`/`getrandbits`) asserting **exactly 8 draws** for ex.1, **1 draw** for ex.2, and **0 draws** on the fallback path; a budget-shift test proving draws happen only when ≥ 2 feasible (shrink the budget so a bar option becomes the single feasible one → its draw disappears).
  - **Property tests §11.6** — every registered pack × every supported mood × `maxLengthSec ∈ {30,45,60,…,600}` × 25 seeds: sections contiguous from bar 0; every `length_bars` a multiple of 4 and ≥ 4; `total_bars × ticks_per_bar ≤ max_length_ticks`; energies ∈ [0,1] at 3 decimals; `Σ phrases[].bars == length_bars`; `index`/`total_of_type` consistent; `ending` non-null on exactly the final section; labels per §3.3.
  - **Ladder & fallback §11.7** — a fixture per degrade op class (drop/shrink/dropFromRepeat) via crafted small budgets; 30 s at each pack's `tempoRange.lo` → valid ≥ 4-bar form; a tiny budget (e.g. one just above 4 bars) hits the fallback and validates.
**Constraints:** append-only draw order; ordered candidate lists only (no dict/set iteration for candidate ordering — iterate authored YAML order); arithmetic fitting (ladder/count never drawn); 3-decimal half-even energies; hard ceiling always honored. **If any §7.4 printed value does not reproduce from a faithful implementation, escalate to the orchestrator — do NOT tune code to the number** (golden-value arbitration). The orchestrator has pre-verified all of them, so a mismatch means an implementation bug.
**Verify:** 4 gates green; both worked examples field-for-field; seed vector, determinism (draw counts 8/1/0), property, and ladder/fallback tests pass.

### T5 — §10 doc-amendment consistency (orchestrator or sonnet)
**Read:** PHASE_3 §10 (the 6 additive amendments), `plans/PHASE_1.md` (§3.4 vocabulary note, §4.2 extension-points line, §7 Q4), `plans/PHASE_2.md` (§9 Q4), `plans/ROADMAP.md` (§2 decisions log, §4 Phase 3 bullet).
**Do:** Verify each §10 amendment is reflected in the target doc; apply any missing edit (additive only, docs-only, no behavior change). Known state to confirm (from git history these may already be present — the ROADMAP §2 form-model row and §4 outro-before-bridge sketch appear to be in place; verify): PHASE_1 §3.4 references the full 11-type vocabulary in PHASE_3 §3; PHASE_1 §4.2 extension-points line is annotated pinned-by-PHASE_3 §4; PHASE_1 §7 Q4 marks `forms.yaml` resolved (progressions/timbres remain with Phases 4/7); PHASE_2 §9 Q4 marks the no-energy-knob resolution; ROADMAP §2 has the form-model row and §4 the degradation-order update. Patch any gap; note findings in the commit message.
**Verify:** grep-level consistency; no code change.

---

## 5. Whole-session review (PROMPT §3)

After T1–T5: dispatch fresh **opus** review agents (parallel, disjoint lenses) over the whole session's implementation:
1. Correctness/logic — the §7.1 algorithm: feasibility/`minimalTotal` recomputation, inherit-shared resolution, repeat-count clamping, ladder ordering, fallback, label specials, energy order-of-operations.
2. Contract compliance vs PHASE_3 §3/§4/§5/§6/§7 and the `SongForm` pinned core + extension fields; §3.2 semantics table left intact for downstream.
3. Test quality/coverage vs DoD §11.1–§11.8 (goldens real and field-for-field, draw-count shim genuine, property invariants complete, one rejection fixture per F-rule class).
4. Code quality/simplification + invariant compliance (§12: single `form` stream, integer weights, ordered lists, arithmetic fitting, no wall-clock, style-as-data).

Each finding → validation agent → confirmed findings get a fix agent + gate re-run (max 2 cycles). Then walk PHASE_3 §11 DoD items 1–8 one by one with evidence (test names, fixture paths, command output). Finish gates-green; commit.

---

## 6. Definition-of-Done checklist (PHASE_3 §11 — fill with evidence at close-out)

- [ ] §11.1 `forms.yaml` parsing into frozen models; F1–F13 implemented; one rejection fixture per rule class; both reference files load clean.
- [ ] §11.2 `form/energy.yaml` §6.1 base table; test asserts §6.1–§6.4 reproduce both examples' energy columns exactly (13 sections).
- [ ] §11.3 Form stage implements §7.1; both §7.4 SongForms asserted field-for-field.
- [ ] §11.4 §7.2 form-stream RNG vectors asserted exactly.
- [ ] §11.5 Determinism: same plan → identical form; counting shim (8 / 1 / 0 draws); draws-only-when-≥2-feasible budget-shift test.
- [ ] §11.6 Property tests: pack × mood × length grid × 25 seeds → valid form (all listed invariants).
- [ ] §11.7 Ladder & fallback: fixture per degrade op class; 30 s @ `tempoRange.lo` valid ≥ 4-bar form; tiny-budget fallback validates.
- [ ] §11.8 §10 amendments applied and consistent.

## 7. Escalate to the orchestrator when
- A §7.4 printed value does not reproduce from a faithful implementation (golden-value arbitration — do NOT tune code to a number; the orchestrator pre-verified every one).
- Algorithm text is genuinely ambiguous beyond the D-S decisions above.
- A fix loop hits its 2-cycle bound, or scope grows past this plan.
