from unittest.mock import MagicMock

from draftloop_retrieval.reranker import FlashReranker


def test_flash_reranker_returns_top_k():
    fake = MagicMock()
    resp = MagicMock()
    resp.text = '[{"index":0,"score":7.0},{"index":2,"score":9.5},{"index":1,"score":3.0}]'
    fake.generate.return_value = resp
    rr = FlashReranker(client=fake, model="gemini-2.5-flash")
    candidates = ["doc a", "doc b", "doc c"]
    ranked = rr.rerank(query="anything", candidates=candidates, top_k=2)
    assert len(ranked) == 2
    assert ranked[0].index == 2
    assert ranked[0].score == 9.5


def test_flash_reranker_empty_input_returns_empty():
    fake = MagicMock()
    rr = FlashReranker(client=fake, model="gemini-2.5-flash")
    assert rr.rerank(query="q", candidates=[], top_k=5) == []
