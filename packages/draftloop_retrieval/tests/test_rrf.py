from draftloop_retrieval.rrf import rrf_fuse


def test_rrf_known_rankings():
    dense = [("a", 0.9), ("b", 0.8), ("c", 0.5)]
    sparse = [("c", 5.0), ("b", 4.0), ("d", 1.0)]
    fused = rrf_fuse([dense, sparse], k=60, top_k=4)
    ids = [x.id for x in fused]
    assert "b" in ids[:2]
    assert "c" in ids[:2]


def test_rrf_returns_top_k_only():
    dense = [(str(i), 1.0 / (i + 1)) for i in range(50)]
    fused = rrf_fuse([dense], k=60, top_k=10)
    assert len(fused) == 10


def test_rrf_handles_empty_rankings():
    fused = rrf_fuse([[], []], k=60, top_k=5)
    assert fused == []


def test_rrf_engine_attribution():
    dense = [("a", 0.9)]
    sparse = [("a", 5.0)]
    fused = rrf_fuse(
        [dense, sparse],
        k=60,
        top_k=1,
        engine_names=["dense", "bm25"],
    )
    assert set(fused[0].engines) == {"dense", "bm25"}
