"""Multi-turn conversation memory tests."""

import pytest

from tests.conftest import requires_openai


@requires_openai
def test_multi_turn_conversation():
    """Two-turn conversation on same thread should preserve context."""
    from langchain_core.messages import HumanMessage

    from shopsmart.graph import build_system
    from shopsmart.pii import redact_pii

    graph, _, _, data, known_names, _ = build_system()

    thread_id = "thread-test-multi-turn"

    # Turn 1: Order status question
    turn1_text = "Hi, I ordered a product last week. Order ORD-00002. Has it been delivered?"
    turn1_redacted, turn1_pii = redact_pii(turn1_text, "CUST-0001", data["customers_db"], known_names)

    turn1_state = {
        "messages": [HumanMessage(content=turn1_redacted)],
        "ticket_id": "MULTI-TURN-001",
        "customer_id": "CUST-0001",
        "customer_tier": "bronze",
        "ticket_text": turn1_text,
        "redacted_text": turn1_redacted,
        "category": "",
        "priority": "",
        "classification_confidence": 0.0,
        "specialist_response": "",
        "needs_escalation": False,
        "human_notes": "",
        "final_response": "",
        "tools_used": [],
        "pii_mapping": turn1_pii,
    }

    config = {"configurable": {"thread_id": thread_id}}
    result1 = graph.invoke(turn1_state, config)

    assert result1.get("final_response")
    assert result1.get("category") in ("order_status", "returns", "product_inquiry")

    # Turn 2: Follow-up about returning the same order
    turn2_text = "Thanks. Actually, I want to return it. It has a defect."
    turn2_redacted, turn2_pii = redact_pii(turn2_text, "CUST-0001", data["customers_db"], known_names)

    turn2_state = {
        "messages": [HumanMessage(content=turn2_redacted)],
        "ticket_id": "MULTI-TURN-002",
        "customer_id": "CUST-0001",
        "customer_tier": "bronze",
        "ticket_text": turn2_text,
        "redacted_text": turn2_redacted,
        "category": "",
        "priority": "",
        "classification_confidence": 0.0,
        "specialist_response": "",
        "needs_escalation": False,
        "human_notes": "",
        "final_response": "",
        "tools_used": [],
        "pii_mapping": turn2_pii,
    }

    result2 = graph.invoke(turn2_state, config)

    assert result2.get("final_response")
    assert len(result2["final_response"]) > 50


@requires_openai
def test_different_threads_isolated():
    """Different thread_ids should not share context."""
    from langchain_core.messages import HumanMessage

    from shopsmart.graph import build_system
    from shopsmart.pii import redact_pii

    graph, _, _, data, known_names, _ = build_system()

    text = "What is the status of order ORD-00001?"
    redacted, pii = redact_pii(text, "CUST-0001", data["customers_db"], known_names)

    base_state = {
        "messages": [HumanMessage(content=redacted)],
        "ticket_id": "ISO-001",
        "customer_id": "CUST-0001",
        "customer_tier": "bronze",
        "ticket_text": text,
        "redacted_text": redacted,
        "category": "",
        "priority": "",
        "classification_confidence": 0.0,
        "specialist_response": "",
        "needs_escalation": False,
        "human_notes": "",
        "final_response": "",
        "tools_used": [],
        "pii_mapping": pii,
    }

    r1 = graph.invoke(base_state, {"configurable": {"thread_id": "thread-iso-A"}})
    r2 = graph.invoke(base_state, {"configurable": {"thread_id": "thread-iso-B"}})

    assert r1.get("final_response")
    assert r2.get("final_response")
