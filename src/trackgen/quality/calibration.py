"""Calibration artifact + Layer-3 band computation (PHASE_8 §8.1/§8.2; T4).

The `calibration.yaml` artifact is a **generated, committed** per-pack file
(`styles/<pack>/calibration.yaml`) that is the home of *both* the Layer-2
chord-tone thresholds and the Layer-3 statistical bands. It is WRITTEN by the
`trackgen calibrate` CLI (C3) and READ by Layers 2 and 3. This module builds the
compute core (the dataclass shape, `compute_bands`, and a `load_calibration`
reader) — it does **not** build the CLI nor write any file to `styles/`.

A band is `mean ± 2.5·SD` over the per-track metric values collected across a
blessed batch for one `(pack, mood)`. **SD is the population SD**
(`statistics.pstdev`) — the band describes the observed batch distribution, not
an inference to a wider population, and it is well-defined for a batch of one.

Shape (`calibration.yaml`, camelCase to match house YAML style)::

    pack: pop_rock
    moods:
      energetic:
        l2Thresholds: {bass: 0.95, comping: 0.98}
        bands:
          noteDensity:      # per role (drum voice-tracks fold into `drums`)
            drums: [3.2, 9.8]
            bass:  [1.1, 4.0]
          meanIoi:
            bass:  [220.0, 640.0]
          pitchRange:
            bass:  [7.0, 24.0]
          emptyBarRate:
            pads:  [0.0, 0.4]
          scaleConsistency:
            bass:  [0.9, 1.0]
          grooveConsistency: [2.0, 9.0]   # song-wide, no role split

Bands are keyed per role for the five per-track metrics; `grooveConsistency` is
song-wide (one value per track), so it has no role split. Distribution-comparison
machinery (KLD/OA) is deliberately absent (D9).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, cast

import yaml

from trackgen.packs import resolve_pack
from trackgen.packs.loader import STYLES_ROOT
from trackgen.pipeline.trace import GenerationTrace
from trackgen.quality.layer3 import Metrics, compute_metrics
from trackgen.schema.document import Role

# Engine-default L2-1 thresholds (§8.1); a pack's calibration.yaml may override.
DEFAULT_L2_THRESHOLDS: dict[str, float] = {"bass": 0.95, "comping": 0.98}

_BAND_SD = 2.5

# The five per-track metrics that band per role. `groove_consistency` is
# song-wide and handled separately.
_PER_TRACK_METRICS: tuple[str, ...] = (
    "note_density",
    "mean_ioi",
    "pitch_range",
    "empty_bar_rate",
    "scale_consistency",
)

# snake_case metric name -> camelCase YAML key.
_YAML_KEY: dict[str, str] = {
    "note_density": "noteDensity",
    "mean_ioi": "meanIoi",
    "pitch_range": "pitchRange",
    "empty_bar_rate": "emptyBarRate",
    "scale_consistency": "scaleConsistency",
}


@dataclass(frozen=True)
class Band:
    """A `[lo, hi]` acceptance band (`mean ± 2.5·SD`)."""

    lo: float
    hi: float


@dataclass(frozen=True)
class PackMoodCalibration:
    """One `(pack, mood)` cell: the L2 thresholds + the L3 bands per role."""

    l2_thresholds: dict[str, float]
    note_density: dict[Role, Band]
    mean_ioi: dict[Role, Band]
    pitch_range: dict[Role, Band]
    empty_bar_rate: dict[Role, Band]
    scale_consistency: dict[Role, Band]
    groove_consistency: Band | None


@dataclass(frozen=True)
class Calibration:
    """A whole pack's `calibration.yaml`: per-mood L2 thresholds + L3 bands."""

    pack: str
    moods: dict[str, PackMoodCalibration]


def pack_and_mood(trace: GenerationTrace) -> tuple[str, str]:
    """The `(pack, mood)` key for a trace — how C3 groups a batch.

    The pack is `trace.plan.style_pack.id`. The mood *name* is not stored on the
    plan (only its V/A `mood_vector` is), so it is read from the echoed
    `doc.meta.params["mood"]`; when the render used the pack default (no `mood`
    param), it is resolved from the pack's `interpreter.default_mood`.
    """
    pack = trace.plan.style_pack.id
    mood = trace.document.meta.params.get("mood")
    if isinstance(mood, str):
        return pack, mood
    resolved = resolve_pack(pack)
    if resolved is not None and resolved.interpreter is not None:
        return pack, resolved.interpreter.default_mood
    return pack, "default"


def _band(values: list[float]) -> Band:
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values)
    return Band(lo=mean - _BAND_SD * sd, hi=mean + _BAND_SD * sd)


def compute_bands(
    batch: list[GenerationTrace] | list[Metrics],
    l2_thresholds: dict[str, float] | None = None,
) -> PackMoodCalibration:
    """Compute the L3 bands for one `(pack, mood)` from a batch.

    `batch` is either raw traces (metrics are computed here) or pre-computed
    `Metrics` dicts. Per metric, per role, the non-`None` per-track values are
    collected across the batch and banded as `mean ± 2.5·pstdev`. A
    (metric, role) pair with no values is omitted. `groove_consistency` is banded
    over the one song-wide value per render.
    """
    metrics_list: list[Metrics] = [
        compute_metrics(item) if isinstance(item, GenerationTrace) else item
        for item in batch
    ]

    per_metric: dict[str, dict[Role, list[float]]] = {
        name: {} for name in _PER_TRACK_METRICS
    }
    groove_values: list[float] = []

    for metrics in metrics_list:
        groove = metrics["groove_consistency"]
        if groove is not None:
            groove_values.append(groove)
        for track_metrics in metrics["tracks"].values():
            role = track_metrics["role"]
            for name, value in (
                ("note_density", track_metrics["note_density"]),
                ("mean_ioi", track_metrics["mean_ioi"]),
                ("pitch_range", track_metrics["pitch_range"]),
                ("empty_bar_rate", track_metrics["empty_bar_rate"]),
                ("scale_consistency", track_metrics["scale_consistency"]),
            ):
                if value is not None:
                    per_metric[name].setdefault(role, []).append(float(value))

    def role_bands(name: str) -> dict[Role, Band]:
        return {role: _band(vals) for role, vals in per_metric[name].items() if vals}

    return PackMoodCalibration(
        # `is None`, not `or`: an artifact authored with an explicit empty
        # `l2Thresholds: {}` is falsy, and `or` would silently substitute the
        # engine defaults for it — the opposite of S23-11's "preserve what the
        # artifact says". Unreachable on the shipped packs, but `or` is not the
        # intended semantics and the distinction is free.
        l2_thresholds=dict(
            DEFAULT_L2_THRESHOLDS if l2_thresholds is None else l2_thresholds
        ),
        note_density=role_bands("note_density"),
        mean_ioi=role_bands("mean_ioi"),
        pitch_range=role_bands("pitch_range"),
        empty_bar_rate=role_bands("empty_bar_rate"),
        scale_consistency=role_bands("scale_consistency"),
        groove_consistency=_band(groove_values) if groove_values else None,
    )


def _pmc_to_yaml_dict(pmc: PackMoodCalibration) -> dict[str, Any]:
    bands: dict[str, Any] = {}
    for name in _PER_TRACK_METRICS:
        role_map: dict[Role, Band] = getattr(pmc, name)
        if role_map:
            bands[_YAML_KEY[name]] = {
                role: [band.lo, band.hi] for role, band in role_map.items()
            }
    if pmc.groove_consistency is not None:
        bands["grooveConsistency"] = [
            pmc.groove_consistency.lo,
            pmc.groove_consistency.hi,
        ]
    return {"l2Thresholds": dict(pmc.l2_thresholds), "bands": bands}


def calibration_to_yaml_dict(calibration: Calibration) -> dict[str, Any]:
    """The plain-dict form C3 will `yaml.safe_dump` to `calibration.yaml`."""
    return {
        "pack": calibration.pack,
        "moods": {
            mood: _pmc_to_yaml_dict(pmc) for mood, pmc in calibration.moods.items()
        },
    }


def _band_from_pair(pair: list[Any]) -> Band:
    return Band(lo=float(pair[0]), hi=float(pair[1]))


def _pmc_from_yaml_dict(body: dict[str, Any]) -> PackMoodCalibration:
    bands: dict[str, Any] = body.get("bands", {})

    def role_bands(name: str) -> dict[Role, Band]:
        raw: dict[str, list[Any]] = bands.get(_YAML_KEY[name], {})
        return {cast(Role, role): _band_from_pair(pair) for role, pair in raw.items()}

    groove = bands.get("grooveConsistency")
    thresholds = body.get("l2Thresholds", DEFAULT_L2_THRESHOLDS)
    return PackMoodCalibration(
        l2_thresholds={key: float(val) for key, val in thresholds.items()},
        note_density=role_bands("note_density"),
        mean_ioi=role_bands("mean_ioi"),
        pitch_range=role_bands("pitch_range"),
        empty_bar_rate=role_bands("empty_bar_rate"),
        scale_consistency=role_bands("scale_consistency"),
        groove_consistency=_band_from_pair(groove) if groove is not None else None,
    )


def load_calibration(pack: str) -> Calibration | None:
    """Read `styles/<pack>/calibration.yaml`, or `None` when absent.

    In C2 no `calibration.yaml` exists on disk (it is written by the C3
    `trackgen calibrate` CLI), so this returns `None` for every pack — the
    signal for Layers 2/3 to fall back to engine defaults.
    """
    path = STYLES_ROOT / pack / "calibration.yaml"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not data:
        return None
    moods = {
        name: _pmc_from_yaml_dict(body) for name, body in data.get("moods", {}).items()
    }
    return Calibration(pack=data.get("pack", pack), moods=moods)
