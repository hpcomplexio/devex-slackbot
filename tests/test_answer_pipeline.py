"""Unit tests for enhanced answer pipeline with status correlation."""

from datetime import datetime
from typing import List, Optional
from unittest.mock import Mock

import numpy as np

from src.faqbot.pipeline.answer import AnswerPipeline, AnswerResult
from src.faqbot.status.cache import StatusUpdate, StatusUpdateCache


# Mock classes
class MockEmbeddingModel:
    """Mock embedding model."""

    def embed(self, text: str) -> np.ndarray:
        """Return deterministic embedding."""
        vec = np.array([len(text), len(text.split()), hash(text) % 100], dtype=float)
        return vec / np.linalg.norm(vec)


class MockChunk:
    """Mock FAQ chunk."""

    def __init__(self, heading: str, content: str):
        self.heading = heading
        self.content = content
        self.block_id = f"block_{hash(heading) % 1000}"
        self.notion_url = f"https://notion.so/{self.block_id}"


class MockSearchResult:
    """Mock search result."""

    def __init__(self, chunk: MockChunk, similarity: float):
        self.chunk = chunk
        self.similarity = similarity


class MockVectorStore:
    """Mock vector store."""

    def __init__(self, results: List[MockSearchResult]):
        self.results = results

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[MockSearchResult]:
        """Return mock results."""
        return self.results[:top_k]


class MockClaudeClient:
    """Mock Claude API client."""

    def __init__(self, response: Optional[str] = "This is a test answer."):
        self.response = response

    def generate_answer(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Return mock answer."""
        return self.response


def create_test_status_update(
    text: str = "INCIDENT: Deploy is broken",
    posted_at: Optional[datetime] = None,
) -> StatusUpdate:
    """Helper to create test status update."""
    if posted_at is None:
        posted_at = datetime.now()

    return StatusUpdate(
        message_ts="123",
        channel_id="C123",
        message_text=text,
        message_link="https://slack.com/link/123",
        posted_at=posted_at,
        keywords_matched=["deploy", "broken", "incident"],
        embedding=None,
    )


class TestAnswerPipelineWithoutStatus:
    """Test answer pipeline without status cache (existing functionality)."""

    def test_successful_answer(self):
        """Test successful answer generation."""
        # Setup
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("How to deploy", "Deploy using kubectl")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Deploy using kubectl apply.")

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            min_similarity=0.70,
            min_gap=0.15,
        )

        # Execute
        result = pipeline.answer_question("How do I deploy?")

        # Verify
        assert result.answered is True
        assert result.answer == "Deploy using kubectl apply."
        assert result.confidence is not None
        assert result.confidence.should_answer is True
        assert result.status_updates is None or len(result.status_updates) == 0

    def test_low_confidence_skip(self):
        """Test that low confidence results in no answer."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Unrelated", "Content")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.50)])
        claude_client = MockClaudeClient()

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            min_similarity=0.70,
        )

        result = pipeline.answer_question("How do I deploy?")

        assert result.answered is False
        assert result.reason is not None
        assert "threshold" in result.reason.lower() or "score" in result.reason.lower()

    def test_no_results(self):
        """Test handling of no search results."""
        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore([])
        claude_client = MockClaudeClient()

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
        )

        result = pipeline.answer_question("How do I deploy?")

        assert result.answered is False
        assert "No relevant FAQ content found" in result.reason


class TestAnswerPipelineWithStatus:
    """Test answer pipeline WITH status cache (new functionality)."""

    def test_answer_with_status_correlation(self):
        """Test that status updates are included in answer."""
        # Setup FAQ search
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Deploy troubleshooting", "Check your configuration")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Check your configuration files.")

        # Setup status cache
        status_cache = StatusUpdateCache(ttl_hours=24)
        status_update = create_test_status_update(
            "INCIDENT: Main branch build is failing. Deploy blocked."
        )
        status_cache.add_update(status_update)

        # Create pipeline with status cache
        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=status_cache,
            min_similarity=0.70,
        )

        # Execute
        result = pipeline.answer_question("Why is deploy broken?")

        # Verify
        assert result.answered is True
        assert "Check your configuration files." in result.answer
        assert "Related Status Updates:" in result.answer
        assert "Main branch build is failing" in result.answer
        assert "View full message" in result.answer
        assert result.status_updates is not None
        assert len(result.status_updates) > 0

    def test_answer_without_status_match(self):
        """Test answer when no status updates match."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Authentication", "Set up your API keys")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Set up your API keys in .env")

        # Empty status cache
        status_cache = StatusUpdateCache(ttl_hours=24)

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=status_cache,
        )

        result = pipeline.answer_question("How do I authenticate?")

        # Should have FAQ answer but no status section
        assert result.answered is True
        assert "Set up your API keys" in result.answer
        assert "Related Status Updates:" not in result.answer
        assert result.status_updates is not None
        assert len(result.status_updates) == 0

    def test_status_only_low_faq_confidence(self):
        """Test that status is returned even when FAQ confidence is low."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Unrelated", "Content")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.40)])
        claude_client = MockClaudeClient()

        # Add relevant status update
        status_cache = StatusUpdateCache(ttl_hours=24)
        status_update = create_test_status_update("INCIDENT: Deploy failing")
        status_cache.add_update(status_update)

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=status_cache,
            min_similarity=0.70,
        )

        result = pipeline.answer_question("Why is deploy broken?")

        # FAQ confidence too low, but status should still be included
        assert result.answered is False  # FAQ confidence failed
        assert result.status_updates is not None
        assert len(result.status_updates) > 0

    def test_status_truncation(self):
        """Test that long status messages are truncated in answer."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Deploy", "Deploy guide")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Deploy guide content.")

        # Create long status update with relevant keywords
        long_message = (
            "INCIDENT: Deploy pipeline is broken and failing. "
            + "This is a very long status message. " * 20  # Make it long
        )
        status_cache = StatusUpdateCache(ttl_hours=24)
        status_update = create_test_status_update(long_message)
        status_cache.add_update(status_update)

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=status_cache,
        )

        result = pipeline.answer_question("Why is deploy broken?")

        # Verify truncation
        assert result.answered is True
        assert "..." in result.answer  # Truncation indicator
        assert "Related Status Updates:" in result.answer
        # Original message is longer than 200 chars
        assert len(long_message) > 200
        # But answer should not contain the full message
        assert long_message not in result.answer

    def test_multiple_status_updates(self):
        """Test handling of multiple matching status updates."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Deploy", "Deploy guide")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Deploy guide.")

        # Add multiple status updates
        status_cache = StatusUpdateCache(ttl_hours=24)
        status_cache.add_update(create_test_status_update("INCIDENT: Deploy broken"))
        status_cache.add_update(create_test_status_update("INCIDENT: Build failing"))
        status_cache.add_update(create_test_status_update("INCIDENT: GitHub down"))

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=status_cache,
        )

        result = pipeline.answer_question("Why is deploy broken?")

        # Should include top 2 status updates
        assert result.answered is True
        assert result.status_updates is not None
        # Top 2 shown in answer
        status_count = result.answer.count("[View full message]")
        assert status_count == 2  # Top 2 shown

    def test_status_cache_optional(self):
        """Test that pipeline works without status cache (backwards compatible)."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Deploy", "Deploy guide")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Deploy guide.")

        # No status cache provided
        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=None,  # Explicitly None
        )

        result = pipeline.answer_question("How do I deploy?")

        # Should work normally without status
        assert result.answered is True
        assert "Deploy guide." in result.answer
        assert "Related Status Updates:" not in result.answer


class TestStatusEmbeddingLazyLoading:
    """Test that status embeddings are generated lazily."""

    def test_embedding_lazy_loading(self):
        """Test that embeddings are only generated when needed."""
        embedding_model = MockEmbeddingModel()
        chunk = MockChunk("Deploy", "Guide")
        vector_store = MockVectorStore([MockSearchResult(chunk, 0.85)])
        claude_client = MockClaudeClient("Guide.")

        status_cache = StatusUpdateCache(ttl_hours=24)
        status_update = create_test_status_update("INCIDENT: Deploy broken")
        status_cache.add_update(status_update)

        # Initially no embedding
        assert status_update.embedding is None

        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            status_cache=status_cache,
        )

        # After answering question, embedding should be generated
        result = pipeline.answer_question("Why is deploy broken?")

        # Embedding should now exist
        assert status_update.embedding is not None
        assert isinstance(status_update.embedding, np.ndarray)


class TestAnswerResultDataclass:
    """Test AnswerResult dataclass with status field."""

    def test_answer_result_with_status(self):
        """Test creating AnswerResult with status updates."""
        status_update = create_test_status_update()
        result = AnswerResult(
            answered=True,
            answer="Test answer",
            results=[],
            confidence=None,
            status_updates=[(status_update, 0.95)],
        )

        assert result.answered is True
        assert result.answer == "Test answer"
        assert result.status_updates is not None
        assert len(result.status_updates) == 1
        assert result.status_updates[0][1] == 0.95  # Similarity score

    def test_answer_result_without_status(self):
        """Test AnswerResult without status (backwards compatible)."""
        result = AnswerResult(
            answered=True,
            answer="Test answer",
            results=[],
        )

        assert result.answered is True
        assert result.status_updates is None
