import pytest
from draftloop_core.storage import DocumentStore
from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore


@pytest.fixture
async def store(tmp_path):
    s = SqliteDocumentStore(tmp_path / "test.db")
    await s.init_schema()
    return s


async def test_implements_protocol(store):
    assert isinstance(store, DocumentStore)


async def test_put_and_get_roundtrip(store):
    await store.put("M-001/doc_1", {"hello": "world"})
    got = await store.get("M-001/doc_1")
    assert got == {"hello": "world"}


async def test_missing_key_returns_none(store):
    assert (await store.get("M-001/missing")) is None


async def test_delete(store):
    await store.put("M-001/doc_1", {"x": 1})
    await store.delete("M-001/doc_1")
    assert (await store.get("M-001/doc_1")) is None


async def test_list_with_prefix(store):
    await store.put("M-001/doc_1", {"x": 1})
    await store.put("M-001/doc_2", {"x": 2})
    await store.put("M-002/doc_1", {"x": 3})
    keys: list[str] = []
    async for k, _ in store.list("M-001/"):
        keys.append(k)
    assert sorted(keys) == ["M-001/doc_1", "M-001/doc_2"]
