from abc import ABC, abstractmethod


class AbstractFetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> bytes: ...
