"""MCP server tests — verify tool registration and invocation."""

import pytest


def test_mcp_server_tool_count():
    """MCP server should expose 10+ tools (10 domain + health_check)."""
    from shopsmart.mcp_server import mcp

    tools = mcp._tool_manager._tools
    assert len(tools) >= 10, f"Expected at least 10 MCP tools, got {len(tools)}"


def test_mcp_tool_names():
    """All 10 domain tools should be registered in the MCP server."""
    from shopsmart.mcp_server import mcp

    tool_names = set(mcp._tool_manager._tools.keys())
    expected = {
        "lookup_customer",
        "lookup_order",
        "search_orders_by_customer",
        "check_return_eligibility",
        "lookup_product",
        "search_products",
        "policy_lookup",
        "calculate_refund",
        "check_billing_status",
        "escalate_to_manager",
    }
    missing = expected - tool_names
    assert not missing, f"Missing MCP tools: {missing}"


def test_mcp_health_check():
    """Health check tool should return immediately without API key."""
    from shopsmart.mcp_server import health_check

    result = health_check()
    assert "tools available" in result
