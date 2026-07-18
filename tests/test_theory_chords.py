"""Golden + cross-validation tests for the theory resolution core
(PHASE_4 §3, §6.4, §7.4, §8; DoD §14.2 partial + §14.8).

The PHASE_4 tables are normative: if the implementation disagrees, the
implementation is wrong (ROADMAP §3 golden-value arbitration). The §10 worked
examples print `ø7` shorthand for half-diminished symbols; the pinned §3.3
rule 3 mapping (`min7b5 → "m7b5"`) is the algorithm text and wins, so the
resolved symbol is e.g. `"Em7b5"`, asserted below.
"""

from __future__ import annotations

import pytest

from trackgen.schema.ir import ChordSpec, Key
from trackgen.theory import (
    EXTENSION_OFFSETS,
    QUALITY_INTERVALS,
    SCALE_INTERVALS,
    GuideTones,
    ScaleHint,
    TokenError,
    chord_function,
    chord_intervals,
    chord_scale,
    chord_symbol,
    chord_tones,
    extensions_legal,
    guide_tones,
    legal_extensions,
    resolve_token,
    scale_pcs,
)

C_MAJOR = Key(tonic_pc=0, mode="major")
D_MINOR = Key(tonic_pc=2, mode="minor")
E_MAJOR = Key(tonic_pc=4, mode="major")


# --- §8.1 / §8.2 pinned tables (asserted exactly) ----------------------------


def test_quality_interval_stacks_exact() -> None:
    assert QUALITY_INTERVALS == {
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


def test_extension_offsets_exact() -> None:
    assert EXTENSION_OFFSETS == {
        "9": 14,
        "b9": 13,
        "#9": 15,
        "11": 17,
        "#11": 18,
        "13": 21,
        "b13": 20,
    }


def test_scale_sets_exact() -> None:
    assert SCALE_INTERVALS == {
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


def test_all_scales_are_14() -> None:
    assert len(SCALE_INTERVALS) == 14


# --- §3.1 resolve_token: every suffix -----------------------------------------

# (token, quality, root_pc, symbol) resolved in C major (tonic 0).
_SUFFIX_GOLDENS = [
    ("I", "maj", 0, "C"),
    ("i", "min", 0, "Cm"),
    ("V7", "dom7", 7, "G7"),
    ("ii7", "min7", 2, "Dm7"),
    ("Imaj7", "maj7", 0, "Cmaj7"),
    ("imaj7", "minMaj7", 0, "CmMaj7"),
    ("I6", "maj6", 0, "C6"),
    ("i6", "min6", 0, "Cm6"),
    ("iiø7", "min7b5", 2, "Dm7b5"),
    ("iih7", "min7b5", 2, "Dm7b5"),  # alias ø7 == h7
    ("vii°", "dim", 11, "Bdim"),
    ("viidim", "dim", 11, "Bdim"),  # alias ° == dim
    ("vii°7", "dim7", 11, "Bdim7"),
    ("viidim7", "dim7", 11, "Bdim7"),  # alias °7 == dim7
    ("I+", "aug", 0, "Caug"),
    ("Iaug", "aug", 0, "Caug"),  # alias + == aug
    ("Isus2", "sus2", 0, "Csus2"),
    ("Isus4", "sus4", 0, "Csus4"),
    ("I7sus4", "dom7sus4", 0, "C7sus4"),
]


@pytest.mark.parametrize(("token", "quality", "root_pc", "symbol"), _SUFFIX_GOLDENS)
def test_resolve_token_suffixes(
    token: str, quality: str, root_pc: int, symbol: str
) -> None:
    spec = resolve_token(token, C_MAJOR)
    assert spec.quality == quality
    assert spec.root_pc == root_pc
    assert spec.symbol == symbol
    assert spec.roman == token  # echoes the authored token verbatim
    assert spec.extensions == []
    assert spec.bass_pc is None


# --- §3.1 suspended suffixes require the uppercase numeral --------------------


@pytest.mark.parametrize(
    ("token", "quality"),
    [
        ("Isus2", "sus2"),
        ("IVsus4", "sus4"),
        ("V7sus4", "dom7sus4"),
    ],
)
def test_resolve_token_sus_uppercase_resolves(token: str, quality: str) -> None:
    # The §3.1 table prints sus suffixes with an uppercase numeral, and the
    # shown case is required — the uppercase forms resolve.
    assert resolve_token(token, C_MAJOR).quality == quality


@pytest.mark.parametrize("token", ["isus2", "ivsus4", "v7sus4"])
def test_resolve_token_sus_lowercase_rejected(token: str) -> None:
    # A lowercase numeral before a sus suffix is a case mismatch (like ø7/°/+).
    with pytest.raises(TokenError):
        resolve_token(token, C_MAJOR)


# --- §3.1 alterations ---------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "key", "root_pc", "symbol"),
    [
        ("bVI", C_MAJOR, 8, "Ab"),
        ("bVII", C_MAJOR, 10, "Bb"),
        ("bIII", C_MAJOR, 3, "Eb"),
        ("#iv°7", C_MAJOR, 6, "F#dim7"),
        # borrowed / flat-side roots spelled with flats (never sharps):
        ("bVI7", D_MINOR, 10, "Bb7"),  # "Bb7 in D minor, never A#7"
        ("bIII", D_MINOR, 5, "F"),
        ("bVII", D_MINOR, 0, "C"),
        ("bVI", D_MINOR, 10, "Bb"),
    ],
)
def test_resolve_token_alterations(
    token: str, key: Key, root_pc: int, symbol: str
) -> None:
    spec = resolve_token(token, key)
    assert spec.root_pc == root_pc
    assert spec.symbol == symbol


# --- §3.1 slash bass ----------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "root_pc", "bass_pc", "symbol"),
    [
        ("I/3", 0, 4, "C/E"),
        ("I/5", 0, 7, "C/G"),
        ("V/7", 7, 11, "G/B"),
        ("i/b3", 0, 3, "Cm/Eb"),
    ],
)
def test_resolve_token_slash_bass(
    token: str, root_pc: int, bass_pc: int, symbol: str
) -> None:
    spec = resolve_token(token, C_MAJOR)
    assert spec.root_pc == root_pc
    assert spec.bass_pc == bass_pc
    assert spec.symbol == symbol


# --- §3.1 rejections (raise) --------------------------------------------------


@pytest.mark.parametrize(
    "token",
    [
        "",  # empty
        "~",  # bar-level hold, never a chord token
        "I~",
        "I(9)",  # §3.5 grammar: extgroup after a bare degree (no quality suffix)
        "I7()",  # empty extension group
        "I7(9",  # unbalanced extension group
        "I7(x9)",  # unknown extension name
        "Iø7",  # ø7 requires a lowercase (minor-third) numeral
        "i+",  # + requires an uppercase (major-third) numeral
        "Idim",  # dim requires a lowercase numeral
        "V°7",  # °7 requires a lowercase numeral
        "isus2",  # sus suffixes require an uppercase numeral (§3.1 table)
        "ivsus4",
        "v7sus4",
        "Iv",  # mixed-case numeral
        "iV",
        "VIII",  # not a legal numeral (I..VII only)
        "H7",  # not a numeral at all
        "Ix9",  # unrecognized suffix
        "I/8",  # bass digit out of range
        "I/0",
        "I/",  # empty bass
    ],
)
def test_resolve_token_rejects(token: str) -> None:
    with pytest.raises(TokenError):
        resolve_token(token, C_MAJOR)


# --- §3.5 authored extension groups (resolve) --------------------------------


@pytest.mark.parametrize(
    ("token", "key", "extensions", "symbol"),
    [
        ("I7(#9)", C_MAJOR, ["#9"], "C7#9"),
        ("V7(#9)", C_MAJOR, ["#9"], "G7#9"),
        ("bVI7(#11)", D_MINOR, ["#11"], "Bb7#11"),
        ("I7(9,13)", C_MAJOR, ["9", "13"], "C7913"),
    ],
)
def test_resolve_token_authored_extensions(
    token: str, key: Key, extensions: list[str], symbol: str
) -> None:
    # §3.5: a parenthesized extgroup after an explicit quality resolves; the
    # authored list is stored verbatim; `roman` echoes the token; `symbol` is
    # spelled per §3.3 (unchanged extension-display logic).
    spec = resolve_token(token, key)
    assert spec.extensions == extensions
    assert spec.roman == token
    assert spec.symbol == symbol


def test_resolve_token_defers_6_4_legality_to_loader() -> None:
    # §3.5 P5-vs-P11 split: the theory layer parses the extgroup as grammar and
    # does NOT enforce §6.4 quality-legality — `b9` is illegal on `maj7` but the
    # token still resolves here. The loader's rule P11 rejects it (see
    # tests/test_progressions_pack.py::test_p11_rejects_illegal_extension).
    spec = resolve_token("Imaj7(b9)", C_MAJOR)
    assert spec.quality == "maj7"
    assert spec.extensions == ["b9"]
    assert extensions_legal(spec.quality, spec.extensions) is False


# --- §3.3 spelling across all 12 tonics × both table classes ------------------

_MAJOR_CLASS_TABLE = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
_MINOR_CLASS_TABLE = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B")


@pytest.mark.parametrize("tonic_pc", range(12))
def test_tonic_spelling_major_class(tonic_pc: int) -> None:
    # major-class modes (major/mixolydian/lydian) share one tonic-name table.
    expected = _MAJOR_CLASS_TABLE[tonic_pc]
    assert resolve_token("I", Key(tonic_pc=tonic_pc, mode="major")).symbol == expected
    assert (
        resolve_token("I", Key(tonic_pc=tonic_pc, mode="mixolydian")).symbol == expected
    )
    assert resolve_token("I", Key(tonic_pc=tonic_pc, mode="lydian")).symbol == expected


@pytest.mark.parametrize("tonic_pc", range(12))
def test_tonic_spelling_minor_class(tonic_pc: int) -> None:
    # minor-class modes (minor/dorian/phrygian) share the other table.
    expected = _MINOR_CLASS_TABLE[tonic_pc]
    assert resolve_token("I", Key(tonic_pc=tonic_pc, mode="minor")).symbol == expected
    assert resolve_token("I", Key(tonic_pc=tonic_pc, mode="dorian")).symbol == expected
    assert (
        resolve_token("I", Key(tonic_pc=tonic_pc, mode="phrygian")).symbol == expected
    )


def test_flat_side_roots_spelled_with_flats() -> None:
    # The whole minor-key flat-side cluster spells with flats, not sharps.
    assert resolve_token("bVI7", D_MINOR).symbol == "Bb7"
    assert (
        resolve_token("bVI", Key(tonic_pc=9, mode="minor")).symbol == "F"
    )  # A minor: bVI = F
    assert (
        resolve_token("bIII", Key(tonic_pc=4, mode="minor")).symbol == "G"
    )  # E minor: bIII = G


# --- §3.2 function assignment -------------------------------------------------


@pytest.mark.parametrize(
    ("token", "function"),
    [
        ("I", "T"),
        ("Imaj7", "T"),  # quality-independent
        ("bII", "S"),
        ("ii", "S"),
        ("bIII", "T"),
        ("iii", "T"),
        ("IV", "S"),
        ("#iv°7", "O"),  # #4 -> O
        ("V", "D"),
        ("V7", "D"),
        ("bVI", "S"),
        ("vi", "T"),
        ("bVII", "D"),  # backdoor / subtonic pre-tonic
        ("vii°", "D"),  # leading-tone
        ("#I", "O"),  # alteration not in the table
        ("#V", "O"),
    ],
)
def test_chord_function(token: str, function: str) -> None:
    assert chord_function(token) == function


# --- §8.1 / §8.3 tones --------------------------------------------------------


def test_chord_intervals_and_tones() -> None:
    cmaj7 = resolve_token("Imaj7", C_MAJOR)
    assert chord_intervals(cmaj7) == [0, 4, 7, 11]
    assert chord_tones(cmaj7) == [0, 4, 7, 11]

    g7 = resolve_token("V7", C_MAJOR)
    assert chord_tones(g7) == [7, 11, 2, 5]

    dm7b5 = resolve_token("iiø7", C_MAJOR)
    assert chord_tones(dm7b5) == [2, 5, 8, 0]

    # extensions append above the triad/seventh, ascending by offset.
    dressed = ChordSpec(
        root_pc=0, quality="dom7", extensions=["13", "9"], symbol="C13", roman="I"
    )
    assert chord_intervals(dressed) == [0, 4, 7, 10, 14, 21]
    assert chord_tones(dressed) == [0, 4, 7, 10, 2, 9]


@pytest.mark.parametrize(
    ("token", "third", "seventh"),
    [
        ("Imaj7", 4, 11),
        ("I", 4, None),  # triad: no seventh
        ("i", 3, None),
        ("Isus4", None, None),  # suspended: no third
        ("I7sus4", None, 10),  # dom7sus4: seventh but no third
        ("vii°7", 2, 8),  # B dim7: root 11 -> third D(+3=2), dim7th Ab(+9=8)
        ("i6", 3, None),  # 6 is not a seventh
        ("V7", 11, 5),  # G7: third B(11), seventh F(5)
    ],
)
def test_guide_tones(token: str, third: int | None, seventh: int | None) -> None:
    spec = resolve_token(token, C_MAJOR)
    assert guide_tones(spec) == GuideTones(third=third, seventh=seventh)


def test_scale_pcs() -> None:
    assert scale_pcs(0, "ionian") == [0, 2, 4, 5, 7, 9, 11]
    assert scale_pcs(2, "dorian") == [2, 4, 5, 7, 9, 11, 0]
    assert scale_pcs(0, "altered") == [0, 1, 3, 4, 6, 8, 10]
    assert scale_pcs(9, "half_whole_dim") == [9, 10, 0, 1, 3, 4, 6, 7]


# --- §7.4 chord-scale hint (precedence: alteration > degree > fallback) -------


def _dom7(root_pc: int, extensions: list[str]) -> ChordSpec:
    return ChordSpec(
        root_pc=root_pc, quality="dom7", extensions=extensions, symbol="x", roman=None
    )


def test_chord_scale_dominant_precedence() -> None:
    # A7 (degree 5 of D minor); alteration rows outrank the mixolydian default.
    assert chord_scale(_dom7(9, []), D_MINOR).name == "mixolydian"
    assert chord_scale(_dom7(9, ["b9"]), D_MINOR).name == "half_whole_dim"
    assert chord_scale(_dom7(9, ["#9"]), D_MINOR).name == "altered"
    assert chord_scale(_dom7(9, ["b9", "b13"]), D_MINOR).name == "altered"
    assert chord_scale(_dom7(9, ["b13"]), D_MINOR).name == "mixolydian_b13"
    assert chord_scale(_dom7(9, ["#11"]), D_MINOR).name == "lydian_dominant"
    # Bb7 (b6 of D minor): non-resolving backdoor/blues dominant -> lydian_dom.
    assert chord_scale(_dom7(10, []), D_MINOR).name == "lydian_dominant"


def test_chord_scale_worked_examples() -> None:
    # Example 1 (E major).
    assert chord_scale(resolve_token("I", E_MAJOR), E_MAJOR) == ScaleHint(4, "ionian")
    assert chord_scale(resolve_token("IV", E_MAJOR), E_MAJOR) == ScaleHint(9, "lydian")
    assert chord_scale(resolve_token("vi", E_MAJOR), E_MAJOR) == ScaleHint(1, "aeolian")
    b7 = ChordSpec(root_pc=11, quality="dom7", extensions=[], symbol="B7", roman="V")
    assert chord_scale(b7, E_MAJOR) == ScaleHint(11, "mixolydian")

    # Example 2 (D minor).
    assert chord_scale(resolve_token("i7", D_MINOR), D_MINOR) == ScaleHint(2, "aeolian")
    assert chord_scale(resolve_token("iv7", D_MINOR), D_MINOR) == ScaleHint(7, "dorian")
    assert chord_scale(resolve_token("iiø7", D_MINOR), D_MINOR) == ScaleHint(
        4, "locrian_nat2"
    )
    # dressed dominants from the example
    assert chord_scale(_dom7(9, ["b9"]), D_MINOR).name == "half_whole_dim"  # A7b9
    assert chord_scale(_dom7(9, ["b13"]), D_MINOR).name == "mixolydian_b13"  # A7b13
    assert chord_scale(_dom7(10, ["13"]), D_MINOR).name == "lydian_dominant"  # Bb13


def test_chord_scale_families() -> None:
    # min-family mode-native degree-1 rows.
    i_min = resolve_token("i", Key(tonic_pc=0, mode="minor"))
    i_dor = resolve_token("i", Key(tonic_pc=0, mode="dorian"))
    i_phr = resolve_token("i", Key(tonic_pc=0, mode="phrygian"))
    assert chord_scale(i_min, Key(tonic_pc=0, mode="minor")).name == "aeolian"
    assert chord_scale(i_dor, Key(tonic_pc=0, mode="dorian")).name == "dorian"
    assert chord_scale(i_phr, Key(tonic_pc=0, mode="phrygian")).name == "phrygian"
    # min-family degree rows.
    assert chord_scale(resolve_token("ii", C_MAJOR), C_MAJOR).name == "dorian"
    assert chord_scale(resolve_token("iii", C_MAJOR), C_MAJOR).name == "phrygian"
    assert chord_scale(resolve_token("vi", C_MAJOR), C_MAJOR).name == "aeolian"
    # single-row families.
    assert chord_scale(resolve_token("iiø7", C_MAJOR), C_MAJOR).name == "locrian_nat2"
    assert (
        chord_scale(resolve_token("vii°7", C_MAJOR), C_MAJOR).name == "whole_half_dim"
    )
    assert chord_scale(resolve_token("Isus4", C_MAJOR), C_MAJOR).name == "mixolydian"
    assert chord_scale(resolve_token("imaj7", C_MAJOR), C_MAJOR).name == "melodic_minor"
    assert chord_scale(resolve_token("I+", C_MAJOR), C_MAJOR).name == "whole_tone"
    # maj-family: mixolydian-mode tonic, and borrowed-major on b7.
    mixo = Key(tonic_pc=0, mode="mixolydian")
    assert chord_scale(resolve_token("I", mixo), mixo).name == "mixolydian"
    assert chord_scale(resolve_token("bVII", C_MAJOR), C_MAJOR).name == "lydian"


# --- §6.4 extension availability ---------------------------------------------


def test_legal_extensions_table() -> None:
    assert legal_extensions("maj") == frozenset({"9", "#11", "13"})
    assert legal_extensions("maj7") == frozenset({"9", "#11", "13"})
    assert legal_extensions("maj6") == frozenset({"9"})
    assert legal_extensions("dom7") == frozenset({"9", "b9", "#9", "#11", "13", "b13"})
    assert legal_extensions("dom7sus4") == frozenset(
        {"9", "b9", "#9", "#11", "13", "b13"}
    )
    assert legal_extensions("min") == frozenset({"9", "11", "13"})
    assert legal_extensions("min7") == frozenset({"9", "11", "13"})
    assert legal_extensions("minMaj7") == frozenset({"9", "11", "13"})
    assert legal_extensions("min6") == frozenset({"9"})
    assert legal_extensions("min7b5") == frozenset({"9", "11", "b13"})
    for q in ("dim", "dim7", "aug", "sus2", "sus4"):
        assert legal_extensions(q) == frozenset()


def test_extensions_legal_helper() -> None:
    assert extensions_legal("dom7", ["b9", "b13"]) is True
    assert extensions_legal("maj", ["9"]) is True
    assert extensions_legal("maj", ["11"]) is False  # 11 is an avoid tone over maj
    assert extensions_legal("min7", ["11"]) is True
    assert extensions_legal("dim7", ["9"]) is False
    assert extensions_legal("dom7", []) is True


# --- §3.3 rule 4 tidy-display (via chord_symbol re-derivation) ----------------


@pytest.mark.parametrize(
    ("quality", "extensions", "symbol"),
    [
        ("dom7", ["9"], "C9"),
        ("dom7", ["13"], "C13"),
        ("min7", ["9"], "Cm9"),
        ("min7", ["11"], "Cm11"),
        ("maj7", ["9"], "Cmaj9"),
        ("maj", ["9"], "Cadd9"),
        ("maj6", ["9"], "C6/9"),
        ("dom7", ["b9", "b13"], "C7b9b13"),  # otherwise: base + ladder-order exts
        ("min7", ["11", "9"], "Cm7911"),  # no pair tidy rule -> "m7" + ladder order
    ],
)
def test_chord_symbol_tidy_display(
    quality: str, extensions: list[str], symbol: str
) -> None:
    spec = ChordSpec(
        root_pc=0,
        quality=quality,  # type: ignore[arg-type]
        extensions=extensions,
        symbol="placeholder",
        roman="I",
    )
    assert chord_symbol(spec, C_MAJOR) == symbol


def test_chord_symbol_matches_resolve_token() -> None:
    # chord_symbol re-derivation agrees with resolve_token for undressed specs.
    for token in ["I", "bVI7", "iiø7", "V7", "#iv°7", "i", "bVII"]:
        spec = resolve_token(token, D_MINOR)
        assert chord_symbol(spec, D_MINOR) == spec.symbol


def test_chord_symbol_canonical_when_no_roman() -> None:
    # A transform-minted spec without provenance spells from the interval.
    spec = ChordSpec(root_pc=10, quality="dom7", extensions=[], symbol="x", roman=None)
    assert chord_symbol(spec, D_MINOR) == "Bb7"  # b6 of D minor


# --- Determinism / purity -----------------------------------------------------


def test_resolve_token_deterministic() -> None:
    a = resolve_token("bVI7", D_MINOR)
    b = resolve_token("bVI7", D_MINOR)
    assert a == b


def test_chord_intervals_ascending_and_int() -> None:
    for token, key in [("Imaj7", C_MAJOR), ("iiø7", D_MINOR), ("V7", E_MAJOR)]:
        ivs = chord_intervals(resolve_token(token, key))
        assert ivs == sorted(ivs)
        assert all(isinstance(x, int) for x in ivs)


# --- §14.8 music21 cross-validation ------------------------------------------

# Documented exclusion (PHASE_4 §8.7/D12): music21's ChordSymbol has no
# 'mMaj7' abbreviation, so minMaj7 cannot be parsed and is excluded. The
# comparison is on pitch-class SETS over the non-defective subset; roman
# resolution is never routed through music21 (its altered-root #1410 and
# mode-native-degree defects would otherwise corrupt pitches).
MUSIC21_EXCLUDED_QUALITIES = frozenset({"minMaj7"})

_CROSS_VALIDATION_TOKENS = [
    "I",
    "bVI",  # flat root -> exercises the b->- conversion
    "II",
    "vi",
    "ii",
    "V7",
    "bVII7",  # Bb7 flat root
    "Imaj7",
    "ii7",
    "viiø7",
    "vii°",
    "vii°7",
    "I+",
    "I6",
    "i6",
    "Isus2",
    "Isus4",
    "I7sus4",
]


def _to_music21_figure(symbol: str) -> str:
    # music21 ChordSymbol uses '-' for a flat root, not 'b'; only the root's
    # accidental (right after the first letter) needs converting.
    if len(symbol) >= 2 and symbol[1] == "b":
        return symbol[0] + "-" + symbol[2:]
    return symbol


@pytest.mark.parametrize("token", _CROSS_VALIDATION_TOKENS)
def test_chord_tones_cross_validate_music21(token: str) -> None:
    from music21 import harmony

    spec = resolve_token(token, C_MAJOR)
    if spec.quality in MUSIC21_EXCLUDED_QUALITIES:
        pytest.skip(f"{spec.quality} not representable in music21 ChordSymbol")
    figure = _to_music21_figure(spec.symbol)
    cs = harmony.ChordSymbol(figure)
    assert set(chord_tones(spec)) == set(cs.pitchClasses)


def test_music21_minmaj7_excluded_is_real() -> None:
    # Guard the documented exclusion: confirm music21 genuinely can't parse it.
    from music21 import harmony

    with pytest.raises(ValueError):
        harmony.ChordSymbol("CmMaj7")
