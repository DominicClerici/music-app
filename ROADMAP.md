# Backing Track Generator — Roadmap

A backend pipeline that algorithmically composes complete, structured, instrumental backing tracks from structured user parameters, and emits them as a JSON document a browser client plays with Tone.js.

This document is the high-level plan. Each phase below will be expanded into its own `PHASE_N.md` design document in a dedicated session, driven by `PROMPT.md`.

---

## 1. Vision

A user picks parameters — style family, mood, tempo, key, instrument flavors, max length — and gets back a full song-shaped backing track: real structure (intro, verses, choruses, bridge, outro), a cohesive rhythm-section arrangement with fills and transitions, and synthesized instrument tones matched to the mood. The track is fully instrumental and deliberately leaves melodic space for the user to play or sing over.

Primary audiences:

- **Musicians** jamming or practicing improvisation over believable, idiomatic grooves.
- **Casual creators** generating mood-matched music to play over.

In both cases the track is *played over* — musical believability, groove, and soloist space are the top quality criteria.

Explicitly **not** in scope: neural audio generation, free-text prompts, and the browser player itself (we define the output contract; the client is a separate concern).

## 2. Decisions Log

Decisions made during roadmap planning (2026-07-06). These are settled unless a phase session surfaces a concrete reason to amend them.

| Decision | Choice |
| --- | --- |
| Generation engine | **Layered hybrid**: authored pattern vocabulary for the groove skeleton + theory rules for form/harmony/voicing/arrangement + seeded weighted-random selection + algorithmic humanization. (The architecture every successful product in this niche — Band-in-a-Box, Yamaha arranger styles, iReal Pro, MMA, JJazzLab — converged on. Pure rule-generation makes idiomatic grooves fragile; pure pattern libraries make mood a discrete bank instead of a knob.) |
| Genre handling | **Hybrid**: a small set of style families provide pattern vocabulary; mood/energy parameters morph within them. |
| Initial style families | Pop/Rock, Chill/Lo-fi, Blues, Jazz, Fusion Jazz. Early phases develop against **Pop/Rock** (reference) and **Jazz** (contrast — walking bass and swing stress the architecture most); full authoring of all five happens in Phase 8. |
| Instruments parameter | **Role-based ensemble**: the system thinks in roles (drums, bass, comping, pads/texture); the user picks a sound flavor per role or an ensemble preset. |
| Reproducibility | **Seeded randomness with the seed exposed**: same params + same seed → identical track. Fresh seed per generation by default; seed always returned in the output. |
| Output format | Tone.js-oriented JSON (`TrackDocument`), modeled on `@tonejs/midi`'s schema with Tone.js synth patches/effects replacing General MIDI programs. |
| Backend stack | **Python ≥ 3.12** (decided in Phase 1, 2026-07-06): the project's focus is generation quality, and encoding the output for the browser is trivial serialization. music21 (wrapped) for theory; pydantic v2 models with exported JSON Schema as the client contract. See `PHASE_1.md` §2/D1–D2. |
| Style × mood interaction | **Packs declare supported moods** (decided in Phase 2, 2026-07-06): each style pack lists its supported subset of the 12-word mood vocabulary plus a default; unsupported combos are validation errors, never silent substitution. Mood = V/A anchor + formulas + per-mood overrides. See `PHASE_2.md` §4–5/D1–D3. |
| Form model | **Templates with parameterized slots + repeat blocks** (decided in Phase 3, 2026-07-07): `forms.yaml` declares section defaults + weighted template spines; repeat blocks fit the length budget arithmetically (BiaB/Aebersold convention); an 11-type section vocabulary (starter six + postchorus/head/solo/main/breakdown) carries one semantics table for Phases 4–6; energy = engine base table + positional rules + arousal + pack envelope. Fitting fills toward `maxLength` from below (hard ceiling), degrading outro-before-bridge per corpus presence. See `PHASE_3.md` §3–7/D1–D14. |
| Harmony model | **Authored pools + bounded transforms** (decided in Phase 4, 2026-07-07): `progressions.yaml` holds per-phrase-label Roman-numeral progressions (case+suffix tokens, major-scale-relative degrees), gated by mode/valence/dissonance, drawn once per harmonyTag; runtime rewrites only three boundary events (turnaround relaunch at same-tag loops, dormant deceptive fallback, mandatory final close from a `finals` pool); a 7-tier dissonance-dressing ladder with dominant-hotter function offsets maps `budgets.dissonance` to chord color; repeats are harmonically identical in v1; modulation deferred with `HarmonicPlan.keys` regions reserved; the shared theory library (owned interval/scale tables, voicing candidates, integer-cost Viterbi voice-leading) is pinned for Phase 5. See `PHASE_4.md` §3–8/D1–D16. |

## 3. System Overview

### The contract

A stateless service:

```
generate(params, seed?) → TrackDocument
```

**Params** (structured, no free text): style family, mood, tempo (or auto-from-mood), key (or auto), per-role sound flavor / ensemble preset, max length, optional master seed.

**TrackDocument** (the output): a self-contained JSON description of the whole song — tempo map, time signatures, section markers, and per-track data: a Tone.js instrument patch (constructor options as JSON), an ordered effects chain, and a flat note list (tick-based time, pitch, duration, velocity). Times are tempo-relative (ticks/bars), never seconds. A 3-minute multi-track song is ~30–60 KB gzipped — one HTTP response.

### The pipeline

Nine stages, each consuming and producing a well-defined intermediate representation (IR), so every stage can be developed, tested, and re-rolled independently:

```
params ──> 1. Interpreter          params → GenerationPlan
                                     mood → valence/arousal → tempo, mode, swing,
                                     density budgets, dissonance budget, timbre palette;
                                     style family → pattern vocabulary, form tendencies
       ──> 2. Form generator       plan → SongForm
                                     section sequence + bar counts fitted to max length
                                     + per-section energy (0–1)
       ──> 3. Harmony generator    form → HarmonicPlan
                                     progressions per section from tagged pools,
                                     functional constraints, boundary cadences
       ──> 4. Arrangement planner  form + plan → ArrangementPlan
                                     active roles per section, density/register budgets,
                                     soloist-space rules
       ──> 5. Part generators      arrangement → per-role Phrases
                                     drums (pattern lib + intensity ladder),
                                     bass (kick-lock / walking), comping (voice-led
                                     voicings + comping rhythms), pads/texture
       ──> 6. Transition engine    phrases → phrases + fills, crashes, risers, stops
       ──> 7. Humanizer            swing, velocity accent maps + jitter,
                                     micro-timing, 4-bar pattern mutation
       ──> 8. Sound designer       role + mood + flavor → Tone.js patches + FX chains
       ──> 9. Serializer           everything → TrackDocument
```

### Invariants

These are binding on every phase. A phase session that needs to break one must propose a roadmap amendment, not silently diverge.

1. **Style packs are data, not code.** A style family is a versioned data pack: pattern banks, progression pools, form tendencies, timbre palette. Adding a style is authoring, not engineering.
2. **Rhythm is stored separately from pitch.** Patterns encode rhythm plus chord-degree roles (root, fifth, guide tones, tensions) and are retargeted to the actual chords at render time with voice-leading rules. Never store literal notes and transpose naively.
3. **Hierarchical seeds.** A master seed derives named sub-seeds (form, harmony, drums, bass, …). Enables "keep the song, reroll just the drums," sharing, and deterministic tests.
4. **The soloist owns the lead register.** Backing voices stay below ~C5; backing parts are rhythmic-harmonic, never melodic; density budgets keep space open. Every part generator respects this.
5. **Deterministic pipeline.** Given params + seed, every stage is pure and reproducible. No wall-clock, no unseeded randomness.

## 4. Phases

### Phase 1 — Foundations & Contracts

The domain model and every interface the rest of the system builds against.

- `TrackDocument` schema: notes, tempo map, sections, instrument patches, effect chains, seed echo, schema version.
- Pipeline IRs: `GenerationPlan`, `SongForm`, `HarmonicPlan`, `ArrangementPlan`, `Phrase`.
- Hierarchical seed system design.
- Style-pack data format (structure only; content comes later).
- Backend stack decision.
- **Milestone:** a hand-written `TrackDocument` plays correctly in a throwaway Tone.js test page — validating the output contract before any generation exists.

### Phase 2 — Parameter & Mood Model

The user-facing parameter surface and the Interpreter stage.

- Parameter schema and validation (moods, tempo/key ranges and auto-resolution, role flavors, ensemble presets, max length).
- Mood taxonomy → valence/arousal mapping → the parameter table (tempo range, mode, harmonic rhythm, note density, register, articulation, dynamics, dissonance, swing, layer count).
- Style family definitions and the style × mood interaction model (does every style support every mood, or do styles constrain moods? — resolve here).
- `GenerationPlan` production.

### Phase 3 — Form & Structure

- Form templates per style family: verse–chorus (pop/rock), 12-bar (blues), AABA (jazz), one-part loop (chill), and their variants.
- Per-section energy curves (e.g., intro 0.3, verse 0.5, pre-chorus 0.65, chorus 0.9, final chorus 1.0).
- Fitting to max length: arithmetic repeat counts + a pack-authored degradation ladder (outro first, then intro-shrink, then bridge — corpus presence ranks expendability; refined from this sketch's original "bridge first" by PHASE_3 D11), never emit a section under 4 bars.
- Section-type semantics downstream stages consume (what "chorus" *means* to the arranger, the harmony engine, the transition engine).

### Phase 4 — Harmony Engine

- Progression pools tagged by mood/style (Roman-numeral form, transposed to the user key).
- Functional-harmony constraint rules (tonic/subdominant/dominant flow) for variation and bridge generation.
- Cadence logic at section boundaries (verses end open on V, choruses close on I, deceptive cadences before repeated final choruses).
- Key/mode selection and mood mapping (absorbed by Phase 2, PHASE_2 D5: the Interpreter emits the final key/mode; Phase 4 owns everything *inside* the key); borrowed-chord substitutions.
- Shared theory utilities: chord symbol → pitches, voicing candidates, voice-leading distance minimization. These become the library every part generator uses.

### Phase 5 — Rhythm Section Part Generators

The largest phase — its session should split it further.

- **Arrangement planner:** which roles are active per section, per-role density and register lanes, soloist-space enforcement, layer count scaling with energy.
- **Drums:** pattern-library format (per style, per intensity level), pattern selection with weights and eligibility masks, the intensity ladder for verse/chorus contrast.
- **Bass:** kick-locking root patterns by energy level; walking bass for jazz/blues (root on 1, chord/scale tones, leading tone into the next root); approach-note transitions.
- **Comping:** guide-tone voicings (3rd + 7th + color) voice-led between chords, rhythmic comping patterns (sustained, charleston, off-beat, pushes) varied every 2–4 bars.
- **Pads/texture:** slow-attack sustained layer, energy-gated.
- **Milestone:** first fully generated track end-to-end — one style, minimal everything, serialized through the Serializer stage to a valid `TrackDocument` and played in the Phase 1 test page. (The Serializer itself is thin: its format is fully pinned by Phase 1's schema; it gets built here as part of wiring the pipeline.)

### Phase 6 — Transitions, Variation & Humanization

The "sounds like a band, not a MIDI file" phase.

- Fill generation and placement: small fill each 4-bar phrase, big fill at section boundaries, sized to the energy jump; crash + kick on the downbeat after.
- Transition devices: risers before high-energy sections, breakdowns, the 1-beat full stop before a chorus.
- Anti-repetition: mutate patterns slightly every 4 bars, comping rhythm every 8; nothing loops verbatim.
- Humanization: swing ratios per style, metric velocity accent maps + jitter, ghost notes, micro-timing offsets (laid-back hats, tight kick/bass), duration variation.

### Phase 7 — Sound Design

- Role + mood + user flavor → concrete Tone.js instrument patches (oscillator, envelope, filter as JSON constructor options).
- Synthesized drum kit recipes (MembraneSynth kick, NoiseSynth snare, MetalSynth hats) parameterized by mood brightness.
- Effect chains per role and mood (reverb/chorus/distortion/delay mappings), timbre-to-mood tables (waveform, filter cutoff, attack/release ↔ valence/arousal).
- Mix defaults: per-role levels, panning, master chain.

### Phase 8 — Quality, Evaluation & Style Pack Expansion

- Structural validators: register collisions, fill presence, cadence correctness, density budget compliance — automated checks on generated output.
- Golden-seed regression tests (params + seed → exact expected document).
- Listening-test workflow for subjective quality.
- Style-pack authoring workflow and full build-out of all five families (Pop/Rock, Chill/Lo-fi, Blues, Jazz, Fusion Jazz).

## 5. Sequencing Notes

- Phases 2–4 are pure data-in/data-out and testable without audio. The first *audible* generated result lands mid-Phase 5 — which is why Phase 1's hand-written-document milestone exists: it de-risks the output format long before generation works.
- Style-pack **content** authoring is deliberately late (Phase 8); earlier phases build the machinery against the two reference styles only.
- Phase boundaries are conceptual, not strictly serial — e.g., Phase 7's patch format is pinned in Phase 1's schema; Phase 6's humanizer can be prototyped as soon as Phase 5 emits phrases.

## 6. Glossary

- **Role** — an arrangement function: drums, bass, comping, pads/texture. Users pick sounds per role, not raw instruments.
- **Style family / style pack** — a genre vocabulary shipped as data: patterns, progressions, form tendencies, timbres.
- **Intensity ladder** — ordered variants of the same groove at increasing energy (the Yamaha Main A→D idea); how verse/chorus contrast is achieved within one style.
- **Guide tones** — the 3rd and 7th of a chord; the minimum pitches that define its quality, the core of comping voicings.
- **Energy** — a 0–1 per-section scalar driving density, layer count, register, dynamics, and pattern intensity selection.
- **IR** — intermediate representation passed between pipeline stages.
- **Phrase** — a per-role list of notes (rhythm + pitch + velocity) for a span of bars, pre-humanization.
