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

### C-01: `PARAM_MALFORMED` structural error code added beyond the §3.1 catalog
- **Date / session:** 2026-07-15, session 02 (Phase 2)
- **What deviated:** PHASE_2 §3.1 pins a 14-code validation catalog (all semantic conditions, assuming well-typed JSON input). The implementation adds a 15th code, `PARAM_MALFORMED`, emitted by `generate_plan` when `Params.model_validate` rejects a malformed field *type* (e.g. a fractional `tempoBpm`, a non-mapping `key`/`roleFlavors`). `validate_params` (the §3.1 catalog function) is unchanged and still returns only the 14 documented codes.
- **Why:** `validate_params` operates on the raw client dict and deliberately defers type/structural checks to the pydantic `Params` model (D-S6 two-layer design). Without wrapping, a malformed-type request escaped the public `generate_plan` boundary as a raw `pydantic.ValidationError` — contradicting §3.1's "failures return the full list of errors." Wrapping into `ParamsInvalid` with a structural code keeps a single structured error type at the boundary without fabricating a *semantic* §3.1 code.
- **Impact:** A later client-contract/HTTP layer enumerating error codes must include `PARAM_MALFORMED` (structural) alongside the 14 semantic §3.1 codes. Its `field` is a pydantic dotted location (e.g. `tempoBpm`), and its `message` is the pydantic message (not a hand-authored catalog message). Purely additive — no existing code changes meaning.
- **Doc amendment:** none needed — §3.1 does not specify behavior for malformed input types, so this fills an unspecified gap rather than changing a pinned condition. A future PHASE_2 §3.1 pass could document it explicitly.
- **Status:** resolved
