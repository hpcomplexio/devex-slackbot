"""FAISS vector store for FAQ chunks."""

import faiss
import numpy as np
from typing import List, Optional
from dataclasses import dataclass

from ..notion.chunking import FAQChunk


@dataclass
class SearchResult:
    """A search result with chunk and similarity score."""

    chunk: FAQChunk
    similarity: float


class VectorStore:
    """FAISS-based vector store for FAQ chunks."""

    def __init__(self, dimension: int):
        """Initialize vector store.

        Args:
            dimension: Dimension of embeddings (e.g., 384 for all-MiniLM-L6-v2)
        """
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self.chunks: List[FAQChunk] = []

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

    def clear(self) -> None:
        """Clear all chunks and reset index."""
        self.chunks = []
        self.index = faiss.IndexFlatIP(self.dimension)

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
