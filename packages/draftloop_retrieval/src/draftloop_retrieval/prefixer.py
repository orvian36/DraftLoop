"""Anthropic-style Contextual Retrieval prefix generator (via Gemini Flash)."""

from __future__ import annotations

from draftloop_core.llm import GeminiClient

from draftloop_retrieval.types import Chunk

PREFIX_PROMPT = """Given the following chunk taken from a legal document, write a single
1-2 sentence prefix (50-100 tokens) that situates the chunk in the larger document.
Mention: document type, section, paragraph, and the main fact or claim.
Return ONLY the prefix text — no preamble.

Chunk:
\"\"\"
{chunk_text}
\"\"\"

Doc id: {doc_id} | Section: {section} | Page: {page}
"""


class ContextualPrefixer:
    def __init__(self, *, client: GeminiClient, model: str) -> None:
        self._client = client
        self._model = model

    def prefix(self, chunks: list[Chunk]) -> list[Chunk]:
        out: list[Chunk] = []
        for c in chunks:
            prompt = PREFIX_PROMPT.format(
                chunk_text=c.text[:1500],
                doc_id=c.doc_id,
                section=c.section_label or "n/a",
                page=c.page,
            )
            resp = self._client.generate(model=self._model, contents=prompt)
            blurb = (resp.text or "").strip()
            out.append(
                c.model_copy(
                    update={
                        "context_prefix": blurb,
                        "embedding_text": (blurb + "\n\n" + c.text).strip(),
                    }
                )
            )
        return out
