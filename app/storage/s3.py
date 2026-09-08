import asyncio
from functools import lru_cache

import boto3

from app.core.config import settings
from app.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    def __init__(self):
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint or None,
            region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key or None,
            aws_secret_access_key=settings.storage_secret_key or None,
        )
        self.bucket = settings.storage_bucket
        self.public_base_url = settings.storage_public_base_url.rstrip("/")

    async def save(self, *, key: str, content: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return f"{self.public_base_url}/{key}"

    async def delete(self, *, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self.bucket, Key=key)


@lru_cache
def get_s3_backend() -> S3StorageBackend:
    return S3StorageBackend()
