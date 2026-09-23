"""Validate uploaded files and normalise them to PDF bytes."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {"pdf"}


class InvalidFileError(ValueError):
    """Raised when an upload is empty, too large, of the wrong type or corrupted."""


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def is_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


def image_to_pdf(content: bytes) -> bytes:
    """Wrap an image in a single-page PDF sized to the image."""
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.load()
            rgb = img.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidFileError("The image is corrupted or not a real JPG/PNG.") from exc

    png = io.BytesIO()
    rgb.save(png, format="PNG")
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=rgb.width, height=rgb.height)
        page.insert_image(page.rect, stream=png.getvalue())
        return doc.tobytes()
    finally:
        doc.close()


def prepare_document(filename: str, content: bytes, max_mb: int = 10) -> bytes:
    """Return the upload as PDF bytes, or raise InvalidFileError with a readable reason."""
    ext = _extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise InvalidFileError(f"Unsupported file type '.{ext or '?'}'. Use PDF, JPG or PNG.")
    if not content:
        raise InvalidFileError("The file is empty.")
    if len(content) > max_mb * 1024 * 1024:
        raise InvalidFileError(f"The file is larger than {max_mb} MB.")

    if ext == "pdf":
        if not is_pdf(content):
            raise InvalidFileError("The file has a .pdf extension but is not a valid PDF.")
        try:
            with pymupdf.open(stream=content, filetype="pdf") as doc:
                if doc.page_count == 0:
                    raise InvalidFileError("The PDF has no pages.")
        except (pymupdf.FileDataError, RuntimeError) as exc:
            raise InvalidFileError("The PDF is corrupted and cannot be opened.") from exc
        return content

    return image_to_pdf(content)
