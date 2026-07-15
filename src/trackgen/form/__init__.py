"""The Form stage (PHASE_3).

Currently exports the engine energy model (§6): the base table loader and
the pure `section_energy` function. The Form generator stage (§7) is a
sibling task and will extend these exports.
"""

from trackgen.form.energy import (
    EnergyLoadError,
    EnergyTable,
    load_energy_table,
    section_energy,
)

__all__ = [
    "EnergyLoadError",
    "EnergyTable",
    "load_energy_table",
    "section_energy",
]
