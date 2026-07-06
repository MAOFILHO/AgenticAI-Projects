"""Integration tests for specialist agent paths."""

import pytest

from tests.conftest import requires_openai


@requires_openai
def test_order_status_quick_answer(data):
    """Test: order_status ticket with explicit order ID goes through quick_answer."""
    from shopsmart.graph import build_system, process_ticket

    graph, _, _, data_loaded, known_names, lf, _ = build_system()

    order_ticket = next(
        (t for t in data_loaded["tickets"] if t["category"] == "order_status" and "ORD-" in t["text"]),
        None,
    )
    if not order_ticket:
        pytest.skip("No order_status ticket with explicit order ID found")

    result, _ = process_ticket(order_ticket, graph, data_loaded, known_names)
    assert result.get("final_response")
    assert "quick_answer" in str(result.get("tools_used", []))


@requires_openai
def test_returns_specialist(data):
    """Test: returns ticket routes to returns specialist."""
    from shopsmart.graph import build_system, process_ticket

    graph, _, _, data_loaded, known_names, lf, _ = build_system()

    returns_ticket = next(
        (t for t in data_loaded["tickets"] if t["category"] == "returns"),
        None,
    )
    if not returns_ticket:
        pytest.skip("No returns ticket found")

    result, _ = process_ticket(returns_ticket, graph, data_loaded, known_names)
    assert result.get("final_response")
    assert result.get("category") in ("returns", "order_status")


@requires_openai
def test_billing_specialist(data):
    """Test: billing ticket routes to billing specialist."""
    from shopsmart.graph import build_system, process_ticket

    graph, _, _, data_loaded, known_names, lf, _ = build_system()

    billing_ticket = next(
        (t for t in data_loaded["tickets"] if t["category"] == "billing"),
        None,
    )
    if not billing_ticket:
        pytest.skip("No billing ticket found")

    result, _ = process_ticket(billing_ticket, graph, data_loaded, known_names)
    assert result.get("final_response")


@requires_openai
def test_product_specialist(data):
    """Test: product inquiry routes to product specialist."""
    from shopsmart.graph import build_system, process_ticket

    graph, _, _, data_loaded, known_names, lf, _ = build_system()

    product_ticket = next(
        (t for t in data_loaded["tickets"] if t["category"] == "product_inquiry"),
        None,
    )
    if not product_ticket:
        pytest.skip("No product_inquiry ticket found")

    result, _ = process_ticket(product_ticket, graph, data_loaded, known_names)
    assert result.get("final_response")
