import pytest

from invoice_extractor.parsing import NoDocumentFound, parse_analysis, parse_item, parse_number


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("€ 1.234,56", 1234.56),  # Italian
        ("1,234.56", 1234.56),    # English
        ("12,50", 12.5),
        ("1.500", 1500.0),        # thousands separator only
        ("-3,20", -3.2),
        (7, 7.0),
        ("", None),
        ("n/a", None),
    ],
)
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_parse_analysis_merges_invoice_and_receipt(invoice_result, receipt_result):
    data = parse_analysis(invoice_result, receipt_result)

    assert data["fields"]["VendorName"] == "Bottega Verdi S.r.l."
    assert data["fields"]["VendorTaxId"] == "IT01234567890"
    # phone and time only come from the receipt model
    assert data["fields"]["MerchantPhoneNumber"] == "+39 02 1234 5678"
    assert data["fields"]["TransactionTime"] == "10:42"

    assert len(data["items"]) == 3
    assert data["items"][0] == {
        "description": "Caffè in grani 1 kg",
        "product_code": "CAF-001",
        "quantity": 2.0,
        "unit_price": 18.5,
        "amount": 37.0,
    }
    assert "VendorName" in data["boxes"] and "MerchantPhoneNumber" in data["boxes"]
    assert data["page"]["unit"] == "inch"


def test_item_without_quantity_or_unit_price_is_completed():
    item = {"valueObject": {"Description": {"content": "Servizio"}, "Amount": {"content": "40,00"}}}
    assert parse_item(item) == {
        "description": "Servizio",
        "product_code": "",
        "quantity": 1.0,
        "unit_price": 40.0,
        "amount": 40.0,
    }


def test_empty_result_raises():
    with pytest.raises(NoDocumentFound):
        parse_analysis({"documents": []}, None)
