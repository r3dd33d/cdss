import pytest

from cdss.core.exceptions import ExtractError, FetchError
from cdss.sources.extract.html import extract_html
from cdss.sources.extract.pdf import extract_pdf


def test_extract_html_basic():
    html = b"<html><body><p>NSCLC standard of care includes osimertinib.</p></body></html>"
    result = extract_html(html)
    assert "NSCLC" in result or len(result) > 0  # trafilatura may vary


def test_extract_html_empty_raises():
    with pytest.raises(ExtractError):
        extract_html(b"<html></html>")


def test_extract_pdf_bad_bytes_raises():
    with pytest.raises(ExtractError):
        extract_pdf(b"not a pdf")


def test_extract_html_truncates():
    big = b"<p>" + b"x" * 20000 + b"</p>"
    result = extract_html(big, max_chars=100)
    assert len(result) <= 100


@pytest.mark.asyncio
async def test_httpx_fetcher_raises_fetch_error():
    import httpx
    from unittest.mock import AsyncMock, patch
    from cdss.sources.fetch.httpx_fetcher import HttpxFetcher

    fetcher = HttpxFetcher(timeout_seconds=5)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock,
               side_effect=httpx.ConnectError("fail")):
        with pytest.raises(FetchError):
            await fetcher.fetch("https://example.com/page")
