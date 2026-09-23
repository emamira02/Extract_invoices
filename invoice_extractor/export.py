"""Build the downloadable JSON, with keys in the user's language."""

from __future__ import annotations

import json
from typing import Any

from .parsing import HEADER_FIELDS, ITEM_COLUMNS


def build_export(fields: dict[str, str], items: list[dict[str, Any]], category: str | None, strings: dict) -> dict:
    out: dict[str, Any] = {strings["fields"][name]: fields.get(name, "") for name in HEADER_FIELDS}
    out[strings["category_key"]] = category or ""
    out[strings["product_list"]] = [
        {strings["columns"][col]: item.get(col) for col in ITEM_COLUMNS} for item in items
    ]
    return out


def to_json_bytes(data: dict) -> bytes:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str).encode("utf-8")
