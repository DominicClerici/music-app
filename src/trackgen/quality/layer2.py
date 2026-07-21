"""Layer 2 — musical rule checks (PHASE_8 §8.1; SESSION_16 §4).

Two musical checks over `(doc, trace)`, split by severity: L2-1 is a **FAIL**
(gates a render as invalid), L2-2 is a **WARN** (non-gating). The suite realizes
that split by calling `layer2_failures` (L2-1) into its gating result and
`layer2_warnings` (L2-2) into its separate soft-warning result.

- **L2-1** chord-tone-on-strong-beat ratio (**FAIL** below threshold) —
  `layer2_failures`. For the fraction of a role's strong-beat notes whose pitch
  class lies in the governing chord's tones ∪ chord-scale ∪ the §6.4 legal
  altered tensions for its quality (S22-13 — see `allowed_pitch_classes`), the
  ratio must clear the role threshold. The strong-beat sets are asymmetric
  (§8.1, confirmed §4):
  **bass** = beat 1 only (`ticks % 1920 == 0`); **comping** = strong beats 1 & 3
  (`ticks % 1920 in {0, 960}`).
  L2-1 measures **`trace.phrases_stage6`** — the pre-humanizer snapshot — not
  `doc.tracks`; see `_check_l2_1_chord_tone_ratio` for why, and
  `layer2_skip_diagnostics` for the loud unmeasurable-role signal.
  Where the pack's own voicing table puts the **quartal** class in play for a
  `(role, section)`, the allowed set additionally admits the perfect fourth above
  the chord root (C-32) — see `quartal_voiced_groups`.
- **L2-2** voice crossing (**WARN**) — `layer2_warnings`. At every
  *voiced-sonority* instant — a tick where a bass note AND a comping note are both
  struck (a shared onset) — `max(sounding bass midi) < min(sounding comping midi)`
  must hold; otherwise the voices cross and a warning is emitted. Warnings do NOT
  gate a render as invalid; they carry the `"L2-2:"` prefix. See the crossing-grain
  note on `_check_l2_2_voice_crossing`.

Thresholds are engine defaults (bass 0.95 / comping 0.98) unless a pack's
`calibration.yaml` overrides them. The override lives in the per-`(pack, mood)`
artifact (§8.1: `moods.<mood>.l2Thresholds.{bass,comping}`) that `trackgen
calibrate` writes; `load_l2_thresholds` delegates to
`calibration.load_calibration` — the single reader of that shape — keyed by the
document's mood, so a written `calibration.yaml`'s thresholds are actually read
by L2-1. When no `calibration.yaml` exists (the C2 state, and any pack without a
blessed calibration) the read returns `None` and the engine defaults are used.
"""

from __future__ import annotations

from typing import NamedTuple

from trackgen.packs import resolve_pack
from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality._common import governing_chord
from trackgen.quality.calibration import load_calibration
from trackgen.schema.document import TrackDocument
from trackgen.schema.ir import ChordEvent
from trackgen.theory.chords import (
    EXTENSION_OFFSETS,
    chord_tones,
    legal_extensions,
    scale_pcs,
)

# PHASE_1: PPQ 480, 4/4 — one beat is 480 ticks, one bar 1920 ticks.
_TICKS_PER_BEAT = 480
_TICKS_PER_BAR = 1920

# Bar-relative strong-beat onsets: beat 1 at 0, beat 3 at 960 (2 * 480).
_BEAT_1 = 0
_BEAT_3 = 2 * _TICKS_PER_BEAT

# Engine-default L2-1 thresholds (SESSION_16 §4; C3 overrides via calibration.yaml).
_BASS_THRESHOLD = 0.95
_COMPING_THRESHOLD = 0.98

# C-32: the quartal voicing class and the offset of its second voice. The class
# is `[[0, 5, 10, 15]]` (`theory/voicing.py:185`) — offset 5 is the perfect
# fourth above the root, i.e. the natural 11 §6.4's tension table withholds from
# a dominant 7th. Named here so the widening reads against the shape it comes
# from rather than a bare literal.
_QUARTAL_CLASS = "quartal"
_QUARTAL_FOURTH = 5

# Strong-beat set per role, as bar-relative onset residues.
_STRONG_BEATS: dict[str, frozenset[int]] = {
    "bass": frozenset({_BEAT_1}),
    "comping": frozenset({_BEAT_1, _BEAT_3}),
}


def load_l2_thresholds(
    pack: str, mood: str | None = None
) -> tuple[float, float] | None:
    """Read `(bass, comping)` L2-1 thresholds from a pack's `calibration.yaml`.

    Delegates to `calibration.load_calibration`, the single reader of the
    per-`(pack, mood)` artifact shape (`moods.<mood>.l2Thresholds.{bass,comping}`)
    that `trackgen calibrate` writes — so the thresholds L2-1 measures against are
    exactly the ones the calibrator emits. Returns `None` (⇒ caller falls back to
    the engine defaults `(0.95, 0.98)`) when the file is absent, when the given
    mood has no cell, or when the cell's thresholds are malformed. `mood` defaults
    to the pack's interpreter default mood when not supplied.
    """
    calibration = load_calibration(pack)
    if calibration is None:
        return None
    if mood is None:
        resolved = resolve_pack(pack)
        if resolved is not None and resolved.interpreter is not None:
            mood = resolved.interpreter.default_mood
    pmc = calibration.moods.get(mood) if mood is not None else None
    if pmc is None:
        return None
    bass = pmc.l2_thresholds.get("bass")
    comping = pmc.l2_thresholds.get("comping")
    if not isinstance(bass, int | float) or not isinstance(comping, int | float):
        return None
    return float(bass), float(comping)


def allowed_pitch_classes(chord: ChordEvent, *, quartal: bool = False) -> set[int]:
    """The L2-1 in-set pitch classes for a governing chord (S22-13, C-32).

    `chord tones ∪ chord-scale ∪ legal altered tensions`. The third term reuses
    PHASE_4 §6.4's own legality table (`theory.chords.legal_extensions`) — the
    same hard filter dressing and the document validator enforce — rather than a
    second, drift-prone list. Without it, a voicing that sounds a tension the
    §6.4 table declares legal for the quality (canonically: a quartal comping
    voicing's ♯9 over a dom7) counts as out-of-set purely because that alteration
    is absent from the parent scale — a validator gap, not a musical fault. The
    term is strictly additive: it only unions in more classes, so anything that
    passed before still passes, and legality stays quality-specific (a ♯9 is
    in-set over dom7 and still out-of-set over maj7).

    **`quartal=True` unions in one further class: the perfect fourth above the
    chord root** (`root_pc + 5`, the natural 11) — C-32, ruled by the user
    2026-07-21 as option D of the S23-2 disposition, and the exact precedent
    C-29 set for the ♯9 of the very same voicing. `theory/voicing.py:185` pins
    the class as `[[0, 5, 10, 15]]`, so a quartal voicing *always* sounds that
    fourth — but **this widening admits offset 5 only**, so "always sounds it" is
    not "always allowed". Offsets 10 and 15 are in the set only where they happen
    to fall in some *other* term: over the shipped case (`dom7` in
    `half_whole_dim`) 10 is a chord tone and 15 → ♯9 is a legal extension per
    C-29, so both land. That is a property of the quality, not of the voicing.
    Over `maj` in `lydian` **all three** of 5, 10 and 15 sit outside the set
    (lydian carries the ♯11, not the natural 11) — reachable at chord level,
    though it has never bitten in practice, since no shipped pack pairs a quartal
    comping rung with that chord (see the 3 200-render measurement below). A pack
    that authors a quartal comping ladder over other qualities must re-measure
    rather than inherit this paragraph as a guarantee. PHASE_8 §6.4 in turn pins
    quartal as fusion's signature low-rung
    comping harmony. §6.4's tension table then excludes `11` over a dominant
    7th — correctly, as a musical rule about *dressing* a chord symbol (the
    avoid note that makes `7sus4` a separate quality) — but the fourth is not
    dressing here, it is a structural voice of a voicing class the pack was
    told to use. Measured over 3 200 fusion renders, this is the **only**
    out-of-set pitch class L2-1 ever sees on fusion comping: interval 5 over a
    dom7 in `half_whole_dim`, and nothing else at all.

    The flag is a *caller's* statement about which voicing class is in play, not
    a property of the chord: see `quartal_voiced_groups` for how `measure_l2_1`
    derives it from pack data, and why the default stays `False` so no other
    pack's gate is loosened. Strictly additive in the same sense as C-29 — one
    more pitch class, never one fewer."""
    tension_pcs = {
        (chord.chord.root_pc + EXTENSION_OFFSETS[ext]) % 12
        for ext in legal_extensions(chord.chord.quality)
    }
    quartal_pcs = {(chord.chord.root_pc + _QUARTAL_FOURTH) % 12} if quartal else set()
    return (
        set(chord_tones(chord.chord))
        | set(scale_pcs(chord.scale.root_pc, chord.scale.name))
        | tension_pcs
        | quartal_pcs
    )


def quartal_voiced_groups(trace: GenerationTrace) -> frozenset[tuple[str, str]]:
    """The `(role, section_id)` pairs whose pack voicing classes include quartal.

    **The mechanism C-32's widening keys off, and the reason it cannot leak.**
    Nothing downstream of `parts/voicing.py::build_voicing_map` records *which*
    candidate class won the Viterbi pass — `optimal_voicing_path` returns bare
    MIDI lists, and the per-role voicing map never enters the `GenerationTrace`
    — so per-note provenance does not exist to be read. What does exist is the
    pinned pack data that *produced* the candidates: `pack.voicing[role].
    classes[rung]`, indexed by the intensity the arrangement assigned that
    `(role, section)`. Keying off it means the widening is switched on by
    exactly the authored table that puts a quartal fourth into the render.

    Narrow on three independent axes, each of which alone confines it to
    fusion_jazz comping:

    1. **Only roles with a `voicing:` block.** `bass` has none — it is not a
       voiced role — so a bass group can never be widened, whatever the pack.
    2. **Only rungs that declare `quartal`.** Of the five shipped packs, the only
       comping ladder naming quartal is fusion_jazz's, at rungs 1–2 (`styles/
       fusion_jazz/patterns/comping.yaml`); pop_rock, jazz, chill_lofi and blues
       name triad/shell/rootless classes exclusively. jazz *does* use quartal —
       but for **pads**, and L2-1 is defined over bass and comping only
       (`_STRONG_BEATS`), so it is never measured and never widened.
    3. **Only sections at such a rung.** fusion's rungs 3–4 are
       `rootless_a/rootless_b` and stay on the un-widened set.

    A pack that later authors quartal comping opts into the same treatment by
    the same data, which is the point: the widening tracks the voicing table
    rather than a pack name.

    Known over-approximation, stated rather than hidden: a quartal-declaring rung
    also offers `rootless_a`/`rootless_b`, and the DP may pick one of those for a
    given chord. Such a group is widened even though no quartal fourth sounded in
    it — the fourth is *admitted*, not *required*. Tightening that would need the
    per-note provenance the pipeline does not carry; the residual cost is one
    extra pitch class on fusion comping rungs 1–2 only."""
    pack = resolve_pack(trace.plan.style_pack.id)
    if pack is None:
        return frozenset()
    return frozenset(
        (entry.role, entry.section_id)
        for entry in trace.arrangement.entries
        if entry.role in pack.voicing
        and _QUARTAL_CLASS in pack.voicing[entry.role].classes.get(entry.intensity, ())
    )


# Memo key for `_memoized_allowed_pitch_classes`: every field of the `ChordEvent`
# that `allowed_pitch_classes` reads, plus its `quartal` argument. `extensions` is
# included even though it is empirically inert on shipped packs (`extensions ⊆
# legal_extensions(quality)`, so its pitch classes are already inside the
# `tension_pcs` term) — a *total* key cannot rot, and `allowed_pitch_classes` is
# public, so a hand-built `ChordEvent` carrying an extension its quality does not
# declare legal is reachable and would otherwise collide. The `quartal` flag is
# part of the key for the same totality reason: the same chord is measured under
# both settings within one render (C-32 widens per section, not per document), so
# omitting it would serve a widened set to an un-widened group.
# See `test_allowed_pitch_class_memo_matches_uncached_lookup`.
_AllowedKey = tuple[int, str, tuple[str, ...], int, str, bool]


def _memoized_allowed_pitch_classes(
    cache: dict[_AllowedKey, set[int]], chord: ChordEvent, quartal: bool = False
) -> set[int]:
    """`allowed_pitch_classes(chord, quartal=…)`, memoized in `cache`.

    Pure-function memo: the return value must equal
    `allowed_pitch_classes(chord, quartal=quartal)` for every `(chord, quartal)`,
    whatever the cache already holds. A render reuses a handful of distinct chord
    identities across thousands of notes, so the memo removes almost all of the
    repeated set construction."""
    key: _AllowedKey = (
        chord.chord.root_pc,
        chord.chord.quality,
        tuple(chord.chord.extensions),
        chord.scale.root_pc,
        chord.scale.name,
        quartal,
    )
    allowed = cache.get(key)
    if allowed is None:
        allowed = cache[key] = allowed_pitch_classes(chord, quartal=quartal)
    return allowed


class L2_1Measurement(NamedTuple):
    """One measured `(track_id, role)` group's L2-1 population, at stage-6 grain.

    `total` is the measurable denominator (strong-beat, pitched, chord-governed
    notes); `in_set` the numerator; `pitched` every pitched note the group
    emitted, measurable or not. `pitched > 0 and total == 0` is the *vacuous*
    case — the group produced notes but L2-1 could measure none of them."""

    track_id: str
    role: str
    total: int
    in_set: int
    pitched: int


def measure_l2_1(trace: GenerationTrace) -> list[L2_1Measurement]:
    """L2-1's per-`(track_id, role)` populations, read from `trace.phrases_stage6`.

    **Grain (S23-1, C-31).** L2-1 is defined over notes "attacking on beats 1/3"
    (§8.1). Those attacks exist on the *pre-humanizer* grid: stage 7 applies swing
    and jitter, which displace onsets off ticks 0/960 by design, so an exact
    `ticks % 1920 in strong` filter over `doc.tracks` discards most of the
    population it is defined over — measured at 5–18 % retention, and **0 %** for
    jazz and chill_lofi comping, where the check degenerated to a vacuous pass.
    Reading `phrases_stage6` is the same treatment W7 already applies for the same
    reason (`layer1.py::_check_w7_grid_legality`); L2-1 simply never got it.

    A `Phrase` is one `(section, role)` span, so a track's notes arrive across
    several phrases; they are accumulated per `track_id` (matching the per-track
    grain of the document the check used to read). Groups appear in first-phrase
    order, so the result is deterministic.

    A note whose governing chord is undefined is excluded from both numerator and
    denominator — with no chord in force there is no set to measure it against.

    **Allowed set (C-32).** A note is measured against the widened set when its
    `(role, section)` is one the pack's voicing table puts quartal in play for —
    `quartal_voiced_groups`, which on the five shipped packs is fusion_jazz
    comping at rungs 1–2 and nothing else. The section comes from the governing
    chord (`ChordEvent.section_id`), so the widening follows the harmony the note
    is actually judged against."""
    stats: dict[str, list[int]] = {}
    roles: dict[str, str] = {}
    allowed_cache: dict[_AllowedKey, set[int]] = {}
    quartal_groups = quartal_voiced_groups(trace)

    for phrase in trace.phrases_stage6:
        strong = _STRONG_BEATS.get(phrase.role)
        if strong is None:
            continue
        acc = stats.setdefault(phrase.track_id, [0, 0, 0])
        # `track_id → role` is 1:1 — an assumption the serializer already makes
        # (`serialize._build_track` types the whole track from
        # `track_phrases[0].role`), so this rewrite on a track's second and later
        # phrases always writes back the value already there.
        roles[phrase.track_id] = phrase.role
        for note in phrase.notes:
            if note.midi is None:
                continue
            acc[2] += 1
            if note.ticks % _TICKS_PER_BAR not in strong:
                continue
            chord = governing_chord(trace, note.ticks)
            if chord is None:
                continue
            allowed = _memoized_allowed_pitch_classes(
                allowed_cache,
                chord,
                (phrase.role, chord.section_id) in quartal_groups,
            )
            acc[0] += 1
            if note.midi % 12 in allowed:
                acc[1] += 1

    return [
        L2_1Measurement(track_id, roles[track_id], *stats[track_id])
        for track_id in stats
    ]


def _l2_1_thresholds(doc: TrackDocument, trace: GenerationTrace) -> dict[str, float]:
    """The `(bass, comping)` thresholds in force for this render, by role."""
    pack = trace.plan.style_pack.id
    mood = doc.meta.params.get("mood")
    loaded = load_l2_thresholds(pack, mood if isinstance(mood, str) else None)
    bass_threshold, comping_threshold = (
        loaded if loaded is not None else (_BASS_THRESHOLD, _COMPING_THRESHOLD)
    )
    return {"bass": bass_threshold, "comping": comping_threshold}


def _check_l2_1_chord_tone_ratio(
    doc: TrackDocument, trace: GenerationTrace
) -> list[str]:
    """FAIL if a role's strong-beat chord-tone ratio falls below its threshold.

    Measures `measure_l2_1(trace)` (stage-6 grain — see there). A group with an
    empty denominator yields no *failure* here: a division is impossible, and a
    pack legitimately lacking a role must not be gated red. That case is instead
    reported through `layer2_skip_diagnostics`, so it is never silent."""
    thresholds = _l2_1_thresholds(doc, trace)

    violations: list[str] = []
    for m in measure_l2_1(trace):
        if m.total == 0:
            continue
        ratio = m.in_set / m.total
        threshold = thresholds[m.role]
        if ratio < threshold:
            violations.append(
                f"L2-1: track '{m.track_id}' (role={m.role}) chord-tone ratio "
                f"{ratio:.3f} on {m.total} strong-beat note(s) is below threshold "
                f"{threshold:.3f} ({m.in_set}/{m.total} in-set)"
            )
    return violations


def _check_l2_1_unmeasurable(_doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """WARN when an L2-1 role emitted notes but none of them were measurable.

    `_doc` is unused — the diagnostic reads only `trace.phrases_stage6` — and is
    kept for signature symmetry with the other `_check_*` predicates, all of which
    the layer's public entry points call uniformly as `check(doc, trace)`.

    The defect S23-1 repairs was not the wrong grain alone — it was that the
    wrong grain *emptied the denominator silently*, so two packs' comping was
    gated by a check measuring nothing and no caller could tell. An empty
    denominator must therefore be **loud**. It is a warning rather than a failure
    because a legitimate empty denominator exists (a pack that never sounds a
    role), and gating on it would red-line valid renders.

    Fires only when the group produced pitched notes yet none survived the
    strong-beat / governing-chord filter — a role that emitted nothing at all has
    nothing to report."""
    return [
        f"L2-1-SKIP: track '{m.track_id}' (role={m.role}) has no measurable "
        f"strong-beat note among {m.pitched} pitched note(s) — L2-1 measured "
        f"nothing for this track and its threshold was not applied"
        for m in measure_l2_1(trace)
        if m.total == 0 and m.pitched > 0
    ]


def _check_l2_2_voice_crossing(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """WARN when bass and comping cross at a voiced-sonority instant.

    Crossing is evaluated at each *shared onset* — a tick where both a bass note
    and a comping note are struck — comparing the highest bass and lowest comping
    pitch then sounding (`[ticks, ticks + duration_ticks)`). A warn fires when
    `max(sounding bass) >= min(sounding comping)`. One message per crossing tick.

    Crossing-grain note (SESSION_16 §4 deviation, flagged for T5): a naive sweep
    over *every* sustained temporal overlap flags the two lines whenever a walking
    bass note simply sustains past an independently-timed comping stab — on the
    jazz reference that is 44 such instants, 0 of which cross when the two voices
    are actually struck together. Those are the normal rhythmic independence of a
    walking bass and a comping part, not a crossed voicing. Voice crossing is a
    property of a voiced sonority, so it is checked where the voices co-attack;
    this keeps both reference packs clean while still firing on a genuine crossing
    (a bass note voiced at/above a co-struck comping note). Limitation: a bass note
    rising at/above a purely sustained comping chord with no shared onset is not
    caught by this grain."""
    bass_notes = [
        (n.ticks, n.ticks + n.duration_ticks, n.midi)
        for track in doc.tracks
        if track.role == "bass"
        for n in track.notes
        if n.midi is not None
    ]
    comping_notes = [
        (n.ticks, n.ticks + n.duration_ticks, n.midi)
        for track in doc.tracks
        if track.role == "comping"
        for n in track.notes
        if n.midi is not None
    ]
    if not bass_notes or not comping_notes:
        return []

    bass_onsets = {start for start, _end, _midi in bass_notes}
    comping_onsets = {start for start, _end, _midi in comping_notes}
    shared_onsets = sorted(bass_onsets & comping_onsets)

    violations: list[str] = []
    for tick in shared_onsets:
        bass_here = [midi for start, end, midi in bass_notes if start <= tick < end]
        comping_here = [
            midi for start, end, midi in comping_notes if start <= tick < end
        ]
        if not bass_here or not comping_here:
            continue
        top_bass = max(bass_here)
        bottom_comping = min(comping_here)
        if top_bass >= bottom_comping:
            violations.append(
                f"L2-2: voice crossing at ticks={tick} — sounding bass midi "
                f"{top_bass} >= comping midi {bottom_comping}"
            )
    return violations


def layer2_failures(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """L2-1 chord-tone-ratio **failures** (gating). Empty list == no failure."""
    return _check_l2_1_chord_tone_ratio(doc, trace)


def layer2_skip_diagnostics(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """`L2-1-SKIP:` diagnostics — an L2-1 role L2-1 could not measure at all.

    Non-gating, and deliberately distinct from the `L2-1:` failure prefix so a
    caller can tell "this role failed" from "this role was never checked"."""
    return _check_l2_1_unmeasurable(doc, trace)


def layer2_warnings(doc: TrackDocument, trace: GenerationTrace) -> list[str]:
    """Layer-2 **non-gating** messages: L2-2 crossings + `L2-1-SKIP:` diagnostics.

    Empty list == no warning and nothing went unmeasured. The skip half delegates
    to `layer2_skip_diagnostics` rather than re-deriving it, so the two public
    non-gating entry points cannot drift apart."""
    return _check_l2_2_voice_crossing(doc, trace) + layer2_skip_diagnostics(doc, trace)
