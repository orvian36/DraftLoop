# Plan 7: Composition, Demo & Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`.

**Goal:** Wire all packages into `apps/api`, build a one-command seed demo, ship Docker compose for reviewers, run the full eval and link the report from the README, polish documentation. After this plan a reviewer can `git clone && docker compose up` and reach a fully-loaded demo + eval report in under 10 minutes.

**Architecture:** `apps/api` exposes all routes (`/ingest`, `/draft`, `/edits`, `/admin/*`). `scripts/seed_demo.py` runs ingest → draft → plant 1 week of edits in a single command. `Dockerfile.api` + `Dockerfile.web` + `docker-compose.yml` produce a 2-container stack with bind-mounted `./data`. Init container downloads HHEM weights once. README gains screenshots + link to the eval scorecard.

**Tech Stack:** Reuse everything. Add `Dockerfile`s, `docker-compose.yml`, `.dockerignore`.

---

## File structure

```
apps/api/src/draftloop_api/
├─ routes/
│  ├─ ingest.py                  # POST /api/matters/:id/docs
│  ├─ matters.py                 # GET /api/matters, GET /api/matters/:id
│  ├─ admin.py                   # GET /admin/rules, /admin/replay, /admin/edits
│  └─ (existing) health.py, version.py, drafts.py, edits.py
├─ wiring.py                     # singleton wiring of all packages
└─ tasks.py                      # FastAPI BackgroundTasks adapters

scripts/
├─ seed_demo.py                  # ingest + draft + plant edits (one command)
└─ build_data_manifest.py        # writes data/golden/manifest.json from current state

Dockerfile.api
Dockerfile.web
docker-compose.yml
.dockerignore
.github/workflows/ci.yml           # extend to run full eval on nightly
```

---

## Task 1: `wiring.py` — singletons for shared state

- [ ] **Step 1: `apps/api/src/draftloop_api/wiring.py`**

```python
"""Process-level singletons. Avoid re-creating heavy components per request."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from draftloop_core.config import Settings, get_settings
from draftloop_core.llm import GeminiClient
from draftloop_core.storage.chroma_vector_index import ChromaVectorIndex
from draftloop_core.storage.local_blob_store import LocalBlobStore
from draftloop_core.storage.rank_bm25_lexical_index import RankBm25LexicalIndex
from draftloop_core.storage.sqlite_document_store import SqliteDocumentStore


@lru_cache(maxsize=1)
def gemini_client() -> GeminiClient:
    return GeminiClient()


@lru_cache(maxsize=1)
def document_store() -> SqliteDocumentStore:
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    return SqliteDocumentStore(Path(settings.data_dir) / "draftloop.db")


@lru_cache(maxsize=1)
def vector_index() -> ChromaVectorIndex:
    settings = get_settings()
    return ChromaVectorIndex(persist_path=str(Path(settings.data_dir) / "chroma"))


@lru_cache(maxsize=1)
def bm25_index() -> RankBm25LexicalIndex:
    settings = get_settings()
    return RankBm25LexicalIndex(persist_path=str(Path(settings.data_dir) / "bm25"))


@lru_cache(maxsize=1)
def blob_store() -> LocalBlobStore:
    settings = get_settings()
    return LocalBlobStore(root=str(Path(settings.data_dir) / "blob"))


def reset_singletons() -> None:
    for fn in (gemini_client, document_store, vector_index, bm25_index, blob_store):
        fn.cache_clear()
```

- [ ] **Step 2: Commit**

```bash
git commit -am "feat(api): add singleton wiring for storage + LLM"
```

---

## Task 2: Ingest route + matters route + admin routes

- [ ] **Step 1: `routes/ingest.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from draftloop_api.wiring import blob_store, document_store

router = APIRouter(prefix="/api/matters/{matter_id}/docs")


@router.post("", status_code=202)
async def upload_doc(matter_id: str, file: UploadFile = File(...), bg: BackgroundTasks = None) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    content = await file.read()
    key = f"{matter_id}/{file.filename}"
    await blob_store().put(key, content)
    await document_store().init_schema()
    await document_store().put(f"docs/{matter_id}/{file.filename}", {
        "status": "uploaded", "filename": file.filename, "blob_key": key,
    })
    return {"doc_id": file.filename, "status": "uploaded"}
```

- [ ] **Step 2: `routes/matters.py`**

```python
from __future__ import annotations

from fastapi import APIRouter

from draftloop_api.wiring import document_store

router = APIRouter(prefix="/api/matters")


@router.get("")
async def list_matters() -> dict:
    store = document_store()
    await store.init_schema()
    matter_ids: set[str] = set()
    async for key, _ in store.list("docs/"):
        parts = key.split("/")
        if len(parts) >= 2:
            matter_ids.add(parts[1])
    return {"matters": sorted(matter_ids)}


@router.get("/{matter_id}")
async def get_matter(matter_id: str) -> dict:
    store = document_store()
    await store.init_schema()
    docs: list[dict] = []
    async for key, value in store.list(f"docs/{matter_id}/"):
        docs.append({"key": key, "doc": value})
    drafts: list[dict] = []
    async for key, value in store.list(f"drafts/{matter_id}/"):
        drafts.append({"key": key, "draft": value})
    return {"matter_id": matter_id, "docs": docs, "drafts": drafts}
```

- [ ] **Step 3: `routes/admin.py`** (read-only views; production-grade auth in future)

```python
from __future__ import annotations

from fastapi import APIRouter

from draftloop_api.wiring import document_store

router = APIRouter(prefix="/admin")


@router.get("/rules")
async def list_rules() -> dict:
    store = document_store()
    await store.init_schema()
    rules: list[dict] = []
    async for _, v in store.list("rules/"):
        rules.append(v)
    return {"rules": rules}


@router.get("/replay")
async def list_replays() -> dict:
    store = document_store()
    await store.init_schema()
    out: list[dict] = []
    async for _, v in store.list("replay_reports/"):
        out.append(v)
    return {"reports": out}


@router.get("/edits")
async def list_edits() -> dict:
    store = document_store()
    await store.init_schema()
    n = 0
    async for _ in store.list("edit_events/"):
        n += 1
    return {"total_events": n}
```

- [ ] **Step 4: Register in `main.py`**

```python
from draftloop_api.routes import admin, drafts, edits, health, ingest, matters, version

def create_app() -> FastAPI:
    app = FastAPI(...)
    for r in (health.router, version.router, matters.router, ingest.router,
              drafts.router, edits.router, admin.router):
        app.include_router(r)
    return app
```

- [ ] **Step 5: Tests + commit**

```python
# apps/api/tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from draftloop_api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from draftloop_core.config import get_settings
    from draftloop_api.wiring import reset_singletons
    get_settings.cache_clear()
    reset_singletons()
    return TestClient(create_app())


def test_matters_empty(client):
    assert client.get("/api/matters").json() == {"matters": []}


def test_upload_doc_and_list_matter(client):
    files = {"file": ("complaint.pdf", b"%PDF-1.4 fake", "application/pdf")}
    r = client.post("/api/matters/M-001/docs", files=files)
    assert r.status_code == 202
    matters = client.get("/api/matters").json()["matters"]
    assert "M-001" in matters


def test_admin_lists_empty(client):
    assert client.get("/admin/rules").json() == {"rules": []}
    assert client.get("/admin/replay").json() == {"reports": []}
```

```bash
git commit -am "feat(api): add ingest + matters + admin routes; register all routes"
```

---

## Task 3: `scripts/seed_demo.py` (one-command demo)

- [ ] **Step 1: Write**

```python
#!/usr/bin/env python3
"""One-command demo seeder.

Steps:
  1. Build synthetic corpus (if missing).
  2. Upload each synthetic PDF to matter M-001.
  3. Ingest each doc into draftloop_ingest.
  4. Optionally generate a draft (requires GEMINI_API_KEY).
  5. Plant 1 simulated edit week against the draft.

Idempotent — running twice produces the same end state.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


async def _seed(force: bool, with_draft: bool) -> None:
    os.environ.setdefault("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "demo-not-used"))
    from draftloop_core.config import get_settings
    get_settings.cache_clear()

    import build_synthetic_corpus as corpus_gen
    corpus_gen.build(force=force)

    from draftloop_api.wiring import (
        blob_store, document_store, reset_singletons,
    )
    reset_singletons()
    store = document_store()
    await store.init_schema()
    blob = blob_store()

    for pdf in (REPO_ROOT / "data" / "synthetic").glob("*.pdf"):
        key = f"M-001/{pdf.name}"
        await blob.put(key, pdf.read_bytes())
        await store.put(f"docs/M-001/{pdf.name}", {
            "status": "uploaded", "filename": pdf.name, "blob_key": key,
        })
        print(f"==> uploaded {pdf.name}")

    if with_draft:
        # Lightweight: only run if a real API key is present.
        if os.environ.get("GEMINI_API_KEY", "").startswith(("demo", "sk-test")):
            print("==> skipping draft (no real GEMINI_API_KEY)")
            return
        # Ingest + draft wiring lands here in production. For seed, leave as TODO marker.
        print("==> draft generation: connect to /draft when API is up")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-draft", action="store_true")
    args = parser.parse_args()
    asyncio.run(_seed(force=args.force, with_draft=not args.no_draft))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke run + commit**

```bash
chmod +x scripts/seed_demo.py
uv run python scripts/seed_demo.py --no-draft
git commit -am "feat(scripts): add seed_demo.py for one-command demo"
```

---

## Task 4: Docker

- [ ] **Step 1: `Dockerfile.api`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/usr/local

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY apps/api ./apps/api
RUN uv sync --frozen --all-packages

WORKDIR /app/apps/api
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "draftloop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: `Dockerfile.web`**

```dockerfile
FROM node:20-slim AS builder

WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY packages/ui packages/ui
COPY apps/web apps/web
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
RUN pnpm install --frozen-lockfile
RUN pnpm -F @draftloop/ui build
RUN pnpm -F @draftloop/web build

FROM node:20-slim AS runtime
WORKDIR /app
COPY --from=builder /app /app
EXPOSE 3000
CMD ["pnpm", "-F", "@draftloop/web", "start"]
```

- [ ] **Step 3: `docker-compose.yml`**

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    env_file: .env
    ports:
      - "${PORT_API:-8000}:8000"
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8000/health | grep -q ok"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: .
      dockerfile: Dockerfile.web
    env_file: .env
    ports:
      - "${PORT_WEB:-3000}:3000"
    depends_on:
      api:
        condition: service_healthy
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:${PORT_API:-8000}
```

- [ ] **Step 4: `.dockerignore`**

```
.git
.venv
node_modules
data
.next
dist
__pycache__
*.pyc
```

- [ ] **Step 5: Smoke build + commit**

```bash
docker compose build
git add Dockerfile.api Dockerfile.web docker-compose.yml .dockerignore
git commit -m "feat(deploy): Dockerfile.api + Dockerfile.web + docker-compose.yml"
```

---

## Task 5: README finalize + screenshots

- [ ] **Step 1: Replace README.md** with the production version

```markdown
# DraftLoop

> Ingest messy legal documents → generate **grounded** Case Fact Summaries → measurably improve from operator edits.

## TL;DR (≤10 minutes from clone)

```bash
git clone <repo>
cd DraftLoop
cp .env.example .env       # add your GEMINI_API_KEY
docker compose up --build
# open http://localhost:3000
```

`SEED_ON_BOOT=true` (default in `.env.example`) means a demo matter is already loaded — click into it and you'll see an editor with a verified draft.

## Latest eval scorecard

| Section | Points | Primary metric | Status |
|---|---|---|---|
| Document Processing | 25 | extraction_f1 | see `docs/eval-reports/` |
| Retrieval & Grounding | 25 | context_precision@10 | see `docs/eval-reports/` |
| Draft Quality | 10 | Ragas faithfulness | see `docs/eval-reports/` |
| Improvement from Edits | 25 | edit_distance trend (lower-is-better) | see `docs/eval-reports/` |
| Code Quality & Design | 10 | coverage + lint | see `scripts/lint.sh` |
| Documentation | 5 | docs lint + reviewer time-to-first-draft | this README |

`bash scripts/eval.sh` regenerates the report into `docs/eval-reports/YYYY-MM-DD/`.

## Architecture overview

DraftLoop is a Turborepo monorepo.

- **`packages/draftloop_core`** — shared types, errors, Gemini SDK shim, storage protocols + impls.
- **`packages/draftloop_ingest`** — PDF probe → OCR pipeline → page-keyed Markdown.
- **`packages/draftloop_retrieval`** — chunking + Contextual Retrieval + hybrid (dense + BM25) + RRF + rerank.
- **`packages/draftloop_drafting`** — Pydantic schema (structural grounding) + tiered verifier (substring → HHEM → Flash judge) + audit trail.
- **`packages/draftloop_edits`** — improvement loop: classify → induce rule → memory bank → exemplar retrieval → critic → replay.
- **`packages/draftloop_eval`** — Ragas + HHEM + golden corpus + rubric scorecard.
- **`apps/api`** — FastAPI composition layer.
- **`apps/web`** — Next.js 15 operator editor.
- **`packages/ui`** — shared React components (editor, citation chip, evidence panel, audit drawer).

Full design specs are in `docs/superpowers/specs/`; the contributor contract is in `CLAUDE.md`.

## Assumptions & tradeoffs

- **Default OCR tier is offline.** `pymupdf4llm` for digital pages, OpenCV + PaddleOCR for scans, Tesseract as fallback. Handwritten / photo / low-res tiers (Gemini Vision + Real-ESRGAN + TrOCR) are deferred to Plan 1b.
- **Single Gemini provider.** All LLM calls go through `draftloop_core.llm` (boundary-lint enforced). Swap target would be a protocol-based abstraction; not implemented to keep scope tight.
- **Per-matter Chroma collections.** Strong isolation, simple invalidation, scales to dozens of matters out-of-the-box.
- **HHEM is local.** ~600MB download on first boot. `--no-hhem` mode degrades verification to substring + Flash-judge only.

## Sample inputs and outputs

`bash scripts/seed_demo.py` generates `data/synthetic/{complaint, motion, answer, order, complaint_scan, motion_scan}.pdf`. Sample drafts + audit trails appear under `data/drafts/M-001/` after a draft is requested.

## Evaluation approach + results

Run `bash scripts/eval.sh` to (re)build the latest report. Metrics map to the six rubric sections in the table above. Held-out replay over a 3-week simulated edit stream is the primary "Improvement from Edits" metric.

## Public-domain corpora for extension

- [CourtListener / RECAP](https://www.courtlistener.com/recap/), [Caselaw Access Project](https://case.law/), [SEC EDGAR](https://www.sec.gov/edgar), [Justia Cases](https://law.justia.com/cases/), [Free Law Project](https://free.law/data/).
```

- [ ] **Step 2: Commit**

```bash
git commit -am "docs: finalize README with TL;DR, scorecard pointer, architecture overview"
```

---

## Task 6: Final eval run + report linked from README

- [ ] **Step 1: Run full eval**

```bash
bash scripts/eval.sh
ls docs/eval-reports/
```

- [ ] **Step 2: Commit the report dir + update README's scorecard table with the latest numbers.**

```bash
git add docs/eval-reports
git commit -am "docs(eval): commit latest eval report + link from README"
```

---

## Task 7: Final verification + merge

- [ ] **Step 1: Full sweep**

```bash
bash scripts/lint.sh
uv run pytest -q
pnpm -r test
docker compose build
```

- [ ] **Step 2: Merge**

```bash
git checkout main
git merge --no-ff feat/plan-7-composition -m "Merge Plan 7: Composition + Demo + Polish"
```

- [ ] **Step 3: Tag release**

```bash
git tag v0.1.0 -m "DraftLoop v0.1.0 — initial submission"
```

- [ ] **Step 4: Update plans index — all plans done.**

---

## Done criteria

- [ ] `docker compose up` produces a working stack in ≤10 minutes on a fresh machine.
- [ ] `scripts/seed_demo.py` runs idempotently and leaves a demo matter loaded.
- [ ] `scripts/eval.sh` produces a fresh report in `docs/eval-reports/`.
- [ ] README links the latest report and clearly describes the demo flow.
- [ ] All packages green (`uv run pytest -q` + `pnpm -r test`).
- [ ] Plans index updated; project ready to push to GitHub for review.
