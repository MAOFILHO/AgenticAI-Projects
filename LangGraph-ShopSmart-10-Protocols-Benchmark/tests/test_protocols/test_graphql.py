import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_search_products_graphql_success(graphql_server, products_db):
    from shopsmart.protocols.graphql_client import search_products_graphql

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        sample = next(iter(products_db.values()))
        result = search_products_graphql(sample["category"])
        assert result["results_count"] >= 1
        assert metrics.protocol_stats["GRAPHQL"]["call_count"] == 1
    finally:
        set_active_metrics(None)


def test_search_products_graphql_no_match(graphql_server):
    from shopsmart.protocols.graphql_client import search_products_graphql

    result = search_products_graphql("zzz_no_such_product_zzz")
    assert result["results_count"] == 0


def test_fault_mode_malformed(graphql_server, products_db):
    from shopsmart.protocols.graphql_client import search_products_graphql

    os.environ["FAULT_MODE_GRAPHQL"] = "malformed"
    try:
        sample = next(iter(products_db.values()))
        result = search_products_graphql(sample["category"])
        assert "malformed" in result
    finally:
        os.environ.pop("FAULT_MODE_GRAPHQL", None)
