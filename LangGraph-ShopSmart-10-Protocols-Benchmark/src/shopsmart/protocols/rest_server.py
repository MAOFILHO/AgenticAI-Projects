"""Local REST 'Order Status Service' stand-in — run as a subprocess.

`GET /orders/{order_id}` mirrors mcp_server.lookup_order, backed by the
same orders.json dataset, so the REST protocol does real work comparable
to the existing MCP tool.

Run standalone: `python -m shopsmart.protocols.rest_server`
"""

from fastapi import FastAPI, HTTPException

from shopsmart.config import get_data_dir
from shopsmart.data_loader import load_all

app = FastAPI(title="ShopSmart REST Order Service")
_orders_db: dict = {}


@app.on_event("startup")
def _load_data():
    global _orders_db
    data = load_all(get_data_dir())
    _orders_db = data["orders_db"]


@app.get("/health")
def health():
    return {"status": "ok", "service": "rest-order-service"}


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    if order_id not in _orders_db:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    o = _orders_db[order_id]
    return {
        "order_id": o["order_id"],
        "customer_id": o["customer_id"],
        "order_date": o["order_date"],
        "items": [
            {"name": item["name"], "quantity": item["quantity"], "price": item["price"]}
            for item in o["items"]
        ],
        "total": o["total"],
        "status": o["status"],
        "tracking_number": o["tracking_number"],
        "estimated_delivery": o["estimated_delivery"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
