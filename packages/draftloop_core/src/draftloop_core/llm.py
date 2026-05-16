"""Single point of contact for Google Gemini.

All Gemini calls in DraftLoop go through this module (CLAUDE.md §4).
Boundary lint blocks ``from google import genai`` elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google import genai  # boundary: allow draftloop_core.llm is the only legal entrypoint
from google.genai import types as genai_types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
            raise ValueError(f"embed batch size {len(contents)} exceeds cap {EMBED_BATCH_CAP}")

        try:
            if hasattr(genai_types, "EmbedContentConfig"):
                config: Any = genai_types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=output_dimensionality,
                )
            else:
                config = {
                    "task_type": task_type,
                    "output_dimensionality": output_dimensionality,
                }
            resp = self._client.models.embed_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise LLMError(
                f"embed_content failed: {exc}",
                code="LLM_EMBED_FAILED",
            ) from exc

        return [list(e.values) for e in resp.embeddings]
