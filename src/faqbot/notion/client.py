"""Notion API client wrapper."""

import time
from typing import Dict, List, Any
from notion_client import Client
from notion_client.errors import APIResponseError


class NotionClient:
    """Wrapper for Notion API with rate limiting and error handling."""

    def __init__(self, api_key: str):
        """Initialize Notion client."""
        self.client = Client(auth=api_key)
        self._last_request_time = 0
        self._min_interval = 1 / 3  # 3 requests per second

    def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve page metadata."""
        self._rate_limit()
        try:
            return self.client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            raise RuntimeError(f"Failed to retrieve page {page_id}: {e}")

    def get_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """Retrieve all blocks from a page with pagination."""
        blocks = []
        start_cursor = None

        while True:
            self._rate_limit()
            try:
                response = self.client.blocks.children.list(
                    block_id=block_id, start_cursor=start_cursor
                )
                blocks.extend(response.get("results", []))

                if not response.get("has_more", False):
                    break

                start_cursor = response.get("next_cursor")
            except APIResponseError as e:
                raise RuntimeError(f"Failed to retrieve blocks for {block_id}: {e}")

        return blocks

    def get_page_content(self, page_id: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Retrieve page metadata and all blocks."""
        page = self.get_page(page_id)
        blocks = self.get_blocks(page_id)
        return page, blocks
