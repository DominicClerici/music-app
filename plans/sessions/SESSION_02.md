# Session 02 — Phase 2: Parameter & Mood Model

**Status:** awaiting user approval (step-1 gate).
**Phase:** 2 (`plans/PHASE_2.md`). Fresh phase, single session, not split into chunks.
**Consumes:** PHASE_1 contracts — `GenerationPlan` pinned core + its three Phase-2 extension slots (`schema/ir.py`), seed system (`seeds.py`, `interpreter` stream already registered), pack loader/models (`packs/`), `Role`/`Key`/`SwingSpec`/`TimeSignature` IR models.
**Produces:** the `params` schema + validation catalog, the mood model + data, the `interpreter.yaml` pack extension with `pop_rock`/`jazz` reference packs, and the Interpreter stage emitting a complete `GenerationPlan`.

This file is written for implementer subagents with **zero prior context**. Each task lists the exact files to read, the exact files to touch, the constraints, and the verification it must pass.

---

## 0. Orientation for every subagent

Read first, always: `plans/PHASE_2.md` in full, `plans/ROADMAP.md` §3 (invariants + golden-value arbitration), and this file's task. Then the specific PHASE-doc sections named in your task.

**Binding invariants (ROADMAP §3):** style packs are data not code; determinism — no wall-clock, no unseeded randomness outside `src/trackgen/seeds.py` (Ruff TID251 enforces the import layer; never work around it); hierarchical seeds; soloist owns above ~C5 (this phase emits no notes, but `registerBias` must never raise a ceiling — it's a scalar only).

**Golden-value arbitration (ROADMAP §3):** the PHASE_2 printed sample numbers are derived samples; the algorithm/data *text* is authoritative. **However — the orchestrator has already independently recomputed every load-bearing sample in this phase and they reproduce exactly:** the full §4.4 derived-defaults table (12 moods × 12 values, 0 mismatches), both §6.5 tempo draws (123 pop_rock, 69 jazz — stable across any pack `tempoRange` that is a superset of the mood window), the §6.5 budgets (`0.648/0.132`, `0.505/0.653`), `maxLengthTicks` (`177120`, `132480`), the swing ratio `0.722`, and the `interpreter` seed vector. **Pin these numbers as written; no amendment is expected.** If your faithful implementation nonetheless diverges, assume an implementation bug first; escalate to the orchestrator before touching any printed number.

**Gates (all four must be green; run and read output — never assume):**
```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

**Conventions established in Phase 1 (match them):**
- IR models (`schema/ir.py`) subclass `IRModel` (frozen; plain snake_case fields, **no** camelCase alias — IRs are never serialized into `TrackDocument`).
- Pack/API models that ARE part of the JSON contract subclass a base with `frozen=True, alias_generator=to_camel, populate_by_name=True, extra="forbid"` (see `packs/models.py:PackModel`). The public `params` schema uses camelCase JSON aliases exactly like this.
- Loaders read YAML via `yaml.safe_load`, wrap `OSError`/`YAMLError`/`ValidationError` into a domain error (`PackLoadError` pattern in `packs/loader.py`).
- Schema export is deterministic: `json.dumps(..., indent=2, sort_keys=True) + "\n"`, `by_alias=True` (see `schema/export.py`).
- Tests carry a docstring citing the PHASE section; golden numbers get a "normative — do not edit to match code" comment (see `tests/test_seeds.py`).

---

## 1. Session scope

**In scope (Phase 2 DoD §11 items 1–8):**
1. `params` pydantic model + full §3.1 validation catalog (stable codes, full-list reporting) + `docs/schema/params.schema.json`.
2. Mood model: `moods.yaml` (12 anchors + §4.3 overrides), frozen models, §4.2 formulas + §4.3 override application; exact §4.4 derived-defaults test.
3. Pack-loader extension: `interpreter.yaml` parsing + §5.1 validation rules; `pop_rock` + `jazz` reference packs; per-rule rejection tests.
4. Interpreter stage implementing §6 exactly; §6.5 worked-example golden tests + `interpreter` seed vector.
5. Determinism: same-params-same-seed identity; zero RNG draws when `tempoBpm` given (counting-RNG shim); user-tempo/user-key bypass tests.
6. Property tests: every registered pack × every supported mood × auto-everything → valid `GenerationPlan` honoring `tempoRange`/`modes`/expression ranges, `swing.ratio ∈ [0.5, 0.75]`.
7. One failing-params fixture per §3.1 code, asserting code + field.
8. PHASE_1/ROADMAP §10 amendments applied and consistent.

**Explicitly out of scope:** everything downstream of `GenerationPlan` (form, harmony content, patterns, humanization, patches); pack *content* beyond the two `interpreter.yaml` reference examples; real pattern banks for `pop_rock`/`jazz` (Phase 5/8 — empty banks only this session); per-section energy/mood; any client UI.

---

## 2. Pinned scoping decisions (resolved by the orchestrator — do not relitigate)

These resolve ambiguities the PHASE doc leaves to implementation. They are binding for this session.

- **D-S1 — `interpreter.yaml` is OPTIONAL in `load_pack`.** `load_pack` parses & validates `interpreter.yaml` into `StylePack.interpreter: InterpreterConfig | None` **when the file exists**; when absent, `interpreter` is `None` and the pack still loads (keeps the Phase-1 `_stub` pack and its tests working untouched). `interpret()` requires a non-None `interpreter` and raises a clear error if absent.
- **D-S2 — Reference packs are real pack directories.** `styles/pop_rock/` and `styles/jazz/` each get: `manifest.yaml`, `interpreter.yaml`, and four `patterns/{drums,bass,comping,pads}.yaml` files each containing `{patterns: []}` (the Phase-1 loader requires these files to exist; real patterns land in Phase 5/8). Do **not** relax `load_pack`'s file-existence requirement (that would be a Phase-1 contract change / caveat).
- **D-S3 — Pack registry.** The set of registered `styleFamily` ids = pack directories under `styles/` **excluding `_stub`**. In Phase 2 only `pop_rock` and `jazz` are registered; `blues`/`chill_lofi`/`fusion_jazz` are not built yet and therefore correctly raise `STYLE_UNKNOWN`. Provide a small registry/resolver (`styles/<id>/`).
- **D-S4 — Reference `interpreter.yaml` content is the §5.1 examples verbatim.** The §6.5 goldens depend on it — especially `expressionRanges` (`pop_rock` density `[0.20,0.85]` / dissonance `[0.05,0.40]`; `jazz` density `[0.25,0.90]` / dissonance `[0.35,0.90]`), `tonics`, `supportedMoods`, `defaultMood`, `feel`, `flavors`, `ensembles`.
- **D-S5 — Reference `manifest.yaml`.** `version: 0.1.0` (the §6.5 `stylePack.version`), `timeSignatures: [[4, 4]]`, `id` = `pop_rock`/`jazz`, `formatVersion: 1`, plus `name`/`engine`. `tempoRange` must be a **superset** of the §6.5 mood windows (pop_rock ⊇ `[106,130]`, jazz ⊇ `[61,75]`); pick musically sensible style ranges (suggested `pop_rock: [70, 180]`, `jazz: [60, 220]`) — any superset reproduces the draws, verified by the orchestrator.
- **D-S6 — Params validation is two layers.** (a) `validate_params(raw: dict, pack: StylePack | None) -> list[ParamError]` producing the full §3.1 catalog (each `{code, field, message}`, **all** errors not first-failure, stable codes); (b) a frozen pydantic `Params` model with camelCase aliases for typing + schema export. When `styleFamily` resolves to no pack (`STYLE_UNKNOWN`), still run pack-independent checks (`SEED_CONFLICT`, `SEED_INVALID`, `LENGTH_OUT_OF_RANGE`, `MOOD_UNKNOWN`, `TITLE_TOO_LONG`, `ROLE_UNKNOWN`, `STREAM_UNKNOWN`) and skip pack-relative ones (`MOOD_UNSUPPORTED`, `TEMPO_OUT_OF_RANGE`, `MODE_UNSUPPORTED`, `FLAVOR_UNKNOWN`, `PRESET_UNKNOWN`).
- **D-S7 — GenerationPlan new fields are REQUIRED.** §7 says they are now pinned; make `mood_vector`/`budgets`/`timbre_directives` required on `GenerationPlan` and update the three existing construction sites in `tests/test_schema.py` (lines ~195, ~210, ~430) to supply them with valid minimal values.
- **D-S8 — Rounding.** Every derived float → `round(x, 3)` (Python half-even); `tempoBpm` integer; `maxLengthTicks = floor(maxLengthSec × tempoBpm × 8)` as a single `int()`/`math.floor` at the end.
- **D-S9 — Package layout.** New engine code lives in a `src/trackgen/interpreter/` package: `params.py`, `moods.py` + `moods.yaml`, `stage.py` (the `interpret()` function), `__init__.py`. Keep `moods.yaml` beside `moods.py` and load it by path relative to the module.

---

## 3. Task list (ordered; models assigned per PROMPT §"Subagent model rules")

| # | Task | Model | Files (scope) | DoD |
| --- | --- | --- | --- | --- |
| T1 | GenerationPlan extension | sonnet | `schema/ir.py`, `schema/__init__.py`, `tests/test_schema.py` | §11.? (enables 4) |
| T2 | Mood model + data + derived-table test | sonnet | `interpreter/moods.py`, `interpreter/moods.yaml`, `interpreter/__init__.py`, `tests/test_moods.py` | §11.2 |
| T3 | Pack `interpreter.yaml` extension + reference packs | sonnet | `packs/models.py`, `packs/loader.py`, `packs/__init__.py`, `styles/pop_rock/**`, `styles/jazz/**`, `tests/test_interpreter_pack.py` | §11.3 |
| T4 | Params model + validation catalog + schema export | sonnet | `interpreter/params.py`, `interpreter/__init__.py`, `schema/export.py` (or new `interpreter/export.py`), `docs/schema/params.schema.json`, `tests/test_params.py` | §11.1, §11.7 |
| T5 | Interpreter stage (`interpret()`) + goldens/determinism/property tests | **opus** | `interpreter/stage.py`, `interpreter/__init__.py`, `tests/test_interpreter.py` | §11.4, §11.5, §11.6 |
| T6 | §10 doc-amendment consistency check | sonnet (or orchestrator) | `plans/PHASE_1.md` (verify/patch), `plans/ROADMAP.md` (verify) | §11.8 |

**Parallelism:** T1 first (foundational; T5 depends on it). After T1, **T2 ∥ T3** may run in parallel (fully disjoint file sets: `interpreter/moods.*` vs `packs/*` + `styles/*`). Serialize T4 after T3 (needs the `InterpreterConfig` shape for pack-relative checks) and note T4 shares `interpreter/__init__.py` with T2 — merge exports carefully / run T4 after T2 lands. T5 last (integrates all). T6 during whole-session review.

Per PROMPT §2, each task: implement → run 4 gates → opus review of the task diff → bounded fix loop (max 2 cycles) → commit at the verified gate → update PROGRESS.md immediately.

---

## 4. Task details

### T1 — GenerationPlan extension (sonnet)
**Read:** PHASE_2 §7 (all three sub-tables), current `schema/ir.py` (`IRModel`, `GenerationPlan`).
**Do:** Add three frozen `IRModel` subclasses and wire them as **required** fields on `GenerationPlan` (snake_case; no camel alias):
- `MoodVector`: `valence: float` (−1..1), `arousal: float` (−1..1).
- `Budgets`: `note_density`, `dissonance`, `dynamics_base`, `dynamics_range`, `articulation_legato`: `float` (0..1); `layers_max: int` (2..4); `harmonic_rhythm_base: float`; `register_bias: float` (−1..1).
- `TimbreDirectives`: `brightness`, `attack_hardness`, `space`: `float` (0..1).
Add fields `mood_vector: MoodVector`, `budgets: Budgets`, `timbre_directives: TimbreDirectives` to `GenerationPlan`. Export the three new models from `schema/__init__.py` (`__all__` + import). Update the three `GenerationPlan(...)` construction sites in `tests/test_schema.py` to supply valid values. Add a test constructing a full `GenerationPlan` with the new fields and asserting field access + that out-of-range values (e.g. `layers_max=5`, `brightness=1.2`) raise `ValidationError`.
**Verify:** 4 gates green; new `GenerationPlan` validation test passes.

### T2 — Mood model + data + derived-table test (sonnet)
**Read:** PHASE_2 §4 (all: §4.1 anchors, §4.2 formulas, §4.3 overrides, §4.4 table).
**Do:**
- `interpreter/moods.yaml`: the 12 anchors (`valence`/`arousal`) and per-mood `overrides` (§4.3 — only the 7 moods with overrides carry them; overridable keys are the 13 §4.2 derived names). Engine-owned data, loaded/validated like a pack (frozen models, `extra="forbid"`).
- `interpreter/moods.py`: frozen models (`MoodAnchor`/`MoodRow`/`MoodTable`), a `load_moods()` reading the YAML by module-relative path, a `formulas(v, a) -> dict` implementing §4.2 exactly (`clamp01`, `round(x, 3)` half-even, integer/piecewise rungs), and `apply_overrides(overrides, derived) -> dict` (§4.3 — override replaces the derived value **after formula, before pack expression-range mapping**, i.e. in normalized space; `tempoCenter` override is a raw BPM float, not rounded). Provide `derived_defaults(mood) -> dict` returning the post-override values.
- `tests/test_moods.py`: assert the **full §4.4 table exactly** — all 12 moods, `tempoCenter` to 1 decimal (pre-round) and the 11 other columns to 3 decimals; mark BOLD (overridden) cells; assert `layersMax` is `3` or `4` for all v1 anchors (rung 2 unreachable). Assert `moods.yaml` loads and that every anchor V,A ∈ [−1,1].
**Constraints:** formulas use only the ordered YAML data; no `random`/`time` import. The §4.4 numbers are normative (comment: do not edit to match code).
**Verify:** 4 gates green; derived-table test passes with the doc's exact numbers.

### T3 — Pack `interpreter.yaml` extension + reference packs (sonnet)
**Read:** PHASE_2 §5.1 (schema-by-example + the Rules bullet list), §2 (contracts consumed), current `packs/models.py` + `packs/loader.py` + `tests/test_packs.py`.
**Do:**
- `packs/models.py`: add frozen `PackModel` subclasses for `interpreter.yaml`: `InterpreterConfig` with `supported_moods: list[str]`, `default_mood: str`, `modes: list[str]`, `tonics: dict[str, list[str]]`, `feel: Literal["straight8","straight16","swing8","swing16"]`, `swing_ratio: float | None = None`, `feel_table: str | None = None`, `expression_ranges` (a submodel with `density: tuple[float,float]` and `dissonance: tuple[float,float]`), `flavors: dict[Role, list[str]]`, `ensembles: dict[str, dict[Role, str]]`. Add `interpreter: InterpreterConfig | None = None` to `StylePack`.
- Enforce the §5.1 **Rules** (in the model validators and/or loader): `supported_moods` non-empty ⊆ the 12-word vocabulary; `default_mood ∈ supported_moods`; `modes` non-empty ordered subset of the engine ladder `[major, mixolydian, dorian, minor, phrygian]`; every listed mode has a non-empty `tonics` entry; `expression_ranges` values ∈ [0,1] with `lo ≤ hi`; every `Role` present in `flavors` with ≥1 id; `ensembles.default` required and covers all four roles; every ensemble value is a declared flavor id for that role. Emit clear errors (wrap into `PackLoadError` like the manifest path). Import the 12-mood vocabulary + the mode ladder from a single source of truth (define constants in `interpreter/moods.py` or a small shared module and import — do not duplicate the list).
- `packs/loader.py`: after loading manifest + banks, if `interpreter.yaml` exists, parse+validate it into `StylePack.interpreter` (per **D-S1**; absent → `None`). Add a registry/resolver helper: `registered_styles() -> set[str]` (dirs under `styles/` minus `_stub`) and `resolve_pack(style_family) -> StylePack | None`.
- Reference packs per **D-S2/D-S4/D-S5**: `styles/pop_rock/` and `styles/jazz/` with `manifest.yaml`, `interpreter.yaml` (the §5.1 examples verbatim), and four empty `patterns/*.yaml`.
- `tests/test_interpreter_pack.py`: `pop_rock` + `jazz` load with a populated `.interpreter`; one **rejection test per §5.1 rule class** (empty supportedMoods; mood outside vocabulary; default not supported; mode not in ladder; mode with no tonics; expression range lo>hi or out of [0,1]; role missing from flavors; ensembles.default missing / not covering all roles; ensemble value not a declared flavor). Assert `_stub` still loads with `interpreter is None`.
**Verify:** 4 gates green; existing `tests/test_packs.py` still green (unchanged behavior for `_stub`).

### T4 — Params model + validation catalog + schema export (sonnet)
**Read:** PHASE_2 §3 (field table + example), §3.1 (error catalog — all 14 codes), §6 step 1, §2; T3's `InterpreterConfig` + registry.
**Do:**
- `interpreter/params.py`: frozen pydantic `Params` model (camelCase aliases, `populate_by_name=True`, `extra="forbid"`) mirroring §3 (`style_family` required; the rest optional with the §3 shapes — `key` a submodel `{tonic?: str, mode?: str}`, `role_flavors: dict[str,str]`, `seed_overrides: dict[str,str]`, etc.). Type-level constraints only where they don't collide with the coded catalog.
- A `ParamError` dataclass/model `{code: str, field: str, message: str}` and `validate_params(raw: dict, pack: StylePack | None) -> list[ParamError]` implementing all 14 §3.1 codes with the exact conditions and **full-list** reporting (per **D-S6** ordering rule for STYLE_UNKNOWN). Include the tonic parser (note `A`–`G`, optional `#`/`b` → pitch class) feeding `KEY_TONIC_INVALID`. Validate `seed` as base36 u64 via `trackgen.seeds.from_base36`; `SEED_CONFLICT` when both `seed` and `seedText`; `STREAM_UNKNOWN` against `trackgen.seeds.STREAMS`.
- Export `docs/schema/params.schema.json` deterministically (`by_alias=True`, sorted keys, indent 2, trailing newline — reuse `schema/export.py`'s pattern; add an `export_params_schema()` + a drift-guard test like the existing TrackDocument one).
- `tests/test_params.py`: **one failing fixture per §3.1 code**, each asserting the returned list contains an error with that `code` and the expected `field`; a valid maximal-call fixture (the §3 example) returning `[]`; a full-list test (a params blob with ≥2 independent errors returns both). Schema drift-guard test.
**Verify:** 4 gates green; committed `params.schema.json` matches a fresh export.

### T5 — Interpreter stage (opus)
**Read:** PHASE_2 §6 (all: resolution order §6, §6.1 RNG discipline, §6.2 tempo, §6.3 key ladder+bands, §6.4 swing table, §6.5 worked examples + seed vector), §7, §12; T1–T4 outputs; `seeds.py` (`stream_seed`, `derive`, `fresh_master`), `weighted_choice` (unused here — single `randrange`).
**Do:**
- `interpreter/stage.py`: `interpret(params: Params, pack: StylePack, master_seed: int, overrides: dict[str, int]) -> GenerationPlan` implementing the §6 resolution order exactly:
  1. (validation is the caller's job / already done — but `interpret` may assert `pack.interpreter is not None`).
  2. `mood = params.mood or pack.interpreter.default_mood`; 3. `(V,A) = moods.yaml[mood].anchor`; 4. `derived = formulas(V,A)`; 5. `apply_overrides`; 6. tempo per §6.2 — **the single seeded draw**, only when `params.tempoBpm` is absent, `rng = random.Random(stream_seed(master_seed, overrides, "interpreter"))`, integer `randrange` only; 7. `resolve_key` (§6.3 ladder + bands, deterministic, tonic from pack `tonics[mode][0]` unless given); 8. `resolve_swing` (§6.4 table w/ piecewise-linear interp, `ratio = r/(1+r)` rounded 3dp, evaluated at `tempoBpm` for swing8 / `2×tempoBpm` for swing16; pack `swingRatio` overrides); 9. `pack_scale` density+dissonance through `expressionRanges` (§4.2 formula), all other derived values global; 10. merge `ensembles.default → ensembles[preset] → roleFlavors`; 11. `maxLengthTicks = floor(maxLengthSec × tempoBpm × 8)`; 12. assemble `GenerationPlan` (`mood_vector` = raw anchor V,A; `budgets`/`timbre_directives` from the scaled/overridden values).
  - Provide a thin orchestrator entry too: `generate_plan(raw_params: dict, *, seed_master: int | None = None) -> GenerationPlan` that resolves the pack from `styleFamily`, runs `validate_params` (raising a structured `ParamsInvalid` carrying the catalog on any error), derives the master seed (`params.seed`/`seedText` → `seeds`; else `fresh_master()`), and calls `interpret`. `fresh_master()` is the only entropy entry (API boundary) — never inside `interpret`.
- `tests/test_interpreter.py`:
  - **§6.5 golden Example 1** (`{styleFamily:"pop_rock", seed:"1ps9wxb"}`) and **Example 2** (`{styleFamily:"jazz", mood:"melancholic", maxLengthSec:240, seed:"1ps9wxb"}`): assert the produced `GenerationPlan` **field-for-field** against the doc (key `{4,"major"}`/`{2,"minor"}`, tempo `123`/`69`, swing `null`/`{0.722,"8"}`, `maxLengthTicks` `177120`/`132480`, budgets `0.648/0.132`/`0.505/0.653`, moodVector, timbreDirectives, roleFlavors). Master seed `3735928559`.
  - **Seed vector** (§6.5): `derive(3735928559,"interpreter") == 1597995742192405040` (base36 `c52i7pgxyq7k`) — already in `test_seeds.py`; re-assert the first-five `randrange(100)` == `[70,19,35,93,77]` context if useful.
  - **Determinism §11.5:** same params+seed → identical plan (run twice, assert equal); with `tempoBpm` given, **zero** RNG draws via a counting-`random.Random` shim (wrap `randrange`/`getrandbits`); user-key and user-tempo paths bypass ladder/draw.
  - **Property tests §11.6 (Hypothesis or parametrized matrix):** for every registered pack × every `supportedMood`, auto-everything → plan validates, `tempoBpm ∈ pack.tempoRange`, `key.mode ∈ pack.modes`, budgets within `[0,1]`, and `swing.ratio ∈ [0.5,0.75]` when non-null.
**Constraints:** exactly one `randrange` draw on the auto path, zero otherwise (PHASE_2 §6.1 / D4); ordered YAML lists only (no dict/set iteration for candidate ordering); 3-decimal half-even rounding; integer tempo/ticks.
**Verify:** 4 gates green; both worked examples field-for-field; determinism + property tests pass.

### T6 — §10 doc-amendment consistency (sonnet or orchestrator)
**Read:** PHASE_2 §10 (the 5 additive amendments), `plans/PHASE_1.md` (§5.2 registry, §5.6 golden vectors, §6 pack layout, §7 Q1), `plans/ROADMAP.md` §2.
**Do:** Verify each §10 amendment is reflected in the target doc; apply any missing edit (additive only). Known state to confirm: `seeds.py:STREAMS` + `test_seeds.py` already carry `interpreter` (§5.2/§5.6 ✓); ROADMAP §2 already has the style×mood row (✓). Confirm PHASE_1 §6 pack layout mentions `interpreter.yaml` and PHASE_1 §7 Q1 is marked resolved; patch if not. No behavior change, docs only.
**Verify:** grep-level consistency; note findings in the commit message.

---

## 5. Whole-session review (PROMPT §3)

After T1–T6: dispatch fresh **opus** review agents (parallel, disjoint lenses) over the whole session's implementation:
1. Correctness/logic — resolution order, tempo/key/swing edge cases, rounding, single-draw discipline.
2. Contract compliance vs PHASE_2 §3/§4/§5/§6/§7 and the GenerationPlan pinned core.
3. Test quality/coverage vs DoD §11.1–§11.8 (are goldens real, property tests meaningful, one fixture per error code present).
4. Code quality/simplification + invariant compliance (§12: single stream, integer randomness, ordered lists, no wall-clock).

Each finding → validation agent → confirmed findings get a fix agent + gate re-run (max 2 cycles). Then walk PHASE_2 §11 DoD items 1–8 one by one with evidence (test names, fixture paths, command output). Finish gates-green; commit.

---

## 6. Definition-of-Done checklist (PHASE_2 §11 — fill with evidence at close-out)

- [ ] §11.1 Params model + full §3.1 catalog (stable codes, full-list) + `params.schema.json` committed.
- [ ] §11.2 `moods.yaml` (12 anchors + overrides) in frozen models; §4.4 table asserted exactly.
- [ ] §11.3 `interpreter.yaml` parsing + §5.1 rules; `pop_rock`/`jazz` reference packs; per-rule rejection tests.
- [ ] §11.4 Interpreter §6 exact; §6.5 both examples field-for-field + seed vector.
- [ ] §11.5 Determinism: same-params→same-plan; `tempoBpm` given → zero draws (counting shim); bypass paths.
- [ ] §11.6 Property tests: pack × supported mood × auto → valid, honors ranges/modes, swing ∈ [0.5,0.75].
- [ ] §11.7 One failing-params fixture per §3.1 code (code + field asserted).
- [ ] §11.8 §10 amendments applied and consistent.

## 7. Escalate to the orchestrator when
- A §6.5 printed number does not reproduce from a faithful implementation (golden-value arbitration — do NOT tune code to a number).
- Algorithm text is genuinely ambiguous beyond the D-S decisions above.
- A fix loop hits its 2-cycle bound, or scope grows past this plan.
