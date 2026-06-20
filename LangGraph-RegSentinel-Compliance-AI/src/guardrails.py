"""Task 1 — Guardrails: detect prompt-injection in untrusted free-text fields."""
import re

from src.tools import query_transactions


# Common prompt-injection patterns found in transaction memos / counterparty fields
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
    r"(?i)disregard\s+the\s+above",
    r"(?i)you\s+are\s+now",
    r"(?i)do\s+not\s+(?:file|report|flag)",
    r"(?i)\boverride\b",
    r"(?i)act\s+as\s+(?:a\s+)?(?:different|new)",
    r"(?i)system\s*prompt",
    r"(?i)jailbreak",
]


def scan_for_injection(text: str) -> list[str]:
    """Return suspicious spans found in an untrusted free-text field.

    Returns a list of matched strings (empty list == clean input).
    """
    if not text:
        return []
    matched = []
    for pattern in _INJECTION_PATTERNS:
        for m in re.finditer(pattern, text):
            matched.append(m.group(0))
    return matched


def scan_transaction_memos(start_date: str, end_date: str) -> list[dict]:
    """Sweep counterparty/destination free-text fields in the period for injection attempts."""
    alerts = []
    txns = query_transactions(start_date, end_date)
    for txn in txns:
        for field in ("counterparty", "destination"):
            val = txn.get(field, "")
            if val and isinstance(val, str):
                spans = scan_for_injection(val)
                if spans:
                    alerts.append({
                        "txn_id": txn.get("txn_id"),
                        "field": field,
                        "spans": spans,
                    })
    return alerts
