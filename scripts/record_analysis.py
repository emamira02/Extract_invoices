"""Call Azure on a file and save the raw responses as JSON (e.g. to refresh demo data).

    python scripts/record_analysis.py path/to/invoice.pdf sample_data/sample_invoice

writes sample_data/sample_invoice.invoice.json and sample_data/sample_invoice.receipt.json.
Requires AZURE_DOCINTEL_ENDPOINT and AZURE_DOCINTEL_KEY in the environment or .env.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from invoice_extractor.azure_client import analyze_pdf  # noqa: E402
from invoice_extractor.config import load_settings  # noqa: E402
from invoice_extractor.files import prepare_document  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, prefix = Path(sys.argv[1]), sys.argv[2]
    settings = load_settings()
    pdf = prepare_document(src.name, src.read_bytes(), settings.max_upload_mb)
    invoice, receipt = analyze_pdf(pdf, settings)
    for name, data in [("invoice", invoice), ("receipt", receipt)]:
        if data is not None:
            Path(f"{prefix}.{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Saved.")


if __name__ == "__main__":
    main()
