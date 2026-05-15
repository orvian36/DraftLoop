# Plan 3: Drafting & Verification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`.

**Goal:** Implement `packages/draftloop_drafting` covering (a) the `CaseFactSummary` Pydantic schema with structural grounding (min_length=1 citations + UNSUPPORTED sentinel), (b) prompt assembly with cached system + exemplar slots, (c) the single-call generator against `gemini-2.5-pro`, (d) the tiered verifier (substring → HHEM → Flash judge), (e) audit-trail emission, (f) the `Drafter` orchestrator. After this plan, the API can request a draft for a matter and get back a verified, grounded `CaseFactSummary` + `audit_trail.json`.

**Architecture:** `Drafter.draft(DraftRequest) -> DraftResult`. Stateless; injects retrieval (from Plan 2) and optional exemplars/principles (Plan 5 adds those, this plan stubs them as empty lists). Verifier is its own module reusable for re-verification after edits. HHEM via `transformers` / `vectara/hallucination_evaluation_model`.

**Tech Stack:** Python 3.12, `pydantic>=2.8`, `transformers>=4.45`, `torch>=2.4` (CPU OK), `sentencepiece`, reuse `draftloop_core.llm.GeminiClient`, reuse `draftloop_retrieval.HybridRetriever`.

---

## File structure

```
packages/draftloop_drafting/
├─ pyproject.toml
├─ src/draftloop_drafting/
│  ├─ __init__.py
│  ├─ schema.py                    # CaseFactSummary, Fact, Citation
│  ├─ types.py                     # DraftRequest, DraftResult, VerificationReport
│  ├─ prompt_assembler.py          # Renders system + exemplars + tagged chunks
│  ├─ cache_manager.py             # Gemini context caching wrapper
│  ├─ generator.py                 # Single-call + two-call modes
│  ├─ verifier.py                  # Substring + HHEM + Flash-judge tiered verifier
│  ├─ hhem_runner.py               # HHEM-2.1-Open inference
│  ├─ audit_trail.py               # audit_trail.json writer
│  └─ orchestrator.py              # Drafter
└─ tests/
   ├─ test_schema.py
   ├─ test_prompt_assembler.py
   ├─ test_generator.py
   ├─ test_verifier.py
   ├─ test_hhem_runner.py
   ├─ test_audit_trail.py
   └─ test_orchestrator.py

packages/draftloop_drafting/prompts/
├─ system.md                       # System prompt template (cached)
└─ user.md                         # User prompt template

tests/integration/
└─ test_drafting_pipeline.py
```

---

## Task 1: Package scaffold

- [ ] **Step 1: `packages/draftloop_drafting/pyproject.toml`**

```toml
[project]
name = "draftloop-drafting"
version = "0.1.0"
description = "DraftLoop grounded drafting + verification"
requires-python = ">=3.12,<3.13"
dependencies = [
    "draftloop-core",
    "draftloop-retrieval",
    "transformers>=4.45.0",
    "torch>=2.4.0",
    "sentencepiece>=0.2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/draftloop_drafting"]
```

- [ ] **Step 2: Add `"packages/draftloop_drafting"` to root workspace members.**
- [ ] **Step 3: `__init__.py` with version + lazy submodules.**
- [ ] **Step 4: `uv sync --all-packages`; commit.**

```bash
git add packages/draftloop_drafting pyproject.toml uv.lock
git commit -m "feat(drafting): scaffold draftloop_drafting package"
```

---

## Task 2: `schema.py` — Pydantic CaseFactSummary

- [ ] **Step 1: Failing test**

```python
import pytest
from pydantic import ValidationError

from draftloop_drafting.schema import (
    UNSUPPORTED,
    CaseFactSummary,
    Citation,
    Fact,
)


def test_citation_quote_capped_at_240():
    Citation(chunk_id="c1", quote="x" * 240)
    with pytest.raises(ValidationError):
        Citation(chunk_id="c1", quote="x" * 241)


def test_fact_requires_at_least_one_citation_unless_unsupported():
    with pytest.raises(ValidationError):
        Fact(sentence_id="s_1", text="claim", citations=[], confidence="high")
    f = Fact(
        sentence_id="s_1", text="claim",
        citations=[Citation(chunk_id="c1", quote="evidence")],
        confidence="high",
    )
    assert f.citations[0].chunk_id == "c1"


def test_unsupported_sentinel_allows_empty_citations():
    f = Fact(sentence_id="s_1", text=UNSUPPORTED, citations=[], confidence="low")
    assert f.text == "UNSUPPORTED"


def test_case_fact_summary_holds_all_slots():
    f = Fact(sentence_id="s_1", text="x",
             citations=[Citation(chunk_id="c1", quote="y")], confidence="high")
    summary = CaseFactSummary(
        parties=[f], jurisdiction=[f], key_dates=[f], claims=[f],
        relief_sought=[f], procedural_posture=[f], key_evidence=[f],
    )
    assert len(summary.parties) == 1
```

- [ ] **Step 2: Implement `schema.py`**

```python
"""CaseFactSummary schema with structural grounding."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

UNSUPPORTED = "UNSUPPORTED"


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    quote: str = Field(..., max_length=240)


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)

    sentence_id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

    @model_validator(mode="after")
    def _enforce_grounding(self) -> Fact:
        if self.text == UNSUPPORTED:
            return self
        if len(self.citations) < 1:
            raise ValueError(
                f"Fact {self.sentence_id!r}: requires >=1 Citation or text=UNSUPPORTED"
            )
        return self


class CaseFactSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    parties: list[Fact]
    jurisdiction: list[Fact]
    key_dates: list[Fact]
    claims: list[Fact]
    relief_sought: list[Fact]
    procedural_posture: list[Fact]
    key_evidence: list[Fact]
```

- [ ] **Step 3: Tests pass (4 tests). Commit.**

```bash
git add packages/draftloop_drafting/src/draftloop_drafting/schema.py packages/draftloop_drafting/tests/test_schema.py
git commit -m "feat(drafting): add CaseFactSummary schema with structural grounding"
```

---

## Task 3: `types.py` — DraftRequest / DraftResult / VerificationReport

- [ ] **Step 1: Failing test**

```python
from draftloop_drafting.schema import Citation, Fact, CaseFactSummary
from draftloop_drafting.types import (
    DraftRequest,
    DraftResult,
    FactVerification,
    VerificationReport,
)
from draftloop_retrieval.types import Chunk, RetrievalHit


def test_draft_request_minimum_fields():
    req = DraftRequest(matter_id="M-1", draft_id="D-1", retrieval_hits={"claims": []})
    assert req.drafter_mode == "single_call"
    assert req.drafter_model == "gemini-2.5-pro"
    assert req.exemplars == {"fact": [], "style": []}
    assert req.principles == []


def test_verification_report_summary():
    fv = FactVerification(
        sentence_id="s_1", substring_passed=True, hhem_score=0.9,
        llm_judge="skipped", final_verdict="pass",
        original_text=None, fail_reason=None,
    )
    report = VerificationReport(
        matter_id="M-1", draft_id="D-1", fact_results=[fv],
        summary={"pass": 1}, duration_ms=10,
    )
    assert report.summary["pass"] == 1
```

- [ ] **Step 2: Implement `types.py`**

```python
"""Public types for the drafting orchestrator."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from draftloop_drafting.schema import CaseFactSummary
from draftloop_retrieval.types import RetrievalHit


class DraftRequest(BaseModel):
    matter_id: str
    draft_id: str
    retrieval_hits: dict[str, list[RetrievalHit]]
    exemplars: dict[str, list[dict[str, Any]]] = Field(default_factory=lambda: {"fact": [], "style": []})
    principles: list[str] = Field(default_factory=list)
    drafter_mode: Literal["single_call", "two_call"] = "single_call"
    drafter_model: str = "gemini-2.5-pro"
    extraction_model: str = "gemini-2.5-flash"


class FactVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    sentence_id: str
    substring_passed: bool
    hhem_score: float | None
    llm_judge: Literal["supported", "unsupported", "skipped"]
    final_verdict: Literal["pass", "rewrite_to_unsupported"]
    original_text: str | None
    fail_reason: str | None


class VerificationReport(BaseModel):
    matter_id: str
    draft_id: str
    fact_results: list[FactVerification]
    summary: dict[str, int]
    duration_ms: int


class DraftResult(BaseModel):
    matter_id: str
    draft_id: str
    summary: CaseFactSummary
    verification: VerificationReport
    audit_trail_path: str
    cost_usd: float
    duration_ms: int
    token_usage: dict[str, int]
```

- [ ] **Step 3: Tests pass. Commit.**

```bash
git commit -am "feat(drafting): add DraftRequest/DraftResult/VerificationReport types"
```

---

## Task 4: Prompt files + PromptAssembler

- [ ] **Step 1: Write `packages/draftloop_drafting/prompts/system.md`**

```markdown
You draft case-fact summaries for a litigation team. The summary must be
GROUNDED — every Fact.text MUST be supported by ≥1 Citation drawn from the
<context> block below. Citations MUST be VERBATIM substrings of the cited
chunk (Citation.quote ⊆ chunk.text after whitespace-normalize).

If evidence is missing, contradictory, or low-confidence for a slot, emit
EXACTLY: Fact(text="UNSUPPORTED", citations=[]). Do not infer, do not
paraphrase unsupported claims, do not merge facts from different chunks
unless you cite all sources.

If a chunk's contains_needs_review=true, treat it as low-confidence evidence
— corroborate with another chunk or emit UNSUPPORTED.

STYLE RULES (learned from operator edits):
{style_rules}

FACT EXEMPLARS — past edits showing preferred phrasing of facts:
{fact_exemplars}

STYLE EXEMPLARS — past edits showing preferred tone/structure:
{style_exemplars}

<context>
{tagged_chunks}
</context>
```

- [ ] **Step 2: Write `packages/draftloop_drafting/prompts/user.md`**

```markdown
Draft a Case Fact Summary for matter {matter_id}. Use ONLY the <context>
above. Return JSON matching the CaseFactSummary schema.
```

- [ ] **Step 3: Failing test for `prompt_assembler.py`**

```python
from draftloop_drafting.prompt_assembler import PromptAssembler
from draftloop_retrieval.types import Chunk, RetrievalHit


def _hit(cid: str, slot: str = "claims") -> RetrievalHit:
    chunk = Chunk(
        chunk_id=cid, doc_id="d", matter_id="M-1", page=1, section_label="Claims",
        para_id=None, char_start=0, char_end=10, text="alleged breach",
        context_prefix="", embedding_text="x", embedding_dim=1536,
        confidence_min=0.9, contains_needs_review=False, ingest_version="v1",
    )
    return RetrievalHit(
        chunk=chunk, slot=slot, rerank_score=8.0, fusion_score=0.5,
        matched_query="q", retrieval_engines=["dense"], rank=1,
    )


def test_assembler_renders_chunks_with_ids():
    asm = PromptAssembler()
    system, user = asm.render(
        matter_id="M-1",
        retrieval_hits={"claims": [_hit("c1")]},
        fact_exemplars=[],
        style_exemplars=[],
        principles=[],
    )
    assert '<chunk id="c1"' in system
    assert "alleged breach" in system
    assert "matter M-1" in user
```

- [ ] **Step 4: Implement `prompt_assembler.py`**

```python
"""Render the system + user prompts from templates + retrieval/exemplars."""

from __future__ import annotations

from pathlib import Path

from draftloop_retrieval.types import RetrievalHit

PROMPT_DIR = Path(__file__).parent / "prompts"


class PromptAssembler:
    def __init__(self) -> None:
        self._system_tpl = (PROMPT_DIR / "system.md").read_text(encoding="utf-8")
        self._user_tpl = (PROMPT_DIR / "user.md").read_text(encoding="utf-8")

    def render(
        self,
        *,
        matter_id: str,
        retrieval_hits: dict[str, list[RetrievalHit]],
        fact_exemplars: list[dict],
        style_exemplars: list[dict],
        principles: list[str],
    ) -> tuple[str, str]:
        tagged = self._render_chunks(retrieval_hits)
        system = self._system_tpl.format(
            style_rules="\n".join(f"- {p}" for p in principles) or "(none)",
            fact_exemplars=self._render_exemplars(fact_exemplars),
            style_exemplars=self._render_exemplars(style_exemplars),
            tagged_chunks=tagged,
        )
        user = self._user_tpl.format(matter_id=matter_id)
        return system, user

    @staticmethod
    def _render_chunks(hits_by_slot: dict[str, list[RetrievalHit]]) -> str:
        seen: set[str] = set()
        parts: list[str] = []
        for slot, hits in hits_by_slot.items():
            for h in hits:
                if h.chunk.chunk_id in seen:
                    continue
                seen.add(h.chunk.chunk_id)
                parts.append(
                    f'<chunk id="{h.chunk.chunk_id}" page="{h.chunk.page}" '
                    f'section="{h.chunk.section_label or ""}" '
                    f'confidence_min="{h.chunk.confidence_min:.2f}" '
                    f'needs_review="{str(h.chunk.contains_needs_review).lower()}">\n'
                    f"{h.chunk.text}\n</chunk>"
                )
        return "\n\n".join(parts) or "(no chunks)"

    @staticmethod
    def _render_exemplars(ex: list[dict]) -> str:
        if not ex:
            return "(none)"
        return "\n".join(
            f"- rule: {e.get('induced_rule', '')}\n  before: {e.get('before_text', '')}\n  after: {e.get('after_text', '')}"
            for e in ex
        )
```

- [ ] **Step 5: Test passes. Commit.**

```bash
git add packages/draftloop_drafting/src/draftloop_drafting/prompt_assembler.py packages/draftloop_drafting/prompts packages/draftloop_drafting/tests/test_prompt_assembler.py
git commit -m "feat(drafting): add PromptAssembler with system/user templates"
```

---

## Task 5: Generator (single-call + two-call modes)

- [ ] **Step 1: Failing test**

```python
import json
from unittest.mock import MagicMock

from draftloop_drafting.generator import Generator
from draftloop_drafting.schema import CaseFactSummary


def test_single_call_parses_json_into_schema():
    fake = MagicMock()
    summary = {
        "parties": [{"sentence_id": "s_1", "text": "Acme vs Widgets",
                     "citations": [{"chunk_id": "c1", "quote": "Acme"}],
                     "confidence": "high"}],
        "jurisdiction": [], "key_dates": [], "claims": [],
        "relief_sought": [], "procedural_posture": [], "key_evidence": [],
    }
    resp = MagicMock()
    resp.text = json.dumps(summary)
    resp.parsed = None
    resp.usage = MagicMock(input_tokens=1000, output_tokens=200, cached_tokens=0)
    fake.generate.return_value = resp

    g = Generator(client=fake, model="gemini-2.5-pro", mode="single_call")
    out, usage = g.generate(system_prompt="sys", user_prompt="usr")
    assert isinstance(out, CaseFactSummary)
    assert out.parties[0].text == "Acme vs Widgets"
    assert usage.input_tokens == 1000
```

- [ ] **Step 2: Implement `generator.py`**

```python
"""Single-call / two-call Gemini wrapper that returns a CaseFactSummary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from draftloop_core.errors import DraftingError
from draftloop_core.llm import GeminiClient, LLMUsage

from draftloop_drafting.schema import CaseFactSummary


@dataclass
class Generator:
    client: GeminiClient
    model: str
    mode: Literal["single_call", "two_call"] = "single_call"

    def generate(self, *, system_prompt: str, user_prompt: str) -> tuple[CaseFactSummary, LLMUsage]:
        if self.mode == "single_call":
            return self._single(system_prompt, user_prompt)
        return self._two_call(system_prompt, user_prompt)

    def _single(self, system: str, user: str) -> tuple[CaseFactSummary, LLMUsage]:
        resp = self.client.generate(
            model=self.model,
            contents=[
                {"role": "user", "parts": [{"text": system + "\n\n" + user}]},
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": CaseFactSummary.model_json_schema(),
            },
        )
        try:
            data = json.loads(resp.text)
        except Exception as exc:
            raise DraftingError(
                f"invalid JSON from drafter: {exc}",
                code="DRAFTING_INVALID_JSON",
            ) from exc
        try:
            summary = CaseFactSummary.model_validate(data)
        except Exception as exc:
            raise DraftingError(
                f"schema validation failed: {exc}",
                code="DRAFTING_SCHEMA_INVALID",
            ) from exc
        return summary, resp.usage

    def _two_call(self, system: str, user: str) -> tuple[CaseFactSummary, LLMUsage]:
        md = self.client.generate(
            model=self.model,
            contents=system + "\n\n" + user + "\n\nReturn Markdown with inline [chunk_id] tags.",
        )
        restructure_prompt = (
            "Convert the following Markdown into JSON matching the CaseFactSummary schema. "
            "Preserve [chunk_id] tags as Citation entries.\n\n" + (md.text or "")
        )
        resp = self.client.generate(
            model=self.model,
            contents=restructure_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": CaseFactSummary.model_json_schema(),
            },
        )
        data = json.loads(resp.text)
        summary = CaseFactSummary.model_validate(data)
        merged_usage = LLMUsage(
            input_tokens=md.usage.input_tokens + resp.usage.input_tokens,
            output_tokens=md.usage.output_tokens + resp.usage.output_tokens,
            cached_tokens=md.usage.cached_tokens + resp.usage.cached_tokens,
        )
        return summary, merged_usage
```

- [ ] **Step 3: Test passes. Commit.**

```bash
git commit -am "feat(drafting): add Generator (single-call + two-call) with schema validation"
```

---

## Task 6: HHEMRunner

- [ ] **Step 1: Failing test (skipped if transformers/HHEM not available)**

```python
import importlib.util
import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("transformers") is None,
    reason="transformers not installed",
)


def test_hhem_scores_entailment_higher_than_contradiction(tmp_path):
    from draftloop_drafting.hhem_runner import HhemRunner

    runner = HhemRunner()
    e_score = runner.score(premise="The sky is blue.", hypothesis="The sky is blue.")
    c_score = runner.score(premise="The sky is blue.", hypothesis="The sky is red.")
    assert e_score > c_score
    assert 0.0 <= e_score <= 1.0
    assert 0.0 <= c_score <= 1.0
```

- [ ] **Step 2: Implement `hhem_runner.py`**

```python
"""HHEM-2.1-Open NLI faithfulness scorer.

Loads vectara/hallucination_evaluation_model lazily (first .score() call).
"""

from __future__ import annotations

import threading


class HhemRunner:
    _lock = threading.Lock()
    _model = None
    _tokenizer = None

    def _load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            HhemRunner._tokenizer = AutoTokenizer.from_pretrained(
                "vectara/hallucination_evaluation_model", trust_remote_code=True
            )
            HhemRunner._model = AutoModelForSequenceClassification.from_pretrained(
                "vectara/hallucination_evaluation_model", trust_remote_code=True
            )
            HhemRunner._model.eval()

    def score(self, *, premise: str, hypothesis: str) -> float:
        import torch

        self._load()
        pairs = [(premise, hypothesis)]
        with torch.no_grad():
            scores = HhemRunner._model.predict(pairs)
        return float(scores[0])
```

- [ ] **Step 3: Test passes (if model downloadable) or skips. Commit.**

```bash
git commit -am "feat(drafting): add HHEMRunner (vectara/hallucination_evaluation_model)"
```

---

## Task 7: Tiered Verifier

- [ ] **Step 1: Failing test**

```python
from unittest.mock import MagicMock

from draftloop_drafting.schema import Citation, Fact
from draftloop_drafting.types import FactVerification
from draftloop_drafting.verifier import Verifier


def test_verifier_passes_when_substring_and_hhem_high():
    fake_hhem = MagicMock()
    fake_hhem.score.return_value = 0.95
    fake_judge = MagicMock()  # never called in this path
    verifier = Verifier(hhem=fake_hhem, judge=fake_judge, judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Plaintiff alleges breach.",
        citations=[Citation(chunk_id="c1", quote="Plaintiff alleges breach")],
        confidence="high",
    )
    chunks = {"c1": "On 2024-03-14, Plaintiff alleges breach of the SaaS agreement."}
    fv = verifier.verify_fact(fact, chunks)
    assert fv.final_verdict == "pass"
    fake_judge.generate.assert_not_called()


def test_verifier_rewrites_when_substring_misses():
    fake_hhem = MagicMock()
    fake_hhem.score.return_value = 0.9
    fake_judge = MagicMock()
    verifier = Verifier(hhem=fake_hhem, judge=fake_judge, judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Plaintiff was on Mars.",
        citations=[Citation(chunk_id="c1", quote="Plaintiff was on Mars")],
        confidence="high",
    )
    chunks = {"c1": "Plaintiff alleges breach."}
    fv = verifier.verify_fact(fact, chunks)
    assert fv.substring_passed is False
    assert fv.final_verdict == "rewrite_to_unsupported"


def test_verifier_escalates_uncertain_to_judge():
    fake_hhem = MagicMock()
    fake_hhem.score.return_value = 0.6  # uncertain band
    fake_judge = MagicMock()
    judge_resp = MagicMock()
    judge_resp.text = "SUPPORTED"
    fake_judge.generate.return_value = judge_resp
    verifier = Verifier(hhem=fake_hhem, judge=fake_judge, judge_model="gemini-2.5-flash")
    fact = Fact(
        sentence_id="s_1",
        text="Allegation",
        citations=[Citation(chunk_id="c1", quote="alleg")],
        confidence="high",
    )
    fv = verifier.verify_fact(fact, {"c1": "alleg"})
    assert fv.llm_judge == "supported"
    assert fv.final_verdict == "pass"
```

- [ ] **Step 2: Implement `verifier.py`**

```python
"""Tiered verifier: substring → HHEM → Flash judge."""

from __future__ import annotations

from dataclasses import dataclass

from draftloop_core.llm import GeminiClient

from draftloop_drafting.hhem_runner import HhemRunner
from draftloop_drafting.schema import UNSUPPORTED, Citation, Fact
from draftloop_drafting.types import FactVerification

HHEM_LO = 0.5
HHEM_HI = 0.7


@dataclass
class Verifier:
    hhem: HhemRunner
    judge: GeminiClient
    judge_model: str

    def verify_fact(self, fact: Fact, chunks_by_id: dict[str, str]) -> FactVerification:
        if fact.text == UNSUPPORTED:
            return FactVerification(
                sentence_id=fact.sentence_id, substring_passed=True,
                hhem_score=None, llm_judge="skipped", final_verdict="pass",
                original_text=None, fail_reason=None,
            )
        for cit in fact.citations:
            if not self._substring_ok(cit, chunks_by_id):
                return self._rewrite(fact, reason="substring_failed", substring_passed=False)

        chunk_text = " ".join(chunks_by_id.get(c.chunk_id, "") for c in fact.citations)
        score = self.hhem.score(premise=chunk_text, hypothesis=fact.text)
        if score < HHEM_LO:
            return self._rewrite(fact, reason="hhem_low", hhem_score=score, substring_passed=True)
        if score < HHEM_HI:
            verdict = self._judge(fact.text, chunk_text)
            if verdict == "unsupported":
                return self._rewrite(
                    fact, reason="judge_unsupported",
                    hhem_score=score, llm_judge="unsupported", substring_passed=True,
                )
            return FactVerification(
                sentence_id=fact.sentence_id, substring_passed=True,
                hhem_score=score, llm_judge="supported", final_verdict="pass",
                original_text=None, fail_reason=None,
            )
        return FactVerification(
            sentence_id=fact.sentence_id, substring_passed=True,
            hhem_score=score, llm_judge="skipped", final_verdict="pass",
            original_text=None, fail_reason=None,
        )

    @staticmethod
    def _substring_ok(cit: Citation, chunks_by_id: dict[str, str]) -> bool:
        chunk = chunks_by_id.get(cit.chunk_id, "")
        return _norm(cit.quote) in _norm(chunk)

    def _judge(self, claim: str, chunk_text: str) -> str:
        prompt = (
            "Is this claim entailed by the evidence? Answer only SUPPORTED or UNSUPPORTED.\n"
            f"Claim: {claim}\nEvidence: {chunk_text}\n"
        )
        resp = self.judge.generate(model=self.judge_model, contents=prompt)
        return "supported" if "SUPPORTED" in (resp.text or "").upper() and "UN" not in (resp.text or "").upper() else "unsupported"

    @staticmethod
    def _rewrite(
        fact: Fact, *, reason: str,
        substring_passed: bool = True,
        hhem_score: float | None = None,
        llm_judge: str = "skipped",
    ) -> FactVerification:
        return FactVerification(
            sentence_id=fact.sentence_id,
            substring_passed=substring_passed,
            hhem_score=hhem_score,
            llm_judge=llm_judge,  # type: ignore[arg-type]
            final_verdict="rewrite_to_unsupported",
            original_text=fact.text,
            fail_reason=reason,
        )


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()
```

- [ ] **Step 3: Test passes. Commit.**

```bash
git commit -am "feat(drafting): add tiered Verifier (substring + HHEM + Flash judge)"
```

---

## Task 8: AuditTrail writer

- [ ] **Step 1: Failing test**

```python
import json
from draftloop_drafting.audit_trail import AuditTrailWriter


def test_writes_audit_json(tmp_path):
    writer = AuditTrailWriter(root=str(tmp_path))
    path = writer.write(
        matter_id="M-1",
        draft_id="D-1",
        model="gemini-2.5-pro",
        drafter_mode="single_call",
        prompt_hash="abc",
        cache_name=None,
        retrieved_chunks=[{"chunk_id": "c1", "slot": "claims", "rerank_score": 8.0, "engines": ["dense"]}],
        exemplars_used=[],
        style_rules_active=[],
        verification={"summary": {"pass": 5}},
        token_usage={"input": 1000, "output": 200, "cached": 0},
        cost_usd=0.05,
        duration_ms=4000,
        ingest_versions={"doc_1": "v1"},
    )
    data = json.loads(open(path).read())
    assert data["matter_id"] == "M-1"
    assert data["model"] == "gemini-2.5-pro"
```

- [ ] **Step 2: Implement `audit_trail.py`**

```python
"""Persist audit_trail.json next to each draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditTrailWriter:
    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        *,
        matter_id: str,
        draft_id: str,
        model: str,
        drafter_mode: str,
        prompt_hash: str,
        cache_name: str | None,
        retrieved_chunks: list[dict],
        exemplars_used: list[dict],
        style_rules_active: list[str],
        verification: dict[str, Any],
        token_usage: dict[str, int],
        cost_usd: float,
        duration_ms: int,
        ingest_versions: dict[str, str],
    ) -> str:
        payload = {
            "matter_id": matter_id,
            "draft_id": draft_id,
            "model": model,
            "drafter_mode": drafter_mode,
            "prompt_hash": prompt_hash,
            "cache_name": cache_name,
            "retrieved_chunks": retrieved_chunks,
            "exemplars_used": exemplars_used,
            "style_rules_active": style_rules_active,
            "verification": verification,
            "token_usage": token_usage,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "ingest_versions": ingest_versions,
        }
        out_dir = self._root / matter_id / draft_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "audit_trail.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
```

- [ ] **Step 3: Test passes. Commit.**

```bash
git commit -am "feat(drafting): add AuditTrailWriter (audit_trail.json per draft)"
```

---

## Task 9: Drafter orchestrator

- [ ] **Step 1: Failing test (mocks everything)**

```python
import json
from unittest.mock import MagicMock

from draftloop_drafting.orchestrator import Drafter
from draftloop_drafting.schema import CaseFactSummary, Fact, Citation
from draftloop_drafting.types import DraftRequest


def test_drafter_end_to_end_with_mocks(tmp_path):
    summary = CaseFactSummary(
        parties=[Fact(sentence_id="s_1", text="X vs Y", citations=[Citation(chunk_id="c1", quote="X")], confidence="high")],
        jurisdiction=[], key_dates=[], claims=[],
        relief_sought=[], procedural_posture=[], key_evidence=[],
    )
    gen = MagicMock()
    gen.generate.return_value = (summary, MagicMock(input_tokens=100, output_tokens=20, cached_tokens=0))
    ver = MagicMock()
    ver.verify_fact.return_value = MagicMock(
        sentence_id="s_1", substring_passed=True, hhem_score=0.9,
        llm_judge="skipped", final_verdict="pass",
        original_text=None, fail_reason=None,
    )
    writer = MagicMock()
    writer.write.return_value = str(tmp_path / "audit.json")
    asm = MagicMock()
    asm.render.return_value = ("system", "user")

    drafter = Drafter(
        prompt_assembler=asm, generator=gen, verifier=ver, audit_writer=writer,
    )
    req = DraftRequest(matter_id="M-1", draft_id="D-1", retrieval_hits={"parties": []})
    out = drafter.draft(req)
    assert out.summary == summary
    assert out.verification.summary["pass"] >= 1
    assert out.audit_trail_path.endswith("audit.json")
```

- [ ] **Step 2: Implement `orchestrator.py`**

```python
"""Drafter — orchestrates assembly → generate → verify → audit."""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from dataclasses import dataclass

from draftloop_drafting.audit_trail import AuditTrailWriter
from draftloop_drafting.generator import Generator
from draftloop_drafting.prompt_assembler import PromptAssembler
from draftloop_drafting.schema import UNSUPPORTED, CaseFactSummary, Fact
from draftloop_drafting.types import (
    DraftRequest,
    DraftResult,
    FactVerification,
    VerificationReport,
)
from draftloop_drafting.verifier import Verifier


@dataclass
class Drafter:
    prompt_assembler: PromptAssembler
    generator: Generator
    verifier: Verifier
    audit_writer: AuditTrailWriter

    def draft(self, req: DraftRequest) -> DraftResult:
        start = time.monotonic()
        system, user = self.prompt_assembler.render(
            matter_id=req.matter_id,
            retrieval_hits=req.retrieval_hits,
            fact_exemplars=req.exemplars.get("fact", []),
            style_exemplars=req.exemplars.get("style", []),
            principles=req.principles,
        )
        prompt_hash = hashlib.sha256((system + user).encode()).hexdigest()

        summary, usage = self.generator.generate(system_prompt=system, user_prompt=user)

        chunks_by_id = {
            hit.chunk.chunk_id: hit.chunk.text
            for hits in req.retrieval_hits.values()
            for hit in hits
        }

        verified, fact_verifs = self._verify_all(summary, chunks_by_id)
        summary_counts = Counter(fv.final_verdict for fv in fact_verifs)

        verification_report = VerificationReport(
            matter_id=req.matter_id,
            draft_id=req.draft_id,
            fact_results=fact_verifs,
            summary={k: int(v) for k, v in summary_counts.items()},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

        retrieved_chunks_meta = [
            {
                "chunk_id": hit.chunk.chunk_id,
                "slot": slot,
                "rerank_score": hit.rerank_score,
                "engines": list(hit.retrieval_engines),
            }
            for slot, hits in req.retrieval_hits.items()
            for hit in hits
        ]
        audit_path = self.audit_writer.write(
            matter_id=req.matter_id,
            draft_id=req.draft_id,
            model=req.drafter_model,
            drafter_mode=req.drafter_mode,
            prompt_hash=prompt_hash,
            cache_name=None,
            retrieved_chunks=retrieved_chunks_meta,
            exemplars_used=req.exemplars.get("fact", []) + req.exemplars.get("style", []),
            style_rules_active=req.principles,
            verification={"summary": dict(summary_counts)},
            token_usage={
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "cached": usage.cached_tokens,
            },
            cost_usd=0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
            ingest_versions={},
        )

        return DraftResult(
            matter_id=req.matter_id,
            draft_id=req.draft_id,
            summary=verified,
            verification=verification_report,
            audit_trail_path=audit_path,
            cost_usd=0.0,
            duration_ms=int((time.monotonic() - start) * 1000),
            token_usage={
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "cached": usage.cached_tokens,
            },
        )

    def _verify_all(
        self, summary: CaseFactSummary, chunks_by_id: dict[str, str]
    ) -> tuple[CaseFactSummary, list[FactVerification]]:
        results: list[FactVerification] = []
        new_slots: dict[str, list[Fact]] = {}
        for slot_name, facts in summary.model_dump().items():
            new_facts: list[Fact] = []
            for fact_dict in facts:
                fact = Fact.model_validate(fact_dict)
                fv = self.verifier.verify_fact(fact, chunks_by_id)
                results.append(fv)
                if fv.final_verdict == "rewrite_to_unsupported":
                    new_facts.append(
                        Fact(
                            sentence_id=fact.sentence_id,
                            text=UNSUPPORTED,
                            citations=[],
                            confidence="low",
                        )
                    )
                else:
                    new_facts.append(fact)
            new_slots[slot_name] = new_facts
        verified = CaseFactSummary.model_validate(new_slots)
        return verified, results
```

- [ ] **Step 3: Test passes. Commit.**

```bash
git commit -am "feat(drafting): add Drafter orchestrator (assemble + generate + verify + audit)"
```

---

## Task 10: Integration test

```python
# tests/integration/test_drafting_pipeline.py
"""End-to-end drafting with mocked Gemini. Verifies orchestrator wiring + verifier
behavior against a planted-bad-citation case.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from draftloop_drafting import Drafter, DraftRequest
from draftloop_drafting.audit_trail import AuditTrailWriter
from draftloop_drafting.generator import Generator
from draftloop_drafting.prompt_assembler import PromptAssembler
from draftloop_drafting.schema import CaseFactSummary, Citation, Fact
from draftloop_drafting.verifier import Verifier
from draftloop_retrieval.types import Chunk, RetrievalHit


def _hit(cid: str, text: str) -> RetrievalHit:
    chunk = Chunk(
        chunk_id=cid, doc_id="d", matter_id="M-1", page=1, section_label="Claims",
        para_id=None, char_start=0, char_end=len(text), text=text,
        context_prefix="", embedding_text=text, embedding_dim=1536,
        confidence_min=1.0, contains_needs_review=False, ingest_version="v1",
    )
    return RetrievalHit(
        chunk=chunk, slot="claims", rerank_score=8.0, fusion_score=0.5,
        matched_query="q", retrieval_engines=["dense"], rank=1,
    )


def test_planted_bad_citation_rewrites_to_unsupported(tmp_path):
    bad = CaseFactSummary(
        parties=[], jurisdiction=[], key_dates=[], claims=[
            Fact(sentence_id="s_1", text="Defendant denies.",
                 citations=[Citation(chunk_id="c1", quote="Plaintiff was on Mars")],
                 confidence="high")
        ],
        relief_sought=[], procedural_posture=[], key_evidence=[],
    )
    gen = MagicMock()
    gen.generate.return_value = (bad, MagicMock(input_tokens=100, output_tokens=20, cached_tokens=0))
    fake_hhem = MagicMock()
    fake_hhem.score.return_value = 0.9
    fake_judge = MagicMock()
    fake_judge.generate.return_value = MagicMock(text="UNSUPPORTED")
    verifier = Verifier(hhem=fake_hhem, judge=fake_judge, judge_model="gemini-2.5-flash")
    drafter = Drafter(
        prompt_assembler=PromptAssembler(),
        generator=gen,
        verifier=verifier,
        audit_writer=AuditTrailWriter(root=str(tmp_path)),
    )
    req = DraftRequest(
        matter_id="M-1", draft_id="D-1",
        retrieval_hits={"claims": [_hit("c1", "Defendant denies.")]},
    )
    result = drafter.draft(req)
    only_claim = result.summary.claims[0]
    assert only_claim.text == "UNSUPPORTED"
```

- [ ] **Commit + merge**

```bash
git add tests/integration/test_drafting_pipeline.py
git commit -m "test(integration): planted bad citation rewrites to UNSUPPORTED"

bash scripts/lint.sh
uv run pytest -q
git checkout main
git merge --no-ff feat/plan-3-drafting -m "Merge Plan 3: Drafting & Verification"
```

---

## Done criteria

- [ ] All tests pass.
- [ ] HHEM-2.1-Open downloads on first run; pinned in container build (Plan 7).
- [ ] Audit trail JSON is emitted for every draft.
- [ ] `Fact` model rejects empty citations unless `text == "UNSUPPORTED"`.
- [ ] Plans index updated; next is Plan 4 (Operator UI).
