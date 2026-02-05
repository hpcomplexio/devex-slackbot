"""Shared service for FAQ suggestions across all interfaces."""

from dataclasses import dataclass
from typing import List


@dataclass
class FAQSuggestion:
    """Formatted FAQ suggestion for display in Slack.

    This provides a simplified interface for showing FAQ results
    to users without exposing internal retrieval details.
    """

    block_id: str
    heading: str
    content_preview: str
    similarity: float
    url: str


class FAQSuggestionService:
    """Shared service for FAQ suggestions across all interfaces.

    This centralizes the FAQ search logic so that reaction handlers,
    slash commands, and other interfaces can all use the same
    search and filtering logic.
    """

    def __init__(self, embedding_model, vector_store, min_similarity: float = 0.50):
        """Initialize the FAQ suggestion service.

        Args:
            embedding_model: The embedding model for generating query embeddings
            vector_store: The vector store containing FAQ chunks
            min_similarity: Minimum similarity threshold for suggestions (0.0 to 1.0)
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.min_similarity = min_similarity

    def search(self, query: str, top_k: int = 5) -> List[FAQSuggestion]:
        """Search FAQs and return formatted suggestions.

        Args:
            query: The user's question or search query
            top_k: Maximum number of suggestions to return

        Returns:
            List of FAQ suggestions sorted by similarity (descending)
        """
        # Generate embedding for the query
        query_embedding = self.embedding_model.embed(query)

        # Search the vector store
        results = self.vector_store.search(query_embedding, top_k=top_k)

        # Filter by minimum similarity and format as suggestions
        suggestions = []
        for result in results:
            if result.similarity >= self.min_similarity:
                suggestions.append(
                    FAQSuggestion(
                        block_id=result.chunk.block_id,
                        heading=result.chunk.heading,
                        content_preview=result.chunk.content[:200],  # Truncate preview
                        similarity=result.similarity,
                        url=result.chunk.notion_url,
                    )
                )

        return suggestions
