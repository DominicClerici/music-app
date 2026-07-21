# Session 22 — `fusion_jazz` listening set (PHASE_8 §8.4 / §9.4 step 9)

Twelve `TrackDocument` fixtures for the T8 listening gate. Open any of them in the
playground (`playground/index.html`), or re-render from the coordinates below.

Coordinates come from T6's 384-render audition sweep; every fixture was verified to
actually exhibit what it claims before being written here.

## How to play

Most fixtures reproduce through the audition CLI:

```sh
uv run trackgen audition --pack fusion_jazz --mood <mood> --seed <seed> --play
```

**Items 09b and 10 cannot** — the `audition` CLI exposes no `--ensemble` or
`--role-flavors` flag (T6 anomaly A3), so they were built with `trackgen generate
--params`. Their `.json` files here are the only way to hear them without hand-rolling
params. This gap is worth closing in C9's tooling pass.

## The checklist (DoD §14.10, fusion slice)

| # | File | Coordinate | Listen for |
| --- | --- | --- | --- |
| 01 | `01-tight-16th-pocket` | energetic / `4f5cuofjnj8p` / 120 s | **16th pocket is tight.** 144 BPM, the grid's fastest cell, swing resolved to exactly 0.5 (straight). This is `feelTable: tight`'s cleanest outing — the funk microtiming should feel near-quantized, not swung. |
| 02 | `02-slow-swing-edge` | calm / `2tr7d5zbeci59` / 120 s | **The opposite swing extreme.** 75 BPM, swing ratio ≈ 0.655 — what §6.1 calls "Purdie-shuffle territory". Does this still read as fusion, or has it become a shuffle? |
| 03 | `03-breakdown-rebuild` | energetic / `3dh2l2q87gcj2` / 120 s | **Breakdown strips to drums+bass and rebuilds.** 137 BPM vamp. The breakdown should drop to two layers, then the following `main` should bring comping and pads back. |
| 04 | `04-vamp-no-drift` | energetic / `1annhkotoruhq` / 120 s | **Vamps loop without harmonic drift** — the S22-3 fix by ear. The vamp should cycle on its authored changes with no chord appearing that wasn't written. Before the fix, a one-chord pedal rendered as `I7sus4 \| vi \| I7sus4 \| vi …`. |
| 05 | `05-quartal-ceiling` | energetic / `3i4mo6knn7ftj` / 120 s | **Quartal Rhodes sits under C5.** The grid's highest comping note (MIDI 70, B♭4). If anything pokes above C5 and crowds where a soloist would sit, it is here. |
| 07 | `07-tune-rung4-solo` | energetic / `1ps9wxb` / 120 s | **Rung 4, the `tune`-only tier** — §6.4's ride-based drive in the solo. This tier never appears in `vamp` renders (caveat C-28). |
| 08 | `08-stop-device` | energetic / `2wo6kmlu5dhb5` / 240 s | The **`stop` device** (T6 measured it firing twice here) — the funk break. Also a long-form tune with rung-4 solo content. |

## The two open questions — these decide something

### 06 — the L2-1 residual (decision S22-15)

| File | Coordinate | |
| --- | --- | --- |
| `06-THE-L21-QUESTION` | triumphant / `2fxzjnj28din9` / 240 s | ratio 0.970 on 33 strong-beat notes |
| `06b-L21-starker` | triumphant / `2fxzjnj28din9` / 120 s | ratio 0.923 on 13 notes — the same defect, starker |

A **single** A♭ sounds against an `E♭7♭9` — a natural 11 over a dominant chord, from a
quartal comping voicing at rung 2 (intro/outro sections). §6.4 excludes `11` on dom7
precisely because a perfect 4th over a dominant is the classic avoid note; that is why
`7sus4` exists as a separate chord.

This was accepted on paper at S22-15. **The question is whether it is acceptable by ear.**
If it grates, the fix is to drop `quartal` from comping rungs 1–2 (measured clean, 0/400) —
at the cost of §6.4's pinned "quartal as the low-rung signature" and a DoD §14.10 amendment,
since `rhodes` is a comping flavor and quartal would then live only on pads.

### 09 — the `fusion_ride_kit` ride (A/B pair)

| File | |
| --- | --- |
| `09a-ride-A-funk_kit` | the default kit — ride resonance 6115, decay 0.40, release 0.50 |
| `09b-ride-B-fusion_ride` | `fusion_ride_kit` — resonance **7862**, decay 0.55, release 0.70 |

Identical coordinate (energetic / `1ps9wxb` / 240 s), only the drum flavor differs, so this
is a clean A/B. `fusion_ride_kit`'s ride is both **brighter and longer** than anything else
in the repo — no other pack up-ranges a ride at all. A reviewer flagged it may read as
sizzly rather than as a ping. Its hats are correspondingly darker, so the kit is coherently
ride-forward by design; the question is only whether the ride itself is pleasant.

## 10 — the only way to hear `clav` + `AutoFilter`

`10-headhunters-clav` — energetic / `1ps9wxb` / 240 s, `ensemblePreset: headhunters`.

Flavor selection is deterministic-default and never drawn, so **4 of the pack's 8 authored
timbres never appear in an auto-parameter render**: `fusion_ride_kit`, `clav`,
`electric_finger`, `glass_pad`. That means the `AutoFilter` clav wah (§3.7's first user)
is unreachable without hand-passed params. This is engine-level behaviour that predates
fusion, not a pack defect — but it is a larger dormancy than caveat C-28 currently records.

## Logging

Per §8.4, append findings to `listening/log.jsonl` — one entry per error spotted, keyed by
the seed so every complaint is a reproducible permalink. Zero entries is a valid outcome and
is what the two prior packs recorded.
