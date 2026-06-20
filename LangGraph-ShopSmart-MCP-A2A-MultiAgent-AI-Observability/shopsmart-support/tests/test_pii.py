"""PII redaction and restoration tests."""

from shopsmart.pii import build_known_names, redact_pii, restore_pii


def test_email_redaction(customers_db, known_names):
    text = "Hi, my email is john@example.com and I need help."
    redacted, mapping = redact_pii(text, None, customers_db, known_names)
    assert "john@example.com" not in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert mapping["[EMAIL_REDACTED]"] == "john@example.com"


def test_phone_redaction(customers_db, known_names):
    text = "Call me at 555-123-4567 please."
    redacted, mapping = redact_pii(text, None, customers_db, known_names)
    assert "555-123-4567" not in redacted
    assert "[PHONE_REDACTED]" in redacted


def test_name_redaction(customers_db, known_names):
    name = next(iter(known_names))
    text = f"Hi, I'm {name} and I need help."
    redacted, mapping = redact_pii(text, None, customers_db, known_names)
    assert name not in redacted
    assert "[NAME_REDACTED]" in redacted


def test_restore_pii():
    pii_mapping = {
        "[EMAIL_REDACTED]": "john@example.com",
        "[NAME_REDACTED]": "John Smith",
    }
    text = "Dear [NAME_REDACTED], we'll contact you at [EMAIL_REDACTED]."
    restored = restore_pii(text, pii_mapping)
    assert "John Smith" in restored
    assert "john@example.com" in restored
    assert "[EMAIL_REDACTED]" not in restored


def test_roundtrip(customers_db, known_names):
    original = "Hi, I'm John Smith. My email is john.smith@email.com. Call me at 555-754-2824."
    redacted, mapping = redact_pii(original, "CUST-0001", customers_db, known_names)
    restored = restore_pii(redacted, mapping)
    for value in mapping.values():
        assert value in restored


def test_no_pii_in_text(customers_db, known_names):
    text = "What is the status of order ORD-00001?"
    redacted, mapping = redact_pii(text, None, customers_db, known_names)
    assert redacted == text
    assert len(mapping) == 0


def test_build_known_names(customers_db):
    full, first, last = build_known_names(customers_db)
    assert len(full) > 0
    assert len(first) > 0
    assert len(last) > 0
