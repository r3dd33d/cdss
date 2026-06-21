import io

from cdss.core.exceptions import ExtractError


def extract_pdf(raw: bytes, max_chars: int = 12000) -> str:
    """Extract text from PDF bytes using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ExtractError("PDF contains no extractable text")
        return text[:max_chars]
    except ExtractError:
        raise
    except Exception as exc:
        raise ExtractError(f"PDF extraction failed: {exc}") from exc
