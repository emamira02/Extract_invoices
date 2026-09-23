"""Generate the fictional sample invoice used by demo mode and the tests.

Creates:
  sample_data/sample_invoice.pdf
  sample_data/sample_invoice.invoice.json   (shape of AnalyzeResult.as_dict(), prebuilt-invoice)
  sample_data/sample_invoice.receipt.json   (shape of AnalyzeResult.as_dict(), prebuilt-receipt)

The JSON files are *not* real Azure output: they are built by hand in the same
format, with bounding boxes taken from the text positions in the generated PDF.
To replace them with a real response, run scripts/record_analysis.py with your key.

    python scripts/make_sample_invoice.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parent.parent / "sample_data"
PT_PER_INCH = 72.0

VENDOR = "Bottega Verdi S.r.l."
ADDRESS = "Via Roma 12, 20121 Milano (MI)"
PHONE = "+39 02 1234 5678"
VAT = "IT01234567890"
DATE = "12/03/2025"
TIME = "10:42"
ITEMS = [
    ("Caffè in grani 1 kg", "CAF-001", 2, 18.50),
    ("Tazzine in ceramica (set 6)", "TAZ-006", 1, 24.00),
    ("Filtri carta n.4 (100 pz)", "FIL-104", 3, 3.20),
]


def eur(value: float) -> str:
    """Italian formatting without the euro sign (base-14 PDF fonts cannot draw it)."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4
    write = page.insert_text

    page.draw_rect(pymupdf.Rect(0, 0, 595, 110), color=None, fill=(0.12, 0.27, 0.45))
    write((48, 62), "FATTURA", fontsize=26, fontname="hebo", color=(1, 1, 1))
    write((48, 88), "Documento di esempio - dati fittizi", fontsize=10, color=(0.85, 0.9, 1))

    write((48, 150), VENDOR, fontsize=14, fontname="hebo")
    write((48, 170), ADDRESS, fontsize=10)
    write((48, 186), f"Tel. {PHONE}", fontsize=10)
    write((48, 202), f"P.IVA {VAT}", fontsize=10)

    write((380, 150), "Fattura n. 2025/0142", fontsize=10, fontname="hebo")
    write((380, 170), f"Data: {DATE}", fontsize=10)
    write((380, 186), f"Ora: {TIME}", fontsize=10)

    write((48, 250), "Cliente: Mario Rossi, Via Garibaldi 5, 10121 Torino (TO)", fontsize=10)

    y = 300
    headers = [(48, "Descrizione"), (270, "Codice"), (350, "Q.tà"), (400, "Prezzo EUR"), (490, "Importo EUR")]
    page.draw_rect(pymupdf.Rect(40, y - 16, 555, y + 6), color=None, fill=(0.93, 0.95, 0.98))
    for x, h in headers:
        write((x, y), h, fontsize=10, fontname="hebo")
    total = 0.0
    for desc, code, qty, price in ITEMS:
        y += 26
        amount = qty * price
        total += amount
        for x, text in [(48, desc), (270, code), (350, str(qty)), (400, eur(price)), (490, eur(amount))]:
            write((x, y), text, fontsize=10)
        page.draw_line((40, y + 8), (555, y + 8), color=(0.85, 0.85, 0.85))

    vat = round(total * 0.22, 2)
    y += 44
    write((380, y), "Imponibile", fontsize=10)
    write((490, y), eur(total), fontsize=10)
    write((380, y + 18), "IVA 22%", fontsize=10)
    write((490, y + 18), eur(vat), fontsize=10)
    write((380, y + 42), "TOTALE EUR", fontsize=12, fontname="hebo")
    write((490, y + 42), eur(total + vat), fontsize=12, fontname="hebo")
    return doc.tobytes()


def region(page: pymupdf.Page, text: str, occurrence: int = 0) -> dict:
    rect = page.search_for(text)[occurrence]
    x0, y0, x1, y1 = (v / PT_PER_INCH for v in (rect.x0, rect.y0, rect.x1, rect.y1))
    poly = [round(v, 4) for v in (x0, y0, x1, y0, x1, y1, x0, y1)]
    return {"pageNumber": 1, "polygon": poly}


def field(page, content: str, kind: str = "string", search: str | None = None, **value) -> dict:
    out = {"type": kind, "content": content, "confidence": 0.95, "boundingRegions": [region(page, search or content)]}
    out.update(value)
    return out


def currency(page, amount: float, search_occurrence: int = 0) -> dict:
    text = eur(amount)
    return {
        "type": "currency",
        "content": text,
        "valueCurrency": {"amount": round(amount, 2), "currencySymbol": "€", "currencyCode": "EUR"},
        "confidence": 0.95,
        "boundingRegions": [region(page, text, search_occurrence)],
    }


def build_results(pdf: bytes) -> tuple[dict, dict]:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    page = doc[0]
    page_info = [{"pageNumber": 1, "width": round(595 / 72, 4), "height": round(842 / 72, 4), "unit": "inch"}]

    items = []
    subtotal = 0.0
    for desc, code, qty, price in ITEMS:
        amount = qty * price
        subtotal += amount
        items.append({
            "type": "object",
            "content": f"{desc} {code} {qty} {eur(price)} {eur(amount)}",
            "valueObject": {
                "Description": field(page, desc),
                "ProductCode": field(page, code),
                "Quantity": {"type": "number", "content": str(qty), "valueNumber": qty, "confidence": 0.9},
                "UnitPrice": currency(page, price),
                "Amount": currency(page, amount, 0 if eur(amount) != eur(price) else 1),
            },
        })
    total = round(subtotal * 1.22, 2)

    invoice = {
        "_note": "Synthetic sample in AnalyzeResult.as_dict() format - generated by scripts/make_sample_invoice.py",
        "modelId": "prebuilt-invoice",
        "pages": page_info,
        "documents": [{
            "docType": "invoice",
            "confidence": 0.95,
            "fields": {
                "VendorName": field(page, VENDOR),
                "VendorAddress": field(page, ADDRESS, kind="address"),
                "VendorTaxId": field(page, VAT),
                "InvoiceId": field(page, "2025/0142"),
                "InvoiceDate": field(page, DATE, kind="date", valueDate="2025-03-12"),
                "CustomerName": field(page, "Mario Rossi"),
                "SubTotal": currency(page, subtotal),
                "InvoiceTotal": currency(page, total),
                "Items": {"type": "array", "valueArray": items},
            },
        }],
    }
    receipt = {
        "_note": "Synthetic sample in AnalyzeResult.as_dict() format - generated by scripts/make_sample_invoice.py",
        "modelId": "prebuilt-receipt",
        "pages": page_info,
        "documents": [{
            "docType": "receipt.retailMeal",
            "confidence": 0.8,
            "fields": {
                "MerchantName": field(page, VENDOR),
                "MerchantPhoneNumber": field(page, PHONE, kind="phoneNumber"),
                "TransactionTime": field(page, TIME, kind="time"),
                "Total": currency(page, total),
            },
        }],
    }
    doc.close()
    return invoice, receipt


def main() -> None:
    OUT.mkdir(exist_ok=True)
    pdf = build_pdf()
    (OUT / "sample_invoice.pdf").write_bytes(pdf)
    invoice, receipt = build_results(pdf)
    for name, data in [("invoice", invoice), ("receipt", receipt)]:
        (OUT / f"sample_invoice.{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote sample files to {OUT}")


if __name__ == "__main__":
    main()
