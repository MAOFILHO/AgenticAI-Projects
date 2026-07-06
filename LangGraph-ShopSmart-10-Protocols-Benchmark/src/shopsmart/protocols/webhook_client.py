"""Webhook client that dispatches shipping-update events to the local
webhook receiver (webhook_server.py) and waits for a signed 202 ack.

Wrapped with the shared fault-injection + timing/tracing seam so this
protocol is measured identically to REST, GraphQL, and gRPC.
"""

import hashlib
import hmac
import json

import httpx

from shopsmart.config import get_timeout_s, get_webhook_url
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_SECRET = b"shopsmart-webhook-shared-secret"
_fault = FaultInjector("WEBHOOK")


def _sign(body: bytes) -> str:
    return hmac.new(_SECRET, body, hashlib.sha256).hexdigest()


@timed_protocol_call("WEBHOOK")
def notify_shipping_partner_webhook(order_id: str, event: str) -> dict:
    """Push a shipping-exception/return-pickup event to the shipping partner webhook."""
    _fault.maybe_inject_pre_call()

    url = get_webhook_url()
    timeout = get_timeout_s("WEBHOOK")
    body = json.dumps({"order_id": order_id, "event": event}).encode()
    signature = _sign(body)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            content=body,
            headers={"Content-Type": "application/json", "X-Signature": signature},
        )
        response.raise_for_status()
        payload = response.json()

    return _fault.maybe_inject_post_call(payload)
