"""
pii.py — PII redaction and restoration utilities.

All ticket text must pass through redact_pii() before reaching any LLM.
"""
import re


def build_name_sets(customers_db: dict) -> tuple[set, set, set]:
    """Build sets of full names, first names, and last names for redaction."""
    full_names = {c["name"] for c in customers_db.values()}
    first_names = {c["name"].split()[0] for c in customers_db.values()}
    last_names = {c["name"].split()[-1] for c in customers_db.values()}
    return full_names, first_names, last_names


def redact_pii(
    text: str,
    customers_db: dict,
    customer_id: str = None,
) -> tuple[str, dict]:
    """
    Redact PII from ticket text before sending to any LLM.

    Redacts:
    - Email addresses (regex)
    - Phone numbers (regex)
    - Known customer names (database-driven, longest-first)

    Returns:
        (redacted_text, pii_mapping) where pii_mapping maps placeholder -> original value.
    """
    known_names, _, _ = build_name_sets(customers_db)

    redacted = text
    pii_mapping: dict[str, str] = {}

    # 1. Email addresses
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    for email in re.findall(email_pattern, redacted):
        pii_mapping["[EMAIL_REDACTED]"] = email
        redacted = redacted.replace(email, "[EMAIL_REDACTED]")

    # 2. Phone numbers (555-123-4567, 555.123.4567, 5551234567)
    phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
    for phone in re.findall(phone_pattern, redacted):
        pii_mapping["[PHONE_REDACTED]"] = phone
        redacted = redacted.replace(phone, "[PHONE_REDACTED]")

    # 3. Known full names (longest first to avoid partial collisions)
    for name in sorted(known_names, key=len, reverse=True):
        if name in redacted:
            pii_mapping["[NAME_REDACTED]"] = name
            redacted = redacted.replace(name, "[NAME_REDACTED]")

    # 4. Specific customer first name if a customer_id was provided
    if customer_id and customer_id in customers_db:
        first_name = customers_db[customer_id]["name"].split()[0]
        if first_name in redacted and "[NAME_REDACTED]" not in pii_mapping:
            pii_mapping["[NAME_REDACTED]"] = customers_db[customer_id]["name"]
            redacted = redacted.replace(first_name, "[NAME_REDACTED]")

    return redacted, pii_mapping


def restore_pii(text: str, pii_mapping: dict) -> str:
    """Restore PII placeholders with original values for customer-facing responses."""
    restored = text
    for placeholder, original in pii_mapping.items():
        restored = restored.replace(placeholder, original)
    return restored
