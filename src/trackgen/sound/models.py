"""Shared sound-engine data models (PHASE_7 §3.1).

`MappingEntry` — one bounded directive→parameter mapping `{param, min, max,
curve}` — is the atom every engine-data file (`mod_defaults.yaml`) and, in
Chunk 2, the real `timbres.yaml` `mod` blocks are built from. Its
well-formedness caps (§3.1) live here: `curve ∈ {linear, exp}` (the `Curve`
Literal), and an `exp` curve requires strictly positive endpoints (the log map
`min × (max/min)^d` is undefined otherwise). Inverted ranges (`min > max`) are
legal — `attackHardness` maps slow→fast that way (§3.1, Serum/Ableton
semantics), so they are deliberately not rejected.
"""

from typing import Literal

from pydantic import model_validator

from trackgen.packs.models import PackModel

Curve = Literal["linear", "exp"]


class MappingEntry(PackModel):
    """One directive→parameter mapping (§3.1): a dotted `param` path and a
    bounded `[min, max]` range evaluated by `curve`."""

    param: str
    min: float
    max: float
    curve: Curve

    @model_validator(mode="after")
    def _check_exp_positive(self) -> "MappingEntry":
        # An exp map is `min × (max/min)^d`; non-positive endpoints make the
        # ratio/log undefined, so §3.1 requires min, max > 0 for `exp` only.
        if self.curve == "exp" and (self.min <= 0 or self.max <= 0):
            raise ValueError(
                f"mapping {self.param!r}: curve 'exp' requires min > 0 and "
                f"max > 0, got min={self.min}, max={self.max} (§3.1)"
            )
        return self
