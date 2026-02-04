"""Heading-based chunking of Notion pages."""

from typing import Dict, Any, List

from ..types import FAQChunk
from .parser import (
    extract_text_from_block,
    is_heading,
    get_page_title,
)


def build_notion_url(page_id: str, block_id: str) -> str:
    """Build a Notion URL pointing to a specific block."""
    # Remove hyphens from IDs for URL
    clean_page_id = page_id.replace("-", "")
    clean_block_id = block_id.replace("-", "")
    return f"https://www.notion.so/{clean_page_id}#{clean_block_id}"


def chunk_by_headings(
    page: Dict[str, Any], blocks: List[Dict[str, Any]], page_id: str
) -> List[FAQChunk]:
    """Split page content into chunks based on headings.

    Each chunk contains:
    - heading text
    - all content until the next heading
    - block ID of the heading
    - Notion URL pointing to the heading

    If page has no headings, returns a single chunk with page title.
    """
    chunks = []
    current_heading = None
    current_heading_id = None
    current_content = []

    for block in blocks:
        # Skip blocks we can't extract text from
        text = extract_text_from_block(block)
        if text is None:
            continue

        # Check if this is a heading
        if is_heading(block):
            # Save previous chunk if exists
            if current_heading is not None:
                content_text = "\n".join(current_content).strip()
                if content_text:  # Only add non-empty chunks
                    chunks.append(
                        FAQChunk(
                            heading=current_heading,
                            content=content_text,
                            block_id=current_heading_id,
                            notion_url=build_notion_url(page_id, current_heading_id),
                        )
                    )

            # Start new chunk
            current_heading = text.strip()
            current_heading_id = block["id"]
            current_content = []
        else:
            # Add content to current chunk
            if text.strip():
                current_content.append(text.strip())

    # Save final chunk
    if current_heading is not None:
        content_text = "\n".join(current_content).strip()
        if content_text:
            chunks.append(
                FAQChunk(
                    heading=current_heading,
                    content=content_text,
                    block_id=current_heading_id,
                    notion_url=build_notion_url(page_id, current_heading_id),
                )
            )

    # Edge case: page with no headings
    if not chunks:
        # Collect all text content
        all_content = []
        for block in blocks:
            text = extract_text_from_block(block)
            if text and text.strip():
                all_content.append(text.strip())

        if all_content:
            page_title = get_page_title(page)
            # Use page ID as block ID since there are no headings
            chunks.append(
                FAQChunk(
                    heading=page_title,
                    content="\n".join(all_content),
                    block_id=page_id,
                    notion_url=f"https://www.notion.so/{page_id.replace('-', '')}",
                )
            )

    return chunks
