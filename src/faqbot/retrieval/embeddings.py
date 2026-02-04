"""Sentence Transformers wrapper for embeddings."""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingModel:
    """Wrapper for Sentence Transformers embedding model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model.

        Args:
            model_name: Name of the Sentence Transformers model.
                       Default is all-MiniLM-L6-v2 (384 dimensions).
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        # Normalize for cosine similarity
        return embedding / np.linalg.norm(embedding)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts.

        Returns:
            numpy array of shape (len(texts), dimension)
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        # Normalize each embedding
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / norms
