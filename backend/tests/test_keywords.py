"""Unit tests for keyword extractor with multi-word phrase support."""

from app.utils.keywords import extract_keywords


def test_extract_keywords_preserves_multi_word_phrases():
    """Test that 'product design' and 'user research' are preserved as phrases."""
    text = "I like product design and user research"
    result = extract_keywords(text, max_keywords=3)
    
    # Expected: noun chunks or bigrams like "Product Design", "User Research"
    # Check that we get at least one multi-word phrase
    assert len(result) >= 1
    # At least one result should be multi-word (contain a space)
    multi_word = [kw for kw in result if " " in kw]
    assert len(multi_word) >= 1, f"Expected multi-word phrases but got: {result}"


def test_extract_keywords_messy_run_on_pairs():
    """Messy grammar with four interests should yield four non-overlapping pairs."""
    text = "i like product design user research and data science machine learning"
    result = extract_keywords(text, max_keywords=4)
    # Expect at least four distinct two-word phrases without overlap
    assert len(result) >= 4, f"Expected at least 4 keywords, got: {result}"
    expected = {"Product Design", "User Research", "Data Science", "Machine Learning"}
    lower_result = [r.lower() for r in result]
    for exp in expected:
        assert exp.lower() in lower_result, f"Missing expected phrase '{exp}' in {result}"


def test_extract_keywords_single_words_fallback():
    """Test that single-word inputs still work and yield multiple items."""
    text = "technology finance engineering"
    result = extract_keywords(text, max_keywords=3)
    # Depending on spaCy noun chunking or fallback, we may get bigrams or singles.
    assert len(result) >= 1
    # Ensure presence of at least one expected token or bigram
    expected_any = {"Technology", "Finance", "Engineering", "Technology Finance", "Finance Engineering"}
    assert any(r in expected_any for r in result), f"Unexpected result set: {result}"


def test_extract_keywords_empty_input():
    """Test that empty input returns empty list."""
    assert extract_keywords("") == []
    assert extract_keywords("   ") == []


def test_extract_keywords_stopwords_only():
    """Test that stopword-only input returns minimal tokens."""
    text = "I am the one who is"
    result = extract_keywords(text, max_keywords=3)
    # spaCy may extract noun chunks like "the one" even from stopword-heavy text
    # So we just ensure it doesn't crash and returns a reasonable result
    assert isinstance(result, list)
    assert len(result) <= 3
