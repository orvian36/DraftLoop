from unittest.mock import AsyncMock, MagicMock

import pytest

from draftloop_ingest.types import IngestResult
from draftloop_retrieval.indexer import Indexer
from draftloop_retrieval.splitter import StructuralSplitter


@pytest.fixture
def fake_client():
    c = MagicMock()
    # Return one vector per input text, regardless of batch size.
    c.embed.side_effect = lambda *, model, contents, task_type, output_dimensionality: [
        [0.1] * output_dimensionality for _ in contents
    ]
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
