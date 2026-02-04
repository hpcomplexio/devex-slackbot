#!/usr/bin/env python3
"""Test script for markdown FAQ source."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.faqbot.markdown.reader import read_markdown_file, parse_markdown_blocks
from src.faqbot.markdown.chunking import chunk_markdown


def main():
    """Test markdown reading and chunking."""
    print("=" * 70)
    print("Testing Markdown FAQ Source")
    print("=" * 70)

    # Use the sample FAQ file
    faq_path = Path(__file__).parent.parent / "faq.md"

    if not faq_path.exists():
        print(f"❌ Error: FAQ file not found at {faq_path}")
        return 1

    print(f"\n📄 Reading: {faq_path}")

    # Step 1: Read file
    try:
        content = read_markdown_file(str(faq_path))
        print(f"✓ File read successfully ({len(content)} characters)")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return 1

    # Step 2: Parse blocks
    try:
        blocks = parse_markdown_blocks(content)
        headings = [b for b in blocks if b['type'] == 'heading']
        print(f"✓ Parsed {len(blocks)} blocks ({len(headings)} headings)")
    except Exception as e:
        print(f"❌ Error parsing blocks: {e}")
        return 1

    # Step 3: Create chunks
    try:
        chunks = chunk_markdown(blocks, str(faq_path))
        print(f"✓ Created {len(chunks)} FAQ chunks")
    except Exception as e:
        print(f"❌ Error creating chunks: {e}")
        return 1

    # Display results
    print("\n" + "=" * 70)
    print("FAQ Chunks Preview")
    print("=" * 70)

    for i, chunk in enumerate(chunks, 1):
        print(f"\n{i}. {chunk.heading}")
        print("-" * 70)
        # Truncate content for display
        content_preview = chunk.content[:150]
        if len(chunk.content) > 150:
            content_preview += "..."
        print(content_preview)
        print(f"\nBlock ID: {chunk.block_id}")
        print(f"URL: {chunk.notion_url}")

    print("\n" + "=" * 70)
    print(f"✓ Success! Found {len(chunks)} FAQ sections")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
