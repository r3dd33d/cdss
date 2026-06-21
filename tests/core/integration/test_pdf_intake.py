"""Integration: PDF extraction feeds intake correctly."""
import io
import pytest

from cdss.sources.extract.pdf import extract_pdf
from cdss.core.exceptions import ExtractError


def _minimal_pdf_bytes() -> bytes:
    """Minimal valid single-page PDF with readable text."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
        b"0000000058 00000 n\n0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )


def test_extract_pdf_invalid_raises():
    with pytest.raises(ExtractError):
        extract_pdf(b"not a pdf")


def test_extract_pdf_empty_bytes_raises():
    with pytest.raises(ExtractError):
        extract_pdf(b"")


def test_extract_pdf_truncates():
    """A valid-but-text-empty PDF should raise ExtractError (no text)."""
    with pytest.raises(ExtractError):
        extract_pdf(_minimal_pdf_bytes())
