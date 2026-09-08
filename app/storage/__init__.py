import uuid
from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

_EXT_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
}


@lru_cache
def get_storage_backend() -> StorageBackend:
    if settings.storage_backend == "s3":
        from app.storage.s3 import get_s3_backend

        return get_s3_backend()
    return LocalStorageBackend()


def generate_object_key(*, folder: str, content_type: str) -> str:
    ext = _EXT_BY_TYPE.get(content_type, "bin")
    return f"{folder}/{uuid.uuid4().hex}.{ext}"


__all__ = [
    "ALLOWED_IMAGE_TYPES",
    "ALLOWED_VIDEO_TYPES",
    "MAX_IMAGE_BYTES",
    "MAX_VIDEO_BYTES",
    "get_storage_backend",
    "generate_object_key",
]
