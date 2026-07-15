# playground — Tone.js milestone player

Throwaway page (not product code) that de-risks the `TrackDocument` output contract by
playing a fixture through Tone.js. Implements the **PHASE_1 §3.7 player contract** exactly.

## Run it

The page fetches `../fixtures/milestone.trackdoc.json` by default, so it needs a static
file server (a `file://` open hits CORS on that fetch). From the repo root:

```sh
uv run python -m http.server
```

then open <http://localhost:8000/playground/> and click **Play** (audio starts only on a
user gesture, per the browser autoplay policy).

The **file picker** loads any fixture JSON directly and works **without** a server (no
fetch involved) — use it if you'd rather just open `index.html` from disk.

## Tone.js version

Pinned to **`tone@15.1.22`** (current stable 15.x, resolved 2026-07-14) via jsDelivr CDN,
no build step. Major 15 matches the fixture's `meta.toneVersion: "^15.1.0"`.

## §3.7 steps implemented

1. `Transport.PPQ = header.ppq` set **before** any scheduled object (`buildGraph`).
2. Tempo map scheduled at tick positions via `bpm.setValueAtTime` over an accumulating
   tick→seconds walk — never pre-flattened to seconds.
3. Instruments/effects instantiated through explicit **whitelist maps**
   (`INSTRUMENT_WHITELIST`, `VOICE_WHITELIST`, `EFFECT_WHITELIST`); unknown types are
   rejected and logged.
4. Per-track chain `instrument → effects[] → Channel(volumeDb,pan,mute) → master`, with
   `channel.send(bus, gainDb)` per send; buses `receive()` their id and terminate into the
   master chain; master `effects → Destination`.
5. Before playback: `await` every `Reverb.ready`, then `.start()` LFO effects
   (`Chorus`/`Tremolo`/`AutoFilter`).
6. Notes scheduled via `Tone.Part` at tick transport positions (`"<n>i"`); NoiseSynth
   triggers without pitch, all others with `Frequency(midi,"midi")`; always uses the Part
   callback's `time` argument.

## UI

File picker + default fetch, Play/Stop, a sections table and tempo-map table, a live
playhead (current tick / bpm / active section), an on-page console logging every
instantiated node and any rejected type, and a **per-bus mute** checkbox (mute the reverb
bus → dry) for the listening checklist.

## Manual verification

The **PHASE_1 §9.6 listening checklist** is the human's manual step — run it against the
milestone fixture in this page (all six tracks audible, tempo steps up at the chorus,
reverb audible on sends and dry when the bus is muted, plays identically on reload, etc.).
