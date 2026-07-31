"""Shared fixtures and guards for the test suite.

The offline suite must never touch the network or an LLM provider. Two guards
enforce that: pydantic_ai's own ALLOW_MODEL_REQUESTS kill switch, and a
socket-level block that turns any stray outbound connection into a loud failure.
"""
from __future__ import annotations

import os
import socket

import pytest

from shared.metrics import RunMetrics


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless -m live was explicitly requested."""
    if "live" in (config.getoption("-m") or ""):
        return
    skip_live = pytest.mark.skip(reason="live test — run with `pytest -m live`")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
def _no_network(request, monkeypatch):
    """Block outbound sockets for every test that isn't marked `live`."""
    if "live" in request.keywords:
        return

    real_socket = socket.socket
    blocked_families = {socket.AF_INET, socket.AF_INET6}

    def guarded(family=socket.AF_INET, *args, **kwargs):
        # asyncio builds its event loop on an AF_UNIX socketpair, so only real
        # network families are blocked — otherwise every async test dies on setup.
        if family in blocked_families:
            raise RuntimeError(
                "Outbound network access attempted in an offline test. "
                "Use TestModel/FunctionModel, or mark the test with @pytest.mark.live."
            )
        return real_socket(family, *args, **kwargs)

    monkeypatch.setattr(socket, "socket", guarded)

    # Belt and braces: pydantic-ai's own guard gives a clearer error first.
    try:
        from pydantic_ai import models

        monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    except ImportError:
        pass

    yield
    socket.socket = real_socket


@pytest.fixture(autouse=True)
def _fake_api_key(request, monkeypatch):
    """Agent construction reads provider env vars; give it a dummy so offline
    tests don't depend on the developer's real key being present (or absent)."""
    if "live" in request.keywords:
        return
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-offline-not-a-real-key")


@pytest.fixture
def metrics() -> RunMetrics:
    return RunMetrics(framework="test")


@pytest.fixture
def clear_data_cache():
    """Reset the data_loader module cache around a test."""
    from shared import data_loader

    data_loader._cache.clear()
    yield
    data_loader._cache.clear()


@pytest.fixture(scope="session")
def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
