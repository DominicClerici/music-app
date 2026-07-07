# PHASE_4 — Harmony Engine

Designed 2026-07-07 (session 4). Status: **awaiting approval**.

This document pins the Harmony engine — pipeline stage 3, `SongForm → HarmonicPlan` — end to end: the chord-token grammar and its resolution to `ChordSpec`, the `progressions.yaml` pack-file schema (resolving the progressions part of PHASE_1 Q4), the generator algorithm (pool selection, assembly, the three boundary transforms, dissonance dressing), the `HarmonicPlan` extension points PHASE_1 reserved for this phase, and the shared theory library (chord→pitches, voicing candidates, voice-leading minimization) every Phase 5 part generator builds against. It also resolves PHASE_1 Q6 (modulation representation, deferred) and PHASE_2 Q3 (`harmonicRhythmBase` semantics).

Research base (session 4): the de Clercq & Temperley rock-harmony corpus (exact chord and transition distributions from the RS 5×20 corpus), Hooktheory TheoryTab trends (75k songs), the McGill Billboard corpus, the iRb jazz corpus (Broze & Shanahan, 1,186 standards) and JazzHarmonyTreebank; canonical 12-bar-blues / rhythm-changes / turnaround / modal-vamp conventions; Rohrmeier's generative syntax of tonal harmony and Steedman's blues grammar; cadence and Markov-constraint literature (Pachet & Roy); dissonance-mapping systems (MetaCompose, AffectMachine-Classical/Pop, Wallis, Farbood) and empirical consonance work (Harrison & Pearce, Lahdelma & Eerola); the substitution-rule and chord-scale catalogs (Open Music Theory, Impro-Visor's vocabulary files); the harmony machinery of Band-in-a-Box, iReal Pro, JJazzLab, MMA, Yamaha/Korg arrangers, Hookpad, Scaler, ChordBot; Tymoczko's voice-leading geometry and Viterbi-voicing practice (Harrison's `voicer`); music21 Roman-numeral internals and documented issues (#1410, #1344, #197).

---

## 1. Scope

**In scope**

- The chord-token grammar for authored progressions and its deterministic resolution to `ChordSpec` (degree→pitch-class mapping, quality, spelling, function).
- The `progressions.yaml` pack-file schema — pools, turnarounds, finals — with validation rules and normative reference content for `pop_rock` and `jazz`.
- The Harmony generator algorithm: eligibility gating, one-draw-per-tag selection, phrase assembly, the three runtime boundary transforms (turnaround swap, deceptive substitution, final close), RNG discipline, and two normative worked examples chained from PHASE_2 §6.5 / PHASE_3 §7.4.
- The dissonance-dressing ladder: tier boundaries, function offsets, the dressing tables (engine data), and the extension-availability filter.
- Field-level pinning of the `HarmonicPlan` extension points PHASE_1 §4.3 reserved for this phase: `keys`, per-event `scale` / `function` / `tags`, `poolSelections`.
- The chord-scale hint table and the function-assignment table.
- The shared theory library: quality→interval tables, `resolve_token`, `chord_tones`/`guide_tones`, scale sets, voicing candidate generators, voice-leading distance, and the Viterbi voicing-path optimizer with integer costs.
- Resolution of PHASE_1 Q6 (modulation: deferred, representation reserved) and PHASE_2 Q3 (`harmonicRhythmBase`: soft selection filter).
- Amendments to earlier documents (all additive, §13).

**Explicitly not in scope**

- Any note emission. This phase produces chord *symbols with structure* (ChordSpecs); concrete pitches appear only in Phrases, produced by Phase 5 using this phase's theory library. The voicing utilities here return candidates and paths when *called*; nothing in the Harmony stage itself voices anything.
- Pattern selection, comping rhythms, bass lines (Phase 5); fills and boundary rendering of cadences/ritards (Phase 6); synthesis (Phase 7).
- Style-pack *content* beyond the two reference `progressions.yaml` files (Phase 8 authors chill_lofi/blues/fusion_jazz).
- Mid-song modulation (deferred post-v1 with its representation reserved — §7.1, D10).
- Harmonic variation between repeat instances of a section (deliberately none in v1 — D7).

---

## 2. Contracts consumed

| Upstream contract | What this phase does with it |
| --- | --- |
| `GenerationPlan.key` (PHASE_1 §4.1, PHASE_2 §6.3) | **Final** — never rewritten (PHASE_2 D5). `tonicPc` anchors degree resolution and spelling; `mode` gates pool-entry eligibility. |
| `GenerationPlan.budgets.dissonance` (PHASE_2 §7.2) | Drives the dressing ladder (§6) and optional entry eligibility bands. Arrives pack-scaled (pop 0.05–0.40, jazz 0.35–0.90), so one global ladder serves all styles — packs position themselves on it via `expressionRanges`. |
| `GenerationPlan.budgets.harmonicRhythmBase` (PHASE_2 §7.2) | Consumed as a **soft selection filter** (§5.2) — resolves PHASE_2 Q3 (D9). |
| `GenerationPlan.moodVector` (PHASE_2 §7.1) | `valence` gates entry eligibility bands (PHASE_3 arousal-gate precedent; AffectMachine: valence is the chord-color axis). `arousal` is **not consumed** — research says arousal must not touch chords. Mood words never visible. |
| `SongForm` (PHASE_1 §4.2, PHASE_3 §4) | `sections[].harmonyTag` keys the pools; `phrases` drive assembly (same label ⇒ same harmonic material — satisfied structurally, §4.1); `type` drives cadence validation classes; adjacent same-tag sections trigger turnarounds; `ending` on the final section triggers the final close. |
| Section semantics table (PHASE_3 §3.2, harmony column) | Implemented by §4/§5: intro/verse pools validated open, prechorus/bridge validated dominant-ending, head/solo authored closed with turnaround relaunch, chorus closes via the final-close transform on the last instance, outro obeys `ending`. |
| Seed system (PHASE_1 §5) | All draws from `random.Random(stream_seed(master, overrides, "harmony"))` via `weighted_choice`; integer weights; draws only when ≥ 2 candidates (PHASE_3 D13); append-only order (§5.5). |
| `HarmonicPlan` pinned core (PHASE_1 §4.3) | Produces `chords: [ChordEvent]` covering the song with no gaps/overlaps; `ChordSpec` produced exactly as pinned. Fills the extension points reserved for this phase (§7). |
| Pack structure (PHASE_1 §6) | `progressions.yaml` schema defined here (§4), resolving that part of Q4. The PHASE_3 §5.1 deferred cross-file check (every `harmonyTag` served by a pool) lands with this loader (P1). |
| Theory stack (PHASE_1 D2) | The `theory/` wrapper is built this phase. Resolution and voicing run on **owned tables** (documented music21 defects on altered-root sevenths and modal degrees — D12); music21 is retained for symbol parsing, spelling verification, and cross-validation tests. |
| Determinism rules (PHASE_1 §5.3) | Integer weights; ordered YAML candidate lists; integer-cost DP in the voicing optimizer (D16); 3-decimal rounding is n/a (no derived floats emitted). |

---

## 3. Chord tokens & resolution

### 3.1 Token grammar (pinned)

```
token    := degree quality? bass?
degree   := ("b" | "#")? numeral          numeral ∈ {I…VII, i…vii}
quality  := "7" | "maj7" | "6" | "ø7" | "°" | "°7" | "+" | "sus2" | "sus4" | "7sus4"
bass     := "/" ("b" | "#")? digit        digit ∈ 1–7
hold     := "~"                           (bar-level token: previous chord continues)
```

- **Case carries the triad third**: uppercase = major third, lowercase = minor third.
- **Degrees are major-scale-relative, mode-independent** (the de Clercq–Temperley / Hooktheory corpus convention): `I..VII → pc offsets 0 2 4 5 7 9 11` from `tonicPc`; `b` lowers, `#` raises by one semitone. Minor-key pools therefore write `i, iv, bVI, bVII, V7` and dorian pools `i, IV, bVII` — exactly as musicians notate them. `vii°` is the leading-tone diminished (pc 11) in every mode, `bVII` the subtonic (pc 10). No per-mode degree tables exist to disagree with each other.
- **Suffix → ChordSpec quality** (case shown is required; mismatches are validation errors):

| Token shape | quality | Token shape | quality |
| --- | --- | --- | --- |
| `X` | `maj` | `x` | `min` |
| `X7` | `dom7` | `x7` | `min7` |
| `Xmaj7` | `maj7` | `xmaj7` | `minMaj7` |
| `X6` | `maj6` | `x6` | `min6` |
| `xø7` (alias `xh7`) | `min7b5` | `x°` / `x°7` (alias `dim`/`dim7`) | `dim` / `dim7` |
| `X+` (alias `aug`) | `aug` | `Xsus2` / `Xsus4` / `X7sus4` | `sus2` / `sus4` / `dom7sus4` |

- **Bare tokens are dressable** (no suffix — the dissonance ladder may upgrade them, §6); **suffixed tokens are pinned** (dressing may add extensions at high tiers but never changes the core quality).
- **No secondary-dominant slash syntax** (`V7/ii`) in v1: absolute altered-degree tokens express the same chords (`VI7`, `III7`, `II7` are the rhythm-changes bridge) with simpler parsing and unambiguous provenance (D3; ergonomics revisited in Q8 §12).
- **No authored extensions** in v1 tokens — extensions come only from dressing (Q1 §12).
- `bass` resolves through the same degree map to `ChordSpec.bassPc`. Unexercised by the v1 reference packs (Q2 §12).
- **Within-bar timing**: a bar is a list of 1, 2, or 4 tokens splitting its beats evenly (4/4: whole, halves, quarters). Three tokens in 4/4 is a validation error. `~` as the sole token continues the previous chord for the whole bar; holds merge into the previous event *within one phrase instance* (phrase- and section-boundary events are never merged — a repeated phrase re-states its first chord as a new event).

### 3.2 Function assignment (pinned table)

Every resolved chord gets a function label from its degree (quality-independent; used by dressing offsets §6.2, cadence validation §4.3, the turnaround transform §5.4, and emitted on the event §7.2):

| Degree | 1 | b2 | 2 | b3 | 3 | 4 | #4 | 5 | b6 | 6 | b7 | 7 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Function | T | S | S | T | T | S | O | D | S | T | D | D |

Any other alteration → `O`. `bVII → D` encodes the rock/backdoor pre-tonic role the corpus documents (bVII→I is its most common transition); `bVI → S`, `bIII → T` follow the flat-side cluster's functional behavior.

### 3.3 Spelling & the `symbol` field (pinned)

`ChordSpec.symbol` is derived, never parsed (PHASE_1 §4.3). Deterministic rule set:

1. **Tonic name** from a fixed 12×2 table (major-class modes: major, mixolydian, lydian; minor-class: minor, dorian, phrygian) — chosen to minimize key-signature accidentals, ties broken conventionally:
   - major-class: `C Db D Eb E F F# G Ab A Bb B`
   - minor-class: `C C# D Eb E F F# G G# A Bb B`
2. **Chord-root letter** = tonic letter advanced `(degree − 1)` steps in the A–G cycle; **accidental** = `rootPc − pc(natural letter)` rendered as `b`/`#`/nothing (v1 content never exceeds one accidental).
3. **Quality string**: `maj→""`, `min→"m"`, `dom7→"7"`, `maj7→"maj7"`, `min7→"m7"`, `min7b5→"m7b5"`, `dim→"dim"`, `dim7→"dim7"`, `aug→"aug"`, `maj6→"6"`, `min6→"m6"`, `minMaj7→"mMaj7"`, `sus2/sus4/dom7sus4→"sus2"/"sus4"/"7sus4"`.
4. **Extension tidy-display**: `dom7+[9]→"9"`, `dom7+[13]→"13"`, `min7+[9]→"m9"`, `min7+[11]→"m11"`, `maj7+[9]→"maj9"`, `maj+[9]→"add9"`, `maj6+[9]→"6/9"`; otherwise base string + extensions in ladder order (`"A7b9b13"`). Slash bass appended as `"/"` + spelled bass note.

`ChordSpec.roman` echoes the **authored token** (or the transform's token) verbatim — provenance, like `SongForm.templateId`.

---

## 4. The `progressions.yaml` schema

Three top-level parts: `pools` (per-harmonyTag progression entries), `turnarounds` (loop-back relaunch bars), `finals` (song-close bars). All selection data is integer-weighted and ordered as authored.

### 4.1 Schema, field-level

```yaml
pools:
  <harmonyTag>:                # every tag forms.yaml references must appear
    - id: <str>                # unique within the pool
      weight: <int ≥ 1>
      modes: [<mode>, ...]     # required; entry eligible iff plan.key.mode ∈ modes
      valence: [min, max]      # optional gate on moodVector.valence  ∈ [−1, 1]
      dissonance: [min, max]   # optional gate on budgets.dissonance ∈ [0, 1]
      phrases:                 # one progression per phrase LABEL (PHASE_3 §4.1)
        <label>:               # ordered bars; each bar = list of 1|2|4 tokens, or [~]
          - [<token>, ...]

turnarounds:                   # may be empty (transform inert — pop_rock v1)
  - id / weight / modes / valence? / dissonance?   # as above
    bars: [ [<token>, ...], ... ]   # 1 or 2 bars; last chord D-function

finals:                        # REQUIRED, non-empty
  - id / weight / modes / valence? / dissonance?
    bars: [ [<token>, ...], ... ]   # 1 or 2 bars; last chord degree-1-rooted
```

The per-phrase-label unit makes *same label ⇒ same harmonic material* structural: the engine draws one entry per tag and instantiates `phrases[label]` for every phrase occurrence; a 16-bar verse (`a,a,a,a`) reuses one 4-bar progression, jazz `aaba_32` authors exactly `{a: 8 bars, b: 8 bars}` (D2).

### 4.2 Entry density (computed, not authored)

`density(entry) = totalTokens / totalBars` across all phrase labels (holds don't count). Used by the §5.2 soft filter. The loader computes and caches it.

### 4.3 Validation rules (loader; each class gets a rejection fixture)

- **P1** *(cross-file)* every `harmonyTag` used by any bar option in `forms.yaml` has a non-empty pool — this is the deferred check PHASE_3 §5.1 assigned to this loader. Unused pools are legal.
- **P2** entry `id`s unique per pool (and within `turnarounds`/`finals`); `weight` int ≥ 1; `modes` non-empty, ⊆ the engine mode vocabulary (PHASE_2 §6.3 ladder).
- **P3** `valence` bands within [−1, 1], `dissonance` within [0, 1], `lo ≤ hi`.
- **P4** *(cross-file)* for every bar option of every section type that uses tag `T` in `forms.yaml`, each entry in pool `T` provides exactly the phrase labels that option uses, each with the option's phrase length in bars.
- **P5** every bar has 1, 2, or 4 tokens (or is `[~]`); tokens parse per §3.1; case/suffix combinations legal; `~` never in a phrase's first bar (and never in `turnarounds`/`finals`).
- **P6** *(completeness, F13 pattern)* for every mode in the pack's `interpreter.yaml` `modes` menu and every pool (and `finals`): ≥ 1 entry listing that mode and carrying **no** valence/dissonance bands — selection can never come up empty.
- **P7** *(cadence classes, from PHASE_3 §3.2)* for each pool, by the section **types** its tag serves in `forms.yaml`: `prechorus`/`bridge` → every entry's final chord is D-function; `intro`/`verse` → every entry's final chord is **not** degree-1-rooted (open). Other types: unconstrained (pop loop choruses are loops — D5).
- **P8** `turnarounds`: 1–2 bars; final chord D-function.
- **P9** `finals`: non-empty; 1–2 bars; final chord rooted on degree 1.
- **P10** strict schema — unknown keys rejected (pydantic).

---

## 5. The Harmony generator

`harmony(plan, form, pack.progressions, rng) → HarmonicPlan`, with `rng = random.Random(stream_seed(master, overrides, "harmony"))`.

### 5.1 Algorithm (normative resolution order)

```
1. d = plan.budgets.dissonance;  baseTier = tier(d)          (§6.1)
   V = plan.moodVector.valence;  key = plan.key
2. tags = distinct harmonyTags of form.sections, in first-appearance order
3. for each tag:                                             # selection + dressing
     a. eligible = pool entries passing mode / valence / dissonance gates
     b. apply the density filter (§5.2)
     c. entry = weighted_choice(eligible, rng)               # draw iff ≥ 2
     d. dress the entry's chords (§6) in authored phrase order, bar order,
        token order, skipping holds                          # draw iff ≥ 2 options
4. assemble the timeline: per section in order, walk its phrases,
   instantiate the dressed label progressions; merge holds within a phrase
   instance; each event gets sectionId, startTick, durationTicks
5. TURNAROUND (§5.4): for each boundary where sections i, i+1 share a tag,
   in timeline order: find section i's terminal tonic run; eligible
   turnaround entries (gates + lengthBars ≤ run bars); if any:
   draw iff ≥ 2, dress its chords, replace the run's last lengthBars bars,
   tag events "turnaround"
   else if the section's last event is degree-1-rooted: DECEPTIVE — replace
   its chord with the fixed substitute (major-class modes: vi min7;
   minor-class: bVI maj), no draw, tag "deceptive"
6. FINAL CLOSE (§5.5): finals entry (gates; draw iff ≥ 2); dress its chords;
   replace the last lengthBars bars of the final section; tag events "final"
7. emit HarmonicPlan: keys = [{startTick: 0, tonicPc, mode}], chords,
   poolSelections (§7.3)
```

### 5.2 Density filter (resolves PHASE_2 Q3 — D9)

If `budgets.harmonicRhythmBase == 0.5`: restrict the eligible set to entries with `density ≤ 1.0` **iff that restriction is non-empty**; otherwise ignore it. If `== 1.0`: no restriction. Pool content keeps full authority over local harmonic rhythm (turnaround bars run 2 chords/bar in 1/bar songs; the rhythm-changes bridge halves the rate); the scalar is a mood-driven *selection preference*, never a rewrite. PHASE_2 §7.2's row is amended accordingly (§13).

### 5.3 Selection semantics

One draw per **distinct tag** per song — every section sharing a tag gets the same dressed progression (D4, D7): chorus-2 is chorus-1, jazz head and solos share the form (their `inherit` already shares one tag). Candidate order is authored YAML order; draws only when ≥ 2 candidates survive gating (PHASE_3 D13).

### 5.4 Turnaround transform

The jazz relaunch convention — *replace terminal tonic bars so the form cycles* — generalized:

- **Trigger**: section `i` and `i+1` have the same `harmonyTag`.
- **Terminal tonic run**: the maximal trailing sequence of section `i`'s events whose chord root is degree 1 and function T, measured in whole bars.
- **Eligible**: turnaround entries passing mode/valence/dissonance gates with `lengthBars ≤` the run's bars. None eligible (or empty run) → deceptive fallback (§5.1 step 5). Pop_rock ships an empty `turnarounds` list, so the transform is inert there and loop choruses stay untouched.
- Each boundary draws **independently** (per-event dressing too): consecutive solo choruses relaunch with different turnarounds, like a live rhythm section. The identical-repeats rule (D7) covers section *bodies*; boundaries are where controlled variety lives.
- The deceptive rule is **dormant in v1** — no v1 form produces a closing section followed by a same-tag repeat without an eligible turnaround (jazz always has one; pop has no same-tag adjacency). It exists, tested by synthetic fixture, for PHASE_3 Q2's doubled final choruses (Phase 8).

### 5.5 Final close

The song's final section (whichever survived PHASE_3 fitting — the `ending` directive travels with it) always closes on the tonic:

- Draw from `finals` (mode/bands gated; P9 guarantees candidates); dress; replace the final `lengthBars` bars of the final section.
- With `ending.tagBars > 0`, the replacement lands at the section's end — inside the tag phrase, which is where PHASE_3 §4.1 says this phase cadences. Phase 6 renders the `close` device (ritard/cold/fade) over it; `tagBars ∈ {4, 8} ≥ 2` so the replacement always fits.
- Replacement is unconditional (idempotent if the authored ending already matched — determinism over cleverness).

### 5.6 RNG discipline

- All draws via `weighted_choice` on the `harmony` stream, in the exact order of §5.1: per-tag `[entry, dressing…]` in tag first-appearance order → per-boundary `[entry, dressing…]` in timeline order → finals `[entry, dressing…]`. Append-only across versions (PHASE_2 §6.1 rule); ladder/table lookups and the deceptive rule are never drawn.
- Golden vectors (master `1ps9wxb` = 3735928559, extending PHASE_1 §5.6): `derive(M, "harmony") = 226146634901021418` (pinned there); `random.Random` on it: first five `getrandbits(32)` = `[1607822876, 501707672, 365345814, 982234362, 2945966636]`; first five `randrange(100)` from a fresh instance = `[47, 14, 10, 29, 87]`.

---

## 6. The dressing ladder

Maps `budgets.dissonance` to concrete chord color on the drawn progressions (D8). Engine-owned data (`src/trackgen/harmony/dressing.yaml`, loaded like `moods.yaml`; internal, recalibratable). Grounded in the AffectMachine finding (valence-axis → chord color; arousal never touches chords) and the empirical consonance ordering (Harrison & Pearce; Lahdelma & Eerola — mild extensions read as sophistication, not error).

### 6.1 Tiers

| Tier | Dissonance | Color ceiling |
| --- | --- | --- |
| 0 | < 0.15 | pure triads |
| 1 | 0.15–0.30 | sus / add9 / 6 |
| 2 | 0.30–0.45 | plain 7ths |
| 3 | 0.45–0.60 | 9ths |
| 4 | 0.60–0.75 | 11ths / 13ths |
| 5 | 0.75–0.90 | single-alteration dominants |
| 6 | ≥ 0.90 | altered dominants |

Because the scalar arrives pack-scaled, pop_rock (0.05–0.40) physically tops out at tier 2 and jazz (0.35–0.90) never falls below it — one ladder, style-correct color at both ends, no per-pack dressing data.

### 6.2 Function offsets

`effTier = clamp(baseTier + offset, 0, 6)` with offset **D: +1, T: −1, S/O: 0** — tension lives on the dominant, tonics stay coolest (standard practice; also what keeps a tier-4 jazz tonic from wearing the same color as its V7).

### 6.3 Dressing tables (normative)

Per chord **class** (from the parsed token) × effective tier → weighted options, drawn per chord slot (iff ≥ 2 options). Classes `dim`, `dim7`, `aug`, `sus*`, `maj6`, `min6`, `minMaj7`, `min7b5` are **passthrough** (never dressed) in v1.

**Bare major triad, function T/S:**

| eff | options (weight) |
| --- | --- |
| 0 | maj (3) |
| 1 | maj (2) · maj+[9] (1) · maj6 (1) |
| 2 | maj7 (2) · maj+[9] (1) |
| 3 | maj7+[9] (2) · maj7 (1) |
| 4–6 | maj7+[9] (2) · maj6+[9] (1) |

**Bare major triad, function D:**

| eff | options |
| --- | --- |
| 0 | maj (3) |
| 1 | maj (2) · dom7 (1) |
| 2 | dom7 (1) |
| 3 | dom7+[9] (2) · dom7 (1) |
| 4 | dom7+[13] (2) · dom7+[9] (1) |
| 5 | dom7+[b9] (2) · dom7+[b13] (1) |
| 6 | dom7+[b9,b13] (2) · dom7+[#9] (1) |

**Bare minor triad (any function):** 0: min · 1: min (2), min+[9] (1) · 2: min7 (2), min (1) · 3: min7+[9] (2), min7 (1) · 4–6: min7+[9] (2), min7+[11] (1).

**Pinned `dom7` (extensions only):** ≤2: none · 3: +[9] (2), none (1) · 4: +[13] (2), +[9] (1) · 5: +[b9] (2), +[b13] (1) · 6: +[b9,b13] (2), +[#9] (1).

**Pinned `maj7`:** ≤2: none · 3: +[9] (2), none (1) · 4–6: +[9] (1).

**Pinned `min7`:** ≤2: none · 3: +[9] (2), none (1) · 4–6: +[9] (2), +[11] (1).

### 6.4 Extension availability (hard filter, pinned)

The tables above are constructed inside these limits, and the document validator re-checks every emitted ChordSpec against them:

| Quality family | Legal extensions |
| --- | --- |
| maj, maj7 | 9, #11, 13 |
| maj6 | 9 |
| dom7, dom7sus4 | 9, b9, #9, #11, 13, b13 |
| min, min7, minMaj7 | 9, 11, 13 |
| min6 | 9 |
| min7b5 | 9, 11, b13 |
| dim, dim7, aug, sus2, sus4 | none (v1) |

(Natural 11 is an avoid tone over major/dominant qualities; b9 belongs to dominants — the Levine/OMT rules, machine-checkable.)

### 6.5 Dressing scope

Dressing runs **once per tag** on the drawn entry (D7) — all instances of a section share the identical dressed progression — plus once per drawn turnaround/finals entry at its own draw point (§5.1). Dressed results feed every part generator identically; per-performance color variation is Phase 5/6 territory.

---

## 7. `HarmonicPlan` extension points (now pinned)

The slots PHASE_1 §4.3 reserved for this phase, defined field-level. Changing these requires amending this document.

### 7.1 Plan-level: `keys` (resolves PHASE_1 Q6 — D10)

| Field | Type | Notes |
| --- | --- | --- |
| `keys` | `[{startTick: int, tonicPc: int 0–11, mode: str}]` | ordered by `startTick`, first at 0. **Exactly one entry in v1**, echoing `GenerationPlan.key`. Every ChordSpec resolves against the region containing its `startTick`. A future modulation transform appends a region and transposes later events — additive, no schema break. |

### 7.2 Per-`ChordEvent` fields (added to the pinned `{startTick, durationTicks, sectionId, chord}`)

| Field | Type | Notes |
| --- | --- | --- |
| `scale` | `{rootPc: int, name: str}` | required; the chord-scale hint (§7.4) Phase 5 uses for `tension`/`approach` degree resolution and walking-bass passing tones |
| `function` | `"T" \| "S" \| "D" \| "O"` | required; from the §3.2 table (secondary/altered → per its degree row) |
| `tags` | `[str]` | `[]` for plain authored events; vocabulary v1: `"turnaround"`, `"deceptive"`, `"final"`. Phase 6 reads these for boundary rendering (extension of the vocabulary needs an amendment here) |

### 7.3 Plan-level: `poolSelections` (provenance)

`{str: str}` — pool key → drawn entry id. Keys: each harmonyTag; `"turnaround:<sectionId>"` per boundary that swapped (the section whose tail was replaced); `"finals"`. Debugging + golden tests, same spirit as `templateId`.

### 7.4 Chord-scale hint table (pinned; Impro-Visor-derived)

Assigned per event from (quality, degree, extensions, mode). **Rows evaluate top-to-bottom within a quality family; first match wins** (alteration rows outrank degree rows, which outrank defaults):

| Chord | Scale (`name` on root) |
| --- | --- |
| maj / maj6 / maj7 on degree 1 | `ionian` (mode major); `mixolydian` when mode = mixolydian |
| maj-family on degree 4 | `lydian` |
| maj-family on b3 / b6 / b7 (borrowed majors) | `lydian` |
| maj-family on degree 5 | `mixolydian` |
| dom7 + #9 or b9,b13 | `altered` |
| dom7 + b9 | `half_whole_dim` |
| dom7 + b13 | `mixolydian_b13` |
| dom7 + #11 | `lydian_dominant` |
| dom7 on b6 / b7 (non-resolving: backdoor, blues bVI7) | `lydian_dominant` |
| dom7, otherwise (none/9/13 extensions) | `mixolydian` |
| min-family on degree 1, mode minor / dorian / phrygian | `aeolian` / `dorian` / `phrygian` (the mode itself) |
| min-family on degree 2 | `dorian` |
| min-family on degree 3 | `phrygian` |
| min-family on degree 4 | `dorian` |
| min-family on degree 6 | `aeolian` |
| min7b5 | `locrian_nat2` |
| dim / dim7 | `whole_half_dim` |
| sus2 / sus4 / dom7sus4 | `mixolydian` |
| minMaj7 | `melodic_minor` |
| aug | `whole_tone` |

Unlisted combinations fall back: maj-family → `ionian`, min-family → `dorian`, dom7 → `mixolydian`.

---

## 8. Theory utilities (the shared library)

Pure functions in `src/trackgen/theory/` (PHASE_1 §2); the algorithms and default tables below are pinned; Phase 5 owns *policy* (candidate classes per role, cost-weight tuning) and may extend candidate classes via amendment (D11).

### 8.1 Quality → interval stacks (pinned)

Semitone offsets from root:

```
maj 0 4 7      min 0 3 7      dim 0 3 6      aug 0 4 8
sus2 0 2 7     sus4 0 5 7     maj6 0 4 7 9   min6 0 3 7 9
dom7 0 4 7 10  maj7 0 4 7 11  min7 0 3 7 10  minMaj7 0 3 7 11
min7b5 0 3 6 10   dim7 0 3 6 9   dom7sus4 0 5 7 10
extensions: 9→14  b9→13  #9→15  11→17  #11→18  13→21  b13→20
```

### 8.2 Scale sets (pinned)

```
ionian 0 2 4 5 7 9 11        dorian 0 2 3 5 7 9 10      phrygian 0 1 3 5 7 8 10
lydian 0 2 4 6 7 9 11        mixolydian 0 2 4 5 7 9 10  aeolian 0 2 3 5 7 8 10
locrian_nat2 0 2 3 5 6 8 10  melodic_minor 0 2 3 5 7 9 11
lydian_dominant 0 2 4 6 7 9 10   mixolydian_b13 0 2 4 5 7 8 10
altered 0 1 3 4 6 8 10       half_whole_dim 0 1 3 4 6 7 9 10
whole_half_dim 0 2 3 5 6 8 9 11  whole_tone 0 2 4 6 8 10
```

### 8.3 Function surface (pinned signatures)

```
resolve_token(token: str, key: {tonicPc, mode}) -> ChordSpec    # §3 rules; symbol + roman included
chord_intervals(spec) -> [int]           # §8.1 stack + extensions, ascending
chord_tones(spec) -> [pc]                # root-ordered pitch classes
guide_tones(spec) -> {third: pc | None, seventh: pc | None}
scale_pcs(rootPc, name) -> [pc]          # §8.2
voicing_candidates(spec, cls, lane) -> [[midi]]      # §8.4; lane = {low, high}, hard ceiling
vl_distance(a: [midi], b: [midi], weights) -> int    # §8.5
optimal_voicing_path(specs: [ChordSpec], candidates_fn, weights) -> [[midi]]   # §8.6
```

### 8.4 Voicing candidate classes (pinned formulas)

All candidates enumerate every octave placement that fits the lane (`bottom ≥ lane.low`, `top ≤ lane.high` — the C5 ceiling is structural: non-drum lanes have `high ≤ 71`); generation order (class formula order, then ascending octave) is the deterministic tie-break order.

| Class | Formula |
| --- | --- |
| `shell2` | {3rd, 7th} (guide tones; triads: {3rd, 5th}) |
| `shell3` | {root, 3rd, 7th} (Freddie Green; triads: root position close) |
| `rootless_a` | 3–5–7–9 stack (Bill Evans A; 9 from extensions else omitted → 3-5-7) |
| `rootless_b` | 7–9–3–5 stack (B form) |
| `drop2` | close 4-note stack (root pos + 3 inversions), 2nd-from-top dropped an octave |
| `triad_close` | triad, root position + 2 inversions |
| `triad_open` | `triad_close` with the middle voice dropped an octave |
| `quartal` | three stacked 4ths from the scale (§7.4) starting on a chord tone (pads) |
| `fifths` | {root, root+7, root+12} — 3rd-omitted pad stack (added by PHASE_5 §6.5, 2026-07-07, resolving part of Q9) |

### 8.5 Voice-leading distance (pinned; integer)

Voicings compared ascending-sorted, equal cardinality (pad/truncate policy is the caller's — Phase 5's callers pad the shorter voicing with its own top pitch, PHASE_5 §6.4, 2026-07-07). With integer weights `w`:

```
vl_distance(a, b, w) = w.move · Σᵢ |aᵢ − bᵢ|          # L1 taxicab (Tymoczko)
                     + w.top  · |a_top − b_top|        # top voice is most audible
                     − w.common · |{pitches in both}|  # common-tone retention reward
```

### 8.6 Voicing-path optimizer (pinned; Viterbi DP, integer costs)

```
cost(path) = Σₜ vl_distance(vₜ₋₁, vₜ, w) + Σₜ w.drift · |top(vₜ) − anchor|
best[t][j] = emit(cₜⱼ) + min_i (best[t−1][i] + trans(cₜ₋₁ᵢ, cₜⱼ))
```

`anchor` = the lane's register anchor (default: lane midpoint) — the drift term is what stops pure smoothness minimization from marching voicings downward (documented failure mode). All terms are semitone counts × integer weights → **pure integer DP**, no float comparisons (PHASE_1 §5.3 spirit; D16). Ties break to the lowest candidate index. Complexity O(N·K²), trivial at our scale. **Default weights (pinned):** `move 4, top 4, common 3, drift 1`. Phase 5 passes its own per-role weights; defaults are the tested reference.

### 8.7 music21 boundary (D12)

Runtime resolution/voicing never calls music21 — the owned tables above are authoritative (documented music21 defects: altered-root sevenths forced dominant (#1410), secondary-numeral key mutation (#1344), no mode-native degree model). music21 (exact version pinned in the lockfile) is used for: parsing externally supplied chord symbols (future), spelling cross-checks, and a test-suite cross-validation pass comparing `chord_tones` against `harmony.ChordSymbol` on the non-defective subset.

---

## 9. Reference content (normative)

Both files are normative as schema fixtures and golden-test data; *content* is reference-quality, refined in Phase 8. Weights encode the corpus statistics (§ research: RS-corpus chord/transition distributions, Hooktheory loop rankings, canonical blues/AABA changes).

### 9.1 `styles/pop_rock/progressions.yaml`

```yaml
pools:
  intro:
    - { id: tonic_vamp,       weight: 60, modes: [major],
        phrases: { a: [[I], [IV], [I], [IV]] } }
    - { id: axis_intro,       weight: 40, modes: [major],
        phrases: { a: [[I], [V], [vi], [IV]] } }
    - { id: minor_vamp,       weight: 60, modes: [minor],
        phrases: { a: [[i], [bVI], [i], [bVII]] } }
    - { id: minor_axis_intro, weight: 40, modes: [minor],
        phrases: { a: [[i], [bVI], [bIII], [bVII]] } }
  verse:
    - { id: anchor,           weight: 40, modes: [major],
        phrases: { a: [[I], [IV], [I], [V]] } }
    - { id: axis_verse,       weight: 30, modes: [major],
        phrases: { a: [[I], [V], [vi], [IV]] } }
    - { id: mixo_rock,        weight: 20, modes: [major], valence: [-1.0, 0.5],
        phrases: { a: [[I], [bVII], [IV], [IV]] } }
    - { id: doo_wop,          weight: 10, modes: [major], valence: [0.2, 1.0],
        phrases: { a: [[I], [vi], [IV], [V]] } }
    - { id: minor_anchor,     weight: 40, modes: [minor],
        phrases: { a: [[i], [bVII], [bVI], [bVII]] } }
    - { id: minor_axis_verse, weight: 30, modes: [minor],
        phrases: { a: [[i], [bVI], [bIII], [bVII]] } }
  prechorus:
    - { id: four_five,     weight: 50, modes: [major],
        phrases: { a: [[IV], [V], [IV], [V]] } }
    - { id: lift,          weight: 30, modes: [major],
        phrases: { a: [[vi], [IV], [V], [V]] } }
    - { id: two_five_pop,  weight: 20, modes: [major],
        phrases: { a: [[ii], [IV], [V], [V]] } }
    - { id: minor_lift,    weight: 50, modes: [minor],
        phrases: { a: [[iv], [bVI], [V], [V]] } }
    - { id: minor_shuttle, weight: 50, modes: [minor],
        phrases: { a: [[iv], [V], [iv], [V]] } }
  chorus:
    - { id: axis,          weight: 45, modes: [major],
        phrases: { a: [[I], [V], [vi], [IV]] } }
    - { id: axis_rotation, weight: 20, modes: [major],
        phrases: { a: [[vi], [IV], [I], [V]] } }
    - { id: four_lift,     weight: 15, modes: [major],
        phrases: { a: [[I], [IV], [vi], [V]] } }
    - { id: fifties,       weight: 10, modes: [major], valence: [0.2, 1.0],
        phrases: { a: [[I], [vi], [IV], [V]] } }
    - { id: plagal_rock,   weight: 10, modes: [major],
        phrases: { a: [[I], [bVII], [IV], [I]] } }
    - { id: minor_axis,    weight: 60, modes: [minor],
        phrases: { a: [[i], [bVI], [bIII], [bVII]] } }
    - { id: andalusian,    weight: 20, modes: [minor], valence: [-1.0, 0.0],
        phrases: { a: [[i], [bVII], [bVI], [V]] } }
    - { id: minor_climb,   weight: 20, modes: [minor],
        phrases: { a: [[i], [iv], [bVI], [bVII]] } }
  bridge:
    - { id: depart_six,       weight: 40, modes: [major],
        phrases: { a: [[vi], [IV], [I], [V]] } }
    - { id: subdominant_turn, weight: 35, modes: [major],
        phrases: { a: [[IV], [I], [ii], [V]] } }
    - { id: flat_lift,        weight: 25, modes: [major], valence: [-1.0, 0.5],
        phrases: { a: [[bVI], [bVII], [I], [V]] } }
    - { id: minor_depart,     weight: 60, modes: [minor],
        phrases: { a: [[bVI], [iv], [i], [V]] } }
    - { id: minor_flat_walk,  weight: 40, modes: [minor],
        phrases: { a: [[bVI], [bVII], [i], [V]] } }
  outro:
    - { id: plagal_tag, weight: 60, modes: [major],
        phrases: { a: [[I], [IV], [I], [IV]] } }
    - { id: axis_out,   weight: 40, modes: [major],
        phrases: { a: [[I], [V], [vi], [IV]] } }
    - { id: minor_tag,  weight: 100, modes: [minor],
        phrases: { a: [[i], [bVI], [i], [bVI]] } }

turnarounds: []        # pop loops don't relaunch through turnarounds (v1)

finals:
  - { id: authentic,       weight: 50, modes: [major], bars: [[V],  [I]] }
  - { id: plagal,          weight: 50, modes: [major], bars: [[IV], [I]] }
  - { id: minor_authentic, weight: 60, modes: [minor], bars: [[V],  [i]] }
  - { id: minor_plagal,    weight: 40, modes: [minor], bars: [[iv], [i]] }
```

(Corpus anchoring: `axis` and its rotation lead the chorus pool per Hooktheory's rankings; `plagal_rock`/`mixo_rock` carry the bVII that is 8.1% of all rock harmony; iii and vii° appear nowhere — 1.9%/0.4% in the corpus; the 50/50 major finals split encodes rock's plagal/authentic parity, where IV→I actually outnumbers V→I.)

### 9.2 `styles/jazz/progressions.yaml`

```yaml
pools:
  intro:
    - { id: two_five_vamp,       weight: 60, modes: [major, mixolydian],
        phrases: { a: [[ii7], [V7], [ii7], [V7]] } }
    - { id: turnaround_in,       weight: 40, modes: [major, mixolydian],
        phrases: { a: [[Imaj7], [VI7], [ii7], [V7]] } }
    - { id: minor_two_five_vamp, weight: 60, modes: [minor, dorian],
        phrases: { a: [[iiø7], [V7], [iiø7], [V7]] } }
    - { id: minor_vamp,          weight: 40, modes: [minor, dorian],
        phrases: { a: [[i7], [bVI7], [i7], [V7]] } }
  aaba_32:
    - id: rhythm_a
      weight: 100
      modes: [major, mixolydian]   # mixolydian coverage required by P6 (user-forced mode)
      phrases:
        a: [[Imaj7, vi7], [ii7, V7], [Imaj7, vi7], [ii7, V7],
            [Imaj7, I7], [IVmaj7, iv7], [Imaj7, V7], [Imaj7]]
        b: [[III7], [~], [VI7], [~], [II7], [~], [V7], [~]]
    - id: minor_aaba
      weight: 100
      modes: [minor, dorian]
      phrases:
        a: [[i7], [iv7], [i7], [~], [iiø7], [V7], [i7], [~]]
        b: [[iv7], [~], [i7], [~], [iiø7], [V7], [i7], [V7]]
  blues_12:
    - id: jazz_blues
      weight: 60
      modes: [major, mixolydian]
      phrases:
        a: [[I7], [IV7], [I7], [~]]
        b: [[IV7], [#iv°7], [I7], [VI7]]
        c: [[ii7], [V7], [I7], [~]]
    - id: basic_blues
      weight: 40
      modes: [major, mixolydian]
      phrases:
        a: [[I7], [~], [~], [~]]
        b: [[IV7], [~], [I7], [~]]
        c: [[V7], [IV7], [I7], [~]]
    - id: minor_quick
      weight: 60
      modes: [minor, dorian]
      phrases:
        a: [[i7], [iv7], [i7], [~]]
        b: [[iv7], [~], [i7], [~]]
        c: [[bVI7], [V7], [i7], [~]]
    - id: minor_basic
      weight: 40
      modes: [minor, dorian]
      phrases:
        a: [[i7], [~], [~], [~]]
        b: [[iv7], [~], [i7], [~]]
        c: [[bVI7], [V7], [i7], [~]]
  outro:
    - { id: final_two_five, weight: 100, modes: [major, mixolydian],
        phrases: { a: [[iii7], [VI7], [ii7], [V7]] } }
    - { id: minor_outro,    weight: 100, modes: [minor, dorian],
        phrases: { a: [[i7], [iv7], [i7], [~]] } }

turnarounds:
  - { id: one_six_two_five,     weight: 40, modes: [major, mixolydian],
      bars: [[Imaj7, VI7], [ii7, V7]] }
  - { id: three_six_two_five,   weight: 25, modes: [major, mixolydian],
      bars: [[iii7, VI7], [ii7, V7]] }
  - { id: quick_two_five,       weight: 20, modes: [major, mixolydian],
      bars: [[ii7, V7]] }                                    # 1 bar — fits AABA's 1-bar tonic run
  - { id: tritone_turn,         weight: 15, modes: [major, mixolydian], dissonance: [0.55, 1.0],
      bars: [[Imaj7, bIII7], [ii7, bII7]] }
  - { id: minor_turn,           weight: 50, modes: [minor, dorian],
      bars: [[i7, bVI7], [iiø7, V7]] }
  - { id: minor_two_five,       weight: 30, modes: [minor, dorian],
      bars: [[i7], [iiø7, V7]] }
  - { id: minor_quick_two_five, weight: 20, modes: [minor, dorian],
      bars: [[iiø7, V7]] }                                   # 1 bar

finals:
  - { id: two_five_close,     weight: 60, modes: [major, mixolydian],
      bars: [[ii7, V7], [Imaj7]] }
  - { id: backdoor_close,     weight: 40, modes: [major, mixolydian],
      bars: [[iv7, bVII7], [Imaj7]] }
  - { id: minor_close,        weight: 60, modes: [minor, dorian],
      bars: [[iiø7, V7], [i7]] }
  - { id: minor_plagal_close, weight: 40, modes: [minor, dorian],
      bars: [[iv7], [i7]] }
```

(Anchoring: `jazz_blues` is the bebop-standard grid — quick-change bar 2, #iv°7 bar 6, VI7 bar 8, ii–V bars 9–10, authored **closed** in 11–12 so the turnaround transform relaunches it, exactly the convention; `rhythm_a` is the rhythm-changes A + Sears-Roebuck dominant-cycle bridge with its halved harmonic rhythm; `bVI7–V7` is the defining minor-blues cadence; the backdoor final is the iv–bVII7–I formula; the tritone turnaround is dissonance-gated per the style-gating consensus.)

---

## 10. Worked examples (normative golden fixtures)

Both chain from PHASE_2 §6.5's GenerationPlans and PHASE_3 §7.4's SongForms (seed `1ps9wxb`, master 3735928559; harmony stream seed 226146634901021418; 4/4, 1920 ticks/bar). Every draw below is computed, not illustrative.

### 10.1 Example 1 — pop_rock / happy

Key E major (tonicPc 4). dissonance 0.132 → **tier 0**; D-function chords dress at tier 1; valence +0.75; harmonicRhythmBase 1.0 (filter inert). Form: intro-1(4) · verse-1(8) · chorus-1(16) · verse-2(8) · chorus-2(16) · bridge-1(8) · chorus-3(16), `ending {tagBars: 0, close: cold}` on chorus-3. Tags in first-appearance order: intro, verse, chorus, bridge. No same-tag boundaries; pop turnarounds empty → both boundary transforms inert; final close fires on chorus-3.

Draw narrative (**8 draws total**): intro → **tonic_vamp** (over axis_intro); verse → **anchor** (mixo_rock excluded by valence gate: 0.75 ∉ [−1, 0.5]; candidates anchor/axis_verse/doo_wop); verse's V dresses **maj** (stays triad); chorus → **axis**; chorus's V dresses **dom7**; bridge → **depart_six** (flat_lift valence-excluded); bridge's V dresses **maj**; finals → **plagal**.

| Section | Bars | Chords (per 4-bar phrase) |
| --- | --- | --- |
| intro-1 | 0–4 | E · A · E · A |
| verse-1, verse-2 | 4–12, 28–36 | (E · A · E · B) × 2 |
| chorus-1, chorus-2 | 12–28, 36–52 | (E · B7 · C♯m · A) × 4 |
| bridge-1 | 52–60 | (C♯m · A · E · B) × 2 |
| chorus-3 | 60–76 | (E · B7 · C♯m · A) × 3, then E · B7 · **A · E** |

The finals entry `plagal` replaces chorus-3's bars 75–76 (`tags: ["final"]` on both events): the song closes IV→I — the corpus-dominant rock cadence. 76 events, all 1 bar (1920 ticks); no holds. Scales: E `ionian`, A `lydian`, B/B7 `mixolydian`, C♯m `aeolian`. Functions: E=T, A=S, B/B7=D, C♯m=T. `poolSelections`: `{intro: tonic_vamp, verse: anchor, chorus: axis, bridge: depart_six, finals: plagal}`. Verse V stayed a triad while chorus V drew B7 — same seed, per-slot color.

Sample event (chorus-1, bar 13):

```jsonc
{ "startTick": 24960, "durationTicks": 1920, "sectionId": "chorus-1",
  "chord": { "rootPc": 11, "quality": "dom7", "extensions": [],
             "symbol": "B7", "roman": "V" },
  "scale": { "rootPc": 11, "name": "mixolydian" }, "function": "D", "tags": [] }
```

### 10.2 Example 2 — jazz / melancholic

Key D minor (tonicPc 2). dissonance 0.653 → **tier 4** (T-function chords → 3, D → 5); valence −0.5; harmonicRhythmBase 0.5 → density filter active: minor_quick 0.667, minor_basic 0.5 chords/bar — both ≤ 1.0, both stay. Form: head-1(12) · solo-1..3(12 each) · head-2(12) · outro-1(4), `ending {tagBars: 4, close: ritard}` on outro-1. Tags: blues_12, outro. Same-tag boundaries: head-1→solo-1, solo-1→solo-2, solo-2→solo-3, solo-3→head-2 (4 turnaround events; head-2→outro-1 differs → head out stays closed). Final close fires on outro-1.

Draw narrative (**30 draws total**): blues_12 → **minor_quick**; its 8 chord slots dress **Dm9 · Gm9 · Dm9 · Gm11 · Dm9 · B♭13 · A7♭9 · Dm9**; outro → **minor_outro** (single candidate, no draw), dresses **Dm9 · Gm11 · Dm9**; turnarounds draw **minor_turn** (Dm7, B♭9, Eø7, A7♭13), **minor_two_five** (Dm9, Eø7, A7♭9), **minor_turn** (Dm7, B♭13, Eø7, A7♭13), **minor_turn** (Dm7, B♭13, Eø7, A7♭13); finals → **minor_close**, dressing **Eø7 · A7♭13 · Dm7**.

The dressed 12-bar form (all head/solo instances share it; turnaround bars 11–12 vary per boundary):

| Bar | 1 | 2 | 3–4 | 5–6 | 7–8 | 9 | 10 | 11–12 (closed) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Chord | Dm9 | Gm9 | Dm9 | Gm11 | Dm9 | B♭13 | A7♭9 | Dm9 |

| Section | Bars 11–12 become | Source |
| --- | --- | --- |
| head-1 | Dm7 B♭9 · Eø7 A7♭13 | turnaround:head-1 = minor_turn |
| solo-1 | Dm9 · Eø7 A7♭9 | turnaround:solo-1 = minor_two_five |
| solo-2 | Dm7 B♭13 · Eø7 A7♭13 | turnaround:solo-2 = minor_turn |
| solo-3 | Dm7 B♭13 · Eø7 A7♭13 | turnaround:solo-3 = minor_turn |
| head-2 | Dm9 (closed — head out resolves) | — |

Outro-1 (bars 60–64; the whole section is the tag): **Dm9 · Gm11 · Eø7 A7♭13 · Dm7** — finals `minor_close` replaced bars 3–4 (`tags: ["final"]`); Phase 6 ritards over it. Scales: Dm9/Dm7 `aeolian`, Gm9/Gm11 `dorian`, B♭13/B♭9 `lydian_dominant`, A7♭9 `half_whole_dim`, A7♭13 `mixolydian_b13`, Eø7 `locrian_nat2`. `poolSelections`: `{blues_12: minor_quick, outro: minor_outro, "turnaround:head-1": minor_turn, "turnaround:solo-1": minor_two_five, "turnaround:solo-2": minor_turn, "turnaround:solo-3": minor_turn, finals: minor_close}`.

Semantics-table compliance is visible: the same melancholic quartet PHASE_3 fitted now plays a D-minor jazz blues with quick change, a rising-color turnaround relaunch under each solo handoff, a resolved head out, and a ii–V close under the ritard tag.

---

## 11. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Architecture: authored pools + a closed set of bounded transforms** (cadence/turnaround/deceptive/final-close + dressing), no open-ended generation | The shipping consensus (BiaB Melodist genre databases, ChordBot templates, Yamaha/Casio preset banks) is pool-based with rule layers; raw grammar/Markov generation has documented phrase-goal failure modes; every transform here is a table-driven rewrite — testable, seedable | Pools-only with per-context variants (authoring cost multiplies across contexts × tiers × styles); T/S/D grammar generation (believability and golden-testing costs, no shipping precedent as primary path) |
| D2 | **Pool entries are per-phrase-label progressions** | Makes PHASE_3's *same label ⇒ same material* structurally unviolable; one 4-bar draw serves 8- and 16-bar verses; jazz AABA authors exactly its A and B; loader cross-checks labels/lengths against `forms.yaml` | Whole-section bar lists (per-bar-count entry duplication, contract by validation only); free-length tiled loops (can't express AABA/blues where the progression *is* the form) |
| D3 | **Token grammar: case + suffix Roman numerals; major-scale-relative degrees; bare = dressable, suffixed = pinned; no secondary-slash syntax; no authored extensions; even beat splits; `~` holds** | Matches how the corpora and musicians notate (de Clercq–Temperley, Hooktheory); mode-independent degree map kills the classical minor-VI/VII ambiguity (and music21's Minor67 mess) outright; pin-vs-dress gives the ladder a clean contract; III7–VI7–II7–V7 covers secondary dominants without parser complexity | Always-explicit quality (dissonance dimension pushed into authoring); computed-quality bare degrees (can't pin blues I7/jazz Imaj7); per-mode diatonic degree maps (bVI/bVII would mean different pcs per mode — author trap); `V7/x` syntax (zero v1 need) |
| D4 | **Selection: required `modes` gate + optional valence/dissonance bands; one draw per harmonyTag per song** | Mode gating is semantic necessity; bands follow PHASE_3's arousal-gate precedent and AffectMachine's valence-as-chord-color; one draw per tag makes repeats identical (recognizability) and jazz head/solo share the form by construction | Fresh draw per section instance (breaks repeat-recognition; head/solo would need a special case); mood-word tags on entries (violates PHASE_2 §7.1); mode-only gating (loses bright/dark choice within a mode) |
| D5 | **Cadence logic: loader validates authoring (prechorus/bridge end D-function; intro/verse end open); runtime rewrites only turnaround/deceptive/final-close boundary events** | Pool authors naturally write their tag's cadence; loop-based pop choruses must not be rewritten to end on I (corpus: IV→I plagal loops outrank V→I; the "arrival" is the next downbeat); runtime transforms cover exactly what authoring can't know (which section survives fitting, loop-backs, repeats) — the BiaB shape (body as authored, ending machine-placed) | Full runtime cadence-rewrite table per boundary (fights authored hooks, duplicates authoring, large golden surface); per-entry authored ending variants (2–3× authoring cost to reproduce what transforms compute) |
| D6 | **Turnaround transform: on same-tag boundaries, replace the terminal tonic run (trailing degree-1/T events, whole bars) with a drawn turnaround entry of fitting length; per-boundary draws; deceptive (vi min7 / bVI maj, fixed) as fallback; both inert when the pack ships no turnarounds** | Exactly the jazz convention ("replace terminal tonic bars to relaunch the form"); authoring pools *closed* + swapping at loop-backs covers iReal's 1st/2nd-ending reality generatively; run-length eligibility keeps 2-bar turnarounds out of 1-bar tonic tails (AABA gets a 1-bar ii–V entry); per-boundary draws give live-band relaunch variety without touching section bodies | Authoring open (turnaround baked in) + close-on-final-only (head out would loop-end; every consumer of "the form ends on I" breaks); one turnaround drawn per song (mechanical repetition at every relaunch) |
| D7 | **Identical repeats in v1: dressing runs once per tag; no substitution pass between instances** | Corpus reality — harmony is the most-repeated layer; a re-drawn chord quality in verse-2 changes bass+comping+pads together (audible "wrong"); anti-repetition is Phases 5/6's assignment (patterns, comping, fills); BiaB's auto-substitution is user-invoked, not default | Seeded substitution pass on later instances (hook damage risk, big rule+test surface); final-instance escalation (duplicates Phase 5 intensity + PHASE_3 R3 energy peak) |
| D8 | **Dressing: 7-tier global ladder × function offsets (D+1/T−1) × per-class weighted option tables, drawn per chord slot; extension-availability hard filter** | AffectMachine's validated valence→dissonance channel; empirical tension ordering (triads < 7ths < 9ths < 11/13 < altered); pack `expressionRanges` position styles on ONE ladder (pop tops at tier 2 = triadic rock, jazz floors there — zero per-pack dressing data); per-slot draws avoid every-V-identical color; function offsets put tension on the dominant | Deterministic tier lookup (uniform mechanical color); dressing-gates-substitutions-only (mood→color channel unused; pop pools would need authored 7th variants); per-pack dressing tables (authoring burden, no identified need — Q3) |
| D9 | **`harmonicRhythmBase` = soft density filter** (base 0.5 restricts to computed density ≤ 1.0 when non-empty; base 1.0 inert) — resolves PHASE_2 Q3 | Real harmonic rhythm lives in pool content (turnaround bars, halved bridges); the scalar keeps its mood signal (calm/dreamy → slower changes) as a preference that can never fail or rewrite; density computed by the loader — zero authoring burden | Dropping the field (loses a real, cheap mood signal); hard eligibility gate (per-tag × density pack-completeness rules — brittle) |
| D10 | **Modulation deferred; `HarmonicPlan.keys` list reserved** (one region at tick 0 in v1) — resolves PHASE_1 Q6 | No corpus prevalence data for the pop key-lift; implementation is a mechanical tail-transpose + optional pivot chord, purely additive once key regions are first-class; spending v1 effort on a dated trope fails the believability-first rule | Shipping the truck-driver lift now (new transform + golden surface, interacts with unbuilt Phase 5 retargeting); no schema reservation (future modulation becomes a breaking change) |
| D11 | **Theory library pinned in full: interval/scale tables, `resolve_token`, voicing candidate classes, integer `vl_distance`, Viterbi `optimal_voicing_path` with parameterized weights (pinned defaults)** | ROADMAP assigns exactly this list to Phase 4; DP-over-candidates is the published correct method (per-pair greedy provably drifts); Phase 5 — already the largest phase — gets algorithms and tunes policy (classes, weights) instead of reimplementing | Primitives only (dumps the hardest algorithm on Phase 5); fixed cost constants (comping vs pads genuinely need different trade-offs — immediate amendment bait) |
| D12 | **Owned resolution/voicing tables; music21 demoted to parse/spell/cross-validation** | music21's RomanNumeral forces altered-root sevenths to dominant quality (#1410), corrupts pitches on key mutation with secondaries (#1344), and has no mode-native degree model — disqualifying for the runtime path; owned tables are ~40 lines of pinned data and fully golden-testable; PHASE_1 D2's wrapper contract is unchanged (pure functions in, ints out) | Routing runtime through RomanNumeral with workarounds (fighting documented defects at the core of the engine); dropping music21 entirely (loses symbol parsing + independent verification) |
| D13 | **`finals` pool required; final close unconditionally replaces the final bars** | Cut/unclosed endings are the #1 "sounds generated" tell (PHASE_3 D6 rationale, extended); unconditional replacement is deterministic and idempotent when authoring already matched; mode-gated finals encode the corpus split (authentic vs plagal 50/50 in rock; ii–V vs backdoor in jazz) | Close-only-if-open heuristics (fragile chord-equality edge cases); fixed engine cadence (style identity lost — jazz backdoor, rock plagal) |
| D14 | **Chord-scale hint pinned on every event, from an Impro-Visor-derived table** | Phase 5's `tension`/`approach` degrees and walking bass need scales; Impro-Visor's vocabulary is the open, established mapping (ii→dorian, V7alt→altered, ø7→locrian ♮2…); computing it here once keeps every part generator consistent | Phase 5 computes per-role (divergent scales across roles on one chord); no hint (Phase 5 reinvents chord-scale theory) |
| D15 | **Spelling: fixed tonic-name tables + degree-letter arithmetic** | Roman provenance makes correct spelling nearly free (root letter from degree, accidental from the pc delta) — no global speller; deterministic; produces "B♭7 in D minor", never "A♯7" | Line-of-fifths optimization (needed only for provenance-less input we don't have); music21 spelling (drags the score model into the runtime path) |
| D16 | **Integer-cost voicing DP** (semitone counts × integer weights; lowest-index tie-break) | Extends PHASE_1 §5.3's integer-weights rule to deterministic optimization: no float comparisons anywhere in selection or search; cross-platform bit-identical | Float costs (ulp-sensitive ties); rational arithmetic (needless machinery) |

---

## 12. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | Authored extensions in tokens (e.g. `V7b9` in a pack) — needed once Phase 8 authors fusion/lo-fi color? | Phase 8 | authoring experience; grammar extension is additive |
| Q2 | Slash-bass `/n` is grammar-complete but unexercised (pedal intros, pop I/3) | Phase 8 | first pack that wants it; P-rule fixtures exist |
| Q3 | Per-pack dressing-table overrides (jazz b9-leaning dominants in minor vs pop) — PHASE_2 Q1's pattern applied to dressing | Phase 8 | whether the global tables + expressionRanges prove insufficient across 5 packs |
| Q4 | A seeded substitution pass between repeat instances (BiaB-style percentage) | Post-v1 | listening evidence that identical repeats read as static (D7 hook documented) |
| Q5 | Truck-driver modulation transform over `keys` regions | Post-v1 | demand; representation reserved (D10) |
| Q6 | Target-aware intro approach (BiaB-style last-chord rewrite toward the first body chord) | Phase 8 / post-v1 | whether authored-open intros ever land badly against a drawn first section |
| Q7 | Deceptive rule is dormant (no v1 form triggers it) — does it fire correctly for Phase 8's doubled final choruses? | Phase 8 | PHASE_3 Q2 (doubled-chorus forms); synthetic fixture exists meanwhile |
| Q8 | Secondary-dominant slash syntax (`V7/ii`) for authoring ergonomics | Phase 8 | author feedback; absolute tokens cover v1 |
| Q9 | Additional voicing candidate classes (cluster pads, spread triads, guitar-shape sets) — **partially resolved**: PHASE_5 added `fifths` (2026-07-07); further classes remain open for Phase 8 | Phase 5 → Phase 8 | pack-authoring needs; additive to §8.4 |

---

## 13. Amendments to earlier documents (this session)

All additive; applied in the same commit as this document:

1. **PHASE_1 §7 Q4**: `progressions.yaml` schema marked resolved (PHASE_4 §4); `timbres.yaml` remains with Phase 7.
2. **PHASE_1 §7 Q6**: mid-song modulation marked resolved — deferred post-v1 with representation reserved (PHASE_4 §7.1, D10).
3. **PHASE_1 §4.3**: extension-points line annotated as pinned by PHASE_4 §7.
4. **PHASE_2 §7.2**: `harmonicRhythmBase` semantics amended to "soft selection filter, consumed by Phase 4" (PHASE_4 §5.2, D9).
5. **PHASE_2 §9 Q3**: resolved (D9).
6. **ROADMAP §2 decisions log**: row added for the harmony model.
7. **ROADMAP §4 Phase 4 bullet**: key/mode-selection line annotated (absorbed by Phase 2 D5; Phase 4 owns everything inside the key).

---

## 14. Definition of done

Phase 4 is **built** when an implementation session demonstrates:

1. **Loader**: `progressions.yaml` parsing into frozen pydantic models; validation rules P1–P10 implemented with one rejection fixture per rule class; both reference files load clean; the P1/P4 cross-file checks run against the PHASE_3 reference `forms.yaml` files.
2. **Theory module**: `resolve_token` golden tests covering every suffix, alterations, case errors, holds, and slash bass; §8.1/§8.2 tables asserted; spelling goldens (all 12 tonics × both table classes; "B♭7 in D minor" class of cases); `chord_tones`/`guide_tones`; voicing candidates per class with lane pruning (nothing above MIDI 71 in a ≤71 lane); `vl_distance` and `optimal_voicing_path` golden-tested on a hand-verified C-major ii–V–I fixture (shell and rootless classes), including a register-drift case proving the anchor term prevents downward marching; integer-cost property (all costs are ints).
3. **Dressing data**: `dressing.yaml` matching §6.3 exactly; unit tests for tier boundaries, function offsets and clamping; every table option validated against §6.4.
4. **Harmony stage**: implements §5.1 exactly; golden tests asserting both §10 HarmonicPlans **event-for-event** (ticks, durations, sectionIds, full ChordSpecs incl. symbol/roman, scale, function, tags, keys, poolSelections).
5. **Seed goldens**: the §5.6 harmony-stream RNG vectors asserted exactly.
6. **Determinism**: same inputs → identical plan (repeated-run); counting-RNG shim asserting **8 draws** for example 1 and **30 draws** for example 2; a singleton-candidates fixture consuming zero draws; a budget/form change shifting no draws before its first divergent candidate set (append-only discipline).
7. **Property tests**: every pack × supported mood × `maxLengthSec ∈ {30…600}` × 25 seeds → a HarmonicPlan that validates: chords tile `[0, totalBars × ticksPerBar)` with no gaps/overlaps; every event inside its section's tick range; every ChordSpec quality in the PHASE_1 enum with §6.4-legal extensions; every event carries scale + function; final event of the song rooted on degree 1; sections of type prechorus/bridge end D-function; `keys == [{0, tonicPc, mode}]`; same-tag sections have identical bodies outside replaced bars; `poolSelections` complete.
8. **Cross-validation**: a test comparing `chord_tones` against music21 `harmony.ChordSymbol` for the resolvable subset (documented exclusions for its known defects), with music21 version pinned.
9. **Deceptive fixture**: a synthetic same-tag adjacency with no eligible turnaround exercising the deceptive rule end-to-end.
10. **Amendments** (§13) applied and consistent.

---

## 15. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §4/§9: pools, turnarounds, finals, weights, gates — all YAML; engine dressing/scale/function tables are likewise data files |
| 2. Rhythm separate from pitch | This phase emits chord *specs*, never notes; within-bar chord timing is even-split beat math; §8's voicing utilities produce candidates only when Phase 5 calls them |
| 3. Hierarchical seeds | §5.6: single named `harmony` stream; append-only draw order; rerolling `harmony` re-rolls progressions/color without touching any other stage |
| 4. Soloist owns above ~C5 | §8.4: voicing candidates hard-prune at the lane ceiling; non-drum lanes have `high ≤ 71` (PHASE_1 §4.4); no field this phase emits can raise a ceiling |
| 5. Deterministic pipeline | Integer weights and ordered candidate lists throughout; draws only via `weighted_choice` when ≥ 2 candidates; integer-cost DP (D16); no floats in any selection; entropy enters nowhere |
