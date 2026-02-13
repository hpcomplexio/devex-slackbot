"""Cross-encoder reranking for improved result accuracy."""

from typing import List, Union, TYPE_CHECKING
import numpy as np
from sentence_transformers import CrossEncoder

from ..types import FAQChunk
from .store import SearchResult, VectorStore

if TYPE_CHECKING:
    from .hybrid import HybridSearch


class CrossEncoderReranker:
    """Cross-encoder reranker for FAQ chunks.

    Uses a cross-encoder model to rerank search results with higher accuracy
    than bi-encoder semantic similarity.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize cross-encoder model.

        Args:
            model_name: Name of the cross-encoder model from sentence-transformers
        """
        self.model = CrossEncoder(model_name)
        self.model_name = model_name

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """Rerank search results using cross-encoder.

        Args:
            query: User query
            results: Initial search results to rerank
            top_k: Number of results to return after reranking

        Returns:
            Reranked SearchResults with updated similarity scores
        """
        if not results:
            return []

        # Prepare query-document pairs
        # Format: (query, "heading\ncontent") for each chunk
        pairs = [
            (query, f"{r.chunk.heading}\n{r.chunk.content}")
            for r in results
        ]

        # Get cross-encoder scores (raw logits)
        raw_scores = self.model.predict(pairs)

        # Normalize scores to [0, 1] using sigmoid
        # Cross-encoder outputs logits (typically -10 to +10), sigmoid converts to probabilities
        normalized_scores = 1 / (1 + np.exp(-np.array(raw_scores)))

        # Create new SearchResults with normalized scores
        reranked = [
            SearchResult(chunk=r.chunk, similarity=float(score))
            for r, score in zip(results, normalized_scores)
        ]

        # Sort by score (descending) and return top_k
        reranked.sort(key=lambda x: x.similarity, reverse=True)
        return reranked[:top_k]


class RerankedSearch:
    """Search wrapper that adds cross-encoder reranking.

    Performs two-stage retrieval:
    1. Initial retrieval (semantic or hybrid) to get candidates
    2. Cross-encoder reranking for final ranking
    """

    def __init__(
        self,
        base_search: Union[VectorStore, "HybridSearch"],
        reranker: CrossEncoderReranker,
        embedding_model,
        retrieval_top_k: int = 20,
        rerank_top_k: int = 5,
        use_hybrid: bool = False,
        hybrid_semantic_top_k: int = 20,
        hybrid_bm25_top_k: int = 20,
    ):
        """Initialize reranked search.

        Args:
            base_search: Base search (VectorStore or HybridSearch)
            reranker: Cross-encoder reranker
            embedding_model: Embedding model for query encoding
            retrieval_top_k: Number of candidates to retrieve
            rerank_top_k: Number of results to return after reranking
            use_hybrid: Whether base_search is using hybrid mode
            hybrid_semantic_top_k: Semantic top_k for hybrid search
            hybrid_bm25_top_k: BM25 top_k for hybrid search
        """
        self.base_search = base_search
        self.reranker = reranker
        self.embedding_model = embedding_model
        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k
        self.use_hybrid = use_hybrid
        self.hybrid_semantic_top_k = hybrid_semantic_top_k
        self.hybrid_bm25_top_k = hybrid_bm25_top_k

    def search(self, query: str) -> List[SearchResult]:
        """Search with reranking.

        Args:
            query: User query string

        Returns:
            Reranked search results
        """
        # Stage 1: Retrieve candidates
        if self.use_hybrid:
            # Use hybrid search
            candidates = self.base_search.search_hybrid(
                query=query,
                embedding_model=self.embedding_model,
                top_k=self.retrieval_top_k,
                semantic_top_k=self.hybrid_semantic_top_k,
                bm25_top_k=self.hybrid_bm25_top_k,
            )
        else:
            # Use pure semantic search
            query_embedding = self.embedding_model.embed(query)
            candidates = self.base_search.search(
                query_embedding,
                top_k=self.retrieval_top_k
            )

        # Stage 2: Rerank
        return self.reranker.rerank(query, candidates, top_k=self.rerank_top_k)
