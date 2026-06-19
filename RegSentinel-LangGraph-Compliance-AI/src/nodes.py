"""LangGraph nodes: worker (parallel), synthesis (sequential), critic/refiner loop."""
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL
from src.guardrails import scan_transaction_memos
from src.state import ComplianceState
from src.tools import (
    compute_severity_score,
    detect_aml_patterns,
    get_audit_events,
    search_regulations,
)

# ── Shared model instance ──────────────────────────────────────────────────────
llm = ChatOpenAI(model=OPENAI_MODEL)


def _llm_text(system: str, user: str) -> str:
    msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return msg.content if hasattr(msg, "content") else str(msg)


# ── Parallel worker nodes ──────────────────────────────────────────────────────
def regulation_node(state: ComplianceState) -> dict:
    """RAG over the regulatory corpus → key requirements with citation IDs."""
    hits = search_regulations(
        "CTR filing threshold, structuring, SOX 404 controls, SoD", k=4
    )
    ctx = "\n".join(f"[{h['regulation_id']}] {h['excerpt'][:220]}" for h in hits)
    sys = (
        "You research US banking compliance regulations. Summarise the key requirements "
        "in 3-5 bullets and ALWAYS cite regulation IDs."
    )
    out = _llm_text(sys, f"Regulation context:\n{ctx}\n\nRequest: {state['user_request']}")
    return {"regulation_findings": out, "findings": [{"source": "regulation", "text": out}]}


def transaction_node(state: ComplianceState) -> dict:
    """BSA/AML scan of high-risk customers."""
    scans = {cid: detect_aml_patterns(cid) for cid in ("FFT-C006", "FFT-C004", "FFT-C014")}
    memo_alerts = scan_transaction_memos("2026-07-01", "2026-09-30")
    sys = (
        "You analyse banking transactions for BSA/AML red flags. Summarise each as "
        "customer_id | pattern | evidence | txn_ids. Cite actual transaction IDs."
    )
    out = _llm_text(sys, f"AML scans:\n{json.dumps(scans, indent=2)}")
    return {
        "transaction_findings": out,
        "findings": [{"source": "transaction", "text": out}],
        "guardrail_alerts": memo_alerts,
    }


def audit_node(state: ComplianceState) -> dict:
    """SOX §404 / FFIEC audit-log review."""
    events = get_audit_events("2026-07-01", "2026-09-30")
    anomalies = [e for e in events if e.get("anomaly")]
    sys = (
        "You review IT audit logs for SOX §404 and FFIEC control violations. Summarise each "
        "as event_id | category | control_failure | severity_rationale."
    )
    out = _llm_text(sys, f"Audit anomalies (Q3 2026):\n{json.dumps(anomalies, indent=2)}")
    return {"audit_findings": out, "findings": [{"source": "audit", "text": out}]}


# ── Sequential synthesis nodes ─────────────────────────────────────────────────
def classify_node(state: ComplianceState) -> dict:
    sys = (
        "You are a compliance classifier. Group every finding under one of: "
        "BSA_AML, SOX_404_ICFR, FFIEC_IT, OCC_VENDOR_RISK. "
        "Output one bullet per finding: '[framework] [short description] [evidence ref]'."
    )
    user = (
        f"Regulation context:\n{state.get('regulation_findings', '')}\n\n"
        f"Transaction findings:\n{state.get('transaction_findings', '')}\n\n"
        f"Audit findings:\n{state.get('audit_findings', '')}"
    )
    return {"classified_findings": _llm_text(sys, user)}


def score_node(state: ComplianceState) -> dict:
    anchors = "\n".join(
        f"  {line.strip()} -> heuristic {compute_severity_score(line)['severity']}"
        for line in state.get("classified_findings", "").splitlines()
        if line.strip()
    )
    sys = (
        "Assign a severity score (1-10) to each classified finding with a one-sentence "
        "rationale. Format: '[severity] [framework] [finding] — [rationale]'."
    )
    return {
        "scored_findings": _llm_text(
            sys,
            f"Findings:\n{state.get('classified_findings', '')}\n\nHeuristic anchors:\n{anchors}",
        )
    }


def format_node(state: ComplianceState) -> dict:
    sys = (
        "Produce the First Federal Trust Q3 2026 Compliance Report in markdown with: "
        "# title; ## Executive Summary (2-3 sentences, headline severity, count of critical "
        "findings); ## Findings by Framework with ### BSA/AML, ### SOX §404 (ICFR), ### FFIEC IT, "
        "### OCC Vendor Risk; ## Recommended Remediation (3-5 prioritised actions); "
        "## Required Regulatory Filings (SARs/CTRs with target deadlines). "
        "Use $ for USD. Be precise — cite txn_ids and event_ids."
    )
    return {"final_report": _llm_text(sys, state.get("scored_findings", ""))}


# ── Critic / Refiner / Router ──────────────────────────────────────────────────
MAX_ITERATIONS = 3


def critic_node(state: ComplianceState) -> dict:
    sys = (
        "You are a compliance officer reviewing a draft Q3 report. Quality bar: "
        "(1) every BSA finding cites a txn_id; (2) every SOX finding cites an event_id; "
        "(3) the filings section lists specific SAR/CTR actions; (4) severities are justified. "
        "Reply with the single token PASS if ALL pass; otherwise list the failing point(s) "
        "in 1-3 sentences. Do NOT rewrite the report."
    )
    fb = _llm_text(sys, state.get("final_report", ""))
    return {
        "critic_feedback": fb,
        "quality_passed": fb.strip().upper().startswith("PASS"),
        "revision_count": state.get("revision_count", 0) + 1,
    }


def refiner_node(state: ComplianceState) -> dict:
    sys = "Rewrite ONLY the sections the critic flagged. Return the FULL improved report."
    user = (
        f"Current draft:\n{state.get('final_report', '')}\n\n"
        f"Critic feedback:\n{state.get('critic_feedback', '')}"
    )
    return {"final_report": _llm_text(sys, user)}


def route_after_critic(state: ComplianceState) -> str:
    """Conditional edge: EXIT when quality passes or iteration cap is reached."""
    if state.get("quality_passed") or state.get("revision_count", 0) >= MAX_ITERATIONS:
        return "END"
    return "refiner"
