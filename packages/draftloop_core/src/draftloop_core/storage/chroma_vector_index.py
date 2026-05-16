"""ChromaVectorIndex — VectorIndex impl backed by persistent local Chroma.

One collection per ``matter_id`` enforces per-matter isolation.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

import chromadb

from draftloop_core.storage import VectorHit, VectorItem


class ChromaVectorIndex:
    def __init__(self, persist_path: str) -> None:
        Path(persist_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_path)

    def _collection(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(self, collection: str, items: list[VectorItem]) -> None:
        if not items:
            return
        col = self._collection(collection)

        def _do():
            # Chroma requires non-empty metadata per item; pad if caller supplied {}.
            metadatas = [(it.metadata or {"_": "1"}) for it in items]
            col.upsert(
                ids=[it.id for it in items],
                embeddings=[it.vector for it in items],
                metadatas=metadatas,
                documents=[it.document or "" for it in items],
            )

        await asyncio.to_thread(_do)

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        col = self._collection(collection)

        def _do():
            kwargs: dict[str, Any] = {
                "query_embeddings": [vector],
                "n_results": top_k,
            }
            if filters:
                kwargs["where"] = filters
            return col.query(**kwargs)

        try:
            res = await asyncio.to_thread(_do)
        except Exception:
            return []
        ids = (res.get("ids") or [[]])[0]
        distances = (res.get("distances") or [[]])[0]
        metadatas = (res.get("metadatas") or [[]])[0]
        documents = (res.get("documents") or [[]])[0]
        out: list[VectorHit] = []
        for i, did in enumerate(ids):
            distance = distances[i] if i < len(distances) else 0.0
            score = 1.0 - float(distance)
            out.append(
                VectorHit(
                    id=did,
                    score=score,
                    metadata=metadatas[i] if i < len(metadatas) else {},
                    document=documents[i] if i < len(documents) else None,
                )
            )
        return out

    async def delete_collection(self, collection: str) -> None:
        def _do():
            with contextlib.suppress(Exception):
                self._client.delete_collection(collection)

        await asyncio.to_thread(_do)
