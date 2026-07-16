# SESSION_08 — Phase 5, Chunk 3 (part generators / walker / voicing)

Resume mid-phase (`@PROMPT.md - Phase 5`). Chunks 1 (session 06) and 2 (session 07) are
COMPLETE — loaders/foundations/reference-banks (DoD 1+2) and the Arrangement planner +
pattern selection (DoD 3+4); 816 tests green, four gates. This session builds the **four
part generators** — drums, pattern-bass, the **walking-bass engine** (§6.3), and the
comping/pads **voicing pass** over PHASE_4's Viterbi optimizer (§6.4/§6.5) — proving
**DoD 5** (walker §9.2), **DoD 6** (voicing §9.3), and **DoD 7** (generators end-to-end).
It resolves **C-04** (voicing API). Chunk 4 (orchestrator + Serializer + stub timbres +
milestone + whole-document goldens) comes last.

## Scope

**In scope**

- **Voicing pass** (`parts/voicing.py`, §6.4/§6.5): one `optimal_voicing_path` (PHASE_4 §8.6)
  run per voiced role over the **entire** chord timeline in order; per-event candidate
  classes = `pack.voicing[role].classes[rung of the event's section]`; the role's
  **bias-shifted arrangement lane**; per-role weights (comping `move4/top4/common3/drift1`;
  pads `move4/top2/common5/drift1`); anchor = `lane.high − 6`; cardinality padding (pad the
  shorter voicing with its own top pitch, already in `theory.voicing._pad_to_equal`).
  Produces a per-role map `ChordEvent → tuple[int,…]` (keyed by event `start_tick`).
  **Resolves C-04** (confirm keyless `quartal` = perfect-4ths; pass the real `lane.high−6`
  anchor; candidate-class-per-role via pack data so triads never hit 4-note classes).
- **Walking-bass engine** (`parts/walker.py`, §6.3): two-feel / four-feel from `feelByIntensity`;
  per-bar sub-streams `Random(derive(derive(bass,"walk"), f"bar:{absBar}"))`; the `nearest`
  helper; final-bar rule; two-chords-per-bar rule; beat-3-before-beat-2 strongest-first fill;
  drawn approach types; beat-1 root-decay on repeated bars; deterministic embellishment
  placement with `tempoBpm > 200` suppression; draw-iff-≥2 discipline; fixed authored
  velocities/durations (§6.3 tail).
- **Generators dispatcher** (`parts/generators.py`, §6 shared loop + §6.1/§6.2/§6.4/§6.5 +
  §8.2 drum voice→track map): `generate(role, …) → list[Phrase]`. Drums (voice→track map),
  pattern-bass, comping (chord-hit rhythm + voicing pitches), pads (chord-hit rhythm + voicing
  pitches, articulation-exempt); bass dispatches on `pack.bass_mode` (`walking` → the T2
  walker; `patterns` → standard instantiation). Tiles the selected pattern per phrase (§3.2),
  retargets each event (§3.3 via `parts/retarget.retarget_event`), applies §3.4 velocity /
  articulation and §3.5 gating, emits one `Phrase` per (track, section) with notes sorted
  `(ticks, midi)`.
- Golden + property tests proving DoD 5 (§9.2), DoD 6 (§9.3), DoD 7 (§9.4 + end-to-end).

**Out of scope** (do not build; later chunk / other phases)

- The pipeline **orchestrator** (§8.1 `for role in […]: generate(...)` top-level driver),
  the **Serializer** (§8.3), stub **timbres.yaml** (§8.4), the **milestone** fixtures, and
  the **whole-document** golden `TrackDocument`s — **Chunk 4** (DoD 8/9/10). T4 here may build
  a *test-only* thin driver that loops `generate` over the four roles to prove DoD 7; it must
  not build/commit the real orchestrator or serializer.
- Fills, transitions, crashes, stops, swing, jitter, mutation — Phase 6. All patterns are
  authored straight; `kind: fill` / `kind: break` patterns exist in the banks but are **not
  selected or emitted** this phase.
- Any change to `schema/`, `packs/`, `harmony/`, `form/`, `interpreter/`, `theory/`,
  `arrangement/`, or the existing `parts/{retarget,dynamics,selection}.py` — those contracts
  are **frozen** for this chunk. (If a genuine defect in one is found, STOP and escalate — do
  not edit a frozen module without sign-off.)

## Contracts consumed (all built + committed; read the source before coding)

- **Schema** (`schema/ir.py` — Phase-1 core, do NOT modify):
  - `Phrase{track_id:str, role:Role, start_tick:int, end_tick:int, notes:list[PhraseNote]}`;
    `PhraseNote{ticks, duration_ticks(≥1), midi:int|None (drums may set None; pitched roles
    set 0–127), velocity(>0,≤1), tags:list[str]}`. Generators produce exactly these.
  - `ChordEvent{start_tick, duration_ticks, section_id, chord:ChordSpec, scale:EventScale,
    function, tags}`; `ChordSpec{root_pc, quality, extensions, bass_pc, symbol, roman}`;
    `EventScale{root_pc, name}`. The `HarmonicPlan.chords` timeline tiles `[0, total)`
    gaplessly; `scale` feeds the walker's beat-2/approach pools; `tags` (`turnaround`/`final`)
    are visible to the walker's final-bar rule.
  - `ArrangementEntry{section_id, role, active, intensity(1–4 rung), density_budget, register}`;
    `Register{low_midi, high_midi}`. `register` is the role's **bias-shifted lane** (uniform
    across sections for a given role — computed once per role by `arrange`). This is the lane
    the voicing pass and retargeting use (NOT the pattern's own `retarget` register — that is
    only the octave-placement anchor input for single-degree events).
  - `FormSection{id, type, index, start_bar, length_bars, energy, phrases:list[SectionPhrase],
    …}`; `SectionPhrase{label, bars}`. Phrase starts are the pinned tiling alignment points
    (§3.2): a section's absolute tick range is `start_bar×1920 … (start_bar+length_bars)×1920`;
    within it, each `SectionPhrase` occupies `bars×1920` ticks in order.
- **Retargeting** (`parts/retarget.py`, Chunk 1 — reuse verbatim): `retarget_event(*, degree,
  octave, push, ticks, duration_ticks, chords, role, lane:Register, pattern_register:Register,
  on_chord_change, voicing_for) -> list[RetargetedNote]`. `RetargetedNote{ticks,
  duration_ticks, midi, tags}`. `degree == "chord"` requires the `voicing_for` hook
  (`Callable[[ChordEvent], Sequence[int]]`) — the generator injects the T1 per-role voicing
  map. `push` overhang past a tile end is by design (do not dedup overlaps). `lane` = the
  `ArrangementEntry.register`; `pattern_register` = `Register(env.retarget.register_low,
  env.retarget.register_high)`. Handoff note (b): key the voicing map by ChordEvent
  identity/`start_tick`, not `root_pc`.
- **Dynamics** (`parts/dynamics.py`, Chunk 1 — reuse verbatim): `apply_velocity(authored,
  dynamics_base)` (all roles); `articulation_scales(role, *, bass_walking=…)` → whether §3.4
  articulation applies (comping + pattern-mode bass only; drums/pads/walker exempt);
  `apply_articulation(authored_dur, articulation_legato, *, scale, gap_ticks=None)`;
  `is_event_active(min_density, density_budget)` (§3.5 gating).
- **Selection** (`parts/selection.py`, Chunk 2): `select_patterns(plan, form, arrangement,
  pack, master, overrides, *, rng_factory=None) -> SelectionResult`; `SelectionResult.by_section:
  dict[(section_id, role), PatternEnvelope]` is the chosen pattern for every active,
  pattern-mode pair. Walking-mode bass has **no** `by_section` entry (the walker serves it).
- **Arrangement** (`arrangement/arrange.py`, Chunk 2): `arrange(plan, form, pack, rng) ->
  ArrangementPlan`. Use to obtain per-(section,role) `active`/`intensity`/`density_budget`/`register`.
- **Intensity** (`arrangement/intensity.py`): `intensity(energy) -> int` (1–4). The walker maps
  each section's rung → feel via `pack.walking.feel_by_intensity[rung]`.
- **Theory / voicing** (`theory/voicing.py`, Phase 4 — reuse verbatim, do NOT modify):
  `voicing_candidates(spec:ChordSpec, cls:str, lane:LaneLike) -> list[list[int]]` (ascending
  MIDI, lane-pruned); `Lane(low, high)` (adapt a `Register` via `Lane(reg.low_midi,
  reg.high_midi)`); `optimal_voicing_path(specs, candidates_fn, weights:VoicingWeights, *,
  anchor:int|None) -> list[list[int]]` (integer-cost Viterbi; ties → lowest candidate index);
  `VoicingWeights(move, top, common, drift)`. Cardinality padding lives inside
  `optimal_voicing_path` (`_pad_to_equal`) — do not re-pad at the call site. The nine class
  names are in `packs.models.VOICING_CLASSES`.
- **Pack surface** (`packs/models.py::StylePack`): `pack.patterns[role]`,
  `pack.layering_order`, `pack.bass_mode`, `pack.walking:WalkingConfig{feel_by_intensity,
  approach_weights:dict[str,int], beat1_repeat_weights:dict[str,int]}`,
  `pack.voicing[role]:VoicingConfig{classes:dict[int,tuple[str,…]]}`. `PatternEnvelope{id,
  role, kind, energy_level, length_ticks, weight, eligibility, events, retarget}`;
  `PitchedEvent{pos, dur, degree, octave, velocity, push, min_density}`; `DrumEvent{pos,
  voice, velocity, dur:int|None, min_density}`; `Retarget{register_low, register_high,
  on_chord_change}`.
- **Seeds** (`seeds.py`): `stream_seed(master, overrides, name)`, `derive(parent, name)`,
  `weighted_choice(items, weights:Sequence[int], rng)`, `Rng = random.Random`. §3.6 walker
  discipline: bass stream seed = `stream_seed(master, overrides, "bass")`; walk stream =
  `derive(bass_seed, "walk")`; per-bar rng = `Rng(derive(walk_seed, f"bar:{absBar}"))`.
- **Rounding**: 3-dp half-even = built-in `round(x, 3)`; integer half-even = `round(x)`. No
  `round3` symbol. `clamp01` in `interpreter/moods.py`.
- **Driving the upstream pipeline in tests** (T4 goldens): mirror `tests/test_arrange.py` /
  `tests/test_selection_goldens.py` — interpret→form→harmony→arrange→select at seed `1ps9wxb`
  (master **3735928559**), pop_rock/happy and jazz/melancholic. All those stages exist and are
  golden-locked; the walker/voicing/generators consume their real output.

## Golden anchors (orchestrator pre-verified — reproduce, do not tune)

**Voicing pass configuration (static, confirmed):**
- Lanes come from `arrange` (bias-shifted): pop comping **50–71**, pop pads **45–71**; jazz
  comping **46–69**, jazz pads **41–69** (jazz pads dormant — `layersMax` 3). Anchor =
  `lane.high − 6`: jazz comping **63**, pop comping **65**, pop pads **65** — matches §9.3's
  stated anchors (63 / 65).
- Candidate classes per rung (pack data, already authored): pop comping `{1,2:[triad_close,
  triad_open], 3,4:[triad_close, shell3]}`; jazz comping `{1,2:[shell2, shell3], 3,4:[rootless_a,
  rootless_b]}`; pop pads `[fifths]` all rungs; jazz pads `[quartal]` all rungs. Weights:
  comping `VoicingWeights(4,4,3,1)`, pads `VoicingWeights(4,2,5,1)`.
- The candidate set for one chord event = the **concatenation, in class order**, of
  `voicing_candidates(spec, cls, lane)` over each `cls in classes[rung]` — this union is the
  DP stage's candidate list (generation order = the DP tie-break order).
- §9.3 spot-checks to reproduce **exactly** (MIDI): jazz comping heads (rung 2) Dm9→`F3+C4`
  (53,60), Gm9→`G3+B♭3+F4`, B♭13→`D3+A♭3`, A7♭9→`D♭3+G3`; jazz solos (rung 3) Dm9→`C3 E3 F3 A3`
  (rootless Type B), Gm9→`B♭2 D3 F3 A3` (Type A); pop comping verse-1 E→`E3 G♯3 B3`, A→`E3 A3
  C♯4`; pop pads chorus E→`E3 B3 E4`, B7→`B2 F♯3 B3`, C♯m→`C♯3 G♯3 C♯4`, A→`A2 E3 A3`. **All
  tops ≤ 71** (the C5 ceiling holds structurally). The A/B rootless alternation around the
  ii–V **emerges** from cost minimization — do not special-case it.

**Walker (jazz/melancholic, bass stream):** these are *computed* samples (§9.2) — reproduce
faithfully; **do not tune** (see caveat watch). Per-section draw counts **9 / 38 / 37 / 36 / 7 /
1** (head-1 / solo-1 / solo-2 / solo-3 / head-2 / outro-1 = **128 total**); note counts **24 /
50 / 53 / 53 / 24 / 7**. Excerpt pitches: head-1 bars 0–3 (two-feel, Dm9·Gm9·Dm9·Dm9) beat-1/
beat-3 = `D2/A2 · G2/D2 · D2/A2 · D3/A2`; solo-1 bars 12–15 four-feel grid per §9.2 table
(incl. the bar-15 beat-1 fifth **decay draw** `A1` and the and-of-4 dead-note **ghost**); outro-1
= `D2·A1 | G1·D2 | E2·A2 (2/bar) | D2 whole-note` (final-bar rule, lowest in-lane). Authored
walker velocities/durations (pre-§3.4): four-feel beat-1 `0.75`, beats 2–4 `0.68`; two-feel
beat-1 `0.72`, beat-3 & beat-4-approach `0.68`; final whole-note `0.75`; ghost `0.25`.
Durations two-feel 960, four-feel 480, final 1920, ghost 60.

**Instantiation (§9.4) spot-checks (post-§3.4):** velocity shift pop **+0.06**, jazz **−0.025**;
articulation pop **×0.904**, jazz **×1.108** (clamped to gaps). Jazz head-1 bar 0: bass D2
root `0.695` / A2 fifth `0.655` halves (dur 960); comping F3+C4 @0 dur **720** (Charleston
0.62 dur700 ×1.108=776 clamped to the 720 gap; vel `0.595`) and @720 dur **443** (vel `0.525`).
Pop verse-1 bar 4 (chord E): bass root quarters E2(40) dur 434 (480×0.904); comping E3+G♯3+B3
@0 dur 814, @960 dur 814. **§8.2 drum voice→track map:** kick→`kick`, snare→`snare`,
hat_closed+hat_open→`hats` (default dur closed 60 / open 360), ride→`ride` (dur 240),
tom_low/mid/high→same, perc→`perc`; default dur for kick/snare 120; crash is Phase-6.

## C-04 resolution (decide in T1; record in CAVEATS as resolved)

C-04 (open since session 04) is this chunk's to close. Decisions (all confirm the committed
`theory/voicing.py` behavior — no signature change, no golden contradicts them):
1. **`quartal` = perfect-4ths** (`[0,5,10,15]`), the only key-free reading — kept. Jazz pads
   (the only quartal user) are dormant in v1 (`layersMax` 3), so no §9.3 golden exercises it;
   record the confirmation and defer a diatonic-quartal widening to Phase 8.
2. **Anchor = `lane.high − 6`** passed explicitly to `optimal_voicing_path` (§6.4) — verified
   against §9.3's stated anchors (jazz comping 63, pop comping 65).
3. **Candidate class per role via pack data** — the per-rung classes are chosen so triads never
   hit 4-note seventh-chord classes (pop comping uses `triad_close/triad_open/shell3`; jazz uses
   `shell2/shell3/rootless_*`). No engine change needed; the voicing pass reads `classes[rung]`.

Update C-04 **Status: resolved** at close-out with the concrete readings and where each is
proven (T1 units + §9.3 goldens).

## Tasks

T1 ‖ T2 in parallel (disjoint files). T3 after both. T4 after T3. T5 (review + close-out) last.

### T1 — Voicing pass (`parts/voicing.py`) · model: **opus** · resolves **C-04**, builds toward **DoD 6**

**Files (create):** `src/trackgen/parts/voicing.py`, `tests/test_voicing_pass.py`.
**Do NOT edit `src/trackgen/parts/__init__.py`** (T2 runs in parallel and would clobber it — the
orchestrator consolidates exports later). Import your module by full path in tests
(`from trackgen.parts.voicing import …`). **Touch nothing else.**

**Implements:** PHASE_5 §6.4 (comping voicing pass), §6.5 (pads voicing pass + `fifths`),
resolves **C-04**. Consumes the committed `theory/voicing.py` verbatim (no edits there).

**Requirements:**
- Provide a builder, e.g. `build_voicing_map(role, arrangement, chords, pack) ->
  dict[int, tuple[int, …]]` (or a `Callable[[ChordEvent], Sequence[int]]`) — a per-role map
  from each `ChordEvent.start_tick` to that event's voicing MIDI. Runs **once per role** over
  the **entire** `chords` timeline in order (all events, active or not — keeps DP indices
  aligned with the plan; harmless for inactive sections).
- **Per-event candidate classes** = `pack.voicing[role].classes[rung]`, where `rung` = the
  intensity of the event's section (map `ChordEvent.section_id` → `ArrangementEntry.intensity`
  via the arrangement; every section has an entry). Build the stage's candidate list as the
  in-order concatenation of `voicing_candidates(event.chord, cls, lane)` over each class.
  If a class yields no lane-fitting placement, skip it; the concatenation across classes must
  be non-empty (the pinned lanes + classes guarantee this — assert/raise clearly if ever empty).
- **Lane** = the role's bias-shifted arrangement lane (`ArrangementEntry.register` for that
  role — uniform across sections; take any entry, or the first). Adapt to `Lane(low_midi,
  high_midi)`.
- **Weights**: comping `VoicingWeights(move=4, top=4, common=3, drift=1)`; pads
  `VoicingWeights(move=4, top=2, common=5, drift=1)`.
- **Anchor** = `lane.high_midi − 6`, passed explicitly to `optimal_voicing_path` (C-04 #2).
- The DP returns one voicing per event in timeline order; zip with the events to build the
  `start_tick → voicing` map. **Zero draws** (integer Viterbi) — no `random` import anywhere.
- The generator (T3) injects this map as `retarget_event`'s `voicing_for` hook, keyed by
  `chord_event.start_tick` (handoff note b). Provide the map in a form that hook can use for
  **any** event it is asked about (including a pushed event's *next* chord).

**Tests (`tests/test_voicing_pass.py`):**
- **Mechanism units** (small synthetic `ChordSpec`/`ChordEvent` + a `Register`): the candidate
  set is the concatenation-in-class-order; anchor is `lane.high−6`; comping vs pads weights are
  applied; the map keys are `start_tick`s; every returned voicing is ascending, lane-fitting,
  and **top ≤ lane.high** (≤ 71 for the reference lanes). Cardinality-padding unit: a shell2→
  rootless_a boundary (unequal cardinality) produces a valid path (padding is internal — assert
  the path exists and voices are in-lane, not the padded intermediate).
- **C-04 confirmations**: `quartal` yields `[0,5,10,15]`-shaped placements (perfect fourths);
  a triad under pop comping's `triad_close/…` classes never produces a 4-voice voicing.
- **Integer-cost property**: over a spread of chord timelines (or the reference packs' real
  timelines), every emitted voicing is lane-fitting with top ≤ 71; the pass is deterministic
  (same inputs → identical map) and consumes zero draws.
- (The exact §9.3 MIDI goldens land in **T4**, driven end-to-end — keep T1 to mechanism +
  invariants so T4's transcription is an independent check.)

**Verify:** four gates green.

### T2 — Walking-bass engine (`parts/walker.py`) · model: **opus** · builds toward **DoD 5**

**Files (create):** `src/trackgen/parts/walker.py`, `tests/test_walker.py`.
**Do NOT edit `src/trackgen/parts/__init__.py`** (T1 runs in parallel and would clobber it — the
orchestrator consolidates exports later). Import your module by full path in tests
(`from trackgen.parts.walker import …`). **Touch nothing else.** (Disjoint from T1.)

**Implements:** PHASE_5 §6.3 (the walker) exactly, incl. the §6.3-tail velocities/durations and
the §3.6 per-bar sub-stream discipline.

**Requirements:**
- Entry point, e.g. `walk(arrangement, chords, form, plan, pack, *, master, overrides,
  rng_factory=None) -> dict[str, list[WalkNote]]` — per active-bass `section_id`, the ordered
  list of `WalkNote{ticks, duration_ticks, midi, velocity, tags}` (authored **pre-§3.4**
  velocities; the generator applies the shift). `rng_factory: Callable[[int], Rng] | None`
  maps an absolute bar index → its rng; default = `Rng(derive(derive(stream_seed(master,
  overrides, "bass"), "walk"), f"bar:{absBar}"))` (§3.6). Injectable so T4's draw-count shims
  can count per bar. The walker only runs when `pack.bass_mode == "walking"`.
- **Feel** per section = `pack.walking.feel_by_intensity[intensity(section.energy)]`. Pitch
  state (previous emitted pitch) **resets at section start**. Bars iterate in absolute order;
  `absBar` seeds the per-bar rng; `barInSection` drives embellishment placement.
- **`nearest(pc, ref)`** = the in-lane pitch of class `pc` minimizing `(|p−ref|, p)` (tie-break
  **downward**). Lane = the bass `ArrangementEntry.register` (28–55, unshifted).
- **Two-feel** (half notes, dur 960): (1) final bar of the song's final section → one whole-note
  root at the **lowest** in-lane placement, then stop; (2) two chords in the bar → one half-note
  root per chord, `nearest` to previous; (3) else beat-1 root (`nearest`), beat-3 fifth placed a
  P4 below or P5 above beat 1 — **draw 1:1 iff both fit the lane**, else the one that fits; add a
  beat-4 quarter approach when the next bar changes chord **and** `densityBudget ≥ 0.55`.
- **Four-feel** (quarter notes, dur 480): (1) beat-1 root, except on the 2nd+ consecutive full
  bar of the same chord where the degree is **drawn** from `beat1RepeatWeights` (fifth2/third1/
  root1), placed `nearest` to previous; (2) two chords in the bar → root(1), approach(→c2 root),
  root(2), approach(→ next bar target); (3) **beat-3 filled before beat-2**: candidates =
  in-lane chord-tone pitches within 7 semitones of **both** beat-1 and the next bar's target,
  excluding both; weight 3 if within 2 semitones of the beat1↔target midpoint else 1; **draw iff
  ≥2**; empty → relax to within 12 of beat-1; (4) beat-2: in-lane chord + `event.scale` tones
  1–4 semitones from beat-1, excluding beat-3's pitch; weight 3 if ≤2 semitones else 1; draw iff
  ≥2; empty → relax to within 7; (5) beat-4: approach to next bar target, type **drawn** from
  `approachWeights` (`chromatic_below`→target−1; `diatonic`→first scale tone below target;
  `dominant`→target+7), folded into the lane; (6) embellishment: on bars where `barInSection % N
  == N−1` (N=4 if `densityBudget < 0.55` else 2), **suppressed when `tempoBpm > 200`** — a
  dead-note ghost (dur 60, vel 0.25, tag `"ghost"`) on the and-of-4 repeating the beat-4 pitch.
- **Draw order within a bar is fixed** (§3.6): beat-1 decay (if drawn) → beat 3 → beat 2 →
  approach type. Candidate lists materialized in **ascending pitch order** before drawing. Draws
  only via `weighted_choice` and only when **≥ 2** candidates (a singleton/forced pick consumes
  zero draws — this is what makes the §9.2 counts exact).
- **Next-bar target** = the root of the chord governing the next bar's downbeat (`nearest` to
  beat-1); at song end the current root substitutes.
- Authored velocities/durations exactly per the §6.3 tail (see Golden anchors). Walker is
  **articulation-exempt** (fixed durations); the generator still applies §3.4 **velocity** shift.

**Tests (`tests/test_walker.py`):** mechanism + structure over small synthetic
arrangement/chords (do **not** transcribe the §9.2 pipeline goldens here — that is T4):
- `nearest` tie-break-downward; lane containment.
- Two-feel: root/fifth placement (P4-below/P5-above, draw-iff-both-fit), beat-4 approach
  gate (`densityBudget ≥ 0.55` **and** chord change), final-bar rule (lowest root, whole note,
  stops), two-chords-per-bar halves.
- Four-feel: beat-1 root vs repeated-bar decay draw; beat-3-before-beat-2 candidate rules +
  relaxations; beat-4 approach types; two-chords-per-bar quartet; embellishment placement
  (N by density) + `tempoBpm > 200` suppression.
- **Draw discipline**: a counting-rng-per-bar shim proves the fixed draw order and that a
  singleton/forced choice consumes **zero** draws; **per-bar sub-stream independence** —
  regenerating one bar's rng in isolation reproduces that bar's draws (changing an earlier bar's
  rng does not shift a later bar).
- Velocities/durations match the authored §6.3 tail values (pre-shift).

**Verify:** four gates green.

### T3 — Generators dispatcher (`parts/generators.py`) · model: **opus** · builds toward **DoD 7**

**Files (create):** `src/trackgen/parts/generators.py`, `tests/test_generators.py`.
**May edit:** `src/trackgen/parts/__init__.py` (export `generate`). **Touch nothing else.**
Depends on **T1** (voicing map) and **T2** (walker) — dispatch after both land + are committed.

**Implements:** PHASE_5 §6 shared instantiation loop; §6.1 (drums) with the §8.2 voice→track
map; §6.2 (pattern-bass); §6.4/§6.5 comping/pads (rhythm from `degree: chord` patterns, pitches
from the T1 voicing map); bass dispatch on `pack.bass_mode`.

**Requirements:**
- Entry point, e.g. `generate(role, arrangement, chords, form, plan, pack, selection, *,
  master, overrides, prior_phrases=()) -> list[Phrase]` — every active `(section, role)`,
  producing one `Phrase` per **(track, section)**. `prior_phrases` is the reserved
  drums→bass→comping→pads handoff (§4.4) — accepted, **not consumed** in v1.
- **Shared loop** (§6): for each section where the role is active, for each phrase, tile the
  selected pattern (`selection.by_section[(section_id, role)]`) across the phrase's tick span,
  truncating at the phrase end (all patterns 1–2 bars, phrases multiples of 4 bars → exact).
  For each tiled event: skip if `is_event_active(min_density, density_budget)` is False (§3.5);
  else resolve. Emit notes sorted `(ticks, midi)`; `Phrase.start_tick`/`end_tick` = the section
  span. Pitched-role events overhanging a tile end via `push` are kept (do not dedup).
- **Drums** (§6.1): each `DrumEvent` → a note on the §8.2 track for its `voice` (hat_closed +
  hat_open both → `hats`). One `Phrase` per **active voice-track** per section (a section emits
  several drum Phrases — one per distinct track its events use). `PhraseNote.midi` for drums is
  left `None` (trigger MIDI is Phase-7's timbres). Default `dur` per §8.2 when unauthored
  (kick/snare 120, hat_closed 60, hat_open 360, ride 240, perc default per map). Velocity via
  `apply_velocity`; **articulation-exempt** (`articulation_scales("drums")` is False).
- **Bass** dispatch: `pack.bass_mode == "walking"` → call the **T2 walker** for the bass
  Phrases (apply `apply_velocity` to each `WalkNote`; articulation-exempt; one `Phrase` per
  section, track `bass`). `pack.bass_mode == "patterns"` → standard instantiation of the
  selected bass pattern; degree events retargeted via `retarget_event` (role `bass`, lane =
  bass register, `pattern_register` from the envelope's `retarget`, `on_chord_change` from it);
  velocity via `apply_velocity`; articulation **applies** (`articulation_scales("bass",
  bass_walking=False)` True) with `gap_ticks` = ticks to the same track's next event.
- **Comping** (§6.4): build the comping voicing map once (T1 `build_voicing_map("comping", …)`);
  instantiate the selected `degree: chord` pattern; each hit → `retarget_event(degree="chord",
  …, voicing_for=<map lookup by start_tick>)`. A pushed hit sounds the **next** event's voicing
  (retarget already handles `push`). Velocity via `apply_velocity`; articulation **applies**.
  One `Phrase` per section, track `comping`.
- **Pads** (§6.5): identical to comping but with the pads voicing map, track `pads`, and
  **articulation-exempt** (full authored durations). `onChordChange: retrigger` (from the
  envelope). One `Phrase` per section, track `pads`.
- No `random` import in this module for the pattern roles (drums/comping/pads/pattern-bass are
  draw-free at generation time — selection already drew). The walker (T2) owns bass-walking draws.

**Tests (`tests/test_generators.py`):** generator-level mechanisms over small synthetic inputs
and/or the reference packs (the full §9.4/end-to-end goldens are T4):
- Tiling: a 1-bar pattern tiled across a 4-bar phrase yields 4 copies at the right offsets; a
  2-bar pattern across a 4-bar phrase yields 2; truncation at the phrase end.
- §3.5 gating drops a `minDensity`-above-budget event and keeps it below-threshold.
- Drums: voice→track mapping (hats merge), default durs, one Phrase per emitted track, midi None.
- Pattern-bass: degree retargeting + articulation scaling + gap clamp; walking-bass dispatch
  routes to the walker and applies the velocity shift.
- Comping/pads: `degree: chord` hits emit the voicing-map pitches; pads are articulation-exempt
  (durations unscaled) while comping scales; a pushed comping hit sounds the next chord's voicing.
- Notes sorted `(ticks, midi)`; velocities in `(0,1]`; non-drum midi ≤ 71.

**Verify:** four gates green.

### T4 — Normative goldens + DoD 5/6/7 · model: **opus** · proves **DoD 5, 6, 7**

**Files (create):** `tests/test_walker_goldens.py`, `tests/test_voicing_goldens.py`,
`tests/test_generator_goldens.py`. **Touch no source and no other test file.** Depends on
T1/T2/T3 (dispatch after all three are committed). This is the **independent transcriber**: it
drives the real chained pipeline at seed `1ps9wxb` and asserts the §9 printed values verbatim.

**Tests:**
- **DoD 5 — walker (§9.2)** (`test_walker_goldens.py`): drive interpret→form→harmony→arrange→
  walker for jazz/melancholic. Assert per-section **draw counts 9/38/37/36/7/1** (counting-rng-
  per-bar shim via the walker's `rng_factory`, summed per section; **total 128**) and **note
  counts 24/50/53/53/24/7**; the head-1 bars 0–3 beat-1/beat-3 pitches, the solo-1 bars 12–15
  four-feel grid (incl. bar-15 beat-1 `A1` decay draw + and-of-4 ghost tag), the turnaround
  bars 10–11 root halves, and outro-1 (incl. the final whole-note low D). **Property**: every
  walker note in the bass lane; beat-1 rule compliance; approach targets are a half-step-below /
  scale-tone-below / dominant of the next target; final-bar rule fires only on final sections —
  over pop_rock(n/a: pop bass is patterns) + jazz × supported moods × a seed spread.
  *(Pop bass is `mode: patterns` → the walker property runs on jazz only; note this.)*
- **DoD 6 — voicing (§9.3)** (`test_voicing_goldens.py`): drive the pipeline for both packs;
  assert the **exact MIDI** for the §9.3 spot-checks (jazz comping shells rung 2 + rootless
  rung 3 incl. the emergent A/B alternation; pop comping verse-1 + chorus; pop pads chorus
  `fifths`). Assert **all tops ≤ 71**. **Property**: integer-cost path is deterministic; every
  voicing lane-fitting with top ≤ 71; cardinality-padding path valid — over both packs × moods.
- **DoD 7 — generators end-to-end (§9.4)** (`test_generator_goldens.py`): a **test-only** thin
  driver loops `generate` over `[drums, bass, comping, pads]` for both worked examples. Assert
  the §9.4 excerpts (pop verse-1 bar 4 + jazz head-1 bar 0 — kick/snare/hats/bass/comping
  values, post-§3.4 velocity + articulation). Assert the whole-output invariants: notes sorted
  `(ticks, midi)` per Phrase; every note within its section span; velocities in `(0,1]`;
  non-drum midi ≤ 71; `push` tags present on the pushed comping/bass hits and `ghost` tags on
  the walker dead notes where §9 says. **Determinism**: repeated `generate` runs identical;
  per-stream draw counts (drums/bass/comping/pads) match a counting shim (comping/pads/drums/
  pattern-bass = 0 generation draws; jazz bass-walk = 128).

**Verify:** four gates green; every §9.2/§9.3/§9.4 value reproduces with **zero doc edits**. If
any printed value diverges from the faithful implementation, **STOP and escalate** (golden-value
arbitration — see caveat watch); do not tune.

### T5 — Whole-chunk review + close-out · orchestrator + fresh **opus** review lenses

After T1–T4 are committed, dispatch **fresh opus** review agents in parallel (PROMPT §3), scoped
to the chunk's whole implementation (not per-task diffs):

1. **Correctness / logic** — the walker matches §6.3 (feel, draw order + draw-iff-≥2, nearest,
   final-bar/two-chord rules, approach types, decay, embellishment gates); the voicing pass
   matches §6.4/§6.5 (classes-per-rung, weights, `lane.high−6` anchor, full-timeline DP); the
   generator loop matches §6/§3.3–§3.5/§8.2.
2. **Contract compliance** — no frozen module touched (`git diff ff4cc7f..HEAD` clean on
   schema/packs/harmony/form/interpreter/theory/arrangement/retarget/dynamics/selection);
   Phrases/notes conform to the pinned schema; `push`/`ghost` tag vocabulary correct.
3. **Test quality + DoD 5/6/7** — §9.2/§9.3/§9.4 goldens are **doc-transcribed** (not tuned to
   code output) and non-vacuous; draw-count shims prove 128 and the per-section split; property
   matrices are real; every DoD 5/6/7 item provable by a named test.
4. **Code quality / simplification** — no needless duplication of retarget/voicing/theory logic;
   the walker's candidate/draw machinery is clear; determinism holds (no `random` outside the
   walker's seeded per-bar rng; no wall-clock).

Validation agent before any fix; confirmed findings → fix agent + gate re-run (**max 2 cycles/
task**; escalate on a surviving finding). Then: verify all four gates green; walk the DoD 5/6/7
checklist item-by-item with evidence; update PROGRESS.md (statuses, session-08 log row, fresh
handoff block → Chunk 4); set **C-04 Status: resolved** in CAVEATS with the concrete readings;
log any *new* deviation as a caveat. Commit doc updates. Report to me.

## Definition of done — this chunk targets DoD 5 + 6 + 7

- [ ] **§13.5 Walker** — §9.2 excerpt notes exactly; per-section draw counts 9/38/37/36/7/1
  (total 128); note counts 24/50/53/53/24/7; per-bar sub-stream independence; property (every
  note in lane, beat-1 rule, approach targets, final-bar rule on final sections). Evidence:
  `tests/test_walker.py` + `tests/test_walker_goldens.py`.
- [ ] **§13.6 Voicing passes** — §9.3 voicings exact MIDI (jazz shells/rootless, pop triads,
  pop pads fifths); integer-cost property; all tops ≤ 71; cardinality-padding unit. **Resolves
  C-04.** Evidence: `tests/test_voicing_pass.py` + `tests/test_voicing_goldens.py`.
- [ ] **§13.7 Generators end-to-end** — both worked examples produce Phrases passing: notes
  sorted, within section spans, velocities in (0,1], non-drum pitches ≤ 71, `push`/`ghost` tags
  present where §9 says (§9.4 excerpts asserted). Evidence: `tests/test_generators.py` +
  `tests/test_generator_goldens.py`.

## Verification (every task)

`uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy` — all
green, output read, before each commit. Never claim a gate passes without running it this session.

## Notes / caveat watch

- **Golden-value arbitration is the live risk this chunk.** §9.2 (walker draw/note counts +
  pitches) and §9.3 (voicing MIDI) are the docs' most intricate *computed* samples. Implement
  §6.3/§6.4/§6.5 faithfully; the algorithm text wins on divergence. If T4 finds a printed value
  the faithful implementation doesn't reproduce, **STOP and escalate to me** (ROADMAP §3 rule 1)
  — never tune code toward a printed number, and amend a doc sample only with sign-off + the
  recomputed fixture in the same commit.
- **C-04 is resolved here** (see the dedicated section) — the readings confirm committed
  behavior; record them, don't re-litigate.
- **Frozen contracts**: `theory/voicing.py`, `parts/{retarget,dynamics,selection}.py`,
  `arrangement/`, and all upstream stages are consumed **verbatim**. A genuine defect → escalate,
  don't edit.
- **Lane vs pattern register**: the voicing pass and single-degree octave anchoring both use the
  **arrangement** lane (`ArrangementEntry.register`); the pattern's own `retarget` register is
  the octave-placement *anchor input* for single-degree events only (`retarget_event`'s
  `pattern_register` arg). Don't confuse the two.
- **Module/signature latitude**: `parts/voicing.py` / `parts/walker.py` / `parts/generators.py`
  placement and the exact `build_voicing_map` / `walk` / `generate` signatures are
  orchestrator/implementer calls within scope — not design re-pins. Keep them minimal and
  Chunk-4-friendly (Chunk 4's §8.1 orchestrator will loop `generate` over the four roles).
