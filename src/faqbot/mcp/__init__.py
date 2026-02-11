"""
MCP (Model Context Protocol) integration module.

This module provides MCP-based integrations for external services,
starting with Notion OAuth authentication and token management.
"""

from .token_manager import NotionTokenManager

__all__ = ["NotionTokenManager"]
