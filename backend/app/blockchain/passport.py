"""
Blockchain Digital Passport (OUTPUT module 7).

Creates a tamper-evident export passport for a shipment: the shipment record is
validated by the smart-contract gate, written to the hash-chained ledger, and a
QR code (SVG) is generated that encodes a verification payload (passport id +
block hash). Scanning the QR + re-querying the chain proves the record is
authentic and unaltered — the traceability story.

QR generation uses `qrcode`'s SVG factory (no Pillow). If qrcode is unavailable
the passport is still created and recorded; only the QR image is omitted.
"""
from __future__ import annotations

import io
from uuid import uuid4

from . import ledger


def _make_qr_svg(payload: str) -> str | None:
    """Render `payload` as an inline SVG QR code, or None if qrcode is missing."""
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage

        img = qrcode.make(payload, image_factory=SvgPathImage, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode()
    except Exception:
        return None


def _verify_payload(passport_id: str, block_hash: str) -> str:
    return f"teapass://verify?id={passport_id}&hash={block_hash[:16]}"


def create_passport(shipment: dict) -> dict:
    """
    Record a shipment on-chain and return {passport, block, qr_svg, verify_url}.

    `shipment` must include: estate, grade, volume_kg, destination,
    compliance_passed (bool); eri is optional context.
    """
    passport_id = "TEA-" + uuid4().hex[:8].upper()
    data = {
        "type": "export_passport",
        "passport_id": passport_id,
        "estate": shipment.get("estate", "Unknown Estate"),
        "grade": shipment.get("grade", "BOPF"),
        "volume_kg": int(shipment.get("volume_kg", 0)),
        "destination": shipment.get("destination", ""),
        "compliance_passed": bool(shipment.get("compliance_passed", False)),
        "eri": shipment.get("eri"),
        "certifications": shipment.get("certifications", []),
    }

    # Smart-contract gate — raises SmartContractError if the rules are violated.
    ledger.validate_passport(data)

    block = ledger.add_block(data)
    verify_url = _verify_payload(passport_id, block["hash"])
    return {
        "passport": data,
        "block": block,
        "verify_url": verify_url,
        "qr_svg": _make_qr_svg(verify_url),
    }


def get_passport(passport_id: str) -> dict | None:
    """Fetch a recorded passport (with a freshly rendered QR) by id."""
    block = ledger.find_block(passport_id)
    if not block:
        return None
    verify_url = _verify_payload(passport_id, block["hash"])
    return {
        "passport": block["data"],
        "block": block,
        "verify_url": verify_url,
        "qr_svg": _make_qr_svg(verify_url),
    }
