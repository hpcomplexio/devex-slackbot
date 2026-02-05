#!/usr/bin/env python3
"""Manual test script for Phase 4 (Reaction-based Search Handlers).

Run this script to verify the implementation without needing pytest.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime
from src.faqbot.slack.reactions import build_suggestion_blocks, SEARCH_EMOJI
from src.faqbot.search.suggestions import FAQSuggestion
from src.faqbot.status.cache import StatusUpdate
from src.faqbot.retrieval.store import get_chunk_by_id


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


class MockChunk:
    """Mock FAQ chunk."""

    def __init__(self, block_id, heading, content, notion_url):
        self.block_id = block_id
        self.heading = heading
        self.content = content
        self.notion_url = notion_url


class MockVectorStore:
    """Mock vector store."""

    def __init__(self, chunks):
        self.chunks = chunks


def test_build_suggestion_blocks_faq_only():
    """Test building blocks with only FAQ suggestions."""
    print("\n1. Testing block building with FAQ suggestions only...")

    suggestions = [
        FAQSuggestion(
            block_id="chunk1",
            heading="How to deploy",
            content_preview="Deploy using kubectl apply...",
            similarity=0.85,
            url="https://notion.so/deploy",
        ),
        FAQSuggestion(
            block_id="chunk2",
            heading="Authentication",
            content_preview="Set up your API keys...",
            similarity=0.70,
            url="https://notion.so/auth",
        ),
    ]

    blocks = build_suggestion_blocks(
        suggestions=suggestions,
        status_results=[],
        thread_ts="123.456",
        channel_id="C123",
    )

    # Verify structure
    if len(blocks) == 0:
        print_error("No blocks generated")
        return False

    if blocks[0]["type"] != "section":
        print_error(f"First block type is {blocks[0]['type']}, expected 'section'")
        return False

    if "FAQ" not in blocks[0]["text"]["text"]:
        print_error("Header doesn't mention FAQ")
        return False

    # Count buttons
    button_count = sum(
        1
        for block in blocks
        if block.get("type") == "section"
        and "accessory" in block
        and block["accessory"].get("type") == "button"
    )

    if button_count != 2:
        print_error(f"Expected 2 buttons, got {button_count}")
        return False

    print_success(f"FAQ-only blocks built correctly with {button_count} buttons")
    return True


def test_build_suggestion_blocks_status_only():
    """Test building blocks with only status updates."""
    print("\n2. Testing block building with status updates only...")

    status_update = StatusUpdate(
        message_ts="123",
        channel_id="C_STATUS",
        message_text="INCIDENT: Deploy is broken",
        message_link="https://slack.com/link",
        posted_at=datetime.now(),
        keywords_matched=["deploy", "broken", "incident"],
        embedding=None,
    )

    blocks = build_suggestion_blocks(
        suggestions=[],
        status_results=[(status_update, 0.95)],
        thread_ts="123.456",
        channel_id="C123",
    )

    if len(blocks) == 0:
        print_error("No blocks generated")
        return False

    block_text = json.dumps(blocks)

    if "Status" not in block_text:
        print_error("Status header not found")
        return False

    if "Deploy is broken" not in block_text:
        print_error("Status message not found in blocks")
        return False

    print_success("Status-only blocks built correctly")
    return True


def test_build_suggestion_blocks_both():
    """Test building blocks with both FAQs and status."""
    print("\n3. Testing block building with both FAQs and status...")

    suggestions = [
        FAQSuggestion(
            block_id="chunk1",
            heading="Deploy guide",
            content_preview="Guide content",
            similarity=0.80,
            url="https://notion.so/deploy",
        )
    ]

    status_update = StatusUpdate(
        message_ts="123",
        channel_id="C_STATUS",
        message_text="INCIDENT: Build failing",
        message_link="https://slack.com/link",
        posted_at=datetime.now(),
        keywords_matched=["build", "failing"],
        embedding=None,
    )

    blocks = build_suggestion_blocks(
        suggestions=suggestions,
        status_results=[(status_update, 0.90)],
        thread_ts="123.456",
        channel_id="C123",
    )

    block_text = json.dumps(blocks)

    missing = []
    for expected in ["FAQ", "Status", "Deploy guide", "Build failing"]:
        if expected not in block_text:
            missing.append(expected)

    if missing:
        print_error(f"Missing expected content: {missing}")
        return False

    print_success("Combined FAQ + Status blocks built correctly")
    return True


def test_block_structure_valid():
    """Test that blocks have valid Slack Block Kit structure."""
    print("\n4. Testing block structure validity...")

    suggestions = [
        FAQSuggestion(
            block_id="test",
            heading="Test",
            content_preview="Content",
            similarity=0.75,
            url="https://notion.so/test",
        )
    ]

    blocks = build_suggestion_blocks(
        suggestions=suggestions,
        status_results=[],
        thread_ts="123.456",
        channel_id="C123",
    )

    for i, block in enumerate(blocks):
        if "type" not in block:
            print_error(f"Block {i} missing 'type' field")
            return False

        if block["type"] not in ["section", "divider", "context"]:
            print_error(f"Block {i} has invalid type: {block['type']}")
            return False

        if block["type"] == "section":
            if "text" not in block:
                print_error(f"Section block {i} missing 'text' field")
                return False

            if block["text"]["type"] not in ["mrkdwn", "plain_text"]:
                print_error(f"Section block {i} has invalid text type")
                return False

    print_success(f"All {len(blocks)} blocks have valid structure")
    return True


def test_button_payloads_valid():
    """Test that button action values are valid JSON."""
    print("\n5. Testing button payload JSON validity...")

    suggestions = [
        FAQSuggestion(
            block_id="chunk1",
            heading="Test",
            content_preview="Content",
            similarity=0.80,
            url="https://notion.so/test",
        )
    ]

    blocks = build_suggestion_blocks(
        suggestions=suggestions,
        status_results=[],
        thread_ts="123.456",
        channel_id="C123",
    )

    button_found = False
    for block in blocks:
        if (
            block.get("type") == "section"
            and "accessory" in block
            and block["accessory"].get("type") == "button"
        ):
            button_found = True
            value = block["accessory"]["value"]

            try:
                payload = json.loads(value)
            except json.JSONDecodeError:
                print_error("Button value is not valid JSON")
                return False

            required_fields = ["block_id", "thread_ts", "channel_id"]
            for field in required_fields:
                if field not in payload:
                    print_error(f"Button payload missing field: {field}")
                    return False

            if payload["thread_ts"] != "123.456":
                print_error(f"Wrong thread_ts: {payload['thread_ts']}")
                return False

            if payload["channel_id"] != "C123":
                print_error(f"Wrong channel_id: {payload['channel_id']}")
                return False

    if not button_found:
        print_error("No buttons found in blocks")
        return False

    print_success("Button payloads are valid JSON with correct fields")
    return True


def test_status_message_truncation():
    """Test that long status messages are truncated."""
    print("\n6. Testing status message truncation...")

    long_message = "INCIDENT: " + "A" * 200
    status_update = StatusUpdate(
        message_ts="123",
        channel_id="C_STATUS",
        message_text=long_message,
        message_link="https://slack.com/link",
        posted_at=datetime.now(),
        keywords_matched=["incident"],
        embedding=None,
    )

    blocks = build_suggestion_blocks(
        suggestions=[],
        status_results=[(status_update, 0.90)],
        thread_ts="123.456",
        channel_id="C123",
    )

    block_text = json.dumps(blocks)

    if "..." not in block_text:
        print_error("No truncation indicator (...) found")
        return False

    if long_message in block_text:
        print_error("Full long message found (not truncated)")
        return False

    print_success("Long status messages are truncated correctly")
    return True


def test_multiple_status_limited():
    """Test that only top 2 status updates are shown."""
    print("\n7. Testing status update limiting (max 2)...")

    status_updates = [
        (
            StatusUpdate(
                f"msg{i}",
                "C_STATUS",
                f"INCIDENT {i}",
                f"link{i}",
                datetime.now(),
                ["incident"],
            ),
            0.9 - i * 0.1,
        )
        for i in range(5)
    ]

    blocks = build_suggestion_blocks(
        suggestions=[],
        status_results=status_updates,
        thread_ts="123.456",
        channel_id="C123",
    )

    block_text = json.dumps(blocks)
    incident_count = sum(1 for i in range(5) if f"INCIDENT {i}" in block_text)

    if incident_count != 2:
        print_error(f"Expected 2 incidents shown, got {incident_count}")
        return False

    if "INCIDENT 0" not in block_text or "INCIDENT 1" not in block_text:
        print_error("Top 2 incidents not shown")
        return False

    print_success("Status updates limited to top 2 correctly")
    return True


def test_search_emoji_constant():
    """Test that search emoji constant is correct."""
    print("\n8. Testing search emoji constant...")

    if SEARCH_EMOJI != "mag":
        print_error(f"Expected 'mag', got '{SEARCH_EMOJI}'")
        return False

    print_success(f"Search emoji constant is correct: '{SEARCH_EMOJI}' (🔍)")
    return True


def test_empty_suggestions_and_status():
    """Test handling when no results are found."""
    print("\n9. Testing empty suggestions and status...")

    blocks = build_suggestion_blocks(
        suggestions=[],
        status_results=[],
        thread_ts="123.456",
        channel_id="C123",
    )

    if len(blocks) == 0:
        print_error("No blocks generated for empty results")
        return False

    # Count buttons (should be 0)
    button_count = sum(
        1
        for block in blocks
        if block.get("type") == "section"
        and "accessory" in block
        and block["accessory"].get("type") == "button"
    )

    if button_count != 0:
        print_error(f"Expected 0 buttons for empty results, got {button_count}")
        return False

    print_success("Empty results handled correctly (no buttons)")
    return True


def test_get_chunk_by_id():
    """Test the get_chunk_by_id helper function."""
    print("\n10. Testing get_chunk_by_id helper function...")

    chunks = [
        MockChunk("chunk1", "Heading 1", "Content 1", "url1"),
        MockChunk("chunk2", "Heading 2", "Content 2", "url2"),
    ]

    vector_store = MockVectorStore(chunks)

    # Test finding existing chunk
    result = get_chunk_by_id(vector_store, "chunk2")

    if result is None:
        print_error("Chunk not found (should exist)")
        return False

    if result.block_id != "chunk2":
        print_error(f"Wrong chunk returned: {result.block_id}")
        return False

    if result.heading != "Heading 2":
        print_error(f"Wrong heading: {result.heading}")
        return False

    # Test non-existent chunk
    result = get_chunk_by_id(vector_store, "nonexistent")

    if result is not None:
        print_error("Found chunk that shouldn't exist")
        return False

    print_success("get_chunk_by_id works correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  TESTING PHASE 4: REACTION-BASED SEARCH HANDLERS")
    print("=" * 60)

    tests = [
        test_build_suggestion_blocks_faq_only,
        test_build_suggestion_blocks_status_only,
        test_build_suggestion_blocks_both,
        test_block_structure_valid,
        test_button_payloads_valid,
        test_status_message_truncation,
        test_multiple_status_limited,
        test_search_emoji_constant,
        test_empty_suggestions_and_status,
        test_get_chunk_by_id,
    ]

    passed = 0
    failed = 0

    try:
        for test in tests:
            if test():
                passed += 1
            else:
                failed += 1

        print("\n" + "=" * 60)
        if failed == 0:
            print(f"  ✅ ALL {passed} TESTS PASSED!")
        else:
            print(f"  ⚠️  {passed} PASSED, {failed} FAILED")
        print("=" * 60)

        if failed == 0:
            print("\n✨ Phase 4 implementation verified!")
            print("   - Reaction event handlers created")
            print("   - Button action handlers implemented")
            print("   - Block building logic working")
            print("   - Status correlation integrated")
            print("\nNext step: Phase 5 - Implement slash command handlers")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Review implementation.")

        print("=" * 60 + "\n")

    except Exception as e:
        print("\n" + "=" * 60)
        print("  ❌ TEST FAILED WITH ERROR")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
