# SESSION 16 — Phase 8, Chunk 2: the validator suite (W1–W8 / L2 / L3)

**Status:** planning — awaiting user approval. No implementation dispatched.
**Phase / chunk:** Phase 8, Chunk 2 (per the §14/§9-chunk plan in `plans/PROGRESS.md`).
**DoD target:** PHASE_8 **§14.4** — "W1–W8 implemented with one violating fixture each; L2-1/L2-2 with per-pack thresholds from `calibration.yaml`; L3 metrics + band computation; V1–V8 unchanged and passing everywhere."

---

## 1. Scope

Build the three-layer quality/evaluation validator suite pinned in **PHASE_8 §8.1**, reading the C1
`GenerationTrace` (every IR boundary). This is **engine/validator code only** — no packs, no CLI, no
`calibration.yaml` written to disk.

**In scope:**
- **Layer 1** — hard pipeline invariants **W1–W8** (§8.1 table), each with one violating fixture. The
  suite entry `validate_pipeline(doc, trace) -> list[str]` **subsumes** the doc validator by *calling*
  the existing `schema/validate.py::validate_document(doc)` and appending the W-checks (it does **not**
  reimplement V1–V8).
- **Layer 2** — musical checks: **L2-1** chord-tone-on-strong-beat ratio (FAIL below threshold),
  **L2-2** voice crossing (WARN). Engine-default thresholds (bass 0.95 / comping 0.98); a thin
  optional `calibration.yaml` read-hook that returns `None`→defaults in C2 (no file exists yet).
- **Layer 3** — the six MusPy-shaped metrics (per-track) + the band-computation core
  (`mean ± 2.5 SD` per `(pack, mood)`). Warn-only, batch-only. **Compute core only** — the
  `trackgen calibrate` CLI and the on-disk `calibration.yaml` are **C3**, not this session.

**Explicitly OUT of scope** (these are later chunks — do NOT touch):
- The `trackgen calibrate` CLI / writing `styles/<pack>/calibration.yaml` (C3, §9.3).
- Audition CLI, pack linter, `--explain` selection log (C3).
- The 60-track golden corpus, `bless`, smoke matrix (C4).
- Any pack authoring or `styles/` edits; any reference-pack refinement (C5+).
- Any change to `schema/validate.py` (V1–V8 are **frozen** — DoD §14.4 requires them "unchanged and
  passing everywhere").
- Any change to a pipeline stage, IR schema, or `pipeline/trace.py` (C1 is closed; the trace is the
  read-only input).

**Determinism / invariants:** validators are pure read-only functions over `(doc, trace)` — no new RNG
draws, no wall-clock (TID251 enforces the import layer). W5 is the one check that *re-runs* the
pipeline (to compare a regenerate); it draws only through the existing seeded path.

---

## 2. Module layout (pinned)

New package `src/trackgen/quality/`:

| File | Owner task | Contents |
| --- | --- | --- |
| `quality/_common.py` | T1 | Shared read-only helpers (see §3). Imported by every layer. |
| `quality/layer1.py` | T1 (W1/W3/W4/W6/W8) → T2 (W2/W5/W7) | The eight W-checks + `layer1_checks(doc, trace) -> list[str]` aggregator. |
| `quality/layer2.py` | T1 stub → T3 fill | `layer2_checks(doc, trace) -> list[str]` (L2-1 fail + L2-2 warn) + threshold source. |
| `quality/layer3.py` | T4 | `compute_metrics(trace) -> dict` (six metrics, per track/role). |
| `quality/calibration.py` | T4 | `compute_bands(batch) -> Calibration`; the `calibration.yaml` dataclass shape + a `load_calibration(pack) -> Calibration \| None` reader (returns `None` when absent). |
| `quality/suite.py` | T1 | `validate_pipeline(doc, trace)` = `validate_document(doc)` + `layer1_checks` + `layer2_checks`. |

**No import cycle** (verified by scoping): `schema/validate.py`→`schema/document` only; `pipeline/trace`
→ stages + `schema/ir`; nothing under `schema/`/`pipeline/`/`parts/` imports `quality/`. `quality/*`
importing `validate_document`, `GenerationTrace`, IR structs, and `theory` helpers is one-directional.
Import `GenerationTrace` normally (not under `TYPE_CHECKING`) — the suite is never imported by a stage.

Tests: `tests/test_quality_layer1.py` (T1 + T2), `tests/test_quality_layer2.py` (T3),
`tests/test_quality_layer3.py` (T4).

---

## 3. Shared helpers (T1 builds in `quality/_common.py`)

Every helper is a pure function over trace/IR fields. Verified field names (from `schema/ir.py`):

- **`entry_index(trace) -> dict[tuple[str, Role], ArrangementEntry]`** — index `trace.arrangement.entries`
  by `(entry.section_id, entry.role)`. (The IR stores a **flat list**, not a dict — the handoff's
  `registers[(id,role)]` sketch does not match; build the index.) Fields: `ArrangementEntry.{section_id,
  role, active, intensity, density_budget, register}`, `Register.{low_midi, high_midi}`.
- **`tick_to_section(trace) -> callable(tick) -> FormSection | None`** — map a tick to the `FormSection`
  whose span `[start_bar*1920, (start_bar+length_bars)*1920)` contains it. `_TICKS_PER_BAR = 1920`
  (4/4, all v1 packs; `Header.ppq = 480`). Use **`trace.song_form.sections`** (`FormSection.{id, type,
  start_bar, length_bars, energy, ending, harmony_tag}`), **never** `doc.sections` (those carry a display
  `label`, no `id` matching `ArrangementEntry.section_id`).
- **`governing_chord(trace, tick) -> ChordEvent | None`** — the `ChordEvent` in `trace.harmony.chords`
  whose span `[start_tick, start_tick+duration_ticks)` contains `tick`. `ChordEvent.{start_tick,
  duration_ticks, section_id, chord, scale, function, tags}`; `EventScale.{root_pc, name}`.
- **`INTERNAL_TAGS: frozenset[str]`** and **`strip_internal(tags) -> list[str]`** — the C-11 internal
  drum provenance tags to exclude from the W6 output-vocabulary check: the drum-voice names (the domain
  of `parts/generators.py::_VOICE_TRACK` — `kick, snare, hat_closed, hat_open, ride, crash, toms, perc`)
  plus `"ornament"`. Derive the voice-name set by importing `_VOICE_TRACK` (single-source it; do not
  hardcode a copy that can drift). **Note the collision:** `"crash"` is BOTH a pinned output tag (§3.9)
  AND a drum voice name — do not strip `"crash"`; strip only the non-output provenance names + `ornament`.

Chord-tone / scale pcs come from existing theory helpers (do **not** re-derive): `theory/chords.py::
chord_tones(spec) -> list[int]` and `scale_pcs(root_pc, name) -> list[int]`. The per-event scale hint is
pre-attached on `ChordEvent.scale`, so L2-1 / scale-consistency use `scale_pcs(ce.scale.root_pc,
ce.scale.name)` directly — no key reconstruction.

---

## 4. Scoping decisions (pinned in this plan; flagged for user at the approval gate)

§8.1's W-check descriptions are one-liners; the code exposes latitude. These resolutions are the
faithful, mechanical readings and **honor existing caveats** — none amends a PHASE doc or breaks an
invariant. **The five marked ★ are the judgment calls surfaced to the user for confirmation.**

1. **★ W6 / C-11 tag handling.** `NoteEvent` in the document carries *no* tags (serializer drops them),
   so W6 is inherently a **trace-phrase** check. Drum `PhraseNote`s carry sanctioned C-11 internal
   provenance tags (voice names + `ornament`) that are NOT in the pinned output set
   `{ghost, push, fill, crash, var, hold}`. **Decision:** W6 reads `phrases_stage7`, `strip_internal(...)`
   the C-11 tags, and asserts the remainder ⊆ the pinned set. This catches a genuine stray/typo tag
   while not false-positiving on the logged provenance mechanism. (Alternative rejected: run W6 on the
   tagless document → vacuously true.)
2. **★ W2 device-policy strictness.** Fill-vs-stop and phrase-fill inclusion are RNG **draws**, so the
   exact device at a given boundary is not statically knowable from `SongForm` alone. **Decision:** W2 is
   a **policy-consistency evidence check**, not a per-boundary re-derivation: for each section boundary,
   assert the *rendered* evidence is legal for the **entered section type** per the §3.2 table —
   suppression classes (`postchorus`, `breakdown`) carry no entry crash; `breakdown` entries show dropout
   truncation; a `crash`-tagged event only lands on a legal entered downbeat; `fill`-tagged events only
   in a fill bar (last bar of the outgoing section) or a rendered stop window. It verifies "the devices
   present are policy-legal," not "the exact drawn device fired." `breakdown`/`postchorus` are not
   produced by any v1 reference form, so those branches are exercised by the **synthetic violating
   fixture** only. (Reads `phrases_stage6` tags + `song_form` boundaries; keys only on `fill`/`crash`,
   ignoring C-11 provenance.)
3. **★ W7 grid legality granularity.** Checks **`phrases_stage6`** (pre-humanizer — humanize
   legitimately moves onsets off-grid via swing/jitter, which is exactly why the trace keeps a separate
   post-6 snapshot). **Decision:** per-note grid membership — `pos_in_beat = ticks % 480` must lie on the
   straight grid (`{0,120,240,360}` 16th / `{0,240}` 8th) **or** the triplet grid `{0,160,320}` (§3.1).
   Mutation-added / non-authored events (`var`, `crash`, `hold` tags) are **grid-exempt** (they are
   device/mutation artifacts, not authored pattern onsets). The one-grid-**per-pattern** homogeneity
   (§3.1's flam rule) is checked at the **per-`Phrase`** grouping available in the trace (a Phrase is
   one `(section, role)` span); flag in the implementation notes that recovering true per-source-pattern
   grouping is lost after tiling/mutation, so per-Phrase homogeneity is the faithful mechanical proxy.
4. **★ W4 density-gate recheck.** The doc does not label which note came from which pattern event, so a
   doc-note→event backmap is not generally possible (only drums expose it via the C-11 `ornament` tag on
   `phrases_stage5`). **Decision:** W4 is a **selection-vs-budget recompute**: for each active
   `(section_id, role)` pattern-mode entry, for each authored event with `min_density is not None`, flag
   any pair where `entry.density_budget < event.min_density` **and** the event nonetheless appears
   instantiated — i.e. re-run the `parts/dynamics.py::is_event_active(min_density, density_budget)` gate
   and assert the active-set is consistent (catches a budget/threshold drift bug). Reads
   `trace.selection` (pattern envelopes' events) + `entry_index`.
5. **★ W5 determinism placement.** Implemented as `regenerate_matches(doc) -> bool` /
   check that re-running `generate_trace(doc.meta.params).document` serializes **byte-identical**. It
   *is* included in `validate_pipeline` (§8.1: "runs on every render") but the implementer must expose
   it such that a caller can skip it (it doubles render cost); the C4 smoke matrix is its primary home.
   Confirm `doc.meta.params` round-trips the exact `raw_params` (incl. seed) that `serialize(...,
   params=...)` echoes.

Non-★ (mechanical, unambiguous): **W1** per-`(section,role)` lane membership (strengthens V4; keep V4
running as the drum-skip fallback) — `low_midi ≤ midi ≤ high_midi` for every non-drum doc note in its
section's lane. **W3** ending integrity — assert ≥1 `"final"`-tagged `ChordEvent` and the last is
degree-1-rooted (`chord.root_pc == trace.harmony.keys[0].tonic_pc`); `T_last = ` its `start_tick`; in the
document no drum attack `≥ T_last` except the single hold crash+kick, and pitched notes at `T_last`
extend to the final section `end_tick`. **W8** per-`track_id` note-count identical between
`phrases_stage6` and `phrases_stage7` (the PHASE_6 D1 humanizer contract).

**L2-1 beat sets** (confirmed from §8.1 text): bass = beat 1 only (`ticks % 1920 == 0`); comping =
strong beats 1 & 3 (`ticks % 1920 in {0, 960}`). FAIL if ratio `< 0.95` (bass) / `< 0.98` (comping).

---

## 5. Task list

All implementer tasks are **`opus`** — every one involves real judgment (validator logic against a
nuanced design, discriminating fixtures, caveat interactions); none clears the "truly trivial" bar.

**Wave A (structural foundation, alone):**

| # | Task | Model | Files (write) | Depends |
| --- | --- | --- | --- | --- |
| **T1** | `quality/_common.py` (all §3 helpers) + `quality/layer1.py` with **W1, W3, W4, W6, W8** + the `layer1_checks` aggregator + `quality/layer2.py` **stub** (`layer2_checks` returns `[]`) + `quality/suite.py::validate_pipeline(doc, trace)` = `validate_document(doc)` + `layer1_checks` + `layer2_checks`. One violating fixture per W1/W3/W4/W6/W8 + a **subsumption** test (a real `generate_trace` doc passes `validate_pipeline` cleanly AND `validate_document` still returns `[]`). | opus | `src/trackgen/quality/{_common,layer1,layer2,suite}.py`, `tests/test_quality_layer1.py` | — |

**Wave B (after T1; T2 ‖ T3 ‖ T4 — disjoint files):**

| # | Task | Model | Files (write) | Depends |
| --- | --- | --- | --- | --- |
| **T2** | Add **W2, W5, W7** to `quality/layer1.py` (into `layer1_checks`). One violating fixture each (W2: synthetic breakdown/postchorus + a stray crash; W5: mutate `doc.meta`/a note so regenerate differs; W7: shift one `phrases_stage6` onset off-grid). Extends `tests/test_quality_layer1.py`. | opus | `src/trackgen/quality/layer1.py`, `tests/test_quality_layer1.py` | T1 |
| **T3** | Fill `quality/layer2.py::layer2_checks` — **L2-1** (fail, ratio + engine defaults 0.95/0.98) + **L2-2** (warn, voice crossing) + the thin `calibration.yaml` threshold read-hook (returns defaults in C2). One violating fixture each (L2-1 sub-threshold; L2-2 crossing). `tests/test_quality_layer2.py`. | opus | `src/trackgen/quality/layer2.py`, `tests/test_quality_layer2.py` | T1 |
| **T4** | `quality/layer3.py::compute_metrics` (the six metrics, per track/role, grounded in `TrackDocument`) + `quality/calibration.py::compute_bands` (mean ± 2.5 SD per `(pack, mood)`) + the `Calibration` dataclass/`calibration.yaml` shape + `load_calibration(pack) -> Calibration \| None`. Tests: metric values on a real doc + band arithmetic on a small synthetic batch. `tests/test_quality_layer3.py`. | opus | `src/trackgen/quality/{layer3,calibration}.py`, `tests/test_quality_layer3.py` | T1 |

**Wave C:**

| # | Task | Model | Depends |
| --- | --- | --- | --- |
| **T5** | Whole-chunk 2-lens review (correctness/contract + test-quality/DoD) over the full C2 diff + DoD §14.4 checklist with evidence + close-out (PROGRESS handoff → C3, any CAVEATS). | orchestrator | T2, T3, T4 |

Note on T2/T3/T4 test-file disjointness: T2 extends `test_quality_layer1.py`; T3 writes
`test_quality_layer2.py`; T4 writes `test_quality_layer3.py`. Source files are disjoint (T2→layer1.py,
T3→layer2.py, T4→layer3.py+calibration.py). Safe to run in parallel. `suite.py` is written once (T1) and
never re-edited — the aggregators it calls (`layer1_checks`, `layer2_checks`) are filled in place, so no
task re-touches `suite.py`.

---

## 6. Verification each task must pass

Gates (all four, read the output) — the full suite is **~11m20s / ~4758 tests**; run pytest with an
extended timeout:

```
uv run pytest            # extended timeout
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Per-task specifics:
- **T1** — `validate_pipeline` on a real `generate_trace(pop_rock/jazz)` returns `[]`; `validate_document`
  on the same doc still returns `[]` (subsumption). Each of W1/W3/W4/W6/W8 has a fixture that fires
  **that rule id only** (message prefixed `W1:`…`W8:`), built by `generate_trace(real)` →
  nested `model_copy(update=...)` → `dataclasses.replace(trace, ...)` (frozen pydantic + frozen
  dataclass; the pattern `tests/test_validate.py` uses for V1–V8). W6 fixture: a stray non-provenance tag
  on a phrase note; prove the C-11 drum provenance tags do NOT fire W6 (discriminating).
- **T2** — W2/W5/W7 fixtures fire only their own rule. W2 must exercise a suppression-class branch
  (synthetic `breakdown` entry). W7 fixture proves a swung stage-**7** onset would NOT be flagged (it
  reads stage-6). W5 fixture proves a mutated doc fails regenerate while the untouched doc passes.
- **T3** — L2-1 sub-threshold fixture drops the ratio below 0.95/0.98 and FAILs; a real doc passes.
  L2-2 crossing fixture warns; L2 uses engine defaults (no `calibration.yaml` on disk). Prove the beat
  sets (bass beat-1 only; comping beats 1 & 3).
- **T4** — `compute_metrics` on a real doc returns all six metrics with hand-checkable values on at least
  one (e.g. note-density = notes/bar); `compute_bands` on a synthetic 3–4-value batch reproduces
  `mean ± 2.5 SD` exactly. Warn/batch-only — not wired into the per-render suite.

**Review (T5):** two fresh opus lenses over the whole C2 diff — (a) correctness/contract: do the checks
match §8.1 and the §4 pinned decisions, are the caveat interactions (C-10/11/12) handled, no invariant
broken, V1–V8 untouched; (b) test-quality/DoD: is every violating fixture **discriminating** (fires its
own rule, not another; a real doc passes), not vacuous or tuned. Bounded 2 fix cycles per finding.

---

## 7. DoD §14.4 mapping

- W1–W8 implemented, one violating fixture each → T1 (W1/W3/W4/W6/W8) + T2 (W2/W5/W7).
- L2-1 / L2-2 with per-pack thresholds from `calibration.yaml` → T3 (engine defaults + read-hook; the
  file itself is C3 — note the bootstrap order §8.1 line 753: C2 gates on defaults, C3 writes the file).
- L3 metrics + band computation → T4.
- V1–V8 unchanged and passing everywhere → `schema/validate.py` untouched; subsumption test (T1) +
  full-suite green after every task.
