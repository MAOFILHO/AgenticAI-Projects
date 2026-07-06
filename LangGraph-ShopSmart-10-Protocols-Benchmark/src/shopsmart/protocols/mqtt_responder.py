"""Local 'Warehouse Inventory' MQTT responder — run as a subprocess against
the Mosquitto broker started by `make brokers-up`.

Subscribes to `shopsmart/stock/request`, looks up live stock status for the
requested product, and publishes the reply to
`shopsmart/stock/response/{correlation_id}` — a request/reply pattern layered
on top of MQTT's pub/sub, mirroring how a real warehouse inventory system
would push stock alerts.

Run standalone: `python -m shopsmart.protocols.mqtt_responder`
"""

import json

import paho.mqtt.client as mqtt

from shopsmart.config import get_data_dir, get_mqtt_broker_host, get_mqtt_broker_port
from shopsmart.data_loader import load_all

_products_db: dict = {}

REQUEST_TOPIC = "shopsmart/stock/request"


def _on_message(client, userdata, msg):
    try:
        request = json.loads(msg.payload)
    except json.JSONDecodeError:
        return

    product_id = request.get("product_id")
    correlation_id = request.get("correlation_id")
    product = _products_db.get(product_id)

    if product is None:
        response = {"error": f"Product {product_id} not found"}
    else:
        response = {
            "product_id": product_id,
            "stock_status": product.get("stock_status", "unknown"),
        }

    client.publish(f"shopsmart/stock/response/{correlation_id}", json.dumps(response))


def main():
    global _products_db
    data = load_all(get_data_dir())
    _products_db = data["products_db"]

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = _on_message
    client.connect(get_mqtt_broker_host(), get_mqtt_broker_port())
    client.subscribe(REQUEST_TOPIC)
    print(f"[MQTT Responder] Listening on {REQUEST_TOPIC}")
    client.loop_forever()


if __name__ == "__main__":
    main()
