"""JSON Schema export for `TrackDocument` (PHASE_1 §2 "Schema export" row).

The exported artifact is the client contract: `docs/schema/trackdocument.schema.json`.
Serialized with `by_alias=True` so the schema uses the camelCase JSON keys, and
with sorted keys + a fixed indent so re-exporting is byte-stable (guards drift).
"""

import json
from pathlib import Path

from trackgen.schema.document import TrackDocument

DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "schema"
    / "trackdocument.schema.json"
)


def schema_json() -> str:
    """Return the exported JSON Schema as a deterministic, formatted string."""
    schema = TrackDocument.model_json_schema(by_alias=True)
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def export_schema(path: Path = DEFAULT_SCHEMA_PATH) -> Path:
    """Write the exported JSON Schema to `path`, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(schema_json(), encoding="utf-8")
    return path
