from unittest.mock import MagicMock

import pytest

from draftloop_core.llm import GeminiClient, LLMResponse, LLMUsage


@pytest.fixture
def fake_sdk(monkeypatch):
    """Patch the google.genai.Client so no network call is made."""
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.text = '{"ok": true}'
    fake_resp.parsed = None
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
