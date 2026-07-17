# SESSION_09 — Phase 5, Chunk 4 (orchestrator + Serializer + milestone) — FINAL chunk of Phase 5

Resume mid-phase (`@PROMPT.md - Phase 5`). Chunks 1/2/3 (sessions 06/07/08) are COMPLETE:
loaders/foundations (DoD 1+2), arrangement + selection (DoD 3+4), part generators / walker /
voicing (DoD 5+6+7). 941 tests green, four gates. This is the **final chunk** — it wires the
pipeline end to end and proves **DoD 8** (Serializer + milestone V1–V8), **DoD 9** (full-pipeline
determinism), **DoD 10** (whole-document goldens). As the phase's last session it also runs a
**whole-PHASE 4-lens review across all four chunks** and completes the **full §13 DoD 1–11 checklist**.

The §9.5 milestone **listening** checklist is a MANUAL user step (like Phase 1 §9.6) — not automatable;
this session produces the playable fixtures and states the checklist for the user.

---

## Authoritative wiring facts (verified against the code this session — supersede stale doc pseudocode)

The §8.1 orchestrator pseudocode is **stale** vs the real signatures. The authoritative driver is the
existing test-only loop `_drive_full` in `tests/test_generator_goldens.py:62-93`. Real chain:

```python
plan = generate_plan(raw_params)                     # trackgen.interpreter.stage — resolves pack,
                                                     #   derives master seed, builds overrides; ENTROPY BOUNDARY
pack = resolve_pack(raw_params["styleFamily"])       # trackgen.packs
sf   = form(plan, pack.forms)                         # trackgen.form.stage — NO rng param (builds its own)
hp   = harmony(plan, sf, pack.progressions,
               stream_rng(plan.seed.master, plan.seed.overrides, "harmony"))   # caller passes a Random
ap   = arrange(plan, sf, pack, Rng(0))                # trackgen.arrangement — rng accepted, UNUSED (0 draws)
sel  = select_patterns(plan, sf, ap, pack,
                       plan.seed.master, plan.seed.overrides)   # trackgen.parts.selection — §8.1 OMITS this
phrases = []
for role in ("drums","bass","comping","pads"):        # Role = Literal, pinned order
    phrases += generate(role, ap, hp, sf, plan, pack, sel,
                        master=plan.seed.master, overrides=plan.seed.overrides,
                        prior_phrases=phrases)         # prior_phrases accepted, not consumed in v1
# --- Chunk-4 additions below ---
phrases = transitions(phrases)                        # STUB: identity (Phase 6)
phrases, tempo_events = humanize(phrases)             # STUB: (phrases, []) — ritard events are Phase 6
patches = sound_design(plan, pack)                    # STUB: reads pack.timbres, picks per-role flavor
doc     = serialize(plan, sf, phrases, patches)       # §8.3
```

Key type facts (do not re-derive — confirmed at `file:line`):
- `Role = Literal["drums","bass","comping","pads"]` (`schema/document.py:20`) — a **string**, not an enum.
- `Rng = random.Random`; seed plumbing in `seeds.py`: `stream_rng(master, overrides, name)`,
  `stream_seed`, `derive`, `to_base36`/`from_base36`. Stream registry includes `transitions`,
  `humanize`, `sound` (reserved — the stubs make **zero draws**).
- `plan.seed.master: int`, `plan.seed.overrides: dict[str,int]` (`SeedSpec`, `ir.py:47`).
- `Phrase{track_id:str, role:Role, start_tick:int, end_tick:int, notes:list[PhraseNote]}`;
  `PhraseNote{ticks, duration_ticks(≥1), midi:int|None, velocity(0,1], tags:list[str]}`
  (`ir.py:228/236`). **No per-note section_id** — one Phrase per (track, section); the Phrase span
  is the section span. `PhraseNote.tags` are internal and are **dropped** at serialization
  (`NoteEvent` has no `tags` field).
- Drum notes leave `generate` with `midi=None` (`generators.py:228`); the Serializer injects the
  trigger midi from timbres for triggered synths and leaves NoiseSynth (snare) notes `midi=None` (V5).
- Drum voice→track map `_VOICE_TRACK` + `_DEFAULT_DUR` + `_TRACK_ORDER` already in `generators.py`
  (kick/snare/hats/ride/tom_low/tom_mid/tom_high/perc); `crash` dropped (Phase 6). Do not touch.

---

## Scope

**In scope**

- **Timbres substrate** (`packs/`, `styles/*/timbres.yaml`): an **additive** stub `timbres.yaml`
  schema + loader wiring + a `StylePack.timbres` slot + both reference-pack stub files (§8.4). The
  file is explicitly **provisional** (Phase 7 owns the real schema).
- **Stub pipeline stages** (`pipeline/stubs.py`): identity `transitions(phrases) -> phrases`;
  `humanize(phrases) -> (phrases, [])`; `sound_design(plan, pack) -> dict[str, TrackSound]` that
  reads `pack.timbres`, selects the flavor per role from `plan.role_flavors`, and returns, per
  track_id, the instrument patch + drum trigger midi (None for NoiseSynth). **Zero draws.**
- **Serializer** (`pipeline/serialize.py`, §8.3): `serialize(plan, form, phrases, patches) -> TrackDocument`
  — thin, per the pinned rules below. Output passes PHASE_1 §3.8 V1–V8 + the schema.
- **Orchestrator** (`pipeline/orchestrator.py`, §8.1): `generate_track(raw_params: dict) -> TrackDocument`
  — the chain above; subsumes `_drive_full`. Exported from `pipeline/__init__.py`.
- **CLI** (`cli.py`): a minimal `generate` command that writes a serialized `TrackDocument` JSON.
- **Milestone fixtures + whole-document goldens** (`fixtures/`, tests): both worked examples
  (pop_rock/happy and jazz/melancholic, seed `1ps9wxb`) generated through `generate_track`,
  committed as `fixtures/{pop_rock,jazz}.milestone.trackdoc.json`, asserted V1–V8 + schema +
  byte-stable re-serialization (DoD 8/10).
- **Determinism** (tests): repeated `generate_track` → identical doc; per-stream counting-RNG shims
  reproduce the established per-chunk draw counts; a check that the new `pipeline/` modules make no
  draws and import no `random`/wall-clock (DoD 9).
- **Whole-phase close-out**: 4-lens review across all four chunks; full §13 DoD 1–11 checklist with
  evidence; PROGRESS/CAVEATS updates.

**Out of scope** (do not build)

- Real Transitions/Humanizer/Sound-design behavior (Phases 6/7). The three stubs are identity /
  empty / patch-lookup only — **no** fills, swing, jitter, ritard tempo events, reverb bus, or real
  mixing. `tempo_events` from the humanize stub is always `[]`.
- The **PHASE_7 §7 supersession** of §8.3 (per-track `channel`/`sends`, `reverb` bus, pack master
  chain). Chunk 4 emits the §8.3 **stub** mix (below) — the handoff pins this explicitly.
- Any change to generator/selection/arrange/walker/voicing/retarget **behavior**, or to
  `schema/`, `theory/`, `form/`, `harmony/`, `interpreter/`, `arrangement/`. Those are **frozen**.
  The *only* permitted edits outside `pipeline/`, `cli.py`, `fixtures/`, `tests/`, `styles/` are the
  **additive** timbres field/loader in `packs/models.py` + `packs/loader.py` (T1). If a genuine
  defect in a frozen module surfaces, STOP and escalate — do not edit it without sign-off.

---

## Pinned design decisions for this chunk (build exactly these)

### D-A. Stub `timbres.yaml` schema (provisional; §8.4)

Per pack, a `timbres.yaml` mapping each role's flavor ids to a patch, reusing the PHASE_1 milestone
fixture's proven recipes. Drums are a **kit** (per-drum-track patch + trigger midi); pitched roles map
a flavor to one instrument patch. Strict schema (`extra="forbid"`), frozen pydantic models in
`packs/models.py`:

```yaml
# styles/<pack>/timbres.yaml   (PROVISIONAL — Phase 7 replaces schema + content)
drums:
  <flavor_id>:                 # e.g. acoustic_kit / tight_kit (pop), brush_kit / ride_kit (jazz)
    kick:  { midi: 24, instrument: { type: MembraneSynth, options: {...} } }
    snare: {           instrument: { type: NoiseSynth,     options: {...} } }   # NO midi (V5)
    hats:  { midi: 80, instrument: { type: MetalSynth,     options: {...} } }
    ride:  { midi: 82, instrument: { type: MetalSynth,     options: {...} } }
    tom_low:  { midi: 43, instrument: {...} }
    tom_mid:  { midi: 47, instrument: {...} }
    tom_high: { midi: 50, instrument: {...} }
    perc:  { midi: 39, instrument: {...} }
bass:    { <flavor_id>: { instrument: { type: MonoSynth,  options: {...} } } }
comping: { <flavor_id>: { instrument: { type: PolySynth, voice: FMSynth, maxPolyphony: 6, options: {...} } } }
pads:    { <flavor_id>: { instrument: { type: PolySynth, voice: AMSynth, maxPolyphony: 6, options: {...} } } }
```

- Instrument recipes = the exact PHASE_1 `fixtures/milestone.trackdoc.json` patches (MembraneSynth
  kick, NoiseSynth snare, MetalSynth hats/ride, MonoSynth bass, PolySynth/FMSynth comping,
  PolySynth/AMSynth pads). Read them from that fixture — do not invent new options.
- Trigger midi (stub): kick 24, hats 80, ride 82, tom_low 43, tom_mid 47, tom_high 50, perc 39;
  **snare carries no midi** (NoiseSynth → V5). All flavors of a role reuse the same recipe in the
  stub (flavor differentiation is Phase 7); both flavor ids must still be present (completeness).
- **No effects** in the stub (`effects=[]` on every track) and **no per-flavor mix** — the mix is the
  Serializer's engine table (D-C). This keeps the stub minimal and V-valid.
- Flavor-id coverage the stub must include (from each `interpreter.yaml`): pop_rock drums
  `[acoustic_kit,tight_kit]`, bass `[electric_fingered,electric_picked]`, comping
  `[clean_electric,crunch_electric,piano]`, pads `[warm_analog,airy_strings]`; jazz drums
  `[brush_kit,ride_kit]`, bass `[upright]`, comping `[piano,guitar_hollow]`, pads
  `[airy_strings,organ_soft]`.

### D-B. `sound_design` stub contract

`sound_design(plan, pack) -> dict[str, TrackSound]`, keyed by **track_id** — the eight drum track
ids plus `"bass"/"comping"/"pads"`. `TrackSound` is a small frozen model
`{instrument: InstrumentPatch, effects: list[EffectPatch] = [], midi: int | None = None}` (drum
trigger midi; None for snare/pitched roles — pitched notes already carry their own midi from
`generate`). The active flavor per role = `plan.role_flavors[role]`. It reads `pack.timbres`; **zero
draws**; runs before serialize (does not see phrases) so it returns patches for **all** candidate
tracks — the Serializer emits only those with ≥1 note.

### D-C. Serializer rules (§8.3, thin)

- **Group** phrases by `track_id`; concatenate notes in **section order** (phrases already carry
  `start_tick`; order by it). Convert each `PhraseNote` → `NoteEvent` (drop `tags`). For drum tracks:
  inject `patches[track_id].midi` into every note **iff** it is not None; snare (NoiseSynth, midi
  None) keeps `midi=None`. Pitched tracks keep the note's own `midi`.
- **Sort** each track's notes `(ticks, midi)` with `midi=None` sorting first (matches
  `_note_sort_key`); **clamp** `duration_ticks ≥ 1`; **truncate** any note with
  `ticks + duration_ticks > sections[-1].end_tick` down to end (V8); drop a note starting at/after the
  song end (shouldn't occur).
- **Emit a track** per distinct `track_id` with ≥1 surviving note, ordered
  `[kick,snare,hats,ride,tom_low,tom_mid,tom_high,perc]` (drum sub-order) then `bass, comping, pads`.
  `Track.id = track_id`; `role` from the phrase; `name` = human label (title-cased id);
  `instrument`/`effects` from `patches[track_id]`; `channel` from the stub table below; `sends = []`.
- **Sections**: 1:1 from `form.sections`. `type = s.type`; `label = section_label(s.type, s.index,
  s.total_of_type, s.variant)` (import from `form/stage.py`); `start_tick = s.start_bar*1920`;
  `end_tick = (s.start_bar+s.length_bars)*1920`; `energy = s.energy`. (4/4, PPQ 480 → 1920 ticks/bar.)
- **Header**: `ppq = 480`; `tempos = [Tempo(ticks=0, bpm=plan.tempo_bpm)]` (single base tempo — ritard
  events are Phase 6, absent); `time_signatures = [TimeSignature(ticks=0, …)]` from `plan.time_signature`.
- **Meta**: `seed = to_base36(plan.seed.master)`; `seed_overrides = {k: to_base36(v)}`;
  `params = <the raw params dict>`; `generator_version = "0.1.0"`; `tone_version = "^15.1.0"`;
  `title = None` (dropped by `exclude_none`).
- **Stub mix** (§8.3 engine table, Serializer constant — authoritative, intentionally ≠ the PHASE_1
  fixture's hand-authored mix): `Channel{volume_db, pan, mute=False}` per track_id —
  kick −2/0 · snare −4/0 · hats −4/+0.2 · ride −4/−0.15 · tom_low/mid/high −4/0 · perc −4/0 ·
  bass −3/0 · comping −6/+0.1 · pads −10/−0.1.
- **buses = []**; **master** = `[Compressor{threshold:-24, ratio:4}, Limiter{threshold:-1}]`.
- Serialize to JSON with `model_dump(by_alias=True, exclude_none=True)` (camelCase, drop None).

### D-D. Milestone worked examples

Reuse the **exact** `raw_params` dicts the existing chained goldens already use (see
`tests/test_generator_goldens.py`, `test_selection_goldens.py`, `test_arrange.py`): pop_rock/happy
and jazz/melancholic, **seed `1ps9wxb`** (master 3735928559). This keeps the whole-doc goldens on the
same seed chain as PHASE_2 §6.5 → PHASE_3 §7.4 → PHASE_4 §10 → PHASE_5 §9. Generate both docs through
`generate_track`, commit as fixtures, assert against the fixtures (bless-in-spirit, ROADMAP §3 rule 3).

---

## Task list (serial — the pieces are tightly coupled; per-task review keeps each clean)

| # | Task | Model | Files (scope) | Proves | Verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Timbres schema + loader + both stub `timbres.yaml` + `sound_design`/`transitions`/`humanize` stubs | opus | `packs/models.py` (+timbres models & `StylePack.timbres`, additive), `packs/loader.py` (read `timbres.yaml`), `styles/{pop_rock,jazz}/timbres.yaml` (new), `pipeline/stubs.py` (new), `tests/test_timbres.py` (new) | part of DoD 8 | both packs load with `.timbres`; stub covers every flavor id; `sound_design` returns the D-B map; identity transitions/humanize; zero draws; four gates |
| T2 | Serializer `serialize(plan, form, phrases, patches) -> TrackDocument` + unit tests | opus | `pipeline/serialize.py` (new), `tests/test_serialize.py` (new) | DoD 8 (V1–V8) | synthetic + real phrases → doc passes `validate_document` == []; V5 snare-None / V4 ≤71 / V8 truncation / stub mix / meta seed echo unit-asserted; four gates |
| T3 | Orchestrator `generate_track(raw_params) -> TrackDocument` + `pipeline/__init__.py` exports + CLI `generate` | opus | `pipeline/orchestrator.py` (new), `pipeline/__init__.py`, `cli.py` (add command), `tests/test_orchestrator.py` (new) | DoD 8 wiring | both examples run end-to-end → valid docs; orchestrator matches `_drive_full` chain incl. `select_patterns`; CLI writes valid JSON; four gates |
| T4 | Milestone fixtures + whole-document goldens + full-pipeline determinism | opus | `fixtures/{pop_rock,jazz}.milestone.trackdoc.json` (new), `tests/test_whole_document_goldens.py` (new), `tests/test_pipeline_determinism.py` (new) | DoD 8/9/10 | both fixtures committed + byte-stable re-serialize; V1–V8 on each; repeated-run identity; per-stream counting shims reproduce established counts; `pipeline/` random-free; four gates |
| T5 | Whole-PHASE 4-lens review (all 4 chunks) + full §13 DoD 1–11 checklist + close-out | orchestrator (opus review agents) | `plans/PROGRESS.md`, `plans/CAVEATS.md` | phase DoD | 4 fresh opus lenses; each finding validated before fix (2-cycle bound); DoD 1–11 each ticked with evidence; four gates green; commit |

**No parallelism** — T2 consumes T1's `TrackSound`/patch shape; T3 wires T1+T2; T4 drives T3. Serialize
in order. (If T2's serializer contract can be pinned crisply enough from D-B/D-C, a reviewer may note
T1↔T2 could have overlapped, but correctness on the milestone outweighs the saved wall-clock.)

---

## Per-task detail

### T1 — Timbres substrate + stub stages

- **Models** (`packs/models.py`, additive; the file's other models stay untouched): a frozen
  `TrackTimbre{midi: int | None = None, instrument: InstrumentPatch}`; `DrumKit` = mapping
  drum-track-id → `TrackTimbre`; `TimbresConfig{drums: dict[str,DrumKit], bass/comping/pads:
  dict[str,TrackTimbre]}`, all `extra="forbid"`; add `timbres: TimbresConfig | None = None` to
  `StylePack`. Reuse the schema's `InstrumentPatch`/`InstrumentType`/`PolySynthVoice` from
  `schema/document.py` (import; do not redefine).
- **Loader** (`packs/loader.py`): in `load_pack`, read optional `timbres.yaml` (same pattern as
  `interpreter.yaml`/`forms.yaml`), validate into `TimbresConfig`, set `StylePack.timbres`. Absent
  file → `None` (packs without timbres still load — `_stub`, tests).
- **Stub files** (`styles/{pop_rock,jazz}/timbres.yaml`): author per D-A, copying the exact
  instrument `options` from `fixtures/milestone.trackdoc.json`. Cover every flavor id (D-A list).
  Header comment: `# PROVISIONAL stub (PHASE_5 §8.4) — Phase 7 replaces schema + content`.
- **Stubs** (`pipeline/stubs.py`): `transitions(phrases: list[Phrase]) -> list[Phrase]` (identity);
  `humanize(phrases) -> tuple[list[Phrase], list[Tempo]]` returning `(phrases, [])`;
  `sound_design(plan, pack) -> dict[str, TrackSound]` per D-B (raise a clear error if
  `pack.timbres is None` or a needed flavor id is missing). Define `TrackSound` here (or in models —
  reviewer's call). No `random`, no wall-clock.
- **Tests** (`test_timbres.py`): both packs load with `.timbres`; every flavor id present;
  `sound_design` returns a patch for all 8 drum tracks + bass/comping/pads; snare `midi is None`,
  kick/hats/ride midi = 24/80/82; a counting-RNG shim proves `sound_design` draws 0.

### T2 — Serializer

- Implement D-C exactly. Pure function; no I/O. Build `TrackDocument` via the snake_case constructors
  (`populate_by_name`) and rely on `exclude_none` at dump time.
- **Tests** (`test_serialize.py`): drive with a small hand-built phrase set AND with the real pop/jazz
  phrase lists (via the `_drive_full` pattern — import the stages) to assert `validate_document(doc)
  == []`. Targeted asserts: snare notes `midi is None` while kick/hats/ride notes carry the trigger
  midi (V5); no non-drum note `midi > 71` (V4); a note authored past song end is truncated to
  `sections[-1].end_tick` (V8); `duration_ticks ≥ 1`; sections contiguous 1:1 with the form; header
  single tempo at tick 0; meta `seed == to_base36(master)`; stub mix values per track_id; master =
  Compressor+Limiter; `buses == []`; tracks emitted only for track_ids with notes, in the pinned order.

### T3 — Orchestrator + CLI

- `generate_track(raw_params: dict) -> TrackDocument` = the authoritative chain (top of this file),
  including the **`select_patterns`** step §8.1 omits, then `transitions`→`humanize`→`sound_design`→
  `serialize`. Thread the raw params into `meta.params`. Export `generate_track` (and `serialize`) from
  `pipeline/__init__.py`.
- **CLI** (`cli.py`): add `generate` — accept style/mood/seed/tempo/key/max-length options (or a
  `--params <json>` file), call `generate_track`, write `json.dumps(doc.model_dump(by_alias=True,
  exclude_none=True), indent=2)` to `--out` or stdout. Keep it minimal; reuse the raw-params dict shape
  `generate_plan` already expects.
- **Tests** (`test_orchestrator.py`): both examples → `validate_document == []`; the orchestrator's
  phrase set equals `_drive_full`'s (guards against drift from the reference loop); a CLI smoke test
  (invoke via Typer's runner) yields parseable JSON that re-validates.

### T4 — Milestone fixtures + whole-doc goldens + determinism

- Generate both docs via `generate_track` at seed `1ps9wxb`; write them to
  `fixtures/{pop_rock,jazz}.milestone.trackdoc.json` (pretty JSON, `by_alias`, `exclude_none`). This is
  the **first whole-document golden** (ROADMAP Phase-8 mechanism, seeded here; bless-in-spirit).
- **Goldens** (`test_whole_document_goldens.py`): load each fixture; assert it re-serializes
  byte-identically from a fresh `generate_track` (the regression surface); `validate_document == []`;
  spot-pin a handful of §9.4 facts as documentation anchors (e.g. pop verse-1 bar-4 comping midis
  `G♯3,B3,E4`, jazz head-1 walker note count 24, the jazz ending's final low-D whole note) — using the
  **corrected** C-09 values, and if any generated fixture value ever conflicts with §9.4/§9.5 prose the
  fixture wins (recompute; ROADMAP §3). Confirm no non-drum note > 71 across the whole doc (invariant 4).
- **Determinism** (`test_pipeline_determinism.py`): `generate_track(same params)` twice → identical
  dumped dict (DoD 9); per-stream counting-RNG shims over the full pipeline reproduce the established
  counts (harmony 8/30 for Ex1/Ex2 per Phase 4; selection pop 1 / jazz 3; jazz walker 128; arrangement
  0; the three stubs 0) — assert the composed total and each stream; a structural test that
  `pipeline/{orchestrator,serialize,stubs}.py` import no `random`/`time`/`datetime` (TID251 already
  bans them — assert the modules are clean and make zero draws through a shim).

### T5 — Whole-phase review + DoD + close-out (orchestrator-run)

- Dispatch **4 fresh opus lenses** over the **entire Phase-5 implementation across all four chunks**
  (not per-task diffs): (1) correctness/logic — the full pipeline seams, Serializer V-rule edges,
  determinism; (2) contract compliance vs PHASE_5 §3–§8 (esp. §8.1 chain incl. select, §8.2 map, §8.3
  Serializer rules, §8.4 stub provenance) + frozen-module integrity (`git diff` on frozen paths clean
  apart from the additive timbres field); (3) test quality / DoD coverage (goldens doc/fixture-anchored,
  not vacuous); (4) code quality / simplification (incl. the deferred `_fold_into_lane`/`_third_pc`/
  `_fifth_pc` dedup noted in the Chunk-3 handoff — decide fix-now vs defer).
- Each finding → a **validation** agent before any change; confirmed → fix agent + gate re-run;
  **2-cycle bound**, escalate on survival.
- Walk the **full §13 DoD 1–11** one by one with evidence (re-attest 1–7 from prior chunks with test
  pointers; prove 8/9/10 here; 11 = §12 amendments, already verified in Chunk 1 — re-confirm).
- Finish gates green; commit; rewrite PROGRESS handoff to mark **Phase 5 COMPLETE** and point Phase 6.

---

## DoD mapping (§13)

- **DoD 8** (Serializer + milestone) — T2 (V1–V8 unit) + T3 (end-to-end valid) + T4 (committed fixtures,
  play checklist stated for manual user audition).
- **DoD 9** (determinism, full pipeline) — T4 (repeated-run identity + per-stream counting shims +
  random-free `pipeline/`).
- **DoD 10** (whole-document goldens) — T4 (both fixtures as the first whole-doc regression surface).
- **DoD 11** (amendments) — re-attested in T5 (already verified present in Chunk 1).
- **DoD 1–7** — re-attested in T5's whole-phase review with test pointers from chunks 1–3.

## Gates & ground rules

- Every task: `uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy`
  — orchestrator runs and reads them before commit.
- Every `Agent` dispatch sets `model` explicitly (opus for all T1–T4 implementers, all reviewers).
- Determinism: no wall-clock, no unseeded randomness outside `seeds.py`; the three stubs and the
  Serializer make **zero** draws; TID251 covers the new modules.
- Frozen modules untouched except the additive `packs` timbres extension (T1). Escalate on any genuine
  frozen-module defect rather than editing it.

## Risks / notes

- **Stub mix ≠ PHASE_1 fixture mix** — intentional (§8.3 stub table is authoritative; the fixture mix
  was hand-authored). **Not a caveat** — emitting the pinned §8.3 stub is following the design. Note it
  in PROGRESS so a reviewer doesn't false-alarm.
- **No buses/sends in the stub** (§8.3 "no buses") — the PHASE_1 fixture's reverb sends are absent from
  the milestone docs; V6 passes trivially. Also following §8.3, not a deviation.
- **`generatorVersion`/`toneVersion`** have no code source — hardcoded in the Serializer (`0.1.0` /
  `^15.1.0`). If a later phase wants them derived, that's a Phase-8 concern.
- **C-09 arbitration is closed** — §9.2/§9.3/§9.4 samples were corrected to the faithful engine in
  Chunk 3. Chunk-4 whole-doc goldens are fresh authoritative fixtures; no new arbitration expected, but
  the fixture wins over any conflicting §9.4/§9.5 prose (recompute; ROADMAP §3).
