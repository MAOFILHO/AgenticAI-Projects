import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_get_live_tracking_ws_success(websocket_server, orders_db):
    from shopsmart.protocols.websocket_client import get_live_tracking_ws

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        order_id = next(iter(orders_db))
        result = get_live_tracking_ws(order_id)
        assert result["order_id"] == order_id
        assert result["live"] is True
        assert metrics.protocol_stats["WS"]["call_count"] == 1
    finally:
        set_active_metrics(None)


def test_get_live_tracking_ws_not_found(websocket_server):
    from shopsmart.protocols.websocket_client import get_live_tracking_ws

    with pytest.raises(Exception):
        get_live_tracking_ws("ORD-NONEXISTENT")


def test_fault_mode_timeout(websocket_server, orders_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.websocket_client import get_live_tracking_ws

    os.environ["FAULT_MODE_WS"] = "timeout"
    os.environ["WS_TIMEOUT_S"] = "0.1"
    os.environ["WS_MAX_RETRIES"] = "0"
    try:
        order_id = next(iter(orders_db))
        with pytest.raises(ProtocolFault):
            get_live_tracking_ws(order_id)
    finally:
        os.environ.pop("FAULT_MODE_WS", None)
        os.environ.pop("WS_TIMEOUT_S", None)
        os.environ.pop("WS_MAX_RETRIES", None)
