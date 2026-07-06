"""Local 'Legacy ERP' SOAP stand-in — run as a subprocess.

Hand-rolled SOAP 1.1 over HTTP (envelope in, envelope out) rather than a
full WSDL toolchain, since the only real requirement for the benchmark is
that the wire format and parsing overhead look like a legacy XML/SOAP
integration, not a modern JSON API.

`POST /soap` with SOAPAction `GetLegacySkuInfo` returns a legacy SKU code,
warehouse location, and unit cost for a product — the kind of lookup a
real ERP system exposes over SOAP.

Run standalone: `python -m shopsmart.protocols.soap_server`
"""

from fastapi import FastAPI, HTTPException, Request, Response
from lxml import etree

from shopsmart.config import get_data_dir
from shopsmart.data_loader import load_all

app = FastAPI(title="ShopSmart Legacy ERP SOAP Service")
_products_db: dict = {}

NS = "http://shopsmart.example.com/erp"


@app.on_event("startup")
def _load_data():
    global _products_db
    data = load_all(get_data_dir())
    _products_db = data["products_db"]


@app.get("/health")
def health():
    return {"status": "ok", "service": "soap-erp-service"}


def _fault_envelope(message: str) -> bytes:
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Server</faultcode>
      <faultstring>{message}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""
    return envelope.encode()


@app.post("/soap")
async def soap_endpoint(request: Request):
    body = await request.body()
    try:
        root = etree.fromstring(body)
    except etree.XMLSyntaxError:
        return Response(content=_fault_envelope("Malformed XML"), media_type="text/xml", status_code=400)

    ns = {"erp": NS, "soap": "http://schemas.xmlsoap.org/soap/envelope/"}
    product_id_el = root.find(".//erp:ProductId", ns)
    if product_id_el is None or product_id_el.text is None:
        return Response(content=_fault_envelope("Missing ProductId"), media_type="text/xml", status_code=400)

    product_id = product_id_el.text
    product = _products_db.get(product_id)
    if product is None:
        return Response(
            content=_fault_envelope(f"Product {product_id} not found"),
            media_type="text/xml",
            status_code=404,
        )

    legacy_sku = f"LEGACY-{product_id.replace('PROD-', '')}"
    response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:erp="{NS}">
  <soap:Body>
    <erp:GetLegacySkuInfoResponse>
      <erp:ProductId>{product_id}</erp:ProductId>
      <erp:LegacySku>{legacy_sku}</erp:LegacySku>
      <erp:WarehouseCode>WH-{(hash(product_id) % 5) + 1}</erp:WarehouseCode>
      <erp:UnitCost>{round(product["price"] * 0.6, 2)}</erp:UnitCost>
    </erp:GetLegacySkuInfoResponse>
  </soap:Body>
</soap:Envelope>"""
    return Response(content=response_xml.encode(), media_type="text/xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8006)
