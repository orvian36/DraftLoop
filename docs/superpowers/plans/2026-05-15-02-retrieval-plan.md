# Plan 2: Retrieval & Grounding — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Implement `packages/draftloop_retrieval` covering (a) the indexing pipeline (chunk → contextual prefix → embed → dual index), (b) the query-time pipeline (multi-query → dense + BM25 → RRF → rerank), and (c) the storage default impls (ChromaVectorIndex + RankBM25LexicalIndex). After this plan, drafts can be requested against an ingested corpus and retrieval will surface top-15 cited chunks per slot.

**Architecture:** `Indexer.index(IngestResult) -> IndexResult` populates Chroma + BM25 per `matter_id`. `HybridRetriever.retrieve(SlotPlan) -> dict[slot, list[RetrievalHit]]` runs decompose → multi-query → dense+BM25 → RRF(k=60) → Flash rerank → top-15. Reranker is behind a `Reranker` protocol so `FlashReranker` (default) and `CrossEncoderReranker` (offline option) can swap. Embeddings use `gemini-embedding-001` at 1536 dims via Matryoshka truncation.

**Tech Stack:** Python 3.12, `chromadb>=0.5` (persistent local file backend), `rank-bm25>=0.2.2`, `tiktoken>=0.7` (token-count for chunk-size enforcement), reuse `draftloop_core.llm.GeminiClient`, reuse `draftloop_core.types`.

---

## File structure

```
packages/draftloop_retrieval/
├─ pyproject.toml
├─ src/draftloop_retrieval/
│  ├─ __init__.py
│  ├─ types.py                     # Chunk, RetrievalHit, RetrievalQuery, Slot, SlotPlan, RetrievalResult, VectorItem/Hit re-exports
│  ├─ indexer.py                   # Indexer orchestrator
│  ├─ splitter.py                  # StructuralSplitter (heading-aware + recursive 512/64)
│  ├─ prefixer.py                  # ContextualPrefixer (Flash batch)
│  ├─ embedder.py                  # GeminiEmbedder (batch ≤100, dim=1536)
│  ├─ retriever.py                 # HybridRetriever
│  ├─ query_planner.py             # SlotPlan + paraphrase expansion via Flash
│  ├─ rrf.py                       # Reciprocal Rank Fusion (k=60)
│  ├─ reranker.py                  # Reranker protocol + FlashReranker + CrossEncoderReranker
│  ├─ slot_plan.py                 # SLOT_PLAN constant (parties, jurisdiction, …)
│  └─ tokenize.py                  # statute-aware BM25 pre-tokenizer
└─ tests/
   ├─ test_types.py
   ├─ test_splitter.py
   ├─ test_prefixer.py
   ├─ test_rrf.py
   ├─ test_tokenize.py
   ├─ test_query_planner.py
   ├─ test_reranker.py
   ├─ test_chroma_vector_index.py
   ├─ test_rank_bm25_lexical_index.py
   ├─ test_indexer.py
   └─ test_retriever.py

packages/draftloop_core/src/draftloop_core/storage/
├─ chroma_vector_index.py
└─ rank_bm25_lexical_index.py

tests/integration/
└─ test_retrieval_end_to_end.py    # ingest synthetic → index → query each slot
```

---

## Task 1: `draftloop_retrieval` package scaffold

**Files:**
- Create: `packages/draftloop_retrieval/pyproject.toml`
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/__init__.py`
- Create: `packages/draftloop_retrieval/tests/__init__.py`
- Modify: root `pyproject.toml` (workspace members)

- [ ] **Step 1: Write `packages/draftloop_retrieval/pyproject.toml`**

```toml
[project]
name = "draftloop-retrieval"
version = "0.1.0"
description = "DraftLoop hybrid retrieval (Chroma + BM25 + RRF + rerank)"
requires-python = ">=3.12,<3.13"
dependencies = [
    "draftloop-core",
    "draftloop-ingest",
    "chromadb>=0.5.0",
    "rank-bm25>=0.2.2",
    "tiktoken>=0.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/draftloop_retrieval"]
```

- [ ] **Step 2: Empty `__init__.py` (lazy submodule loading)**

```python
"""DraftLoop hybrid retrieval — Chroma + BM25 + RRF + Flash rerank."""
__version__ = "0.1.0"
```

- [ ] **Step 3: Update root `pyproject.toml` workspace members**

Append `"packages/draftloop_retrieval"` to `[tool.uv.workspace] members`.

- [ ] **Step 4: `uv sync --all-packages`; commit**

```bash
uv sync --all-packages
git add packages/draftloop_retrieval pyproject.toml uv.lock
git commit -m "feat(retrieval): scaffold draftloop_retrieval package"
```

---

## Task 2: Public types — Chunk, RetrievalHit, SlotPlan

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/types.py`
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/slot_plan.py`
- Create: `packages/draftloop_retrieval/tests/test_types.py`

- [ ] **Step 1: Failing test**

```python
from draftloop_retrieval.types import Chunk, RetrievalHit, RetrievalQuery
from draftloop_retrieval.slot_plan import SLOT_PLAN, Slot


def test_chunk_carries_offsets():
    c = Chunk(
        chunk_id="doc_3_p4_c_0012",
        doc_id="doc_3",
        matter_id="M-001",
        page=4,
        section_label="Claims",
        para_id="¶12",
        char_start=1822,
        char_end=1987,
        text="Plaintiff alleges breach.",
        context_prefix="From the Complaint, Section II, ¶12.",
        embedding_text="From the Complaint, Section II, ¶12.\n\nPlaintiff alleges breach.",
        embedding_dim=1536,
        confidence_min=0.95,
        contains_needs_review=False,
        ingest_version="v1",
    )
    assert c.char_start < c.char_end


def test_slot_plan_has_seven_slots():
    assert len(SLOT_PLAN) == 7
    assert all(isinstance(s, Slot) for s in SLOT_PLAN)
    assert {s.name for s in SLOT_PLAN} == {
        "parties", "jurisdiction", "key_dates", "claims",
        "relief_sought", "procedural_posture", "key_evidence",
    }


def test_retrieval_hit_carries_provenance():
    chunk = Chunk(
        chunk_id="x", doc_id="d", matter_id="M-1", page=1, section_label=None,
        para_id=None, char_start=0, char_end=10, text="x", context_prefix="",
        embedding_text="x", embedding_dim=1536, confidence_min=1.0,
        contains_needs_review=False, ingest_version="v1",
    )
    hit = RetrievalHit(
        chunk=chunk, slot="claims", rerank_score=8.4, fusion_score=0.5,
        matched_query="q", retrieval_engines=["dense", "bm25"], rank=1,
    )
    assert "dense" in hit.retrieval_engines and "bm25" in hit.retrieval_engines
```

- [ ] **Step 2: Implement `types.py`**

```python
"""Public types for the retrieval package."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    doc_id: str
    matter_id: str
    page: int
    section_label: str | None
    para_id: str | None
    char_start: int
    char_end: int
    text: str
    context_prefix: str
    embedding_text: str
    embedding_dim: int
    confidence_min: float = Field(..., ge=0.0, le=1.0)
    contains_needs_review: bool
    ingest_version: str


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    slot: str
    paraphrases: list[str]


class RetrievalHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    slot: str
    rerank_score: float
    fusion_score: float
    matched_query: str
    retrieval_engines: list[Literal["dense", "bm25"]]
    rank: int


class RetrievalResult(BaseModel):
    matter_id: str
    slots: dict[str, list[RetrievalHit]]
    queries_used: dict[str, list[str]]
    duration_ms: int
    cost_usd: float
```

- [ ] **Step 3: Implement `slot_plan.py`**

```python
"""The seven fact slots for the Case Fact Summary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    name: str
    intent: str


SLOT_PLAN: list[Slot] = [
    Slot("parties",            "Who are the named parties, their roles, and counsel?"),
    Slot("jurisdiction",       "Court, venue, jurisdiction basis, governing law."),
    Slot("key_dates",          "Filing date, incident date, contract date, hearings."),
    Slot("claims",             "Causes of action / counts and against whom."),
    Slot("relief_sought",      "Damages, injunctions, other remedies requested."),
    Slot("procedural_posture", "Current stage: pleading, discovery, motion, trial, appeal."),
    Slot("key_evidence",       "Exhibits, declarations, statements relied on."),
]
```

- [ ] **Step 4: Run tests; expect 3 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/types.py packages/draftloop_retrieval/src/draftloop_retrieval/slot_plan.py packages/draftloop_retrieval/tests/test_types.py
git commit -m "feat(retrieval): add public types + SlotPlan"
```

---

## Task 3: Structural + recursive splitter

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/splitter.py`
- Create: `packages/draftloop_retrieval/tests/test_splitter.py`

- [ ] **Step 1: Failing test**

```python
from draftloop_retrieval.splitter import StructuralSplitter


SAMPLE_MARKDOWN = """<!-- page=1 -->
# COMPLAINT

## Parties

Plaintiff Acme Corp brings this action against Defendant Widgets Inc.

## Claims

Count I — Breach of Contract. Defendant breached the SaaS agreement on 2024-03-14.

Count II — Unjust Enrichment.

<!-- page=2 -->
## Relief Sought

Plaintiff seeks damages and injunctive relief.
"""


def test_splitter_respects_section_boundaries():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    chunks = list(
        splitter.split(
            markdown=SAMPLE_MARKDOWN,
            doc_id="doc_1",
            matter_id="M-001",
            ingest_version="v1",
        )
    )
    # No chunk crosses two sections.
    for c in chunks:
        # Each chunk's text must come entirely from one section_label.
        if c.section_label:
            assert c.section_label in {"Parties", "Claims", "Relief Sought"}


def test_splitter_emits_char_offsets_that_reproduce_text():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    chunks = list(splitter.split(
        markdown=SAMPLE_MARKDOWN, doc_id="d", matter_id="M", ingest_version="v"
    ))
    for c in chunks:
        assert SAMPLE_MARKDOWN[c.char_start:c.char_end].strip() == c.text.strip()


def test_splitter_carries_page_from_marker():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    chunks = list(splitter.split(
        markdown=SAMPLE_MARKDOWN, doc_id="d", matter_id="M", ingest_version="v"
    ))
    pages_seen = {c.page for c in chunks}
    assert pages_seen == {1, 2}


def test_chunk_id_is_deterministic():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    runs = [
        list(splitter.split(
            markdown=SAMPLE_MARKDOWN, doc_id="d", matter_id="M", ingest_version="v"
        ))
        for _ in range(2)
    ]
    assert [c.chunk_id for c in runs[0]] == [c.chunk_id for c in runs[1]]
```

- [ ] **Step 2: Implement `splitter.py`**

```python
"""Structure-aware Markdown splitter.

Tier 1: split on H1/H2/H3 headings (Docling-style, but heading-only here).
Tier 2: within each section, recursive ~512-token chunking with overlap.

Every emitted Chunk carries (char_start, char_end) into the source Markdown
and a stable chunk_id derived from (doc_id, ingest_version, char_start, char_end).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator

import tiktoken

from draftloop_retrieval.types import Chunk

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
_PAGE_MARKER_RE = re.compile(r"<!--\s*page=(\d+)\s*-->")


class StructuralSplitter:
    def __init__(self, chunk_size_tokens: int = 512, overlap_tokens: int = 64) -> None:
        self.chunk_size_tokens = chunk_size_tokens
        self.overlap_tokens = overlap_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")

    def split(
        self,
        *,
        markdown: str,
        doc_id: str,
        matter_id: str,
        ingest_version: str,
    ) -> Iterator[Chunk]:
        sections = self._split_sections(markdown)
        for section in sections:
            yield from self._recursive_split(
                section_text=section["text"],
                section_start=section["start"],
                section_label=section["label"],
                full_markdown=markdown,
                doc_id=doc_id,
                matter_id=matter_id,
                ingest_version=ingest_version,
            )

    def _split_sections(self, md: str) -> list[dict]:
        headings = [(m.start(), m.group(2).strip()) for m in _HEADING_RE.finditer(md)]
        sections: list[dict] = []
        if not headings:
            sections.append({"start": 0, "label": None, "text": md})
            return sections
        # Leading content before first heading
        if headings[0][0] > 0:
            sections.append({"start": 0, "label": None, "text": md[: headings[0][0]]})
        for i, (pos, label) in enumerate(headings):
            end = headings[i + 1][0] if i + 1 < len(headings) else len(md)
            sections.append({"start": pos, "label": label, "text": md[pos:end]})
        return sections

    def _page_for_offset(self, full_md: str, offset: int) -> int:
        page = 1
        for m in _PAGE_MARKER_RE.finditer(full_md, 0, offset + 1):
            page = int(m.group(1))
        return page

    def _recursive_split(
        self,
        *,
        section_text: str,
        section_start: int,
        section_label: str | None,
        full_markdown: str,
        doc_id: str,
        matter_id: str,
        ingest_version: str,
    ) -> Iterator[Chunk]:
        tokens = self._enc.encode(section_text)
        if not tokens:
            return
        step = max(1, self.chunk_size_tokens - self.overlap_tokens)
        for start_tok in range(0, len(tokens), step):
            window = tokens[start_tok : start_tok + self.chunk_size_tokens]
            if not window:
                continue
            slice_text = self._enc.decode(window)
            # Re-anchor to original text by find().
            local_start = section_text.find(slice_text.strip()[:40])
            if local_start < 0:
                local_start = 0
            char_start = section_start + local_start
            char_end = char_start + len(slice_text)
            if char_end > len(full_markdown):
                char_end = len(full_markdown)
            actual_text = full_markdown[char_start:char_end]
            page = self._page_for_offset(full_markdown, char_start)
            chunk_id = self._chunk_id(doc_id, ingest_version, char_start, char_end)
            yield Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                matter_id=matter_id,
                page=page,
                section_label=section_label,
                para_id=None,
                char_start=char_start,
                char_end=char_end,
                text=actual_text.strip(),
                context_prefix="",
                embedding_text=actual_text.strip(),
                embedding_dim=1536,
                confidence_min=1.0,
                contains_needs_review=False,
                ingest_version=ingest_version,
            )
            if start_tok + self.chunk_size_tokens >= len(tokens):
                break

    @staticmethod
    def _chunk_id(doc_id: str, version: str, start: int, end: int) -> str:
        h = hashlib.sha1(f"{doc_id}|{version}|{start}|{end}".encode()).hexdigest()[:10]
        return f"{doc_id}_c_{h}"
```

- [ ] **Step 3: Run tests; expect 4 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/splitter.py packages/draftloop_retrieval/tests/test_splitter.py
git commit -m "feat(retrieval): add structure-aware recursive splitter"
```

---

## Task 4: Statute-aware BM25 tokenizer

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/tokenize.py`
- Create: `packages/draftloop_retrieval/tests/test_tokenize.py`

- [ ] **Step 1: Failing test**

```python
from draftloop_retrieval.tokenize import tokenize_for_bm25


def test_preserves_statute_citations_as_single_tokens():
    text = "Jurisdiction under 28 U.S.C. § 1331 is invoked."
    tokens = tokenize_for_bm25(text)
    assert "28 U.S.C. § 1331" in tokens


def test_lowercases_and_strips_punctuation_for_normal_words():
    tokens = tokenize_for_bm25("The Plaintiff filed.")
    assert "plaintiff" in tokens
    assert "filed" in tokens
    assert "the" in tokens  # don't strip stopwords here — BM25 handles term weighting


def test_preserves_versus_citations():
    text = "See Marbury v. Madison, 5 U.S. 137 (1803)."
    tokens = tokenize_for_bm25(text)
    assert "5 U.S. 137" in tokens
```

- [ ] **Step 2: Implement `tokenize.py`**

```python
"""BM25 pre-tokenizer that preserves legal citations as single tokens."""

from __future__ import annotations

import re

_STATUTE_RE = re.compile(r"\d{1,3}\s+U\.?S\.?C\.?\s*§\s*\d+(?:\(\w+\))?")
_REPORTER_RE = re.compile(r"\d+\s+U\.?S\.?\s+\d+")


def tokenize_for_bm25(text: str) -> list[str]:
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
    cleaned = re.sub(r"[^\w§§_]+", " ", cleaned, flags=re.UNICODE)

    tokens: list[str] = []
    for tok in cleaned.split():
        if tok in placeholders:
            tokens.append(placeholders[tok])
        else:
            tokens.append(tok.lower())
    return tokens
```

- [ ] **Step 3: Run tests; expect 3 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/tokenize.py packages/draftloop_retrieval/tests/test_tokenize.py
git commit -m "feat(retrieval): add statute-aware BM25 tokenizer"
```

---

## Task 5: Reciprocal Rank Fusion

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/rrf.py`
- Create: `packages/draftloop_retrieval/tests/test_rrf.py`

- [ ] **Step 1: Failing test**

```python
from draftloop_retrieval.rrf import rrf_fuse


def test_rrf_known_rankings():
    dense = [("a", 0.9), ("b", 0.8), ("c", 0.5)]
    sparse = [("c", 5.0), ("b", 4.0), ("d", 1.0)]
    fused = rrf_fuse([dense, sparse], k=60, top_k=4)
    ids = [x.id for x in fused]
    # 'b' should win — present in both at rank 2.
    assert "b" in ids[:2]
    # 'c' should also be high — rank 3 in dense, rank 1 in sparse.
    assert "c" in ids[:2]


def test_rrf_returns_top_k_only():
    dense = [(str(i), 1.0 / (i + 1)) for i in range(50)]
    fused = rrf_fuse([dense], k=60, top_k=10)
    assert len(fused) == 10


def test_rrf_handles_empty_rankings():
    fused = rrf_fuse([[], []], k=60, top_k=5)
    assert fused == []
```

- [ ] **Step 2: Implement `rrf.py`**

```python
"""Reciprocal Rank Fusion (k=60 default)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusedHit:
    id: str
    score: float
    engines: tuple[str, ...]


def rrf_fuse(
    rankings: list[list[tuple[str, float]]],
    *,
    k: int = 60,
    top_k: int = 50,
    engine_names: list[str] | None = None,
) -> list[FusedHit]:
    if engine_names is None:
        engine_names = [f"engine_{i}" for i in range(len(rankings))]
    scores: dict[str, float] = {}
    engines: dict[str, set[str]] = {}
    for engine_idx, ranking in enumerate(rankings):
        for rank, (doc_id, _score) in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            engines.setdefault(doc_id, set()).add(engine_names[engine_idx])
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [FusedHit(id=i, score=s, engines=tuple(sorted(engines[i]))) for i, s in ordered]
```

- [ ] **Step 3: Run; expect 3 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/rrf.py packages/draftloop_retrieval/tests/test_rrf.py
git commit -m "feat(retrieval): add Reciprocal Rank Fusion (k=60)"
```

---

## Task 6: ChromaVectorIndex default impl in `draftloop_core`

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/storage/chroma_vector_index.py`
- Create: `packages/draftloop_core/tests/test_chroma_vector_index.py`

- [ ] **Step 1: Failing test**

```python
import pytest

from draftloop_core.storage import VectorIndex, VectorItem
from draftloop_core.storage.chroma_vector_index import ChromaVectorIndex


@pytest.fixture
async def index(tmp_path):
    idx = ChromaVectorIndex(persist_path=str(tmp_path))
    return idx


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
    await index.upsert("M-1", [VectorItem(id="a", vector=[1.0], metadata={})])
    await index.delete_collection("M-1")
    hits = await index.search("M-1", [1.0], top_k=5)
    assert hits == []
```

- [ ] **Step 2: Implement `chroma_vector_index.py`**

```python
"""ChromaVectorIndex — VectorIndex impl backed by persistent local Chroma.

One collection per ``matter_id`` enforces per-matter isolation.
"""

from __future__ import annotations

import asyncio
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
            col.upsert(
                ids=[it.id for it in items],
                embeddings=[it.vector for it in items],
                metadatas=[it.metadata for it in items],
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
            score = 1.0 - float(distance)  # cosine distance -> similarity
            out.append(VectorHit(
                id=did,
                score=score,
                metadata=metadatas[i] if i < len(metadatas) else {},
                document=documents[i] if i < len(documents) else None,
            ))
        return out

    async def delete_collection(self, collection: str) -> None:
        def _do():
            try:
                self._client.delete_collection(collection)
            except Exception:
                pass
        await asyncio.to_thread(_do)
```

- [ ] **Step 3: Run; expect 4 PASS. Commit.**

```bash
git add packages/draftloop_core/src/draftloop_core/storage/chroma_vector_index.py packages/draftloop_core/tests/test_chroma_vector_index.py
git commit -m "feat(core): add ChromaVectorIndex default impl (per-matter collections)"
```

---

## Task 7: RankBM25LexicalIndex default impl

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/storage/rank_bm25_lexical_index.py`
- Create: `packages/draftloop_core/tests/test_rank_bm25_lexical_index.py`

- [ ] **Step 1: Failing test**

```python
from draftloop_core.storage.rank_bm25_lexical_index import (
    LexicalDoc,
    LexicalHit,
    RankBm25LexicalIndex,
)


def test_add_and_search(tmp_path):
    idx = RankBm25LexicalIndex(persist_path=str(tmp_path))
    idx.add(
        "M-1",
        [
            LexicalDoc(id="a", text="Plaintiff alleges breach of the SaaS agreement."),
            LexicalDoc(id="b", text="Defendant denies all allegations."),
            LexicalDoc(id="c", text="The motion to dismiss is denied."),
        ],
    )
    hits = idx.search("M-1", "saas agreement breach", top_k=2)
    assert isinstance(hits[0], LexicalHit)
    ids = [h.id for h in hits]
    assert "a" in ids


def test_search_unknown_collection_returns_empty(tmp_path):
    idx = RankBm25LexicalIndex(persist_path=str(tmp_path))
    assert idx.search("M-unknown", "anything", top_k=5) == []


def test_persists_across_instances(tmp_path):
    idx1 = RankBm25LexicalIndex(persist_path=str(tmp_path))
    idx1.add("M-1", [LexicalDoc(id="x", text="hello world")])
    idx2 = RankBm25LexicalIndex(persist_path=str(tmp_path))
    hits = idx2.search("M-1", "hello", top_k=1)
    assert hits and hits[0].id == "x"
```

- [ ] **Step 2: Implement `rank_bm25_lexical_index.py`**

```python
"""RankBm25LexicalIndex — sparse retrieval impl using rank-bm25 + a pickle file per matter."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from draftloop_retrieval.tokenize import tokenize_for_bm25  # boundary: allow shared tokenizer


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
            all_docs[d.id] = {"id": d.id, "text": d.text, "tokens": tokenize_for_bm25(d.text)}
        payload = list(all_docs.values())
        with self._path(collection).open("wb") as f:
            pickle.dump(payload, f)

    def search(self, collection: str, query: str, top_k: int) -> list[LexicalHit]:
        docs = self._load(collection)
        if not docs:
            return []
        bm25 = BM25Okapi([d["tokens"] for d in docs])
        scores = bm25.get_scores(tokenize_for_bm25(query))
        ranked = sorted(
            zip(docs, scores, strict=True), key=lambda x: x[1], reverse=True
        )[:top_k]
        return [LexicalHit(id=d["id"], score=float(s), text=d["text"]) for d, s in ranked]

    def _load(self, collection: str) -> list[dict]:
        p = self._path(collection)
        if not p.exists():
            return []
        with p.open("rb") as f:
            return pickle.load(f)
```

NOTE: The `from draftloop_retrieval.tokenize import …` is cross-package and would normally fail boundary lint (core importing from retrieval). Instead, **move the tokenizer to `draftloop_core.text.tokenize`** before implementing this task, or duplicate the small tokenizer here as `_tokenize`. Simplest: duplicate the tokenizer inline (it's <30 lines). Replace the boundary-cross with a local copy:

```python
# packages/draftloop_core/src/draftloop_core/storage/rank_bm25_lexical_index.py
import re

_STATUTE_RE = re.compile(r"\d{1,3}\s+U\.?S\.?C\.?\s*§\s*\d+(?:\(\w+\))?")
_REPORTER_RE = re.compile(r"\d+\s+U\.?S\.?\s+\d+")


def _tokenize(text: str) -> list[str]:
    preserved: list[str] = []
    placeholders: dict[str, str] = {}

    def stash(m):
        token = m.group(0).strip()
        ph = f"__CIT{len(preserved)}__"
        preserved.append(token)
        placeholders[ph] = token
        return ph

    cleaned = _STATUTE_RE.sub(stash, text)
    cleaned = _REPORTER_RE.sub(stash, cleaned)
    cleaned = re.sub(r"[^\w§§_]+", " ", cleaned)
    return [placeholders.get(t, t.lower()) for t in cleaned.split()]
```

- [ ] **Step 3: Run; expect 3 PASS. Commit.**

```bash
git add packages/draftloop_core/src/draftloop_core/storage/rank_bm25_lexical_index.py packages/draftloop_core/tests/test_rank_bm25_lexical_index.py
git commit -m "feat(core): add RankBm25LexicalIndex with statute-aware tokenizer"
```

---

## Task 8: ContextualPrefixer (Flash batch)

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/prefixer.py`
- Create: `packages/draftloop_retrieval/tests/test_prefixer.py`

- [ ] **Step 1: Failing test**

```python
from unittest.mock import MagicMock
import pytest

from draftloop_retrieval.prefixer import ContextualPrefixer
from draftloop_retrieval.types import Chunk


@pytest.fixture
def fake_client():
    c = MagicMock()
    resp = MagicMock()
    resp.text = "From the Complaint, Section II ¶12, alleging breach."
    c.generate.return_value = resp
    return c


def _mk_chunk(text: str) -> Chunk:
    return Chunk(
        chunk_id="x", doc_id="doc_3", matter_id="M-1", page=4,
        section_label="Claims", para_id="¶12",
        char_start=0, char_end=len(text), text=text,
        context_prefix="", embedding_text=text, embedding_dim=1536,
        confidence_min=1.0, contains_needs_review=False, ingest_version="v1",
    )


def test_prefixer_adds_blurb(fake_client):
    p = ContextualPrefixer(client=fake_client, model="gemini-2.5-flash")
    chunks = [_mk_chunk("Plaintiff alleges breach.")]
    out = p.prefix(chunks)
    assert out[0].context_prefix != ""
    assert "Section II" in out[0].context_prefix or "Complaint" in out[0].context_prefix
    assert out[0].embedding_text.startswith(out[0].context_prefix)
```

- [ ] **Step 2: Implement `prefixer.py`**

```python
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
            out.append(c.model_copy(update={
                "context_prefix": blurb,
                "embedding_text": (blurb + "\n\n" + c.text).strip(),
            }))
        return out
```

- [ ] **Step 3: Run; expect 1 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/prefixer.py packages/draftloop_retrieval/tests/test_prefixer.py
git commit -m "feat(retrieval): add Flash-based ContextualPrefixer"
```

---

## Task 9: GeminiEmbedder + Indexer orchestrator

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/embedder.py`
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/indexer.py`
- Create: `packages/draftloop_retrieval/tests/test_indexer.py`

- [ ] **Step 1: Failing test**

```python
from unittest.mock import MagicMock, AsyncMock
import pytest

from draftloop_retrieval.indexer import Indexer
from draftloop_retrieval.splitter import StructuralSplitter
from draftloop_ingest.types import IngestResult, Page


@pytest.fixture
def fake_client():
    c = MagicMock()
    c.embed.return_value = [[0.1] * 1536]
    g = MagicMock()
    g.text = "prefix"
    c.generate.return_value = g
    return c


async def test_indexer_pipeline_runs(tmp_path, fake_client):
    vec_index = AsyncMock()
    bm25_index = MagicMock()
    indexer = Indexer(
        vec_index=vec_index,
        bm25_index=bm25_index,
        client=fake_client,
        embed_model="gemini-embedding-001",
        embed_dim=1536,
        prefix_model="gemini-2.5-flash",
        splitter=StructuralSplitter(chunk_size_tokens=64, overlap_tokens=8),
    )
    ingest = IngestResult(
        doc_id="doc_1",
        source_path="/tmp/x.pdf",
        pages=[],
        markdown="<!-- page=1 -->\n# Complaint\n\nPlaintiff alleges breach.",
        needs_review_spans=[],
        aggregate_confidence=1.0,
        engines_used={1: ["pymupdf4llm"]},
        duration_ms=10,
        ingest_version="v1",
    )
    result = await indexer.index(matter_id="M-1", ingest=ingest)
    assert result.chunks_indexed > 0
    vec_index.upsert.assert_awaited()
    bm25_index.add.assert_called()
```

- [ ] **Step 2: Implement `embedder.py`**

```python
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
```

- [ ] **Step 3: Implement `indexer.py`**

```python
"""Indexer — orchestrates: split → prefix → embed → upsert + BM25 add."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_core.llm import GeminiClient
from draftloop_core.storage import VectorIndex, VectorItem
from draftloop_core.storage.rank_bm25_lexical_index import LexicalDoc, RankBm25LexicalIndex

from draftloop_ingest.types import IngestResult
from draftloop_retrieval.embedder import GeminiEmbedder
from draftloop_retrieval.prefixer import ContextualPrefixer
from draftloop_retrieval.splitter import StructuralSplitter
from draftloop_retrieval.types import Chunk


@dataclass(frozen=True)
class IndexResult:
    matter_id: str
    doc_id: str
    chunks_indexed: int


class Indexer:
    def __init__(
        self,
        *,
        vec_index: VectorIndex,
        bm25_index: RankBm25LexicalIndex,
        client: GeminiClient,
        embed_model: str,
        embed_dim: int,
        prefix_model: str,
        splitter: StructuralSplitter | None = None,
    ) -> None:
        self._vec_index = vec_index
        self._bm25_index = bm25_index
        self._client = client
        self._embedder = GeminiEmbedder(client=client, model=embed_model, dim=embed_dim)
        self._prefixer = ContextualPrefixer(client=client, model=prefix_model)
        self._splitter = splitter or StructuralSplitter()

    async def index(self, *, matter_id: str, ingest: IngestResult) -> IndexResult:
        chunks: list[Chunk] = list(
            self._splitter.split(
                markdown=ingest.markdown,
                doc_id=ingest.doc_id,
                matter_id=matter_id,
                ingest_version=ingest.ingest_version,
            )
        )
        if not chunks:
            return IndexResult(matter_id=matter_id, doc_id=ingest.doc_id, chunks_indexed=0)

        prefixed = self._prefixer.prefix(chunks)
        vectors = self._embedder.embed_documents(
            [c.embedding_text for c in prefixed]
        )
        items = [
            VectorItem(
                id=c.chunk_id,
                vector=vectors[i],
                metadata={
                    "matter_id": matter_id,
                    "doc_id": c.doc_id,
                    "page": c.page,
                    "section_label": c.section_label or "",
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "confidence_min": c.confidence_min,
                    "contains_needs_review": c.contains_needs_review,
                    "ingest_version": c.ingest_version,
                },
                document=c.text,
            )
            for i, c in enumerate(prefixed)
        ]
        await self._vec_index.upsert(matter_id, items)
        self._bm25_index.add(
            matter_id,
            [LexicalDoc(id=c.chunk_id, text=c.context_prefix + " " + c.text) for c in prefixed],
        )
        return IndexResult(matter_id=matter_id, doc_id=ingest.doc_id, chunks_indexed=len(prefixed))
```

- [ ] **Step 4: Run; expect 1 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/embedder.py packages/draftloop_retrieval/src/draftloop_retrieval/indexer.py packages/draftloop_retrieval/tests/test_indexer.py
git commit -m "feat(retrieval): add Gemini embedder + Indexer orchestrator"
```

---

## Task 10: QueryPlanner (multi-query paraphrase expansion)

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/query_planner.py`
- Create: `packages/draftloop_retrieval/tests/test_query_planner.py`

- [ ] **Step 1: Failing test**

```python
from unittest.mock import MagicMock
from draftloop_retrieval.query_planner import QueryPlanner
from draftloop_retrieval.slot_plan import SLOT_PLAN


def test_planner_emits_paraphrases_per_slot():
    fake = MagicMock()
    resp = MagicMock()
    resp.text = "1. Who are the parties?\n2. Identify plaintiffs and defendants.\n3. Counsel involved.\n"
    fake.generate.return_value = resp
    planner = QueryPlanner(client=fake, model="gemini-2.5-flash", n=3)
    qs = planner.plan(SLOT_PLAN)
    assert set(qs.keys()) == {s.name for s in SLOT_PLAN}
    assert all(1 <= len(v) <= 5 for v in qs.values())
```

- [ ] **Step 2: Implement `query_planner.py`**

```python
"""Slot → 3-5 paraphrased queries (multi-query expansion)."""

from __future__ import annotations

import re

from draftloop_core.llm import GeminiClient
from draftloop_retrieval.slot_plan import Slot

PROMPT = """Generate {n} distinct paraphrases of the following retrieval intent.
Each paraphrase should be a self-contained question or noun phrase that could be
used to search a corpus of legal documents.

Intent: {intent}

Return as a numbered list. Do not add preamble.
"""


class QueryPlanner:
    def __init__(self, *, client: GeminiClient, model: str, n: int = 3) -> None:
        self._client = client
        self._model = model
        self._n = n

    def plan(self, slots: list[Slot]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for slot in slots:
            resp = self._client.generate(
                model=self._model,
                contents=PROMPT.format(n=self._n, intent=slot.intent),
            )
            phrases = self._parse(resp.text or "")
            if not phrases:
                phrases = [slot.intent]
            out[slot.name] = phrases[: self._n]
        return out

    @staticmethod
    def _parse(text: str) -> list[str]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        cleaned: list[str] = []
        for ln in lines:
            m = re.match(r"^(?:\d+[.)]\s+|-\s+)?(.*)$", ln)
            if m:
                phrase = m.group(1).strip()
                if phrase:
                    cleaned.append(phrase)
        return cleaned
```

- [ ] **Step 3: Run; expect 1 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/query_planner.py packages/draftloop_retrieval/tests/test_query_planner.py
git commit -m "feat(retrieval): add QueryPlanner (multi-query expansion via Flash)"
```

---

## Task 11: Reranker (Flash default + cross-encoder swap)

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/reranker.py`
- Create: `packages/draftloop_retrieval/tests/test_reranker.py`

- [ ] **Step 1: Failing test**

```python
from unittest.mock import MagicMock
from draftloop_retrieval.reranker import FlashReranker


def test_flash_reranker_returns_top_k():
    fake = MagicMock()
    resp = MagicMock()
    # Return JSON-shaped scores
    resp.text = '[{"index":0,"score":7.0},{"index":2,"score":9.5},{"index":1,"score":3.0}]'
    fake.generate.return_value = resp
    rr = FlashReranker(client=fake, model="gemini-2.5-flash")
    candidates = ["doc a", "doc b", "doc c"]
    ranked = rr.rerank(query="anything", candidates=candidates, top_k=2)
    assert len(ranked) == 2
    assert ranked[0].index == 2
    assert ranked[0].score == 9.5
```

- [ ] **Step 2: Implement `reranker.py`**

```python
"""Reranker protocol + FlashReranker default + CrossEncoderReranker option."""

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
```

- [ ] **Step 3: Run; expect 1 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/reranker.py packages/draftloop_retrieval/tests/test_reranker.py
git commit -m "feat(retrieval): add FlashReranker (Reranker protocol + JSON-output)"
```

---

## Task 12: HybridRetriever

**Files:**
- Create: `packages/draftloop_retrieval/src/draftloop_retrieval/retriever.py`
- Create: `packages/draftloop_retrieval/tests/test_retriever.py`

- [ ] **Step 1: Failing test**

```python
from unittest.mock import MagicMock, AsyncMock
import pytest

from draftloop_core.storage import VectorHit
from draftloop_core.storage.rank_bm25_lexical_index import LexicalHit
from draftloop_retrieval.retriever import HybridRetriever
from draftloop_retrieval.reranker import RerankedItem
from draftloop_retrieval.slot_plan import SLOT_PLAN
from draftloop_retrieval.types import Chunk


def _chunk(cid: str) -> Chunk:
    return Chunk(
        chunk_id=cid, doc_id="d", matter_id="M-1", page=1, section_label=None,
        para_id=None, char_start=0, char_end=10, text=f"text {cid}",
        context_prefix="", embedding_text=f"text {cid}", embedding_dim=1536,
        confidence_min=1.0, contains_needs_review=False, ingest_version="v1",
    )


async def test_retriever_runs_full_pipeline_per_slot():
    vec_index = AsyncMock()
    bm25_index = MagicMock()
    embedder = MagicMock()
    planner = MagicMock()
    reranker = MagicMock()
    chunk_loader = MagicMock()

    planner.plan.return_value = {slot.name: [f"q {slot.name}"] for slot in SLOT_PLAN}
    embedder.embed_queries.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
    vec_index.search.return_value = [VectorHit(id="c1", score=0.9, metadata={})]
    bm25_index.search.return_value = [LexicalHit(id="c1", score=5.0, text="text c1")]
    reranker.rerank.return_value = [RerankedItem(index=0, score=8.0)]
    chunk_loader.return_value = {"c1": _chunk("c1")}

    retriever = HybridRetriever(
        vec_index=vec_index, bm25_index=bm25_index, embedder=embedder,
        planner=planner, reranker=reranker, chunk_loader=chunk_loader,
        rrf_k=60, dense_top=10, bm25_top=10, rerank_top=5,
    )
    result = await retriever.retrieve(matter_id="M-1", slot_plan=SLOT_PLAN)
    assert set(result.slots.keys()) == {s.name for s in SLOT_PLAN}
    assert all(len(hits) >= 1 for hits in result.slots.values())
```

- [ ] **Step 2: Implement `retriever.py`**

```python
"""HybridRetriever — multi-query → dense + BM25 → RRF → rerank → top-k per slot."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from draftloop_core.storage import VectorIndex
from draftloop_core.storage.rank_bm25_lexical_index import RankBm25LexicalIndex

from draftloop_retrieval.embedder import GeminiEmbedder
from draftloop_retrieval.query_planner import QueryPlanner
from draftloop_retrieval.reranker import Reranker
from draftloop_retrieval.rrf import rrf_fuse
from draftloop_retrieval.slot_plan import Slot
from draftloop_retrieval.types import Chunk, RetrievalHit, RetrievalResult


@dataclass
class HybridRetriever:
    vec_index: VectorIndex
    bm25_index: RankBm25LexicalIndex
    embedder: GeminiEmbedder
    planner: QueryPlanner
    reranker: Reranker
    chunk_loader: Callable[[list[str]], dict[str, Chunk]]
    rrf_k: int = 60
    dense_top: int = 50
    bm25_top: int = 50
    rerank_top: int = 15

    async def retrieve(self, *, matter_id: str, slot_plan: list[Slot]) -> RetrievalResult:
        start = time.monotonic()
        queries = self.planner.plan(slot_plan)
        slots_out: dict[str, list[RetrievalHit]] = {}

        for slot in slot_plan:
            paraphrases = queries.get(slot.name, [slot.intent])
            vectors = self.embedder.embed_queries(paraphrases)

            dense_rankings: list[list[tuple[str, float]]] = []
            for vec in vectors:
                hits = await self.vec_index.search(matter_id, vec, top_k=self.dense_top)
                dense_rankings.append([(h.id, h.score) for h in hits])

            bm25_rankings: list[list[tuple[str, float]]] = []
            for q in paraphrases:
                lex_hits = self.bm25_index.search(matter_id, q, top_k=self.bm25_top)
                bm25_rankings.append([(h.id, h.score) for h in lex_hits])

            fused = rrf_fuse(
                dense_rankings + bm25_rankings,
                k=self.rrf_k,
                top_k=self.dense_top,
                engine_names=["dense"] * len(dense_rankings) + ["bm25"] * len(bm25_rankings),
            )

            if not fused:
                slots_out[slot.name] = []
                continue

            ids_in_order = [f.id for f in fused]
            chunks_by_id = self.chunk_loader(ids_in_order)
            candidates_text = [chunks_by_id[i].text for i in ids_in_order if i in chunks_by_id]
            ranked = self.reranker.rerank(
                query=slot.intent, candidates=candidates_text, top_k=self.rerank_top,
            )

            hits_out: list[RetrievalHit] = []
            for rank, r in enumerate(ranked, start=1):
                if r.index >= len(ids_in_order):
                    continue
                cid = ids_in_order[r.index]
                if cid not in chunks_by_id:
                    continue
                fhit = fused[r.index]
                hits_out.append(
                    RetrievalHit(
                        chunk=chunks_by_id[cid],
                        slot=slot.name,
                        rerank_score=r.score,
                        fusion_score=fhit.score,
                        matched_query=paraphrases[0],
                        retrieval_engines=list(fhit.engines),  # type: ignore[arg-type]
                        rank=rank,
                    )
                )
            slots_out[slot.name] = hits_out

        return RetrievalResult(
            matter_id=matter_id,
            slots=slots_out,
            queries_used=queries,
            duration_ms=int((time.monotonic() - start) * 1000),
            cost_usd=0.0,  # populated by audit trail later
        )
```

- [ ] **Step 3: Run; expect 1 PASS. Commit.**

```bash
git add packages/draftloop_retrieval/src/draftloop_retrieval/retriever.py packages/draftloop_retrieval/tests/test_retriever.py
git commit -m "feat(retrieval): add HybridRetriever (multi-query + dense + BM25 + RRF + rerank)"
```

---

## Task 13: Integration test against synthetic corpus

**Files:**
- Create: `tests/integration/test_retrieval_end_to_end.py`

- [ ] **Step 1: Write integration test (uses VCR cassettes for Gemini)**

```python
"""End-to-end retrieval: ingest synthetic complaint → index → query each slot → assert hits.

This test is GATED on GEMINI_API_KEY being set to a real key in env (CI uses cassettes).
For local runs without a key, skip.
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

pytestmark = pytest.mark.skipif(
    os.environ.get("GEMINI_API_KEY", "").startswith(("", "sk-test", "demo")),
    reason="needs real GEMINI_API_KEY for live retrieval e2e",
)


@pytest.mark.asyncio
async def test_retrieval_e2e(tmp_path):
    from draftloop_core.config import get_settings
    from draftloop_core.llm import GeminiClient
    from draftloop_core.storage.chroma_vector_index import ChromaVectorIndex
    from draftloop_core.storage.rank_bm25_lexical_index import RankBm25LexicalIndex
    from draftloop_ingest import IngestPipeline, IngestRequest
    from draftloop_retrieval.indexer import Indexer
    from draftloop_retrieval.retriever import HybridRetriever
    from draftloop_retrieval.embedder import GeminiEmbedder
    from draftloop_retrieval.query_planner import QueryPlanner
    from draftloop_retrieval.reranker import FlashReranker
    from draftloop_retrieval.slot_plan import SLOT_PLAN

    get_settings.cache_clear()
    settings = get_settings()
    client = GeminiClient()

    import build_synthetic_corpus as gen
    pdfs = gen.build(force=False)
    complaint = next(p for p in pdfs if p.name == "complaint.pdf")

    ingest = IngestPipeline().run(IngestRequest(matter_id="M-1", source_path=str(complaint)))

    vec_index = ChromaVectorIndex(persist_path=str(tmp_path / "chroma"))
    bm25_index = RankBm25LexicalIndex(persist_path=str(tmp_path / "bm25"))
    indexer = Indexer(
        vec_index=vec_index, bm25_index=bm25_index, client=client,
        embed_model=settings.embed_model, embed_dim=settings.embed_dim,
        prefix_model=settings.extraction_model,
    )
    await indexer.index(matter_id="M-1", ingest=ingest)

    # chunk_loader: read from SQLite metadata, simplified here as round-trip via Chroma
    def loader(ids):
        # In production this hits SQLite; for this test, reconstruct via Chroma get()
        col = vec_index._collection("M-1")
        got = col.get(ids=ids, include=["documents", "metadatas"])
        result = {}
        for i, cid in enumerate(got["ids"]):
            md = got["metadatas"][i]
            from draftloop_retrieval.types import Chunk
            result[cid] = Chunk(
                chunk_id=cid, doc_id=md["doc_id"], matter_id="M-1",
                page=md["page"], section_label=md.get("section_label") or None,
                para_id=None,
                char_start=md["char_start"], char_end=md["char_end"],
                text=got["documents"][i], context_prefix="",
                embedding_text=got["documents"][i], embedding_dim=1536,
                confidence_min=md["confidence_min"],
                contains_needs_review=md["contains_needs_review"],
                ingest_version=md["ingest_version"],
            )
        return result

    embedder = GeminiEmbedder(client=client, model=settings.embed_model, dim=settings.embed_dim)
    planner = QueryPlanner(client=client, model=settings.extraction_model, n=3)
    reranker = FlashReranker(client=client, model=settings.extraction_model)

    retriever = HybridRetriever(
        vec_index=vec_index, bm25_index=bm25_index, embedder=embedder,
        planner=planner, reranker=reranker, chunk_loader=loader,
    )
    result = await retriever.retrieve(matter_id="M-1", slot_plan=SLOT_PLAN)
    assert any(len(hits) > 0 for hits in result.slots.values())
```

- [ ] **Step 2: Run if GEMINI_API_KEY is real; otherwise the test skips.**

- [ ] **Step 3: Commit + final verification**

```bash
git add tests/integration/test_retrieval_end_to_end.py
git commit -m "test(integration): retrieval e2e against synthetic complaint"

bash scripts/lint.sh
uv run pytest -q
git checkout main
git merge --no-ff feat/plan-2-retrieval -m "Merge Plan 2: Retrieval & Grounding"
```

---

## Plan 2 — Done criteria

- [ ] All tasks above checked off.
- [ ] `uv run pytest -q` green (28 + Plan 1 ingest + ~20 retrieval tests).
- [ ] `scripts/check_boundaries.py` clean.
- [ ] Integration test passes when run with a real Gemini key.
- [ ] Plans index updated; next is Plan 3 (Drafting).
