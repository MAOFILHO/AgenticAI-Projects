"""HITL escalation interrupt/resume tests."""

import pytest

from tests.conftest import requires_openai


@requires_openai
def test_platinum_escalation_triggers():
    """Platinum customer with high priority should trigger HITL escalation."""
    from langchain_core.messages import HumanMessage
    from langgraph.types import Command

    from shopsmart.graph import build_system
    from shopsmart.pii import redact_pii

    graph, _, _, data, known_names, _, _ = build_system()

    # Find platinum customer ticket with escalation category
    # (simple order questions get classified as order_status/low even for platinum)
    platinum_ticket = None
    for ticket in data["tickets"]:
        cust = data["customers_db"].get(ticket["customer_id"], {})
        if cust.get("tier") == "platinum" and ticket.get("category") == "escalation":
            platinum_ticket = ticket
            break

    if not platinum_ticket:
        pytest.skip("No platinum escalation ticket found")

    customer_id = platinum_ticket["customer_id"]
    customer = data["customers_db"][customer_id]
    redacted_text, pii_mapping = redact_pii(
        platinum_ticket["text"], customer_id, data["customers_db"], known_names
    )

    initial_state = {
        "messages": [HumanMessage(content=redacted_text)],
        "ticket_id": platinum_ticket["ticket_id"],
        "customer_id": customer_id,
        "customer_tier": customer["tier"],
        "ticket_text": platinum_ticket["text"],
        "redacted_text": redacted_text,
        "category": "",
        "priority": "",
        "classification_confidence": 0.0,
        "specialist_response": "",
        "needs_escalation": False,
        "human_notes": "",
        "final_response": "",
        "tools_used": [],
        "pii_mapping": pii_mapping,
    }

    thread_id = f"thread-test-hitl-{platinum_ticket['ticket_id']}"
    config = {"configurable": {"thread_id": thread_id}}

    # First invocation should pause at escalation
    result = graph.invoke(initial_state, config)

    # The graph should have classified and flagged for escalation
    assert result.get("needs_escalation") is True or result.get("category") == "escalation"

    # Resume with manager notes
    manager_notes = "Approved. Offer 10% discount on next order as goodwill gesture."
    result_resumed = graph.invoke(Command(resume=manager_notes), config)

    assert result_resumed.get("final_response")
    assert len(result_resumed["final_response"]) > 50
