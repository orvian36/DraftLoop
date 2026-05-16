from draftloop_retrieval.splitter import StructuralSplitter


SAMPLE_MARKDOWN = """<!-- page=1 -->
# COMPLAINT

## Parties

Plaintiff Acme Corp brings this action against Defendant Widgets Inc.

## Claims

Count I — Breach of Contract. Defendant breached the SaaS agreement on 2024-03-14.

Count II — Unjust Enrichment.

<!-- page=2 -->
## Relief Sought

Plaintiff seeks damages and injunctive relief.
"""


def test_splitter_respects_section_boundaries():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    chunks = list(
        splitter.split(
            markdown=SAMPLE_MARKDOWN,
            doc_id="doc_1",
            matter_id="M-001",
            ingest_version="v1",
        )
    )
    for c in chunks:
        if c.section_label:
            assert c.section_label in {"COMPLAINT", "Parties", "Claims", "Relief Sought"}


def test_splitter_emits_char_offsets_that_reproduce_text():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    chunks = list(
        splitter.split(markdown=SAMPLE_MARKDOWN, doc_id="d", matter_id="M", ingest_version="v")
    )
    for c in chunks:
        assert SAMPLE_MARKDOWN[c.char_start : c.char_end].strip() == c.text.strip()


def test_splitter_carries_page_from_marker():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    chunks = list(
        splitter.split(markdown=SAMPLE_MARKDOWN, doc_id="d", matter_id="M", ingest_version="v")
    )
    pages_seen = {c.page for c in chunks}
    assert pages_seen.issubset({1, 2})


def test_chunk_id_is_deterministic():
    splitter = StructuralSplitter(chunk_size_tokens=80, overlap_tokens=10)
    runs = [
        list(
            splitter.split(markdown=SAMPLE_MARKDOWN, doc_id="d", matter_id="M", ingest_version="v")
        )
        for _ in range(2)
    ]
    assert [c.chunk_id for c in runs[0]] == [c.chunk_id for c in runs[1]]
