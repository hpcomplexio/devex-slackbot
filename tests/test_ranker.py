"""Tests for confidence gating logic."""

import pytest
from src.faqbot.retrieval.ranker import check_confidence, filter_results
from src.faqbot.retrieval.store import SearchResult
from src.faqbot.notion.chunking import FAQChunk


def create_result(similarity: float) -> SearchResult:
    """Create a mock SearchResult."""
    chunk = FAQChunk(
        heading="Test",
        content="Test content",
        block_id="123",
        notion_url="https://notion.so/123",
    )
    return SearchResult(chunk=chunk, similarity=similarity)


def test_check_confidence_no_results():
    """Test confidence check with no results."""
    result = check_confidence([])
    assert result.should_answer is False
    assert "No results" in result.reason


def test_check_confidence_below_threshold():
    """Test confidence check with score below threshold."""
    results = [create_result(0.65)]
    result = check_confidence(results, min_similarity=0.70)
    assert result.should_answer is False
    assert "below threshold" in result.reason
    assert result.top_score == 0.65


def test_check_confidence_single_result_above_threshold():
    """Test confidence check with single result above threshold."""
    results = [create_result(0.85)]
    result = check_confidence(results, min_similarity=0.70)
    assert result.should_answer is True
    assert "Single result" in result.reason
    assert result.top_score == 0.85


def test_check_confidence_insufficient_gap():
    """Test confidence check with insufficient gap between results."""
    results = [create_result(0.75), create_result(0.70)]
    result = check_confidence(results, min_similarity=0.70, min_gap=0.15)
    assert result.should_answer is False
    assert "Gap" in result.reason
    assert result.gap == 0.05


def test_check_confidence_sufficient_gap():
    """Test confidence check with sufficient gap between results."""
    results = [create_result(0.85), create_result(0.65)]
    result = check_confidence(results, min_similarity=0.70, min_gap=0.15)
    assert result.should_answer is True
    assert "thresholds met" in result.reason
    assert result.top_score == 0.85
    assert result.second_score == 0.65
    assert result.gap == 0.20


def test_filter_results():
    """Test filtering results by similarity."""
    results = [
        create_result(0.85),
        create_result(0.70),
        create_result(0.65),
        create_result(0.50),
    ]

    filtered = filter_results(results, min_similarity=0.70)
    assert len(filtered) == 2
    assert filtered[0].similarity == 0.85
    assert filtered[1].similarity == 0.70
