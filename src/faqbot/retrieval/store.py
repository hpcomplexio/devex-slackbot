"""FAISS vector store for FAQ chunks."""

import faiss
import numpy as np
from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass

from ..types import FAQChunk

if TYPE_CHECKING:
    from .bm25_index import BM25Index
    from .hybrid import HybridSearch
    from .embeddings import EmbeddingModel


@dataclass
class SearchResult:
    """A search result with chunk and similarity score."""

    chunk: FAQChunk
    similarity: float


class VectorStore:
    """FAISS-based vector store for FAQ chunks."""

    def __init__(self, dimension: int, bm25_index: Optional["BM25Index"] = None):
        """Initialize vector store.

        Args:
            dimension: Dimension of embeddings (e.g., 384 for all-MiniLM-L6-v2)
            bm25_index: Optional BM25 index for hybrid search
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self.chunks: List[FAQChunk] = []
        self.bm25_index = bm25_index

    def add_chunks(self, chunks: List[FAQChunk], embeddings: np.ndarray) -> None:
        """Add chunks with their embeddings to the store.

        Args:
            chunks: List of FAQ chunks
            embeddings: Normalized embeddings array of shape (len(chunks), dimension)
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        self.chunks = chunks
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings.astype(np.float32))

        # Also build BM25 index if enabled
        if self.bm25_index is not None:
            self.bm25_index.build(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """Search for most similar chunks.

        Args:
            query_embedding: Normalized query embedding
            top_k: Number of results to return

        Returns:
            List of SearchResults sorted by similarity (highest first)
        """
        if self.index.ntotal == 0:
            return []

        # Ensure query is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Search
        distances, indices = self.index.search(
            query_embedding.astype(np.float32), min(top_k, self.index.ntotal)
        )

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0:  # FAISS returns -1 for missing results
                results.append(
                    SearchResult(chunk=self.chunks[idx], similarity=float(dist))
                )

        return results

    def search_hybrid(
        self,
        query: str,
        embedding_model: "EmbeddingModel",
        top_k: int = 5,
        semantic_top_k: int = 20,
        bm25_top_k: int = 20
    ) -> List[SearchResult]:
        """Search using hybrid (BM25 + semantic) approach.

        Args:
            query: User query string
            embedding_model: Embedding model for query encoding
            top_k: Number of final results to return
            semantic_top_k: Number of semantic results to retrieve
            bm25_top_k: Number of BM25 results to retrieve

        Returns:
            List of SearchResults sorted by fused score (highest first)

        Raises:
            ValueError: If BM25 index is not configured
        """
        if self.bm25_index is None:
            raise ValueError("BM25 index not configured. Initialize VectorStore with bm25_index parameter.")

        # Import here to avoid circular dependency
        from .hybrid import HybridSearch

        # Create hybrid search instance
        hybrid_search = HybridSearch(
            vector_store=self,
            bm25_index=self.bm25_index,
            embedding_model=embedding_model,
            semantic_top_k=semantic_top_k,
            bm25_top_k=bm25_top_k,
        )

        # Perform hybrid search
        return hybrid_search.search(query, top_k=top_k)

    def clear(self) -> None:
        """Clear all chunks and reset index."""
        self.chunks = []
        self.index = faiss.IndexFlatIP(self.dimension)
        if self.bm25_index is not None:
            self.bm25_index.clear()

    def size(self) -> int:
        """Return number of chunks in the store."""
        return len(self.chunks)


def get_chunk_by_id(vector_store: VectorStore, block_id: str) -> Optional[FAQChunk]:
    """Find a chunk by its block ID.

    Args:
        vector_store: The vector store to search
        block_id: The block ID to search for

    Returns:
        The matching FAQChunk or None if not found
    """
    for chunk in vector_store.chunks:
        if chunk.block_id == block_id:
            return chunk
    return None
