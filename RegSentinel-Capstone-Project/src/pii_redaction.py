"""Task 2 — PII Redaction: mask SSN / EIN / account numbers / customer names (GLBA)."""
import re
from typing import Optional

from src.data_loader import fft_query


def redact_pii(text: str, extra_names: Optional[list[str]] = None) -> str:
    """Mask SSN / EIN / account numbers / customer names before display and logging.

    Satisfies GLBA Safeguards Rule DLP requirements.
    """
    if not text or not isinstance(text, str):
        return text

    # 1. Social Security Numbers  e.g. 123-45-6789
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN-REDACTED]", text)

    # 2. Employer Identification Numbers  e.g. 12-3456789
    text = re.sub(r"\b\d{2}-\d{7}\b", "[EIN-REDACTED]", text)

    # 3. Bank account numbers  e.g. ACC-99012
    text = re.sub(r"\bACC-\d+\b", "[ACCT-REDACTED]", text)

    # 4. Customer names from the database (+ any caller-supplied extras)
    try:
        rows = fft_query("SELECT name FROM customers")
        customer_names: list[str] = [r["name"] for r in rows if r.get("name")]
    except Exception:
        customer_names = []

    if extra_names:
        customer_names.extend(extra_names)

    # Longest-first to prevent partial-match shadowing ("John" before "John Doe")
    customer_names = sorted(set(customer_names), key=len, reverse=True)

    for name in customer_names:
        if name and len(name.strip()) > 1:
            text = re.sub(r"\b" + re.escape(name) + r"\b", "[NAME-REDACTED]", text)

    return text
