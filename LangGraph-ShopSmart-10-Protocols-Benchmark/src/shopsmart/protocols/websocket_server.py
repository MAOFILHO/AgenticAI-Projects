"""Local 'Live Tracking' WebSocket service — run as a subprocess.

A client connects, sends an order_id, and receives one live tracking
status message back (mirrors a carrier's real-time tracking push feed).

Run standalone: `python -m shopsmart.protocols.websocket_server`
"""

import asyncio
import json

import websockets

from shopsmart.config import get_data_dir
from shopsmart.data_loader import load_all

_orders_db: dict = {}


async def _handler(websocket):
    async for message in websocket:
        try:
            request = json.loads(message)
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"error": "invalid request"}))
            continue

        order_id = request.get("order_id")
        order = _orders_db.get(order_id)
        if order is None:
            await websocket.send(json.dumps({"error": f"Order {order_id} not found"}))
            continue

        await websocket.send(
            json.dumps(
                {
                    "order_id": order_id,
                    "status": order["status"],
                    "tracking_number": order["tracking_number"],
                    "estimated_delivery": order["estimated_delivery"],
                    "live": True,
                }
            )
        )


async def _serve():
    global _orders_db
    data = load_all(get_data_dir())
    _orders_db = data["orders_db"]
    async with websockets.serve(_handler, "127.0.0.1", 8005):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(_serve())
