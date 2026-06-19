"""Shared tool functions used by all 5 ADK runners.

These functions contain the business logic; each runner wraps them
in its framework-specific decorator (@tool, @function_tool, etc.).
"""
import json
from shared.data_loader import get_stats, load_data


def get_transaction_stats() -> str:
    """Return transaction monitoring statistics for MidwestBank."""
    s = get_stats()
    return json.dumps({
        "total_transactions": s["total_transactions"],
        "total_amount_usd": s["total_amount"],
        "suspicious_transactions": s["suspicious_count"],
        "suspicious_percentage": s["suspicious_pct"],
        "suspicious_total_amount_usd": s["suspicious_amount"],
        "ctr_eligible_over_10k": s["ctr_eligible"],
        "ctr_threshold_usd": s["ctr_threshold"],
    }, indent=2)


def get_sar_status() -> str:
    """Return SAR (Suspicious Activity Report) filing status."""
    s = get_stats()
    return json.dumps({
        "total_sar_filings": s["sar_total"],
        "sar_by_status": s["sar_by_status"],
        "sar_by_type": s["sar_by_type"],
        "total_amount_involved_usd": s["sar_total_amount"],
    }, indent=2)


def get_kyc_stats() -> str:
    """Return KYC/CDD (Know Your Customer / Customer Due Diligence) compliance statistics."""
    s = get_stats()
    return json.dumps({
        "total_customers": s["total_customers"],
        "kyc_verified": s["kyc_verified"],
        "kyc_verified_pct": s["kyc_verified_pct"],
        "kyc_expired": s["kyc_expired"],
        "kyc_pending": s["kyc_pending"],
        "pep_flagged_customers": s["pep_count"],
        "risk_score_distribution": s["risk_distribution"],
    }, indent=2)


def detect_aml_patterns() -> str:
    """Detect AML red-flag patterns: structuring, layering, high-velocity."""
    d = load_data()
    txn = d["transactions"]
    s = get_stats()

    patterns = []

    if "is_suspicious" in txn.columns and "txn_type" in txn.columns:
        structuring_candidates = txn[
            (txn["amount"] >= 9000) & (txn["amount"] < 10000) & (txn["is_suspicious"] == True)
        ]
        if len(structuring_candidates) > 0:
            patterns.append({
                "pattern": "structuring",
                "count": len(structuring_candidates),
                "description": f"{len(structuring_candidates)} transactions between $9,000-$10,000 flagged suspicious (potential CTR avoidance)"
            })

    high_velocity = txn.groupby("customer_id").filter(lambda g: len(g) > 20) if "customer_id" in txn.columns else []
    if len(high_velocity) > 0:
        patterns.append({
            "pattern": "high_velocity",
            "count": len(high_velocity["customer_id"].unique()) if "customer_id" in high_velocity.columns else 0,
            "description": "Customers with >20 transactions in reporting period"
        })

    return json.dumps({
        "aml_patterns_detected": len(patterns),
        "patterns": patterns,
        "total_suspicious_transactions": s["suspicious_count"],
        "requires_sar_filing": s["suspicious_count"] > 0,
    }, indent=2)


def get_risk_summary() -> str:
    """Return high-risk customer and priority risk indicators summary."""
    s = get_stats()
    d = load_data()
    cust = d["customers"]

    high_risk_count = 0
    if "risk_score" in cust.columns:
        high_risk = cust[cust["risk_score"].astype(str).str.lower().isin(["high", "3", "4", "5"])]
        high_risk_count = len(high_risk)

    return json.dumps({
        "high_risk_customers": high_risk_count,
        "pep_customers": s["pep_count"],
        "kyc_deficiencies": s["kyc_expired"] + s["kyc_pending"],
        "pending_sar_filings": s["sar_by_status"].get("pending", 0),
        "priority_actions": [
            f"File {s['sar_by_status'].get('pending', 0)} pending SARs",
            f"Remediate {s['kyc_expired']} expired KYC records",
            f"Review {s['suspicious_count']} suspicious transactions",
            f"Enhanced due diligence for {s['pep_count']} PEP customers",
        ]
    }, indent=2)
