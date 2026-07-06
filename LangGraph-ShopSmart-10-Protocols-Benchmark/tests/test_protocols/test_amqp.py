import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_audit_customer_billing_amqp_success(amqp_responder, customers_db):
    from shopsmart.protocols.amqp_client import audit_customer_billing_amqp

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        customer_id = next(iter(customers_db))
        result = audit_customer_billing_amqp(customer_id)
        assert result["customer_id"] == customer_id
        assert "risk_score" in result
        assert metrics.protocol_stats["AMQP"]["call_count"] == 1
    finally:
        set_active_metrics(None)


def test_audit_customer_billing_amqp_not_found(amqp_responder):
    from shopsmart.protocols.amqp_client import audit_customer_billing_amqp

    with pytest.raises(Exception):
        audit_customer_billing_amqp("CUST-NONEXISTENT")


def test_fault_mode_refused_raises(amqp_responder, customers_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.amqp_client import audit_customer_billing_amqp

    os.environ["FAULT_MODE_AMQP"] = "refused"
    try:
        customer_id = next(iter(customers_db))
        with pytest.raises(ProtocolFault):
            audit_customer_billing_amqp(customer_id)
    finally:
        os.environ.pop("FAULT_MODE_AMQP", None)
