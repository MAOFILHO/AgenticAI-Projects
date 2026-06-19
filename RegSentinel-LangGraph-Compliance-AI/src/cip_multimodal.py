"""Task 5 (Stretch) — Multimodal CIP: vision-based business-registration KYC extraction."""
import base64
import io
import json

from langchain_core.messages import HumanMessage
from PIL import Image, ImageDraw


# ── Synthetic document generator (provided) ────────────────────────────────────
def make_fake_registration(
    name: str = "Coastal Imports LLC",
    ein: str = "12-3456789",
    state: str = "MA",
    reg_no: str = "MA-LLC-884213",
) -> Image.Image:
    """Generate a synthetic business-registration scan for testing."""
    img = Image.new("RGB", (640, 360), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((8, 8, 632, 352), outline="black", width=2)
    lines = [
        "STATE OF MASSACHUSETTS",
        "CERTIFICATE OF ORGANIZATION",
        "",
        f"Entity Name : {name}",
        "Entity Type : Limited Liability Company",
        f"EIN         : {ein}",
        f"Reg. Number : {reg_no}",
        f"Jurisdiction: {state}",
        "Status      : ACTIVE",
    ]
    for i, ln in enumerate(lines):
        d.text((28, 30 + i * 34), ln, fill="black")
    return img


def img_to_b64(img: Image.Image) -> str:
    """Encode a PIL image as a base64 PNG string."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Vision extraction ──────────────────────────────────────────────────────────
def cip_extract_from_image(b64png: str, llm=None) -> str:
    """Run the vision model over a KYC/registration scan and extract CIP fields as JSON."""
    if llm is None:
        from src.nodes import llm as _llm
        llm = _llm

    prompt = (
        "Analyze the provided business-registration document scan. "
        "Extract the metadata fields and compile them into a raw JSON object. "
        "Do not include any introductory commentary or markdown blocks.\n\n"
        "Use this exact JSON structure:\n"
        "{\n"
        '  "entity_name": "string",\n'
        '  "entity_type": "string",\n'
        '  "ein": "string",\n'
        '  "registration_number": "string",\n'
        '  "jurisdiction": "string",\n'
        '  "status": "string"\n'
        "}"
    )

    message = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64png}"}},
    ])

    try:
        response = llm.invoke([message])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines() if not line.strip().startswith("```")
            ).strip()
        return json.dumps(json.loads(raw), indent=2)
    except Exception as e:
        return json.dumps({"error": f"Extraction failed: {e}"})


def verify_cip(customer_id: str, extracted_json_str: str, customers: dict) -> str:
    """Cross-check extracted CIP data against the customer ledger."""
    try:
        extracted = json.loads(extracted_json_str)
        customer = customers.get(customer_id)
        if not customer:
            return f"Customer {customer_id} not found in ledger."
        if customer.get("ein") == extracted.get("ein"):
            return f"✓ CIP Verification Successful for {customer_id}."
        return f"✗ CIP Verification Failed: EIN mismatch for {customer_id}."
    except Exception as e:
        return f"Verification error: {e}"
