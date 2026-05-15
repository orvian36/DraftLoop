from collections.abc import AsyncIterator
from typing import Any

from draftloop_core.storage import (
    BlobStore,
    DocumentStore,
    VectorHit,
    VectorIndex,
    VectorItem,
)


def test_protocols_declare_expected_methods():
    assert {"get", "put", "delete", "list"} <= set(dir(DocumentStore))
    assert {"upsert", "search", "delete_collection"} <= set(dir(VectorIndex))
    assert {"get", "put", "delete"} <= set(dir(BlobStore))


def test_vector_item_schema():
    item = VectorItem(id="c1", vector=[0.1, 0.2], metadata={"matter_id": "M-1"})
    assert item.id == "c1"
    assert item.vector == [0.1, 0.2]


def test_vector_hit_carries_score():
    hit = VectorHit(id="c1", score=0.83, metadata={"matter_id": "M-1"})
    assert hit.score == 0.83


def test_protocols_are_runtime_checkable():
    """Protocols should be @runtime_checkable so duck-typed impls can be asserted."""

    class FakeDS:
        async def get(self, key: str) -> Any: ...
        async def put(self, key: str, value: Any) -> None: ...
        async def delete(self, key: str) -> None: ...
        async def list(self, prefix: str = "") -> AsyncIterator[tuple[str, Any]]:
            if False:
                yield "", None

    inst = FakeDS()
    assert isinstance(inst, DocumentStore)
