# PHASE_7 — Sound Design

Designed 2026-07-07 (session 7). Status: **awaiting approval**.

This document pins pipeline stage 8 — the Sound designer, `GenerationPlan + pack → patches/FX/mix` — end to end: the patch-evaluation model (base patch + bounded directive modulation, baked once per song), the `timbres.yaml` pack-file schema (resolving the last piece of PHASE_1 Q4), the engine-owned modulation-default and option-allowlist data files, the bus/insert routing architecture, the mix layer (per-track levels/pans/sends, master chain), drum-kit recipes, and normative reference content for `pop_rock` and `jazz`. It replaces the PHASE_5 §8.4 stub `timbres.yaml` and the §8.3 stub channel/master defaults, concretizes PHASE_1 §3.6's "maintained server-side allowlist," and partially resolves PHASE_6 Q2 (the riser patch recipe).

Research base (session 7): the timbre–affect literature (Eerola/Ferrer/Alluri 2012; Chau/Wu/Horner 2017 — register-dependence of the centroid–affect relationship; Grey/McAdams timbre-space axes; log-attack-time as the perceptual envelope axis); reverb–emotion measurement (Mo/Wu/Horner ICMC 2016; Tajadura-Jiménez 2010; Västfjäll 2002); roughness psychoacoustics (Plomp & Levelt; Vassilakis); applied emotion→parameter systems (AffectMachine-Classical/Pop, Wallis 2011, MetaCompose); shipped Tone.js synthesis recipes (official `shiny.html`/`bembe.html`/`monoSynth.html` examples, documented community drum/EP/pad recipes, v14→v15 API notes); the patch+mix-as-data architectures of GM/GS/XG (program + CC7/10/91/93 + XG's per-part Brightness/EG vector), Yamaha SFF setup measures and CASM note limits, Band-in-a-Box `.STY`/`.STX`, JJazzLab `Instrument`/`InstrumentMix`, Logic Patches + Smart Control macro mappings, and synth-macro data models (Vital/Serum/Ableton rack ranges); and mixing practice (Senior, Owsinski's five arrangement elements, published rhythm-section dB/pan/send tables, master-bus and LUFS conventions, jazz-combo vs pop/rock mix norms).

---

## 1. Scope

**In scope**

- The patch-evaluation model: how `timbreDirectives` (brightness, attackHardness, space) turn a flavor's base patch into concrete Tone.js constructor options — mapping-entry semantics (`{param, min, max, curve}`), merge rules, evaluation order, rounding, determinism.
- The `timbres.yaml` pack-file schema, complete and field-level (resolving the last part of PHASE_1 Q4): pitched flavors, drum kits, per-flavor effects and mix, the reverb-bus config, the master chain. Validation rules with the PHASE_2 D14 cross-file flavor-completeness check.
- Engine-owned data files: `sound/mod_defaults.yaml` (per-role/per-voice directive mapping defaults) and `sound/allowlist.yaml` (the (class, option-path) allowlist PHASE_1 §3.6 called for).
- Routing: one shared reverb bus with per-track sends; character effects as per-flavor inserts; pads width via StereoWidener.
- The mix layer: per-track `channel` values (replacing PHASE_5 §8.3's stubs), gain-staging conventions for hot synth classes, per-pack master chains.
- Drum-kit structure: per-voice patches, trigger `midi` values, per-voice mix, brightness/space modulation of kit color.
- Normative reference `timbres.yaml` content for `pop_rock` and `jazz` covering every flavor id the PHASE_2 `interpreter.yaml` files declare.
- The dormant riser patch recipe (PHASE_6 Q2's Phase-7 half).
- Worked examples chained from PHASE_2 §6.5 (evaluated patches, sends, bus, master for both reference tracks).
- Amendments to earlier documents (all additive, §12).

**Explicitly not in scope**

- Any note or timing change — this stage never touches Phrases. It consumes the plan and emits sound.
- The browser player (PHASE_1 §3.7 already pins the client contract this stage's output feeds: whitelist instantiation, `Chorus`/`Tremolo`/`AutoFilter.start()`, awaiting `Reverb.ready`).
- Sampled instruments (PHASE_1 D13/Q8 — synthesis only; the research confirms acoustic piano and strummed guitar are the honest casualties, §4.6).
- Style-pack content beyond the two reference `timbres.yaml` files (Phase 8), including riser pack opt-in (PHASE_6 Q2's other half).
- Loudness normalization / LUFS measurement (an offline-render concern; targets documented as guidance, §6.4).
- Runtime/per-section timbre changes — patches are baked once per song (D6).

---

## 2. Contracts consumed

| Upstream contract | What this phase does with it |
| --- | --- |
| `GenerationPlan.timbreDirectives` (PHASE_2 §7.3) | The three scalars drive all patch modulation (§3). No fields are added to the slot (PHASE_2 offered negotiation; none needed). `brightness` → per-role tone-color parameters; `attackHardness` → envelope attack (pitched roles only, D4); `space` → reverb sends + bus decay/preDelay. |
| `GenerationPlan.roleFlavors` (PHASE_1 §4.1, PHASE_2 §6 step 10) | Resolved flavor ids select recipes. The PHASE_2 D14 completeness check lands here: every flavor id a pack's `interpreter.yaml` declares must have a recipe (TB1). |
| `GenerationPlan.moodVector`, `budgets` | **Not consumed.** The directives already carry the mood overrides (PHASE_2 §4.3); dynamics/density were consumed upstream. Mood words never visible (PHASE_2 §7.1 discipline). |
| Patch encoding (PHASE_1 §3.6) | Output patches are exactly the pinned tagged unions: instrument whitelist (10 classes), PolySynth `voice`/`maxPolyphony` rules, effect whitelist (15 classes). The "maintained server-side allowlist of (class, option-path) pairs" is concretized as `sound/allowlist.yaml` (§5.2, D12). |
| Buses/sends/master (PHASE_1 §3.6, D5) | One document bus (`reverb`) with per-track `sends`; `master.effects` from pack data. The PHASE_1 milestone fixture already exercised this exact shape. |
| Track model (PHASE_1 §3.5, D4) | One instrument per track; drum kit = one track per voice. `channel {volumeDb ≤ 6, pan ∈ [−1,1], mute}` filled by this stage. |
| Drum voice→track mapping (PHASE_5 §8.2) | Kit recipes are keyed by the nine voice-track ids (`kick, snare, hats, ride, crash, tom_low, tom_mid, tom_high, perc`); `hat_closed`/`hat_open` share the `hats` patch. Trigger `midi` values (reserved to this phase there) are pinned per kit voice (§4.3). |
| Serializer (PHASE_5 §8.3) | The stub channel defaults, stub mix, and stub master chain are replaced by this stage's output (§7, amendment §12.4). Tracks are instantiated only for voices/roles with phrases; sound design emits the full map, the Serializer selects. |
| Seed system (PHASE_1 §5) | The `sound` stream stays **reserved — zero draws in v1** (D3, the `arrangement` precedent). `sound_design` is a pure function of `(plan, pack)`. |
| `toneVersion` (PHASE_1 §3.2, Q9) | Recipes are authored against `^15.1.x` (constructor-option shapes stable v14→v15 for every whitelisted class). Exact pin remains PHASE_1 Q9 (implementation session). |
| Determinism rules (PHASE_1 §5.3) | No draws; deterministic evaluation order (§3.4); 3-decimal half-even rounding on every evaluated value. |
| Riser reservation (PHASE_6 §9 Q2) | The patch half is resolved here (§4.7, dormant); placement/pack opt-in stays Phase 8. |

---

## 3. The patch-evaluation model

The architecture (D1, D5, D6): a flavor is a **base patch** (fixed Tone.js constructor options) plus a **mix block**; the three directives modulate it through **bounded mapping entries** merged from engine defaults and per-flavor overrides; evaluation happens **once per song** at patch-build time, emitting plain JSON. This is the shipping-product consensus made data: XG's per-part Brightness/EG vector, Logic Smart Controls' per-patch `{min, max, curve}` mappings, Ableton macro *variations* (snapshot evaluation), Yamaha's setup-measure-once model. Mood never swaps a patch — identity is the user's flavor choice; character within the identity is continuous (the industry line every product studied draws).

### 3.1 Mapping entries

```yaml
- { param: <dotted path>, min: <number>, max: <number>, curve: linear|exp }
```

- `param` is a dotted path into either the patch's `options` object (`filterEnvelope.baseFrequency`, `noise.playbackRate`, `resonance`) or the flavor's mix block (`mix.sends.reverb`).
- Evaluation at directive value `d ∈ [0, 1]`:
  - `linear`: `v = min + d × (max − min)`
  - `exp`: `v = min × (max/min)^d` — for frequencies and times, whose perception is logarithmic (log-attack-time and log-frequency are the empirical perceptual axes). Requires `min, max > 0`.
- **Inverted ranges are legal** (`min > max`): `attackHardness` maps attack from slow to fast this way (Serum/Ableton semantics).
- Every evaluated value is rounded to 3 decimals (half-even) before entering the patch.

### 3.2 Merge rule (engine defaults + flavor overrides — D1)

Engine data `sound/mod_defaults.yaml` (§5.1) ships one mapping table per role (drums: per voice). A flavor's optional `mod` block **replaces the default list per directive key** (drums: per `(directive, voice)` key) — the PHASE_2 anchor/formulas/overrides pattern applied to timbre. An empty list (`brightness: []`) explicitly disables a directive for that flavor. There is no entry-level merging: whoever owns the key owns the whole list.

**Why overrides exist:** the defaults are authored against each role's reference engine class (§5.1); a flavor built on a different class has different levers — an FM electric piano maps `brightness` to `modulationIndex`, not a filter cutoff — and a flavor may re-range a default where its character demands (the jazz brush kit re-ranges the snare's `noise.playbackRate` downward). Validation forces this to stay coherent: every effective mapping's `param` must be legal for the flavor's engine class per the allowlist (TB7), so a mismatched default can never silently apply.

### 3.3 Base XOR mod (pinned)

After the merge, a given `param` path may be set by the base patch **or** targeted by a mapping — never both (TB7). Mapped parameters are simply absent from `base`; the mapping is the single authority for their value. This kills the "which value wins" ambiguity at the schema level. Unmapped subfields of the same nested object are authored in `base` as normal (e.g. `filterEnvelope.decay` in base while `filterEnvelope.baseFrequency` is mapped).

### 3.4 Evaluation order and determinism

For each track's patch: deep-copy `base`; apply directives in the fixed order **brightness → attackHardness → space**, each mapping list in authored order, setting each evaluated value into the options object (or mix block) by path. Since base XOR mod holds and the three directive lists target disjoint or identical-by-authoring paths, the order is load-bearing only for pathological authoring — it is pinned so such authoring is still deterministic. Zero RNG (D3): `sound_design` accepts the `sound` stream for interface uniformity and never consumes it; the stream and its PHASE_1 golden vectors stay reserved.

### 3.5 Register discipline

Brightness ranges are **per-role** because spectral centroid is register-confounded (Chau 2017: centroid↔octave r ≈ 0.69) — the same 0–1 scalar must mean different absolute Hz per role (bass caps at 2.5 kHz where pads reach 9 kHz, §5.1). Tone.js has no filter keytracking; the mitigation is Yamaha's: our roles are already register-bounded (ArrangementPlan lanes), so each flavor's filter values are tuned for its role's lane. Per-note cutoff scaling is post-v1 (§11 Q2).

---

## 4. The `timbres.yaml` schema

The last pack file (PHASE_1 §6 layout), schema owned by this phase. Three top-level parts: `flavors`, `bus`, `master`.

### 4.1 Top level

```yaml
flavors:
  drums:   { <flavorId>: <KitFlavor>, ... }      # exactly the ids interpreter.yaml declares
  bass:    { <flavorId>: <PitchedFlavor>, ... }
  comping: { <flavorId>: <PitchedFlavor>, ... }
  pads:    { <flavorId>: <PitchedFlavor>, ... }

bus:                                # the single shared reverb bus (D2)
  reverb:
    decay: [lo, hi]                 # seconds; evaluated exp by `space` (§6.2)
    preDelay: [lo, hi]              # seconds; evaluated linear by `space`
    returnFilterHz: <number>        # highpass on the return (keeps the low end dry)

master:                             # EffectPatch list, verbatim into TrackDocument.master
  - { type: Compressor, options: {...} }
  - { type: Limiter,    options: {...} }
```

### 4.2 `PitchedFlavor`

```yaml
engine: { type: <class>, voice: <class>?, maxPolyphony: <int>? }
  # type from the PHASE_1 §3.6 instrument whitelist;
  # voice/maxPolyphony present iff type == PolySynth (PHASE_1 V7 rules)
base: { ... }                       # Tone.js constructor options, minus mapped params (§3.3)
effects: [ <EffectPatch>, ... ]     # ordered inserts; the flavor's identity FX (may be empty)
mix:
  volumeDb: <float ≤ 6>
  pan: <float −1..1>
  sends: { reverb: <gainDb> }?      # base send; omitted when a `space` mapping targets it
mod:                                # optional per-directive override lists (§3.2)
  brightness: [ <mapping>, ... ]
  attackHardness: [ ... ]
  space: [ ... ]
```

### 4.3 `KitFlavor`

```yaml
kit:                                # ALL NINE voice-track ids required (TB5)
  kick:     { midi: 24, patch: {type: MembraneSynth, options: {...}}, mix: {...} }
  snare:    {           patch: {type: NoiseSynth,    options: {...}}, mix: {...} }   # no midi (unpitched)
  hats:     { midi: 80, patch: {type: MetalSynth,    options: {...}}, mix: {...} }
  ride:     { midi: 82, patch: ..., mix: ... }
  crash:    { midi: 84, patch: ..., mix: ... }
  tom_low:  { midi: 43, ... }
  tom_mid:  { midi: 47, ... }
  tom_high: { midi: 50, ... }
  perc:     {           patch: {type: NoiseSynth, ...}, mix: ... }                   # unpitched in v1 refs
mod:                                # optional; keyed directive → voice → mapping list
  brightness: { snare: [ ... ] }
```

- `midi` is the trigger note the part generators emit for that track (PHASE_5 §8.2 reserved it here). Required unless the voice's patch is `NoiseSynth` (PHASE_1 V5). Values above are the pinned reference conventions (kick C1=24; toms G1/B1/D2; hats/ride/crash trigger notes for MetalSynth, whose sounding pitch comes from its `frequency` option, not the trigger).
- Per-voice `mix` has the same shape as pitched `mix`.
- Kits cover all nine ids even when a pack's patterns don't use a voice (cheap, and Phase 6 adds `crash` at runtime); the Serializer instantiates only tracks that have phrases.

### 4.4 Mix semantics — two-layer gain (D7)

- **`options.volume`** (inside a patch) = class gain-staging trim, making raw synth classes comparable: MetalSynth is notoriously hot (reference trims −12 on hats/ride/crash), NoiseSynth moderately (−4). These are part of the recipe.
- **`mix.volumeDb`** (→ `channel.volumeDb`) = the musical balance, from the researched rhythm-section tables (kick-anchored offsets; jazz rides prominent, pop kick forward).
- Both are pack data; final loudness calibration is an implementation-session listening task (§11 Q1, DoD §13.8).

### 4.5 Validation rules (loader; each class gets a rejection fixture)

- **TB1** *(cross-file, resolves the PHASE_2 D14 deferred check)* per role, the flavor-id set in `timbres.yaml` **equals** the set declared in `interpreter.yaml` — no dangling declarations, no orphan recipes.
- **TB2** `engine.type` in the PHASE_1 instrument whitelist; `voice` + `maxPolyphony` (1–32) present iff `type == PolySynth`, `voice` in the Monophonic whitelist (PHASE_1 V7).
- **TB3** every `base` option path is in `sound/allowlist.yaml` for the patch's class (§5.2); same for every kit voice patch.
- **TB4** every insert's `type` is in the effect whitelist; its option paths in the allowlist. Bus/master entries likewise; `master` must end with a `Limiter`.
- **TB5** kits define exactly the nine voice-track ids; `midi` present iff the voice's class ≠ NoiseSynth; `midi ∈ 0–127`.
- **TB6** mix: `volumeDb ≤ 6`; `pan ∈ [−1, 1]`; every `sends` key references a declared bus (`reverb` is the only v1 bus).
- **TB7** mod: directive keys ⊆ {brightness, attackHardness, space}; entries well-formed (`curve ∈ {linear, exp}`; `exp` ⇒ `min, max > 0`); every effective mapping's `param` legal for the flavor's engine class (or `mix.sends.reverb`); after merge, base XOR mod holds per path (§3.3).
- **TB8** `bus.reverb`: `0 < decay.lo ≤ decay.hi`; `0 ≤ preDelay.lo ≤ preDelay.hi`; `returnFilterHz > 0`.
- **TB9** strict schema — unknown keys rejected (pydantic).

### 4.6 Honest-synthesis policy (D11)

The PHASE_2 flavor ids are kept verbatim (`piano`, `clean_electric`, …) — renaming would break the PHASE_2 golden fixtures for nothing. The recipes interpret them as **stylized synthesis approximations, not emulations**: `piano` is warm FM keys that read piano-ish in an ensemble; `clean_electric` is a plucky filtered PolySynth, not Karplus-Strong (PluckSynth is monophonic and barred as a PolySynth voice — PHASE_1 V7). The research is blunt that acoustic piano and strummed guitar are the two weak synthesis targets; sampled flavors remain PHASE_1 Q8 (post-v1).

### 4.7 The riser recipe (dormant — resolves the patch half of PHASE_6 Q2)

Pinned recipe, unwired in v1: a noise swell needs no automation lane — the *note's own envelope* is the riser. `{type: NoiseSynth, options: {noise: {type: "white"}, envelope: {attack: <riser length s>, decay: 0.1, sustain: 1.0, release: 0.3}, volume: -10}}` through inserts `[{type: Filter, options: {type: "highpass", frequency: 900, Q: 1}}]` with a hot reverb send, triggered as one note spanning the riser. Attack-in-seconds vs tempo, track/role convention, and placement are Phase 8's (PHASE_6 Q2 remainder).

---

## 5. Engine data

### 5.1 `sound/mod_defaults.yaml` (normative)

Loaded like `moods.yaml`/`feel.yaml`; internal, recalibratable. Reference engine classes: bass **MonoSynth**, comping **PolySynth/MonoSynth**, pads **PolySynth/MonoSynth** — the subtractive path, whose brightness lever is the filter envelope. Flavors on other classes override (§3.2). Ranges follow the research synthesis: log cutoff bands per role (register-relative brightness), log attack bands (log-attack-time), linear dB send bands; the numeric endpoints are convention anchored to well-evidenced directions.

```yaml
bass:
  brightness:
    - { param: filterEnvelope.baseFrequency, min: 120, max: 2500, curve: exp }
    - { param: filter.Q,                     min: 0.8, max: 2.0,  curve: linear }
  attackHardness:
    - { param: envelope.attack,       min: 0.12, max: 0.001, curve: exp }   # inverted: hard = fast
    - { param: filterEnvelope.octaves, min: 1.5, max: 3.5,   curve: linear }
  space: []          # bass stays dry regardless of space (mud; low-register roughness)

comping:
  brightness:
    - { param: filterEnvelope.baseFrequency, min: 400, max: 8000, curve: exp }
  attackHardness:
    - { param: envelope.attack, min: 0.08, max: 0.001, curve: exp }
  space:
    - { param: mix.sends.reverb, min: -24, max: -9, curve: linear }

pads:
  brightness:
    - { param: filterEnvelope.baseFrequency, min: 350, max: 9000, curve: exp }
  attackHardness:
    - { param: envelope.attack, min: 1.2, max: 0.005, curve: exp }
  space:
    - { param: mix.sends.reverb, min: -18, max: -6, curve: linear }

drums:               # per voice; attackHardness deliberately absent (D4)
  brightness:
    hats:  [ { param: resonance, min: 2000, max: 5500, curve: exp } ]
    ride:  [ { param: resonance, min: 3500, max: 7000, curve: exp } ]
    crash: [ { param: resonance, min: 2500, max: 5000, curve: exp } ]
    snare: [ { param: noise.playbackRate, min: 2.0, max: 4.0, curve: linear } ]
  space:
    snare:    [ { param: mix.sends.reverb, min: -18, max: -6, curve: linear } ]
    tom_low:  [ { param: mix.sends.reverb, min: -16, max: -8, curve: linear } ]
    tom_mid:  [ { param: mix.sends.reverb, min: -16, max: -8, curve: linear } ]
    tom_high: [ { param: mix.sends.reverb, min: -16, max: -8, curve: linear } ]
    crash:    [ { param: mix.sends.reverb, min: -14, max: -8, curve: linear } ]
    # kick: none (dry); hats/ride: fixed base sends in the kit mix
```

Rationale rows: `attackHardness` never touches drums — trigger envelopes *are* the kit's identity (a brush kit with a hard attack is no longer a brush kit; the flavor choice already expresses tightness — D4). Dark moods dull the cymbals and fatten the snare crack (brightness → MetalSynth `resonance`, NoiseSynth `playbackRate`), satisfying ROADMAP §4's "parameterized by mood brightness" literally.

### 5.2 `sound/allowlist.yaml` (D12 — concretizes PHASE_1 §3.6)

Engine data enumerating, per whitelisted class, the option paths the generator may emit — the single source for TB3/TB4/TB7 and the documented Tone.js-upgrade gate ("a Tone.js upgrade is a deliberate migration, not silent drift"). Seed content = exactly the paths used by §5.1, §8, and the PHASE_1 fixture, e.g.:

```yaml
MonoSynth:  [volume, oscillator.type, oscillator.count, oscillator.spread,
             envelope.attack, envelope.decay, envelope.sustain, envelope.release, envelope.attackCurve,
             filter.type, filter.Q, filter.rolloff,
             filterEnvelope.attack, filterEnvelope.decay, filterEnvelope.sustain, filterEnvelope.release,
             filterEnvelope.baseFrequency, filterEnvelope.octaves, filterEnvelope.exponent]
FMSynth:    [volume, harmonicity, modulationIndex, oscillator.type, oscillator.partials,
             envelope.*, modulation.type, modulationEnvelope.*]
MetalSynth: [volume, frequency, harmonicity, modulationIndex, resonance, octaves, envelope.attack, envelope.decay, envelope.release]
MembraneSynth: [volume, pitchDecay, octaves, oscillator.type, envelope.*]
NoiseSynth: [volume, noise.type, noise.playbackRate, envelope.*]
AMSynth:    [volume, harmonicity, oscillator.type, envelope.*, modulation.type, modulationEnvelope.*]
Synth:      [volume, oscillator.type, oscillator.partials, oscillator.count, oscillator.spread, envelope.*]
Reverb: [decay, preDelay, wet]        Chorus: [frequency, delayTime, depth, spread, wet]
Distortion: [distortion, oversample, wet]   Filter: [type, frequency, Q, rolloff]
StereoWidener: [width]   Tremolo: [frequency, depth, spread, wet]
Compressor: [threshold, ratio, attack, release]   Limiter: [threshold]
EQ3: [low, mid, high, lowFrequency, highFrequency]
Vibrato: [frequency, depth, wet]   AutoFilter: [frequency, baseFrequency, octaves, depth, wet]
```

(`envelope.*` expands to the five envelope fields + `attackCurve`; the committed file is fully expanded. Classes/paths are added by amendment as packs need them; DuoSynth/PluckSynth/other whitelisted effects enter the allowlist when first used. The Vibrato and AutoFilter rows were added by PHASE_8 §3.7, 2026-07-07 — first used by chill_lofi's tape wobble and fusion_jazz's clav wah.)

---

## 6. Routing, mix, and master

### 6.1 Routing (D2)

- **One document bus, `reverb`**, effects `[Reverb {decay, preDelay, wet: 1.0}, Filter {type: highpass, frequency: returnFilterHz, Q: 0.5}]`. Every wet path is send-controlled; the HPF'd return keeps summed low end clean (the researched convention). One convolution instance per document — the CPU idiom PHASE_1 D5 built buses for.
- **Sends** per track from the evaluated mix block: snare highest, pads high, comping medium, toms/crash moderate, hats/ride low fixed, **kick and bass none** (dry — universal practice, and it protects the low end).
- **Inserts = identity.** Chorus on EPs/pads, Distortion on crunch guitar, Tremolo on organ, StereoWidener on pads — the flavor's character, per-flavor data. (Client obligations — `.start()` on Chorus/Tremolo/AutoFilter, awaiting `Reverb.ready` — are already in PHASE_1 §3.7.)
- **Pads width**: pan 0 + `StereoWidener {width: 0.7}` insert (D8) — wide bed, strong mono-safe center (the anti-Aebersold finding).

### 6.2 Bus evaluation by `space`

`decay = round3(lo × (hi/lo)^space)` (exp — reverb-time perception is ratio-like), `preDelay = round3(lo + space × (hi − lo))`. Reference ranges: pop_rock `decay [0.8, 3.0]`, jazz `[0.7, 2.2]`, both `preDelay [0.01, 0.03]` — spanning the measured emotion-relevant band (dry/intimate → sad/dreamy/mysterious) while capped below the "long reverb reads unpleasant" zone; jazz's tighter ceiling encodes the band-in-one-room chamber norm.

### 6.3 Channel tables (normative reference values; replace PHASE_5 §8.3 stubs)

Pop/rock — kick-anchored, kit forward: kick −9/0 · snare −10.5/0 · hats −17/+0.3 · ride −19/−0.2 · crash −14/−0.35 · toms −13 at −0.3/−0.1/+0.15 · perc −16/+0.2 · bass −11/0 · comping −13/−0.3 · pads −18/0(wide). Jazz — bass upfront, ride prominent, everything softer: kick −12/0 · snare −12/0 · hats −16/+0.25 · **ride −13/−0.2** · crash −15/−0.3 · toms −14 at −0.25/−0.05/+0.15 · perc −18/+0.2 · **bass −10/0** · comping −12/−0.25 · pads −20/0(wide). (Audience perspective; kick/snare/bass always dead center; these live per flavor/voice in §8.)

### 6.4 Master chains (pack data)

- pop_rock: `Compressor {threshold: -20, ratio: 2, attack: 0.03, release: 0.25}` + `Limiter {threshold: -1}` — gentle glue, slow enough attack to pass the kick transient.
- jazz: `Compressor {threshold: -18, ratio: 1.5, attack: 0.03, release: 0.4}` + `Limiter {threshold: -1}` — barely-there glue, no pumping.
- Loudness guidance (documented, not enforced — no offline render in the pipeline): favor dynamics over loudness for a play-along; ≈ −14 LUFS pop / −16 jazz if a client ever normalizes.

### 6.5 Soloist space (invariant 4, mixing edition)

Owsinski's five-elements frame: the generated band occupies Foundation (kick/snare/bass), Pad, and Rhythm — **the Lead slot is deliberately empty** for the live player. Concretely: comping/pads levels sit ≥ 2–4 dB under the kick/snare tier; the reverb return is HPF'd; MetalSynth voices carry baked trims so cymbals never eat the top octave; register separation is already structural (lanes ≤ B4).

---

## 7. The sound-design stage

`sound_design(plan, pack) → SoundDesign`, pure (D3). Output: `{trackSounds: {trackId: {instrument, effects, channel, sends}}, buses, master}`.

```
1. d = plan.timbreDirectives
2. for each role in [drums, bass, comping, pads]:
     flavor = pack.timbres.flavors[role][plan.roleFlavors[role]]
     mod    = merge(modDefaults[role], flavor.mod)        # §3.2 per-key replacement
     drums: for each of the nine kit voices → evaluate (§3.4) → one trackSounds entry per voice
     pitched: evaluate → one trackSounds entry (trackId = role name)
     each entry: instrument = evaluated patch (PolySynth emitted as {type, voice, maxPolyphony, options});
                 effects = flavor inserts verbatim; channel = {volumeDb, pan, mute: false};
                 sends = [{bus: "reverb", gainDb}] iff the evaluated mix has one
3. buses  = [{id: "reverb", effects: [Reverb {decay, preDelay per §6.2, wet: 1.0},
                                      Filter {highpass, returnFilterHz, Q: 0.5}]}]
4. master = pack.timbres.master verbatim
```

**Serializer integration** (amends PHASE_5 §8.3): the Serializer takes `SoundDesign` and, for each track that has phrases (plus the `crash` track whenever Phase 6 emitted crash events), fills `instrument`/`effects`/`channel`/`sends` from `trackSounds`; document `buses` and `master` come from the stage output. The stub defaults are deleted. A document may therefore carry a `reverb` bus with zero senders only if no sending track exists — harmless; the Serializer omits the bus when no instantiated track sends to it (keeps V6 tight and documents minimal).

Patches are baked once per song (D6): no per-section timbre variation exists in v1 — section contrast is arrangement/intensity/energy territory (Phases 3–6), matching every product studied (variations change phrases, never voices).

---

## 8. Reference content (normative)

Both files normative as schema fixtures and golden-test data; content is reference-quality, refined in Phase 8. Entries marked `# …` are abridged — completing them per the stated conventions is an implementation-session authoring task (DoD §13.1); every value the §9 goldens depend on is stated in full. Recipes trace to shipped Tone.js sources (official examples, documented community recipes) noted inline.

### 8.1 `styles/pop_rock/timbres.yaml`

```yaml
flavors:
  drums:
    acoustic_kit:
      kit:
        kick:     { midi: 24, patch: { type: MembraneSynth, options: {
                      pitchDecay: 0.05, octaves: 4, oscillator: {type: sine},
                      envelope: {attack: 0.001, decay: 0.4, sustain: 0.01, release: 1.4, attackCurve: exponential} } },
                    mix: {volumeDb: -9, pan: 0} }                       # PHASE_1 fixture recipe
        snare:    { patch: { type: NoiseSynth, options: { volume: -4,
                      noise: {type: pink},                              # playbackRate mapped (brightness)
                      envelope: {attack: 0.001, decay: 0.13, sustain: 0, release: 0.03} } },
                    mix: {volumeDb: -10.5, pan: 0} }                    # send mapped (space)
        hats:     { midi: 80, patch: { type: MetalSynth, options: { volume: -12,
                      frequency: 250, harmonicity: 5.1, modulationIndex: 32, octaves: 1.5,
                      envelope: {attack: 0.001, decay: 0.05, release: 0.01} } },   # resonance mapped
                    mix: {volumeDb: -17, pan: 0.3, sends: {reverb: -20}} }
        ride:     { midi: 82, patch: { type: MetalSynth, options: { volume: -12,
                      frequency: 400, harmonicity: 12, modulationIndex: 16, octaves: 1,
                      envelope: {attack: 0.001, decay: 0.35, release: 0.5} } },    # resonance mapped
                    mix: {volumeDb: -19, pan: -0.2, sends: {reverb: -18}} }
        crash:    { midi: 84, patch: { type: MetalSynth, options: { volume: -12,
                      frequency: 300, harmonicity: 5.1, modulationIndex: 32, octaves: 1.5,
                      envelope: {attack: 0.001, decay: 1.5, release: 1.5} } },     # resonance mapped
                    mix: {volumeDb: -14, pan: -0.35} }                  # send mapped (space)
        tom_low:  { midi: 43, patch: { type: MembraneSynth, options: {
                      pitchDecay: 0.05, octaves: 5, oscillator: {type: sine},
                      envelope: {attack: 0.001, decay: 0.35, sustain: 0, release: 0.3} } },
                    mix: {volumeDb: -13, pan: -0.3} }                   # send mapped
        tom_mid:  { midi: 47, ... }   # as tom_low; pan -0.1
        tom_high: { midi: 50, ... }   # as tom_low; pan +0.15
        perc:     { patch: { type: NoiseSynth, options: { volume: -6,
                      noise: {type: white}, envelope: {attack: 0.001, decay: 0.05, sustain: 0, release: 0.02} } },
                    mix: {volumeDb: -16, pan: 0.2} }
    tight_kit:
      kit:        # same structure; the shiny.html kick (pitchDecay 0.02, octaves 6, square4,
        ...       # decay 0.2), snappier snare (decay 0.09), shorter hats (decay 0.03),
                  # brighter base frequencies; same midi/mix/mapped params
  bass:
    electric_fingered:                              # canonical monoSynth.html bass
      engine: { type: MonoSynth }
      base:
        oscillator: {type: square8}
        envelope: {decay: 0.3, sustain: 0.4, release: 0.8}              # attack mapped
        filter: {type: lowpass, rolloff: -12}                           # Q mapped
        filterEnvelope: {attack: 0.001, decay: 0.7, sustain: 0.1, release: 0.8}
          # baseFrequency + octaves mapped
      effects: []
      mix: {volumeDb: -11, pan: 0}                                      # no send: bass dry
    electric_picked:
      engine: { type: MonoSynth }
      base:
        oscillator: {type: sawtooth}
        envelope: {decay: 0.2, sustain: 0.35, release: 0.6}
        filter: {type: lowpass, rolloff: -12}
        filterEnvelope: {attack: 0.001, decay: 0.25, sustain: 0.2, release: 0.5}
      effects: []
      mix: {volumeDb: -11, pan: 0}
      mod:                                          # picked bite: brighter, snappier band
        brightness: [ { param: filterEnvelope.baseFrequency, min: 200, max: 3500, curve: exp },
                      { param: filter.Q, min: 0.8, max: 2.0, curve: linear } ]
        attackHardness: [ { param: envelope.attack, min: 0.04, max: 0.001, curve: exp },
                          { param: filterEnvelope.octaves, min: 1.5, max: 3.5, curve: linear } ]
  comping:
    clean_electric:
      engine: { type: PolySynth, voice: MonoSynth, maxPolyphony: 12 }
      base:
        oscillator: {type: triangle}
        envelope: {decay: 0.5, sustain: 0.3, release: 0.6}              # attack mapped
        filter: {type: lowpass, rolloff: -12, Q: 1}
        filterEnvelope: {attack: 0.002, decay: 0.4, sustain: 0.4, release: 0.6, octaves: 2.2}
          # baseFrequency mapped
      effects: [ { type: Chorus, options: {frequency: 1.5, delayTime: 3.5, depth: 0.4, wet: 0.3} } ]
      mix: {volumeDb: -13, pan: -0.3}               # reverb send mapped (space)
    crunch_electric:
      engine: { type: PolySynth, voice: MonoSynth, maxPolyphony: 12 }
      base: ...                                     # as clean_electric, sawtooth oscillator,
                                                    # envelope decay 0.4 / sustain 0.35
      effects: [ { type: Distortion, options: {distortion: 0.4, oversample: "2x", wet: 0.6} } ]
      mix: {volumeDb: -13, pan: -0.3}
    piano:                                          # stylized FM keys (§4.6)
      engine: { type: PolySynth, voice: FMSynth, maxPolyphony: 12 }
      base:
        harmonicity: 3
        oscillator: {type: sine}
        envelope: {decay: 1.2, sustain: 0.1, release: 1.2}              # attack mapped
        modulation: {type: sine}
        modulationEnvelope: {attack: 0.002, decay: 0.2, sustain: 0, release: 0.2}
      effects: []
      mix: {volumeDb: -13, pan: -0.3}
      mod:
        brightness: [ { param: modulationIndex, min: 4, max: 14, curve: exp } ]   # FM lever, not cutoff
  pads:
    warm_analog:
      engine: { type: PolySynth, voice: MonoSynth, maxPolyphony: 8 }
      base:
        oscillator: {type: fatsawtooth, count: 3, spread: 30}
        envelope: {decay: 0.6, sustain: 0.5, release: 1.6}              # attack mapped
        filter: {type: lowpass, rolloff: -12, Q: 1}
        filterEnvelope: {attack: 0.4, decay: 0.8, sustain: 0.6, release: 1.6, octaves: 2}
          # baseFrequency mapped
      effects: [ { type: Chorus, options: {frequency: 0.8, delayTime: 4, depth: 0.5, wet: 0.3} },
                 { type: StereoWidener, options: {width: 0.7} } ]
      mix: {volumeDb: -18, pan: 0}                  # reverb send mapped (space)
    airy_strings:
      engine: { type: PolySynth, voice: MonoSynth, maxPolyphony: 8 }
      base: ...                                     # fatsawtooth count 4 spread 20; envelope
                                                    # decay 0.3 / sustain 0.8 / release 2.4
      effects: [ { type: Chorus, options: {frequency: 0.6, delayTime: 5, depth: 0.7, wet: 0.4} },
                 { type: StereoWidener, options: {width: 0.7} } ]
      mix: {volumeDb: -18, pan: 0}

bus:
  reverb: { decay: [0.8, 3.0], preDelay: [0.01, 0.03], returnFilterHz: 350 }

master:
  - { type: Compressor, options: {threshold: -20, ratio: 2, attack: 0.03, release: 0.25} }
  - { type: Limiter,    options: {threshold: -1} }
```

### 8.2 `styles/jazz/timbres.yaml` (defining entries)

```yaml
flavors:
  drums:
    brush_kit:
      kit:
        kick:     { midi: 24, patch: { type: MembraneSynth, options: {
                      pitchDecay: 0.08, octaves: 3, oscillator: {type: sine},
                      envelope: {attack: 0.002, decay: 0.35, sustain: 0, release: 0.4} } },
                    mix: {volumeDb: -12, pan: 0, sends: {reverb: -18}} }   # touch of room (fixed)
        snare:    { patch: { type: NoiseSynth, options: { volume: -4,
                      noise: {type: pink},                              # playbackRate mapped (override ↓)
                      envelope: {attack: 0.02, decay: 0.25, sustain: 0.05, release: 0.3} } },
                    mix: {volumeDb: -12, pan: 0} }                      # brush swish; send mapped
        hats:     { midi: 80, patch: { ... MetalSynth, volume: -12, frequency: 220,
                      envelope: {attack: 0.001, decay: 0.06, release: 0.02} ... } },
                    mix: {volumeDb: -16, pan: 0.25, sends: {reverb: -15}} }
        ride:     { midi: 82, patch: { type: MetalSynth, options: { volume: -12,
                      frequency: 420, harmonicity: 12, modulationIndex: 14, octaves: 1,
                      envelope: {attack: 0.001, decay: 0.5, release: 0.8} } },
                    mix: {volumeDb: -13, pan: -0.2, sends: {reverb: -12}} }   # the jazz anchor: prominent
        crash:    { midi: 84, ... }   # decay 1.8; mix -15/-0.3; send mapped
        tom_low/tom_mid/tom_high:     # as pop, softer velocities live in patterns; mix -14, pans -0.25/-0.05/+0.15
        perc:     { ... }             # shaker-ish NoiseSynth; mix -18/+0.2
      mod:
        brightness:
          snare: [ { param: noise.playbackRate, min: 0.4, max: 0.9, curve: linear } ]  # brush, not crack
    ride_kit:
      kit: ...    # sticks: snare decay 0.13/attack 0.001, ride modulationIndex 16, brighter hats;
                  # same midi/mix shape
  bass:
    upright:                                        # FM pizzicato (research recipe)
      engine: { type: FMSynth }
      base:
        harmonicity: 1
        oscillator: {type: sine}
        envelope: {decay: 0.6, sustain: 0, release: 0.4}                # attack mapped (override)
        modulation: {type: sine}
        modulationEnvelope: {attack: 0.005, decay: 0.15, sustain: 0, release: 0.1}
      effects: [ { type: Filter, options: {type: lowpass, frequency: 900, Q: 0.5} } ]  # woody cap
      mix: {volumeDb: -10, pan: 0}                  # jazz: bass upfront; dry
      mod:                                          # FM engine ⇒ full override (TB7 forces this)
        brightness: [ { param: modulationIndex, min: 1.5, max: 6, curve: exp } ]
        attackHardness: [ { param: envelope.attack, min: 0.05, max: 0.002, curve: exp } ]
  comping:
    piano:                                          # warm FM keys, jazz-voiced
      engine: { type: PolySynth, voice: FMSynth, maxPolyphony: 12 }
      base:
        harmonicity: 3
        oscillator: {type: sine}
        envelope: {decay: 1.4, sustain: 0.08, release: 1.4}             # attack mapped
        modulation: {type: sine}
        modulationEnvelope: {attack: 0.002, decay: 0.25, sustain: 0, release: 0.2}
      effects: []
      mix: {volumeDb: -12, pan: -0.25}              # reverb send mapped (space)
      mod:
        brightness: [ { param: modulationIndex, min: 4, max: 14, curve: exp } ]
    guitar_hollow:
      engine: { type: PolySynth, voice: MonoSynth, maxPolyphony: 12 }
      base: ...                                     # triangle osc, mellow filter
                                                    # (filterEnvelope decay 0.5, sustain 0.3),
                                                    # envelope decay 0.7 / sustain 0.25 / release 0.8
      effects: []
      mix: {volumeDb: -12, pan: -0.25}
  pads:
    airy_strings:
      engine: { type: PolySynth, voice: MonoSynth, maxPolyphony: 8 }
      base: ...                                     # as pop airy_strings, spread 15
      effects: [ { type: Chorus, options: {frequency: 0.6, delayTime: 5, depth: 0.6, wet: 0.35} },
                 { type: StereoWidener, options: {width: 0.6} } ]
      mix: {volumeDb: -20, pan: 0}
    organ_soft:
      engine: { type: PolySynth, voice: AMSynth, maxPolyphony: 8 }
      base:
        oscillator: {type: sine}
        envelope: {decay: 0.1, sustain: 1.0, release: 0.3}              # attack mapped; organ = flat sustain
        modulation: {type: square}
        modulationEnvelope: {attack: 0.5, decay: 0, sustain: 1, release: 0.5}
      effects: [ { type: Tremolo, options: {frequency: 4.5, depth: 0.35, spread: 90, wet: 0.5} } ]
      mix: {volumeDb: -20, pan: 0}
      mod:
        brightness: [ { param: harmonicity, min: 1.0, max: 2.0, curve: linear } ]   # drawbar-mix analog

bus:
  reverb: { decay: [0.7, 2.2], preDelay: [0.01, 0.03], returnFilterHz: 400 }

master:
  - { type: Compressor, options: {threshold: -18, ratio: 1.5, attack: 0.03, release: 0.4} }
  - { type: Limiter,    options: {threshold: -1} }
```

(Jazz pads are dormant in v1 — `layersMax` 3 keeps the trio — but both declared flavor ids carry recipes: TB1 is unconditional.)

---

## 9. Worked examples (normative golden fixtures)

Both chain from PHASE_2 §6.5 (seed `1ps9wxb`). Every value below is computed from the pinned formulas; tables display 1 decimal for readability (times/sends as noted) — **the golden fixtures assert the full round3 values recomputed at implementation time**. Zero draws in both (D3).

### 9.1 Example 1 — pop_rock / happy

Directives `{brightness: 0.835, attackHardness: 0.66, space: 0.36}`; flavors acoustic_kit / electric_fingered / clean_electric / warm_analog.

| Track | Evaluated (mapped params only) | Send (gainDb) |
| --- | --- | --- |
| kick | — (no mappings) | — |
| snare | `noise.playbackRate` = 2 + 0.835×2 = **3.67** | −18 + 0.36×12 = **−13.7** |
| hats | `resonance` = 2000×2.75^0.835 ≈ **4654.5** | −20 (fixed) |
| ride | `resonance` = 3500×2^0.835 ≈ **6243.6** | −18 (fixed) |
| crash | `resonance` = 2500×2^0.835 ≈ **4459.7** | −14 + 0.36×6 = **−11.8** |
| toms | — | −16 + 0.36×8 = **−13.1** |
| bass | `filterEnvelope.baseFrequency` = 120×20.833^0.835 ≈ **1514.8 Hz**; `filter.Q` = **1.802**; `envelope.attack` = 0.12×(1/120)^0.66 ≈ **0.0051 s**; `filterEnvelope.octaves` = **2.82** | none (dry) |
| comping | `filterEnvelope.baseFrequency` = 400×20^0.835 ≈ **4880.0 Hz**; `envelope.attack` = 0.08×0.0125^0.66 ≈ **0.0044 s** | −24 + 0.36×15 = **−18.6** |
| pads | `filterEnvelope.baseFrequency` = 350×25.714^0.835 ≈ **5267.0 Hz**; `envelope.attack` = 1.2×(0.005/1.2)^0.66 ≈ **0.0322 s** | −18 + 0.36×12 = **−13.7** |

Bus: `decay` = 0.8×3.75^0.36 ≈ **1.287 s**, `preDelay` = **0.0172**, return HPF 350. Master: the §8.1 chain verbatim. Reading: a happy track gets bright open filters, snappy attacks (a 32 ms pad swell — fast for a pad, right for A = +0.4), sizzly cymbals, a tight plate-ish room. Every non-drum evaluated patch stays a patch — notes and lanes were fixed upstream; nothing here can violate the C5 ceiling.

### 9.2 Example 2 — jazz / melancholic

Directives `{brightness: 0.333, attackHardness: 0.32, space: 0.657}`; flavors brush_kit / upright / piano / airy_strings (pads never activate — no pads track exists to fill).

| Track | Evaluated (mapped params only) | Send (gainDb) |
| --- | --- | --- |
| kick | — | −18 (fixed) |
| snare | `noise.playbackRate` = 0.4 + 0.333×0.5 = **0.567** (brush override) | −18 + 0.657×12 = **−10.1** |
| hats | `resonance` = 2000×2.75^0.333 ≈ **2801.1** | −15 (fixed) |
| ride | `resonance` = 3500×2^0.333 ≈ **4408.7** | −12 (fixed) |
| crash | `resonance` = 2500×2^0.333 ≈ **3149.1** | −14 + 0.657×6 = **−10.1** |
| toms | — | −16 + 0.657×8 = **−10.7** |
| bass (upright) | `modulationIndex` = 1.5×4^0.333 ≈ **2.380**; `envelope.attack` = 0.05×0.04^0.333 ≈ **0.0171 s** | none (dry) |
| comping (piano) | `modulationIndex` = 4×3.5^0.333 ≈ **6.071**; `envelope.attack` = 0.08×0.0125^0.32 ≈ **0.0197 s** | −24 + 0.657×15 = **−14.1** |

Bus: `decay` = 0.7×3.143^0.657 ≈ **1.485 s**, `preDelay` = **0.0231**, return HPF 400. Master: §8.2 chain. Reading: dulled cymbals, a soft brush snare (playbackRate 0.57 vs pop's 3.67 — the override doing its job), a woody low-index upright, warm dark FM keys, and a chamber-sized room with generous sends — the melancholic quartet sounds like it plays in one room. The document's `reverb` bus, sends, and per-track channels replace every PHASE_5 stub value; V1–V8 still hold (this stage adds no notes).

---

## 10. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Modulation layer: engine per-role default mapping tables + per-flavor overrides** (per-directive-key replacement) | The moods.yaml anchor+overrides pattern applied to timbre; defaults keep 5 packs coherent and authoring cheap; overrides cover engine-class differences (FM brightness = modulationIndex) and character re-ranges (brush snare); per-patch mappings are the Logic/Ableton norm | Fully pack-authored mappings (5 packs × ~12 flavors of restated boilerplate; coherence by discipline only); engine-only modulation (FM vs subtractive forces per-class special cases into the engine anyway; packs couldn't voice mood response) |
| D2 | **One shared `reverb` bus + per-flavor identity inserts; kick/bass dry** | GM/Logic architecture (shared engines, per-part sends); one convolution instance (the PHASE_1 D5 idiom); shared chorus is musically wrong (rate/depth is per-instrument character); HPF'd return keeps summed low end clean | Reverb+chorus buses (forces one chorus character on all senders); inserts-only (8–10 convolution engines; "one room" coherence by accident) |
| D3 | **Zero draws; `sound` stream reserved** | No product randomizes timbre — a flavor is a curated identity, directives already move character, "reroll the sound" has no musical meaning like "reroll the drums"; tightest goldens; append-only discipline makes adding a draw later safe | Seeded color draws now (marginal audible gain, no precedent, new golden surface) |
| D4 | **Drums modulated by brightness + space only; attackHardness exempt** | Trigger envelopes are the kit's identity — modulating them converges acoustic_kit on tight_kit and un-jazzes the brush kit, duplicating the flavor choice; brightness → cymbal `resonance` / snare noise color satisfies ROADMAP's "parameterized by mood brightness" literally; space → sends like every role | All three directives (blurs flavor boundaries); none (leaves the roadmap bullet unimplemented; dark ballads get sizzly hats) |
| D5 | **Mapping semantics: absolute `{param, min, max, curve: linear\|exp}`; inverted ranges legal; base XOR mod per path; round3** | The Ableton/Serum range model — bounded by construction, no runtime state; exp for frequencies/times (log perception: log-attack-time, log-frequency axes); XOR kills value-precedence ambiguity at the schema level | Relative/multiplicative modulation (base×factor — no product precedent, compounds unpredictably); free curves/remap graphs (Vital/Logic power without v1 need); base-as-midpoint semantics (two authorities for one value) |
| D6 | **Patches baked once per song; no per-section timbre** | Directives are song-level; every product studied varies sections by phrases/layers, never voices; per-song baking keeps this stage a pure lookup+evaluate and the document minimal | Per-section patch evaluation (nothing varies per section in v1 inputs; would multiply tracks or require runtime automation the schema lacks) |
| D7 | **Two-layer gain: `options.volume` = class gain-staging trim (MetalSynth −12, NoiseSynth −4); `channel.volumeDb` = musical balance from the researched tables** | MetalSynth/NoiseSynth are intrinsically hot — normalizing at the patch makes channel values read as the mix table they came from; both layers are pack data, calibrated by ear at implementation (Q1) | Single-layer channel-only (channel values become class-hotness-entangled and untransferable across kits); engine-hardcoded trims (recalibration = code change) |
| D8 | **Pads: pan 0 + StereoWidener 0.7 insert; moderate pans elsewhere; kick/snare/bass dead center** | Wide bed with a strong mono-safe center; the researched anti-Aebersold finding (hard L/R splits distract and collapse in mono); audience-perspective pan table | Hard-panned comping/pads (full-production move, wrong for a play-along); pads as point-panned mono (loses the bed function) |
| D9 | **Master chain = pack data: gentle Compressor + Limiter −1 (pop 2:1/−20; jazz 1.5:1/−18)** | Researched glue conventions (2:1/30 ms/2–3 dB GR pop; barely-there jazz, no pumping); pack data because compression character is style identity | Engine-fixed master (jazz pumping like pop); no master chain (PHASE_1 fixture already ships one; naked sums clip) |
| D10 | **Bus decay/preDelay = pack ranges evaluated by `space` (exp/linear)** | Mo/Wu/Horner co-varied RT and wet — space legitimately drives both sends and room size; pack ranges encode style (plate-ish pop vs chamber jazz) capped below the "long reverb = unpleasant" zone | Fixed per-pack decay (space only moves sends — halves the measured effect); global engine range (jazz and pop share a room) |
| D11 | **PHASE_2 flavor ids kept verbatim; recipes are stylized approximations, not emulations** | Renaming breaks PHASE_2 golden fixtures (`roleFlavors` in worked examples) for zero user value; research is honest that piano/guitar are weak synthesis targets — the recipes aim for ensemble-believable, not soloed-realistic | Synthesis-honest renames (`ep_classic` etc. — fixture churn, PHASE_2 amendment, same sounds); dropping weak flavors (shrinks the user surface Phase 2 validated) |
| D12 | **`sound/allowlist.yaml` = the PHASE_1 §3.6 (class, option-path) allowlist, as engine data; validates base patches, inserts, bus/master, and mod targets** | One source of truth for "what may the generator emit"; makes the Tone.js-upgrade gate auditable; TB7's engine-class check rides on it for free | Allowlist in code (recalibration/extension = code change); no allowlist (silent Tone option drift — exactly what PHASE_1 D12 warned against) |
| D13 | **Kits define all nine voice tracks with per-voice `{midi, patch, mix}`; trigger midi pinned (kick 24, toms 43/47/50, hats 80, ride 82, crash 84; NoiseSynth voices unpitched)** | Phase 6 adds crash at runtime and Phase 8 packs will use more voices — complete kits cost lines, not risk; midi values follow the C1-kick / MetalSynth-frequency-is-the-pitch conventions and formalize the PHASE_5 stub | Kits covering only pattern-used voices (crash/perc gaps surface at runtime); midi in engine data (it's timbre-coupled — the kit owns it) |
| D14 | **Riser recipe pinned (NoiseSynth swell, envelope-as-automation) but dormant** | Resolves PHASE_6 Q2's patch half with zero schema cost — the note's own envelope does the sweep, no automation lane needed; wiring is Phase 8's | Full riser implementation (device placement is pack opt-in territory); leaving Q2 untouched (Phase 8 would design a patch mid-authoring) |

---

## 11. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | Final loudness calibration: the D7 class trims and channel tables are research-derived but unheard — do the summed reference tracks balance? (PHASE_8 §8.4, 2026-07-07: named listening task **T1**, run per pack via the calibration report) | Phase 7/8 implementation (listening checklist, DoD §13.8) | ears on the milestone documents |
| Q2 | Keytrack emulation (per-note cutoff scaling) for wide-lane comping — is lane-tuned filtering enough? | Post-v1 | listening evidence of dull-highs/harsh-lows across the comping lane |
| Q3 | Riser wiring: track/role convention, placement rules, pack opt-in (PHASE_6 Q2 remainder; recipe pinned §4.7) (PHASE_8 §3.8, 2026-07-07: **no v1 pack opts in** — stays dormant post-v1) | Post-v1 | transitions.yaml extension + arrangement of the riser track |
| Q4 | ~~Per-pack `mod_defaults` overrides?~~ **Resolved** — not needed: per-flavor `mod` overrides cover every new engine-class and character case across all five packs (PHASE_8 §3.8, 2026-07-07) | ~~Phase 8~~ | — |
| Q5 | StereoWidener 0.7 on pads vs strict mono compatibility | Post-v1 listening | mono-fold checks on real devices |
| Q6 | LUFS normalization / offline loudness measurement | Post-v1 | whether clients need normalized output (targets documented §6.4) |
| Q7 | Acoustic-piano quality: does the FM-keys `piano` read acceptably in-ensemble, or does it push PHASE_1 Q8 (Sampler) forward? (PHASE_8 §8.4, 2026-07-07: named listening task **T2**) | Phase 8 listening | pack authoring across 5 styles |
| Q8 | Exact Tone.js minor pin (PHASE_1 Q9) — unchanged, implementation session | Phase 1/7 implementation | current stable at build time |

---

## 12. Amendments to earlier documents (this session)

All additive; applied in the same commit as this document:

1. **PHASE_1 §7 Q4**: `timbres.yaml` schema marked resolved (PHASE_7 §4) — Q4 now fully closed.
2. **PHASE_1 §3.6**: the "maintained server-side allowlist of (class, option-path) pairs" annotated as pinned by PHASE_7 §5.2 (`sound/allowlist.yaml`, D12).
3. **PHASE_2 §7.3**: consumption annotations — `brightness` → per-role tone-color mappings, `attackHardness` → envelope attack (drums exempt), `space` → reverb sends + bus decay/preDelay (PHASE_7 §5.1/§6.2); no fields added to the slot.
4. **PHASE_5 §8.3/§8.4**: Serializer stub channel/mix/master defaults and the stub `timbres.yaml` replaced by the sound-design stage output and the PHASE_7 §4 schema; the §8.4 trigger-midi stub values formalized (crash 84 added) by PHASE_7 §4.3/D13.
5. **PHASE_6 §9 Q2**: partially resolved — riser patch recipe pinned (PHASE_7 §4.7); placement/pack opt-in remains Phase 8.
6. **ROADMAP §2 decisions log**: row added for the Phase 7 sound-design model.

---

## 13. Definition of done

Phase 7 is **built** when an implementation session demonstrates:

1. **Loader**: `timbres.yaml` parsing into frozen pydantic models; TB1–TB9 implemented with one rejection fixture per rule class; both reference files (fully enumerated versions of §8, including the abridged entries) load clean; TB1 runs against the PHASE_2 reference `interpreter.yaml` files.
2. **Engine data**: `sound/mod_defaults.yaml` matching §5.1 exactly and `sound/allowlist.yaml` (fully expanded) committed; validator caps (`exp` positivity, directive keys, path legality) enforced with rejection fixtures.
3. **Evaluation**: unit tests for both curves (endpoints, midpoint, inverted ranges), round3 half-even, per-key merge replacement (including empty-list disable and per-voice drum keys), base-XOR-mod rejection, and the fixed directive evaluation order.
4. **Stage goldens**: both §9 worked examples asserted **field-for-field** — every evaluated patch (full options objects, not just mapped params), every channel/send value, the bus (decay/preDelay/HPF), and the master chain, against full-precision recomputation of the §9 formulas.
5. **Determinism**: repeated-run identity; a counting-RNG shim asserting **zero draws** on the `sound` stream for both examples.
6. **Property tests**: every pack × supported mood × every declared flavor combination → output where every patch validates against the PHASE_1 §3.6 whitelists + allowlist paths, PolySynth carries voice/maxPolyphony (V7), every send references the `reverb` bus, `volumeDb ≤ 6`, `pan ∈ [−1, 1]`, bus decay within the pack range, master ends in a Limiter.
7. **Serializer integration**: PHASE_5's stub sound/channel/master defaults deleted; both worked examples regenerate end-to-end (Phases 2–7 real) into `TrackDocument`s passing V1–V8, with the jazz document carrying kit sends + chamber bus and the pop document the plate-ish bus; documents committed as updated golden fixtures.
8. **Listening checklist** (manual, both milestone documents in the Phase 1 playground): all tracks audible at sane relative levels (Q1 calibration pass — adjust pack data, not code); kick/snare/bass centered, cymbals off-center, pads wide but mono-safe; reverb audible on snare/comping/pads, kick/bass dry; **A/B the same pack across two moods** (pop happy vs pop melancholic-adjacent, e.g. `calm`): cymbals audibly duller, attacks softer, room larger on the low-arousal track; jazz reads as one room, ride prominent; nothing above the soloist — comping/pads never mask the register above C5; master never clips at full ensemble.
9. **Amendments** (§12) applied and consistent.

---

## 14. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §4/§8: flavors, kits, mappings, bus ranges, master chains — all YAML; engine owns evaluation + defaults as data files (`mod_defaults.yaml`, `allowlist.yaml`), the PHASE_5 D15 lineage |
| 2. Rhythm stored separately from pitch | Untouched — this stage emits no notes; patches/sends/levels are orthogonal to all note content |
| 3. Hierarchical seeds | §3.4/D3: the `sound` stream is reserved, never consumed; rerolling any other stream cannot change patches (pure function of plan + pack) |
| 4. Soloist owns above ~C5 | §6.5: level/register discipline (comping/pads under the rhythm tier, HPF'd return, cymbal trims); no field this stage emits can move a note — lanes and V4 hold structurally |
| 5. Deterministic pipeline | Zero draws; fixed evaluation order; round3 half-even on every evaluated value; pure function of `(plan, pack)`; entropy enters nowhere |
