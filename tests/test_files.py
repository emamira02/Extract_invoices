import io

import pymupdf
import pytest
from PIL import Image

from invoice_extractor.files import InvalidFileError, prepare_document


def _png(width=40, height=20) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_image_is_converted_to_single_page_pdf():
    pdf = prepare_document("receipt.PNG", _png())
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        assert doc.page_count == 1
        assert (doc[0].rect.width, doc[0].rect.height) == (40, 20)


@pytest.mark.parametrize(
    "name, content, reason",
    [
        ("notes.txt", b"hello", "Unsupported"),
        ("empty.pdf", b"", "empty"),
        ("fake.pdf", b"not a pdf", "not a valid PDF"),
        ("broken.jpg", b"\xff\xd8garbage", "corrupted"),
    ],
)
def test_invalid_files_are_rejected_with_a_reason(name, content, reason):
    with pytest.raises(InvalidFileError, match=reason):
        prepare_document(name, content)


def test_size_limit():
    with pytest.raises(InvalidFileError, match="larger than 1 MB"):
        prepare_document("big.png", b"0" * (1024 * 1024 + 1), max_mb=1)
