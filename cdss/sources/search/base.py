from abc import ABC, abstractmethod

from cdss.core.models.source import SourceRef


class AbstractSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[SourceRef]: ...
