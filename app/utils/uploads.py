"""Upload validation: never trust the client-declared filename or
Content-Type header alone. We re-derive the real image type by sniffing
the bytes with Pillow, cap size, and always generate a random storage key."""

import io

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.exceptions import BadRequestError
from app.storage import (
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_BYTES,
    generate_object_key,
    get_storage_backend,
)

_PIL_FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


async def validate_and_store_image(file: UploadFile, *, folder: str) -> str:
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise BadRequestError("Image exceeds maximum allowed size")
    if not content:
        raise BadRequestError("Empty file")

    try:
        image = Image.open(io.BytesIO(content))
        detected_format = image.format
        image.verify()
    except UnidentifiedImageError as exc:
        raise BadRequestError("File is not a valid image") from exc

    mime = _PIL_FORMAT_TO_MIME.get(detected_format or "")
    if mime not in ALLOWED_IMAGE_TYPES:
        raise BadRequestError("Unsupported image type; use JPEG, PNG or WEBP")

    key = generate_object_key(folder=folder, content_type=mime)
    backend = get_storage_backend()
    return await backend.save(key=key, content=content, content_type=mime)
