# Plan 1: Ingestion (Digital + Scanned tiers) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `packages/draftloop_ingest` covering the **digital-native** and **scanned (printed)** input tiers end-to-end, plus a deterministic synthetic corpus generator and golden truth so future plans (and the eval harness in Plan 6) can run against known-good ground truth. Handwritten / photo / low-res tiers (Gemini Vision, TrOCR, Real-ESRGAN) are explicitly **deferred to Plan 1b**.

**Architecture:** `IngestPipeline.run(req: IngestRequest) -> IngestResult` is the single entry point. Two engine tiers: `pypdfium2 + pymupdf4llm` for pages with a usable text layer, `OpenCV preprocess + PaddleOCR (PP-OCRv5)` for scanned pages, with `pytesseract` as a fallback when Paddle is unavailable. State machine persisted via `DocumentStore` (SQLite impl). Confidence normalization to a uniform `Line` record. Markdown reconstruction is structure-aware via Docling-style heading detection (deferring full Docling integration if too heavy — fallback is a thin layout assembler we write ourselves).

**Tech Stack:** Python 3.12, `pymupdf4llm` (AGPL — note in README), `pypdfium2` (BSD), `paddleocr` (PP-OCRv5), `pytesseract` (fallback), `opencv-python`, `Pillow`, `reportlab` (synthetic corpus), `aiosqlite` (SQLite async). All inside `packages/draftloop_ingest`.

---

## File structure (new files in this plan)

```
packages/draftloop_ingest/
├─ pyproject.toml
├─ src/draftloop_ingest/
│  ├─ __init__.py                  # public API exports
│  ├─ types.py                     # IngestRequest, IngestResult, Page, Line, NeedsReviewSpan, DocStatus
│  ├─ pipeline.py                  # IngestPipeline orchestrator
│  ├─ probe.py                     # pypdfium2 per-page text-layer detection
│  ├─ raster.py                    # PDF -> page images (300 DPI)
│  ├─ classifier.py                # printed/handwritten/photo + blur score
│  ├─ preprocess.py                # OpenCV deskew + denoise + binarize
│  ├─ markdown_assembler.py        # heading-aware Markdown synthesis from Pages
│  ├─ state.py                     # DocStatus state machine + persistence
│  └─ engines/
│     ├─ __init__.py
│     ├─ base.py                   # OcrEngine + DigitalExtractor protocols
│     ├─ pymupdf4llm_engine.py     # digital path
│     ├─ paddle_engine.py          # PaddleOCR PP-OCRv5
│     └─ tesseract_engine.py       # fallback
└─ tests/
   ├─ test_types.py
   ├─ test_probe.py
   ├─ test_classifier.py
   ├─ test_preprocess.py
   ├─ test_markdown_assembler.py
   ├─ test_engines_pymupdf4llm.py
   ├─ test_engines_paddle.py
   ├─ test_engines_tesseract.py
   ├─ test_state.py
   ├─ test_pipeline_digital.py
   └─ test_pipeline_scanned.py

packages/draftloop_core/src/draftloop_core/storage/
├─ sqlite_document_store.py        # SQLite DocumentStore default impl
└─ local_blob_store.py             # Local FS BlobStore default impl
packages/draftloop_core/tests/
├─ test_sqlite_document_store.py
└─ test_local_blob_store.py

scripts/
├─ build_synthetic_corpus.py       # generates data/synthetic/*.pdf
└─ run_ingest_demo.py              # one-PDF demo with confidence heatmap

data/
├─ synthetic/                      # generated PDFs (gitignored)
└─ golden/                         # committed: ingest_truth/*.md + *_needs_review.json

tests/integration/
├─ __init__.py
└─ test_ingest_pipeline.py         # end-to-end against synthetic corpus
```

---

## Conventions

- Conventional Commits.
- TDD discipline: failing test → impl → green test → commit, per task.
- All Gemini calls (none in this plan) would route through `draftloop_core.llm`.
- All boundary rules from CLAUDE.md apply.

---

## Task 1: `draftloop_ingest` package scaffold

**Files:**
- Create: `packages/draftloop_ingest/pyproject.toml`
- Create: `packages/draftloop_ingest/src/draftloop_ingest/__init__.py`
- Create: `packages/draftloop_ingest/tests/__init__.py`
- Modify: root `pyproject.toml` (add `packages/draftloop_ingest` to workspace members)

- [ ] **Step 1: Write `packages/draftloop_ingest/pyproject.toml`**

```toml
[project]
name = "draftloop-ingest"
version = "0.1.0"
description = "DraftLoop document ingestion + OCR pipeline"
requires-python = ">=3.12,<3.13"
dependencies = [
    "draftloop-core",
    "pypdfium2>=4.30.0",
    "pymupdf4llm>=0.0.17",
    "Pillow>=10.4.0",
    "opencv-python>=4.10.0",
    "numpy>=1.26.0",
    "paddleocr>=2.8.0; python_version<'3.13'",
    "pytesseract>=0.3.10",
    "reportlab>=4.2.0",
    "aiosqlite>=0.20.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/draftloop_ingest"]
```

- [ ] **Step 2: Write `packages/draftloop_ingest/src/draftloop_ingest/__init__.py`**

```python
"""DraftLoop document ingestion + OCR.

Public API:
    IngestPipeline, IngestRequest, IngestResult, Page, Line, NeedsReviewSpan, DocStatus
"""
from draftloop_ingest.pipeline import IngestPipeline
from draftloop_ingest.types import (
    DocStatus,
    IngestRequest,
    IngestResult,
    Line,
    NeedsReviewSpan,
    Page,
)

__all__ = [
    "IngestPipeline",
    "IngestRequest",
    "IngestResult",
    "Page",
    "Line",
    "NeedsReviewSpan",
    "DocStatus",
]
__version__ = "0.1.0"
```

- [ ] **Step 3: Empty `packages/draftloop_ingest/tests/__init__.py`**

- [ ] **Step 4: Update root `pyproject.toml` workspace members**

Append `"packages/draftloop_ingest"` to `[tool.uv.workspace] members`. Final value:
```toml
members = ["packages/draftloop_core", "packages/draftloop_ingest", "apps/api"]
```

- [ ] **Step 5: `uv sync --all-packages`**, then commit.

```bash
uv sync --all-packages
git add packages/draftloop_ingest pyproject.toml uv.lock
git commit -m "feat(ingest): scaffold draftloop_ingest package"
```

The `__init__.py` references modules (`pipeline`, `types`) that don't exist yet — same lazy-load pattern as in Plan 0; import is via full path (`from draftloop_ingest.types import …`). Tests for Task 2 will land first, after which `from draftloop_ingest import …` works.

---

## Task 2: `draftloop_ingest.types` — public schema

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/types.py`
- Create: `packages/draftloop_ingest/tests/test_types.py`

- [ ] **Step 1: Failing test**

`packages/draftloop_ingest/tests/test_types.py`:
```python
import pytest

from draftloop_ingest.types import (
    DocStatus,
    IngestRequest,
    IngestResult,
    Line,
    NeedsReviewSpan,
    Page,
)


def test_line_invariant_low_conf_is_review():
    line = Line(
        page=1,
        text="hello",
        bbox=(0, 0, 10, 10),
        confidence=0.7,
        engine="paddleocr",
    )
    assert line.needs_review is True


def test_line_invariant_high_conf_is_not_review():
    line = Line(
        page=1,
        text="hello",
        bbox=(0, 0, 10, 10),
        confidence=0.95,
        engine="paddleocr",
    )
    assert line.needs_review is False


def test_doc_status_transitions_are_well_defined():
    assert DocStatus.UPLOADED.value == "uploaded"
    assert DocStatus.READY.value == "ready"
    assert DocStatus.FAILED.value == "failed"


def test_ingest_request_requires_source_path():
    with pytest.raises(Exception):
        IngestRequest()
    req = IngestRequest(matter_id="M-001", source_path="/tmp/x.pdf")
    assert req.matter_id == "M-001"


def test_ingest_result_aggregate_confidence_validates():
    page = Page(
        page=1,
        width_px=816,
        height_px=1056,
        dpi=96,
        class_="digital",
        engines_used=["pymupdf4llm"],
        lines=[],
        needs_review=False,
    )
    res = IngestResult(
        doc_id="doc_1",
        source_path="/tmp/x.pdf",
        pages=[page],
        markdown="<!-- page=1 -->",
        needs_review_spans=[],
        aggregate_confidence=0.99,
        engines_used={1: ["pymupdf4llm"]},
        duration_ms=120,
        ingest_version="v1",
    )
    assert res.doc_id == "doc_1"
    assert res.pages[0].class_ == "digital"
```

- [ ] **Step 2: Run; expect failure (module not found).**

```bash
uv run pytest packages/draftloop_ingest/tests/test_types.py -v
```

- [ ] **Step 3: Implement `types.py`**

```python
"""Public types for the ingestion package."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NEEDS_REVIEW_THRESHOLD = 0.80

EngineName = Literal[
    "pymupdf4llm",
    "paddleocr",
    "tesseract",
    "gemini_vision",
    "trocr",
]
PageClass = Literal[
    "digital", "clean_scan", "low_res", "handwritten", "photo", "mixed"
]
ReviewReason = Literal["low_ocr_conf", "illegible", "blurry", "redacted"]


class DocStatus(StrEnum):
    UPLOADED = "uploaded"
    PROBING = "probing"
    EXTRACTING = "extracting"
    RASTERIZING = "rasterizing"
    CLASSIFYING = "classifying"
    PREPROCESSING = "preprocessing"
    OCR_RUNNING = "ocr_running"
    VERIFYING = "verifying"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class Line(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float = Field(..., ge=0.0, le=1.0)
    engine: EngineName
    needs_review: bool = False

    @model_validator(mode="after")
    def _enforce_review_invariant(self) -> Line:
        # Force needs_review := confidence < threshold (no caller override).
        object.__setattr__(self, "needs_review", self.confidence < NEEDS_REVIEW_THRESHOLD)
        return self


class NeedsReviewSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[int, int, int, int]
    text: str
    confidence: float
    reason: ReviewReason


class Page(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    width_px: int
    height_px: int
    dpi: int
    class_: PageClass
    engines_used: list[EngineName]
    lines: list[Line]
    needs_review: bool


class IngestRequest(BaseModel):
    matter_id: str
    source_path: str
    doc_id: str | None = None       # if absent, derived from source_path basename
    enable_paddle: bool = True
    enable_tesseract_fallback: bool = True


class IngestResult(BaseModel):
    doc_id: str
    source_path: str
    pages: list[Page]
    markdown: str
    needs_review_spans: list[NeedsReviewSpan]
    aggregate_confidence: float
    engines_used: dict[int, list[EngineName]]
    duration_ms: int
    ingest_version: str
    failed: bool = False
    fail_reason: str | None = None
```

- [ ] **Step 4: Run tests; expect 5 PASS.**

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/types.py packages/draftloop_ingest/tests/test_types.py
git commit -m "feat(ingest): add public types (Line, Page, IngestResult, DocStatus)"
```

---

## Task 3: SQLite DocumentStore impl in `draftloop_core`

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/storage/sqlite_document_store.py`
- Create: `packages/draftloop_core/tests/test_sqlite_document_store.py`

- [ ] **Step 1: Failing test**

```python
import json

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
```

- [ ] **Step 2: Run; expect failure.**

- [ ] **Step 3: Implement `sqlite_document_store.py`**

```python
"""Default DocumentStore impl backed by SQLite (via aiosqlite).

Production swap target: PostgresDocumentStore (not implemented here).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import aiosqlite

from draftloop_core.errors import StorageError


class SqliteDocumentStore:
    """File-backed JSON-blob store keyed by string. Async API for FastAPI compatibility."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    async def init_schema(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def get(self, key: str) -> Any | None:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT value FROM kv WHERE key = ?", (key,)
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"corrupt value at {key!r}",
                code="STORAGE_CORRUPT_VALUE",
            ) from exc

    async def put(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO kv(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, payload),
            )
            await db.commit()

    async def delete(self, key: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM kv WHERE key = ?", (key,))
            await db.commit()

    async def list(self, prefix: str = "") -> AsyncIterator[tuple[str, Any]]:
        like = f"{prefix}%"
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT key, value FROM kv WHERE key LIKE ? ORDER BY key", (like,)
            ) as cur:
                async for row in cur:
                    yield row[0], json.loads(row[1])
```

- [ ] **Step 4: Run tests; expect 5 PASS.**

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/storage/sqlite_document_store.py packages/draftloop_core/tests/test_sqlite_document_store.py
git commit -m "feat(core): add SqliteDocumentStore default impl"
```

---

## Task 4: Local FS BlobStore impl in `draftloop_core`

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/storage/local_blob_store.py`
- Create: `packages/draftloop_core/tests/test_local_blob_store.py`

- [ ] **Step 1: Failing test**

```python
import pytest

from draftloop_core.storage import BlobStore
from draftloop_core.storage.local_blob_store import LocalBlobStore


@pytest.fixture
def store(tmp_path):
    return LocalBlobStore(tmp_path)


async def test_implements_protocol(store):
    assert isinstance(store, BlobStore)


async def test_put_and_get_roundtrip(store):
    await store.put("M-001/pdfs/a.pdf", b"\x25PDF-fake")
    got = await store.get("M-001/pdfs/a.pdf")
    assert got == b"\x25PDF-fake"


async def test_missing_key_raises(store):
    with pytest.raises(FileNotFoundError):
        await store.get("M-001/nope.pdf")


async def test_delete(store):
    await store.put("M-001/a.bin", b"123")
    await store.delete("M-001/a.bin")
    with pytest.raises(FileNotFoundError):
        await store.get("M-001/a.bin")


async def test_keys_with_subdirs(store, tmp_path):
    await store.put("M-001/sub/a.bin", b"hello")
    p = tmp_path / "M-001" / "sub" / "a.bin"
    assert p.exists() and p.read_bytes() == b"hello"
```

- [ ] **Step 2: Implement `local_blob_store.py`**

```python
"""Default BlobStore impl: keys map directly to file paths under a root dir."""

from __future__ import annotations

import asyncio
from pathlib import Path


class LocalBlobStore:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Disallow traversal: key MUST NOT contain ".." segments.
        if any(seg == ".." for seg in Path(key).parts):
            raise ValueError(f"invalid key {key!r}: '..' segments not allowed")
        return self._root / key

    async def get(self, key: str) -> bytes:
        p = self._path(key)
        return await asyncio.to_thread(p.read_bytes)

    async def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(p.write_bytes, data)

    async def delete(self, key: str) -> None:
        p = self._path(key)
        await asyncio.to_thread(p.unlink, missing_ok=True)
```

- [ ] **Step 3: Run tests; expect 5 PASS.**

- [ ] **Step 4: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/storage/local_blob_store.py packages/draftloop_core/tests/test_local_blob_store.py
git commit -m "feat(core): add LocalBlobStore default impl"
```

---

## Task 5: pypdfium2 probe (text-layer detection)

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/probe.py`
- Create: `packages/draftloop_ingest/tests/test_probe.py`

- [ ] **Step 1: Failing test**

```python
import pypdfium2 as pdfium
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest.probe import probe_pdf, PageProbe


def _make_digital_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(72, 720, "Hello DraftLoop. This is a digital-native PDF.")
    c.showPage()
    c.drawString(72, 720, "Second page also has text.")
    c.showPage()
    c.save()


def test_probe_detects_text_pages(tmp_path):
    pdf = tmp_path / "digital.pdf"
    _make_digital_pdf(pdf)
    probes = probe_pdf(pdf)
    assert len(probes) == 2
    assert all(p.has_text_layer for p in probes)
    assert probes[0].text_char_count >= 30
    assert probes[0].width_px > 0 and probes[0].height_px > 0


def test_probe_marks_empty_page_as_scan_candidate(tmp_path):
    # Page with no text (only a rectangle) -> probe should say no text.
    pdf = tmp_path / "scan.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.rect(100, 100, 200, 200, fill=1)
    c.showPage()
    c.save()
    probes = probe_pdf(pdf)
    assert len(probes) == 1
    assert probes[0].has_text_layer is False
```

- [ ] **Step 2: Implement `probe.py`**

```python
"""Per-page text-layer probe via pypdfium2.

Determines whether a page has usable embedded text (digital tier)
or must be rasterized + OCR'd (scanned tier).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

TEXT_PRESENCE_MIN_CHARS = 50


@dataclass(frozen=True)
class PageProbe:
    page_index: int
    has_text_layer: bool
    text_char_count: int
    width_px: int
    height_px: int


def probe_pdf(path: str | Path) -> list[PageProbe]:
    path = Path(path)
    probes: list[PageProbe] = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        for i, page in enumerate(pdf):
            try:
                text_page = page.get_textpage()
                try:
                    text = text_page.get_text_range()
                finally:
                    text_page.close()
            except Exception:
                text = ""
            width = int(page.get_width())
            height = int(page.get_height())
            has_text = len((text or "").strip()) >= TEXT_PRESENCE_MIN_CHARS
            probes.append(
                PageProbe(
                    page_index=i,
                    has_text_layer=has_text,
                    text_char_count=len(text or ""),
                    width_px=width,
                    height_px=height,
                )
            )
    finally:
        pdf.close()
    return probes
```

- [ ] **Step 3: Run tests; expect 2 PASS.**

- [ ] **Step 4: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/probe.py packages/draftloop_ingest/tests/test_probe.py
git commit -m "feat(ingest): add pypdfium2 per-page text-layer probe"
```

---

## Task 6: pymupdf4llm digital extractor

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/engines/__init__.py`
- Create: `packages/draftloop_ingest/src/draftloop_ingest/engines/base.py`
- Create: `packages/draftloop_ingest/src/draftloop_ingest/engines/pymupdf4llm_engine.py`
- Create: `packages/draftloop_ingest/tests/test_engines_pymupdf4llm.py`

- [ ] **Step 1: Failing test**

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest.engines.pymupdf4llm_engine import Pdf4llmExtractor


def _make_digital_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Complaint")
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "Plaintiff brings this action against Defendant.")
    c.showPage()
    c.save()


def test_extracts_digital_page_to_markdown(tmp_path):
    pdf = tmp_path / "complaint.pdf"
    _make_digital_pdf(pdf)
    extractor = Pdf4llmExtractor()
    pages = extractor.extract(pdf, page_indices=[0])
    assert len(pages) == 1
    page = pages[0]
    assert page.page == 1
    assert page.class_ == "digital"
    assert "Complaint" in (page.markdown or "")
    assert all(line.engine == "pymupdf4llm" for line in page.lines)
    assert all(line.confidence == 1.0 for line in page.lines)
```

- [ ] **Step 2: Implement `engines/base.py`**

```python
"""Engine protocols + the unified `ExtractedPage` shape they all return."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from draftloop_ingest.types import Line, PageClass


class ExtractedPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int                       # 1-based
    width_px: int
    height_px: int
    dpi: int
    class_: PageClass
    lines: list[Line]
    markdown: str                   # per-page markdown fragment, may be empty
    engine: str


@runtime_checkable
class DigitalExtractor(Protocol):
    def extract(self, path: str | Path, page_indices: list[int]) -> list[ExtractedPage]: ...


@runtime_checkable
class OcrEngine(Protocol):
    """Engines accept a rasterized page image and return an ExtractedPage."""

    def ocr(
        self,
        *,
        image_bytes: bytes,
        page: int,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> "ExtractedPage": ...
```

- [ ] **Step 3: Implement `engines/pymupdf4llm_engine.py`**

```python
"""Digital extractor backed by pymupdf4llm. Returns Markdown + per-line records."""

from __future__ import annotations

from pathlib import Path

import pymupdf4llm

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


class Pdf4llmExtractor:
    def extract(self, path: str | Path, page_indices: list[int]) -> list[ExtractedPage]:
        # pymupdf4llm.to_markdown returns one item per requested page when page_chunks=True
        chunks = pymupdf4llm.to_markdown(
            str(path),
            page_chunks=True,
            pages=page_indices,
            extract_words=True,
        )
        out: list[ExtractedPage] = []
        for entry in chunks:
            page_no = int(entry.get("metadata", {}).get("page", 0)) + 1
            md = entry.get("text", "") or ""
            words = entry.get("words", []) or []
            lines: list[Line] = []
            # Group words into lines by y0 tolerance (~3 pt).
            sorted_words = sorted(words, key=lambda w: (round(float(w[1]) / 3), float(w[0])))
            current_y = None
            current_line: list[tuple[float, float, float, float, str]] = []
            grouped: list[list[tuple[float, float, float, float, str]]] = []
            for w in sorted_words:
                x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
                if current_y is None or abs(y0 - current_y) <= 3:
                    current_line.append((x0, y0, x1, y1, text))
                    current_y = y0
                else:
                    grouped.append(current_line)
                    current_line = [(x0, y0, x1, y1, text)]
                    current_y = y0
            if current_line:
                grouped.append(current_line)
            for grp in grouped:
                xs = [int(p[0]) for p in grp]
                ys = [int(p[1]) for p in grp]
                xes = [int(p[2]) for p in grp]
                yes = [int(p[3]) for p in grp]
                text = " ".join(p[4] for p in grp).strip()
                if not text:
                    continue
                lines.append(
                    Line(
                        page=page_no,
                        text=text,
                        bbox=(min(xs), min(ys), max(xes), max(yes)),
                        confidence=1.0,
                        engine="pymupdf4llm",
                    )
                )
            # Width/height not always exposed; approximate from page bbox if needed.
            out.append(
                ExtractedPage(
                    page=page_no,
                    width_px=int(entry.get("metadata", {}).get("page_width", 612)),
                    height_px=int(entry.get("metadata", {}).get("page_height", 792)),
                    dpi=72,
                    class_="digital",
                    lines=lines,
                    markdown=md,
                    engine="pymupdf4llm",
                )
            )
        return out
```

- [ ] **Step 4: Implement `engines/__init__.py`**

```python
from draftloop_ingest.engines.base import (
    DigitalExtractor,
    ExtractedPage,
    OcrEngine,
)
from draftloop_ingest.engines.pymupdf4llm_engine import Pdf4llmExtractor

__all__ = [
    "DigitalExtractor",
    "OcrEngine",
    "ExtractedPage",
    "Pdf4llmExtractor",
]
```

- [ ] **Step 5: Run tests; expect 1 PASS.**

- [ ] **Step 6: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/engines/ packages/draftloop_ingest/tests/test_engines_pymupdf4llm.py
git commit -m "feat(ingest): add pymupdf4llm digital extractor"
```

---

## Task 7: Page rasterizer + preprocessor

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/raster.py`
- Create: `packages/draftloop_ingest/src/draftloop_ingest/preprocess.py`
- Create: `packages/draftloop_ingest/tests/test_preprocess.py`

- [ ] **Step 1: Implement `raster.py`** (no tests — depends on graphics backend, exercised indirectly by pipeline integration tests)

```python
"""Rasterize PDF pages to PNG bytes at a target DPI."""

from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium


def rasterize_page(path: str | Path, page_index: int, dpi: int = 300) -> bytes:
    """Return PNG bytes for one page at the requested DPI."""
    pdf = pdfium.PdfDocument(str(path))
    try:
        page = pdf[page_index]
        scale = dpi / 72.0
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        from io import BytesIO

        buf = BytesIO()
        pil.save(buf, format="PNG")
        return buf.getvalue()
    finally:
        pdf.close()
```

- [ ] **Step 2: Failing test for preprocess**

```python
import cv2
import numpy as np
import pytest

from draftloop_ingest.preprocess import preprocess_image


def _gen_dirty_image() -> bytes:
    """Generate a 600x600 image with rotated text-like rectangles + noise."""
    img = np.full((600, 600), 240, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (300, 130), 30, -1)
    cv2.rectangle(img, (100, 200), (350, 230), 30, -1)
    noise = np.random.default_rng(42).normal(0, 25, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    # Rotate by 7 degrees to simulate skew.
    M = cv2.getRotationMatrix2D((300, 300), 7, 1.0)
    img = cv2.warpAffine(img, M, (600, 600), borderValue=255)
    ok, encoded = cv2.imencode(".png", img)
    assert ok
    return encoded.tobytes()


def test_preprocess_returns_binary_image_bytes():
    raw = _gen_dirty_image()
    out = preprocess_image(raw)
    assert isinstance(out, bytes) and len(out) > 0
    # Decode and verify it is mostly binary (high contrast).
    arr = np.frombuffer(out, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    unique = np.unique(img)
    assert len(unique) <= 4, "binarization should produce ~2 levels"


def test_preprocess_deskews_within_2_degrees():
    """After preprocessing, the dominant text rows should be ~horizontal."""
    raw = _gen_dirty_image()
    out = preprocess_image(raw)
    arr = np.frombuffer(out, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    # Detect non-white pixels and fit a min-area rect.
    coords = np.column_stack(np.where(img < 128))
    if coords.size == 0:
        pytest.skip("preprocess made image empty")
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    # Normalize angle to [-45, 45].
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    assert abs(angle) <= 2.0, f"deskewed angle {angle} not within ±2°"
```

- [ ] **Step 3: Implement `preprocess.py`**

```python
"""OpenCV preprocessing: deskew + denoise + binarize.

Input/output: PNG bytes. Pipeline is conservative — gentle defaults intended
to leave high-quality scans untouched while rescuing noisy ones.
"""

from __future__ import annotations

import cv2
import numpy as np


def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("could not decode image")
    return img


def _encode(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("could not encode image")
    return buf.tobytes()


def _deskew(img: np.ndarray) -> np.ndarray:
    inv = cv2.bitwise_not(img)
    thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.2:
        return img
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        img, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _denoise(img: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(img, None, h=10, templateWindowSize=7, searchWindowSize=21)


def _binarize(img: np.ndarray) -> np.ndarray:
    return cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]


def preprocess_image(image_bytes: bytes) -> bytes:
    img = _decode(image_bytes)
    img = _denoise(img)
    img = _deskew(img)
    img = _binarize(img)
    return _encode(img)
```

- [ ] **Step 4: Run tests; expect 2 PASS.**

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/raster.py packages/draftloop_ingest/src/draftloop_ingest/preprocess.py packages/draftloop_ingest/tests/test_preprocess.py
git commit -m "feat(ingest): add page rasterizer + OpenCV preprocessor (deskew, denoise, binarize)"
```

---

## Task 8: Tesseract fallback engine

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/engines/tesseract_engine.py`
- Create: `packages/draftloop_ingest/tests/test_engines_tesseract.py`

- [ ] **Step 1: Failing test (skipped if `tesseract` binary missing)**

```python
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from draftloop_ingest.engines.tesseract_engine import TesseractEngine


pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract binary not installed; skipping",
)


def _render_text_image(text: str) -> bytes:
    img = Image.new("L", (800, 200), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), text, fill=0, font=font)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_tesseract_reads_obvious_text():
    image_bytes = _render_text_image("Plaintiff brings this action.")
    engine = TesseractEngine()
    result = engine.ocr(
        image_bytes=image_bytes,
        page=1,
        width_px=800,
        height_px=200,
        dpi=300,
    )
    joined = " ".join(line.text for line in result.lines)
    assert "Plaintiff" in joined
    assert all(line.engine == "tesseract" for line in result.lines)
    assert all(0.0 <= line.confidence <= 1.0 for line in result.lines)
```

- [ ] **Step 2: Implement `tesseract_engine.py`**

```python
"""Tesseract OCR fallback engine."""

from __future__ import annotations

from io import BytesIO

import pytesseract
from PIL import Image

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


class TesseractEngine:
    def ocr(
        self,
        *,
        image_bytes: bytes,
        page: int,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> ExtractedPage:
        img = Image.open(BytesIO(image_bytes))
        data = pytesseract.image_to_data(
            img, output_type=pytesseract.Output.DICT, config="--psm 6"
        )

        # Group words into lines by (block_num, par_num, line_num)
        grouped: dict[tuple[int, int, int], list[int]] = {}
        for i in range(len(data["text"])):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            grouped.setdefault(key, []).append(i)

        lines: list[Line] = []
        for _, idxs in grouped.items():
            texts = [data["text"][i] for i in idxs]
            text = " ".join(t.strip() for t in texts if t and t.strip())
            if not text:
                continue
            confs = [int(c) for c in (data["conf"][i] for i in idxs) if int(c) >= 0]
            avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
            xs = [int(data["left"][i]) for i in idxs]
            ys = [int(data["top"][i]) for i in idxs]
            xes = [int(data["left"][i] + data["width"][i]) for i in idxs]
            yes = [int(data["top"][i] + data["height"][i]) for i in idxs]
            lines.append(
                Line(
                    page=page,
                    text=text,
                    bbox=(min(xs), min(ys), max(xes), max(yes)),
                    confidence=avg_conf,
                    engine="tesseract",
                )
            )

        return ExtractedPage(
            page=page,
            width_px=width_px,
            height_px=height_px,
            dpi=dpi,
            class_="clean_scan",
            lines=lines,
            markdown="\n".join(line.text for line in lines),
            engine="tesseract",
        )
```

- [ ] **Step 3: Run test (will skip on systems without tesseract); ensure no errors when skipped.**

- [ ] **Step 4: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/engines/tesseract_engine.py packages/draftloop_ingest/tests/test_engines_tesseract.py
git commit -m "feat(ingest): add Tesseract OCR fallback engine"
```

---

## Task 9: PaddleOCR engine (default scanned-page extractor)

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/engines/paddle_engine.py`
- Create: `packages/draftloop_ingest/tests/test_engines_paddle.py`

- [ ] **Step 1: Failing test (skipped if `paddleocr` import fails)**

```python
import importlib.util

import pytest
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

paddleocr_available = importlib.util.find_spec("paddleocr") is not None

pytestmark = pytest.mark.skipif(
    not paddleocr_available,
    reason="paddleocr not installed; skipping",
)


def _render_text_image(text: str) -> bytes:
    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 80), text, fill="black", font=font)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_paddle_reads_printed_text():
    from draftloop_ingest.engines.paddle_engine import PaddleEngine

    image_bytes = _render_text_image("Motion to Dismiss filed.")
    engine = PaddleEngine()
    result = engine.ocr(
        image_bytes=image_bytes,
        page=1,
        width_px=800,
        height_px=200,
        dpi=300,
    )
    joined = " ".join(line.text for line in result.lines)
    assert "Motion" in joined or "Dismiss" in joined
    assert all(line.engine == "paddleocr" for line in result.lines)
```

- [ ] **Step 2: Implement `paddle_engine.py`**

```python
"""PaddleOCR PP-OCRv5 engine (default scanned-page extractor)."""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


class PaddleEngine:
    """Thin wrapper around paddleocr.PaddleOCR.

    The first instantiation pulls model weights; cached after.
    """

    def __init__(self) -> None:
        # Lazy import keeps `pytest --collect-only` fast on machines without paddle.
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
        )

    def ocr(
        self,
        *,
        image_bytes: bytes,
        page: int,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> ExtractedPage:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        result = self._ocr.ocr(arr, cls=True)
        # paddleocr returns [[ [box, (text, score)], ... ]] for v2.x; ensure we unwrap one page.
        page_result = result[0] if result and isinstance(result[0], list) else []
        lines: list[Line] = []
        for box, (text, score) in page_result:
            if not text:
                continue
            xs = [int(p[0]) for p in box]
            ys = [int(p[1]) for p in box]
            lines.append(
                Line(
                    page=page,
                    text=text,
                    bbox=(min(xs), min(ys), max(xs), max(ys)),
                    confidence=float(score),
                    engine="paddleocr",
                )
            )
        return ExtractedPage(
            page=page,
            width_px=width_px,
            height_px=height_px,
            dpi=dpi,
            class_="clean_scan",
            lines=lines,
            markdown="\n".join(line.text for line in lines),
            engine="paddleocr",
        )
```

- [ ] **Step 3: Run test (will skip if paddleocr unavailable). Commit.**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/engines/paddle_engine.py packages/draftloop_ingest/tests/test_engines_paddle.py
git commit -m "feat(ingest): add PaddleOCR PP-OCRv5 engine for scanned pages"
```

---

## Task 10: Markdown assembler

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/markdown_assembler.py`
- Create: `packages/draftloop_ingest/tests/test_markdown_assembler.py`

- [ ] **Step 1: Failing test**

```python
from draftloop_ingest.markdown_assembler import assemble_markdown
from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.types import Line


def _line(page: int, text: str, conf: float = 1.0, y: int = 100) -> Line:
    return Line(
        page=page,
        text=text,
        bbox=(0, y, 100, y + 20),
        confidence=conf,
        engine="pymupdf4llm",
    )


def test_assemble_markdown_emits_per_page_marker():
    p1 = ExtractedPage(
        page=1, width_px=612, height_px=792, dpi=72, class_="digital",
        lines=[_line(1, "Heading", 1.0), _line(1, "body text", 1.0, y=150)],
        markdown="# Heading\n\nbody text",
        engine="pymupdf4llm",
    )
    p2 = ExtractedPage(
        page=2, width_px=612, height_px=792, dpi=72, class_="digital",
        lines=[_line(2, "Second page", 1.0)],
        markdown="second page",
        engine="pymupdf4llm",
    )
    md = assemble_markdown([p1, p2])
    assert "<!-- page=1 -->" in md
    assert "<!-- page=2 -->" in md
    assert md.index("<!-- page=1 -->") < md.index("<!-- page=2 -->")
    assert "Heading" in md
    assert "Second page" in md


def test_assemble_markdown_falls_back_when_engine_returned_no_md():
    """If an engine returned empty markdown, synthesize from Line.text."""
    p = ExtractedPage(
        page=1, width_px=612, height_px=792, dpi=72, class_="clean_scan",
        lines=[_line(1, "first line"), _line(1, "second line", y=130)],
        markdown="",
        engine="paddleocr",
    )
    md = assemble_markdown([p])
    assert "first line" in md
    assert "second line" in md
```

- [ ] **Step 2: Implement `markdown_assembler.py`**

```python
"""Combine per-page extractor output into a single Markdown blob.

Insert ``<!-- page=N -->`` markers so downstream chunking can preserve page
provenance.
"""

from __future__ import annotations

from draftloop_ingest.engines.base import ExtractedPage


def assemble_markdown(pages: list[ExtractedPage]) -> str:
    parts: list[str] = []
    for p in sorted(pages, key=lambda x: x.page):
        parts.append(f"<!-- page={p.page} -->")
        if p.markdown and p.markdown.strip():
            parts.append(p.markdown.strip())
        else:
            parts.append("\n".join(line.text for line in p.lines))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
```

- [ ] **Step 3: Run tests; expect 2 PASS.**

- [ ] **Step 4: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/markdown_assembler.py packages/draftloop_ingest/tests/test_markdown_assembler.py
git commit -m "feat(ingest): add page-keyed Markdown assembler"
```

---

## Task 11: IngestPipeline orchestrator

**Files:**
- Create: `packages/draftloop_ingest/src/draftloop_ingest/pipeline.py`
- Create: `packages/draftloop_ingest/tests/test_pipeline_digital.py`
- Create: `packages/draftloop_ingest/tests/test_pipeline_scanned.py`

- [ ] **Step 1: Failing test (digital path end-to-end)**

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest import IngestPipeline, IngestRequest


def _make_digital_pdf(path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Complaint")
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "Plaintiff brings this action against Defendant for breach of contract.")
    c.showPage()
    c.drawString(72, 720, "Page 2: Procedural posture is the motion to dismiss stage.")
    c.showPage()
    c.save()


def test_pipeline_digital_path(tmp_path):
    pdf = tmp_path / "complaint.pdf"
    _make_digital_pdf(pdf)
    pipeline = IngestPipeline()
    result = pipeline.run(
        IngestRequest(matter_id="M-001", source_path=str(pdf))
    )
    assert result.failed is False
    assert len(result.pages) == 2
    assert all(p.class_ == "digital" for p in result.pages)
    assert "Complaint" in result.markdown
    assert "<!-- page=1 -->" in result.markdown
    assert "<!-- page=2 -->" in result.markdown
    assert result.aggregate_confidence == 1.0
    assert result.engines_used == {1: ["pymupdf4llm"], 2: ["pymupdf4llm"]}
```

- [ ] **Step 2: Implement `pipeline.py`**

```python
"""IngestPipeline — top-level orchestrator for ingestion.

Decides per page which engine to invoke, normalizes outputs, emits
IngestResult.
"""

from __future__ import annotations

import time
from pathlib import Path

from draftloop_core.obs import get_logger, traced

from draftloop_ingest.engines.base import ExtractedPage
from draftloop_ingest.engines.pymupdf4llm_engine import Pdf4llmExtractor
from draftloop_ingest.markdown_assembler import assemble_markdown
from draftloop_ingest.probe import probe_pdf
from draftloop_ingest.raster import rasterize_page
from draftloop_ingest.types import (
    IngestRequest,
    IngestResult,
    NeedsReviewSpan,
    Page,
)

logger = get_logger("draftloop.ingest")

INGEST_VERSION = "v1"


class IngestPipeline:
    def __init__(
        self,
        *,
        digital_extractor: Pdf4llmExtractor | None = None,
        paddle_engine_factory=None,
        tesseract_engine_factory=None,
    ) -> None:
        self._digital = digital_extractor or Pdf4llmExtractor()
        self._paddle_factory = paddle_engine_factory
        self._tesseract_factory = tesseract_engine_factory
        self._paddle = None
        self._tesseract = None

    def _get_paddle(self):
        if self._paddle is None:
            if self._paddle_factory is not None:
                self._paddle = self._paddle_factory()
            else:
                try:
                    from draftloop_ingest.engines.paddle_engine import PaddleEngine
                    self._paddle = PaddleEngine()
                except Exception as exc:
                    logger.warning("ingest.paddle_unavailable", error=str(exc))
                    self._paddle = False
        return self._paddle or None

    def _get_tesseract(self):
        if self._tesseract is None:
            if self._tesseract_factory is not None:
                self._tesseract = self._tesseract_factory()
            else:
                try:
                    from draftloop_ingest.engines.tesseract_engine import TesseractEngine
                    self._tesseract = TesseractEngine()
                except Exception as exc:
                    logger.warning("ingest.tesseract_unavailable", error=str(exc))
                    self._tesseract = False
        return self._tesseract or None

    @traced("draftloop.ingest.run")
    def run(self, req: IngestRequest) -> IngestResult:
        start = time.monotonic()
        doc_id = req.doc_id or Path(req.source_path).stem
        try:
            probes = probe_pdf(req.source_path)
        except Exception as exc:
            return IngestResult(
                doc_id=doc_id,
                source_path=req.source_path,
                pages=[],
                markdown="",
                needs_review_spans=[],
                aggregate_confidence=0.0,
                engines_used={},
                duration_ms=int((time.monotonic() - start) * 1000),
                ingest_version=INGEST_VERSION,
                failed=True,
                fail_reason=f"probe_failed: {exc}",
            )

        digital_indices = [p.page_index for p in probes if p.has_text_layer]
        scanned_indices = [p.page_index for p in probes if not p.has_text_layer]

        extracted: dict[int, ExtractedPage] = {}
        engines_used: dict[int, list[str]] = {}

        if digital_indices:
            for page in self._digital.extract(req.source_path, digital_indices):
                extracted[page.page] = page
                engines_used[page.page] = ["pymupdf4llm"]

        for idx in scanned_indices:
            page_no = idx + 1
            image_bytes = rasterize_page(req.source_path, idx, dpi=300)
            from draftloop_ingest.preprocess import preprocess_image
            preprocessed = preprocess_image(image_bytes)

            probe = probes[idx]
            page_obj: ExtractedPage | None = None
            engines_for_page: list[str] = []

            paddle = self._get_paddle() if req.enable_paddle else None
            if paddle is not None:
                try:
                    page_obj = paddle.ocr(
                        image_bytes=preprocessed,
                        page=page_no,
                        width_px=probe.width_px,
                        height_px=probe.height_px,
                        dpi=300,
                    )
                    engines_for_page.append("paddleocr")
                except Exception as exc:
                    logger.warning("ingest.paddle_failed", page=page_no, error=str(exc))

            if (page_obj is None or not page_obj.lines) and req.enable_tesseract_fallback:
                tess = self._get_tesseract()
                if tess is not None:
                    try:
                        page_obj = tess.ocr(
                            image_bytes=preprocessed,
                            page=page_no,
                            width_px=probe.width_px,
                            height_px=probe.height_px,
                            dpi=300,
                        )
                        engines_for_page.append("tesseract")
                    except Exception as exc:
                        logger.warning("ingest.tesseract_failed", page=page_no, error=str(exc))

            if page_obj is not None:
                extracted[page_no] = page_obj
                engines_used[page_no] = engines_for_page

        pages_list = [extracted[k] for k in sorted(extracted)]
        markdown = assemble_markdown(pages_list)

        needs_review_spans: list[NeedsReviewSpan] = []
        confs: list[float] = []
        emitted_pages: list[Page] = []
        for ep in pages_list:
            page_conf = (
                sum(line.confidence for line in ep.lines) / len(ep.lines)
                if ep.lines else 0.0
            )
            confs.append(page_conf)
            page_needs_review = any(line.needs_review for line in ep.lines)
            for line in ep.lines:
                if line.needs_review:
                    needs_review_spans.append(
                        NeedsReviewSpan(
                            page=ep.page,
                            bbox=line.bbox,
                            text=line.text,
                            confidence=line.confidence,
                            reason="low_ocr_conf",
                        )
                    )
            emitted_pages.append(
                Page(
                    page=ep.page,
                    width_px=ep.width_px,
                    height_px=ep.height_px,
                    dpi=ep.dpi,
                    class_=ep.class_,
                    engines_used=engines_used.get(ep.page, []),
                    lines=ep.lines,
                    needs_review=page_needs_review,
                )
            )

        aggregate = sum(confs) / len(confs) if confs else 0.0
        return IngestResult(
            doc_id=doc_id,
            source_path=req.source_path,
            pages=emitted_pages,
            markdown=markdown,
            needs_review_spans=needs_review_spans,
            aggregate_confidence=aggregate,
            engines_used=engines_used,
            duration_ms=int((time.monotonic() - start) * 1000),
            ingest_version=INGEST_VERSION,
        )
```

- [ ] **Step 3: Failing test (scanned path)**

`packages/draftloop_ingest/tests/test_pipeline_scanned.py`:
```python
import importlib.util

import pytest
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from pypdfium2 import PdfDocument
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from draftloop_ingest import IngestPipeline, IngestRequest

paddleocr_available = importlib.util.find_spec("paddleocr") is not None
import shutil
tesseract_available = shutil.which("tesseract") is not None

pytestmark = pytest.mark.skipif(
    not (paddleocr_available or tesseract_available),
    reason="neither paddleocr nor tesseract available; scan path cannot run",
)


def _make_scanned_pdf(path) -> None:
    img = Image.new("L", (1700, 2200), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    draw.text((150, 300), "Notice of Hearing", fill=0, font=font)
    draw.text((150, 420), "Hearing scheduled for 2026-06-15.", fill=0, font=font)
    img_path = str(path) + ".png"
    img.save(img_path)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawImage(img_path, 0, 0, width=letter[0], height=letter[1])
    c.showPage()
    c.save()


def test_pipeline_scan_path(tmp_path):
    pdf = tmp_path / "notice.pdf"
    _make_scanned_pdf(pdf)
    pipeline = IngestPipeline()
    result = pipeline.run(
        IngestRequest(matter_id="M-001", source_path=str(pdf))
    )
    assert result.failed is False
    assert len(result.pages) == 1
    text = " ".join(line.text for line in result.pages[0].lines)
    assert "Notice" in text or "Hearing" in text or "2026" in text
```

- [ ] **Step 4: Run tests; expect digital PASS unconditionally, scan PASS or SKIP depending on engine availability.**

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_ingest/src/draftloop_ingest/pipeline.py packages/draftloop_ingest/tests/test_pipeline_digital.py packages/draftloop_ingest/tests/test_pipeline_scanned.py
git commit -m "feat(ingest): add IngestPipeline orchestrator (digital + scanned paths)"
```

---

## Task 12: Synthetic corpus generator script

**Files:**
- Create: `scripts/build_synthetic_corpus.py`
- Create: `scripts/run_ingest_demo.py`

- [ ] **Step 1: Write `scripts/build_synthetic_corpus.py`**

```python
#!/usr/bin/env python3
"""Generate DraftLoop's deterministic synthetic corpus.

Writes 6 PDF variants into ``data/synthetic/`` (gitignored). The variants
cover the input classes Plan 1 must handle end-to-end:

  digital-native:
    - complaint.pdf
    - motion.pdf
    - answer.pdf
    - order.pdf
  scanned:
    - complaint_scan.pdf       # rendered at 300 DPI, re-embedded as image
    - motion_scan.pdf

Re-running is idempotent: the same inputs produce byte-identical outputs
(seed=42 wherever randomness is involved).
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image
from pypdfium2 import PdfDocument
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DATA_DIR = Path("data/synthetic")
TEMPLATES = {
    "complaint": {
        "title": "COMPLAINT",
        "body": (
            "Plaintiff Acme Corp. brings this action against Defendant Widgets Inc. "
            "for breach of the SaaS agreement executed on 2024-03-14 in Illinois. "
            "Plaintiff seeks damages in the amount of $250,000 and injunctive relief. "
            "The Court has jurisdiction under 28 U.S.C. Section 1331."
        ),
    },
    "motion": {
        "title": "MOTION TO DISMISS",
        "body": (
            "Defendant Widgets Inc. moves to dismiss the Complaint pursuant to Rule 12(b)(6) "
            "for failure to state a claim. The motion is set for hearing on 2026-06-15."
        ),
    },
    "answer": {
        "title": "ANSWER",
        "body": (
            "Defendant Widgets Inc. responds to each paragraph of the Complaint. "
            "Paragraph 1 is admitted. Paragraph 2 is denied. Paragraph 3 is denied for lack "
            "of knowledge sufficient to form a belief as to its truth."
        ),
    },
    "order": {
        "title": "ORDER",
        "body": (
            "The Court, having considered the Motion to Dismiss and the Response, hereby "
            "GRANTS in part and DENIES in part. So ordered on 2026-05-20."
        ),
    },
}


def _draw_digital(path: Path, title: str, body: str) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, title)
    c.setFont("Helvetica", 12)
    y = 690
    for line in body.split(". "):
        if not line:
            continue
        c.drawString(72, y, line.strip() + ".")
        y -= 18
    c.showPage()
    c.save()


def _rasterize_to_pdf(src: Path, dst: Path, dpi: int = 300) -> None:
    """Convert ``src`` PDF to a scanned-style PDF where each page is a PNG image."""
    pdf = PdfDocument(str(src))
    try:
        c = canvas.Canvas(str(dst), pagesize=letter)
        for page in pdf:
            scale = dpi / 72.0
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            buf.seek(0)
            tmp_png = dst.with_suffix(".tmp.png")
            tmp_png.write_bytes(buf.getvalue())
            c.drawImage(str(tmp_png), 0, 0, width=letter[0], height=letter[1])
            c.showPage()
            tmp_png.unlink(missing_ok=True)
        c.save()
    finally:
        pdf.close()


def build(force: bool = False) -> list[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for name, meta in TEMPLATES.items():
        dst = DATA_DIR / f"{name}.pdf"
        if not dst.exists() or force:
            _draw_digital(dst, meta["title"], meta["body"])
        produced.append(dst)
    for name in ["complaint", "motion"]:
        src = DATA_DIR / f"{name}.pdf"
        dst = DATA_DIR / f"{name}_scan.pdf"
        if not dst.exists() or force:
            _rasterize_to_pdf(src, dst, dpi=300)
        produced.append(dst)
    return produced


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    produced = build(force=args.force)
    for p in produced:
        print(p)
    print(f"==> {len(produced)} files in {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write `scripts/run_ingest_demo.py`**

```python
#!/usr/bin/env python3
"""One-PDF demo: run IngestPipeline and print Markdown + confidence summary."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "demo-not-used")

from draftloop_ingest import IngestPipeline, IngestRequest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--json", action="store_true", help="Emit IngestResult JSON")
    args = parser.parse_args()

    pipeline = IngestPipeline()
    result = pipeline.run(
        IngestRequest(matter_id="DEMO", source_path=str(Path(args.pdf).resolve()))
    )

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    print(f"doc_id            : {result.doc_id}")
    print(f"pages             : {len(result.pages)}")
    print(f"engines_used      : {result.engines_used}")
    print(f"aggregate_conf    : {result.aggregate_confidence:.3f}")
    print(f"needs_review spans: {len(result.needs_review_spans)}")
    print(f"duration_ms       : {result.duration_ms}")
    print()
    print("---- Markdown ----")
    print(result.markdown)
    return 0 if not result.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Test corpus generation**

```bash
chmod +x scripts/build_synthetic_corpus.py scripts/run_ingest_demo.py
uv run python scripts/build_synthetic_corpus.py
ls -lh data/synthetic/
```

Expected: 6 PDFs (complaint.pdf, motion.pdf, answer.pdf, order.pdf, complaint_scan.pdf, motion_scan.pdf). `data/` is gitignored, so the files do NOT get committed.

- [ ] **Step 4: Smoke-run the demo**

```bash
uv run python scripts/run_ingest_demo.py data/synthetic/complaint.pdf
```

Expected: prints the Markdown with `<!-- page=1 -->` marker, `engines_used: {1: ['pymupdf4llm']}`, aggregate confidence ~1.0.

- [ ] **Step 5: Commit scripts only (the generated PDFs are gitignored)**

```bash
git add scripts/build_synthetic_corpus.py scripts/run_ingest_demo.py
git commit -m "feat(ingest): add synthetic corpus generator + run_ingest_demo script"
```

---

## Task 13: Integration test against synthetic corpus

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_ingest_pipeline.py`

- [ ] **Step 1: Write integration test**

```python
"""End-to-end ingestion against the synthetic corpus.

Builds the corpus on demand if it isn't present, then asserts core invariants
across all six PDFs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from draftloop_ingest import IngestPipeline, IngestRequest  # noqa: E402


@pytest.fixture(scope="module")
def synthetic_corpus():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import build_synthetic_corpus as gen
    return gen.build(force=False)


def test_digital_corpus_all_pages_extracted(synthetic_corpus):
    pipeline = IngestPipeline()
    digital_pdfs = [p for p in synthetic_corpus if "_scan" not in p.name]
    assert len(digital_pdfs) == 4

    for pdf in digital_pdfs:
        result = pipeline.run(
            IngestRequest(matter_id="TEST", source_path=str(pdf))
        )
        assert not result.failed, f"{pdf.name}: {result.fail_reason}"
        assert len(result.pages) >= 1, f"{pdf.name}: no pages extracted"
        assert all(p.class_ == "digital" for p in result.pages)
        assert result.aggregate_confidence == 1.0
        assert "<!-- page=1 -->" in result.markdown


def test_complaint_has_expected_facts(synthetic_corpus):
    pipeline = IngestPipeline()
    complaint = next(p for p in synthetic_corpus if p.name == "complaint.pdf")
    result = pipeline.run(IngestRequest(matter_id="TEST", source_path=str(complaint)))
    md = result.markdown.lower()
    assert "acme" in md
    assert "widgets" in md
    assert "saas agreement" in md
    assert "2024-03-14" in md
```

- [ ] **Step 2: `mkdir -p tests/integration; echo > tests/integration/__init__.py`**

- [ ] **Step 3: Run**

```bash
uv run pytest tests/integration/test_ingest_pipeline.py -v
```
Expected: PASS for both tests.

- [ ] **Step 4: Run the full test suite**

```bash
uv run pytest -q
```
Expected: all previous tests pass plus the new ones. Coverage on `packages/draftloop_ingest/` ≥80%.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_ingest_pipeline.py
git commit -m "test(integration): ingest pipeline over synthetic corpus"
```

---

## Task 14: Final verification

- [ ] **Step 1: Run every lint and test**

```bash
bash scripts/lint.sh
uv run pytest -q
pnpm -r test
```
Expected: all green. Boundaries clean. Diagrams render.

- [ ] **Step 2: Smoke-run the demo on a scanned PDF**

```bash
uv run python scripts/run_ingest_demo.py data/synthetic/complaint_scan.pdf
```
Expected (paddle/tesseract permitting): non-empty Markdown with detected text + aggregate confidence > 0.6.

- [ ] **Step 3: Update plans-index**

Edit `docs/superpowers/plans/2026-05-15-plans-index.md` to mark Plan 1 done; mention any newly discovered gaps that should land in Plan 1b (handwritten/photo/low-res tiers) or be deferred.

- [ ] **Step 4: Commit any incidental fixes (formatter, plans-index update)**

```bash
git add -A
git commit -m "chore: post-Plan-1 verification fixes"
```

If nothing changed, no commit needed.

- [ ] **Step 5: Merge to main**

```bash
git checkout main
git merge --no-ff feat/plan-1-ingestion -m "Merge Plan 1: Ingestion (digital + scanned tiers + synthetic corpus)"
```

---

## Plan 1 — Done criteria

- [ ] Every task above is `[x]` checked off.
- [ ] `bash scripts/lint.sh` exits 0.
- [ ] `uv run pytest` is fully green.
- [ ] `scripts/check_boundaries.py` reports `Boundaries clean.`
- [ ] `scripts/build_synthetic_corpus.py` produces 6 PDFs; `scripts/run_ingest_demo.py` runs on each.
- [ ] `tests/integration/test_ingest_pipeline.py` covers all six corpus PDFs.
- [ ] PaddleOCR runs successfully on at least one scanned PDF in the CI environment, OR the test gracefully skips with a documented "paddle not available" message.
- [ ] Plan 1b (handwritten/photo/low-res tiers) is recorded in the plans index as deferred.

When all bullets are checked, mark the index entry for Plan 1 as `done` and proceed to write Plan 2 (Retrieval).
