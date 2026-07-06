"""AMQP client implementing the RabbitMQ RPC pattern against the local
Fraud/Audit responder (amqp_responder.py).

Declares an exclusive reply-to queue, publishes the audit request with a
correlation id, and blocks (via `connection.process_data_events`) until the
correlated reply arrives or the timeout elapses.
"""

import json
import logging
import uuid

import pika

from shopsmart.config import get_amqp_url, get_timeout_s
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

logging.getLogger("pika").setLevel(logging.WARNING)

REQUEST_QUEUE = "shopsmart.billing.audit.requests"

_fault = FaultInjector("AMQP")


@timed_protocol_call("AMQP")
def audit_customer_billing_amqp(customer_id: str) -> dict:
    """Run a billing fraud/audit risk check via AMQP RPC."""
    _fault.maybe_inject_pre_call()

    timeout = get_timeout_s("AMQP")
    connection = pika.BlockingConnection(pika.URLParameters(get_amqp_url()))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=REQUEST_QUEUE)
        reply_queue = channel.queue_declare(queue="", exclusive=True).method.queue

        correlation_id = str(uuid.uuid4())
        response_holder: dict = {}

        def _on_response(ch, method, properties, body):
            if properties.correlation_id == correlation_id:
                response_holder["payload"] = json.loads(body)

        channel.basic_consume(queue=reply_queue, on_message_callback=_on_response, auto_ack=True)
        channel.basic_publish(
            exchange="",
            routing_key=REQUEST_QUEUE,
            properties=pika.BasicProperties(reply_to=reply_queue, correlation_id=correlation_id),
            body=json.dumps({"customer_id": customer_id}),
        )

        connection.process_data_events(time_limit=timeout)
        if "payload" not in response_holder:
            raise TimeoutError(f"AMQP billing audit for {customer_id} timed out after {timeout}s")
    finally:
        connection.close()

    payload = response_holder["payload"]
    if "error" in payload:
        raise RuntimeError(payload["error"])

    return _fault.maybe_inject_post_call(payload)
