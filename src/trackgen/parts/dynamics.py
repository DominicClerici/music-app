"""Velocity, articulation, and density gating (PHASE_5 §3.4, §3.5).

Pure, deterministic transforms -- no randomness, no clock (ROADMAP invariant 5).
Emitted velocities are 3-decimal half-even rounded (`round(x, 3)`, Python's
built-in banker's rounding), matching the codebase convention used by
`interpreter/moods.py` and `form/energy.py`.
"""

from __future__ import annotations

from trackgen.schema.document import Role


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, value))


def apply_velocity(authored: float, dynamics_base: float) -> float:
    """§3.4 velocity (all roles): additive mood shift, clamped to [0.05, 1.0].

    `round3(clamp(authored + 0.4 * (dynamicsBase - 0.5), 0.05, 1.0))`. Additive,
    so authored accent relationships (ghost vs backbeat) survive at every mood;
    identity at `dynamicsBase = 0.5`. Phase 6 adds accent maps and jitter on top.
    """
    return round(_clamp(authored + 0.4 * (dynamics_base - 0.5), 0.05, 1.0), 3)


def articulation_scales(role: Role, *, bass_walking: bool = False) -> bool:
    """§3.4 articulation-eligibility contract: only comping and pattern-mode bass.

    Drums (trigger lengths), pads (full-sustain), and the walker (fixed,
    rule-set durations -- `bass_walking=True`) are exempt. The caller passes the
    result to `apply_articulation`'s `scale` so the exemption is explicit, never
    silently applied.
    """
    if role == "comping":
        return True
    if role == "bass":
        return not bass_walking
    return False


def apply_articulation(
    authored_dur: int,
    articulation_legato: float,
    *,
    scale: bool,
    gap_ticks: int | None = None,
) -> int:
    """§3.4 articulation: scale a note's duration, clamped to the gap ahead.

    When `scale` is True (comping + pattern-mode bass, per `articulation_scales`):
    `round(authored * (0.7 + 0.6 * articulationLegato))` -- x0.7 (staccato) to
    x1.3 (legato), identity at 0.5. When `scale` is False (drums/pads/walker, the
    §3.4 exemption) the authored duration passes through unscaled. Either way the
    result is clamped to `gap_ticks` (the ticks before the same track's next
    event) when supplied. `scale` is a required keyword: the caller must decide
    eligibility via `articulation_scales`, so scaling is never applied silently.
    """
    if scale:
        dur = round(authored_dur * (0.7 + 0.6 * articulation_legato))
    else:
        dur = authored_dur
    if gap_ticks is not None:
        dur = min(dur, gap_ticks)
    return dur


def is_event_active(min_density: float | None, density_budget: float) -> bool:
    """§3.5 density gating: an event instantiates iff the budget clears its floor.

    A `minDensity`-carrying event plays iff `densityBudget >= minDensity`; an
    event without the field (`None`) always plays. Deterministic -- no draws, no
    probabilities.
    """
    if min_density is None:
        return True
    return density_budget >= min_density
