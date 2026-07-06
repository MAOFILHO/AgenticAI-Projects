"""REST client for the local Order Status Service (rest_server.py).

Wrapped with the shared fault-injection + timing/tracing seam so this
protocol is measured identically to GraphQL, gRPC, and the rest.
"""

import httpx

from shopsmart.config import get_rest_base_url, get_timeout_s
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_fault = FaultInjector("REST")


@timed_protocol_call("REST")
def lookup_order_rest(order_id: str) -> dict:
    """Look up an order via the REST Order Status Service."""
    _fault.maybe_inject_pre_call()

    base_url = get_rest_base_url()
    timeout = get_timeout_s("REST")
    with httpx.Client(timeout=timeout) as client:
        response = client.get(f"{base_url}/orders/{order_id}")
        response.raise_for_status()
        payload = response.json()

    return _fault.maybe_inject_post_call(payload)
