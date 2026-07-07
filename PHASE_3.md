# PHASE_3 — Form & Structure

Designed 2026-07-07 (session 3). Status: **awaiting approval**.

This document pins the Form generator — pipeline stage 2, `GenerationPlan → SongForm` — end to end: the full section-type vocabulary and its downstream semantics, the `SongForm` extension points PHASE_1 reserved for this phase, the `forms.yaml` style-pack schema (resolving the forms part of PHASE_1 Q4), the length-fitting algorithm, and the per-section energy model. It also resolves PHASE_2 open question Q4 (no user-facing energy knob in v1).

Research base (session 3): fresh statistics computed from the Harmonix Set (Nieto et al., ISMIR 2019 — 912 annotated chart songs: section-sequence, bar-count, and transition distributions), cross-checked against Summach (*MTO* 2011), Tough (MEIEA 2018), von Appen & Frei-Hauenschild (2015), Stroud (*MTO* 2022), Nobile (*MTO* 2022), and Léveillé Gauvin (2018); a parse of the Aebersold play-along index (973 tracks — chorus-count × tempo statistics); Van Balen et al. (ISMIR 2013) and Farbood (2012) on section energy; Frieler et al. (2016) on jazz-solo dramaturgy; and the form machinery of Band-in-a-Box, Yamaha SFF styles, Korg Pa, iReal Pro, JJazzLab, MMA, Soundraw, and the Amper patents (US 10854180 — weighted form-probability tables).

---

## 1. Scope

**In scope**

- The section-type vocabulary, complete for v1 (11 types), with the semantics table Phases 4/5/6 consume — what each type *means* to harmony, arrangement, and transitions.
- The `SongForm` extension points reserved by PHASE_1 §4.2, pinned field-level: phrase substructure, harmony tags, variation markers, occurrence totals, the ending directive, and document-level template provenance.
- The `forms.yaml` pack-file schema (structure + validation rules), with normative reference content for `pop_rock` and `jazz`.
- The Form generator algorithm: template selection, slot resolution, length fitting (arithmetic repeat counts, feasibility-constrained draws, degradation ladder, minimal fallback), RNG discipline, and two normative worked examples chained from PHASE_2 §6.5.
- The energy model: engine base table, positional rules, arousal modulation, pack envelopes, template overrides.
- Section labels for `TrackDocument.sections` (the 1:1 derivation PHASE_1 §4.2 promises).
- Amendments to earlier documents (all additive, §10).

**Explicitly not in scope**

- Harmony content: which chords fill the sections (Phase 4 — this phase emits `harmonyTag` hooks, not chords). Cadence *logic* is Phase 4's (§4 explains why no cadence field exists here).
- Arrangement, pattern selection, fills, transitions: Phase 5 maps `energy` to intensity rungs; Phase 6 renders fills/risers/ritards at the boundaries and directives this phase marks.
- Style-pack *content* beyond the two reference `forms.yaml` files (Phase 8 authors chill_lofi/blues/fusion_jazz, using `main`/`breakdown`/`postchorus`/`variant` — see §9 Q1).
- A count-in. iReal Pro's count-in is client UX, not musical content; a client can prepend its own click bar (D14).
- Mid-song tempo/time-signature changes (one signature per song, PHASE_1 §4.1).

---

## 2. Contracts consumed

| Upstream contract | What this phase does with it |
| --- | --- |
| `GenerationPlan` pinned core (PHASE_1 §4.1) | Consumes `maxLengthTicks` (hard budget), `timeSignature` (bar→tick), `stylePack` (loads the pack's `forms.yaml`). |
| `GenerationPlan.moodVector` (PHASE_2 §7.1) | `arousal` drives energy modulation (§6.3) and template eligibility gates (§5.2). `valence` is unused by Form in v1. Mood *words* are never visible here (PHASE_2 §7.1 discipline). |
| `GenerationPlan.budgets` (PHASE_2 §7.2) | **Not consumed.** Density/dissonance/dynamics budgets target Phases 4–6; section energy is this phase's own output, not derived from them. |
| Seed system (PHASE_1 §5) | All draws from `random.Random(stream_seed(master, overrides, "form"))`; `weighted_choice` only; integer weights; append-only draw discipline (§7.2). |
| `SongForm` pinned core (PHASE_1 §4.2) | Produces every pinned field exactly: `sections[{id, type, index, startBar, lengthBars, energy}]`, `totalBars`; `lengthBars ≥ 4` honored everywhere including endings (D6). Fills the extension points PHASE_1 reserved for this phase (§4). |
| Section vocabulary ownership (PHASE_1 §3.4) | Extends the starter six to eleven types (§3); `TrackDocument.sections.type` carries them. |
| Pack structure (PHASE_1 §6) | `forms.yaml` schema defined here (§5); manifest `timeSignatures[0]` determines ticks-per-bar; new pack-sanity rule F11 ties `tempoRange.lo` to the 30 s minimum length. |
| Determinism rules (PHASE_1 §5.3) | Integer weights, ordered YAML lists, no floats in selection, 3-decimal half-even rounding for emitted energies (PHASE_2 precedent). |

---

## 3. Section-type vocabulary & semantics

### 3.1 The vocabulary (pinned, closed)

Eleven types. Packs may only use these; extending the list is an amendment to this document. Rationale: pop/rock needs the sectional six (+ `postchorus`, present in 13–22% of modern pop and recurring systematically — Stroud 2022, Harmonix); jazz/blues are *cyclic* forms needing `head`/`solo` (mapping them onto verse/chorus would hand downstream stages false semantics — D2); loop styles need `main`/`breakdown` (lo-fi's grammar is layer variation over a loop, not harmonic sections).

| Type | Structural role | Used by (reference) |
| --- | --- | --- |
| `intro` | opening; establishes key + groove | all styles |
| `verse` | narrative body; low-mid energy | pop_rock |
| `prechorus` | buildup into chorus | pop_rock |
| `chorus` | arrival + plateau; the hook | pop_rock |
| `postchorus` | hook sustain after a chorus | (Phase 8 styles) |
| `bridge` | contrast/departure, once, late | pop_rock |
| `head` | full pass of a cyclic form; user states the melody | jazz (blues in Phase 8) |
| `solo` | full pass of a cyclic form; user improvises | jazz (blues in Phase 8); also pop solo sections |
| `main` | loop section in loop-based styles | (Phase 8: chill_lofi) |
| `breakdown` | stripped-down dip | (Phase 8 styles) |
| `outro` | close | all styles |

### 3.2 Semantics table (normative for Phases 4/5/6)

Each row is the contract a downstream stage implements. These are *tendencies keyed off type + position*; the concrete rules live in the owning phase, but they must be consistent with this table.

| Type | Harmony (Phase 4) | Arrangement (Phase 5) | Transitions (Phase 6) |
| --- | --- | --- | --- |
| `intro` | tonic-centered vamp or turnaround from the `intro` pool; ends **open** into the first body section | reduced layers (below the following section); groove established, full kit optional | fill into the next section's downbeat |
| `verse` | `verse` pool; ends **open** (half cadence toward prechorus/chorus) | moderate density; the most soloist space of any body section | small fill at phrase boundaries; medium fill at section end |
| `prechorus` | dominant-directed motion; ends **on V** | density rises above verse; layers may pre-enter | build device allowed (riser/snare build); fill into chorus mandatory |
| `chorus` | `chorus` pool; closes **on I**; final instance gets the strongest close | fullest layering within budgets; widest register use (still ≤ C5 lanes) | crash on entry downbeat; big fill preceding |
| `postchorus` | tonic prolongation, loop-friendly | slightly thinner than chorus, hook-supporting | smooth continuation, no big fill on entry |
| `bridge` | contrast: off-tonic start, ends **on V** into the return | thinner texture, register/timbre contrast | biggest fill of the song into what follows (usually final chorus) |
| `head` | the form's progression verbatim (`harmonyTag` pool) | stable, supportive comping; low interaction (user is playing the melody) | small boundary fill only |
| `solo` | same progression as `head` (shared via `inherit`) | interactive comping; density follows the energy arch | fills between passes welcome |
| `main` | repeating loop progression | layer add/drop driven by energy + `variant` | subtle transitions only (filter/texture, not fills) |
| `breakdown` | thinned harmony: pedal point or held chord permitted | minimum layers above silence | entered by *dropout* (no fill); exit fill into the next section |
| `outro` | cadential; obeys the `ending` directive (§4.2) | winding down | renders the `ending` directive: tag repeat, ritard, cold stop, or fade |

### 3.3 Display labels (pinned — derivation of `TrackDocument.sections[].label`)

`index`/`totalOfType` drive the label; rule: append the index iff `totalOfType > 1`, with these specials:

| Type | Label rule |
| --- | --- |
| `chorus` | `index == totalOfType and totalOfType ≥ 2` → `"Final Chorus"`; else `"Chorus {index}"` (no index if single) |
| `head` | first → `"Head In"`, last → `"Head Out"`, middle → `"Head {index}"` |
| `solo` | `"Solo Chorus {index}"` (no index if single) |
| `main` | `"Part {variant}"` if `variant` set, else `"Part {index}"` |
| all others | title-cased type (`"Pre-Chorus 2"`, `"Verse 1"`, `"Bridge"`, `"Intro"`, `"Outro"`, `"Breakdown"`, `"Post-Chorus"`) |

---

## 4. `SongForm` extension points (now pinned)

The slots PHASE_1 §4.2 reserved for this phase, defined field-level. Changing these requires amending this document.

### 4.1 Per-section fields (added to the pinned `{id, type, index, startBar, lengthBars, energy}`)

| Field | Type | Notes |
| --- | --- | --- |
| `totalOfType` | int ≥ 1 | occurrences of this `type` in the whole form; `index == totalOfType` ⇒ final instance (the fact half the research conventions key on) |
| `phrases` | `[{label: str, bars: int}]` | covers the section exactly (`Σ bars == lengthBars`); uniform phrase length in v1 (§5.1 F3). Same label ⇒ same harmonic material (Phase 4); phrase starts are Phase 5 pattern-alignment points and Phase 6 small-fill points |
| `harmonyTag` | str | key into the pack's Phase 4 progression pools (`aaba_32`, `blues_12`, `chorus`, …). Cross-file referential check lands with Phase 4's loader (PHASE_2 D14 pattern) |
| `variant` | str \| null | variation marker for same-type-different-content sections (lo-fi A/B loops, BiaB-style middle-chorus variation). `null` in both reference packs (§9 Q1) |
| `ending` | `{tagBars: int, close: "ritard" \| "cold" \| "fade"} \| null` | **non-null on the final section only.** `tagBars ∈ {0, 4, 8}`: the last `tagBars` bars are the tag phrase (Phase 4 cadences there; Phase 6 renders the ritard/fade). `0` = close on the last bar without a tag |

### 4.2 Document-level field

| Field | Type | Notes |
| --- | --- | --- |
| `templateId` | str | provenance (which template produced this form) — debugging + golden tests, same spirit as `ChordSpec.roman` |

### 4.3 Deliberately absent: a cadence field

ROADMAP assigns cadence *logic* to Phase 4 ("verses end open on V, choruses close on I, deceptive cadences before repeated final choruses"). Every input those rules need is already in `SongForm` (`type`, `index`, `totalOfType`, the next section's `type`, `ending`). A Phase 3 cadence field would put two stages in charge of one decision — the ambiguity PHASE_1's contracts exist to prevent (D8). The §3.2 harmony column documents the tendencies Phase 4 must implement.

### 4.4 Worked `SongForm` fragment

One section from worked example 2 (§7.4):

```jsonc
{
  "id": "solo-2", "type": "solo", "index": 2, "totalOfType": 3,
  "startBar": 24, "lengthBars": 12, "energy": 0.704,
  "phrases": [ {"label": "a", "bars": 4}, {"label": "b", "bars": 4}, {"label": "c", "bars": 4} ],
  "harmonyTag": "blues_12", "variant": null, "ending": null
}
```

---

## 5. The `forms.yaml` schema

Two top-level parts (D3 — JJazzLab's section/part split): `sections` declare per-type defaults once; `templates` are weighted spines referencing them. Plus the pack's energy envelope.

### 5.1 Schema, field-level

```yaml
energyRange: [lo, hi]        # pack energy envelope, 0 ≤ lo ≤ hi ≤ 1 (§6.4)

sections:                    # per-type defaults for this style
  <type>:                    # key ∈ §3.1 vocabulary
    bars: [[n, w], ...]      # weighted bar-count options, ordered as authored;
                             #   n: int, multiple of 4, ≥ 4; w: int ≥ 1
    phrases: {n: [labels]}   # per bar option: phrase labels; len divides n,
                             #   quotient (= phrase length) an int ≥ 4.
                             #   Scalar list allowed when there is a single option.
    harmonyTag: {n: tag}     # per bar option; scalar allowed when single option
  <type>:
    inherit: <type>          # alternative: share another type's resolved bars/
                             #   phrases/harmonyTag (jazz solo ≡ head). Single level.

templates:
  - id: <str>                # unique in pack
    weight: <int ≥ 1>        # selection weight among eligible templates
    eligibility:             # optional gate; template also auto-gated by minBars
      arousal: [min, max]    # inclusive band on moodVector.arousal
    spine:                   # ordered elements; ≤ 1 repeat block per template (v1)
      - { section: <type>,           # slot
          optional: [incW, excW],    # optional: integer include:exclude odds
          energy: <float 0-1>,       # optional: energy override (§6.5)
          variant: <str> }           # optional: variation marker
      - repeat:                      # repeat block
          count: [min, max]          # max may be null = fit to budget
          slots: [ <slot>, ... ]
    ending: { tagBars: 0|4|8, close: ritard|cold|fade }   # attaches to the
                             #   form's FINAL section, whichever survives fitting
    degrade:                 # ordered emergency ladder (§7.3)
      - { drop: <type> }             # remove top-level slots of the type
      - { shrink: <type> }           # force the type to its smallest bar option
      - { dropFromRepeat: <type> }   # remove the type from the repeat block
    fallback: { section: <type>, bars: <int> }   # minimal form of last resort
```

**Validation rules** (loader; each class gets a rejection fixture):

- **F1** `sections` non-empty; every key in the §3.1 vocabulary; bar options: ints, multiples of 4, ≥ 4; weights ints ≥ 1; list order preserved.
- **F2** `inherit`: target exists in `sections`, does not itself inherit, and the inheriting entry declares no other fields.
- **F3** `phrases`: an entry for every bar option `n`; `len(labels)` divides `n` with integer quotient ≥ 4. `harmonyTag`: an entry for every option.
- **F4** `templates` non-empty; `id`s unique; `weight` int ≥ 1; at most one repeat block per template; `count.min ≥ 1`, `count.max ≥ min` or null; block slots non-empty; every slot's `section` declared in `sections`.
- **F5** an `inherit`ing type's first spine occurrence must come after its target's first occurrence (resolution order, §7.1 step 3).
- **F6** `optional` weights: both ints ≥ 1.
- **F7** slot `energy` overrides ∈ [0, 1]; `variant` non-empty string.
- **F8** `ending.tagBars ∈ {0, 4, 8}`; `close` in its enum. `tagBars` ≤ the smallest bar option of every type that can end the form.
- **F9** `degrade` ops reference types present in the template's spine; `fallback.section` is a type in the template; `fallback.bars` a multiple of 4, ≥ 4.
- **F10** `energyRange`: `0 ≤ lo ≤ hi ≤ 1`.
- **F11** *(manifest cross-check)* `tempoRange.lo` must yield a bar budget ≥ 4 at `maxLengthSec = 30` — for `/4` signatures, `tempoRange.lo ≥ 8 × numerator` (4/4 ⇒ ≥ 32 BPM). Guarantees the fitter always has room for one legal section.
- **F12** every template declares `fallback`.
- **F13** at least one template per pack has no `arousal` gate (so every supported mood reaches a template).

Cross-file (deferred, PHASE_2 D14 pattern): every `harmonyTag` must be served by a pool in `progressions.yaml` — checked when Phase 4's loader lands.

### 5.2 Template selection semantics

A template is **eligible** iff (a) its `arousal` gate, if any, contains `moodVector.arousal`, and (b) its `minBars ≤ barBudget`, where `minBars` is computed by the loader: all optionals excluded, every type at its smallest bar option, repeat at `count.min`. Selection = `weighted_choice` over eligible templates in authored order (draw skipped if exactly one — §7.2). If none is eligible, the fitter goes straight to `templates[0].fallback` (§7.3).

### 5.3 Reference content — `styles/pop_rock/forms.yaml` (normative)

```yaml
energyRange: [0.00, 1.00]

sections:
  intro:     { bars: [[4, 3], [8, 1]],  phrases: { 4: [a],    8: [a, a] },
               harmonyTag: { 4: intro,  8: intro } }
  verse:     { bars: [[8, 3], [16, 1]], phrases: { 8: [a, a], 16: [a, a, a, a] },
               harmonyTag: { 8: verse,  16: verse } }
  prechorus: { bars: [[4, 2], [8, 2]],  phrases: { 4: [a],    8: [a, a] },
               harmonyTag: { 4: prechorus, 8: prechorus } }
  chorus:    { bars: [[8, 3], [16, 1]], phrases: { 8: [a, a], 16: [a, a, a, a] },
               harmonyTag: { 8: chorus, 16: chorus } }
  bridge:    { bars: [[8, 3], [4, 1]],  phrases: { 8: [a, a], 4: [a] },
               harmonyTag: { 8: bridge, 4: bridge } }
  outro:     { bars: [[4, 3], [8, 1]],  phrases: { 4: [a],    8: [a, a] },
               harmonyTag: { 4: outro,  8: outro } }

templates:
  - id: verse_chorus_bridge        # the plurality form: ~45% of the corpus
    weight: 60
    spine:
      - { section: intro, optional: [6, 1] }        # intros present in 86% of songs
      - repeat:
          count: [2, 3]                             # 2–3 verse–chorus cycles
          slots:
            - { section: verse }
            - { section: prechorus, optional: [2, 3] }   # ~39% prevalence
            - { section: chorus }
      - { section: bridge }
      - { section: chorus }                         # the final chorus
      - { section: outro, optional: [4, 5] }        # ~44% prevalence
    ending: { tagBars: 0, close: cold }             # fade-outs are dead (Slate 2014)
    degrade:
      - { drop: outro }          # research order: outro (44% presence) before
      - { shrink: intro }        #   bridge (67%) — refines the ROADMAP sketch (D11)
      - { drop: bridge }
      - { dropFromRepeat: prechorus }
      - { shrink: verse }
      - { shrink: chorus }
      - { drop: intro }
    fallback: { section: chorus, bars: 8 }

  - id: verse_chorus               # no bridge: the V–C–V–C(–V–C) minority (~17%)
    weight: 25
    spine:
      - { section: intro, optional: [6, 1] }
      - repeat:
          count: [2, 3]
          slots:
            - { section: verse }
            - { section: chorus }                   # last cycle's chorus is final
      - { section: outro, optional: [4, 5] }
    ending: { tagBars: 0, close: cold }
    degrade:
      - { drop: outro }
      - { shrink: intro }
      - { shrink: verse }
      - { shrink: chorus }
      - { drop: intro }
    fallback: { section: chorus, bars: 8 }

  - id: chorus_first               # hook-first opening (~10-14%); high energy only
    weight: 15
    eligibility: { arousal: [0.15, 1.0] }
    spine:
      - { section: chorus, energy: 0.65 }           # the withheld first chorus
      - repeat:
          count: [2, 2]
          slots:
            - { section: verse }
            - { section: chorus }
      - { section: bridge }
      - { section: chorus }
      - { section: outro, optional: [4, 5] }
    ending: { tagBars: 0, close: cold }
    degrade:
      - { drop: outro }
      - { drop: bridge }
      - { shrink: verse }
      - { shrink: chorus }
    fallback: { section: chorus, bars: 8 }
```

### 5.4 Reference content — `styles/jazz/forms.yaml` (normative)

```yaml
energyRange: [0.10, 0.90]          # a jazz trio never slams like a rock band

sections:
  intro: { bars: [[4, 3], [8, 1]], phrases: { 4: [a], 8: [a, a] },
           harmonyTag: { 4: intro, 8: intro } }      # pool: turnarounds/vamps (Phase 4)
  head:  { bars: [[32, 3], [12, 1]],                 # AABA standard : jazz blues
           phrases: { 32: [a, a, b, a], 12: [a, b, c] },
           harmonyTag: { 32: aaba_32, 12: blues_12 } }
  solo:  { inherit: head }                           # solos play the same form
  outro: { bars: [[4, 1]], phrases: { 4: [a] }, harmonyTag: { 4: outro } }

templates:
  - id: head_solos_head            # head in → N solo choruses → head out
    weight: 100
    spine:
      - { section: intro, optional: [1, 1] }
      - { section: head }
      - repeat:
          count: [1, null]         # null = fill the budget (Aebersold tempo scaling)
          slots:
            - { section: solo }
      - { section: head }
      - { section: outro }
    ending: { tagBars: 4, close: ritard }   # tag the last phrase, ritard close
    degrade:
      - { shrink: intro }
      - { drop: intro }
      - { drop: outro }
    fallback: { section: solo, bars: 12 }
```

Both files are normative as schema and as golden-test fixtures; their *content* is reference-quality and gets refined in Phase 8 (alongside chill_lofi/blues/fusion_jazz authoring, which exercises `main`, `breakdown`, `postchorus`, `variant`, and 8/16-bar blues options).

---

## 6. The energy model

Architecture (D7): **base table + positional rules + arousal modulation + pack envelope + template overrides** — the anchor/formulas/overrides pattern PHASE_2 validated, applied to energy. Empirical footing: energy is a *section-level* property, flat within sections (Nobile 2022; Van Balen 2013 — choruses are louder/brighter/rougher with *less* internal variance); repeated sections escalate; the final chorus is the global peak; arousal shifts the whole curve; style compresses it (lo-fi's flat dramaturgy).

### 6.1 Engine base table

Engine-owned data (`src/trackgen/form/energy.yaml`, loaded like `moods.yaml`; internal, recalibratable):

| Type | intro | verse | prechorus | chorus | postchorus | bridge | head | solo | main | breakdown | outro |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Base | 0.30 | 0.45 | 0.60 | 0.75 | 0.65 | 0.40 | 0.50 | 0.60 | 0.50 | 0.25 | 0.35 |

### 6.2 Positional rules (deterministic, applied in this order)

- **R1 — escalation.** For `type ∈ {verse, prechorus, chorus, postchorus, main}`: `e += 0.05 × min(index − 1, 2)` (repeat instances get busier, capped +0.10 — the verse-2/chorus-2 convention).
- **R2 — solo arch.** For `solo` (replacing the base): `e = 0.60 + 0.30 × index / totalOfType` — a rising line peaking at 0.90 on the last solo pass (Frieler's inverted-U with a late peak). `head` deliberately has no rule: head out returns to head-in energy.
- **R3 — final-chorus peak.** For `chorus` with `index == totalOfType and totalOfType ≥ 2`: `e += 0.15` (the global maximum; with R1 a third chorus reaches 0.75 + 0.10 + 0.15 = 1.00).
- **R4 — template override.** A slot's authored `energy:` **replaces** the base + R1–R3 result (it is still modulated and enveloped below) — the escape hatch for documented exceptions like the withheld first chorus.

Dips before peaks are *structural*, not arithmetic: templates place a `bridge`/`breakdown` before the final chorus; no rule fabricates dips.

### 6.3 Arousal modulation

`e = clamp01(e + 0.10 × arousal)` — linear, one term (PHASE_2's linearity precedent). A happy track (A = +0.40) lifts every section +0.04; melancholic (A = −0.45) lowers everything −0.045.

### 6.4 Pack envelope

`energy = round(lo + e × (hi − lo), 3)` with the pack's `energyRange` — identical mechanism to PHASE_2's `expressionRanges`. Pop/rock `[0, 1]` is the identity; jazz `[0.10, 0.90]` keeps a combo dynamic; a Phase 8 lo-fi pack writes `[0.25, 0.60]` and gets flat dramaturgy from one line of data. The **post-envelope value** is what `SongForm.sections[].energy` carries (3 decimals, half-even) and what `TrackDocument` echoes; downstream stages consume it as-is.

### 6.5 Relationship to `ArrangementPlan.intensity`

Phase 5 owns the mapping from continuous energy to its 1–4 intensity ladder (PHASE_1 §4.4). The research strongly supports quantizing to 4 bands (Yamaha Main A–D, Korg V1–4) while keeping the float for continuous modulation (velocity, hat openness) — recorded here as guidance, decided in Phase 5. (**Resolved** — PHASE_5 §3.1, 2026-07-07: global thresholds 0.30 / 0.55 / 0.80; the float stays live for density and Phase 6 modulation.)

---

## 7. The Form generator

`form(plan, pack.forms, rng) → SongForm`, with `rng = random.Random(stream_seed(master, overrides, "form"))`.

### 7.1 Algorithm (normative resolution order)

```
1. ticksPerBar = numerator × (480 × 4 // denominator)          # 1920 in 4/4
   barBudget   = maxLengthTicks // ticksPerBar
2. eligible    = templates passing §5.2 (arousal gate, minBars ≤ barBudget)
   template    = weighted_choice(eligible, weights, rng)        # draw iff ≥ 2
   (eligible empty → emit fallback form directly, step 6)
3. SLOT RESOLUTION — walk the spine in order (repeat-block inner slots at the
   block's position, once — NOT per repetition):
     a. optional slot: if force-including it keeps minimalTotal ≤ barBudget,
        draw include/exclude at the authored odds; else exclude without a draw.
     b. bar count: resolved ONCE PER TYPE at the type's first included
        occurrence (inherit-target types share one resolution — D9).
        Feasible options = those keeping minimalTotal ≤ barBudget.
        ≥ 2 feasible → weighted_choice among them; exactly 1 → take it (no
        draw); 0 → take the smallest authored option (ladder will repair).
     minimalTotal = spine sum with: excluded/undecided optionals = 0,
     unresolved types at their smallest option, repeat block at count.min.
4. REPEAT COUNT (arithmetic, no draw):
     count = (barBudget − fixedBars) // blockBars,
     clamped to [count.min, count.max]  (max null ⇒ unbounded above)
5. total = fixedBars + count × blockBars
   while total > barBudget and ladder not exhausted:
       apply next degrade op; recompute count and total
6. if still total > barBudget (or step 2 found nothing eligible):
       emit the fallback form: one section of fallback.section with
       lengthBars = min(fallback.bars, 4 × (barBudget // 4)), energy per §6,
       the template ending attached
7. ASSEMBLE: expand the repeat block count times; number `index` per type in
   order of appearance; compute totalOfType; ids "{type}-{index}"; labels
   per §3.3; phrases/harmonyTag from the resolved bar option; attach the
   template `ending` to the LAST section; energies per §6; startBar
   cumulative from 0; totalBars = Σ lengthBars.
```

Properties: `totalBars × ticksPerBar ≤ maxLengthTicks` always (hard ceiling honored); the fitter *fills toward* the budget from below and stops at the template's caps (D5 — a 10-minute pop/rock request yields the pack's longest canonical form, not five identical cycles; jazz/blues/loop styles fill any budget by adding passes).

### 7.2 RNG discipline

- Draws happen **only** via `weighted_choice` on the `form` stream, **only** when ≥ 2 feasible candidates exist, in the fixed order: template → spine order (inclusion draw before bar draw per slot).
- Draw sequence is append-only across versions (PHASE_2 §6.1 rule); any new draw is a `generatorVersion` minor bump caught by golden tests.
- Ladder ops and repeat counts are arithmetic — never drawn.
- Golden vectors (master `1ps9wxb` = 3735928559, extending PHASE_1 §5.6): `derive(M, "form") = 7567330889165579844` (pinned there); `random.Random` on it: first five `getrandbits(32)` = `[1669109759, 4115657646, 81846092, 4122630717, 1459238978]`; first five `randrange(100)` from a fresh instance = `[49, 2, 43, 66, 44]`.

### 7.3 Degradation ladder & fallback

The ladder (§5.1 `degrade`) exists for budgets too small for the template's drawn/minimal configuration; ops apply in authored order, deterministically, each followed by a count/total recompute. The ladder's *order* is pack data; the reference order drops the outro before the bridge — corpus presence says outros (44%) are more expendable than bridges (67%) — refining ROADMAP §4's "(bridge first)" sketch (D11, ROADMAP amendment §10).

The fallback guarantees output for any `barBudget ≥ 4` (guaranteed in turn by F11): one canonical section, minimum 4 bars. A 30 s request at a pack's slowest tempo always produces a playable form.

### 7.4 Worked examples (normative golden fixtures)

Both chain from PHASE_2 §6.5's GenerationPlans (seed `1ps9wxb`, master 3735928559; both 4/4 ⇒ 1920 ticks/bar).

**Example 1 — pop_rock / happy** (A = +0.40, tempo 123, `maxLengthTicks` 177120 ⇒ budget **92 bars**):

Draw narrative (form stream): all three templates eligible (minBars 44/32/52; `chorus_first`'s arousal gate [0.15, 1.0] admits 0.40) → template draw picks **`verse_chorus_bridge`**; intro included, **4** bars; verse **8**; prechorus **excluded**; chorus **16**; bridge **8**; outro **excluded**. Fixed = 4+8+16 = 28; cycle = 8+16 = 24; count = (92−28)//24 = 2 (in [2,3]). Total **76 bars** = 145,920 ticks ≤ 177,120 ✓ (≈ 2:28 at 123 BPM).

| id | type | index/total | startBar | bars | phrases | harmonyTag | energy | label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| intro-1 | intro | 1/1 | 0 | 4 | a | intro | 0.340 | Intro |
| verse-1 | verse | 1/2 | 4 | 8 | a a | verse | 0.490 | Verse 1 |
| chorus-1 | chorus | 1/3 | 12 | 16 | a a a a | chorus | 0.790 | Chorus 1 |
| verse-2 | verse | 2/2 | 28 | 8 | a a | verse | 0.540 | Verse 2 |
| chorus-2 | chorus | 2/3 | 36 | 16 | a a a a | chorus | 0.840 | Chorus 2 |
| bridge-1 | bridge | 1/1 | 52 | 8 | a a | bridge | 0.440 | Bridge |
| chorus-3 | chorus | 3/3 | 60 | 16 | a a a a | chorus | 1.000 | Final Chorus |

`totalBars` 76; `templateId` "verse_chorus_bridge"; `ending {tagBars: 0, close: cold}` on **chorus-3** (the outro was excluded, so the directive attaches to the surviving final section). Energy checks: chorus-3 = 0.75 + 0.10 (R1) + 0.15 (R3) + 0.04 (arousal) → clamped 1.000; the I–V–C–V–C–B–C skeleton is the corpus plurality form.

**Example 2 — jazz / melancholic** (A = −0.45, tempo 69, `maxLengthTicks` 132480 ⇒ budget **69 bars**):

Draw narrative: one template (no draw). Intro include *feasible* (min config 44 ≤ 69) → 1:1 draw → **excluded**. Head bar options: 32 infeasible (32×3 + 4 = 100 > 69 — one head-in, min one solo, head-out, outro), 12 feasible → **forced 12, no draw** (the melancholic quartet plays a minor jazz blues — the feasibility filter, not a special case, makes the call). Solo inherits 12; second head shares the type resolution; outro single-option 4. Fixed = 12+12+4 = 28; count = (69−28)//12 = **3** solos. Total **64 bars** = 122,880 ticks ≤ 132,480 ✓ (≈ 3:43 at 69 BPM). One RNG draw consumed in total.

| id | type | index/total | startBar | bars | phrases | harmonyTag | energy | label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| head-1 | head | 1/2 | 0 | 12 | a b c | blues_12 | 0.464 | Head In |
| solo-1 | solo | 1/3 | 12 | 12 | a b c | blues_12 | 0.624 | Solo Chorus 1 |
| solo-2 | solo | 2/3 | 24 | 12 | a b c | blues_12 | 0.704 | Solo Chorus 2 |
| solo-3 | solo | 3/3 | 36 | 12 | a b c | blues_12 | 0.784 | Solo Chorus 3 |
| head-2 | head | 2/2 | 48 | 12 | a b c | blues_12 | 0.464 | Head Out |
| outro-1 | outro | 1/1 | 60 | 4 | a | outro | 0.344 | Outro |

`totalBars` 64; `templateId` "head_solos_head"; `ending {tagBars: 4, close: ritard}` on outro-1 (the whole 4-bar outro is the tag). Energy checks: solo-2 = 0.60 + 0.30×(2/3) = 0.80 → −0.045 → envelope 0.10 + 0.755×0.80 = **0.704**; the solos rise to a late peak and the head out returns to head-in level (Frieler; jam-session convention).

---

## 8. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Form model: templates with parameterized slots + repeat blocks** | Every researched product decomposes form as framing + repeatable body + per-slot options (BiaB intro/chorus×N/tag/ending, Yamaha section alphabet, JJazzLab parts, Soundraw blocks, Amper's two-level weighted tables); jazz's tempo-dependent chorus count and the 30–600 s range fall out of the repeat mechanism naturally. | Literal weighted form strings (template explosion across the length range; no principled jazz N); succession-grammar/Markov generation (corpus shows songs cluster on a few global spines — local transition realism ≠ believable global shape; constraint patching converges on a worse-specified template system). |
| D2 | **Vocabulary: 11 flat closed types** (starter six + postchorus, head, solo, main, breakdown) | One type = one meaning everywhere — the property that makes the §3.2 semantics table consumable by Phases 4/5/6; jazz/blues cyclic passes and loop-style sections genuinely behave unlike pop verse/chorus (harmony, energy shape, comping posture). | Stretching the starter six (semantics become per-style lies; downstream exception tables); role+label two-axis (loses verse-vs-chorus cadence semantics Phase 4 needs; meaning migrates into unvalidated labels). |
| D3 | **`forms.yaml` = section defs + template spines** (JJazzLab's split) | Each fact lives once; new templates are ~10 lines; two small schemas validate independently; mirrors the structure/occurrence split JJazzLab and Yamaha both converged on. | Self-contained templates (copy drift across templates); composable named blocks (third indirection level, over-engineering for 5 packs — repeat blocks already cover the one real reuse case). |
| D4 | **Selection: integer weights + eligibility gates (`arousal` band, auto `minBars`)** | Style tendencies as data (Amper's exact mechanism); arousal-banded gates respect PHASE_2 §7.1 (stages never see mood words); `minBars` gating means a 30 s request never draws an unfittable template. | Mood-name-keyed template lists (violates PHASE_2 §7.1); no gating with rejection sampling (unbounded draws break the append-only discipline). |
| D5 | **Fitting: arithmetic repeat counts → feasibility-constrained draws → authored degradation ladder → fallback; fill toward budget from below, respecting template caps** | Predictable and testable (each ladder rung is a golden case); repeat-by-division reproduces BiaB and the Aebersold tempo curve for free; nobody hears unused headroom, but everyone hears a mid-phrase cut — and every shipped product fits at bar/section granularity. Pop caps ≈ canonical length; loop/cyclic styles fill any budget. | Bounded exhaustive search with utilization scoring (opaque "why this form", new tuning surface); always-fill for pop/rock (five identical cycles is worse than a shorter canonical track; cap is pack data, Phase 8 can loosen). |
| D6 | **Endings are directives on the final section, not sub-4-bar sections** | Honors PHASE_1's pinned `lengthBars ≥ 4` without amendment; matches how tags/ritards actually work (they transform the last bars of existing material); the directive travels with whichever section survives fitting. | 2-bar ending sections (PHASE_1 amendment for one convention); no ending model (every shipped product reserves a musical close — cut endings are the #1 "sounds generated" tell). |
| D7 | **Energy: engine base table + positional rules + arousal modulation + pack envelope + slot overrides** | The anchor/formulas/overrides architecture PHASE_2 validated, applied to the second research-backed scalar; every finding lands in exactly one layer (escalation, final peak, solo arch, lo-fi flatness); overrides cover documented exceptions (withheld first chorus). | Fully pack-authored energies (5 packs × templates × slots of uncoordinated floats — the problem PHASE_2 D1 already rejected); fully computed with no override (fails the documented special cases). |
| D8 | **No cadence field in `SongForm`** | ROADMAP assigns cadence logic to Phase 4; every needed input (type, index, totalOfType, successor, ending) is already in the form; two stages must not share authority over one decision (PHASE_2 D5 precedent). | Phase 3 emitting per-boundary cadence directives (split ownership, ambiguity the contracts exist to prevent). |
| D9 | **Bar counts resolve once per section type** (inherit-targets share the resolution) | Verses are equal-length across cycles in 67% of the corpus; jazz head/solos *must* share one form (that's what "the form" means); halves the draw count and simplifies feasibility. Slot-level `bars:` override reserved for future per-occurrence deviations (§9 Q2). | Per-slot draws (can silently emit V1=8/V2=16 — the 10% case — and worse, head=32/solo=12, which is musical nonsense). |
| D10 | **No user-facing energy knob in v1** (resolves PHASE_2 Q4) | Arousal modulation + pack envelopes already modulate the curve; PHASE_2 D6 rejected an intensity scalar once for lack of research basis; the insertion point (a scalar folded into §6.3) is documented for post-v1 revisit with listening evidence. | Adding an `energy` param now (PHASE_2 params amendment on zero evidence). |
| D11 | **Reference ladder order: outro → intro-shrink → bridge → prechorus → …** | Corpus presence ranks expendability (outro 44% < prechorus 39%-when-present < bridge 67% < intro 86%); refines ROADMAP §4's illustrative "(bridge first)" (amended, §10). Ladder order stays pack data — styles may disagree. | Following the roadmap sketch literally (would cut the more-essential section first). |
| D12 | **4-bar grid: every bar option and fallback a multiple of 4, ≥ 4** | 71–89% of corpus section instances are exact 4-bar multiples; the grid is what phrase substructure, fills-every-4-bars (Phase 6), and pattern alignment (Phase 5) all assume. Odd lengths (9-bar chorus tags) deferred as authored spice (§9 Q2). | Free bar counts (pushes odd-length handling into every downstream stage for a ≤ 3% corpus phenomenon). |
| D13 | **Draws only when ≥ 2 feasible candidates** | Zero wasted RNG consumption; the draw sequence is fully determined by (pack, params, budget), keeping golden tests tight and the PHASE_2-style counting-RNG assertions meaningful. | Always drawing (consumes entropy on forced choices; every budget change would shift all downstream draws in the stream). |
| D14 | **No count-in** | A count-in is client UX (iReal Pro renders it client-side); embedding it would pollute `sections`/note data for every consumer. | Emitting a count-in section (violates the "sections are music" contract; breaks energy/validator assumptions). |

---

## 9. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | ~~Do the unexercised types/options survive contact with authoring?~~ **Resolved** (PHASE_8 §3.3/D2, 2026-07-07): `main`/`breakdown` and the 8/16-bar cyclic options are exercised by chill_lofi/blues/fusion and work; `postchorus` stays unexercised (future pop-adjacent pack); `variant` did **not** survive as load-bearing — label-only in v1, design reserved (PHASE_8 §12 Q2) | ~~Phase 8~~ | — |
| Q2 | Authored "spice" deviations: shortened verse 2 (23% of corpus), doubled final chorus (45%), 9-bar chorus tags — via slot-level `bars:` overrides? (PHASE_8 §3.8, 2026-07-07: **deferred post-v1** — with pop's empty `turnarounds`, PHASE_4 D6 keeps the deceptive rule inert, so a doubled chorus repeats identically; no payoff now) | Post-v1 | listening tests; D9's override hook |
| Q3 | Intra-section energy ramps (prechorus/buildup rising within the section) — v1 keeps sections flat per Nobile; EDM-style styles would want ramps | Phase 5/6 if a style needs it | whether prechorus builds read as static at render |
| Q4 | ~~More than one repeat block per template?~~ **Resolved** — not needed: lo-fi's ABAB…B shape fits one repeat block plus trailing slots (PHASE_8 §4.2/D2, 2026-07-07); F4's ≤ 1 rule stands | ~~Phase 8~~ | — |
| Q5 | Blues stop-time / featured choruses (a `variant` on `solo`?) (PHASE_8 §3.8, 2026-07-07: **deferred post-v1** — requires load-bearing `variant` selection, deliberately kept dormant; the PHASE_6 `stop` boundary device covers the adjacent need) | Post-v1 | load-bearing `variant` (PHASE_8 §12 Q2) |
| Q6 | Should section-length options be tempo-aware (16-bar sections at very fast tempos)? Currently only budget-aware. | Post-v1 listening | evidence that fast-tempo forms feel short-sectioned |

---

## 10. Amendments to earlier documents (this session)

All additive; applied in the same commit as this document:

1. **PHASE_1 §3.4**: section-type vocabulary note updated — full v1 vocabulary (11 types) now defined in PHASE_3 §3.
2. **PHASE_1 §4.2**: extension-points line annotated as pinned by PHASE_3 §4.
3. **PHASE_1 §7 Q4**: `forms.yaml` schema marked resolved (PHASE_3 §5); `progressions.yaml`/`timbres.yaml` remain with Phases 4/7.
4. **PHASE_2 §9 Q4**: resolved — no user-facing energy knob in v1 (PHASE_3 D10).
5. **ROADMAP §2 decisions log**: row added for the form model, vocabulary, and fitting policy.
6. **ROADMAP §4 Phase 3 bullet**: length-fitting sketch updated to the research-based degradation order (outro before bridge — D11).

---

## 11. Definition of done

Phase 3 is **built** when an implementation session demonstrates:

1. **Loader**: `forms.yaml` parsing into frozen pydantic models; all §5.1 validation rules F1–F13 implemented; one rejection fixture per rule class; the two reference files load clean.
2. **Energy data**: `src/trackgen/form/energy.yaml` with the §6.1 base table; a test asserting §6.1–§6.4 reproduce both worked examples' energy columns exactly (all 13 sections).
3. **Form stage**: implements §7.1 exactly; golden tests asserting both §7.4 SongForms **field-for-field** (ids, types, index/totalOfType, startBar/lengthBars, phrases, harmonyTags, energies, labels, ending placement, templateId, totalBars).
4. **Seed goldens**: the §7.2 form-stream RNG vectors asserted exactly.
5. **Determinism**: same plan → identical SongForm (repeated-run); a counting-RNG shim asserting the exact draw count for both worked examples (8 draws for example 1, 1 draw for example 2) and zero draws on the fallback path; draws-only-when-≥2-feasible verified by a budget-shift test.
6. **Property tests**: every pack × supported mood × `maxLengthSec ∈ {30, 45, 60, …, 600}` × 25 seeds → a SongForm that validates: sections contiguous from bar 0; every `lengthBars` a multiple of 4 and ≥ 4; `totalBars × ticksPerBar ≤ maxLengthTicks`; energies ∈ [0, 1] at 3 decimals; phrases sum to section length; `index`/`totalOfType` consistent; `ending` on exactly the final section; labels per §3.3.
7. **Ladder & fallback**: a fixture exercising each degrade op class; 30 s at each pack's `tempoRange.lo` produces a valid ≥ 4-bar form; an artificially tiny budget hits the fallback and still validates.
8. **Amendments** (§10) applied and consistent.

---

## 12. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §5: templates, weights, gates, ladder order, envelopes — all YAML; the engine's energy table is likewise data |
| 2. Rhythm separate from pitch | Untouched — this phase emits no notes; phrases/harmonyTags are structural references |
| 3. Hierarchical seeds | §7.2: single named `form` stream; append-only draws; rerolling `form` re-rolls structure without touching any other stage |
| 4. Soloist owns above ~C5 | No field this phase emits affects register; §3.2 arrangement semantics defer to ArrangementPlan lanes |
| 5. Deterministic pipeline | §7.1/§7.2: integer weights, ordered candidate lists, arithmetic fitting, draws only via `weighted_choice`, 3-decimal half-even rounding; entropy enters nowhere |
