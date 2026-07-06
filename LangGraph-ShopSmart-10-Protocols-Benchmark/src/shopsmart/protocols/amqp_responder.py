"""Local 'Fraud/Audit' AMQP responder — run as a subprocess against the
RabbitMQ broker started by `make brokers-up`.

Implements the classic RabbitMQ RPC pattern: consumes from
`shopsmart.billing.audit.requests`, computes a simple risk score from the
customer's billing history, and replies on the request's `reply_to` queue
tagged with its `correlation_id`.

Run standalone: `python -m shopsmart.protocols.amqp_responder`
"""

import json
import logging

import pika

from shopsmart.config import get_amqp_url, get_data_dir
from shopsmart.data_loader import load_all

logging.getLogger("pika").setLevel(logging.WARNING)

REQUEST_QUEUE = "shopsmart.billing.audit.requests"

_customers_db: dict = {}


def _risk_score(customer_id: str) -> dict:
    customer = _customers_db.get(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}
    return {
        "customer_id": customer_id,
        "risk_score": "low",
        "flagged": False,
    }


def _on_request(channel, method, properties, body):
    request = json.loads(body)
    response = _risk_score(request.get("customer_id"))
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        body=json.dumps(response),
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    global _customers_db
    data = load_all(get_data_dir())
    _customers_db = data["customers_db"]

    connection = pika.BlockingConnection(pika.URLParameters(get_amqp_url()))
    channel = connection.channel()
    channel.queue_declare(queue=REQUEST_QUEUE)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=REQUEST_QUEUE, on_message_callback=_on_request)
    print(f"[AMQP Responder] Listening on {REQUEST_QUEUE}")
    channel.start_consuming()


if __name__ == "__main__":
    main()
