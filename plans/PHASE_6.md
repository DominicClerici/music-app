# PHASE_6 — Transitions, Variation & Humanization

Designed 2026-07-07 (session 6). Status: **awaiting approval**.

This document pins pipeline stages 6 and 7 — the Transition engine (`Phrase[] → Phrase[]`, note-structural) and the Humanizer (`Phrase[] → Phrase[] + TempoEvent[]`, performance rendering) — end to end: the boundary taxonomy and device placement policy, fill selection/sizing/rendering, the crash/stop/dropout devices, the ending renderer (hold, ritard tempo curve, fade policy), the anti-repetition mutation operator set, the `transitions.yaml` pack-file schema, the humanizer's swing/offset/jitter/accent/duration model and its `feel.yaml` engine data, and the pipeline-signature change that carries ritard tempo events to the Serializer. It resolves PHASE_1 Q5 (PPQ 480 suffices) and disposes of PHASE_5 Q5 and Q9 as routed here.

Research base (session 6): Band-in-a-Box part-marker fill placement and shot/hold ending grammar; the Yamaha SFF/SFF2 section model via the Wierzba & Bedesem spec (Fill In AA–DD/BA, one-measure fill limit, crash-at-time-0 convention, nearest-fill fallback) and JJazzLab's automated fill parameter; Korg Pa Auto Fill and Fill Mode; MMA's groove-swap fills and RSKIP/RTIME/RVOLUME/RDURATION operators; drummer pedagogy on fill frequency/length and the crash+kick resolution convention; jazz setup-figure practice; pop production transition devices (risers, snare builds, stops, dropouts); swing microtiming research (Friberg & Sundström ride ratios; the 2022 *Communications Physics* downbeat-delay finding; Benadon's backbeat asymmetry); ensemble-asynchrony measurements (jazz-trio bass/ride/hi-hat offsets; the <19 ms preference and ~40 ms flam thresholds); timing-fluctuation structure (Räsänen et al.'s Porcaro analysis — SD 8.7 ms, bar-to-bar amplitude correlation 0.88, 2-bar periodicity; Hennig et al.'s 1/f preference); velocity accent hierarchies and DAW humanizer defaults (Logic, Ableton Groove Pool, Roger Linn's dynamics-first doctrine); repetition cognition (Margulis; inverted-U exposure; play-along tolerance); variation-safety literature (Vogl & Knees bounded-distance variation; YamJJazz alternate phrases; GEDMAS); and final-ritard modeling (Friberg & Sundberg 1999 kinematic model; Desain & Honing; notation-software stepped-tempo practice; fade-out obsolescence data).

---

## 1. Scope

**In scope**

- The boundary taxonomy (interior phrase boundaries, section boundaries by entered-type class) and the hybrid placement policy: deterministic devices at section boundaries, drawn small fills at phrase boundaries.
- Fill selection (destination-rung with nearest-rung fallback), sizing (content-window + tail truncation), and rendering (groove replacement inside the window); the crash+kick entry rule and its suppression classes.
- The `stop` device (shipped), `dropout` (designed, dormant — no v1 form reaches `breakdown`), and the reserved `riser` device slot.
- Ending rendering: the HOLD note-structure transform for all close types, the Friberg–Sundberg ritard tempo curve sampled to stepped `header.tempos` events, and the v1 `fade` → HOLD alias.
- The anti-repetition mutation model: five constructive-safe engine operators (`hat_lift`, `drop_ornament`, `kick_pickup`, `anticipate`, `drop_hit`), 2-bar drum units / 8-bar comping units, pack-gated tables.
- The `transitions.yaml` pack-file schema with validation rules and normative reference content for `pop_rock` and `jazz`.
- The Humanizer: swing rendering (tick-domain, offbeat-only), per-role × beat-class micro-timing offset maps in milliseconds (`feel.yaml`, engine data), triangular integer timing/velocity jitter (consuming `budgets.dynamicsRange`), the metric velocity accent map, and duration rules (walking-bass legato stretch).
- RNG discipline for both stages (sub-streams, draw orders, golden vectors) and worked draw narratives for both chained examples.
- Resolution of PHASE_1 Q5 (PPQ 480 confirmed); disposition of PHASE_5 Q5/Q9.
- Amendments to earlier documents (all additive, §10).

**Explicitly not in scope**

- New note *vocabulary*: this phase never invents harmonic material — fills come from pack banks, mutations rearrange/remove/duplicate existing material, the humanizer is note-count-preserving. Ghost-note *insertion* stays compositional (Phase 5 authored ghosts; research consensus — this refines the ROADMAP §4 sketch's "ghost notes" bullet, which the humanizer *modulates*, not creates).
- The riser's sound source (a noise-sweep patch and its track) — reserved here, owned by Phase 7/8 (§9 Q2).
- Concrete Tone.js patches, mixing (Phase 7); the crash track's patch comes from the stub/real `timbres.yaml` like every drum track.
- Style-pack content beyond the two reference `transitions.yaml` files (Phase 8).
- Correlated 1/f timing drift (deferred with rationale, §9 Q1); tempo rubato outside the final ritard (backing tracks keep the grid — research consensus).
- Stop-time choruses / `kind: break` patterns (Phase 8; the v1 `stop` device needs no break patterns — §9 Q5).

---

## 2. Contracts consumed

| Upstream contract | What this phase does with it |
| --- | --- |
| `Phrase[]` (PHASE_1 §4.5, PHASE_5 §6/§8) | Both stages transform phrases in place (per track, per section). Stage 6 adds/removes/moves notes; stage 7 only adjusts `ticks`/`durationTicks`/`velocity` of existing notes. Existing tags `"ghost"`/`"push"` preserved; new tags added (§3.9). |
| `SongForm` (PHASE_1 §4.2, PHASE_3 §4) | `phrases` substructure → interior boundary set; section `type` → device class (semantics table §3.2 of PHASE_3, transitions column — implemented here); `energy` → crash velocity, stop eligibility; `ending` → close rendering (§5.7/§3.6); `totalOfType`/`index` unused directly (energy already encodes final-chorus peak). |
| `HarmonicPlan` (PHASE_1 §4.3, PHASE_4 §7) | The final `"final"`-tagged events locate the HOLD transform's anchor (§3.6). Chord boundaries are *not* re-consulted — anticipation mutations move already-voiced notes (§3.7). |
| `ArrangementPlan` (PHASE_1 §4.4, PHASE_5 §4) | `intensity` → fill rung resolution (destination/current rung); `active` → which roles have mutation units; `densityBudget` not consumed (density was Phase 5's; §3.7 ops are count-bounded, not density-driven). |
| `GenerationPlan` (PHASE_1 §4.1, PHASE_2 §7) | `swing` → §5.2 rendering (ratio/subdivision computed by Phase 2, deliberately unrendered by Phase 5); `budgets.dynamicsRange` → velocity-jitter width (§5.5 — the PHASE_2 §7.2 slot reserved for this phase, now consumed); `tempoBpm` → ms→tick conversion (§5.3) and ritard base; `dynamicsBase`/`articulationLegato` already consumed by Phase 5, untouched here. |
| Section semantics table (PHASE_3 §3.2, transitions column) | Implemented in full by §3.2: chorus crash-on-entry + big fill preceding; postchorus smooth (no fill/crash); breakdown entered by dropout; bridge fill sized by the energy jump into the final chorus; outro renders `ending`; head/solo small boundary fills. |
| Pattern envelope (PHASE_1 §6.2, PHASE_5 §3.2/§5.5) | `kind: fill` patterns selected/placed here (PHASE_5 authored them for this purpose); `eligibility.tempoBpm` respected in fill selection; fills stay exactly 1 bar (PT1) — sizing is windowing, not schema (§3.3). One new completeness rule (PT12, §10.6). |
| Drum voice→track mapping (PHASE_5 §8.2) | `crash` voice (reserved there for this phase) now emitted; tracks appear per the existing mapping rules; crash default `dur` 1440 added to the §8.2 defaults (§10.7). |
| Seed system (PHASE_1 §5) | Streams `transitions` and `humanize` (registry-pinned; golden vectors in PHASE_1 §5.6). Sub-streams §3.8/§5.8. All draws via `weighted_choice`/`randrange`, integer weights, draws only when ≥ 2 candidates (PHASE_3 D13), append-only order. |
| Velocity/rounding conventions (PHASE_5 §3.4, PHASE_1 §5.3) | Fill events instantiate with the §3.4 dynamics shift like any pattern event; crash velocities are absolute (pack-ranged, §3.4 exempt). 3-decimal half-even rounding for all emitted velocities; single float→int tick rounding per note (§5.1). |
| Orchestrator stubs (PHASE_5 §8.1) | The two identity stubs are replaced by these stages; the Serializer gains a tempo-events input (§6, additive). |

---

## 3. The Transition engine (stage 6)

`transitions(phrases, form, chords, arr, plan, pack) → Phrase[]`. Three sub-passes in pinned order: **6a ending note-structure → 6b boundary devices → 6c mutation**. 6a runs first so the final bars are settled before device placement; 6c runs last on the post-device note set. Stage 6 owns all note-structural change; the division with stage 7 (performance-only, note-count-preserving) is D1.

### 3.1 Boundary taxonomy

From `SongForm`:

- **Section boundary** — each adjacent section pair `(i, i+1)`. The *fill bar* is the last bar of section `i`; the *entered downbeat* is section `i+1`'s first tick. The song end is not a boundary (6a owns it).
- **Interior phrase boundary** — each phrase start within a section except the section start (PHASE_3 `phrases`). Its fill bar is the bar before the phrase start. By construction (4-bar phrases, 1-bar fills) interior fill bars never collide with section fill bars.

### 3.2 Device assignment (deterministic at section boundaries — D2)

Per section boundary, by the **entered** section's type, implementing PHASE_3 §3.2's transitions column:

| Entered type | Device | Crash+kick on entered downbeat |
| --- | --- | --- |
| `breakdown` | `dropout` (§3.5) | no |
| `postchorus` | none ("smooth continuation") | no |
| any other | `fill` — or `stop` when eligible (§3.4) | yes |

Stop eligibility: entered intensity rung = 4 **and** entered energy > outgoing energy **and** pack `stop.enabled`. When eligible, draw `[stop, fill]` at the pack's `stop.odds` (1 draw). Everything else in this table is draw-free.

Per interior phrase boundary: draw include/exclude at the pack's `phraseFill.odds` (always 1 draw — two outcomes always exist); included boundaries get a *small* fill (§3.3), no crash.

### 3.3 Fill selection, sizing, rendering (D3)

**Selection.** Candidates = the pack's drum `kind: fill` patterns passing `eligibility.tempoBpm`, at the resolution rung: **destination section's rung** for section boundaries (the Yamaha destination-fill convention), **current section's rung** for phrase boundaries. If the rung has no candidates, fall back **down one rung at a time to 1, then up to 4** (Yamaha graceful fallback; guarantees resolution given PT12). Among candidates: `weighted_choice` iff ≥ 2.

**Window.** A fill's window = `[beatFloor(first event pos), lengthTicks)` where `beatFloor` rounds down to the containing beat. Packs author fill size *as content*: a big fill starts its events at beat 1 (window = whole bar), a medium fill at beat 3 (the existing reference fills: `pr_dr_f1`/`pr_dr_f2` window `[960, 1920)`, `jz_dr_f1` window `[960, 1920)` — first event 1200 floors to 960). The loader computes and caches the window; TR7 requires ≥ 1 event in the last 2 beats.

**Sizing.** Section-boundary fills render their **full window**. Phrase-boundary fills render **window ∩ [lengthTicks − 960, lengthTicks)** — the last 2 beats — so one bank serves both tiers (research: 1–2-beat fills at phrase turns, bar-scale fills at section boundaries).

**Rendering.** In the fill bar, on the drums role only: delete all drum-voice events whose tick falls inside the (bar-aligned) rendered window; instantiate the fill's events at their positions with the PHASE_5 §3.4 velocity shift applied; tag them `"fill"`. Groove events before the window keep playing (the authored fill's silence before its window *is* the design). All other roles play through unchanged (research: bass/comping hold time under a drum fill; lay-out/unison variants are Phase 8 — §9 Q6).

### 3.4 The `stop` device (D4)

Replaces the fill entirely at its boundary. Rendering, across **all roles**: delete every note attacking in `[enteredTick − 480, enteredTick)`; truncate any note sustaining into that window to end at `enteredTick − 480`. The entered downbeat then lands with the crash+kick rule plus every role's pattern attack — the "slam back." One beat of full-band silence is the v1 length (the research range is 1 beat–1 bar; 1 beat is the tightest, safest form). Jazz ships `stop.enabled: false`; the pop reference odds keep it rare (1:4 at eligible boundaries — both worked-example draws resolved to `fill`; a synthetic odds fixture exercises the rendering path, §11.8).

### 3.5 The `dropout` device (designed, dormant — D5)

Entering a `breakdown`: no fill, no crash; every role's notes sustaining across the entered downbeat are truncated at it (clean cut into the thinned texture the Arrangement planner already provides). No v1 form produces a `breakdown` (Phase 8 styles); a synthetic fixture keeps the path tested — the PHASE_4 deceptive-rule precedent.

### 3.6 Ending note-structure — the HOLD transform (6a; D6)

Let `T_last` = the `startTick` of the song's **final chord event** — the last `"final"`-tagged `ChordEvent` (PHASE_4 §5.5 guarantees the finals replacement exists and its last event is degree-1-rooted). Then:

1. **Pitched roles** (bass, comping, pads): notes attacking at `T_last` extend to the final section's `endTick` (`durationTicks = endTick − ticks`); notes attacking after `T_last` are deleted. Extended notes get velocity `+0.05` (clamped ≤ 1.0) and tag `"hold"`.
2. **Drums**: all drum events attacking at or after `T_last` are deleted; a `crash` (dur 1440) **and** a `kick` are added at `T_last`, velocity = the §3.7 crash formula evaluated at the **final section's own energy**, + 0.05, tagged `"hold"`.
3. This applies to **every** `close` value — `cold` and `fade` are HOLD-only; `ritard` is HOLD plus the §5.7 tempo curve. `fade` is a documented alias of `cold` in v1 (D7): per-note velocity fades cannot reach silence and distort timbre, real fades need a gain-automation lane the schema deliberately lacks, and fades are extinct in the target styles. True fade awaits a document-level automation extension (§9 Q3).

The audible ring-out past note-off comes from synth release envelopes (Phase 7's patches), so V8 (all notes end within the final section) holds structurally. No fills or mutations may touch bars at or after `T_last`'s bar (§3.7); no section boundary exists there (6a runs first).

**SHOT** (the choked-hit cold variant BiaB encodes as `C7..`) is deferred as a possible `close` enum extension (Phase 8, §9 Q4); HOLD is the research-preferred default.

### 3.7 Crash rule and the mutation pass (6b tail / 6c)

**Crash+kick on entered downbeats.** After every section-boundary `fill` or `stop` (not `dropout`/`postchorus`/none): add a `crash` event (dur 1440) at the entered downbeat, velocity `round3(lo + energy × (hi − lo))` from the pack's `crash.velocity` range and the **entered** section's energy; add a `kick` at the same tick **iff no kick attacks there already** (double-hit guard; pop patterns have one, the jazz ride patterns don't — the jazz crash gets its soft kick "bomb"). Both tagged `"crash"`. Crash velocities are absolute (the pack range encodes style loudness; PHASE_5 §3.4 shift not applied).

**Mutation (6c — D8).** Anti-repetition as a closed set of constructive-safe operators drawn per unit with heavy no-op bias. Units: **drums — 2-bar units** from each section start (the measured groove periodicity; the ROADMAP §4 "every 4 bars" sketch refined by the corpus evidence, §10.1); **comping — 8-bar units** from each section start, last unit may be short (the "comp differently each chorus" convention and ROADMAP's "comping every 8"). Bass and pads have no operators in v1 (variation-budget evidence: the walker already varies per bar; pads vary least of all roles). Units exist only where the role is `active`.

One draw per unit from the pack's `mutation.<role>` table (authored order; draw iff the table has ≥ 2 entries), on the unit's own sub-stream (§3.8). The drawn operator applies **or degrades to a no-op** when no legal target exists (documented, deterministic; keeps draw counts form-invariant). Operators never target: events tagged `"fill"`, `"crash"`, or `"hold"`; any event in a stop window; any event at or after the final chord event's bar.

| Op | Role | Semantics |
| --- | --- | --- |
| `hat_lift` | drums | the last `hat_closed` event at an offbeat-8th position (`pos % 480 == 240`) in the unit's **second** bar → voice `hat_open`, dur 360, tag `"var"`. No such event → no-op. |
| `drop_ornament` | drums | delete the last instantiated event in the unit that carries `minDensity` (the authored ornament class — pre-declared droppable). None → no-op. |
| `kick_pickup` | drums | target = last kick in the unit not at a bar start; add a kick at `target − 240` iff no kick lies within ±120 of that tick; velocity `round3(target.velocity × 0.85)`, tag `"var"`. No target/occupied → no-op. |
| `anticipate` | comping | target = last comping event in the unit attacking at a bar start, excluding the unit's first event; shift its `ticks` by −240 (pitches unchanged — an anticipation *sounds the incoming chord early*, exactly the authored-`push` idiom); truncate the previous comping note to the new start if it overlaps; skip (no-op) if any comping note attacks in `[new, old)`. Tag `"var"`. |
| `drop_hit` | comping | delete the last comping event in the unit whose bar contains ≥ 2 comping attacks (the ≥ 2 guard prevents fully silent bars). None → no-op. |

Safety is structural: no operator can remove a backbeat snare, a beat-1 event, or any non-ornament note; none touches pitch content or registers; each unit changes by at most one event. With the Humanizer's jitter on top, no bar renders byte-identical — the roadmap's "nothing loops verbatim," delivered by feel + sparse structural spice, per the evidence that real grooves vary in dynamics, not structure.

### 3.8 RNG discipline (stage 6)

- **`derive(transitions, "devices")`** — one RNG, consumed in boundary timeline order; per boundary: `[stop-vs-fill draw iff eligible]` then `[include draw iff phrase boundary]` then `[fill selection draw iff ≥ 2 candidates]`. 6a and the crash rule are draw-free.
- **`derive(derive(derive(transitions, "mutate"), role), f"bar:{unitStartAbsBar}")`** — one RNG per (role, unit); one draw each. Per-unit isolation means skipped/no-op units can never shift another unit's outcome (PHASE_5 walker precedent).
- Golden vectors (master `1ps9wxb` = 3735928559; `transitions` = 17897360909067852929, pinned PHASE_1 §5.6): `derive(transitions, "devices")` = 11162692426947704816; `derive(transitions, "mutate")` = 2353238394870311228; `derive(mutate, "drums")` = 10947905152221053268.
- Append-only order across versions (PHASE_2 §6.1 rule); golden draw-count tests enforce (§11).

### 3.9 Tags contributed (PHASE_1 §4.5 vocabulary, additive)

`"fill"` (fill-pattern events), `"crash"` (entry crash/kick), `"var"` (mutation-added/-modified events), `"hold"` (HOLD-extended/added finals). Stage 7 adds none.

---

## 4. The `transitions.yaml` schema

New pack file (added to the PHASE_1 §6 layout, §10.5), schema owned by this phase.

### 4.1 Schema, field-level

```yaml
phraseFill: { odds: [include, exclude] }   # integer odds ≥ 1 for interior phrase-boundary fills
stop:
  enabled: true|false
  odds: [stop, fill]                       # required iff enabled; integer odds ≥ 1
crash: { velocity: [lo, hi] }              # 0 ≤ lo ≤ hi ≤ 1; entry-crash velocity range over energy
mutation:                                  # per-role operator tables; authored order is draw order
  drums:   { none: <int ≥ 1>, <op>: <int ≥ 1>, ... }
  comping: { none: <int ≥ 1>, <op>: <int ≥ 1>, ... }
```

**Validation rules** (loader; each class gets a rejection fixture):

- **TR1** `phraseFill.odds`: two ints ≥ 1. `crash.velocity`: floats in [0, 1], `lo ≤ hi`.
- **TR2** `stop.enabled` boolean; `odds` present iff enabled, two ints ≥ 1.
- **TR3** `mutation` keys ⊆ {`drums`, `comping`}; each table non-empty with `none` present; weights ints ≥ 1; op names from the §3.7 vocabulary for that role. A single-entry table (`none` only) is legal — that role never draws.
- **TR4** strict schema — unknown keys rejected (pydantic).
- **TR5** *(cross-file)* the pack's drum bank contains ≥ 1 ungated `kind: fill` pattern (= PT12, §10.6) — fill resolution can never come up empty.
- **TR6** *(engine constant, checked at load)* every fill pattern's computed window is non-empty.
- **TR7** every fill pattern has ≥ 1 event with `pos ≥ lengthTicks − 960` (a fill must reach the barline — phrase-fill truncation is otherwise silent).

### 4.2 Reference content — `styles/pop_rock/transitions.yaml` (normative)

```yaml
phraseFill: { odds: [1, 2] }               # ~1/3 of phrase turns get a small fill
stop:       { enabled: true, odds: [1, 4] }  # rare spice at rung-4 rising entries
crash:      { velocity: [0.55, 0.95] }
mutation:
  drums:   { none: 10, hat_lift: 2, drop_ornament: 1, kick_pickup: 2 }
  comping: { none: 3, anticipate: 2, drop_hit: 1 }
```

### 4.3 Reference content — `styles/jazz/transitions.yaml` (normative)

```yaml
phraseFill: { odds: [1, 3] }               # jazz fills sparser, quieter (setup figures)
stop:       { enabled: false }
crash:      { velocity: [0.40, 0.70] }     # compressed dynamics — combo, not arena
mutation:
  drums:   { none: 6, drop_ornament: 1 }   # no hat_lift (jazz hats sit on 2/4), no kick_pickup
  comping: { none: 4, anticipate: 1, drop_hit: 1 }
```

Jazz's "setup figure" boundary sound is fill-bank *content* (`jz_dr_f1`: a quiet beat-3.5 pickup), not engine machinery — style difference stays data (invariant 1).

---

## 5. The Humanizer (stage 7)

`humanize(phrases, form, plan) → (Phrase[], tempoEvents)`. **Note-count-preserving**: it never adds or removes a note; it adjusts `ticks`, `durationTicks`, `velocity`. Per-note operation order (D9): **swing → offset map → timing jitter → velocity accent → velocity jitter → duration**. All timing math runs in float milliseconds/ticks and rounds to integer ticks **once** at the end (half-even); global clamp `ticks ≥ 0` and `ticks + durationTicks ≤ song end`. Each phrase's notes are re-sorted `(ticks, midi)` after adjustment (jitter can reorder near-simultaneous notes; the PHASE_1 §4.5 sort contract is re-established before emission).

The ms→tick factor is computed once per song: `ticksPerMs = 480 × tempoBpm / 60000` (123 BPM → 0.984; 69 BPM → 0.552). Offsets and jitter are authored in ms because feel offsets are ~constant in ms across tempo (the constant-short-note finding), while swing — a *proportional* effect — lives in ticks and scales with the tempo map automatically.

### 5.1 Beat classes

From the note's **pre-humanization grid position** within its bar: `down` (0), `back2` (480), `beat3` (960), `back4` (1440), `off` (everything else). Swung notes keep the class of their straight position.

### 5.2 Swing (D10)

Applied iff `plan.swing ≠ null`, at its `subdivision`, to **offbeat-subdivision events only** — downbeats never move (universal across the measurement literature and every DAW implementation):

- `swing8`: events at `pos_in_beat == 240` → `pos_in_beat = round(480 × ratio)` (0.722 → 347).
- `swing16`: events at `pos % 240 == 120` → `(pos − 120) + round(240 × ratio)`.

All roles' offbeat events move identically *in position* (drums, comping, pattern bass, the walker's and-of-4 ghosts); per-instrument swing differentiation (ride leads, comping downbeats late) is delivered by the §5.3 offset maps, matching the research mechanism (soloists delay downbeats, lock offbeats to the ride). Straight-feel packs (`swing = null`): no-op.

**Gap-preserving stretch**: after repositioning a track's bar, any note whose original end abutted a repositioned note's original start (gap ≤ 10 ticks) has its duration adjusted to end at the new start; a repositioned note whose end abutted the next grid point keeps that end (duration shrinks — the swung short note).

### 5.3 Micro-timing offset maps — `feel.yaml` (engine data; D11)

`src/trackgen/humanize/feel.yaml`, loaded like `moods.yaml`; internal, recalibratable; validator caps `|offset| ≤ 25 ms` (inside the < 19 ms ensemble-preference ceiling with jitter margin, far under the ~40 ms flam threshold). The `offsetsMs` tables are **named profiles** (amended by PHASE_8 §3.4, 2026-07-07): the engine menu is `straight`, `swung`, `laidback`, `tight` (the two new profiles' values in PHASE_8 §3.4); selection = the pack's `interpreter.yaml` `feelTable` when present, else the swing-derived default (null → `straight`, else `swung`). Values in ms; scalar = all beat classes; per-class maps where measurement demands:

```yaml
offsetsMs:
  swung:                             # jazz-trio + downbeat-delay measurements
    kick: 0
    snare: 3
    hats: -3                         # hi-hat leads the ride (measured +9..28 ms; conservative)
    ride: 0                          # the anchor
    toms: 0
    crash: 0
    perc: 0
    bass: -2                         # marginally ahead of / locked to ride (+2.1 ms measured)
    comping: { down: 18, back2: 6, beat3: 10, back4: 4, off: 2 }   # downbeat delay ≈ swing cue
    pads: 0
  straight:                          # pop/rock laid-back conventions
    kick: 0                          # the P-center anchor
    snare: { down: 4, back2: 8, beat3: 4, back4: 6, off: 4 }       # laid-back backbeat, 2 > 4
    hats: -2
    ride: 0
    toms: 0
    crash: 0
    perc: 0
    bass: 2
    comping: 5
    pads: 0
jitterMs:  { kick: 4, snare: 5, hats: 5, ride: 4, toms: 5, crash: 0, perc: 5,
             bass: 6, comping: 8, pads: 0 }
accent:    { down: 0.03, back2: 0.0, beat3: 0.015, back4: 0.0, off: -0.03 }
velJitter: { base: 0.04, rangeScale: 0.08 }
bassLegato: 0.95
```

Drum offsets/jitter key by **voice** (kick/snare/hats/ride/toms/crash/perc — toms share one row); pitched roles by role.

### 5.4 Timing jitter (D12)

Sub-JND white triangular jitter; the *structured* offsets carry the audible feel (the Linn doctrine), jitter supplies the measured statistical looseness at amplitudes where white-vs-correlated is near the perceptual floor. Correlated 1/f drift is deferred (§9 Q1).

Per note: `w = round(jitterMs[voice/role] × ticksPerMs)`; if `w ≥ 1`, `dt = tri(rng, w)` where the pinned helper is

```python
def tri(rng, w):                 # triangular on [-w, +w], SD ≈ w/2.45; built on allowed ops
    return rng.randrange(w + 1) + rng.randrange(w + 1) - w
```

(2 draws; `w == 0` — crash, pads, or tiny factors — consumes none). At 123 BPM, snare w = 5 → SD ≈ 2 ms; at 69 BPM, comping w = 4.

### 5.5 Velocity: accent map + jitter (D13)

1. **Accent** (deterministic): `v += accent[beatClass]` — small and additive so authored relationships (ghost ≈ 0.26–0.36, backbeat ≈ 0.9+) survive; encodes the measured hierarchy beat 1 > 3 > 2/4 > offbeats.
2. **Jitter**: width `W = round(1000 × (velJitter.base + velJitter.rangeScale × budgets.dynamicsRange))` thousandths (pop/happy: 0.21 → W = 57; jazz/melancholic: 0.217 → 57; tense: 0.35 → 68 — **`dynamicsRange` consumed here**, closing the PHASE_2 §7.2 reservation); `dv = tri(rng, W) / 1000` (2 draws).
3. Clamp + round: `velocity = round3(clamp(v + dv, 0.05, 1.0))`.

Pads are exempt from timing and velocity jitter (`jitterMs: 0`; accent still applies) — slow attacks wash micro-variation into noise.

### 5.6 Duration (D14)

- **Bass legato** (the walking-line finding — durations fill ~90–100 % of the IOI): for every bass note whose gap to the same track's next attack is ≤ 60 ticks, `durationTicks = round(bassLegato × (nextAttack − ticks))`. Walker quarters 480 → 456; two-feel halves 960 → 912; the final whole note (no successor) is untouched. Applies to both bass modes.
- All other durations pass through (Phase 5's articulation scaling and §5.2's gap-preserving stretch already provide duration variation; per-note length jitter added nothing at our magnitudes and is omitted — D14).
- Drum trigger durations and pads: exempt.

### 5.7 Ritard rendering (D15)

For `ending.close == "ritard"` (jazz reference; `cold`/`fade` emit no tempo events): over the tag region — `tagBars` bars ending at the final section's `endTick` (for `tagBars: 0`, the section's last bar):

```
v(x) = (1 + (v_end³ − 1) · x) ^ (1/3)        x ∈ [0, 1] over the tag, q = 3, v_end = 0.65
```

The Friberg–Sundberg kinematic final-ritard model (constant braking power; q 2–3 rated best by listeners; measured depths ~0.6–0.7). Sampling: at every 8th note (240 ticks) except the final bar, which samples every 16th (120 ticks) — the curve steepens toward the stop; `bpm = round(tempoBpm × v(x), 1)`; consecutive duplicate bpm values and any event equal to the prevailing tempo are dropped. Tempo never reaches 0 — the stop is the HOLD release. Output: `tempoEvents = [{ticks, bpm}]` (absolute ticks), appended by the Serializer after the tick-0 base tempo (V1-compliant). Swing needs no adjustment — tick-domain offsets integrate through the tempo map (standard MIDI semantics; the client schedules via `bpm.setValueAtTime`).

Worked (jazz example, 69 BPM, 4-bar tag at bars 60–64): **39 events**, first `{+240, 68.5}`, reaching `{+7560, 45.5}` = 0.659 × 69 at the tag's last 16th-note sample — computed table in §7.2.

**PHASE_1 Q5 resolved**: PPQ 480 suffices for all humanizer micro-timing — every modeled effect is ≥ 3 ticks at reference tempi, math is float-ms with one terminal rounding; no schema bump (D16).

### 5.8 RNG discipline (stage 7)

- Per-role sub-streams: `derive(derive(humanize, role), f"bar:{absBar}")` — one RNG per (role, bar); the drums role covers all its voice-tracks. Within a bar, notes are processed in `(gridTicks, trackId, midi|-1)` order; per note: timing draws (2, iff w ≥ 1) then velocity draws (2, iff W ≥ 1). Per-bar isolation → excerpt-reproducible, mutation-independent.
- Deterministic sub-passes (swing, offsets, accents, durations, ritard) consume nothing.
- Golden vectors (master `1ps9wxb`; `humanize` = 3899203291477031323, pinned PHASE_1 §5.6): `random.Random` on it: first five `getrandbits(32)` = `[4182865326, 1966627690, 4223947781, 2670867691, 1704714080]`; first five `randrange(100)` from a fresh instance = `[58, 79, 50, 70, 90]`; `derive(derive(humanize, "drums"), "bar:0")` = 6949714659275352449.

---

## 6. Pipeline signature change (additive)

Stage 7 becomes `humanize(phrases, form, plan) → (Phrase[], tempoEvents)`; the Serializer's header assembly becomes `tempos = [{ticks: 0, bpm: plan.tempoBpm}] + tempoEvents`. PHASE_1 §4's pipeline recap and PHASE_5 §8.1/§8.3 are amended accordingly (§10.2/§10.8). `TrackDocument` is untouched — `header.tempos` was multi-event from day one (the PHASE_1 milestone fixture already exercised two tempo events).

---

## 7. Worked examples (normative golden fixtures)

Both chain from PHASE_2 §6.5 / PHASE_3 §7.4 / PHASE_4 §10 / PHASE_5 §9 (seed `1ps9wxb`, master 3735928559). Every draw outcome below is **computed** (session reference script) from the §3.8 draw order, the §4.2/§4.3 tables, and the PHASE_5 §7 banks.

### 7.1 Example 1 — pop_rock / happy (123 BPM, cold close)

Boundaries: section fills into verse-1/chorus-1/verse-2/chorus-2/bridge-1/chorus-3 (fill bars 3, 11, 27, 35, 51, 59); interior phrase boundaries at bars 8, 16, 20, 24, 32, 40, 44, 48, 56, 64, 68, 72. Fill rungs: verse/bridge → 2 → `pr_dr_f1` (sole candidate); chorus-1 → 3 → fallback-down 2 → `pr_dr_f1`; chorus-2/3 → 4 → `pr_dr_f2`. Stop-eligible: chorus-2 and chorus-3 entries (rung 4, rising energy).

**Devices stream — 14 draws**: stop draws at fill bars 35 and 59 both → **fill** (odds 1:4); phrase-fill include draws → **included at fill bars 19, 55, 67** (`pr_dr_f1`, `pr_dr_f1`, `pr_dr_f2`, truncated to beats 3–4), excluded at fill bars 7, 15, 23, 31, 39, 43, 47, 63, 71. All fill selections single-candidate (0 selection draws).

Crashes (dur 1440, velocity `0.55 + energy × 0.40`): bar 4 → 0.746, bar 12 → 0.866, bar 28 → 0.766, bar 36 → 0.886, bar 52 → 0.726, bar 60 → 0.950. Kick never added (pop mains have beat-1 kicks).

**Mutation — drums 38 unit draws, 15 ops fired**: `kick_pickup` @4, 20, 40, 46, 66, 70; `hat_lift` @8, 10, 22, 24, 26, 38, 58; `drop_ornament` @54 (bridge rung 2, `pr_dr_2a` — no `minDensity` events → **no-op**), @68 (chorus-3 rung 4, `pr_dr_4` — drops its last gated event in the unit). **Comping 9 unit draws, 3 ops**: `drop_hit` @20, @36; `anticipate` @44. Sample renderings: unit @4 `kick_pickup` → kick added bar 5 tick 720 (and-of-2), velocity `round3(0.94 × 0.85)` = 0.799, tag `var`; unit @8 `hat_lift` → bar 9's hat at 1680 becomes `hat_open` dur 360.

**Fill bar 3** (intro, `pr_dr_i` + `pr_dr_f1` window [960, 1920)): hats at 960/1440 deleted; fill snares at 960/1200/1440/1680, velocities 0.66/0.74/0.82/0.91 (§3.4 shift +0.06), tag `fill`; kick@0 and hats@0/480 keep playing.

**Ending (cold → HOLD)** at `T_last` = tick 144000 (bar 75, the final E of the plagal close): bass/comping/pads notes attacking there extend to 145920 (+0.05 velocity, tag `hold`); later attacks deleted; drums cleared from 144000; crash+kick added at 144000, velocity 1.000 (0.950 + 0.05). No tempo events.

**Humanizer** (straight table; ticksPerMs 0.984): snare backbeats +8 ticks (beat 2) / +6 (beat 4); hats −2; bass +2; comping +5; jitter widths kick 4 / snare 5 / hats 5 / bass 6 / comping 8 ticks; velocity accent ±0.03/±0.015; W = 57 thousandths. Bass legato: root quarters dur 434 → abutting gap 46 ≤ 60 → `round(0.95 × 480)` = 456.

### 7.2 Example 2 — jazz / melancholic (69 BPM, ritard close, 4-bar tag)

Boundaries: section fills into solo-1/2/3, head-2, outro-1 (fill bars 11, 23, 35, 47, 59 — every one `jz_dr_f1`: solos at rung 3 exact, head-2/outro at rung 2 → fallback down misses → up to 3); interior phrase boundaries at bars 4, 8, 16, 20, 28, 32, 40, 44, 52, 56.

**Devices stream — 10 draws**: phrase fills **included at fill bars 3 and 31** (odds 1:3), excluded at fill bars 7, 15, 19, 27, 39, 43, 51, 55. No stop draws (disabled). All selections single-candidate.

Crashes (velocity `0.40 + energy × 0.30`): bar 12 → 0.587, bar 24 → 0.611, bar 36 → 0.635, bar 48 → 0.539, bar 60 → 0.503 — each **with an added kick** (the ride patterns have no beat-1 kick): the soft entry "bomb," tag `crash`.

**Mutation — drums 32 unit draws, 4 ops**: `drop_ornament` @4 and @54 (rung-2 `jz_dr_2`, no `minDensity` events → **no-ops**), @20 and @40 (rung-3 `jz_dr_3a` → each drops its unit's last gated comping hit). **Comping 11 unit draws, 5 ops**: `anticipate` @0, @8 (head-1: bar 7's / bar 11's bar-start Charleston hit pulled to the preceding and-of-4 — sounding its chord 240 ticks early, the authored-push idiom emerging from mutation); `drop_hit` @20, @36, @48 (units whose bars have 2 Charleston attacks → the second is dropped, leaving a football bar).

**Ending (ritard + HOLD)**: tag = bars 60–64 (ticks 115200–122880). Tempo events — 39 after dedupe, sampled per-8th (bars 60–62) then per-16th (bar 63):

| rel tick | +240 | +480 | +960 | +1920 | +2880 | +3840 | +4800 | +5760 | +6720 | +7200 | +7560 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bpm | 68.5 | 67.9 | 66.8 | 64.5 | 62.1 | 59.4 | 56.4 | 53.1 | 49.3 | 47.2 | **45.5** |

(intermediate events omitted for space; the full 39-event list is the golden fixture). Final tempo 45.5 = 0.659 × 69, at the tag's last 16th-note sample (+7560) ✓. HOLD at `T_last` = bar 63 (the finals' Dm7): walker's whole-note D2 extends (already bar-long) +0.05 velocity; comping voicing extends; drums bar 63 cleared, crash+kick at velocity 0.553 (0.503 + 0.05).

**Humanizer** (swung table; ticksPerMs 0.552; ratio 0.722 → offbeat 240 → **347**): bar 0 of head-1 renders — ride 0/480/**827**/960/1440/**1787** (swing) with 0 offset; hats 480 → 478, 1440 → 1438 (−3 ms → −2t); comping Charleston 0 → +10t (down +18 ms), and-of-2 hit 720 → 827 (swing) + 1t (off +2 ms) = 828; bass D2 beat 1 −1t → clamp 0, A2 beat 3 → 959; walker ghosts at and-of-4 swing to 1787. Jitter: ride w 2, hats/snare 3, bass 3, comping 4 ticks (then per-bar draws); velocity W = 57. Bass legato: two-feel halves 960 → 912, four-feel quarters 480 → 456.

### 7.3 Milestone check

Both examples still serialize to `TrackDocument`s passing V1–V8: fills/crashes/mutations preserve the drum-track exemption and never touch pitched registers (C5 ceiling intact — stage 6 moves/removes pitched notes but never re-pitches; stage 7 never changes `midi`); the jazz document now carries a 40-entry tempo map (base + 39 ritard events) — the first generated use of multi-event `header.tempos`.

---

## 8. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Stage split: Transitions = all note-structural edits (fills, devices, mutation, ending notes); Humanizer = strictly note-count-preserving performance rendering** | Crisp per-stage invariant; rerolling `humanize` re-performs identical notes ("same track, new take"), rerolling `transitions` re-rolls fills+variation with stable feel; mutation must precede accent maps/jitter anyway. Moves "4-bar pattern mutation" from ROADMAP §3's stage-7 line to stage 6 (clarifying amendment, §10.1). | Mutation in Humanizer (ROADMAP literal — humanizer stops being shape-preserving, streams blur); one merged stage (contradicts PHASE_1's pinned pipeline/registry/stubs). |
| D2 | **Hybrid placement: deterministic devices at section boundaries; drawn small fills at interior phrase boundaries** | Products fire a fill at every section switch (BiaB/Yamaha/Korg) and the PHASE_3 semantics table makes boundary devices contractual; drummers fill *selectively* at phrase turns ("every 8 or 16 bars") — a seeded draw is the honest model; reroll varies interior fills, never structural ones. | Fully deterministic (identical placement every seed; weak reroll); everything drawn (structural fills become skippable or special-cased back to this design). |
| D3 | **Fill = 1-bar pattern in the bar before the boundary; window from authored content (beat-floor of first event); section fills full-window, phrase fills last-2-beats truncation; destination-rung selection with nearest-down-then-up fallback** | The universal 1-bar convention (BiaB/Yamaha "one measure"); content-derived windows keep PT1 intact and authoring natural (write the fill as played); truncation gives the 1–2-beat phrase-turn tier from one bank; destination-fill + graceful fallback are Yamaha's exact mechanisms. | Explicit `fillBeats` eligibility field (3 sizes × 4 rungs × 5 packs of redundant authoring); full-bar fills only (contradicts the length-distribution evidence — the "MIDI file" tell). |
| D4 | **`stop` ships: 1 beat of full-band silence replacing the fill, drawn as a rare alternative at rung-4 rising entries; pack-gated** | ROADMAP names it; pure note deletion/truncation, zero schema; the research's most reliable impact device; 1 beat is the tightest canonical form; odds keep it spice, not formula. | Deferring (drops a roadmap-named device); always-stop at max-contrast boundaries (formula fatigue). |
| D5 | **`dropout` designed but dormant; `riser` reserved unimplemented; snare-roll build = fill content, not a device** | Breakdown is contractual (semantics table) but unreachable until Phase 8 — synthetic-fixture pattern (PHASE_4 deceptive precedent); the riser needs a Phase 7 sound source and is least essential to pop/rock+jazz v1; `pr_dr_f1` *is* a snare build — no mechanism needed. | Shipping the riser on a stub patch (provisional audio dependency for marginal v1 value); dropping dropout design (leaves breakdown semantics undesigned for Phase 8). |
| D6 | **HOLD transform for every close: extend final-chord notes to section end with coordinated release, +0.05 bump, drums cleared and replaced by crash+kick at the final downbeat** | The dominant real-world ending (fermata/Big Rock Ending); needs only note edits already in the schema; V8-safe (ring-out lives in release envelopes); uniform across close types so `ritard` = HOLD + curve. | Letting patterns play through the final bar (the "cut ending" generated-music tell PHASE_3 D6/PHASE_4 D13 exist to kill); SHOT default (less common; deferred as enum extension, Q4). |
| D7 | **`fade` aliases to HOLD in v1 (documented stub)** | Per-note velocity fades can't reach silence and dull timbre while falling (velocity ≠ gain); real fades are automation-lane territory the schema deliberately omits; fades are extinct in the target styles (1984: 100 % of top-10 faded; 2011–13: ~1 song). Enum value stays legal — no PHASE_3 amendment. | Velocity-taper fade (knowingly substandard, pollutes just-calibrated velocity semantics); removing `fade` from the pinned enum (breaking change for a free reservation). |
| D8 | **Mutation = five constructive-safe engine operators on 2-bar drum / 8-bar comping units, one heavily none-biased draw per unit on per-unit sub-streams; tables are pack data; ops degrade to no-ops** | Corpus: real grooves vary in dynamics on a ~2-bar period, structure stays fixed (r ≈ 0.88; backbeat invariant) — so ops are rare, tiny, and can never touch the skeleton (safety by construction, the bounded-distance rule); per-unit seeds keep draw counts form-invariant and excerpts independent; pack tables let styles disable ops (invariant 1). Refines ROADMAP's "every 4 bars" to the measured 2-bar grid with equivalent realized rate (§10.1). | Pattern re-pick among same-rung mains (YamJJazz model — our alternates aren't authored interchangeable; money-beat↔four-on-floor mid-verse is a groove change); probabilistic per-note RSKIP/RTIME (draw counts scale with notes; golden fragility; the failure modes the safety literature documents); both mechanisms (two systems, one job). |
| D9 | **Humanizer op order swing → offsets → timing jitter → accent → velocity jitter → duration; float-ms math, one terminal int rounding; ms-authored offsets, tick-domain swing** | Swing is proportional (scales with tempo via the map — correct MIDI semantics); feel offsets are ~constant in ms across tempo (constant-short-note finding), so ms is the honest authoring unit; single rounding avoids accumulated bias. | Tick-authored offsets (wrong across the 30–300 BPM range); per-op rounding (bias accumulation). |
| D10 | **Swing displaces offbeat-subdivision events only, uniformly across roles; per-instrument differentiation via offset maps; 16ths unswung in swing8; gap-preserving duration stretch** | Every measurement and DAW agrees downbeats don't move; the ride-leads/soloist-delays finding is an *onset-offset* phenomenon (downbeat delay), not per-role ratios — offset maps model it directly; jazz doesn't compound-swing 16ths. | Per-role swing ratios (misreads the mechanism; the 2022 study shows offbeats lock, downbeats delay); swinging all subdivisions (measurably wrong). |
| D11 | **`feel.yaml` engine data: per-voice/role × beat-class offsets (swung/straight tables), jitter widths, accent deltas, velocity-jitter formula, bass legato factor; \|offset\| ≤ 25 ms validator** | Every value traces to a measurement (hi-hat leads, bass +2 ms vs ride, laid-back backbeat 2 > 4, downbeat delay ~18 ms, < 19 ms ensemble preference, 40 ms flam ceiling); engine data = recalibratable without schema churn (moods.yaml/energy.yaml precedent); per-pack overrides deferred (Q7). | Hardcoded constants (recalibration = code change); per-pack feel authoring now (PHASE_2 Q1 pattern says wait for evidence across 5 packs). |
| D12 | **Timing jitter: white triangular (`tri` helper on `randrange`), SD ≈ 2–5 ms, per-role/per-bar sub-streams; correlated 1/f drift deferred** | At sub-JND amplitude the white-vs-correlated difference approaches the perceptual floor while structured offsets carry the audible feel (Linn doctrine + our offset maps); cross-bar correlation state conflicts with per-bar seed isolation (excerpt tests, reroll granularity); `random.gauss` is outside the allowed-ops list — `tri` is built on `randrange`. | Correlated AR/1-f now (research-maximal but breaks per-bar independence for an unproven audibility gain at these amplitudes — Q1 documents the revisit); zero jitter (every measured performance has 8–15 ms SD; every DAW defaults nonzero). |
| D13 | **Velocity = additive metric accent map + `dynamicsRange`-scaled triangular jitter, clamp (0.05, 1], round3** | Measured hierarchy (1 > 3 > 2/4 > offbeats) applied small so authored ghost/backbeat relationships survive (PHASE_5 D8's logic); `dynamicsRange` finally lands where PHASE_2 §7.2 reserved it — width, not center. | Multiplicative accents (crush/clip at extremes); consuming dynamicsRange as offset-map scaling (it's a *width* budget by definition). |
| D14 | **Duration: bass legato stretch (0.95 × IOI on abutting notes) only; no per-note length jitter** | The one measured duration phenomenon we lack (walking lines fill ~90–100 % of IOI; the walker's fixed 480s were explicitly deferred to us); elsewhere Phase 5's articulation scaling + the swing stretch already vary durations; length jitter at musical magnitudes added nothing in review. | Length jitter everywhere (draw-count cost, no evidence of audible benefit); leaving walker durations fixed (measurably non-legato). |
| D15 | **Ritard = Friberg–Sundberg position-domain curve, q = 3, v_end = 0.65, stepped per-8th (per-16th final bar), 0.1-bpm rounding, dedupe; tempo never 0; `cold`/`fade` emit no events** | The published kinematic model, parameterized in exactly our domain (score position); q = 3 and depth ~0.65 sit centrally in the perceptually preferred band; stepped integer-ish events are notation-software practice and our schema's native form; density biased where the curve steepens. | Linear tempo ramp (measured ritards are never linear; disliked in listening tests); Tone `linearRampTo` (schema pins step events); deeper/param-per-pack curves (no evidence need; engine constants, recalibratable). |
| D16 | **PPQ 480 confirmed (resolves PHASE_1 Q5)** | Every modeled effect ≥ 3 ticks at reference tempi; JND ~10 ms ≈ 10–20 ticks; float-ms math with one rounding keeps error ≪ 1 ms. | PPQ 960 bump (schema rev + client churn for headroom nothing uses). |
| D17 | **Crash+kick on entered downbeats (energy-scaled pack velocity range, kick only if absent); suppressed for breakdown/postchorus entries** | The single most universal post-fill convention (crash "emphasizes the start of a new section"; Yamaha encodes crash-at-time-0; crash+kick struck together for weight); double-hit guard respects V3; suppression classes come straight from the semantics table. | Crash baked into fill patterns (Phase 5 convention says mains/fills never author crashes — placement is contextual); fixed crash velocity (ignores style dynamics — jazz combo ≠ arena rock). |

---

## 9. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | Correlated 1/f timing drift (shared "clock" stream + lag-1 anticorrelation) — audibly better than white at our amplitudes? | Post-v1 | listening evidence; would need a section-scoped drift stream design that preserves excerpt reproducibility (D12 hook documented) |
| Q2 | Riser implementation: sound source (noise → filter-ramp patch), track/role convention, placement rules — **patch half resolved** (PHASE_7 §4.7, 2026-07-07: NoiseSynth envelope-swell recipe pinned, dormant); track/placement/pack opt-in remain (PHASE_8 §3.8, 2026-07-07: **no v1 pack opts in** — lo-fi is anti-climax, blues doesn't use risers, fusion builds by arrangement; stays dormant post-v1) | Post-v1 | the device slot and vocabulary position are reserved here |
| Q3 | True fade via a document-level automation lane (CC11/master-gain analog) | Post-v1 | `TrackDocument` automation extension (relates to PHASE_1 Q7's debug-block precedent for additive schema growth) |
| Q4 | SHOT (choked-hit) cold variant as a `close` enum extension (PHASE_8 §3.8, 2026-07-07: **deferred** — blues band-hit endings are finals-pool + ending-pattern content under `cold`) | Post-v1 | PHASE_3 §4.1 enum amendment; BiaB's shot/hold split is the model |
| Q5 | Stop-time choruses and `kind: break` pattern semantics (PHASE_5 Q5 remainder) (PHASE_8 §3.8, 2026-07-07: **deferred post-v1** — requires load-bearing `variant`, PHASE_8 §12 Q2) | Post-v1 | load-bearing `variant`; PHASE_5 §3.2's fill-eligibility amendment path |
| Q6 | Fill lay-out / unison-hit variants for non-drum roles during big fills | Phase 8 | listening evidence that always-play reads as stiff at max-energy boundaries |
| Q7 | ~~Per-pack `feel.yaml` overrides?~~ **Resolved** — the two-table model provably fails at five packs (lo-fi laid-back vs fusion tight, both swung); resolved as named engine profiles + a pack `feelTable` selector, never per-pack value authoring (PHASE_8 §3.4/D5, 2026-07-07; §5.3 amended) | ~~Phase 8~~ | — |
| Q8 | Mutation operators for pattern-mode bass (octave pop, passing-tone toggle)? (PHASE_8 §3.8, 2026-07-07: **re-deferred with evidence** — all three new packs are patterns-mode bass, and in each genre the locked bass loop is the idiom: boogie cell, fusion ostinato, static sub) | Post-v1 | listening evidence; operator vocabulary is additive |
| Q9 | Walker repeated-note polish (PHASE_5 Q9) — unchanged, stays post-v1; the humanizer does not re-pitch | Post-v1 | listening evidence |

---

## 10. Amendments to earlier documents (this session)

All additive/clarifying; applied in the same commit as this document:

1. **ROADMAP §3 pipeline diagram**: "4-bar pattern mutation" moves from the stage-7 (Humanizer) line to stage 6 (Transition engine), restated as "pattern mutation (2-bar units)" (D1, D8 — the PHASE_3 D11 refinement precedent). **ROADMAP §2**: decisions-log row added for the Phase 6 model. **ROADMAP §4 Phase 6 bullet**: "mutate patterns slightly every 4 bars" annotated with the 2-bar-unit refinement; "ghost notes" annotated as authored in Phase 5, modulated here.
2. **PHASE_1 §4 pipeline recap**: stage 7 output annotated `Phrase[] + tempo events` (§6).
3. **PHASE_1 §4.5**: `tags` vocabulary annotated — PHASE_6 contributes `"fill"`, `"crash"`, `"var"`, `"hold"`.
4. **PHASE_1 §7 Q5**: resolved — PPQ 480 confirmed (D16).
5. **PHASE_1 §6 pack layout**: `transitions.yaml` added, schema owned by Phase 6 (§4).
6. **PHASE_5 §3.2 completeness rules**: PT12 added — ≥ 1 ungated `kind: fill` drum pattern per pack (= TR5); fill selection respects `eligibility.tempoBpm` (no new eligibility dimensions needed in v1 — the reserved amendment slot stays open for Phase 8).
7. **PHASE_5 §8.2**: `crash` row annotated (emitted by Phase 6; default dur 1440).
8. **PHASE_5 §8.1/§8.3**: transitions/humanize stubs replaced by these stages; Serializer consumes `tempoEvents` (§6).
9. **PHASE_5 §11 Q5**: partially resolved (v1 stop needs no break patterns; remainder → Phase 8). **PHASE_5 §11 Q9**: disposition confirmed post-v1 (§9 Q9).
10. **PHASE_2 §7.2**: `dynamicsRange` row annotated with its concrete consumption (velocity-jitter width, PHASE_6 §5.5).

---

## 11. Definition of done

Phase 6 is **built** when an implementation session demonstrates:

1. **Loader**: `transitions.yaml` parsing into frozen pydantic models; TR1–TR7 implemented with one rejection fixture per rule class; both reference files load clean; fill windows computed and cached; PT12 enforced against both reference packs.
2. **Feel data**: `src/trackgen/humanize/feel.yaml` matching §5.3 exactly; validator caps (offsets ≤ 25 ms, jitter ≤ 10 ms, |accent| ≤ 0.05) enforced with rejection fixtures.
3. **Transitions stage**: implements §3 exactly; golden tests asserting both §7 device narratives (placements, selections, exact draw counts: pop 14 devices + 38 + 9 mutation, jazz 10 + 32 + 11) and the fired-op lists **verbatim**, including the four documented no-ops.
4. **Rendering goldens**: pop fill bar 3 (§7.1) note-for-note; a crash+kick entry with and without an existing kick (pop bar 12, jazz bar 12); one mutated unit per operator class (including pitches-preserved `anticipate` and the ≥ 2-attacks `drop_hit` guard); HOLD renderings for both examples (extensions, deletions, +0.05 bumps, tags).
5. **Humanizer stage**: unit tests for §5.2 swing (offbeat-only, both subdivisions, gap-preserving stretch, straight-pack no-op), §5.3 offset application (both feel tables, ms→tick at both reference tempi), §5.4/§5.5 `tri` distribution bounds and draw-skip at w = 0, accent map, dynamicsRange width formula, §5.6 bass legato (both feels + final-note exemption); a golden excerpt test asserting jazz head-1 bar 0 (§7.2) pre-jitter positions exactly.
6. **Ritard**: golden test asserting the jazz tempo-event list (39 events, endpoints and §7.2 table values exact); property: monotone decreasing, never ≤ 0.5 × base, first event > tick 0 of the tag, none after the final downbeat sample; cold/fade emit zero events; fade renders identically to cold (alias test).
7. **Determinism**: repeated-run identity through both stages; counting-RNG shims asserting the exact per-stream/sub-stream draw counts for both examples; per-unit and per-bar sub-stream isolation tests (regenerating one unit/bar reproduces its draws in isolation); the note-count-preservation invariant asserted on the Humanizer for both full examples.
8. **Synthetic fixtures**: a stop-heavy odds pack fixture exercising §3.4 rendering end-to-end; a `breakdown` form fixture exercising §3.5 dropout; a fill bank with only rung-1 fills exercising the fallback chain both directions.
9. **Property tests**: every pack × supported mood × lengths × 25 seeds → fills only in legal fill bars; no drum groove event inside a rendered window; crash suppression honored for postchorus/breakdown; no note before tick 0 or past song end; non-drum `midi` values untouched by both stages (C5 ceiling); backbeat-class snare events (velocity ≥ 0.7 at back2/back4) never removed or moved by mutation; every document still passes V1–V8.
10. **Milestone**: both worked examples regenerate end-to-end through the real stages (stubs deleted), serialize, and play in the Phase 1 playground; listening checklist — fills lead every section change and resolve onto an audible crash; the jazz ritard reads as a band slowing, not steps; the pop ending rings and releases together; no bar loops byte-identically (diff test); the swing feel survives the ritard.
11. **Amendments** (§10) applied and consistent.

---

## 12. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §4: placement odds, stop gating, crash ranges, mutation tables — all YAML; fills are pack patterns; engine owns algorithms parameterized by pack data (PHASE_5 D15 lineage); `feel.yaml` is engine data like `moods.yaml` |
| 2. Rhythm stored separately from pitch | This phase never resolves degrees or re-pitches: fills are unpitched drum events; mutations move/remove already-voiced notes (anticipation deliberately preserves pitches — §3.7); the Humanizer never touches `midi` |
| 3. Hierarchical seeds | §3.8/§5.8: two pinned streams, named sub-streams, per-unit/per-bar isolation; rerolling `humanize` re-performs the same notes; rerolling `transitions` re-rolls fills/variation only |
| 4. Soloist owns above ~C5 | No operator or humanizer op changes `midi`; added events are drum-voice only (crash/kick — drums exempt per PHASE_1 D14); property test §11.9 re-verifies |
| 5. Deterministic pipeline | Integer weights; draws only via `weighted_choice`/`randrange` when ≥ 2 outcomes; `tri` built on allowed ops; float math with single terminal rounding; append-only draw order; no wall-clock, no unseeded entropy |
