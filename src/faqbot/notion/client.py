"""Notion API client with OAuth authentication."""

import asyncio
import time
import json
import urllib.request as req
import urllib.error
from typing import Dict, List, Any
from ..mcp.token_manager import NotionTokenManager


class NotionClient:
    """
    Notion API client using OAuth authentication.

    This client uses OAuth tokens managed by NotionTokenManager instead of API keys,
    aligning with the MCP-based authentication approach used in cpx-claude-agents.
    """

    NOTION_API_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, token_manager: NotionTokenManager):
        """
        Initialize Notion client with OAuth token manager.

        Args:
            token_manager: Token manager for OAuth authentication
        """
        self.token_manager = token_manager
        self._last_request_time = 0
        self._min_interval = 1 / 3  # 3 requests per second

    def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        """
        Make authenticated request to Notion API.

        Args:
            endpoint: API endpoint (e.g., "/pages/{page_id}")
            method: HTTP method
            data: Request body data (for POST/PATCH)

        Returns:
            API response as dictionary

        Raises:
            RuntimeError: If request fails
        """
        # Get fresh OAuth token
        access_token = self.token_manager.get_access_token()

        # Build request
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": self.NOTION_API_VERSION,
            "Content-Type": "application/json"
        }

        request_data = json.dumps(data).encode() if data else None
        request = req.Request(url, data=request_data, method=method, headers=headers)

        try:
            response = req.urlopen(request)
            return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error body"
            raise RuntimeError(
                f"Notion API request failed: {e.code} {e.reason}\n{error_body}"
            )
        except Exception as e:
            raise RuntimeError(f"Notion API request failed: {e}")

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieve page metadata.

        Args:
            page_id: Notion page ID

        Returns:
            Page metadata dictionary
        """
        self._rate_limit()
        return self._make_request(f"/pages/{page_id}")

    def get_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all blocks from a page with pagination.

        Args:
            block_id: Notion block/page ID

        Returns:
            List of block dictionaries
        """
        blocks = []
        start_cursor = None

        while True:
            self._rate_limit()

            # Build endpoint with pagination
            endpoint = f"/blocks/{block_id}/children"
            if start_cursor:
                endpoint += f"?start_cursor={start_cursor}"

            response = self._make_request(endpoint)
            blocks.extend(response.get("results", []))

            if not response.get("has_more", False):
                break

            start_cursor = response.get("next_cursor")

        return blocks

    def get_page_content(self, page_id: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Retrieve page metadata and all blocks.

        Args:
            page_id: Notion page ID

        Returns:
            Tuple of (page_metadata, blocks_list)
        """
        page = self.get_page(page_id)
        blocks = self.get_blocks(page_id)
        return page, blocks

    # Async variants for future compatibility
    async def get_page_async(self, page_id: str) -> Dict[str, Any]:
        """Async version of get_page."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_page, page_id)

    async def get_blocks_async(self, block_id: str) -> List[Dict[str, Any]]:
        """Async version of get_blocks."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_blocks, block_id)

    async def get_page_content_async(
        self, page_id: str
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Async version of get_page_content."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_page_content, page_id)
