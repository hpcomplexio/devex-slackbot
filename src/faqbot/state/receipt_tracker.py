"""Read receipt tracking for mentioned users."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ReceiptRecord:
    """Record of a message requiring acknowledgment."""

    message_ts: str
    channel_id: str
    thread_ts: str
    question: str
    answer_preview: str  # first 200 chars
    mentioned_user_ids: List[str]
    acknowledged_user_ids: List[str] = field(default_factory=list)
    posted_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 604800)  # 7 days


class ReceiptTracker:
    """Track read receipts for messages with mentions."""

    def __init__(self, ttl_hours: int = 168):
        """Initialize receipt tracker.

        Args:
            ttl_hours: Time-to-live in hours (default: 168 = 7 days)
        """
        self.records: Dict[str, ReceiptRecord] = {}  # message_ts -> record
        self.ttl_seconds = ttl_hours * 3600

    def track_message(
        self,
        message_ts: str,
        channel_id: str,
        thread_ts: str,
        question: str,
        answer_preview: str,
        mentioned_user_ids: List[str],
    ) -> None:
        """Add new message to track for acknowledgments.

        Args:
            message_ts: Message timestamp (unique ID)
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            question: Original question text
            answer_preview: Preview of answer (first 200 chars)
            mentioned_user_ids: List of Slack user IDs mentioned
        """
        self._cleanup_expired()

        now = time.time()
        record = ReceiptRecord(
            message_ts=message_ts,
            channel_id=channel_id,
            thread_ts=thread_ts,
            question=question,
            answer_preview=answer_preview,
            mentioned_user_ids=mentioned_user_ids,
            acknowledged_user_ids=[],
            posted_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self.records[message_ts] = record

    def mark_acknowledged(self, message_ts: str, user_id: str) -> bool:
        """Mark user as having acknowledged a message.

        Args:
            message_ts: Message timestamp to update
            user_id: User ID who acknowledged

        Returns:
            True if successfully marked, False if user not mentioned or already acked
        """
        self._cleanup_expired()

        record = self.records.get(message_ts)
        if not record:
            return False

        # Check if user was mentioned
        if user_id not in record.mentioned_user_ids:
            return False

        # Check if already acknowledged
        if user_id in record.acknowledged_user_ids:
            return False

        record.acknowledged_user_ids.append(user_id)
        return True

    def get_pending_receipts(self, user_id: Optional[str] = None) -> List[ReceiptRecord]:
        """Get records with pending acknowledgments.

        Args:
            user_id: If provided, filter to records where this user hasn't acked yet

        Returns:
            List of ReceiptRecords with pending acknowledgments
        """
        self._cleanup_expired()

        pending = []
        for record in self.records.values():
            # Check if all users have acknowledged
            if set(record.acknowledged_user_ids) == set(record.mentioned_user_ids):
                continue  # All acked, skip

            # If filtering by user, check if user is in mentioned but not acked
            if user_id:
                if user_id in record.mentioned_user_ids and user_id not in record.acknowledged_user_ids:
                    pending.append(record)
            else:
                # No filter, include any record with pending acks
                pending.append(record)

        # Sort by posted_at descending (newest first)
        pending.sort(key=lambda r: r.posted_at, reverse=True)
        return pending

    def get_record(self, message_ts: str) -> Optional[ReceiptRecord]:
        """Get specific record by message timestamp.

        Args:
            message_ts: Message timestamp

        Returns:
            ReceiptRecord if found, None otherwise
        """
        self._cleanup_expired()
        return self.records.get(message_ts)

    def _cleanup_expired(self) -> None:
        """Remove expired records."""
        now = time.time()
        expired = [ts for ts, record in self.records.items() if record.expires_at < now]
        for ts in expired:
            del self.records[ts]

    def size(self) -> int:
        """Get number of tracked records.

        Returns:
            Number of active records
        """
        self._cleanup_expired()
        return len(self.records)
