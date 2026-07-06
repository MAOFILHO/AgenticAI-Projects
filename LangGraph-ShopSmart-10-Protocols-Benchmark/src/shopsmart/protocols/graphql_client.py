"""GraphQL client for the local Product Catalog service (graphql_server.py).

Wrapped with the shared fault-injection + timing/tracing seam so this
protocol is measured identically to REST, gRPC, and the rest.
"""

import httpx

from shopsmart.config import get_graphql_url, get_timeout_s
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_fault = FaultInjector("GRAPHQL")

_QUERY = """
query Products($query: String!) {
  products(query: $query) {
    productId
    name
    category
    price
    stockStatus
  }
}
"""


@timed_protocol_call("GRAPHQL")
def search_products_graphql(query: str) -> dict:
    """Search products via the GraphQL Product Catalog service."""
    _fault.maybe_inject_pre_call()

    url = get_graphql_url()
    timeout = get_timeout_s("GRAPHQL")
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json={"query": _QUERY, "variables": {"query": query}})
        response.raise_for_status()
        body = response.json()

    if "errors" in body and body["errors"]:
        payload = {"error": body["errors"][0].get("message", "GraphQL error")}
    else:
        results = body["data"]["products"]
        payload = {"query": query, "results_count": len(results), "results": results}

    return _fault.maybe_inject_post_call(payload)
