import httpx

from cdss.core.models.source import SourceRef
from cdss.sources.search.base import AbstractSearchProvider


class SerperSiteScoped(AbstractSearchProvider):
    """Site-scoped search using the Serper API."""

    _URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str, sites: list[str], user_agent: str) -> None:
        self._api_key = api_key
        self._sites = sites
        self._user_agent = user_agent

    async def search(self, query: str, top_k: int = 5) -> list[SourceRef]:
        site_filter = " OR ".join(f"site:{s}" for s in self._sites)
        full_query = f"({site_filter}) {query}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self._URL,
                headers={"X-API-KEY": self._api_key, "User-Agent": self._user_agent},
                json={"q": full_query, "num": top_k},
            )
            resp.raise_for_status()
        results = resp.json().get("organic", [])
        refs = []
        for i, r in enumerate(results[:top_k]):
            domain = r.get("link", "").split("/")[2] if r.get("link") else "unknown"
            site_id = next((s for s in self._sites if domain.endswith(s)), domain)
            refs.append(SourceRef(
                url=r.get("link", ""),
                title=r.get("title", ""),
                site_id=site_id,
                rank=i + 1,
            ))
        return refs
