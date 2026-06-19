"""Load and pre-compute MidwestBank compliance dataset statistics."""
import json
import os
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

_cache: dict = {}


def load_data() -> dict:
    """Load all dataset files once and cache them."""
    if _cache:
        return _cache

    customers = pd.read_csv(DATA_DIR / "customers.csv")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    sar = pd.read_csv(DATA_DIR / "sar_filings.csv")
    findings = pd.read_csv(DATA_DIR / "prior_findings.csv")

    with open(DATA_DIR / "regulatory_thresholds.json") as f:
        thresholds = json.load(f)
    with open(DATA_DIR / "fincen_template.md") as f:
        fincen_template = f.read()
    with open(DATA_DIR / "occ_template.md") as f:
        occ_template = f.read()
    with open(DATA_DIR / "state_template.md") as f:
        state_template = f.read()

    _cache.update({
        "customers": customers,
        "transactions": transactions,
        "sar": sar,
        "findings": findings,
        "thresholds": thresholds,
        "fincen_template": fincen_template,
        "occ_template": occ_template,
        "state_template": state_template,
    })
    return _cache


def get_stats() -> dict:
    """Return pre-computed statistics for tool use."""
    d = load_data()
    txn = d["transactions"]
    cust = d["customers"]
    sar = d["sar"]
    thresh = d["thresholds"]

    ctr_threshold = float(thresh.get("ctr_threshold", {}).get("amount", 10000))

    suspicious = txn[txn.get("is_suspicious", pd.Series(dtype=bool)) == True] if "is_suspicious" in txn.columns else pd.DataFrame()
    ctr_eligible = txn[txn["amount"] >= ctr_threshold] if "amount" in txn.columns else pd.DataFrame()

    kyc_dist = cust["kyc_status"].value_counts().to_dict() if "kyc_status" in cust.columns else {}
    risk_dist = cust["risk_score"].value_counts().to_dict() if "risk_score" in cust.columns else {}
    sar_by_status = sar["status"].value_counts().to_dict() if "status" in sar.columns else {}
    sar_by_type = sar["suspicious_activity_type"].value_counts().to_dict() if "suspicious_activity_type" in sar.columns else {}
    pep_count = int(cust["pep_flag"].sum()) if "pep_flag" in cust.columns else 0

    return {
        "total_customers": len(cust),
        "total_transactions": len(txn),
        "total_amount": float(txn["amount"].sum()) if "amount" in txn.columns else 0,
        "suspicious_count": len(suspicious),
        "suspicious_pct": round(len(suspicious) / max(len(txn), 1) * 100, 2),
        "suspicious_amount": float(suspicious["amount"].sum()) if "amount" in suspicious.columns and len(suspicious) > 0 else 0,
        "ctr_eligible": len(ctr_eligible),
        "ctr_threshold": ctr_threshold,
        "kyc_verified": int(kyc_dist.get("verified", 0)),
        "kyc_expired": int(kyc_dist.get("expired", 0)),
        "kyc_pending": int(kyc_dist.get("pending", 0)),
        "kyc_verified_pct": round(int(kyc_dist.get("verified", 0)) / max(len(cust), 1) * 100, 2),
        "pep_count": pep_count,
        "risk_distribution": {str(k): int(v) for k, v in risk_dist.items()},
        "sar_total": len(sar),
        "sar_by_status": {str(k): int(v) for k, v in sar_by_status.items()},
        "sar_by_type": {str(k): int(v) for k, v in sar_by_type.items()},
        "sar_total_amount": float(sar["amount_involved"].sum()) if "amount_involved" in sar.columns else 0,
    }
