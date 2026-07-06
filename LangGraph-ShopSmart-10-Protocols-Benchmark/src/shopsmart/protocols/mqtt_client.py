"""MQTT client implementing a request/reply pattern against the local
Warehouse Inventory responder (mqtt_responder.py), via a Mosquitto broker.

Publishes a stock-check request with a correlation id, subscribes to the
matching per-request response topic, and waits for the reply — this is how
a real warehouse pub/sub integration typically layers synchronous RPC-style
calls on top of MQTT for use inside a request/response tool-calling loop.
"""

import json
import threading
import uuid

import paho.mqtt.client as mqtt

from shopsmart.config import get_mqtt_broker_host, get_mqtt_broker_port, get_timeout_s
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_fault = FaultInjector("MQTT")


@timed_protocol_call("MQTT")
def check_stock_alert_mqtt(product_id: str) -> dict:
    """Check live stock status via the MQTT warehouse inventory responder."""
    _fault.maybe_inject_pre_call()

    correlation_id = str(uuid.uuid4())
    response_topic = f"shopsmart/stock/response/{correlation_id}"
    timeout = get_timeout_s("MQTT")

    result_holder: dict = {}
    received = threading.Event()

    def _on_message(client, userdata, msg):
        result_holder["payload"] = json.loads(msg.payload)
        received.set()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = _on_message
    client.connect(get_mqtt_broker_host(), get_mqtt_broker_port())
    client.subscribe(response_topic)
    client.loop_start()

    try:
        client.publish(
            "shopsmart/stock/request",
            json.dumps({"product_id": product_id, "correlation_id": correlation_id}),
        )
        if not received.wait(timeout=timeout):
            raise TimeoutError(f"MQTT stock check for {product_id} timed out after {timeout}s")
    finally:
        client.loop_stop()
        client.disconnect()

    payload = result_holder["payload"]
    if "error" in payload:
        raise RuntimeError(payload["error"])

    return _fault.maybe_inject_post_call(payload)
