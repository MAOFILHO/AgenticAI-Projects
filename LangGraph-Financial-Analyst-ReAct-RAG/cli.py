"""
cli.py — Interactive CLI for the Meridian Wealth Agentic RAG system.
Run: python cli.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from src.agent import init_clients, build_policy_vectorstore, build_tools, build_agent, call_agent

PRESET_QUERIES = {
    "1": (
        "Quarterly Briefing — CLT-001",
        """Prepare a quarterly briefing for Client CLT-001 (Rajesh Mehta).
Include: portfolio performance summary with per-holding returns, relevant market conditions
for his sectors, check if his current allocation complies with our investment policies for
his risk profile (Moderate-Aggressive), and provide any recommended rebalancing actions.
Also check for latest news on sectors he is most exposed to.""",
    ),
    "2": (
        "IT Sector Comparison — CLT-001 vs CLT-002",
        """Compare the IT sector exposure of Client CLT-001 and Client CLT-002.
Which client is more overweight in IT? Check our sector concentration policy limits
from the policy documents and recommend if either client needs to trim IT positions.
Also look up the latest market outlook for Indian IT sector.""",
    ),
    "3": (
        "Concentration Policy Check — CLT-003",
        """Client CLT-003 (Amit Choudhury) wants to increase his position in Adani Enterprises.
Check his current Adani holding as a percentage of his total portfolio from the database,
then search our policy documents for the single-stock concentration limit and the stop-loss
framework for his risk profile (Aggressive). Advise whether this purchase is permissible.""",
    ),
    "4": (
        "Web Search + Sector Outlook — CLT-005",
        """Client CLT-005 (Karan Malhotra) has heavy exposure to Telecom and Auto sectors.
Look up his portfolio from the database, then search the web for the latest news on RBI
monetary policy decisions and their potential impact on these sectors.
Summarize the outlook and recommend any portfolio actions.""",
    ),
}


def menu():
    print("\n" + "="*60)
    print("  Meridian Wealth Agentic RAG — Interactive CLI")
    print("="*60)
    for k, (label, _) in PRESET_QUERIES.items():
        print(f"  [{k}] {label}")
    print("  [5] Custom query")
    print("  [q] Quit")
    print("─"*60)
    return input("Select option: ").strip()


def main():
    print("🚀 Initialising agent (this may take ~30s for embeddings)...")
    llm, embedding_model = init_clients()
    _, retriever, _ = build_policy_vectorstore(embedding_model)
    tools = build_tools(retriever)
    agent = build_agent(llm, tools)
    print("✅ Agent ready.\n")

    while True:
        choice = menu()
        if choice == "q":
            print("Goodbye!")
            sys.exit(0)
        elif choice in PRESET_QUERIES:
            _, query = PRESET_QUERIES[choice]
            call_agent(agent, query)
        elif choice == "5":
            query = input("\nEnter your query:\n> ").strip()
            if query:
                call_agent(agent, query)
        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()
