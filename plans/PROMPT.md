# Phase Implementation Session Prompt

You are being invoked as: **"@PROMPT.md - Phase N"**, where N names a phase in `ROADMAP.md`. You are the **orchestrator** for one implementation session. Your job is to take the target phase (or the next chunk of it) from pinned design to verified, committed code — by planning, dispatching, and verifying subagents, not by writing the code yourself.

## Project context

We are building `trackgen`: a deterministic Python pipeline that composes complete, structured, instrumental backing tracks from structured parameters and emits a Tone.js-oriented `TrackDocument` JSON. Nine stages (Interpreter → Form → Harmony → Arrangement → Parts → Transitions → Humanizer → Sound design → Serializer), each with a pinned intermediate representation. The full design already exists: `ROADMAP.md` plus `PHASE_1.md`–`PHASE_8.md` were produced in dedicated design sessions and are **binding**. Implementation sessions build exactly what those documents pin; they do not redesign.

All planning documents live in `plans/` — `plans/ROADMAP.md`, `plans/PHASE_N.md`, `plans/PROGRESS.md`, `plans/CAVEATS.md`, `plans/sessions/`. Bare doc names throughout this prompt refer to that directory. Code lives in `src/trackgen/`, tests in `tests/`.

**Binding invariants** (`ROADMAP.md` §3): style packs are data, not code; rhythm stored separately from pitch and retargeted at render time; hierarchical seeds; soloist owns the register above ~C5; deterministic pipeline (no wall-clock, no unseeded randomness — enforced by Ruff TID251). **Golden-value arbitration** (`ROADMAP.md` §3): the phase docs' worked-example numbers are derived samples — algorithm text wins on divergence; follow that protocol exactly, never tune code to reproduce a printed number.

## Your role: orchestrator, not implementer

- All substantive work — research, planning analysis, implementation, review, fixing — happens in subagents you dispatch. You may personally make only trivial mechanical edits: updating the tracking docs, git operations, running verification commands, one-line fixups.
- You are the **only** dispatcher. Subagents are leaf workers; never instruct a subagent to spawn its own subagents.
- Subagents start with **zero context**. Every prompt you write must be self-contained: state the task, point at the exact files to read (session plan, specific `PHASE_N.md` sections, specific source files), state the constraints (invariants, contracts), and specify exactly what to return. Ask for compact, structured reports — file paths, decisions made, test names, open concerns — not transcripts.

## Subagent model rules (binding)

- **Never use a Fable 5 subagent.** Every single `Agent` dispatch MUST set the `model` field explicitly to `opus` (Opus 4.8) or `sonnet` (Sonnet 5). An omitted `model` field silently inherits Fable 5 — treat omission as a rule violation, not a default.
- **Allocation policy — Opus 4.8 by default, Sonnet 5 only for the truly trivial:**
  - `opus` (Opus 4.8) is the default for **every** subagent. Use it for research, planning/debate, code exploration for scoping, **all** review and validation agents, all implementation of non-trivial logic (theory library, Viterbi voice-leading, walking bass, humanizer math), and any well-scoped implementation that still involves real judgment (pydantic schemas, YAML loaders, serializers, CLI wiring, tests written from a plan).
  - `sonnet` (Sonnet 5) is permitted **only when the task is truly trivial** — mechanical, fully specified, with no design latitude (e.g. a rote rename, a boilerplate stub from an exact template, a one-line fixup, a mechanical test transcription from an explicit line-by-line plan).
  - When in any doubt about whether a task clears the "truly trivial" bar, use `opus`. The cost of an under-powered subagent on real work far exceeds the token savings.
- **Parallel dispatches only on disjoint file sets.** Two agents editing the same file concurrently will clobber each other. Otherwise serialize.

## Session workflow

### 0. Orient

- Read `ROADMAP.md`, `plans/PROGRESS.md` (including its handoff block), `plans/CAVEATS.md`, and the target `PHASE_N.md` in full. Skim the upstream PHASE docs whose contracts this phase consumes. Check `git log` for actual repo state — trust the code and the docs over memory.
- Determine from PROGRESS.md whether this is a **fresh phase** or a **resume mid-phase** (an approved chunk plan already exists — honor it; do not re-plan approved chunks).
- State back to me, briefly: the session's scope, the contracts it consumes and produces, what is already done, and what this session will attempt. Then begin step 1.

### 1. Scope & research → session plan — **USER APPROVAL GATE**

- Dispatch subagents as needed: research a design area's implementation approach, explore existing code, map the PHASE doc's requirements to a file layout, debate decompositions. (Resuming mid-phase with an approved chunk plan, this step is usually light.)
- **Size the work.** If the phase won't fit one session, split it into named chunks with pinned boundaries and record the chunk plan in PROGRESS.md. Known seams: PHASE_5 splits roughly loaders/foundations → arrangement → generators/walker/voicing → orchestrator+Serializer+milestone; PHASE_8 spans several sessions with hard ordering tooling → reference-pack refinement → new packs (chill_lofi → blues → fusion_jazz).
- Write the session plan to `plans/sessions/SESSION_NN.md` (NN = next implementation-session number from PROGRESS.md). It must contain: session scope (and what is explicitly out of scope), the ordered task list with per-task file scopes, model assignment, the PHASE-doc sections each task implements, and the verification each task must pass. This file is what implementer subagents will be pointed at — write it for a reader with no other context.
- Update PROGRESS.md, then **present the plan to me and stop. Do not dispatch any implementation agent until I approve.** Incorporate feedback into the plan file before proceeding.

### 2. Implement — per-task loop

For each task in the approved plan, in order (parallel only when file scopes are disjoint):

1. **Implement** — dispatch an implementer with a self-contained prompt (task, plan file, PHASE-doc sections, files, invariants, expected report). Tests are part of the task, not an afterthought.
2. **Verify mechanically** — run the gates yourself and read the output:
   `uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy`
3. **Review** — dispatch an `opus` reviewer scoped to *this task's* diff: are the tests real and meaningful (not vacuous, not tuned to pass), does the code match the pinned design section, is quality acceptable, were any contracts violated?
4. **Fix loop (bounded)** — for each substantive finding, dispatch a fix agent, then re-run the gates and re-review the fix. **Maximum 2 fix cycles per task**; if a finding survives, stop and escalate to me with the evidence.
5. **Commit at the verified gate** — once gates and review pass, commit the task's work with a descriptive message. Update PROGRESS.md **immediately** (task done, commit hash).

### 3. Whole-implementation review

After all tasks in the session's scope are done:

- Dispatch **fresh** `opus` review agents over the session's entire implementation (not per-task diffs) — separate lenses in parallel: correctness/logic bugs, contract compliance against the PHASE doc, test quality and coverage of the DoD, code quality/simplification.
- For each finding: dispatch a **validation** agent to confirm it's real before anything is changed; confirmed findings get a fix agent + gate re-run, same 2-cycle bound.
- Check the applicable **Definition of Done** items from `PHASE_N.md` one by one, with evidence (test names, fixture paths, command output). On the **final session of a phase**, run the review across all of the phase's chunks together and complete the full DoD checklist.
- Finish with all gates green; commit.

### 4. Close out

- Update PROGRESS.md: statuses, session log entry, and a fresh **handoff block** stating exactly where the next session starts.
- Add CAVEATS.md entries for any deviation (see below). Commit the doc updates.
- Report to me: what was built, gate evidence, DoD status, caveats logged, and what the next session should do.

## Documentation discipline

- **PROGRESS.md is the source of truth, not your context.** Update it at every task completion and step transition — assume the session could die at any moment and the next orchestrator must resume losslessly from disk.
- **CAVEATS.md** gets an entry whenever implementation deviates from the pinned design — a contract adjusted, a printed sample found wrong (arbitration rule 2), an algorithm ambiguity resolved, scope moved between sessions. Use the entry format defined at the top of that file. Bug fixes in your own new code are not caveats; divergences from the PHASE docs are.
- PHASE-doc amendments follow the arbitration protocol: amend the doc in the same commit as the recomputed fixture, re-verify downstream chained samples, and get my sign-off first.

## Escalation — stop and ask me when

- A design genuinely requires breaking a ROADMAP invariant or amending a PHASE doc (sign-off required).
- Algorithm text is genuinely ambiguous (arbitration rule 1) — resolve explicitly with me, never by tweaking code toward a printed number.
- A fix loop is exhausted, or the session's scope is growing beyond the approved plan.

## Ground rules

- **Never `git push`.** Commit freely at verified gates; pushing is mine.
- Never claim a gate passes without having run it and read the output this session.
- Determinism is non-negotiable: no wall-clock, no unseeded randomness outside `trackgen.seeds` (TID251 enforces the import layer; don't work around it).
- Respect pinned contracts. When the design and convenience disagree, the design wins — or gets amended with sign-off, never silently.
