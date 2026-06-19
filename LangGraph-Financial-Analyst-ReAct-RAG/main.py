"""
main.py — Meridian Wealth Partners Financial Analyst Agentic RAG
Run: python main.py
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent / ".env")

from src.agent import (
    DB_PATH, POLICY_DIR, init_clients,
    build_policy_vectorstore, build_tools, build_agent,
    call_agent, print_trace, query_db
)
from src.diagrams import generate_all_diagrams


def verify_data():
    """Sanity-check database and policy docs are present."""
    assert os.path.exists(DB_PATH), f"❌ DB not found: {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    print(f"✅ Database: {DB_PATH} ({os.path.getsize(DB_PATH)/1024:.1f} KB)")
    for table in ["clients", "holdings", "market_data"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   📋 {table}: {count} rows")
    print("\n👤 Clients:")
    for row in conn.execute("SELECT client_id, name, risk_profile, aum_inr FROM clients"):
        print(f"   {row[0]}: {row[1]} | {row[2]} | AUM: ₹{row[3]:,.0f}")
    conn.close()


def run_queries(agent):
    """Execute the four lab queries and return results."""

    query1 = """Prepare a quarterly briefing for Client CLT-001 (Rajesh Mehta).
Include: portfolio performance summary with per-holding returns, relevant market conditions
for his sectors, check if his current allocation complies with our investment policies for
his risk profile (Moderate-Aggressive), and provide any recommended rebalancing actions.
Also check for latest news on sectors he is most exposed to."""

    query2 = """Compare the IT sector exposure of Client CLT-001 and Client CLT-002.
Which client is more overweight in IT? Check our sector concentration policy limits
from the policy documents and recommend if either client needs to trim IT positions.
Also look up the latest market outlook for Indian IT sector."""

    query3 = """Client CLT-003 (Amit Choudhury) wants to increase his position in Adani Enterprises.
Check his current Adani holding as a percentage of his total portfolio from the database,
then search our policy documents for the single-stock concentration limit and the stop-loss
framework for his risk profile (Aggressive). Advise whether this purchase is permissible."""

    query4 = """Client CLT-005 (Karan Malhotra) has heavy exposure to Telecom and Auto sectors.
Look up his portfolio from the database, then search the web for the latest news on RBI
monetary policy decisions and their potential impact on these sectors.
Summarize the outlook and recommend any portfolio actions."""

    results = {}
    print("\n" + "="*80)
    print("QUERY 1 — Quarterly Client Briefing (CLT-001)")
    print("="*80)
    results["result1"] = call_agent(agent, query1)
    print_trace(results["result1"])

    print("\n" + "="*80)
    print("QUERY 2 — Cross-Client IT Sector Comparison")
    print("="*80)
    results["result2"] = call_agent(agent, query2)

    print("\n" + "="*80)
    print("QUERY 3 — Single-Stock Concentration & Risk Policy")
    print("="*80)
    results["result3"] = call_agent(agent, query3)

    print("\n" + "="*80)
    print("QUERY 4 — Live Web Search: RBI Policy + Sector Outlook")
    print("="*80)
    results["result4"] = call_agent(agent, query4)

    return results


def print_summary(results, pdf_files, policy_vectorstore):
    """Print tool usage summary across all queries."""
    labels = [
        ("Client Briefing (CLT-001)", results["result1"]),
        ("IT Sector Comparison",       results["result2"]),
        ("Concentration Policy Check", results["result3"]),
        ("Web Search + Sector Outlook",results["result4"]),
    ]

    print("\n📊 Agent Tool Usage Summary")
    print(f"{'='*70}")
    print(f"{'Query':<35} {'# Tools':<10} {'Tools Used'}")
    print(f"{'─'*70}")

    total_calls = 0
    tool_freq = {}
    for name, result in labels:
        tmsgs = [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]
        tnames = [m.name for m in tmsgs]
        total_calls += len(tnames)
        for tn in tnames:
            tool_freq[tn] = tool_freq.get(tn, 0) + 1
        print(f"{name:<35} {len(tnames):<10} {', '.join(tnames)}")

    print(f"{'─'*70}")
    print(f"{'TOTAL':<35} {total_calls}")

    print(f"\n📈 Tool Frequency:")
    for tn, cnt in sorted(tool_freq.items(), key=lambda x: -x[1]):
        print(f"   {tn:<25} {cnt:>2} {'█' * cnt}")

    conn = sqlite3.connect(DB_PATH)
    print(f"\n🏗️  Data Infrastructure Summary:")
    print(f"   SQLite: {DB_PATH} ({os.path.getsize(DB_PATH)/1024:.0f} KB)")
    for table in ["clients", "holdings", "market_data"]:
        cnt = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"     → {table}: {cnt} rows")
    conn.close()
    print(f"   FAISS: {policy_vectorstore.index.ntotal} vectors from {len(pdf_files)} policy PDFs")
    print(f"   Web:   Tavily API (live search)")


def main():
    print("🚀 Meridian Wealth Partners — Financial Analyst Agentic RAG")
    print("="*60)

    # 1. Check API keys
    for key in ["OPENAI_API_KEY", "TAVILY_API_KEY"]:
        status = "✅ Loaded" if os.environ.get(key) else "❌ MISSING"
        print(f"   {key}: {status}")

    # 2. Verify data
    verify_data()

    # 3. Init LLM + embeddings
    llm, embedding_model = init_clients()
    print("\n✅ Clients initialised")
    print(f"   LLM: gpt-5-mini  |  Embeddings: text-embedding-3-small")

    # 4. Build RAG vector store
    vectorstore, retriever, pdf_files = build_policy_vectorstore(embedding_model)

    # 5. Test RAG retrieval
    print("\n🔍 RAG Retrieval Smoke-Test:")
    test_queries = [
        "What is the maximum single stock concentration allowed?",
        "What are the drawdown limits for an Aggressive profile?",
        "How should we rebalance when tax year end is approaching?",
    ]
    for q in test_queries:
        docs = retriever.invoke(q)
        src = Path(docs[0].metadata.get("source", "?")).name
        pg = docs[0].metadata.get("page", "?")
        print(f"   ✔ \"{q[:60]}\" → {src} (p{pg})")

    # 6. Build tools & agent
    tools = build_tools(retriever)
    agent = build_agent(llm, tools)
    print(f"\n✅ ReAct agent ready — tools: {[t.name for t in tools]}")

    # 7. Save architecture diagrams
    generate_all_diagrams(agent)

    # 8. Run the four lab queries
    results = run_queries(agent)

    # 9. Print summary
    print_summary(results, pdf_files, vectorstore)

    print("\n✅ All done. Check output/ for PNG diagrams.")


if __name__ == "__main__":
    main()
