"""Unit tests for reaction-based search handlers."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import numpy as np

from src.faqbot.search.suggestions import FAQSuggestion, FAQSuggestionService
from src.faqbot.slack.reactions import build_suggestion_blocks
from src.faqbot.status.cache import StatusUpdate


# Mock classes for testing
@dataclass
class MockChunk:
    """Mock FAQ chunk."""

    block_id: str
    heading: str
    content: str
    notion_url: str


@dataclass
class MockSearchResult:
    """Mock search result."""

    chunk: MockChunk
    similarity: float


class MockEmbeddingModel:
    """Mock embedding model."""

    def embed(self, text: str) -> np.ndarray:
        """Return deterministic embedding."""
        vec = np.array([len(text), len(text.split()), hash(text) % 100], dtype=float)
        return vec / np.linalg.norm(vec)


class MockVectorStore:
    """Mock vector store."""

    def __init__(self, results: List[MockSearchResult]):
        self.results = results
        self.chunks = [r.chunk for r in results]

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[MockSearchResult]:
        """Return mock results."""
        return self.results[:top_k]


class TestBuildSuggestionBlocks:
    """Test suggestion block building."""

    def test_build_blocks_faq_only(self):
        """Test building blocks with only FAQ suggestions."""
        suggestions = [
            FAQSuggestion(
                block_id="chunk1",
                heading="How to deploy",
                content_preview="Deploy using kubectl apply...",
                similarity=0.85,
                url="https://notion.so/deploy",
            ),
            FAQSuggestion(
                block_id="chunk2",
                heading="Authentication",
                content_preview="Set up your API keys...",
                similarity=0.70,
                url="https://notion.so/auth",
            ),
        ]

        blocks = build_suggestion_blocks(
            suggestions=suggestions,
            status_results=[],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Verify structure
        assert len(blocks) > 0
        assert blocks[0]["type"] == "section"
        assert "FAQ" in blocks[0]["text"]["text"]

        # Count buttons (should be 2)
        button_count = sum(
            1
            for block in blocks
            if block.get("type") == "section"
            and "accessory" in block
            and block["accessory"].get("type") == "button"
        )
        assert button_count == 2

    def test_build_blocks_status_only(self):
        """Test building blocks with only status updates."""
        status_update = StatusUpdate(
            message_ts="123",
            channel_id="C_STATUS",
            message_text="INCIDENT: Deploy is broken",
            message_link="https://slack.com/link",
            posted_at=datetime.now(),
            keywords_matched=["deploy", "broken", "incident"],
            embedding=None,
        )

        blocks = build_suggestion_blocks(
            suggestions=[],
            status_results=[(status_update, 0.95)],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Verify structure
        assert len(blocks) > 0
        assert blocks[0]["type"] == "section"
        assert "Status" in blocks[0]["text"]["text"]

        # Verify status content appears
        block_text = json.dumps(blocks)
        assert "Deploy is broken" in block_text

    def test_build_blocks_both_faq_and_status(self):
        """Test building blocks with both FAQs and status."""
        suggestions = [
            FAQSuggestion(
                block_id="chunk1",
                heading="Deploy guide",
                content_preview="Guide content",
                similarity=0.80,
                url="https://notion.so/deploy",
            )
        ]

        status_update = StatusUpdate(
            message_ts="123",
            channel_id="C_STATUS",
            message_text="INCIDENT: Build failing",
            message_link="https://slack.com/link",
            posted_at=datetime.now(),
            keywords_matched=["build", "failing"],
            embedding=None,
        )

        blocks = build_suggestion_blocks(
            suggestions=suggestions,
            status_results=[(status_update, 0.90)],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Verify both sections present
        block_text = json.dumps(blocks)
        assert "FAQ" in block_text
        assert "Status" in block_text
        assert "Deploy guide" in block_text
        assert "Build failing" in block_text

    def test_block_structure_valid(self):
        """Test that blocks have valid Slack Block Kit structure."""
        suggestions = [
            FAQSuggestion(
                block_id="test",
                heading="Test",
                content_preview="Content",
                similarity=0.75,
                url="https://notion.so/test",
            )
        ]

        blocks = build_suggestion_blocks(
            suggestions=suggestions,
            status_results=[],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Check all blocks have required fields
        for block in blocks:
            assert "type" in block
            assert block["type"] in ["section", "divider", "context"]

            if block["type"] == "section":
                assert "text" in block
                assert block["text"]["type"] in ["mrkdwn", "plain_text"]

    def test_button_payloads_valid_json(self):
        """Test that button action values are valid JSON."""
        suggestions = [
            FAQSuggestion(
                block_id="chunk1",
                heading="Test",
                content_preview="Content",
                similarity=0.80,
                url="https://notion.so/test",
            )
        ]

        blocks = build_suggestion_blocks(
            suggestions=suggestions,
            status_results=[],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Find button blocks
        for block in blocks:
            if (
                block.get("type") == "section"
                and "accessory" in block
                and block["accessory"].get("type") == "button"
            ):
                # Verify value is valid JSON
                value = block["accessory"]["value"]
                payload = json.loads(value)

                assert "block_id" in payload
                assert "thread_ts" in payload
                assert "channel_id" in payload
                assert payload["thread_ts"] == "123.456"
                assert payload["channel_id"] == "C123"

    def test_status_message_truncation(self):
        """Test that long status messages are truncated."""
        long_message = "INCIDENT: " + "A" * 200  # Make it long
        status_update = StatusUpdate(
            message_ts="123",
            channel_id="C_STATUS",
            message_text=long_message,
            message_link="https://slack.com/link",
            posted_at=datetime.now(),
            keywords_matched=["incident"],
            embedding=None,
        )

        blocks = build_suggestion_blocks(
            suggestions=[],
            status_results=[(status_update, 0.90)],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Find status block
        block_text = json.dumps(blocks)

        # Should contain ellipsis (truncation indicator)
        assert "..." in block_text

        # Original message should not be in full
        assert long_message not in block_text

    def test_multiple_status_updates_limited_to_2(self):
        """Test that only top 2 status updates are shown."""
        status_updates = [
            (
                StatusUpdate(
                    f"msg{i}",
                    "C_STATUS",
                    f"INCIDENT {i}",
                    f"link{i}",
                    datetime.now(),
                    ["incident"],
                ),
                0.9 - i * 0.1,
            )
            for i in range(5)
        ]

        blocks = build_suggestion_blocks(
            suggestions=[],
            status_results=status_updates,
            thread_ts="123.456",
            channel_id="C123",
        )

        # Count how many incident messages appear
        block_text = json.dumps(blocks)
        incident_count = sum(
            1 for i in range(5) if f"INCIDENT {i}" in block_text
        )

        # Should only show top 2
        assert incident_count == 2
        assert "INCIDENT 0" in block_text
        assert "INCIDENT 1" in block_text


class TestReactionHandlerLogic:
    """Test reaction handler logic (without actual Slack integration)."""

    def test_suggestion_service_integration(self):
        """Test that suggestion service returns expected results."""
        chunks = [
            MockChunk(
                "chunk1",
                "How to deploy",
                "Deploy using kubectl apply...",
                "https://notion.so/deploy",
            )
        ]

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore([MockSearchResult(chunks[0], 0.85)])
        service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.50)

        suggestions = service.search("how do I deploy?", top_k=5)

        assert len(suggestions) == 1
        assert suggestions[0].heading == "How to deploy"
        assert suggestions[0].similarity == 0.85

    def test_search_emoji_constant(self):
        """Test that search emoji constant is correct."""
        from src.faqbot.slack.reactions import SEARCH_EMOJI

        assert SEARCH_EMOJI == "mag"  # 🔍 magnifying glass

    def test_empty_suggestions_and_status(self):
        """Test handling when no results are found."""
        blocks = build_suggestion_blocks(
            suggestions=[],
            status_results=[],
            thread_ts="123.456",
            channel_id="C123",
        )

        # Should still have basic structure (header, footer)
        assert len(blocks) > 0
        # But no buttons
        button_count = sum(
            1
            for block in blocks
            if block.get("type") == "section"
            and "accessory" in block
            and block["accessory"].get("type") == "button"
        )
        assert button_count == 0


class TestGetChunkById:
    """Test the get_chunk_by_id helper function."""

    def test_get_chunk_by_id_found(self):
        """Test finding a chunk by ID."""
        from src.faqbot.retrieval.store import get_chunk_by_id

        chunks = [
            MockChunk("chunk1", "Heading 1", "Content 1", "url1"),
            MockChunk("chunk2", "Heading 2", "Content 2", "url2"),
        ]

        vector_store = MockVectorStore([MockSearchResult(c, 0.8) for c in chunks])

        result = get_chunk_by_id(vector_store, "chunk2")

        assert result is not None
        assert result.block_id == "chunk2"
        assert result.heading == "Heading 2"

    def test_get_chunk_by_id_not_found(self):
        """Test when chunk ID doesn't exist."""
        from src.faqbot.retrieval.store import get_chunk_by_id

        chunks = [MockChunk("chunk1", "Heading 1", "Content 1", "url1")]

        vector_store = MockVectorStore([MockSearchResult(chunks[0], 0.8)])

        result = get_chunk_by_id(vector_store, "nonexistent")

        assert result is None
