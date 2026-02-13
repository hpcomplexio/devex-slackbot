"""Tests for confidence gating logic."""

import pytest
from src.faqbot.retrieval.ranker import check_confidence, check_confidence_ratio, filter_results
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
    assert result.gap is not None and abs(result.gap - 0.05) < 0.001


def test_check_confidence_sufficient_gap():
    """Test confidence check with sufficient gap between results."""
    results = [create_result(0.85), create_result(0.65)]
    result = check_confidence(results, min_similarity=0.70, min_gap=0.15)
    assert result.should_answer is True
    assert "thresholds met" in result.reason
    assert result.top_score == 0.85
    assert result.second_score == 0.65
    assert result.gap is not None and abs(result.gap - 0.20) < 0.001


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


# Tests for ratio-based confidence (new)


def test_check_confidence_ratio_no_results():
    """Test ratio-based confidence check with no results."""
    result = check_confidence_ratio([])
    assert result.should_answer is False
    assert "No results" in result.reason


def test_check_confidence_ratio_below_threshold():
    """Test ratio-based confidence check with score below threshold."""
    results = [create_result(0.65)]
    result = check_confidence_ratio(results, min_similarity=0.70)
    assert result.should_answer is False
    assert "below threshold" in result.reason
    assert result.top_score == 0.65


def test_check_confidence_ratio_single_result_above_threshold():
    """Test ratio-based confidence check with single result above threshold."""
    results = [create_result(0.85)]
    result = check_confidence_ratio(results, min_similarity=0.70)
    assert result.should_answer is True
    assert "Single result" in result.reason
    assert result.top_score == 0.85


def test_check_confidence_ratio_insufficient_ratio():
    """Test ratio-based confidence check with insufficient ratio.

    This simulates the hybrid search RRF case where scores cluster tightly.
    """
    # Score 1.0 / 0.984 = 1.016, which is below min_ratio=1.05
    results = [create_result(1.0), create_result(0.984)]
    result = check_confidence_ratio(results, min_similarity=0.70, min_ratio=1.05)
    assert result.should_answer is False
    assert "Ratio" in result.reason
    assert result.ratio is not None
    assert abs(result.ratio - 1.016) < 0.001


def test_check_confidence_ratio_sufficient_ratio_hybrid():
    """Test ratio-based confidence with sufficient ratio for hybrid search.

    Uses lower min_ratio=1.02 appropriate for RRF scoring.
    """
    # Score 1.0 / 0.97 = 1.031, which is above min_ratio=1.02
    results = [create_result(1.0), create_result(0.97)]
    result = check_confidence_ratio(results, min_similarity=0.70, min_ratio=1.02)
    assert result.should_answer is True
    assert "thresholds met" in result.reason
    assert result.ratio is not None
    assert result.ratio > 1.02


def test_check_confidence_ratio_sufficient_ratio_semantic():
    """Test ratio-based confidence with sufficient ratio for semantic search.

    Uses higher min_ratio=1.10 appropriate for semantic scoring.
    """
    # Score 0.85 / 0.70 = 1.214, which is above min_ratio=1.10
    results = [create_result(0.85), create_result(0.70)]
    result = check_confidence_ratio(results, min_similarity=0.70, min_ratio=1.10)
    assert result.should_answer is True
    assert "thresholds met" in result.reason
    assert result.ratio is not None
    assert result.ratio > 1.10


def test_check_confidence_ratio_second_score_zero():
    """Test ratio-based confidence when second score is zero (edge case)."""
    results = [create_result(0.85), create_result(0.0)]
    result = check_confidence_ratio(results, min_similarity=0.70, min_ratio=1.10)
    assert result.should_answer is True
    # Ratio should be infinity when second score is zero
    assert result.ratio == float("inf")
