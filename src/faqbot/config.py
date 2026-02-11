"""Configuration loader with validation."""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # Required fields (no defaults)
    slack_bot_token: str
    slack_app_token: str
    slack_allowed_channels: List[str]
    anthropic_api_key: str

    # FAQ Source (with defaults)
    faq_source: str = "markdown"  # Options: "markdown" or "notion"
    faq_file_path: Optional[str] = None  # For markdown source

    # Notion OAuth (only required if faq_source == "notion")
    notion_oauth_client_id: Optional[str] = None
    notion_oauth_client_secret: Optional[str] = None
    notion_oauth_refresh_token: Optional[str] = None
    notion_faq_page_id: Optional[str] = None

    # Retrieval (with defaults)
    top_k: int = 5
    min_similarity: float = 0.70
    min_gap: float = 0.15
    faq_sync_interval: int = 30  # minutes

    # Suggestion features (new in Phase 4-5)
    reaction_search_enabled: bool = True
    slash_command_enabled: bool = True
    suggestion_min_similarity: float = 0.50  # Lower than answer threshold
    suggestion_top_k: int = 5

    # Status monitoring (new in Phase 1)
    status_monitoring_enabled: bool = True
    slack_status_channels: List[str] = field(default_factory=list)  # Channels to monitor
    status_cache_ttl_hours: int = 24  # How long to keep status updates

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        # Required variables
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        slack_app_token = os.getenv("SLACK_APP_TOKEN")
        slack_allowed_channels = os.getenv("SLACK_ALLOWED_CHANNELS")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # FAQ source configuration
        faq_source = os.getenv("FAQ_SOURCE", "markdown").lower()
        faq_file_path = os.getenv("FAQ_FILE_PATH")
        notion_oauth_client_id = os.getenv("NOTION_OAUTH_CLIENT_ID")
        notion_oauth_client_secret = os.getenv("NOTION_OAUTH_CLIENT_SECRET")
        notion_oauth_refresh_token = os.getenv("NOTION_OAUTH_REFRESH_TOKEN")
        notion_faq_page_id = os.getenv("NOTION_FAQ_PAGE_ID")

        # Validate required
        missing = []
        if not slack_bot_token:
            missing.append("SLACK_BOT_TOKEN")
        if not slack_app_token:
            missing.append("SLACK_APP_TOKEN")
        if not slack_allowed_channels:
            missing.append("SLACK_ALLOWED_CHANNELS")
        if not anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")

        # Validate FAQ source-specific requirements
        if faq_source not in ["markdown", "notion"]:
            raise ValueError(
                f"Invalid FAQ_SOURCE: {faq_source}. Must be 'markdown' or 'notion'"
            )

        if faq_source == "markdown":
            if not faq_file_path:
                missing.append("FAQ_FILE_PATH (required when FAQ_SOURCE=markdown)")
        elif faq_source == "notion":
            if not notion_oauth_client_id:
                missing.append("NOTION_OAUTH_CLIENT_ID (required when FAQ_SOURCE=notion)")
            if not notion_oauth_client_secret:
                missing.append("NOTION_OAUTH_CLIENT_SECRET (required when FAQ_SOURCE=notion)")
            if not notion_oauth_refresh_token:
                missing.append("NOTION_OAUTH_REFRESH_TOKEN (required when FAQ_SOURCE=notion)")
            if not notion_faq_page_id:
                missing.append("NOTION_FAQ_PAGE_ID (required when FAQ_SOURCE=notion)")

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

        # Suggestion features (new)
        reaction_search_enabled = os.getenv("REACTION_SEARCH_ENABLED", "true").lower() == "true"
        slash_command_enabled = os.getenv("SLASH_COMMAND_ENABLED", "true").lower() == "true"
        suggestion_min_similarity = float(os.getenv("SUGGESTION_MIN_SIMILARITY", "0.50"))
        suggestion_top_k = int(os.getenv("SUGGESTION_TOP_K", "5"))

        # Status monitoring (new)
        status_monitoring_enabled = os.getenv("STATUS_MONITORING_ENABLED", "true").lower() == "true"
        slack_status_channels_str = os.getenv("SLACK_STATUS_CHANNELS", "")
        status_channels = (
            [ch.strip() for ch in slack_status_channels_str.split(",") if ch.strip()]
            if slack_status_channels_str
            else []
        )
        status_cache_ttl_hours = int(os.getenv("STATUS_CACHE_TTL_HOURS", "24"))

        return cls(
            slack_bot_token=slack_bot_token,
            slack_app_token=slack_app_token,
            slack_allowed_channels=channels,
            faq_source=faq_source,
            faq_file_path=faq_file_path,
            notion_oauth_client_id=notion_oauth_client_id,
            notion_oauth_client_secret=notion_oauth_client_secret,
            notion_oauth_refresh_token=notion_oauth_refresh_token,
            notion_faq_page_id=notion_faq_page_id,
            anthropic_api_key=anthropic_api_key,
            top_k=top_k,
            min_similarity=min_similarity,
            min_gap=min_gap,
            faq_sync_interval=faq_sync_interval,
            reaction_search_enabled=reaction_search_enabled,
            slash_command_enabled=slash_command_enabled,
            suggestion_min_similarity=suggestion_min_similarity,
            suggestion_top_k=suggestion_top_k,
            status_monitoring_enabled=status_monitoring_enabled,
            slack_status_channels=status_channels,
            status_cache_ttl_hours=status_cache_ttl_hours,
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

        # Validate suggestion features
        if not 0 <= self.suggestion_min_similarity <= 1:
            raise ValueError("SUGGESTION_MIN_SIMILARITY must be between 0 and 1")
        if self.suggestion_top_k < 1:
            raise ValueError("SUGGESTION_TOP_K must be >= 1")

        # Validate status monitoring
        if self.status_cache_ttl_hours < 1:
            raise ValueError("STATUS_CACHE_TTL_HOURS must be >= 1")
