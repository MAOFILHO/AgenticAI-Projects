"""MCP Client — bridges MCP server tools to LangChain for agent consumption.

Architecture: All tools are defined and registered in the MCP server
(mcp_server.py). This client wraps them as LangChain StructuredTool
objects so specialist agents can invoke them. Every tool call flows
through the MCP tool layer.

Usage:
    tools_list, tools_dict = build_mcp_tools(
        customers_db, orders_db, products_db, customer_orders, retriever
    )
"""

from langchain_core.tools import StructuredTool

from shopsmart.mcp_server import (
    initialize as _mcp_initialize,
    lookup_customer as _lookup_customer,
    lookup_order as _lookup_order,
    search_orders_by_customer as _search_orders_by_customer,
    check_return_eligibility as _check_return_eligibility,
    lookup_product as _lookup_product,
    search_products as _search_products,
    policy_lookup as _policy_lookup,
    calculate_refund as _calculate_refund,
    check_billing_status as _check_billing_status,
    escalate_to_manager as _escalate_to_manager,
)


def build_mcp_tools(
    customers_db: dict,
    orders_db: dict,
    products_db: dict,
    customer_orders: dict,
    policy_retriever,
) -> tuple[list, dict]:
    """Initialize MCP server and build LangChain tool wrappers.

    1. Initializes the MCP server with data stores and RAG retriever
    2. Creates LangChain StructuredTool wrappers for each MCP tool
    3. Returns (tools_list, tools_dict) for agent builders

    All tool invocations go through the MCP-registered functions.
    """
    _mcp_initialize(customers_db, orders_db, products_db, customer_orders, policy_retriever)

    tools = [
        StructuredTool.from_function(
            func=_lookup_customer,
            name="lookup_customer",
            description=(
                "Look up customer information by customer ID. "
                "Returns customer tier, join date, and ticket history."
            ),
        ),
        StructuredTool.from_function(
            func=_lookup_order,
            name="lookup_order",
            description=(
                "Look up a specific order by order ID. "
                "Returns order status, items, total, tracking number, and estimated delivery."
            ),
        ),
        StructuredTool.from_function(
            func=_search_orders_by_customer,
            name="search_orders_by_customer",
            description="Find all orders for a given customer. Returns a summary list with status.",
        ),
        StructuredTool.from_function(
            func=_check_return_eligibility,
            name="check_return_eligibility",
            description=(
                "Check if an order is eligible for return. "
                "Standard items: 30 days. Electronics: 15 days."
            ),
        ),
        StructuredTool.from_function(
            func=_lookup_product,
            name="lookup_product",
            description="Look up detailed product information by product ID.",
        ),
        StructuredTool.from_function(
            func=_search_products,
            name="search_products",
            description="Search products by name or category. Case-insensitive partial matching.",
        ),
        StructuredTool.from_function(
            func=_policy_lookup,
            name="policy_lookup",
            description=(
                "Search ShopSmart's official policies using semantic search. "
                "Use for returns, shipping, billing policy questions."
            ),
        ),
        StructuredTool.from_function(
            func=_calculate_refund,
            name="calculate_refund",
            description=(
                "Calculate the refund amount for an order based on the return reason. "
                "Defective items get full refund; others exclude shipping."
            ),
        ),
        StructuredTool.from_function(
            func=_check_billing_status,
            name="check_billing_status",
            description="Check recent billing and payment information for a customer.",
        ),
        StructuredTool.from_function(
            func=_escalate_to_manager,
            name="escalate_to_manager",
            description="Flag a ticket for escalation to a human support manager.",
        ),
    ]

    tools_dict = {t.name: t for t in tools}
    print(f"  [MCP Client] {len(tools)} tools loaded from MCP server")

    return tools, tools_dict
