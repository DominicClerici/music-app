# PHASE_8 — Quality, Evaluation & Style Pack Expansion

Designed 2026-07-07 (session 8). Status: **awaiting approval**.

This document pins the final roadmap phase: the quality/evaluation framework (structural validators beyond PHASE_1 §3.8, the golden-seed regression corpus and its bless workflow, the smoke matrix, the listening-test protocol), the style-pack authoring workflow and its tooling, and the designs of the three remaining style packs — **chill_lofi**, **blues**, **fusion_jazz** — plus the refinement path for the two reference packs. It also dispositions every open question earlier phases routed to Phase 8, resolving PHASE_2 Q1/Q6, PHASE_3 Q1/Q4, PHASE_4 Q1, PHASE_5 Q4/Q7, PHASE_6 Q7, and PHASE_7 Q4, and re-deferring the remainder with updated evidence.

Research base (session 8): lo-fi hip-hop production analyses (tempo/swing corpora, Dilla microtiming studies, structure analyses of released tracks, the IASPM "Beats to Relax/Study To" literature); blues jam-track practice (Band-in-a-Box blues style sets, StudyBass boogie pedagogy, Fred Below/Chicago vs SRV/Texas shuffle documentation, swing-ratio measurements, stop-time conventions); fusion/jazz-funk sources (Headhunters/Chameleon and Actual Proof transcription analyses, the ZGMTH early-funk microtiming corpus — 16th swing 1.07–1.8:1, never triplet; Kilchenmann & Senn on funk vs swing microtiming magnitude; fusion form analyses of Cantaloupe Island / Maiden Voyage / So What); and evaluation/QA practice (Yang & Lerch's generative-music metrics and MGEval, MusPy's metric suite, the LilyPond regression-test model, Jest/ApprovalTests blessing workflows, MUSHRA vs pairwise listening methodology from MusicLM/MusicGen/Music Transformer, BiaB StyleMaker/RealDrums authoring tooling — Developer Mode lint, `DrumAudioResults.txt` selection logs, the <3-candidates warning — Yamaha Style Creator's looping-section edit loop, Wwise loudness calibration, Microsoft PICT combinatorial coverage, the rule of three for seed counts).

---

## 1. Scope

**In scope**

- Machinery resolutions the three new packs force, all additive: the blues meter/shuffle model, the lo-fi loop-form model, named humanizer feel profiles with a pack selector (amending PHASE_6 §5.3 / PHASE_2 §5.1), authored chord-extension tokens (amending PHASE_4 §3.1), and dispositions for every Phase-8-routed open question.
- Full pack designs for `chill_lofi`, `blues`, and `fusion_jazz`: manifest, `interpreter.yaml`, `forms.yaml`, `progressions.yaml`, pattern-bank conventions with normative defining entries, `transitions.yaml`, and `timbres.yaml` defining entries. Content is authored to the PHASE_5/PHASE_7 "defining entries" standard: schema-normative and golden-anchoring, with full bank enumeration an implementation-session authoring task (D16).
- The reference-pack (pop_rock, jazz) refinement path.
- The validator suite: three layers (hard pipeline invariants W1–W8; musical rule checks L2; statistical style bands L3) — concretizing ROADMAP §4's "register collisions, fill presence, cadence correctness, density budget compliance."
- The golden-seed regression framework: IR-level golden corpus, the `bless` workflow with semantic diffing, and the smoke matrix (generalizing every prior phase's property tests to five packs).
- The listening-test workflow: error-spotting protocol, pairwise A/B, anchored milestone rubric; the PHASE_7 Q1/Q7 listening tasks.
- The pack-authoring workflow: tooling (audition CLI, pack linter, selection log, calibration report) and the per-pack authoring checklist.

**Explicitly not in scope**

- Implementation of anything (this is the last design session; implementation sessions follow).
- New pipeline stages or IRs — Phase 8 adds no stage; every design here consumes the Phases 1–7 contracts as pinned.
- Stop-time choruses, `kind: break` semantics, riser wiring, SHOT endings, true 12/8 meter, doubled final choruses, per-pack dressing overrides — all explicitly deferred with rationale (§3.8, §12).
- The browser player; audio-rendered (as opposed to document-level) regression testing (D11).
- Any style family beyond the roadmap's five.

---

## 2. Contracts consumed

Phase 8 produces no new pipeline contract; it consumes **everything** and validates the whole. The load-bearing consumptions:

| Upstream contract | What this phase does with it |
| --- | --- |
| Pack file schemas (PHASE_2 §5.1, PHASE_3 §5, PHASE_4 §4, PHASE_5 §5, PHASE_6 §4, PHASE_7 §4) | The three new packs are authored against them verbatim. Two schemas gain additive fields: `interpreter.yaml` `feelTable` (§3.4), the token grammar's extension group (§3.5). Every loader rule (F/P/PT/TR/TB) applies to the new packs unchanged; §4–§6 note where a rule shaped the content (e.g. P6 mode-coverage, PT5 completeness at unreachable rungs). |
| Engine data files (`moods`, `energy`, `intensity`, `lanes`, `dressing`, `feel`, `mod_defaults`, `allowlist`) | Consumed as-is except `feel.yaml`, which grows two named profiles (§3.4), and `allowlist.yaml`, which gains `Vibrato`/`AutoFilter` paths (PHASE_7 §5.2's amendment path). The verdict pattern "do global tables survive five packs?" is answered per table in §3.8. |
| Mood model (PHASE_2 §4–§6) | Each new pack's `supportedMoods`/`tempoRange`/`expressionRanges` were checked against the anchors and formulas: mood-derived tempo centers ∩ pack ranges produce each genre's tempo tiers with **zero per-pack mood overrides** (resolves PHASE_2 Q1 — §3.8). |
| Swing model (PHASE_2 §6.4) | Verified against genre measurements: the tempo-dependent table matches blues shuffle as-is (no override); evaluated at 2× tempo it matches funk 16th swing (fusion, no override); lo-fi needs the existing pack `swingRatio` override (0.57). |
| Form machinery (PHASE_3) | `main`, `breakdown`, `head`-at-16-bars, 8/16-bar cyclic options, and the fallback/degrade/repeat mechanics are exercised by the new packs; `postchorus` and `variant` are not (§3.8 dispositions PHASE_3 Q1). One repeat block suffices for every new template (resolves PHASE_3 Q4). |
| Harmony machinery (PHASE_4) | Pools/turnarounds/finals as pinned; PHASE_4 D6's transforms-inert-on-empty-`turnarounds` rule is load-bearing for lo-fi and fusion vamps (§3.3). The dressing ladder + `expressionRanges` produce each genre's color floor (lo-fi 7ths/9ths, blues 9/13/#9) without per-pack dressing data (PHASE_4 Q3 stays deferred, evidence strengthened). |
| Part generators (PHASE_5) | Pattern selection, retargeting (the `sixth` degree finally earns its reservation — blues boogie), `minDensity` gating, `push`, voicing classes, and `mode: patterns` serve all three packs; the walker serves none of them (§3.2). |
| Transition/humanizer machinery (PHASE_6) | Device tables, the dormant `dropout` device (wakes for lo-fi/fusion `breakdown`), the `stop` device (blues/fusion enable it), mutation tables, swing rendering, and the ms-domain feel maps — consumed as pinned, with the feel-profile selection rule amended (§3.4). |
| Sound design (PHASE_7) | `timbres.yaml` schema, mod-mapping semantics, bus/mix architecture consumed verbatim by three new timbre files; per-flavor `mod` overrides cover every new engine-class case (FM Rhodes, AM organ) — resolves PHASE_7 Q4 (§3.8). |
| Seed system & determinism rules (PHASE_1 §5) | The golden corpus, bless workflow, and smoke matrix (§8) are built directly on `(params, seed) → identical document`; the validator layers assume and re-verify it (W5). |
| Document validator V1–V8 (PHASE_1 §3.8) | Layer 1 subsumes it and extends it with pipeline-aware checks W1–W8 (§8.1). |

---

## 3. Machinery resolutions

Every resolution below is additive. §13 lists the resulting amendments document-by-document.

### 3.1 Blues meter: 4/4 + swing + explicit triplet authoring (D1)

The blues pack stays 4/4 with `feel: swing8`. Two authoring modes coexist in one bank:

- **Shuffle patterns** are authored on the straight 8th grid; the existing swing transform renders the shuffle. The PHASE_2 §6.4 tempo table already encodes the measured blues behavior — ratio 0.722 at ≤ 90 BPM narrowing toward straight at speed (research band: slow 66–72 %, uptempo 58–62 %) — so blues ships **no `swingRatio` override**.
- **Slow-blues (12/8-feel) patterns** author **explicit triplet positions** (`pos` 0/160/320 within each beat — pattern `pos` was never grid-restricted), which the swing transform ignores (it only touches `pos_in_beat == 240`), and are gated to the slow tier via `eligibility.tempoBpm` (the mechanism PHASE_5 D3 built for brush ballads).

**One-grid-per-pattern rule (normative authoring convention, linted — §9.2):** a pattern's events lie entirely on the straight-8th/16th grid *or* entirely on the triplet grid, never both. Rationale: a swung straight-8th (→ 347) and an authored triplet (320) land 27 ticks apart; across patterns that difference is feel, inside one pattern it is flam.

True 12/8 (per-signature humanizer beat classes and feel tables) is deferred (§12 Q1). Rejected: a 12/8 pack (PHASE_6 §5.1's beat-class model and `feel.yaml` are 4/4-shaped; a real amendment for one pack); per-tier signature switching (new Interpreter machinery on top of that).

### 3.2 Bass modes for the new packs (D3; resolves PHASE_5 Q4)

All three new packs use `mode: patterns`. Blues bass is **authored boogie/box/pedal/triplet-arpeggio degree patterns** — the boogie cell is `root–third–fifth–sixth | seventh–sixth–fifth–third`, resolving against pinned dom7s to R–3–5–6–♭7 exactly (the `sixth` degree's reserved purpose). Fusion bass is **authored riff ostinatos** (tresillo skeletons, root/octave 16ths, ghosts); the research is explicit that fusion bass riffs rather than walks. Lo-fi bass is root-locked and static by design. Walking blues remains the **jazz pack's** territory (its `blues_12` pools + the walker already ship it); a mixed per-pack mode is not introduced. In each genre a *locked* bass loop is the idiom — this is also the evidence that re-defers PHASE_6 Q8 (bass mutation operators): repetition is the feature (§3.8).

### 3.3 Loop/vamp forms and the inert-transform guarantee (D2, D4)

- **Lo-fi** models its A/B loop structure as **`main`/`breakdown` alternation**: the stripped section *is* `breakdown` (entered by the PHASE_6 §3.5 `dropout` device — dormant until now; arrangement-capped at 2 layers; energy base 0.25). Loop identity across sections is structural: `main`, `breakdown`, `intro`, and `outro` all point at **one `harmonyTag` (`loop`)** — one progression draw serves the whole track, which is the genre. `variant` stays **label-only in v1** (dispositions PHASE_3 Q1's variant row — no consumer existed and none is added; §12 Q2 reserves the load-bearing design).
- **Fusion** ships two template families: **`tune`** (`intro? + head + repeat(solo) + head + outro` — the Cantaloupe/Watermelon class, `head` at 16 bars with a 32-bar AABA option) and **`vamp`** (`intro + repeat(main) + breakdown + main + outro` — the Chameleon class). `main` and `breakdown` share the `vamp` tag so the strip-down keeps the groove's harmony.
- **Both packs ship `turnarounds: []`**, and PHASE_4 D6 makes *both* boundary transforms (turnaround and deceptive) inert on an empty list — verified against the failure case: a vamp ending on the tonic (Cantaloupe's final i7) at a same-tag boundary would otherwise be deceptive-substituted every cycle. Vamps loop untouched by construction. Corollary: a doubled final chorus in pop_rock cannot wake the deceptive rule either (pop also ships `[]`), so PHASE_3 Q2 / PHASE_4 Q7 stay honestly deferred (§3.8).
  *[amended 2026-07-21, S22-3 (user-ratified), C-27: **the "both inert" claim above is wrong**, and PHASE_4's own normative text already says so (§5.1 step 5 and §5.4's "None eligible (or empty run) → **deceptive fallback**"). An empty `turnarounds` list makes only the *turnaround* transform inert; the **deceptive** substitution is a fixed, draw-free fallback that fires on **any** same-tag boundary whose section ends tonic-rooted with `function == "T"`. D6's parenthetical held for pop_rock only because **pop has no same-tag adjacency** — which PHASE_4 §5.4 states explicitly. Fusion's `vamp` tag serves `main`/`breakdown`/`outro` repeatedly and `tune_16` serves `head`/`solo`/`solo`/`head`, so the rule wakes at nearly every boundary: measured **874 substitutions across 336 renders** (`tune_16` 625, `vamp` 249). A reproduced render (calm, `vamp`, `sus_pedal`) rendered a one-chord pedal as `I7sus4 | vi | I7sus4 | vi | …` for half the track — **violating DoD §14.10's "vamps loop without harmonic drift".*
  *The real rule: both boundary transforms are inert only **absent same-tag adjacency**; with same-tag adjacency and an empty `turnarounds` list, the deceptive fallback fires on every tonic-rooted, T-function section ending.*
  *Authoring rule (the general form of the lo-fi `loop` rule in the bullet below): every entry in a tag that has same-tag adjacency must be authored **rotated to end open**, or its sections will be deceptive-substituted every cycle.*
  *Fusion's response: the `vamp` pool is re-rotated — `minor_launch` → `[[i7], [~], [iiø7], [V7(#9)]]` (a pure rotation, all content preserved, ends on the dominant), `sus_pedal` → `[[I7sus4], [~], [~], [bVII7]]` (a one-chord tonic pedal cannot be rotated open; this keeps the pedal for 3 of 4 bars and ends on the mixolydian ♭VII, squarely in idiom); `dorian_funk` and `mixo_vamp` already end open. `tune_16`'s chorus-boundary substitution is **accepted as-is** — it is precisely the relaunch device D6 was built for, and a substituted chord at a head/solo turnaround is idiomatic jazz — with the known limitation that the substitution is **fixed and draw-free**, so every chorus relaunches with the same chord.]*
- One authoring rule falls out of P7 for lo-fi's shared tag: because `loop` also serves `intro`, every `loop` entry must end **open** (not degree-1-rooted). Loops are therefore authored **rotated to end open** (`Imaj7–vi7–ii7–V7`, not `ii7–V7–Imaj7–~`) — which is what loop-friendly progressions look like anyway; the finals pool closes the song.

### 3.4 Named feel profiles + pack selector (D5; resolves PHASE_6 Q7)

The PHASE_6 §5.3 two-table model (swing null → `straight`, else → `swung`) fails at five packs: the `swung` table is jazz-calibrated, and the two new swung packs contradict it in opposite directions — lo-fi wants the whole kit **heavily laid back** (Dilla: 10–30 ms behind the grid), fusion wants **tight** (funk microtiming is ~2.6× smaller than swing's; exaggeration measurably hurts groove).

**Resolution:** `feel.yaml`'s `offsetsMs` becomes a menu of **named profiles** — the existing `straight` and `swung` plus two new ones — and `interpreter.yaml` gains an optional `feelTable: <profile>`; absent, the swing-derived default applies (pop_rock and jazz need no change). Calibration data stays engine-owned; packs select, never author values. Jitter widths, accents, `velJitter`, and `bassLegato` remain global in v1.

New profiles (values in ms, same shape and ≤ 25 ms validator as PHASE_6 §5.3):

```yaml
  laidback:                          # lo-fi: whole kit behind the grid, backbeats latest
    kick: 0                          # the anchor
    snare: { down: 10, back2: 16, beat3: 12, back4: 16, off: 10 }
    hats: 6
    ride: 0
    toms: 8
    crash: 0
    perc: 8
    bass: 6
    comping: 12
    pads: 0
  tight:                             # fusion: near-quantized; velocity does the talking
    kick: 0
    snare: 2
    hats: -2
    ride: 0
    toms: 0
    crash: 0
    perc: 0
    bass: 0
    comping: 3
    pads: 0
```

Pack assignments: chill_lofi → `laidback`, fusion_jazz → `tight`, blues → `straight` (electric-blues comping sits on the beat; the `swung` table's +18 ms comping delay is a jazz-piano behavior, not a chank; the kick-anchored laid-back backbeat is shared with pop/rock).

### 3.5 Authored chord extensions (D6; resolves PHASE_4 Q1)

Fusion's verified vocabulary (`bVI7#11`, `13sus`, slot-pinned `7#9`) is unreachable by the dressing ladder — no dressing table emits `#11`, and per-slot pinning of a specific alteration is impossible by construction. The token grammar (PHASE_4 §3.1) gains an **extension group**, parenthesized for unambiguous parsing:

```
token    := degree quality extgroup? bass?
extgroup := "(" ext ("," ext)* ")"       ext ∈ {9, b9, #9, 11, #11, 13, b13}
```

- Extensions are legal **only after an explicit quality suffix** (bare dressable degrees stay unambiguous).
- Legality per quality follows PHASE_4 §6.4 exactly (validated at load; new rule P11, §4.3-adjacent).
- **An authored extension group fully pins the token**: dressing skips the slot entirely — no options, no draw (one more level of the existing bare-vs-suffixed pin logic; draw-count goldens see pinned slots as draw-free).
- `ChordSpec.extensions` receives the authored list verbatim; `symbol`/`roman` derivation is unchanged (`bVI7(#11)` → symbol per §3.3's tidy-display, roman echoes the authored token).

Reference usage: fusion `bVI7(#11)` (Cantaloupe color), `V7(#9)` (minor-launch vamp); blues `I7(#9)`/`V7(#9)` in the aggressive-gated pool entry. Lo-fi needs none — its 7ths/9ths floor falls out of `expressionRanges` hitting dressing tier 3 (the verdict that keeps PHASE_4 Q3 deferred).

### 3.6 Percussion (resolves PHASE_5 Q7)

No fifth role. The `perc` drum voice (PHASE_1 §6.3, mapped 1:1 to a `perc` track by PHASE_5 §8.2) carries lo-fi shaker/rim/tambourine and fusion auxiliary percussion as ordinary drum-bank events. The role enum stays closed.

### 3.7 Allowlist growth (PHASE_7 §5.2 amendment path)

Two whitelisted-but-unlisted effect classes gain allowlist paths, driven by §4/§6 timbres: `Vibrato: [frequency, depth, wet]` (lo-fi tape wobble) and `AutoFilter: [frequency, baseFrequency, octaves, depth, wet]` (fusion clav wah). No instrument-class paths change.

### 3.8 Disposition table for the remaining routed questions (D7)

| Question | Disposition |
| --- | --- |
| Stop-time choruses (PHASE_3 Q5, PHASE_5 Q5, PHASE_6 Q5) | **Deferred post-v1.** Requires variant-aware pattern selection, which §3.3 deliberately keeps dormant; the blues pack is believable without it, and the PHASE_6 `stop` *device* (1-beat boundary silence) covers the adjacent need. `kind: break` stays reserved. |
| Riser (PHASE_6 Q2 / PHASE_7 Q3 remainder) | **Stays dormant post-v1.** None of the five v1 packs wants risers: lo-fi is anti-climax by design, blues doesn't use them, fusion builds by arrangement. The PHASE_7 §4.7 recipe stays pinned. |
| SHOT ending (PHASE_6 Q4) | **Deferred.** Blues "band-hits" endings are expressible as finals-pool + ending-pattern content under `close: cold`. |
| Lydian rung (PHASE_2 Q6) | **Resolved — stays excluded.** No v1 pack's mode menu wants it (lo-fi minor/dorian/major; blues major/minor; fusion dorian/mixolydian/minor/major). |
| Per-pack per-mood overrides (PHASE_2 Q1) | **Resolved — not needed.** Verified across all three packs: mood `tempoCenter` ∩ pack `tempoRange` yields the genre tempo tiers by itself (melancholic 68 → slow blues; energetic 139.5 → [126, 150] → uptempo shuffle; nostalgic 86.5 → lo-fi center), and `expressionRanges` position density/dissonance. |
| Per-pack `mod_defaults` overrides (PHASE_7 Q4) | **Resolved — not needed.** Per-flavor `mod` overrides cover every new engine-class case (§4.6, §6.6). |
| Slash bass (PHASE_4 Q2), secondary-dominant syntax (PHASE_4 Q8) | **Stay unexercised / not needed.** Fusion sus chords use `7sus4` tokens directly. |
| Doubled final chorus + deceptive rule (PHASE_3 Q2, PHASE_4 Q7) | **Deferred post-v1.** With pop's empty `turnarounds` the deceptive rule is inert (PHASE_4 D6), so a doubled chorus repeats identically — no payoff now. The synthetic deceptive fixture remains the rule's only exerciser. |
| Multiple repeat blocks (PHASE_3 Q4) | **Resolved — not needed.** Lo-fi's ABABB shape fits one repeat block plus trailing slots (§4.3); F4's ≤ 1 rule stands. |
| Bass mutation operators (PHASE_6 Q8) | **Deferred, evidence updated:** all three new packs are patterns-mode bass, and in each genre the locked bass loop is the idiom (boogie cell, fusion ostinato, static sub). |
| Per-pack dressing overrides (PHASE_4 Q3) | **Stays deferred, evidence strengthened:** fusion's #9-leaning color is achieved by authoring (§3.5), lo-fi's floor by `expressionRanges`; the global ladder survives five packs. |
| FM-piano adequacy (PHASE_7 Q7), loudness calibration (PHASE_7 Q1) | **Become named listening tasks** in §8.4 — unresolvable on paper. |
| Tempo-aware section lengths (PHASE_3 Q6), fill lay-out variants (PHASE_6 Q6), walker repeated-note polish (PHASE_5 Q9 / PHASE_6 Q9), correlated 1/f drift (PHASE_6 Q1), keytracking (PHASE_7 Q2), StereoWidener mono checks (PHASE_7 Q5), LUFS (PHASE_7 Q6) | **Unchanged — post-v1**, listening-evidence-gated as their owning docs state. The §8.4 error-spotting log is the designated evidence collector. |

---

## 4. Pack design — `chill_lofi`

### 4.1 Manifest & interpreter

```yaml
# styles/chill_lofi/manifest.yaml
formatVersion: 1
id: chill_lofi
name: Chill / Lo-fi
version: 0.1.0
engine: ">=0.1"
timeSignatures: [[4, 4]]
tempoRange: [68, 95]            # research center 82; >95 stops reading as lo-fi
```

```yaml
# styles/chill_lofi/interpreter.yaml
supportedMoods: [nostalgic, calm, dreamy, melancholic, romantic, mysterious, dark, happy]
defaultMood: nostalgic           # the genre's most-cited affect
# vs the PHASE_2 §5 sketch: energetic is DROPPED (contradicts the genre's defining
# low-arousal character); happy kept as the muted "sunny chillhop" edge.

modes: [major, dorian, minor]   # amended 2026-07-20 (S20-1, user-ratified): original printed
                                 # order [minor, dorian, major] violates the interpreter's
                                 # Rule 3 (modes must be a MODE_LADDER-ordered subsequence);
                                 # set and semantics unchanged (selection is ladder-distance)
tonics:
  minor:  [A, D, E]
  dorian: [D, G]
  major:  [C, F, G]

feel: swing16
swingRatio: 0.57                 # research 56-58%; the tempo table would give ~64% at 82 BPM
feelTable: laidback              # §3.4

expressionRanges:
  density:    [0.15, 0.55]       # sparse genre
  dissonance: [0.40, 0.65]       # floor lands dressing tier 3: 7ths/9ths ARE the default;
                                 # ceiling keeps altered dominants out

flavors:
  drums:   [dusty_kit, boombap_kit]
  bass:    [warm_sub, round_pick]
  comping: [ep_mellow, piano_felt]
  pads:    [tape_strings, warm_wash]

ensembles:
  default: { drums: dusty_kit, bass: warm_sub, comping: ep_mellow, pads: tape_strings }
  study:   { drums: boombap_kit, bass: warm_sub, comping: piano_felt, pads: warm_wash }
```

### 4.2 `forms.yaml`

```yaml
energyRange: [0.25, 0.60]        # flat dramaturgy — the exact envelope PHASE_3 §6.4 predicted

sections:
  intro:     { bars: [[4, 3], [8, 1]], phrases: { 4: [a], 8: [a, a] },
               harmonyTag: { 4: loop, 8: loop } }
  main:      { bars: [[8, 1]], phrases: { 8: [a, a] }, harmonyTag: { 8: loop } }
  breakdown: { bars: [[8, 1]], phrases: { 8: [a, a] }, harmonyTag: { 8: loop } }
  outro:     { bars: [[4, 3], [8, 1]], phrases: { 4: [a], 8: [a, a] },
               harmonyTag: { 4: loop, 8: loop } }

templates:
  - id: loop_ab                  # loop-with-beat / loop-without-beat alternation (ABAB..B)
    weight: 60
    spine:
      - { section: intro, optional: [2, 1] }
      - repeat: { count: [1, 2], slots: [ { section: main }, { section: breakdown } ] }
      - { section: main }
      - { section: outro, optional: [3, 1] }
    ending: { tagBars: 0, close: fade }      # fade = HOLD alias (PHASE_6 D7), accepted for v1
    degrade:
      - { drop: outro }
      - { shrink: intro }
      - { dropFromRepeat: breakdown }
      - { drop: intro }
    fallback: { section: main, bars: 8 }

  - id: loop_a                   # main cycles with one late stripped section
    weight: 40
    spine:
      - { section: intro, optional: [2, 1] }
      - repeat: { count: [2, 4], slots: [ { section: main } ] }
      - { section: breakdown }
      - { section: main }
      - { section: outro, optional: [3, 1] }
    ending: { tagBars: 0, close: fade }
    degrade:
      - { drop: outro }
      - { shrink: intro }
      - { drop: breakdown }
      - { drop: intro }
    fallback: { section: main, bars: 8 }
```

Notes: one `harmonyTag` for the whole pack — the track *is* one loop (§3.3). At the default 180 s / ~82 BPM (≈ 61-bar budget) `loop_ab` lands ~40–56 bars ≈ 2:00–2:45 — the genre's length band. `breakdown` sections at typical energies still quantize to rung 2, but the arrangement planner's `breakdown` modifier caps them at 2 layers and the `dropout` device cuts the entry — the "loop without beat" state. The 0.60 energy ceiling makes **rung 4 unreachable**; rung-4 mains are still authored (PT5 completeness) as marginally fuller rung-3 variants, annotated in the linter (§9.2). *[Amended 2026-07-20, S20-5 (user-ratified), C-22: in practice **rung 3 is also unreachable** — with `energetic` dropped (D8), the pack's max arousal is happy (+0.40), whose sections top out at measured energy 0.474 < the 0.55 rung-3 threshold (1200-render sweep). Rung-3 banks and the pads role are therefore dormant in v1 renders; authored as completeness content, accepted deliberately — the flat-rung-2 dramaturgy is the genre. The linter's reachability read (envelope ceiling 0.60 → rung 3 reachable) does not model arousal scaling; no unreachable-content warning fires for rung 3.]*

### 4.3 `progressions.yaml`

```yaml
pools:
  loop:                          # every entry authored ROTATED TO END OPEN (P7: tag serves intro)
    - { id: royal_road,     weight: 30, modes: [major],
        phrases: { a: [[IVmaj7], [V7], [iii7], [vi7]] } }
    - { id: pop_soul,       weight: 30, modes: [major],
        phrases: { a: [[Imaj7], [vi7], [ii7], [V7]] } }
    - { id: minor_two_five, weight: 40, modes: [minor],
        phrases: { a: [[i7], [~], [iiø7], [V7]] } }
    - { id: minor_lament,   weight: 30, modes: [minor],
        phrases: { a: [[bVImaj7], [~], [i7], [V7]] } }
    - { id: dorian_vamp,    weight: 100, modes: [dorian],
        phrases: { a: [[i7], [IV7], [i7], [IV7]] } }

turnarounds: []                  # loops don't relaunch; transforms inert (PHASE_4 D6)

finals:
  - { id: two_five_close, weight: 60, modes: [major],  bars: [[ii7, V7], [Imaj7]] }
  - { id: plagal_soul,    weight: 40, modes: [major],  bars: [[IVmaj7], [Imaj7]] }
  - { id: minor_close,    weight: 60, modes: [minor],  bars: [[iiø7, V7], [i7]] }
  - { id: minor_plagal,   weight: 40, modes: [minor],  bars: [[iv7], [i7]] }
  - { id: dorian_plagal,  weight: 100, modes: [dorian], bars: [[IV7], [i7]] }
```

(7th-quality suffixes are authored — the qualities are the genre; the dissonance floor then dresses 9ths on top at tier 3+. All moods with `harmonicRhythmBase` 0.5 pass the density filter: every entry ≤ 1 chord/bar.)

### 4.4 Pattern-bank conventions & defining entries

`layeringOrder: [drums, bass, comping, pads]`. Retarget defaults: bass `{28, 45, retrigger}`, comping `{50, 69, retrigger}`, pads `{45, 64, retrigger}`.

**Drums** (velocities quiet and varied; nothing above ~0.85): rung 1 — half-time (kick 1, snare on beat 3, sparse hats); rung 2 — boom-bap (kick 1 & 3-side, snare 2/4, 8th hats, with the swung ghost kick as a `minDensity`-gated event — it emerges as density rises); rung 3 — adds `minDensity`-gated 16th hats and `perc` shaker; rung 4 — rung 3 + rim layer (unreachable; completeness only). Each role bank also carries the PT5-required ungated `intro`/`ending` entries (thinned/settled variants of the rung-1–2 mains) — this convention holds for all three packs. Fills quiet, snare-roll shaped. Defining entry:

```yaml
- { id: lf_dr_2, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 3, events: [
    {pos: 0, voice: kick, velocity: 0.80}, {pos: 840, voice: kick, velocity: 0.60, minDensity: 0.45},
    {pos: 480, voice: snare, velocity: 0.72}, {pos: 1440, voice: snare, velocity: 0.70},
    {pos: 0, voice: hat_closed, velocity: 0.42}, {pos: 240, voice: hat_closed, velocity: 0.30},
    {pos: 480, voice: hat_closed, velocity: 0.36}, {pos: 720, voice: hat_closed, velocity: 0.28},
    {pos: 960, voice: hat_closed, velocity: 0.40}, {pos: 1200, voice: hat_closed, velocity: 0.30},
    {pos: 1440, voice: hat_closed, velocity: 0.36}, {pos: 1680, voice: hat_closed, velocity: 0.32}]}
```

**Bass** (`mode: patterns`): rung 1 — whole-note roots; rung 2 — root + fifth halves; rung 3 — sparse syncopated root 8ths with one octave lift; rung 4 — rung 3 + gated ghost 16th. **Comping**: rung 1–2 sustained whole/half `chord` hits; rung 3 offbeat-stab variant with an and-of-4 `push`; voicing classes `{1: [shell3, triad_close], 2: [rootless_a, rootless_b], 3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}` (the research's 3-5-7-9 / 7-9-3-5 voicings are literally our classes). **Pads**: `{1–4: [fifths]}`, whole notes, low velocity.

### 4.5 `transitions.yaml`

```yaml
phraseFill: { odds: [1, 4] }             # fills rare and understated
stop:       { enabled: false }
crash:      { velocity: [0.30, 0.55] }   # soft washes, never arena hits
mutation:
  drums:   { none: 8, drop_ornament: 2, kick_pickup: 1 }
  comping: { none: 5, anticipate: 1, drop_hit: 1 }
```

### 4.6 `timbres.yaml` defining entries

- `dusty_kit`: lowpass-voiced MembraneSynth kick (`pitchDecay 0.08, octaves 3`, longer attack 0.003 — no click), soft NoiseSynth snare (`decay 0.18`, pink; brightness maps `noise.playbackRate` **down-ranged 0.8–2.0** per-flavor override — dusty, not cracky), dark MetalSynth hats (brightness `resonance` override 1500–3500).
- `warm_sub` (bass): MonoSynth sine (`oscillator: {type: sine}`), gentle `Distortion {distortion: 0.12, wet: 0.4}` insert for harmonics; dry, mix −10 dB.
- `ep_mellow` (comping): PolySynth/FMSynth `harmonicity 1` (the mellow-Mark-I pole), brightness → `modulationIndex` 2–8 (per-flavor override); inserts `[Vibrato {frequency: 0.9, depth: 0.12, wet: 0.5}, Chorus]` — the tape-wobble signature (§3.7 allowlist).
- `tape_strings` (pads): PolySynth/MonoSynth fatsawtooth lowpassed, inserts `[Vibrato {frequency: 0.5, depth: 0.10, wet: 0.4}, StereoWidener {width: 0.7}]`.
- Bus `reverb: { decay: [1.2, 3.5], preDelay: [0.02, 0.04], returnFilterHz: 300 }` (the wettest room of the five packs); master `Compressor {threshold: -18, ratio: 3, attack: 0.02, release: 0.3}` + `Limiter {threshold: -1}` (heavier glue — the "compressed and quiet" aesthetic).
- Vinyl crackle / foley: **out of scope as notes and as v1 sound design** — the wobble + dark filtering carry the aesthetic; a document-level noise-bed is noted post-v1 (§12 Q3).

---

## 5. Pack design — `blues`

### 5.1 Manifest & interpreter

```yaml
# styles/blues/manifest.yaml
formatVersion: 1                 # [amended 2026-07-21, S21-1 (user-ratified): printed
id: blues                        #  snippet omitted the required Manifest fields]
name: Blues
version: 0.1.0
engine: ">=0.1"                  # [amended 2026-07-21, S21-1: sibling-verbatim value]
timeSignatures: [[4, 4]]
tempoRange: [50, 150]            # slow 12/8-feel ballads through rock-blues shuffle
```

```yaml
# styles/blues/interpreter.yaml
supportedMoods: [energetic, nostalgic, melancholic, aggressive, dark, tense, mysterious, romantic]
defaultMood: energetic           # the medium shuffle is the shipped-product archetype
# vs the PHASE_2 §5 sketch (drop triumphant/dreamy): ALSO drops happy and calm —
# both fight the dominant-7 grit. Mood → tempo tiers verified: melancholic 68 → slow blues,
# energetic 139.5 → [126, 150] → uptempo shuffle, nostalgic 86.5 → medium-slow.

modes: [major, minor]
tonics:
  major: [E, A, G, C]            # guitar keys
  minor: [A, E, D]

feel: swing8                     # NO swingRatio override: the PHASE_2 §6.4 tempo table
                                 # matches measured blues shuffle as-is (0.722 slow → ~0.58 fast)
                                 # [S21-4: the §6.4 table yields 0.722 flat ≤90 BPM and 0.655 at
                                 # the 150 ceiling — ~0.58 is unreachable within [50,150]; behavior
                                 # identical to jazz's existing table path]
feelTable: straight              # §3.4: electric-blues comping sits on the beat

expressionRanges:
  density:    [0.25, 0.80]
  dissonance: [0.50, 0.90]       # the color floor; dominant-EVERYWHERE comes from authoring (§5.3)

flavors:
  drums:   [blues_kit, roadhouse_kit]
  bass:    [electric_round, upright_soft]
  comping: [crunch_guitar, organ_drawbar]
  pads:    [organ_swell, warm_strings]

ensembles:
  default: { drums: blues_kit, bass: electric_round, comping: crunch_guitar, pads: organ_swell }
  lounge:  { drums: roadhouse_kit, bass: upright_soft, comping: organ_drawbar, pads: warm_strings }
```

### 5.2 `forms.yaml`

Blues jam tracks have no melody head — the form is **all `solo` sections** (the R2 solo energy arch — a rising line peaking on the final chorus — is the documented blues-jam dramaturgy, for free):

```yaml
energyRange: [0.15, 0.95]

sections:
  intro: { bars: [[4, 1]], phrases: { 4: [a] }, harmonyTag: { 4: intro } }
  solo:  { bars: [[12, 4], [8, 1], [16, 1]],
           phrases: { 12: [a, b, c], 8: [a, b], 16: [a, a, b, c] },
           harmonyTag: { 12: blues_12, 8: blues_8, 16: blues_16 } }
  outro: { bars: [[4, 1]], phrases: { 4: [a] }, harmonyTag: { 4: outro } }

templates:
  - id: jam
    weight: 100
    spine:
      - { section: intro, optional: [1, 1] }
      - repeat: { count: [3, null], slots: [ { section: solo } ] }
      - { section: outro, optional: [2, 1] }
    ending: { tagBars: 4, close: cold }
    degrade:
      - { shrink: intro }
      - { drop: intro }
      - { drop: outro }
    fallback: { section: solo, bars: 12 }
```

### 5.3 `progressions.yaml` (defining entries)

Dominant quality is **authored on every chord** — `I7/IV7/V7` pinned; the dressing ladder then adds 9/13 at medium tiers and ♭9/#9 at the top, with function offsets doing the right thing free (I7 → T → tier−1 stays 9/13-colored; V7 → D → tier+1 gets the alterations).

```yaml
pools:
  blues_12:
    - id: quick_change             # the modern jam default; authored CLOSED so turnarounds relaunch
      weight: 60
      modes: [major]
      phrases:
        a: [[I7], [IV7], [I7], [~]]
        b: [[IV7], [~], [I7], [~]]
        c: [[V7], [IV7], [I7], [~]]
    - id: plain
      weight: 25
      modes: [major]
      phrases:
        a: [[I7], [~], [~], [~]]
        b: [[IV7], [~], [I7], [~]]
        c: [[V7], [IV7], [I7], [~]]
    - id: hendrix                  # aggressive corner: authored #9 (§3.5)
                                   # [amended 2026-07-21, S21-6 (user-ratified), C-25: the
                                   # modes:[major] + valence:[-1.0,-0.3] gates are mutually
                                   # exclusive under auto mood-resolution (major-resolving
                                   # moods all have V >= +0.30) — reachable only via an
                                   # explicit key.mode: major override; auto renders get #9
                                   # from the dressing ladder. Accepted dormancy.]
      weight: 15
      modes: [major]
      valence: [-1.0, -0.3]
      dissonance: [0.70, 1.0]
      phrases:
        a: [[I7(#9)], [IV7], [I7(#9)], [~]]
        b: [[IV7], [~], [I7(#9)], [~]]
        c: [[V7(#9)], [IV7], [I7(#9)], [~]]
    - id: minor_12
      weight: 100
      modes: [minor]
      phrases:
        a: [[i7], [iv7], [i7], [~]]
        b: [[iv7], [~], [i7], [~]]
        c: [[bVI7], [V7], [i7], [~]]   # the signature minor-blues cadence
  blues_8:                         # Key-to-the-Highway changes; ends V7 = built-in relaunch
    - { id: key_highway, weight: 100, modes: [major],
        phrases: { a: [[I7], [V7], [IV7], [~]], b: [[I7], [V7], [I7], [V7]] } }
    - { id: minor_8, weight: 100, modes: [minor],
        phrases: { a: [[i7], [V7], [iv7], [~]], b: [[i7], [V7], [i7], [V7]] } }
  blues_16:                        # doubled-front 16-bar
    - { id: sixteen, weight: 100, modes: [major],
        phrases: { a: [[I7], [~], [~], [~]], b: [[IV7], [~], [I7], [~]], c: [[V7], [IV7], [I7], [~]] } }
    - { id: minor_16, weight: 100, modes: [minor],
        phrases: { a: [[i7], [~], [~], [~]], b: [[iv7], [~], [i7], [~]], c: [[bVI7], [V7], [i7], [~]] } }
  intro:
    - { id: v_vamp,        weight: 60, modes: [major], phrases: { a: [[V7], [~], [V7], [~]] } }
    - { id: turnaround_in, weight: 40, modes: [major], phrases: { a: [[I7], [IV7], [I7], [V7]] } }
    - { id: minor_v_vamp,  weight: 100, modes: [minor], phrases: { a: [[V7], [~], [i7], [V7]] } }
  outro:
    - { id: tag_out,       weight: 100, modes: [major], phrases: { a: [[I7], [IV7], [I7], [V7]] } }
    - { id: minor_tag_out, weight: 100, modes: [minor], phrases: { a: [[i7], [iv7], [i7], [V7]] } }

turnarounds:                       # every chorus boundary relaunches like a real band
  - { id: v_four,      weight: 50, modes: [major], bars: [[V7, IV7], [I7, V7]] }
  - { id: quick_v,     weight: 30, modes: [major], bars: [[I7, V7]] }
  - { id: jazz_turn,   weight: 20, modes: [major], dissonance: [0.60, 1.0],
      bars: [[I7, VI7], [ii7, V7]] }
  - { id: minor_turn,  weight: 60, modes: [minor], bars: [[i7, iv7], [bVI7, V7]] }
  - { id: minor_quick, weight: 40, modes: [minor], bars: [[i7, V7]] }
```

*[S21-3: all turnarounds end plain V7 — C-03's SubV admission (bII7-final turnarounds)
is NOT exercised by this pack; the tritone final's `bII7` is parse-only.]*

```yaml
finals:
  - { id: authentic,    weight: 40, modes: [major], bars: [[V7], [I7]] }
  - { id: plagal,       weight: 30, modes: [major], bars: [[IV7], [I7]] }
  - { id: tritone,      weight: 30, modes: [major], dissonance: [0.60, 1.0], bars: [[bII7], [I7]] }
  - { id: minor_auth,   weight: 60, modes: [minor], bars: [[V7], [i7]] }
  - { id: minor_plagal, weight: 40, modes: [minor], bars: [[iv7], [i7]] }
```

Note the P4 discipline: because `solo` serves 12-, 8-, and 16-bar options, each pool provides exactly that option's labels/lengths; P6 mode coverage forces the minor entries in `blues_8`/`blues_16`.

### 5.4 Pattern-bank conventions & defining entries

**Drums** — the two shuffle families across the rung ladder, plus tempo-gated slow-blues triplet patterns (§3.1):

*[amended 2026-07-21, S21-2 (user-ratified), C-23: the printed rung ladder is a derived sample that does not survive §5.2's all-solo form. `main`-kind patterns render **only in `solo` sections**, and the R2 solo energy arch (base 0.60 + 0.30·index/total + 0.10·arousal, envelope [0.15, 0.95]) puts **every rendered solo at energy ≥ 0.624** (rung 3 minimum) with the **final solo at rung 4 for all 8 moods** — so rungs 1–2 mains never render grid-wide. The authored ladder is therefore re-mapped onto the reachable band: the Chicago family (incl. `bl_dr_2`, which lands at **energyLevel 3**, id+events byte-verbatim) and the tempo-gated slow-blues 12/8 patterns sit at **rung 3**; Texas + double-shuffle at **rung 4** (the hat→ride lever moves to the 3→4 boundary the rising arch actually crosses). Comping re-maps equivalently (chank/Charleston → rung 3, driving stabs → rung 4; the tempo-gated triplet-roll → rung 3); bass box/boogie → rung 3, full boogie/pushes → rung 4. Rungs 1–2 are authored as sparser completeness variants (PT5 + the variety lint still require ≥2 ungated candidates each — honest dormant content, recorded in CAVEATS not lint markers, since the [0.15, 0.95] envelope keeps every rung lint-reachable). The energy formulas and §5.2's all-solo form are the pinned inputs; the printed rung expectations are the derived samples that do not survive them.]*

- Rung 1: sparse shuffle, cross-stick 2/4 (ungated) **plus** `eligibility: {tempoBpm: [50, 75]}` slow-blues patterns authored on the triplet grid (ride triplets `pos 0/160/320/480/…`, cross-stick 2/4, kick 1 + pickup into 3).
- Rung 2: **Chicago** — kick 1 & 3, straight-8th hats (swing renders the shuffle), hard snare 2/4.
- Rung 3: **Texas** — four-on-the-floor kick, straight-quarter ride, shuffled snare with `minDensity`-gated ghosts. The hat→ride switch (the genre's #1 energy lever) is the rung 2→3 content change.
- Rung 4: double-shuffle — ride 8ths (swung) both hands implied, four-on-floor, hardest 2/4, gated ghost layer.
- Fills: triplet-grid snare/tom figures; rung-4 tom runs. *[Amended 2026-07-21, S21 T5 (user-ratified), C-24: blues fills author on the straight grid — triplet fills require an all-triplet role context, because W7 enforces grid homogeneity per (section, track) Phrase and grid-blind fill tiling mixes a triplet fill into straight-grid snare content. The 12/8 feel lives on the gated slow-blues mains' ride/kick.]*

```yaml
- { id: bl_dr_2, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 3, events: [
    {pos: 0, voice: kick, velocity: 0.90}, {pos: 960, voice: kick, velocity: 0.86},
    {pos: 480, voice: snare, velocity: 0.88}, {pos: 1440, voice: snare, velocity: 0.85},
    {pos: 0, voice: hat_closed, velocity: 0.60}, {pos: 240, voice: hat_closed, velocity: 0.42},
    {pos: 480, voice: hat_closed, velocity: 0.52}, {pos: 720, voice: hat_closed, velocity: 0.42},
    {pos: 960, voice: hat_closed, velocity: 0.56}, {pos: 1200, voice: hat_closed, velocity: 0.42},
    {pos: 1440, voice: hat_closed, velocity: 0.52}, {pos: 1680, voice: hat_closed, velocity: 0.44}]}
```

**Bass** (`mode: patterns`; the boogie identity): rung 1 — root halves (ungated) + tempo-gated sparse triplet arpeggios (root on 1, fifth/third on triplet positions, space); rung 2 — the box, quarters (`root, fifth, seventh, root(octave: 1)`); rung 3 — the full 2-bar boogie cell, quarters:

```yaml
- { id: bl_bs_3, kind: main, energyLevel: 3, lengthTicks: 3840, weight: 1, events: [
    {pos: 0,    dur: 480, degree: root,    octave: 0, velocity: 0.76},
    {pos: 480,  dur: 480, degree: third,   octave: 0, velocity: 0.70},
    {pos: 960,  dur: 480, degree: fifth,   octave: 0, velocity: 0.72},
    {pos: 1440, dur: 480, degree: sixth,   octave: 0, velocity: 0.70},
    {pos: 1920, dur: 480, degree: seventh, octave: 0, velocity: 0.74},
    {pos: 2400, dur: 480, degree: sixth,   octave: 0, velocity: 0.70},
    {pos: 2880, dur: 480, degree: fifth,   octave: 0, velocity: 0.72},
    {pos: 3360, dur: 480, degree: third,   octave: 0, velocity: 0.70}]}
```

Rung 4 — shuffled-8th boogie (straight-8th authoring, swing renders) with a `push`-flagged bar-end root. **Comping**: rung 1 sustained + tempo-gated triplet-roll pattern (chord hits on triplet positions); rung 2 the chank (2 & 4 stabs); rung 3 Charleston + gap stabs; rung 4 driving stabs with pushes. Voicing classes `{1: [shell2, triad_open], 2: [shell3, rootless_a], 3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}` — the rootless-9th stab sound. **Pads**: organ footballs, `{1–4: [triad_open, fifths]}`.

### 5.5 `transitions.yaml`

```yaml
phraseFill: { odds: [1, 2] }             # blues fills often
stop:       { enabled: true, odds: [1, 3] }  # the 1-beat band stop into a rung-4 chorus
crash:      { velocity: [0.45, 0.90] }
mutation:
  drums:   { none: 8, kick_pickup: 2, drop_ornament: 1, hat_lift: 1 }
  comping: { none: 3, anticipate: 2, drop_hit: 1 }
```

### 5.6 `timbres.yaml` defining entries

- `blues_kit`: roomy MembraneSynth kick (decay 0.45), cracky NoiseSynth snare (white, decay 0.11), prominent MetalSynth ride; `roadhouse_kit` darker/drier.
- `electric_round` (bass): MonoSynth triangle, lowpass rolloff −12, round attack band (attackHardness override 0.06→0.004); dry.
- `crunch_guitar` (comping): PolySynth/MonoSynth sawtooth + `Distortion {distortion: 0.3, oversample: "2x", wet: 0.6}`.
- `organ_drawbar` (comping alt): PolySynth/AMSynth sine + `Tremolo {frequency: 5.2, depth: 0.4, spread: 90, wet: 0.5}` + light Distortion; brightness → `harmonicity` 1.0–2.0 (the PHASE_7 `organ_soft` lever).
- `organ_swell` / `warm_strings` (pads): AMSynth swell + Tremolo / fat-saw strings + StereoWidener.
- Bus `reverb: { decay: [0.8, 2.5], preDelay: [0.01, 0.03], returnFilterHz: 350 }`; master = pop_rock-style gentle glue.

---

## 6. Pack design — `fusion_jazz`

### 6.1 Manifest & interpreter

```yaml
# styles/fusion_jazz/manifest.yaml
formatVersion: 1                 # [amended 2026-07-21, S22-1 (user-ratified): printed
id: fusion_jazz                  #  snippet omitted the required Manifest fields]
name: Fusion Jazz
version: 0.1.0
engine: ">=0.1"                  # [amended 2026-07-21, S22-1: sibling-verbatim value]
timeSignatures: [[4, 4]]
tempoRange: [75, 145]            # core funk-fusion 85-120 + the medium tier
```

```yaml
# styles/fusion_jazz/interpreter.yaml
supportedMoods: [energetic, calm, mysterious, dreamy, nostalgic, triumphant, happy, tense]
defaultMood: energetic
# vs the PHASE_2 §5 sketch ("fusion sits near jazz"): near but not identical —
# fusion picks up triumphant (jazz dropped it) and drops romantic/dark/melancholic.

modes: [major, mixolydian, dorian, minor]   # [amended 2026-07-21, S22-2 (user-ratified):
                                 #  the printed `[dorian, mixolydian, minor, major]` is a HARD
                                 #  LOAD FAILURE — `packs/models.py` requires `modes` to be a
                                 #  subsequence of the mode ladder `major, mixolydian, dorian,
                                 #  minor, phrygian`. Reordered here, `tonics` reordered to
                                 #  match. Behaviourally inert: `_resolve_mode` is set-based
                                 #  with a brighter-rung tie-break and returns the identical
                                 #  mode for all 8 fusion moods under either ordering. The
                                 #  printed "the first dorian-primary pack" gloss is a wrong
                                 #  derived claim — see the S22-6 note below.]
tonics:
  major:      [F, C]
  mixolydian: [F, Bb]
  dorian:     [D, G, Bb]         # Bb dorian = Chameleon — [amended 2026-07-21, S22-8: auto
                                 #  renders take `tonics[mode][0]` = **D**; the Chameleon key
                                 #  Bb requires an explicit `key.tonic` param]
  minor:      [C, A]

feel: swing16                    # NO swingRatio override: the table evaluated at 2×tempo gives
                                 # 58% at 100 BPM → straight at ~120+ — matching the funk corpus.
                                 # At the slow edge (75-90) it reaches 61.5-65.5% — Purdie-shuffle
                                 # territory, accepted; revisit via the §8.4 error-spotting log.
                                 # [amended 2026-07-21, S22-8: the printed "63-66%" is a wrong
                                 #  derived sample; measured 61.5-65.5% across 75-90 BPM. The
                                 #  "58% at 100 BPM" and "straight at ~120+" figures are exact.]
feelTable: tight                 # §3.4

expressionRanges:
  density:    [0.30, 0.90]
  dissonance: [0.55, 0.90]       # m9/11 floor

flavors:
  drums:   [funk_kit, fusion_ride_kit]
  bass:    [synth_moog, electric_finger]
  comping: [rhodes, clav]
  pads:    [analog_poly, glass_pad]

ensembles:
  default:     { drums: funk_kit, bass: synth_moog, comping: rhodes, pads: analog_poly }
  headhunters: { drums: funk_kit, bass: synth_moog, comping: clav, pads: analog_poly }
```

*[amended 2026-07-21, S22-6 (user-ratified), C-28: **"the first dorian-primary pack" is a wrong derived claim.** Measured auto mode-resolution (`_ideal_rung` → `_resolve_mode`) over the eight supported moods resolves **major 6 of 8**, dorian 1, minor 1:*

| mood | resolved mode |
| --- | --- |
| energetic · calm · dreamy · nostalgic · triumphant · happy | **major** (6/8) |
| mysterious | **dorian** (1/8) |
| tense | **minor** (1/8) |

*and **`mixolydian` is structurally unreachable** — `_ideal_rung` places it at valence ∈ [0.00, 0.25) and no fusion mood lands in that band, so `sus_pedal` / `mixo_vamp` / `dominant_16` / `sus_chain_mixo` / `mixo_groove_in` / `backdoor` are auto-dormant (P6 requires the coverage regardless). The §8.2 corpus triple (energetic, calm, tense) therefore captures **zero dorian cells**; `tests/test_fusion_jazz_pack.py` compensates with explicit `key.mode: dorian` pins (Bb and D) covering the `cantaloupe_class` / `dorian_funk` / quartal paths. Dorian remains the pack's *idiomatic* centre — it is simply not its auto-resolution majority.]*

### 6.2 `forms.yaml`

```yaml
energyRange: [0.20, 0.95]

sections:
  intro:     { bars: [[4, 3], [8, 1]], phrases: { 4: [a], 8: [a, a] },
               harmonyTag: { 4: intro, 8: intro } }
  head:      { bars: [[16, 3], [32, 1]],
               phrases: { 16: [a, b, c, d], 32: [a, a, b, a] },
               harmonyTag: { 16: tune_16, 32: modal_32 } }
  solo:      { inherit: head }
  main:      { bars: [[8, 1]], phrases: { 8: [a, a] }, harmonyTag: { 8: vamp } }
  breakdown: { bars: [[8, 1]], phrases: { 8: [a, a] }, harmonyTag: { 8: vamp } }
  outro:     { bars: [[4, 1]], phrases: { 4: [a] }, harmonyTag: { 4: vamp } }

templates:
  - id: tune                     # Cantaloupe / Watermelon / Maiden Voyage class
    weight: 60
    spine:
      - { section: intro, optional: [1, 1] }
      - { section: head }
      - repeat: { count: [1, null], slots: [ { section: solo } ] }
      - { section: head }
      - { section: outro }
    ending: { tagBars: 0, close: cold }
    degrade:
      - { shrink: intro }
      - { drop: intro }
      - { drop: outro }
    fallback: { section: solo, bars: 16 }

  - id: vamp                     # Chameleon class: groove vehicle with strip-down/rebuild
    weight: 40
    spine:
      - { section: intro }
      - repeat: { count: [2, null], slots: [ { section: main } ] }
      - { section: breakdown }
      - { section: main }
      - { section: outro, optional: [2, 1] }
    ending: { tagBars: 0, close: fade }
    degrade:
      - { drop: outro }
      - { shrink: intro }
      - { drop: breakdown }
      - { drop: intro }
    fallback: { section: main, bars: 8 }
```

(`outro` shares the `vamp` tag — vamp-out is the genre's ending. In the `tune` template, sharing works because tags are drawn per song, not per template: a `tune` render draws `vamp` only for its outro, giving a groove-loop tag under the close — idiomatic.)

### 6.3 `progressions.yaml` (defining entries)

```yaml
pools:
  tune_16:
    - id: cantaloupe_class        # i7 | bVI7#11 | vi7 | i7, 4 bars each
      weight: 60
      modes: [minor, dorian]
      phrases:
        a: [[i7], [~], [~], [~]]
        b: [[bVI7(#11)], [~], [~], [~]]      # authored extension (§3.5)
        c: [[vi7], [~], [~], [~]]
        d: [[i7], [~], [~], [~]]
    - id: dominant_16             # Watermelon-class 16-bar dominant blues
      weight: 40
      modes: [mixolydian, major]
      phrases:
        a: [[I7], [~], [~], [~]]
        b: [[IV7], [~], [I7], [~]]
        c: [[V7], [IV7], [V7], [IV7]]
        d: [[I7], [~], [~], [~]]
  modal_32:                       # sus-chain AABA (Maiden Voyage shape)
    - id: sus_chain
      weight: 100
      modes: [dorian, minor]
      phrases:
        a: [[I7sus4], [~], [~], [~], [bIII7sus4], [~], [~], [~]]
        b: [[bII7sus4], [~], [~], [~], [VIImaj7], [~], [~], [~]]
    - id: sus_chain_mixo          # P6 coverage for the major-class modes
      weight: 100
      modes: [mixolydian, major]
      phrases:
        a: [[I7sus4], [~], [~], [~], [bVII7sus4], [~], [~], [~]]
        b: [[IV7sus4], [~], [~], [~], [bVImaj7], [~], [~], [~]]
  vamp:
    - { id: dorian_funk,  weight: 40, modes: [dorian, minor],
        phrases: { a: [[i7], [~], [IV7], [~]] } }                  # Chameleon
    - { id: sus_pedal,    weight: 20, modes: [mixolydian, major],
        phrases: { a: [[I7sus4], [~], [~], [~]] } }
    - { id: minor_launch, weight: 20, modes: [minor, dorian],
        phrases: { a: [[iiø7], [V7(#9)], [i7], [~]] } }
    - { id: mixo_vamp,    weight: 20, modes: [mixolydian, major],
        phrases: { a: [[I7], [~], [bVII7], [~]] } }
  intro:
    - { id: groove_in,      weight: 100, modes: [dorian, minor],
        phrases: { a: [[i7], [~], [IV7], [~]] } }                  # ends open (P7)
    - { id: mixo_groove_in, weight: 100, modes: [mixolydian, major],
        phrases: { a: [[I7], [~], [bVII7], [~]] } }

turnarounds: []                   # vamps and static 16-bar forms loop untouched (§3.3)
                                  # [amended 2026-07-21, S22-3, C-27: NOT untouched — an empty
                                  #  list disables only the turnaround transform; the deceptive
                                  #  fallback still fires on every tonic-rooted T-function
                                  #  ending at a same-tag boundary. `minor_launch` and
                                  #  `sus_pedal` are authored re-rotated to end open; see the
                                  #  §3.3 S22-3 annotation for the rule and the measurements.]

finals:
  - { id: dorian_plagal, weight: 60, modes: [dorian, minor], bars: [[IV7], [i7]] }
  - { id: sharp_nine,    weight: 40, modes: [dorian, minor], bars: [[V7(#9)], [i7]] }
  - { id: backdoor,      weight: 100, modes: [mixolydian, major], bars: [[bVII7], [I7]] }
```

### 6.4 Pattern-bank conventions & defining entries

**Drums**: rung 1 — sparse funk (kick 1, cross-stick, 8th hats); rung 2 — light 16th funk: syncopated kick, snare 2/4, 8th hats with **hard quarter accents** (the research insists the groove fails without them); rung 3 — full funk: `minDensity`-gated 16th hats, ghost snares, plus a second weighted entry with the **displaced backbeat** (snare on the "a" of 1, tick 360 — Chameleon's signature); rung 4 — **ride-based drive**: ride 8ths + busy kick. A verified machinery fact makes rung 4 automatically tight: `swing16` displaces only `pos % 240 == 120` events, so 8th-grid ride lines pass through straight. Fills: 16th linear figures, busier than jazz.

```yaml
- { id: fu_dr_2, kind: main, energyLevel: 2, lengthTicks: 1920, weight: 3, events: [
    {pos: 0, voice: kick, velocity: 0.92}, {pos: 720, voice: kick, velocity: 0.78},
    {pos: 1200, voice: kick, velocity: 0.72, minDensity: 0.50},
    {pos: 480, voice: snare, velocity: 0.90}, {pos: 1440, voice: snare, velocity: 0.88},
    {pos: 1080, voice: snare, velocity: 0.25, minDensity: 0.60},   # ghost, e-of-3
    {pos: 0, voice: hat_closed, velocity: 0.62}, {pos: 240, voice: hat_closed, velocity: 0.40},
    {pos: 480, voice: hat_closed, velocity: 0.58}, {pos: 720, voice: hat_closed, velocity: 0.40},
    {pos: 960, voice: hat_closed, velocity: 0.60}, {pos: 1200, voice: hat_closed, velocity: 0.40},
    {pos: 1440, voice: hat_closed, velocity: 0.58}, {pos: 1680, voice: hat_closed, velocity: 0.42}]}
```

**Bass** (`mode: patterns`): rung 1 — root/♭7 (`seventh`) half notes; rung 2 — the **tresillo skeleton** (3+3+2 in 16ths: `root` @0 dur 360, `seventh` @360 dur 360, `root` @720 dur 480 …) *[amended 2026-07-21, S22-11 (user-ratified): the printed parenthetical is internally inconsistent. The prose "3+3+2 in 16ths" is 360 + 360 + 240 = **960** ticks — a half-bar cell, doubled per bar — but the printed third duration **480** overruns the next cell's onset by 240 ticks, and nothing downstream truncates it (`retrigger` splits only at **chord** boundaries; there is no note-overlap validator), so the printed reading emits two simultaneously sounding bass notes. Per ROADMAP §3 arbitration rule 1 the **prose wins**: the literal 3+3+2 doubled cell is the rung-2 anchor (`fu_bs_2`, weight 3). The printed `dur 480` is a **wrong printed sample**; it is retained as the weight-2 sibling `fu_bs_2b`, re-read as a valid whole-bar 3+3+4+3+3 ostinato, for variety.]*; rung 3 — 16th funk: root/octave with low-velocity `minDensity`-gated ghost 16ths on the e/a; rung 4 — dense 16ths, octave pops, `approach` into changes, pushes *[amended 2026-07-21, S22-14 (user-ratified): **`approach` composed with `push` is broken** — `push` advances the retarget frame to the chord *after* the first boundary in the note's span, so the `approach` degree resolves against the chord **two changes ahead**. ~~Measured over 48 renders: **0 of 399** approach firings resolved correctly as authored; **72 of 408** resolved correctly with `push` removed.~~ `push: true` is therefore **dropped from the `approach` events** (pushes stay on the non-approach events of the rung-4 bank). ~~**Accepted residual:** the pattern tiles every bar while fusion's chords span 2–4 bars, so roughly half of all firings have no change to approach; measured **38 %** land on the root and **39 %** on a perfect 4th against the sounding chord (~24 % genuine tensions) — consonant, idiomatic, and preferable to replacing the device, which is why it is accepted rather than re-authored.~~ **Flagged for the §8.4 listening pass.**

*[corrected 2026-07-21, T10 lens A (instrumented at the production `retarget_event` call site) + orchestrator re-measurement: **the struck numbers above were contaminated and are withdrawn; the ruling itself stands.** The original sweep identified approach events **positionally** (`ticks % 1920 == 1680 and duration_ticks == 240`), but **four** rung-4 bass events share that shape — `fifth` (vel 0.66, `fu_bs_2`), `root` (0.72, `fu_bs_3`) and the two genuine `approach` events (0.80 `fu_bs_4`, 0.82 `fu_bs_4b`). The `fifth` and `root` notes are essentially never a half-step below the arriving chord root, so they diluted the numerator. **Isolating true approach notes by velocity, un-pushed on-change correctness is 16/16 = 100.0 %** (orchestrator) and **580/580 = 100.0 %** (lens A, larger sweep) — i.e. the T2 reviewer's original "100 %" claim was **correct**, and this note's earlier "0 % / 18 %" framing was the artifact. **`push` is still correctly dropped, for a different reason:** `apply_articulation` clamps the authored `dur: 240` to the gap (typically ~194 ticks), so the note usually ends *before* the barline, `_boundaries_in_span` is empty, and `push` silently falls through to the governing chord — `push` is therefore **inert on the large majority of firings and actively wrong on the remainder** (lens A: wrong on 116 of 1328). **Corrected accepted residual:** ~50 % of approach firings (orchestrator 16/32; lens A 56.3 %) have **no chord change at the next barline**, and in those bars the degree does **not** fall back to the governing chord as written above — `resolve_degree_pc` returns `(root(next timeline chord) − 1) % 12`, so the note is a **leading tone to a chord that has not arrived yet**. Against the *sounding* chord the orchestrator found 12 of 16 off-change notes inside chord tones ∪ scale and **4 outside (12.5 % of all approach firings)**; lens A measured 25 % of off-change notes outside (**14.1 % of all firings**). The honest statement is therefore **~12–14 % of approach firings are a short chromatic bass note against the sounding chord** — defensible for a ~194-tick bar-end pickup, but **not** "consonant, idiomatic and musically inert" as this note originally claimed.]*. **Comping** (Rhodes/clav): rung 1 footballs; rung 2 sparse syncopated stabs + and-of-4 `push`; rung 3 16th anticipations; rung 4 clav-style stabby 16ths. Voicing classes `{1: [quartal, rootless_a, rootless_b], 2: [quartal, rootless_a, rootless_b], 3: [rootless_a, rootless_b], 4: [rootless_a, rootless_b]}` — quartal harmony as the low-rung signature. **Pads**: `{1–4: [quartal]}`, sustained, retrigger.

*[amended 2026-07-21, S22-4 (user-ratified), C-27's sibling ruling: the printed rungs 1–2 classes `[quartal, rootless_a]` produce an **uncaught `ValueError`** (`src/trackgen/parts/voicing.py` — no candidate in any declared class). Quartal `[0, 5, 10, 15]` needs a 15-semitone span; the comping arrangement lane leaves a 7–9 semitone root window, and for `Bbm9` (i7+9 in **Bb dorian — §6.1's own pinned Chameleon key**) and `A7#9` (V7(#9) in D dorian) at comping lane low 50 (`registerBias ≥ +0.15` ⇒ moods calm/triumphant/happy) `rootless_a` is empty too, so both printed classes come back empty. Measured **54 of 1152** explicit-`key`-override renders crashed; an independent sweep of 20 304 (mood, key, token, rung) combinations found **38 empty** under the printed map and **0** under the ratified map. `rootless_b` is added as a third fallback at rungs 1–2; **quartal is still tried first**, so the pinned low-rung quartal signature is preserved. Data fix, no engine change.]*

*[amended 2026-07-21, S22-5 (user-ratified), C-28: **measured rung reachability.** The ladder is authored **exactly as printed — no re-map** (unlike blues' S21-2), because rungs 2–4 are all live and carry §6.4's defining content, and PT5 + the variety lint require a rung-1 bank regardless. But three dormancies are now measured facts a later session must know:*

| template / section | kind | energy range | live rungs |
| --- | --- | --- | --- |
| tune / intro · outro | intro · ending | 0.376–0.485 · 0.414–0.522 | rung ignored |
| tune / **head** | main | 0.526–0.635 | **2, 3** |
| tune / **solo** | main | 0.676–0.935 | **3, 4** |
| vamp / **main** | main | 0.526–0.710 | **2, 3** |
| vamp / **breakdown** | main | 0.339–0.448 | **2 only** |
| fallback / solo | main | 0.826–0.935 | **4 only** |

*— **rung 1 is dead grid-wide** (a proof, not a sample: rung 1 needs pre-envelope `e < 0.1333`, and the lowest base is `breakdown` 0.25 at the lowest arousal, calm −0.65 ⇒ `e = 0.185`); **rung 4 is `tune`-template-only** (`vamp` maxes at 0.710), so the rung-4 ride drive is a tune-template device; and **`breakdown` is arrangement-capped to 2 layers**, so it renders **drums + bass only** — its rung-2 comping/pads content never sounds there. Rung-1 banks are golden-blind completeness content (the C-20 class), selection-locked by `tests/test_fusion_jazz_variety.py`.]*

### 6.5 `transitions.yaml`

```yaml
phraseFill: { odds: [1, 2] }
stop:       { enabled: true, odds: [1, 4] }   # the funk break
crash:      { velocity: [0.45, 0.85] }
mutation:
  drums:   { none: 6, kick_pickup: 2, drop_ornament: 2, hat_lift: 1 }
  comping: { none: 3, anticipate: 2, drop_hit: 1 }
```

### 6.6 `timbres.yaml` defining entries

- `rhodes` (comping): PolySynth/FMSynth sine/sine; **brightness → `modulationIndex` 3–14** (per-flavor override — the mellow-Mark-I-to-bright-DX7 axis), `modulationEnvelope {attack: 0.002, decay: 0.4, sustain: 0, release: 0.2}` (the tine ping), carrier decay 2.2; light Chorus insert.
- `clav` (comping alt): PolySynth/MonoSynth sawtooth, attack 0.003 / decay 0.18 / sustain 0, resonant lowpass filterEnvelope (base ~400 Hz band via brightness, 4 octaves); insert `AutoFilter {frequency: 2.5, baseFrequency: 350, octaves: 2.5, depth: 0.5, wet: 0.4}` — the wah (§3.7).
- `synth_moog` (bass): MonoSynth sawtooth, `filter {type: lowpass, rolloff: -24, Q: 4}`, snappy filterEnvelope (base ~120 Hz band, 3.5 octaves); dry. `electric_finger`: triangle core, gentler filter, ~20 ms attack band.
- `analog_poly` (pads): PolySynth/MonoSynth fatsawtooth (count 3, spread 25), attack band around 0.35 s, + StereoWidener. `glass_pad`: brighter FM alternative.
- `funk_kit`: **tight and dry** — short decays everywhere (kick decay 0.22, snare 0.12, sustain 0), minimal sends. Bus `reverb: { decay: [0.6, 1.8], preDelay: [0.008, 0.02], returnFilterHz: 400 }` — the driest room of the five packs (70s damped-head practice as data). Master: `Compressor {threshold: -20, ratio: 2, attack: 0.03, release: 0.25}` + Limiter.

---

## 7. Reference-pack refinement

pop_rock and jazz run through the §9.3 authoring checklist **first** — they are the workflow's shakedown cruise before the three new packs. Their refinement scope: complete every `# …`-abridged bank entry (already an implementation DoD item in PHASE_5 §13.1 / PHASE_7 §13.1); run the calibration report and level pass (PHASE_7 Q1); run the §8.4 error-spotting protocol per supported mood; capture their golden/band artifacts. Content changes discovered by listening are pack-version bumps under the normal bless workflow — no design changes are anticipated, and none are made here.

---

## 8. Quality & evaluation framework

### 8.1 Validator suite — three layers (D9, D10)

**Layer 1 — hard pipeline invariants.** Runs on every render (tests, smoke, CI). Subsumes PHASE_1 §3.8 V1–V8 and adds pipeline-aware checks (they read the IRs, not just the document):

| # | Check |
| --- | --- |
| W1 | **Lane compliance**: every non-drum note within its `(section, role)` bias-shifted register lane from `ArrangementPlan` (stronger than V4's global ≤ 71). |
| W2 | **Device-policy compliance**: every section boundary carries what PHASE_6 §3.2's table assigns — `fill`-tagged events in the fill bar (or a rendered stop window), a `crash`-tagged entry downbeat; suppression classes (postchorus, breakdown) actually suppressed; dropout truncation applied on breakdown entries. |
| W3 | **Ending integrity**: song's final chord degree-1-rooted with `final` tags present; HOLD applied (no drum attack at/after `T_last` except the hold crash+kick; pitched holds extended to section end). |
| W4 | **Density-gate recheck**: no instantiated event whose authored `minDensity` exceeds its section's `densityBudget`. |
| W5 | **Determinism**: regenerate from `meta` — byte-identical document. |
| W6 | **Tag vocabulary**: all note tags from the pinned set (`ghost, push, fill, crash, var, hold`). |
| W7 | **Pre-humanizer grid legality**: stage-6 output onsets lie on the straight 8th/16th grid or the triplet grid per the §3.1 rule (checked per source pattern). |
| W8 | **Humanizer note-count preservation** per track (the PHASE_6 D1 contract, asserted end-to-end). |

**Layer 2 — musical rule checks.** Per render; warn by default, fail where marked:

- **L2-1 chord-tone-on-strong-beat ratio** (fail below threshold): for bass and comping, the fraction of notes attacking on beats 1/3 whose pitch class ∈ governing chord tones ∪ chord scale *[amended 2026-07-21, S22-13 (user-ratified), C-29: the allowed set is **widened** to `chord tones ∪ chord scale ∪ the alterations PHASE_4 §6.4 already declares legal for the chord's quality`* (for a dominant 7th: 9, ♭9, ♯9, ♯11, 13, ♭13). *Forcing reason: quartal's top voice is a **♯9**, which over a dominant 7th is canonical funk/jazz vocabulary (the Hendrix chord) — L2-1 as pinned was under-modelling altered tensions and failed **19 of 192** fusion renders on musically correct content. The widening is **strictly additive** (it can only admit pitches, never reject one it previously accepted) and reuses §6.4's existing legality table rather than inventing one. **Generation-neutral:** `quality/` is never imported by the generation path, so no golden moves and no `generatorVersion` bump.]*. Thresholds per style live in the pack's calibration artifact (§8.2); engine defaults: bass beat-1 ≥ 0.95, comping strong-beat ≥ 0.98. This is the highest-signal single metric for retargeting/voicing bugs. *[amended 2026-07-21, S23-2 option D (user-ratified), C-32: the allowed set is **widened once more**, to admit the **perfect fourth above the chord root** (the natural 11) — but **only for a `(role, section)` whose pack voicing classes declare `quartal`* (`pack.voicing[role].classes[rung]`, read at the rung the arrangement assigned that section). *Forcing reason, the exact shape of C-29's: `theory/voicing.py:185` resolves `quartal` to `[[0, 5, 10, 15]]`, so offset 5 — the natural 11 — is a **structural voice of every quartal voicing**, and §6.4 pins quartal as fusion_jazz's signature low-rung comping harmony. §6.4's tension table withholds `11` from a dominant 7th, correctly as a rule about *dressing a chord symbol* (the avoid note that makes `7sus4` a separate quality) — but here the fourth is not dressing, it is a voice the pack's own pinned table was told to sound. L2-1 was therefore counting the pack's signature voicing as wrong. **Mechanism, and why it is narrow:** nothing downstream of `parts/voicing.py::build_voicing_map` records which candidate class won the Viterbi pass, so per-note provenance does not exist; the widening instead keys off the pinned pack data that *produced* the candidate. That confines it on three independent axes — only roles with a `voicing:` block (`bass` has none, on any pack), only rungs naming `quartal` (of the five shipped packs, only fusion_jazz comping rungs 1–2; jazz's quartal is on **pads**, which L2-1 does not measure), and only sections at such a rung (fusion's rungs 3–4 are unaffected). **Strictly additive**, like C-29: exactly one pitch class is ever unioned in, never one removed, so nothing that passed before can fail now. **Measured at depth** — 80 seeds × all moods × 5 lengths (60/120/180/240/300 s) × 5 packs, 18 000 renders / 36 000 (track, role) rows: fusion comping fell from **30 failing rows to 0** (451 out-of-set strong-beat notes to 0), the four other packs measured **byte-identically — 0 rows changed, 0 failures before or after**, and fusion bass was untouched. No threshold moved. **Generation-neutral:** `quality/` is never imported by the generation path, so no golden moves and no `generatorVersion` bump.]*
- **L2-2 voice crossing** (warn): whenever bass and comping sound simultaneously, `max(bass) < min(comping)`.
- Deliberately absent: parallel-fifths/octaves failure — rock parallel fifths are idiomatic; voice-leading quality is the Viterbi optimizer's job, not a gate.

**Layer 3 — statistical style bands.** Batch-only, warn-only. Six MusPy-shaped metrics per track: per-role note density (notes/bar), mean IOI, pitch range, empty-bar rate, groove consistency (mean Hamming distance between adjacent bars' drum-onset vectors), scale consistency. Bands = per-`(pack, mood)` mean ± 2.5 SD computed from the blessed calibration batch, stored as a **generated, committed artifact** `styles/<pack>/calibration.yaml` (also home of the L2 thresholds). Distribution-comparison machinery (KLD/OA) is explicitly not used — noise at our N (D9).

**Bootstrap order** *(note added 2026-07-08)*: L2 thresholds and L3 bands read from `calibration.yaml`, which `trackgen calibrate` computes from a blessed batch — circular until a pack's first batch exists. The cycle breaks exactly as §9.4 already sequences it: Layer 1 (W1–W8) plus L2 at its engine defaults (0.95/0.98) gate the first renders; the first calibration batch is accepted by *listening* (§9.4 steps 7–9), not by Layer 3; `trackgen calibrate` then writes the pack's first `calibration.yaml` (step 8), activating pack-specific L2 thresholds and L3 bands for every subsequent run; goldens are captured only after that (step 10). A pack's first blessed corpus is therefore L3-unvalidated by construction — expected, not a gap.

### 8.2 Golden corpus & the bless workflow (D11)

- **Corpus**: the two chained worked examples (PHASE_2 §6.5 → PHASE_6 §7) remain the master goldens; plus a matrix of **5 packs × 3 moods (default + the supported set's V/A extremes) × 2 lengths (120 s, 240 s) × 2 seeds = 60 tracks**. Each fixture stores **every IR boundary** — GenerationPlan, SongForm, HarmonicPlan, ArrangementPlan, Phrases post-stage-5/6/7 (+ tempo events), SoundDesign, TrackDocument — as exact JSON (`fixtures/goldens/<pack>/<mood>/<length>-<seed>/<stage>.json`). A golden diff therefore localizes to the **first divergent stage**.
- **Bless workflow** (the LilyPond/ApprovalTests model): `trackgen bless` re-renders the corpus and emits a **semantic diff report** — per track: first divergent stage; notes added/removed/moved per document track/section; Layer-3 metric deltas; never raw JSON diffs. Two legal moves on any diff: fix the code, or `bless --approve`, which rewrites baselines in a **dedicated commit** and verifies a `generatorVersion` bump accompanied the change (the append-only draw discipline made mechanical). Reflexive re-blessing is the failure mode the report format exists to prevent: the report is small enough to actually read.
- **Smoke matrix**: every pack × supported mood × 3 length buckets (60/180/480 s) × 5 seeds, running Layers 1–2 — the five-pack generalization of every prior phase's property tests. Periodically (nightly/weekly), a 300-seed sweep on the two reference packs bounds per-cell failure below ~1 % (rule of three).

### 8.3 What Layer 3 and the goldens are *not*

No audio-rendered regression (documents are the deterministic artifact; audio adds FP nondeterminism for no defect class we can't catch upstream); no neural/corpus-similarity scoring; no aesthetic gates in CI. Subjective quality is §8.4's job, by humans, cheaply.

### 8.4 Listening-test workflow (D12)

MUSHRA is explicitly rejected (it measures fidelity to a reference; generated music has none). Three right-sized instruments:

1. **Error-spotting protocol** (per iteration session): render fresh seeds for the cells under test; listen against a fixed checklist — wrong-pitch moment · groove stumble · dead/abrupt transition · register clash or mud · ending failure · "would I solo over this?" — logging entries as `{params, seed, time-in-track, category, note}` to `listening/log.jsonl`. Every complaint is reproducible by construction (the seed system's purpose); recurring categories graduate into Layer-1/2 validator candidates. This is also the designated evidence collector for every listening-gated deferred question (§3.8's last row).
2. **Pairwise A/B** (per engine change with audible intent): identical seeds rendered old-vs-new, presentation order blinded, "which sounds better" forced choice, ~20 trials → binomial significance, workable for a single listener.
3. **Anchored milestone rubric** (milestones only): 5-point scales with written anchor descriptions per point on four axes — musicality, groove, style-fit, soloist space — scored per pack × 3 moods.

Named listening tasks inherited from PHASE_7: **T1 level calibration** (Q1: adjust pack mix data until the summed reference tracks balance; re-run the calibration report), **T2 FM-piano adequacy** (Q7: A/B the `piano`/`rhodes` flavors in-ensemble; outcome either "acceptable" or a documented push toward PHASE_1 Q8 sampling).

---

## 9. Authoring workflow & tooling

### 9.1 Audition CLI (build first — D13)

`trackgen audition --pack blues --mood energetic [--seed X] [--section solo-2] [--solo drums] [--mute pads] [--tempo 105] [--out fixture.json | --play]`

- `--play` writes the fixture and opens the Phase 1 playground on it; `--section` renders one section's span (independently reproducible by the per-section/per-bar sub-stream design); `--solo`/`--mute` filter tracks at serialization.
- The edit→hear loop is the whole game (the BiaB single-cell / Yamaha looping-section lesson); everything else in this section exists to serve it.

### 9.2 Pack linter (D13)

`trackgen lint styles/<pack>/` — two tiers:

- **Errors**: every existing loader rule (F1–F13, P1–P11, PT1–PT12, TR1–TR7, TB1–TB9, interpreter rules) with file/line context.
- **Warnings** (authoring quality, non-blocking): **variety coverage** — any `(role, kind, rung)` slot where ≤ 1 candidate survives all gates for some supported (mood, tempo) cell, i.e. zero reroll variety (the BiaB "< 3 candidates" idea, adapted); **grid mixing** — a pattern with both straight-grid and triplet-grid events (§3.1's rule); **unreachable content** — patterns/rungs no reachable energy can select (lo-fi rung 4 — annotatable as `# expected-unreachable` to silence); **dangling gates** — eligibility bands no supported mood/tempo can enter; **weight degeneracy** — a pool where one entry holds > 90 % of weight.

### 9.3 Selection log & calibration report (D13)

- `--explain` on any render emits the per-slot decision trace: template draw and candidates, per-tag pool picks with surviving candidate counts, per-`(role, kind, rung)` pattern picks, device/mutation draws and no-ops, dressing tier per slot. (The `DrumAudioResults.txt` idea.) It doubles as the debugging tool and feeds the bless diff report.
- `trackgen calibrate styles/<pack>/` batch-renders the pack across its moods and reports: per-track velocity/level distributions vs the PHASE_7 channel-table intent, per-section note density vs budgets, tempo-band violations, and (re)computes the §8.1 Layer-3 bands + L2 thresholds into `calibration.yaml`.

### 9.4 The authoring checklist (normative per-pack process)

1. `manifest.yaml` + `interpreter.yaml` (moods, modes, tonics, feel + `feelTable`, ranges, flavors) — lint.
2. `forms.yaml` — lint; audition form skeletons via `--explain` (no audio needed yet).
3. `progressions.yaml` — lint (P-rules + cross-file); audition harmony with stub patterns.
4. Pattern banks, role by role, **rung by rung, auditioning each rung in isolation as it is written** (`--section` + `--solo`).
5. `transitions.yaml` — audition boundaries specifically (a fill bar, a stop, the ending).
6. `timbres.yaml` — audition each flavor solo, then ensembles.
7. Full-track audition per (mood × template) — the whole supported grid at least once.
8. `trackgen calibrate` + the T1-style level pass; adjust pack data, not code.
9. §8.4 error-spotting pass; fix or file every entry.
10. Capture goldens + calibration bands; stamp `version`; commit.

Order of packs: pop_rock → jazz (refinement shakedown, §7) → chill_lofi → blues → fusion_jazz (new-pack build-out, simplest first).

---

## 10. Worked sketch (hand-computable slice)

Draw-dependent values (template/pool/pattern picks) land with the implementation goldens; everything below is deterministic arithmetic from pinned tables, chained from the PHASE_2 machinery. **`chill_lofi` / defaults** (`{styleFamily: "chill_lofi"}`, mood → nostalgic, V +0.30 / A −0.35):

- **Tempo**: center 86.5 (§4.4 table) → auto range `[78, 95] ∩ [68, 95]` = `[78, 95]` — a seeded draw inside the genre band.
- **Key**: V +0.30 ≥ +0.25 → ideal rung `major`; menu `[minor, dorian, major]` → `major`, tonic C. (Melancholic → `minor`/A; mysterious → ideal `dorian` → D dorian — the menu covers the ladder's low rungs.)
- **Budgets**: densityNorm 0.428 → `0.15 + 0.428 × 0.40` = **0.321**; dissonanceNorm 0.310 → `0.40 + 0.310 × 0.25` = **0.478** → **tier 3** — 9ths on tonic-function 7ths (T offset −1 → tier 2 → plain 7ths on I; S/O at 3; D at 4). The "7ths default, 9ths as color" finding, reproduced by arithmetic.
- **Swing**: `swing16`, pack ratio override → `{ratio: 0.57, subdivision: "16"}`.
- **Energy** (loop_ab shape, arousal −0.035, envelope `[0.25, 0.60]`): intro base 0.30 → **0.343**; main-1 0.50 → **0.413** (rung 2); breakdown 0.25 → **0.325** (rung 2, but layer-capped at 2 and dropout-entered); main-2 0.55 (R1) → **0.430** (rung 2); main-3 0.60 → **0.448**. Flat dramaturgy: the whole song lives inside rung 2 with arrangement doing the contrast — exactly the genre.
- **Arrangement**: `layersMax` 3 (A ≤ 0.3) → mains run drums+bass+comping; pads enter never at defaults (count = min(3, base 3)) — *[amended 2026-07-20, S20-5, C-22: the original "pads are reserved for higher-arousal moods … with rung-3 sections" claim was a wrong derived sample — no supported mood reaches rung 3 (max measured energy 0.474, happy), so pads never enter in any v1 render; ensembles only swap flavors, never layer counts]*; breakdowns drop to drums+bass, then dropout cuts the entry. densityBudget main-1 = `0.321 × (0.7 + 0.6 × 0.413)` = **0.304** — most `minDensity`-gated ornaments (0.45–0.75) stay out: sparse, as designed.

---

## 11. Decisions log

| # | Decision | Rationale | Rejected alternatives |
| --- | --- | --- | --- |
| D1 | **Blues meter: 4/4 + swing8 + explicit triplet-grid authoring, tempo-gated; one-grid-per-pattern rule (linted); no swingRatio override** | Zero machinery: the tempo-dependent swing table already matches measured shuffle ratios; triplet positions are authorable (pos was never grid-locked) and swing-transform-invisible; eligibility tempo bands were built for this | True 12/8 pack (per-signature humanizer beat classes + feel tables — a PHASE_6 amendment for one pack); per-tier signature switching (Interpreter machinery on top) |
| D2 | **Lo-fi A/B = `main`/`breakdown` alternation; one shared `harmonyTag`; `variant` label-only in v1; loops authored rotated-open** | The genre's variation is subtractive (drum dropouts) — which is our dormant `breakdown`+`dropout` machinery verbatim; shared tag = loop identity by construction (the head/solo mechanism); P7 compliance falls out of loop-friendly rotation | Load-bearing `variant` (cache-key + eligibility + slot-tag amendments to PHASE_3/5 for a contrast the genre doesn't center); two-tag A/B (breaks "the track is one loop") |
| D3 | **All three new packs `mode: patterns`; blues bass = authored boogie cells (resolves PHASE_5 Q4); walking blues stays in the jazz pack** | Boogie/riff/static basses are locked loops — pattern vocabulary exactly (the `sixth` degree's reserved purpose); the walker can't lock a riff; jazz already ships walked blues, keeping the packs maximally distinct | Mixed per-pack mode (PHASE_5 selection amendment to serve a corner jazz covers); walker-with-boogie-parameters (wrong tool — contour engine vs locked riff) |
| D4 | **Fusion = `tune` + `vamp` template families** | Matches the researched form split (16-bar/AABA tune vehicles vs vamp-throughout grooves); exercises head/solo at 16 bars and main/breakdown in a second style; `turnarounds: []` + PHASE_4 D6 inertness keeps tonic-ending vamps loop-clean — verified against the Cantaloupe failure case | Cyclic-only (loses the genre's center of gravity); vamp-only (loses the jam vehicles practicing musicians want) |
| D5 | **Humanizer feel = named engine profiles (`straight/swung/laidback/tight`) + optional pack `feelTable` selector (resolves PHASE_6 Q7)** | The two-table model provably fails at five packs (lo-fi laid-back vs fusion tight, both swung); engine-data-plus-selection is the project's own pattern; jitter/accents stay global pending evidence | Per-pack feel authoring (psychoacoustically fragile calibration data spread over five files); doing nothing (contradicts both packs' research) |
| D6 | **Authored chord extensions: parenthesized extension groups after an explicit quality; authored = fully pinned, draw-free (resolves PHASE_4 Q1)** | Fusion's defining colors (#11, slot-pinned #9) are unreachable by dressing; parentheses parse unambiguously against digit-bearing qualities and match lead-sheet practice; full-pin extends the existing bare/suffixed logic one level | Scale-hint-only approximation (the #11 never sounds in voicings); per-pack dressing overrides (heavier, can't pin slots — and now evidenced unnecessary, D7) |
| D7 | **Disposition table §3.8**: stop-time, riser, SHOT, doubled-chorus/deceptive, bass mutation ops, per-pack dressing → deferred with updated evidence; percussion role, lydian, per-pack mood/mod_defaults overrides, multiple repeat blocks → resolved-not-needed | Each verified against the three pack designs rather than argued in the abstract; the recurring "do global tables survive five packs" question gets a per-table verdict | Forcing dormant machinery awake for content that doesn't need it; leaving the questions unadjudicated for implementation to trip over |
| D8 | **Pack mood lists as pinned in §4–§6, deviating from the PHASE_2 §5 sketch where research demanded** (lo-fi drops energetic; blues drops happy+calm; fusion gains triumphant, drops romantic/dark/melancholic) | PHASE_2 §5.1 explicitly made final lists a Phase 8 authoring decision; each deviation traces to genre evidence; defaults = each genre's most-shipped affect | Following the sketch literally (ships energetic lo-fi — a contradiction in terms) |
| D9 | **Validator suite = 3 layers: hard W1–W8, musical L2 (chord-tone ratio + voice crossing), statistical L3 bands (mean ± 2.5 SD per pack×mood); no KLD/OA; no parallel-fifths gate** | Rule-based failure modes are bugs, not drift — near-deterministic single-render checks carry the signal (Yang & Lerch's own framing); distribution comparisons are noise at our N; rock parallel fifths are idiomatic | Neural-evaluation metric stacks (wrong tool); music21 counterpoint gating (chorale rules on a rhythm section) |
| D10 | **Layer-3 bands + L2 thresholds live in a generated, committed `calibration.yaml` per pack** | Bands are style data (jazz density ≠ lo-fi density) derived from blessed output — regenerate-on-bless keeps them honest; committing makes drift reviewable | Engine-global thresholds (wrong across styles); uncommitted/recomputed-per-run bands (silent drift) |
| D11 | **Golden corpus: exact JSON at every IR boundary, 60-track matrix + the master worked examples; `bless` with semantic diff report, dedicated commit, generatorVersion-bump check; document-level only (no audio regression)** | IR-level goldens localize a diff to the first divergent stage (nine-stage pipeline's payoff); the LilyPond mandatory-human-review model prevents rubber-stamp blessing; audio rendering adds FP nondeterminism and catches nothing documents don't | TrackDocument-only goldens (every diff investigation restarts from stage 1); rendered-audio null tests (flaky, redundant); byte-diff reports (unreadable → reflexive blessing) |
| D12 | **Listening = error-spotting counts (seed-keyed, checklist-driven) + pairwise A/B at identical seeds (~20 trials) + anchored 4-axis milestone rubric; MUSHRA rejected** | The generation-literature consensus (pairwise beats absolute at small N; Jukebox/MusicGen practice); error counts turn fuzzy quality into reproducible, validator-graduating data; the seed system makes every complaint a permalink | MUSHRA (needs a reference + trained panel; measures fidelity, not musicality); unstructured listening (unreproducible, unaccumulating) |
| D13 | **Tooling order: audition CLI → pack linter (variety/grid/unreachable warnings) → `--explain` selection log → calibration report; authoring checklist pinned §9.4; reference packs run the checklist first** | Edit→hear speed dominates authoring productivity (BiaB/Yamaha/FMOD lesson); coverage linting and selection logs are the two highest-value ideas in shipped style tooling; shakedown on known-good packs de-risks the process before new content | Linter-first (nothing to hear); golden tooling first (regression polish before there's content to regress) |
| D14 | **Pack tempo ranges/feels as pinned**: lo-fi [68, 95]/swing16@0.57/laidback; blues [50, 150]/swing8-table/straight; fusion [75, 145]/swing16-table/tight | Each triple traces to measured genre bands; two of three packs need **no** ratio override (the PHASE_2 table's tempo-dependence matches shuffle and funk measurements — verified arithmetic, §5.1/§6.1) | Flat per-pack ratios (measurably wrong across each range); wider ranges (>95 lo-fi and >150 blues leave the genre) |
| D15 | **Blues/fusion enable the `stop` device; lo-fi disables it; crash ranges per pack** | The 1-beat band stop is idiomatic blues/funk drama at rung-4 entries (distinct from deferred stop-time *choruses*); lo-fi's aesthetic forbids slams | Enabling everywhere (lo-fi anti-climax violated); conflating stop with stop-time (different devices, different machinery) |
| D16 | **Content depth: normative defining entries + rung/pool conventions in this doc; full bank enumeration is implementation-session authoring (DoD §14.2)** | The PHASE_5 §7 / PHASE_7 §8 precedent; design sessions pin schemas, conventions, and golden anchors — enumerating hundreds of pattern events is authoring labor the checklist + tooling exist for | Exhaustive banks in the design doc (hundreds of untested YAML lines frozen before the audition loop exists); pure prose (nothing golden-anchoring) |

---

## 12. Open questions

| # | Question | Resolves in | Depends on |
| --- | --- | --- | --- |
| Q1 | True 12/8 meter support (per-signature humanizer beat classes, feel tables, swing semantics) | Post-v1 | a pack that can't live on the triplet-grid approximation (§3.1); PHASE_6 §5.1 amendment |
| Q2 | Load-bearing `variant` (pattern cache key + eligibility + slot-level harmonyTag) — the gateway to stop-time choruses (§3.8) and true B-sections | Post-v1 | listening evidence that subtractive contrast (D2) reads as insufficient; PHASE_3/PHASE_5 amendments sketched in session 8 brainstorm |
| Q3 | Lo-fi noise-bed (vinyl crackle/foley) as a document-level sound-design extension | Post-v1 | relates to PHASE_6 Q3's automation-lane extension; Vibrato wobble meanwhile carries the aesthetic |
| Q4 | Do the L2 thresholds and L3 bands hold as authored packs mature (are 0.95/0.98 and ±2.5 SD right)? | Phase 8 implementation | first calibration batches; thresholds are data (`calibration.yaml`), tunable without design change |
| Q5 | Golden-corpus growth policy beyond 60 (per-bugfix regression fixtures? per-pack expansion?) | Implementation experience | bless-report signal-to-noise at 60 tracks |
| Q6 | Listening-panel scaling (recruiting musician listeners for the rubric beyond the developer) | Post-v1 / product | whether solo error-spotting + A/B plateaus |
| Q7 | Half-time feel for lo-fi (notated 82, felt 41 — affects energy/density reading of authored patterns) | Phase 8 implementation listening | whether rung-1 half-time patterns at 82 read as intended or need a dedicated eligibility band |
| Q8 | Fusion ride-swing top gear (per-section 8th-swing over a 16th-funk song) | Post-v1 | per-section feel machinery nobody has yet; rung-4 ride content stays straight meanwhile (§6.4) |

---

## 13. Amendments to earlier documents (this session)

All additive; applied in the same commit as this document:

1. **PHASE_2 §5.1** (`interpreter.yaml` schema): optional `feelTable: <profile name>` added (§3.4); validation: value ∈ the engine profile menu. §5's expected-mood-list sketch annotated with the final Phase 8 lists (D8).
2. **PHASE_2 §9 Q1**: resolved — no per-pack mood overrides needed (§3.8). **§9 Q6**: resolved — Lydian stays excluded (§3.8).
3. **PHASE_3 §9 Q1**: resolved — `main`/`breakdown` and the 8/16-bar cyclic options survive contact (exercised by chill_lofi/blues/fusion); `postchorus` remains unexercised (future pop-adjacent pack); `variant` did **not** survive as load-bearing — label-only in v1 (D2, §12 Q2). **§9 Q4**: resolved — one repeat block suffices (D2). **§9 Q5**: deferred post-v1 (§3.8). **§9 Q2**: deferred post-v1 (deceptive inert — §3.8).
4. **PHASE_4 §3.1**: token grammar gains the parenthesized extension group; authored extensions fully pin the token (dressing skips, draw-free) (§3.5). New loader rule **P11**: authored extensions legal per §6.4 for the token's quality. **§12 Q1**: resolved (§3.5). **§12 Q2/Q8**: closed not-needed (§3.8). **§12 Q3**: stays deferred, evidence strengthened (§3.8). **§12 Q7**: deferred post-v1 (§3.8).
5. **PHASE_5 §11 Q4**: resolved — blues bass = authored boogie patterns (D3). **§11 Q7**: resolved — `perc` voice, no fifth role (§3.6). **§11 Q5 remainder**: deferred post-v1 (§3.8).
6. **PHASE_6 §5.3**: `offsetsMs` becomes named profiles (`straight, swung, laidback, tight` — §3.4 values); selection = pack `feelTable` if present, else the existing swing-derived default. **§9 Q7**: resolved (D5). **§9 Q2**: riser stays dormant post-v1 (§3.8). **§9 Q4/Q5/Q8**: deferred per §3.8.
7. **PHASE_7 §5.2** (`sound/allowlist.yaml`): `Vibrato` and `AutoFilter` path entries added (§3.7). **§11 Q3**: riser wiring post-v1 (§3.8). **§11 Q4**: resolved — no per-pack mod_defaults overrides (§3.8). **§11 Q1/Q7**: become §8.4 listening tasks T1/T2.
8. **ROADMAP §2 decisions log**: row added for the Phase 8 model (quality framework + pack expansion). **ROADMAP §4 Phase 8 bullet list**: annotated with this document's §8/§9 structure.

---

## 14. Definition of done

Phase 8 is **built** when implementation sessions demonstrate (this phase is large; implementation will span several sessions — the tooling and reference-pack items gate the new-pack items):

1. **Machinery amendments**: feel profiles + `feelTable` selection (both new tables matching §3.4 exactly, validator caps enforced); authored-extension parsing with P11 rejection fixtures and pin-semantics tests (an authored-extension slot consumes zero dressing draws); allowlist additions.
2. **Reference packs refined** (§7): all abridged PHASE_5/PHASE_7 entries enumerated; lint clean; calibrated (T1 executed); goldens + `calibration.yaml` captured.
3. **Three new packs authored** to full banks per §4–§6's conventions (every defining entry verbatim; completeness per PT5/PT12/P6 and all loader rules; lint clean including the §9.2 warning tier — no unannotated warnings).
4. **Validator layers**: W1–W8 implemented with one violating fixture each; L2-1/L2-2 with per-pack thresholds from `calibration.yaml`; L3 metrics + band computation; V1–V8 unchanged and passing everywhere.
5. **Golden corpus**: the 60-track matrix captured at every IR boundary; `bless` implemented with the semantic diff report (first-divergent-stage, note add/remove/move counts, metric deltas) and the generatorVersion-bump check; a deliberate-change rehearsal documented (make a benign change, read the report, bless it in a dedicated commit).
6. **Smoke matrix** in CI (packs × moods × 3 lengths × 5 seeds, Layers 1–2); one 300-seed reference-pack sweep run clean.
7. **Tooling**: audition CLI with `--section`/`--solo`/`--mute`/`--play`; pack linter (errors + all five warning classes); `--explain` selection log; `trackgen calibrate` producing `calibration.yaml`.
8. **Listening**: T1 (levels) and T2 (FM piano) executed and logged; one full error-spotting pass per new pack with every entry fixed or filed; the A/B harness demonstrated on one real change; one milestone rubric pass over all five packs × 3 moods recorded.
9. **Five-pack property tests**: every prior phase's property suites (PHASE_2 §11.6 … PHASE_7 §13.6) run pack-parameterized over all five packs × supported moods × lengths × 25 seeds, green.
10. **End-to-end**: for each new pack, its default-params track and two mood extremes serialize, validate (Layers 1–2), and pass the pack's own listening checklist in the playground: lo-fi — laid-back swung groove, dropout sections audibly strip, fade-close rings out, nothing exuberant; blues — shuffle locks at three tempo tiers, boogie bass outlines the changes, turnarounds relaunch every chorus, stop lands when drawn; fusion — 16th pocket is tight, vamps loop without harmonic drift, quartal Rhodes sits under C5, breakdown strips to drums+bass and rebuilds.
11. **Amendments** (§13) applied and consistent.

With §14 complete, all eight phases are built: `generate(params, seed) → TrackDocument` stands as specified in ROADMAP §3 across five style families.

---

## 15. Roadmap invariant compliance

| Invariant | Where honored |
| --- | --- |
| 1. Style packs are data, not code | §4–§6: three new packs are pure YAML against pinned schemas; the two machinery additions (feel profiles, extension grammar) keep calibration in engine data and expression in pack data; §9's tooling operates on data |
| 2. Rhythm stored separately from pitch | All new banks author degrees/chord-hits (the boogie cell and tresillo skeletons are degree sequences); triplet-grid authoring changes positions, never pitch encoding; validators W1/L2-1 police the retargeting boundary |
| 3. Hierarchical seeds | The golden corpus, bless workflow, smoke matrix, and listening log all key on `(params, seed)` — the seed system is the QA substrate; no new streams, no draw-order changes (authored-extension slots are draw-free by construction) |
| 4. Soloist owns above ~C5 | W1 strengthens V4 to per-section lanes; every new pack's voicing classes/lanes inherit the ≤ 71 ceiling; fusion quartal and lo-fi rootless voicings verified against lanes in §4.4/§6.4 conventions |
| 5. Deterministic pipeline | W5 asserts it per render; the bless workflow depends on it; all new content uses integer weights, gated eligibility, and authored order; the extension grammar removes draws (pinning) rather than adding any |
