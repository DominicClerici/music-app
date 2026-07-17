"""6a — the HOLD ending note-structure transform (PHASE_6 §3.6).

Runs first (before device placement) so the final bars are settled. `T_last` is
the `start_tick` of the song's last `"final"`-tagged `ChordEvent` (PHASE_4 §5.5
guarantees it exists, degree-1-rooted). Pitched notes attacking at `T_last`
extend to the final section's end with a coordinated release + a `+0.05` bump;
later attacks are deleted. Drums are cleared from `T_last` on and replaced by a
struck `crash` + `kick`. Applies identically to every `close` value — the
`ritard` tempo curve is a separate Chunk-2 concern.
"""

from __future__ import annotations

from trackgen.packs.models import StylePack
from trackgen.schema.ir import GenerationPlan, HarmonicPlan, SongForm
from trackgen.transitions._common import (
    BAR,
    Builder,
    add_crash_and_kick,
    crash_velocity,
    section_containing,
)

_PITCHED_ROLES = frozenset({"bass", "comping", "pads"})


def find_t_last(chords: HarmonicPlan) -> int:
    """`T_last` = `start_tick` of the last `"final"`-tagged chord event (§3.6)."""
    finals = [c for c in chords.chords if "final" in c.tags]
    if not finals:
        raise ValueError("no 'final'-tagged chord event: HOLD anchor is undefined")
    return finals[-1].start_tick


def hold_ending(
    builders: list[Builder],
    form: SongForm,
    chords: HarmonicPlan,
    plan: GenerationPlan,
    pack: StylePack,
    t_last: int,
) -> None:
    """Apply the §3.6 HOLD transform in place on the builder list."""
    final_section = section_containing(form.sections, t_last)
    final_end = (final_section.start_bar + final_section.length_bars) * BAR

    for b in builders:
        if b.role in _PITCHED_ROLES:
            kept = []
            for n in b.notes:
                if n.ticks == t_last:
                    kept.append(
                        n.model_copy(
                            update={
                                "duration_ticks": final_end - n.ticks,
                                "velocity": round(min(1.0, n.velocity + 0.05), 3),
                                "tags": [*n.tags, "hold"],
                            }
                        )
                    )
                elif n.ticks > t_last:
                    continue  # attacks after the final chord — deleted.
                else:
                    kept.append(n)
            b.notes = kept
        elif b.role == "drums":
            b.notes = [n for n in b.notes if n.ticks < t_last]

    # Struck crash + kick at T_last: the §3.7 formula at the final section's own
    # energy, +0.05 (clamped), tagged "hold". Drums are already cleared, so the
    # kick is added unconditionally (no double-hit guard — §3.6).
    velocity = round(min(1.0, crash_velocity(pack, final_section.energy) + 0.05), 3)
    add_crash_and_kick(
        builders, final_section, t_last, velocity, "hold", guard_existing_kick=False
    )
