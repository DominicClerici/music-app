"""Calibrate tooling (PHASE_8 §9.3) — batch-render a pack, write `calibration.yaml`.

`calibrate(pack_id)` renders the pack across its supported moods × a small fixed
seed set, groups the traces by `(pack, mood)`, drives the C2 `compute_bands`
core, assembles a `Calibration`, and writes it to `styles/<pack>/calibration.yaml`
via `calibration_to_yaml_dict` + `yaml.safe_dump`. The written artifact is the
home of both the Layer-2 chord-tone thresholds and the Layer-3 statistical bands
(§8.1), read back by `calibration.load_calibration`.

The batch is deterministic: same `(pack, seeds, moods)` → identical yaml. Grouping
and mood ordering follow the `moods` argument (defaulting to the pack's
`supported_moods` order); within a mood the seed order is preserved. The `§9.3`
human report (per-track velocity/level, per-section note density, tempo-band
observations) is report-only — it never gates and is emitted separately from the
artifact write.

Per the §8.1 bootstrap order, a *blessed* reference-pack `calibration.yaml` is
committed only after listening review (a later chunk); this tool just proves the
emit path works — tests write to `tmp_path`, never into the committed `styles/`.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import yaml

from trackgen.packs import resolve_pack
from trackgen.packs.loader import STYLES_ROOT
from trackgen.pipeline.trace import GenerationTrace, generate_trace
from trackgen.quality.calibration import (
    Calibration,
    calibration_to_yaml_dict,
    compute_bands,
    pack_and_mood,
)

_TICKS_PER_BAR = 1920

# A small fixed seed set (base36 u64). Kept short so a calibration batch stays
# cheap while still giving `compute_bands` a spread to band over.
_DEFAULT_SEEDS: tuple[str, ...] = ("1", "2", "3")


def calibrate(
    pack_id: str,
    *,
    out_path: Path | None = None,
    seeds: Sequence[str] = _DEFAULT_SEEDS,
    moods: Sequence[str] | None = None,
    report: bool = False,
) -> Calibration:
    """Batch-render `pack_id`, write its `calibration.yaml`, return the `Calibration`.

    Renders each mood in `moods` (default: the pack's `supported_moods`) × each
    seed in `seeds`, groups by `(pack, mood)`, bands each group with
    `compute_bands`, and writes the assembled `Calibration` to `out_path`
    (default `styles/<pack_id>/calibration.yaml`). When `report` is set the §9.3
    human report is printed to stdout (report-only, no gating).
    """
    pack = resolve_pack(pack_id)
    if pack is None or pack.interpreter is None:
        raise ValueError(
            f"pack {pack_id!r} did not resolve to a pack with an interpreter"
        )

    mood_list = (
        list(moods) if moods is not None else list(pack.interpreter.supported_moods)
    )

    grouped: dict[tuple[str, str], list[GenerationTrace]] = defaultdict(list)
    for mood in mood_list:
        for seed in seeds:
            trace = generate_trace({"styleFamily": pack_id, "mood": mood, "seed": seed})
            grouped[pack_and_mood(trace)].append(trace)

    cal = Calibration(
        pack=pack_id,
        moods={mood: compute_bands(traces) for (_pk, mood), traces in grouped.items()},
    )

    target = (
        out_path if out_path is not None else STYLES_ROOT / pack_id / "calibration.yaml"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(
            calibration_to_yaml_dict(cal), sort_keys=False, allow_unicode=True
        ),
        encoding="utf-8",
    )

    if report:
        print(format_report(pack_id, grouped))

    return cal


def format_report(
    pack_id: str, grouped: dict[tuple[str, str], list[GenerationTrace]]
) -> str:
    """Render the §9.3 human report from the grouped batch (report-only)."""
    lines = [f"calibration report — pack {pack_id!r}"]
    for (_pk, mood), traces in grouped.items():
        lines.append(f"\nmood {mood!r} ({len(traces)} render(s)):")
        lines.extend(_report_velocity_level(traces))
        lines.extend(_report_section_density(traces))
        lines.extend(_report_tempo(pack_id, traces))
    return "\n".join(lines)


def _report_velocity_level(traces: list[GenerationTrace]) -> list[str]:
    velocities: dict[str, list[float]] = defaultdict(list)
    levels: dict[str, float] = {}
    for trace in traces:
        for track in trace.document.tracks:
            levels[track.id] = track.channel.volume_db
            velocities[track.id].extend(n.velocity for n in track.notes)
    lines = ["  per-track velocity / level:"]
    for track_id in sorted(velocities):
        vels = velocities[track_id]
        if vels:
            span = (
                f"vel min={min(vels):.2f} mean={statistics.fmean(vels):.2f} "
                f"max={max(vels):.2f}"
            )
        else:
            span = "vel (no notes)"
        lines.append(f"    {track_id}: {span}, level={levels[track_id]:.1f} dB")
    return lines


def _report_section_density(traces: list[GenerationTrace]) -> list[str]:
    lines = ["  per-section note density (notes/bar, all tracks):"]
    trace = traces[0]
    doc = trace.document
    for section in doc.sections:
        bars = max(1, (section.end_tick - section.start_tick) // _TICKS_PER_BAR)
        count = sum(
            1
            for track in doc.tracks
            for note in track.notes
            if section.start_tick <= note.ticks < section.end_tick
        )
        lines.append(
            f"    {section.label} ({section.type}, energy={section.energy:.2f}): "
            f"{count / bars:.2f}"
        )
    return lines


def _report_tempo(pack_id: str, traces: list[GenerationTrace]) -> list[str]:
    pack = resolve_pack(pack_id)
    lo, hi = pack.manifest.tempo_range if pack is not None else (0, 0)
    bpms = sorted(
        {tempo.bpm for trace in traces for tempo in trace.document.header.tempos}
    )
    observed = ", ".join(f"{bpm:.1f}" for bpm in bpms) or "(none)"
    out_of_band = [bpm for bpm in bpms if not lo <= bpm <= hi]
    note = f" — OUT of range: {out_of_band}" if out_of_band else ""
    return [f"  tempo: observed [{observed}] vs manifest range [{lo}, {hi}]{note}"]
