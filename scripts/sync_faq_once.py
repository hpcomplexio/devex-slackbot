"""Test script to fetch and chunk FAQ content from Notion."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from faqbot.config import Config
from faqbot.notion.client import NotionClient
from faqbot.notion.chunking import chunk_by_headings


def main():
    """Fetch and print FAQ chunks."""
    try:
        # Load config
        print("Loading configuration...")
        config = Config.from_env()
        config.validate()
        print(f"✓ Config loaded. FAQ Page ID: {config.notion_faq_page_id}")

        # Initialize Notion client
        print("\nInitializing Notion client...")
        client = NotionClient(config.notion_api_key)
        print("✓ Client initialized")

        # Fetch page content
        print("\nFetching page content...")
        page, blocks = client.get_page_content(config.notion_faq_page_id)
        print(f"✓ Retrieved {len(blocks)} blocks")

        # Chunk content
        print("\nChunking content by headings...")
        chunks = chunk_by_headings(page, blocks, config.notion_faq_page_id)
        print(f"✓ Created {len(chunks)} chunks")

        # Print chunks
        print("\n" + "=" * 80)
        print("CHUNKS")
        print("=" * 80)
        for i, chunk in enumerate(chunks, 1):
            print(f"\n[Chunk {i}]")
            print(f"Heading: {chunk.heading}")
            print(f"Content: {chunk.content[:200]}{'...' if len(chunk.content) > 200 else ''}")
            print(f"URL: {chunk.notion_url}")
            print("-" * 80)

        print(f"\n✓ Successfully processed {len(chunks)} chunks")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
