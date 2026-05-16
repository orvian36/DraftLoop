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
        for hits in hits_by_slot.values():
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
            f"- rule: {e.get('induced_rule', '')}\n"
            f"  before: {e.get('before_text', '')}\n"
            f"  after: {e.get('after_text', '')}"
            for e in ex
        )
