"""The shared theory library (PHASE_4 §8) — pure, deterministic tables and
chord-resolution functions consumed by the Harmony stage and every Phase 5
part generator."""

from trackgen.theory.chords import (
    EXTENSION_OFFSETS,
    QUALITY_INTERVALS,
    SCALE_INTERVALS,
    Function,
    GuideTones,
    KeyLike,
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

__all__ = [
    "EXTENSION_OFFSETS",
    "QUALITY_INTERVALS",
    "SCALE_INTERVALS",
    "Function",
    "GuideTones",
    "KeyLike",
    "ScaleHint",
    "TokenError",
    "chord_function",
    "chord_intervals",
    "chord_scale",
    "chord_symbol",
    "chord_tones",
    "extensions_legal",
    "guide_tones",
    "legal_extensions",
    "resolve_token",
    "scale_pcs",
]
