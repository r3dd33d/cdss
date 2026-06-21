from cdss.core.exceptions import ExtractError


def extract_html(raw: bytes, max_chars: int = 12000) -> str:
    """Extract readable text from HTML bytes using trafilatura."""
    try:
        import trafilatura
        text = trafilatura.extract(raw.decode("utf-8", errors="replace"))
        if not text:
            raise ExtractError("trafilatura returned empty text")
        return text[:max_chars]
    except ImportError:
        # Fallback: strip tags naively if trafilatura is not installed.
        import re
        text = " ".join(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", errors="replace")).split())
        if not text:
            raise ExtractError("No text extracted from HTML")
        return text[:max_chars]
