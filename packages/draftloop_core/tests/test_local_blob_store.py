import pytest

from draftloop_core.storage import BlobStore
from draftloop_core.storage.local_blob_store import LocalBlobStore


@pytest.fixture
def store(tmp_path):
    return LocalBlobStore(tmp_path)


async def test_implements_protocol(store):
    assert isinstance(store, BlobStore)


async def test_put_and_get_roundtrip(store):
    await store.put("M-001/pdfs/a.pdf", b"\x25PDF-fake")
    got = await store.get("M-001/pdfs/a.pdf")
    assert got == b"\x25PDF-fake"


async def test_missing_key_raises(store):
    with pytest.raises(FileNotFoundError):
        await store.get("M-001/nope.pdf")


async def test_delete(store):
    await store.put("M-001/a.bin", b"123")
    await store.delete("M-001/a.bin")
    with pytest.raises(FileNotFoundError):
        await store.get("M-001/a.bin")


async def test_keys_with_subdirs(store, tmp_path):
    await store.put("M-001/sub/a.bin", b"hello")
    p = tmp_path / "M-001" / "sub" / "a.bin"
    assert p.exists() and p.read_bytes() == b"hello"
