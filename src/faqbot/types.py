"""Shared types for the FAQ bot."""

from dataclasses import dataclass


@dataclass
class FAQChunk:
    """A chunk of FAQ content.

    Represents a section of FAQ content with a heading, content text,
    unique identifier, and source URL. This is the core data structure
    that flows through the entire pipeline regardless of FAQ source.
    """

    heading: str       # Section heading/title
    content: str       # Main text content
    block_id: str      # Unique identifier for this chunk
    notion_url: str    # Source URL (can be any URL, not just Notion)

    def __str__(self) -> str:
        """String representation for debugging."""
        content_preview = (
            self.content[:100] + "..." if len(self.content) > 100 else self.content
        )
        return f"FAQChunk(heading='{self.heading}', content='{content_preview}')"
