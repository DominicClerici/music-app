"""Tests for the style-pack loader (PHASE_1 §9 item 3)."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from trackgen.packs import PackLoadError, load_pack

STUB_PACK = Path(__file__).resolve().parent.parent / "styles" / "_stub"

VALID_MANIFEST: dict[str, object] = {
    "formatVersion": 1,
    "id": "_bad",
    "name": "Bad",
    "version": "0.1.0",
    "engine": ">=0.1",
    "timeSignatures": [[4, 4]],
    "tempoRange": [80, 140],
}

BASE_ENVELOPE: dict[str, object] = {
    "id": "p1",
    "role": "bass",
    "kind": "main",
    "energyLevel": 2,
    "lengthTicks": 1920,
    "weight": 10,
    "events": [{"pos": 0, "dur": 480, "degree": "root", "octave": 0, "velocity": 0.8}],
    "retarget": {"registerLow": 36, "registerHigh": 55, "onChordChange": "hold"},
}


def _write_pack(root: Path, envelope: dict[str, object]) -> Path:
    """Write a full pack dir with `envelope` as the sole entry in bass.yaml."""
    (root / "patterns").mkdir(parents=True, exist_ok=True)
    (root / "manifest.yaml").write_text(yaml.safe_dump(VALID_MANIFEST))
    (root / "patterns" / "bass.yaml").write_text(
        yaml.safe_dump({"patterns": [envelope]})
    )
    for role in ("drums", "comping", "pads"):
        (root / "patterns" / f"{role}.yaml").write_text(
            yaml.safe_dump({"patterns": []})
        )
    return root


def test_load_stub_pack() -> None:
    pack = load_pack(STUB_PACK)

    assert pack.manifest.id == "_stub"
    assert pack.manifest.format_version == 1
    assert pack.manifest.time_signatures == [(4, 4)]

    drums_main = next(p for p in pack.patterns["drums"] if p.id == "drums_main_1")
    assert drums_main.kind == "main"
    assert drums_main.energy_level == 2

    kick_event = drums_main.events[0]
    assert kick_event.voice == "kick"  # type: ignore[union-attr]

    bass_main = pack.patterns["bass"][0]
    root_event = bass_main.events[0]
    assert root_event.degree == "root"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.pop("weight"),  # missing required field
        lambda e: e.__setitem__("weight", 0),  # weight < 1
        lambda e: e.__setitem__("weight", 1.5),  # weight is a float
        lambda e: e.__setitem__("kind", "chorus"),  # bad kind
        lambda e: e.__setitem__(
            "events",
            [{"pos": 0, "dur": 480, "degree": "ninth", "octave": 0, "velocity": 0.8}],
        ),  # bad degree
        lambda e: e.__setitem__(
            "events", [{"pos": 0, "voice": "cowbell", "velocity": 0.8}]
        ),  # bad drum voice
        lambda e: e.__setitem__("energyLevel", 5),  # out of 1-4
        lambda e: e["retarget"].__setitem__("onChordChange", "slide"),  # bad enum
        lambda e: e["events"].__setitem__(
            0,
            {
                "pos": 0,
                "dur": 480,
                "degree": "root",
                "octave": 0,
                "velocity": 0.8,
                "swing": True,
            },
        ),  # unknown field on event (extra="forbid")
    ],
    ids=[
        "missing-weight",
        "weight-zero",
        "weight-float",
        "bad-kind",
        "bad-degree",
        "bad-voice",
        "energy-out-of-range",
        "bad-on-chord-change",
        "unknown-event-field",
    ],
)
def test_rejects_envelope_violations(tmp_path: Path, mutate: object) -> None:
    envelope = yaml.safe_load(yaml.safe_dump(BASE_ENVELOPE))  # deep copy
    mutate(envelope)  # type: ignore[operator]
    pack_dir = _write_pack(tmp_path, envelope)

    with pytest.raises((ValidationError, PackLoadError)):
        load_pack(pack_dir)


@pytest.mark.parametrize(
    "empty_value", [None, []], ids=["patterns-none", "patterns-empty"]
)
def test_rejects_bank_with_empty_patterns(tmp_path: Path, empty_value: object) -> None:
    pack_dir = _write_pack(tmp_path, yaml.safe_load(yaml.safe_dump(BASE_ENVELOPE)))
    # Overwrite one bank so its `patterns:` key is None / empty (not a list of entries).
    (pack_dir / "patterns" / "bass.yaml").write_text(
        yaml.safe_dump({"patterns": empty_value})
    )
    # None `patterns:` is treated as empty and must not crash; an empty pack is
    # still structurally loadable, so this asserts no unwrapped error is raised.
    load_pack(pack_dir)


def test_rejects_bank_patterns_not_a_list(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, yaml.safe_load(yaml.safe_dump(BASE_ENVELOPE)))
    (pack_dir / "patterns" / "bass.yaml").write_text(
        yaml.safe_dump({"patterns": {"not": "a list"}})
    )
    with pytest.raises(PackLoadError):
        load_pack(pack_dir)


def test_rejects_manifest_not_a_mapping(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, yaml.safe_load(yaml.safe_dump(BASE_ENVELOPE)))
    (pack_dir / "manifest.yaml").write_text(yaml.safe_dump(["not", "a", "mapping"]))
    with pytest.raises(PackLoadError):
        load_pack(pack_dir)


def test_rejects_manifest_missing_required_field(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, yaml.safe_load(yaml.safe_dump(BASE_ENVELOPE)))
    bad_manifest = dict(VALID_MANIFEST)
    del bad_manifest["id"]
    (pack_dir / "manifest.yaml").write_text(yaml.safe_dump(bad_manifest))
    with pytest.raises(PackLoadError):
        load_pack(pack_dir)
