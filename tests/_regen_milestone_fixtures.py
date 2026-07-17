"""Regeneration helper for the whole-document milestone fixtures (SESSION_09 T4).

NOT a pytest module (no `test_` prefix — pytest does not collect it). Run it by
hand to (re)bless the two milestone fixtures from the authoritative engine:

    uv run python tests/_regen_milestone_fixtures.py

It writes `fixtures/{pop_rock,jazz}.milestone.trackdoc.json` as pretty JSON
(`to_json`: `by_alias`, `exclude_none`). The values are blessed in spirit by the
engine (ROADMAP §3 rule 3) — never hand-edit them; rerun this instead.
"""

from __future__ import annotations

from pathlib import Path

from trackgen.pipeline import generate_track
from trackgen.pipeline.serialize import to_json

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

_EXAMPLES: dict[str, dict[str, object]] = {
    "pop_rock.milestone.trackdoc.json": {"styleFamily": "pop_rock", "seed": "1ps9wxb"},
    "jazz.milestone.trackdoc.json": {
        "styleFamily": "jazz",
        "mood": "melancholic",
        "maxLengthSec": 240,
        "seed": "1ps9wxb",
    },
}


def main() -> None:
    for filename, params in _EXAMPLES.items():
        doc = generate_track(params)
        out = _FIXTURES / filename
        out.write_text(to_json(doc) + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(doc.tracks)} tracks)")


if __name__ == "__main__":
    main()
