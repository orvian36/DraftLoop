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
        chunk_id="x",
        doc_id="doc_3",
        matter_id="M-1",
        page=4,
        section_label="Claims",
        para_id="¶12",
        char_start=0,
        char_end=len(text),
        text=text,
        context_prefix="",
        embedding_text=text,
        embedding_dim=1536,
        confidence_min=1.0,
        contains_needs_review=False,
        ingest_version="v1",
    )


def test_prefixer_adds_blurb(fake_client):
    p = ContextualPrefixer(client=fake_client, model="gemini-2.5-flash")
    chunks = [_mk_chunk("Plaintiff alleges breach.")]
    out = p.prefix(chunks)
    assert out[0].context_prefix != ""
    assert "Section II" in out[0].context_prefix or "Complaint" in out[0].context_prefix
    assert out[0].embedding_text.startswith(out[0].context_prefix)
