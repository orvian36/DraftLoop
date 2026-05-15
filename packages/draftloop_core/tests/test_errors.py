import pytest

from draftloop_core.errors import (
    DraftLoopError,
    IngestError,
    RetrievalError,
    DraftingError,
    EditLoopError,
    EvalError,
    ConfigError,
    LLMError,
    StorageError,
)


def test_root_error_carries_code_and_message():
    err = DraftLoopError(code="GENERIC", message="boom")
    assert err.code == "GENERIC"
    assert err.message == "boom"
    assert str(err) == "[GENERIC] boom"


def test_subclasses_set_default_code_prefix():
    cases = [
        (IngestError("oh no"), "INGEST"),
        (RetrievalError("oh no"), "RETRIEVAL"),
        (DraftingError("oh no"), "DRAFTING"),
        (EditLoopError("oh no"), "EDITS"),
        (EvalError("oh no"), "EVAL"),
        (ConfigError("oh no"), "CONFIG"),
        (LLMError("oh no"), "LLM"),
        (StorageError("oh no"), "STORAGE"),
    ]
    for err, prefix in cases:
        assert err.code.startswith(prefix), f"{type(err).__name__} -> {err.code}"


def test_explicit_code_overrides_default():
    err = IngestError("encrypted", code="INGEST_PDF_ENCRYPTED")
    assert err.code == "INGEST_PDF_ENCRYPTED"


def test_error_is_raisable():
    with pytest.raises(IngestError) as excinfo:
        raise IngestError("encrypted", code="INGEST_PDF_ENCRYPTED")
    assert excinfo.value.code == "INGEST_PDF_ENCRYPTED"
