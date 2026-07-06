"""Bridges the existing in-process MCP tool path into the same benchmark
seam used by REST/GraphQL/gRPC/etc., so MCP gets a comparable row in
`metrics.protocol_stats`.

MCP tools in this project are already in-process function calls (see
mcp_client.py's `StructuredTool.from_function` bridging) rather than a
real over-the-wire transport, so "latency" here measures call/dispatch
overhead rather than network I/O — that asymmetry is itself one of the
things the benchmark surfaces when comparing all 10 protocols side by side.
"""

from shopsmart.config import get_data_dir
from shopsmart.data_loader import load_all
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_fault = FaultInjector("MCP")
_customers_db: dict = {}


def _ensure_loaded():
    global _customers_db
    if not _customers_db:
        data = load_all(get_data_dir())
        _customers_db = data["customers_db"]


@timed_protocol_call("MCP")
def lookup_customer_via_mcp_benchmark(customer_id: str) -> dict:
    """Look up a customer via the same in-process MCP dispatch path as
    lookup_customer, instrumented for the protocol benchmark."""
    _fault.maybe_inject_pre_call()
    _ensure_loaded()

    c = _customers_db.get(customer_id)
    if c is None:
        payload = {"error": f"Customer {customer_id} not found"}
    else:
        payload = {
            "customer_id": c["customer_id"],
            "tier": c["tier"],
            "join_date": c["join_date"],
            "past_tickets_count": c["past_tickets_count"],
        }

    return _fault.maybe_inject_post_call(payload)
