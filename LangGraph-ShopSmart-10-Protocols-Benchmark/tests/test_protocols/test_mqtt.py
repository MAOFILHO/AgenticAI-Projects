import os

import pytest

from shopsmart.metrics import SystemMetrics
from shopsmart.protocol_timing import set_active_metrics


def test_check_stock_alert_mqtt_success(mqtt_responder, products_db):
    from shopsmart.protocols.mqtt_client import check_stock_alert_mqtt

    metrics = SystemMetrics()
    set_active_metrics(metrics)
    try:
        product_id = next(iter(products_db))
        result = check_stock_alert_mqtt(product_id)
        assert result["product_id"] == product_id
        assert "stock_status" in result
        assert metrics.protocol_stats["MQTT"]["call_count"] == 1
    finally:
        set_active_metrics(None)


def test_check_stock_alert_mqtt_not_found(mqtt_responder):
    from shopsmart.protocols.mqtt_client import check_stock_alert_mqtt

    with pytest.raises(Exception):
        check_stock_alert_mqtt("PROD-NONEXISTENT")


def test_fault_mode_timeout(mqtt_responder, products_db):
    from shopsmart.fault_injector import ProtocolFault
    from shopsmart.protocols.mqtt_client import check_stock_alert_mqtt

    os.environ["FAULT_MODE_MQTT"] = "timeout"
    os.environ["MQTT_TIMEOUT_S"] = "0.1"
    os.environ["MQTT_MAX_RETRIES"] = "0"
    try:
        product_id = next(iter(products_db))
        with pytest.raises(ProtocolFault):
            check_stock_alert_mqtt(product_id)
    finally:
        os.environ.pop("FAULT_MODE_MQTT", None)
        os.environ.pop("MQTT_TIMEOUT_S", None)
        os.environ.pop("MQTT_MAX_RETRIES", None)
