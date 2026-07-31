"""End-to-end smoke test of the full Pydantic AI pipeline with zero network.

This is the closest thing to "does the product actually work" that can run in CI.
It is possible only because Pydantic AI ships TestModel/FunctionModel; the other
five frameworks have no equivalent, which is itself a finding worth recording in
the comparison.
"""
from __future__ import annotations

import json

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from runners.pydantic_ai_runner import (
    ComplianceDeps,
    ComplianceState,
    build_agents,
    build_graph,
)
from shared.metrics import RunMetrics


def test_model_requests_are_blocked_globally():
    """Guard on the guard: if this flips to True, offline tests are lying."""
    assert models.ALLOW_MODEL_REQUESTS is False


async def test_full_pipeline_runs_offline():
    graph = build_graph(build_agents(model=TestModel()))
    metrics = RunMetrics(framework="Pydantic AI")
    state = ComplianceState()

    report = await graph.run(state=state, deps=ComplianceDeps(metrics=metrics))

    assert isinstance(report, str)
    assert report.startswith("# Executive Summary")
    assert state.final_report == report
    assert len(state.drafts) == 5
    assert metrics.llm_calls > 0
    assert metrics.tool_calls > 0


def test_run_entry_point_offline(monkeypatch, capsys):
    """Exercise the real `run(metrics)` contract main.py calls, with TestModel
    swapped in underneath."""
    import runners.pydantic_ai_runner as r

    monkeypatch.setattr(r, "build_agents", lambda model=None: build_agents(model=TestModel()))

    metrics = RunMetrics(framework="Pydantic AI")
    report = r.run(metrics)
    metrics.finish(report)

    out = capsys.readouterr().out
    assert "Now running the pipeline using Pydantic AI" in out
    assert "Report generated" in out

    assert metrics.status == "success"
    assert metrics.report_word_count > 0
    assert metrics.llm_calls > 0


async def test_approved_on_first_pass_skips_the_retry_loop():
    """FunctionModel lets us script a passing review, proving the loop exits early
    rather than always running to the cap."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert info.output_tools is not None
        tool = info.output_tools[0]
        schema = tool.parameters_json_schema
        props = schema.get("properties", {})

        payload: dict = {}
        if "approved" in props:
            payload = {"approved": True, "issues": [], "accuracy_score": 5}
        elif "executive_summary" in props:
            payload = {"executive_summary": "Summary.", "body": "Body."}
        else:
            payload = {
                "section_id": "x",
                "topic": "X",
                "content": "Section content.",
                "key_figures": [],
            }
        return ModelResponse(parts=[ToolCallPart(tool.name, json.dumps(payload))])

    graph = build_graph(build_agents(model=FunctionModel(respond)))
    state = ComplianceState()
    metrics = RunMetrics(framework="Pydantic AI")

    await graph.run(state=state, deps=ComplianceDeps(metrics=metrics))

    assert state.iteration == 1, "review approved on pass 1 but the loop still repeated"
    assert state.accuracy_score == 5
    # 1 iteration x (5 drafts + 1 review) + 1 synthesis
    assert metrics.llm_calls == 7


async def test_report_contains_all_section_topics():
    graph = build_graph(build_agents(model=TestModel()))
    state = ComplianceState()

    await graph.run(state=state, deps=ComplianceDeps(metrics=RunMetrics(framework="X")))

    topics = {d.topic for d in state.drafts}
    assert topics == {
        "AML Transaction Monitoring",
        "SAR Filing Status",
        "KYC/CDD Compliance",
        "AML Pattern Detection",
        "Risk Indicators Summary",
    }


async def test_pipeline_is_reentrant():
    """main.py may run a framework more than once; state must not leak between runs."""
    agents = build_agents(model=TestModel())

    first_state, second_state = ComplianceState(), ComplianceState()
    graph = build_graph(agents)

    await graph.run(state=first_state, deps=ComplianceDeps(metrics=RunMetrics(framework="X")))
    await graph.run(state=second_state, deps=ComplianceDeps(metrics=RunMetrics(framework="Y")))

    assert first_state.iteration == second_state.iteration
    assert len(first_state.drafts) == len(second_state.drafts) == 5


def test_offline_suite_cannot_reach_the_network():
    """Prove the socket guard in conftest is armed."""
    import socket

    with pytest.raises(RuntimeError, match="Outbound network access"):
        socket.socket()
