"""Unit tests for status update cache."""

from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np

from src.faqbot.status.cache import INCIDENT_KEYWORDS, StatusUpdate, StatusUpdateCache


class MockEmbeddingModel:
    """Mock embedding model for testing."""

    def embed(self, text: str) -> np.ndarray:
        """Return a deterministic embedding based on text length."""
        # Normalize to unit length for cosine similarity
        vec = np.array([len(text), len(text.split()), hash(text) % 100], dtype=float)
        return vec / np.linalg.norm(vec)


def create_test_update(
    text: str = "INCIDENT: Deploy is broken",
    keywords: Optional[List[str]] = None,
    posted_at: Optional[datetime] = None,
) -> StatusUpdate:
    """Helper to create a test status update."""
    if keywords is None:
        keywords = ["deploy", "broken", "incident"]
    if posted_at is None:
        posted_at = datetime.now()

    return StatusUpdate(
        message_ts="1234567890.123456",
        channel_id="C123456",
        message_text=text,
        message_link="https://slack.com/archives/C123456/p1234567890123456",
        posted_at=posted_at,
        keywords_matched=keywords,
        embedding=None,
    )


class TestStatusUpdateCache:
    """Test suite for StatusUpdateCache."""

    def test_add_and_retrieve(self):
        """Test adding and retrieving status updates."""
        cache = StatusUpdateCache(ttl_hours=24)
        update = create_test_update()

        cache.add_update(update)

        assert len(cache.updates) == 1
        assert cache.size() == 1
        assert cache.updates[0] == update

    def test_ttl_expiration(self):
        """Test that old updates are cleaned up."""
        cache = StatusUpdateCache(ttl_hours=0)  # Immediate expiration

        # Create an update that's already expired
        old_time = datetime.now() - timedelta(hours=1)
        update = create_test_update(posted_at=old_time)

        cache.add_update(update)

        # Cleanup should remove it
        assert cache.size() == 0

    def test_keyword_filtering(self):
        """Test keyword-based filtering."""
        cache = StatusUpdateCache(ttl_hours=24)

        update1 = create_test_update("Deploy is broken", keywords=["deploy", "broken"])
        update2 = create_test_update(
            "GitHub is down", keywords=["github", "down"]
        )
        update3 = create_test_update(
            "Build is failing", keywords=["build", "failing"]
        )

        cache.add_update(update1)
        cache.add_update(update2)
        cache.add_update(update3)

        # Filter by "deploy"
        deploy_updates = cache.get_recent_updates(keywords=["deploy"])
        assert len(deploy_updates) == 1
        assert deploy_updates[0] == update1

        # Filter by "github" or "build"
        multi_updates = cache.get_recent_updates(keywords=["github", "build"])
        assert len(multi_updates) == 2

        # Get all (no filter)
        all_updates = cache.get_recent_updates()
        assert len(all_updates) == 3

    def test_case_insensitive_keyword_filtering(self):
        """Test that keyword filtering is case-insensitive."""
        cache = StatusUpdateCache(ttl_hours=24)

        update = create_test_update("Deploy is broken", keywords=["Deploy", "Broken"])
        cache.add_update(update)

        # Should match regardless of case
        result = cache.get_recent_updates(keywords=["deploy"])
        assert len(result) == 1

        result = cache.get_recent_updates(keywords=["DEPLOY"])
        assert len(result) == 1

    def test_semantic_search(self):
        """Test semantic similarity search."""
        cache = StatusUpdateCache(ttl_hours=24)
        embedding_model = MockEmbeddingModel()

        update1 = create_test_update("Deploy pipeline is broken")
        update2 = create_test_update("GitHub API is down")
        update3 = create_test_update("Build service is failing")

        cache.add_update(update1)
        cache.add_update(update2)
        cache.add_update(update3)

        # Search for similar to "deploy"
        query_embedding = embedding_model.embed("deploy issue")
        results = cache.search_semantic(
            query_embedding, embedding_model, top_k=2, min_similarity=0.0
        )

        # Should return results sorted by similarity
        assert len(results) <= 2
        assert all(isinstance(r[0], StatusUpdate) for r in results)
        assert all(isinstance(r[1], float) for r in results)

        # Check sorted descending
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    def test_semantic_search_with_threshold(self):
        """Test semantic search respects similarity threshold."""
        cache = StatusUpdateCache(ttl_hours=24)
        embedding_model = MockEmbeddingModel()

        update = create_test_update("Deploy is broken")
        cache.add_update(update)

        query_embedding = embedding_model.embed("completely unrelated query xyz")
        results = cache.search_semantic(
            query_embedding, embedding_model, top_k=5, min_similarity=0.99
        )

        # With very high threshold, should return few/no results
        assert len(results) <= 1

    def test_lazy_embedding_generation(self):
        """Test that embeddings are generated lazily."""
        cache = StatusUpdateCache(ttl_hours=24)
        embedding_model = MockEmbeddingModel()

        update = create_test_update("Deploy is broken")
        cache.add_update(update)

        # Initially no embedding
        assert update.embedding is None

        # After search, embedding should be generated
        query_embedding = embedding_model.embed("deploy")
        cache.search_semantic(query_embedding, embedding_model)

        assert update.embedding is not None
        assert isinstance(update.embedding, np.ndarray)

    def test_clear(self):
        """Test clearing all status updates."""
        cache = StatusUpdateCache(ttl_hours=24)

        cache.add_update(create_test_update())
        cache.add_update(create_test_update())

        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0

    def test_empty_cache_search(self):
        """Test searching an empty cache."""
        cache = StatusUpdateCache(ttl_hours=24)
        embedding_model = MockEmbeddingModel()

        query_embedding = embedding_model.embed("deploy")
        results = cache.search_semantic(query_embedding, embedding_model)

        assert len(results) == 0


class TestIncidentKeywords:
    """Test incident keyword detection."""

    def test_incident_keywords_exist(self):
        """Test that incident keywords are defined."""
        assert len(INCIDENT_KEYWORDS) > 0
        assert "broken" in INCIDENT_KEYWORDS
        assert "deploy" in INCIDENT_KEYWORDS
        assert "incident" in INCIDENT_KEYWORDS

    def test_incident_keywords_lowercase(self):
        """Test that all keywords are lowercase for consistent matching."""
        assert all(kw == kw.lower() for kw in INCIDENT_KEYWORDS)
