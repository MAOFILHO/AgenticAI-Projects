"""
graph.py — Assemble and compile the ShopSmart multi-agent StateGraph.

Topology:
    START
      └─ supervisor (classifies ticket + sets routing flags)
           ├─ quick_answer      (deterministic order lookup, no LLM)
           ├─ order_handler     (order specialist agent)
           ├─ returns_handler   (returns specialist agent)
           ├─ billing_handler   (billing specialist agent)
           ├─ product_handler   (product specialist agent)
           └─ escalation        (HITL interrupt for human review)
                └─ (all branches) ─── format_response ─── END
"""
import re

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from state import CustomerSupportState


def route_ticket(state: CustomerSupportState) -> str:
    """
    Routing function for conditional edges after the supervisor.

    Priority order:
    1. Escalation flag (set by supervisor based on business rules)
    2. order_status with explicit order ID → deterministic quick_answer
    3. Classified category → appropriate specialist
    """
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
        "technical": "order_handler",   # technical routed to order specialist
        "escalation": "escalation",
    }
    return mapping.get(category, "order_handler")


def build_graph(nodes: dict):
    """
    Build and compile the StateGraph.

    Args:
        nodes: dict mapping node name -> callable, from nodes.build_all_nodes()

    Returns:
        Compiled LangGraph (graph), MemorySaver (memory), InMemoryStore (store)
    """
    builder = StateGraph(CustomerSupportState)

    # Register nodes
    for name, fn in nodes.items():
        builder.add_node(name, fn)

    # Entry point
    builder.add_edge(START, "supervisor")

    # Conditional branching from supervisor
    handler_names = [
        "quick_answer",
        "order_handler",
        "returns_handler",
        "billing_handler",
        "product_handler",
        "escalation",
    ]
    builder.add_conditional_edges(
        "supervisor",
        route_ticket,
        {name: name for name in handler_names},
    )

    # All handlers converge at format_response
    for name in handler_names:
        builder.add_edge(name, "format_response")

    builder.add_edge("format_response", END)

    memory = MemorySaver()
    store = InMemoryStore()

    graph = builder.compile(checkpointer=memory, store=store)

    print("Graph compiled successfully!")
    print(f"  Nodes : {len(nodes)}")
    print("  Checkpointer: MemorySaver | Store: InMemoryStore")

    return graph, memory, store
