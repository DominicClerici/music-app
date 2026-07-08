# PHASE_2 — Parameter & Mood Model

Designed 2026-07-06 (session 2). Status: **awaiting approval**.

This document pins the public parameter surface (`params`, resolving PHASE_1 open question Q1), the mood model (a 12-word vocabulary over a valence/arousal space with per-mood overrides), the style × mood interaction model, and the Interpreter — pipeline stage 1, which turns validated params into a complete `GenerationPlan`. It fills the three `GenerationPlan` extension points PHASE_1 assigned to this phase (`moodVector`, `budgets`, `timbreDirectives`) at field level.

Research base (session 2): the Gabrielsson & Lindström cue tables and the Eerola/Friberg/Bresin factorial studies (cue → emotion mappings, linearity); ANEW/Warriner affective norms with music-domain corrections (Saari & Eerola, Gracenote's mood wheel); numeric mappings from published generation systems (KTH Director Musices, Wallis et al., TransProse, MetaCompose, Ehrlich 2019, AffectMachine-Classical/Pop); Friberg & Sundström's swing measurements; and the parameter surfaces of Band-in-a-Box, Yamaha styles, iReal Pro, JJazzLab, MMA, Soundraw, AIVA, Mubert, Beatoven, and Ecrett.

---

## 1. Scope

**In scope**

- The `params` schema, complete and field-level — the public API surface, echoed as `meta.params`.
- Validation rules and the structured validation-error catalog.
- The mood taxonomy: 12 mood words, their valence/arousal anchors, and the anchor + formulas + overrides architecture.
- The mood → parameter formula set (tempo, density, dissonance, dynamics, articulation, layers, harmonic rhythm, register bias, timbre) with concrete equations and constants.
- The style × mood interaction model and the pack-side data that drives it: a new pack file `interpreter.yaml` (supported moods, mode menu, tonic pools, feel, expression ranges, flavors, ensembles).
- The Interpreter algorithm: resolution order, its single seeded draw, determinism rules, and two normative worked examples.
- Field-level definitions of `GenerationPlan.moodVector`, `.budgets`, `.timbreDirectives`.
- Amendments to PHASE_1 (all additive, listed in §10): `interpreter` seed stream, `interpreter.yaml` in the pack layout.

**Explicitly not in scope**

- Everything downstream of `GenerationPlan`: form templates (Phase 3), progression pools and all harmony *content* (Phase 4), pattern selection (Phase 5), humanization (Phase 6), concrete Tone.js patches (Phase 7 — this phase emits *directives*, Phase 7 turns them into patches).
- Style-pack *content* beyond the two reference `interpreter.yaml` examples (Phase 8).
- Per-section energy and mood-per-section (Phase 3 owns section energy; a user-facing per-section control is deliberately deferred — see §9).
- The browser player and any client UI (mood pickers, etc. — only the API values matter here).

---

## 2. Contracts consumed

| Upstream contract | What this phase does with it |
| --- | --- |
| `GenerationPlan` pinned core (PHASE_1 §4.1) | Produces every pinned field; defines the three extension points it owns. Field shapes are consumed as-is — nothing is reshaped. |
| Seed system (PHASE_1 §5) | `params.seed` / `params.seedText` / `params.seedOverrides` follow §5.1/§5.4 exactly; the Interpreter's RNG comes from `stream_seed(master, overrides, "interpreter")`. |
| Pack `manifest.yaml` (PHASE_1 §6.1) | `tempoRange` is the hard tempo validation bound; `timeSignatures[0]` becomes `GenerationPlan.timeSignature`. |
| Mode vocabulary (PHASE_1 §4.1) | Starter set `major, minor, dorian, mixolydian` extended (as PHASE_1 permits) with `phrygian`. `lydian` deliberately excluded in v1 (§8 D8). |
| Determinism rules (PHASE_1 §5.3) | The tempo draw uses integer `randrange` only; all candidate orderings come from explicitly ordered YAML lists, never dict/set iteration. |

---

## 3. The `params` schema

The complete input surface. All fields except `styleFamily` are optional — `generate({styleFamily: "pop_rock"})` is a valid call that resolves everything else from the pack and its default mood.

| Field | Type | Default | Constraints |
| --- | --- | --- | --- |
| `styleFamily` | str | — (required) | must match a registered pack id (`pop_rock`, `chill_lofi`, `blues`, `jazz`, `fusion_jazz`) |
| `mood` | str | pack's `defaultMood` | one of the 12 words in §4.1 AND in the pack's `supportedMoods` |
| `tempoBpm` | int | auto (§6.2 draw) | within pack `tempoRange` (hard bound; user value wins over the mood range — an explicit 170 BPM sad track is allowed if the pack permits 170) |
| `key` | `{tonic?: str, mode?: str}` | auto | `tonic`: note name `A`–`G` with optional `#`/`b` (normalized to pitch class); `mode`: must be in the pack's `modes` menu. Either subfield may be given alone; the other resolves per §6.3 |
| `roleFlavors` | `{role: flavorId}` | `{}` | keys from the role enum (`drums, bass, comping, pads`); each value must be a flavor id the pack declares for that role |
| `ensemblePreset` | str | `"default"` | must be an ensemble id the pack declares. Merge order: pack `default` preset → named preset → `roleFlavors` entries (most specific wins) |
| `maxLengthSec` | int | 180 | `30 ≤ maxLengthSec ≤ 600` |
| `seed` | str | fresh (os.urandom at API boundary) | canonical base36 u64 (PHASE_1 §5.1); mutually exclusive with `seedText` |
| `seedText` | str | — | any non-empty string, SHA-256-hashed per PHASE_1 §5.1 |
| `seedOverrides` | `{streamName: base36 str}` | `{}` | keys must be registry stream names (now including `interpreter`); values base36 u64 |
| `title` | str | absent | ≤ 120 chars; echoed to `meta.title` |

Example — the maximal call:

```jsonc
{
  "styleFamily": "jazz",
  "mood": "melancholic",
  "tempoBpm": 72,                      // omit for auto
  "key": { "tonic": "D", "mode": "minor" },  // omit for auto
  "ensemblePreset": "default",
  "roleFlavors": { "comping": "guitar_hollow" },
  "maxLengthSec": 240,
  "seed": "1ps9wxb",
  "seedOverrides": {},
  "title": "Late set"
}
```

`meta.params` echoes the **user's input verbatim** (PHASE_1 §3.2) — defaults are *not* baked in. Regeneration identity is `(params, seed, seedOverrides, generatorVersion)`; resolution behavior (default mood, tempo draw, tonic pick) is pinned by `generatorVersion` plus the pack version recorded in `GenerationPlan.stylePack`.

### 3.1 Validation-error catalog

Validation runs before any generation; failures return the full list of errors (not first-failure). Each error: `{code, field, message}` with stable codes:

| Code | Condition |
| --- | --- |
| `STYLE_UNKNOWN` | `styleFamily` matches no registered pack |
| `MOOD_UNKNOWN` | `mood` is not one of the 12 vocabulary words |
| `MOOD_UNSUPPORTED` | `mood` is valid but absent from the pack's `supportedMoods`; message lists the supported set |
| `TEMPO_OUT_OF_RANGE` | `tempoBpm` outside pack `tempoRange`; message includes the range |
| `KEY_TONIC_INVALID` | unparsable tonic name |
| `MODE_UNSUPPORTED` | `key.mode` not in the pack's `modes` menu; message lists the menu |
| `ROLE_UNKNOWN` | `roleFlavors` key outside the role enum |
| `FLAVOR_UNKNOWN` | flavor id not declared by the pack for that role |
| `PRESET_UNKNOWN` | `ensemblePreset` not declared by the pack |
| `LENGTH_OUT_OF_RANGE` | `maxLengthSec` outside [30, 600] |
| `SEED_CONFLICT` | both `seed` and `seedText` given |
| `SEED_INVALID` | `seed` not valid base36 u64 |
| `STREAM_UNKNOWN` | `seedOverrides` key not in the stream registry |
| `TITLE_TOO_LONG` | `title` > 120 chars |

---

## 4. The mood model

Architecture (decided this session, §8 D1): **anchor + formulas + overrides**. A mood is a data row — a (valence, arousal) anchor plus optional hand-authored overrides — and a shared set of continuous formulas turns any anchor into parameter defaults. Formulas keep the 12 moods coherent and make new moods cheap; overrides encode the music-domain corrections the research documents formulas getting wrong (romantic ≠ bright, aggressive ≠ dull, tense ≠ loud).

Coordinates live in `src/trackgen/interpreter/moods.yaml` (engine-owned data, loaded and validated like a pack) and are **internal implementation detail** — the public API accepts mood words only (D6), so anchors can be recalibrated without breaking any client.

### 4.1 The 12-mood vocabulary and anchors

Selection criteria (from the taxonomy research): tile all four V/A quadrants; be dense in the low-arousal half (the most-used mood tags in the wild — chill, mellow, relaxing, dark, melancholy — are all low-arousal); include the words GEMS says pure circumplex misses (nostalgic, triumphant); include both a fear-side and an anger-side word in the −V/+A corner, disambiguated by overrides, not a third dimension.

Anchors are ANEW/Warriner word norms **hand-corrected against music-domain sources** (Saari & Eerola's music-tag plot, the Gracenote wheel). V, A ∈ [−1, +1].

| Mood | V | A | Anchor rationale (word norm → music correction) |
| --- | --- | --- | --- |
| `happy` | +0.75 | +0.40 | ANEW happy (+0.80, +0.37), essentially uncorrected |
| `energetic` | +0.45 | +0.80 | arousal-dominant; ANEW excitement/thrill corner |
| `triumphant` | +0.80 | +0.55 | ANEW triumphant valence +0.96 tempered; GEMS "power" |
| `calm` | +0.55 | −0.65 | ANEW relaxed (+0.50, −0.65) |
| `dreamy` | +0.35 | −0.45 | Warriner dream (+0.43, −0.12), arousal lowered per music-tag placement |
| `romantic` | +0.65 | −0.25 | ANEW arousal +0.65 is a documented word-norm artifact; romantic *music* is low-arousal (Gracenote places Romantic near the calm side) |
| `nostalgic` | +0.30 | −0.35 | mildly positive, low arousal (Saari & Eerola: sentimental arousal ≈ −0.7); mid-plane word reached via mixed cues |
| `melancholic` | −0.50 | −0.45 | ANEW dreary (−0.49, −0.51); sad-but-soft, distinct from `dark` |
| `dark` | −0.55 | −0.15 | Saari & Eerola: dark ↔ valence r = −.94, arousal near neutral |
| `mysterious` | −0.20 | −0.30 | music-tag space puts mysterious/haunting at mildly negative valence, low arousal |
| `tense` | −0.45 | +0.50 | ANEW tense (−0.36, +0.38) deepened; the fear-side recipe (soft, variable) lives in overrides |
| `aggressive` | −0.60 | +0.70 | ANEW valence +0.03 is a word-norm artifact; aggressive *music* rates ≈ −0.6 valence (Saari: angry V −.69, A +.63) |

Geometry note: tension is not stored — it is the derived diagonal `tension ≈ (A − V)/√2` (Thayer's rotation), available to any stage that wants it. The anger/fear corner is disambiguated by cue recipes in overrides (aggressive → loud+bright+hard; tense → soft+wide dynamics), per the dominance-dimension research.

### 4.2 The formulas

All formulas are linear or piecewise in (V, A) — the factorial studies found cue effects combine linearly with no significant interactions, so nothing fancier is warranted. `clamp01(x) = min(1, max(0, x))`. Every derived float is rounded to 3 decimals (Python `round`, half-even) before entering the plan; tempo is an integer.

| Derived value | Formula | Research basis |
| --- | --- | --- |
| `tempoCenter` (BPM) | `100 × 2^(0.6 × A)` | log-in-arousal (AffectMachine-Pop); spans ≈ 66–152 over A ∈ [−1, 1], inside the happy 130–180 / sad 40–70 anchor evidence once overrides apply |
| tempo range | `[round(0.9 × c), round(1.1 × c)] ∩ pack.tempoRange` (if empty: clamp c into pack range, ±0) | style bounds are hard (BIAB/Yamaha convention) |
| `noteDensityNorm` | `clamp01(0.55 + 0.35 × A)` | density ← arousal, linear (Ehrlich p(onset)=A; TransProse bins) |
| `dissonanceNorm` | `clamp01(0.40 − 0.30 × V + 0.15 × max(0, A))` | dissonance ← −valence (MetaCompose ladder, Wallis extensions), small +arousal term (Farbood tension) |
| `dynamicsBase` | `clamp01(0.55 + 0.25 × A)` | loudness ← arousal, monotonic (strongest continuous-response arousal cue) |
| `dynamicsRange` | `clamp01(0.15 + 0.15 × |A|)` | expressive width grows away from neutral |
| `articulationLegato` | `clamp01(0.5 − 0.4 × A)` | staccato ← high arousal, legato ← low (KTH rule sets); 0 = staccato, 1 = legato |
| `layersMax` | `A ≤ −0.7 → 2; A ≤ 0.3 → 3; else 4` | layer count ← arousal (AffectMachine gating thresholds, Wallis chord size) |
| `harmonicRhythmBase` (chords/bar) | `A < −0.4 → 0.5; else 1.0` | **designer's choice** — no published system modulates chord rate by emotion (documented literature gap); Farbood-consistent. Phase 4 consumes as a baseline hint |
| `registerBias` | `0.25 × V` | register's valence effect is real but weak/ambiguous — deliberately small; Phase 5 applies it *within* ArrangementPlan lanes |
| `brightness` | `clamp01(0.55 + 0.30 × V + 0.15 × A)` | brightness ← valence (+arousal) (MetaCompose, Moody's synth banks) |
| `attackHardness` | `clamp01(0.5 + 0.4 × A)` | attack/velocity hardness ← arousal (Williams' velocity split, AffectMachine) |
| `space` (reverb/air) | `clamp01(0.5 − 0.35 × A)` | slower/calmer → more space; consumed by Phase 7 |

Two of these pass through **pack expression ranges** (§5.1) before landing in the plan — density and dissonance are style-relative (jazz's floor dissonance exceeds pop's ceiling):

```
budgets.noteDensity = pack.density.lo + noteDensityNorm × (pack.density.hi − pack.density.lo)
budgets.dissonance  = pack.dissonance.lo + dissonanceNorm × (pack.dissonance.hi − pack.dissonance.lo)
```

All other derived values are global (not pack-scaled).

**Swing is deliberately absent from this table.** The microtiming research is unambiguous: swing ratio is a function of style feel and tempo, not emotion (the swung short note sits near-constant ≈ 100 ms across tempi; exaggerating microtiming to signal energy degrades groove). Swing resolution is §6.4.

### 4.3 Overrides

An override replaces a derived value **after the formula, before pack expression-range mapping** (so overrides are in normalized space and packs still constrain). Overridable keys: exactly the 13 derived values of §4.2. The v1 override table — each row is a research-documented formula failure, not taste:

| Mood | Overrides | Why |
| --- | --- | --- |
| `melancholic` | `tempoCenter: 68` | formula gives 83; sad-music evidence clusters 40–70 BPM (Vieillard 46; TransProse floor 42) |
| `dark` | `tempoCenter: 80` | brooding drags below its near-neutral arousal's formula value (94) |
| `aggressive` | `tempoCenter: 146`, `brightness: 0.75`, `dynamicsBase: 0.80` | anger = fast + loud + **harsh-bright** timbre; the brightness formula's valence term wrongly darkens it (the exact case the override mechanism exists for) |
| `tense` | `dynamicsBase: 0.45`, `dynamicsRange: 0.35` | the fear-side recipe: **soft but variable** dynamics (Juslin's fear profile), unlike aggressive's sustained loud |
| `romantic` | `brightness: 0.45` | warm, not bright — positive valence must not brighten the timbre here |
| `calm` | `brightness: 0.45` | "peaceful" is the quadrant where soft timbre does the most work (Eerola 2013: timbre sr² .13 for peaceful vs .01 median) |
| `dreamy` | `space: 0.85` | washed reverb is the genre-defining cue; formula gives 0.657 |

### 4.4 Derived defaults for all 12 moods (after overrides, before pack ranges)

Normative reference table — implementation must reproduce these exactly (3-decimal rounding; tempoCenter pre-round shown to 1 decimal):

| Mood | tmpC | densN | dissN | dynB | dynR | artic | layers | hRhy | regB | bright | attack | space |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| happy | 118.1 | 0.690 | 0.235 | 0.650 | 0.210 | 0.340 | 4 | 1.0 | +0.188 | 0.835 | 0.660 | 0.360 |
| energetic | 139.5 | 0.830 | 0.385 | 0.750 | 0.270 | 0.180 | 4 | 1.0 | +0.113 | 0.805 | 0.820 | 0.220 |
| triumphant | 125.7 | 0.743 | 0.243 | 0.688 | 0.232 | 0.280 | 4 | 1.0 | +0.200 | 0.873 | 0.720 | 0.307 |
| calm | 76.3 | 0.323 | 0.235 | 0.388 | 0.247 | 0.760 | 3 | 0.5 | +0.138 | **0.450** | 0.240 | 0.728 |
| dreamy | 82.9 | 0.393 | 0.295 | 0.438 | 0.217 | 0.680 | 3 | 0.5 | +0.087 | 0.588 | 0.320 | **0.850** |
| romantic | 90.1 | 0.463 | 0.205 | 0.488 | 0.188 | 0.600 | 3 | 1.0 | +0.163 | **0.450** | 0.400 | 0.588 |
| nostalgic | 86.5 | 0.428 | 0.310 | 0.463 | 0.202 | 0.640 | 3 | 1.0 | +0.075 | 0.588 | 0.360 | 0.622 |
| melancholic | **68.0** | 0.393 | 0.550 | 0.438 | 0.217 | 0.680 | 3 | 0.5 | −0.125 | 0.333 | 0.320 | 0.657 |
| dark | **80.0** | 0.498 | 0.565 | 0.513 | 0.172 | 0.560 | 3 | 1.0 | −0.138 | 0.362 | 0.440 | 0.552 |
| mysterious | 88.3 | 0.445 | 0.460 | 0.475 | 0.195 | 0.620 | 3 | 1.0 | −0.050 | 0.445 | 0.380 | 0.605 |
| tense | 123.1 | 0.725 | 0.610 | **0.450** | **0.350** | 0.300 | 4 | 1.0 | −0.113 | 0.490 | 0.700 | 0.325 |
| aggressive | **146.0** | 0.795 | 0.685 | **0.800** | 0.255 | 0.220 | 4 | 1.0 | −0.150 | **0.750** | 0.780 | 0.255 |

(Bold = overridden. `layersMax` never hits 2 in v1 — no anchor has A ≤ −0.7; the rung exists for future moods.)

---

## 5. Style × mood: pack-side data

Decision (D3): **each pack declares its supported moods**; unsupported combos are a `MOOD_UNSUPPORTED` validation error naming the supported set. No silent clamping, no nearest-mood fallback — the API never emits a track the pack can't make believable, and a client can build any softer UX from the declared lists.

### 5.1 `interpreter.yaml` (new pack file, schema owned by this phase)

Added to the PHASE_1 §6 pack layout alongside `progressions.yaml`/`forms.yaml`/`timbres.yaml` (amendment, §10). Full schema by example:

```yaml
# styles/pop_rock/interpreter.yaml
supportedMoods: [happy, energetic, triumphant, calm, dreamy, romantic,
                 nostalgic, melancholic, dark, tense, aggressive]   # no 'mysterious'
defaultMood: happy

modes: [major, minor]          # ordered subset of the engine mode ladder (§6.3)
tonics:                        # per-mode preference order, note names; first = auto pick
  major: [E, A, G, C, D]       # guitar-idiomatic keys
  minor: [A, E, B, D]

feel: straight8                # straight8 | straight16 | swing8 | swing16
# swingRatio: 0.60             # optional override of the tempo-derived ratio (§6.4)
# feelTable: laidback          # optional named humanizer feel profile (added by PHASE_8 §3.4,
                               #   2026-07-07); absent → swing-derived default (PHASE_6 §5.3)

expressionRanges:              # style-relative floors/ceilings for the two pack-scaled budgets
  density:    [0.20, 0.85]
  dissonance: [0.05, 0.40]

flavors:                       # vocabulary only; timbres.yaml (Phase 7) maps ids → patches
  drums:   [acoustic_kit, tight_kit]
  bass:    [electric_fingered, electric_picked]
  comping: [clean_electric, crunch_electric, piano]
  pads:    [warm_analog, airy_strings]

ensembles:
  default: { drums: acoustic_kit, bass: electric_fingered,
             comping: clean_electric, pads: warm_analog }
  driven:  { drums: tight_kit, bass: electric_picked,
             comping: crunch_electric, pads: airy_strings }
```

```yaml
# styles/jazz/interpreter.yaml
supportedMoods: [happy, energetic, calm, dreamy, romantic, nostalgic,
                 melancholic, dark, mysterious, tense]   # no 'triumphant', no 'aggressive'
defaultMood: nostalgic

modes: [major, mixolydian, dorian, minor]
tonics:
  major:      [Bb, F, Eb, C]   # flat keys — horn-idiomatic
  mixolydian: [Bb, F]
  dorian:     [D, G, C]
  minor:      [D, G, C]

feel: swing8

expressionRanges:
  density:    [0.25, 0.90]
  dissonance: [0.35, 0.90]     # jazz's floor is pop's ceiling — this is why ranges are pack data

flavors:
  drums:   [brush_kit, ride_kit]
  bass:    [upright]
  comping: [piano, guitar_hollow]
  pads:    [airy_strings, organ_soft]

ensembles:
  default: { drums: brush_kit, bass: upright, comping: piano, pads: airy_strings }
```

Rules:

- `supportedMoods` non-empty, ⊆ the 12-word vocabulary; `defaultMood ∈ supportedMoods`.
- `modes` non-empty, ordered subset of the engine ladder; every mode listed must have a non-empty `tonics` entry.
- `expressionRanges` values in [0, 1], `lo ≤ hi`.
- Every role must appear in `flavors` with ≥ 1 id; `ensembles.default` is required and must cover all four roles; every ensemble value must be a declared flavor id.
- Flavor/ensemble ids here are *vocabulary* — validation surface for `params`. Phase 7's `timbres.yaml` must provide a patch recipe for every declared flavor id (a pack with a dangling flavor id fails pack validation once Phase 7's loader lands).
- `feelTable` (optional; added by PHASE_8 §3.4, 2026-07-07): must name an engine feel profile from the PHASE_6 §5.3 menu; absent → the swing-derived default.
- These two files are normative as schema; their *content* is reference-quality, refined during Phase 8 authoring.

The mood lists above encode the interaction model's intent: pop/rock drops only `mysterious`; jazz drops `triumphant`/`aggressive`; expect chill/lo-fi to drop `aggressive`/`triumphant`/`tense`, blues to drop `triumphant`/`dreamy`, fusion to sit near jazz. Final lists are Phase 8 authoring decisions per pack. (Decided 2026-07-07, PHASE_8 §4–§6/D8: chill_lofi also drops `energetic`; blues also drops `happy`/`calm`; fusion gains `triumphant`, drops `romantic`/`dark`/`melancholic`.)

---

## 6. The Interpreter

`interpret(params, master_seed, overrides) → GenerationPlan`. Resolution order is normative (later steps read earlier results):

```
1. validate(params, pack)                  # full error list, §3.1
2. mood   = params.mood or pack.defaultMood
3. (V, A) = moods.yaml[mood].anchor
4. derived = formulas(V, A)                # §4.2
5. derived = apply_overrides(moods.yaml[mood].overrides, derived)   # §4.3
6. tempoBpm = params.tempoBpm or draw_tempo(derived.tempoCenter, pack, rng)   # §6.2 — THE seeded draw
7. key    = resolve_key(params.key, V, pack)                        # §6.3, deterministic
8. swing  = resolve_swing(pack.feel, tempoBpm, pack.swingRatio?)    # §6.4, deterministic
9. budgets, timbreDirectives = pack_scale(derived, pack.expressionRanges)     # §4.2
10. roleFlavors = merge(pack.ensembles.default, pack.ensembles[params.ensemblePreset], params.roleFlavors)
11. maxLengthTicks = floor(maxLengthSec × tempoBpm × 8)
    # = maxLengthSec × (tempoBpm/60) beats/sec × 480 ticks/beat, floored to int once
12. assemble GenerationPlan (worked examples §6.5)
```

### 6.1 RNG discipline

The Interpreter receives `random.Random(stream_seed(master, overrides, "interpreter"))` — the `interpreter` stream is added to PHASE_1's registry (amendment, §10). **v1 makes exactly one draw** (the tempo draw), and only when `params.tempoBpm` is absent. When the user supplies a tempo, the stream goes unconsumed — per-stream isolation (PHASE_1 §5.3) guarantees this cannot shift any other stage.

Future draws (e.g., tonic selection, §9 Q2) must be *appended* to the draw sequence, never inserted before existing draws, and constitute a `generatorVersion` minor bump (golden tests catch violations).

### 6.2 Tempo resolution

User value (already validated against pack `tempoRange`) wins unconditionally — the mood range constrains only the auto path (the iReal-Pro lesson: never clobber an explicit user tempo).

Auto path:

```
lo = max(round(0.9 × tempoCenter), pack.tempoRange.lo)
hi = min(round(1.1 × tempoCenter), pack.tempoRange.hi)
if lo > hi:  tempoBpm = clamp(round(tempoCenter), pack.tempoRange)   # degenerate: no draw
else:        tempoBpm = lo + rng.randrange(hi − lo + 1)              # single integer draw
```

### 6.3 Key resolution (deterministic in v1)

The engine **mode ladder** — the empirically monotonic valence ordering (Temperley & Tan; the contested Lydian rung is excluded, D8) — with valence bands:

| Rung | Mode | Ideal band |
| --- | --- | --- |
| 0 | `major` | V ≥ +0.25 |
| 1 | `mixolydian` | 0.00 ≤ V < +0.25 |
| 2 | `dorian` | −0.30 ≤ V < 0.00 |
| 3 | `minor` | −0.65 ≤ V < −0.30 |
| 4 | `phrygian` | V < −0.65 |

Resolution:

- `params.key.mode` given → use it (already validated against `pack.modes`).
- Else: find the ideal rung from the mood's V; pick the pack-menu mode minimizing rung distance; ties break toward the brighter (lower) rung. Example: `mysterious` (V = −0.20, ideal `dorian`) on pop/rock's `[major, minor]` menu → `minor` (distance 1 beats major's 2) — moot in v1 since pop/rock doesn't support `mysterious`, but the rule is normative.
- `params.key.tonic` given → use it. Else: **first entry of the pack's `tonics` list for the resolved mode**. Deterministic in v1; widening to a seeded draw is Q2.
- Emit `key = {tonicPc, mode}` (tonic normalized to pitch class). This is final: **Phase 4 never changes `key`** — it owns everything *inside* the key (progressions, borrowed chords, cadences; mid-song modulation stays PHASE_1 Q6, reserved to Phase 4's extension point).

No rung in v1 is reachable below `minor` by mood (no anchor has V < −0.65); `phrygian` exists in the ladder for future moods/packs.

### 6.4 Swing resolution (deterministic; style + tempo, never mood)

From pack `feel`:

- `straight8` / `straight16` → `swing = null`.
- `swing8` → `subdivision: "8"`; `swing16` → `subdivision: "16"`.
- Ratio from the tempo-dependent table below — piecewise-linear encoding of Friberg & Sundström's measurement that the swung short note is near-constant (~100 ms), so the long:short ratio relaxes as tempo rises. Evaluated at `tempoBpm` for `swing8`, at `2 × tempoBpm` for `swing16` (the swung unit is half as long). Pack `swingRatio` overrides the table entirely.

| BPM (long:short) | ≤ 90 | 120 | 140 | 160 | 200 | ≥ 240 |
| --- | --- | --- | --- | --- | --- | --- |
| ratio | 2.60:1 | 2.24:1 | 2.00:1 | 1.80:1 | 1.40:1 | 1.00:1 |

Linear interpolation between columns; encoded into PHASE_1's `swing.ratio = r/(1+r)` (so 2:1 → 0.667; range lands inside the pinned [0.5, 0.75]). Rounded to 3 decimals.

### 6.5 Worked examples (normative — golden fixtures)

**Example 1** — minimal params, pop/rock: `{styleFamily: "pop_rock", seed: "1ps9wxb"}` (master 3735928559):

```jsonc
{
  "stylePack": { "id": "pop_rock", "version": "0.1.0" },
  "seed": { "master": 3735928559, "overrides": {} },
  "key": { "tonicPc": 4, "mode": "major" },        // happy V=+0.75 → major; tonics.major[0] = E
  "tempoBpm": 123,                                  // center 118.1 → range [106,130]; draw = 123
  "timeSignature": { "numerator": 4, "denominator": 4 },
  "swing": null,                                    // feel: straight8
  "maxLengthTicks": 177120,                         // 180 s × 123 BPM × 8
  "roleFlavors": { "drums": "acoustic_kit", "bass": "electric_fingered",
                   "comping": "clean_electric", "pads": "warm_analog" },
  "moodVector": { "valence": 0.75, "arousal": 0.4 },
  "budgets": {
    "noteDensity": 0.648,        // 0.20 + 0.690 × 0.65
    "dissonance": 0.132,         // 0.05 + 0.235 × 0.35
    "dynamicsBase": 0.65, "dynamicsRange": 0.21,
    "articulationLegato": 0.34,
    "layersMax": 4, "harmonicRhythmBase": 1.0, "registerBias": 0.188
  },
  "timbreDirectives": { "brightness": 0.835, "attackHardness": 0.66, "space": 0.36 }
}
```

**Example 2** — explicit-ish params, jazz: `{styleFamily: "jazz", mood: "melancholic", maxLengthSec: 240, seed: "1ps9wxb"}`:

```jsonc
{
  "stylePack": { "id": "jazz", "version": "0.1.0" },
  "seed": { "master": 3735928559, "overrides": {} },
  "key": { "tonicPc": 2, "mode": "minor" },        // V=−0.50 → minor; tonics.minor[0] = D
  "tempoBpm": 69,                                   // override center 68 → range [61,75]; draw = 69
  "timeSignature": { "numerator": 4, "denominator": 4 },
  "swing": { "ratio": 0.722, "subdivision": "8" },  // 69 BPM ≤ 90 → 2.6:1 → 0.722
  "maxLengthTicks": 132480,                         // 240 s × 69 BPM × 8
  "roleFlavors": { "drums": "brush_kit", "bass": "upright",
                   "comping": "piano", "pads": "airy_strings" },
  "moodVector": { "valence": -0.5, "arousal": -0.45 },
  "budgets": {
    "noteDensity": 0.505,        // 0.25 + 0.393 × 0.65 (rounded)
    "dissonance": 0.653,         // 0.35 + 0.550 × 0.55 (rounded)
    "dynamicsBase": 0.438, "dynamicsRange": 0.217,
    "articulationLegato": 0.68,
    "layersMax": 3, "harmonicRhythmBase": 0.5, "registerBias": -0.125
  },
  "timbreDirectives": { "brightness": 0.333, "attackHardness": 0.32, "space": 0.657 }
}
```

Seed golden vectors (extending PHASE_1 §5.6, same master 3735928559): `derive(M, "interpreter") = 1597995742192405040` (base36 `c52i7pgxyq7k`); `random.Random` on it: first five `getrandbits(32)` = `[2363389903, 657679001, 1185547844, 3677075558, 3126580447]`; first five `randrange(100)` from a fresh instance = `[70, 19, 35, 93, 77]`.

---

## 7. `GenerationPlan` extension points (now pinned)

The three Phase-2-owned slots from PHASE_1 §4.1, defined field-level. These are now **pinned** — changing them requires amending this document.

### 7.1 `moodVector`

| Field | Type | Notes |
| --- | --- | --- |
| `valence` | float [−1, 1] | the resolved mood's anchor V |
| `arousal` | float [−1, 1] | the resolved mood's anchor A |

The mood *word* is not in the plan — downstream stages must key behavior off the vector and budgets (which carry the overrides' effects), never off mood names. Tension, when a stage wants it, is the derived `(arousal − valence)/√2`.

### 7.2 `budgets`

| Field | Type | Consumers | Semantics |
| --- | --- | --- | --- |
| `noteDensity` | float [0, 1] | Phase 5 (arrangement planner distributes into per-role/per-section `densityBudget` — formula pinned PHASE_5 §4.2, 2026-07-07) | pack-scaled overall event-density budget; 0 = sparsest the style allows, 1 = densest |
| `dissonance` | float [0, 1] | Phase 4 (progression/extension selection), Phase 5 (tension-degree usage) | pack-scaled harmonic-color budget; Phase 4 defines its concrete ladder against this scalar |
| `dynamicsBase` | float [0, 1] | Phases 5/6 | center of the velocity distribution before accent maps |
| `dynamicsRange` | float [0, 1] | Phase 6 | expressive velocity width around the base (consumed as the velocity-jitter width, PHASE_6 §5.5, 2026-07-07) |
| `articulationLegato` | float [0, 1] | Phases 5/6 | 0 = staccato, 1 = legato; scales default note durations |
| `layersMax` | int 2–4 | Phase 5 (arrangement planner) | ceiling on simultaneously active roles at peak section energy |
| `harmonicRhythmBase` | float, v1 ∈ {0.5, 1.0} | Phase 4 | baseline chords per bar, consumed as a **soft selection filter** over progression-pool entries (amended by PHASE_4 §5.2/D9, 2026-07-07: base 0.5 prefers entries with computed density ≤ 1.0 when available; base 1.0 is inert; pool content keeps authority over local harmonic rhythm) |
| `registerBias` | float [−1, 1] | Phase 5 | nudges part registers up/down *within* ArrangementPlan lanes; never violates the C5 ceiling (concretized PHASE_5 §4.3, 2026-07-07: shifts comping/pads lanes by `round(bias × 12)` semitones, clamped ≤ 71; bass/drums unshifted). Consumption of `dynamicsBase` (additive velocity shift) and `articulationLegato` (duration scaling, comping + pattern-mode bass) pinned in PHASE_5 §3.4 |

### 7.3 `timbreDirectives`

Consumed by Phase 7 (sound design), which owns the mapping from directives + `roleFlavors` to concrete Tone.js patches.

| Field | Type | Semantics |
| --- | --- | --- |
| `brightness` | float [0, 1] | filter cutoff / harmonic richness tendency |
| `attackHardness` | float [0, 1] | envelope attack sharpness tendency |
| `space` | float [0, 1] | reverb/air amount tendency (bus send levels, decay) |

Phase 7 may add fields here as *it* needs (it consumes, this phase produces; additions are negotiated amendments to this table). (Consumption pinned by PHASE_7, 2026-07-07 — no fields added: `brightness` → per-role tone-color mappings, `attackHardness` → envelope attack on pitched roles (drums exempt), `space` → reverb sends + bus decay/preDelay; PHASE_7 §5.1/§6.2.)

---

## 8. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Mood model: V/A anchor + shared formulas + per-mood overrides** | Formulas keep 12 moods coherent and new moods cheap (linearity is empirically supported — zero significant cue interactions in the factorial studies); overrides encode the documented music-domain corrections (romantic/aggressive/tense) that pure formulas get wrong. | Pure V/A formulas (fails at documented corners; fixing one mood bends all); fully hand-authored per-mood tables (12 × 13 values with no enforced coherence; the Gracenote-style curation cost without the data). |
| D2 | **12-mood vocabulary** (happy, energetic, triumphant, calm, dreamy, romantic, nostalgic, melancholic, dark, mysterious, tense, aggressive) | Tiles all quadrants; dense in the low-arousal half where real-world mood tags concentrate; includes the GEMS words (nostalgic, triumphant) plain circumplex misses; every word earns authoring cost across 5 packs. Additive to extend later. | 8 words (loses the differentiating mid-plane words); 16+ (near-neighbors like happy/playful/hopeful risk indistinguishable v1 output; larger per-pack burden). |
| D3 | **Packs declare `supportedMoods` + `defaultMood`; unsupported combos are validation errors** | With no human-in-the-loop curation, the full mood×style cross-product ships garbage corners; quality ownership belongs in the pack, where the patterns live. Explicit error > silent substitution. | All moods everywhere with V/A clamping (silent "you got something else"); nearest-supported-mood fallback (complicates the contract; client can build the same UX from the declared lists). |
| D4 | **Interpreter draws seeded randomness, scope = exactly one tempo draw** (auto path only); `interpreter` stream added to registry | Without it, every same-params track has identical tempo regardless of seed — audibly samey in the core fresh-seed flow. Narrow scope keeps the stage testable; append-only draw discipline + golden tests make widening safe later. | Fully deterministic (frozen feel per params combo); broader draw scope now (unproven audibility, harder to reason about, easy to widen later / hard to narrow). |
| D5 | **Interpreter emits final `key.mode` from the pack's mode menu via the valence ladder; Phase 4 owns everything inside the key and never rewrites it** | One authoritative key for every stage (the ambiguity PHASE_1 contracts exist to prevent); mode-as-#1-valence-cue belongs with the mood model; mode menus keep style identity (blues stays dominant-colored, jazz keeps dorian/mixolydian). | Binary major/minor in Phase 2 with Phase 4 refinement (two stages sharing authority over a pinned field); global valence ladder without pack menus (musically wrong at corners — dark blues going phrygian). |
| D6 | **`params.mood` accepts mood words only; V/A coordinates stay internal** | Anchors stay recalibratable without breaking clients; every reachable input is a curated, tested point; the supported-moods gate stays airtight (raw vectors would bypass it). Matches every shipping product. | Raw V/A override (bypasses quality gate, freezes coordinates as public contract); intensity scalar (no research basis for half-strength moods; Phase 3's section energy covers the use case). |
| D7 | **Tempo: optional exact integer BPM; pack range = hard bound; mood range constrains only the auto path; auto = uniform integer draw in `[0.9c, 1.1c] ∩ pack range`** | Musician tools all expose exact BPM; style-range validation is the BIAB/Yamaha convention; explicit user tempo always wins (the iReal-Pro clobbering lesson). | Named buckets (Soundraw's low/normal/high — leaves musicians unable to hit a number); mood range as hard bound (forbids legitimate "fast sad" requests). |
| D8 | **Mode ladder = major > mixolydian > dorian > minor > phrygian; Lydian excluded in v1** | The included ordering is empirically monotonic in valence (Temperley & Tan) and matches the generation-system consensus; Lydian is the one rung where theory (Persichetti: brightest) and data (Temperley & Tan: below mixolydian) conflict. | Full Persichetti ladder including Lydian (contested rung); major/minor only (loses jazz/blues modal identity). |
| D9 | **Swing = f(pack feel, tempo), never mood; Friberg-derived ratio table with constant-short-note shape; pack override available** | The microtiming literature is unambiguous: swing ratio tracks style and tempo (short note ≈ constant ~100 ms), and exaggerating microtiming to signal emotion degrades groove. | Mood-scaled swing (contradicts research); fixed per-style ratio ignoring tempo (measurably wrong across the tempo range). |
| D10 | **Auto-tonic: deterministic first entry of the pack's per-mode tonic pool; pools are instrument-idiomatic (guitar keys for pop/rock, flat keys for jazz)** | Absolute key is emotionally inert (key-character lists are temperament artifacts; every affective generator fixes the tonic) — so key choice should serve *players*, which is what jam-track products do. Deterministic keeps D4's narrow-draw promise. | Mood-derived tonic (no evidence basis); seeded tonic draw (widens RNG scope now — deferred, Q2). |
| D11 | **Density and dissonance pass through per-pack `expressionRanges`; all other derived values are global** | These two are style-relative (jazz's dissonance floor exceeds pop's ceiling); mapping mood-normalized [0,1] through pack ranges is exactly how "mood morphs within a style" (roadmap §2) becomes arithmetic. Dynamics/articulation/timbre read as absolute across styles. | Pack-scaling everything (per-pack authoring burden with no identified need); pack-scaling nothing (aggressive jazz and aggressive pop would share literal dissonance values — musically wrong). |
| D12 | **Length: `maxLengthSec` (30–600, default 180), converted to `maxLengthTicks` after tempo resolution** | Consumer norm is seconds; the musical truth (bars/sections) is Phase 3's job via the tick budget. Conversion needs resolved tempo, hence Interpreter-late. | Bars/choruses param (musician-only framing; Phase 3 can add a form-count param later if wanted); both-units param in v1 (YAGNI). |
| D13 | **Ensemble preset + per-role flavor overrides merge (default → named preset → `roleFlavors`)** | Yamaha OTS insight: presets so users rarely pick per-role, overridable so they can. Pack must ship a complete `default` — every call resolves to full role coverage. | Mutually exclusive preset XOR flavors (needless rigidity); no presets (per-role burden on every casual call). |
| D14 | **Flavor/ensemble *vocabulary* lives in `interpreter.yaml`; patch *implementation* stays in Phase 7's `timbres.yaml`** | Phase 2 must validate flavor ids without owning synthesis; the vocabulary/implementation split keeps this phase self-contained and gives pack validation a cross-file completeness check. | Vocabulary inside `timbres.yaml` (couples param validation to a Phase 7 schema that doesn't exist yet). |

---

## 9. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | ~~Per-pack per-mood overrides?~~ **Resolved** — not needed: mood tempo centers ∩ pack tempo ranges yield each genre's tiers, and expression ranges do the rest, across all five packs (PHASE_8 §3.8, 2026-07-07) | ~~Phase 8~~ | — |
| Q2 | Widen the interpreter draw to tonic selection (seeded pick from the pool instead of first-entry)? | Any later phase / listening feedback | evidence that fixed auto-keys feel repetitive; append-only draw discipline (§6.1) makes this safe |
| Q3 | ~~`harmonicRhythmBase` mapping — does it survive contact with Phase 4's progression design?~~ **Resolved** — renegotiated to a soft density filter at pool selection (PHASE_4 §5.2/D9; §7.2 row amended, 2026-07-07) | ~~Phase 4~~ | — |
| Q4 | ~~User-facing global energy/intensity knob (distinct from mood)?~~ **Resolved** — no knob in v1; arousal modulation + pack energy envelopes cover it, insertion point documented (PHASE_3 §6.3/D10) | ~~Phase 3~~ (resolved 2026-07-07) | revisit post-v1 only with listening evidence |
| Q5 | Mood blending / custom V/A input (API power users)? | Post-v1 | D6 keeps coordinates private; revisit only with a validation story for arbitrary points |
| Q6 | ~~Lydian rung in the mode ladder?~~ **Resolved** — stays excluded: no v1 pack's mode menu wants it (PHASE_8 §3.8, 2026-07-07) | ~~Phase 8~~ | — |
| Q7 | Non-4/4 time signatures in `params`? | When a pack ships one | pack manifests already declare `timeSignatures`; params stays silent until needed |

---

## 10. Amendments to earlier documents (this session)

All additive; applied in the same commit as this document:

1. **PHASE_1 §5.2 stream registry**: `interpreter` added to the top-level stream names (D4).
2. **PHASE_1 §5.6 golden vectors**: row added for `interpreter` (value in §6.5).
3. **PHASE_1 §6 pack layout**: `interpreter.yaml` added, schema owned by Phase 2 (§5.1).
4. **PHASE_1 §7 Q1** (params schema): resolved by this document (§3).
5. **ROADMAP §2 decisions log**: row added for the style × mood interaction model and mood vocabulary (D2/D3).

---

## 11. Definition of done

Phase 2 is **built** when an implementation session demonstrates:

1. **Params model**: pydantic v2 model for §3 (frozen), full §3.1 error catalog with stable codes, full-list (not first-failure) reporting; `docs/schema/params.schema.json` exported and committed.
2. **Mood data**: `src/trackgen/interpreter/moods.yaml` with the 12 anchors and §4.3 overrides, loaded into frozen models; a test asserting the §4.4 derived-defaults table **exactly** (all 12 moods × 13 values).
3. **Pack loader extension**: `interpreter.yaml` parsing + §5.1 validation rules (including ensemble completeness and flavor-id referential checks); reference files for `pop_rock` and `jazz` as in §5.1; rejection tests for each validation-rule class.
4. **Interpreter stage**: implements §6 exactly; golden tests asserting both §6.5 worked-example GenerationPlans **field-for-field**, plus the `interpreter` seed golden vectors.
5. **Determinism**: same params + seed → identical plan (repeated-run test); `params.tempoBpm` given → zero RNG consumption (assert via a counting-RNG shim); user-tempo and user-key paths bypass draws/ladders correctly.
6. **Property tests**: every pack × every supported mood × auto-everything produces a plan that passes GenerationPlan validation, honors pack `tempoRange`, `modes`, and expression ranges, and satisfies `swing.ratio ∈ [0.5, 0.75]` when non-null.
7. **Validation coverage**: one failing-params fixture per §3.1 error code, each asserting code + field.
8. **PHASE_1/ROADMAP amendments** (§10) applied and consistent (registry, golden vectors, pack layout, Q1, decisions log).

---

## 12. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §5.1: all style×mood behavior is declarative YAML (`supportedMoods`, menus, ranges); the engine's mood table is likewise data |
| 2. Rhythm separate from pitch | Untouched — this phase emits no notes; budgets/directives are scalars |
| 3. Hierarchical seeds | §6.1: one named stream (`interpreter`), derived per PHASE_1 §5.2; override-based rerolls work unchanged |
| 4. Soloist owns above ~C5 | `registerBias` explicitly operates within ArrangementPlan lanes (§7.2); no field this phase emits can raise a ceiling |
| 5. Deterministic pipeline | §6.1 single-draw discipline; integer-only randomness; ordered-YAML candidate lists; 3-decimal half-even rounding pinned; entropy still enters only at the API boundary |
