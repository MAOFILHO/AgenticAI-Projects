import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_get_legacy_sku_info_soap_success(soap_server, products_db):
    from shopsmart.protocols.soap_client import get_legacy_sku_info_soap

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        product_id = next(iter(products_db))
        result = get_legacy_sku_info_soap(product_id)
        assert result["product_id"] == product_id
        assert result["legacy_sku"].startswith("LEGACY-")
        assert metrics.protocol_stats["SOAP"]["call_count"] == 1
    finally:
        set_active_metrics(None)


def test_get_legacy_sku_info_soap_not_found(soap_server):
    from shopsmart.protocols.soap_client import get_legacy_sku_info_soap

    with pytest.raises(Exception):
        get_legacy_sku_info_soap("PROD-NONEXISTENT")


def test_fault_mode_malformed(soap_server, products_db):
    from shopsmart.protocols.soap_client import get_legacy_sku_info_soap

    os.environ["FAULT_MODE_SOAP"] = "malformed"
    try:
        product_id = next(iter(products_db))
        result = get_legacy_sku_info_soap(product_id)
        assert "malformed" in result
    finally:
        os.environ.pop("FAULT_MODE_SOAP", None)


def test_fault_mode_refused_raises(soap_server, products_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.soap_client import get_legacy_sku_info_soap

    os.environ["FAULT_MODE_SOAP"] = "refused"
    try:
        product_id = next(iter(products_db))
        with pytest.raises(ProtocolFault):
            get_legacy_sku_info_soap(product_id)
    finally:
        os.environ.pop("FAULT_MODE_SOAP", None)
