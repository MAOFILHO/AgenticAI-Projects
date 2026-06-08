"""Five compliance tools used by the LangGraph worker nodes."""
from typing import Optional

from langchain_core.tools import StructuredTool

from src.data_loader import AUDIT_EVENTS, fft_query
from src.rag import get_vectorstore


# ── Tool 1 ────────────────────────────────────────────────────────────────────
def query_transactions(
    start_date: str, end_date: str, customer_id: Optional[str] = None
) -> list:
    """Filter transactions within a date range. Optionally restrict to one customer."""
    sql = (
        "SELECT txn_id, account_id, customer_id, date, amount, type, channel, "
        "cash, counterparty, destination, reportable_ctr "
        "FROM transactions WHERE date BETWEEN ? AND ?"
    )
    params: list = [start_date, end_date]
    if customer_id:
        sql += " AND customer_id = ?"
        params.append(customer_id)
    sql += " ORDER BY date"
    return fft_query(sql, tuple(params))


# ── Tool 2 ────────────────────────────────────────────────────────────────────
def detect_aml_patterns(customer_id: str, days_window: int = 30) -> dict:
    """Scan a customer's transactions for BSA/AML red flags (structuring, layering, CTR)."""
    txns = fft_query(
        "SELECT * FROM transactions WHERE customer_id=? ORDER BY date",
        (customer_id,),
    )
    flags = []

    # Structuring: ≥3 sub-$10K cash deposits
    sub = [t for t in txns if t["type"] == "deposit" and t["cash"] and 9000 <= t["amount"] < 10000]
    if len(sub) >= 3:
        flags.append({
            "pattern": "structuring",
            "regulation": "BSA_STRUCTURING",
            "count": len(sub),
            "txn_ids": [t["txn_id"] for t in sub],
            "evidence": f"{len(sub)} sub-$10K cash deposits",
        })

    # Layering: wire-in then ≥2 international wire-outs
    w_in = [t for t in txns if t["type"] == "wire_in"]
    w_out_intl = [t for t in txns if t["type"] == "wire_out" and t["destination"] == "international"]
    if w_in and len(w_out_intl) >= 2:
        flags.append({
            "pattern": "layering",
            "regulation": "FINCEN_LAYERING",
            "count": len(w_out_intl),
            "txn_ids": [t["txn_id"] for t in w_in + w_out_intl],
            "evidence": f"wire-in then {len(w_out_intl)} international wire-outs",
        })

    # Large cash (CTR threshold)
    large = [t for t in txns if t["cash"] and t["amount"] > 10000]
    if large:
        flags.append({
            "pattern": "large_cash_over_ctr",
            "regulation": "BSA_CTR",
            "count": len(large),
            "txn_ids": [t["txn_id"] for t in large],
            "evidence": f"{len(large)} cash txns over the $10K CTR threshold",
        })

    return {"customer_id": customer_id, "flag_count": len(flags), "flags": flags}


# ── Tool 3 ────────────────────────────────────────────────────────────────────
def get_audit_events(start_date: str, end_date: str) -> list:
    """Return audit-log events within a date range (inclusive)."""
    return [e for e in AUDIT_EVENTS if start_date <= e["timestamp"][:10] <= end_date]


# ── Tool 4 ────────────────────────────────────────────────────────────────────
def compute_severity_score(finding_text: str) -> dict:
    """Heuristic 1-10 severity grading for a compliance finding."""
    t = (finding_text or "").lower()
    score, rationale = 4, "process gap, no immediate filing impact"

    if any(k in t for k in ["sar", "ctr filing", "fincen 111", "fincen 112", "structuring", "layering"]):
        score, rationale = 10, "regulatory filing required (BSA SAR/CTR)"
    elif any(k in t for k in ["material weakness", "sod violation", "segregation", "self-approval", "sox §404 failure"]):
        score, rationale = 9, "ICFR control failure with reporting implications"
    elif any(k in t for k in ["no_change_ticket", "after_hours", "unauthorized", "no ticket"]):
        score, rationale = 7, "change-management control failure"
    elif any(k in t for k in ["vendor access", "kyc unverified", "documentation gap"]):
        score, rationale = 5, "control deficiency, remediable"

    return {"severity": score, "rationale": rationale}


# ── Tool 5 ────────────────────────────────────────────────────────────────────
def search_regulations(query: str, k: int = 2) -> list:
    """Semantic-search the US compliance regulation corpus; return top-k with regulation IDs."""
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=k)
    return [
        {"regulation_id": r.metadata["regulation_id"], "excerpt": r.page_content[:600]}
        for r in results
    ]


# ── LangChain StructuredTools (for LLM tool-calling if needed) ────────────────
TOOLS = [
    StructuredTool.from_function(f)
    for f in (query_transactions, detect_aml_patterns, get_audit_events,
               compute_severity_score, search_regulations)
]
