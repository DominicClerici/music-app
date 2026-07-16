"""The Harmony engine (PHASE_4).

This session ships the dissonance-dressing ladder (§6): the tier logic, function
offsets, the `dressing.yaml` option tables, and the pure `dressing_options`
selection surface. The generator (§5) and loader (§4) are sibling tasks.
"""

from trackgen.harmony.dressing import (
    DressingLoadError,
    DressingOption,
    DressingTable,
    dressing_options,
    effective_tier,
    load_dressing_table,
    tier,
)

__all__ = [
    "DressingLoadError",
    "DressingOption",
    "DressingTable",
    "dressing_options",
    "effective_tier",
    "load_dressing_table",
    "tier",
]
