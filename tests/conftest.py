"""Shared pytest setup.

`StylePack.timbres` is annotated with a string forward reference to the real
`sound.timbres.TimbresConfig` (a runtime import in `packs.models` would cycle —
`sound.timbres` imports `PackModel` back). That reference is completed by a
`StylePack.model_rebuild()` at the bottom of `sound/timbres.py`, which runs
whenever `sound.timbres` is imported. Production always imports it (the loader
does, lazily, on every `load_pack`), but a few unit tests construct `StylePack`
directly without touching `sound.*`. Importing it here guarantees the rebuild
has run before any test — including single-file runs — constructs a `StylePack`.
"""

import trackgen.sound.timbres  # noqa: F401  (import for its model_rebuild side effect)
