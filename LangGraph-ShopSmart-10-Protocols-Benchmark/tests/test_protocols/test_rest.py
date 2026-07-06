import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_lookup_order_rest_success(rest_server, orders_db):
    from shopsmart.protocols.rest_client import lookup_order_rest

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        order_id = next(iter(orders_db))
        result = lookup_order_rest(order_id)
        assert result["order_id"] == order_id
        assert metrics.protocol_stats["REST"]["call_count"] == 1
        assert metrics.protocol_stats["REST"]["error_rate"] == 0.0
    finally:
        set_active_metrics(None)


def test_lookup_order_rest_not_found(rest_server):
    from shopsmart.protocols.rest_client import lookup_order_rest

    with pytest.raises(Exception):
        lookup_order_rest("ORD-NONEXISTENT")


def test_fault_mode_error_returns_degraded_payload(rest_server, orders_db):
    from shopsmart.protocols.rest_client import lookup_order_rest

    os.environ["FAULT_MODE_REST"] = "error"
    try:
        order_id = next(iter(orders_db))
        result = lookup_order_rest(order_id)
        assert "error" in result
    finally:
        os.environ.pop("FAULT_MODE_REST", None)


def test_fault_mode_refused_raises(rest_server, orders_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.rest_client import lookup_order_rest

    os.environ["FAULT_MODE_REST"] = "refused"
    os.environ["REST_MAX_RETRIES"] = "0"
    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        order_id = next(iter(orders_db))
        with pytest.raises(ProtocolFault):
            lookup_order_rest(order_id)
        assert metrics.protocol_stats["REST"]["error_rate"] == 100.0
    finally:
        os.environ.pop("FAULT_MODE_REST", None)
        os.environ.pop("REST_MAX_RETRIES", None)
        set_active_metrics(None)
