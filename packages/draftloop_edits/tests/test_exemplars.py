from unittest.mock import AsyncMock, MagicMock

import pytest

from draftloop_core.storage import VectorHit
from draftloop_edits.exemplars import ExemplarRetriever
from draftloop_edits.types import EditClass


@pytest.fixture
def retriever():
    vec = AsyncMock()
    vec.search.return_value = [
        VectorHit(
            id="rule_a",
            score=0.9,
            metadata={
                "rule_id": "rule_a", "event_id": "e1",
                "edit_classes": "fact_correction", "operator_id": "op1",
                "slot": "claims", "trust_weight": 1.0, "pinned": False,
                "created_at": "2026-05-01T00:00:00",
            },
            document="ISO dates",
        ),
        VectorHit(
            id="rule_b",
            score=0.85,
            metadata={
                "rule_id": "rule_b", "event_id": "e2",
                "edit_classes": "tone", "operator_id": "op2",
                "slot": "claims", "trust_weight": 0.8, "pinned": False,
                "created_at": "2026-05-01T00:00:00",
            },
            document="tone",
        ),
    ]
    embedder = MagicMock()
    embedder.embed_queries.return_value = [[0.1] * 1536]
    embedder.embed_documents.return_value = [[0.2] * 1536]
    return ExemplarRetriever(
        vec_index=vec, embedder=embedder,
        max_fact=5, max_style=3, token_budget=2000,
    )


async def test_fact_pass_filters_fact_correction_only(retriever):
    bundle = await retriever.recall(
        slot="claims", source_evidence_texts=["chunk text"], rule_intent="rules about claims",
    )
    for ex in bundle.fact_exemplars:
        assert any(c in (EditClass.FACT_CORRECTION, EditClass.CITATION_FIX) for c in ex.edit_class)


async def test_style_pass_filters_tone_or_structure(retriever):
    bundle = await retriever.recall(
        slot="claims", source_evidence_texts=["chunk text"], rule_intent="rules about claims",
    )
    for ex in bundle.style_exemplars:
        assert any(c in (EditClass.TONE, EditClass.STRUCTURE) for c in ex.edit_class)


async def test_empty_source_returns_empty_bundle(retriever):
    bundle = await retriever.recall(
        slot="claims", source_evidence_texts=[], rule_intent="rules",
    )
    assert bundle.fact_exemplars == []
    assert bundle.style_exemplars == []
    assert bundle.total_tokens == 0
