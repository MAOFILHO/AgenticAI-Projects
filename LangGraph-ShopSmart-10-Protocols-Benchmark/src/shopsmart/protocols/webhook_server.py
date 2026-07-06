"""Local 'Shipping Partner' webhook receiver — run as a subprocess.

`POST /webhook/shipping-update` mimics an external shipping partner
acknowledging a delivery-exception notification pushed by the returns
specialist. Real webhook receivers validate a signature header and reply
202 with a delivery receipt id — this stand-in does the same.

Run standalone: `python -m shopsmart.protocols.webhook_server`
"""

import hashlib
import hmac
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="ShopSmart Webhook Receiver (Shipping Partner)")

_SECRET = b"shopsmart-webhook-shared-secret"
_received: list[dict] = []


def _sign(body: bytes) -> str:
    return hmac.new(_SECRET, body, hashlib.sha256).hexdigest()


@app.get("/health")
def health():
    return {"status": "ok", "service": "webhook-receiver"}


@app.post("/webhook/shipping-update")
async def receive_shipping_update(request: Request, x_signature: str = Header(default="")):
    body = await request.body()
    expected = _sign(body)
    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()
    receipt = {
        "receipt_id": str(uuid.uuid4()),
        "order_id": payload.get("order_id"),
        "event": payload.get("event"),
        "received_at": time.time(),
    }
    _received.append(receipt)
    return {"status": "accepted", "receipt_id": receipt["receipt_id"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8004)
