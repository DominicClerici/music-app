"""Theory resolution core — chord tokens → `ChordSpec` and the shared tables
(PHASE_4 §3, §6.4, §7.4, §8).

Pure, deterministic functions of their inputs — no randomness, no clock, no
entropy (ROADMAP invariant 5). The pinned tables (§8.1 interval stacks, §8.2
scale sets, §3.1 grammar, §3.2 function table, §3.3 spelling, §6.4 extension
availability, §7.4 chord-scale hints) are transcribed verbatim from PHASE_4;
the printed worked-example numbers are derived samples — on divergence the
table text wins (ROADMAP §3 golden-value arbitration).

`resolve_token` never receives holds (`~`) or parenthesized extension groups —
both are out of this session's scope (§14.1 scope note) and raise `TokenError`.
"""

from __future__ import annotations

from typing import Literal, NamedTuple, Protocol

from trackgen.schema.ir import ChordQuality, ChordSpec

Function = Literal["T", "S", "D", "O"]


class KeyLike(Protocol):
    """Structural key: `trackgen.schema.ir.Key` or any object exposing these.

    Only `tonic_pc` (0–11) and `mode` are read; degrees are major-scale-relative
    and mode-independent (§3.1), so `mode` affects only spelling class and the
    chord-scale hint, never degree→pitch resolution.
    """

    tonic_pc: int
    mode: str


class TokenError(ValueError):
    """An authored chord token violates the §3.1 grammar.

    The `progressions.yaml` loader (a sibling task) relies on `resolve_token`
    raising this to reject bad tokens during pack validation (P5).
    """


class ScaleHint(NamedTuple):
    """The §7.4 chord-scale hint: a scale `name` rooted on `root_pc`."""

    root_pc: int
    name: str


class GuideTones(NamedTuple):
    """The §8.3 guide tones — chord third and seventh as pitch classes.

    Either is `None` when the quality has no such member (triads have no
    seventh; suspended chords have no third).
    """

    third: int | None
    seventh: int | None


# --- §8.1 Quality → semitone interval stacks (pinned) ------------------------

QUALITY_INTERVALS: dict[ChordQuality, tuple[int, ...]] = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "maj6": (0, 4, 7, 9),
    "min6": (0, 3, 7, 9),
    "dom7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "minMaj7": (0, 3, 7, 11),
    "min7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9),
    "dom7sus4": (0, 5, 7, 10),
}

# §8.1 extension → semitone offset from root.
EXTENSION_OFFSETS: dict[str, int] = {
    "9": 14,
    "b9": 13,
    "#9": 15,
    "11": 17,
    "#11": 18,
    "13": 21,
    "b13": 20,
}

# Display / ordering order for extensions (dressing-ladder order, §3.3 rule 4).
_EXTENSION_LADDER: tuple[str, ...] = ("9", "b9", "#9", "11", "#11", "13", "b13")

# --- §8.2 Named scale → pitch-class set (pinned) -----------------------------

SCALE_INTERVALS: dict[str, tuple[int, ...]] = {
    "ionian": (0, 2, 4, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "locrian_nat2": (0, 2, 3, 5, 6, 8, 10),
    "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "lydian_dominant": (0, 2, 4, 6, 7, 9, 10),
    "mixolydian_b13": (0, 2, 4, 5, 7, 8, 10),
    "altered": (0, 1, 3, 4, 6, 8, 10),
    "half_whole_dim": (0, 1, 3, 4, 6, 7, 9, 10),
    "whole_half_dim": (0, 2, 3, 5, 6, 8, 9, 11),
    "whole_tone": (0, 2, 4, 6, 8, 10),
}

# --- §6.4 Extension availability (hard filter, pinned) -----------------------

_LEGAL_EXTENSIONS: dict[ChordQuality, frozenset[str]] = {
    "maj": frozenset({"9", "#11", "13"}),
    "maj7": frozenset({"9", "#11", "13"}),
    "maj6": frozenset({"9"}),
    "dom7": frozenset({"9", "b9", "#9", "#11", "13", "b13"}),
    "dom7sus4": frozenset({"9", "b9", "#9", "#11", "13", "b13"}),
    "min": frozenset({"9", "11", "13"}),
    "min7": frozenset({"9", "11", "13"}),
    "minMaj7": frozenset({"9", "11", "13"}),
    "min6": frozenset({"9"}),
    "min7b5": frozenset({"9", "11", "b13"}),
    "dim": frozenset(),
    "dim7": frozenset(),
    "aug": frozenset(),
    "sus2": frozenset(),
    "sus4": frozenset(),
}


def legal_extensions(quality: ChordQuality) -> frozenset[str]:
    """The §6.4 legal-extension set for a quality (a hard filter).

    Shared with the dressing module and property tests: dressing may only add
    extensions from this set, and the document validator re-checks every emitted
    `ChordSpec` against it.
    """
    return _LEGAL_EXTENSIONS[quality]


def extensions_legal(quality: ChordQuality, extensions: list[str]) -> bool:
    """True iff every extension in `extensions` is §6.4-legal for `quality`."""
    return all(e in _LEGAL_EXTENSIONS[quality] for e in extensions)


# --- Degree / spelling primitives --------------------------------------------

# Major-scale-relative degree → semitone offset (§3.1): I..VII → 0 2 4 5 7 9 11.
_MAJOR_SCALE: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)

_LETTERS = "ABCDEFG"
_LETTER_PC: dict[str, int] = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# §3.3 rule 1 — the fixed 12×2 tonic-name tables (index = tonic pitch class).
_TONIC_NAMES: dict[str, tuple[str, ...]] = {
    # major-class modes: major, mixolydian, lydian
    "major": ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"),
    # minor-class modes: minor, dorian, phrygian
    "minor": ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"),
}
_MAJOR_CLASS_MODES = frozenset({"major", "mixolydian", "lydian"})

# §3.2 function assignment, keyed by (accidental, degree). Absent → "O".
_FUNCTION_TABLE: dict[tuple[int, int], Function] = {
    (0, 1): "T",
    (-1, 2): "S",
    (0, 2): "S",
    (-1, 3): "T",
    (0, 3): "T",
    (0, 4): "S",
    (1, 4): "O",
    (0, 5): "D",
    (-1, 6): "S",
    (0, 6): "T",
    (-1, 7): "D",
    (0, 7): "D",
}

# Canonical interval → (accidental, degree), matching the §3.2 table keys. Used
# when a spec has no roman provenance (transform-minted chords).
_CANONICAL_DEGREE: dict[int, tuple[int, int]] = {
    0: (0, 1),
    1: (-1, 2),
    2: (0, 2),
    3: (-1, 3),
    4: (0, 3),
    5: (0, 4),
    6: (1, 4),
    7: (0, 5),
    8: (-1, 6),
    9: (0, 6),
    10: (-1, 7),
    11: (0, 7),
}

# §3.1 roman numeral → (degree, base-is-uppercase). Uppercase carries a major
# third, lowercase a minor third.
_NUMERALS: dict[str, tuple[int, bool]] = {
    "I": (1, True),
    "II": (2, True),
    "III": (3, True),
    "IV": (4, True),
    "V": (5, True),
    "VI": (6, True),
    "VII": (7, True),
    "i": (1, False),
    "ii": (2, False),
    "iii": (3, False),
    "iv": (4, False),
    "v": (5, False),
    "vi": (6, False),
    "vii": (7, False),
}

# §3.1 suffix table. Case-polymorphic suffixes let the base case pick the
# quality (uppercase, lowercase); no case error is possible for them.
_POLYMORPHIC_SUFFIX: dict[str, tuple[ChordQuality, ChordQuality]] = {
    "": ("maj", "min"),
    "7": ("dom7", "min7"),
    "maj7": ("maj7", "minMaj7"),
    "6": ("maj6", "min6"),
}
# Case-fixed suffixes require a specific base case (True = uppercase required).
# The §3.1 table prints suspended suffixes with an uppercase numeral under the
# "case shown is required" preamble, so they too require the uppercase base.
_FIXED_SUFFIX: dict[str, tuple[ChordQuality, bool]] = {
    "ø7": ("min7b5", False),
    "h7": ("min7b5", False),
    "°": ("dim", False),
    "dim": ("dim", False),
    "°7": ("dim7", False),
    "dim7": ("dim7", False),
    "+": ("aug", True),
    "aug": ("aug", True),
    "sus2": ("sus2", True),
    "sus4": ("sus4", True),
    "7sus4": ("dom7sus4", True),
}

# §3.3 rule 3 — quality → display string.
_QUALITY_DISPLAY: dict[ChordQuality, str] = {
    "maj": "",
    "min": "m",
    "dom7": "7",
    "maj7": "maj7",
    "min7": "m7",
    "min7b5": "m7b5",
    "dim": "dim",
    "dim7": "dim7",
    "aug": "aug",
    "maj6": "6",
    "min6": "m6",
    "minMaj7": "mMaj7",
    "sus2": "sus2",
    "sus4": "sus4",
    "dom7sus4": "7sus4",
}

# §3.3 rule 4 — extension tidy-display: (quality, exact extensions) → whole
# quality+extension string.
_TIDY_DISPLAY: dict[tuple[ChordQuality, tuple[str, ...]], str] = {
    ("dom7", ("9",)): "9",
    ("dom7", ("13",)): "13",
    ("min7", ("9",)): "m9",
    ("min7", ("11",)): "m11",
    ("maj7", ("9",)): "maj9",
    ("maj", ("9",)): "add9",
    ("maj6", ("9",)): "6/9",
}


class _ParsedDegree(NamedTuple):
    accidental: int  # -1 / 0 / +1
    degree: int  # 1..7
    base_is_upper: bool


def _parse_degree(text: str) -> tuple[_ParsedDegree, str]:
    """Parse the leading `("b"|"#")? numeral` of a token, returning it and the
    trailing remainder (the quality suffix). Raises `TokenError` on a bad or
    mixed-case numeral."""
    i = 0
    accidental = 0
    if text[:1] == "b":
        accidental = -1
        i = 1
    elif text[:1] == "#":
        accidental = 1
        i = 1
    j = i
    while j < len(text) and text[j] in "iIvV":
        j += 1
    numeral = text[i:j]
    entry = _NUMERALS.get(numeral)
    if entry is None:
        raise TokenError(f"not a roman numeral: {numeral!r} in token {text!r}")
    degree, base_is_upper = entry
    return _ParsedDegree(accidental, degree, base_is_upper), text[j:]


def _resolve_quality(suffix: str, base_is_upper: bool, token: str) -> ChordQuality:
    """Map a §3.1 suffix + base case to a `ChordQuality`, raising on an unknown
    suffix or a case/suffix mismatch."""
    if suffix in _POLYMORPHIC_SUFFIX:
        upper, lower = _POLYMORPHIC_SUFFIX[suffix]
        return upper if base_is_upper else lower
    if suffix in _FIXED_SUFFIX:
        quality, need_upper = _FIXED_SUFFIX[suffix]
        if base_is_upper != need_upper:
            wanted = "uppercase" if need_upper else "lowercase"
            raise TokenError(
                f"suffix {suffix!r} requires a {wanted} numeral in token {token!r}"
            )
        return quality
    raise TokenError(f"unrecognized quality suffix {suffix!r} in token {token!r}")


def _parse_bass(bass_text: str, token: str) -> tuple[int, int]:
    """Parse a `("b"|"#")? digit` bass spec into (accidental, degree)."""
    accidental = 0
    rest = bass_text
    if rest[:1] == "b":
        accidental = -1
        rest = rest[1:]
    elif rest[:1] == "#":
        accidental = 1
        rest = rest[1:]
    if len(rest) != 1 or rest not in "1234567":
        raise TokenError(f"bad slash-bass {bass_text!r} in token {token!r}")
    return accidental, int(rest)


def _degree_pc(tonic_pc: int, accidental: int, degree: int) -> int:
    return (tonic_pc + _MAJOR_SCALE[degree - 1] + accidental) % 12


def _spell_note(tonic_pc: int, mode: str, accidental: int, degree: int) -> str:
    """Spell one note (chord root or bass) per §3.3 rules 1–2."""
    cls = "major" if mode in _MAJOR_CLASS_MODES else "minor"
    tonic_letter = _TONIC_NAMES[cls][tonic_pc][0]
    letter = _LETTERS[(_LETTERS.index(tonic_letter) + degree - 1) % 7]
    note_pc = _degree_pc(tonic_pc, accidental, degree)
    delta = ((note_pc - _LETTER_PC[letter] + 6) % 12) - 6
    if delta > 0:
        mark = "#" * delta
    elif delta < 0:
        mark = "b" * -delta
    else:
        mark = ""
    return letter + mark


def _quality_ext_display(quality: ChordQuality, extensions: list[str]) -> str:
    """§3.3 rules 3–4 — the quality + extension display string (no root/bass)."""
    ordered = tuple(sorted(extensions, key=_EXTENSION_LADDER.index))
    tidy = _TIDY_DISPLAY.get((quality, ordered))
    if tidy is not None:
        return tidy
    return _QUALITY_DISPLAY[quality] + "".join(ordered)


def _spell(
    key: KeyLike,
    accidental: int,
    degree: int,
    quality: ChordQuality,
    extensions: list[str],
    bass: tuple[int, int] | None,
) -> str:
    """Assemble a full `symbol` from spelled root, quality+extensions, and an
    optional slash bass (§3.3)."""
    root = _spell_note(key.tonic_pc, key.mode, accidental, degree)
    symbol = root + _quality_ext_display(quality, extensions)
    if bass is not None:
        bass_accidental, bass_degree = bass
        symbol += "/" + _spell_note(
            key.tonic_pc, key.mode, bass_accidental, bass_degree
        )
    return symbol


# --- Public resolution surface -----------------------------------------------


def resolve_token(token: str, key: KeyLike) -> ChordSpec:
    """Resolve an authored chord token to a `ChordSpec` per PHASE_4 §3.

    Grammar (§3.1): `("b"|"#")? numeral quality? ("/" ("b"|"#")? digit)?`.
    Case carries the triad third (uppercase major, lowercase minor); degrees are
    major-scale-relative and mode-independent. `symbol` is spelled per §3.3 and
    `roman` echoes `token` verbatim.

    Raises `TokenError` on: an empty token, a bar-level hold (`~`), a
    parenthesized extension group (Phase 8 scope — out of scope here), a bad or
    mixed-case numeral, an unrecognized suffix, a case/suffix mismatch, or a
    malformed slash bass.
    """
    if not token:
        raise TokenError("empty token")
    if "~" in token:
        raise TokenError(f"hold {token!r} is a bar-level token, not a chord token")
    if "(" in token or ")" in token:
        raise TokenError(
            f"extension group in {token!r} is out of scope (Phase 8, §3.5/P11)"
        )

    main, sep, bass_text = token.partition("/")
    parsed, suffix = _parse_degree(main)
    quality = _resolve_quality(suffix, parsed.base_is_upper, token)

    bass: tuple[int, int] | None = None
    bass_pc: int | None = None
    if sep == "/":
        bass = _parse_bass(bass_text, token)
        bass_pc = _degree_pc(key.tonic_pc, bass[0], bass[1])

    root_pc = _degree_pc(key.tonic_pc, parsed.accidental, parsed.degree)
    extensions: list[str] = []  # authored extension groups are rejected above
    symbol = _spell(key, parsed.accidental, parsed.degree, quality, extensions, bass)

    return ChordSpec(
        root_pc=root_pc,
        quality=quality,
        extensions=extensions,
        bass_pc=bass_pc,
        symbol=symbol,
        roman=token,
    )


def chord_function(token: str) -> Function:
    """The §3.2 function label for a token's degree (quality-independent).

    Only the leading `("b"|"#")? numeral` is read; quality/bass are ignored.
    Any alteration outside the pinned table → `"O"`. Raises `TokenError` on a
    bad numeral.
    """
    parsed, _ = _parse_degree(token.partition("/")[0])
    return _FUNCTION_TABLE.get((parsed.accidental, parsed.degree), "O")


def chord_symbol(spec: ChordSpec, key: KeyLike) -> str:
    """Re-derive a `ChordSpec.symbol` from its current quality/extensions (§3.3).

    Used after dressing mutates a spec's quality/extensions. Degree provenance
    comes from `spec.roman` when present (authored spelling, e.g. `bVI`→"Bb");
    otherwise it is taken canonically from the root's interval to the tonic.
    """
    if spec.roman is not None:
        main, sep, bass_text = spec.roman.partition("/")
        parsed, _ = _parse_degree(main)
        accidental, degree = parsed.accidental, parsed.degree
        bass = _parse_bass(bass_text, spec.roman) if sep == "/" else None
    else:
        accidental, degree = _CANONICAL_DEGREE[(spec.root_pc - key.tonic_pc) % 12]
        bass = None
        if spec.bass_pc is not None:
            bass = _CANONICAL_DEGREE[(spec.bass_pc - key.tonic_pc) % 12]
    return _spell(key, accidental, degree, spec.quality, spec.extensions, bass)


# --- §7.4 Chord-scale hint ---------------------------------------------------


def chord_scale(spec: ChordSpec, key: KeyLike) -> ScaleHint:
    """The §7.4 chord-scale hint for a spec in a key.

    Rows evaluate top-to-bottom within a quality family, first match wins
    (alteration rows outrank degree rows outrank the family fallback). The scale
    is rooted on the chord root; `interval` is the root's semitone distance
    above the tonic.
    """
    quality = spec.quality
    interval = (spec.root_pc - key.tonic_pc) % 12
    extensions = set(spec.extensions)
    mode = key.mode

    name: str
    if quality in ("maj", "maj6", "maj7"):
        if interval == 0:
            name = "mixolydian" if mode == "mixolydian" else "ionian"
        elif interval == 5:  # degree 4
            name = "lydian"
        elif interval in (3, 8, 10):  # borrowed majors on b3 / b6 / b7
            name = "lydian"
        elif interval == 7:  # degree 5
            name = "mixolydian"
        else:
            name = "ionian"
    elif quality == "dom7":
        if "#9" in extensions or ("b9" in extensions and "b13" in extensions):
            name = "altered"
        elif "b9" in extensions:
            name = "half_whole_dim"
        elif "b13" in extensions:
            name = "mixolydian_b13"
        elif "#11" in extensions:
            name = "lydian_dominant"
        elif interval in (8, 10):  # non-resolving: backdoor / blues bVI7
            name = "lydian_dominant"
        else:
            name = "mixolydian"
    elif quality in ("min", "min6", "min7"):
        if interval == 0 and mode in ("minor", "dorian", "phrygian"):
            name = {"minor": "aeolian", "dorian": "dorian", "phrygian": "phrygian"}[
                mode
            ]
        elif interval == 2:  # degree 2
            name = "dorian"
        elif interval == 4:  # degree 3
            name = "phrygian"
        elif interval == 5:  # degree 4
            name = "dorian"
        elif interval == 9:  # degree 6
            name = "aeolian"
        else:
            name = "dorian"
    elif quality == "min7b5":
        name = "locrian_nat2"
    elif quality in ("dim", "dim7"):
        name = "whole_half_dim"
    elif quality in ("sus2", "sus4", "dom7sus4"):
        name = "mixolydian"
    elif quality == "minMaj7":
        name = "melodic_minor"
    else:  # aug
        name = "whole_tone"

    return ScaleHint(root_pc=spec.root_pc, name=name)


# --- §8.1 / §8.2 / §8.3 tone utilities ---------------------------------------


def chord_intervals(spec: ChordSpec) -> list[int]:
    """The §8.1 semitone stack plus extension offsets, ascending."""
    base = list(QUALITY_INTERVALS[spec.quality])
    exts = sorted(EXTENSION_OFFSETS[e] for e in spec.extensions)
    return base + exts


def chord_tones(spec: ChordSpec) -> list[int]:
    """The chord's pitch classes, root-ordered (§8.3)."""
    return [(spec.root_pc + iv) % 12 for iv in chord_intervals(spec)]


# Guide-tone (third, seventh) semitone offsets per quality (§8.3). `None` where
# the quality has no such member.
_GUIDE_OFFSETS: dict[ChordQuality, tuple[int | None, int | None]] = {
    "maj": (4, None),
    "min": (3, None),
    "dim": (3, None),
    "aug": (4, None),
    "sus2": (None, None),
    "sus4": (None, None),
    "maj6": (4, None),
    "min6": (3, None),
    "dom7": (4, 10),
    "maj7": (4, 11),
    "min7": (3, 10),
    "minMaj7": (3, 11),
    "min7b5": (3, 10),
    "dim7": (3, 9),
    "dom7sus4": (None, 10),
}


def guide_tones(spec: ChordSpec) -> GuideTones:
    """The §8.3 guide tones (third, seventh) as pitch classes, or `None`."""
    third_off, seventh_off = _GUIDE_OFFSETS[spec.quality]
    third = None if third_off is None else (spec.root_pc + third_off) % 12
    seventh = None if seventh_off is None else (spec.root_pc + seventh_off) % 12
    return GuideTones(third=third, seventh=seventh)


def scale_pcs(root_pc: int, name: str) -> list[int]:
    """The §8.2 scale `name` as pitch classes rooted on `root_pc`, ascending."""
    return [(root_pc + iv) % 12 for iv in SCALE_INTERVALS[name]]
