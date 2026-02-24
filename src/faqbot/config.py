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

    # Notion (only required if faq_source == "notion")
    # Option 1: Simple API key (recommended)
    notion_api_key: Optional[str] = None
    notion_faq_page_id: Optional[str] = None

    # Option 2: OAuth (legacy)
    notion_oauth_client_id: Optional[str] = None
    notion_oauth_client_secret: Optional[str] = None
    notion_oauth_refresh_token: Optional[str] = None

    # Retrieval (with defaults)
    top_k: int = 5
    min_similarity: float = 0.70
    min_gap: float = 0.15
    min_ratio: float = 1.05  # Default ratio threshold (5% better than second)
    faq_sync_interval: int = 30  # minutes

    # Mode-specific ratio thresholds (used when ratio-based confidence is enabled)
    semantic_min_ratio: float = 1.10  # Higher for semantic (wider score spread)
    hybrid_min_ratio: float = 1.02  # Lower for RRF (tight score clustering)
    reranking_min_ratio: float = 1.05  # Medium for cross-encoder

    # Hybrid search (new)
    hybrid_search_enabled: bool = False
    hybrid_semantic_top_k: int = 20
    hybrid_bm25_top_k: int = 20

    # Reranking (new)
    reranking_enabled: bool = False
    reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranking_retrieval_top_k: int = 20
    reranking_top_k: int = 5

    # Suggestion features (new in Phase 4-5)
    reaction_search_enabled: bool = True
    slash_command_enabled: bool = True
    suggestion_min_similarity: float = 0.50  # Lower than answer threshold
    suggestion_top_k: int = 5

    # Status monitoring (new in Phase 1)
    status_monitoring_enabled: bool = True
    slack_status_channels: List[str] = field(default_factory=list)  # Channels to monitor
    status_cache_ttl_hours: int = 24  # How long to keep status updates

    # Interaction logging (new)
    interaction_log_enabled: bool = True
    interaction_log_path: str = "./data/interactions.db"

    # Read receipts / mention tracking (new)
    mention_tracking_enabled: bool = True
    receipt_ttl_hours: int = 168  # 7 days

    # Admin users (comma-separated Slack user IDs)
    slack_admin_user_ids: str = ""

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
        notion_api_key = os.getenv("NOTION_API_KEY")
        notion_faq_page_id = os.getenv("NOTION_FAQ_PAGE_ID")
        notion_oauth_client_id = os.getenv("NOTION_OAUTH_CLIENT_ID")
        notion_oauth_client_secret = os.getenv("NOTION_OAUTH_CLIENT_SECRET")
        notion_oauth_refresh_token = os.getenv("NOTION_OAUTH_REFRESH_TOKEN")

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
            if not notion_faq_page_id:
                missing.append("NOTION_FAQ_PAGE_ID (required when FAQ_SOURCE=notion)")
            # Support both API key and OAuth, but require at least one
            has_api_key = bool(notion_api_key)
            has_oauth = bool(notion_oauth_client_id and notion_oauth_client_secret and notion_oauth_refresh_token)
            if not has_api_key and not has_oauth:
                missing.append("NOTION_API_KEY or OAuth credentials (required when FAQ_SOURCE=notion)")

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
        min_ratio = float(os.getenv("MIN_RATIO", "1.05"))
        faq_sync_interval = int(os.getenv("FAQ_SYNC_INTERVAL", "30"))

        # Mode-specific ratio thresholds
        semantic_min_ratio = float(os.getenv("SEMANTIC_MIN_RATIO", "1.10"))
        hybrid_min_ratio = float(os.getenv("HYBRID_MIN_RATIO", "1.02"))
        reranking_min_ratio = float(os.getenv("RERANKING_MIN_RATIO", "1.05"))

        # Suggestion features (new)
        reaction_search_enabled = os.getenv("REACTION_SEARCH_ENABLED", "true").lower() == "true"
        slash_command_enabled = os.getenv("SLASH_COMMAND_ENABLED", "true").lower() == "true"
        suggestion_min_similarity = float(os.getenv("SUGGESTION_MIN_SIMILARITY", "0.50"))
        suggestion_top_k = int(os.getenv("SUGGESTION_TOP_K", "5"))

        # Hybrid search (new)
        hybrid_search_enabled = os.getenv("HYBRID_SEARCH_ENABLED", "false").lower() == "true"
        hybrid_semantic_top_k = int(os.getenv("HYBRID_SEMANTIC_TOP_K", "20"))
        hybrid_bm25_top_k = int(os.getenv("HYBRID_BM25_TOP_K", "20"))

        # Reranking (new)
        reranking_enabled = os.getenv("RERANKING_ENABLED", "false").lower() == "true"
        reranking_model = os.getenv("RERANKING_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        reranking_retrieval_top_k = int(os.getenv("RERANKING_RETRIEVAL_TOP_K", "20"))
        reranking_top_k = int(os.getenv("RERANKING_TOP_K", "5"))

        # Status monitoring (new)
        status_monitoring_enabled = os.getenv("STATUS_MONITORING_ENABLED", "true").lower() == "true"
        slack_status_channels_str = os.getenv("SLACK_STATUS_CHANNELS", "")
        status_channels = (
            [ch.strip() for ch in slack_status_channels_str.split(",") if ch.strip()]
            if slack_status_channels_str
            else []
        )
        status_cache_ttl_hours = int(os.getenv("STATUS_CACHE_TTL_HOURS", "24"))

        # Interaction logging (new)
        interaction_log_enabled = os.getenv("INTERACTION_LOG_ENABLED", "true").lower() == "true"
        interaction_log_path = os.getenv("INTERACTION_LOG_PATH", "./data/interactions.db")

        # Read receipts / mention tracking (new)
        mention_tracking_enabled = os.getenv("MENTION_TRACKING_ENABLED", "true").lower() == "true"
        receipt_ttl_hours = int(os.getenv("RECEIPT_TTL_HOURS", "168"))

        # Admin users (new)
        slack_admin_user_ids = os.getenv("SLACK_ADMIN_USER_IDS", "")

        return cls(
            slack_bot_token=slack_bot_token,
            slack_app_token=slack_app_token,
            slack_allowed_channels=channels,
            faq_source=faq_source,
            faq_file_path=faq_file_path,
            notion_api_key=notion_api_key,
            notion_faq_page_id=notion_faq_page_id,
            notion_oauth_client_id=notion_oauth_client_id,
            notion_oauth_client_secret=notion_oauth_client_secret,
            notion_oauth_refresh_token=notion_oauth_refresh_token,
            anthropic_api_key=anthropic_api_key,
            top_k=top_k,
            min_similarity=min_similarity,
            min_gap=min_gap,
            min_ratio=min_ratio,
            faq_sync_interval=faq_sync_interval,
            semantic_min_ratio=semantic_min_ratio,
            hybrid_min_ratio=hybrid_min_ratio,
            reranking_min_ratio=reranking_min_ratio,
            reaction_search_enabled=reaction_search_enabled,
            slash_command_enabled=slash_command_enabled,
            suggestion_min_similarity=suggestion_min_similarity,
            suggestion_top_k=suggestion_top_k,
            hybrid_search_enabled=hybrid_search_enabled,
            hybrid_semantic_top_k=hybrid_semantic_top_k,
            hybrid_bm25_top_k=hybrid_bm25_top_k,
            reranking_enabled=reranking_enabled,
            reranking_model=reranking_model,
            reranking_retrieval_top_k=reranking_retrieval_top_k,
            reranking_top_k=reranking_top_k,
            status_monitoring_enabled=status_monitoring_enabled,
            slack_status_channels=status_channels,
            status_cache_ttl_hours=status_cache_ttl_hours,
            interaction_log_enabled=interaction_log_enabled,
            interaction_log_path=interaction_log_path,
            mention_tracking_enabled=mention_tracking_enabled,
            receipt_ttl_hours=receipt_ttl_hours,
            slack_admin_user_ids=slack_admin_user_ids,
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if self.top_k < 1:
            raise ValueError("TOP_K must be >= 1")
        if not 0 <= self.min_similarity <= 1:
            raise ValueError("MIN_SIMILARITY must be between 0 and 1")
        if not 0 <= self.min_gap <= 1:
            raise ValueError("MIN_GAP must be between 0 and 1")
        if self.min_ratio < 1:
            raise ValueError("MIN_RATIO must be >= 1")
        if self.semantic_min_ratio < 1:
            raise ValueError("SEMANTIC_MIN_RATIO must be >= 1")
        if self.hybrid_min_ratio < 1:
            raise ValueError("HYBRID_MIN_RATIO must be >= 1")
        if self.reranking_min_ratio < 1:
            raise ValueError("RERANKING_MIN_RATIO must be >= 1")
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

        # Validate read receipts
        if self.receipt_ttl_hours < 1:
            raise ValueError("RECEIPT_TTL_HOURS must be >= 1")

        # Validate hybrid search
        if self.hybrid_semantic_top_k < 1:
            raise ValueError("HYBRID_SEMANTIC_TOP_K must be >= 1")
        if self.hybrid_bm25_top_k < 1:
            raise ValueError("HYBRID_BM25_TOP_K must be >= 1")

        # Validate reranking
        if self.reranking_retrieval_top_k < 1:
            raise ValueError("RERANKING_RETRIEVAL_TOP_K must be >= 1")
        if self.reranking_top_k < 1:
            raise ValueError("RERANKING_TOP_K must be >= 1")
        if not self.reranking_model:
            raise ValueError("RERANKING_MODEL must not be empty")
