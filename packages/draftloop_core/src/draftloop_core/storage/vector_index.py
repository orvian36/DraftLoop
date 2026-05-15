"""VectorIndex protocol — embedding upsert + ANN search.

Default impl: Chroma local (added in Plan 2). Production swap: Qdrant.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class VectorItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    vector: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)
    document: str | None = None


class VectorHit(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    document: str | None = None


@runtime_checkable
class VectorIndex(Protocol):
    async def upsert(self, collection: str, items: list[VectorItem]) -> None: ...
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]: ...
    async def delete_collection(self, collection: str) -> None: ...
