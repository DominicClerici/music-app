# SESSION_06 — Phase 5, Chunk 1 (loaders + foundations)

**Phase:** 5 — Rhythm-section part generators. **Chunk:** 1 of 4.
**Design (binding):** `plans/PHASE_5.md`. **Upstream contracts:** `PHASE_1.md`
§4.4/§4.5/§6.2/§6.3, `PHASE_4.md` §8. **Invariants:** `ROADMAP.md` §3.
**Status:** awaiting approval — no task dispatched.

Written for a context-free implementer/reviewer: each task states its files,
the exact PHASE_5 sections it implements, the constraints, and the verification
it must pass. Read the named PHASE_5 sections in full before writing code — do
not redesign; build exactly what is pinned. On any divergence between a printed
worked-example number and the algorithm/data text, the **text wins** (golden-
value arbitration, ROADMAP §3) — never tune code to a printed sample.

---

## Phase-5 chunk plan (4 chunks; recorded here + PROGRESS.md)

Phase 5 is too large for one session (ROADMAP §4 seam; PHASE_5 §1). Split into
four chunks along the pinned seams:

1. **Chunk 1 — this session (SESSION_06): loaders + foundations.** Pattern-bank
   schemas (§5) + loader + PT1–PT11; the two reference banks fully enumerated
   (§7); the cross-cutting foundation modules (§3.1 intensity, §3.3 retargeting,
   §3.4 velocity/articulation, §3.5 density gating); §12 amendment check.
   **Proves DoD 1, 2**; DoD 11 (amendments) attested.
2. **Chunk 2 — arrangement + selection.** `arrange()` (§4) + the pattern-
   selection machinery and eligibility/completeness at runtime (§3.2). **DoD 3, 4.**
3. **Chunk 3 — generators / walker / voicing.** Drums, pattern-bass, the
   walking-bass engine (§6.3), comping + pads voicing passes (§6.4/§6.5).
   Resolves C-04 (real lane anchor, class-per-role, quartal reading). **DoD 5, 6, 7.**
4. **Chunk 4 — orchestrator + Serializer + milestone.** Pipeline wiring (§8.1),
   Serializer (§8.3) + stub timbres (§8.4) + drum→track map (§8.2), both
   milestone fixtures, whole-document goldens, determinism shims; whole-phase
   review + full §13 DoD. **DoD 8, 9, 10** + final DoD sign-off.

**This session's scope = Chunk 1 only.** Out of scope: `arrange()`, selection at
runtime, any part generator, the walker, voicing passes, the orchestrator, the
Serializer, milestone fixtures. Those are chunks 2–4. Chunk 1 builds the data
schemas + reference content + pure foundation transforms that later chunks compose.

---

## Task list (ordered; T2 ‖ T3 parallel after T1)

| # | Task | Model | Files (scope) | PHASE_5 §§ | Depends |
| --- | --- | --- | --- | --- | --- |
| T1 | Pattern-bank schema + loader + PT1–PT11 + one rejection fixture per class | opus | `packs/models.py`, `packs/loader.py`, `tests/test_patterns_pack.py` (new); `styles/_stub/patterns/*` iff needed | §5, §5.1, §5.5, §3.2 completeness, event-vocab (§3.3) | — |
| T2 | Reference banks §7 fully enumerated (8 YAML) + load/anchor test | opus | `styles/pop_rock/patterns/*.yaml`, `styles/jazz/patterns/*.yaml`, `tests/test_reference_banks.py` (new) | §7.1–§7.4, §5.3, §5.4 | T1 |
| T3 | Foundation modules §3.1/§3.3/§3.4/§3.5 + unit tests (DoD 2) | opus | `arrangement/intensity.py`+`.yaml`, `parts/retarget.py`, `parts/dynamics.py`, `tests/test_foundations.py` (new) | §3.1, §3.3, §3.4, §3.5 | T1 |
| T4 | §12 amendment-consistency check + whole-chunk review + close-out | orchestrator | `plans/*` | §12 | T1–T3 |

Module names in T3 are indicative; the design pins YAML schema + transform
behavior, not Python file layout. Keep new engine data under `arrangement/`
(engine-owned data, per §3.1/§4.3) and pure part-foundation transforms under a
new `parts/` package.

---

## T1 — Pattern-bank schema + loader + validation (opus)

**Implements:** PHASE_5 §5 (schemas), §5.1 (`layeringOrder`), §5.5 (PT1–PT11),
§3.2 completeness rules, and the additive event-vocabulary extensions the degree
table (§3.3) and pack schemas (§5) require. **Read §5, §5.1, §5.5, §3.2, §3.3
(degree/field vocabulary only), and §7 (to see every shape that must load).**

### Event-vocabulary extensions (additive to `PHASE_1 §6.3`; PackModel is `extra="forbid"`, so every new field MUST be declared)

- `Degree` (packs/models.py) gains **`sixth`** and **`chord`** (§3.3 rows; D5).
- `PitchedEvent` gains **`push: bool = False`** (PT8: boolean, pitched events
  only) and **`min_density: float | None = None`** (PT8: ∈[0,1]). **`octave`
  must become optional/defaulted** (`octave: int = 0`): §7 comping/pads events
  author `{pos, dur, degree: chord, velocity}` with no `octave`, while bass
  events set `octave: 0|1`. `degree: chord`/`push`-pushed-chord events ignore
  placement/anchor (§3.3), so octave is irrelevant for them.
- `DrumEvent` gains **`dur: int | None = None`** (§5.2 "dur optional, defaulting
  per voice"; PT2 `dur ≥ 1` where present) and **`min_density: float | None`**.
- PT3 is enforced structurally by `extra="forbid"`: `DrumEvent` never declares
  `degree`/`push`/`octave`; `PitchedEvent` never declares `voice`. `degree` must
  come from the §3.3 vocabulary (now incl. `sixth`/`chord`).

### Per-role bank shapes (§5)

The four banks no longer share one flat envelope-list shape. Model per role and
extend `StylePack` so later chunks can read the role-specific data:

- **`drums.yaml`** — envelope list; **carries the pack-level `layeringOrder`**
  (§5.1; both reference packs put it at the top of drums.yaml — §7.1). PT10:
  `layeringOrder` present exactly once per pack, a permutation of the four roles
  `[drums, bass, comping, pads]`.
- **`bass.yaml`** — top-level **`mode: patterns | walking`** (required, PT6);
  **`walking:` block required iff `mode: walking`** with `feelByIntensity`
  (rungs 1–4 → `two|four`), `approachWeights`, `beat1RepeatWeights` (non-empty
  integer-weight maps); `patterns:` required iff `mode: patterns`.
- **`comping.yaml` / `pads.yaml`** — **`voicing: {classes: {1:[…],2:[…],3:[…],
  4:[…]}}`** required (PT7): each rung → a non-empty ordered list of class names
  from PHASE_4 §8.4 ∪ {`fifths`} (the nine committed in `theory/voicing.py`:
  shell2, shell3, rootless_a, rootless_b, drop2, triad_close, triad_open,
  quartal, fifths). Plus the envelope `patterns:` list.

`StylePack` must expose, for later chunks: per-role `mode`/`walking`, per-role
`voicing.classes`, and `layeringOrder`. Choose the model shape (e.g. typed bank
models, or side fields on `StylePack`) — but **keep `_stub` and every existing
Phase 1–4 test green** (only `tests/test_packs.py` reads `pack.patterns[role]`,
against `_stub`; migrate that accessor if you change the shape, and update the
`_stub` pattern files if the envelope extension breaks their load).

### Validation PT1–PT11 (§5.5) — one rejection fixture per rule class

Model-level where a single bank suffices (pydantic validators, mirroring the
existing `PoolEntry`/`FormsConfig` style); loader-level for cross-file/completeness:

- **PT1** envelope: `id` unique per pack; `role` matches the file; `kind` in enum;
  `energyLevel` int 1–4; `lengthTicks` a positive **whole number of bars**
  (multiple of 1920 at 4/4 — validate against the bar tick length); `weight` int
  ≥ 1; **`kind: fill` patterns exactly 1 bar** (1920).
- **PT2** events: `pos` int ≥ 0 and `< lengthTicks`; `dur` int ≥ 1 where present;
  `velocity ∈ (0, 1]`; events authored in non-decreasing `pos` order.
- **PT3** vocabulary (see above; mostly structural via `extra="forbid"`).
- **PT4** `eligibility.tempoBpm`: ints, `0 < min ≤ max` (extends the existing
  `Eligibility` — currently `tuple[int,int] | None`; add the ordering/positivity
  check).
- **PT5** completeness (§3.2), **loader-level** (needs the whole role bank): per
  role with a pattern bank — ≥ 1 `main` with **no** eligibility gate at **each**
  rung 1–4; ≥ 1 ungated `intro`; ≥ 1 ungated `ending`. A `mode: walking` bass
  bank is **exempt** (no patterns). (PT12 — the drum-`fill` completeness rule —
  is PHASE_6's, per §3.2; do **not** add it here.)
- **PT6** `mode` only in `bass.yaml`; `walking` present iff `mode: walking`;
  `feelByIntensity` covers rungs 1–4 with values `two|four`; weight maps
  non-empty, integer-valued.
- **PT7** `voicing.classes` present in comping/pads, covers rungs 1–4, class
  names ∈ PHASE_4 §8.4 ∪ {`fifths`}.
- **PT8** `minDensity ∈ [0,1]`; `push` boolean, **pitched events only**.
- **PT9** `retarget` present on pitched-role patterns: `registerLow <
  registerHigh`, span ≥ 12, `onChordChange` in enum. (Bass/comping/pads carry
  `retarget`; drums do not — §5.2.)
- **PT10** `layeringOrder` present once per pack, a permutation of the four roles.
- **PT11** strict schema — unknown keys rejected (already `extra="forbid"`; add a
  fixture proving an unknown key rejects).

### Verify (T1)
- `uv run pytest` · `ruff check` · `ruff format --check` · `mypy` all green.
- `tests/test_patterns_pack.py`: one rejection fixture per PT1–PT11 class
  (assert the raised `PackLoadError`/`ValidationError` mentions the rule);
  positive: a small in-test bank exercising every new field loads.
- All pre-existing tests (644) still pass (`_stub` + Phase 1–4 untouched in
  behavior).

**Report:** files changed; the chosen `StylePack` shape + how later chunks read
mode/walking/voicing/layeringOrder; the PT#→fixture map; any `_stub` change and
why; open concerns.

---

## T2 — Reference banks §7 fully enumerated (opus) — after T1

**Implements:** PHASE_5 §7.1–§7.4 (complete the `# …`-abridged entries per the
§6.1 drum / §6.2 bass rung conventions and the §7 `retarget` defaults), §5.3
(jazz walking block), §5.4 (voicing classes). **Read §7 in full, plus §6.1/§6.2
for the rung content conventions, and §5.2–§5.4 for the per-file blocks.**

Author all eight files fully (no `# …` placeholders): `styles/pop_rock/patterns/
{drums,bass,comping,pads}.yaml` and `styles/jazz/patterns/{drums,bass,comping,
pads}.yaml`. Every value **explicitly stated** in §7 is a golden anchor and must
be reproduced verbatim (ids, kinds, energyLevels, weights, lengthTicks, and the
full events of `pr_dr_2a`, `pr_dr_i`, `pr_bs_2`, `pr_cp_2`, `jz_dr_2`,
`jz_cp_2a`, plus all bank candidate counts, the `voicing.classes` maps, the
walking block, `layeringOrder`). Entries shown abridged (`pr_dr_3`, `pr_dr_4`,
`pr_bs_3`, `pr_bs_4`, `pr_cp_3`, `pr_cp_4`, pads, jazz `jz_dr_3a/3b/4`,
`jz_cp_3a/3b/4`, etc.) are completed to the pinned rung conventions — this is
authoring latitude **only** within what §6.1/§6.2 pin; the stated anchors are not.

`retarget` per-file defaults (§7): bass `{registerLow: 28, registerHigh: 45,
onChordChange: retrigger}`, comping `{52, 67, retrigger}`, pads `{45, 64,
retrigger}` (entries may override). Drums carry no `retarget`.

**Do NOT** author swing, accents, fills-placement, or crashes — straight grid
only (D21); `kind: fill` patterns are authored under the envelope but their
selection/placement is Phase 6. Jazz pads are `quartal` at every rung though
dormant in v1 (`layersMax` 3) — author them anyway (§7.4).

### Verify (T2)
- `resolve_pack("pop_rock")` and `resolve_pack("jazz")` both load **clean**
  (PT1–PT11 + §3.2 completeness all pass) — this is DoD-1's "both reference packs
  load clean".
- `tests/test_reference_banks.py`: assert the §7 stated-anchor entries
  field-for-field (the six fully-enumerated patterns above, event lists exact);
  assert per-rung completeness (a `main`+ungated entry at each rung 1–4, ungated
  intro + ending) for drums/comping/pads in both packs and pop bass; assert the
  jazz bass `mode: walking` + walking block values; assert `voicing.classes`
  maps and `layeringOrder`; assert bank candidate counts match §9.1's draw
  narrative premises (e.g. jazz drums rung 3 has {jz_dr_3a w3, jz_dr_3b w2};
  jazz comping rung 2 has {jz_cp_2a w3, jz_cp_2b w2}).
- Four gates green.

**Report:** the completed entries (which were authored vs stated-verbatim); the
per-rung candidate counts per bank per pack; confirmation both packs load clean;
any place §7's prose left genuine latitude and how it was resolved.

---

## T3 — Foundation transforms §3.1/§3.3/§3.4/§3.5 (opus) — after T1, ‖ T2

**Implements:** PHASE_5 §3.1 (intensity), §3.3 (retargeting), §3.4 (velocity/
articulation), §3.5 (density gating), as pure deterministic transforms with
isolated unit tests (**DoD 2**). **Read §3.1, §3.3, §3.4, §3.5 in full**, plus
`PHASE_4 §8` for the theory helpers (`chord_tones`, `guide_tones`, `scale_pcs`,
`chord_intervals`, `EXTENSION_OFFSETS`, `QUALITY_INTERVALS`) and §7.4 for the
`EventScale` hint (already on `ChordEvent.scale`).

### §3.1 intensity (`arrangement/intensity.yaml` + `intensity.py`)
Global engine threshold table (engine-owned data): rung 1 `e<0.30`, 2
`0.30≤e<0.55`, 3 `0.55≤e<0.80`, 4 `e≥0.80`. `intensity(energy) -> int∈1..4`.
Boundary-exact (0.30→2, 0.55→3, 0.80→4).

### §3.3 retargeting (`parts/retarget.py`)
Pure functions turning a pattern event + its governing `ChordEvent` (and the next
event, the role's lane as a `schema.ir.Register`, and role) into resolved
pitch(es)/handling. Pin exactly:
- **Degree table** (§3.3) with the **dressing-safe fallback column** — every
  degree (`root` incl. bass `bassPc` rule, `third`, `fifth`, `sixth`, `seventh`,
  `guide3`, `guide7`, `tension`, `approach`, `chord`) and its fallback when the
  quality lacks the slot. `tension` = first `extensions` entry, fallback = the
  chord-scale's 2nd degree; `approach` = chromatic half-step **below** the next
  event's effective root in the nearest octave, fallback (song end) = `root`.
  `chord` = the role's voicing-pass voicing (a Chunk-3 input) — here expose the
  hook/return shape; do not build the voicing pass.
- **`push`** (§3.3): resolve against the chord in effect immediately **after**
  the next boundary within `(ticks, ticks+durationTicks]`; no boundary in span →
  resolve normally; pushed notes tagged `"push"`; pushed `chord` → next voicing.
- **Octave placement + lane folding** (§3.3): `anchor` = midpoint of
  (pattern `retarget` register ∩ role lane) (lane alone if disjoint); place the
  pc in the unique octave within `(anchor−6, anchor+6]`; shift by `12×octave`;
  **fold by octaves to the nearest position inside the lane, ties down**. Lanes
  span ≥ 12 so folding always succeeds.
- **`onChordChange`** (§3.3): `hold` / `retrigger` (split at boundary, re-resolve
  the remainder, **drop remainders < 60 ticks**) / `stop` (truncate at boundary).
  Default `retrigger` for pitched roles; drums exempt.

### §3.4 velocity/articulation (`parts/dynamics.py`)
- Velocity (all roles): `round3(clamp(authored + 0.4×(dynamicsBase−0.5), 0.05,
  1.0))`. Identity at 0.5. `round3` = 3-decimal half-even (match the codebase's
  rounding convention).
- Articulation (**comping + pattern-mode bass only**): `round(authored ×
  (0.7 + 0.6×articulationLegato))`, clamped to the gap before the same track's
  next event. **Exempt:** drums, pads, walker.

### §3.5 density gating
An event with `minDensity` instantiates iff `section.densityBudget ≥ minDensity`;
events without the field always play. Deterministic — no draws.

### Verify (T3) — DoD 2
`tests/test_foundations.py`, all four gates green:
- §3.1: boundary values (0.29/0.30/0.54/0.55/0.79/0.80/1.0).
- §3.3: every degree × representative qualities (triad, 6th, 7th, min7b5, sus,
  extended) × ≥ 2 dressing tiers, hitting **every fallback row**; `push` with a
  boundary in span, no boundary in span, and song-end; octave folding at both
  lane edges with the **tie-down** rule; `onChordChange` hold/retrigger/stop incl.
  the < 60-tick remainder drop.
- §3.4: identity at 0.5, both clamps, exemptions (drums/pads/walker unchanged).
- §3.5: gated event dropped below threshold, kept at/above, ungated always kept.

**Report:** module layout + public signatures later chunks call; the degree→
fallback table as implemented; how `chord`/voicing-pass is stubbed for Chunk 3;
any §3.3 ambiguity resolved and how (flag for a possible CAVEAT).

---

## T4 — Amendment check + whole-chunk review + close-out (orchestrator)

- **§12 amendments** (DoD 11): verify each of the 11 additive annotations is
  present + consistent in its target doc (PHASE_1 §7 Q2/Q3, §4.4, §4.5, §6.2,
  §6.3; PHASE_2 §7.2; PHASE_3 §6.5; PHASE_4 §8.4/§8.5; ROADMAP §2). These were
  "applied in the same commit as PHASE_5" — expect present; if any is missing,
  escalate (do not silently edit a PHASE doc without sign-off).
- **Whole-chunk review** (fresh opus lenses, parallel): (A) contract/integration
  — schemas match §5/§7, loader PT1–PT11 correct, foundations match §3.1/§3.3–
  §3.5; (B) test quality / DoD 1+2 coverage — fixtures real (not vacuous), the
  §7 anchors are doc-transcribed, DoD-2 hits every fallback/boundary. Validate
  each finding before fixing (2-cycle bound).
- **Close-out:** PROGRESS.md statuses + session-log row + handoff for Chunk 2;
  CAVEATS entries for any deviation; commit the doc updates.

---

## Constraints (every task)

- **Determinism** (ROADMAP inv. 5): no wall-clock, no unseeded randomness outside
  `seeds.py` (TID251 enforces the import layer — never work around it). Chunk 1 is
  almost entirely draw-free (data + pure transforms); the only RNG discipline note
  is that selection/walker come in later chunks.
- **Style packs are data** (inv. 1): all bank content, weights, eligibility,
  voicing classes, walker params, layering order live in YAML; engine code only
  parameterizes.
- **Rhythm ≠ pitch** (inv. 2): patterns author degrees/chord-hits, never literal
  pitches; retargeting is where pitch first appears.
- **Soloist owns > ~C5** (inv. 4): non-drum lanes `high ≤ 71`; octave folding in
  §3.3 must not escape a lane.
- Integer weights, ascending-sorted candidate lists, 3-decimal half-even rounding
  for emitted velocities/budgets.
- Gates (all four, read the output): `uv run pytest` · `uv run ruff check .` ·
  `uv run ruff format --check .` · `uv run mypy`.
- Subagent model policy (PROMPT §"Subagent model rules"): every dispatch sets
  `model` explicitly; **opus** for all of T1–T3 (real judgment); never Fable 5.
