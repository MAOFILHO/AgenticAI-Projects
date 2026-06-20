"""Supervisor routing accuracy tests (batch 20 tickets)."""

import pytest

from tests.conftest import requires_openai


@requires_openai
def test_routing_accuracy_batch(data):
    """Run supervisor classification on 20 tickets and check accuracy."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from shopsmart.config import build_primary_llm
    from shopsmart.nodes import SUPERVISOR_SYSTEM_PROMPT
    from shopsmart.pii import build_known_names, redact_pii
    from shopsmart.state import TicketClassification

    llm = build_primary_llm()
    classifier = llm.with_structured_output(TicketClassification)

    known_names, _, _ = build_known_names(data["customers_db"])
    tickets = data["tickets"][:20]

    correct = 0
    total = 0

    for ticket in tickets:
        redacted, _ = redact_pii(ticket["text"], ticket["customer_id"], data["customers_db"], known_names)
        try:
            classification = classifier.invoke([
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(content=f"Classify this support ticket:\n\n{redacted}"),
            ])
            if classification.category == ticket["category"]:
                correct += 1
            total += 1
        except Exception:
            total += 1

    accuracy = correct / total * 100 if total else 0
    print(f"\nRouting Accuracy: {correct}/{total} = {accuracy:.1f}%")
    assert accuracy >= 60, f"Routing accuracy {accuracy:.1f}% below 60% threshold"
