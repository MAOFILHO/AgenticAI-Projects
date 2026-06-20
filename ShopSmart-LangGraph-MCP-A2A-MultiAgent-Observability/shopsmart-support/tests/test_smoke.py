"""Smoke tests — verify the system boots and core components work."""

import pytest

from shopsmart.data_loader import load_all
from shopsmart.state import CustomerSupportState, TicketClassification
from shopsmart.config import get_data_dir
from tests.conftest import requires_openai


def test_data_loads(data):
    assert len(data["customers_db"]) > 0
    assert len(data["orders_db"]) > 0
    assert len(data["products_db"]) > 0
    assert len(data["tickets"]) > 0
    assert len(data["policies_text"]) > 100


def test_state_schema_fields():
    fields = CustomerSupportState.__annotations__
    assert "messages" in fields
    assert "ticket_id" in fields
    assert "category" in fields
    assert "needs_escalation" in fields
    assert "final_response" in fields
    assert len(fields) == 15


def test_classification_model():
    tc = TicketClassification(
        category="order_status",
        priority="low",
        confidence=0.95,
        requires_escalation=False,
        reasoning="Simple order inquiry",
    )
    assert tc.category == "order_status"
    assert tc.confidence == 0.95


def test_classification_model_validation():
    with pytest.raises(Exception):
        TicketClassification(
            category="invalid_category",
            priority="low",
            confidence=0.5,
            requires_escalation=False,
            reasoning="test",
        )


@requires_openai
def test_rag_retrieves(data):
    from shopsmart.config import build_embeddings
    from shopsmart.rag import build_policy_retriever

    embeddings = build_embeddings()
    retriever = build_policy_retriever(data["policies_text"], embeddings)
    results = retriever.invoke("What is the return policy?")
    assert len(results) > 0
    assert any("return" in doc.page_content.lower() for doc in results)


@requires_openai
def test_system_boots():
    from shopsmart.graph import build_system

    graph, memory, store, data, known_names, _ = build_system()
    assert graph is not None
    assert len(data["tickets"]) > 0
