"""Local gRPC 'Pricing Service' stand-in — run as a subprocess.

`GetPrice(product_id)` mirrors part of mcp_server.lookup_product (price +
stock status), backed by the same products.json dataset, so gRPC does real
work comparable to the existing MCP tool.

Run standalone: `python -m shopsmart.protocols.grpc_pricing_server`
"""

from concurrent import futures

import grpc

from shopsmart.config import get_data_dir, get_grpc_pricing_addr
from shopsmart.data_loader import load_all
from shopsmart.protocols import grpc_pricing_pb2, grpc_pricing_pb2_grpc

_products_db: dict = {}


class PricingServicer(grpc_pricing_pb2_grpc.PricingServiceServicer):
    def GetPrice(self, request, context):
        product = _products_db.get(request.product_id)
        if product is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Product {request.product_id} not found")
            return grpc_pricing_pb2.PriceResponse()

        return grpc_pricing_pb2.PriceResponse(
            product_id=product["product_id"],
            price=product["price"],
            currency="USD",
            stock_status=product["stock_status"],
        )


def serve():
    global _products_db
    data = load_all(get_data_dir())
    _products_db = data["products_db"]

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    grpc_pricing_pb2_grpc.add_PricingServiceServicer_to_server(PricingServicer(), server)
    addr = get_grpc_pricing_addr()
    server.add_insecure_port(addr)
    server.start()
    print(f"[gRPC] Pricing Service listening on {addr}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
