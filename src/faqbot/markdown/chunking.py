"""Chunking logic for markdown content."""
from typing import Dict, List
from ..types import FAQChunk


def chunk_markdown(blocks: List[Dict], file_path: str) -> List[FAQChunk]:
    """Convert markdown blocks to FAQChunk objects.

    Splits markdown by headings similar to the Notion chunking logic.
    Each chunk contains a heading and all content until the next heading.

    Args:
        blocks: List of parsed markdown blocks from parse_markdown_blocks()
        file_path: Path to the source markdown file (used for URLs)

    Returns:
        List of FAQChunk objects
    """
    chunks = []
    current_heading = None
    current_heading_line = None
    current_content = []

    for block in blocks:
        if block['type'] == 'heading':
            # Save previous chunk if it exists
            if current_heading and current_content:
                content_text = '\n'.join(current_content).strip()
                if content_text:  # Only add non-empty chunks
                    chunks.append(FAQChunk(
                        heading=current_heading,
                        content=content_text,
                        block_id=f"line_{current_heading_line}",
                        notion_url=f"file://{file_path}#L{current_heading_line}"
                    ))

            # Start new chunk
            current_heading = block['text']
            current_heading_line = block['line_number']
            current_content = []

        elif block['type'] == 'text':
            # Add content to current chunk
            current_content.append(block['text'])

    # Don't forget the last chunk
    if current_heading and current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text:
            chunks.append(FAQChunk(
                heading=current_heading,
                content=content_text,
                block_id=f"line_{current_heading_line}",
                notion_url=f"file://{file_path}#L{current_heading_line}"
            ))

    return chunks
