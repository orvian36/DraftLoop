"""Tiered verifier: substring -> HHEM (if available) -> Flash judge."""

from __future__ import annotations

import re
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

        if score is None:
            # HHEM unavailable — escalate to Flash judge directly.
            verdict = self._judge(fact.text, chunk_text)
            if verdict == "unsupported":
                return self._rewrite(
                    fact, reason="judge_unsupported",
                    hhem_score=None, llm_judge="unsupported", substring_passed=True,
                )
            return FactVerification(
                sentence_id=fact.sentence_id, substring_passed=True,
                hhem_score=None, llm_judge="supported", final_verdict="pass",
                original_text=None, fail_reason=None,
            )
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
        text = (resp.text or "").upper()
        # "UNSUPPORTED" contains "SUPPORTED" as substring, so order matters.
        if "UNSUPPORTED" in text:
            return "unsupported"
        if "SUPPORTED" in text:
            return "supported"
        return "unsupported"

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
