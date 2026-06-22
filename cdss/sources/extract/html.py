from cdss.core.exceptions import ExtractError


def _strip_tags(html: str) -> str:
    import re
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def extract_html(raw: bytes, max_chars: int = 12000) -> str:
    """Extract readable text from HTML bytes using trafilatura with tag-stripping fallback."""
    decoded = raw.decode("utf-8", errors="replace")
    try:
        import trafilatura
        text = trafilatura.extract(decoded)
        if text:
            return text[:max_chars]
    except ImportError:
        pass

    text = _strip_tags(decoded)
    if not text:
        raise ExtractError("No text extracted from HTML")
    return text[:max_chars]
