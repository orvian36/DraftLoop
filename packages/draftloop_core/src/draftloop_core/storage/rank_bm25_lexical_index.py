"""RankBm25LexicalIndex — sparse retrieval impl using rank-bm25 + a pickle file per matter."""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi


_STATUTE_RE = re.compile(r"\d{1,3}\s+U\.?S\.?C\.?\s*§\s*\d+(?:\(\w+\))?")
_REPORTER_RE = re.compile(r"\d+\s+U\.?S\.?\s+\d+")


def _tokenize(text: str) -> list[str]:
    """Statute-aware tokenizer (duplicated from draftloop_retrieval to respect package boundaries)."""
    preserved: list[str] = []
    placeholders: dict[str, str] = {}

    def stash(m: re.Match) -> str:
        token = m.group(0).strip()
        placeholder = f"__CIT{len(preserved)}__"
        preserved.append(token)
        placeholders[placeholder] = token
        return placeholder

    cleaned = _STATUTE_RE.sub(stash, text)
    cleaned = _REPORTER_RE.sub(stash, cleaned)
    cleaned = re.sub(r"[^\w§_]+", " ", cleaned, flags=re.UNICODE)
    return [placeholders.get(t, t.lower()) for t in cleaned.split()]


@dataclass(frozen=True)
class LexicalDoc:
    id: str
    text: str


@dataclass(frozen=True)
class LexicalHit:
    id: str
    score: float
    text: str


class RankBm25LexicalIndex:
    def __init__(self, persist_path: str) -> None:
        self._root = Path(persist_path)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, collection: str) -> Path:
        return self._root / f"{collection}.bm25.pkl"

    def add(self, collection: str, docs: list[LexicalDoc]) -> None:
        existing = self._load(collection)
        all_docs = {d["id"]: d for d in existing}
        for d in docs:
            all_docs[d.id] = {"id": d.id, "text": d.text, "tokens": _tokenize(d.text)}
        payload = list(all_docs.values())
        with self._path(collection).open("wb") as f:
            pickle.dump(payload, f)

    def search(self, collection: str, query: str, top_k: int) -> list[LexicalHit]:
        docs = self._load(collection)
        if not docs:
            return []
        bm25 = BM25Okapi([d["tokens"] for d in docs])
        scores = bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(docs, scores, strict=True), key=lambda x: x[1], reverse=True)[:top_k]
        return [LexicalHit(id=d["id"], score=float(s), text=d["text"]) for d, s in ranked]

    def _load(self, collection: str) -> list[dict]:
        p = self._path(collection)
        if not p.exists():
            return []
        with p.open("rb") as f:
            return pickle.load(f)
