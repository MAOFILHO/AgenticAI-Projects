"""Structural tests for the pydantic-graph pipeline in the Pydantic AI runner.

These assert the *shape* of the pipeline (fan-out, fan-in, retry cycle) without
running any LLM — the graph is declared up front, so it can be inspected statically.
That is itself one of the framework's selling points.
"""
from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from runners.pydantic_ai_runner import (
    MAX_REVIEW_ITERATIONS,
    ComplianceDeps,
    build_agents,
    build_graph,
    render_graph,
)
from shared.metrics import RunMetrics


@pytest.fixture
def graph():
    return build_graph(build_agents(model=TestModel()))


def test_graph_builds(graph):
    assert graph is not None


def test_graph_renders_mermaid(graph):
    diagram = graph.render()
    assert diagram.startswith("stateDiagram-v2")


@pytest.mark.parametrize(
    "node",
    ["plan_sections", "draft_section", "review_sections", "synthesize"],
)
def test_every_step_appears_in_the_diagram(graph, node):
    assert node in graph.render()


def test_diagram_has_parallel_fan_out(graph):
    """`.map()` must produce a fork — this is what makes the five sections concurrent."""
    assert "<<fork>>" in graph.render()


def test_diagram_has_fan_in_join(graph):
    assert "<<join>>" in graph.render()


def test_diagram_has_the_review_decision(graph):
    assert "<<choice>>" in graph.render()


def test_diagram_contains_the_retry_cycle(graph):
    """The decision must be able to route back to drafting, not just forward."""
    diagram = graph.render()
    assert "decision --> plan_sections" in diagram
    assert "decision --> synthesize" in diagram


def test_diagram_has_entry_and_exit(graph):
    diagram = graph.render()
    assert "[*] --> plan_sections" in diagram
    assert "synthesize --> [*]" in diagram


def test_render_graph_helper_matches_the_readme_snippet():
    """render_graph() is what the README documents; it must work with no arguments
    and no API key."""
    diagram = render_graph()
    assert "stateDiagram-v2" in diagram
    assert "<<fork>>" in diagram


def test_render_graph_accepts_direction():
    assert "direction LR" in render_graph(direction="LR")


def test_build_agents_returns_three_typed_agents():
    section, review, synthesis = build_agents(model=TestModel())
    assert section is not review is not synthesis


def test_section_agent_has_all_five_tools_registered():
    """Each planned section needs its tool available on the drafting agent."""
    section_agent, _, _ = build_agents(model=TestModel())
    source = __import__("inspect").getsource(
        __import__("runners.pydantic_ai_runner", fromlist=["_register_tools"])._register_tools
    )
    for tool in ("transaction_stats", "sar_status", "kyc_stats", "aml_patterns", "risk_summary"):
        assert f"def {tool}(" in source


async def test_review_loop_caps_at_max_iterations():
    """TestModel always returns approved=False, so this exercises the worst case:
    the loop must terminate at MAX_REVIEW_ITERATIONS rather than spinning forever."""
    from runners.pydantic_ai_runner import ComplianceState

    graph = build_graph(build_agents(model=TestModel()))
    metrics = RunMetrics(framework="Pydantic AI")
    state = ComplianceState()

    await graph.run(state=state, deps=ComplianceDeps(metrics=metrics))

    assert state.iteration == MAX_REVIEW_ITERATIONS


async def test_all_five_sections_are_drafted():
    from runners.pydantic_ai_runner import ComplianceState

    graph = build_graph(build_agents(model=TestModel()))
    state = ComplianceState()

    await graph.run(state=state, deps=ComplianceDeps(metrics=RunMetrics(framework="X")))

    assert len(state.drafts) == 5
    assert {d.section_id for d in state.drafts} == {
        "aml_transactions", "sar_filings", "kyc_cdd", "aml_patterns", "risk_summary",
    }


async def test_metrics_are_injected_and_incremented():
    """Dependency injection is the point: the tools update the live RunMetrics."""
    from runners.pydantic_ai_runner import ComplianceState

    graph = build_graph(build_agents(model=TestModel()))
    metrics = RunMetrics(framework="Pydantic AI")

    await graph.run(state=ComplianceState(), deps=ComplianceDeps(metrics=metrics))

    # 3 iterations x (5 drafts + 1 review) + 1 synthesis
    assert metrics.llm_calls == MAX_REVIEW_ITERATIONS * 6 + 1
    assert metrics.tool_calls > 0
