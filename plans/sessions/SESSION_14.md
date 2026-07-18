# SESSION_14 — Phase 7 (Sound design), Chunk 2: the flip + integration + whole-phase

**Phase:** 7 — Sound design. **Chunk:** 2 of 2 (final). **Session:** 14.
**Design authority:** `plans/PHASE_7.md` (binding). Read it; this plan does not restate it.
**Orchestrator prompt:** `plans/PROMPT.md`. **Invariants:** `ROADMAP.md` §3.

---

## Where Chunk 1 left this (pinned inputs — all committed, tested, UNWIRED)

Chunk 1 (session 13) landed the new `src/trackgen/sound/` package, all unwired; four
gates green (**4364 tests**). The reference packs still run the **stub** sound surface.
The pieces C2 consumes:

- `sound/models.py` — `MappingEntry` (`{param,min,max,curve}`; curve enum; `exp⇒min,max>0`).
- `sound/allowlist.py` + `allowlist.yaml` (D12) — `load_allowlist()` → `Allowlist.is_legal(cls, path)`.
  Seeded fully-expanded, **coverage-proven** against §5.1 + §8.1/§8.2 recipes + all 3 fixtures,
  so C2 content will not false-reject.
- `sound/mod_defaults.py` + `mod_defaults.yaml` — §5.1 verbatim; `load_mod_defaults()`.
- `sound/evaluate.py` — `round3` / `evaluate_mapping` / `merge_mod` / `assert_base_xor_mod` /
  `apply_directives` + `get_by_path` / `set_by_path`. Reproduces the §9.1 anchors.
- `sound/timbres.py` — the **real** `timbres.yaml` schema (`PitchedFlavor` / `KitFlavor` /
  `KitVoice` / `MixBlock` / `EngineSpec` / `ReverbBus` / `BusConfig` / `FlavorsConfig` /
  `MasterChain` / `TimbresConfig`), TB1–TB9, and the module-private normalization helpers
  `_pitched_defaults` / `_pitched_override` / `_drum_defaults` / `_drum_override` +
  `_engine_class` / `_leaf_paths`. TB1 is the standalone `check_flavor_completeness(timbres, declared)`.

**The stub C2 REPLACES** (all deleted this session):
- `pipeline/stubs.py::sound_design(plan, pack) -> dict[str, TrackSound]` (+ `TrackSound` if it
  goes unused after the serializer rewrite).
- `pipeline/serialize.py` `_STUB_MIX`, `_MASTER_EFFECTS`, hard-coded `buses=[]`.
- `packs/models.py` stub `TimbresConfig` / `TrackTimbre` / `DrumKit`.
- The current stub `styles/{pop_rock,jazz}/timbres.yaml` content.

**Declared flavor ids** (from `interpreter.yaml`; every one needs a full recipe, TB1 is
unconditional):
- **pop_rock** — drums `[acoustic_kit, tight_kit]`, bass `[electric_fingered, electric_picked]`,
  comping `[clean_electric, crunch_electric, piano]`, pads `[warm_analog, airy_strings]`.
- **jazz** — drums `[brush_kit, ride_kit]`, bass `[upright]`, comping `[piano, guitar_hollow]`,
  pads `[airy_strings, organ_soft]`.

**Verified handoff facts (carry forward, do not re-derive):**
- **Reuse, don't re-derive:** the stage needs the identical directive-name normalization
  (`attack_hardness`→`attackHardness`) + drum `(directive,voice)` keying that live as the
  module-private helpers in `sound/timbres.py`. **T1 extracts them to a shared internal module**
  (`sound/_merge.py`) imported by both `timbres.py` and the new `sound/stage.py`, so the two
  callers cannot diverge.
- **`apply_directives` working-dict convention:** build `{**base_options, "mix": mix_block}`, run
  `apply_directives`, then split back via `result.pop("mix")`. Top-level `"mix"` is reserved (no
  whitelisted class emits an option named `mix`).
- **round3 vs §9 display:** pop bass `envelope.attack` golden is `round3=0.005` (§9.1's "0.0051"
  is a >3-decimal readability display — §9 fixtures assert full round3, not the printed digits).
- **Serializer only ever changes the sound surface:** Phase 7 changes `meta`/`instrument`/
  `effects`/`channel`/`buses`/`master`/`sends`, **never** note-structural or timing content
  (this stage emits no notes). The re-blessed fixtures must show note/tick/velocity fields
  **byte-identical** to the current Phase-6 fixtures; only the sound fields move.

---

## Chunk 2 scope

### In scope
- The `sound_design(plan, timbres) → SoundDesign` stage (§7) + the `SoundDesign` output type.
- Completing + authoring the real `styles/{pop_rock,jazz}/timbres.yaml` (the §8 abridged entries).
- The atomic flip: `resolve_pack` → real `TimbresConfig` + TB1 live vs `interpreter.yaml`;
  `StylePack.timbres` retyped; orchestrator + Serializer consume `SoundDesign`; all stubs deleted.
- Re-blessing both whole-document goldens (dedicated commit, arbitration rule 3).
- §9.1/§9.2 stage goldens field-for-field; zero-draw determinism; the DoD-6 property matrix.
- Whole-**phase** 4-lens review (across C1+C2); full DoD 1(complete)/4/5/6/7/8(user audition)/9;
  §12 amendment audit; close-out.

### Explicitly out of scope
- Any note/timing change (the stage emits no notes; note-structural fixture content is frozen).
- Riser **wiring/placement** (§4.7 recipe stays dormant; schema expresses it, no pack opts in — Q3).
- Any stage-1–6 internal change; the Phase-5/6 goldens + the 1575-doc Phase-6 property matrix must
  stay green throughout (they are the note/timing regression guard).
- LUFS/offline loudness (§6.4 guidance only). Final ear-calibration is DoD 8 (user audition, like
  Phase 1 §9.6 / Phase 6 §11.10) — code/automated DoD is fully in scope; the human ear-check is not.

---

## The `SoundDesign` type (pinned, §7)

New pydantic model in `sound/stage.py`, reusing the PHASE_1 document types:

```
TrackSound   = { instrument: InstrumentPatch, effects: list[EffectPatch],
                 channel: Channel, sends: list[Send] }   # sends: 0 or 1 (reverb)
SoundDesign  = { track_sounds: dict[str, TrackSound], buses: list[Bus], master: Master }
```

- `instrument` — the evaluated patch. PolySynth emitted as `{type, voice, maxPolyphony, options}`
  (V7); non-PolySynth as `{type, options}`. `options.volume` class trims (D7) flow through verbatim.
- `channel` — `{volumeDb, pan, mute: false}` from the evaluated mix block.
- `sends` — `[Send(bus="reverb", gainDb=<evaluated>)]` iff the evaluated mix has a reverb send,
  else `[]`.
- `buses` — `[Bus(id="reverb", effects=[Reverb{decay,preDelay per §6.2, wet:1.0},
  Filter{highpass, frequency=returnFilterHz, Q:0.5}])]` (always emitted by the stage).
- `master` — `Master(effects=pack master chain verbatim)`.

**Reverb-bus omission is the Serializer's job (§7):** the serializer includes the `reverb` bus only
when ≥1 **instantiated** track (one with phrases) sends to it; otherwise it omits the bus (keeps V6
tight). Both reference packs always have senders (snare/comping/pads etc.), so the omission branch is
defensive — but pin + test it (a synthetic all-dry document, or assert the branch directly).

**The stage keys `track_sounds` by track id:** the nine kit voice ids + `bass`/`comping`/`pads`,
exactly as the stub did (single-source the drum ids from `parts.generators._TRACK_ORDER`). It runs
before serialize (no phrases), so it emits every candidate track; the Serializer selects those with
notes.

---

## Task list

Ordering: **T1 → T2 → (T3 ‖ T4) → T5.** T3 (re-bless: `fixtures/*.json` +
`test_whole_document_goldens.py`) and T4 (new property + determinism test files) touch disjoint
files and both depend only on T2 → parallel-eligible. Everything else is serial (the flip is a
single-file-set knot). **All implementer tasks are `opus`** — none clears the "truly trivial" bar
(content authoring with §8 completion + §9 recompute; the atomic flip with wiring/deletion; the
independent re-bless arbiter; the property matrix).

| # | Task | Model | Files (scope) | Depends |
| --- | --- | --- | --- | --- |
| T1 | Stage + `SoundDesign` type + shared-helper extraction + reference content (as a **test fixture**, not yet in `styles/`) + §9 stage goldens — **all unwired, green** | opus | new `sound/stage.py`, new `sound/_merge.py`, edit `sound/timbres.py` (import extracted helpers), new `tests/fixtures/timbres/{pop_rock,jazz}.timbres.yaml`, new `tests/test_sound_stage.py` + `tests/test_sound_stage_goldens.py` | C1 |
| T2 | The atomic flip: content → `styles/`; loader swap + TB1 live + `StylePack.timbres` retype; orchestrator + Serializer consume `SoundDesign`; delete all stubs; **xfail** the 2 whole-doc reserialize goldens | opus | `styles/{pop_rock,jazz}/timbres.yaml`, `packs/loader.py`, `packs/models.py`, `pipeline/orchestrator.py`, `pipeline/serialize.py`, `pipeline/stubs.py`, `pipeline/__init__.py`, `sound/__init__.py`, any stub-referencing test (`test_milestone_fixture.py` et al.), `tests/test_whole_document_goldens.py` (xfail only) | T1 |
| T3 | Re-bless both whole-document goldens (**dedicated commit**, arbitration rule 3); remove T2 xfails; independent-arbiter verify V1–V8 + §9 sound anchors + note/timing byte-invariance | opus | `fixtures/{pop_rock,jazz}.milestone.trackdoc.json`, `tests/test_whole_document_goldens.py` | T2 |
| T4 | DoD-6 property matrix + zero-draw pipeline determinism | opus | new `tests/test_phase7_property.py`, new `tests/test_sound_determinism.py` | T2 |
| T5 | Whole-**phase** 4-lens review (C1+C2) + full DoD 1/4/5/6/7/8/9 + §12 amendment audit + close-out | orchestrator | `plans/*` (docs), review agents | T3, T4 |

---

## Per-task detail

### T1 — Stage + `SoundDesign` + shared helpers + reference content + §9 goldens (unwired)

**Why unwired stays green:** T1 touches neither `resolve_pack` nor `styles/*/timbres.yaml` nor the
pipeline. The stage is a new module consuming a `sound.timbres.TimbresConfig` passed directly; its
tests build that config from the new **test-fixture** copies of the reference content
(`tests/fixtures/timbres/*.yaml`). The stub loader stays live → all 4364 tests stay green.

**PHASE_7 sections:** §7 (stage algorithm), §3 (evaluation — reuse C1), §6.2 (bus eval), §6.3
(channel tables), §8 (content), §9 (goldens), §4.4/D7 (two-layer gain).

1. **Extract shared helpers.** Move `_pitched_defaults` / `_pitched_override` / `_drum_defaults` /
   `_drum_override` (and any of `_engine_class` / `_leaf_paths` the stage needs) from `sound/timbres.py`
   into `sound/_merge.py`; re-import them in `timbres.py` so its behavior is unchanged (TB tests stay
   green). The stage imports the same functions — one source of truth for the normalization.
2. **`SoundDesign` type + `sound_design(plan, timbres) → SoundDesign`** per §7 pseudocode:
   `d = plan.timbreDirectives`; for each role select `timbres.flavors[role][plan.roleFlavors[role]]`;
   `merge_mod(role_defaults, flavor.mod)` (§3.2); evaluate via `apply_directives` on
   `{**base, "mix": mix_block}` then split; drums → one entry per kit voice, pitched → one entry keyed
   by role name; build `channel`/`sends`/`instrument`/`effects`; bus per §6.2; master verbatim. Pure,
   zero draws (D3) — takes no rng.
3. **Author the real reference content** for both packs at `tests/fixtures/timbres/{pop_rock,jazz}.timbres.yaml`,
   completing the §8 abridged entries per the stated conventions (pop `tight_kit`, `tom_mid`/`tom_high`,
   `crunch_electric` base, `airy_strings` base; jazz `ride_kit`, `crash`, toms, `perc`, `hats`,
   `guitar_hollow` base, `airy_strings` base — the §8 `# …` comments state each direction, and every
   §9-depended value is stated in full). These files must validate clean under `sound.timbres.TimbresConfig`
   and pass TB1 against the `interpreter.yaml` declared sets. **T2 moves them verbatim into `styles/`.**
4. **§9.1/§9.2 stage goldens** (`test_sound_stage_goldens.py`): build the plan via `generate_plan`
   for each §9 example (pop `{styleFamily:"pop_rock", seed:"1ps9wxb"}`; jazz `{styleFamily:"jazz",
   mood:"melancholic", maxLengthSec:240, seed:"1ps9wxb"}`), run `sound_design`, assert **field-for-field**
   against full-precision recomputation of the §9 formulas: every evaluated patch (full options object,
   not only mapped params), every channel `{volumeDb,pan}`, every send `gainDb`, the bus
   `{decay,preDelay,returnFilterHz}`, and the master chain. Confirm the §9.1 anchors (snare 3.67; pop
   bass `filterEnvelope.baseFrequency` 1514.763, `envelope.attack` round3 0.005) and §9.2 anchors
   (brush snare 0.567; upright `modulationIndex` 2.380).
5. **Stage-level determinism:** repeated-run identity of `sound_design` on the same `(plan, timbres)`.

**⚠ Arbitration-risk surface (C-09 precedent).** The §9 tables are *derived samples*; the golden
fixtures assert the full round3 recompute. If any faithfully-recomputed value diverges from a printed
§9 number (beyond the known 0.005/0.0051 display case), **do NOT tune** — mark it `xfail` and escalate
to the orchestrator with the trace, exactly like C-09/session-08. The orchestrator resolves with user
sign-off (amend §9 + fixture in one commit) before T2.

**Return:** files created; the extracted-helper list; the two content files' full flavor coverage
(role → ids); every §9 value recomputed with any divergence flagged; test names; gate output.

### T2 — The atomic flip

**PHASE_7:** §4 (schema, live), §4.5 TB1, §7 (stage + Serializer integration), §12.4 (Serializer
stub replacement). This is the one indivisible landing; expect the two whole-doc reserialize goldens
to go red and **xfail them** (removed in T3) — every *other* test must stay green.

1. **Content → `styles/`:** replace `styles/{pop_rock,jazz}/timbres.yaml` with T1's authored files
   **verbatim** (so the §9 stage goldens still hold).
2. **`packs/loader.py`:** validate the timbres file with `sound.timbres.TimbresConfig`; after load,
   call `check_flavor_completeness(timbres, declared)` where `declared` is built from
   `interpreter.flavors` (TB1 live — "both reference files load clean" + TB1 vs `interpreter.yaml`);
   wrap failures in `PackLoadError`. Retype `StylePack.timbres` → `sound.timbres.TimbresConfig | None`.
3. **`pipeline/orchestrator.py`:** import the real `sound_design` from `sound.stage`; call
   `sound_design(plan, pack.timbres)` (guard `pack.timbres is not None`); pass the resulting
   `SoundDesign` into `serialize`.
4. **`pipeline/serialize.py`:** take `SoundDesign` (not `dict[str, TrackSound]`). For each emitted
   track fill `instrument`/`effects`/`channel`/`sends` from `design.track_sounds[track_id]`; set
   document `buses` = `design.buses` **filtered** to only buses that ≥1 emitted track sends to
   (§7 omission rule); `master` = `design.master`. Drum trigger midi still comes from the kit voice
   (now on the evaluated patch path — keep the existing `is_drum`/trigger-midi handling; a NoiseSynth
   voice has no trigger midi and its notes carry their own midi, unchanged). **Delete** `_STUB_MIX`,
   `_MASTER_EFFECTS`, the hard-coded `buses=[]`.
5. **Delete stubs:** `pipeline/stubs.py::sound_design` (and `TrackSound` if serialize no longer needs
   it — the new `SoundDesign.TrackSound` supersedes it; if `stubs.py` becomes empty, remove it and its
   imports); `packs/models.py` stub `TimbresConfig`/`TrackTimbre`/`DrumKit`; the stub-schema import in
   `loader.py`. Update `sound/__init__.py`'s "unwired" docstring.
6. **Fix stub-coupled tests:** any test importing the stub `TimbresConfig`/`TrackTimbre`/`TrackSound`/
   `_STUB_MIX` (e.g. `test_milestone_fixture.py`, stub loader tests) — retarget to the real types or
   delete if now redundant. **Do not** weaken a real assertion to make it pass; if a test encodes
   stub-specific behavior that no longer exists, delete it with a one-line why.
7. **xfail** the two `test_whole_document_goldens.py::test_fixture_reserializes_identically[pop|jazz]`
   cases with `reason="Phase-7 flip changes the sound surface; re-blessed in T3"`.

**Return:** the exact diff surface per file; every stub symbol deleted; the list of stub-coupled tests
touched (retargeted vs deleted, with why); confirmation all non-xfailed tests green + the 4 gates.

### T3 — Re-bless the whole-document goldens (dedicated commit, independent arbiter)

**Posture:** independent arbiter (C-09 / Phase-6-C3-T2 precedent) — the fixture is blessed *from the
engine*, never hand-edited.

1. Run `uv run python tests/_regen_milestone_fixtures.py`; remove the T2 xfails.
2. **Verify, do not trust:** (a) both re-blessed docs pass V1–V8 (`validate_document == []`); (b) the
   §9.1/§9.2 **sound** anchors appear in the committed docs — per-track `channel {volumeDb,pan}`,
   `sends[{bus:"reverb",gainDb}]`, the evaluated `instrument.options` for at least the §9-tabled tracks,
   the `reverb` bus `{decay,preDelay,returnFilterHz}` (pop plate-ish `decay≈1.287`, jazz chamber
   `≈1.485`), and the pack master chain; (c) **note/timing byte-invariance** — diff the re-blessed
   fixtures against the pre-flip (Phase-6) fixtures and confirm every `notes[*]`
   `ticks`/`durationTicks`/`midi`/`velocity` field is unchanged; only `meta`/`instrument`/`effects`/
   `channel`/`sends`/`buses`/`master` differ. If a note field moved, a stage-1–6 regression slipped in
   — stop and escalate.
3. Update the stub-referencing comments/anchors in `test_whole_document_goldens.py` (the `_STUB_MIX`
   / `_TRIGGER_MIDI` note; any §9.4/§9.5 anchor that references the old stub mix). Keep the
   note-structural anchors (they must be unchanged).

**Return:** arbiter check table (V1–V8, each §9 sound anchor, note-invariance diff result); track/note
counts pre vs post; any divergence escalated.

### T4 — Property matrix (DoD 6) + zero-draw determinism (DoD 5)

1. **`test_phase7_property.py`** — for both packs × every supported mood × every declared flavor
   combination (the `interpreter.yaml` `ensembles` +, if feasible, the cross-product of declared
   flavor ids per role), run `sound_design` (drive the plan through `generate_plan`/the interpreter to
   get real directives + role flavors) and assert on the output: every patch validates against the
   PHASE_1 §3.6 instrument/effect whitelists **and** every option path is allowlist-legal for its
   class; PolySynth carries `voice`+`maxPolyphony` (V7); every send references the `reverb` bus;
   `volumeDb ≤ 6`; `pan ∈ [−1,1]`; bus `decay` within the pack's authored range; master ends in a
   `Limiter`. Assert the matrix is non-trivially sized (log the count; no silent cap — ROADMAP §3).
2. **`test_sound_determinism.py`** — a counting-RNG shim asserting **zero draws** on the `sound`
   stream for both §9 examples through the full `generate_track` (D3, the Phase-6 total-draw-shim
   idiom); repeated-run identity of `generate_track` for both examples.

**Return:** matrix dimensions + document count; the invariant list asserted; zero-draw evidence; gates.

### T5 — Whole-phase review + DoD + close-out (orchestrator)

1. **Fresh `opus` 4-lens review over the whole phase (C1+C2)**, parallel disjoint lenses:
   (a) correctness/logic (evaluation, merge, stage, serializer, bus-omission); (b) contract compliance
   vs PHASE_7 §3/§4/§7 + PHASE_1 §3.6 whitelists/V-rules; (c) test quality & DoD coverage (goldens
   real & field-for-field, property matrix non-vacuous, determinism discriminating); (d) code
   quality/simplification (the extracted `_merge.py`, no stub remnants, no dead code).
2. For each finding: **validation** agent confirms it's real before any change; confirmed → fix agent
   + gate re-run (2-cycle bound).
3. **Full DoD (§13):** 1 (complete — both reference files load clean + TB1 live), 4 (§9 goldens),
   5 (determinism/zero-draw), 6 (property matrix), 7 (Serializer integration — stubs deleted, both
   docs re-blessed & V1–V8), 9 (§12 amendments applied & consistent — audit each of the 6). **DoD 8**
   (listening checklist) = user audition gate: automated portion proven (both milestone docs load in
   the Phase-1 playground; kick/snare/bass centered, cymbals off-center, pads wide, reverb on
   snare/comping/pads, kick/bass dry, master doesn't clip), ear-check logged pending like Phase 1 §9.6.
4. **Close out:** update PROGRESS.md (statuses, session log row, fresh handoff → Phase 8), CAVEATS.md
   for any deviation (§9 amendments if T1/T3 escalated; anything else), commit doc updates. Report
   built / gate evidence / DoD status / caveats / next-session (Phase 8).

---

## Gates (all four green before each commit; read the output)

```
uv run pytest            # full suite ~7m25s / 4364+ tests — use an extended timeout
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Determinism enforced by TID251 (entropy only in `seeds.py`). Never claim a gate passes without
running it and reading the output this session.

## Escalation

- Any §9 printed sample diverging from the faithful recompute (beyond the 0.005/0.0051 display) →
  arbitration rule 2: xfail + escalate for user sign-off, amend §9 + fixture in one commit. **Never**
  tune code to a printed number.
- A note/timing field changing in the re-blessed fixtures (a stage-1–6 regression) → stop, escalate.
- A ROADMAP-invariant break or a PHASE-doc amendment beyond §9 sample corrections → sign-off first.
- Fix loop exhausted (2 cycles) or scope growing beyond this plan → stop and ask.
