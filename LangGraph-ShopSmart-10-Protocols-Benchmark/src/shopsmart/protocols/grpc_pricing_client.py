"""gRPC client for the local Pricing Service (grpc_pricing_server.py).

Wrapped with the shared fault-injection + timing/tracing seam so this
protocol is measured identically to REST, GraphQL, and the rest.
"""

import grpc

from shopsmart.config import get_grpc_pricing_addr, get_timeout_s
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call
from shopsmart.protocols import grpc_pricing_pb2, grpc_pricing_pb2_grpc

_fault = FaultInjector("GRPC")


@timed_protocol_call("GRPC")
def get_price_grpc(product_id: str) -> dict:
    """Get current pricing for a product via the gRPC Pricing Service."""
    _fault.maybe_inject_pre_call()

    addr = get_grpc_pricing_addr()
    timeout = get_timeout_s("GRPC")
    with grpc.insecure_channel(addr) as channel:
        stub = grpc_pricing_pb2_grpc.PricingServiceStub(channel)
        request = grpc_pricing_pb2.PriceRequest(product_id=product_id)
        try:
            response = stub.GetPrice(request, timeout=timeout)
        except grpc.RpcError as exc:
            payload = {"error": f"gRPC error: {exc.details() if hasattr(exc, 'details') else exc}"}
            return _fault.maybe_inject_post_call(payload)

    payload = {
        "product_id": response.product_id,
        "price": response.price,
        "currency": response.currency,
        "stock_status": response.stock_status,
    }
    return _fault.maybe_inject_post_call(payload)
