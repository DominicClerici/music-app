"""The engine modulation-default tables (PHASE_7 §5.1).

`mod_defaults.yaml` ships one directive→mapping table per role (drums: per
voice) — the defaults a flavor's optional `mod` block replaces per directive key
(§3.2). Loaded module-adjacent like `feel.yaml` / `moods.yaml`; internal,
recalibratable data. Pitched roles (bass/comping/pads) carry all three
directives; drums carry brightness + space only — `attackHardness` is
deliberately absent (D4: trigger envelopes *are* the kit's identity), enforced
structurally by the `DrumModDefaults` field set + `extra="forbid"`.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from trackgen.packs.models import PackModel
from trackgen.sound.models import MappingEntry


class ModDefaultsLoadError(Exception):
    """Raised when `mod_defaults.yaml` is missing, malformed, or fails validation."""


class PitchedModDefaults(PackModel):
    """A pitched role's default tables: one mapping list per directive (§5.1).
    `space` may be empty (bass stays dry regardless of space)."""

    brightness: tuple[MappingEntry, ...]
    attack_hardness: tuple[MappingEntry, ...]
    space: tuple[MappingEntry, ...]


class DrumModDefaults(PackModel):
    """The drum default tables: per-voice mapping lists under brightness and
    space only — no `attackHardness` (D4)."""

    brightness: dict[str, tuple[MappingEntry, ...]]
    space: dict[str, tuple[MappingEntry, ...]]


class ModDefaults(PackModel):
    """The complete §5.1 engine modulation defaults."""

    bass: PitchedModDefaults
    comping: PitchedModDefaults
    pads: PitchedModDefaults
    drums: DrumModDefaults


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise ModDefaultsLoadError(
            f"{path}: could not read mod_defaults ({exc})"
        ) from exc
    except yaml.YAMLError as exc:
        raise ModDefaultsLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_mod_defaults() -> ModDefaults:
    """Load and validate the module-adjacent `mod_defaults.yaml`."""
    path = Path(__file__).parent / "mod_defaults.yaml"
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise ModDefaultsLoadError(f"{path}: mod_defaults file must be a mapping")
    try:
        return ModDefaults.model_validate(raw)
    except ValidationError as exc:
        raise ModDefaultsLoadError(f"{path}: invalid mod_defaults\n{exc}") from exc
