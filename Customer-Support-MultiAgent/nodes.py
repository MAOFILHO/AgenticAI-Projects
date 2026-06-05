"""
nodes.py — All LangGraph node functions.
"""
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from state import CustomerSupportState, TicketClassification


# ─────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────

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


def _specialist_prompt(domain: str, guidelines: str) -> str:
    return (
        f"You are ShopSmart's {domain} specialist. {guidelines}\n\n"
        "Always use your tools to look up real data before answering. "
        "Be empathetic, specific, and professional."
    )


ORDER_PROMPT = _specialist_prompt(
    "order",
    "Help customers with order tracking, delivery status, and order issues.\n\n"
    "Guidelines:\n"
    "- Always look up the specific order when an order ID is mentioned\n"
    "- If no order ID is provided, search by customer ID\n"
    "- Provide specific tracking details and estimated delivery dates\n"
    "- Be empathetic if the order is delayed\n"
    "- For cancelled orders, explain next steps",
)

RETURNS_PROMPT = _specialist_prompt(
    "returns",
    "Help with return requests, refund calculations, and exchange policies.\n\n"
    "Guidelines:\n"
    "- ALWAYS check return eligibility before promising a return\n"
    "- Look up the order to verify it exists and is delivered\n"
    "- Use policy_lookup for any policy questions\n"
    "- Calculate the refund amount before confirming\n"
    "- Clearly explain the return process and timeline",
)

BILLING_PROMPT = _specialist_prompt(
    "billing",
    "Help with payment issues, billing disputes, and invoice questions.\n\n"
    "Guidelines:\n"
    "- Check the customer's billing status for recent charges\n"
    "- Look up specific orders if mentioned\n"
    "- Reference official policies for billing disputes\n"
    "- For double charges, assure quick resolution (within 24 hours)\n"
    "- Never disclose full payment details, only last 4 digits",
)

PRODUCT_PROMPT = _specialist_prompt(
    "product",
    "Help with product questions, availability, specifications, and recommendations.\n\n"
    "Guidelines:\n"
    "- Search for products by name when no product ID is given\n"
    "- Provide specifications, pricing, and stock status\n"
    "- Reference product FAQ when available\n"
    "- If a product is out of stock, suggest alternatives\n"
    "- Use policy_lookup for warranty and return questions",
)


# ─────────────────────────────────────────────────────────────
# LangGraph ReAct agent builder (no AgentExecutor)
# ─────────────────────────────────────────────────────────────

def _build_react_executor(llm, tools: list, system_prompt: str):
    """Build a LangGraph ReAct agent. Returns a compiled graph."""
    from langgraph.prebuilt import create_react_agent
    return create_react_agent(llm, tools, prompt=system_prompt)


# ─────────────────────────────────────────────────────────────
# Node builder — call once at startup
# ─────────────────────────────────────────────────────────────

def build_nodes(llm_primary, llm_secondary, all_tools_dict: dict, customers_db: dict):
    classifier_llm = llm_primary.with_structured_output(TicketClassification)

    # ── Supervisor ───────────────────────────────────────────
    def supervisor_router(state: CustomerSupportState) -> dict:
        redacted_text = state["redacted_text"]
        customer_tier = state.get("customer_tier", "bronze")

        classification: TicketClassification = classifier_llm.invoke([
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=f"Classify this support ticket:\n\n{redacted_text}"),
        ])

        needs_escalation = classification.requires_escalation
        if customer_tier == "platinum" and classification.priority in ("high", "critical"):
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
        print(f"  [Supervisor] Reasoning: {classification.reasoning}")

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

    # ── Quick-Answer factory ─────────────────────────────────
    def _make_quick_answer(orders_db_ref: dict):
        def quick_answer_node(state: CustomerSupportState) -> dict:
            redacted_text = state["redacted_text"]
            order_match = re.search(r"ORD-\d{5}", redacted_text)

            if not order_match:
                return {
                    "specialist_response": (
                        "I'd be happy to help with your order. "
                        "Could you please provide your order number?"
                    ),
                    "tools_used": state.get("tools_used", []) + ["quick_answer_fallback"],
                }

            order_id = order_match.group()
            if order_id not in orders_db_ref:
                return {
                    "specialist_response": (
                        f"I could not find order {order_id} in our system. "
                        "Please double-check the order number and try again."
                    ),
                    "tools_used": state.get("tools_used", []) + ["quick_answer_lookup"],
                }

            order = orders_db_ref[order_id]
            status = order["status"]
            tracking = order["tracking_number"]
            est_delivery = order["estimated_delivery"][:10]
            items_summary = ", ".join(item["name"] for item in order["items"])

            status_messages = {
                "delivered": (
                    f"Your order {order_id} ({items_summary}) has been delivered. "
                    f"Tracking: {tracking}."
                ),
                "in_transit": (
                    f"Your order {order_id} ({items_summary}) is currently in transit. "
                    f"Tracking: {tracking}. Estimated delivery: {est_delivery}."
                ),
                "processing": (
                    f"Your order {order_id} ({items_summary}) is being processed. "
                    f"Tracking will be available once shipped. Estimated delivery: {est_delivery}."
                ),
                "cancelled": (
                    f"Your order {order_id} ({items_summary}) was cancelled. "
                    "If you did not request this cancellation, please let us know."
                ),
            }
            response = status_messages.get(status, f"Your order {order_id} has status: {status}.")
            print(f"  [Quick Answer] Deterministic lookup for {order_id} -> status: {status}")

            return {
                "specialist_response": response,
                "tools_used": state.get("tools_used", []) + ["quick_answer_lookup"],
            }

        return quick_answer_node

    # ── Specialist node factory ──────────────────────────────
    def _make_specialist_node(agent, agent_name: str):
        def handler(state: CustomerSupportState) -> dict:
            redacted_text = state["redacted_text"]
            customer_id = state.get("customer_id", "unknown")

            context = (
                f"Customer ID: {customer_id}\n"
                f"Ticket Category: {state.get('category', 'unknown')}\n"
                f"Priority: {state.get('priority', 'unknown')}\n"
                f"\nCustomer Message:\n{redacted_text}"
            )

            print(f"  [{agent_name}] Processing ticket...")
            try:
                result = agent.invoke({"messages": [("human", context)]})
                response_text = ""
                for msg in reversed(result.get("messages", [])):
                    if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                        response_text = msg.content
                        break
            except Exception as exc:
                response_text = (
                    f"I apologize — I encountered an issue processing your request. "
                    f"Let me transfer you to a human agent. (Error: {exc})"
                )

            if not response_text:
                response_text = (
                    "I apologize, but I was unable to process your request. "
                    "Let me transfer you to a human agent."
                )

            print(f"  [{agent_name}] Response generated ({len(response_text)} chars)")

            return {
                "specialist_response": response_text,
                "tools_used": state.get("tools_used", []) + [agent_name],
                "messages": [AIMessage(content=f"[{agent_name}] {response_text[:200]}...")],
            }

        handler.__name__ = f"handle_{agent_name}"
        return handler

    # ── HITL Escalation ──────────────────────────────────────
    def escalation_hitl_node(state: CustomerSupportState) -> dict:
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
        if priority in ("high", "critical"):
            reasons.append(f"{priority.capitalize()} priority ticket")
        escalation_reason = "; ".join(reasons) if reasons else "Manual escalation"

        print(f"  [HITL] Escalation triggered for ticket {ticket_id}")
        print(f"  [HITL] Reason: {escalation_reason}")
        print("  [HITL] Waiting for human manager input...")

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

    # ── Response Formatter ───────────────────────────────────
    def format_response_node(state: CustomerSupportState) -> dict:
        specialist_response = state.get("specialist_response", "")
        customer_id = state.get("customer_id", "")
        ticket_id = state.get("ticket_id", "")

        customer_name = "Valued Customer"
        if customer_id in customers_db:
            customer_name = customers_db[customer_id]["name"].split()[0]

        format_prompt = (
            f"Rewrite the following customer support response as a professional, "
            f"friendly email from ShopSmart Customer Support.\n\n"
            f"Customer's first name: {customer_name}\n"
            f"Ticket ID: {ticket_id}\n\n"
            f"Guidelines:\n"
            f"- Start with a personalized greeting using the customer's first name\n"
            f"- Be empathetic and professional\n"
            f"- Include all specific details (order numbers, tracking, dates)\n"
            f"- End with an offer for further assistance\n"
            f"- Sign off as 'ShopSmart Customer Support Team'\n"
            f"- Keep it concise but complete\n\n"
            f"Original response to reformat:\n{specialist_response}"
        )

        formatted = llm_secondary.invoke([HumanMessage(content=format_prompt)])
        final_response = formatted.content
        print(f"  [Formatter] Response formatted ({len(final_response)} chars)")

        return {
            "final_response": final_response,
            "tools_used": state.get("tools_used", []) + ["response_formatter"],
        }

    return supervisor_router, escalation_hitl_node, format_response_node, _make_quick_answer, _make_specialist_node


# ─────────────────────────────────────────────────────────────
# Top-level factory
# ─────────────────────────────────────────────────────────────

def build_all_nodes(llm_primary, llm_secondary, all_tools_dict, customers_db, orders_db):
    (
        supervisor_router,
        escalation_hitl_node,
        format_response_node,
        _make_quick_answer,
        _make_specialist_node,
    ) = build_nodes(llm_primary, llm_secondary, all_tools_dict, customers_db)

    quick_answer_node = _make_quick_answer(orders_db)

    def _tools(*names):
        return [all_tools_dict[n] for n in names]

    handle_order = _make_specialist_node(
        _build_react_executor(llm_primary, _tools("lookup_order", "search_orders_by_customer", "lookup_customer"), ORDER_PROMPT),
        "order_specialist",
    )
    handle_returns = _make_specialist_node(
        _build_react_executor(llm_primary, _tools("lookup_order", "check_return_eligibility", "calculate_refund", "policy_lookup"), RETURNS_PROMPT),
        "returns_specialist",
    )
    handle_billing = _make_specialist_node(
        _build_react_executor(llm_primary, _tools("check_billing_status", "lookup_customer", "lookup_order", "policy_lookup"), BILLING_PROMPT),
        "billing_specialist",
    )
    handle_product = _make_specialist_node(
        _build_react_executor(llm_primary, _tools("lookup_product", "search_products", "policy_lookup"), PRODUCT_PROMPT),
        "product_specialist",
    )

    return {
        "supervisor": supervisor_router,
        "quick_answer": quick_answer_node,
        "order_handler": handle_order,
        "returns_handler": handle_returns,
        "billing_handler": handle_billing,
        "product_handler": handle_product,
        "escalation": escalation_hitl_node,
        "format_response": format_response_node,
    }