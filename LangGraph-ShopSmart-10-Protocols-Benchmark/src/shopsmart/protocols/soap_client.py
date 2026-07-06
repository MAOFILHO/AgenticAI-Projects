"""SOAP client for the local Legacy ERP stand-in (soap_server.py).

Builds a SOAP 1.1 envelope by hand (no WSDL toolchain — see soap_server.py
docstring), POSTs it with a SOAPAction header, and parses the XML response.
This is deliberately more ceremony/overhead than the JSON protocols, which
is itself part of what the benchmark measures for a "legacy" transport.
"""

import httpx
from lxml import etree

from shopsmart.config import get_soap_url, get_timeout_s
from shopsmart.fault_injector import FaultInjector
from shopsmart.protocol_timing import timed_protocol_call

_fault = FaultInjector("SOAP")
NS = "http://shopsmart.example.com/erp"

_REQUEST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:erp="{ns}">
  <soap:Body>
    <erp:GetLegacySkuInfo>
      <erp:ProductId>{product_id}</erp:ProductId>
    </erp:GetLegacySkuInfo>
  </soap:Body>
</soap:Envelope>"""


@timed_protocol_call("SOAP")
def get_legacy_sku_info_soap(product_id: str) -> dict:
    """Look up legacy ERP SKU/warehouse/cost info via SOAP."""
    _fault.maybe_inject_pre_call()

    url = get_soap_url()
    timeout = get_timeout_s("SOAP")
    body = _REQUEST_TEMPLATE.format(ns=NS, product_id=product_id).encode()

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            content=body,
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "GetLegacySkuInfo"},
        )

    root = etree.fromstring(response.content)
    ns = {"soap": "http://schemas.xmlsoap.org/soap/envelope/", "erp": NS}

    fault = root.find(".//soap:Fault/faultstring", ns)
    if fault is not None:
        raise RuntimeError(fault.text)

    payload = {
        "product_id": root.findtext(".//erp:ProductId", namespaces=ns),
        "legacy_sku": root.findtext(".//erp:LegacySku", namespaces=ns),
        "warehouse_code": root.findtext(".//erp:WarehouseCode", namespaces=ns),
        "unit_cost": float(root.findtext(".//erp:UnitCost", namespaces=ns)),
    }

    return _fault.maybe_inject_post_call(payload)
