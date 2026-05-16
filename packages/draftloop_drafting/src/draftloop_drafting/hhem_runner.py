"""HHEM-2.1-Open NLI faithfulness scorer.

Optional. Loads ``vectara/hallucination_evaluation_model`` lazily on first call;
if ``transformers`` / ``torch`` aren't installed, ``HhemRunner.available`` is
False and ``score()`` returns ``None`` so callers can fall through to other
verification tiers.
"""

from __future__ import annotations

import threading

_LOCK = threading.Lock()


class HhemRunner:
    _model = None
    _tokenizer = None

    @property
    def available(self) -> bool:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except Exception:
            return False
        return True

    def _load(self) -> bool:
        with _LOCK:
            if HhemRunner._model is not None:
                return True
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                HhemRunner._tokenizer = AutoTokenizer.from_pretrained(
                    "vectara/hallucination_evaluation_model", trust_remote_code=True
                )
                HhemRunner._model = AutoModelForSequenceClassification.from_pretrained(
                    "vectara/hallucination_evaluation_model", trust_remote_code=True
                )
                HhemRunner._model.eval()
                return True
            except Exception:
                return False

    def score(self, *, premise: str, hypothesis: str) -> float | None:
        if not self.available:
            return None
        if not self._load():
            return None
        try:
            import torch

            assert HhemRunner._model is not None
            with torch.no_grad():
                scores = HhemRunner._model.predict([(premise, hypothesis)])
            return float(scores[0])
        except Exception:
            return None
