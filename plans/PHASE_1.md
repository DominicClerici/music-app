# PHASE_1 — Foundations & Contracts

Designed 2026-07-06 (session 1). Status: **awaiting approval**.

This document pins the domain model and every interface the rest of the system builds against: the `TrackDocument` output schema, the five pipeline IRs, the hierarchical seed system, the style-pack structure, and the backend stack. Later phases build *against* this document; changing anything marked **pinned** requires amending this file with sign-off, not working around it.

---

## 1. Scope

**In scope**

- Backend stack decision and project skeleton.
- `TrackDocument` schema, complete and field-level (this phase owns it end-to-end).
- The **pinned core** of each pipeline IR — `GenerationPlan`, `SongForm`, `HarmonicPlan`, `ArrangementPlan`, `Phrase` — plus named extension points owned by later phases.
- The hierarchical seed system, complete (algorithm, stream registry, reroll API, encoding, determinism rules, golden vectors).
- Style-pack packaging and the shared pattern-envelope/event primitives (bank-specific schemas belong to Phases 3/4/5/7).
- The milestone: a hand-written `TrackDocument` playing correctly in a throwaway Tone.js test page.

**Explicitly not in scope**

- Any generation logic (no Interpreter, no form/harmony/parts algorithms).
- Style-pack *content* (Phase 8) and the bank-specific schemas inside packs (owned by their phases).
- The parameter surface and mood model (Phase 2) — `meta.params` is treated as an opaque echoed object here.
- The production browser player. The playground page exists only to validate the contract.

### Contract depth rule (applies to §4)

Each IR section below has two parts:

- **Pinned core** — fields every *consuming* stage relies on. Changing one requires amending this document.
- **Extension points** — named slots a later phase owns. That phase may add fields freely inside its slot without touching this document; it may not repurpose pinned fields.

---

## 2. Backend stack

**Decision: Python ≥ 3.12.** Rationale: the project's center of gravity is generation quality, not transport; encoding JSON output for the browser is trivial from any language (user decision, session 1). Consequences accepted: the `TrackDocument` contract is maintained as language-neutral JSON Schema (exported from pydantic) rather than shared TS types.

| Concern | Choice |
| --- | --- |
| Language / runtime | Python ≥ 3.12 |
| Delivery surface | **Pure library** — `generate(params, seed?) → TrackDocument`, one pure entry point — **plus a thin Typer CLI**. An HTTP layer is deferred until a client exists; it is a small wrapper over `generate()` (D16), never a second validation surface. |
| Packaging & deps | **uv** with a committed `uv.lock`; music21 and the Tone.js target (Q9) pinned to exact versions. Reproducibility is a core project value, so a dependency bump is a deliberate, reviewed event — never silent drift. |
| Lint / format | **Ruff** (formatter + linter). A custom banned-API ruleset forbids module-level `random.`, `datetime.now`, `time.*`, and `os.urandom` outside the seed boundary — turning determinism invariant 5 (§9.7) from a manual grep into an enforced gate. |
| Type checking | **mypy** (strict). Frozen pydantic IRs make static checking high-value. |
| CLI framework | **Typer** — type-hint driven, pairs with pydantic; hosts the PHASE_8 §9.1 audition CLI (`--explain`, `--section`, `--solo/--mute`, `bless`). |
| Models & validation | pydantic v2, `frozen=True` on every IR and document model (immutability makes stage purity structural) |
| Music theory | **music21 (BSD, maintained), wrapped**: a thin `theory/` module exposes pure functions (plain ints/strings in and out — pitch classes, MIDI numbers, chord specs). Pipeline stages import our wrapper, never music21. Rationale: music21's Roman-numeral/key machinery is the best available and generation-grade; the wrapper contains its score-centric object model and keeps a swap-out possible. mingus is GPL + unmaintained (disqualified); fully hand-rolled theory re-implements solved problems. Voicing search and voice-leading minimization (Phase 4) will be ours, over the wrapper. **The wrapper lazy-imports music21** inside its functions, never at module top — music21's import is slow and pulls numpy in transitively, so CLI startup and non-theory tests stay fast. |
| Style-pack files | YAML via PyYAML (`safe_load`), validated into frozen pydantic models at load |
| RNG | stdlib `random.Random`, one instance per stream (see §5); no numpy API dependence |
| Tests | pytest; golden-vector and golden-seed tests from day one |
| Property tests | **Hypothesis** for invariant tests — it draws params + seed and asserts invariants (register ceiling, V1–V8, fills only in legal bars), never fighting the RNG; the fixed smoke matrix stays a `pytest.mark.parametrize` grid |
| Goldens / approval | **Committed JSON fixtures + a hand-rolled semantic `bless` reporter** (PHASE_8 §8.2 / D11). No snapshot library (syrupy/approvaltests) for the golden *system* — the required musical, per-stage diff is domain-specific; a snapshot lib may back only the simple exact-match IR goldens if it ever helps |
| JSON serialization | stdlib `json` (a 30–60 KB document needs nothing faster; orjson is a later, HTTP-time concern) |
| Schema export | pydantic → JSON Schema, committed at `docs/schema/trackdocument.schema.json`; the browser client validates against this artifact |

### Repository layout

```
music-app/
  pyproject.toml
  uv.lock
  src/trackgen/
    schema/        # pydantic models: TrackDocument + IRs
    seeds.py       # master seed, derive(), streams registry, weighted_choice
    cli.py         # Typer app: generate + PHASE_8 §9.1 audition CLI + bless
    theory/        # music21 wrapper (pure functions only)
    packs/         # style-pack loader + envelope validation
    pipeline/      # stage interfaces (implementations land in later phases)
  styles/          # style packs (data, not code)
  fixtures/        # hand-written documents, golden outputs
  playground/      # throwaway Tone.js test page (not product code)
  docs/schema/     # exported JSON Schema
  tests/
```

The package name `trackgen` is provisional (open question §7, trivial).

---

## 3. The `TrackDocument` contract

A `TrackDocument` is a self-contained JSON description of one complete song. Design principles, each traceable to research findings:

1. **Ticks only.** Every time value is an integer tick at **PPQ 480**; seconds never appear. Rationale: `@tonejs/midi` keeps ticks canonical and its seconds fields are stale-able snapshots; carrying both is the documented cause of the double-tempo-transform bug (Tonejs/Midi #81, wontfix). PPQ 480 is the DAW convention, divisible by 2/3/4/5/6/8 subdivisions, ~1 ms resolution at 120 bpm.
2. **Flat tracks, one instrument instance each.** A synthesized drum kit is three Tone.js instruments (MembraneSynth kick, NoiseSynth snare, MetalSynth hats), so kick/snare/hats are separate tracks sharing `role: "drums"`. Client instantiation is 1:1 with tracks.
3. **Patches are tagged unions of constructor options.** `{type, options}` where `options` is exactly the Tone.js constructor-options object (`instrument.get()` round-trips as constructor input in Tone v14+). Class names resolve through a client-side whitelist, never raw indexing.
4. **Inserts plus optional buses.** Per-track `effects[]` inserts; optional document-level `buses[]` with per-track `sends[]` for shared effects (the one-reverb-many-sends mix idiom; Tone.Channel has send/receive built in).
5. **Self-describing regeneration identity.** `meta` carries everything needed to regenerate or reroll the track.

### 3.1 Top level

```jsonc
{
  "schemaVersion": 1,
  "meta":   { /* §3.2 */ },
  "header": { /* §3.3 */ },
  "sections": [ /* §3.4 */ ],
  "buses":  [ /* §3.6 */ ],
  "master": { "effects": [ /* EffectPatch[], §3.6 */ ] },
  "tracks": [ /* §3.5 */ ]
}
```

### 3.2 `meta` — regeneration identity

| Field | Type | Notes |
| --- | --- | --- |
| `generatorVersion` | string (semver) | version of the pipeline that produced this document |
| `toneVersion` | string (semver range) | Tone.js range the patches were authored against, e.g. `"^15.1.0"`. Client refuses/warns on major mismatch (Tone v13→v14 broke patch shapes historically). |
| `seed` | string (base36) | master seed |
| `seedOverrides` | object `{streamName: base36}` | per-stream reroll overrides in effect; `{}` if none |
| `params` | object | the validated input params, echoed verbatim. Shape owned by Phase 2; opaque here. |
| `title` | string, optional | display title |

`(params, seed, seedOverrides, generatorVersion)` regenerate the document exactly.

### 3.3 `header` — timing

| Field | Type | Constraints |
| --- | --- | --- |
| `ppq` | int | always `480` (constant in v1; here so the client never hardcodes) |
| `tempos` | `[{ticks: int, bpm: float}]` | sorted ascending by `ticks`; first entry MUST be at `ticks: 0`; `bpm > 0` |
| `timeSignatures` | `[{ticks: int, numerator: int, denominator: int}]` | sorted; first at `ticks: 0`; `denominator ∈ {2,4,8,16}` |

Semantics: an event applies from its tick until the next event of the same kind ("last event at-or-before tick" lookup, matching SMF/`@tonejs/midi`).

### 3.4 `sections` — explicit ranges, not markers

```jsonc
{ "type": "chorus", "label": "Chorus 2", "startTick": 30720, "endTick": 46080, "energy": 0.9 }
```

- `type`: section-type string (vocabulary owned by Phase 3; the full v1 vocabulary — 11 types — is defined in PHASE_3 §3, superseding the starter set listed here at design time).
- Sections are contiguous, non-overlapping, start at tick 0, and cover the song end-to-end. `endTick` is exclusive and equals the next section's `startTick`.
- `energy`: the section's 0–1 energy scalar, carried for client display and validators.

Rationale: every consumer (client UI, looping, our validators) wants ranges; MIDI's instant markers in an untyped meta bucket are the weaker encoding.

### 3.5 `tracks[]`

| Field | Type | Constraints |
| --- | --- | --- |
| `id` | string | unique within document, stable snake_case (`"kick"`, `"comping"`) |
| `role` | `"drums" \| "bass" \| "comping" \| "pads"` | closed enum in v1 (roadmap's role set) |
| `name` | string | display name |
| `instrument` | InstrumentPatch (§3.6) | |
| `effects` | EffectPatch[] | ordered insert chain, may be empty |
| `channel` | `{volumeDb: float, pan: float, mute: bool}` | `pan ∈ [-1, 1]`; `volumeDb ≤ 6` |
| `sends` | `[{bus: string, gainDb: float}]` | each `bus` must reference `buses[].id`; may be empty |
| `notes` | NoteEvent[] | sorted by `(ticks, midi)`; stable order is part of the contract (diffability, golden tests) |

**NoteEvent**

| Field | Type | Constraints |
| --- | --- | --- |
| `ticks` | int | ≥ 0 |
| `durationTicks` | int | **≥ 1** (zero-duration notes throw or go silent in Tone.js; the Serializer clamps) |
| `midi` | int 0–127, conditional | REQUIRED unless the track's instrument is `NoiseSynth` (unpitched — its trigger takes no note); MUST be absent on NoiseSynth tracks |
| `velocity` | float | `0 < velocity ≤ 1` (Tone.js convention; never 0–127) |

**Register invariant (roadmap invariant 4), made precise:** on every track with `role ≠ "drums"`, all `midi ≤ 71` (B4 — strictly below C5 = MIDI 72, scientific pitch, C4 = 60). Drum tracks are exempt because their `midi` values are synthesis trigger parameters (MembraneSynth kick at C1, MetalSynth hats around G5), not harmonic content. Enforced by the document validator and upstream by `ArrangementPlan` register lanes.

### 3.6 Patches

**InstrumentPatch**

```jsonc
{ "type": "MonoSynth", "options": { "oscillator": {"type": "sawtooth"}, "envelope": {...}, "filter": {...}, "filterEnvelope": {...} } }

{ "type": "PolySynth", "voice": "FMSynth", "maxPolyphony": 12, "options": { /* voice options */ } }
```

- `type` whitelist (v1): `Synth, MonoSynth, DuoSynth, FMSynth, AMSynth, MembraneSynth, NoiseSynth, MetalSynth, PluckSynth, PolySynth`. No `Sampler` in v1 — the roadmap commits to synthesized tones; sampled flavors would add async asset loading and hosting concerns (open question §7).
- `voice` (PolySynth only) whitelist: `Synth, MonoSynth, FMSynth, AMSynth, MembraneSynth, MetalSynth` — Tone.js requires PolySynth voices to be Monophonic subclasses; NoiseSynth/PluckSynth are not eligible and the validator rejects them.
- `options` is a plain nested JSON object of Tone.js constructor options. The generator only ever emits keys from a maintained server-side allowlist of (class, option-path) pairs, so a Tone.js upgrade is a deliberate migration, not silent drift. (Allowlist pinned as engine data `sound/allowlist.yaml` by PHASE_7 §5.2, 2026-07-07.)

**EffectPatch**

```jsonc
{ "type": "Reverb", "options": { "decay": 2.2, "preDelay": 0.01, "wet": 0.25 } }
```

`type` whitelist (v1): `Reverb, Freeverb, JCReverb, Chorus, FeedbackDelay, PingPongDelay, Distortion, Filter, EQ3, Compressor, Limiter, StereoWidener, AutoFilter, Tremolo, Vibrato`. Notes: `Filter/EQ3/Compressor/Limiter` are Tone "components" without a `wet` param — the schema does not add one. `wet` for true effects lives inside `options`.

**Buses**

```jsonc
"buses": [ { "id": "reverb", "effects": [ { "type": "Reverb", "options": { "decay": 2.5, "wet": 1.0 } } ] } ]
```

Bus `id`s unique; a bus's chain terminates in the master chain. Tracks feed buses via `sends` at `gainDb`.

### 3.7 The player contract (normative for any client)

1. Set `Tone.Transport.PPQ = header.ppq` **before** creating any scheduled objects (Tone's default is 192, not 480).
2. Schedule `header.tempos` on the Transport (`bpm.setValueAtTime` at tick positions); never pre-flatten to seconds.
3. Instantiate instruments/effects through an explicit whitelist map (`"FMSynth"` → `Tone.FMSynth`); reject unknown types.
4. Signal chain per track: `instrument → effects[] (in order) → Channel(volumeDb, pan, mute) → master input`; plus `channel.send(bus, gainDb)` per send. Master: `Destination` ← `master.effects` chain.
5. Before starting playback: `await` every `Reverb.ready`; call `.start()` on `Chorus`, `Tremolo`, `AutoFilter` instances.
6. Schedule notes via `Tone.Part` with tick-based times; NoiseSynth notes call `triggerAttackRelease(duration, time, velocity)` (no pitch); all others `triggerAttackRelease(Frequency(midi, "midi"), duration, time, velocity)`. Always use the callback's `time` argument, never `Tone.now()`.

### 3.8 Document validator (ships with the schema)

Structural rules beyond pydantic types, all testable without audio:

- V1 tempos/timeSignatures sorted, first at tick 0.
- V2 sections contiguous from 0, non-overlapping, exclusive ends, full coverage.
- V3 note lists sorted by `(ticks, midi)` (unpitched tracks: by `ticks`, and duplicate `ticks` are invalid — two simultaneous triggers of one instrument is a double-hit bug); `durationTicks ≥ 1`; velocities in (0, 1].
- V4 register invariant: non-drum tracks have all `midi ≤ 71`.
- V5 `midi` present iff instrument is not NoiseSynth.
- V6 every `sends[].bus` resolves to a declared bus; track ids unique; bus ids unique.
- V7 PolySynth patches carry `voice` + `maxPolyphony`; voice in Monophonic whitelist; non-PolySynth patches carry neither.
- V8 all notes end (`ticks + durationTicks`) within the final section's `endTick`.

### 3.9 Worked example (abbreviated)

The full version of this document is the milestone fixture (§8). Abbreviated to one bar and two tracks:

```jsonc
{
  "schemaVersion": 1,
  "meta": {
    "generatorVersion": "0.1.0", "toneVersion": "^15.1.0",
    "seed": "1ps9wxb", "seedOverrides": {},
    "params": { "styleFamily": "pop_rock", "mood": "happy", "tempo": 96, "key": "C" },
    "title": "Milestone fixture"
  },
  "header": {
    "ppq": 480,
    "tempos": [ { "ticks": 0, "bpm": 96 }, { "ticks": 15360, "bpm": 112 } ],
    "timeSignatures": [ { "ticks": 0, "numerator": 4, "denominator": 4 } ]
  },
  "sections": [
    { "type": "intro",  "label": "Intro",   "startTick": 0,     "endTick": 7680,  "energy": 0.3 },
    { "type": "verse",  "label": "Verse 1", "startTick": 7680,  "endTick": 15360, "energy": 0.5 },
    { "type": "chorus", "label": "Chorus",  "startTick": 15360, "endTick": 23040, "energy": 0.9 },
    { "type": "outro",  "label": "Outro",   "startTick": 23040, "endTick": 30720, "energy": 0.35 }
  ],
  "buses": [ { "id": "reverb", "effects": [ { "type": "Reverb", "options": { "decay": 2.5, "wet": 1.0 } } ] } ],
  "master": { "effects": [
    { "type": "Compressor", "options": { "threshold": -24, "ratio": 4 } },
    { "type": "Limiter",    "options": { "threshold": -1 } } ] },
  "tracks": [
    {
      "id": "kick", "role": "drums", "name": "Kick",
      "instrument": { "type": "MembraneSynth", "options": {
        "pitchDecay": 0.05, "octaves": 4, "oscillator": { "type": "sine" },
        "envelope": { "attack": 0.001, "decay": 0.4, "sustain": 0.01, "release": 1.4, "attackCurve": "exponential" } } },
      "effects": [], "channel": { "volumeDb": -2, "pan": 0, "mute": false }, "sends": [],
      "notes": [
        { "ticks": 0,    "durationTicks": 240, "midi": 24, "velocity": 0.9 },
        { "ticks": 960,  "durationTicks": 240, "midi": 24, "velocity": 0.85 }
      ]
    },
    {
      "id": "snare", "role": "drums", "name": "Snare",
      "instrument": { "type": "NoiseSynth", "options": {
        "noise": { "type": "pink", "playbackRate": 3 },
        "envelope": { "attack": 0.001, "decay": 0.13, "sustain": 0, "release": 0.03 } } },
      "effects": [], "channel": { "volumeDb": -6, "pan": 0.05, "mute": false },
      "sends": [ { "bus": "reverb", "gainDb": -18 } ],
      "notes": [ { "ticks": 480, "durationTicks": 120, "velocity": 0.8 } ]   // no midi: unpitched
    }
    // ... hats (MetalSynth), bass (MonoSynth), comping (PolySynth/FMSynth), pads (PolySynth/AMSynth + Chorus)
  ]
}
```

---

## 4. Pipeline IR contracts

Conventions shared by all IRs: frozen pydantic models; every time value is an integer tick at PPQ 480; pitch classes are ints 0–11 (C = 0); MIDI numbers use C4 = 60. IRs are internal — they are not serialized into `TrackDocument` (a future opt-in debug block is an open question).

Pipeline recap and ownership:

```
params → [1 Interpreter]   → GenerationPlan   (producer: Phase 2)
       → [2 Form]          → SongForm         (Phase 3)
       → [3 Harmony]       → HarmonicPlan     (Phase 4)
       → [4 Arrangement]   → ArrangementPlan  (Phase 5)
       → [5 Parts]         → Phrase[]         (Phase 5)
       → [6 Transitions]   → Phrase[]         (Phase 6)
       → [7 Humanizer]     → Phrase[] + tempo events   (Phase 6; events appended to
                                              header.tempos — PHASE_6 §6, 2026-07-07)
       → [8 Sound design]  → patches/FX       (Phase 7)
       → [9 Serializer]    → TrackDocument    (format pinned here; built in Phase 5)
```

### 4.1 `GenerationPlan` — produced by Interpreter, consumed by every stage

**Pinned core**

| Field | Type | Notes |
| --- | --- | --- |
| `stylePack` | `{id: str, version: str}` | resolved pack reference |
| `seed` | `{master: int (u64), overrides: {str: int}}` | see §5 |
| `key` | `{tonicPc: int 0–11, mode: str}` | mode strings: `"major", "minor", "dorian", "mixolydian"` starter set; vocabulary extensible by Phase 2/4 |
| `tempoBpm` | float | resolved (auto-from-mood already applied) |
| `timeSignature` | `{numerator: int, denominator: int}` | one per song in v1; mid-song changes are out of scope until a phase needs them |
| `swing` | `{ratio: float, subdivision: "8" \| "16"} \| null` | `ratio ∈ [0.5, 0.75]`, 0.5 = straight |
| `maxLengthTicks` | int | hard budget the Form generator fits to |
| `roleFlavors` | `{role: str}` | user's per-role sound flavor ids |

**Extension points** — `moodVector` (valence/arousal), `budgets` (density/dissonance/dynamics/layers), `timbreDirectives`: owned by **Phase 2** (with Phase 7 consuming `timbreDirectives`).

### 4.2 `SongForm` — produced by Form generator; consumed by Harmony, Arrangement, Transitions

**Pinned core**

| Field | Type | Notes |
| --- | --- | --- |
| `sections` | ordered list | see below |
| `totalBars` | int | |

Each section: `{id: str, type: str, index: int, startBar: int, lengthBars: int, energy: float}`.

- `id` unique (`"chorus-2"`); `type` from the section vocabulary (Phase 3 owns; starter set as §3.4); `index` = 1-based occurrence count per type; `startBar` 0-based; `lengthBars ≥ 4` (roadmap: never emit a section under 4 bars); `energy ∈ [0, 1]`.
- Bar → tick conversion is `startBar × numerator × (480 × 4 / denominator)` using the plan's time signature.
- `TrackDocument.sections` is derived 1:1 from these (type/label/energy + tick ranges).

**Extension points** — phrase substructure (4-bar groupings), cadence directives at boundaries, repetition/variation markers: owned by **Phase 3** (pinned in PHASE_3 §4, 2026-07-07 — note: Phase 3 pinned an `ending` directive but deliberately no cadence field; cadence logic stayed with Phase 4).

### 4.3 `HarmonicPlan` — produced by Harmony engine; consumed by all Part generators, Transitions

**Pinned core**

| Field | Type | Notes |
| --- | --- | --- |
| `chords` | ordered `[ChordEvent]` | covers the whole song, no gaps/overlaps |

`ChordEvent = {startTick: int, durationTicks: int, sectionId: str, chord: ChordSpec}`

`ChordSpec` (the shape every part generator retargets against):

| Field | Type | Notes |
| --- | --- | --- |
| `rootPc` | int 0–11 | |
| `quality` | enum | v1 core: `maj, min, dim, aug, maj6, min6, dom7, maj7, min7, minMaj7, min7b5, dim7, sus2, sus4, dom7sus4` |
| `extensions` | `[str]` | from `9, b9, #9, 11, #11, 13, b13`; may be empty |
| `bassPc` | int 0–11, optional | slash-chord bass; absent = root position |
| `symbol` | str | display symbol ("Am7", "F/G") — derived, for debugging/UI |
| `roman` | str, optional | Roman-numeral provenance ("V7/ii") — debugging/tests |

Structured fields (`rootPc`/`quality`/`extensions`) are canonical; `symbol` is never parsed by any stage.

**Extension points** — cadence annotations, borrowed-chord provenance, per-section key/modulation, chord-scale hints for part generators: owned by **Phase 4** (pinned in PHASE_4 §7, 2026-07-07: `keys` regions, per-event `scale`/`function`/`tags`, `poolSelections`).

### 4.4 `ArrangementPlan` — produced by Arrangement planner; consumed by Part generators, Transitions

**Pinned core**: `entries: [ArrangementEntry]`, one per `(sectionId, role)` pair, covering every section × every role:

| Field | Type | Notes |
| --- | --- | --- |
| `sectionId` | str | references SongForm |
| `role` | role enum | |
| `active` | bool | role silent in this section if false |
| `intensity` | int 1–4 | rung on the style pack's pattern intensity ladder (granularity provisional — Phase 5 confirms; see §7) |
| `densityBudget` | float 0–1 | soloist-space enforcement knob |
| `register` | `{lowMidi: int, highMidi: int}` | the role's lane; validator: `highMidi ≤ 71` for every role except drums |

**Extension points** — layering order, per-role articulation directives, lane-interaction rules (e.g. bass/kick locking hints): owned by **Phase 5** (resolved by PHASE_5 §4.4, 2026-07-07: layering order lives in pack data; the other two slots closed with no fields added — bass feel keys off `intensity`, kick-lock is an authoring convention with a reserved generator-interface hook).

### 4.5 `Phrase` — produced by Part generators; transformed by Transitions and Humanizer; consumed by Serializer

A Phrase carries **concrete pitches**: retargeting from degree-based patterns to actual chords happens *inside* the part generators (patterns + `HarmonicPlan` in, notes out), per the roadmap glossary. Downstream stages never see chord degrees.

**Pinned core**

| Field | Type | Notes |
| --- | --- | --- |
| `trackId` | str | target document track (`"kick"`, `"bass"`) |
| `role` | role enum | |
| `startTick`, `endTick` | int | span covered |
| `notes` | `[PhraseNote]` | sorted by `(ticks, midi)` |

`PhraseNote = {ticks: int, durationTicks: int, midi: int?, velocity: float, tags: [str]}` — same semantics as document NoteEvents (`midi` absent only for unpitched instruments); `tags` is a free string list for cross-stage annotations (e.g. `"ghost"`, `"accent"`, `"fill"`).

**Extension points** — the `tags` vocabulary and any structured humanizer hints: owned by **Phases 5/6** (PHASE_5 §8.1 contributes `"ghost"` and `"push"`, 2026-07-07; PHASE_6 §3.9 contributes `"fill"`, `"crash"`, `"var"`, `"hold"`, 2026-07-07). Source annotations for debugging (`sourcePatternId`, bar index) may be added by Phase 5.

The Humanizer is `Phrase[] → Phrase[]` (same shape, adjusted ticks/velocities/durations); the Serializer is `Phrase[] + patches → TrackDocument` and is intentionally thin.

---

## 5. Hierarchical seed system

Owned entirely by this phase. Requirements: same `(params, seed)` → identical track; named sub-streams; "reroll just the drums"; shareable seeds.

### 5.1 Master seed

- Internally: unsigned 64-bit int.
- User input is one of two **distinct, mutually exclusive** parameters (never guessed from shape — every lowercase alphanumeric string is *also* valid base36, so sniffing would be ambiguous):
  - `seed`: a canonical base36 string (what documents echo and users share). Parsed as base36, must decode to a u64.
  - `seedText`: any free string ("banana"). Always hashed: `master = int.from_bytes(sha256(utf8(s)).digest()[:8], "big")`.
- `meta.seed` always echoes the canonical base36 integer — never the raw `seedText`. (u64 exceeds JSON's safe-integer range in JS, so the base36 *string* is also the transport encoding.)
- Fresh seeds (no user seed given): 8 bytes from `os.urandom` at the API boundary — the single place entropy may enter; everything downstream is pure.

### 5.2 Derivation — named, chained, hash-based

```python
def derive(parent: int, name: str) -> int:
    payload = parent.to_bytes(8, "big") + b"/" + name.encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
```

- SHA-256 gives full avalanche: no correlated-stream risk (the `seed+1`-into-weak-PRNG failure mode documented by NumPy and Minecraft's MC-55596 is impossible by construction).
- **Names, not indices**: adding a stage never renumbers existing streams, so old seeds keep producing the same song across versions (within a `generatorVersion`).
- Hierarchy by chaining: `derive(derive(derive(M, "drums"), "fills"), "bar:17")` — the same tree-hashing scheme as NumPy `SeedSequence` / JAX `fold_in`.

**Stream registry (pinned)** — top-level names: `interpreter, form, harmony, arrangement, drums, bass, comping, pads, transitions, humanize, sound`. Sub-stream names below a top-level stream are owned by that stage's phase. (`interpreter` added by PHASE_2 D4, 2026-07-06 — additive amendment.)

### 5.3 Per-stage RNG instances

The orchestrator constructs `random.Random(stream_seed)` per stage and passes it in explicitly. Stages never import `random` module-level functions, never create their own instances, and never read ambient entropy or wall-clock. Rationale: a shared sequence couples stages through consumption order — one extra draw in harmony would change every downstream stage and make per-stream rerolling impossible in principle (the bug DCSS shipped and retrofitted away).

Allowed operations on a stage RNG: `getrandbits`, `randrange`, and our own helpers below. Distribution helpers whose algorithms have changed across CPython versions (`sample`, `choices`, `shuffle`) are banned; we provide deterministic equivalents:

```python
def weighted_choice(items: Sequence[T], weights: Sequence[int], rng: random.Random) -> T:
    # weights are INTEGERS — float cumulative sums can flip picks in the last ulp
    total = sum(weights)                      # > 0, validated
    r = rng.randrange(total)
    acc = 0
    for item, w in zip(items, weights):
        acc += w
        if r < acc:
            return item
```

**Determinism rules (binding on all phases):** integer weights everywhere; any candidate list built from a dict/set is sorted by an explicit stable key before drawing; no floats in selection logic (floats are fine in *outputs* like velocity); no wall-clock, no `os.urandom` outside the API boundary.

### 5.4 Reroll API

Song identity = `(params, master, overrides)` where `overrides: {streamName: int}`.

```python
def stream_seed(master: int, overrides: dict[str, int], name: str) -> int:
    return overrides.get(name, derive(master, name))
```

Reroll the drums = set `overrides["drums"]` to a fresh random u64 (stored thereafter); revert = delete the key. `meta.seedOverrides` echoes the map, so any document is reroll-continuable.

### 5.5 Encoding

Seeds display and transport as lowercase **base36** (≤ 13 chars for u64; case-insensitive on input; `int(s, 36)` both directions in Python/JS).

### 5.6 Golden vectors (normative — the implementation MUST reproduce these)

Master from string: `master_from_string("banana") = 13011977409198548045` (base36 `2qux517snxfm5`).

For `master = 3735928559` (base36 `1ps9wxb`):

| Stream | `derive(M, name)` | base36 |
| --- | --- | --- |
| `interpreter` | 1597995742192405040 | `c52i7pgxyq7k` |
| `form` | 7567330889165579844 | `1lhqyx6gblkjo` |
| `harmony` | 226146634901021418 | `1puqahumzht6` |
| `arrangement` | 17905737752012141625 | `3s1f2al1nfupl` |
| `drums` | 13141849116576272873 | `2rufwpmioicx5` |
| `bass` | 12266082893315700426 | `2l6wrhtnwz6bu` |
| `comping` | 15485288006162947228 | `39necguatbd7g` |
| `pads` | 16576309723187015011 | `3hxszdzu7hdgj` |
| `transitions` | 17897360909067852929 | `3rz4ky8iu33wh` |
| `humanize` | 3899203291477031323 | `tmh47jcjtpjv` |
| `sound` | 11189761989562234097 | `2d0ivksicdiwh` |

Chained: `derive(drums, "fills") = 2174782555333666359`; `derive(fills, "bar:17") = 1110592329615889969`.

RNG behavior: `random.Random(derive(M, "drums"))` first five `getrandbits(32)` = `[2813930941, 3236345189, 575825508, 1551984896, 116936044]`; first five `randrange(100)` from a fresh instance = `[83, 96, 17, 46, 3]`.

---

## 6. Style-pack structure

A style family ships as a **versioned directory of YAML files** — data, not code (roadmap invariant 1). YAML over JSON for authoring ergonomics: comments are invaluable in hand-authored pattern banks, and per-role files keep diffs and reviews sane. Loaded once via `yaml.safe_load`, validated into frozen pydantic models; YAML's scalar footguns are neutralized by pydantic coercion + strict schemas.

```
styles/pop_rock/
  manifest.yaml        # identity + compatibility
  interpreter.yaml     # supported moods, mode menu, tonic pools, feel,
                       #   expression ranges, flavors/ensembles — schema owned by Phase 2
  patterns/
    drums.yaml         # pattern bank, schema owned by Phase 5
    bass.yaml          #   "
    comping.yaml       #   "
    pads.yaml          #   "
  progressions.yaml    # progression pools, schema owned by Phase 4
  forms.yaml           # form tendencies, schema owned by Phase 3
  transitions.yaml     # boundary devices & mutation config, schema owned by Phase 6
  timbres.yaml         # timbre palette, schema owned by Phase 7
```

### 6.1 `manifest.yaml` (pinned)

```yaml
formatVersion: 1          # style-pack format version (this document's)
id: pop_rock
name: Pop / Rock
version: 0.1.0            # pack content version, semver
engine: ">=0.1"           # generator compatibility range
timeSignatures: [[4, 4]]  # signatures the pack's patterns support
tempoRange: [70, 170]     # sane bpm bounds for the family
```

### 6.2 Shared pattern envelope (pinned)

Every entry in every pattern bank, regardless of role, carries this envelope — the fields the *selection* machinery (weights + eligibility, per the BIAB/Yamaha/MMA consensus) and the Arrangement planner rely on:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | str | unique within the pack |
| `role` | role enum | |
| `kind` | `main \| fill \| intro \| ending \| break` | pattern class (the Yamaha section model); fills are 1 bar by convention |
| `energyLevel` | int 1–4 | rung on the intensity ladder (matches `ArrangementPlan.intensity`) |
| `lengthTicks` | int | whole bars at PPQ 480 |
| `weight` | int ≥ 1 | selection weight among eligible candidates (integer, per §5.3) |
| `eligibility` | object | extension point owned by Phase 5 — pinned by PHASE_5 §3.2 (2026-07-07): optional `tempoBpm: [min, max]` only in v1; Phase 6 may add fill-specific dimensions by amendment there |
| `events` | list | see below |
| `retarget` | object | `{registerLow: int, registerHigh: int, onChordChange: hold \| retrigger \| stop}` pinned; semantics pinned by PHASE_5 §3.3 (anchor placement, lane folding, retrigger split); voicing policy lives in PHASE_5 §5.4/§6.4 |

### 6.3 Event primitives (pinned)

**Pitched roles** (bass, comping, pads) — rhythm + chord-degree roles, never literal pitches (roadmap invariant 2; MMA's degree/velocity tuple is the model):

```yaml
# {pos: int ticks from pattern start, dur: int ticks, degree: role, octave: int offset, velocity: 0-1}
- { pos: 0,   dur: 480, degree: root,   octave: 0, velocity: 0.9 }
- { pos: 480, dur: 240, degree: fifth,  octave: 0, velocity: 0.7 }
- { pos: 720, dur: 240, degree: guide3, octave: 0, velocity: 0.75 }
```

`degree` core vocabulary (v1): `root, third, fifth, seventh, guide3, guide7, tension, approach`. Semantics of `tension` (which tension, chosen how) and `approach` (chromatic vs diatonic, targeting next chord) are resolved by Phase 5 with Phase 4's theory utilities; the vocabulary may be *extended* by Phase 5, not repurposed. (Resolved and extended by PHASE_5 §3.3, 2026-07-07: full resolution table with dressing-safe fallbacks; added degrees `sixth` and `chord`; added event fields `push` and `minDensity`.)

**Drums** — voice + velocity, no harmonic content:

```yaml
- { pos: 0,   voice: kick,       velocity: 0.9 }
- { pos: 480, voice: snare,      velocity: 0.8 }
- { pos: 240, voice: hat_closed, velocity: 0.5 }
```

Drum voice vocabulary (v1): `kick, snare, hat_closed, hat_open, ride, crash, tom_low, tom_mid, tom_high, perc`. The voice→track mapping is engine data pinned by PHASE_5 §8.2 (2026-07-07 amendment: `hat_closed`/`hat_open` share the `hats` track; all others map 1:1); trigger conventions and patches remain in the pack's `timbres.yaml` (Phase 7).

`progressions.yaml`, `forms.yaml`, `timbres.yaml` have only their *existence and ownership* pinned here; their schemas are designed in Phases 4, 3, and 7 respectively, as sections in those PHASE docs.

---

## 7. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | ~~Params schema (`meta.params` shape)~~ **Resolved** — PHASE_2 §3 | Phase 2 | mood taxonomy design |
| Q2 | ~~Intensity-ladder granularity: is 1–4 right?~~ **Resolved** — confirmed 1–4, global energy thresholds (PHASE_5 §3.1) | ~~Phase 5~~ | — |
| Q3 | ~~Eligibility-tag dimension set for pattern selection~~ **Resolved** — optional tempo band only + completeness rules (PHASE_5 §3.2) | ~~Phase 5~~ | — |
| Q4 | ~~`progressions.yaml` / `forms.yaml` / `timbres.yaml` schemas~~ **Fully resolved** — `forms.yaml` PHASE_3 §5; `progressions.yaml` PHASE_4 §4; `timbres.yaml` PHASE_7 §4 | ~~Phases 4 / 3 / 7~~ | — |
| Q5 | ~~Does PPQ 480 suffice for humanizer micro-timing?~~ **Resolved** — confirmed sufficient; every modeled effect ≥ 3 ticks, float-ms math with one terminal rounding (PHASE_6 §5.7/D16) | ~~Phase 6~~ | — |
| Q6 | ~~Mid-song key modulation representation~~ **Resolved** — deferred post-v1; `HarmonicPlan.keys` region list reserved (PHASE_4 §7.1/D10) | ~~Phase 4~~ | — |
| Q7 | Optional `debug` block embedding IRs in `TrackDocument` | Any phase that needs it | additive, non-breaking |
| Q8 | Sampler support (sampled instrument flavors) | Post-v1 | asset hosting + async loading story |
| Q9 | Exact Tone.js minor version to pin (`^15.1.0` assumed) | Phase 1 implementation session | check current stable when the playground is built |
| Q10 | Package name (`trackgen` provisional) | Phase 1 implementation session | none (trivial) |

---

## 8. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Backend: Python ≥ 3.12** | Focus is generation quality; browser handoff is trivial serialization (user decision). | TypeScript/Node (research's lean: Tonal.js + shared zod types — outweighed by the quality-focus argument); deferring the decision (would have left schemas language-ambiguous all session). |
| D2 | **Theory: music21, wrapped** | Best-in-class Roman-numeral/key machinery, BSD, maintained; wrapper keeps stages decoupled from its score-centric model. | Hand-rolled theory (re-implements solved problems); mingus (GPL, dead since 2020); pychord (too narrow); deciding in Phase 4 (leaves a load-bearing dependency dangling). |
| D3 | **Ticks only, PPQ 480** | Seconds fields are derived data that goes stale; carrying both causes the documented double-tempo bug (Tonejs/Midi #81). 480 = DAW convention, rich divisibility. | Ticks + derived seconds (@tonejs/midi's shape — redundant, trap-prone); PPQ 960 (insurance without identified need; Q5 escape hatch exists). |
| D4 | **Flat tracks + `role` tag; drum kit = one track per drum voice** | Tone.js synth drums are distinct classes needing distinct instances; 1:1 track↔instrument keeps the client trivial; grouping derivable from `role`. | Nested role groups (two-level schema everywhere for one use case); single drums track with per-note voice selector (client demux, awkward per-voice mixing). |
| D5 | **FX: per-track inserts + optional named buses/sends** | Gets the idiomatic shared-reverb mix without a future schema break; unused = zero cost; Tone.Channel send/receive exists. | Inserts only (duplicate convolution CPU, schema bump later); reverb-only hardcoded bus (bakes a mixing assumption in). |
| D6 | **`meta` = full regeneration identity (params + seed + overrides + versions)** | Documents self-describing: regenerate or reroll from the document alone; ~1 KB. | Seed only (client must hold params; shared docs not reproducible); embedding debug IRs by default (moved to Q7 as opt-in). |
| D7 | **Sections as typed ranges with `energy`** | Every consumer wants ranges; instant markers in an untyped meta bucket are strictly weaker. | MIDI-marker instants (`{name, ticks}`). |
| D8 | **Seeds: SHA-256 name-chained derivation + per-stage `random.Random`** | Avalanche kills correlated-stream failure modes; names keep streams stable across versions; per-stage instances are what make per-stream rerolling possible at all; stdlib-only. | numpy SeedSequence (ties stream identity to numpy internals; positional spawn keys); stateless counter-based draws (verbose addressing for sequential lines); shared global RNG (breaks rerolling — disqualifying). |
| D9 | **Integer weights + owned `weighted_choice`; ban `choices/sample/shuffle`** | Float cumulative sums flip picks in the last ulp; CPython has changed distribution-helper algorithms across versions. | stdlib helpers (version-fragile); float weights (nondeterminism risk). |
| D10 | **Style packs: directory of YAML + manifest** | Hand-authoring ergonomics (comments!), reviewable diffs, per-role files; pydantic validation neutralizes YAML footguns. | JSON files (no comments, noisy to author); single file per style (thousands of lines, merge-conflict magnet). |
| D11 | **IRs pinned as core + named extension points** | Cross-stage load-bearing fields locked now; owning phases keep design freedom where their research hasn't happened yet; additions never silently break consumers. | Full field-level now (designs Phase 3–5 internals without their research); semantics-only (nothing concrete to validate or build against). |
| D12 | **Patch encoding: tagged union of Tone constructor options; whitelists both sides; `toneVersion` pinned in meta** | `get()`/constructor round-trip makes options-as-JSON sound; whitelists prevent arbitrary instantiation; Tone v13→v14 proved version drift is real. | GM-style program numbers (roadmap already replaced them); node-graph event streams (over-general for our fixed chain shape). |
| D13 | **No Sampler in v1; synthesis only** | Roadmap commits to synthesized tones; samples add async asset loading/hosting concerns with no v1 payoff. | Allowing Sampler with URL maps (deferred to Q8). |
| D14 | **Register invariant concretized: non-drum `midi ≤ 71` (below C5=72); drums exempt** | Makes roadmap invariant 4 machine-checkable; drum trigger notes are timbre parameters, not harmonic content. | Applying the ceiling to drums too (would forbid MetalSynth's ~G5 trigger convention for hats). |
| D15 | **Milestone fixture exercises every schema feature** | The milestone exists to de-risk the contract; anything unexercised stays risky until Phase 5. | Minimal smoke fixture; dual smoke+full fixtures (playground can load any fixture later anyway). |
| D16 | **Project tooling (2026-07-08): uv + Ruff/mypy + Typer + Hypothesis; goldens = committed JSON + hand-rolled semantic `bless`; library-first, HTTP deferred** | Reproducibility is the project's core value, so an exact `uv.lock` and pinned music21/Tone make dependency bumps deliberate bless-style events; Ruff banned-API rules turn determinism invariant 5 into an enforced gate, not a manual grep; the semantic per-stage bless report (PHASE_8 §8.2) is domain-specific, so no snapshot library can produce it; the pipeline is a pure function, so a library + Typer CLI is the honest shape and HTTP is a thin wrapper when a client exists; music21 is lazy-imported to contain its slow import and transitive numpy pull. | FastAPI from day one (premature request/validation/deploy surface, orthogonal to generation quality); Poetry / pip-tools (slower, weaker reproducibility than uv); syrupy/approvaltests as the golden *system* (textual diffs can't satisfy the semantic report); Hypothesis over pipeline internals (avoided — it draws params+seed, never fights the RNG). |

---

## 9. Definition of done

Phase 1 is **built** when an implementation session demonstrates all of the following:

1. **Schema package**: frozen pydantic models for `TrackDocument` (complete) and the five IR pinned cores, with the §3.8 validator rules implemented; `docs/schema/trackdocument.schema.json` exported and committed.
2. **Seed module**: `master_from_string`, `derive`, `stream_seed`, base36 codec, `weighted_choice` — passing a golden-vector test that asserts every value in §5.6 exactly.
3. **Pack loader**: loads a minimal stub pack (`styles/_stub/` with a manifest and one tiny pattern bank per role using only pinned envelope/event fields), validates it, and rejects fixtures with each class of envelope violation.
4. **Milestone fixture**: `fixtures/milestone.trackdoc.json` — hand-written, 16 bars (intro/verse/chorus/outro, 4 bars each), tempo change 96→112 at the chorus, six tracks (kick MembraneSynth, snare NoiseSynth *unpitched*, hats MetalSynth, bass MonoSynth, comping PolySynth/FMSynth, pads PolySynth/AMSynth with a Chorus insert), a shared reverb bus with sends from snare/comping/pads, master Compressor+Limiter, full meta echo with seed `1ps9wxb`. Passes schema + validator.
5. **Playground**: `playground/index.html` (plain HTML + `tone@15.1.x` from CDN, no build step) implementing the §3.7 player contract: loads any fixture, builds the graph, plays through.
6. **Listening checklist** (manual, against the milestone fixture):
   - [ ] All six tracks audible; drums (kick/snare/hats) in time with each other.
   - [ ] Snare (unpitched) triggers correctly; hats ring metallic, kick has pitch drop.
   - [ ] Bass and comping change pitch with the (hand-written) chord changes; nothing sounds above C5 except cymbal shimmer.
   - [ ] Tempo audibly steps up at the chorus downbeat; sections align with the documented tick ranges (log or UI markers).
   - [ ] Reverb audible on sends (mute the bus → dry), master limiter prevents clipping at full ensemble.
   - [ ] Document plays identically on reload (no scheduling nondeterminism).
7. **Determinism guard**: a test that constructs two RNGs from the same stream seed and asserts identical draw sequences, plus a Ruff banned-API rule (§2) that fails on any `random.` module-level call, `datetime.now`, `time.*`, or `os.urandom` outside the seed API boundary.

Golden-seed regression tests over full generated documents arrive with Phase 5 (first end-to-end track); Phase 1's golden surface is the seed vectors + fixture validation.

---

## 10. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §6: YAML directories, loaded and validated; no executable content |
| 2. Rhythm stored separately from pitch | §6.3: degree-role events in packs; concrete pitches only appear in Phrases after retargeting (§4.5) |
| 3. Hierarchical seeds | §5: named tree derivation, per-stage instances, override-based rerolls |
| 4. Soloist owns above ~C5 | §3.5/§3.8 V4 (document validator), §4.4 (register lanes) — non-drum `midi ≤ 71` |
| 5. Deterministic pipeline | §5.3 rules, §9.7 guard; entropy enters only at the API boundary |
