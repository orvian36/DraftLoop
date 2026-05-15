from draftloop_core.storage.rank_bm25_lexical_index import (
    LexicalDoc,
    LexicalHit,
    RankBm25LexicalIndex,
)


def test_add_and_search(tmp_path):
    idx = RankBm25LexicalIndex(persist_path=str(tmp_path))
    idx.add(
        "M-1",
        [
            LexicalDoc(id="a", text="Plaintiff alleges breach of the SaaS agreement."),
            LexicalDoc(id="b", text="Defendant denies all allegations."),
            LexicalDoc(id="c", text="The motion to dismiss is denied."),
        ],
    )
    hits = idx.search("M-1", "saas agreement breach", top_k=2)
    assert isinstance(hits[0], LexicalHit)
    ids = [h.id for h in hits]
    assert "a" in ids


def test_search_unknown_collection_returns_empty(tmp_path):
    idx = RankBm25LexicalIndex(persist_path=str(tmp_path))
    assert idx.search("M-unknown", "anything", top_k=5) == []


def test_persists_across_instances(tmp_path):
    idx1 = RankBm25LexicalIndex(persist_path=str(tmp_path))
    idx1.add("M-1", [LexicalDoc(id="x", text="hello world")])
    idx2 = RankBm25LexicalIndex(persist_path=str(tmp_path))
    hits = idx2.search("M-1", "hello", top_k=1)
    assert hits and hits[0].id == "x"
