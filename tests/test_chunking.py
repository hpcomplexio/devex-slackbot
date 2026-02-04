"""Tests for Notion chunking logic."""

import pytest
from src.faqbot.notion.chunking import chunk_by_headings, build_notion_url


def test_chunk_by_headings():
    """Test heading-based chunking."""
    page = {"properties": {"title": {"type": "title", "title": [{"plain_text": "FAQ"}]}}}

    blocks = [
        {
            "id": "block1",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"plain_text": "Section 1"}]},
        },
        {
            "id": "block2",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Content for section 1"}]},
        },
        {
            "id": "block3",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Section 2"}]},
        },
        {
            "id": "block4",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Content for section 2"}]},
        },
    ]

    chunks = chunk_by_headings(page, blocks, "page123")

    assert len(chunks) == 2
    assert chunks[0].heading == "Section 1"
    assert chunks[0].content == "Content for section 1"
    assert chunks[0].block_id == "block1"
    assert chunks[1].heading == "Section 2"
    assert chunks[1].content == "Content for section 2"
    assert chunks[1].block_id == "block3"


def test_chunk_by_headings_no_headings():
    """Test chunking page with no headings."""
    page = {"properties": {"title": {"type": "title", "title": [{"plain_text": "FAQ"}]}}}

    blocks = [
        {
            "id": "block1",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Some content"}]},
        },
        {
            "id": "block2",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "More content"}]},
        },
    ]

    chunks = chunk_by_headings(page, blocks, "page123")

    assert len(chunks) == 1
    assert chunks[0].heading == "FAQ"
    assert "Some content" in chunks[0].content
    assert "More content" in chunks[0].content


def test_build_notion_url():
    """Test Notion URL building."""
    url = build_notion_url("page-123-456", "block-789-abc")
    assert url == "https://www.notion.so/page123456#block789abc"
