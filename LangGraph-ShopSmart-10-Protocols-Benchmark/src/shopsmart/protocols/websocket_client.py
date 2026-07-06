"""WebSocket client for the local Live Tracking service (websocket_server.py).

Opens a connection, sends one request, reads one live update, closes —
mirrors how an agent would pull a live status mid-task rather than holding
a long-lived subscription open.
"""

import json

import websockets
import websockets.sync.client

from shopsmart.config import get_timeout_s, get_ws_tracking_url
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_fault = FaultInjector("WS")


@timed_protocol_call("WS")
def get_live_tracking_ws(order_id: str) -> dict:
    """Fetch a live tracking update over WebSocket."""
    _fault.maybe_inject_pre_call()

    url = get_ws_tracking_url()
    timeout = get_timeout_s("WS")

    with websockets.sync.client.connect(url, open_timeout=timeout, close_timeout=timeout) as ws:
        ws.send(json.dumps({"order_id": order_id}))
        raw = ws.recv(timeout=timeout)
        payload = json.loads(raw)

    if "error" in payload:
        raise RuntimeError(payload["error"])

    return _fault.maybe_inject_post_call(payload)
