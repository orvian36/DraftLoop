import pytest

from draftloop_core.storage import VectorIndex, VectorItem
from draftloop_core.storage.chroma_vector_index import ChromaVectorIndex


@pytest.fixture
async def index(tmp_path):
    return ChromaVectorIndex(persist_path=str(tmp_path))


async def test_implements_protocol(index):
    assert isinstance(index, VectorIndex)


async def test_upsert_then_search_returns_nearest(index):
    items = [
        VectorItem(id="a", vector=[1.0, 0.0, 0.0], metadata={"matter_id": "M-1"}),
        VectorItem(id="b", vector=[0.0, 1.0, 0.0], metadata={"matter_id": "M-1"}),
        VectorItem(id="c", vector=[0.0, 0.0, 1.0], metadata={"matter_id": "M-1"}),
    ]
    await index.upsert("M-1", items)
    hits = await index.search("M-1", [0.9, 0.1, 0.0], top_k=2)
    ids = [h.id for h in hits]
    assert "a" in ids


async def test_filters_honored(index):
    await index.upsert("M-1", [VectorItem(id="x", vector=[1.0, 0.0], metadata={"matter_id": "M-1", "page": 4})])
    await index.upsert("M-1", [VectorItem(id="y", vector=[1.0, 0.0], metadata={"matter_id": "M-1", "page": 9})])
    hits = await index.search("M-1", [1.0, 0.0], top_k=10, filters={"page": 4})
    ids = [h.id for h in hits]
    assert "x" in ids and "y" not in ids


async def test_delete_collection(index):
    await index.upsert("M-2", [VectorItem(id="a", vector=[1.0], metadata={})])
    await index.delete_collection("M-2")
    hits = await index.search("M-2", [1.0], top_k=5)
    assert hits == []
