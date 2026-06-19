"""Task 4 — Evaluation: deterministic citation check + LLM-as-judge faithfulness metric."""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from src.data_loader import AUDIT_EVENTS, fft_query

# ── Ground-truth sets (populated dynamically from the database) ────────────────
def _load_known_txn_ids() -> set[str]:
    rows = fft_query("SELECT txn_id FROM transactions")
    return {r["txn_id"] for r in rows}


def _load_known_event_ids() -> set[str]:
    return {e["event_id"] for e in AUDIT_EVENTS}


KNOWN_TXN_IDS:   set[str] = _load_known_txn_ids()
KNOWN_EVENT_IDS: set[str] = _load_known_event_ids()

# Checklist for the LLM judge — critical findings the report MUST cover
GROUND_TRUTH_CRITICAL = [
    "FFT-C006 structuring pattern (≥3 sub-$10K cash deposits)",
    "FFT-C004 layering pattern (wire-in then ≥2 international wire-outs)",
    "Large-cash CTR filing required for transactions > $10K",
    "SOX §404 SoD violation — self-approval of financial system change",
    "FFIEC change-management failure — after-hours change without ticket",
    "BSA SAR filing obligation triggered",
]


# ── Metric 1: Deterministic citation accuracy ──────────────────────────────────
def citation_accuracy(report: str) -> dict:
    """Check that every transaction/event ID cited in the report actually exists.

    Returns a dict with keys: score (0.0-1.0), n_citations, hallucinated_ids.
    """
    if not report:
        return {"score": 1.0, "n_citations": 0, "hallucinated_ids": []}

    # Extract IDs that look like TXN_… or EVENT_… patterns
    raw_citations = re.findall(r"\b(?:TXN|EVENT|AE)[_\-][A-Z0-9_\-]+\b", report)
    if not raw_citations:
        return {"score": 1.0, "n_citations": 0, "hallucinated_ids": []}

    all_valid = KNOWN_TXN_IDS.union(KNOWN_EVENT_IDS)
    # Normalise: uppercase + replace hyphens with underscores
    normalised_valid = {uid.replace("-", "_").upper() for uid in all_valid}

    hallucinated, valid_count = [], 0
    for cited in raw_citations:
        if cited.replace("-", "_").upper() in normalised_valid:
            valid_count += 1
        else:
            hallucinated.append(cited)

    score = valid_count / len(raw_citations) if raw_citations else 1.0
    return {
        "score": round(score, 2),
        "n_citations": len(raw_citations),
        "hallucinated_ids": list(set(hallucinated)),
    }


# ── Metric 2: LLM-as-judge (faithfulness + completeness) ─────────────────────
def judge_report(report: str, llm=None) -> dict:
    """Ask the LLM to score the report on faithfulness and completeness (0.0-1.0 each)."""
    if not report:
        return {"faithfulness": 0.0, "completeness": 0.0, "notes": "Empty report."}
    if llm is None:
        # Lazy import to avoid circular dependency
        from src.nodes import llm as _llm
        llm = _llm

    critical_items_str = "\n".join(f"- {item}" for item in GROUND_TRUTH_CRITICAL)

    system_prompt = (
        "You are an expert regulatory examiner. Evaluate the bank compliance report "
        "on two dimensions:\n"
        "1. Faithfulness (0.0-1.0): are assertions supported by audit evidence without hallucination?\n"
        "2. Completeness (0.0-1.0): does the report flag ALL of the following known risk conditions?\n"
        f"{critical_items_str}\n\n"
        "Respond ONLY with a raw JSON object (no markdown, no preamble):\n"
        '{"faithfulness": 0.00, "completeness": 0.00, "notes": "narrative string"}'
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Evaluate this report:\n\n{report}"),
        ])
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines() if not line.strip().startswith("```")
            ).strip()
        parsed = json.loads(raw)
        return {
            "faithfulness": parsed.get("faithfulness", 0.0),
            "completeness": parsed.get("completeness", 0.0),
            "notes": parsed.get("notes", ""),
        }
    except Exception as e:
        return {"faithfulness": 0.0, "completeness": 0.0, "notes": f"Eval error: {e}"}
