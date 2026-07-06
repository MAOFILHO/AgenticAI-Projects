"""StateGraph assembly, compilation, and CLI entry point."""

import os
import re
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from shopsmart.state import CustomerSupportState, TicketClassification
from shopsmart.config import (
    build_embeddings,
    build_primary_llm,
    build_secondary_llm,
    get_data_dir,
    load_env,
)
from shopsmart.data_loader import load_all
from shopsmart.pii import build_known_names, redact_pii
from shopsmart.rag import build_policy_retriever
from shopsmart.mcp_client import build_mcp_tools
from shopsmart.agents import (
    build_billing_specialist,
    build_order_specialist,
    build_product_specialist,
    build_returns_specialist,
)
from shopsmart.nodes import (
    build_format_response_node,
    build_handler_nodes,
    build_quick_answer_node,
    build_supervisor_node,
    escalation_hitl_node,
)
from shopsmart.a2a import setup_a2a
from shopsmart.observability import setup_langsmith, setup_langfuse
from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics
from shopsmart.protocols.a2a_bridge import set_active_a2a_client


def route_ticket(state: CustomerSupportState) -> str:
    """Conditional routing after supervisor classification."""
    if state.get("needs_escalation", False):
        return "escalation"

    category = state.get("category", "")

    if category == "order_status":
        redacted_text = state.get("redacted_text", "")
        if re.search(r"ORD-\d{5}", redacted_text):
            return "quick_answer"
        return "order_handler"

    mapping = {
        "returns": "returns_handler",
        "billing": "billing_handler",
        "product_inquiry": "product_handler",
        "technical": "order_handler",
        "escalation": "escalation",
    }
    return mapping.get(category, "order_handler")


def build_system():
    """Build the complete ShopSmart support system.

    Returns (graph, memory, store, data, known_names, langfuse_handler, metrics).
    """
    load_env()

    # Observability (enabled by default)
    setup_langsmith()
    langfuse_handler, _ = setup_langfuse()

    # Protocol benchmark metrics (shared across all protocol client calls)
    metrics = SystemMetrics()
    set_active_metrics(metrics)

    # Data
    data = load_all(get_data_dir())

    # LLMs
    llm_primary = build_primary_llm()
    llm_secondary = build_secondary_llm()
    embeddings = build_embeddings()

    # RAG
    retriever = build_policy_retriever(data["policies_text"], embeddings)

    # Tools (via MCP)
    _, tools_dict = build_mcp_tools(
        data["customers_db"],
        data["orders_db"],
        data["products_db"],
        data["customer_orders"],
        retriever,
    )

    # Specialist agents
    specialists = {
        "order_specialist": build_order_specialist(llm_primary, tools_dict),
        "returns_specialist": build_returns_specialist(llm_primary, tools_dict),
        "billing_specialist": build_billing_specialist(llm_primary, tools_dict),
        "product_specialist": build_product_specialist(llm_primary, tools_dict),
    }

    # A2A protocol
    a2a_registry, a2a_client = setup_a2a(specialists)
    set_active_a2a_client(a2a_client)

    # Nodes
    classifier_llm = llm_primary.with_structured_output(TicketClassification)
    supervisor = build_supervisor_node(classifier_llm)
    quick_answer = build_quick_answer_node(data["orders_db"])
    handler_nodes = build_handler_nodes(specialists)
    format_response = build_format_response_node(llm_secondary, data["customers_db"])

    # Assemble graph
    all_nodes = {
        "supervisor": supervisor,
        "quick_answer": quick_answer,
        **handler_nodes,
        "escalation": escalation_hitl_node,
        "format_response": format_response,
    }

    builder = StateGraph(CustomerSupportState)
    for name, fn in all_nodes.items():
        builder.add_node(name, fn)

    builder.add_edge(START, "supervisor")

    handler_names = [
        "quick_answer", "order_handler", "returns_handler",
        "billing_handler", "product_handler", "escalation",
    ]
    builder.add_conditional_edges(
        "supervisor",
        route_ticket,
        {name: name for name in handler_names},
    )

    for name in handler_names:
        builder.add_edge(name, "format_response")

    builder.add_edge("format_response", END)

    memory = MemorySaver()
    store = InMemoryStore()

    graph = builder.compile(checkpointer=memory, store=store)

    known_names, _, _ = build_known_names(data["customers_db"])

    # Auto-generate Mermaid diagram
    _export_mermaid_diagram(graph)

    print(f"\nSystem ready: {len(all_nodes)} nodes, {len(handler_names)} handlers")

    return graph, memory, store, data, known_names, langfuse_handler, metrics


def _export_mermaid_diagram(graph):
    """Export the LangGraph workflow as Mermaid markdown + PNG to docs/."""
    docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    try:
        mermaid_code = graph.get_graph().draw_mermaid()
        md_path = docs_dir / "graph_diagram.md"
        md_path.write_text(
            "# ShopSmart Support — Auto-Generated Graph Diagram\n\n"
            "```mermaid\n"
            f"{mermaid_code}\n"
            "```\n"
        )
        print(f"\n  [Diagram] Mermaid markdown: file://{md_path.resolve()}")
    except Exception as e:
        print(f"\n  [Diagram] Could not generate markdown: {e}")

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        png_path = docs_dir / "graph_diagram.png"
        png_path.write_bytes(png_data)
        print(f"  [Diagram] PNG image: file://{png_path.resolve()}")
    except Exception:
        print("  [Diagram] PNG generation skipped (requires internet for Mermaid.ink API)")


def process_ticket(ticket: dict, graph, data: dict, known_names: set, thread_id: str | None = None, langfuse_handler=None):
    """Process a single ticket through the full multi-agent system."""
    if thread_id is None:
        thread_id = f"thread-{ticket['ticket_id']}"

    customer_id = ticket["customer_id"]
    customer = data["customers_db"].get(customer_id, {})
    customer_tier = customer.get("tier", "bronze")

    redacted_text, pii_mapping = redact_pii(
        ticket["text"], customer_id, data["customers_db"], known_names
    )

    initial_state = {
        "messages": [HumanMessage(content=redacted_text)],
        "ticket_id": ticket["ticket_id"],
        "customer_id": customer_id,
        "customer_tier": customer_tier,
        "ticket_text": ticket["text"],
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

    config = {"configurable": {"thread_id": thread_id}}
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    print("=" * 70)
    print(f"PROCESSING TICKET: {ticket['ticket_id']}")
    print(f"Customer: {customer_id} (Tier: {customer_tier})")
    print(f"Redacted Text: {redacted_text}")
    print("-" * 70)

    result = graph.invoke(initial_state, config)

    print("-" * 70)
    print(f"Category: {result.get('category', 'N/A')}")
    print(f"Priority: {result.get('priority', 'N/A')}")
    print(f"Tools Used: {result.get('tools_used', [])}")
    print(f"Escalation: {result.get('needs_escalation', False)}")
    print()
    print("FINAL RESPONSE:")
    print(result.get("final_response", "No response generated."))
    print("=" * 70)

    return result, config


def main():
    """CLI entry point — process a sample ticket."""
    graph, memory, store, data, known_names, langfuse_handler, metrics = build_system()

    tickets = data["tickets"]
    if len(sys.argv) > 1:
        ticket_id = sys.argv[1]
        ticket = next((t for t in tickets if t["ticket_id"] == ticket_id), None)
        if not ticket:
            print(f"Ticket {ticket_id} not found.")
            return
        process_ticket(ticket, graph, data, known_names, langfuse_handler=langfuse_handler)
    else:
        ticket = tickets[0]
        process_ticket(ticket, graph, data, known_names, langfuse_handler=langfuse_handler)


if __name__ == "__main__":
    main()
