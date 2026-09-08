from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, *, key: str, content: bytes, content_type: str) -> str:
        """Persist bytes under `key` and return a publicly reachable URL."""

    @abstractmethod
    async def delete(self, *, key: str) -> None: ...
