#!/usr/bin/env python3
"""Manual test script for Phase 1 (Status Cache) and Phase 2 (FAQ Suggestions).

Run this script to verify the implementation without needing pytest or Slack.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import numpy as np
from src.faqbot.status.cache import StatusUpdate, StatusUpdateCache, INCIDENT_KEYWORDS
from src.faqbot.search.suggestions import FAQSuggestion, FAQSuggestionService


# Mock classes for testing
class MockEmbeddingModel:
    """Mock embedding model."""

    def embed(self, text: str) -> np.ndarray:
        """Return a simple embedding based on text."""
        vec = np.array([len(text), len(text.split()), hash(text) % 100], dtype=float)
        return vec / np.linalg.norm(vec)


class MockChunk:
    """Mock FAQ chunk."""

    def __init__(self, block_id, heading, content, notion_url):
        self.block_id = block_id
        self.heading = heading
        self.content = content
        self.notion_url = notion_url


class MockSearchResult:
    """Mock search result."""

    def __init__(self, chunk, similarity):
        self.chunk = chunk
        self.similarity = similarity


class MockVectorStore:
    """Mock vector store."""

    def __init__(self, chunks, similarities):
        self.chunks = chunks
        self.similarities = similarities

    def search(self, query_embedding, top_k):
        return [
            MockSearchResult(chunk, sim)
            for chunk, sim in zip(self.chunks[: top_k], self.similarities[: top_k])
        ]


def print_test_header(test_name):
    """Print a test section header."""
    print(f"\n{'=' * 60}")
    print(f"  {test_name}")
    print(f"{'=' * 60}")


def print_success(message):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print error message."""
    print(f"❌ {message}")


def test_phase1_status_cache():
    """Test Phase 1: Status Update Cache."""
    print_test_header("PHASE 1: STATUS UPDATE CACHE")

    # Test 1: Create cache and add update
    print("\n1. Testing cache creation and add_update()...")
    cache = StatusUpdateCache(ttl_hours=24)
    update = StatusUpdate(
        message_ts="1234567890.123456",
        channel_id="C123456",
        message_text="INCIDENT: Deploy is broken. Investigating.",
        message_link="https://slack.com/link",
        posted_at=datetime.now(),
        keywords_matched=["deploy", "broken", "incident"],
        embedding=None,
    )
    cache.add_update(update)

    if len(cache.updates) == 1:
        print_success(f"Added update to cache. Cache size: {cache.size()}")
    else:
        print_error(f"Expected 1 update, got {len(cache.updates)}")

    # Test 2: TTL expiration
    print("\n2. Testing TTL expiration...")
    short_cache = StatusUpdateCache(ttl_hours=0)  # Immediate expiration
    old_update = StatusUpdate(
        message_ts="old",
        channel_id="C123",
        message_text="Old incident",
        message_link="link",
        posted_at=datetime.now() - timedelta(hours=1),
        keywords_matched=["incident"],
        embedding=None,
    )
    short_cache.add_update(old_update)

    if short_cache.size() == 0:
        print_success("Expired updates cleaned up correctly")
    else:
        print_error(f"Expected 0 updates after expiration, got {short_cache.size()}")

    # Test 3: Keyword filtering
    print("\n3. Testing keyword filtering...")
    filter_cache = StatusUpdateCache(ttl_hours=24)
    updates = [
        StatusUpdate(
            "1", "C1", "Deploy broken", "link1", datetime.now(), ["deploy", "broken"]
        ),
        StatusUpdate(
            "2", "C1", "GitHub down", "link2", datetime.now(), ["github", "down"]
        ),
        StatusUpdate(
            "3", "C1", "Build failing", "link3", datetime.now(), ["build", "failing"]
        ),
    ]

    for u in updates:
        filter_cache.add_update(u)

    deploy_updates = filter_cache.get_recent_updates(keywords=["deploy"])
    if len(deploy_updates) == 1:
        print_success(f"Keyword filter 'deploy' returned {len(deploy_updates)} update(s)")
    else:
        print_error(f"Expected 1 deploy update, got {len(deploy_updates)}")

    # Test 4: Semantic search
    print("\n4. Testing semantic search...")
    embedding_model = MockEmbeddingModel()
    search_cache = StatusUpdateCache(ttl_hours=24)

    status_updates = [
        StatusUpdate(
            "1",
            "C1",
            "Deploy pipeline is completely broken",
            "link1",
            datetime.now(),
            ["deploy", "broken"],
        ),
        StatusUpdate(
            "2", "C1", "GitHub API is down", "link2", datetime.now(), ["github", "down"]
        ),
    ]

    for u in status_updates:
        search_cache.add_update(u)

    query_embedding = embedding_model.embed("deploy issue")
    results = search_cache.search_semantic(
        query_embedding, embedding_model, top_k=2, min_similarity=0.0
    )

    if len(results) > 0:
        print_success(
            f"Semantic search returned {len(results)} result(s), top similarity: {results[0][1]:.2f}"
        )
        print(f"   Top result: '{results[0][0].message_text[:50]}...'")
    else:
        print_error("Semantic search returned no results")

    # Test 5: Check incident keywords
    print("\n5. Checking incident keywords...")
    if len(INCIDENT_KEYWORDS) > 0:
        print_success(
            f"Found {len(INCIDENT_KEYWORDS)} incident keywords: {INCIDENT_KEYWORDS[:5]}..."
        )
    else:
        print_error("No incident keywords defined")


def test_phase2_faq_suggestions():
    """Test Phase 2: FAQ Suggestion Service."""
    print_test_header("PHASE 2: FAQ SUGGESTION SERVICE")

    # Test 1: Create suggestion service
    print("\n1. Testing suggestion service creation...")
    chunks = [
        MockChunk(
            "chunk1",
            "How to deploy to Kubernetes",
            "To deploy to Kubernetes, use kubectl apply -f deployment.yaml. This will create the necessary pods and services.",
            "https://notion.so/deploy",
        ),
        MockChunk(
            "chunk2",
            "Authentication setup",
            "Set up authentication by configuring your .env file with the appropriate API keys.",
            "https://notion.so/auth",
        ),
    ]
    similarities = [0.85, 0.45]

    embedding_model = MockEmbeddingModel()
    vector_store = MockVectorStore(chunks, similarities)
    service = FAQSuggestionService(embedding_model, vector_store, min_similarity=0.50)

    print_success("Created FAQ suggestion service")

    # Test 2: Search with results
    print("\n2. Testing search with matching results...")
    suggestions = service.search("how do I deploy?", top_k=5)

    if len(suggestions) > 0:
        print_success(f"Found {len(suggestions)} suggestion(s)")
        for i, sug in enumerate(suggestions, 1):
            print(
                f"   {i}. {sug.heading} (similarity: {sug.similarity:.2f})\n"
                f"      Preview: {sug.content_preview[:80]}..."
            )
    else:
        print_error("Expected suggestions but got none")

    # Test 3: Similarity filtering
    print("\n3. Testing similarity threshold filtering...")
    # The second chunk (0.45 similarity) should be filtered out (< 0.50 threshold)
    if len(suggestions) == 1:
        print_success("Low-similarity results correctly filtered out")
    else:
        print_error(f"Expected 1 result after filtering, got {len(suggestions)}")

    # Test 4: Content preview truncation
    print("\n4. Testing content preview truncation...")
    long_content = "a" * 500
    long_chunk = MockChunk("chunk3", "Long content test", long_content, "https://url")
    long_store = MockVectorStore([long_chunk], [0.80])
    long_service = FAQSuggestionService(embedding_model, long_store, min_similarity=0.50)
    long_suggestions = long_service.search("test", top_k=1)

    if long_suggestions and len(long_suggestions[0].content_preview) == 200:
        print_success(
            f"Content truncated to {len(long_suggestions[0].content_preview)} chars"
        )
    else:
        print_error(
            f"Expected 200 char preview, got {len(long_suggestions[0].content_preview) if long_suggestions else 0}"
        )

    # Test 5: Empty results
    print("\n5. Testing empty results handling...")
    empty_store = MockVectorStore([chunks[0]], [0.30])  # Below threshold
    empty_service = FAQSuggestionService(embedding_model, empty_store, min_similarity=0.50)
    empty_suggestions = empty_service.search("test", top_k=5)

    if len(empty_suggestions) == 0:
        print_success("Empty results handled correctly (no results below threshold)")
    else:
        print_error(f"Expected 0 results, got {len(empty_suggestions)}")


def test_integration():
    """Test integration between Phase 1 and Phase 2."""
    print_test_header("INTEGRATION TEST: STATUS + FAQ SUGGESTIONS")

    print("\n1. Simulating a real-world scenario...")
    print("   Scenario: User asks 'why is deploy broken?' during an incident")

    # Step 1: Status update is cached (Phase 1)
    print("\n   Step 1: Incident announcement is posted in #status")
    cache = StatusUpdateCache(ttl_hours=24)
    status_update = StatusUpdate(
        message_ts="123",
        channel_id="C_STATUS",
        message_text="INCIDENT: Main branch build is failing. Deploy pipeline blocked.",
        message_link="https://slack.com/status/123",
        posted_at=datetime.now(),
        keywords_matched=["incident", "deploy", "build", "failing"],
        embedding=None,
    )
    cache.add_update(status_update)
    print_success(f"Status update cached: '{status_update.message_text[:60]}...'")

    # Step 2: User searches FAQs (Phase 2)
    print("\n   Step 2: User asks 'why is deploy broken?'")
    chunks = [
        MockChunk(
            "faq1",
            "Deploy troubleshooting",
            "Check the build logs and ensure your Kubernetes config is correct.",
            "https://notion.so/deploy",
        )
    ]
    embedding_model = MockEmbeddingModel()
    vector_store = MockVectorStore(chunks, [0.75])
    faq_service = FAQSuggestionService(embedding_model, vector_store)

    faq_suggestions = faq_service.search("why is deploy broken", top_k=3)
    print_success(f"FAQ search returned {len(faq_suggestions)} suggestion(s)")

    # Step 3: Status correlation (would be done in Phase 3)
    print("\n   Step 3: Correlating with status updates...")
    query_embedding = embedding_model.embed("why is deploy broken")
    status_matches = cache.search_semantic(
        query_embedding, embedding_model, top_k=3, min_similarity=0.50
    )

    if status_matches:
        print_success(
            f"Found {len(status_matches)} related status update(s):\n"
            f"   - '{status_matches[0][0].message_text[:70]}...' (similarity: {status_matches[0][1]:.2f})"
        )
        print("\n   ✨ In the final system, bot would show:")
        print("      1. FAQ answer: 'Check the build logs...'")
        print(
            f"      2. Related status: 'INCIDENT: Main branch build is failing...' [link]"
        )
    else:
        print_error("No status matches found")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  TESTING PHASE 1 & 2 IMPLEMENTATION")
    print("  (Status Monitoring + FAQ Suggestions)")
    print("=" * 60)

    try:
        test_phase1_status_cache()
        test_phase2_faq_suggestions()
        test_integration()

        print("\n" + "=" * 60)
        print("  ✅ ALL TESTS COMPLETED!")
        print("=" * 60)
        print("\nNext steps:")
        print("  - Phase 3: Enhance answer pipeline with status correlation")
        print("  - Phase 4: Implement reaction-based search (🔍 emoji)")
        print("  - Phase 5: Implement slash command (/ask)")
        print("=" * 60 + "\n")

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"  ❌ TEST FAILED WITH ERROR")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
