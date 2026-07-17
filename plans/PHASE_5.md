# PHASE_5 — Rhythm Section Part Generators

Designed 2026-07-07 (session 5). Status: **awaiting approval**.

This document pins pipeline stages 4 and 5 — `SongForm + GenerationPlan → ArrangementPlan` and `ArrangementPlan + HarmonicPlan → Phrase[]` — end to end: the energy→intensity mapping (resolving PHASE_3 §6.5's guidance and PHASE_1 Q2), the shared pattern-selection machinery and its eligibility model (resolving PHASE_1 Q3), the retargeting semantics that turn degree-based pattern events into concrete pitches (pinning the `tension`/`approach` semantics PHASE_1 §6.3 deferred here), the four pattern-bank schemas (`patterns/*.yaml`), the four part generators (drums, bass — including the walking-bass engine, comping — including the voicing pass over PHASE_4's Viterbi optimizer, pads), the pipeline orchestrator and the (intentionally thin) Serializer, and the first end-to-end milestone. It also resolves PHASE_4 Q9 (one new voicing candidate class).

Research base (session 5): the Band-in-a-Box StyleMaker weight/mask system and bass macro-note tokens; the Yamaha SFF/SFF2 style format via the Wierzba & Bedesem specification (Main A–D structure, NTR/NTT transposition rules, RTR retrigger rules, note-limit octave folding) and JJazzLab's YamJJazz engine; Korg Pa additive-variation conventions; MMA's degree-encoded pattern tuples, WALK/BASS track split, voicing modes, and velocity ladder; walking-bass pedagogy (Friedland, Reid, StudyBass's rhythmic-weight framework) and the Dias & Guedes target-note/trajectory walking-bass generator (SMC 2013); the FiloBass corpus (Cheston et al. 2023); jazz comping pedagogy (Charleston-family rhythm cells, Bill Evans A/B rootless voicings, Jeb Patton, Jens Larsen) and pop strum/keyboard comping conventions; low-interval-limit tables (Lowell & Pullig lineage); pad-voicing production practice; drum groove corpora on repetition and microtiming; Owsinski's five arrangement elements; and Aebersold/iReal soloist-space conventions.

---

## 1. Scope

**In scope**

- Energy → intensity quantization (global thresholds) and confirmation of the 1–4 intensity ladder.
- The shared pattern-selection algorithm: cache granularity, kind mapping, eligibility (tempo band), completeness rules, RNG discipline.
- Retargeting: the degree-resolution table (with dressing-safe fallbacks), the `push` anticipation flag, anchor-based octave placement with lane folding, `onChordChange` semantics, and two degree-vocabulary extensions (`sixth`, `chord`).
- Velocity (`dynamicsBase`) and articulation (`articulationLegato`) application rules, and the `minDensity` density-gating mechanism.
- The Arrangement planner: role activation (layering order + count rules), density-budget formula, register lanes and `registerBias` application, generation order; all three `ArrangementPlan` extension points PHASE_1 §4.4 reserved are resolved.
- The four pattern-bank schemas (`patterns/drums.yaml`, `bass.yaml`, `comping.yaml`, `pads.yaml`) with validation rules and normative reference content for `pop_rock` and `jazz`.
- The four part generators, including the walking-bass engine (algorithm + parameters) and the comping/pads voicing pass over PHASE_4's `optimal_voicing_path`.
- The pipeline orchestrator, the Serializer (format fully pinned by PHASE_1; built here), the drum-voice→track mapping, and stub policies for the not-yet-built stages (6, 7).
- The end-to-end milestone: both chained worked examples generate valid, playable `TrackDocument`s.
- Amendments to earlier documents (all additive, §12).

**Explicitly not in scope**

- Fills, transitions, crashes, risers, stops (Phase 6 — fill *patterns* are authored here under the pinned envelope; their selection and placement are Phase 6's). Kind `break` is schema-legal but unused until Phase 6/8.
- Swing rendering, velocity accent maps, jitter, micro-timing, pattern mutation (Phase 6). All patterns are authored on the straight grid; Phase 5 output is straight.
- Concrete Tone.js patches and mixing (Phase 7) — the milestone uses hand-authored stub `timbres.yaml` files marked provisional.
- Style-pack content beyond the two reference packs (Phase 8).
- Runtime kick/bass alignment (reserved hook, §6.3; v1 uses authoring convention).

---

## 2. Contracts consumed

| Upstream contract | What this phase does with it |
| --- | --- |
| `GenerationPlan` (PHASE_1 §4.1, PHASE_2 §7) | `budgets.noteDensity` → density budgets (§4.2); `budgets.dynamicsBase` → velocity shift (§3.4); `budgets.articulationLegato` → duration scaling (§3.4); `budgets.layersMax` → activation cap (§4.1); `budgets.registerBias` → lane shift (§4.3); `moodVector` not consumed directly (energy already encodes it); `swing` not consumed (Phase 6 renders it); `tempoBpm` → eligibility gates, walker embellishment gate; `roleFlavors` passed through to Phase 7. |
| `SongForm` (PHASE_1 §4.2, PHASE_3 §4) | `sections[].energy` → intensity + density; `type` → kind mapping + activation modifiers; `phrases` → pattern tiling alignment; `ending` untouched (Phase 6 renders; the bass walker's final-bar rule and kind `ending` banks cover this phase's contribution). |
| `HarmonicPlan` (PHASE_1 §4.3, PHASE_4 §7) | `chords` govern every retargeted event; per-event `scale` feeds `tension`/`approach`/walker pools; `bassPc` honored by the bass role; `tags` (`turnaround`/`final`) visible to the walker's final-bar rule; `keys` unused (single region in v1). |
| Section semantics table (PHASE_3 §3.2, arrangement column) | Implemented by §4.1's modifiers: intro thinner than what follows, breakdown minimal, bridge thinner, chorus fullest within budgets. |
| Theory library (PHASE_4 §8) | `chord_intervals`/`chord_tones`/`guide_tones`/`scale_pcs` drive degree resolution; `voicing_candidates` (+ the new `fifths` class), `vl_distance`, `optimal_voicing_path` drive the comping/pads voicing pass. Phase 5 sets *policy*: per-role candidate classes (pack data, §5.4) and per-role cost weights (§6.4/§6.5), as PHASE_4 D11 assigns. |
| Pattern envelope & event primitives (PHASE_1 §6.2/§6.3) | Envelope consumed as pinned; `eligibility` and `retarget` extension slots filled here (§3.2, §3.3); event vocabulary extended additively (`sixth`, `chord`, `push`, `minDensity`). |
| Seed system (PHASE_1 §5) | Streams `arrangement, drums, bass, comping, pads`; named sub-streams via `derive` chaining (§3.6); all draws via `weighted_choice`, integer weights, draws only when ≥ 2 candidates (PHASE_3 D13), append-only order. |
| `Phrase` (PHASE_1 §4.5) | Produced exactly as pinned; `tags` vocabulary contributions: `"ghost"`, `"push"` (§8.1). |
| Determinism rules (PHASE_1 §5.3) | Integer weights; ordered/sorted candidate lists (ascending pitch for walker pools); integer-cost Viterbi (PHASE_4 D16); 3-decimal half-even rounding for emitted velocities and density budgets. |

---

## 3. Cross-cutting foundations

### 3.1 Energy → intensity (resolves PHASE_1 Q2, PHASE_3 §6.5)

The intensity ladder stays **1–4** — the industry consensus (Yamaha Main A–D, Korg Variation 1–4). Quantization is a global engine threshold table (engine-owned data, `src/trackgen/arrangement/intensity.yaml`):

| Rung | Energy |
| --- | --- |
| 1 | e < 0.30 |
| 2 | 0.30 ≤ e < 0.55 |
| 3 | 0.55 ≤ e < 0.80 |
| 4 | e ≥ 0.80 |

One ladder for all packs: pack `energyRange` envelopes (PHASE_3 §6.4) already position each style's dramaturgy on it — the same mechanism as PHASE_4's dissonance tiers. Calibration against the PHASE_3 worked examples: pop/happy → intro 2, verses 2/2, choruses 3/4/4, bridge 2; jazz/melancholic → heads 2, solos 3/3/3, outro 2. Both verses share a rung (repeat consistency); choruses escalate 3→4; the jazz head/solo split lands exactly on the two-feel/four-feel boundary (§6.3).

### 3.2 Pattern selection

**Cache granularity: one draw per (role, kind, rung) per song.** Sections map to kinds: `intro` → `intro`, `outro` → `ending`, everything else → `main`. Selection iterates sections in form order; the first section needing an unfilled cache key selects a pattern; later sections reuse it. Consequences: same-rung sections share their groove (verse 1 ≡ verse 2 — the corpus-repetition finding and PHASE_4 D7's logic applied to rhythm); chorus (rung 3) vs final chorus (rung 4) differ — the Yamaha Main C→D move. Intra-section variety is Phase 6's charter (mutation every 4 bars), not this stage's.

- Eligible set for `main`: patterns of the role with `kind: main` and `energyLevel == rung`, passing the eligibility gate. For `intro`/`ending`: all patterns of that kind passing eligibility (`energyLevel` ignored — these banks are small and section-scoped).
- Selection = `weighted_choice` over eligible in authored order, **draw iff ≥ 2** (PHASE_3 D13), on the role's `select` sub-stream (§3.6).
- Sections of type `breakdown` use `main` patterns at their (low) rung; `kind: break` is reserved for Phase 6/8.
- **Tiling**: the selected pattern instantiates per *phrase* (PHASE_3 phrase starts are the pinned alignment points), repeating to fill the phrase and truncating at its end. All v1 patterns are 1–2 bars; phrases are multiples of 4 bars, so tiling is exact.

**Eligibility (resolves PHASE_1 Q3)** — one dimension in v1:

```yaml
eligibility: { tempoBpm: [min, max] }   # optional; pattern eligible iff min ≤ plan.tempoBpm ≤ max
```

Everything else in the research catalog (bar-position masks, post-fill, chord-type/next-chord-motion conditions) is either made unnecessary by per-rung caching and degree abstraction, handled structurally (positional variation authored *inside* multi-bar patterns), or owned by Phase 6 (fill-specific dimensions — Phase 6 may add eligibility fields for `kind: fill`/`break` patterns by amending this section; PHASE_6, 2026-07-07: no new dimensions needed in v1 — the slot stays open for Phase 8).

**Completeness rules** (loader; the F13/P6 pattern — selection can never come up empty):

- Per role with a pattern bank: ≥ 1 `main` pattern with **no** eligibility gate at **each** rung 1–4; ≥ 1 ungated `intro`; ≥ 1 ungated `ending`.
- A bass bank with `mode: walking` (§5.3) is exempt — the walker serves every section and kind.
- **PT12** (added by PHASE_6 §10.6, 2026-07-07): the drum bank carries ≥ 1 ungated `kind: fill` pattern — Phase 6's fill resolution (destination rung + nearest-rung fallback) can never come up empty. Fill selection also respects `eligibility.tempoBpm`.

### 3.3 Retargeting: degrees → pitches

Every pitched pattern event resolves against the `ChordEvent` governing its absolute tick (its **governing chord**). Degree resolution, using PHASE_4 §8 tables:

| Degree | Resolves to | Fallback when the quality lacks it |
| --- | --- | --- |
| `root` | `rootPc`; **bass role**: `bassPc` if present, else `rootPc` (the Yamaha NTT-Bass slash rule) | — |
| `third` | the quality's third slot — the 2nd interval of the §8.1 stack (sus2 → 2nd, sus4 → 4th) | — |
| `fifth` | the quality's fifth (dim → ♭5, aug → ♯5) | — |
| `sixth` | the 6th interval (maj6/min6) | the chord-scale's 6th degree |
| `seventh` | the 7th interval | maj6/min6 → the 6th; triads → the fifth |
| `guide3` | `guide_tones().third` | — |
| `guide7` | `guide_tones().seventh` | triads → the fifth |
| `tension` | first entry of `extensions` (semitone offset per §8.1) | no extensions → the chord-scale's 2nd degree (scale-correct 9th: ♭9 over `altered`, ♮9 over `dorian`, …) |
| `approach` | chromatic **half-step below** the *next* chord event's effective root, in the octave nearest that target's placement | no next chord (song end) → `root` |
| `chord` | the event sounds the governing chord's **voicing** from the role's voicing pass (§6.4) — placement/anchor rules do not apply | — |

`sixth` and `chord` are additive extensions of PHASE_1 §6.3's vocabulary (permitted there); `sixth` exists for the blues boogie cell (Phase 8's first need), `chord` for comping/pads (§6.4). Half-step-below is the sole v1 approach direction (the research's signature device); above/diatonic pattern-degree variants are a Phase 8 vocabulary extension (§11 Q3). The fallback column exists because dressing (PHASE_4 §6) changes qualities per mood — one authored pattern must resolve sensibly whether its chorus chord came out `C`, `Cmaj7`, or `Cmaj9`.

**Anticipation — the `push` flag.** Pattern events may set `push: true`. A pushed event resolves against the chord in effect immediately **after** the next chord-event boundary that falls within the note's span `(ticks, ticks + durationTicks]`; if no boundary falls in the span, it resolves normally. This is the BiaB "pushed pattern" mechanism: the and-of-4 comping hit and the pop bass push sound the incoming chord. Pushed `chord` events sound the next event's voicing. Pushed notes are emitted with tag `"push"`.

**Octave placement** (single-degree events): `anchor` = midpoint of the intersection of the pattern's `retarget` register and the role's arrangement lane (the lane alone if disjoint). The degree's pc is placed in the unique octave within `(anchor − 6, anchor + 6]`, then shifted by `12 × octave` (the event's authored offset), then **folded by octaves to the nearest position inside the lane** (ties resolve downward) — the Yamaha note-limit rule. Lanes span ≥ 12 semitones (validator), so folding always succeeds.

**`onChordChange`** (the pinned `retarget.onChordChange`, applied when an un-pushed note's span crosses a chord boundary):

| Value | Behavior |
| --- | --- |
| `hold` | note keeps sounding as attacked (old-chord tone rings over the new chord) |
| `retrigger` | note ends at the boundary; a new note attacks there, re-resolved against the new chord, for the remainder (remainders < 60 ticks are dropped) |
| `stop` | note truncates at the boundary |

Schema default for pitched roles: `retrigger` (the adaptation of Yamaha's pitch-shift RTR family to a format without pitch bend). Drum events carry no harmonic content and are exempt.

### 3.4 Velocity and articulation

- **Velocity (all roles)**: `velocity = round3(clamp(authored + 0.4 × (dynamicsBase − 0.5), 0.05, 1.0))`. Additive, so authored accent relationships (ghost ≈ 0.2–0.3 vs backbeat ≈ 0.85–1.0) survive at every mood; the center moves ± 0.2 max. Identity at `dynamicsBase = 0.5`. Phase 6 adds accent maps, jitter, and `dynamicsRange` on top.
- **Articulation (comping + bass pattern mode only)**: `durationTicks = round(authored × (0.7 + 0.6 × articulationLegato))`, clamped to the gap before the same track's next event. Range ×0.7 (staccato moods) to ×1.3 (legato moods), identity at 0.5. **Exempt**: drums (trigger lengths), pads (always sound their full authored duration), and the walker (emits fixed durations; Phase 6 humanizes).

### 3.5 Density gating

Pattern events may carry `minDensity: float ∈ [0,1]`. An event is instantiated iff the section's `densityBudget ≥ minDensity`. This is the *deterministic* mechanism (no draws, no probabilities) by which one pattern audibly thins or thickens across sections of the same rung: ghost snares, extra kicks, 16th pickups, and dense strum subdivisions are authored with thresholds around 0.6–0.75 and simply drop out of low-density sections. Events without the field always play.

### 3.6 Seeds and draw discipline

Top-level streams (PHASE_1 registry): `arrangement` (reserved — **zero draws in v1**; the planner is arithmetic), `drums`, `bass`, `comping`, `pads`. Sub-streams:

- `derive(roleStream, "select")` — pattern selection draws, in section order (§3.2).
- `derive(bassStream, "walk")`, then `derive(walkStream, f"bar:{absoluteBarIndex}")` — one RNG per walked bar (§6.3), so bars draw independently: a changed draw in one bar can never shift another bar's line, and section excerpts are independently reproducible.

Within a walked bar the draw order is fixed: beat-1 decay (if drawn) → beat 3 → beat 2 → approach type. Comping/pads voicing passes make **no draws** (integer Viterbi). Draw sequences are append-only across versions (PHASE_2 §6.1 rule); golden draw-count tests enforce it (§9).

---

## 4. The Arrangement planner

`arrange(plan, form, pack, rng) → ArrangementPlan` — fully deterministic (the `rng` is accepted for interface uniformity and never consumed in v1).

### 4.1 Role activation

The pack declares one ordered layering list in `patterns/manifest` position (§5.1): both reference packs use `[drums, bass, comping, pads]`. Per section:

```
rung   = intensity(energy)                      # §3.1 thresholds
count  = min(layersMax, baseCount[rung])        # baseCount: {1: 2, 2: 3, 3: 4, 4: 4}
if type == intro:      count = max(1, countOf(next section) − 1)
elif type == breakdown: count = min(count, 2)
elif type == bridge:    count = min(count, 3)
active = first `count` roles of the pack's layering order
```

Every `(section, role)` pair gets an entry (pinned core); inactive roles get `active: false`. The additive-layering consequences: jazz/melancholic (`layersMax` 3) is a pads-less trio throughout; pop/happy verses run drums+bass+comping with pads entering at the choruses; intros thin relative to what follows (drums+bass for the pop example — the BiaB drums-first convention generalized).

### 4.2 Density budget

`densityBudget = round3(clamp01(noteDensity × (0.7 + 0.6 × energy)))` — identical for every active role in the section (per-role character comes from patterns; a per-role factor is deliberately not introduced, §11 Q1). Consumed via §3.5 gating and the walker's embellishment rate (§6.3).

### 4.3 Register lanes

Engine data (`src/trackgen/arrangement/lanes.yaml`):

| Role | Lane (MIDI) | Rationale |
| --- | --- | --- |
| `drums` | exempt (0–127) | trigger pitches are timbre parameters (PHASE_1 D14) |
| `bass` | 28–55 (E1–G3) | instrument range / working band from the research |
| `comping` | 48–71 (C3–B4) | low-interval limit (close voicings ≥ C3); C5 ceiling |
| `pads` | 43–71 (G2–B4) | open/3rd-omitted voicings tolerate the lower floor |

`registerBias` shifts the **comping and pads** lanes by `round(bias × 12)` semitones (round-half-even), clamped so `highMidi ≤ 71`; bass and drums never shift. Worked values: pop (+0.188) → comping 50–71, pads 45–71; jazz (−0.125) → comping 46–69, pads 41–69. The validator re-checks `highMidi ≤ 71` on every non-drum entry (PHASE_1 §4.4).

### 4.4 Extension points (PHASE_1 §4.4 — now resolved)

- **Layering order**: lives in the pack (§4.1/§5.1) — no `ArrangementPlan` field needed.
- **Per-role articulation directives**: closed, none added. Bass feel keys off the intensity rung (§6.3); `articulationLegato` is consumed directly from budgets (§3.4).
- **Lane-interaction rules**: closed, none added. Kick/bass locking is an authoring convention in v1 (§6.3); the generator interface reserves the runtime hook (§11 Q2).

**Generation order (pinned)**: `drums → bass → comping → pads`. Part generators receive the phrases of earlier roles; in v1 no generator consumes them (the reserved kick-lock hook), but the order is contract so adding that pass is non-breaking.

### 4.5 Worked arrangement (both examples — computed)

Pop/happy (`noteDensity` 0.648, `layersMax` 4, bias +0.188):

| Section | energy | rung | count | densityBudget | active |
| --- | --- | --- | --- | --- | --- |
| intro-1 | 0.340 | 2 | 2 | 0.586 | drums, bass |
| verse-1 | 0.490 | 2 | 3 | 0.644 | drums, bass, comping |
| chorus-1 | 0.790 | 3 | 4 | 0.761 | + pads |
| verse-2 | 0.540 | 2 | 3 | 0.664 | drums, bass, comping |
| chorus-2 | 0.840 | 4 | 4 | 0.780 | + pads |
| bridge-1 | 0.440 | 2 | 3 | 0.625 | drums, bass, comping |
| chorus-3 | 1.000 | 4 | 4 | 0.842 | + pads |

Jazz/melancholic (`noteDensity` 0.505, `layersMax` 3, bias −0.125): head-1/head-2 — rung 2, count 3, density 0.494; solo-1/2/3 — rung 3, count 3, densities 0.543 / 0.567 / 0.591; outro-1 — rung 2, count 3, density 0.458. Active everywhere: drums, bass, comping (pads capped out by `layersMax` — the trio).

---

## 5. Pattern-bank schemas

All four files share PHASE_1 §6.2's pinned envelope (`id, role, kind, energyLevel, lengthTicks, weight, eligibility, events, retarget`) with the extensions pinned in §3. Common event-field extensions (additive to PHASE_1 §6.3): `minDensity` (any event), `push` (pitched events), degrees `sixth`/`chord` (pitched events).

### 5.1 Pack-level additions

```yaml
# patterns/manifest section — one per pack (top of drums.yaml or a shared patterns/_meta.yaml)
layeringOrder: [drums, bass, comping, pads]    # ordered; must contain all four roles exactly once
```

### 5.2 `patterns/drums.yaml`

Envelope + drum events (`{pos, voice, velocity, dur?, minDensity?}`; `dur` optional, defaulting per voice — §8.2). No `retarget` block (drums exempt). Conventions (normative for reference packs): mains never use `crash` (Phase 6 owns boundary crashes); mains 1–2 bars; fills 1 bar; authored velocities — primaries 0.85–1.0, ghosts 0.2–0.3, closed hats 0.4–0.65 with quarter accents; jazz ride 0.65–0.75 sitting *above* its snare/kick comping hits (0.3–0.5).

### 5.3 `patterns/bass.yaml`

```yaml
mode: patterns | walking        # top-level, required
walking:                        # required iff mode: walking
  feelByIntensity: {1: two, 2: two, 3: four, 4: four}
  approachWeights: {chromatic_below: 2, diatonic: 1, dominant: 1}   # integer weights
  beat1RepeatWeights: {fifth: 2, third: 1, root: 1}                 # integer weights
patterns: [...]                 # required iff mode: patterns (envelope entries)
```

`mode: walking` banks carry no patterns and are exempt from completeness (§3.2); the walker (§6.3) serves every section. `mode: patterns` banks follow the standard envelope with pitched events.

### 5.4 `patterns/comping.yaml` and `patterns/pads.yaml`

```yaml
voicing:                        # required for comping and pads
  classes: {1: [shell2, shell3], 2: [shell2, shell3],
            3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}
patterns: [...]
```

`classes` maps each rung 1–4 to a non-empty ordered list of PHASE_4 §8.4 candidate classes (now including `fifths`, §6.5). Patterns use `degree: chord` hits for voiced material; single-degree events remain legal for authored color lines.

### 5.5 Validation rules (loader; each class gets a rejection fixture)

- **PT1** envelope: `id` unique per pack; `role` matches the file; `kind` in enum; `energyLevel` int 1–4; `lengthTicks` a positive whole number of bars; `weight` int ≥ 1; `kind: fill` patterns exactly 1 bar.
- **PT2** events: `pos` int ≥ 0 and < `lengthTicks`; `dur` int ≥ 1 where present; `velocity ∈ (0, 1]`; events ordered by `pos` as authored.
- **PT3** vocabulary: drums events carry `voice` from PHASE_1 §6.3's list and never `degree`/`push`/`octave`; pitched events carry `degree` from the §3.3 vocabulary.
- **PT4** `eligibility.tempoBpm`: ints, `0 < min ≤ max`.
- **PT5** completeness per §3.2 (mains × 4 rungs + intro + ending, all ungated), `mode: walking` exempt.
- **PT6** `mode` only in `bass.yaml`; `walking` block present iff `mode: walking`, with `feelByIntensity` covering rungs 1–4 (values `two|four`) and integer weight maps non-empty.
- **PT7** `voicing.classes` present in comping/pads, covering rungs 1–4, class names from PHASE_4 §8.4 ∪ {`fifths`}.
- **PT8** `minDensity ∈ [0, 1]`; `push` boolean, pitched events only.
- **PT9** `retarget` present on pitched-role patterns: `registerLow < registerHigh`, span ≥ 12, `onChordChange` in enum.
- **PT10** `layeringOrder` present once per pack, a permutation of the four roles.
- **PT11** strict schema — unknown keys rejected (pydantic).

---

## 6. Part generators

All generators share the instantiation loop: for each section where the role is active, for each phrase, tile the cached pattern (§3.2); resolve each event via §3.3 (skipping `minDensity`-gated events per §3.5); apply §3.4 velocity/articulation; emit one `Phrase` per (track, section) with notes sorted `(ticks, midi)`.

### 6.1 Drums

Tracks per §8.2's voice→track mapping; one Phrase per active voice-track per section. Rung content conventions (normative for the reference banks): pop/rock — 1: kick 1+3, quarter hats; 2: money beat; 3: + `minDensity`-gated ghost snares, open-hat accents, busier kick (2-bar); 4: ride/open-hat drive, denser kick (2-bar). Jazz — 1: brush sweeps + hats 2/4; 2: straight-grid ride pattern (1, 2, 2&, 3, 4, 4&) + hats 2/4; 3: + snare/kick comping hits (2-bar); 4: dense up-tempo ride + active comping. (Straight grid throughout; the swing ratio renders these as spang-a-lang in Phase 6.)

### 6.2 Bass — pattern mode

Standard instantiation. Rung conventions: 1 — whole/half roots; 2 — quarter roots; 3 — 8ths with `fifth` motion and a `push`-flagged bar-end root (2-bar); 4 — driving 8ths with `octave`-offset pops, `minDensity`-gated 16th pickups, pushes (2-bar). Kick coherence is an **authoring convention**: the pack author writes bass rung *N* against drums rung *N* (the Yamaha/BiaB reality). The runtime alignment hook stays reserved (§4.4, §11 Q2).

### 6.3 Bass — walking mode (the walker)

Engine algorithm, parameterized by §5.3 pack data. Per active section, feel = `feelByIntensity[rung]`; pitch state (previous emitted pitch) resets at section start; per-bar RNG = `random.Random(derive(derive(bass, "walk"), f"bar:{absBar}"))`.

**Shared placement helper**: `nearest(pc, ref)` = the lane pitch of class `pc` minimizing `(|p − ref|, p)` — deterministic tie-break downward.

**Two-feel** (`feel: two`, half notes, dur 960):

1. Final bar of the song's final section: emit one whole-note root at the **lowest** in-lane placement; stop.
2. Two chords in the bar → one half-note root per chord, `nearest` to the previous pitch.
3. Else beat 1 = root (`nearest`); beat 3 = fifth — placed a P4 below or P5 above beat 1; **draw 1:1 iff both fit the lane**, else the one that fits. An extra quarter-note approach on beat 4 is added when the next bar changes chord **and** `densityBudget ≥ 0.55`.

**Four-feel** (`feel: four`, quarter notes, dur 480):

1. Beat 1: root — except on the 2nd+ consecutive full bar of the same chord, where the degree is drawn from `beat1RepeatWeights` (fifth 2 · third 1 · root 1 — root-obligation decay). Placement `nearest` to the previous pitch.
2. Two chords in the bar → root(chord 1), approach(→ chord 2 root), root(chord 2), approach(→ next bar's target).
3. Beat 3 (filled before beat 2 — strongest-first, the Dias & Guedes recursion): candidates = in-lane chord-tone pitches within 7 semitones of both beat 1 and the next bar's target, excluding both; weight 3 if within 2 semitones of the beat1↔target midpoint, else 1; draw iff ≥ 2. (Empty → relax to within 12 of beat 1.)
4. Beat 2: candidates = in-lane chord + scale tones (the event's `scale`) 1–4 semitones from beat 1, excluding beat 3's pitch; weight 3 if ≤ 2 semitones (stepwise preference); draw iff ≥ 2. (Empty → relax to within 7.)
5. Beat 4: approach to the next bar's target, type drawn from `approachWeights`: `chromatic_below` → target − 1; `diatonic` → first scale tone below the target; `dominant` → target + 7 (folded into the lane). Result folded into the lane.
6. Embellishment: on bars where `barInSection % N == N − 1` (N = 4 if `densityBudget < 0.55` else 2), suppressed when `tempoBpm > 200`: a dead-note ghost (dur 60, velocity 0.25 pre-shift, tag `"ghost"`) on the and-of-4 repeating the beat-4 pitch.

Candidate lists are materialized in ascending pitch order (stable key) before drawing. The next bar's *target* is the root of the chord governing the next bar's downbeat (`nearest` to beat 1); at song end the current root substitutes.

**Walker velocities (authored values, pre-§3.4 shift)**: four-feel — beat 1 `0.75`, beats 2–4 `0.68`; two-feel — beat 1 `0.72`, beat 3 (and any beat-4 approach) `0.68`; final whole note `0.75`; dead-note ghosts `0.25`. Durations: two-feel 960, four-feel 480, final bar 1920, ghosts 60 — fixed (articulation-exempt per §3.4; Phase 6 humanizes).

### 6.4 Comping

Rhythm from `degree: chord` patterns (cells per rung — jazz: footballs → Charleston family → Charleston + anticipated-4& push / Red Garland → dotted-quarter cross-rhythm; pop: whole-note blocks → downbeat halves → "old faithful" strum shape → pulsing 8ths). Pitches from the **voicing pass**: once per song, `optimal_voicing_path` (PHASE_4 §8.6) runs over the *entire chord timeline* in order (all events, including sections where comping is inactive — harmless, and it keeps the DP's indices trivially aligned with the plan). Per-event candidate classes = `voicing.classes[rung of the event's section]`; lane = the role's bias-shifted lane; weights = PHASE_4 defaults (move 4, top 4, common 3, drift 1); anchor = `lane.high − 6` (top voices settle in the C4–C5 research zone). Unequal-cardinality comparisons (shell2 → rootless_a at a section boundary) pad the shorter voicing with its own top pitch (the Phase 5 caller policy PHASE_4 §8.5 delegates). A/B-form alternation is not ruled in — it *emerges* from cost minimization (§9 shows it doing so). Pushed hits sound the next event's voicing.

### 6.5 Pads

Chord-hit patterns of whole/half notes, `onChordChange: retrigger`, authored velocities 0.4–0.6, articulation-exempt. Voicing pass identical to §6.4 with pads classes and stillness weights: **move 4, top 2, common 5, drift 1**. New candidate class (resolves PHASE_4 Q9, amending its §8.4 table):

| Class | Formula |
| --- | --- |
| `fifths` | {root, root+7, root+12} — the 3rd-omitted pad stack from production practice |

Jazz pads use `quartal`; pop pads use `fifths`. Energy gating falls out of the layering order (pads activate last).

---

## 7. Reference pattern banks (normative)

Content is reference-quality (refined in Phase 8); schema and these fixtures are normative golden-test data. Velocities/durations are authored (pre-§3.4). `retarget` defaults per file: bass `{registerLow: 28, registerHigh: 45, onChordChange: retrigger}`, comping `{52, 67, retrigger}`, pads `{45, 64, retrigger}` (shown once; entries may override).

### 7.1 `styles/pop_rock/patterns/drums.yaml` (events abridged to the defining voices)

```yaml
layeringOrder: [drums, bass, comping, pads]
patterns:
  - { id: pr_dr_1, kind: main, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, voice: kick, velocity: 0.90}, {pos: 960, voice: kick, velocity: 0.85},
      {pos: 480, voice: snare, velocity: 0.75}, {pos: 1440, voice: snare, velocity: 0.72},
      {pos: 0, voice: hat_closed, velocity: 0.55}, {pos: 480, voice: hat_closed, velocity: 0.45},
      {pos: 960, voice: hat_closed, velocity: 0.50}, {pos: 1440, voice: hat_closed, velocity: 0.45}]}
  - { id: pr_dr_2a, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 3, events: [
      {pos: 0, voice: kick, velocity: 0.92}, {pos: 960, voice: kick, velocity: 0.88},
      {pos: 480, voice: snare, velocity: 0.85}, {pos: 1440, voice: snare, velocity: 0.82},
      # 8th-note hats, quarters accented
      {pos: 0, voice: hat_closed, velocity: 0.58}, {pos: 240, voice: hat_closed, velocity: 0.40},
      {pos: 480, voice: hat_closed, velocity: 0.48}, {pos: 720, voice: hat_closed, velocity: 0.40},
      {pos: 960, voice: hat_closed, velocity: 0.55}, {pos: 1200, voice: hat_closed, velocity: 0.40},
      {pos: 1440, voice: hat_closed, velocity: 0.48}, {pos: 1680, voice: hat_closed, velocity: 0.42}]}
  - { id: pr_dr_2b, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 1, events: [
      # four-on-the-floor variant
      {pos: 0, voice: kick, velocity: 0.90}, {pos: 480, voice: kick, velocity: 0.85},
      {pos: 960, voice: kick, velocity: 0.88}, {pos: 1440, voice: kick, velocity: 0.85},
      {pos: 480, voice: snare, velocity: 0.80}, {pos: 1440, voice: snare, velocity: 0.78},
      {pos: 0, voice: hat_closed, velocity: 0.50}, {pos: 240, voice: hat_closed, velocity: 0.38},
      {pos: 480, voice: hat_closed, velocity: 0.46}, {pos: 720, voice: hat_closed, velocity: 0.38},
      {pos: 960, voice: hat_closed, velocity: 0.48}, {pos: 1200, voice: hat_closed, velocity: 0.38},
      {pos: 1440, voice: hat_closed, velocity: 0.46}, {pos: 1680, voice: hat_closed, velocity: 0.40}]}
  - { id: pr_dr_3, kind: main, energyLevel: 3, lengthTicks: 3840, weight: 1, events: [
      # bar 1 = money beat (as pr_dr_2a); bar 2 adds ghost + extra kick + open hat:
      # ... bar-1 events at pos 0–1680 as pr_dr_2a ...
      {pos: 3000, voice: snare, velocity: 0.25, minDensity: 0.70},   # ghost, a-of-3 bar 2
      {pos: 3120, voice: kick, velocity: 0.80, minDensity: 0.65},    # and-of-3 kick, bar 2
      {pos: 3600, voice: hat_open, velocity: 0.60, dur: 360}]}       # 4& open hat, bar 2
  - { id: pr_dr_4, kind: main, energyLevel: 4, lengthTicks: 3840, weight: 1, events: [
      # ride 8ths both bars (on-beat 0.62 / off-beat 0.50), kick 1, 2&(minDensity 0.60), 3;
      # snare 2/4 at 0.92/0.90; bar-2 ghost (0.28, minDensity 0.70) + 4& open hat 0.65
      # (fully enumerated in the pack file)
      {pos: 0, voice: ride, velocity: 0.62}, {pos: 240, voice: ride, velocity: 0.50}]}   # …
  - { id: pr_dr_i, kind: intro, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, voice: kick, velocity: 0.85},
      {pos: 0, voice: hat_closed, velocity: 0.50}, {pos: 480, voice: hat_closed, velocity: 0.40},
      {pos: 960, voice: hat_closed, velocity: 0.45}, {pos: 1440, voice: hat_closed, velocity: 0.40}]}
  - { id: pr_dr_e, kind: ending, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, voice: kick, velocity: 0.90}, {pos: 960, voice: kick, velocity: 0.85},
      {pos: 480, voice: snare, velocity: 0.80},
      {pos: 0, voice: hat_closed, velocity: 0.50}, {pos: 480, voice: hat_closed, velocity: 0.45},
      {pos: 960, voice: hat_closed, velocity: 0.48}]}
  - { id: pr_dr_f1, kind: fill, energyLevel: 2, lengthTicks: 1920, weight: 1, events: [
      # snare 8th build into the barline (Phase 6 selects/places)
      {pos: 960, voice: snare, velocity: 0.60}, {pos: 1200, voice: snare, velocity: 0.68},
      {pos: 1440, voice: snare, velocity: 0.76}, {pos: 1680, voice: snare, velocity: 0.85}]}
  - { id: pr_dr_f2, kind: fill, energyLevel: 4, lengthTicks: 1920, weight: 1, events: [
      # tom run (Phase 6)
      {pos: 960, voice: tom_high, velocity: 0.75}, {pos: 1200, voice: tom_mid, velocity: 0.78},
      {pos: 1440, voice: tom_low, velocity: 0.82}, {pos: 1680, voice: snare, velocity: 0.88}]}
```

### 7.2 `styles/pop_rock/patterns/bass.yaml`

```yaml
mode: patterns
patterns:
  - { id: pr_bs_1, kind: main, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: root, octave: 0, velocity: 0.70}]}
  - { id: pr_bs_2, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 480, degree: root, octave: 0, velocity: 0.72},
      {pos: 480, dur: 480, degree: root, octave: 0, velocity: 0.66},
      {pos: 960, dur: 480, degree: root, octave: 0, velocity: 0.70},
      {pos: 1440, dur: 480, degree: root, octave: 0, velocity: 0.66}]}
  - { id: pr_bs_3, kind: main, energyLevel: 3, lengthTicks: 3840, weight: 1, events: [
      # bar 1: straight root 8ths (0.74 on-beat / 0.62 off-beat);
      # bar 2: fifth on beat 3&, pushed root into the next bar
      {pos: 0, dur: 240, degree: root, octave: 0, velocity: 0.74},    # … 8ths continue
      {pos: 3120, dur: 240, degree: fifth, octave: 0, velocity: 0.68},
      {pos: 3600, dur: 240, degree: root, octave: 0, velocity: 0.72, push: true}]}
  - { id: pr_bs_4, kind: main, energyLevel: 4, lengthTicks: 3840, weight: 1, events: [
      # driving 8ths (0.78/0.66); bar-2 octave pop + gated 16th pickup + push
      {pos: 2640, dur: 240, degree: root, octave: 1, velocity: 0.70},
      {pos: 3120, dur: 240, degree: fifth, octave: 0, velocity: 0.70},
      {pos: 3480, dur: 120, degree: root, octave: 0, velocity: 0.60, minDensity: 0.75},
      {pos: 3600, dur: 240, degree: root, octave: 0, velocity: 0.75, push: true}]}
  - { id: pr_bs_i, kind: intro, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: root, octave: 0, velocity: 0.68}]}
  - { id: pr_bs_e, kind: ending, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: root, octave: 0, velocity: 0.70}]}
```

### 7.3 `styles/pop_rock/patterns/comping.yaml` / `pads.yaml`

```yaml
# comping.yaml
voicing:
  classes: {1: [triad_close, triad_open], 2: [triad_close, triad_open],
            3: [triad_close, shell3], 4: [triad_close, shell3]}
patterns:
  - { id: pr_cp_1, kind: main, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: chord, velocity: 0.55}]}
  - { id: pr_cp_2, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 900, degree: chord, velocity: 0.62},
      {pos: 960, dur: 900, degree: chord, velocity: 0.58}]}
  - { id: pr_cp_3, kind: main, energyLevel: 3, lengthTicks: 1920, weight: 1, events: [
      # "old faithful" strum shape: D D U U D(push) — accented downs, lighter ups
      {pos: 0, dur: 420, degree: chord, velocity: 0.66},
      {pos: 480, dur: 200, degree: chord, velocity: 0.60},
      {pos: 720, dur: 200, degree: chord, velocity: 0.52},
      {pos: 1200, dur: 200, degree: chord, velocity: 0.54},
      {pos: 1680, dur: 220, degree: chord, velocity: 0.60, push: true}]}
  - { id: pr_cp_4, kind: main, energyLevel: 4, lengthTicks: 1920, weight: 1, events: [
      # pulsing 8ths 0.68/0.55 alternating, final 8th pushed
      {pos: 0, dur: 200, degree: chord, velocity: 0.68},   # … 8ths continue …
      {pos: 1680, dur: 200, degree: chord, velocity: 0.66, push: true}]}
  - { id: pr_cp_i, kind: intro, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: chord, velocity: 0.50}]}
  - { id: pr_cp_e, kind: ending, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: chord, velocity: 0.60}]}

# pads.yaml
voicing: { classes: {1: [fifths], 2: [fifths], 3: [fifths], 4: [fifths]} }
patterns:
  # pr_pd_1..3: whole-note chord (velocity 0.45/0.45/0.50); pr_pd_4: half-note pulse 0.55/0.50
  # pr_pd_i / pr_pd_e: whole-note chord 0.45
```

### 7.4 `styles/jazz/patterns/*` (defining entries)

```yaml
# drums.yaml — straight-grid ride line; Phase 6 swings it
patterns:
  - { id: jz_dr_1, kind: main, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, voice: snare, velocity: 0.35, dur: 900},   # brush sweep proxy
      {pos: 960, voice: snare, velocity: 0.35, dur: 900},
      {pos: 480, voice: hat_closed, velocity: 0.50}, {pos: 1440, voice: hat_closed, velocity: 0.50}]}
  - { id: jz_dr_2, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 1, events: [
      # ride: 1, 2, 2&, 3, 4, 4& (swings to spang-a-lang)
      {pos: 0, voice: ride, velocity: 0.70}, {pos: 480, voice: ride, velocity: 0.72},
      {pos: 720, voice: ride, velocity: 0.55}, {pos: 960, voice: ride, velocity: 0.70},
      {pos: 1440, voice: ride, velocity: 0.72}, {pos: 1680, voice: ride, velocity: 0.55},
      {pos: 480, voice: hat_closed, velocity: 0.50}, {pos: 1440, voice: hat_closed, velocity: 0.50}]}
  - { id: jz_dr_3a, kind: main, energyLevel: 3, lengthTicks: 3840, weight: 3, events: [
      # ride+hats both bars, plus comping hits: snare 2& bar 1 (gated), kick 4& bar 1,
      # snare a-of-2 bar 2 — velocities 0.30–0.45, all below the ride
      {pos: 720, voice: snare, velocity: 0.40, minDensity: 0.50},
      {pos: 1680, voice: kick, velocity: 0.35, minDensity: 0.55},
      {pos: 3120, voice: snare, velocity: 0.38}]}                      # …
  - { id: jz_dr_3b, kind: main, energyLevel: 3, lengthTicks: 3840, weight: 2, events: [
      # cross-stick variant: rim on 4 bar 1, sparse kick bombs
      {pos: 1440, voice: snare, velocity: 0.42}, {pos: 3360, voice: kick, velocity: 0.36}]}  # …
  - { id: jz_dr_4, kind: main, energyLevel: 4, lengthTicks: 1920, weight: 1, events: [
      # dense ride + active comping (full enumeration in pack)
      {pos: 0, voice: ride, velocity: 0.75}]}                          # …
  - { id: jz_dr_i, kind: intro, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 480, voice: hat_closed, velocity: 0.50}, {pos: 1440, voice: hat_closed, velocity: 0.50}]}
  - { id: jz_dr_e, kind: ending, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, voice: ride, velocity: 0.70},
      {pos: 480, voice: hat_closed, velocity: 0.50}, {pos: 1440, voice: hat_closed, velocity: 0.50}]}
  - { id: jz_dr_f1, kind: fill, energyLevel: 3, lengthTicks: 1920, weight: 1, events: [
      {pos: 1200, voice: snare, velocity: 0.55}, {pos: 1440, voice: snare, velocity: 0.62},
      {pos: 1680, voice: tom_mid, velocity: 0.66}]}

# bass.yaml
mode: walking
walking:
  feelByIntensity: {1: two, 2: two, 3: four, 4: four}
  approachWeights: {chromatic_below: 2, diatonic: 1, dominant: 1}
  beat1RepeatWeights: {fifth: 2, third: 1, root: 1}

# comping.yaml
voicing:
  classes: {1: [shell2, shell3], 2: [shell2, shell3],
            3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}
patterns:
  - { id: jz_cp_1, kind: main, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: chord, velocity: 0.50}]}             # football
  - { id: jz_cp_2a, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 3, events: [
      {pos: 0, dur: 700, degree: chord, velocity: 0.62},               # Charleston
      {pos: 720, dur: 400, degree: chord, velocity: 0.55}]}
  - { id: jz_cp_2b, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 2, events: [
      {pos: 240, dur: 400, degree: chord, velocity: 0.58},             # reverse Charleston
      {pos: 960, dur: 700, degree: chord, velocity: 0.60}]}
  - { id: jz_cp_3a, kind: main, energyLevel: 3, lengthTicks: 1920, weight: 3, events: [
      {pos: 0, dur: 660, degree: chord, velocity: 0.62},
      {pos: 720, dur: 300, degree: chord, velocity: 0.56},
      {pos: 1680, dur: 260, degree: chord, velocity: 0.60, push: true}]}   # anticipated 4&
  - { id: jz_cp_3b, kind: main, energyLevel: 3, lengthTicks: 1920, weight: 2, events: [
      {pos: 720, dur: 240, degree: chord, velocity: 0.58},             # Red Garland 2&/4&
      {pos: 1680, dur: 240, degree: chord, velocity: 0.58, push: true}]}
  - { id: jz_cp_4, kind: main, energyLevel: 4, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 600, degree: chord, velocity: 0.66},               # dotted-quarter cross
      {pos: 720, dur: 600, degree: chord, velocity: 0.60},
      {pos: 1440, dur: 400, degree: chord, velocity: 0.62}]}
  - { id: jz_cp_i, kind: intro, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: chord, velocity: 0.48}]}
  - { id: jz_cp_e, kind: ending, energyLevel: 1, lengthTicks: 1920, weight: 1, events: [
      {pos: 0, dur: 1920, degree: chord, velocity: 0.55}]}

# pads.yaml — quartal footballs at every rung (jazz pads are dormant in v1: layersMax 3)
voicing: { classes: {1: [quartal], 2: [quartal], 3: [quartal], 4: [quartal]} }
```

Entries carrying `# …` comments are abridged here for readability — completing them per the §6.1/§6.2 rung conventions is an implementation-session authoring task (DoD §13.1). Every value the §9 goldens depend on (ids, kinds, rungs, weights, and the full events of `pr_dr_2a`, `pr_dr_i`, `pr_bs_2`, `pr_cp_2`, `jz_dr_2`, `jz_cp_2a`, plus all bank candidate counts) is stated in full above.

---

## 8. Pipeline wiring & Serializer

### 8.1 Orchestrator

```
plan   = interpret(params, master, overrides)                  # Phase 2
form   = form(plan, pack.forms, rng_form)                      # Phase 3
chords = harmony(plan, form, pack.progressions, rng_harmony)   # Phase 4
arr    = arrange(plan, form, pack, rng_arrangement)            # §4
phrases = []
for role in [drums, bass, comping, pads]:                      # pinned order (§4.4)
    phrases += generate(role, arr, chords, plan, pack, phrases, streams[role])
phrases = transitions(phrases, ...)     # Phase 6 — designed PHASE_6 §3 (stub until built)
phrases, tempoEvents = humanize(phrases, ...)   # Phase 6 — PHASE_6 §5; also returns
                                        #   ritard tempo events (PHASE_6 §6, 2026-07-07)
patches = sound_design(plan, pack)      # Phase 7 — stub timbres until built
doc    = serialize(plan, form, phrases, patches)               # §8.3
```

`Phrase` granularity: one per (track, section). Phase 5 `tags` contributions: `"ghost"` (walker dead notes), `"push"` (anticipations) — additive to PHASE_1 §4.5's vocabulary.

### 8.2 Drum voice → track mapping (engine data, pinned)

| Voice(s) | Track id | Note |
| --- | --- | --- |
| `kick` | `kick` | |
| `snare` | `snare` | |
| `hat_closed`, `hat_open` | `hats` | open = longer `durationTicks` on the shared MetalSynth track (default durs: closed 60, open 360) |
| `ride` | `ride` | default dur 240 |
| `crash` | `crash` | emitted by Phase 6 (entry crashes, HOLD final hit); default dur 1440 (PHASE_6 §10.7, 2026-07-07) |
| `tom_low` / `tom_mid` / `tom_high` | `tom_low` / `tom_mid` / `tom_high` | |
| `perc` | `perc` | |

Tracks exist only for voices the selected patterns actually emit. Default `dur` for voices without one authored: kick/snare 120. This amends PHASE_1 §6.3 (which parked the mapping in Phase 7's `timbres.yaml`): the *mapping* is engine data pinned here; trigger MIDI notes and patches remain Phase 7's (`midi` values for drum tracks come from the stub/real timbres).

### 8.3 Serializer (thin, as PHASE_1 intends)

Per track: concatenate its Phrases in section order; sort notes by `(ticks, midi)`; clamp `durationTicks ≥ 1`; truncate any note ending past the final section's end (V8). Document assembly: `sections` derived 1:1 from `SongForm` (types, §3.3 labels, energy, tick ranges); `header` from the plan (PPQ 480, base tempo + the Humanizer's ritard tempo events when present — amended by PHASE_6 §6, 2026-07-07; single time signature); `meta` echoes params/seed/overrides/versions; per-track `instrument`/`effects` from the sound-design stage; stub channel defaults (drums −4 dB except kick −2, bass −3, comping −6, pads −10; pan 0 except hats +0.2, ride −0.15, comping +0.1, pads −0.1); no buses; master = `Compressor {threshold: −24, ratio: 4}` + `Limiter {threshold: −1}`. Output must pass every PHASE_1 §3.8 validator rule (V1–V8). (Superseded by PHASE_7 §7, 2026-07-07: the stub channel/mix/master defaults are replaced by the sound-design stage's per-track `channel`/`sends`, the `reverb` bus, and the pack master chain; the Serializer fills them from `SoundDesign` output.)

### 8.4 Stub `timbres.yaml`

Each reference pack ships a stub mapping every declared flavor id to a patch reused from the PHASE_1 milestone fixture's proven recipes (MembraneSynth kick, NoiseSynth snare, MetalSynth hats/ride, MonoSynth bass, PolySynth/FMSynth comping, PolySynth/AMSynth pads), plus per-drum-track trigger `midi` values (kick 24, toms 43/47/50, hats 80, ride 82 — MetalSynth/NoiseSynth conventions). The stub is explicitly **provisional**: Phase 7 owns this file's real schema and replaces the content; the stub exists so the milestone can serialize and play. (Replaced by PHASE_7 §4, 2026-07-07: real `timbres.yaml` schema with kit-level `{midi, patch, mix}` — trigger midi formalized, crash 84 added.)

---

## 9. Worked examples (normative golden fixtures)

Both chain from PHASE_2 §6.5 / PHASE_3 §7.4 / PHASE_4 §10 (seed `1ps9wxb`, master 3735928559). Arrangement tables: §4.5. Every value below is **computed** from this document's algorithms and the §7 banks (reference implementation in the session workspace). Velocity shifts: pop +0.06, jazz −0.025 (rounded per note); articulation: pop ×0.904, jazz ×1.108 (clamped to gaps).

### 9.1 Selection draw narrative

Pop (streams `drums/select` etc.): drums — intro `pr_dr_i` (single, no draw); rung 2 draw among {pr_dr_2a, pr_dr_2b} → **pr_dr_2a**; rung 3 `pr_dr_3`, rung 4 `pr_dr_4` (single). Bass/comping/pads: all single candidates, zero draws. **Pop selection draws: 1.**

Jazz: drums — rung 2 `jz_dr_2` (single); rung 3 draw {jz_dr_3a w3, jz_dr_3b w2} → **jz_dr_3a**; ending `jz_dr_e` (single). Comping — rung 2 draw {jz_cp_2a w3, jz_cp_2b w2} → **jz_cp_2a** (Charleston); rung 3 draw {jz_cp_3a w3, jz_cp_3b w2} → **jz_cp_3a**; ending `jz_cp_e` (single). **Jazz selection draws: 3.**

### 9.2 Jazz walker (bass stream, per-bar sub-streams)

Draw counts per section (golden): head-1 **9**, solo-1 **38**, solo-2 **37**, solo-3 **36**, head-2 **7**, outro-1 **1** — **128 total**. Note counts: 24 / 51 / 54 / 54 / 24 / 7 — each solo's dead-note ghost count follows from the §6.3 rule-6 embellishment firing on every bar with `barInSection ≡ N−1`, the section's final bar included.

Head-1, bars 0–3 (two-feel; chords Dm9 · Gm9 · Dm9 · Dm9):

| Bar | Beat 1 | Beat 3 |
| --- | --- | --- |
| 0 | D2 root | A2 fifth (above) |
| 1 | G2 root | D2 fifth (below) |
| 2 | D2 root | A2 fifth (above) |
| 3 | D3 root | A2 fifth (forced below — A3 exceeds no lane bound but D3+7=57 > 55) |

Turnaround bars 10–11 (2 chords/bar): root halves D3 · B♭2 | E2 · A2 — the walker states each relaunch chord.

Solo-1, bars 12–15 (four-feel over Dm9):

| Bar | 1 | 2 | 3 | 4 |
| --- | --- | --- | --- | --- |
| 12 | D2 root | E2 (scale) | F2 (chord) | G♭2 chromatic → G2 |
| 13 | G2 root | A2 | F2 | D♭2 chromatic → D2 |
| 14 | D2 root | B♭1 | C2 | D♭2 chromatic → D2 |
| 15 | A1 *fifth (decay draw)* | B♭1 | F1 | F1 diatonic + dead-note ghost (and-of-4) |

The bar-15 beat-1 decay draw fires because bars 14–15 share Dm9; the embellishment lands on bar 15 (`barInSection % 4 == 3`, density 0.543 < 0.55 → N = 4). Outro-1 (two-feel, final): D2 · A1 | G1 · D2 | E2 · A2 (2/bar) | **D2 whole note** (final-bar rule, lowest in-lane placement). One draw total.

### 9.3 Voicing passes (zero draws — integer Viterbi)

Jazz comping (lane 46–69, anchor 63): heads at rung 2 voice shells — Dm9 → **F3+C4** (guide tones), Gm9 → **G3+B♭3+F4** (shell3), B♭13 → **D3+A♭3**, A7♭9 → **D♭3+G3**; solos at rung 3 voice rootless forms — Dm9 → **C4 E4 F4 A4** (Type B: 7-9-3-5), Gm9 → **B♭3 D4 F4 A4** (Type A: 3-5-7-9), B♭13 → **D4 F4 A♭4** (no 9th — rootless falls back to 3-5-♭7), A7♭9 → **G3 B♭3 D♭4 E4**. The A/B alternation around the ii–V (Gm9 Type A → Dm9 Type B, 2 of 4 voices static) **emerges from cost minimization** — nothing rules it in. Pop comping (lane 50–71, anchor 65): verse-1 opens E → G♯3 B3 E4, A → A3 C♯4 E4 (common-tone E4 held, and the E voicing stays put across the whole section); chorus E → G♯3 B3 E4, B7 → F♯3 B3 D♯4, C♯m → G♯3 C♯4 E4, A → A3 C♯4 E4; final plagal close A → A3 C♯4 E4, E → G♯3 B3 E4. Pop pads (`fifths`, lane 45–71, stillness weights): chorus E → E3 B3 E4, B7 → B2 F♯3 B3, C♯m → C♯3 G♯3 C♯4, A → A2 E3 A3. All tops ≤ B4 (MIDI 71) — the C5 ceiling holds structurally.

### 9.4 Instantiation excerpts

Pop verse-1, bar 4 (ticks 7680–9600), governing chord E: kick 0.98 @ 0 / 0.94 @ 960; snare 0.91 @ 480 / 0.88 @ 1440; hats 8ths 0.64/0.46/0.54/0.46/0.61/0.46/0.54/0.48; bass root quarters E2 (40) 0.78/0.72/0.76/0.72 dur 434; comping G♯3+B3+E4 hits @ 0 (dur 814, 0.68) and @ 960 (dur 814, 0.64). Jazz head-1, bar 0 (Dm9): ride 0.675/0.695/0.525/0.675/0.695/0.525 at the straight-grid positions; hats 0.475 @ 480/1440; bass D2 root (0.695) / A2 fifth (0.655) halves; comping Charleston F3+C4 @ 0 (dur 720 — clamped to the 720 gap, 0.595) and @ 720 (dur 443, 0.525). The walker's per-section note counts are golden (§9.2); full-document golden note lists land with the implementation (fixtures, not prose).

### 9.5 Milestone

Both examples serialize to `TrackDocument`s passing V1–V8 and play in the Phase 1 playground. Listening checklist: kick/snare/hats lock; the walking line connects bars (approach → root audible at every barline); head is in 2, solos in 4; comping voicings stay mid-register with tops below C5; the anticipated 4& comping hit in solos sounds the *next* chord; pop pads enter at the chorus; the jazz ending settles (whole-note low D under Dm7); nothing but drum triggers sounds above B4.

---

## 10. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Intensity 1–4 confirmed; global engine thresholds 0.30/0.55/0.80** (resolves PHASE_1 Q2) | 4 rungs is the shipping consensus (Yamaha A–D, Korg V1–4); pack energy envelopes already position styles on one ladder (PHASE_4 dissonance-tier mechanism); calibrates correctly on both worked examples (verses share a rung, choruses escalate, head/solo split lands on the feel boundary) | Pack-authored thresholds (double-encodes the envelope, fragments `energyLevel` semantics); rank-adaptive per song (breaks same-energy⇒same-intensity, fights envelope compression) |
| D2 | **One pattern draw per (role, kind, rung), cached per song; intro/outro map to intro/ending kinds** | Same-rung repeats groove identically (corpus repetition; PHASE_4 D7's recognizability logic); chorus→final-chorus contrast via rung change (Yamaha C→D); fewest draws, tightest goldens; intra-section variety is Phase 6's charter | Per-section draws (breaks repeat recognition, duplicates Phase 6); rolling 2–4-bar redraw (JJazzLab-style — two stages sharing anti-repetition, large golden surface) |
| D3 | **Eligibility = optional tempo band only; completeness rules guarantee non-empty selection** (resolves PHASE_1 Q3) | Tempo is the one selection-time dimension with unambiguous backing (brush ballads, 16th grooves, feel changes); BiaB's other masks exist because it redraws per bar — dead under D2; positional variation is authored inside multi-bar patterns; completeness (F13/P6 pattern) eliminates fallback ladders | Section-type masks (dead data — energy rules already separate head/solo by rung; cache-key growth); full BiaB catalog (validation surface for dimensions our architecture obsoletes) |
| D4 | **Anticipation = authored `push: true`, resolving against the next boundary within the note's span** | The core idiom in both reference styles (jazz 4& anticipation, pop push) must be voiced on the incoming chord; we cannot pitch-bend (fixed-pitch notes), so attack-time re-resolution is the mechanism; authored flag = deterministic, no heuristics (BiaB's shipped model) | Proximity auto-detection (silently re-voices legitimate offbeats; threshold edge cases); defer to Phase 8 (audibly damages rung-1 vocabulary) |
| D5 | **Degree table with dressing-safe fallbacks; vocabulary extended with `sixth` and `chord`; approach = chromatic-below only** | Dressing changes qualities per mood — one pattern must resolve at every tier, hence fallback rows; `sixth` unblocks the blues boogie cell; `chord` is the comping/pads voicing hook; chromatic-below is the research's signature approach | Erroring on missing degrees (couples pattern authoring to dressing tiers); full approach-type vocabulary in pattern degrees (walker covers the need; Phase 8 can extend) |
| D6 | **Octave placement: pattern-register∩lane anchor + nearest-octave lane folding (ties down)** | The Yamaha note-limit convention, deterministic; lanes ≥ 12 semitones make folding total; authored `octave` offsets survive | Absolute authored octaves (breaks under lane shifts); nearest-to-previous-note placement for patterns (stateful, couples bars; reserved to the walker where contour is the point) |
| D7 | **`onChordChange`: hold / retrigger(split, 60-tick remainder guard) / stop; default retrigger for pitched roles** | Adapts Yamaha RTR to a format without pitch bend; retrigger is the audible-correctness default (pads re-voice mid-pattern); hold preserved for authored ring-over | Pitch-bend emulation (schema has no bend); hold default (sustained old-chord tones clash on every 2-chord bar) |
| D8 | **Velocity: additive shift `+0.4×(dynamicsBase−0.5)`, clamped [0.05, 1]** | Preserves authored accent relationships (ghost/backbeat gap) at every mood; identity at neutral; Phase 6 owns width (dynamicsRange) and jitter | Multiplicative (crushes ghosts soft, clips loud, duplicates dynamicsRange); pass-through (mood-blind milestone; contradicts PHASE_2 §7.2's consumer list) |
| D9 | **Articulation scaling ×(0.7+0.6×legato) on comping + pattern-mode bass; drums/pads/walker exempt** | `articulationLegato` is budgeted for note-duration scaling (PHASE_2 §7.2); trigger-length drums and full-sustain pads have nothing to scale; walker durations are rule-set (Phase 6 humanizes) | Scaling everything (audible damage to pads/drums); no scaling (budget unconsumed) |
| D10 | **Density consumption = deterministic `minDensity` event gating + walker embellishment rate** | Zero draws, zero probability — density audibly thins/thickens one pattern across sections and is directly testable; matches how authored ornaments actually layer | Probabilistic event inclusion (draws scale with note count; golden fragility); per-role density formulas (no consumer identified) |
| D11 | **Activation: pack layering order + engine count rules (rung base 2/3/4/4, layersMax cap, intro/breakdown/bridge modifiers)** | Additive layering is the documented intensity mechanism (Korg/Yamaha/BiaB); one line of pack data; reproduces trio jazz and pads-at-chorus pop from existing budgets; intro rule is relative (thinner than what follows), which absolute thresholds can't express | Full activation matrices (11×4×5 packs of hand data restating a convention); per-role energy thresholds (can't express relative rules; fights layersMax) |
| D12 | **densityBudget = noteDensity × (0.7 + 0.6 × energy), uniform across roles** | Simple, monotone in both inputs, spot-checks correctly on both examples; per-role character belongs to patterns | Per-role factor tables (tuning surface, no consumer); energy-only (ignores the mood budget) |
| D13 | **Lanes: bass 28–55, comping 48–71, pads 43–71, drums exempt; bias shifts comping/pads only** | Research register table + low-interval limits; bass anchored (kick relationship, instrument physics); ceiling ≤ 71 structural | Bias-shifting bass (mud risk for a ±3-semitone nudge); per-pack lanes (no v1 need; Phase 8 can amend) |
| D14 | **Generation order drums→bass→comping→pads pinned; generators receive prior roles' phrases; v1 consumes nothing (kick-lock = authoring convention)** | The musically canonical order; the interface makes a future runtime alignment pass non-breaking; shipped products do coherence by authoring, not runtime locking | Runtime kick-reading in v1 (unproven benefit, new failure modes); no interface hook (post-v1 pass becomes a breaking change) |
| D15 | **Bass dual-mode: pack data selects `patterns` or `walking`; the walker is engine code parameterized by pack data** | Walking lines need cross-bar contour state patterns can't express (the MMA WALK failure); pop bass is pattern-idiomatic; invariant-1 reading: algorithms live in the engine (PHASE_3 fitter, PHASE_4 transforms precedent), packs select/parameterize via data — adding styles stays authoring | Patterns-only (bar-restarting walking lines — the documented weak model); algorithmic-only (discards authored hooks; fights invariants 1–2 for the common case) |
| D16 | **Walker: target-first (next root, nearest octave), beats 3→2 strongest-first fill from beat-position pools, drawn approach types, root-decay on repeated bars, feel from rung, deterministic embellishment placement, per-bar sub-streams** | Direct implementation of the pedagogy consensus and Dias & Guedes's published architecture; per-bar seeding makes bars independently reproducible and excerpt-testable; feel-by-rung reproduces head-in-2/solos-in-4 on the worked example for free | Markov/corpus models (no lookahead guarantees, ungoldenable); global-stream sequential draws (any change shifts the whole song's line) |
| D17 | **Comping = rhythm-only `chord`-hit patterns + one Viterbi voicing pass per role over the full chord timeline** | Rhythm and voicing are separable vocabularies (research); the PHASE_4 DP was pinned *for* this; A/B alternation and common-tone retention emerge from cost minimization (verified in §9.3); zero draws | Authored voicing stacks (voice-leading becomes per-pattern×progression authoring; Viterbi unused); greedy nearest (provable register drift — the failure the DP exists to prevent) |
| D18 | **Voicing classes per rung as pack data; `fifths` class added** (resolves PHASE_4 Q9) | Shell→rootless escalation is real practice mapped to rungs; pads need the 3rd-omitted stack (production consensus); one added class, one amendment | Fixed engine class map (style identity lost); per-pattern class overrides (authoring surface without need) |
| D19 | **Pads: whole/half-note chord hits, retrigger, stillness Viterbi weights (move 4, top 2, common 5, drift 1), articulation-exempt** | Pads are the sustained, still, energy-gated layer (research); activation falls out of layering order — no special gating code | Energy-threshold pad gating (duplicates D11); arpeggiated pads (Phase 8 flavor territory) |
| D20 | **Phrase per (track, section); drum voice→track mapping engine-pinned (hats merge closed+open); Phase 5 tags: `ghost`, `push`** | Section granularity is Phase 6's working unit and the reroll/golden unit; the milestone must serialize real tracks now — mapping can't wait for Phase 7 (patches still can); open hat = duration, not a separate instrument | Phrase-per-song (Phase 6 must re-split); mapping in stub timbres only (contract ambiguity PHASE_1 warns against) |
| D21 | **Straight-grid authoring; swing entirely in Phase 6** | Roadmap assigns swing to the humanizer; one grid for all packs keeps patterns feel-portable; `GenerationPlan.swing` already carries the ratio downstream | Authoring swung positions (packs locked to a feel; Phase 6 double-swings or must detect) |
| D22 | **Milestone stubs: identity Transitions/Humanizer, provisional stub timbres reusing PHASE_1 fixture patches; thin Serializer with stub mix defaults** | The milestone de-risks generation, not sound design; PHASE_1's patches are validated by its own milestone; every stub is marked provisional with its owning phase | Blocking the milestone on Phase 6/7 (defeats the roadmap's mid-Phase-5 audibility goal); ad-hoc unvalidated patches (why not reuse proven ones) |

---

## 11. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | Per-role intensity offsets / density factors (e.g. drums a rung hotter than pads in the same section)? | Phase 8 | authoring experience across 5 packs; amend §4.1/§4.2 |
| Q2 | Runtime kick/bass alignment pass (consume the reserved drums→bass phrase handoff)? | Post-v1 | listening evidence that authoring convention is insufficient (D14 hook documented) |
| Q3 | Pattern-degree approach variants (`approach_above`, `approach_diatonic`)? | Phase 8 | first pack needing them; additive vocabulary extension per §3.3 |
| Q4 | ~~Blues bass: boogie patterns vs walking mode?~~ **Resolved** — authored boogie/box/pedal/triplet-arpeggio degree patterns (`mode: patterns`); walking blues remains the jazz pack's territory (PHASE_8 §3.2/D3, 2026-07-07) | ~~Phase 8~~ | — |
| Q5 | `kind: break` semantics and stop-time patterns (PHASE_3 Q5) — **partially resolved** (PHASE_6, 2026-07-07: the v1 `stop` device is pure note deletion and needs no break patterns); remainder **deferred post-v1** (PHASE_8 §3.8, 2026-07-07: stop-time choruses require load-bearing `variant`, PHASE_8 §12 Q2; `kind: break` stays reserved) | Post-v1 | load-bearing `variant` |
| Q6 | Pad voicing motion over long static sections (MMA's `Move`-style slow drift)? | Post-v1 | evidence that held pads read as static across 16+ bars |
| Q7 | ~~Percussion layer: fifth role or drums extension?~~ **Resolved** — no fifth role: the `perc` drum voice carries lo-fi shaker/rim and fusion auxiliary percussion as ordinary drum-bank events (PHASE_8 §3.6, 2026-07-07); role enum stays closed | ~~Phase 8~~ | — |
| Q8 | Comping-reacts-to-soloist (interactive density)? | Post-v1 | there is no soloist input in v1 by design; revisit if a live-input mode ever exists |
| Q9 | Walker repeated-note polish (beat-3/beat-4 collision avoidance)? (PHASE_6, 2026-07-07: confirmed post-v1 — the Humanizer never re-pitches) | Post-v1 listening | whether occasional repeated pitches (§9.2 bar 21) read as natural or mechanical |

---

## 12. Amendments to earlier documents (this session)

All additive; applied in the same commit as this document:

1. **PHASE_1 §7 Q2**: resolved — intensity ladder confirmed 1–4 with global thresholds (PHASE_5 §3.1).
2. **PHASE_1 §7 Q3**: resolved — eligibility = optional tempo band + completeness rules (PHASE_5 §3.2).
3. **PHASE_1 §4.4**: extension-points line annotated as resolved by PHASE_5 §4.4 (layering order in packs; articulation/lane-interaction closed).
4. **PHASE_1 §4.5**: `tags` vocabulary annotated — PHASE_5 contributes `"ghost"`, `"push"`.
5. **PHASE_1 §6.2**: `eligibility` and `retarget` extension slots annotated as pinned by PHASE_5 §3.2/§3.3/PT9.
6. **PHASE_1 §6.3**: degree vocabulary annotated as extended by PHASE_5 (`sixth`, `chord`; event fields `push`, `minDensity`); drum voice→track mapping note amended — mapping is engine data pinned by PHASE_5 §8.2; trigger conventions/patches remain Phase 7.
7. **PHASE_2 §7.2**: `registerBias`, `dynamicsBase`, `articulationLegato`, `noteDensity`, `layersMax` rows annotated with their concrete PHASE_5 consumption (§3.4, §4.1–§4.3).
8. **PHASE_3 §6.5**: annotated resolved — the energy→intensity mapping is PHASE_5 §3.1.
9. **PHASE_4 §8.4**: `fifths` candidate class added (PHASE_5 §6.5; resolves PHASE_4 Q9 in part — further classes remain open there).
10. **PHASE_4 §8.5**: cardinality-padding caller policy documented (pad shorter voicing with its top pitch — PHASE_5 §6.4).
11. **ROADMAP §2 decisions log**: row added for the Phase 5 part-generation model.

---

## 13. Definition of done

Phase 5 is **built** when an implementation session demonstrates:

1. **Loaders**: all four `patterns/*.yaml` schemas parsing into frozen pydantic models; PT1–PT11 implemented with one rejection fixture per rule class; both reference packs load clean (fully enumerated versions of §7, including the abridged events).
2. **Foundations**: unit tests for §3.1 thresholds (boundary values), §3.3 degree resolution (every degree × representative qualities × dressing tiers, fallbacks, `push` boundary cases incl. no-boundary and song-end, octave folding at lane edges with tie-down), §3.4 velocity/articulation formulas (identity points, clamps, exemptions), §3.5 gating.
3. **Arrangement stage**: golden tests asserting both §4.5 tables field-for-field; zero-draw assertion (counting-RNG shim on the `arrangement` stream); property tests — every pack × supported mood × lengths × 25 seeds: full section×role coverage, `active` counts ≤ layersMax, lanes within ceilings, intro thinner than successor.
4. **Selection**: golden tests for both §9.1 draw narratives (selections and exact draw counts: pop 1, jazz 3); completeness property (every reachable (role, kind, rung) resolves for every pack × mood × tempo).
5. **Walker**: golden tests for §9.2 (all excerpt notes exactly; per-section draw counts 9/38/37/36/7/1; total 128; note counts 24/51/54/54/24/7); per-bar sub-stream independence test (regenerating one bar's RNG reproduces its draws in isolation); property tests — every note in lane, beat-1 rule compliance, approach targets correct, final-bar rule on final sections.
6. **Voicing passes**: golden tests for §9.3 voicings (jazz shells/rootless, pop triads, pads fifths — exact MIDI); integer-cost property; all tops ≤ 71; cardinality-padding unit test.
7. **Generators end-to-end**: both worked examples produce Phrases passing: notes sorted, within section spans, velocities in (0,1], non-drum pitches ≤ 71, `push`/`ghost` tags present where §9 says.
8. **Serializer + milestone**: both examples serialize to `TrackDocument`s passing PHASE_1 §3.8 V1–V8 and the schema; documents committed as fixtures; each plays in the Phase 1 playground through the §9.5 listening checklist. This is the roadmap's first-generated-track milestone.
9. **Determinism**: repeated-run identity on the full pipeline; counting-RNG shims asserting exact per-stream draw counts for both examples; a lint/grep check extended to the new modules (no module-level `random`, no wall-clock).
10. **Golden-seed regression**: the two full generated documents become the first whole-document golden tests (ROADMAP Phase 8's mechanism, seeded here).
11. **Amendments** (§12) applied and consistent.

---

## 14. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §5/§7: banks, weights, eligibility, voicing classes, walker parameters, layering order — all YAML; engine owns algorithms (walker, Viterbi, selection), parameterized by pack data (D15 precedent: PHASE_3 fitter, PHASE_4 transforms) |
| 2. Rhythm stored separately from pitch | §3.3/§6: patterns author degrees and chord-hits, never literal pitches; concrete pitches appear only in Phrases after retargeting/voicing; the walker derives pitches from HarmonicPlan at render time |
| 3. Hierarchical seeds | §3.6: per-role streams, named sub-streams, per-bar walker seeds; rerolling `drums` re-rolls only drums; `arrangement` reserved |
| 4. Soloist owns above ~C5 | §4.3 lanes (≤ 71 enforced + validator); §3.3 folding cannot escape a lane; §6.4/§6.5 Viterbi candidates lane-pruned (PHASE_4 §8.4); §9.3 verifies empirically |
| 5. Deterministic pipeline | Integer weights; draws only via `weighted_choice` when ≥ 2 candidates; ascending-sorted candidate lists; integer-cost DP; deterministic gating (no probabilities); arithmetic arrangement; 3-decimal half-even rounding; entropy enters nowhere |
