"""Live end-to-end smoke tests — these call the real OpenAI API and cost money.

Excluded by default. Run explicitly:

    pytest -m live                      # all six frameworks
    pytest -m live -k pydantic_ai       # just the new one

Requires OPENAI_API_KEY and a full `bash install.sh` (all six SDKs present).
"""
from __future__ import annotations

import importlib
import os

import pytest

pytestmark = pytest.mark.live

FRAMEWORKS = [
    ("langgraph", "LangGraph", "runners.langgraph_runner"),
    ("openai_agents", "OpenAI Agent SDK", "runners.openai_agents_runner"),
    ("crewai", "CrewAI", "runners.crewai_runner"),
    ("autogen", "AutoGen", "runners.autogen_runner"),
    ("google_adk", "Google ADK", "runners.google_adk_runner"),
    ("pydantic_ai", "Pydantic AI", "runners.pydantic_ai_runner"),
]


@pytest.fixture(autouse=True)
def _require_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")


@pytest.mark.slow
@pytest.mark.parametrize(("key", "name", "path"), FRAMEWORKS, ids=[f[0] for f in FRAMEWORKS])
def test_framework_produces_a_report(key, name, path):
    from shared.metrics import RunMetrics

    try:
        module = importlib.import_module(path)
    except ImportError as e:
        pytest.skip(f"{name} not installed: {e}")

    metrics = RunMetrics(framework=name)
    report = module.run(metrics)
    metrics.finish(report)

    assert metrics.status == "success"
    assert report.strip(), f"{name} returned an empty report"
    assert metrics.report_word_count >= 100, (
        f"{name} produced only {metrics.report_word_count} words — likely a truncated run"
    )
    assert metrics.elapsed_seconds > 0


@pytest.mark.slow
def test_pydantic_ai_report_cites_real_figures():
    """The typed pipeline should carry actual dataset numbers into the report,
    not generic filler — that is the accuracy claim the project makes."""
    from shared.data_loader import get_stats
    from shared.metrics import RunMetrics

    module = importlib.import_module("runners.pydantic_ai_runner")
    metrics = RunMetrics(framework="Pydantic AI")
    report = module.run(metrics)

    stats = get_stats()
    # At least one hard figure from the dataset should survive into the report.
    candidates = [
        f"{stats['total_customers']:,}",
        str(stats["total_customers"]),
        f"{stats['total_transactions']:,}",
        str(stats["total_transactions"]),
        str(stats["sar_total"]),
        str(stats["pep_count"]),
    ]
    assert any(c in report for c in candidates), (
        "report cited none of the dataset's key figures"
    )
    assert metrics.tool_calls > 0, "no tools were called — the agent invented its data"


@pytest.mark.slow
def test_main_runs_all_six_end_to_end():
    """The actual deliverable: `python main.py` producing a 6-row comparison."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=1800,
    )

    assert result.returncode == 0, result.stderr[-3000:]
    out = result.stdout
    assert "6-ADK COMPARISON" in out
    for _, name, _ in FRAMEWORKS:
        assert name in out
    assert "N/A" not in out.split("ARCHITECTURAL COMPARISON")[-1]
