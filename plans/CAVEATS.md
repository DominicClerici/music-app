# Caveats — Deviations from the Pinned Design

The design docs (`ROADMAP.md`, `PHASE_1.md`–`PHASE_8.md`) are binding, but implementation will occasionally force a deviation. Every deviation is logged here so its impact stays visible to later sessions, which otherwise have no memory of it.

**Log an entry when:** a pinned contract/algorithm/data format is changed or reinterpreted; a printed worked-example sample is found wrong (golden-value arbitration rule 2, `ROADMAP.md` §3); an algorithm ambiguity is resolved; scope is moved between phases/sessions; a dependency pin forces a design adjustment.

**Not caveats:** bugs fixed in this project's own new code, refactors that don't change pinned contracts, or decisions the PHASE docs explicitly left open (those are just decisions — record them in the session plan and PROGRESS.md).

## Entry format

```
### C-<nn>: <one-line title>
- **Date / session:** YYYY-MM-DD, session NN (Phase N)
- **What deviated:** the pinned text vs. what was actually built
- **Why:** the concrete forcing reason
- **Impact:** downstream PHASE docs / phases / fixtures affected; what a later session must know
- **Doc amendment:** commit hash of the PHASE/ROADMAP amendment, or "none needed" with justification
- **Status:** open | resolved
```

Numbered sequentially (`C-01`, `C-02`, …), never renumbered. If a later session resolves or supersedes an entry, update its **Status** in place and note how — do not delete entries.

## Log

### C-02: the degradation ladder (§7.3) is unreachable under the pinned §5.2 + §7.1 rules
- **Date / session:** 2026-07-15, session 03 (Phase 3)
- **What deviated:** PHASE_3 §7.1 step 5 / §7.3 present the `degrade` ladder as reachable ("exists for budgets too small for the template's drawn/minimal configuration"), and DoD §11.7 asks for "a fixture exercising each degrade op class." In the faithful implementation the ladder is **provably unreachable through `form()`**: §5.2 gates a template *in* only if `minBars ≤ barBudget` (its all-smallest config fits); §7.1 step-3 resolves each bar count only to options keeping `minimalTotal ≤ barBudget`, and the smallest option never raises `minimalTotal`, so the "0 feasible → take smallest" branch never fires and `minimalTotal ≤ barBudget` holds throughout; the arithmetic repeat count then yields `total ≤ barBudget` even when clamped up to `count.min` (that case gives `total == minimalTotal`). So the step-5 loop guard `total > barBudget` is never true for a *selected* template; the only over-budget path (no template eligible) routes to the step-6 **fallback**, not the ladder. Confirmed empirically: 0 ladder ops across ~40k property-matrix runs, and two independent review agents reconstructed the proof.
- **Why:** the pinned eligibility filter (§5.2, D4) and the pinned feasibility filter (§7.1 step 3b, D13) together guarantee fit before the ladder can ever run — the ladder and the eligibility/feasibility gates are two mechanisms solving the same "make it fit" problem, and the gates always win first. The step-3b "0 feasible" case the ladder was meant to repair is itself unreachable because the smallest authored option is always feasible.
- **Impact:** the ladder code (`src/trackgen/form/stage.py`, the step-5 branch) is retained as **defensive/unreachable** and is correct if ever reached (drop/shrink/dropFromRepeat verified by inspection). DoD §11.7's "exercise each degrade op class" was satisfied via a **substitute**: `test_degrade_ladder_authored_order` asserts each reference pack's authored ladder covers all three op classes in D11 order (data/config level); `test_30s_at_slow_tempo_valid_form` + tiny-budget fallback tests cover the fallback; a full-grid regression guard asserts the ladder never fires and the hard ceiling always holds. A future change that could make the ladder live — e.g. loosening §5.2 eligibility, or a pack/rule that lets an over-budget template be *selected* — must add real ladder-execution coverage. Two latent, currently-moot validation gaps in the ladder's own input rules were left unfixed for the same reason (they guard the dead path): F8's ending-candidate set omits the section a `drop` op newly exposes as final, and F9 accepts a top-level `drop:` targeting a repeat-only type (a silent no-op at runtime). Revisit both if Phase 8 authoring ever makes the ladder reachable.
- **Doc amendment:** none applied pending sign-off. Candidate: a one-line PHASE_3 §7.3 note that the ladder is defensive/unreachable under v1's eligibility+feasibility rules (retained for robustness and future rule changes). Not an algorithm change — the fitter's behavior is unaffected.
- **Status:** open (awaiting user sign-off on the §11.7 substitute coverage + the optional §7.3 doc note)

### C-01: `PARAM_MALFORMED` structural error code added beyond the §3.1 catalog
- **Date / session:** 2026-07-15, session 02 (Phase 2)
- **What deviated:** PHASE_2 §3.1 pins a 14-code validation catalog (all semantic conditions, assuming well-typed JSON input). The implementation adds a 15th code, `PARAM_MALFORMED`, emitted by `generate_plan` when `Params.model_validate` rejects a malformed field *type* (e.g. a fractional `tempoBpm`, a non-mapping `key`/`roleFlavors`). `validate_params` (the §3.1 catalog function) is unchanged and still returns only the 14 documented codes.
- **Why:** `validate_params` operates on the raw client dict and deliberately defers type/structural checks to the pydantic `Params` model (D-S6 two-layer design). Without wrapping, a malformed-type request escaped the public `generate_plan` boundary as a raw `pydantic.ValidationError` — contradicting §3.1's "failures return the full list of errors." Wrapping into `ParamsInvalid` with a structural code keeps a single structured error type at the boundary without fabricating a *semantic* §3.1 code.
- **Impact:** A later client-contract/HTTP layer enumerating error codes must include `PARAM_MALFORMED` (structural) alongside the 14 semantic §3.1 codes. Its `field` is a pydantic dotted location (e.g. `tempoBpm`), and its `message` is the pydantic message (not a hand-authored catalog message). Purely additive — no existing code changes meaning.
- **Doc amendment:** none needed — §3.1 does not specify behavior for malformed input types, so this fills an unspecified gap rather than changing a pinned condition. A future PHASE_2 §3.1 pass could document it explicitly.
- **Status:** resolved
