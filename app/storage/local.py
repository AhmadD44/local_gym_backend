import asyncio
from pathlib import Path

from app.core.config import settings
from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str | None = None, public_base_url: str | None = None):
        self.base_dir = Path(base_dir or settings.storage_local_dir)
        self.public_base_url = (public_base_url or settings.storage_public_base_url).rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, *, key: str, content: bytes, content_type: str) -> str:
        target = self.base_dir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, content)
        return f"{self.public_base_url}/{key}"

    async def delete(self, *, key: str) -> None:
        target = self.base_dir / key
        await asyncio.to_thread(target.unlink, True)
