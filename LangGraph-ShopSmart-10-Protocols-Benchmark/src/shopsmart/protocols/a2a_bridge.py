"""Bridges the A2A protocol (a2a.py) into the same benchmark seam used by
every other protocol client, so an A2A handler-to-handler delegation shows
up as a row in `metrics.protocol_stats` next to REST/GraphQL/gRPC/etc.

Specialist agents are built before `setup_a2a()` creates the `A2AClient`
(the client needs the already-built specialists to register their A2A
servers), so — like `protocol_timing.set_active_metrics` — the client is
stored in a module-level reference set at runtime, not at tool-decoration
time.
"""

from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_active_a2a_client = None
_fault = FaultInjector("A2A")


def set_active_a2a_client(client) -> None:
    global _active_a2a_client
    _active_a2a_client = client


@timed_protocol_call("A2A")
def lookup_order_via_a2a(order_id: str) -> dict:
    """Delegate an order lookup to order_specialist via an A2A Task, instead
    of calling an order-lookup tool directly. Mirrors real handler-to-handler
    delegation (e.g. returns/billing needing order data)."""
    _fault.maybe_inject_pre_call()

    if _active_a2a_client is None:
        raise RuntimeError("A2A client not initialized — call set_active_a2a_client() first")

    task = _active_a2a_client.send_task("order_specialist", f"Look up order {order_id}")
    if task is None:
        raise RuntimeError("order_specialist not registered with the A2A client")
    if task.status.value == "failed":
        raise RuntimeError(task.output.parts[0].text if task.output else "A2A task failed")

    payload = {
        "order_id": order_id,
        "task_id": task.id,
        "status": task.status.value,
        "result": task.output.parts[0].text if task.output else None,
    }
    return _fault.maybe_inject_post_call(payload)
