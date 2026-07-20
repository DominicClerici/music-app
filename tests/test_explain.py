"""The `--explain` selection log (PHASE_8 §9.3 / SESSION_17 T3).

Proves the load-bearing property — a passed collector never changes the emitted
document (byte-identity on the default path) — plus that the collector records
exactly the §9.3 slots, that at least one record is *discriminating* (a forced
draw outcome is reflected in the matching record), and the CLI wiring (`--explain`
prints the trace to stderr while stdout JSON stays clean).
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from trackgen.cli import app
from trackgen.pipeline import generate_trace, to_json
from trackgen.pipeline.explain import (
    DeviceRecord,
    DressingRecord,
    EntryRecord,
    ExplainCollector,
    MutationRecord,
    PatternRecord,
    TemplateRecord,
    TempoRecord,
    render_explain,
)
from trackgen.seeds import weighted_choice as _real_weighted_choice

_POP: dict[str, object] = {"styleFamily": "pop_rock", "seed": "1ps9wxb"}
_JAZZ: dict[str, object] = {"styleFamily": "jazz", "seed": "1ps9wxb"}

runner = CliRunner()


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop_rock", "jazz"])
def test_collector_is_byte_identical(params: dict[str, object]) -> None:
    """The single most important property: a passed collector leaves the emitted
    document byte-for-byte unchanged (the collector never touches the RNG)."""
    plain = to_json(generate_trace(params).document)
    collected = to_json(generate_trace(params, explain=ExplainCollector()).document)
    assert plain == collected


@pytest.mark.parametrize("params", [_POP, _JAZZ], ids=["pop_rock", "jazz"])
def test_collector_covers_the_required_slots(params: dict[str, object]) -> None:
    """On a real render the collector holds the §9.3 slots: a template, ≥1 pool
    pick with a survivor count, a pattern pick per active role, a device no-op
    AND a device fire, a mutation `none`, and the tempo draw."""
    collector = ExplainCollector()
    trace = generate_trace(params, explain=collector)

    templates = [r for r in collector.records if isinstance(r, TemplateRecord)]
    tempos = [r for r in collector.records if isinstance(r, TempoRecord)]
    entries = [r for r in collector.records if isinstance(r, EntryRecord)]
    dressings = [r for r in collector.records if isinstance(r, DressingRecord)]
    patterns = [r for r in collector.records if isinstance(r, PatternRecord)]
    devices = [r for r in collector.records if isinstance(r, DeviceRecord)]
    mutations = [r for r in collector.records if isinstance(r, MutationRecord)]

    assert len(templates) >= 1
    assert templates[0].chosen == trace.song_form.template_id

    assert len(tempos) == 1  # the single auto-path tempo draw
    assert tempos[0].bpm == trace.plan.tempo_bpm
    assert tempos[0].lo <= tempos[0].bpm <= tempos[0].hi

    pools = [e for e in entries if e.kind == "pool"]
    assert pools and all(p.survivors >= 1 for p in pools)
    assert {e.tag for e in entries if e.kind == "final"} == {"finals"}

    assert dressings  # at least one dressed slot

    # Every active, pattern-mode (role, kind, rung) key draws exactly one pattern
    # record — coverage is proven against the selection cache, not a magic count.
    assert {r.role for r in patterns} == {role for role, _, _ in trace.selection.by_key}
    assert len(patterns) == len(trace.selection.by_key)
    assert all(p.survivors >= 1 for p in patterns)

    assert any(not d.fired for d in devices)  # a phrase-fill exclude (no-op)
    assert any(d.fired for d in devices)  # a fill / stop that fires

    assert any(m.op == "none" for m in mutations)  # a mutation no-op is logged
    assert all(m.candidates for m in mutations)


def test_discriminating_forced_device_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discriminating: force the phrase-fill draw one way, then the other, and
    assert every phrase-fill record reflects the forced outcome. A record that
    logged a constant instead of the real draw would fail one direction."""

    def force(decision: str):  # type: ignore[no-untyped-def]
        def fake(items, weights, rng):  # type: ignore[no-untyped-def]
            if list(items) == ["include", "exclude"]:
                return decision
            return _real_weighted_choice(items, weights, rng)

        return fake

    for decision in ("exclude", "include"):
        monkeypatch.setattr(
            "trackgen.transitions.devices.weighted_choice", force(decision)
        )
        collector = ExplainCollector()
        generate_trace(_POP, explain=collector)
        phrase_fills = [
            r
            for r in collector.records
            if isinstance(r, DeviceRecord) and r.kind == "phrase_fill"
        ]
        assert phrase_fills
        assert all(r.outcome == decision for r in phrase_fills)
        assert all(r.fired == (decision == "include") for r in phrase_fills)


def test_discriminating_forced_mutation_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discriminating: force the drum mutation table to always draw `hat_lift`
    and assert every drum mutation record logs that op (not a hardcoded value)."""

    def fake(items, weights, rng):  # type: ignore[no-untyped-def]
        if "hat_lift" in items:
            return "hat_lift"
        return _real_weighted_choice(items, weights, rng)

    monkeypatch.setattr("trackgen.transitions.mutation.weighted_choice", fake)
    collector = ExplainCollector()
    generate_trace(_POP, explain=collector)
    drum_muts = [
        r
        for r in collector.records
        if isinstance(r, MutationRecord) and r.role == "drums"
    ]
    assert drum_muts
    assert all(r.op == "hat_lift" for r in drum_muts)


def test_render_explain_contains_slot_identities() -> None:
    """The text trace surfaces the slot headings, the chosen template, and
    per-slot counts (smoke-level string assertions)."""
    collector = ExplainCollector()
    trace = generate_trace(_POP, explain=collector)
    text = render_explain(collector)

    for heading in (
        "tempo",
        "template",
        "progressions",
        "dressing",
        "patterns",
        "devices",
        "mutations",
    ):
        assert f"-- {heading} " in text
    assert trace.song_form.template_id in text
    assert "survived" in text
    assert "no-op" in text  # a mutation `none` (or phrase-fill exclude) is shown


def test_cli_generate_explain_stderr_stdout_split() -> None:
    """`generate --explain`: exit 0, the trace on stderr, clean JSON on stdout."""
    result = runner.invoke(
        app,
        ["generate", "--style-family", "pop_rock", "--seed", "1ps9wxb", "--explain"],
    )
    assert result.exit_code == 0, result.output
    assert "selection log" in result.stderr
    assert json.loads(result.stdout)["tracks"]


def test_cli_generate_out_json_unaffected_by_explain(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """`--out` JSON is byte-identical whether or not `--explain` is passed."""
    out_plain = tmp_path / "plain.json"
    out_explain = tmp_path / "explain.json"
    base = ["generate", "--style-family", "pop_rock", "--seed", "1ps9wxb"]
    assert runner.invoke(app, [*base, "--out", str(out_plain)]).exit_code == 0
    res = runner.invoke(app, [*base, "--out", str(out_explain), "--explain"])
    assert res.exit_code == 0
    assert "selection log" in res.stderr
    assert out_plain.read_text() == out_explain.read_text()


def test_cli_audition_explain() -> None:
    """`audition --explain`: exit 0, the trace on stderr, clean JSON on stdout."""
    result = runner.invoke(
        app, ["audition", "--pack", "jazz", "--seed", "1ps9wxb", "--explain"]
    )
    assert result.exit_code == 0, result.output
    assert "selection log" in result.stderr
    assert json.loads(result.stdout)["tracks"]
