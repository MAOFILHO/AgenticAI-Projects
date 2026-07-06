"""Unit tests for all 10 tools (via MCP layer)."""

import json

import pytest

from tests.conftest import requires_openai


@pytest.fixture(scope="module")
def tools_env(data_dir):
    from shopsmart.data_loader import load_all

    data = load_all(data_dir)

    class MockRetriever:
        def invoke(self, query):
            from langchain_core.documents import Document
            return [Document(page_content="30-day return policy for standard items.")]

    from shopsmart.mcp_client import build_mcp_tools

    _, tools_dict = build_mcp_tools(
        data["customers_db"],
        data["orders_db"],
        data["products_db"],
        data["customer_orders"],
        MockRetriever(),
    )
    return tools_dict, data


def test_lookup_customer(tools_env):
    tools_dict, data = tools_env
    result = json.loads(tools_dict["lookup_customer"].invoke("CUST-0001"))
    assert result["customer_id"] == "CUST-0001"
    assert result["name"] == "[REDACTED]"
    assert "tier" in result


def test_lookup_customer_not_found(tools_env):
    tools_dict, _ = tools_env
    result = tools_dict["lookup_customer"].invoke("CUST-9999")
    assert "not found" in result.lower()


def test_lookup_order(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(tools_dict["lookup_order"].invoke("ORD-00001"))
    assert result["order_id"] == "ORD-00001"
    assert "status" in result
    assert "items" in result


def test_lookup_order_not_found(tools_env):
    tools_dict, _ = tools_env
    result = tools_dict["lookup_order"].invoke("ORD-99999")
    assert "not found" in result.lower()


def test_search_orders_by_customer(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(tools_dict["search_orders_by_customer"].invoke("CUST-0001"))
    assert result["customer_id"] == "CUST-0001"
    assert result["order_count"] > 0


def test_search_orders_no_customer(tools_env):
    tools_dict, _ = tools_env
    result = tools_dict["search_orders_by_customer"].invoke("CUST-9999")
    assert "no orders" in result.lower()


def test_check_return_eligibility(tools_env):
    tools_dict, data = tools_env
    delivered_order = next(
        (oid for oid, o in data["orders_db"].items() if o["status"] == "delivered"),
        None,
    )
    if delivered_order:
        result = json.loads(tools_dict["check_return_eligibility"].invoke(delivered_order))
        assert "eligible" in result
        assert "days_since_delivery" in result


def test_check_return_not_delivered(tools_env):
    tools_dict, data = tools_env
    non_delivered = next(
        (oid for oid, o in data["orders_db"].items() if o["status"] != "delivered"),
        None,
    )
    if non_delivered:
        result = json.loads(tools_dict["check_return_eligibility"].invoke(non_delivered))
        assert result["eligible"] is False


def test_lookup_product(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(tools_dict["lookup_product"].invoke("PROD-0001"))
    assert result["product_id"] == "PROD-0001"
    assert "name" in result


def test_search_products(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(tools_dict["search_products"].invoke("Electronics"))
    assert result["results_count"] > 0


def test_policy_lookup(tools_env):
    tools_dict, _ = tools_env
    result = tools_dict["policy_lookup"].invoke("return policy")
    assert "30-day" in result.lower() or "policy" in result.lower()


def test_calculate_refund(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(
        tools_dict["calculate_refund"].invoke({"order_id": "ORD-00001", "reason": "defective"})
    )
    assert "refund_amount" in result
    assert result["refund_type"].startswith("full")


def test_check_billing_status(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(tools_dict["check_billing_status"].invoke("CUST-0001"))
    assert "recent_billing" in result
    assert len(result["recent_billing"]) <= 5


def test_escalate_to_manager(tools_env):
    tools_dict, _ = tools_env
    result = json.loads(tools_dict["escalate_to_manager"].invoke("Customer threatening legal action"))
    assert result["status"] == "escalated"
    assert result["escalation_id"].startswith("ESC-")
