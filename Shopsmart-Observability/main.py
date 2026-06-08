"""
ShopSmart Observability — Lab 22
Run: python main.py
"""

import time

from dotenv import load_dotenv

load_dotenv()

from agent import build_agent
from charts import plot_comparison, print_comparison_table
from data import TEST_TICKETS
from observability import (
    flush_langfuse,
    score_routing_langsmith,
    setup_langfuse,
    setup_langsmith,
)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

print("=" * 70)
print("ShopSmart Observability  — LangSmith + Langfuse  (Lab 22)")
print("=" * 70)

langsmith_active = setup_langsmith()
langfuse_handler, langfuse_active = setup_langfuse()

print()
compiled_agent = build_agent()
print("ShopSmart agent compiled.\n")

# ---------------------------------------------------------------------------
# Part 1 — LangSmith run
# ---------------------------------------------------------------------------

print("Part 1: LangSmith Run")
print("-" * 70)
print(f"{'Ticket':<10} {'Category':<15} {'Latency':>10}  {'Chars':>6}")
print("-" * 70)

langsmith_results = []
for ticket in TEST_TICKETS:
    start = time.time()
    result = compiled_agent.invoke({"customer_query": ticket["query"]})
    latency = time.time() - start

    langsmith_results.append(
        {
            "ticket": ticket["id"],
            "category": result["category"],
            "latency_s": round(latency, 2),
            "response_chars": len(result["response"]),
        }
    )
    print(
        f"{ticket['id']:<10} {result['category']:<15} {latency:>9.2f}s  "
        f"{len(result['response']):>6}"
    )

print()

# Custom scoring demo
if langsmith_active and langsmith_results:
    score = score_routing_langsmith(
        TEST_TICKETS[0]["query"],
        "order_status",
        langsmith_results[0]["category"],
    )
    print(f"[LangSmith] Routing score for {langsmith_results[0]['ticket']}: {score}\n")

# ---------------------------------------------------------------------------
# Part 2 — Langfuse run
# ---------------------------------------------------------------------------

print("Part 2: Langfuse Run")
print("-" * 70)
print(f"{'Ticket':<10} {'Category':<15} {'Latency':>10}  {'Chars':>6}")
print("-" * 70)

langfuse_results = []
for ticket in TEST_TICKETS:
    start = time.time()

    config = (
        {
            "callbacks": [langfuse_handler],
            "metadata": {"ticket_id": ticket["id"]},
        }
        if langfuse_handler
        else {}
    )

    result = compiled_agent.invoke({"customer_query": ticket["query"]}, config=config)
    latency = time.time() - start

    langfuse_results.append(
        {
            "ticket": ticket["id"],
            "category": result["category"],
            "latency_s": round(latency, 2),
            "response_chars": len(result["response"]),
        }
    )
    print(
        f"{ticket['id']:<10} {result['category']:<15} {latency:>9.2f}s  "
        f"{len(result['response']):>6}"
    )

if langfuse_active:
    flush_langfuse()

print()

# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

print_comparison_table(langsmith_results, langfuse_results)
plot_comparison(langsmith_results, langfuse_results)

print("\nDone.")
