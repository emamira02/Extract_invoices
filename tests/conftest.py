import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SAMPLES = ROOT / "sample_data"


@pytest.fixture
def invoice_result() -> dict:
    return json.loads((SAMPLES / "sample_invoice.invoice.json").read_text(encoding="utf-8"))


@pytest.fixture
def receipt_result() -> dict:
    return json.loads((SAMPLES / "sample_invoice.receipt.json").read_text(encoding="utf-8"))
