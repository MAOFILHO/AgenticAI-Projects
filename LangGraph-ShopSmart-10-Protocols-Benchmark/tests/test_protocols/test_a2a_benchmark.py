from tests.conftest import requires_openai


@requires_openai
def test_lookup_order_via_a2a_success(orders_db):
    """End-to-end: builds the real system so order_specialist is registered
    with the A2A client, then delegates an order lookup to it via A2A."""
    from shopsmart.graph import build_system
    from shopsmart.metrics import SystemMetrics
    from shopsmart.protocol_timing import set_active_metrics
    from shopsmart.protocols.a2a_bridge import lookup_order_via_a2a

    build_system()  # wires the module-level A2A client + metrics as a side effect

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        order_id = next(iter(orders_db))
        result = lookup_order_via_a2a(order_id)
        assert result["order_id"] == order_id
        assert result["status"] == "completed"
        assert metrics.protocol_stats["A2A"]["call_count"] == 1
    finally:
        set_active_metrics(None)
