import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_notify_shipping_partner_webhook_success(webhook_server, orders_db):
    from shopsmart.protocols.webhook_client import notify_shipping_partner_webhook

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        order_id = next(iter(orders_db))
        result = notify_shipping_partner_webhook(order_id, "return_pickup_requested")
        assert result["status"] == "accepted"
        assert "receipt_id" in result
        assert metrics.protocol_stats["WEBHOOK"]["call_count"] == 1
        assert metrics.protocol_stats["WEBHOOK"]["error_rate"] == 0.0
    finally:
        set_active_metrics(None)


def test_fault_mode_error_returns_degraded_payload(webhook_server, orders_db):
    from shopsmart.protocols.webhook_client import notify_shipping_partner_webhook

    os.environ["FAULT_MODE_WEBHOOK"] = "error"
    try:
        order_id = next(iter(orders_db))
        result = notify_shipping_partner_webhook(order_id, "return_pickup_requested")
        assert "error" in result
    finally:
        os.environ.pop("FAULT_MODE_WEBHOOK", None)


def test_fault_mode_refused_raises(webhook_server, orders_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.webhook_client import notify_shipping_partner_webhook

    os.environ["FAULT_MODE_WEBHOOK"] = "refused"
    os.environ["WEBHOOK_MAX_RETRIES"] = "0"
    try:
        order_id = next(iter(orders_db))
        with pytest.raises(ProtocolFault):
            notify_shipping_partner_webhook(order_id, "return_pickup_requested")
    finally:
        os.environ.pop("FAULT_MODE_WEBHOOK", None)
        os.environ.pop("WEBHOOK_MAX_RETRIES", None)
