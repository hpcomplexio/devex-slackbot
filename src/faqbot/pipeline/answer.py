"""Main pipeline for answering questions."""

from typing import Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from ..retrieval.embeddings import EmbeddingModel
from ..retrieval.store import VectorStore, SearchResult
from ..retrieval.ranker import check_confidence_ratio, ConfidenceCheck
from ..llm.claude import ClaudeClient
from ..llm.prompts import SYSTEM_PROMPT, build_user_prompt
from ..status.cache import StatusUpdateCache, StatusUpdate, INCIDENT_KEYWORDS

if TYPE_CHECKING:
    from ..retrieval.reranker import RerankedSearch


@dataclass
class AnswerResult:
    """Result of answer generation."""

    answered: bool
    answer: Optional[str] = None
    reason: Optional[str] = None
    results: Optional[List[SearchResult]] = None
    confidence: Optional[ConfidenceCheck] = None
    status_updates: Optional[List[Tuple[StatusUpdate, float]]] = None  # NEW: Status correlations


class AnswerPipeline:
    """Pipeline for retrieving context and generating answers."""

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        claude_client: ClaudeClient,
        top_k: int = 5,
        min_similarity: float = 0.70,
        min_gap: float = 0.15,
        min_ratio: float = 1.05,
        status_cache: Optional[StatusUpdateCache] = None,
        hybrid_search_enabled: bool = False,
        hybrid_semantic_top_k: int = 20,
        hybrid_bm25_top_k: int = 20,
        reranked_search: Optional["RerankedSearch"] = None,
        # Mode-specific ratio thresholds
        semantic_min_ratio: float = 1.10,
        hybrid_min_ratio: float = 1.02,
        reranking_min_ratio: float = 1.05,
    ):
        """Initialize pipeline.

        Args:
            embedding_model: Model for generating embeddings
            vector_store: Vector store with FAQ chunks
            claude_client: Claude API client
            top_k: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold
            min_gap: Minimum gap threshold (legacy, kept for compatibility)
            min_ratio: Default minimum ratio threshold
            status_cache: Optional cache of status updates for incident correlation
            hybrid_search_enabled: Enable hybrid BM25 + semantic search
            hybrid_semantic_top_k: Number of semantic results for hybrid search
            hybrid_bm25_top_k: Number of BM25 results for hybrid search
            reranked_search: Optional reranked search wrapper (takes precedence)
            semantic_min_ratio: Ratio threshold for pure semantic search
            hybrid_min_ratio: Ratio threshold for hybrid search (lower due to RRF)
            reranking_min_ratio: Ratio threshold for cross-encoder reranking
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.claude_client = claude_client
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.min_gap = min_gap
        self.min_ratio = min_ratio
        self.status_cache = status_cache
        self.hybrid_search_enabled = hybrid_search_enabled
        self.hybrid_semantic_top_k = hybrid_semantic_top_k
        self.hybrid_bm25_top_k = hybrid_bm25_top_k
        self.reranked_search = reranked_search
        # Mode-specific ratio thresholds
        self.semantic_min_ratio = semantic_min_ratio
        self.hybrid_min_ratio = hybrid_min_ratio
        self.reranking_min_ratio = reranking_min_ratio

    def answer_question(self, question: str) -> AnswerResult:
        """Answer a question using the full pipeline with status correlation.

        Args:
            question: User's question

        Returns:
            AnswerResult with answer or reason for not answering
        """
        # Step 1: Generate query embedding
        query_embedding = self.embedding_model.embed(question)

        # Step 2: Retrieve relevant FAQ chunks
        if self.reranked_search:
            # Use reranked search (takes precedence over hybrid/semantic)
            results = self.reranked_search.search(question)
        elif self.hybrid_search_enabled:
            # Use hybrid search (BM25 + semantic)
            results = self.vector_store.search_hybrid(
                query=question,
                embedding_model=self.embedding_model,
                top_k=self.top_k,
                semantic_top_k=self.hybrid_semantic_top_k,
                bm25_top_k=self.hybrid_bm25_top_k,
            )
        else:
            # Use pure semantic search
            results = self.vector_store.search(query_embedding, top_k=self.top_k)

        if not results:
            return AnswerResult(
                answered=False, reason="No relevant FAQ content found", results=[]
            )

        # Step 2.5: Search status updates (NEW)
        status_results: List[Tuple[StatusUpdate, float]] = []
        if self.status_cache:
            try:
                # Extract keywords from question
                question_lower = question.lower()
                question_keywords = [
                    kw for kw in INCIDENT_KEYWORDS if kw in question_lower
                ]

                # Semantic search on status updates
                if question_keywords or len(self.status_cache.updates) > 0:
                    status_results = self.status_cache.search_semantic(
                        query_embedding,
                        self.embedding_model,
                        top_k=3,
                        min_similarity=0.50,  # Lower threshold for status
                    )
            except Exception as e:
                # Log error but don't fail the entire pipeline
                # Status correlation is supplementary, not critical
                pass

        # Step 3: Check confidence using ratio-based metric
        # Select appropriate ratio threshold based on search mode
        if self.reranked_search:
            active_min_ratio = self.reranking_min_ratio
        elif self.hybrid_search_enabled:
            active_min_ratio = self.hybrid_min_ratio
        else:
            active_min_ratio = self.semantic_min_ratio

        confidence = check_confidence_ratio(
            results, min_similarity=self.min_similarity, min_ratio=active_min_ratio
        )

        if not confidence.should_answer:
            return AnswerResult(
                answered=False,
                reason=confidence.reason,
                results=results,
                confidence=confidence,
                status_updates=status_results,  # Include status even for low confidence
            )

        # Step 4: Generate answer with Claude
        try:
            user_prompt = build_user_prompt(question, results)
            answer = self.claude_client.generate_answer(SYSTEM_PROMPT, user_prompt)

            if not answer:
                return AnswerResult(
                    answered=False,
                    reason="Failed to generate answer",
                    results=results,
                    confidence=confidence,
                    status_updates=status_results,
                )

            # Step 5: Append status updates to answer (NEW)
            if status_results:
                answer += "\n\n---\n**Related Status Updates:**\n"
                for status, similarity in status_results[:2]:  # Show top 2
                    # Format timestamp
                    time_str = status.posted_at.strftime("%Y-%m-%d %H:%M")
                    # Truncate message
                    message_preview = (
                        status.message_text[:200]
                        if len(status.message_text) > 200
                        else status.message_text
                    )
                    # Add to answer with link
                    answer += f"\n• [{time_str}] {message_preview}"
                    if len(status.message_text) > 200:
                        answer += "..."
                    answer += f" [View full message]({status.message_link})"

            return AnswerResult(
                answered=True,
                answer=answer,
                results=results,
                confidence=confidence,
                status_updates=status_results,
            )

        except Exception as e:
            return AnswerResult(
                answered=False,
                reason=f"Error generating answer: {e}",
                results=results,
                confidence=confidence,
                status_updates=status_results,
            )
