"""Interaction logging with SQLite persistence."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class InteractionRecord:
    """Record of a single bot interaction."""

    id: Optional[int]
    timestamp: float
    interaction_type: str  # "auto_answer", "slash_command", "reaction_search"
    user_id: str
    channel_id: str
    thread_ts: str
    question_text: str
    answered: bool
    confidence_score: Optional[float]
    confidence_ratio: Optional[float]
    answer_text: Optional[str]
    block_ids: List[str]  # FAQ chunks used
    status_updates_shown: int
    # User engagement
    user_clicked_button: bool
    user_reactions: List[str]  # emojis used on bot's answer


class InteractionLog:
    """SQLite-based interaction logger."""

    def __init__(self, db_path: str):
        """Initialize interaction log.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create database table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    interaction_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    thread_ts TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    answered INTEGER NOT NULL,
                    confidence_score REAL,
                    confidence_ratio REAL,
                    answer_text TEXT,
                    block_ids TEXT,
                    status_updates_shown INTEGER DEFAULT 0,
                    user_clicked_button INTEGER DEFAULT 0,
                    user_reactions TEXT DEFAULT '[]'
                )
            """)
            # Create index for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON interactions(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_interaction_type
                ON interactions(interaction_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread_ts
                ON interactions(thread_ts)
            """)
            conn.commit()

    def log_interaction(self, record: InteractionRecord) -> None:
        """Insert interaction record into database.

        Args:
            record: InteractionRecord to log
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO interactions (
                    timestamp, interaction_type, user_id, channel_id, thread_ts,
                    question_text, answered, confidence_score, confidence_ratio,
                    answer_text, block_ids, status_updates_shown,
                    user_clicked_button, user_reactions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp,
                record.interaction_type,
                record.user_id,
                record.channel_id,
                record.thread_ts,
                record.question_text,
                1 if record.answered else 0,
                record.confidence_score,
                record.confidence_ratio,
                record.answer_text,
                json.dumps(record.block_ids),
                record.status_updates_shown,
                1 if record.user_clicked_button else 0,
                json.dumps(record.user_reactions),
            ))
            conn.commit()

    def get_interactions(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        interaction_type: Optional[str] = None,
        answered_only: bool = False,
    ) -> List[InteractionRecord]:
        """Query interactions with filters.

        Args:
            start_time: Start timestamp (inclusive), None for no limit
            end_time: End timestamp (inclusive), None for no limit
            interaction_type: Filter by type, None for all
            answered_only: If True, only return answered interactions

        Returns:
            List of InteractionRecords matching filters
        """
        query = "SELECT * FROM interactions WHERE 1=1"
        params: List[Any] = []

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        if interaction_type is not None:
            query += " AND interaction_type = ?"
            params.append(interaction_type)

        if answered_only:
            query += " AND answered = 1"

        query += " ORDER BY timestamp DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        records = []
        for row in rows:
            records.append(InteractionRecord(
                id=row["id"],
                timestamp=row["timestamp"],
                interaction_type=row["interaction_type"],
                user_id=row["user_id"],
                channel_id=row["channel_id"],
                thread_ts=row["thread_ts"],
                question_text=row["question_text"],
                answered=bool(row["answered"]),
                confidence_score=row["confidence_score"],
                confidence_ratio=row["confidence_ratio"],
                answer_text=row["answer_text"],
                block_ids=json.loads(row["block_ids"]),
                status_updates_shown=row["status_updates_shown"],
                user_clicked_button=bool(row["user_clicked_button"]),
                user_reactions=json.loads(row["user_reactions"]),
            ))

        return records

    def update_engagement(
        self,
        thread_ts: str,
        clicked: bool = False,
        reaction: Optional[str] = None,
    ) -> None:
        """Update engagement data for an existing interaction.

        Args:
            thread_ts: Thread timestamp to identify interaction
            clicked: If True, mark that user clicked button
            reaction: Emoji reaction to add to list
        """
        with sqlite3.connect(self.db_path) as conn:
            if clicked:
                conn.execute("""
                    UPDATE interactions
                    SET user_clicked_button = 1
                    WHERE thread_ts = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (thread_ts,))

            if reaction:
                # Get current reactions
                cursor = conn.execute("""
                    SELECT user_reactions FROM interactions
                    WHERE thread_ts = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (thread_ts,))
                row = cursor.fetchone()
                if row:
                    reactions = json.loads(row[0])
                    if reaction not in reactions:
                        reactions.append(reaction)
                        conn.execute("""
                            UPDATE interactions
                            SET user_reactions = ?
                            WHERE thread_ts = ?
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """, (json.dumps(reactions), thread_ts))

            conn.commit()
