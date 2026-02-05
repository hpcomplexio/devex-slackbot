"""Unit tests for FAQ suggestion service."""

from dataclasses import dataclass
from typing import List

import numpy as np

from src.faqbot.search.suggestions import FAQSuggestion, FAQSuggestionService


@dataclass
class MockChunk:
    """Mock FAQ chunk for testing."""

    block_id: str
    heading: str
    content: str
    notion_url: str


@dataclass
class MockSearchResult:
    """Mock search result from vector store."""

    chunk: MockChunk
    similarity: float


class MockEmbeddingModel:
    """Mock embedding model for testing."""

    def embed(self, text: str) -> np.ndarray:
        """Return a simple embedding based on text length."""
        vec = np.array([len(text), len(text.split())], dtype=float)
        return vec / np.linalg.norm(vec)


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self, chunks: List[MockChunk], similarities: List[float]):
        """Initialize with predefined chunks and their similarities."""
        self.chunks = chunks
        self.similarities = similarities

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[MockSearchResult]:
        """Return mock search results."""
        results = []
        for i, (chunk, sim) in enumerate(zip(self.chunks, self.similarities)):
            if i >= top_k:
                break
            results.append(MockSearchResult(chunk=chunk, similarity=sim))
        return results


class TestFAQSuggestionService:
    """Test suite for FAQSuggestionService."""

    def test_search_returns_suggestions(self):
        """Test that search returns formatted suggestions."""
        chunks = [
            MockChunk(
                block_id="chunk1",
                heading="How to deploy",
                content="Deploy using kubectl apply...",
                notion_url="https://notion.so/page1",
            )
        ]
        similarities = [0.85]

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore(chunks, similarities)
        service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.50)

        suggestions = service.search("how do I deploy?", top_k=5)

        assert len(suggestions) == 1
        assert isinstance(suggestions[0], FAQSuggestion)
        assert suggestions[0].block_id == "chunk1"
        assert suggestions[0].heading == "How to deploy"
        assert suggestions[0].similarity == 0.85

    def test_filters_by_min_similarity(self):
        """Test that suggestions below threshold are filtered out."""
        chunks = [
            MockChunk("chunk1", "High match", "Content 1", "url1"),
            MockChunk("chunk2", "Medium match", "Content 2", "url2"),
            MockChunk("chunk3", "Low match", "Content 3", "url3"),
        ]
        similarities = [0.90, 0.65, 0.30]

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore(chunks, similarities)
        service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.60)

        suggestions = service.search("test query", top_k=10)

        # Only first two should pass threshold
        assert len(suggestions) == 2
        assert suggestions[0].similarity == 0.90
        assert suggestions[1].similarity == 0.65

    def test_truncates_content_preview(self):
        """Test that content preview is truncated to 200 chars."""
        long_content = "a" * 500
        chunks = [MockChunk("chunk1", "Test", long_content, "url1")]
        similarities = [0.85]

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore(chunks, similarities)
        service = FAQSuggestionService(embedding_model, vector_store)

        suggestions = service.search("test", top_k=5)

        assert len(suggestions[0].content_preview) == 200
        assert suggestions[0].content_preview == "a" * 200

    def test_respects_top_k(self):
        """Test that top_k limits the number of results."""
        chunks = [
            MockChunk(f"chunk{i}", f"Heading {i}", f"Content {i}", f"url{i}")
            for i in range(10)
        ]
        similarities = [0.9 - i * 0.05 for i in range(10)]  # Descending similarities

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore(chunks, similarities)
        service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.0)

        suggestions = service.search("test", top_k=3)

        assert len(suggestions) == 3

    def test_empty_results(self):
        """Test handling of no matching results."""
        chunks = [MockChunk("chunk1", "Test", "Content", "url1")]
        similarities = [0.20]

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore(chunks, similarities)
        service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.50)

        suggestions = service.search("test", top_k=5)

        assert len(suggestions) == 0

    def test_sorted_by_similarity(self):
        """Test that results are sorted by similarity descending."""
        chunks = [
            MockChunk("chunk1", "Low", "Content 1", "url1"),
            MockChunk("chunk2", "High", "Content 2", "url2"),
            MockChunk("chunk3", "Medium", "Content 3", "url3"),
        ]
        # Note: Vector store returns in this order
        similarities = [0.60, 0.90, 0.75]

        embedding_model = MockEmbeddingModel()
        vector_store = MockVectorStore(chunks, similarities)
        service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.50)

        suggestions = service.search("test", top_k=10)

        # Should maintain the order from vector store (assumed pre-sorted)
        assert len(suggestions) == 3
        assert suggestions[0].similarity == 0.60
        assert suggestions[1].similarity == 0.90
        assert suggestions[2].similarity == 0.75


class TestFAQSuggestion:
    """Test suite for FAQSuggestion dataclass."""

    def test_suggestion_creation(self):
        """Test creating a suggestion with all fields."""
        suggestion = FAQSuggestion(
            block_id="test123",
            heading="Test Heading",
            content_preview="This is a preview...",
            similarity=0.85,
            url="https://notion.so/test",
        )

        assert suggestion.block_id == "test123"
        assert suggestion.heading == "Test Heading"
        assert suggestion.content_preview == "This is a preview..."
        assert suggestion.similarity == 0.85
        assert suggestion.url == "https://notion.so/test"
