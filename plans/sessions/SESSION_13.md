# SESSION_13 — Phase 7 (Sound design), Chunk 1: foundations

**Phase:** 7 — Sound design. **Chunk:** 1 of 2. **Session:** 13.
**Design authority:** `plans/PHASE_7.md` (binding). Read it; this plan does not restate it.
**Orchestrator prompt:** `plans/PROMPT.md`. **Invariants:** `ROADMAP.md` §3.

---

## Why Phase 7 is split (chunk boundary — pinned)

Phase 7 replaces the whole provisional sound surface at once: the moment the real
`timbres.yaml` **schema** lands, the real reference **content** must land (the stub
content is invalid under it and vice-versa — both schemas are strict), and the moment
`resolve_pack` returns the new `pack.timbres` model, the **stage** that reads it
(`pipeline/stubs.py::sound_design`) and the **Serializer** mix that follows must land
too — otherwise `resolve_pack(...)` and the whole-document goldens break and ~4315
tests go red. That flip is one indivisible integration landing (Chunk 2).

Everything *upstream* of the flip — the engine data, the evaluation model, and the
new schema+validators — can be **built and fully unit-tested in isolation** without
touching `resolve_pack` or the pipeline, because they are new modules wired to
nothing. That is Chunk 1. It mirrors the proven Phase-4 shape (theory + loader in
chunk 1; stage + goldens + whole-phase review in chunk 2).

**Chunk 1 (this session):** engine data (`sound/allowlist.yaml`, `sound/mod_defaults.yaml`)
+ the patch-evaluation model + the real `timbres.yaml` pydantic schema & TB validators
— all new code, **nothing wired into `resolve_pack` or the pipeline**, all four gates
green throughout, reference packs stay on the stub loader. Targets **DoD 2, 3** fully
and **DoD 1** partially (validators + TB1 function + one rejection fixture per rule
class; "both reference files load clean" is the wired check, deferred to Chunk 2).

**Chunk 2 (session 14):** the flip — author the full real `styles/{pop_rock,jazz}/timbres.yaml`,
swap `resolve_pack` to the new loader (TB1 live against `interpreter.yaml`), write the
real `sound_design(plan, pack) → SoundDesign` stage (§7), wire orchestrator + Serializer
(delete `_STUB_MIX`/`_MASTER_EFFECTS`/stub buses + `pipeline/stubs.py::sound_design` +
stub `TimbresConfig`), re-bless both whole-document goldens (dedicated commit), §9 stage
goldens field-for-field, zero-draw determinism, the property matrix, whole-phase 4-lens
review, full DoD 1–9 + §12 amendment audit, close-out. Targets **DoD 1 (complete), 4,
5, 6, 7, 8 (user audition), 9**.

---

## Chunk 1 scope

### In scope
- New package `src/trackgen/sound/` holding the Phase-7-owned engine data + evaluation
  + the real `timbres.yaml` schema, **all unwired**.
- `sound/allowlist.yaml` (the PHASE_1 §3.6 `(class, option-path)` allowlist as engine
  data, D12) + loader.
- `sound/mod_defaults.yaml` (§5.1 verbatim) + loader.
- The shared `MappingEntry` model (`{param, min, max, curve}`) + its well-formedness
  validators (curve enum; `exp ⇒ min,max > 0`).
- The patch-evaluation model (§3): curve evaluation (linear/exp), `round3` (half-even),
  inverted ranges, per-directive-key merge (`merge_mod`, drums per-`(directive,voice)`),
  empty-list disable, base-XOR-mod check, fixed directive order helper.
- The real `timbres.yaml` pydantic schema (`PitchedFlavor`, `KitFlavor`/`KitVoice`,
  `MixBlock`, `ReverbBus`, `MasterChain`, real `TimbresConfig`) + validators **TB2–TB9**
  intra-file and **TB1** as a standalone `check_flavor_completeness(...)` function.
- Rejection fixtures: **one per rule class** (TB1–TB9) + the MappingEntry caps.
- Unit tests for all of the above.

### Explicitly out of scope (Chunk 2)
- Any edit to `packs/loader.py::resolve_pack`, `StylePack.timbres` typing, or the stub
  `TimbresConfig` (it stays live through Chunk 1).
- Any edit to `pipeline/` (orchestrator, serialize, stubs), the reference
  `styles/*/timbres.yaml` content, or the whole-document goldens.
- The real `sound_design` stage, `SoundDesign` output type, §9 stage goldens, the
  property matrix, determinism zero-draw shim, re-bless.
- Riser **content/wiring** (§4.7): Chunk 1 only ensures the schema *can express* the
  riser recipe (a `NoiseSynth` patch + `Filter` insert + a send) — no riser flavor is
  authored, none is wired (dormant, PHASE_8 §3.8: no v1 pack opts in).

---

## Ground rules for every implementer (repeat verbatim in each dispatch)
- Determinism (ROADMAP inv. 5): **zero** RNG, no `random`/`os.urandom`/`time`/`datetime.now`
  (TID251 enforces the import layer — do not work around it). The sound stage is a pure
  function of `(plan, pack)`; Chunk 1 code is pure data + pure functions.
- `round3` half-even = Python built-in `round(x, 3)` — the repo idiom (`form/energy.py:114`,
  `arrange.py:165`). Use it; do not roll a custom rounding.
- **Golden-value arbitration** (ROADMAP §3): the §5.1/§8/§9 printed numbers are derived
  samples. If a faithful transcription of §5.1 or a validator reading diverges from the
  doc, **do not tune** — report it to the orchestrator with evidence (xfail/escalate,
  the C-09 precedent). Chunk 1 transcribes §5.1 and reads §4.5; it computes no §9 sample.
- Four gates must be green and read before you report done:
  `uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy`.
  Full suite is ~7m20s / 4315 tests — run pytest with an extended timeout. You may scope
  your own iteration to the new test file, but the final report must be the full suite.
- New models are frozen pydantic (mirror `packs/models.py::PackModel` config); strict
  (unknown keys rejected) where the schema is strict (TB9). Fully typed for mypy.
- Do not add comments that restate the code (global rule). Comments explain *why* only.

---

## Task list (order: T1 → T2 → T3 → T4; T1 and T2 share `sound/models.py` so serialize)

### T1 — Engine data: allowlist + mod_defaults + shared MappingEntry  (model: **opus**)

**Implements:** PHASE_7 §5.1, §5.2, §3.1 (mapping-entry shape), §4.5 TB7 (well-formedness
slice), D12.

**Build**
- `src/trackgen/sound/__init__.py`.
- `src/trackgen/sound/models.py`:
  - `Curve = Literal["linear", "exp"]`.
  - `MappingEntry(PackModel)`: `param: str`, `min: float`, `max: float`, `curve: Curve`.
    Validators: `curve` in the enum; **if `curve == "exp"` then `min > 0` and `max > 0`**
    (§3.1). Inverted ranges (`min > max`) are **legal** — do not reject them.
- `src/trackgen/sound/allowlist.py` + `src/trackgen/sound/allowlist.yaml`:
  - `allowlist.yaml` = per whitelisted class, the **fully expanded** list of legal option
    paths (no `.*` wildcards in the committed file — §5.2 / DoD 2). Seed content = the
    **union** of: every path the §5.2 illustrative block names (expanded), every `param`
    the §5.1 `mod_defaults` mappings target, every option path used by the §8 reference
    recipes (base patches, inserts, bus, master), and every path the PHASE_1 milestone
    fixture patches use. This guarantee is load-bearing: TB3/TB4/TB7 in Chunk 2 validate
    the real reference content against exactly this file, so a missing seed path there
    becomes a false rejection. When §5.2 prose ("`envelope.*` expands to the five envelope
    fields + attackCurve") is imprecise, the authoritative rule is *include exactly the
    subpaths §5.1/§8/the PHASE_1 fixture actually emit* (`envelope.attack/decay/sustain/
    release/attackCurve`, `modulationEnvelope.attack/decay/sustain/release`, etc.) —
    engine data is a seed, additive by amendment. **Note any such expansion decision in
    your report** so the reviewer/orchestrator can confirm it (candidate handoff note, not
    a caveat unless it contradicts a pinned value).
  - `load_allowlist() -> Allowlist` (fixed module-adjacent path, `Path(__file__).parent`,
    the `feel.py`/`moods.py` idiom) → a frozen model exposing `is_legal(cls: str, path: str)
    -> bool`. Unknown class ⇒ `is_legal` returns `False` (a patch on an un-allowlisted
    class is illegal), not an error.
- `src/trackgen/sound/mod_defaults.py` + `src/trackgen/sound/mod_defaults.yaml`:
  - `mod_defaults.yaml` = §5.1 **verbatim** (bass/comping/pads each with
    brightness/attackHardness/space lists — note bass `space: []` and comping/pads
    `attackHardness` single-entry; drums per-voice under `brightness`/`space`, **no**
    `attackHardness` for drums, D4).
  - `load_mod_defaults() -> ModDefaults` (fixed path). Model shape: pitched roles
    (`bass`/`comping`/`pads`) → `{brightness: [MappingEntry], attackHardness: [...],
    space: [...]}`; `drums` → `{brightness: {voice: [MappingEntry]}, space: {voice: [...]}}`.

**Tests** (`tests/test_sound_engine_data.py`):
- `mod_defaults.yaml` matches §5.1 **field-for-field**: assert the exact `{param,min,max,
  curve}` of every entry for every role/voice/directive (this is the transcription guard;
  a wrong number here is either a typo or a §5.1 arbitration flag — do not tune).
- `bass.space == []` and drums have no `attackHardness` key (D4).
- Allowlist: `load_allowlist()` succeeds; `is_legal` true for a sample of seeded paths per
  class (e.g. `MonoSynth`/`filterEnvelope.baseFrequency`, `MetalSynth`/`resonance`,
  `NoiseSynth`/`noise.playbackRate`, `Reverb`/`decay`, `Compressor`/`threshold`); false for
  an un-seeded path and an unknown class.
- **Coverage assertion (load-bearing):** every `param` targeted by any `mod_defaults`
  mapping `is_legal` for that role's reference engine class per the allowlist (bass →
  MonoSynth, comping/pads → the subtractive path; drum voices → their kit classes). This
  is the C1 proof that the allowlist covers §5.1; the §8/fixture coverage is proven in C2.
- MappingEntry rejection fixtures (constructed inline via `model_validate`, the `feel.py`
  test idiom): bad `curve` value; `exp` with `min == 0`; `exp` with `max <= 0`. Assert an
  inverted **linear** range (`min > max`) is accepted.

**Verify:** four gates; the §5.1 transcription assertions and the allowlist-coverage
assertion pass.  **Files:** `src/trackgen/sound/{__init__,models,allowlist,mod_defaults}.py`,
`src/trackgen/sound/{allowlist,mod_defaults}.yaml`, `tests/test_sound_engine_data.py`.
**DoD:** §13.2 (engine data).

---

### T2 — The patch-evaluation model  (model: **opus**)

**Implements:** PHASE_7 §3.1, §3.2, §3.3, §3.4, D5.

**Build** — `src/trackgen/sound/evaluate.py` (pure functions over `MappingEntry` + plain
dicts; consumes T1's `sound/models.py`):
- `round3(x: float) -> float` = `round(x, 3)` (single half-even, the repo idiom).
- `evaluate_mapping(entry: MappingEntry, d: float) -> float`:
  - `linear`: `min + d*(max − min)`; `exp`: `min * (max/min)**d`; then `round3`.
  - Correct for inverted ranges (`min > max`) by the same formulas (§3.1: attackHardness
    maps slow→fast this way).
- `merge_mod(defaults, override) -> merged`: **per-directive-key replacement** (§3.2) — a
  present override list for a directive replaces the whole default list for that directive;
  an **empty list** explicitly disables the directive; an **absent** key keeps the default.
  For drums the key is `(directive, voice)`. No entry-level merging.
- `assert_base_xor_mod(base_paths: set[str], mapped_paths: set[str]) -> None`: raise on any
  path present in **both** (§3.3) — the schema-level "which value wins" killer. (TB7 in T3
  calls this after merge.)
- `apply_directives(base: dict, mapping_lists_in_order, directive_values) -> dict`: deep-copy
  `base`; apply directives in the fixed order **brightness → attackHardness → space** (§3.4),
  each list in authored order, setting each evaluated value into the options object (or the
  mix block) **by dotted path**. Zero RNG. (A small dotted-path setter/getter helper lives
  here; reuse it in T3's allowlist path checks if convenient.)

**Tests** (`tests/test_sound_evaluate.py`):
- Both curves: endpoints (`d=0 → min`, `d=1 → max`), midpoint (`d=0.5`), an inverted
  linear and an inverted exp range (result decreases as `d` rises).
- `round3` half-even at a `.xxx5` tie (assert banker's rounding, matching `round(x,3)`).
- `merge_mod`: override replaces; **empty-list disables** (result has no entries for that
  directive); absent key keeps default; a drum per-`(directive,voice)` override replaces
  only that voice's list.
- `assert_base_xor_mod` raises when a path is in both, passes when disjoint.
- `apply_directives`: the fixed order is applied; a value lands at the correct nested path;
  a `mix.sends.reverb` mapping writes into the mix block, not the options object.
- Recompute **one** §9.1 mapped value inline (e.g. pop snare `noise.playbackRate` =
  `round3(2 + 0.835*2) = 3.67`, or bass `filterEnvelope.baseFrequency` =
  `round3(120*(2500/120)**0.835)`) to prove the evaluator reproduces a pinned §9 number —
  **not** a golden (that is C2/§13.4), just an evaluator sanity anchor. If it diverges,
  **escalate** (arbitration), do not tune.

**Verify:** four gates.  **Files:** `src/trackgen/sound/evaluate.py`,
`tests/test_sound_evaluate.py`.  **DoD:** §13.3 (evaluation).

---

### T3 — The real `timbres.yaml` schema + TB1–TB9 validators (unwired)  (model: **opus**)

**Implements:** PHASE_7 §4.1–§4.5, §4.6 (honest-synthesis: ids kept verbatim), §4.7
(schema expresses the riser; no content), D12, D13.

**Build** — `src/trackgen/sound/timbres.py` (the real schema; **does not touch**
`packs/models.py::TimbresConfig`, which stays live for the stub loader through C1):
- `MixBlock(PackModel)`: `volume_db: float ≤ 6`, `pan: float ∈ [−1,1]`, `sends: dict[str,
  float] | None` (bus-id → gainDb). (TB6.)
- `KitVoice(PackModel)`: `midi: int | None`, `patch: InstrumentPatch`-shaped (reuse the
  PHASE_1 `schema/document.InstrumentPatch` if it fits, else a local patch model), `mix:
  MixBlock`.
- `KitFlavor(PackModel)`: `kit: dict[str, KitVoice]` (the **nine** voice-track ids), `mod:
  {brightness?: {voice: [MappingEntry]}, space?: {...}, attackHardness?: {...}} | None`.
- `PitchedFlavor(PackModel)`: `engine: {type, voice?, maxPolyphony?}`, `base: dict`,
  `effects: [EffectPatch] = []`, `mix: MixBlock`, `mod: {brightness?: [MappingEntry],
  attackHardness?: [...], space?: [...]} | None`.
- `ReverbBus(PackModel)`: `decay: [lo, hi]`, `preDelay: [lo, hi]`, `returnFilterHz: float`.
- `MasterChain` = `list[EffectPatch]` (must end with a `Limiter` — TB4).
- `TimbresConfig` (real): `flavors: {drums: {id: KitFlavor}, bass/comping/pads: {id:
  PitchedFlavor}}`, `bus: {reverb: ReverbBus}`, `master: MasterChain`. Strict (TB9).

**Validators** (each with a rejection fixture — DoD 1):
- **TB1** — standalone `check_flavor_completeness(timbres, declared: dict[role, set[str]])
  -> None`: per role, the `timbres` flavor-id set **equals** the declared set (no dangling,
  no orphan). **Function only in C1** (exercised with fixtures); the live call from
  `resolve_pack` against `interpreter.yaml` is C2. Resolves the PHASE_2 D14 deferred check.
- **TB2** — `engine.type` in the PHASE_1 instrument whitelist; `voice`+`maxPolyphony`(1–32)
  present **iff** `type == PolySynth`; `voice` in the Monophonic whitelist (PHASE_1 V7).
- **TB3** — every `base` option path ∈ allowlist for the patch class (`sound/allowlist.py`);
  same for every kit-voice patch.
- **TB4** — every insert `type` ∈ the effect whitelist and its option paths ∈ allowlist;
  bus/master entries likewise; **`master` ends with a `Limiter`**.
- **TB5** — kits define **exactly** the nine voice-track ids; `midi` present **iff** the
  voice's class ≠ `NoiseSynth`; `midi ∈ 0–127`.
- **TB6** — mix: `volume_db ≤ 6`; `pan ∈ [−1,1]`; every `sends` key references a declared
  bus (`reverb` is the only v1 bus).
- **TB7** — mod: directive keys ⊆ {brightness, attackHardness, space}; entries well-formed
  (MappingEntry rules); **every effective mapping's `param` legal for the flavor's engine
  class** per allowlist (or is `mix.sends.reverb`); after `merge_mod`, **base XOR mod**
  holds per path (call T2's `assert_base_xor_mod` on merged defaults+override vs base).
- **TB8** — `bus.reverb`: `0 < decay.lo ≤ decay.hi`; `0 ≤ preDelay.lo ≤ preDelay.hi`;
  `returnFilterHz > 0`.
- **TB9** — strict schema; unknown keys rejected (pydantic).

**Tests** (`tests/test_timbres_schema.py`):
- A **complete, valid** synthetic `TimbresConfig` fixture (author a minimal-but-complete
  one-flavor-per-role pack as inline test data — nine kit voices, one pitched flavor each,
  bus, master; you may transcribe a subset of §8 pop_rock as the source, but the reference
  files themselves stay stub-format in C1) loads clean; `check_flavor_completeness` passes
  when declared == present.
- **One rejection fixture per rule class TB1–TB9**, each asserting the specific rule fires
  (match on the rule's error text/code, non-vacuous — the fixture must be otherwise-valid
  and fail *only* on the targeted rule). Include: TB1 dangling id + orphan id; TB2 PolySynth
  missing `voice`; TB3 base path not in allowlist; TB4 master not ending in Limiter + an
  insert path not in allowlist; TB5 missing a kit voice + a `midi` on a NoiseSynth voice;
  TB6 `volume_db = 7` + a `sends` key that is not `reverb`; TB7 a `base` path also targeted
  by a `mod` entry (base-XOR-mod) + a mod `param` illegal for the engine class; TB8
  `decay.lo = 0`; TB9 an unknown top-level key.
- Assert the schema can **express the riser recipe** (§4.7): a `NoiseSynth` patch with an
  envelope, a `Filter` highpass insert, and a `sends` entry validates (no riser flavor is
  added to any reference pack).

**Verify:** four gates; the reference packs still `resolve_pack` clean on the **stub**
loader (you changed nothing in `packs/`).  **Files:** `src/trackgen/sound/timbres.py`,
`tests/test_timbres_schema.py`.  **DoD:** §13.1 partial (validators + rejection fixtures +
TB1 function; "reference files load clean" → C2).

---

### T4 — Whole-chunk review + DoD 1(partial)/2/3 + close-out  (orchestrator + fresh opus reviewers)

- Two fresh **opus** review lenses in parallel over the C1 diff (disjoint concerns):
  1. **correctness/contract** — does the evaluation model match §3 clause-by-clause
     (curves, round3 half-even, per-key merge incl. empty-list-disable, base-XOR-mod, fixed
     order)? Do TB1–TB9 match §4.5 exactly? Is `mod_defaults.yaml` a faithful §5.1
     transcription (re-derive a few entries)? Is the allowlist seed sufficient for §5.1 (and
     spot-check it against §8 recipes so C2 won't hit a false rejection)? Any hidden RNG /
     TID251 risk? Any pinned-value divergence (→ arbitration, not a fix)?
  2. **test-quality/DoD** — are the rejection fixtures non-vacuous (fail only on the targeted
     rule)? Are the §5.1 transcription + allowlist-coverage + evaluator-anchor tests real and
     discriminating? Are DoD 2 and 3 fully proven and DoD 1's C1 slice proven?
- For each confirmed finding: a **validation** agent confirms it's real, then a fix agent +
  gate re-run (max 2 fix cycles; escalate if it survives).
- Confirm four gates green; check DoD 2, 3 fully and DoD 1 (C1 slice) with evidence
  (test names). Log any CAVEATS (expected: none, unless a §5.1/§4.5 divergence surfaces —
  then arbitration + sign-off).
- Close out: update `PROGRESS.md` (T1–T4 done + commits, DoD evidence, fresh handoff → C2),
  add any CAVEATS, commit the doc updates.

---

## Chunk-1 → Chunk-2 handoff (write into PROGRESS.md at close-out)
- New `src/trackgen/sound/` package: engine data + evaluator + real timbres schema, **all
  unwired**. `resolve_pack`, `StylePack.timbres`, the stub `TimbresConfig`, `pipeline/`,
  and the reference `styles/*/timbres.yaml` are **untouched** — the pipeline still runs the
  stub `sound_design` + `_STUB_MIX`.
- C2 flips it: author real content, swap the loader (TB1 live), write + wire the real stage
  (`SoundDesign` = `{trackSounds:{id:{instrument,effects,channel,sends}}, buses, master}`,
  §7), delete the stubs, re-bless the two whole-doc goldens (dedicated commit, arbitration
  rule 3), §9 field-for-field goldens, zero-draw determinism, property matrix (DoD 6),
  whole-phase 4-lens review, DoD 1(complete)/4/5/6/7/8(user)/9 + §12 amendment audit.
- Any allowlist expansion decisions / §5.1 transcription notes flagged by T1–T4 land here
  as verified handoff notes.
