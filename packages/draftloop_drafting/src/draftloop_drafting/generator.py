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
            contents=system + "\n\n" + user,
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
