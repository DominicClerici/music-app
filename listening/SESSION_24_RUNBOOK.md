# Session 24 runbook — the deferred human-listening obligations (Phase 8 close-out)

## 1. Scope & why this is deferred

Every listening *instrument* is built, unit-tested, and gated green — the A/B harness
(`trackgen ab`), the anchored milestone rubric (`trackgen rubric`), and the audition
edit→hear loop (`trackgen audition`, now with `--ensemble`/`--role-flavors`). What
remains are the **human-listening obligations** those instruments exist to serve: the
milestone rubric pass, the pairwise A/B, the T1/T2 named tasks, and the per-pack
error-spotting passes. Under the "minimal now, rest later" ruling these were deferred to
a dedicated listening sitting rather than faked by an orchestrator that cannot hear.
Completing this runbook flips Phase 8 from *"built, listening-pending"* to fully done:
it discharges DoD §14.8 (T1, T2, error-spotting per pack, A/B demonstrated, one rubric
pass) and DoD §14.10 (each pack passes its own playground checklist). Nothing here
changes code or pack data — content changes discovered by ear are normal pack-version
bumps under the bless workflow, logged and made separately.

**Wall-clock is banned (ROADMAP invariant 5).** Every command below takes an explicit
`--date`; pass the real calendar date of your sitting as a literal (the examples use
`2026-07-21`). Estimated total: ~4–6 hours; the sections are independent and may be
split across sittings.

**Serving the playground.** Every `--play` / audition command writes the doc into
`playground/` and opens `index.html?doc=…`. `file://` often can't `fetch`, so if the page
is blank, from `playground/` run:

```sh
uv run python -m http.server 8012
```

then open the `http://localhost:8012/index.html?doc=…` URL the command prints.

---

## 2. The obligations — exact commands

### 2a. Milestone rubric — all 5 packs × 3 moods (§14.8, ~60–90 min)

```sh
uv run trackgen rubric --date 2026-07-21
```

Walks the **15 pinned corpus cells** (5 packs × their 3 corpus moods), each rendered at
the pinned coordinate **seed `1ps9wxb`, length `120 s`** — the same reproducible
coordinate as that cell's golden-corpus sibling. For each cell it opens the render in the
playground, then prompts a **1–5 score on each of four axes** plus optional notes. One
`{"type":"rubric"}` record per cell is appended to `listening/log.jsonl`.

The 15 cells (pack → its three moods):

| Pack | Moods (default, extreme A, extreme B) |
| --- | --- |
| `pop_rock` | happy, aggressive, calm |
| `jazz` | nostalgic, energetic, melancholic |
| `chill_lofi` | nostalgic, happy, melancholic |
| `blues` | energetic, aggressive, romantic |
| `fusion_jazz` | energetic, calm, tense |

**The four axes and their 5 anchors** (read these before scoring — they are the whole
instrument; they discriminate a 3 from a 4 in the ear, not just label numbers). The
through-line is ROADMAP §1: these are tracks a musician plays *over*, and the soloist
owns the register above ~C5.

#### `musicality`
1. Wrong-sounding: pitches clash, chords fight the key, the harmony reads as mistakes rather than choices. You'd stop the track.
2. In-key but lifeless: voice-leading lurches, phrases start and stop arbitrarily, nothing connects into a line you'd hum.
3. Believable and correct: the changes make sense and the parts fit, but it's generic — a competent play-through with no moment that rewards a second listen.
4. Musical and shapely: clear phrasing, purposeful voice-leading, tension and release land where a real player would place them, with a couple of genuinely nice touches.
5. Sounds like real musicians committed to a take: every part has intent, the harmony breathes, and there are moments you'd rewind to hear again.

#### `groove`
1. Mechanical, no pocket: feels like a click track — onsets dead on the grid with no feel, or timing so loose it stumbles. Unplayable-over.
2. Stiff: a pulse exists but it doesn't swing or breathe; kit and bass aren't locked, so the time feels shaky rather than intentional.
3. Solid time: kick and bass agree and the beat is dependable, but it's flat — you could tap along but it doesn't move you.
4. Good pocket: bass and drums lock, the swing/laid-back feel is idiomatic and consistent, and the groove has momentum you feel.
5. Locked, breathing pocket you'd loop for hours: the microtiming feels human and deliberate, the section plays as one, and the groove alone makes you want to play over it.

#### `styleFit`
1. Wrong genre: an ear-test listener would name a different style — the instruments, feel, or harmonic language betray the pack entirely.
2. In the neighborhood but full of tells: anachronistic voicings, a feel borrowed from another genre, or timbres no player of this style would reach for.
3. Recognizably the genre but textbook: hits the obvious markers without the idiom's character — a stock example, not a convincing one.
4. Idiomatic: the voicings, rhythms, instrumentation, and feel are what a player of this style actually does; it sits inside the tradition.
5. Definitively this style at its best: the details a specialist would insist on are all present and the mood inflection reads correctly — named in a bar or two, with a nod.

#### `soloistSpace`
1. No room: the arrangement crowds the solo register (above ~C5), competes for the melody, and is too busy or loud to leave the soloist anywhere to go.
2. Cramped: backing parts stray into the soloist's register or pile into the same frequency band, so you'd fight the track to be heard.
3. Adequate space: the register above ~C5 is mostly clear and levels leave headroom, but the arrangement doesn't invite a solo — you can play over it, just not eagerly.
4. Inviting: parts stay in their lane below the soloist, the texture leaves clear pockets, and the dynamics open up where a solo sits.
5. Made to be soloed over: the register is deliberately clear, the parts frame and answer an imagined soloist, density and dynamics ebb to leave space, and you can't wait to play on top of it.

---

### 2b. Pairwise A/B (§14.8d, ~25–40 min)

The **real, listened** version of the mechanism demo in `listening/session24/ab_demo.jsonl`
(that demo scripted the decisions and proved only that the harness renders a real variant
pair, blinds order reproducibly, and computes the binomial — it is *not* a listening
verdict). Run the same in-pack axis for real, making a genuine "which sounds better"
choice each trial:

```sh
uv run trackgen ab --pack fusion_jazz --mood energetic \
  --axis comping=rhodes:clav --trials 20 \
  --blind-master session24-ab-real --date 2026-07-21
```

It renders 20 seed-matched pairs, plays each pair in a blinded order (derived from
`--blind-master`, so the run replays exactly), forces a 1/2 choice, and scores the tally
with an exact two-sided binomial. One `{"type":"ab"}` record lands in `listening/log.jsonl`.

> **Note on the FM-piano A/B.** §8.4's T2 names an A/B of `piano` vs `rhodes`, but no single
> pack declares both flavors (`piano` lives in jazz/pop_rock/lofi-as-`piano_felt`; `rhodes`
> is fusion_jazz only), and `trackgen ab` requires both flavors valid in one pack — a
> cross-pack `--axis comping=rhodes:clav` on jazz is rejected `FLAVOR_UNKNOWN`. So the
> **blinded** A/B here uses an in-pack pair (rhodes:clav above, or jazz `comping=piano:guitar_hollow`);
> the piano-vs-rhodes *timbre* comparison is done as the audition A/B in §2c (T2).

---

### 2c. T1 — level calibration (§14.8, PHASE_7 Q1, ~45–90 min)

**Goal:** adjust each pack's mix data until the summed reference tracks balance, then
re-run the calibration report. This is a data pass (adjust pack channel/level YAML, never
code) confirmed by ear.

Per pack, generate the calibration artifact and listen to the full mix and to isolated
roles for level balance:

```sh
# 1. (re)compute the level/density report for the pack
uv run trackgen calibrate styles/fusion_jazz/

# 2. hear the full mix at the pinned coordinate
uv run trackgen audition --pack fusion_jazz --mood energetic --seed 1ps9wxb --play

# 3. check individual roles against the mix (repeat --solo per role; also --mute)
uv run trackgen audition --pack fusion_jazz --mood energetic --seed 1ps9wxb --solo bass --play
uv run trackgen audition --pack fusion_jazz --mood energetic --seed 1ps9wxb --solo comping --play
uv run trackgen audition --pack fusion_jazz --mood energetic --seed 1ps9wxb --mute pads --play
```

If a role sits too hot or too quiet, edit that pack's mix/channel data, re-run
`trackgen calibrate`, and re-listen. Repeat across all five packs. Record the outcome as a
`session_pass` (or error-spotting entries if levels are wrong) — see §4.

### 2d. T2 — FM-piano adequacy (§14.8, PHASE_7 Q7, ~20–30 min)

**Goal:** decide whether the FM-synthesized acoustic-piano patch is adequate in-ensemble,
or whether it should be pushed toward sampling (PHASE_1 Q8). Compare the FM `piano` against
the FM `rhodes` EP as the quality reference, in full ensemble:

```sh
# FM piano in its home ensemble
uv run trackgen audition --pack jazz --mood nostalgic --seed 1ps9wxb \
  --role-flavors comping=piano --play

# the rhodes EP reference (fusion's home ensemble)
uv run trackgen audition --pack fusion_jazz --mood energetic --seed 1ps9wxb \
  --role-flavors comping=rhodes --play

# isolate the comping timbre in each to judge the patch itself
uv run trackgen audition --pack jazz --mood nostalgic --seed 1ps9wxb --solo comping --play
```

**Outcome is binary and must be logged:** either **"acceptable"** (FM piano stands) or a
**documented push toward PHASE_1 Q8 sampling** (with the specific inadequacy noted). Record
as a `session_pass` note or, if inadequate, an error-spotting entry categorized
`register clash/mud` or a free-text `note`.

### 2e. Error-spotting pass — per new pack + the C5 reference-pack pass (§14.8 / §8.4, ~60–90 min)

Run the §8.4 error-spotting protocol once per pack: render fresh seeds for the cells under
test and listen against the **fixed checklist**, logging one entry per error spotted.

**The checklist (§8.4):**
- wrong-pitch moment
- groove stumble
- dead/abrupt transition
- register clash or mud
- ending failure
- "would I solo over this?"

Render cells to audition (vary `--seed` to get fresh material; omit `--seed` for a
drawn one):

```sh
uv run trackgen audition --pack blues --mood energetic --play
uv run trackgen audition --pack fusion_jazz --mood tense --seed <fresh> --play
```

**Every error spotted is logged as one entry**, keyed by seed so the complaint is a
reproducible permalink, in the §8.4 shape appended to `listening/log.jsonl`:

```json
{"params": {"styleFamily": "fusion_jazz", "mood": "tense"}, "seed": "<base36 seed>", "timeInTrack": "0:47", "category": "register clash/mud", "note": "pad pokes above C5 under the solo entry"}
```

`category` is one of the six checklist items. **Zero entries is a valid outcome** — it is
what chill_lofi (S20), blues (S21), and fusion_jazz (S22) each recorded — and closes as a
`session_pass` (§4). The three **new** packs (chill_lofi, blues, fusion_jazz) already have
clean passes logged; the outstanding work is the **C5 reference-pack pass**: run the same
protocol over **pop_rock** and **jazz** so all five packs have an error-spotting pass on
record.

---

## 3. The §14.10 per-pack playground checklists (verbatim)

For each pack, its default-params track and two mood extremes must serialize, validate
(Layers 1–2), and pass the pack's own listening checklist in the playground:

- **lo-fi (`chill_lofi`)** — laid-back swung groove; dropout sections audibly strip;
  fade-close rings out; nothing exuberant.
- **blues** — shuffle locks at three tempo tiers; boogie bass outlines the changes;
  turnarounds relaunch every chorus; stop lands when drawn.
- **fusion (`fusion_jazz`)** — 16th pocket is tight; vamps loop without harmonic drift;
  quartal Rhodes sits under C5; breakdown strips to drums+bass and rebuilds.

**Reference packs (C5):**

- **pop_rock** — genre-correct, idiomatic voicings and feel; endings land; no register mud
  under the solo (the rubric baseline the new packs are scored against).
- **jazz** — walked bass and comping swing lock; changes are believable; the FM piano
  (see T2, §2d) is adequate in-ensemble.

Reproduce any checklist cell in the playground with:

```sh
uv run trackgen audition --pack <pack> --mood <mood> --seed 1ps9wxb --play
```

The `fusion_jazz` slice has committed, coordinate-verified fixtures in
`listening/session22/` (see its `README.md`) covering every fusion checklist item plus the
two resolved open questions — reuse those exact coordinates to re-hear the specific moments.

---

## 4. Where results land & how to mark completion

All records append to **`listening/log.jsonl`** (heterogeneous typed JSONL — one JSON
object per line, keyed by a `type` field). The tooling appends automatically; the
error-spotting and pass records are added by hand. Record shapes:

**Error-spotting entry** (§8.4, one per error; seed-keyed permalink):
```json
{"params": {...}, "seed": "<base36>", "timeInTrack": "m:ss", "category": "<one of the six>", "note": "..."}
```

**Session pass** (a clean or closed pass for a pack; the shape used by S20/S21/S22):
```json
{"type": "session_pass", "date": "2026-07-21", "session": 24, "phase": "8/C9", "pack": "pop_rock", "protocol": "PHASE_8 §8.4 error-spotting + §14.10 reference checklist", "coverage": {"moods": [...], "focus_checks": [...]}, "entries": 0, "verdict": "pass", "note": "..."}
```

**Rubric record** (auto-appended by `trackgen rubric`, one per cell):
```json
{"type": "rubric", "date": "2026-07-21", "pack": "fusion_jazz", "mood": "energetic", "seed": "1ps9wxb", "length": 120, "scores": {"musicality": 4, "groove": 5, "styleFit": 4, "soloistSpace": 4}, "notes": "..."}
```

**A/B record** (auto-appended by `trackgen ab`, one per run):
```json
{"type": "ab", "date": "2026-07-21", "pack": "fusion_jazz", "mood": "energetic", "axis": "comping=rhodes:clav", "variantA": {...}, "variantB": {...}, "blindMaster": "session24-ab-real", "trialSeeds": [...], "n": 20, "winsA": 11, "winsB": 9, "pValue": 0.8238}
```

**Completion.** Phase 8 §14.8 + §14.10 are discharged when the log holds: 15 rubric records
(one pass over all cells), one real `ab` record, a T1 and a T2 outcome (as `session_pass`
notes or error-spotting entries), an error-spotting `session_pass` for **pop_rock** and
**jazz** (the three new packs already have theirs), and each pack's §14.10 checklist
confirmed by ear. Any error entry that survives is either fixed (a pack-version bump under
the bless workflow) or filed as a caveat. When all of that is on record, update
`plans/PROGRESS.md` to mark Phase 8 fully done.
