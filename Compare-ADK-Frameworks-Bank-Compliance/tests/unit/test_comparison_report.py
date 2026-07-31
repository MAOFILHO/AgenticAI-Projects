"""Tests for comparison/report.py and the main.py wiring.

The load-bearing test here is `test_every_runner_has_a_description`: it is the guard
that catches a 7th framework being half-added (registered in RUNNERS but never
described), which would silently render "N/A" all over the comparison output.
"""
from __future__ import annotations

import pytest

from comparison.report import ADK_DESCRIPTIONS, print_comparison
from shared.metrics import RunMetrics

DESCRIPTION_FIELDS = ["orchestration", "control", "state", "strengths", "best_for"]

EXPECTED_FRAMEWORKS = [
    "LangGraph",
    "OpenAI Agent SDK",
    "CrewAI",
    "AutoGen",
    "Google ADK",
    "Pydantic AI",
]


def _runners():
    import main

    return main.RUNNERS


def test_six_frameworks_registered():
    assert len(_runners()) == 6


def test_runner_names_match_expected():
    assert [name for _, name, _ in _runners()] == EXPECTED_FRAMEWORKS


def test_runner_keys_are_unique():
    keys = [key for key, _, _ in _runners()]
    assert len(keys) == len(set(keys))


def test_every_runner_has_a_description():
    """Registered in RUNNERS but missing from ADK_DESCRIPTIONS = silent 'N/A' output."""
    missing = [name for _, name, _ in _runners() if name not in ADK_DESCRIPTIONS]
    assert not missing, f"frameworks missing an ADK_DESCRIPTIONS entry: {missing}"


def test_no_orphan_descriptions():
    registered = {name for _, name, _ in _runners()}
    orphans = set(ADK_DESCRIPTIONS) - registered
    assert not orphans, f"ADK_DESCRIPTIONS entries with no runner: {orphans}"


@pytest.mark.parametrize("framework", EXPECTED_FRAMEWORKS)
@pytest.mark.parametrize("field", DESCRIPTION_FIELDS)
def test_description_fields_are_populated(framework, field):
    desc = ADK_DESCRIPTIONS[framework]
    assert field in desc, f"{framework} is missing '{field}'"
    assert desc[field].strip(), f"{framework}.{field} is blank"


def test_pydantic_ai_description_mentions_its_differentiator():
    desc = ADK_DESCRIPTIONS["Pydantic AI"]
    blob = " ".join(desc.values()).lower()
    assert "typed" in blob or "type" in blob
    assert "graph" in blob


def test_print_comparison_renders_all_six(capsys):
    results = [
        (RunMetrics(framework=name), f"report for {name}") for name in EXPECTED_FRAMEWORKS
    ]
    for m, report in results:
        m.finish(report)

    print_comparison(results)
    out = capsys.readouterr().out

    for name in EXPECTED_FRAMEWORKS:
        assert name in out
    assert "N/A" not in out, "a framework is missing description fields"
    assert "ARCHITECTURAL COMPARISON" in out
    assert "KEY DIFFERENCES SUMMARY" in out
    assert "DECISION GUIDE" in out


def test_print_comparison_handles_a_failed_run(capsys):
    ok = RunMetrics(framework="LangGraph")
    ok.finish("fine")
    bad = RunMetrics(framework="Pydantic AI")
    bad.fail("exploded")

    print_comparison([(ok, "fine"), (bad, "")])
    out = capsys.readouterr().out

    assert "success" in out
    assert "error" in out


def test_decision_guide_covers_every_framework():
    """Each framework should be reachable from the decision guide."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        print_comparison([(RunMetrics(framework=n), "") for n in EXPECTED_FRAMEWORKS])
    guide = buf.getvalue().split("DECISION GUIDE:")[1]

    for name in EXPECTED_FRAMEWORKS:
        # The guide uses short forms, so match on a distinctive token.
        token = {"OpenAI Agent SDK": "OpenAI Agents SDK"}.get(name, name)
        assert token in guide, f"{name} has no decision-guide entry"
