"""Every framework must satisfy the same runner contract: `run(metrics) -> str`.

This is deliberately cheap and import-only. It catches the most likely real breakage
(a renamed entry point, a bad import, a runner registered but not written) without
needing an API key or a 20-minute LLM run.

Frameworks that aren't installed are skipped rather than failed, so CI can run this
without the full two-phase install of all six SDKs.
"""
from __future__ import annotations

import importlib
import inspect

import pytest


def _runners():
    import main

    return main.RUNNERS


ALL = [
    pytest.param(key, name, path, id=key)
    for key, name, path in [
        ("langgraph", "LangGraph", "runners.langgraph_runner"),
        ("openai_agents", "OpenAI Agent SDK", "runners.openai_agents_runner"),
        ("crewai", "CrewAI", "runners.crewai_runner"),
        ("autogen", "AutoGen", "runners.autogen_runner"),
        ("google_adk", "Google ADK", "runners.google_adk_runner"),
        ("pydantic_ai", "Pydantic AI", "runners.pydantic_ai_runner"),
    ]
]


def test_registry_matches_this_test_file():
    """Keep the parametrized list above in sync with main.RUNNERS."""
    assert [(k, n, p) for k, n, p in _runners()] == [tuple(p.values) for p in ALL]


def _import_runner(path: str):
    try:
        return importlib.import_module(path)
    except ImportError as e:
        pytest.skip(f"{path} not installed in this environment: {e}")


@pytest.mark.parametrize(("key", "name", "path"), ALL)
def test_runner_module_imports(key, name, path):
    _import_runner(path)


@pytest.mark.parametrize(("key", "name", "path"), ALL)
def test_runner_exposes_callable_run(key, name, path):
    module = _import_runner(path)
    assert hasattr(module, "run"), f"{path} has no run()"
    assert callable(module.run)


@pytest.mark.parametrize(("key", "name", "path"), ALL)
def test_run_takes_exactly_one_metrics_argument(key, name, path):
    module = _import_runner(path)
    params = list(inspect.signature(module.run).parameters.values())
    required = [p for p in params if p.default is inspect.Parameter.empty]
    assert len(required) == 1, f"{path}.run must take exactly one required arg, got {params}"


@pytest.mark.parametrize(("key", "name", "path"), ALL)
def test_runner_declares_its_framework_name(key, name, path):
    module = _import_runner(path)
    assert getattr(module, "FRAMEWORK", None), f"{path} has no FRAMEWORK constant"


@pytest.mark.parametrize(("key", "name", "path"), ALL)
def test_runner_reuses_shared_tools(key, name, path):
    """No runner may reimplement the business logic — that would make the
    comparison meaningless, since they'd no longer be doing the same work."""
    module = _import_runner(path)
    source = inspect.getsource(module)
    assert "shared.tools" in source or "from shared import" in source, (
        f"{path} does not appear to use shared/tools.py"
    )
