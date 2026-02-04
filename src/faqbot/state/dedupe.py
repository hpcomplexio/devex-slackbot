"""Thread deduplication tracking."""

import time
from typing import Dict, Set


class ThreadTracker:
    """Track answered threads to prevent duplicate responses."""

    def __init__(self, ttl_seconds: int = 86400):  # 24 hours default
        """Initialize tracker.

        Args:
            ttl_seconds: Time-to-live for thread records in seconds
        """
        self.ttl_seconds = ttl_seconds
        self.answered_threads: Dict[str, float] = {}  # thread_ts -> timestamp

    def is_answered(self, thread_ts: str) -> bool:
        """Check if thread has been answered.

        Args:
            thread_ts: Thread timestamp (parent message ts)

        Returns:
            True if thread has been answered
        """
        # Clean expired entries first
        self._cleanup_expired()

        return thread_ts in self.answered_threads

    def mark_answered(self, thread_ts: str) -> None:
        """Mark thread as answered.

        Args:
            thread_ts: Thread timestamp (parent message ts)
        """
        self.answered_threads[thread_ts] = time.time()

    def _cleanup_expired(self) -> None:
        """Remove expired thread records."""
        current_time = time.time()
        expired = [
            ts
            for ts, timestamp in self.answered_threads.items()
            if current_time - timestamp > self.ttl_seconds
        ]

        for ts in expired:
            del self.answered_threads[ts]

    def size(self) -> int:
        """Return number of tracked threads."""
        self._cleanup_expired()
        return len(self.answered_threads)
