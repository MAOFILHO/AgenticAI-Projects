"""
tools.py — The 10 domain tools used by ShopSmart specialist agents.

Each tool follows a single-responsibility principle:
  - Accesses databases directly (no LLM calls inside tools)
  - Returns structured JSON strings
  - Handles errors gracefully (returns error strings, never raises)

All databases and the policy retriever are injected via build_tools()
so this module stays stateless and testable.
"""
import json
import uuid
from datetime import datetime
from typing import Callable

from langchain_core.tools import tool


def build_tools(
    customers_db: dict,
    orders_db: dict,
    products_db: dict,
    customer_orders: dict,
    policy_retriever,
) -> list:
    """
    Construct and return all 10 tools with the shared data injected.

    Call this once at startup after data_loader.load_all() and rag.build_policy_retriever().
    """

    # ------------------------------------------------------------------ #
    # Tool 1 — Customer Lookup
    # ------------------------------------------------------------------ #
    @tool
    def lookup_customer(customer_id: str) -> str:
        """Look up customer information by customer ID.
        Returns customer tier, join date, and ticket history.
        """
        if customer_id not in customers_db:
            return f"Error: Customer {customer_id} not found in database."
        c = customers_db[customer_id]
        return json.dumps(
            {
                "customer_id": c["customer_id"],
                "name": "[REDACTED]",
                "tier": c["tier"],
                "join_date": c["join_date"],
                "past_tickets_count": c["past_tickets_count"],
                "last_contact_date": c["last_contact_date"],
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 2 — Order Lookup
    # ------------------------------------------------------------------ #
    @tool
    def lookup_order(order_id: str) -> str:
        """Look up a specific order by order ID.
        Returns order status, items, total, tracking number, and estimated delivery.
        """
        if order_id not in orders_db:
            return f"Error: Order {order_id} not found in database."
        o = orders_db[order_id]
        return json.dumps(
            {
                "order_id": o["order_id"],
                "customer_id": o["customer_id"],
                "order_date": o["order_date"],
                "items": [
                    {"name": item["name"], "quantity": item["quantity"], "price": item["price"]}
                    for item in o["items"]
                ],
                "total": o["total"],
                "status": o["status"],
                "tracking_number": o["tracking_number"],
                "estimated_delivery": o["estimated_delivery"],
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 3 — Search Orders by Customer
    # ------------------------------------------------------------------ #
    @tool
    def search_orders_by_customer(customer_id: str) -> str:
        """Find all orders for a given customer.
        Returns a summary list of all their orders with status.
        """
        if customer_id not in customer_orders:
            return f"No orders found for customer {customer_id}."
        orders = customer_orders[customer_id]
        summary = [
            {
                "order_id": o["order_id"],
                "order_date": o["order_date"][:10],
                "total": o["total"],
                "status": o["status"],
                "items_count": len(o["items"]),
            }
            for o in orders
        ]
        return json.dumps(
            {"customer_id": customer_id, "order_count": len(summary), "orders": summary},
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 4 — Check Return Eligibility
    # ------------------------------------------------------------------ #
    @tool
    def check_return_eligibility(order_id: str) -> str:
        """Check if an order is eligible for return based on ShopSmart's return policy.
        Standard items: 30 days from delivery. Electronics: 15 days.
        """
        if order_id not in orders_db:
            return f"Error: Order {order_id} not found."

        order = orders_db[order_id]

        if order["status"] != "delivered":
            return json.dumps(
                {
                    "order_id": order_id,
                    "eligible": False,
                    "reason": f"Order status is '{order['status']}'. Must be 'delivered' to process a return.",
                }
            )

        delivery_date = datetime.fromisoformat(order["estimated_delivery"])
        days_since_delivery = (datetime.now() - delivery_date).days

        has_electronics = any(
            products_db.get(item.get("product_id", ""), {}).get("category") == "Electronics"
            for item in order["items"]
        )

        return_window = 15 if has_electronics else 30
        eligible = days_since_delivery <= return_window

        return json.dumps(
            {
                "order_id": order_id,
                "eligible": eligible,
                "days_since_delivery": days_since_delivery,
                "return_window_days": return_window,
                "contains_electronics": has_electronics,
                "reason": (
                    "Within return window"
                    if eligible
                    else f"Return window of {return_window} days has expired ({days_since_delivery} days since delivery)"
                ),
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 5 — Product Lookup
    # ------------------------------------------------------------------ #
    @tool
    def lookup_product(product_id: str) -> str:
        """Look up detailed product information by product ID.
        Returns name, category, price, stock status, specs, and FAQ.
        """
        if product_id not in products_db:
            return f"Error: Product {product_id} not found."
        return json.dumps(products_db[product_id], indent=2)

    # ------------------------------------------------------------------ #
    # Tool 6 — Search Products
    # ------------------------------------------------------------------ #
    @tool
    def search_products(query: str) -> str:
        """Search products by name or category. Case-insensitive partial matching.
        Use this when the customer asks about a product by name.
        """
        query_lower = query.lower()
        results = [
            {
                "product_id": p["product_id"],
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "stock_status": p["stock_status"],
            }
            for p in products_db.values()
            if query_lower in p["name"].lower() or query_lower in p["category"].lower()
        ]
        if not results:
            return f"No products found matching '{query}'."
        return json.dumps(
            {"query": query, "results_count": len(results), "results": results}, indent=2
        )

    # ------------------------------------------------------------------ #
    # Tool 7 — Policy Lookup (RAG)
    # ------------------------------------------------------------------ #
    @tool
    def policy_lookup(query: str) -> str:
        """Search ShopSmart's official policies using semantic search.
        Use this to get accurate policy information about returns, shipping, billing, etc.
        """
        results = policy_retriever.invoke(query)
        if not results:
            return "No relevant policy information found."
        policy_text = "\n\n---\n\n".join(doc.page_content for doc in results)
        return f"Relevant ShopSmart Policies:\n\n{policy_text}"

    # ------------------------------------------------------------------ #
    # Tool 8 — Calculate Refund
    # ------------------------------------------------------------------ #
    @tool
    def calculate_refund(order_id: str, reason: str) -> str:
        """Calculate the refund amount for an order based on the return reason.
        Defective items get a full refund including shipping; others exclude shipping.
        """
        if order_id not in orders_db:
            return f"Error: Order {order_id} not found."

        order = orders_db[order_id]
        total = order["total"]
        reason_lower = reason.lower()
        is_defective = any(
            word in reason_lower
            for word in ["defective", "damaged", "broken", "wrong item", "incorrect"]
        )

        if is_defective:
            refund_amount = total
            refund_type = "full (defective/damaged item)"
        else:
            shipping_cost = 0.0 if total > 50 else 5.99
            refund_amount = total - shipping_cost
            refund_type = "partial (shipping costs excluded)"

        return json.dumps(
            {
                "order_id": order_id,
                "order_total": total,
                "refund_amount": round(refund_amount, 2),
                "refund_type": refund_type,
                "reason": reason,
                "processing_time": "5-7 business days",
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 9 — Check Billing Status
    # ------------------------------------------------------------------ #
    @tool
    def check_billing_status(customer_id: str) -> str:
        """Check recent billing and payment information for a customer.
        Returns a summary of the 5 most recent orders and their payment status.
        """
        if customer_id not in customer_orders:
            return f"No billing records found for customer {customer_id}."

        recent = sorted(
            customer_orders[customer_id], key=lambda o: o["order_date"], reverse=True
        )[:5]

        billing_records = [
            {
                "order_id": o["order_id"],
                "order_date": o["order_date"][:10],
                "total": o["total"],
                "status": o["status"],
                "payment_status": "charged" if o["status"] != "cancelled" else "refunded",
            }
            for o in recent
        ]

        return json.dumps(
            {
                "customer_id": customer_id,
                "recent_billing": billing_records,
                "total_recent_charges": sum(
                    r["total"] for r in billing_records if r["payment_status"] == "charged"
                ),
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 10 — Escalate to Manager
    # ------------------------------------------------------------------ #
    @tool
    def escalate_to_manager(reason: str) -> str:
        """Flag a ticket for escalation to a human support manager.
        Use when the issue is beyond automated handling capabilities.
        """
        escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        return json.dumps(
            {
                "escalation_id": escalation_id,
                "status": "escalated",
                "reason": reason,
                "message": "Ticket flagged for human manager review. Expected response within 2 hours.",
            },
            indent=2,
        )

    all_tools = [
        lookup_customer,
        lookup_order,
        search_orders_by_customer,
        check_return_eligibility,
        lookup_product,
        search_products,
        policy_lookup,
        calculate_refund,
        check_billing_status,
        escalate_to_manager,
    ]

    # Expose individual tools as attributes on the list for easy access
    all_tools_dict = {t.name: t for t in all_tools}

    return all_tools, all_tools_dict
