"""Assemble and compile the RegSentinel LangGraph compliance pipeline."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.nodes import (
    audit_node,
    classify_node,
    critic_node,
    format_node,
    refiner_node,
    regulation_node,
    route_after_critic,
    score_node,
    transaction_node,
)
from src.state import ComplianceState

_memory = MemorySaver()
_app = None


def build_graph() -> object:
    """Build and compile the StateGraph; return the compiled app."""
    g = StateGraph(ComplianceState)

    for name, fn in [
        ("regulation",   regulation_node),
        ("transaction",  transaction_node),
        ("audit",        audit_node),
        ("classify",     classify_node),
        ("score",        score_node),
        ("format",       format_node),
        ("critic",       critic_node),
        ("refiner",      refiner_node),
    ]:
        g.add_node(name, fn)

    # Parallel fan-out (3 workers)
    g.add_edge(START, "regulation")
    g.add_edge(START, "transaction")
    g.add_edge(START, "audit")

    # Fan-in to sequential synthesis
    g.add_edge("regulation",  "classify")
    g.add_edge("transaction", "classify")
    g.add_edge("audit",       "classify")

    g.add_edge("classify", "score")
    g.add_edge("score",    "format")
    g.add_edge("format",   "critic")

    # Conditional critic ↔ refiner loop (≤ MAX_ITERATIONS)
    g.add_conditional_edges("critic", route_after_critic, {"refiner": "refiner", "END": END})
    g.add_edge("refiner", "critic")

    app = g.compile(checkpointer=_memory)
    print("✓ Graph compiled — Parallel[reg, txn, audit] ➔ classify ➔ score ➔ format ➔ Loop[critic, refiner] ≤ 3")
    return app


def get_app():
    """Singleton accessor for the compiled graph."""
    global _app
    if _app is None:
        _app = build_graph()
    return _app
