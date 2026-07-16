# Session 04 — Phase 4 (Harmony engine), Chunk 1 of 2

**Phase:** 4 (Harmony engine). **Chunk:** 1 of 2 — *theory library + harmony data foundations*.
**Design source (binding):** `plans/PHASE_4.md`. **Upstream contracts:** `plans/PHASE_1.md` §4.3 (HarmonicPlan/ChordSpec core), `plans/PHASE_3.md` §4 (SongForm), `plans/PHASE_2.md` §7 (budgets).
**Status:** awaiting approval — no task dispatched.

This chunk builds every piece the Harmony *stage* depends on, each fully unit-tested standalone: the shared `theory/` library, the dissonance-dressing ladder data + logic, and the `progressions.yaml` schema/loader with its reference packs. **The stage itself, the `HarmonicPlan` schema extension (§7), the §10 golden chains, determinism/property/deceptive tests, and the §13 amendment check are Chunk 2 (SESSION_05).**

## Why the phase is split

Phase 4 is materially larger than Phases 1–3: the theory library alone (token grammar + spelling + scale-hint resolution, voicing candidate classes, integer-cost Viterbi voice-leading, music21 cross-validation) is a full task set, and the stage adds three boundary transforms plus two event-for-event golden chains (76 + 64 events) with determinism/property coverage. Splitting at the **"pieces vs. assembly"** seam keeps each session's review tractable and matches PROMPT.md §1's sizing rule. The seam is clean: Chunk 1 produces pure, independently-tested modules; Chunk 2 wires them into `harmony(plan, form, progressions, rng)` and proves the goldens.

## Scope

**In scope (this chunk):**
- `src/trackgen/theory/` — quality→interval tables (§8.1), scale sets (§8.2), `resolve_token` (§3.1 grammar → ChordSpec incl. §3.2 function, §3.3 spelling, §7.4 scale-hint), `chord_intervals`/`chord_tones`/`guide_tones`/`scale_pcs`, a §6.4 extension-legality helper, and the voicing layer (§8.4 candidates incl. `fifths`, §8.5 `vl_distance`, §8.6 `optimal_voicing_path`). DoD 2, 8.
- `src/trackgen/harmony/dressing.yaml` + `src/trackgen/harmony/dressing.py` — the 7-tier ladder (§6.1), function offsets + clamp (§6.2), the per-class weighted option tables (§6.3), the §6.4 hard filter. DoD 3.
- `progressions.yaml` schema in `src/trackgen/packs/models.py`, loader wiring in `src/trackgen/packs/loader.py`, and the two reference `styles/{pop_rock,jazz}/progressions.yaml` files (§9.1/§9.2 verbatim). Validation P1–P10 (P11 deferred), §4.2 density, cross-file P1/P4 against the reference `forms.yaml`. DoD 1.

**Explicitly out of scope (→ Chunk 2 / SESSION_05):**
- The `HarmonicPlan` §7 schema extension in `schema/ir.py` (`keys`, per-event `scale`/`function`/`tags`, `poolSelections`).
- `harmony/stage.py` — the §5.1 generator, the three boundary transforms, RNG discipline, timeline assembly.
- The §10 worked-example golden fixtures, §5.6 seed goldens *in the stage's draw sequence*, the 8/30-draw determinism shim, the DoD-7 property matrix, the DoD-9 deceptive fixture, the §13 amendment-consistency check.
- **P11 and the parenthesized extension-group grammar** (`(#11)`, `(#9)`): Phase 8 scope per PHASE_4 §14 DoD-1 scope note. `resolve_token` **rejects** an extension group as unrecognized syntax; neither reference pack uses one.

## Golden-value discipline (binding — ROADMAP §3)

The PHASE_4 printed numbers (§5.6 RNG vectors, §8 table values, §9 pack content, §10 event tables) are **normative**: never edit an expected value to match code output. A divergence is an implementation bug unless the algorithm text is genuinely ambiguous, which escalates to the user (never tune code to a printed number). The orchestrator has pre-verified §5.6's seed vectors reproduce exactly (`derive(3735928559,"harmony")==226146634901021418`; getrandbits/randrange vectors match). The §10 event chains are proven in Chunk 2.

## Invariants (binding — ROADMAP §3)

- **Determinism (inv. 5):** no wall-clock, no unseeded randomness. This chunk emits **no draws** — dressing option tables and voicing DP are pure functions; the *draws* over them happen in the Chunk-2 stage. TID251 bans `random`/`secrets`/`uuid`/`os.urandom`/`datetime.now` outside `seeds.py`; the theory/dressing modules must not import them at all. Integer-cost DP only (§8.6, D16) — no float comparisons in `vl_distance`/`optimal_voicing_path`.
- **Packs are data (inv. 1):** `progressions.yaml` and `dressing.yaml` are data; the engine reads them, never hardcodes pool/table content.
- **Soloist owns above ~C5 (inv. 4):** voicing candidates hard-prune at the lane ceiling; a `high ≤ 71` lane emits nothing above MIDI 71 (§8.4).
- **Rhythm separate from pitch (inv. 2):** theory emits chord specs and voicing *candidates*, never committed notes.

## Conventions to mirror (existing code)

- IR models: frozen pydantic, plain snake_case, in `schema/ir.py` (`ChordSpec` already pinned there — do **not** modify it this chunk).
- Pack models: `packs/models.py` `PackModel` base (frozen, `alias_generator=to_camel`, `populate_by_name=True`, `extra="forbid"`). New `progressions.yaml` models subclass `PackModel`, mirroring `FormsConfig`/`InterpreterConfig`. Cross-file checks that need two files (like `_check_f11`) run in the **loader**, not a model validator.
- Loader: `load_pack` reads optional files by `path.exists()` (see `interpreter.yaml`/`forms.yaml`); add `progressions.yaml` the same way. Wrap `ValidationError`/`ValueError` in `PackLoadError`.
- Engine data files (`moods.yaml`, `form/energy.yaml`) load via `yaml.safe_load` from a path next to their module; `dressing.yaml` mirrors this.
- Tests: pytest; golden numbers transcribed from the doc as literals; rejection tests build a minimal invalid config inline (see `tests/test_forms_pack.py`). music21 is import-guarded/pinned; cross-validation lives in the theory test.
- Gates (all four, green before each commit): `uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy`.

## Task list

Ordering: **T1 first** (foundational). **T2, T3, T4 then run in parallel** — their file sets are disjoint (`theory/voicing.py` · `harmony/*` · `packs/*`+`styles/*`) and each imports only T1's already-committed surface. All four tasks are **opus** (theory algorithms, spelling arithmetic, voicing DP, dressing tables, and cross-file validation all involve real judgment — none clears the "truly trivial" bar).

---

### T1 — Theory resolution core (`theory/chords.py`) · model: opus

**Implements:** PHASE_4 §3 (token grammar, function, spelling), §7.4 (chord-scale hints), §8.1 (interval stacks), §8.2 (scale sets), §8.3 signatures (`resolve_token`, `chord_intervals`, `chord_tones`, `guide_tones`, `scale_pcs`), §6.4 (extension-legality helper).

**Files:** `src/trackgen/theory/chords.py` (new), `src/trackgen/theory/__init__.py` (re-export the surface), `tests/test_theory_chords.py` (new).

**Build:**
- Pinned data tables: quality→semitone stack (§8.1, all 15 qualities + extension offsets 9→14 … b13→20); scale sets (§8.2, all 14 named scales). Assert them in tests exactly.
- Token parser + `resolve_token(token, key) -> ChordSpec`: parse `degree quality? bass?` per §3.1 (case = triad third; degrees major-scale-relative `I..VII→0,2,4,5,7,9,11`, `b`/`#` ±1; suffix→quality per the §3.1 table incl. aliases `h7`/`dim`/`dim7`/`aug`). **Reject** extension groups `(…)` as unrecognized (Phase 8 scope). `~` is a bar-level hold, not a token `resolve_token` handles — reject/never receive it. Emit `ChordSpec{root_pc, quality, extensions, bass_pc, symbol, roman}`; `roman` echoes the authored token verbatim.
- Function label from §3.2 table (by degree, quality-independent; unlisted alteration → `O`).
- Spelling §3.3: fixed 12×2 tonic-name tables (major-class / minor-class), root letter by degree-letter A–G arithmetic, accidental from pc delta, quality string, extension tidy-display rules, slash-bass suffix. This produces `ChordSpec.symbol`.
- Chord-scale hint §7.4 as a top-to-bottom first-match table returning `{root_pc, name}` (used by Chunk 2's event `scale` field and Phase 5). Note the alteration rows outrank degree rows outrank defaults.
- `chord_intervals(spec)`, `chord_tones(spec)`, `guide_tones(spec)` (§8.3), `scale_pcs(root_pc, name)` (§8.2).
- `legal_extensions(quality) -> frozenset[str]` (or `extensions_legal(quality, exts) -> bool`) per §6.4 — shared by T3 and Chunk-2 property tests.

**Verification (DoD 2 partial, DoD 8):** golden tests covering every suffix, alterations (`bVI`, `#iv°7`), case errors (validation raises), slash bass; §8.1/§8.2 tables asserted; spelling goldens across all 12 tonics × both table classes incl. the "B♭7 in D minor, never A♯7" class; `chord_tones`/`guide_tones`; scale-hint precedence cases. **music21 cross-validation (DoD 8):** compare `chord_tones` against `music21.harmony.ChordSymbol` for the resolvable subset, with documented exclusions for the known music21 defects (§8.7 / D12), music21 version pinned (already in `uv.lock`).

---

### T2 — Voicing & voice-leading (`theory/voicing.py`) · model: opus · depends on T1

**Implements:** PHASE_4 §8.4 (candidate classes incl. `fifths`), §8.5 (`vl_distance`), §8.6 (`optimal_voicing_path` Viterbi with pinned default weights `move 4, top 4, common 3, drift 1`).

**Files:** `src/trackgen/theory/voicing.py` (new), extend `theory/__init__.py` re-exports, `tests/test_theory_voicing.py` (new).

**Build:**
- `voicing_candidates(spec, cls, lane) -> [[midi]]`: the nine classes in §8.4 (`shell2, shell3, rootless_a, rootless_b, drop2, triad_close, triad_open, quartal, fifths`) by their pinned formulas; enumerate every octave placement fitting the lane (`bottom ≥ lane.low`, `top ≤ lane.high`); deterministic generation order = class formula order then ascending octave (the tie-break order §8.6 relies on).
- `vl_distance(a, b, weights) -> int`: §8.5 exactly — L1 taxicab (`w.move`) + top-voice term (`w.top`) − common-tone reward (`w.common`); equal-cardinality ascending-sorted inputs (pad/truncate is the caller's concern). **Pure integer.**
- `optimal_voicing_path(specs, candidates_fn, weights) -> [[midi]]`: §8.6 Viterbi DP with the drift term `w.drift·|top(vₜ)−anchor|` (anchor = lane midpoint default); integer costs throughout; ties break to lowest candidate index. O(N·K²).

**Verification (DoD 2):** voicing candidates per class with lane pruning (nothing above MIDI 71 in a ≤71 lane); `vl_distance` and `optimal_voicing_path` golden-tested on a hand-verified C-major ii–V–I fixture (shell and rootless classes); a **register-drift case** proving the anchor term prevents downward marching; integer-cost property (every cost an `int`). (The `fifths`-class *voicing goldens* proper are asserted in PHASE_5 §13.6 — this chunk ships the class and its lane/order behavior.)

---

### T3 — Dressing ladder (`harmony/dressing.*`) · model: opus · depends on T1

**Implements:** PHASE_4 §6.1 (tiers), §6.2 (function offsets + clamp), §6.3 (per-class option tables), §6.4 (extension-availability hard filter). Resolves nothing to draw — this is the *data + pure selection surface* the Chunk-2 stage draws over.

**Files:** `src/trackgen/harmony/__init__.py` (new package), `src/trackgen/harmony/dressing.yaml` (new, engine data), `src/trackgen/harmony/dressing.py` (new), `tests/test_dressing.py` (new).

**Build:**
- `dressing.yaml` transcribing §6.3 exactly: for each dressable class (bare major T/S, bare major D, bare minor, pinned dom7, pinned maj7, pinned min7) × effective tier → ordered weighted options. Passthrough classes (`dim,dim7,aug,sus*,maj6,min6,minMaj7,min7b5`) never dressed (v1).
- `tier(dissonance) -> int` (§6.1 boundaries 0–6), `effective_tier(base_tier, function) -> int` (§6.2 offsets D:+1, T:−1, S/O:0, clamped [0,6]).
- `dressing_options(spec, was_bare, function, base_tier) -> [(ChordSpec, weight)]`: look up the class/tier row, produce the candidate dressed `ChordSpec`s (using T1's `resolve_token`/spec construction + spelling) and integer weights. Bare tokens dress per the bare tables; suffixed dom7/maj7/min7 take only extension additions; passthrough classes return the single unchanged spec. **The stage (Chunk 2) performs the `weighted_choice` draw** — this function only returns the ordered option list.
- Every produced option validated against §6.4 (`legal_extensions` from T1).

**Verification (DoD 3):** unit tests for tier boundaries (each of the 7 ceilings), function offsets and clamping (tier-6 D stays ≤6; tier-0 T stays ≥0), the `dressing.yaml` values match §6.3 field-for-field, and **every** table option is §6.4-legal. Assert passthrough classes are returned unchanged.

---

### T4 — `progressions.yaml` schema + loader + reference packs · model: opus · depends on T1

**Implements:** PHASE_4 §4 (schema, P1–P10, §4.2 density), §9.1/§9.2 (reference content). **P11 excluded** (Phase 8).

**Files:** `src/trackgen/packs/models.py` (extend — add progressions models + a `progressions` field on `StylePack`), `src/trackgen/packs/loader.py` (wire optional `progressions.yaml` + cross-file P1/P4), `styles/pop_rock/progressions.yaml` (new, §9.1 verbatim), `styles/jazz/progressions.yaml` (new, §9.2 verbatim), `tests/test_progressions_pack.py` (new).

**Build:**
- Frozen `PackModel` subclasses for §4.1: `pools` (`{harmonyTag: [PoolEntry]}` with `id/weight/modes/valence?/dissonance?/phrases{label:[bar]}`), `turnarounds` (`bars`, may be empty), `finals` (required, non-empty). Bars are token lists of length 1/2/4 or `[~]`.
- In-model rules (single-file): P2 (unique ids per pool; weight≥1; modes non-empty ⊆ mode vocabulary), P3 (band ranges + lo≤hi), P5 (1/2/4 tokens or `[~]`; tokens parse via T1's parser; `~` never a phrase's first bar and never in turnarounds/finals), P6 (completeness: for every mode in the pack's `interpreter.yaml` `modes` menu, every pool + finals has ≥1 band-free entry listing it), P7 (cadence classes by the section **types** a tag serves — needs `forms.yaml`, so this is a **loader** cross-check, see below), P8 (turnarounds 1–2 bars, final D-function), P9 (finals non-empty, 1–2 bars, final chord degree-1-rooted), P10 (strict schema — `extra="forbid"`).
- §4.2 `density(entry) = totalTokens / totalBars` (holds excluded), computed + cached by the loader.
- **Loader cross-file checks** (mirror `_check_f11`): **P1** — every `harmonyTag` used by any bar option in the pack's `forms.yaml` has a non-empty pool (this is PHASE_3 §5.1's deferred check landing here); unused pools legal. **P4** — for every bar option of every section type using tag `T`, each pool-`T` entry provides exactly that option's phrase labels, each with the option's phrase length in bars. **P7** cadence classes also key off `forms.yaml` section types.
- Wire into `load_pack`: read `progressions.yaml` when present; run the cross-file checks against the already-loaded `forms`; wrap errors in `PackLoadError`.
- The two reference files: §9.1 (pop_rock — 6 pools, empty turnarounds, 4 finals) and §9.2 (jazz — 4 pools incl. `aaba_32`/`blues_12`, 7 turnarounds, 4 finals) copied **verbatim** (D-S4 discipline: do not "improve").

**Verification (DoD 1):** one rejection fixture per rule class P1–P10; both reference files load clean; the P1/P4 cross-file checks run against the reference `forms.yaml`. Assert the harmonyTags each reference `forms.yaml` uses are exactly served (pop_rock `{intro,verse,prechorus,chorus,bridge,outro}`; jazz `{intro,aaba_32,blues_12,outro}`).

---

## Per-task loop (PROMPT.md §2)

For each task, in order (T2/T3/T4 dispatched together after T1 commits): implement (tests included) → run all four gates and read output → dispatch an opus reviewer scoped to that task's diff (tests real & meaningful, code matches the pinned §, no contract violation) → bounded fix loop (max 2 cycles; escalate if a finding survives) → commit at the green gate → update PROGRESS.md immediately.

## Chunk close-out

After T1–T4: fresh opus whole-chunk review (parallel lenses: correctness, contract-compliance vs PHASE_4 §3/§4/§6/§8, test quality vs DoD 1/2/3/8, simplification), validation agents for findings, bounded fixes. Prove DoD items **1, 2, 3, 8** with evidence (test names, fixture paths, command output). Update PROGRESS.md with a chunk-1 log entry + a handoff block pointing SESSION_05 at Chunk 2 (stage + goldens). Log any CAVEATS. DoD items 4/5/6/7/9/10 remain for Chunk 2.
