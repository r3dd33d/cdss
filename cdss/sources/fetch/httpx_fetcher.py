import httpx

from cdss.core.exceptions import FetchError
from cdss.sources.fetch.base import AbstractFetcher


class HttpxFetcher(AbstractFetcher):
    def __init__(self, timeout_seconds: int = 15, user_agent: str = "CDSS/0.1") -> None:
        self._timeout = timeout_seconds
        self._headers = {"User-Agent": user_agent}

    async def fetch(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as c:
                resp = await c.get(url, headers=self._headers)
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            raise FetchError(f"Failed to fetch {url}: {exc}") from exc
