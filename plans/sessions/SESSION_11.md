# SESSION_11 — Phase 6, Chunk 2: The Humanizer (stage 7)

**Phase:** 6 — Transitions, Variation & Humanization. **Chunk:** 2 of 3 (resume mid-phase;
the 3-chunk split is already approved — do NOT re-plan it).
**Design source (binding):** `plans/PHASE_6.md` §5 (the Humanizer, §5.1–§5.8), §5.7 (ritard),
§6 (pipeline-signature change), §7.1/§7.2 (worked humanizer narratives), §8 (D9–D16 rationale),
§10 (amendments), §11 (DoD), §12 (invariants). Read those in full before implementing — this
file is a router, not a substitute.

Implementer subagents start with **zero context**: every task prompt points at the exact
PHASE_6 sections, the exact source files, and the exact expected report. This file is what
they are pointed at.

---

## 1. Chunk scope

Build **all of stage 7** — the note-count-preserving Humanizer — end to end, with unit tests,
golden excerpts, and the ritard tempo curve. Stage-7 signature (PHASE_6 §5, §6):

```
humanize(phrases, form, plan) -> (Phrase[], tempoEvents)
```

`tempoEvents` is `list[schema.document.Tempo]` (`{ticks, bpm}`, absolute ticks), the **ritard
events only** — the Serializer prepends the tick-0 base tempo (that wiring is Chunk 3, §6).

**In scope (Chunk 2):**

- `src/trackgen/humanize/feel.yaml` — the engine feel data, matching §5.3 **exactly** (both
  `offsetsMs` profiles `swung`/`straight`, `jitterMs`, `accent`, `velJitter`, `bassLegato`).
- Its loader + validator, module-local like `interpreter/moods.yaml` (§5.3, D11): frozen pydantic
  models; validator caps **offsets ≤ 25 ms, jitter ≤ 10 ms, |accent| ≤ 0.05**, each with a
  rejection fixture (DoD 2).
- The note-count-preserving engine (§5.1–§5.6): beat classes (§5.1), swing (§5.2, tick-domain,
  offbeat-only, both subdivisions, gap-preserving stretch, straight-pack no-op), ms offset maps
  (§5.3, `ticksPerMs` at both reference tempi), triangular timing jitter (§5.4, the pinned `tri`
  helper, draw-skip at `w == 0`), velocity accent + `dynamicsRange`-scaled jitter (§5.5), bass
  legato (§5.6, both bass modes, final-note exemption), op order **swing → offset → timing jitter
  → accent → velocity jitter → duration** with float-ms math and one terminal half-even rounding,
  the `ticks ≥ 0` / `ticks + dur ≤ song end` clamps, and the per-phrase `(ticks, midi)` re-sort
  (§5).
- RNG discipline (§5.8): per-`(role, absBar)` sub-streams `derive(derive(humanize, role),
  f"bar:{absBar}")`, drums role covering all its voice-tracks, within-bar note order
  `(gridTicks, trackId, midi|-1)`, per-note draw order (timing 2 iff `w≥1`, then velocity 2 iff
  `W≥1`); deterministic sub-passes consume nothing.
- The ritard renderer (§5.7, D15): the Friberg–Sundberg curve `v(x) = (1 + (v_end³−1)·x)^(1/3)`
  (q=3, v_end=0.65) over the tag region, per-8th sampling (per-16th final bar), 0.1-bpm rounding,
  consecutive-duplicate + equal-to-prevailing dedupe, tempo never 0; `cold`/`fade` emit **zero**
  events; the `fade` → `cold` alias (D7). Returns the `Tempo[]` second value of `humanize`.
- Goldens (independent arbiter — the §7.2 ritard table is the **arbitration-risk** surface):
  the jazz head-1 bar-0 **pre-jitter** excerpt (§7.2), the 39-event jazz ritard table (§7.2,
  endpoints + every value exact), stage-7 determinism (repeated-run identity, per-`(role,bar)`
  isolation, exact draw counts via a counting-RNG shim), and the **note-count-preservation**
  invariant on both full worked examples.

**DoD targeted this chunk:** **2** (feel data + validator), **5** (Humanizer stage), **6**
(ritard), plus the **humanizer slice of 7** (stage-7 determinism + note-count preservation).

**Explicitly out of scope (Chunk 3):**

- **All pipeline wiring.** The orchestrator still calls the STUB `humanize`/`transitions`
  (`pipeline/stubs.py`); Chunk 2 tests `humanize()` **directly on `Phrase[]`**, never through the
  orchestrator or `serialize()`. Chunk 3 deletes the stubs, calls the real stages, threads
  `humanize`'s 2nd return into `serialize`'s `header.tempos = [base] + tempoEvents`, adds the
  `crash` Serializer/timbre entries, re-blesses the whole-document goldens, and runs the milestone.
- The whole-phase property matrix (§11.9 V1–V8, combined-stage sweep, C5 ceiling under **both**
  stages) and full §11 DoD 1–11 sign-off + amendment audit (Chunk 3, DoD 9/10/11). Chunk 2 lands
  only the **stage-7-local** properties its goldens/units need.
- Any change to stage 6 (`transitions/`) or to `pipeline/`. Chunk 2 adds a new `humanize/` package
  and its tests **only**; it must not edit `stubs.py`, `orchestrator.py`, or `serialize.py`.

---

## 2. Key integration facts (read before implementing)

Grounded in the current tree (verified this session), so implementers don't rediscover them:

1. **Phrases are frozen** (`ir.py`: `Phrase`/`PhraseNote` are `ConfigDict(frozen=True)`). The
   Humanizer **rebuilds** phrases (`model_copy(update=...)` or fresh construction) — no in-place
   edits. It never adds/removes a note; it changes only `ticks`, `duration_ticks`, `velocity`,
   `tags` untouched (§5, D1). Mirror the Chunk-1 `_common.Builder` pattern if useful (optional).
2. **Drums key by `track_id`, not by note tags.** A drum `Phrase.track_id` is already the
   voice-track: `kick / snare / hats / ride / crash / tom_low / tom_mid / tom_high / perc`
   (`generators._TRACK_ORDER`). The §5.3 feel voice rows are `kick/snare/hats/ride/toms/crash/perc`
   — so map `tom_* → "toms"`, else identity. `hat_closed`/`hat_open` both live on the `hats`
   track (one row). **You do not need the C-11 internal voice tags** for the humanizer — the
   track_id carries the voice. Pitched roles key by `role` (`bass`/`comping`/`pads`).
3. **Beat class is computed from the PRE-swing grid tick** (§5.1): `class(tick % 1920)` →
   `0→down, 480→back2, 960→beat3, 1440→back4, else off`. "Swung notes keep the class of their
   straight position" — so capture each note's class **before** the swing pass moves it, and carry
   it through offset/accent. Op order is swing first, then the class-keyed passes.
4. **`ticksPerMs = 480 × tempoBpm / 60000`**, computed once per song (123 BPM → 0.984; 69 BPM →
   0.552). Offsets/jitter are ms (→ ticks via this factor); swing is tick-domain (scales through
   the tempo map automatically).
5. **RNG grouping is per `(role, absBar)`, across track phrases.** For drums, one RNG per
   absolute bar covers **all** drum voice-tracks; gather every note of the role whose
   `gridTicks // 1920 == absBar`, sort `(gridTicks, trackId, midi|-1)`, and draw in that order.
   `gridTicks` = the pre-humanization tick. `tri(rng, w) = rng.randrange(w+1) + rng.randrange(w+1)
   − w` (2 draws; `w == 0` consumes none). Per note: timing draws (2 iff `w ≥ 1`) **then** velocity
   draws (2 iff `W ≥ 1`). Deterministic passes (swing, offset, accent, duration, ritard) draw
   nothing. Seed: `derive(derive(stream_seed(master, overrides, "humanize"), role),
   f"bar:{absBar}")` (mirror `mutation.py`'s `derive` chaining and `Rng(...)` construction).
6. **Feel-table selection: swing-derived default** (§5.3). Neither v1 pack declares the PHASE_8
   `feelTable` selector (verified: only `jazz/interpreter.yaml` has `feel: swing8`). So select by
   `plan.swing`: `None → "straight"`, non-null → `"swung"`. pop_rock (no swing) → `straight`
   (§7.1); jazz → `swung` (§7.2). Handle a `feelTable` field if present (forward-compat), else the
   default — but do not invent one in the v1 pack files.
7. **Pads are jitter-exempt** (timing AND velocity jitter; `jitterMs.pads == 0` and the velocity
   pass skips pads) but **accent still applies** (§5.5). **Crash** has `jitterMs == 0` too (no
   timing jitter). Bass legato applies to bass only; drum-trigger durations and pads are
   duration-exempt (§5.6).
8. **The RNG anchors are live-verified** (this session, seed `1ps9wxb`, master 3735928559):
   `derive(master,"humanize") = 3899203291477031323`; `random.Random(humanize)` first-five
   `getrandbits(32) = [4182865326, 1966627690, 4223947781, 2670867691, 1704714080]`; first-five
   `randrange(100) = [58, 79, 50, 70, 90]`; `derive(derive(humanize,"drums"),"bar:0") =
   6949714659275352449`. These match §5.8 verbatim — the seed system is correct; a draw-count
   divergence is an engine bug, not a seed issue.
9. **Ritard emit type + tick convention** (§5.7): `tempoEvents: list[schema.document.Tempo]`
   (`{ticks: int≥0, bpm: float>0}`). Ticks are **absolute** (tag-start + rel). The §7.2 table is
   printed **relative** to the tag start (jazz tag = bars 60–64, ticks 115200–122880; first event
   rel +240 → absolute 115440). The tag region is `tagBars` bars ending at the final section's
   `endTick` (`tagBars: 0` → the section's last bar). `x = rel_tick / (tagBars_or_1 × 1920)`. The
   `x=0` sample equals base BPM and is dropped (equal-to-prevailing), so the first emitted event is
   rel +240. Confirmed against the curve this session: rel 240 → 68.47 → round1 68.5 ✓.

---

## 3. Task list

Serial **T1 → T2 → T3 → T4**, then **T5** (mirrors the Chunk-1 cadence — the passes chain, and
T2 is the humanize entry T3's ritard plugs into). All implementation tasks are **opus** (the
humanizer math — swing repositioning + gap-preserving stretch, `tri` distribution, ms→tick with
single terminal rounding, the Friberg–Sundberg curve — carries real judgment; the loader/validator
has design latitude in the cap fixtures). File scopes are disjoint from stage 6 / pipeline.

| # | Task | Model | Files (scope) | PHASE_6 §§ | Verification |
| --- | --- | --- | --- | --- | --- |
| T1 | **Feel data + loader + validator.** Author `humanize/feel.yaml` matching §5.3 exactly; frozen pydantic models (`FeelData` with `offsetsMs` profiles, `jitterMs`, `accent`, `velJitter`, `bassLegato`); `load_feel()` module-local like `moods.py`; validator caps offsets ≤ 25 ms / jitter ≤ 10 ms / \|accent\| ≤ 0.05, each a `ValueError`. Per-class scalar-or-map offset rows (a row may be a scalar `int` or a `{down,back2,beat3,back4,off}` map). | opus | `src/trackgen/humanize/__init__.py`, `src/trackgen/humanize/feel.py`, `src/trackgen/humanize/feel.yaml`, `tests/test_feel.py` | §5.3, §11.2 | four gates green; `load_feel()` returns the pinned values field-for-field; ≥1 rejection fixture per cap class (offset > 25 ms, jitter > 10 ms, accent > 0.05). Per-task opus review. |
| T2 | **The humanizer engine.** `humanize(phrases, form, plan) -> (Phrase[], tempoEvents)` entry (returns `[]` tempoEvents in T2 — T3 fills them). Beat classing (§5.1, pre-swing), swing (§5.2), offset maps (§5.3), the `tri` helper + timing jitter (§5.4), velocity accent + jitter (§5.5), bass legato (§5.6), op order + terminal rounding + clamps + re-sort (§5), RNG discipline (§5.8, per-`(role,absBar)`). Note-count-preserving. | opus | `src/trackgen/humanize/stage.py` (+ optional internal helpers e.g. `swing.py`/`feel_apply.py` under `humanize/`), `tests/test_humanizer.py` | §5.1–§5.6, §5.8, D9–D14 | four gates green; unit tests per §11.5 (swing offbeat-only + both subdivisions + gap-preserving stretch + straight no-op; offset both tables + ms→tick both tempi; `tri` bounds + `w==0` skip; accent map; `dynamicsRange` width `W`; bass legato both feels + final-note exempt); note-count preserved on a synthetic multi-role input. Per-task opus review. |
| T3 | **Ritard renderer.** `humanize`'s tempo-event pass: the §5.7 curve → sampled/dedup'd `Tempo[]`, wired as the 2nd return of `humanize`. `cold`/`fade` → `[]`; `fade` aliases `cold`. Absolute ticks; tag region per §5.7. | opus | `src/trackgen/humanize/ritard.py`, `humanize/stage.py` (wire the 2nd return only — no change to T2's note passes), `tests/test_ritard.py` | §5.7, §6, D15 | four gates green; §11.6 properties (monotone decreasing, never ≤ 0.5×base, first event > tag tick 0, none after the final sample; cold/fade zero events; fade==cold alias). Per-task opus review. |
| T4 | **Goldens (independent arbiter).** Over the real seed-`1ps9wxb` chained pipeline: the jazz head-1 bar-0 **pre-jitter** excerpt (§7.2 positions exact); the **39-event** jazz ritard table (§7.2, endpoints `+240→68.5 … +7560→45.5` + every intermediate value); stage-7 **determinism** (repeated-run identity; per-`(role,bar)` isolation; exact draw counts via a counting-RNG shim); **note-count preservation** on both full worked examples. **Arbiter protocol:** if any §7.2 value diverges from the faithful engine, mark `strict xfail` + **escalate — never tune** (C-09 precedent; the ritard table is the arbitration-risk surface). | opus | `tests/test_humanizer_goldens.py`, `tests/test_ritard_goldens.py` (+ any small fixture helpers under `tests/`) | §7.1, §7.2, §11.3(humanizer slice)/§11.5/§11.6/§11.7 | four gates green (zero unexpected xfail) OR a documented divergence escalated to the orchestrator with a trace. Independent-transcriber discipline: transcribe from the doc, do not snapshot the engine. Per-task opus review. |
| T5 | **Whole-chunk review + DoD + close-out.** 2-lens fresh-opus review (correctness/contract + test-quality/DoD) over the whole stage-7 diff; validate→fix (≤2 cycles); check DoD 2/5/6 + humanizer slice of 7 with evidence; update PROGRESS.md + any CAVEATS; commit. | orchestrator + opus reviewers | `plans/PROGRESS.md`, `plans/CAVEATS.md` (+ review-fix commits) | §11.2/§11.5/§11.6/§11.7 | all four gates green; both review lenses APPROVE (or nits fixed); DoD 2/5/6 PROVEN with named tests. |

**Parallelism:** none — serial T1→T2→T3→T4→T5. T2 and T3 both touch `humanize/stage.py`
(T3 wires the 2nd return), so they cannot run concurrently; T4 depends on all engine code.

---

## 4. Definition-of-Done mapping (this chunk)

- **DoD 2** (feel data + validator) — T1.
- **DoD 5** (Humanizer stage: swing/offset/jitter/accent/legato units + the §7.2 head-1 pre-jitter
  excerpt golden) — T2 (units) + T4 (excerpt golden).
- **DoD 6** (ritard: 39-event list exact + properties + cold/fade/alias) — T3 (properties) + T4
  (golden table).
- **DoD 7 (humanizer slice)** — stage-7 repeated-run determinism, per-`(role,bar)` isolation,
  draw counts, and note-count preservation on both examples — T4.

Deferred to **Chunk 3** (unchanged): DoD 9 whole-phase property matrix (V1–V8 + combined-stage +
C5 ceiling under both stages), DoD 10 milestone, DoD 11 amendment audit, and all wiring.

---

## 5. Escalation triggers (per PROMPT.md)

- Any §7.2 humanizer/ritard sample diverges from the faithful engine → **T4 escalates** (xfail +
  trace); resolve with the user via arbitration (amend the doc + recompute the fixture in one
  commit, or fix an engine bug) — **never tune code to a printed number** (C-09 precedent).
- The op order or a clamp forces a reading not pinned by §5/§D9 → escalate before choosing.
- A fix loop exceeds 2 cycles, or scope grows beyond this file → stop and surface to the user.
