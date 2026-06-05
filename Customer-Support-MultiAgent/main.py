"""
main.py — ShopSmart Customer Support Multi-Agent System
Lab 9 · Project 2 · Spine A Full Build

Run with:
    python main.py

Requires:
    - .env file with OPENAI_API_KEY (copy from .env.example)
    - Python 3.11+
    - pip install -r requirements.txt
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from config import llm_primary, llm_secondary, embeddings
from data_loader import load_all, print_summary
from pii import redact_pii
from rag import build_policy_retriever
from tools import build_tools
from nodes import build_all_nodes
from graph import build_graph
from visualize import visualize_graph


# ─────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────

def bootstrap():
    """Load data, build RAG, wire tools + nodes + graph. Returns (graph, data)."""
    print("\n" + "=" * 60)
    print("BOOTSTRAPPING SHOPSMART MULTI-AGENT SYSTEM")
    print("=" * 60)

    data = load_all()
    print_summary(data)

    print("\nBuilding RAG knowledge base...")
    policy_retriever = build_policy_retriever(data["POLICIES"], embeddings)

    print("\nBuilding tools...")
    all_tools, all_tools_dict = build_tools(
        customers_db=data["CUSTOMERS_DB"],
        orders_db=data["ORDERS_DB"],
        products_db=data["PRODUCTS_DB"],
        customer_orders=data["CUSTOMER_ORDERS"],
        policy_retriever=policy_retriever,
    )
    print(f"  {len(all_tools)} tools ready: {', '.join(t.name for t in all_tools)}")

    print("\nBuilding nodes...")
    nodes = build_all_nodes(
        llm_primary=llm_primary,
        llm_secondary=llm_secondary,
        all_tools_dict=all_tools_dict,
        customers_db=data["CUSTOMERS_DB"],
        orders_db=data["ORDERS_DB"],
    )

    print("\nCompiling graph...")
    graph, memory, store = build_graph(nodes)

    visualize_graph(graph)

    return graph, data


# ─────────────────────────────────────────────────────────────
# Helper: process a single ticket
# ─────────────────────────────────────────────────────────────

def process_ticket(graph, data: dict, ticket: dict, thread_id: str = None) -> tuple[dict, dict]:
    """
    Prepare and run one ticket through the full multi-agent graph.

    Returns (result_state, config).
    """
    if thread_id is None:
        thread_id = f"thread-{ticket['ticket_id']}"

    customers_db = data["CUSTOMERS_DB"]
    customer_id = ticket["customer_id"]
    customer = customers_db.get(customer_id, {})
    customer_tier = customer.get("tier", "bronze")

    redacted_text, pii_mapping = redact_pii(ticket["text"], customers_db, customer_id)

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

    print("\n" + "=" * 70)
    print(f"PROCESSING TICKET: {ticket['ticket_id']}")
    print(f"Customer: {customer_id} (Tier: {customer_tier})")
    print(f"Original Category: {ticket['category']} | Priority: {ticket['priority']}")
    print(f"Redacted Text: {redacted_text}")
    print("-" * 70)

    result = graph.invoke(initial_state, config)

    print("-" * 70)
    print(f"Classified Category : {result.get('category', 'N/A')}")
    print(f"Classified Priority : {result.get('priority', 'N/A')}")
    print(f"Tools Used          : {result.get('tools_used', [])}")
    print(f"Escalation          : {result.get('needs_escalation', False)}")
    print("\nFINAL RESPONSE:")
    print(result.get("final_response", "No response generated."))
    print("=" * 70)

    return result, config


# ─────────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────────

def run_test_cases(graph, data: dict):
    tickets = data["TICKETS"]
    customers_db = data["CUSTOMERS_DB"]

    # ── Test 1: Simple Order Status (Quick Answer — no LLM) ──────────
    print("\n\n" + "▶" * 5 + " TEST 1: Simple Order Status (Quick Answer Path)")
    result_1, config_1 = process_ticket(graph, data, tickets[0])

    # ── Test 2: Return Request (Returns Specialist) ──────────────────
    print("\n\n" + "▶" * 5 + " TEST 2: Return Request (Returns Specialist)")
    result_2, config_2 = process_ticket(graph, data, tickets[5])

    # ── Test 3: Billing Dispute (Billing Specialist) ─────────────────
    print("\n\n" + "▶" * 5 + " TEST 3: Billing Dispute (Billing Specialist)")
    result_3, config_3 = process_ticket(graph, data, tickets[13])

    # ── Test 4: Product Inquiry (Product Specialist) ─────────────────
    print("\n\n" + "▶" * 5 + " TEST 4: Product Inquiry (Product Specialist)")
    result_4, config_4 = process_ticket(graph, data, tickets[1])

    # ── Test 5: Platinum Customer Escalation (HITL) ──────────────────
    print("\n\n" + "▶" * 5 + " TEST 5: Platinum Customer Escalation (HITL)")
    test_ticket_5 = tickets[7]
    customer_5 = customers_db[test_ticket_5["customer_id"]]
    print(f"Customer: {customer_5['name']} (Tier: {customer_5['tier']})")
    print(f"Category: {test_ticket_5['category']} | Priority: {test_ticket_5['priority']}")

    redacted_5, pii_map_5 = redact_pii(
        test_ticket_5["text"], customers_db, test_ticket_5["customer_id"]
    )
    thread_id_5 = f"thread-{test_ticket_5['ticket_id']}"
    initial_state_5 = {
        "messages": [HumanMessage(content=redacted_5)],
        "ticket_id": test_ticket_5["ticket_id"],
        "customer_id": test_ticket_5["customer_id"],
        "customer_tier": customer_5["tier"],
        "ticket_text": test_ticket_5["text"],
        "redacted_text": redacted_5,
        "category": "",
        "priority": "",
        "classification_confidence": 0.0,
        "specialist_response": "",
        "needs_escalation": False,
        "human_notes": "",
        "final_response": "",
        "tools_used": [],
        "pii_mapping": pii_map_5,
    }
    config_5 = {"configurable": {"thread_id": thread_id_5}}

    print("\nRunning graph (expect HITL interrupt)...")
    print("-" * 70)
    result_5 = graph.invoke(initial_state_5, config_5)
    print(f"\nGraph paused. Category: {result_5.get('category')} | Escalation: {result_5.get('needs_escalation')}")

    # Simulate human manager response
    manager_notes = (
        "Checked order — it is currently in transit with tracking available. "
        "As a platinum customer, offer a 10% discount on next order as goodwill. "
        "Provide tracking details and estimated delivery date. "
        "Apologise for any delay and assure priority handling."
    )
    print(f"\nManager notes: {manager_notes}")
    print("\nResuming graph with manager input...")
    print("-" * 70)
    result_5_resumed = graph.invoke(Command(resume=manager_notes), config_5)
    print("\nFINAL RESPONSE (after HITL):")
    print(result_5_resumed.get("final_response", "No response generated."))


# ─────────────────────────────────────────────────────────────
# Multi-Turn Demo
# ─────────────────────────────────────────────────────────────

def run_multi_turn_demo(graph, data: dict):
    customers_db = data["CUSTOMERS_DB"]
    multi_turn_thread = "thread-multi-turn-demo"

    print("\n\n" + "=" * 70)
    print("MULTI-TURN CONVERSATION DEMO")
    print("=" * 70)

    def _make_state(text: str, ticket_id: str):
        redacted, pii_map = redact_pii(text, customers_db, "CUST-0001")
        return {
            "messages": [HumanMessage(content=redacted)],
            "ticket_id": ticket_id,
            "customer_id": "CUST-0001",
            "customer_tier": "bronze",
            "ticket_text": text,
            "redacted_text": redacted,
            "category": "",
            "priority": "",
            "classification_confidence": 0.0,
            "specialist_response": "",
            "needs_escalation": False,
            "human_notes": "",
            "final_response": "",
            "tools_used": [],
            "pii_mapping": pii_map,
        }

    config = {"configurable": {"thread_id": multi_turn_thread}}

    print("\n--- Turn 1: Order Status ---")
    turn1_text = "Hi, I ordered a Bluetooth Speaker last week. Order ORD-00002. Has it been delivered?"
    print(f"Customer: {turn1_text}")
    result_1 = graph.invoke(_make_state(turn1_text, "MULTI-001"), config)
    print(f"\nResponse:\n{result_1.get('final_response', 'N/A')[:400]}...")
    print(f"Tools: {result_1.get('tools_used', [])}")

    print("\n--- Turn 2: Follow-up Return Request ---")
    turn2_text = "Thanks. Actually I want to return it — the speaker has a buzzing sound."
    print(f"Customer: {turn2_text}")
    result_2 = graph.invoke(_make_state(turn2_text, "MULTI-002"), config)
    print(f"\nResponse:\n{result_2.get('final_response', 'N/A')[:400]}...")
    print(f"Tools: {result_2.get('tools_used', [])}")
    print(f"\nNote: Same thread_id '{multi_turn_thread}' → system retains conversation history from Turn 1.")


# ─────────────────────────────────────────────────────────────
# Routing Accuracy Evaluation
# ─────────────────────────────────────────────────────────────

def run_routing_accuracy(data: dict):
    """Evaluate supervisor classification accuracy on the first 20 tickets."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from nodes import SUPERVISOR_SYSTEM_PROMPT
    from state import TicketClassification

    print("\n\n" + "=" * 90)
    print("ROUTING ACCURACY ANALYSIS (20 tickets)")
    print("=" * 90)

    classifier_llm = llm_primary.with_structured_output(TicketClassification)
    tickets = data["TICKETS"][:20]
    customers_db = data["CUSTOMERS_DB"]

    print(f"{'Ticket':<12} {'Actual':<18} {'Predicted':<18} {'Conf':>6} {'Match':>6}")
    print("-" * 70)

    correct = 0
    total = 0
    results = []

    for ticket in tickets:
        redacted, _ = redact_pii(ticket["text"], customers_db, ticket["customer_id"])
        try:
            clf = classifier_llm.invoke([
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(content=f"Classify this support ticket:\n\n{redacted}"),
            ])
            predicted = clf.category
            confidence = clf.confidence
            actual = ticket["category"]
            match = predicted == actual
            if match:
                correct += 1
            total += 1
            results.append({"actual": actual, "predicted": predicted, "match": match})
            print(
                f"{ticket['ticket_id']:<12} {actual:<18} {predicted:<18} "
                f"{confidence:>5.2f} {'YES' if match else 'NO':>6}"
            )
        except Exception as e:
            print(f"{ticket['ticket_id']:<12} ERROR: {str(e)[:60]}")
            total += 1

    print("-" * 70)
    accuracy = (correct / total * 100) if total > 0 else 0
    print(f"\nRouting Accuracy: {correct}/{total} = {accuracy:.1f}%\n")

    # Per-category breakdown
    cat_stats: dict[str, dict] = {}
    for r in results:
        cat = r["actual"]
        cat_stats.setdefault(cat, {"total": 0, "correct": 0})
        cat_stats[cat]["total"] += 1
        if r["match"]:
            cat_stats[cat]["correct"] += 1

    print(f"{'Category':<18} {'Total':>6} {'Correct':>8} {'Accuracy':>10}")
    print("-" * 50)
    for cat, stats in sorted(cat_stats.items()):
        pct = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"{cat:<18} {stats['total']:>6} {stats['correct']:>8} {pct:>9.1f}%")


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    graph, data = bootstrap()

    print("\n\n" + "=" * 70)
    print("RUNNING ALL TEST CASES")
    print("=" * 70)

    run_test_cases(graph, data)
    run_multi_turn_demo(graph, data)
    run_routing_accuracy(data)

    # Final summary
    tickets = data["TICKETS"]
    policies = data["POLICIES"]
    customers_db = data["CUSTOMERS_DB"]
    orders_db = data["ORDERS_DB"]
    products_db = data["PRODUCTS_DB"]

    print("\n\n" + "=" * 70)
    print("SYSTEM SUMMARY")
    print("=" * 70)
    print(f"  Graph Nodes         : 8")
    print(f"  Specialist Agents   : 4 (order, returns, billing, product)")
    print(f"  Tools               : 10")
    print(f"  Patterns            : Supervisor · Specialist Agents · Quick-Answer · RAG · PII · HITL · Memory")
    print(f"  Customers           : {len(customers_db)}")
    print(f"  Orders              : {len(orders_db)}")
    print(f"  Products            : {len(products_db)}")
    print(f"  Tickets             : {len(tickets)}")
    print(f"  Policies            : {len(policies)} characters")


if __name__ == "__main__":
    main()
