"""
End-to-end smoke test — requires a fully deployed AgentCore Runtime.

Run after completing Lab 4:
  python -m pytest tests/smoke_test.py -v
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REGION = "us-east-1"


@pytest.fixture(scope="module")
def runtime_and_token():
    """Load runtime toolkit, configure it, and obtain a valid bearer token."""
    from agentcore.utils import (
        get_or_create_cognito_pool,
        get_ssm_parameter,
        create_agentcore_runtime_execution_role,
    )
    from agentcore.lab4_runtime import configure_runtime

    # Verify runtime ARN exists in SSM — skip if Lab 4 hasn't been run
    try:
        get_ssm_parameter("/app/customersupport/agentcore/runtime_arn")
    except Exception:
        pytest.skip("Runtime ARN not found in SSM — run Lab 4 first.")

    cognito_config = get_or_create_cognito_pool(refresh_token=True)
    execution_role_arn = create_agentcore_runtime_execution_role()
    runtime = configure_runtime(execution_role_arn, cognito_config)
    return runtime, cognito_config["bearer_token"]


def test_runtime_is_ready(runtime_and_token):
    runtime, _ = runtime_and_token
    status = runtime.status()
    assert status.endpoint is not None, "Runtime endpoint is None — not deployed."
    assert status.endpoint.get("status") == "READY", f"Unexpected status: {status.endpoint.get('status')}"


def test_basic_invocation(runtime_and_token):
    runtime, token = runtime_and_token
    session_id = str(uuid.uuid4())
    response = runtime.invoke(
        {"prompt": "List all of your tools"},
        bearer_token=token,
        session_id=session_id,
    )
    assert "response" in response, "Response dict missing 'response' key"
    assert len(response["response"]) > 0, "Empty response from runtime"


def test_warranty_check(runtime_and_token):
    runtime, token = runtime_and_token
    session_id = str(uuid.uuid4())
    response = runtime.invoke(
        {"prompt": "Check warranty status for serial number MNO33333333"},
        bearer_token=token,
        session_id=session_id,
    )
    text = response.get("response", "")
    assert len(text) > 10, "Warranty check returned too short a response"


def test_session_continuity(runtime_and_token):
    """Verify the same session_id maintains conversation context."""
    runtime, token = runtime_and_token
    session_id = str(uuid.uuid4())

    runtime.invoke(
        {"prompt": "My name is Alex and I have a ThinkPad."},
        bearer_token=token,
        session_id=session_id,
    )
    response = runtime.invoke(
        {"prompt": "What laptop brand did I mention?"},
        bearer_token=token,
        session_id=session_id,
    )
    text = response.get("response", "").lower()
    assert "thinkpad" in text, f"Session context not maintained. Response: {text}"
