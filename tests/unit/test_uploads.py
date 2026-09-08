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
    assert url.endswith(".png")
