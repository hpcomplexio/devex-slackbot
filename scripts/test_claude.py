"""Test script for Claude answer generation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from faqbot.config import Config
from faqbot.notion.client import NotionClient
from faqbot.notion.chunking import chunk_by_headings
from faqbot.retrieval.embeddings import EmbeddingModel
from faqbot.retrieval.store import VectorStore
from faqbot.llm.claude import ClaudeClient
from faqbot.pipeline.answer import AnswerPipeline


def main():
    """Test answer generation with sample questions."""
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

        # Initialize components
        print("\nInitializing components...")
        embedding_model = EmbeddingModel()
        vector_store = VectorStore(dimension=embedding_model.dimension)
        claude_client = ClaudeClient(config.anthropic_api_key)

        # Build vector store
        print("Building vector store...")
        chunk_texts = [f"{chunk.heading}\n{chunk.content}" for chunk in chunks]
        embeddings = embedding_model.embed_batch(chunk_texts)
        vector_store.add_chunks(chunks, embeddings)
        print(f"✓ Vector store ready with {vector_store.size()} chunks")

        # Create pipeline
        pipeline = AnswerPipeline(
            embedding_model=embedding_model,
            vector_store=vector_store,
            claude_client=claude_client,
            top_k=config.top_k,
            min_similarity=config.min_similarity,
            min_gap=config.min_gap,
        )

        # Test questions
        test_questions = [
            "How do I reset my password?",
            "What are the office hours?",
            "How do I contact support?",
        ]

        print("\n" + "=" * 80)
        print("TESTING ANSWER GENERATION")
        print("=" * 80)

        for question in test_questions:
            print(f"\nQuestion: {question}")
            print("-" * 80)

            # Generate answer
            result = pipeline.answer_question(question)

            if result.answered:
                print("✓ Answer generated:")
                print(result.answer)
                print(f"\nUsed {len(result.results)} context chunks")
            else:
                print(f"✗ No answer: {result.reason}")
                if result.confidence:
                    print(f"   Top score: {result.confidence.top_score}")
                    if result.confidence.gap:
                        print(f"   Gap: {result.confidence.gap}")

            print()

        print("✓ Answer generation test complete")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
