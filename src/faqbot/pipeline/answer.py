"""Main pipeline for answering questions."""

from typing import Optional, List
from dataclasses import dataclass

from ..retrieval.embeddings import EmbeddingModel
from ..retrieval.store import VectorStore, SearchResult
from ..retrieval.ranker import check_confidence, ConfidenceCheck
from ..llm.claude import ClaudeClient
from ..llm.prompts import SYSTEM_PROMPT, build_user_prompt


@dataclass
class AnswerResult:
    """Result of answer generation."""

    answered: bool
    answer: Optional[str] = None
    reason: Optional[str] = None
    results: Optional[List[SearchResult]] = None
    confidence: Optional[ConfidenceCheck] = None


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
    ):
        """Initialize pipeline.

        Args:
            embedding_model: Model for generating embeddings
            vector_store: Vector store with FAQ chunks
            claude_client: Claude API client
            top_k: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold
            min_gap: Minimum gap threshold
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.claude_client = claude_client
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.min_gap = min_gap

    def answer_question(self, question: str) -> AnswerResult:
        """Answer a question using the full pipeline.

        Args:
            question: User's question

        Returns:
            AnswerResult with answer or reason for not answering
        """
        # Step 1: Generate query embedding
        query_embedding = self.embedding_model.embed(question)

        # Step 2: Retrieve relevant chunks
        results = self.vector_store.search(query_embedding, top_k=self.top_k)

        if not results:
            return AnswerResult(
                answered=False, reason="No relevant FAQ content found", results=[]
            )

        # Step 3: Check confidence
        confidence = check_confidence(
            results, min_similarity=self.min_similarity, min_gap=self.min_gap
        )

        if not confidence.should_answer:
            return AnswerResult(
                answered=False,
                reason=confidence.reason,
                results=results,
                confidence=confidence,
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
                )

            return AnswerResult(
                answered=True,
                answer=answer,
                results=results,
                confidence=confidence,
            )

        except Exception as e:
            return AnswerResult(
                answered=False,
                reason=f"Error generating answer: {e}",
                results=results,
                confidence=confidence,
            )
