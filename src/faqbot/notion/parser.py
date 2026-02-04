"""Text extraction from Notion blocks."""

from typing import Dict, Any, Optional


def extract_rich_text(rich_text_array: list) -> str:
    """Extract plain text from Notion rich_text array."""
    if not rich_text_array:
        return ""
    return "".join(item.get("plain_text", "") for item in rich_text_array)


def extract_text_from_block(block: Dict[str, Any]) -> Optional[str]:
    """Extract text content from a Notion block.

    Returns None for unsupported block types.
    """
    block_type = block.get("type")
    block_data = block.get(block_type, {})

    # Heading blocks
    if block_type in ["heading_1", "heading_2", "heading_3"]:
        return extract_rich_text(block_data.get("rich_text", []))

    # Paragraph blocks
    if block_type == "paragraph":
        return extract_rich_text(block_data.get("rich_text", []))

    # Bulleted list items
    if block_type == "bulleted_list_item":
        return extract_rich_text(block_data.get("rich_text", []))

    # Numbered list items
    if block_type == "numbered_list_item":
        return extract_rich_text(block_data.get("rich_text", []))

    # To-do items
    if block_type == "to_do":
        return extract_rich_text(block_data.get("rich_text", []))

    # Toggle blocks
    if block_type == "toggle":
        return extract_rich_text(block_data.get("rich_text", []))

    # Quote blocks
    if block_type == "quote":
        return extract_rich_text(block_data.get("rich_text", []))

    # Callout blocks
    if block_type == "callout":
        return extract_rich_text(block_data.get("rich_text", []))

    # Code blocks
    if block_type == "code":
        return extract_rich_text(block_data.get("rich_text", []))

    # Unsupported types: images, embeds, files, etc.
    return None


def is_heading(block: Dict[str, Any]) -> bool:
    """Check if block is a heading."""
    return block.get("type") in ["heading_1", "heading_2", "heading_3"]


def get_heading_level(block: Dict[str, Any]) -> Optional[int]:
    """Get heading level (1, 2, or 3) or None if not a heading."""
    block_type = block.get("type")
    if block_type == "heading_1":
        return 1
    elif block_type == "heading_2":
        return 2
    elif block_type == "heading_3":
        return 3
    return None


def get_page_title(page: Dict[str, Any]) -> str:
    """Extract page title from page metadata."""
    properties = page.get("properties", {})

    # Try to find title property
    for prop_name, prop_data in properties.items():
        if prop_data.get("type") == "title":
            title_array = prop_data.get("title", [])
            if title_array:
                return extract_rich_text(title_array)

    return "Untitled"
