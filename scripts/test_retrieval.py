"""Test script for retrieval system with sample questions."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from faqbot.config import Config
from faqbot.notion.client import NotionClient
from faqbot.notion.chunking import chunk_by_headings
from faqbot.retrieval.embeddings import EmbeddingModel
from faqbot.retrieval.store import VectorStore
from faqbot.retrieval.ranker import check_confidence


def main():
    """Test retrieval with sample questions."""
    try:
        # Load config
        print("Loading configuration...")
        config = Config.from_env()
        config.validate()

        # Fetch FAQ content
        print("Fetching FAQ content from Notion...")
        client = NotionClient(config.notion_api_key)
        page, blocks = client.get_page_content(config.notion_faq_page_id)
        chunks = chunk_by_headings(page, blocks, config.notion_faq_page_id)
        print(f"✓ Loaded {len(chunks)} chunks")

        # Initialize embedding model
        print("\nInitializing embedding model (this may download the model)...")
        embedding_model = EmbeddingModel()
        print(f"✓ Model loaded (dimension: {embedding_model.dimension})")

        # Create embeddings for chunks
        print("\nGenerating embeddings for chunks...")
        chunk_texts = [f"{chunk.heading}\n{chunk.content}" for chunk in chunks]
        embeddings = embedding_model.embed_batch(chunk_texts)
        print(f"✓ Generated embeddings of shape {embeddings.shape}")

        # Build vector store
        print("\nBuilding vector store...")
        store = VectorStore(dimension=embedding_model.dimension)
        store.add_chunks(chunks, embeddings)
        print(f"✓ Vector store ready with {store.size()} chunks")

        # Test questions
        test_questions = [
            "How do I reset my password?",
            "What are the office hours?",
            "How do I contact support?",
            "What is the meaning of life?",  # Should fail confidence
        ]

        print("\n" + "=" * 80)
        print("TESTING RETRIEVAL")
        print("=" * 80)

        for question in test_questions:
            print(f"\nQuestion: {question}")
            print("-" * 80)

            # Generate query embedding
            query_embedding = embedding_model.embed(question)

            # Search
            results = store.search(query_embedding, top_k=config.top_k)

            # Check confidence
            confidence = check_confidence(
                results, min_similarity=config.min_similarity, min_gap=config.min_gap
            )

            print(f"Should answer: {confidence.should_answer}")
            print(f"Reason: {confidence.reason}")

            if results:
                print(f"\nTop {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. [{result.similarity:.3f}] {result.chunk.heading}")
                    print(f"     {result.chunk.content[:100]}...")

            print()

        print("✓ Retrieval test complete")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
