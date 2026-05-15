"""Reranker protocol + FlashReranker default."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from draftloop_core.llm import GeminiClient


@dataclass(frozen=True)
class RerankedItem:
    index: int
    score: float


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, *, query: str, candidates: list[str], top_k: int) -> list[RerankedItem]: ...


PROMPT = """Score each candidate 0.0-10.0 for relevance to the query.
Return ONLY a JSON array of objects: [{{"index": int, "score": float}}, ...]

Query: {query}

Candidates:
{candidates}
"""


class FlashReranker:
    def __init__(self, *, client: GeminiClient, model: str) -> None:
        self._client = client
        self._model = model

    def rerank(self, *, query: str, candidates: list[str], top_k: int) -> list[RerankedItem]:
        if not candidates:
            return []
        listed = "\n".join(f"[{i}] {c[:1500]}" for i, c in enumerate(candidates))
        resp = self._client.generate(
            model=self._model,
            contents=PROMPT.format(query=query, candidates=listed),
            config={"response_mime_type": "application/json"},
        )
        try:
            data = json.loads(resp.text)
        except Exception:
            return [RerankedItem(index=i, score=0.0) for i in range(min(top_k, len(candidates)))]
        items = [RerankedItem(index=int(r["index"]), score=float(r["score"])) for r in data]
        items.sort(key=lambda x: x.score, reverse=True)
        return items[:top_k]
