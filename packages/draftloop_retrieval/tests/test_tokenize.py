from draftloop_retrieval.tokenize import tokenize_for_bm25


def test_preserves_statute_citations_as_single_tokens():
    text = "Jurisdiction under 28 U.S.C. § 1331 is invoked."
    tokens = tokenize_for_bm25(text)
    assert "28 U.S.C. § 1331" in tokens


def test_lowercases_and_strips_punctuation_for_normal_words():
    tokens = tokenize_for_bm25("The Plaintiff filed.")
    assert "plaintiff" in tokens
    assert "filed" in tokens
    assert "the" in tokens


def test_preserves_versus_citations():
    text = "See Marbury v. Madison, 5 U.S. 137 (1803)."
    tokens = tokenize_for_bm25(text)
    assert "5 U.S. 137" in tokens
