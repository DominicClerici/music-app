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

*(none yet)*
