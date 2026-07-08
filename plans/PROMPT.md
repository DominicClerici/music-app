# Phase Design Session Prompt

You are being invoked as: **"PROMPT.md — this is session N"**, where N names a phase in `ROADMAP.md`. Your job this session is to take that phase from a roadmap sketch to a complete design document, `PHASE_N.md`, through deep research and collaborative brainstorming with me. This is a **design session, not an implementation session** — no application code gets written.

## Project context

We are building a backend pipeline that algorithmically composes complete, structured, instrumental backing tracks from structured user parameters (style family, mood, tempo, key, role flavors, max length, seed) and emits a `TrackDocument` — a Tone.js-oriented JSON document a browser client plays. Tracks have real song structure (intro/verse/chorus/bridge/outro), a rhythm-section arrangement (drums, bass, comping, pads) with fills and transitions, and synthesized instrument tones matched to mood. Tracks deliberately leave melodic space for the user to play over.

The architecture is a **layered hybrid**: authored pattern vocabulary for the groove skeleton, theory rules for form/harmony/voicing/arrangement, seeded weighted-random selection for variety, algorithmic humanization on output. The pipeline is nine stages (Interpreter → Form → Harmony → Arrangement → Parts → Transitions → Humanizer → Sound design → Serializer), each with a defined intermediate representation. See `ROADMAP.md` §3 for the full diagram and §4 for the phase list.

**Binding invariants** (ROADMAP.md §3): style packs are data, not code; rhythm is stored separately from pitch and retargeted to chords at render time; hierarchical seeds; the soloist owns the register above ~C5; the pipeline is deterministic given params + seed. If your phase's design genuinely needs to break one, stop and propose a ROADMAP.md amendment — never silently diverge.

## Session workflow

Follow these steps in order.

### 1. Orient

- Read `ROADMAP.md` in full.
- Read every completed `PHASE_*.md` — earlier phases define contracts yours must consume or produce.
- Identify the target phase from my instruction. State back, briefly: the phase's scope, its inputs (upstream contracts it consumes), its outputs (contracts it must produce for downstream phases), and what ROADMAP.md already decided about it. Ask me to confirm before going further.

### 2. Research deeply

Before proposing any design, research the phase's specific domain — spawn parallel research agents where useful, using the `opus` model exclusively (never `fable-5`). Think hard; do not design from vibes. Examples of the expected depth:

- Phase 3 (Form): how real songs in each style family are structured, bar-count statistics, energy-curve conventions.
- Phase 5 (Parts): drum pattern representation formats, walking-bass construction rules, comping voicing practice, how Band-in-a-Box/Yamaha/MMA solved each.
- Phase 7 (Sound design): Tone.js synthesis recipes, timbre–emotion research, mixing conventions.

Summarize findings for me before moving on — I want to see what the research says, not just its conclusions.

### 3. Brainstorm collaboratively

- Propose 2–3 approaches for each significant design question, with trade-offs and a clear recommendation.
- Ask me questions **one at a time**; prefer concrete multiple-choice over open-ended.
- Work at the right altitude: more concrete than ROADMAP.md — pin down data structures, algorithms, rule tables, and contracts — but still a design, not code. Pseudocode and JSON schema sketches are appropriate; source files are not.
- Where the phase is large (Phase 5 especially), propose a decomposition first and tackle sub-areas in sequence.

### 4. Deliver PHASE_N.md

Write `PHASE_N.md` at the repo root containing:

- **Scope** — what this phase covers and explicitly does not.
- **Contracts** — the exact data structures this phase consumes and produces (field-level, with examples).
- **Design** — the full design: algorithms, rule tables, data formats, worked examples (e.g., "here is the SongForm for a 3-minute happy pop/rock track").
- **Decisions** — every decision made this session, with rationale and the alternatives rejected.
- **Open questions** — anything deferred, explicitly listed with what resolving it depends on.
- **Definition of done** — what a future implementation session must demonstrate for this phase to be considered built (including testability: golden seeds, validators, fixtures).

Before presenting the final document: self-review it for placeholders ("TBD" only allowed inside Open Questions), internal contradictions, ambiguous requirements, and consistency with ROADMAP.md and prior PHASE docs. Fix issues inline.

### 5. Close out

- Ask me to review `PHASE_N.md`; iterate until I approve.
- If the session changed anything roadmap-level, update `ROADMAP.md` (decisions log and/or the phase list) in the same commit, and say so explicitly.
- Commit the new document(s).

## Ground rules

- Structured parameters only — never design free-text/LLM-prompt inputs.
- The browser player is out of scope in every session; only the output contract matters.
- Musical believability and soloist space outrank cleverness; when research and elegance disagree, follow what shipping products (Band-in-a-Box, Yamaha styles, iReal Pro, JJazzLab, MMA) actually do.
- Respect earlier phases' contracts. If one is wrong, propose amending that PHASE doc — with my sign-off — rather than working around it.
