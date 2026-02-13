"""Confidence gating logic for retrieval results."""

from typing import List, Optional
from dataclasses import dataclass

from .store import SearchResult


@dataclass
class ConfidenceCheck:
    """Result of confidence gating."""

    should_answer: bool
    reason: str
    top_score: Optional[float] = None
    second_score: Optional[float] = None
    gap: Optional[float] = None
    ratio: Optional[float] = None


def check_confidence(
    results: List[SearchResult], min_similarity: float = 0.70, min_gap: float = 0.15
) -> ConfidenceCheck:
    """Check if results meet confidence thresholds.

    Must pass BOTH checks:
    1. Absolute threshold: top_similarity >= min_similarity
    2. Gap threshold: (top_score - second_score) >= min_gap

    Args:
        results: Search results sorted by similarity (highest first)
        min_similarity: Minimum similarity for top result
        min_gap: Minimum gap between top and second result

    Returns:
        ConfidenceCheck with decision and reasoning
    """
    if not results:
        return ConfidenceCheck(
            should_answer=False, reason="No results found", top_score=None
        )

    top_score = results[0].similarity

    # Check 1: Absolute threshold
    if top_score < min_similarity:
        return ConfidenceCheck(
            should_answer=False,
            reason=f"Top score {top_score:.3f} below threshold {min_similarity}",
            top_score=top_score,
        )

    # Check 2: Gap threshold (only if there are multiple results)
    if len(results) > 1:
        second_score = results[1].similarity
        gap = top_score - second_score

        if gap < min_gap:
            return ConfidenceCheck(
                should_answer=False,
                reason=f"Gap {gap:.3f} below threshold {min_gap} (uncertain match)",
                top_score=top_score,
                second_score=second_score,
                gap=gap,
            )

        # Both checks passed with multiple results
        return ConfidenceCheck(
            should_answer=True,
            reason="Both thresholds met",
            top_score=top_score,
            second_score=second_score,
            gap=gap,
        )

    # Only one result, and it passed absolute threshold
    return ConfidenceCheck(
        should_answer=True,
        reason="Single result above threshold",
        top_score=top_score,
    )


def check_confidence_ratio(
    results: List[SearchResult],
    min_similarity: float = 0.70,
    min_ratio: float = 1.05,
) -> ConfidenceCheck:
    """Check confidence using ratio-based metric.

    More robust than gap-based across different score distributions.
    The ratio metric (top_score / second_score) is scale-invariant.

    Must pass BOTH checks:
    1. Absolute threshold: top_similarity >= min_similarity
    2. Ratio threshold: (top_score / second_score) >= min_ratio

    Args:
        results: Search results sorted by similarity (highest first)
        min_similarity: Minimum similarity for top result
        min_ratio: Minimum ratio between top and second result

    Returns:
        ConfidenceCheck with decision and reasoning
    """
    if not results:
        return ConfidenceCheck(
            should_answer=False, reason="No results found", top_score=None
        )

    top_score = results[0].similarity

    # Check 1: Absolute threshold
    if top_score < min_similarity:
        return ConfidenceCheck(
            should_answer=False,
            reason=f"Top score {top_score:.3f} below threshold {min_similarity}",
            top_score=top_score,
        )

    # Check 2: Ratio threshold (only if there are multiple results)
    if len(results) > 1:
        second_score = results[1].similarity
        gap = top_score - second_score

        # Avoid division by zero
        if second_score > 0:
            ratio = top_score / second_score
        else:
            ratio = float("inf")

        if ratio < min_ratio:
            return ConfidenceCheck(
                should_answer=False,
                reason=f"Ratio {ratio:.3f} below threshold {min_ratio} (uncertain match)",
                top_score=top_score,
                second_score=second_score,
                gap=gap,
                ratio=ratio,
            )

        # Both checks passed with multiple results
        return ConfidenceCheck(
            should_answer=True,
            reason="Both thresholds met",
            top_score=top_score,
            second_score=second_score,
            gap=gap,
            ratio=ratio,
        )

    # Only one result, and it passed absolute threshold
    return ConfidenceCheck(
        should_answer=True,
        reason="Single result above threshold",
        top_score=top_score,
    )


def filter_results(
    results: List[SearchResult], min_similarity: float = 0.70
) -> List[SearchResult]:
    """Filter results to only include those above minimum similarity.

    Args:
        results: Search results
        min_similarity: Minimum similarity threshold

    Returns:
        Filtered results
    """
    return [r for r in results if r.similarity >= min_similarity]
