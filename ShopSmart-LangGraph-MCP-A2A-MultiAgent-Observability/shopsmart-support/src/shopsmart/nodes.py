"""All graph node functions for the ShopSmart multi-agent system."""

import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt, Command

from shopsmart.state import CustomerSupportState, TicketClassification

SUPERVISOR_SYSTEM_PROMPT = """You are the ticket classification supervisor for ShopSmart customer support.

Your job is to classify incoming support tickets into the correct category and priority.

Categories:
- order_status: Questions about where an order is, tracking info, delivery estimates
- returns: Return requests, exchange requests, damaged/defective items
- billing: Payment issues, charges, invoices, refund status
- product_inquiry: Product questions, availability, specifications, recommendations
- technical: Account access issues, website problems, password resets
- escalation: Customer explicitly requests a manager, mentions legal action, or expresses extreme dissatisfaction

Priority guidelines:
- low: Simple questions, informational requests
- medium: Standard issues requiring action
- high: Urgent issues, frustrated customers, time-sensitive problems
- critical: Legal threats, safety issues, high-value disputes ($500+)

Escalation triggers (set requires_escalation=True):
- Customer explicitly asks for a manager or supervisor
- Mentions legal action, lawyer, or regulatory complaint
- Mentions social media threats
- Category is clearly 'escalation'
- High-value dispute over $500

Be precise and confident in your classification."""


def build_supervisor_node(classifier_llm):
    """Build the supervisor router node with structured output LLM."""

    def supervisor_router(state: CustomerSupportState) -> dict:
        redacted_text = state["redacted_text"]
        customer_tier = state.get("customer_tier", "bronze")

        classification = classifier_llm.invoke([
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=f"Classify this support ticket:\n\n{redacted_text}"),
        ])

        needs_escalation = classification.requires_escalation

        if customer_tier == "platinum" and classification.priority in ["high", "critical"]:
            needs_escalation = True
        if classification.confidence < 0.6:
            needs_escalation = True
        if classification.category == "escalation":
            needs_escalation = True

        print(
            f"  [Supervisor] Category: {classification.category} | "
            f"Priority: {classification.priority} | "
            f"Confidence: {classification.confidence:.2f} | "
            f"Escalation: {needs_escalation}"
        )

        return {
            "category": classification.category,
            "priority": classification.priority,
            "classification_confidence": classification.confidence,
            "needs_escalation": needs_escalation,
            "tools_used": ["supervisor_classifier"],
            "messages": [
                AIMessage(
                    content=f"Ticket classified as {classification.category} "
                    f"(priority: {classification.priority})"
                )
            ],
        }

    return supervisor_router


def build_quick_answer_node(orders_db: dict):
    """Build the deterministic quick-answer node (no LLM)."""

    def quick_answer_node(state: CustomerSupportState) -> dict:
        redacted_text = state["redacted_text"]
        order_match = re.search(r"ORD-\d{5}", redacted_text)

        if not order_match:
            return {
                "specialist_response": "I'd be happy to help with your order. Could you please provide your order number?",
                "tools_used": state.get("tools_used", []) + ["quick_answer_fallback"],
            }

        order_id = order_match.group()
        if order_id not in orders_db:
            return {
                "specialist_response": f"I could not find order {order_id} in our system. Please double-check the order number.",
                "tools_used": state.get("tools_used", []) + ["quick_answer_lookup"],
            }

        order = orders_db[order_id]
        status = order["status"]
        tracking = order["tracking_number"]
        est_delivery = order["estimated_delivery"][:10]
        items_summary = ", ".join(item["name"] for item in order["items"])

        status_messages = {
            "delivered": f"Your order {order_id} ({items_summary}) has been delivered. Tracking: {tracking}.",
            "in_transit": f"Your order {order_id} ({items_summary}) is currently in transit. Tracking: {tracking}. Estimated delivery: {est_delivery}.",
            "processing": f"Your order {order_id} ({items_summary}) is currently being processed. Estimated delivery: {est_delivery}.",
            "cancelled": f"Your order {order_id} ({items_summary}) was cancelled. If you did not request this, please let us know.",
        }

        response = status_messages.get(status, f"Your order {order_id} has status: {status}.")
        print(f"  [Quick Answer] Deterministic lookup for {order_id} -> status: {status}")

        return {
            "specialist_response": response,
            "tools_used": state.get("tools_used", []) + ["quick_answer_lookup"],
        }

    return quick_answer_node


def _invoke_specialist(agent, agent_name: str, state: CustomerSupportState) -> dict:
    """Generic helper to invoke a specialist agent (create_react_agent graph)."""
    redacted_text = state["redacted_text"]
    customer_id = state.get("customer_id", "unknown")

    context = (
        f"Customer ID: {customer_id}\n"
        f"Ticket Category: {state.get('category', 'unknown')}\n"
        f"Priority: {state.get('priority', 'unknown')}\n"
        f"\nCustomer Message:\n{redacted_text}"
    )

    print(f"  [{agent_name}] Processing ticket...")

    result = agent.invoke({"messages": [{"role": "user", "content": context}]})

    response_text = ""
    if "messages" in result:
        for msg in reversed(result["messages"]):
            if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                response_text = msg.content
                break
            if hasattr(msg, "content") and msg.content and hasattr(msg, "tool_calls") and not msg.tool_calls:
                response_text = msg.content
                break

    if not response_text:
        response_text = "I apologize, but I was unable to process your request. Let me transfer you to a human agent."

    print(f"  [{agent_name}] Response generated ({len(response_text)} chars)")

    return {
        "specialist_response": response_text,
        "tools_used": state.get("tools_used", []) + [agent_name],
        "messages": [AIMessage(content=f"[{agent_name}] {response_text[:200]}...")],
    }


def build_handler_nodes(specialists: dict) -> dict:
    """Build handler nodes for each specialist agent.

    Args:
        specialists: dict mapping name to AgentExecutor
            (order_specialist, returns_specialist, billing_specialist, product_specialist)

    Returns:
        dict of handler node functions keyed by node name
    """

    def handle_order(state: CustomerSupportState) -> dict:
        return _invoke_specialist(specialists["order_specialist"], "order_specialist", state)

    def handle_returns(state: CustomerSupportState) -> dict:
        return _invoke_specialist(specialists["returns_specialist"], "returns_specialist", state)

    def handle_billing(state: CustomerSupportState) -> dict:
        return _invoke_specialist(specialists["billing_specialist"], "billing_specialist", state)

    def handle_product(state: CustomerSupportState) -> dict:
        return _invoke_specialist(specialists["product_specialist"], "product_specialist", state)

    return {
        "order_handler": handle_order,
        "returns_handler": handle_returns,
        "billing_handler": handle_billing,
        "product_handler": handle_product,
    }


def escalation_hitl_node(state: CustomerSupportState) -> dict:
    """HITL escalation node — pauses graph for human manager review."""
    ticket_id = state.get("ticket_id", "unknown")
    customer_id = state.get("customer_id", "unknown")
    customer_tier = state.get("customer_tier", "unknown")
    category = state.get("category", "unknown")
    priority = state.get("priority", "unknown")
    redacted_text = state["redacted_text"]
    confidence = state.get("classification_confidence", 0.0)

    reasons = []
    if customer_tier == "platinum":
        reasons.append("Platinum customer (VIP)")
    if category == "escalation":
        reasons.append("Customer requested escalation")
    if confidence < 0.6:
        reasons.append(f"Low classification confidence ({confidence:.2f})")
    if priority in ["high", "critical"]:
        reasons.append(f"{priority.capitalize()} priority ticket")

    escalation_reason = "; ".join(reasons) if reasons else "Manual escalation"

    print(f"  [HITL] Escalation triggered for ticket {ticket_id}")
    print(f"  [HITL] Reason: {escalation_reason}")

    human_input = interrupt({
        "action": "escalation_review",
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "customer_tier": customer_tier,
        "category": category,
        "priority": priority,
        "classification_confidence": confidence,
        "redacted_text": redacted_text,
        "escalation_reason": escalation_reason,
        "instructions": (
            "Please review this ticket and provide:\n"
            "1. Your resolution notes\n"
            "2. Any special instructions for the customer response"
        ),
    })

    human_notes = human_input if isinstance(human_input, str) else str(human_input)
    print(f"  [HITL] Human manager responded: {human_notes[:100]}...")

    return {
        "specialist_response": f"[Manager Review] {human_notes}",
        "human_notes": human_notes,
        "tools_used": state.get("tools_used", []) + ["escalation_hitl"],
        "messages": [AIMessage(content=f"Ticket escalated. Manager notes: {human_notes[:200]}")],
    }


def build_format_response_node(llm_secondary, customers_db: dict):
    """Build the response formatter node using the secondary LLM."""

    def format_response_node(state: CustomerSupportState) -> dict:
        specialist_response = state.get("specialist_response", "")
        customer_id = state.get("customer_id", "")
        ticket_id = state.get("ticket_id", "")

        customer_name = "Valued Customer"
        if customer_id in customers_db:
            customer_name = customers_db[customer_id]["name"].split()[0]

        format_prompt = f"""Rewrite the following customer support response as a professional,
friendly email response from ShopSmart Customer Support.

Customer's first name: {customer_name}
Ticket ID: {ticket_id}

Guidelines:
- Start with a personalized greeting using the customer's first name
- Be empathetic and professional
- Include all the specific details from the response (order numbers, tracking, dates)
- End with an offer for further assistance
- Sign off as "ShopSmart Customer Support Team"
- Keep it concise but complete

Original response to reformat:
{specialist_response}"""

        formatted = llm_secondary.invoke([HumanMessage(content=format_prompt)])
        final_response = formatted.content
        print(f"  [Formatter] Response formatted ({len(final_response)} chars)")

        return {
            "final_response": final_response,
            "tools_used": state.get("tools_used", []) + ["response_formatter"],
        }

    return format_response_node
