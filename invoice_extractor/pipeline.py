"""End-to-end processing of one document: validate -> analyse -> parse.

Also provides the bundled sample used in demo mode (no Azure key needed).
"""

from __future__ import annotations

import json
from typing import Any

from .azure_client import analyze_pdf
from .config import PROJECT_ROOT, Settings
from .files import prepare_document
from .parsing import parse_analysis

SAMPLE_DIR = PROJECT_ROOT / "sample_data"
SAMPLE_NAME = "sample_invoice.pdf"


def process_upload(filename: str, content: bytes, settings: Settings) -> tuple[bytes, dict[str, Any]]:
    """Return ``(pdf_bytes, parsed_data)``.

    Raises InvalidFileError, AnalysisError or NoDocumentFound with a readable message.
    """
    pdf = prepare_document(filename, content, settings.max_upload_mb)
    invoice, receipt = analyze_pdf(pdf, settings)
    return pdf, parse_analysis(invoice, receipt)


def load_sample() -> tuple[str, bytes, dict[str, Any]]:
    """Return ``(file_name, pdf_bytes, parsed_data)`` for the bundled sample invoice."""
    pdf = (SAMPLE_DIR / SAMPLE_NAME).read_bytes()
    invoice = json.loads((SAMPLE_DIR / "sample_invoice.invoice.json").read_text(encoding="utf-8"))
    receipt = json.loads((SAMPLE_DIR / "sample_invoice.receipt.json").read_text(encoding="utf-8"))
    return SAMPLE_NAME, pdf, parse_analysis(invoice, receipt)
