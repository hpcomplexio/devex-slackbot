"""BM25-based keyword search for FAQ chunks."""

import re
from typing import List, Optional
from rank_bm25 import BM25Okapi

from ..types import FAQChunk
from .store import SearchResult


def simple_tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase and split on non-alphanumeric characters.

    Args:
        text: Text to tokenize

    Returns:
        List of tokens (lowercase words)
    """
    # Lowercase and split on non-alphanumeric (keeps numbers)
    tokens = re.findall(r'\w+', text.lower())
    return tokens


class BM25Index:
    """BM25-based keyword search for FAQ chunks."""

    def __init__(self):
        """Initialize empty BM25 index."""
        self.index: Optional[BM25Okapi] = None
        self.chunks: List[FAQChunk] = []
        self.tokenized_corpus: List[List[str]] = []

    def build(self, chunks: List[FAQChunk]) -> None:
        """Build BM25 index from FAQ chunks.

        Args:
            chunks: List of FAQ chunks to index
        """
        if not chunks:
            self.index = None
            self.chunks = []
            self.tokenized_corpus = []
            return

        self.chunks = chunks

        # Tokenize each chunk (heading + content combined)
        self.tokenized_corpus = []
        for chunk in chunks:
            # Combine heading and content for comprehensive keyword matching
            combined_text = f"{chunk.heading} {chunk.content}"
            tokens = simple_tokenize(combined_text)
            self.tokenized_corpus.append(tokens)

        # Build BM25 index with default parameters (k1=1.5, b=0.75)
        self.index = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """Search using BM25 keyword matching.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of SearchResults sorted by BM25 score (highest first)
        """
        if not self.index or not self.chunks:
            return []

        # Tokenize query
        query_tokens = simple_tokenize(query)

        if not query_tokens:
            return []

        # Get BM25 scores for all documents
        scores = self.index.get_scores(query_tokens)

        # Create SearchResults with scores
        results = []
        for idx, score in enumerate(scores):
            if score > 0:  # Only include documents with positive scores
                results.append(
                    SearchResult(
                        chunk=self.chunks[idx],
                        similarity=float(score)
                    )
                )

        # Sort by score (descending) and return top_k
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear the index."""
        self.index = None
        self.chunks = []
        self.tokenized_corpus = []

    def size(self) -> int:
        """Return number of chunks in the index."""
        return len(self.chunks)
