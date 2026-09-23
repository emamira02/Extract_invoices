"""Render the first page of a PDF and draw the extracted fields' bounding boxes."""

from __future__ import annotations

import io
from typing import Any

import pymupdf
from PIL import Image, ImageDraw

FIELD_COLORS: dict[str, str] = {
    "VendorName": "#e10050",
    "VendorAddress": "#1f5eff",
    "MerchantPhoneNumber": "#ff4d00",
    "InvoiceDate": "#f59e0b",
    "TransactionTime": "#ae00c6",
    "VendorTaxId": "#00a8a8",
    "InvoiceTotal": "#16a34a",
    "AmountDue": "#16a34a",
}
ITEM_COLOR = "#8b5cf6"


def render_first_page(pdf: bytes, zoom: float = 2.0) -> Image.Image:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def draw_boxes(image: Image.Image, boxes: dict[str, dict], page: dict[str, Any]) -> Image.Image:
    """Draw page-1 regions. Coordinates are in the page's unit (inch for PDFs)."""
    img = image.copy()
    draw = ImageDraw.Draw(img)
    width, height = page.get("width"), page.get("height")
    sx = img.width / width if width else 72.0
    sy = img.height / height if height else 72.0

    for name, region in boxes.items():
        if region.get("pageNumber", 1) != 1:
            continue
        poly = region.get("polygon") or []
        if len(poly) < 4:
            continue
        xs = [x * sx for x in poly[0::2]]
        ys = [y * sy for y in poly[1::2]]
        color = ITEM_COLOR if name.startswith("Items[") else FIELD_COLORS.get(name, "#6b7280")
        draw.rectangle([min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3], outline=color, width=3)
    return img


def annotated_png(pdf: bytes, boxes: dict[str, dict], page: dict[str, Any]) -> bytes:
    img = draw_boxes(render_first_page(pdf), boxes, page)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
