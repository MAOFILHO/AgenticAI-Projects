import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_get_price_grpc_success(grpc_server, products_db):
    from shopsmart.protocols.grpc_pricing_client import get_price_grpc

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        product_id = next(iter(products_db))
        result = get_price_grpc(product_id)
        assert result["product_id"] == product_id
        assert result["currency"] == "USD"
        assert metrics.protocol_stats["GRPC"]["call_count"] == 1
    finally:
        set_active_metrics(None)


def test_get_price_grpc_not_found(grpc_server):
    from shopsmart.protocols.grpc_pricing_client import get_price_grpc

    result = get_price_grpc("NONEXISTENT-SKU")
    assert "error" in result


def test_fault_mode_timeout(grpc_server, products_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.grpc_pricing_client import get_price_grpc

    os.environ["FAULT_MODE_GRPC"] = "timeout"
    os.environ["GRPC_TIMEOUT_S"] = "0.1"
    os.environ["GRPC_MAX_RETRIES"] = "0"
    try:
        product_id = next(iter(products_db))
        with pytest.raises(ProtocolFault):
            get_price_grpc(product_id)
    finally:
        os.environ.pop("FAULT_MODE_GRPC", None)
        os.environ.pop("GRPC_TIMEOUT_S", None)
        os.environ.pop("GRPC_MAX_RETRIES", None)
