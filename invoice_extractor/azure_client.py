"""Thin wrapper around Azure AI Document Intelligence.

Returns the raw analysis as plain dicts (``AnalyzeResult.as_dict()``) so that the
parsing step can be unit-tested with JSON fixtures, without calling Azure.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)

from .config import Settings

log = logging.getLogger(__name__)

INVOICE_MODEL = "prebuilt-invoice"
RECEIPT_MODEL = "prebuilt-receipt"
TIMEOUT_SECONDS = 120


class AnalysisError(RuntimeError):
    """A user-facing error raised when Azure cannot analyse the document."""


def _client(settings: Settings) -> DocumentIntelligenceClient:
    if not settings.azure_configured:
        raise AnalysisError(
            "Azure Document Intelligence is not configured. "
            "Set AZURE_DOCINTEL_ENDPOINT and AZURE_DOCINTEL_KEY (see .env.example)."
        )
    return DocumentIntelligenceClient(
        endpoint=settings.azure_endpoint,
        credential=AzureKeyCredential(settings.azure_key),
    )


def _analyze(client: DocumentIntelligenceClient, model_id: str, pdf: bytes, locale: str) -> dict[str, Any]:
    try:
        poller = client.begin_analyze_document(
            model_id,
            body=io.BytesIO(pdf),
            content_type="application/octet-stream",
            locale=locale,
        )
        result = poller.result(timeout=TIMEOUT_SECONDS)
        if result is None:
            raise TimeoutError
        return result.as_dict()
    except ClientAuthenticationError as exc:
        raise AnalysisError("Azure rejected the API key (401). Check AZURE_DOCINTEL_KEY.") from exc
    except ResourceNotFoundError as exc:
        raise AnalysisError("Azure endpoint or model not found (404). Check AZURE_DOCINTEL_ENDPOINT.") from exc
    except ServiceRequestError as exc:
        raise AnalysisError("Could not reach Azure. Check the endpoint URL and your connection.") from exc
    except HttpResponseError as exc:
        if exc.status_code == 429:
            raise AnalysisError("Azure rate limit reached (429). Wait a moment and retry.") from exc
        raise AnalysisError(f"Azure returned an error ({exc.status_code}): {exc.reason}") from exc
    except TimeoutError as exc:
        raise AnalysisError(f"Azure did not answer within {TIMEOUT_SECONDS}s.") from exc


def analyze_pdf(pdf: bytes, settings: Settings) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Run the invoice model, then the receipt model for phone number and time.

    The receipt call is best effort: if it fails the invoice result is still returned.
    """
    client = _client(settings)
    invoice = _analyze(client, INVOICE_MODEL, pdf, settings.locale)
    try:
        receipt = _analyze(client, RECEIPT_MODEL, pdf, settings.locale)
    except AnalysisError as exc:
        log.warning("Receipt model failed, continuing with invoice data only: %s", exc)
        receipt = None
    return invoice, receipt
