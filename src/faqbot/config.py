"""Configuration loader with validation."""

import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # Slack
    slack_bot_token: str
    slack_app_token: str
    slack_allowed_channels: List[str]

    # Notion
    notion_api_key: str
    notion_faq_page_id: str

    # Claude
    anthropic_api_key: str

    # Retrieval
    top_k: int = 5
    min_similarity: float = 0.70
    min_gap: float = 0.15
    faq_sync_interval: int = 30  # minutes

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        # Required variables
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        slack_app_token = os.getenv("SLACK_APP_TOKEN")
        slack_allowed_channels = os.getenv("SLACK_ALLOWED_CHANNELS")
        notion_api_key = os.getenv("NOTION_API_KEY")
        notion_faq_page_id = os.getenv("NOTION_FAQ_PAGE_ID")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Validate required
        missing = []
        if not slack_bot_token:
            missing.append("SLACK_BOT_TOKEN")
        if not slack_app_token:
            missing.append("SLACK_APP_TOKEN")
        if not slack_allowed_channels:
            missing.append("SLACK_ALLOWED_CHANNELS")
        if not notion_api_key:
            missing.append("NOTION_API_KEY")
        if not notion_faq_page_id:
            missing.append("NOTION_FAQ_PAGE_ID")
        if not anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # Parse allowed channels
        channels = [ch.strip() for ch in slack_allowed_channels.split(",")]

        # Optional variables with defaults
        top_k = int(os.getenv("TOP_K", "5"))
        min_similarity = float(os.getenv("MIN_SIMILARITY", "0.70"))
        min_gap = float(os.getenv("MIN_GAP", "0.15"))
        faq_sync_interval = int(os.getenv("FAQ_SYNC_INTERVAL", "30"))

        return cls(
            slack_bot_token=slack_bot_token,
            slack_app_token=slack_app_token,
            slack_allowed_channels=channels,
            notion_api_key=notion_api_key,
            notion_faq_page_id=notion_faq_page_id,
            anthropic_api_key=anthropic_api_key,
            top_k=top_k,
            min_similarity=min_similarity,
            min_gap=min_gap,
            faq_sync_interval=faq_sync_interval,
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if self.top_k < 1:
            raise ValueError("TOP_K must be >= 1")
        if not 0 <= self.min_similarity <= 1:
            raise ValueError("MIN_SIMILARITY must be between 0 and 1")
        if not 0 <= self.min_gap <= 1:
            raise ValueError("MIN_GAP must be between 0 and 1")
        if self.faq_sync_interval < 1:
            raise ValueError("FAQ_SYNC_INTERVAL must be >= 1")
