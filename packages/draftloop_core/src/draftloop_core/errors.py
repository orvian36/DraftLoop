"""DraftLoop error hierarchy with stable, machine-readable codes.

Every error has a `code` (e.g., "INGEST_PDF_ENCRYPTED") and a `message`.
UI surfaces match by `code`, not by string.
"""

from __future__ import annotations


class DraftLoopError(Exception):
    """Root error for all DraftLoop domain failures."""

    default_code_prefix: str = "GENERIC"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code_prefix

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class IngestError(DraftLoopError):
    default_code_prefix = "INGEST"


class RetrievalError(DraftLoopError):
    default_code_prefix = "RETRIEVAL"


class DraftingError(DraftLoopError):
    default_code_prefix = "DRAFTING"


class EditLoopError(DraftLoopError):
    default_code_prefix = "EDITS"


class EvalError(DraftLoopError):
    default_code_prefix = "EVAL"


class ConfigError(DraftLoopError):
    default_code_prefix = "CONFIG"


class LLMError(DraftLoopError):
    default_code_prefix = "LLM"


class StorageError(DraftLoopError):
    default_code_prefix = "STORAGE"
