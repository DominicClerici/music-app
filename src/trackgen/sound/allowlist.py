"""The (class, option-path) allowlist (PHASE_7 §5.2, D12).

Engine data enumerating, per whitelisted Tone.js class, the fully-expanded set
of option paths the generator may emit — the single source PHASE_1 §3.6 called
for and the auditable Tone.js-upgrade gate ("an upgrade is a deliberate
migration, not silent drift"). Loaded module-adjacent like `feel.yaml` /
`moods.yaml`; `is_legal(cls, path)` answers the per-path legality question
TB3/TB4/TB7 (Chunk 2) ask. An un-allowlisted class yields `False`, never an
error — a patch on such a class is simply illegal.

The committed `allowlist.yaml` is fully expanded (no `.*` wildcards, DoD 2):
`envelope.*` is written as `envelope.attack/decay/sustain/release/attackCurve`
and `modulationEnvelope.*` as the four ADSR fields — exactly the subpaths §5.1,
§8, and the PHASE_1 milestone fixture emit (the §5.2 prose is imprecise; the
concrete emission set is authoritative per the SESSION_13 T1 rule). It is a
seed, extended additively by amendment as packs need new paths.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from trackgen.packs.models import PackModel


class AllowlistLoadError(Exception):
    """Raised when `allowlist.yaml` is missing, malformed, or fails validation."""


class Allowlist(PackModel):
    """A frozen `(class → legal option paths)` allowlist."""

    classes: dict[str, frozenset[str]]

    def is_legal(self, cls: str, path: str) -> bool:
        """True iff `path` is an allowed option path for `cls`. An unknown class
        (no allowlist entry) is not an error — it is simply illegal (`False`)."""
        allowed = self.classes.get(cls)
        return allowed is not None and path in allowed


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise AllowlistLoadError(f"{path}: could not read allowlist ({exc})") from exc
    except yaml.YAMLError as exc:
        raise AllowlistLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_allowlist() -> Allowlist:
    """Load and validate the module-adjacent `allowlist.yaml`."""
    path = Path(__file__).parent / "allowlist.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise AllowlistLoadError(f"{path}: allowlist file must be a mapping")
    try:
        return Allowlist.model_validate({"classes": raw})
    except ValidationError as exc:
        raise AllowlistLoadError(f"{path}: invalid allowlist\n{exc}") from exc
