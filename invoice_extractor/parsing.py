"""Turn raw Document Intelligence results (plain dicts) into the app's data model.

Pure functions only: easy to unit-test with JSON fixtures.
"""

from __future__ import annotations

import re
from typing import Any

# Header fields shown in the editor, in display order.
HEADER_FIELDS: list[str] = [
    "VendorName",
    "VendorAddress",
    "MerchantPhoneNumber",
    "InvoiceDate",
    "TransactionTime",
    "VendorTaxId",
    "InvoiceTotal",
]

# Receipt-model fields used to fill gaps left by the invoice model.
RECEIPT_FALLBACKS: dict[str, str] = {
    "MerchantPhoneNumber": "MerchantPhoneNumber",
    "TransactionTime": "TransactionTime",
    "VendorName": "MerchantName",
    "VendorAddress": "MerchantAddress",
    "InvoiceDate": "TransactionDate",
    "InvoiceTotal": "Total",
}

ITEM_COLUMNS: list[str] = ["description", "product_code", "quantity", "unit_price", "amount"]


class NoDocumentFound(ValueError):
    """Azure answered, but recognised no invoice or receipt in the file."""


# --------------------------------------------------------------------------- numbers
_NUMBER_CHARS = re.compile(r"[^0-9,.\-]")


def parse_number(value: Any) -> float | None:
    """Parse amounts written in Italian or English style.

    >>> parse_number("€ 1.234,56"), parse_number("1,234.56"), parse_number("12,50")
    (1234.56, 1234.56, 12.5)
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _NUMBER_CHARS.sub("", str(value))
    if not text or text in {"-", ".", ","}:
        return None

    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text or "." in text:
        sep = "," if "," in text else "."
        head, _, tail = text.rpartition(sep)
        # "1.500" / "1,500" -> thousands; "12,50" / "3.5" -> decimals
        if text.count(sep) > 1 or len(tail) == 3:
            text = text.replace(sep, "")
        else:
            text = head.replace(sep, "") + "." + tail
    try:
        return float(text)
    except ValueError:
        return None


def _field_number(field: dict[str, Any] | None) -> float | None:
    if not field:
        return None
    if "valueCurrency" in field and field["valueCurrency"].get("amount") is not None:
        return float(field["valueCurrency"]["amount"])
    if field.get("valueNumber") is not None:
        return float(field["valueNumber"])
    return parse_number(field.get("content"))


def _content(field: dict[str, Any] | None) -> str:
    return (field or {}).get("content", "") or ""


# --------------------------------------------------------------------------- items
def parse_item(item_field: dict[str, Any]) -> dict[str, Any]:
    """Normalise one line item, filling in quantity and unit price when missing."""
    obj = item_field.get("valueObject", {}) or {}
    quantity = _field_number(obj.get("Quantity"))
    unit_price = _field_number(obj.get("UnitPrice"))
    amount = _field_number(obj.get("Amount"))

    if quantity is None:
        quantity = 1.0
    if unit_price is None and amount is not None and quantity:
        unit_price = round(amount / quantity, 4)
    if amount is None and unit_price is not None:
        amount = round(unit_price * quantity, 2)

    return {
        "description": _content(obj.get("Description")) or _content(item_field),
        "product_code": _content(obj.get("ProductCode")),
        "quantity": quantity,
        "unit_price": unit_price,
        "amount": amount,
    }


# --------------------------------------------------------------------------- polygons
def _first_region(field: dict[str, Any]) -> dict[str, Any] | None:
    regions = field.get("boundingRegions") or []
    return regions[0] if regions else None


def _collect_polygons(fields: dict[str, Any], wanted: set[str], prefix: str = "") -> dict[str, dict]:
    boxes: dict[str, dict] = {}
    for name, field in fields.items():
        if name == "Items":
            for i, item in enumerate(field.get("valueArray", []) or []):
                for sub_name, sub in (item.get("valueObject") or {}).items():
                    region = _first_region(sub)
                    if region:
                        boxes[f"Items[{i}].{sub_name}"] = region
        elif name in wanted:
            region = _first_region(field)
            if region:
                boxes[prefix + name] = region
    return boxes


# --------------------------------------------------------------------------- main entry
def _first_document_fields(result: dict[str, Any] | None) -> dict[str, Any]:
    docs = (result or {}).get("documents") or []
    return docs[0].get("fields", {}) if docs else {}


def _page_info(result: dict[str, Any]) -> dict[str, Any]:
    pages = result.get("pages") or []
    if not pages:
        return {}
    p = pages[0]
    return {"width": p.get("width"), "height": p.get("height"), "unit": p.get("unit", "inch")}


def parse_analysis(invoice: dict[str, Any], receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge invoice + receipt results into ``{fields, items, boxes, page}``."""
    inv_fields = _first_document_fields(invoice)
    rec_fields = _first_document_fields(receipt)
    if not inv_fields and not rec_fields:
        raise NoDocumentFound("No invoice or receipt was recognised in this file.")

    header: dict[str, str] = {name: _content(inv_fields.get(name)) for name in HEADER_FIELDS}
    boxes = _collect_polygons(inv_fields, set(HEADER_FIELDS) | {"AmountDue"})

    for target, source in RECEIPT_FALLBACKS.items():
        if not header[target] and rec_fields.get(source):
            header[target] = _content(rec_fields[source])
            region = _first_region(rec_fields[source])
            if region:
                boxes[target] = region

    items = [parse_item(it) for it in (inv_fields.get("Items", {}) or {}).get("valueArray", []) or []]

    return {
        "fields": header,
        "items": items,
        "boxes": boxes,
        "page": _page_info(invoice if inv_fields else receipt or {}),
    }
