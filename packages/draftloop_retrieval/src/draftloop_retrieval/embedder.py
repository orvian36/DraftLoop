"""Batched Gemini embedder honoring the 100-input batch cap."""

from __future__ import annotations

from draftloop_core.llm import EMBED_BATCH_CAP, GeminiClient


class GeminiEmbedder:
    def __init__(self, *, client: GeminiClient, model: str, dim: int = 1536) -> None:
        self._client = client
        self._model = model
        self._dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_all(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed_all(texts, task_type="RETRIEVAL_QUERY")

    def _embed_all(self, texts: list[str], *, task_type: str) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH_CAP):
            batch = texts[i : i + EMBED_BATCH_CAP]
            out.extend(
                self._client.embed(
                    model=self._model,
                    contents=batch,
                    task_type=task_type,
                    output_dimensionality=self._dim,
                )
            )
        return out
