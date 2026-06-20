"""PII redaction and restoration for customer ticket text."""

import re


def build_known_names(customers_db: dict) -> tuple[set, set, set]:
    """Extract all known names, first names, and last names from the customer database."""
    full_names = {c["name"] for c in customers_db.values()}
    first_names = {c["name"].split()[0] for c in customers_db.values()}
    last_names = {c["name"].split()[-1] for c in customers_db.values()}
    return full_names, first_names, last_names


def redact_pii(
    text: str,
    customer_id: str | None,
    customers_db: dict,
    known_names: set,
) -> tuple[str, dict]:
    """
    Redact PII from ticket text before sending to LLM.

    Returns:
        (redacted_text, pii_mapping) where pii_mapping maps placeholders to originals.
    """
    redacted = text
    pii_mapping: dict[str, str] = {}

    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    for email in re.findall(email_pattern, redacted):
        pii_mapping["[EMAIL_REDACTED]"] = email
        redacted = redacted.replace(email, "[EMAIL_REDACTED]")

    phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
    for phone in re.findall(phone_pattern, redacted):
        pii_mapping["[PHONE_REDACTED]"] = phone
        redacted = redacted.replace(phone, "[PHONE_REDACTED]")

    for name in sorted(known_names, key=len, reverse=True):
        if name in redacted:
            pii_mapping["[NAME_REDACTED]"] = name
            redacted = redacted.replace(name, "[NAME_REDACTED]")

    if customer_id and customer_id in customers_db:
        first_name = customers_db[customer_id]["name"].split()[0]
        if first_name in redacted and "[NAME_REDACTED]" not in pii_mapping:
            pii_mapping["[NAME_REDACTED]"] = customers_db[customer_id]["name"]
            redacted = redacted.replace(first_name, "[NAME_REDACTED]")

    return redacted, pii_mapping


def restore_pii(text: str, pii_mapping: dict) -> str:
    """Restore PII placeholders with original values for customer-facing response."""
    restored = text
    for placeholder, original in pii_mapping.items():
        restored = restored.replace(placeholder, original)
    return restored
