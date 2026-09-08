"""Upload validation: never trust the client-declared filename or
Content-Type header alone. We re-derive the real image type by sniffing
the bytes with Pillow, cap size, and always generate a random storage key.

Every accepted image is also resized and re-encoded as JPEG before
storage (see _process_image) rather than storing the original bytes
as-is: phone-camera photos are routinely 5-8MB, which is both wasteful
of free-tier object storage quota and slower to upload/display in the
Flutter app than necessary for anything actually shown on a phone
screen. This also strips EXIF metadata (which can include GPS location),
which we want gone regardless of the storage-size motivation.
"""

import io

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.exceptions import BadRequestError
from app.storage import (
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_BYTES,
    generate_object_key,
    get_storage_backend,
)

_PIL_FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

_MAX_DIMENSION = 1200
_JPEG_QUALITY = 80
_OUTPUT_MIME = "image/jpeg"


def _process_image(content: bytes) -> bytes:
    """Downscale to fit within _MAX_DIMENSION (never upscales) and
    re-encode as JPEG. Always re-opens fresh from `content` — the caller's
    validation Image was already .verify()'d, which Pillow disallows any
    further use of."""
    opened = Image.open(io.BytesIO(content))
    # Apply the EXIF orientation tag as an actual rotation before we
    # re-encode (and thereby drop that EXIF data) — otherwise phone photos
    # taken in portrait would come out sideways. exif_transpose() only
    # returns None when called with in_place=True, which we don't use.
    image: Image.Image = ImageOps.exif_transpose(opened) or opened

    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        # JPEG has no alpha channel; composite onto white rather than
        # Pillow's default (black) so accidental transparency doesn't
        # turn into a black background.
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        image = background
    elif image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    image.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    image.save(out, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return out.getvalue()


async def validate_and_store_image(file: UploadFile, *, folder: str) -> str:
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise BadRequestError("Image exceeds maximum allowed size")
    if not content:
        raise BadRequestError("Empty file")

    try:
        probe = Image.open(io.BytesIO(content))
        detected_format = probe.format
        probe.verify()
    except UnidentifiedImageError as exc:
        raise BadRequestError("File is not a valid image") from exc

    mime = _PIL_FORMAT_TO_MIME.get(detected_format or "")
    if mime not in ALLOWED_IMAGE_TYPES:
        raise BadRequestError("Unsupported image type; use JPEG, PNG or WEBP")

    try:
        processed = _process_image(content)
    except BadRequestError:
        raise
    except Exception as exc:
        raise BadRequestError("Could not process image") from exc

    key = generate_object_key(folder=folder, content_type=_OUTPUT_MIME)
    backend = get_storage_backend()
    return await backend.save(key=key, content=processed, content_type=_OUTPUT_MIME)
