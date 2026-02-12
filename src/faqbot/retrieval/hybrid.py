"""Hybrid search combining semantic and BM25 using Reciprocal Rank Fusion."""

from typing import List, Dict
from collections import defaultdict

from ..types import FAQChunk
from .store import SearchResult, VectorStore
from .bm25_index import BM25Index
from .embeddings import EmbeddingModel


def reciprocal_rank_fusion(
    semantic_results: List[SearchResult],
    bm25_results: List[SearchResult],
    k: int = 60
) -> List[SearchResult]:
    """Fuse semantic and BM25 results using Reciprocal Rank Fusion (RRF).

    RRF formula: score = sum(1 / (k + rank_i))
    where rank_i is the rank (0-indexed) in each result list

    Args:
        semantic_results: Results from semantic search
        bm25_results: Results from BM25 search
        k: RRF constant (default 60, standard value from IR literature)

    Returns:
        Merged and sorted SearchResults with RRF scores
    """
    # Build map: block_id -> RRF score
    rrf_scores: Dict[str, float] = defaultdict(float)

    # Add semantic rankings
    for rank, result in enumerate(semantic_results):
        block_id = result.chunk.block_id
        rrf_scores[block_id] += 1.0 / (k + rank)

    # Add BM25 rankings
    for rank, result in enumerate(bm25_results):
        block_id = result.chunk.block_id
        rrf_scores[block_id] += 1.0 / (k + rank)

    # Collect all unique chunks
    chunk_map: Dict[str, FAQChunk] = {}
    for result in semantic_results + bm25_results:
        chunk_map[result.chunk.block_id] = result.chunk

    # Create merged results with RRF scores
    merged_results = []
    for block_id, score in rrf_scores.items():
        merged_results.append(
            SearchResult(
                chunk=chunk_map[block_id],
                similarity=score
            )
        )

    # Sort by RRF score (descending)
    merged_results.sort(key=lambda x: x.similarity, reverse=True)

    return merged_results


class HybridSearch:
    """Hybrid search combining semantic and BM25 retrieval."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        embedding_model: EmbeddingModel,
        fusion_method: str = "rrf",
        semantic_top_k: int = 20,
        bm25_top_k: int = 20,
    ):
        """Initialize hybrid search.

        Args:
            vector_store: Vector store for semantic search
            bm25_index: BM25 index for keyword search
            embedding_model: Embedding model for query encoding
            fusion_method: Fusion method (currently only "rrf" supported)
            semantic_top_k: Number of results from semantic search
            bm25_top_k: Number of results from BM25 search
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedding_model = embedding_model
        self.fusion_method = fusion_method
        self.semantic_top_k = semantic_top_k
        self.bm25_top_k = bm25_top_k

        if fusion_method != "rrf":
            raise ValueError(f"Unsupported fusion method: {fusion_method}")

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Perform hybrid search combining semantic and BM25.

        Args:
            query: User query
            top_k: Number of final results to return

        Returns:
            List of SearchResults sorted by fused score
        """
        # Generate query embedding for semantic search
        query_embedding = self.embedding_model.embed(query)

        # Get semantic results
        semantic_results = self.vector_store.search(
            query_embedding,
            top_k=self.semantic_top_k
        )

        # Get BM25 results
        bm25_results = self.bm25_index.search(
            query,
            top_k=self.bm25_top_k
        )

        # Fuse results
        if self.fusion_method == "rrf":
            fused_results = reciprocal_rank_fusion(
                semantic_results,
                bm25_results
            )
        else:
            # Should never reach here due to constructor validation
            raise ValueError(f"Unsupported fusion method: {self.fusion_method}")

        # Return top_k results
        return fused_results[:top_k]
