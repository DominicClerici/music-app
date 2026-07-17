# SESSION_10 — Phase 6, Chunk 1: The Transition engine (stage 6)

**Phase:** 6 — Transitions, Variation & Humanization. **Chunk:** 1 of 3 (fresh phase).
**Design source (binding):** `plans/PHASE_6.md` §3 (the stage), §4 (the `transitions.yaml`
schema), §7.1/§7.2 (worked draw narratives), §10 (amendments), §11 (DoD), §12 (invariants).
Read those sections in full before implementing — this file is a router, not a substitute.

Implementer subagents start with **zero context**: every task prompt points at the exact
PHASE_6 sections, the exact source files, and the exact expected report. This file is what
they are pointed at.

---

## 1. Chunk scope

Build **all of stage 6** — the note-structural Transition engine — and its pack file, end to
end, with goldens and synthetic fixtures. Stage 6 signature (PHASE_6 §3):

```
transitions(phrases, form, chords, arr, plan, pack) -> Phrase[]
```

Three sub-passes in pinned order (§3): **6a ending HOLD → 6b boundary devices → 6c mutation**.

**In scope (Chunk 1):**

- The `transitions.yaml` pack-file schema + loader (TR1–TR7), PT12 enforcement, both reference
  files, fill-window computation + caching (§4, §3.3, §10.6).
- 6a: the HOLD ending note-structure transform for every `close` value (§3.6).
- 6b: boundary taxonomy (§3.1), deterministic device assignment (§3.2), fill selection/sizing/
  rendering (§3.3), the `stop` device (§3.4), the dormant `dropout` device (§3.5), the crash+kick
  entered-downbeat rule (§3.7 head), RNG discipline (§3.8 devices stream).
- 6c: the five mutation operators on 2-bar drum / 8-bar comping units, per-unit sub-streams,
  no-op degradation (§3.7 mutation, §3.8 mutate stream).
- The new tags `"fill"`/`"crash"`/`"var"`/`"hold"` (§3.9).
- Device-narrative goldens (§7.1/§7.2: exact draw counts + fired-op lists **verbatim**, incl. the
  four documented no-ops), rendering goldens (§7.1 fill bar 3, crash±kick, one mutated unit per
  operator class, HOLD both examples), synthetic fixtures (stop-odds, breakdown dropout, rung-1-only
  fallback), and stage-6 determinism (draw counts + per-unit/per-boundary isolation).
- Crash-voice→track plumbing needed to *produce* crash Phrases (`crash` in the voice→track map and
  drum track order).

**Explicitly out of scope (later chunks):**

- The entire Humanizer / stage 7 — swing, `feel.yaml`, offsets, jitter, accent, legato, ritard
  tempo curve (**Chunk 2**, DoD 2/5/6). Chunk-1 goldens assert **pre-humanization** note structure.
- Pipeline wiring: threading `tempoEvents` through the orchestrator→serializer, deleting the stubs,
  making `generate_track` call the real stages, adding `crash` to the Serializer `_EMIT_ORDER`/
  `_STUB_MIX` + a stub-timbres `crash` entry, re-blessing the whole-document goldens, the milestone
  listening check (**Chunk 3**, DoD 10). Chunk 1 tests `transitions()` directly on `Phrase[]`, not
  through `serialize()`.
- Whole-phase property matrix + full §11 DoD 1–11 sign-off + amendment audit (**Chunk 3**, DoD 9/11).
  Chunk 1 lands the *stage-6* property tests (DoD 9 subset: legal fill bars, no groove event inside a
  rendered window, crash suppression for postchorus/breakdown, non-drum `midi` untouched by stage 6,
  backbeat-class snare never removed/moved by mutation). The V1–V8 and combined-stage sweeps are Chunk 3.

**DoD targeted this chunk:** **1** (loader), **3** (device narratives), **4** (rendering goldens),
**8** (synthetic fixtures), plus the stage-6 slices of **7** (determinism) and **9** (properties).

---

## 2. Key integration facts (read before implementing)

Grounded in the current tree (verified this session), so implementers don't rediscover them:

1. **Phrases are frozen** (`ir.py`: `Phrase`/`PhraseNote` are `ConfigDict(frozen=True)`). Stage 6
   cannot mutate in place — it **rebuilds** Phrases (`model_copy(update=...)` or fresh construction)
   with new `notes` lists. "In place" in PHASE_6 §2 is conceptual.
2. **Phrase granularity is one per (track, section)** (`generators.py`): pitched roles emit one
   Phrase per section with `track_id == role`; **drums emit one Phrase per active voice-track per
   section** (`kick`/`snare`/`hats`/`ride`/`tom_*`/`perc`). A fill in a fill bar therefore edits the
   drums Phrases of *one section* across *several voice-tracks*. Locate the section by `start_tick`/
   `end_tick` on the Phrase (bar = tick // 1920).
3. **Fill instantiation reuses existing helpers** — do **not** duplicate: the drum voice→track map
   (`generators._VOICE_TRACK`) and default durs (`generators._DEFAULT_DUR`), and the §3.4 velocity
   shift (`dynamics.apply_velocity(event.velocity, plan.budgets.dynamics_base)`). Fill events are
   `DrumEvent`s from the selected `kind: fill` pattern; instantiate them exactly as `_generate_drums`
   does (velocity shift applied — §3.3 says "the PHASE_5 §3.4 velocity shift applied"), then tag
   `"fill"`. Crash velocities are the exception: **absolute**, no §3.4 shift (§3.7, §2 velocity row).
4. **The `crash` voice is currently dropped** (`generators.py:219` `if event.voice == "crash":
   continue`; `_VOICE_TRACK` has no `crash` key). Stage 6 is the first crash producer. Add `crash ->
   "crash"` to `_VOICE_TRACK` and `"crash"` to `_TRACK_ORDER` (this chunk — the producer side).
   `_DEFAULT_DUR`/emission of authored crashes in mains stays dropped (mains never author crash);
   only stage-6-added crashes (dur 1440, §3.6/§3.7) reach the `crash` track. The Serializer
   `_EMIT_ORDER`/`_STUB_MIX` + stub-timbres crash entry are **Chunk 3** (serialization side).
5. **`transitions.yaml` is a pack file** → follow the `timbres.yaml` precedent: models in
   `packs/models.py`, loaded by `packs/loader.py` into a new `StylePack.transitions` field (additive,
   like `StylePack.timbres`). Fill-window computation (§3.3) is a property of the drum `kind: fill`
   `PatternEnvelope` (needs its events + `length_ticks`); compute+cache at load, TR6/TR7 validate it.
6. **Draw discipline** (§3.8, PHASE_3 D13): `weighted_choice`/`randrange` only, integer weights,
   **draw iff ≥ 2 candidates/outcomes**, append-only order. RNG anchors are **verified faithful this
   session**: `derive(transitions,"devices")` = 11162692426947704816, `derive(transitions,"mutate")`
   = 2353238394870311228, `derive(mutate,"drums")` = 10947905152221053268 — all match §3.8. So the
   §7 draw *counts* (pop 14/38/9, jazz 10/32/11) and fired-op lists are the **arbitration-risk**
   surface (like C-09): T4 is the independent arbiter and escalates on divergence, never tunes.
7. **Boundaries/energy** come from `SongForm.sections` (`start_bar`, `length_bars`, `energy`,
   `phrases`, `ending`). The final chord anchor `T_last` (§3.6) = `start_tick` of the last
   `"final"`-tagged `ChordEvent` in `HarmonicPlan.chords` (PHASE_4 §5.5 guarantees it exists,
   degree-1-rooted). Section rung for fill resolution comes from `ArrangementPlan` `intensity`.

---

## 3. Module layout (proposed; T1 may refine at implementation depth)

New package `src/trackgen/transitions/`:

- `packs/models.py` + `packs/loader.py` (T1) — `TransitionsSpec` model + `StylePack.transitions` +
  fill-window compute/cache + TR/PT12 validation. Reference YAML in `styles/{pop_rock,jazz}/transitions.yaml`.
- `transitions/ending.py` (T2) — 6a HOLD (`_hold_ending`).
- `transitions/devices.py` (T2) — 6b: taxonomy, assignment, fill select/size/render, stop, dropout, crash.
- `transitions/mutation.py` (T3) — 6c: the five operators + per-unit driver.
- `transitions/stage.py` (T2 skeleton, T3 wires 6c) — `transitions(...)` orchestrating 6a→6b→6c.
- `transitions/__init__.py` — re-export `transitions`.

Tests: `tests/test_transitions_pack.py` (T1), `tests/test_transitions_stage.py` (T2/T3 mechanism),
`tests/test_transitions_goldens.py` (T4 narratives+rendering), `tests/test_transitions_fixtures.py`
(T4 synthetic), `tests/test_transitions_determinism.py` (T4).

---

## 4. Task list (serial T1 → T2 → T3 → T4, then T5)

Serial: T2 consumes T1's loaded model + windows; T3 wires into T2's `stage.py`; T4 golden-arbitrates
the whole engine. No safe parallel split (the engine modules share `stage.py`).

| # | Task | Model | Files (scope) | PHASE_6 §§ | Verification |
| --- | --- | --- | --- | --- | --- |
| T1 | `transitions.yaml` schema + loader + reference content + fill windows | opus | `packs/models.py`, `packs/loader.py`, `styles/{pop_rock,jazz}/transitions.yaml`, `tests/test_transitions_pack.py` | §4.1–§4.3, §3.3 window, §10.5/§10.6 | gates; TR1–TR7 each ≥1 rejection fixture; both refs load clean; windows cached + TR6/TR7 asserted; PT12 enforced on both packs |
| T2 | Stage-6 engine: 6a HOLD + 6b devices (taxonomy/assignment/fill/stop/dropout/crash) + `stage.py` | opus | `transitions/{ending,devices,stage,__init__}.py`, `generators._VOICE_TRACK`/`_TRACK_ORDER` (crash), `tests/test_transitions_stage.py` (device/ending units) | §3.1–§3.6, §3.7 crash, §3.8 devices, §3.9 | gates; mechanism units for taxonomy, assignment table, selection+fallback, window sizing, stop, dropout, crash±kick; frozen-Phrase rebuild verified |
| T3 | Mutation pass 6c: five operators + per-unit sub-streams + no-op degradation | opus | `transitions/mutation.py`, one-line `stage.py` wire, `tests/test_transitions_stage.py` (mutation units) | §3.7 mutation table, §3.8 mutate | gates; one unit test per operator incl. no-op path; per-unit isolation; safety (no backbeat/beat-1/ornament-only removal) |
| T4 | Goldens (independent transcriber / arbiter): device narratives + rendering + synthetic fixtures + determinism | opus | `tests/test_transitions_goldens.py`, `tests/test_transitions_fixtures.py`, `tests/test_transitions_determinism.py`, synthetic pack fixtures under `tests/` | §7.1, §7.2, §3.4/§3.5 fixtures, §11.3/4/7/8, DoD-9 subset | gates; §7 draw counts (14/38/9, 10/32/11) + fired-op lists verbatim; fill bar 3 note-for-note; crash±kick both; per-op mutated units; HOLD both; 3 synthetic fixtures; stage-6 property subset |
| T5 | Whole-chunk 2-lens review + DoD 1/3/4/8 checklist + close-out | orchestrator | PROGRESS.md, CAVEATS.md | §11 | 2 fresh opus lenses (correctness/contract + test-quality/DoD); validate→fix (2-cycle bound); gates green; PROGRESS/CAVEATS updated |

### Per-task detail

**T1 — schema + loader + reference content + fill windows.**
- Implement `TransitionsSpec` (and nested `PhraseFill`/`Stop`/`Crash`/`Mutation` models) per the §4.1
  field-level schema; strict (`extra="forbid"`, pydantic) → TR4. Add `StylePack.transitions:
  TransitionsSpec | None` and load `transitions.yaml` in `packs/loader.py` (mirror `timbres.yaml`).
- Validation TR1–TR7, **each with ≥1 non-vacuous rejection fixture** (§11.1): TR1 (phraseFill odds
  two ints ≥1; crash.velocity floats ∈[0,1], lo≤hi), TR2 (stop.enabled bool; odds present iff enabled,
  two ints ≥1), TR3 (mutation keys ⊆ {drums,comping}; each table non-empty with `none`; weights ints
  ≥1; op names from the §3.7 vocabulary **for that role** — `hat_lift`/`drop_ornament`/`kick_pickup`
  for drums, `anticipate`/`drop_hit` for comping; single-entry `none`-only legal), TR4 (unknown key
  rejected), **TR5=PT12** (cross-file: the pack's drum bank has ≥1 **ungated** `kind: fill` pattern),
  TR6 (every fill pattern's computed window non-empty), TR7 (every fill pattern has ≥1 event with
  `pos ≥ lengthTicks − 960` — reaches the barline).
- **Fill window** (§3.3): `window = [beatFloor(first_event_pos), lengthTicks)` where `beatFloor`
  rounds down to the containing beat (480). Compute + cache per drum `kind: fill` pattern at load;
  the reference windows are `pr_dr_f1`/`pr_dr_f2` → `[960,1920)` (first event 1200 floors to 960),
  `jz_dr_f1` → `[960,1920)`. Assert these exact windows in the load test.
- Author both reference files **verbatim** from §4.2 (pop) and §4.3 (jazz). Both load clean; PT12
  passes against the real `pop_rock`/`jazz` drum banks.
- **Expected report:** files touched, the `TransitionsSpec` field list, the TR→fixture mapping table,
  computed windows for all three reference fills, confirmation PT12 fires on both packs, gate output.

**T2 — stage-6 engine (6a + 6b).**
- `stage.py`: `transitions(phrases, form, chords, arr, plan, pack) -> list[Phrase]` running
  6a→6b→(6c hook, filled by T3). Rebuild frozen Phrases; preserve existing `"push"`/`"ghost"` tags.
- **6a HOLD** (`ending.py`, §3.6): find `T_last`; pitched roles (bass/comping/pads) — notes attacking
  at `T_last` extend to the final section `end_tick` (`duration_ticks = end_tick − ticks`), `+0.05`
  velocity (clamp ≤1.0), tag `"hold"`; notes attacking after `T_last` deleted. Drums — delete all
  events at/after `T_last`; add a `crash` (dur 1440) **and** a `kick` at `T_last`, velocity = the §3.7
  crash formula at the **final section's own energy** `+0.05`, tag `"hold"`. Applies to every `close`
  (cold/fade/ritard identical here; ritard's tempo curve is Chunk 2). No boundary/fill/mutation touches
  bars at/after `T_last`'s bar.
- **6b devices** (`devices.py`): boundary taxonomy §3.1 (section boundaries = adjacent pairs, fill bar
  = last bar of section i; interior phrase boundaries = each non-section-start phrase start, fill bar =
  bar before). Device assignment §3.2 by **entered** section type (breakdown→dropout, postchorus→none,
  else fill-or-stop). Stop eligibility §3.4 (entered rung 4 **and** entered energy > outgoing **and**
  pack `stop.enabled` → draw `[stop,fill]` at `stop.odds`). Interior boundaries: draw include/exclude
  at `phraseFill.odds` (always 1 draw). Fill **selection** §3.3 (destination rung for section, current
  rung for phrase; nearest-down-to-1-then-up-to-4 fallback; `weighted_choice` iff ≥2). **Sizing**:
  section fills render full window; phrase fills render `window ∩ [lengthTicks−960, lengthTicks)`.
  **Rendering**: on drums only, delete drum-voice events whose tick falls inside the bar-aligned
  rendered window; instantiate the fill's events (velocity shift, voice→track) tagged `"fill"`; other
  roles untouched. **Stop** §3.4 (all roles: delete notes attacking in `[enteredTick−480, enteredTick)`,
  truncate sustains into it). **Dropout** §3.5 (breakdown: truncate all roles' sustains at the entered
  downbeat; no fill/crash). **Crash rule** §3.7 head: after each section-boundary fill/stop, add `crash`
  (dur 1440) at the entered downbeat, velocity `round3(lo + energy×(hi−lo))` from `crash.velocity` and
  **entered** energy; add `kick` iff none attacks there (double-hit guard); both tag `"crash"`; crash
  velocity absolute (no §3.4 shift).
- **RNG** §3.8: one `derive(transitions,"devices")` RNG consumed in boundary timeline order; per
  boundary `[stop-vs-fill iff eligible]` then `[include iff phrase]` then `[fill selection iff ≥2]`.
  6a and crash are draw-free.
- Crash producer plumbing: add `crash -> "crash"` to `generators._VOICE_TRACK`, `"crash"` to
  `_TRACK_ORDER`. (Serializer side is Chunk 3 — note in the report, don't touch `serialize.py`.)
- **Expected report:** files, the 6a/6b control flow, how frozen Phrases are rebuilt, the devices-RNG
  draw order, mechanism tests written, and any §3 point that required an interpretation (flag for T4).

**T3 — mutation 6c.**
- `mutation.py` per §3.7: units — drums **2-bar** from each section start, comping **8-bar** from each
  section start (last may be short); units only where the role is `active` (ArrangementPlan). One draw
  per unit from `pack.transitions.mutation.<role>` (authored order; draw iff ≥2 entries) on
  `derive(derive(derive(transitions,"mutate"),role),f"bar:{unitStartAbsBar}")`. Operator applies **or
  degrades to a documented no-op**. Operators never target events tagged `"fill"`/`"crash"`/`"hold"`,
  events in a stop window, or events at/after the final chord event's bar.
- The five operators exactly per the §3.7 table (`hat_lift`, `drop_ornament`, `kick_pickup` = drums;
  `anticipate`, `drop_hit` = comping). `anticipate` preserves pitches (shifts `ticks` −240, truncates
  the previous overlapping comping note, no-op if any comping note attacks in `[new,old)`). `drop_hit`
  requires the bar to contain ≥2 comping attacks (guard against silent bars). Tag added/modified events
  `"var"`.
- Wire `mutate(...)` into `stage.py` as the final 6c pass (one-line call; T2 leaves the hook).
- **Safety invariants to unit-test** (§3.7): no operator removes a backbeat snare, a beat-1 event, or a
  non-ornament note; none touches `midi`; each unit changes ≤1 event. One test per operator including
  its no-op path; per-unit RNG isolation (regenerating one unit reproduces its draw alone).
- **Expected report:** files, the per-unit driver + sub-stream derivation, each operator's target
  rule + no-op condition, the safety tests, and any §3.7 interpretation (flag for T4).

**T4 — goldens (independent transcriber + arbiter).**
- Drive the **real** chained pipeline at seed `1ps9wxb` / master 3735928559 (interpret→…→generate→
  transitions), both worked examples. Transcribe goldens from PHASE_6 **§7 text**, not from the code's
  output (doc-transcribed, per PHASE_5 T4 discipline). **On any divergence: do NOT tune** — mark
  `strict xfail` + escalate to the orchestrator with a trace, exactly like C-09. The §7 draw
  counts/op-lists are derived samples; the algorithm text wins.
- **Device narratives** (§11.3): pop **14 devices + 38 mutation + 9 comping** draws; jazz **10 + 32 +
  11**; the fired-op lists **verbatim**, including the four documented no-ops (pop `drop_ornament`@54;
  jazz `drop_ornament`@4/@54 — all no-ops; and the rest). Counting-RNG shims per stream/sub-stream.
- **Rendering** (§11.4): pop fill bar 3 note-for-note (§7.1: hats@960/1440 deleted; fill snares
  960/1200/1440/1680 at velocities 0.66/0.74/0.82/0.91; kick@0 + hats@0/480 survive); a crash+kick
  entry **with** an existing kick (pop bar 12) and **without** (jazz bar 12, kick added); one mutated
  unit per operator class (incl. pitches-preserved `anticipate`, the ≥2-attacks `drop_hit` guard);
  HOLD for both examples (extensions, deletions, +0.05 bumps, tags — pop `T_last`=144000 crash vel
  1.000; jazz `T_last` bar 63 crash vel 0.553).
- **Synthetic fixtures** (§11.8, DoD 8): a stop-heavy odds pack exercising §3.4 stop rendering
  end-to-end; a `breakdown` form exercising §3.5 dropout; a fill bank with only rung-1 fills exercising
  the fallback chain both directions. Build minimal synthetic packs/forms under `tests/`.
- **Determinism** (§11.7 stage-6 slice): repeated-run identity through stage 6; the exact per-stream
  draw counts via counting shims; per-boundary and per-unit isolation.
- **Property subset** (DoD 9, stage-6 only): fills only in legal fill bars; no drum groove event inside
  a rendered window; crash suppression honored for postchorus/breakdown; non-drum `midi` untouched by
  stage 6; backbeat-class snare (vel ≥0.7 at back2/back4) never removed/moved by mutation.
- **Expected report:** every golden with its asserted values; **any divergence found + whether tuned
  (must be "no — xfail+escalated")**; the fixtures built; property matrix dims; gate output.

**T5 — whole-chunk review + close-out (orchestrator).**
- Two fresh **opus** review lenses in parallel over the whole Chunk-1 diff: (a) correctness/contract
  (does the engine match §3/§4 clause-by-clause; frozen contracts untouched; invariants 1–5; RNG
  discipline), (b) test-quality/DoD (are 1/3/4/8 + the stage-6 slices of 7/9 PROVEN with real,
  doc-transcribed, non-vacuous tests).
- Validate each finding before fixing; confirmed findings get a fix agent + gate re-run (2-cycle bound).
- Check DoD 1/3/4/8 with evidence (test names, fixture paths, command output). Update PROGRESS.md +
  CAVEATS.md; commit doc updates. Write the Chunk-2 handoff.

---

## 5. Gates & discipline

- Four gates green before every commit: `uv run pytest` · `uv run ruff check .` ·
  `uv run ruff format --check .` · `uv run mypy`. Run pytest with an extended timeout (~2 min suite).
- Determinism (invariant 5): no `random`/wall-clock outside `seeds.py` (TID251); the transitions
  modules import no entropy source — draws only via injected `Rng`/`weighted_choice`.
- Golden-value arbitration (ROADMAP §3): algorithm text wins over §7 printed samples; on divergence,
  xfail + escalate + (with sign-off) amend the doc alongside the recomputed fixture in one commit, log
  a CAVEAT. **Never** tune code to a printed number.
- Every subagent dispatch sets `model` explicitly (opus for all real work here; no Fable).
- Commit at each verified task gate; update PROGRESS.md immediately with the commit hash.

## 6. Open interpretation points to watch (candidate CAVEATs / arbitration)

- The §7 draw counts/op-lists are the arbitration-risk surface (C-09 precedent). T4 arbitrates.
- **Beat class of the `kick_pickup`/`hat_lift` targets** and the exact "last X in the unit" tie-breaks
  (§3.7) — T3 pins a reading; T4's goldens are the arbiter if a fired-op position diverges.
- **C-10** (latent coincident same-voice drum de-dup): Chunk 1 authors fills/crashes in `parts`/
  `transitions` — a natural guard point. If fill rendering + crash addition can produce two same-voice
  drum events at one tick, decide whether to de-dup here or leave latent; log the decision.
- **Deferred Phase-5 cleanup** (`_fold_into_lane`/`_third_pc`/`_fifth_pc` dup between `walker.py`/
  `retarget.py`): out of scope this chunk unless it obstructs; note only.
