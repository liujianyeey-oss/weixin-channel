import pytest

from weixin_channel.media import (
    aes_ecb_decrypt,
    aes_ecb_encrypt,
    build_download_url,
    build_upload_url,
    detect_extension,
    encrypted_size,
)
from weixin_channel.media_backend import FileSystemMediaBackend


def test_encrypt_decrypt_roundtrip() -> None:
    key = b"1234567890abcdef"
    data = b"hello weixin"
    encrypted = aes_ecb_encrypt(data, key)
    assert encrypted != data
    assert len(encrypted) % 16 == 0
    assert aes_ecb_decrypt(encrypted, key) == data


def test_encrypted_size() -> None:
    assert encrypted_size(0) == 16
    assert encrypted_size(16) == 32
    assert encrypted_size(17) == 32


def test_detect_extension() -> None:
    assert detect_extension(b"\x89PNG\r\n\x1a\nxxxx") == ".png"
    assert detect_extension(b"RIFFxxxxWEBPxxxx") == ".webp"
    assert detect_extension(b"unknown") == ".bin"


def test_urls_quote_params() -> None:
    assert build_download_url("a b").endswith("a%20b")
    assert build_upload_url("a b", "c d").endswith("&filekey=c%20d")


@pytest.mark.asyncio
async def test_filesystem_media_backend_roundtrip(tmp_path):
    backend = FileSystemMediaBackend(tmp_path)
    await backend.save(b"payload", "safe/nested/file.txt")
    assert await backend.exists("safe/nested/file.txt")
    assert await backend.read("safe/nested/file.txt") == b"payload"


@pytest.mark.asyncio
async def test_filesystem_media_backend_rejects_escape(tmp_path):
    backend = FileSystemMediaBackend(tmp_path)
    with pytest.raises(ValueError, match="escapes backend root"):
        await backend.save(b"payload", "../escape.txt")


@pytest.mark.asyncio
async def test_filesystem_media_backend_rejects_directory_key(tmp_path):
    backend = FileSystemMediaBackend(tmp_path)
    with pytest.raises(ValueError, match="must name a file"):
        await backend.save(b"payload", ".")
