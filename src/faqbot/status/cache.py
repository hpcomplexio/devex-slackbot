"""In-memory cache for status updates with TTL-based expiration."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np


@dataclass
class StatusUpdate:
    """A status/incident announcement from a monitored channel."""

    message_ts: str
    channel_id: str
    message_text: str
    message_link: str
    posted_at: datetime
    keywords_matched: List[str]
    embedding: Optional[np.ndarray] = None  # Lazy-loaded on first semantic search


# Incident-related keywords for filtering messages
INCIDENT_KEYWORDS = [
    "broken",
    "down",
    "outage",
    "incident",
    "failing",
    "failure",
    "degraded",
    "maintenance",
    "unavailable",
    "error",
    "issue",
    "investigating",
    "identified",
    "monitoring",
    "resolved",
    "main branch",
    "github",
    "deploy",
    "build",
    "ci/cd",
]


class StatusUpdateCache:
    """In-memory cache of recent status updates from announcement channels.

    Features:
    - Time-based expiration (TTL)
    - Keyword-based filtering
    - Semantic search with lazy embedding generation
    - Automatic cleanup of expired updates
    """

    def __init__(self, ttl_hours: int = 24):
        """Initialize the status update cache.

        Args:
            ttl_hours: How many hours to keep status updates before expiring them
        """
        self.updates: List[StatusUpdate] = []
        self.ttl = timedelta(hours=ttl_hours)

    def add_update(self, update: StatusUpdate) -> None:
        """Add a status update to the cache.

        Args:
            update: The status update to cache
        """
        self.updates.append(update)
        self._cleanup_expired()

    def get_recent_updates(
        self, keywords: Optional[List[str]] = None
    ) -> List[StatusUpdate]:
        """Get recent status updates, optionally filtered by keywords.

        Args:
            keywords: Optional list of keywords to filter by. Returns updates that
                     match ANY of these keywords.

        Returns:
            List of status updates (all updates if no keywords, filtered otherwise)
        """
        self._cleanup_expired()

        if not keywords:
            return self.updates

        # Filter by keyword overlap (case-insensitive)
        keywords_lower = [kw.lower() for kw in keywords]
        return [
            u
            for u in self.updates
            if any(kw in keywords_lower for kw in [k.lower() for k in u.keywords_matched])
        ]

    def search_semantic(
        self,
        query_embedding: np.ndarray,
        embedding_model,
        top_k: int = 3,
        min_similarity: float = 0.50,
    ) -> List[tuple[StatusUpdate, float]]:
        """Search status updates using semantic similarity.

        Args:
            query_embedding: The query embedding vector (already computed)
            embedding_model: The embedding model to use for lazy loading status embeddings
            top_k: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            List of (StatusUpdate, similarity_score) tuples, sorted by similarity descending
        """
        self._cleanup_expired()

        if not self.updates:
            return []

        # Lazy-load embeddings for status messages
        for update in self.updates:
            if update.embedding is None:
                update.embedding = embedding_model.embed(update.message_text)

        # Calculate similarities (cosine similarity via dot product on normalized vectors)
        results = []
        for update in self.updates:
            # Embedding should be loaded by now, but check for type safety
            if update.embedding is None:
                continue

            similarity = float(np.dot(query_embedding, update.embedding))
            if similarity >= min_similarity:
                results.append((update, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _cleanup_expired(self) -> None:
        """Remove status updates older than TTL."""
        cutoff = datetime.now() - self.ttl
        self.updates = [u for u in self.updates if u.posted_at >= cutoff]

    def clear(self) -> None:
        """Clear all status updates from cache. Useful for testing."""
        self.updates = []

    def size(self) -> int:
        """Get the number of status updates in the cache.

        Returns:
            Number of cached status updates
        """
        self._cleanup_expired()
        return len(self.updates)
