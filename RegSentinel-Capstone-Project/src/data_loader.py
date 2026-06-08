"""Data-loading utilities: SQL helper and SIEM audit log."""
import json
import sqlite3

from src.config import FFT_DB_PATH, FFT_AUDIT_PATH


def fft_query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a read-only query against the FFT core-banking SQLite DB."""
    conn = sqlite3.connect(FFT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def load_audit_events() -> list[dict]:
    """Load the full SIEM audit-event log from disk."""
    with open(FFT_AUDIT_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Module-level singletons (loaded once on import) ───────────────────────────
AUDIT_EVENTS: list[dict] = load_audit_events()

# Quick sanity prints (shown when run_regsentinel.py boots)
def print_data_summary() -> None:
    n_cust = fft_query("SELECT COUNT(*) n FROM customers")[0]["n"]
    n_acct = fft_query("SELECT COUNT(*) n FROM accounts")[0]["n"]
    n_txn  = fft_query("SELECT COUNT(*) n FROM transactions")[0]["n"]
    high_risk = [r["customer_id"] for r in fft_query("SELECT customer_id FROM customers WHERE risk_rating='high'")]
    bad_kyc   = [r["customer_id"] for r in fft_query("SELECT customer_id FROM customers WHERE kyc_status!='verified'")]
    anomalies = [e for e in AUDIT_EVENTS if e.get("anomaly")]

    print("CORE BANKING SYSTEM (fft_bank.db)")
    print(f"  customers={n_cust}  accounts={n_acct}  transactions={n_txn}")
    print(f"  high-risk customers : {high_risk}")
    print(f"  KYC not clean       : {bad_kyc}")
    print(f"SECURITY AUDIT LOG: {len(AUDIT_EVENTS)} events, {len(anomalies)} anomalies")
    for e in anomalies:
        print(f"  {e['event_id']}  [{e['severity']:8s}]  {e['anomaly']:28s}  {e['target_system']}")
