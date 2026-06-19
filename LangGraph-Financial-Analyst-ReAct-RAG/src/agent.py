"""
Meridian Wealth Partners — Financial Analyst Agentic RAG Agent
LangGraph ReAct agent backed by SQLite, FAISS (PDF RAG), and Tavily web search.
"""

import os
import json
import sqlite3
import re
import textwrap
from pathlib import Path

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "data" / "meridian_wealth.db")
POLICY_DIR = str(BASE_DIR / "data" / "policy_documents")


# ──────────────────────────────────────────────
# LLM & Embeddings
# ──────────────────────────────────────────────
def init_clients():
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    return llm, embedding_model


# ──────────────────────────────────────────────
# RAG — Build FAISS vector store from policy PDFs
# ──────────────────────────────────────────────
def build_policy_vectorstore(embedding_model):
    assert os.path.exists(POLICY_DIR), f"❌ Policy documents not found at {POLICY_DIR}"

    all_pages = []
    pdf_files = sorted([f for f in os.listdir(POLICY_DIR) if f.endswith(".pdf")])
    print(f"\n📄 Loading {len(pdf_files)} policy PDFs...")

    for pdf_file in pdf_files:
        loader = PyPDFLoader(os.path.join(POLICY_DIR, pdf_file))
        pages = loader.load()
        all_pages.extend(pages)
        print(f"   {pdf_file}: {len(pages)} pages")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(all_pages)
    print(f"✅ Split into {len(chunks)} chunks")

    print(f"⏳ Embedding {len(chunks)} chunks with text-embedding-3-small...")
    vectorstore = FAISS.from_documents(chunks, embedding_model)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    print(f"✅ FAISS vector store built: {vectorstore.index.ntotal} vectors")
    return vectorstore, retriever, pdf_files


# ──────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────
def query_db(sql, params=()):
    """Execute a SQL query against the Meridian Wealth database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_client_portfolio(client_id):
    """Get full portfolio for a client with enriched market data."""
    client = query_db("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    if not client:
        return None

    holdings = query_db(
        """
        SELECT h.ticker, h.company_name, h.shares, h.avg_cost_basis, h.current_price,
               h.sector, h.purchase_date,
               m.ytd_return_pct, m.pe_ratio, m.analyst_rating, m.high_52w, m.low_52w
        FROM holdings h
        LEFT JOIN market_data m ON h.ticker = m.ticker
        WHERE h.client_id = ?
        ORDER BY (h.shares * h.current_price) DESC
        """,
        (client_id,),
    )
    return {"client": client[0], "holdings": holdings}


def search_market_data(query):
    """Search market data by ticker, sector, or company name."""
    q = query.upper().strip()
    results = query_db("SELECT * FROM market_data WHERE ticker = ?", (q,))
    if not results:
        results = query_db(
            "SELECT * FROM market_data WHERE UPPER(sector) LIKE ? OR UPPER(company_name) LIKE ? OR ticker LIKE ?",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    return results


# ──────────────────────────────────────────────
# Agent Tools (defined as closures so retriever is in scope)
# ──────────────────────────────────────────────
def build_tools(policy_retriever_chain):

    @tool
    def portfolio_lookup(client_id: str) -> str:
        """Look up a client's portfolio from the database: holdings, allocation, total value, and risk profile.
        Use this when you need to know what a specific client owns or their investment profile.
        Input: client ID like 'CLT-001', 'CLT-002', etc."""

        portfolio = get_client_portfolio(client_id.upper())
        if not portfolio:
            available = [r["client_id"] for r in query_db("SELECT client_id FROM clients")]
            return f"Client {client_id} not found. Available: {', '.join(available)}"

        c = portfolio["client"]
        holdings = portfolio["holdings"]

        total_current = sum(h["shares"] * h["current_price"] for h in holdings)
        total_cost = sum(h["shares"] * h["avg_cost_basis"] for h in holdings)
        overall_return = ((total_current - total_cost) / total_cost) * 100

        sector_values = {}
        for h in holdings:
            val = h["shares"] * h["current_price"]
            sector_values[h["sector"]] = sector_values.get(h["sector"], 0) + val
        sector_pct = {s: round((v / total_current) * 100, 1) for s, v in sector_values.items()}

        holdings_detail = []
        for h in holdings:
            cv = h["shares"] * h["current_price"]
            gain = ((h["current_price"] - h["avg_cost_basis"]) / h["avg_cost_basis"]) * 100
            wt = (cv / total_current) * 100
            holdings_detail.append(
                {
                    "ticker": h["ticker"],
                    "company": h["company_name"],
                    "shares": h["shares"],
                    "avg_cost": h["avg_cost_basis"],
                    "current_price": h["current_price"],
                    "current_value": round(cv),
                    "unrealized_gain_pct": round(gain, 1),
                    "portfolio_weight_pct": round(wt, 1),
                    "sector": h["sector"],
                    "ytd_return": h["ytd_return_pct"],
                    "analyst_rating": h["analyst_rating"],
                    "purchase_date": h["purchase_date"],
                }
            )

        result = {
            "client_id": c["client_id"],
            "name": c["name"],
            "relationship_manager": c["relationship_mgr"],
            "risk_profile": c["risk_profile"],
            "investment_horizon": c["investment_horizon"],
            "aum_inr": c["aum_inr"],
            "last_review": c["last_review"],
            "total_portfolio_value": round(total_current),
            "total_cost_basis": round(total_cost),
            "overall_return_pct": round(overall_return, 1),
            "sector_allocation": sector_pct,
            "holdings": holdings_detail,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    @tool
    def market_data_search(query: str) -> str:
        """Search the market database for stock tickers or sectors. Returns current price, YTD returns,
        PE ratio, analyst ratings, 52-week range, and market cap. Use this when you need market
        performance data for specific stocks or want to compare sector performance.
        Input: a stock ticker (e.g. 'RELIANCE'), sector name (e.g. 'IT', 'Banking'), or company name."""

        results = search_market_data(query)
        if not results:
            all_tickers = [r["ticker"] for r in query_db("SELECT ticker FROM market_data")]
            return f"No data found for '{query}'. Available: {', '.join(all_tickers)}"

        formatted = [
            {
                "ticker": r["ticker"],
                "company": r["company_name"],
                "sector": r["sector"],
                "price": r["current_price"],
                "ytd_return": r["ytd_return_pct"],
                "pe_ratio": r["pe_ratio"],
                "analyst_rating": r["analyst_rating"],
                "52w_range": f"{r['low_52w']} - {r['high_52w']}",
                "market_cap_cr": r["market_cap_cr"],
            }
            for r in results
        ]
        return json.dumps(formatted, indent=2, ensure_ascii=False)

    @tool
    def calculate_metrics(expression: str) -> str:
        """Perform financial calculations: returns, percentages, allocations, comparisons.
        Input: describe the calculation, e.g. 'return on 596000 vs cost 430000'
        or 'percentage of 350000 out of 2530000' or 'compare 18.5 vs 12.3'."""
        try:
            numbers = [float(x.replace(",", "")) for x in re.findall(r"[\d,]+\.?\d*", expression)]

            if "return" in expression.lower() or "gain" in expression.lower():
                if len(numbers) >= 2:
                    current, cost = numbers[0], numbers[1]
                    ret = ((current - cost) / cost) * 100
                    return f"Return: (₹{current:,.0f} - ₹{cost:,.0f}) / ₹{cost:,.0f} = {ret:+.2f}%"

            if "percentage" in expression.lower() or "allocation" in expression.lower() or "weight" in expression.lower():
                if len(numbers) >= 2:
                    part, whole = numbers[0], numbers[1]
                    return f"Percentage: ₹{part:,.0f} / ₹{whole:,.0f} = {(part/whole)*100:.2f}%"

            if "compare" in expression.lower() and len(numbers) >= 2:
                a, b = numbers[0], numbers[1]
                return f"Comparison: {a:,.2f} vs {b:,.2f} | Diff: {a-b:+,.2f} ({((a-b)/b)*100:+.2f}%)"

            if len(numbers) == 2:
                a, b = numbers
                return f"Values: {a:,.2f} and {b:,.2f} | Sum: {a+b:,.2f} | Diff: {a-b:+,.2f} | Ratio: {a/b:.4f}"

            return f"Provide two numbers with operation type (return, percentage, compare). Got: '{expression}'"
        except Exception as e:
            return f"Calculation error: {str(e)}"

    @tool
    def policy_retriever(query: str) -> str:
        """Search Meridian Wealth Partners' investment policy PDF documents using RAG (vector similarity search).
        Use this when you need to check investment guidelines, allocation rules, rebalancing triggers,
        risk limits, concentration limits, suitability standards, or reporting requirements.
        Returns relevant excerpts with source document name and page number.
        Input: a natural language query about investment policies."""

        docs = policy_retriever_chain.invoke(query)
        results = []
        for i, doc in enumerate(docs, 1):
            src = os.path.basename(doc.metadata.get("source", "unknown"))
            pg = doc.metadata.get("page", "?")
            results.append(f"[Policy Doc {i}: {src} | Page {pg}]\n{doc.page_content}")
        return "\n\n---\n\n".join(results)

    tools = [portfolio_lookup, market_data_search, calculate_metrics, policy_retriever]

    if os.environ.get("TAVILY_API_KEY"):
        web_search = TavilySearch(max_results=3, topic="news")
        tools.append(web_search)
    else:
        print("⚠️  TAVILY_API_KEY not set — tavily_search tool disabled")

    return tools


# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior financial analyst at Meridian Wealth Partners, a SEBI-registered wealth
management firm managing Rs 2,000 Crore in assets across 800 high-net-worth Indian clients.

Your job is to prepare comprehensive client briefings and answer investment queries using your tools.

AVAILABLE DATA SOURCES:
1. portfolio_lookup — queries the SQL database for client holdings, allocation, and risk profile
2. market_data_search — queries the SQL database for stock/sector data (price, YTD, PE, analyst ratings)
3. calculate_metrics — computes financial metrics (returns, allocation percentages, comparisons)
4. policy_retriever — RAG search over the firm's 5 investment policy PDFs (asset allocation, risk management,
   suitability standards, rebalancing protocol, reporting standards)
5. tavily_search — searches the web for latest market news, RBI updates, sector analysis

GUIDELINES:
- Always check the client's risk profile before making recommendations
- When checking policy compliance, ALWAYS use the policy_retriever tool — never guess the rules
- Cite specific policy document names and page numbers when referencing guidelines
- Do not provide compliance conclusions without first using policy_retriever.
- Do not provide market-news claims without using tavily_search.
- If required data is missing, say so explicitly instead of inferring.
- Use Indian Rupee (₹) for all amounts. Use lakhs and crores for large values.
- Include specific numbers: exact returns, allocation percentages, policy thresholds
- For briefings, structure as: Portfolio Summary → Market Context → Policy Compliance → Recommendations
"""


# ──────────────────────────────────────────────
# Build the agent
# ──────────────────────────────────────────────
def build_agent(llm, tools):
    from langchain_core.messages import SystemMessage

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    return agent


# ──────────────────────────────────────────────
# Utility: pretty-print agent trace
# ──────────────────────────────────────────────
def print_trace(result):
    print("\n🔍 AGENT TRACE — Full Message History")
    print(f"{'='*80}\n")

    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__

        if msg_type == "HumanMessage":
            print(f"Step {i} | 👤 USER:")
            print(f"   {str(msg.content)[:200]}...")

        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"\nStep {i} | 🧠 AGENT → calls {len(msg.tool_calls)} tool(s):")
                for tc in msg.tool_calls:
                    args_str = json.dumps(tc["args"], ensure_ascii=False)[:120]
                    print(f"   🔧 {tc['name']}({args_str})")
            else:
                print(f"\nStep {i} | 🤖 FINAL ANSWER ({len(str(msg.content))} chars)")

        elif msg_type == "ToolMessage":
            print(f"\nStep {i} | 📦 TOOL: {msg.name}")
            print(f"   {str(msg.content)[:200]}...")

    print(f"\n{'='*80}")
    tool_msgs = [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]
    print(f"Total steps: {len(result['messages'])} | Tool calls: {len(tool_msgs)}")
    print(f"Tools used: {[m.name for m in tool_msgs]}")


def call_agent(agent, query):
    """Invoke the agent and print a structured response."""
    print(f"\n📋 Query: {query}")
    print(f"{'='*80}\n")

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    print("\n🤖 AGENT RESPONSE:")
    print(f"{'─'*80}")
    final_msg = result["messages"][-1]
    print(final_msg.content if hasattr(final_msg, "content") else final_msg)

    tool_calls = [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]
    print(f"\n📊 Tools used: {[m.name for m in tool_calls]}")

    web_calls = [m for m in tool_calls if m.name == "tavily_search"]
    print(f"🌐 Web search called: {len(web_calls)} time(s)")

    policy_calls = [m for m in tool_calls if m.name == "policy_retriever"]
    print(f"📚 Policy retriever called: {len(policy_calls)} time(s)")
    for pc in policy_calls:
        pdf_refs = re.findall(r"[A-Za-z_]+\.pdf", pc.content)
        if pdf_refs:
            print(f"   Referenced PDFs: {', '.join(set(pdf_refs))}")

    return result
