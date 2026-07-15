# Session 01 — Phase 1: Foundations & Contracts

- **Phase:** 1 (Foundations & Contracts)
- **Type:** fresh phase, single session (Phase 1 fits one session — all contracts are fully pinned in `PHASE_1.md`; no design work, only implementation against a firm spec).
- **Orchestrator drives; all code is written by dispatched subagents.**

This file is written for implementer subagents who start with **zero context**. Each task below names the exact `PHASE_1.md` sections to read, the exact files to create/edit, the constraints, and the verification. Read your task section plus the cited `PHASE_1.md` sections in full before writing code.

---

## Session scope

Deliver the entire Phase 1 Definition of Done (`PHASE_1.md` §9):

1. Seed module (`seeds.py`) with golden-vector + determinism tests.
2. Schema package: frozen pydantic models for `TrackDocument` (complete) + the five IR pinned cores.
3. Document validator (§3.8 V1–V8) + exported JSON Schema at `docs/schema/trackdocument.schema.json`.
4. Pack loader + stub pack `styles/_stub/` + envelope-violation rejection tests.
5. Milestone fixture `fixtures/milestone.trackdoc.json`, passing schema + validator.
6. Playground `playground/index.html` implementing the §3.7 player contract.

**Out of scope** (do not build): any generation logic (Interpreter/Form/Harmony/Parts/etc.), style-pack *content* beyond the tiny `_stub`, the parameter/mood schema (`meta.params` stays an opaque echoed object), bank-specific pack schemas owned by later phases, and the theory/music21 wrapper (Phase 4 — `theory/` stays an empty package this session). The §9.6 manual listening checklist is a human step, performed by the user after the playground lands, not an automated gate.

## Settled open questions (record only; no separate task)

- **Q10 package name:** confirmed `trackgen` (already the package; no change).
- **music21 pin:** `uv.lock` pins `music21==10.5.0`. The lock is the exact-pin surface (CLAUDE.md); `pyproject.toml` carries lower bounds only. Confirmed, no change needed.
- **Q9 Tone.js version:** PHASE_1 assumes `^15.1.0`. Task 6 resolves the exact current stable `tone@15.x` on the CDN and makes the playground and the fixture's `meta.toneVersion` agree. If the current stable major is not 15, **stop and escalate** rather than silently changing the pinned assumption.

## Contracts consumed / produced

- **Consumes:** nothing upstream (this is the first phase). Reads only `PHASE_1.md`.
- **Produces (binding on every later phase):** `TrackDocument` schema, the five IR pinned cores (`GenerationPlan`, `SongForm`, `HarmonicPlan`, `ArrangementPlan`, `Phrase`), the seed system API, the style-pack envelope/event primitives, the exported JSON Schema artifact, and the milestone fixture.

## Global constraints (apply to every task)

- **Gates must be green** before a task is committed: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` (strict). Run via `uv` only. (`uv` lives at `C:\Users\Dominic\scoop\shims`; prepend to PATH.)
- **mypy strict**: everything fully typed, no `Any` leaks, no `# type: ignore` without justification.
- **Determinism (ROADMAP invariant 5):** no `random.`/`os.urandom`/`time.*`/`datetime.now` outside `seeds.py`. Ruff TID251 enforces the import layer — never work around it.
- **Frozen models:** every pydantic IR and document model is `frozen=True` (`PHASE_1.md` §2, §4).
- **pydantic v2** (2.13.x). **Ticks are integers at PPQ 480.** Pitch classes int 0–11 (C=0); MIDI C4=60.
- **Golden-value arbitration (ROADMAP §3):** the algorithm/data *text* wins over any printed sample. Never tune code to reproduce a printed number; if a printed value looks wrong, flag it — do not silently match it.
- Tests are part of each task, not an afterthought. No vacuous tests; assert real values.

---

## Task list

Tasks 1, 2, and 4 touch disjoint file sets (`seeds.py` / `schema/` / `packs/`+`styles/`) and may be implemented concurrently; each is still individually gate-verified, reviewed, and committed. Task 3 depends on Task 2; Task 5 on Tasks 2+3; Task 6 on Task 5.

### Task 1 — Seed system (`seeds.py`) — model: **opus**

**Read:** `PHASE_1.md` §5 (all subsections) and §9 items 2 & 7.
**Files:** `src/trackgen/seeds.py` (new), `tests/test_seeds.py` (new).

**Build** the complete hierarchical seed system exactly as §5 pins it:
- `master_from_string(s: str) -> int` — `int.from_bytes(sha256(utf8(s)).digest()[:8], "big")`.
- `derive(parent: int, name: str) -> int` — per §5.2 (`parent.to_bytes(8,"big") + b"/" + name.encode()` → sha256 → first 8 bytes big-endian).
- `stream_seed(master: int, overrides: dict[str, int], name: str) -> int` — §5.4.
- base36 codec: `to_base36(n: int) -> str` (lowercase) and `from_base36(s: str) -> int` (case-insensitive), for u64.
- `weighted_choice(items, weights, rng)` — the exact §5.3 integer-cumulative algorithm; weights are `int` (validate `sum > 0`).
- Fresh-seed entropy helper reading `os.urandom(8)` — the single entropy boundary (§5.1). This is the only place `os.urandom`/`random` may be used; `seeds.py` is already TID251-exempt in `pyproject.toml`.
- The pinned **stream registry** names (§5.2) as a module constant: `interpreter, form, harmony, arrangement, drums, bass, comping, pads, transitions, humanize, sound`.

**Tests (golden vectors from §5.6 — assert every value exactly):**
- `master_from_string("banana") == 13011977409198548045`, base36 `2qux517snxfm5`.
- For `master = 3735928559` (base36 `1ps9wxb`): all 11 stream `derive` values AND their base36 encodings (the §5.6 table).
- Chained: `derive(drums, "fills") == 2174782555333666359`; `derive(that, "bar:17") == 1110592329615889969`.
- RNG behavior: `random.Random(derive(M,"drums"))` first five `getrandbits(32)` == `[2813930941, 3236345189, 575825508, 1551984896, 116936044]`; first five `randrange(100)` == `[83, 96, 17, 46, 3]`.
- base36 round-trips both directions incl. case-insensitive input.
- **Determinism guard (§9 item 7):** two `random.Random` built from the same `stream_seed` produce identical draw sequences.
- `weighted_choice`: deterministic given a seeded rng; respects weights; rejects non-positive total.

**Verify:** all four gates green; every §5.6 value asserted and passing.

### Task 2 — Schema models: `TrackDocument` + five IR cores — model: **sonnet**

**Read:** `PHASE_1.md` §3 (all of §3.1–§3.6), §4 (all IR tables §4.1–§4.5). Do NOT implement §3.8 validation logic here (Task 3) — but pydantic field-level constraints (ranges, enums, required/optional) belong here.
**Files:** `src/trackgen/schema/` — split into readable modules, e.g. `document.py` (TrackDocument tree: meta, header, sections, tracks, NoteEvent, InstrumentPatch, EffectPatch, buses, master, channel, sends), `ir.py` (GenerationPlan, SongForm, HarmonicPlan/ChordEvent/ChordSpec, ArrangementPlan/ArrangementEntry, Phrase/PhraseNote), and re-export the public names from `schema/__init__.py`. `tests/test_schema.py` (new).

**Build** frozen (`model_config = ConfigDict(frozen=True)`) pydantic v2 models covering **every field** in §3 and §4, with field-level constraints expressible in pydantic:
- Enums as `Literal`/`Enum` where §3 pins closed sets: `role` (`drums|bass|comping|pads`), instrument `type` whitelist, `voice` whitelist, effect `type` whitelist, `ChordSpec.quality`, section-type stays `str` (Phase 3 owns the vocabulary).
- Constraints: `velocity` in (0,1]; `durationTicks >= 1`; `pan` in [-1,1]; `volumeDb <= 6`; `midi` 0–127; `denominator ∈ {2,4,8,16}`; `bpm > 0`; `swing.ratio ∈ [0.5,0.75]`; `intensity` 1–4; `energy ∈ [0,1]`; `lengthBars >= 4`; pitch classes 0–11.
- `meta.params` is an **opaque** `dict` (Phase 2 owns its shape) — do not model it.
- `NoteEvent.midi` optionality: pinned as required-unless-NoiseSynth. Model `midi` as `Optional[int]` at the field layer; the *conditional* (present iff not NoiseSynth) is validator rule V5 (Task 3), not a field constraint.
- Match §3/§4 field names and JSON key casing exactly (camelCase in the JSON document per the §3.9 example — use pydantic `alias`/`populate_by_name` or `serialization_alias` as needed so serialized JSON matches §3.9). IR models are internal (never serialized into the document) so their Python field names may stay snake_case.

**Tests:** construct a valid minimal instance of each model; assert field constraints reject out-of-range values (velocity 0, velocity 1.5, pan 2, durationTicks 0, bad enum, midi 200, denominator 5, lengthBars 3, ratio 0.4); assert `frozen` (mutation raises); assert serialized JSON keys match the §3.9 camelCase contract for the document models.

**Verify:** all four gates green.

### Task 3 — Document validator (V1–V8) + JSON Schema export — model: **sonnet**

**Read:** `PHASE_1.md` §3.8 (V1–V8, verbatim), §3.5 (register invariant, NoteEvent rules), §3.3 (header sorting), §3.4 (sections coverage), §3.6 (PolySynth voice rules), plus §2 "Schema export" row and §9 item 1.
**Files:** `src/trackgen/schema/validate.py` (new) — a pure function `validate_document(doc: TrackDocument) -> list[str]` (or raises a structured error; return a list of violation messages, empty == valid). A CLI/script entry to export JSON Schema: add `src/trackgen/schema/export.py` (or a `cli.py` subcommand) writing `docs/schema/trackdocument.schema.json` from `TrackDocument.model_json_schema()`. Commit the generated `docs/schema/trackdocument.schema.json`. `tests/test_validate.py` (new).

**Build** the eight structural checks exactly as §3.8 states them:
- V1 tempos & timeSignatures sorted ascending by ticks, first at tick 0.
- V2 sections contiguous from tick 0, non-overlapping, exclusive ends, full coverage (each `endTick` == next `startTick`; last `endTick` == song end).
- V3 note lists sorted by `(ticks, midi)` (unpitched: by `ticks`, and duplicate `ticks` invalid); `durationTicks >= 1`; velocity in (0,1].
- V4 register: non-drum tracks all `midi <= 71`.
- V5 `midi` present iff instrument is not `NoiseSynth`.
- V6 every `sends[].bus` resolves to a declared bus; track ids unique; bus ids unique.
- V7 PolySynth ⇒ has `voice` (in Monophonic whitelist) + `maxPolyphony`; non-PolySynth ⇒ neither.
- V8 every note ends (`ticks + durationTicks`) within the final section's `endTick`.

**JSON Schema export:** deterministic output (stable key order); the committed artifact is the client contract. Add a test that re-exporting matches the committed file (guards drift).

**Tests:** a valid document (a small hand-built one, or import the Task 5 fixture once it exists — but this task should not block on Task 5; build a minimal valid doc in-test) passes with zero violations; craft one targeted invalid document per rule V1–V8 and assert the specific violation is reported. Assert the exported schema round-trips (re-export == committed file).

**Verify:** all four gates green; V1–V8 each have a failing-case test.

### Task 4 — Pack loader + stub pack — model: **sonnet**

**Read:** `PHASE_1.md` §6 (all: §6.1 manifest, §6.2 shared envelope, §6.3 event primitives), §9 item 3. Note: only the **pinned envelope + event primitive** fields are in scope; bank-specific schema fields owned by Phases 3/4/5/7 are NOT modeled here.
**Files:** `src/trackgen/packs/` — `models.py` (frozen pydantic: `Manifest` per §6.1; `PatternEnvelope` per §6.2 with `events` typed as the §6.3 primitives — `PitchedEvent` {pos,dur,degree,octave,velocity} and `DrumEvent` {pos,voice,velocity}; `retarget` object), `loader.py` (`load_pack(path) -> StylePack` using `yaml.safe_load`, validating into the frozen models; raise a clear error on envelope/manifest violations). `styles/_stub/` — `manifest.yaml` + `patterns/{drums,bass,comping,pads}.yaml`, each a tiny bank using **only pinned envelope/event fields**. `tests/test_packs.py` (new).

**Constraints:**
- `degree` vocabulary restricted to the §6.3 v1 core: `root, third, fifth, seventh, guide3, guide7, tension, approach` (do not add Phase 5's `sixth`/`chord` — those are later extensions).
- Drum `voice` vocabulary: `kick, snare, hat_closed, hat_open, ride, crash, tom_low, tom_mid, tom_high, perc`.
- `kind ∈ {main, fill, intro, ending, break}`; `energyLevel` 1–4; `weight >= 1` (int); `lengthTicks` whole bars at PPQ 480; `retarget.onChordChange ∈ {hold, retrigger, stop}`.
- `eligibility`: pinned as optional `tempoBpm: [min,max]` only in v1.

**Tests (§9 item 3):** load `styles/_stub/` successfully and assert parsed values; then assert the loader **rejects** each class of envelope violation with a targeted bad fixture (in-test YAML strings or `tests/fixtures/`): missing required field, `weight` < 1, `weight` as float, bad `kind`, bad `degree`, bad drum `voice`, `energyLevel` out of 1–4, bad `onChordChange`.

**Verify:** all four gates green.

### Task 5 — Milestone fixture — model: **opus**

**Read:** `PHASE_1.md` §3 (all), §3.8 (validator), §3.9 (abbreviated example), §9 item 4 (exact fixture spec), §9 item 6 (listening checklist — the fixture must make each check exercisable). Depends on Tasks 2 & 3 (schema + validator committed).
**Files:** `fixtures/milestone.trackdoc.json` (new, hand-written), `tests/test_milestone_fixture.py` (new).

**Build** the milestone fixture exactly per §9 item 4:
- 16 bars: intro / verse / chorus / outro, **4 bars each**, 4/4 at PPQ 480 (one bar = 1920 ticks; sections at 0 / 7680 / 15360 / 23040, end 30720).
- Tempo change **96 → 112 at the chorus downbeat** (tick 15360) — two `tempos` entries.
- **Six tracks:** kick (MembraneSynth), snare (NoiseSynth, **unpitched** — no `midi`), hats (MetalSynth), bass (MonoSynth), comping (PolySynth/FMSynth), pads (PolySynth/AMSynth **with a Chorus insert**).
- Shared **reverb bus** with sends from snare, comping, pads. Master chain: Compressor + Limiter.
- Full `meta` echo with seed `1ps9wxb`, `seedOverrides {}`, `generatorVersion "0.1.0"`, `toneVersion` matching the playground's resolved Tone version (default `^15.1.0` — coordinate with Task 6).
- Real (hand-written) notes: drums in time; bass + comping change pitch across the hand-written chord changes; every non-drum `midi <= 71`; hats may use MetalSynth's ~G5 trigger convention (drums exempt from the ceiling). D15: exercise **every** schema feature (buses, sends, effects insert, master chain, PolySynth voice+maxPolyphony, unpitched NoiseSynth, tempo map, all four section types).

**Tests:** load the JSON, parse into `TrackDocument` (Task 2 models), run `validate_document` (Task 3) and assert **zero** violations; assert the structural facts (six tracks, tempo change at 15360, sends present, NoiseSynth track has no `midi`, all non-drum midi ≤ 71, sections cover 0–30720).

**Verify:** all four gates green; fixture passes schema + validator.

### Task 6 — Playground Tone.js player — model: **opus**

**Read:** `PHASE_1.md` §3.7 (player contract, 6 steps — normative), §3.6 (patch/effect shapes), §9 items 5 & 6. Depends on Task 5 (loads the fixture).
**Files:** `playground/index.html` (new — plain HTML + JS, **no build step**, `tone@15.x` from a CDN such as jsDelivr/unpkg). Optionally a short `playground/README.md` on how to run it (e.g. a static file server, or open directly if CDN allows).

**Build** a page implementing the §3.7 contract exactly:
1. `Tone.Transport.PPQ = header.ppq` **before** creating scheduled objects.
2. Schedule `header.tempos` via `bpm.setValueAtTime` at tick positions; never pre-flatten to seconds.
3. Instantiate instruments/effects through an explicit **whitelist map** (`"FMSynth" -> Tone.FMSynth`, etc.); reject unknown types.
4. Per-track chain: `instrument -> effects[] -> Channel(volumeDb,pan,mute) -> master`; plus `channel.send(bus, gainDb)` per send; buses' chains terminate into master; master = `Destination` ← `master.effects`.
5. Before playback: `await` every `Reverb.ready`; `.start()` on `Chorus`/`Tremolo`/`AutoFilter`.
6. Notes via `Tone.Part` with tick times; NoiseSynth ⇒ `triggerAttackRelease(duration, time, velocity)` (no pitch); others ⇒ `triggerAttackRelease(Frequency(midi,"midi"), duration, time, velocity)`; always use the callback `time` arg, never `Tone.now()`.
- UI: a file picker or fetch to load **any** fixture JSON (default `../fixtures/milestone.trackdoc.json`), a Play/Stop button, and section/tempo markers (log or on-page) so the listening checklist (§9.6) is verifiable.

**Q9 resolution:** determine the current stable `tone@15.x` on the CDN, pin that exact minor in the page, and report it back so the orchestrator aligns the fixture's `meta.toneVersion`. If current stable Tone is **not** major 15, stop and escalate — do not change the pinned assumption unilaterally.

**Verify:** this task has **no Python gate** (HTML/JS, not in the test/type surface). Verification is a code review against the six §3.7 steps + a note on how the user runs it. The §9.6 audio checklist is the user's manual step after this lands.

---

## Verification & review protocol (orchestrator)

Per `PROMPT.md` §2–§3:
- After each task: run all four gates, read output; dispatch an **opus** reviewer scoped to that task's diff (tests real & meaningful, code matches the cited PHASE_1 section, contracts honored). Bounded fix loop (max 2 cycles); escalate if a finding survives.
- Commit each task at its verified gate; update `PROGRESS.md` immediately with the commit hash.
- After all tasks: fresh **opus** whole-session reviews in parallel (correctness, contract-compliance vs PHASE_1, test quality/DoD coverage, simplification); validate each finding before fixing. Then walk the §9 DoD checklist item by item with evidence.

## Definition of Done (PHASE_1 §9) — evidence to collect

1. Schema package + §3.8 validator + committed `docs/schema/trackdocument.schema.json` — Tasks 2, 3.
2. Seed module passing the §5.6 golden-vector test — Task 1.
3. Pack loader + `styles/_stub/` + envelope-violation rejection — Task 4.
4. `fixtures/milestone.trackdoc.json` passing schema + validator — Task 5.
5. `playground/index.html` implementing §3.7 — Task 6.
6. Listening checklist — **user-run** manual step against the playground (orchestrator surfaces it; not an automated gate).
7. Determinism guard test + Ruff banned-api rule — Task 1 (test) + `pyproject.toml` (rule already present; confirm it fires).
