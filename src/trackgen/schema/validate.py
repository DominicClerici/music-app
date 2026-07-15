"""Document validator (PHASE_1 §3.8, rules V1-V8).

Structural rules beyond what pydantic's field-level constraints already
enforce. Pure function: never raises, returns a list of human-readable
violation messages (empty list == valid). Each message is prefixed with its
rule id (e.g. ``"V3: ..."``) so callers/tests can assert which rule fired.
"""

from trackgen.schema.document import TrackDocument


def validate_document(doc: TrackDocument) -> list[str]:
    """Return a list of human-readable violation messages; empty == valid."""
    violations: list[str] = []
    violations.extend(_check_v1_header_sorting(doc))
    violations.extend(_check_v2_sections(doc))
    violations.extend(_check_v3_notes(doc))
    violations.extend(_check_v4_register(doc))
    violations.extend(_check_v5_midi_presence(doc))
    violations.extend(_check_v6_ids_and_sends(doc))
    violations.extend(_check_v7_polysynth_voice(doc))
    violations.extend(_check_v8_notes_within_song(doc))
    return violations


def _check_v1_header_sorting(doc: TrackDocument) -> list[str]:
    violations: list[str] = []

    tempo_ticks = [t.ticks for t in doc.header.tempos]
    if not tempo_ticks or tempo_ticks[0] != 0:
        violations.append("V1: header.tempos first entry must be at ticks == 0")
    if tempo_ticks != sorted(tempo_ticks):
        violations.append("V1: header.tempos not sorted ascending by ticks")

    ts_ticks = [t.ticks for t in doc.header.time_signatures]
    if not ts_ticks or ts_ticks[0] != 0:
        violations.append("V1: header.timeSignatures first entry must be at ticks == 0")
    if ts_ticks != sorted(ts_ticks):
        violations.append("V1: header.timeSignatures not sorted ascending by ticks")

    return violations


def _check_v2_sections(doc: TrackDocument) -> list[str]:
    violations: list[str] = []
    sections = doc.sections

    if not sections:
        violations.append("V2: sections must not be empty")
        return violations

    if sections[0].start_tick != 0:
        violations.append("V2: sections must start contiguous from tick 0")

    for sec in sections:
        if sec.end_tick <= sec.start_tick:
            violations.append(
                f"V2: section {sec.label!r} has non-positive span "
                f"(startTick={sec.start_tick}, endTick={sec.end_tick})"
            )

    for prev, nxt in zip(sections, sections[1:], strict=False):
        if prev.end_tick != nxt.start_tick:
            violations.append(
                f"V2: section gap/overlap between endTick={prev.end_tick} and "
                f"next startTick={nxt.start_tick}"
            )

    return violations


def _check_v3_notes(doc: TrackDocument) -> list[str]:
    violations: list[str] = []

    for track in doc.tracks:
        is_unpitched = track.instrument.type == "NoiseSynth"
        notes = track.notes

        if is_unpitched:
            ticks_seq = [n.ticks for n in notes]
            if ticks_seq != sorted(ticks_seq):
                violations.append(f"V3: track '{track.id}' notes not sorted by ticks")
            if len(set(ticks_seq)) != len(ticks_seq):
                violations.append(
                    f"V3: track '{track.id}' has duplicate ticks (double-hit)"
                )
        else:
            keys = [(n.ticks, n.midi if n.midi is not None else -1) for n in notes]
            if keys != sorted(keys):
                violations.append(
                    f"V3: track '{track.id}' notes not sorted by (ticks, midi)"
                )

        # durationTicks (>= 1) and velocity ((0, 1]) are enforced by NoteEvent
        # field-level constraints, so V3 only checks sort order + duplicate ticks.

    return violations


def _check_v4_register(doc: TrackDocument) -> list[str]:
    violations: list[str] = []
    for track in doc.tracks:
        if track.role == "drums":
            continue
        for note in track.notes:
            if note.midi is not None and note.midi > 71:
                violations.append(
                    f"V4: track '{track.id}' note at ticks={note.ticks} has "
                    f"midi={note.midi} above register ceiling (71)"
                )
    return violations


def _check_v5_midi_presence(doc: TrackDocument) -> list[str]:
    violations: list[str] = []
    for track in doc.tracks:
        is_unpitched = track.instrument.type == "NoiseSynth"
        for note in track.notes:
            if is_unpitched and note.midi is not None:
                violations.append(
                    f"V5: track '{track.id}' note at ticks={note.ticks} is "
                    f"NoiseSynth but has midi set"
                )
            if not is_unpitched and note.midi is None:
                violations.append(
                    f"V5: track '{track.id}' note at ticks={note.ticks} is "
                    f"missing required midi"
                )
    return violations


def _check_v6_ids_and_sends(doc: TrackDocument) -> list[str]:
    violations: list[str] = []

    bus_ids = [bus.id for bus in doc.buses]
    if len(set(bus_ids)) != len(bus_ids):
        violations.append("V6: bus ids not unique")
    bus_id_set = set(bus_ids)

    track_ids = [track.id for track in doc.tracks]
    if len(set(track_ids)) != len(track_ids):
        violations.append("V6: track ids not unique")

    for track in doc.tracks:
        for send in track.sends:
            if send.bus not in bus_id_set:
                violations.append(
                    f"V6: track '{track.id}' send references undeclared bus "
                    f"'{send.bus}'"
                )

    return violations


def _check_v7_polysynth_voice(doc: TrackDocument) -> list[str]:
    violations: list[str] = []
    for track in doc.tracks:
        instrument = track.instrument
        if instrument.type == "PolySynth":
            if instrument.voice is None:
                violations.append(
                    f"V7: track '{track.id}' PolySynth missing a valid Monophonic voice"
                )
            if instrument.max_polyphony is None:
                violations.append(
                    f"V7: track '{track.id}' PolySynth missing maxPolyphony"
                )
        else:
            if instrument.voice is not None:
                violations.append(
                    f"V7: track '{track.id}' non-PolySynth must not set voice"
                )
            if instrument.max_polyphony is not None:
                violations.append(
                    f"V7: track '{track.id}' non-PolySynth must not set maxPolyphony"
                )
    return violations


def _check_v8_notes_within_song(doc: TrackDocument) -> list[str]:
    violations: list[str] = []
    if not doc.sections:
        return violations

    song_end = doc.sections[-1].end_tick
    for track in doc.tracks:
        for note in track.notes:
            if note.ticks + note.duration_ticks > song_end:
                violations.append(
                    f"V8: track '{track.id}' note at ticks={note.ticks} "
                    f"ends after song end (endTick={song_end})"
                )
    return violations


def assert_valid(doc: TrackDocument) -> None:
    """Raise ``ValueError`` with all violations joined if `doc` is invalid."""
    violations = validate_document(doc)
    if violations:
        raise ValueError("TrackDocument is invalid:\n" + "\n".join(violations))
