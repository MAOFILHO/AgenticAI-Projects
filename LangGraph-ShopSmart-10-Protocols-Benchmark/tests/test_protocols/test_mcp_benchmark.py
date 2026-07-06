import os

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_lookup_customer_via_mcp_benchmark_success(customers_db):
    from shopsmart.protocols.mcp_bridge import lookup_customer_via_mcp_benchmark

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        customer_id = next(iter(customers_db))
        result = lookup_customer_via_mcp_benchmark(customer_id)
        assert result["customer_id"] == customer_id
        assert metrics.protocol_stats["MCP"]["call_count"] == 1
        assert metrics.protocol_stats["MCP"]["error_rate"] == 0.0
    finally:
        set_active_metrics(None)


def test_lookup_customer_via_mcp_benchmark_not_found():
    from shopsmart.protocols.mcp_bridge import lookup_customer_via_mcp_benchmark

    result = lookup_customer_via_mcp_benchmark("CUST-NONEXISTENT")
    assert "error" in result


def test_fault_mode_error_returns_degraded_payload(customers_db):
    from shopsmart.protocols.mcp_bridge import lookup_customer_via_mcp_benchmark

    os.environ["FAULT_MODE_MCP"] = "error"
    try:
        customer_id = next(iter(customers_db))
        result = lookup_customer_via_mcp_benchmark(customer_id)
        assert "error" in result
    finally:
        os.environ.pop("FAULT_MODE_MCP", None)
