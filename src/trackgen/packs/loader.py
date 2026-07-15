"""Style-pack loader (PHASE_1 §6, §9 item 3).

`load_pack` reads a pack directory's `manifest.yaml` and per-role
`patterns/{drums,bass,comping,pads}.yaml` banks via `yaml.safe_load` and
validates everything into the frozen models in `trackgen.packs.models`.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from trackgen.packs.models import Manifest, PatternEnvelope, StylePack

PATTERN_ROLES = ("drums", "bass", "comping", "pads")


class PackLoadError(Exception):
    """Raised when a pack file is missing or fails validation."""


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise PackLoadError(f"{path}: could not read pack file ({exc})") from exc
    except yaml.YAMLError as exc:
        raise PackLoadError(f"{path}: invalid YAML ({exc})") from exc


def load_pack(path: str | Path) -> StylePack:
    """Load and validate a style pack directory into a `StylePack`."""
    pack_dir = Path(path)

    manifest_path = pack_dir / "manifest.yaml"
    raw_manifest = _read_yaml(manifest_path)
    try:
        manifest = Manifest.model_validate(raw_manifest)
    except ValidationError as exc:
        raise PackLoadError(f"{manifest_path}: invalid manifest\n{exc}") from exc

    patterns: dict[str, list[PatternEnvelope]] = {}
    for role in PATTERN_ROLES:
        bank_path = pack_dir / "patterns" / f"{role}.yaml"
        raw_bank = _read_yaml(bank_path)
        raw_entries = (raw_bank or {}).get("patterns", [])
        try:
            patterns[role] = [
                PatternEnvelope.model_validate(entry) for entry in raw_entries
            ]
        except ValidationError as exc:
            raise PackLoadError(f"{bank_path}: invalid pattern bank\n{exc}") from exc

    return StylePack(manifest=manifest, patterns=patterns)
