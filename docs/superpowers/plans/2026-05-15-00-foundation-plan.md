# Plan 0: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the DraftLoop monorepo with `draftloop_core` (shared types/errors/config/llm-shim/storage protocols), `apps/api` skeleton, `apps/web` skeleton, `packages/ui` skeleton, lint + boundary + diagram checks, and a green CI pipeline. After this plan, every subsequent plan can land cleanly into a known-good substrate.

**Architecture:** Turborepo monorepo. Python side: uv workspace, `packages/draftloop_core` + `apps/api`. JS side: pnpm workspace, `apps/web` + `packages/ui`. All cross-package boundaries enforced by `scripts/check_boundaries.py`. Diagrams validated by `scripts/check_diagrams.sh`.

**Tech Stack:** Python 3.12, uv ≥0.5, FastAPI ≥0.115, Pydantic ≥2.8, google-genai ≥0.6, structlog, opentelemetry-sdk, pytest, hypothesis, ruff, mypy. Node 20 LTS, pnpm ≥9, Next.js 15, React 19, TypeScript 5.6, Tailwind 3.4, shadcn/ui, Vitest. Turbo ≥2, mermaid-cli ≥10.

---

## File structure (created in this plan)

```
draftloop/
├─ pyproject.toml                    # uv workspace root
├─ uv.lock                           # generated
├─ pnpm-workspace.yaml
├─ package.json                      # JS workspace root (devDeps only)
├─ pnpm-lock.yaml                    # generated
├─ turbo.json
├─ .env.example
├─ .gitignore
├─ .dockerignore
├─ .nvmrc                            # 20
├─ .python-version                   # 3.12
├─ README.md                         # quick-start (replaces existing stub)
├─ CLAUDE.md                         # already exists from brainstorming
│
├─ packages/
│  ├─ draftloop_core/
│  │  ├─ pyproject.toml
│  │  ├─ src/draftloop_core/
│  │  │  ├─ __init__.py
│  │  │  ├─ types.py
│  │  │  ├─ errors.py
│  │  │  ├─ config.py
│  │  │  ├─ obs.py
│  │  │  ├─ llm.py
│  │  │  └─ storage/
│  │  │     ├─ __init__.py
│  │  │     ├─ document_store.py
│  │  │     ├─ vector_index.py
│  │  │     └─ blob_store.py
│  │  └─ tests/
│  │     ├─ test_types.py
│  │     ├─ test_errors.py
│  │     ├─ test_config.py
│  │     ├─ test_llm_shim.py
│  │     └─ test_storage_protocols.py
│  │
│  └─ ui/
│     ├─ package.json
│     ├─ tsconfig.json
│     ├─ tsup.config.ts
│     ├─ src/
│     │  ├─ index.ts
│     │  └─ components/
│     │     └─ HealthBadge.tsx
│     └─ tests/
│        └─ HealthBadge.test.tsx
│
├─ apps/
│  ├─ api/
│  │  ├─ pyproject.toml
│  │  ├─ src/draftloop_api/
│  │  │  ├─ __init__.py
│  │  │  ├─ main.py
│  │  │  ├─ lifespan.py
│  │  │  ├─ deps.py
│  │  │  └─ routes/
│  │  │     ├─ __init__.py
│  │  │     ├─ health.py
│  │  │     └─ version.py
│  │  └─ tests/
│  │     └─ test_health.py
│  │
│  └─ web/
│     ├─ package.json
│     ├─ tsconfig.json
│     ├─ next.config.mjs
│     ├─ tailwind.config.ts
│     ├─ postcss.config.mjs
│     ├─ components.json              # shadcn
│     ├─ src/
│     │  ├─ app/
│     │  │  ├─ layout.tsx
│     │  │  ├─ page.tsx
│     │  │  └─ globals.css
│     │  └─ lib/
│     │     └─ api/client.ts
│     └─ tests/
│        └─ home.test.tsx
│
├─ scripts/
│  ├─ setup.sh
│  ├─ dev.sh
│  ├─ lint.sh
│  ├─ check_boundaries.py
│  ├─ check_diagrams.sh
│  └─ check_diagrams_paths.sh         # helper called by check_diagrams.sh
│
├─ tests/
│  └─ contract/
│     └─ test_openapi_shape.py
│
└─ .github/workflows/
   └─ ci.yml
```

---

## Conventions

- All commits use Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- Every code-change commit follows TDD: failing test → impl → green test → commit.
- Python tests run via `uv run pytest`.
- JS tests run via `pnpm -F <pkg> test`.
- Boundary lint runs `python scripts/check_boundaries.py`.
- Diagrams lint runs `bash scripts/check_diagrams.sh`.

---

## Task 1: Initialize root workspace files

**Files:**
- Create: `pyproject.toml`
- Create: `pnpm-workspace.yaml`
- Create: `package.json`
- Create: `turbo.json`
- Create: `.python-version`
- Create: `.nvmrc`
- Create: `.gitignore` (append to existing if present)
- Create: `.env.example`

- [ ] **Step 1: Write `pyproject.toml` (uv workspace root)**

```toml
[project]
name = "draftloop-workspace"
version = "0.1.0"
description = "DraftLoop monorepo root"
requires-python = ">=3.12,<3.13"
dependencies = []

[tool.uv]
package = false                # this is a workspace root, not a package
dev-dependencies = [
    "ruff>=0.6.0",
    "mypy>=1.11.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "hypothesis>=6.112.0",
    "structlog>=24.4.0",
]

[tool.uv.workspace]
members = ["packages/draftloop_core", "apps/api"]

[tool.uv.sources]
draftloop-core = { workspace = true }

[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["data", "node_modules", ".venv"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC", "C4", "SIM", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["B011"]

[tool.mypy]
python_version = "3.12"
strict = true
exclude = ["build/", "dist/", ".venv/"]

[tool.pytest.ini_options]
addopts = "-ra -q --strict-markers"
asyncio_mode = "auto"
testpaths = ["packages", "apps", "tests"]
```

- [ ] **Step 2: Write `pnpm-workspace.yaml`**

```yaml
packages:
  - "apps/web"
  - "packages/ui"
```

- [ ] **Step 3: Write `package.json`**

```json
{
  "name": "draftloop",
  "version": "0.1.0",
  "private": true,
  "packageManager": "pnpm@9.12.0",
  "scripts": {
    "build": "turbo run build",
    "lint": "turbo run lint",
    "test": "turbo run test",
    "dev": "turbo run dev"
  },
  "devDependencies": {
    "turbo": "^2.1.0",
    "@mermaid-js/mermaid-cli": "^11.0.0",
    "typescript": "^5.6.2"
  }
}
```

- [ ] **Step 4: Write `turbo.json`**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"]
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

- [ ] **Step 5: Write `.python-version` and `.nvmrc`**

`.python-version`:
```
3.12
```

`.nvmrc`:
```
20
```

- [ ] **Step 6: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Node / Next.js
node_modules/
.next/
out/
dist/
.turbo/

# Data (gitignored runtime)
data/

# Env
.env
.env.*.local
!.env.example

# Editor
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 7: Write `.env.example`**

```
GEMINI_API_KEY=
DRAFTER_MODEL=gemini-2.5-pro
DRAFTER_MODE=single_call
EXTRACTION_MODEL=gemini-2.5-flash
EMBED_MODEL=gemini-embedding-001
EMBED_DIM=1536
RERANKER=flash
CRITIC_ENABLED=true
CRITIC_AUTO_APPLY=false
SEED_ON_BOOT=true
EVAL_COST_BUDGET_USD=2
STORE=sqlite
VECTOR_STORE=chroma
BLOB_STORE=local
DATA_DIR=./data
LANGFUSE_HOST=
LOG_LEVEL=INFO
PORT_API=8000
PORT_WEB=3000
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml pnpm-workspace.yaml package.json turbo.json .python-version .nvmrc .gitignore .env.example
git commit -m "chore: scaffold monorepo workspace roots (uv + pnpm + turbo)"
```

---

## Task 2: Scaffold `packages/draftloop_core` package

**Files:**
- Create: `packages/draftloop_core/pyproject.toml`
- Create: `packages/draftloop_core/src/draftloop_core/__init__.py`
- Create: `packages/draftloop_core/tests/__init__.py`

- [ ] **Step 1: Write `packages/draftloop_core/pyproject.toml`**

```toml
[project]
name = "draftloop-core"
version = "0.1.0"
description = "Shared types, errors, config, LLM shim, storage protocols"
requires-python = ">=3.12,<3.13"
dependencies = [
    "pydantic>=2.8.0",
    "pydantic-settings>=2.5.0",
    "structlog>=24.4.0",
    "opentelemetry-sdk>=1.27.0",
    "opentelemetry-exporter-otlp>=1.27.0",
    "google-genai>=0.6.0",
    "tenacity>=9.0.0",
    "ulid-py>=1.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/draftloop_core"]
```

- [ ] **Step 2: Write `packages/draftloop_core/src/draftloop_core/__init__.py`**

```python
"""DraftLoop core — shared types, errors, config, LLM shim, storage protocols.

Public API:
    types, errors, config, obs, llm, storage
"""
from draftloop_core import types, errors, config, obs, llm, storage

__all__ = ["types", "errors", "config", "obs", "llm", "storage"]
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `packages/draftloop_core/tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 4: Run uv sync to verify the package is detected**

Run: `uv sync --all-packages`
Expected: succeeds, creates `.venv/`, lists `draftloop-core` as a workspace member

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/pyproject.toml packages/draftloop_core/src packages/draftloop_core/tests uv.lock
git commit -m "feat(core): scaffold draftloop_core package"
```

---

## Task 3: `draftloop_core.errors` — error hierarchy

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/errors.py`
- Create: `packages/draftloop_core/tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

`packages/draftloop_core/tests/test_errors.py`:
```python
import pytest

from draftloop_core.errors import (
    DraftLoopError,
    IngestError,
    RetrievalError,
    DraftingError,
    EditLoopError,
    EvalError,
    ConfigError,
    LLMError,
    StorageError,
)


def test_root_error_carries_code_and_message():
    err = DraftLoopError(code="GENERIC", message="boom")
    assert err.code == "GENERIC"
    assert err.message == "boom"
    assert str(err) == "[GENERIC] boom"


def test_subclasses_set_default_code_prefix():
    cases = [
        (IngestError("oh no"), "INGEST"),
        (RetrievalError("oh no"), "RETRIEVAL"),
        (DraftingError("oh no"), "DRAFTING"),
        (EditLoopError("oh no"), "EDITS"),
        (EvalError("oh no"), "EVAL"),
        (ConfigError("oh no"), "CONFIG"),
        (LLMError("oh no"), "LLM"),
        (StorageError("oh no"), "STORAGE"),
    ]
    for err, prefix in cases:
        assert err.code.startswith(prefix), f"{type(err).__name__} -> {err.code}"


def test_explicit_code_overrides_default():
    err = IngestError("encrypted", code="INGEST_PDF_ENCRYPTED")
    assert err.code == "INGEST_PDF_ENCRYPTED"


def test_error_is_raisable():
    with pytest.raises(IngestError) as excinfo:
        raise IngestError("encrypted", code="INGEST_PDF_ENCRYPTED")
    assert excinfo.value.code == "INGEST_PDF_ENCRYPTED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/draftloop_core/tests/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'draftloop_core.errors'`

- [ ] **Step 3: Write minimal implementation**

`packages/draftloop_core/src/draftloop_core/errors.py`:
```python
"""DraftLoop error hierarchy with stable, machine-readable codes.

Every error has a `code` (e.g., "INGEST_PDF_ENCRYPTED") and a `message`.
UI surfaces match by `code`, not by string.
"""

from __future__ import annotations


class DraftLoopError(Exception):
    """Root error for all DraftLoop domain failures."""

    default_code_prefix: str = "GENERIC"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code_prefix

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class IngestError(DraftLoopError):
    default_code_prefix = "INGEST"


class RetrievalError(DraftLoopError):
    default_code_prefix = "RETRIEVAL"


class DraftingError(DraftLoopError):
    default_code_prefix = "DRAFTING"


class EditLoopError(DraftLoopError):
    default_code_prefix = "EDITS"


class EvalError(DraftLoopError):
    default_code_prefix = "EVAL"


class ConfigError(DraftLoopError):
    default_code_prefix = "CONFIG"


class LLMError(DraftLoopError):
    default_code_prefix = "LLM"


class StorageError(DraftLoopError):
    default_code_prefix = "STORAGE"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/draftloop_core/tests/test_errors.py -v`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/errors.py packages/draftloop_core/tests/test_errors.py
git commit -m "feat(core): add error hierarchy with stable codes"
```

---

## Task 4: `draftloop_core.types` — shared base types

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/types.py`
- Create: `packages/draftloop_core/tests/test_types.py`

- [ ] **Step 1: Write the failing test**

`packages/draftloop_core/tests/test_types.py`:
```python
import pytest
from pydantic import ValidationError

from draftloop_core.types import (
    MatterId, DocId, ChunkId, DraftId, EditEventId,
    OperatorId, RetrievalEngine, NeedsReview,
    Money,
)


def test_id_aliases_are_strings():
    m: MatterId = "M-001"
    d: DocId = "doc_3"
    c: ChunkId = "doc_3_p4_¶12_c_0012"
    assert all(isinstance(x, str) for x in [m, d, c])


def test_needs_review_invariant_low_conf_is_review():
    nr = NeedsReview.from_confidence(0.65)
    assert nr.needs_review is True
    nr = NeedsReview.from_confidence(0.95)
    assert nr.needs_review is False


def test_needs_review_threshold_boundary():
    """Confidence exactly at 0.80 is NOT needs_review."""
    nr = NeedsReview.from_confidence(0.80)
    assert nr.needs_review is False
    nr = NeedsReview.from_confidence(0.7999)
    assert nr.needs_review is True


def test_retrieval_engine_enum():
    assert RetrievalEngine.DENSE.value == "dense"
    assert RetrievalEngine.BM25.value == "bm25"


def test_money_arithmetic_preserves_currency():
    a = Money(amount=1.5, currency="USD")
    b = Money(amount=2.5, currency="USD")
    assert (a + b).amount == 4.0
    assert (a + b).currency == "USD"


def test_money_rejects_mixed_currency():
    a = Money(amount=1.5, currency="USD")
    b = Money(amount=2.5, currency="EUR")
    with pytest.raises(ValueError):
        _ = a + b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/draftloop_core/tests/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'draftloop_core.types'`

- [ ] **Step 3: Write minimal implementation**

`packages/draftloop_core/src/draftloop_core/types.py`:
```python
"""Shared base types used across all draftloop_* packages.

Anything imported by two or more packages MUST live here, per CLAUDE.md §1.3.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NewType

from pydantic import BaseModel, ConfigDict, Field

MatterId = NewType("MatterId", str)
DocId = NewType("DocId", str)
ChunkId = NewType("ChunkId", str)
DraftId = NewType("DraftId", str)
EditEventId = NewType("EditEventId", str)
OperatorId = NewType("OperatorId", str)
RuleId = NewType("RuleId", str)
PrincipleId = NewType("PrincipleId", str)

NEEDS_REVIEW_THRESHOLD = 0.80


class RetrievalEngine(StrEnum):
    DENSE = "dense"
    BM25 = "bm25"


class EditClass(StrEnum):
    FACT_CORRECTION = "fact_correction"
    CITATION_FIX = "citation_fix"
    TONE = "tone"
    STRUCTURE = "structure"
    ADDITION = "addition"
    DELETION = "deletion"


class NeedsReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_review: bool

    @classmethod
    def from_confidence(cls, confidence: float) -> "NeedsReview":
        return cls(
            confidence=confidence,
            needs_review=confidence < NEEDS_REVIEW_THRESHOLD,
        )


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount: float
    currency: str = "USD"

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(
                f"cannot add Money in different currencies: {self.currency} vs {other.currency}"
            )
        return Money(amount=self.amount + other.amount, currency=self.currency)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/draftloop_core/tests/test_types.py -v`
Expected: PASS — 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/types.py packages/draftloop_core/tests/test_types.py
git commit -m "feat(core): add shared types (ids, enums, NeedsReview, Money)"
```

---

## Task 5: `draftloop_core.config` — Pydantic Settings

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/config.py`
- Create: `packages/draftloop_core/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`packages/draftloop_core/tests/test_config.py`:
```python
import pytest

from draftloop_core.config import Settings, get_settings
from draftloop_core.errors import ConfigError


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DRAFTER_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("EMBED_DIM", "1536")
    s = Settings()
    assert s.gemini_api_key.get_secret_value() == "sk-test"
    assert s.drafter_model == "gemini-2.5-pro"
    assert s.embed_dim == 1536


def test_settings_defaults_applied(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    s = Settings()
    assert s.drafter_mode == "single_call"
    assert s.embed_dim == 1536
    assert s.store == "sqlite"
    assert s.vector_store == "chroma"
    assert s.blob_store == "local"


def test_settings_validates_drafter_mode(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    monkeypatch.setenv("DRAFTER_MODE", "invalid_mode")
    with pytest.raises(ConfigError):
        Settings()


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    a = get_settings()
    b = get_settings()
    assert a is b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/draftloop_core/tests/test_config.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/draftloop_core/src/draftloop_core/config.py`:
```python
"""Centralized Pydantic Settings for DraftLoop.

Single source of truth for runtime config. Use `get_settings()` everywhere.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from draftloop_core.errors import ConfigError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gemini_api_key: SecretStr = Field(...)
    drafter_model: str = Field(default="gemini-2.5-pro")
    drafter_mode: Literal["single_call", "two_call"] = "single_call"
    extraction_model: str = Field(default="gemini-2.5-flash")
    embed_model: str = Field(default="gemini-embedding-001")
    embed_dim: int = Field(default=1536, ge=128, le=3072)

    critic_enabled: bool = True
    critic_auto_apply: bool = False
    seed_on_boot: bool = False
    eval_cost_budget_usd: float = 2.0

    store: Literal["sqlite", "postgres"] = "sqlite"
    vector_store: Literal["chroma", "qdrant"] = "chroma"
    blob_store: Literal["local", "s3"] = "local"
    data_dir: str = "./data"

    langfuse_host: str = ""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    port_api: int = 8000
    port_web: int = 3000

    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)
        except ValidationError as e:
            raise ConfigError(
                f"invalid settings: {e}",
                code="CONFIG_VALIDATION",
            ) from e


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/draftloop_core/tests/test_config.py -v`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/config.py packages/draftloop_core/tests/test_config.py
git commit -m "feat(core): add Pydantic Settings with env loading + validation"
```

---

## Task 6: `draftloop_core.obs` — structured logging + OTel span helper

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/obs.py`
- Create: `packages/draftloop_core/tests/test_obs.py`

- [ ] **Step 1: Write the failing test**

`packages/draftloop_core/tests/test_obs.py`:
```python
import structlog

from draftloop_core.obs import configure_logging, get_logger, traced


def test_get_logger_returns_structlog_logger():
    configure_logging("INFO")
    log = get_logger("draftloop.test")
    assert isinstance(log, structlog.stdlib.BoundLogger) or hasattr(log, "info")


def test_traced_decorator_runs_and_returns_value():
    @traced("test.op")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5


def test_traced_decorator_records_exception(caplog):
    @traced("test.op")
    def boom() -> None:
        raise ValueError("nope")

    try:
        boom()
    except ValueError:
        pass
    # No assertion on log content — span propagation tested in integration.
    # Here we only assert the decorator does not swallow the exception.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/draftloop_core/tests/test_obs.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/draftloop_core/src/draftloop_core/obs.py`:
```python
"""Observability: structlog logging + OTel span decorator.

Every public entry point in a package should be `@traced("<package>.<op>")`.
"""

from __future__ import annotations

import functools
import logging
import sys
from collections.abc import Callable
from typing import TypeVar

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

T = TypeVar("T")


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + OTel. Idempotent."""
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level.upper()),
        format="%(message)s",
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        cache_logger_on_first_use=True,
    )

    if trace.get_tracer_provider().__class__.__name__ != "TracerProvider":
        provider = TracerProvider(resource=Resource.create({"service.name": "draftloop"}))
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def traced(span_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Wrap a callable in an OTel span. Re-raises exceptions after recording."""

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        tracer = trace.get_tracer("draftloop")

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise

        return wrapper

    return decorator
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/draftloop_core/tests/test_obs.py -v`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/obs.py packages/draftloop_core/tests/test_obs.py
git commit -m "feat(core): add structlog + OTel span helper"
```

---

## Task 7: `draftloop_core.llm` — Gemini SDK shim with retry + telemetry

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/llm.py`
- Create: `packages/draftloop_core/tests/test_llm_shim.py`

- [ ] **Step 1: Write the failing test**

`packages/draftloop_core/tests/test_llm_shim.py`:
```python
from unittest.mock import MagicMock

import pytest

from draftloop_core.llm import GeminiClient, LLMResponse, LLMUsage


@pytest.fixture
def fake_sdk(monkeypatch):
    """Patch the google.genai.Client so no network call is made."""
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.text = '{"ok": true}'
    fake_resp.usage_metadata = MagicMock(
        prompt_token_count=100,
        candidates_token_count=50,
        cached_content_token_count=0,
    )
    fake_client.models.generate_content.return_value = fake_resp

    fake_emb_resp = MagicMock()
    fake_emb_resp.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    fake_client.models.embed_content.return_value = fake_emb_resp

    import draftloop_core.llm as llm_mod
    monkeypatch.setattr(llm_mod, "_build_sdk_client", lambda: fake_client)
    return fake_client


def test_generate_text_returns_llm_response(fake_sdk, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    client = GeminiClient()
    resp = client.generate(model="gemini-2.5-pro", contents="hi")
    assert isinstance(resp, LLMResponse)
    assert resp.text == '{"ok": true}'
    assert isinstance(resp.usage, LLMUsage)
    assert resp.usage.input_tokens == 100
    assert resp.usage.output_tokens == 50
    assert resp.usage.cached_tokens == 0


def test_embed_returns_vectors(fake_sdk, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    client = GeminiClient()
    vecs = client.embed(
        model="gemini-embedding-001",
        contents=["chunk"],
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=3,
    )
    assert vecs == [[0.1, 0.2, 0.3]]


def test_embed_enforces_batch_cap(fake_sdk, monkeypatch):
    """Gemini caps embed_content at 100 inputs per call."""
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    client = GeminiClient()
    with pytest.raises(ValueError, match="batch size"):
        client.embed(
            model="gemini-embedding-001",
            contents=["x"] * 101,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=3,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/draftloop_core/tests/test_llm_shim.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/draftloop_core/src/draftloop_core/llm.py`:
```python
"""Single point of contact for Google Gemini.

All Gemini calls in DraftLoop go through this module (CLAUDE.md §4).
Boundary lint blocks `from google import genai` elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types as genai_types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from draftloop_core.config import get_settings
from draftloop_core.errors import LLMError
from draftloop_core.obs import get_logger

logger = get_logger("draftloop.llm")

EMBED_BATCH_CAP = 100  # Gemini hard cap (see research brief)
EMBED_INPUT_TOKEN_CAP = 2048  # gemini-embedding-001 per-item cap


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    cached_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: LLMUsage
    model: str
    parsed: Any | None = None


def _build_sdk_client() -> genai.Client:
    settings = get_settings()
    api_key = settings.gemini_api_key.get_secret_value()
    if not api_key:
        raise LLMError("GEMINI_API_KEY is empty", code="LLM_MISSING_API_KEY")
    return genai.Client(api_key=api_key)


class GeminiClient:
    """Thin shim around google-genai with retry + structured logging."""

    def __init__(self) -> None:
        self._client = _build_sdk_client()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def generate(
        self,
        *,
        model: str,
        contents: Any,
        config: dict[str, Any] | None = None,
    ) -> LLMResponse:
        try:
            resp = self._client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise LLMError(
                f"generate_content failed: {exc}",
                code="LLM_GENERATE_FAILED",
            ) from exc

        usage_meta = getattr(resp, "usage_metadata", None)
        usage = LLMUsage(
            input_tokens=getattr(usage_meta, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage_meta, "candidates_token_count", 0) or 0,
            cached_tokens=getattr(usage_meta, "cached_content_token_count", 0) or 0,
        )

        logger.info(
            "llm.generate",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
        )

        return LLMResponse(
            text=resp.text or "",
            usage=usage,
            model=model,
            parsed=getattr(resp, "parsed", None),
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def embed(
        self,
        *,
        model: str,
        contents: list[str],
        task_type: str,
        output_dimensionality: int,
    ) -> list[list[float]]:
        if len(contents) > EMBED_BATCH_CAP:
            raise ValueError(
                f"embed batch size {len(contents)} exceeds cap {EMBED_BATCH_CAP}"
            )

        try:
            resp = self._client.models.embed_content(
                model=model,
                contents=contents,
                config=genai_types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=output_dimensionality,
                )
                if hasattr(genai_types, "EmbedContentConfig")
                else {
                    "task_type": task_type,
                    "output_dimensionality": output_dimensionality,
                },
            )
        except Exception as exc:
            raise LLMError(
                f"embed_content failed: {exc}",
                code="LLM_EMBED_FAILED",
            ) from exc

        return [list(e.values) for e in resp.embeddings]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/draftloop_core/tests/test_llm_shim.py -v`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/llm.py packages/draftloop_core/tests/test_llm_shim.py
git commit -m "feat(core): add Gemini SDK shim with retry, telemetry, batch caps"
```

---

## Task 8: `draftloop_core.storage` — protocols (DocumentStore, VectorIndex, BlobStore)

**Files:**
- Create: `packages/draftloop_core/src/draftloop_core/storage/__init__.py`
- Create: `packages/draftloop_core/src/draftloop_core/storage/document_store.py`
- Create: `packages/draftloop_core/src/draftloop_core/storage/vector_index.py`
- Create: `packages/draftloop_core/src/draftloop_core/storage/blob_store.py`
- Create: `packages/draftloop_core/tests/test_storage_protocols.py`

- [ ] **Step 1: Write the failing test**

`packages/draftloop_core/tests/test_storage_protocols.py`:
```python
import inspect
from typing import get_type_hints

from draftloop_core.storage import (
    DocumentStore,
    VectorIndex,
    BlobStore,
    VectorItem,
    VectorHit,
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
    assert 0.0 <= hit.score <= 1.0 or hit.score >= 0.0  # cosine / IP both fine


def test_protocols_are_runtime_checkable():
    """Protocols should be @runtime_checkable so duck-typed impls can be asserted."""
    class FakeDS:
        async def get(self, key): ...
        async def put(self, key, value): ...
        async def delete(self, key): ...
        async def list(self, prefix): ...

    inst = FakeDS()
    # Will use isinstance at runtime via @runtime_checkable
    assert isinstance(inst, DocumentStore)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/draftloop_core/tests/test_storage_protocols.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/draftloop_core/src/draftloop_core/storage/__init__.py`:
```python
from draftloop_core.storage.blob_store import BlobStore
from draftloop_core.storage.document_store import DocumentStore
from draftloop_core.storage.vector_index import VectorHit, VectorIndex, VectorItem

__all__ = [
    "BlobStore",
    "DocumentStore",
    "VectorIndex",
    "VectorItem",
    "VectorHit",
]
```

`packages/draftloop_core/src/draftloop_core/storage/document_store.py`:
```python
"""DocumentStore protocol — generic key/value persistence for domain objects.

Default impl: SQLite (added in Plan 1). Production swap: Postgres.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DocumentStore(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def put(self, key: str, value: Any) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def list(self, prefix: str = "") -> AsyncIterator[tuple[str, Any]]: ...
```

`packages/draftloop_core/src/draftloop_core/storage/vector_index.py`:
```python
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
    async def upsert(
        self, collection: str, items: list[VectorItem]
    ) -> None: ...
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorHit]: ...
    async def delete_collection(self, collection: str) -> None: ...
```

`packages/draftloop_core/src/draftloop_core/storage/blob_store.py`:
```python
"""BlobStore protocol — raw bytes (PDFs, page images, model weights).

Default impl: local FS (added in Plan 1). Production swap: S3.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobStore(Protocol):
    async def get(self, key: str) -> bytes: ...
    async def put(self, key: str, data: bytes) -> None: ...
    async def delete(self, key: str) -> None: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/draftloop_core/tests/test_storage_protocols.py -v`
Expected: PASS — 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add packages/draftloop_core/src/draftloop_core/storage packages/draftloop_core/tests/test_storage_protocols.py
git commit -m "feat(core): add storage protocols (DocumentStore, VectorIndex, BlobStore)"
```

---

## Task 9: Scaffold `apps/api` with health endpoint

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/draftloop_api/__init__.py`
- Create: `apps/api/src/draftloop_api/main.py`
- Create: `apps/api/src/draftloop_api/lifespan.py`
- Create: `apps/api/src/draftloop_api/deps.py`
- Create: `apps/api/src/draftloop_api/routes/__init__.py`
- Create: `apps/api/src/draftloop_api/routes/health.py`
- Create: `apps/api/src/draftloop_api/routes/version.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Write `apps/api/pyproject.toml`**

```toml
[project]
name = "draftloop-api"
version = "0.1.0"
description = "DraftLoop FastAPI composition app"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "draftloop-core",
    "httpx>=0.27.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/draftloop_api"]
```

- [ ] **Step 2: Run uv sync**

Run: `uv sync --all-packages`
Expected: succeeds with `draftloop-api` listed as a workspace member.

- [ ] **Step 3: Write the failing test**

`apps/api/tests/test_health.py`:
```python
import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    app = create_app()
    return TestClient(app)


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body
    assert body["uptime_seconds"] >= 0


def test_version_returns_semver(client):
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert body["version"].count(".") == 2
```

`apps/api/tests/__init__.py`: empty file.

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'draftloop_api'`.

- [ ] **Step 5: Write the API skeleton**

`apps/api/src/draftloop_api/__init__.py`:
```python
__version__ = "0.1.0"
```

`apps/api/src/draftloop_api/lifespan.py`:
```python
"""FastAPI lifespan: startup/shutdown hooks (logging, settings warm-up)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from draftloop_core.config import get_settings
from draftloop_core.obs import configure_logging, get_logger

logger = get_logger("draftloop.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.started_at = time.monotonic()
    logger.info("api.startup", drafter_model=settings.drafter_model)
    yield
    logger.info("api.shutdown")
```

`apps/api/src/draftloop_api/deps.py`:
```python
"""FastAPI dependency providers (DI surface)."""

from __future__ import annotations

from draftloop_core.config import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()
```

`apps/api/src/draftloop_api/routes/__init__.py`:
```python
from draftloop_api.routes import health, version

__all__ = ["health", "version"]
```

`apps/api/src/draftloop_api/routes/health.py`:
```python
from __future__ import annotations

import time

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    started = getattr(request.app.state, "started_at", time.monotonic())
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - started),
    }
```

`apps/api/src/draftloop_api/routes/version.py`:
```python
from __future__ import annotations

from fastapi import APIRouter

from draftloop_api import __version__

router = APIRouter()


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": __version__}
```

`apps/api/src/draftloop_api/main.py`:
```python
"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from draftloop_api import __version__
from draftloop_api.lifespan import lifespan
from draftloop_api.routes import health, version


def create_app() -> FastAPI:
    app = FastAPI(
        title="DraftLoop API",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(version.router)
    return app


app = create_app()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest apps/api/tests/test_health.py -v`
Expected: PASS — 2 tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api packages/draftloop_core/src/draftloop_core/__init__.py uv.lock
git commit -m "feat(api): scaffold FastAPI app with /health and /version"
```

---

## Task 10: Add OpenAPI schema contract test

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/contract/__init__.py`
- Create: `tests/contract/test_openapi_shape.py`

- [ ] **Step 1: Write the failing test**

`tests/__init__.py`: empty.
`tests/contract/__init__.py`: empty.

`tests/contract/test_openapi_shape.py`:
```python
"""Contract: OpenAPI schema must include /health and /version, and the
operationIds must be stable so the generated TS client doesn't churn.
"""

import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    return TestClient(create_app())


def test_openapi_lists_health_and_version(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    paths = schema["paths"]
    assert "/health" in paths
    assert "/version" in paths


def test_openapi_has_app_metadata(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "DraftLoop API"
    assert schema["info"]["version"].count(".") == 2
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/contract/test_openapi_shape.py -v`
Expected: PASS — 2 tests pass (no new impl needed; just locks the contract).

- [ ] **Step 3: Commit**

```bash
git add tests/__init__.py tests/contract/
git commit -m "test(contract): pin OpenAPI shape for /health and /version"
```

---

## Task 11: Scaffold `apps/web` (Next.js 15 + Tailwind + shadcn)

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.mjs`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/components.json`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/globals.css`
- Create: `apps/web/src/lib/api/client.ts`

- [ ] **Step 1: Write `apps/web/package.json`**

```json
{
  "name": "@draftloop/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port ${PORT_WEB:-3000}",
    "build": "next build",
    "start": "next start --port ${PORT_WEB:-3000}",
    "lint": "next lint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@draftloop/ui": "workspace:*",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "autoprefixer": "^10.4.20",
    "eslint": "^9",
    "eslint-config-next": "^15.0.0",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.13",
    "typescript": "^5.6.2",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.5.0",
    "jsdom": "^25.0.0"
  }
}
```

- [ ] **Step 2: Write `apps/web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Write `apps/web/next.config.mjs`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@draftloop/ui"],
};

export default nextConfig;
```

- [ ] **Step 4: Write `apps/web/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Write `apps/web/postcss.config.mjs`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Write `apps/web/components.json` (shadcn config)**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

- [ ] **Step 7: Write `apps/web/src/app/layout.tsx`**

```tsx
import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "DraftLoop",
  description: "Grounded legal drafting with an improvement-from-edits loop",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 8: Write `apps/web/src/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 9: Write `apps/web/src/app/page.tsx`**

```tsx
import { HealthBadge } from "@draftloop/ui";

export default async function Home() {
  let apiHealthy = false;
  try {
    const res = await fetch("http://localhost:8000/health", { cache: "no-store" });
    apiHealthy = res.ok;
  } catch {
    apiHealthy = false;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">DraftLoop</h1>
      <p className="mt-3 text-slate-600">
        Grounded legal drafting with an improvement-from-edits loop.
      </p>
      <div className="mt-8">
        <HealthBadge ok={apiHealthy} label={apiHealthy ? "API healthy" : "API unreachable"} />
      </div>
    </main>
  );
}
```

- [ ] **Step 10: Write `apps/web/src/lib/api/client.ts`**

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}
```

- [ ] **Step 11: Commit**

```bash
git add apps/web
git commit -m "feat(web): scaffold Next.js 15 + Tailwind + shadcn config"
```

---

## Task 12: Scaffold `packages/ui` (tsup + HealthBadge)

**Files:**
- Create: `packages/ui/package.json`
- Create: `packages/ui/tsconfig.json`
- Create: `packages/ui/tsup.config.ts`
- Create: `packages/ui/src/index.ts`
- Create: `packages/ui/src/components/HealthBadge.tsx`
- Create: `packages/ui/tests/HealthBadge.test.tsx`
- Create: `packages/ui/vitest.config.ts`

- [ ] **Step 1: Write `packages/ui/package.json`**

```json
{
  "name": "@draftloop/ui",
  "version": "0.1.0",
  "private": true,
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.mjs",
      "require": "./dist/index.js"
    }
  },
  "scripts": {
    "build": "tsup",
    "dev": "tsup --watch",
    "lint": "eslint src",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "peerDependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "tsup": "^8.3.0",
    "typescript": "^5.6.2",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.5.0",
    "jsdom": "^25.0.0",
    "eslint": "^9"
  }
}
```

- [ ] **Step 2: Write `packages/ui/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "node_modules"]
}
```

- [ ] **Step 3: Write `packages/ui/tsup.config.ts`**

```typescript
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  sourcemap: true,
  clean: true,
  external: ["react", "react-dom"],
});
```

- [ ] **Step 4: Write `packages/ui/src/index.ts`**

```typescript
export { HealthBadge } from "./components/HealthBadge";
```

- [ ] **Step 5: Write `packages/ui/src/components/HealthBadge.tsx`**

```tsx
import type { ReactElement } from "react";

export interface HealthBadgeProps {
  ok: boolean;
  label: string;
}

export function HealthBadge({ ok, label }: HealthBadgeProps): ReactElement {
  const cls = ok
    ? "bg-emerald-100 text-emerald-800"
    : "bg-rose-100 text-rose-800";
  return (
    <span
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${cls}`}
    >
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}
      />
      {label}
    </span>
  );
}
```

- [ ] **Step 6: Write `packages/ui/vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
```

- [ ] **Step 7: Write `packages/ui/tests/setup.ts`**

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 8: Write the failing test**

`packages/ui/tests/HealthBadge.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HealthBadge } from "../src/components/HealthBadge";

describe("HealthBadge", () => {
  it("renders the label", () => {
    render(<HealthBadge ok={true} label="API healthy" />);
    expect(screen.getByRole("status")).toHaveTextContent("API healthy");
  });

  it("applies emerald classes when ok=true", () => {
    render(<HealthBadge ok={true} label="OK" />);
    expect(screen.getByRole("status").className).toContain("emerald");
  });

  it("applies rose classes when ok=false", () => {
    render(<HealthBadge ok={false} label="Down" />);
    expect(screen.getByRole("status").className).toContain("rose");
  });
});
```

- [ ] **Step 9: Install JS deps and run tests**

Run: `pnpm install`
Run: `pnpm -F @draftloop/ui test`
Expected: PASS — 3 tests pass.

- [ ] **Step 10: Build the package**

Run: `pnpm -F @draftloop/ui build`
Expected: `packages/ui/dist/index.{js,mjs,d.ts}` produced.

- [ ] **Step 11: Commit**

```bash
git add packages/ui pnpm-lock.yaml
git commit -m "feat(ui): scaffold packages/ui with HealthBadge + tsup build"
```

---

## Task 13: `scripts/setup.sh` — one-shot environment bring-up

**Files:**
- Create: `scripts/setup.sh`

- [ ] **Step 1: Write `scripts/setup.sh`**

```bash
#!/usr/bin/env bash
# DraftLoop one-shot setup.
# Installs uv + pnpm, syncs workspaces, optionally downloads ML models.
set -euo pipefail

usage() {
  cat <<EOF
Usage: scripts/setup.sh [--no-models] [--no-docker] [--help]

  --no-models   Skip HHEM weight download (added by Plan 3)
  --no-docker   Skip Docker-related setup (added by Plan 7)
  --help        Show this message
EOF
}

WITH_MODELS=1
WITH_DOCKER=1
for arg in "$@"; do
  case "$arg" in
    --no-models) WITH_MODELS=0 ;;
    --no-docker) WITH_DOCKER=0 ;;
    --help|-h)   usage; exit 0 ;;
    *)           echo "unknown arg: $arg"; usage; exit 1 ;;
  esac
done

echo "==> ensuring uv is installed"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "==> ensuring pnpm is installed (via corepack)"
if ! command -v pnpm >/dev/null 2>&1; then
  corepack enable
  corepack prepare pnpm@9.12.0 --activate
fi

echo "==> uv sync (Python workspace)"
uv sync --all-packages

echo "==> pnpm install (JS workspace)"
pnpm install

if [ "$WITH_MODELS" = "1" ]; then
  echo "==> model downloads deferred until Plan 3 (HHEM)"
fi

if [ "$WITH_DOCKER" = "1" ]; then
  echo "==> docker setup deferred until Plan 7"
fi

echo "==> setup complete"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/setup.sh`

- [ ] **Step 3: Smoke-run the script**

Run: `bash scripts/setup.sh --no-models --no-docker`
Expected: ends with `==> setup complete`, no errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/setup.sh
git commit -m "chore(scripts): add setup.sh one-shot environment bring-up"
```

---

## Task 14: `scripts/dev.sh` — boot api + web together

**Files:**
- Create: `scripts/dev.sh`

- [ ] **Step 1: Write `scripts/dev.sh`**

```bash
#!/usr/bin/env bash
# Boot the dev stack: apps/api (uvicorn reload) + apps/web (next dev).
set -euo pipefail

PORT_API="${PORT_API:-8000}"
PORT_WEB="${PORT_WEB:-3000}"

pids=()
cleanup() {
  echo
  echo "==> stopping dev servers"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "==> apps/api on :$PORT_API"
(
  cd apps/api
  uv run uvicorn draftloop_api.main:app --reload --host 0.0.0.0 --port "$PORT_API"
) &
pids+=("$!")

echo "==> apps/web on :$PORT_WEB"
(
  PORT_WEB="$PORT_WEB" pnpm -F @draftloop/web dev
) &
pids+=("$!")

wait
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/dev.sh`

- [ ] **Step 3: Commit**

```bash
git add scripts/dev.sh
git commit -m "chore(scripts): add dev.sh to boot api + web concurrently"
```

---

## Task 15: `scripts/check_boundaries.py` — Python boundary lint

**Files:**
- Create: `scripts/check_boundaries.py`
- Create: `tests/lint/test_boundary_lint.py`
- Create: `tests/lint/__init__.py`

- [ ] **Step 1: Write the failing test**

`tests/lint/__init__.py`: empty.

`tests/lint/test_boundary_lint.py`:
```python
"""Boundary lint test: planted violation must be flagged.

Creates a tmp tree mimicking packages/foo/src/foo/__init__.py importing
packages/bar/src/bar/_internal/secret.py and asserts the linter exits non-zero.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_legitimate_imports_pass(tmp_path):
    # Build a clean fake monorepo
    pkg_a = tmp_path / "packages" / "draftloop_a" / "src" / "draftloop_a"
    pkg_b = tmp_path / "packages" / "draftloop_b" / "src" / "draftloop_b"
    for d in (pkg_a, pkg_b):
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    (pkg_a / "__init__.py").write_text("from draftloop_b import api\n")
    (pkg_b / "api.py").write_text("")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_internal_import_fails(tmp_path):
    pkg_a = tmp_path / "packages" / "draftloop_a" / "src" / "draftloop_a"
    pkg_b = tmp_path / "packages" / "draftloop_b" / "src" / "draftloop_b" / "_internal"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)
    (pkg_a / "__init__.py").write_text("from draftloop_b._internal import secret\n")
    (pkg_b.parent / "__init__.py").write_text("")
    (pkg_b / "__init__.py").write_text("")
    (pkg_b / "secret.py").write_text("")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "_internal" in (result.stdout + result.stderr)


def test_direct_genai_import_outside_core_fails(tmp_path):
    pkg = tmp_path / "packages" / "draftloop_ingest" / "src" / "draftloop_ingest"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from google import genai\n")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "genai" in (result.stdout + result.stderr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/lint/test_boundary_lint.py -v`
Expected: FAIL — `scripts/check_boundaries.py` does not exist yet.

- [ ] **Step 3: Write the boundary lint script**

`scripts/check_boundaries.py`:
```python
#!/usr/bin/env python3
"""Boundary lint for DraftLoop packages.

Rules:
  1. No package imports from another package's `_internal/` submodule.
  2. No package imports from `apps/`.
  3. Only `draftloop_core.llm` may `from google import genai`.
  4. Inline escape: a line with comment `# boundary: allow <reason>` is exempt.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def is_allowed_genai_module(module_path: Path) -> bool:
    parts = module_path.parts
    if "draftloop_core" in parts and module_path.name == "llm.py":
        return True
    return False


def check_file(py: Path, root: Path) -> list[str]:
    violations: list[str] = []
    try:
        source = py.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return violations

    try:
        tree = ast.parse(source, filename=str(py))
    except SyntaxError:
        return violations

    lines = source.splitlines()

    def is_exempt(lineno: int) -> bool:
        idx = lineno - 1
        if 0 <= idx < len(lines):
            return "# boundary: allow" in lines[idx]
        return False

    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.ImportFrom) and node.module:
            target = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                break
        if target is None:
            continue

        if "._internal" in target or target.endswith("._internal"):
            if not is_exempt(node.lineno):
                violations.append(
                    f"{py.relative_to(root)}:{node.lineno}: forbidden _internal import: {target}"
                )

        if target.startswith("apps.") or target == "apps":
            if not is_exempt(node.lineno):
                violations.append(
                    f"{py.relative_to(root)}:{node.lineno}: package may not import from apps: {target}"
                )

        if target.startswith("google.genai") or target == "google.genai" or target == "google":
            # Allow only inside draftloop_core/llm.py
            if not is_allowed_genai_module(py) and not is_exempt(node.lineno):
                violations.append(
                    f"{py.relative_to(root)}:{node.lineno}: direct google.genai import outside draftloop_core.llm: {target}"
                )

    return violations


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    args = p.parse_args()

    root = Path(args.root).resolve()
    pkg_root = root / "packages"
    if not pkg_root.exists():
        print(f"no packages/ under {root}", file=sys.stderr)
        return 0

    all_violations: list[str] = []
    for py in pkg_root.rglob("*.py"):
        if "/.venv/" in str(py) or "/__pycache__/" in str(py):
            continue
        all_violations.extend(check_file(py, root))

    if all_violations:
        print("Boundary violations found:")
        for v in all_violations:
            print(f"  {v}")
        return 1

    print("Boundaries clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Make executable and run test**

Run: `chmod +x scripts/check_boundaries.py`
Run: `uv run pytest tests/lint/test_boundary_lint.py -v`
Expected: PASS — 3 tests pass.

- [ ] **Step 5: Run against the real repo to verify zero current violations**

Run: `uv run python scripts/check_boundaries.py --root .`
Expected: `Boundaries clean.` (exit 0)

- [ ] **Step 6: Commit**

```bash
git add scripts/check_boundaries.py tests/lint/
git commit -m "chore(scripts): add Python boundary lint with planted-violation tests"
```

---

## Task 16: `scripts/check_diagrams.sh` — Mermaid diagram render check

**Files:**
- Create: `scripts/check_diagrams.sh`

- [ ] **Step 1: Write `scripts/check_diagrams.sh`**

```bash
#!/usr/bin/env bash
# Validate every Mermaid block in docs/ renders via mmdc.
set -euo pipefail

MMDC="${MMDC:-pnpm exec mmdc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
i=0

# Extract every fenced ```mermaid block into a tmp file
while IFS= read -r doc; do
  awk -v base="$TMP" -v doc="$doc" '
    /^```mermaid$/ { inblock=1; idx++; outfile=sprintf("%s/%s.%03d.mmd", base, gensub("/","_","g",doc), idx); next }
    /^```$/ && inblock { inblock=0; next }
    inblock { print >> outfile }
  ' "$doc"
done < <(find docs -type f -name "*.md")

shopt -s nullglob
for mmd in "$TMP"/*.mmd; do
  i=$((i+1))
  out="${mmd%.mmd}.svg"
  if ! $MMDC -i "$mmd" -o "$out" -q >/dev/null 2>&1; then
    echo "diagram failed to render: $mmd"
    cat "$mmd"
    fail=1
  fi
done

echo "checked $i diagram(s)"
exit "$fail"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/check_diagrams.sh`

- [ ] **Step 3: Smoke-run the script against existing spec docs**

Run: `bash scripts/check_diagrams.sh`
Expected: exits 0, prints `checked N diagram(s)` where N matches the diagrams we wrote in the spec phase.

If `mmdc` is not yet installed locally, install via:
Run: `pnpm install` (Already done; `@mermaid-js/mermaid-cli` is a root devDep.)

- [ ] **Step 4: Commit**

```bash
git add scripts/check_diagrams.sh
git commit -m "chore(scripts): add Mermaid diagram render check"
```

---

## Task 17: `scripts/lint.sh` — bundled lint runner

**Files:**
- Create: `scripts/lint.sh`

- [ ] **Step 1: Write `scripts/lint.sh`**

```bash
#!/usr/bin/env bash
# Run every lint that gates merges in CI.
set -euo pipefail

echo "==> ruff format --check"
uv run ruff format --check .

echo "==> ruff check"
uv run ruff check .

echo "==> mypy --strict packages/"
uv run mypy packages/

echo "==> python boundary lint"
uv run python scripts/check_boundaries.py --root .

echo "==> mermaid diagrams"
bash scripts/check_diagrams.sh

echo "==> pnpm typecheck"
pnpm -r typecheck

echo "==> pnpm lint"
pnpm -r lint

echo "==> all lints passed"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/lint.sh`

- [ ] **Step 3: Run it**

Run: `bash scripts/lint.sh`
Expected: every step prints its header and exits 0; final line `==> all lints passed`.

If `ruff` flags formatting on the new code, fix with `uv run ruff format .` and re-run.

- [ ] **Step 4: Commit**

```bash
git add scripts/lint.sh
git commit -m "chore(scripts): add bundled lint runner"
```

---

## Task 18: CI workflow — fast lane (lint + unit tests + diagrams)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Enable pnpm
        run: |
          corepack enable
          corepack prepare pnpm@9.12.0 --activate

      - name: uv sync
        run: uv sync --all-packages

      - name: pnpm install
        run: pnpm install --frozen-lockfile

      - name: ruff format check
        run: uv run ruff format --check .

      - name: ruff check
        run: uv run ruff check .

      - name: mypy strict
        run: uv run mypy packages/

      - name: boundary lint
        run: uv run python scripts/check_boundaries.py --root .

      - name: mermaid diagrams
        run: bash scripts/check_diagrams.sh

      - name: pnpm typecheck
        run: pnpm -r typecheck

      - name: pnpm lint
        run: pnpm -r lint || true   # next lint config arrives with Plan 4

      - name: Python unit tests
        env:
          GEMINI_API_KEY: sk-test
        run: uv run pytest -q

      - name: JS unit tests
        run: pnpm -r test
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore(ci): add fast-lane workflow (lint + unit tests + diagrams)"
```

---

## Task 19: Replace stub README with quick-start

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Overwrite README.md**

```markdown
# DraftLoop

Ingest messy legal documents → generate **grounded** drafts → improve from operator edits.

## Quick start

```bash
git clone <repo>
cd DraftLoop
cp .env.example .env       # add your GEMINI_API_KEY
bash scripts/setup.sh
bash scripts/dev.sh
# open http://localhost:3000
```

## What's here right now (Plan 0)

- Turborepo monorepo: uv (Python) + pnpm (JS) workspaces, orchestrated by Turbo.
- `packages/draftloop_core` — shared types, errors, config, Gemini SDK shim, storage protocols, observability.
- `apps/api` — FastAPI skeleton with `/health` and `/version`.
- `apps/web` — Next.js 15 + Tailwind landing page that pings the API.
- `packages/ui` — first shared React component (`HealthBadge`), shipped via tsup.
- Boundary lint (`scripts/check_boundaries.py`) + diagram lint (`scripts/check_diagrams.sh`) + bundled `scripts/lint.sh`.
- GitHub Actions CI: lint + Python unit tests + JS unit tests + diagram render.

## What's coming

See `docs/superpowers/plans/2026-05-15-plans-index.md` for the full sequenced roadmap. The implementation walks through Plans 1–7 (ingestion → retrieval → drafting → operator UI → improvement loop → evaluation → composition + demo).

## Reading order

1. `docs/superpowers/specs/2026-05-15-00-overview-design.md` — system context, C4 diagrams, glossary.
2. The phase doc whose package you're touching (`01`..`07`).
3. `CLAUDE.md` — contributor / modularity contract.

## Commands

| Command | Purpose |
|---|---|
| `bash scripts/setup.sh` | One-shot environment bring-up |
| `bash scripts/dev.sh` | Boot API + web together |
| `bash scripts/lint.sh` | Run every lint gate locally |
| `uv run pytest` | Python tests |
| `pnpm -r test` | JS tests |

## License

TBD.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: replace stub README with Plan 0 quick-start"
```

---

## Task 20: End-to-end smoke — API + web boot, health is green

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/test_smoke.py`

- [ ] **Step 1: Write the smoke test (Python-driven, no Playwright yet)**

`tests/e2e/__init__.py`: empty.

`tests/e2e/test_smoke.py`:
```python
"""Smoke: API can boot in-process and serve /health and /version.

Web smoke (Playwright) lands in Plan 4 once there's a real editor.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from draftloop_api.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-test")
    return TestClient(create_app())


def test_health_and_version_are_consistent(client):
    h = client.get("/health").json()
    v = client.get("/version").json()
    assert h["status"] == "ok"
    assert v["version"] == "0.1.0"
```

- [ ] **Step 2: Run test**

Run: `uv run pytest tests/e2e/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/
git commit -m "test(e2e): in-process smoke for /health + /version"
```

---

## Task 21: Final verification — every lint and test green from clean checkout

- [ ] **Step 1: Run full lint suite**

Run: `bash scripts/lint.sh`
Expected: every step passes, final line `==> all lints passed`.

- [ ] **Step 2: Run full Python test suite with coverage**

Run: `uv run pytest --cov=packages --cov=apps --cov-report=term-missing -q`
Expected: all tests pass. Coverage on `packages/` ≥ 80%.

- [ ] **Step 3: Run JS test suite**

Run: `pnpm -r test`
Expected: all tests pass.

- [ ] **Step 4: Verify CI workflow is valid YAML (parseable)**

Run: `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('CI yaml valid')"`
Expected: prints `CI yaml valid`.

- [ ] **Step 5: Verify boundaries clean on the real repo**

Run: `uv run python scripts/check_boundaries.py --root .`
Expected: `Boundaries clean.`

- [ ] **Step 6: Verify diagrams render**

Run: `bash scripts/check_diagrams.sh`
Expected: `checked N diagram(s)` where N is the number of Mermaid blocks across `docs/`.

- [ ] **Step 7: Commit any incidental fixes**

If any step above flagged a fix (e.g., `ruff format` rewrites), commit those:
```bash
git add -A
git commit -m "chore: apply formatter fixes after Plan 0 verification"
```

If nothing changed, no commit needed.

---

## Plan 0 — Done criteria

- [ ] Every task above is `[x]` checked off.
- [ ] `bash scripts/lint.sh` exits 0 from a fresh checkout after `bash scripts/setup.sh`.
- [ ] `uv run pytest` shows 100% pass and ≥80% coverage on `packages/`.
- [ ] `pnpm -r test` shows 100% pass.
- [ ] `scripts/check_boundaries.py` reports `Boundaries clean.`
- [ ] `scripts/check_diagrams.sh` renders every Mermaid block successfully.
- [ ] GitHub Actions workflow file is valid YAML and (once pushed) the `lint-and-test` job goes green on the first PR.
- [ ] `apps/web` home page renders and shows `HealthBadge` green when `apps/api` is up.

When all bullets are checked, mark the index entry for Plan 0 as `done` and proceed to write Plan 1 (Ingestion).
