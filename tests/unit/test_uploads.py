import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import BadRequestError
from app.utils.uploads import validate_and_store_image


def _fake_upload(content: bytes, content_type: str, filename: str) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=Headers({"content-type": content_type}))


async def test_rejects_file_that_is_not_actually_an_image():
    """A `.jpg`-named file containing arbitrary bytes (e.g. a script) must
    be rejected — we sniff real content, never trust the extension or the
    client-supplied Content-Type header."""
    malicious = _fake_upload(b"#!/bin/sh\necho pwned\n", "image/jpeg", "totally-a-photo.jpg")
    with pytest.raises(BadRequestError):
        await validate_and_store_image(malicious, folder="test")


async def test_rejects_empty_file():
    empty = _fake_upload(b"", "image/jpeg", "empty.jpg")
    with pytest.raises(BadRequestError):
        await validate_and_store_image(empty, folder="test")


async def test_accepts_real_png():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    upload = _fake_upload(buffer.getvalue(), "image/png", "photo.png")

    url = await validate_and_store_image(upload, folder="test")
    # Every accepted image is re-encoded as JPEG on the way in (see
    # app/utils/uploads.py), regardless of the original upload format.
    assert url.endswith(".jpg")


async def test_large_image_is_downscaled_and_compressed():
    """A big, uncompressed upload should come out much smaller and capped
    at the configured max dimension — this is the whole point of
    processing images server-side instead of storing them as-is."""
    from PIL import Image

    from app.storage import get_storage_backend
    from app.utils import uploads as uploads_module

    buffer = io.BytesIO()
    Image.new("RGB", (4000, 3000), color="blue").save(buffer, format="PNG")
    original_bytes = buffer.getvalue()
    upload = _fake_upload(original_bytes, "image/png", "huge.png")

    url = await validate_and_store_image(upload, folder="test")
    assert url.endswith(".jpg")

    backend = get_storage_backend()
    stored_path = getattr(backend, "base_dir", None)
    assert stored_path is not None, "test relies on the local storage backend"
    key = url.removeprefix(backend.public_base_url + "/")
    stored_bytes = (stored_path / key).read_bytes()

    assert len(stored_bytes) < len(original_bytes)
    stored_image = Image.open(io.BytesIO(stored_bytes))
    assert stored_image.format == "JPEG"
    assert max(stored_image.size) <= uploads_module._MAX_DIMENSION
