"""Slack event handlers for monitoring status/announcement channels."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from slack_bolt import App

from .cache import INCIDENT_KEYWORDS, StatusUpdate, StatusUpdateCache


def setup_status_monitoring(
    app: App,
    status_cache: StatusUpdateCache,
    status_channels: List[str],
    logger: logging.Logger,
) -> None:
    """Set up monitoring of status/announcement channels.

    Args:
        app: Slack Bolt app instance
        status_cache: The status update cache to populate
        status_channels: List of channel IDs to monitor
        logger: Logger instance for logging events
    """

    @app.event("message")
    def handle_status_message(event: Dict[str, Any], client: Any) -> None:
        """Monitor status channels for incident announcements.

        This handler runs on ALL message events but filters to only
        process messages in configured status channels.

        Args:
            event: Slack message event
            client: Slack client for API calls
        """
        channel = event.get("channel")

        # Only monitor configured status channels
        if channel not in status_channels:
            return

        # Skip bot messages and edits
        if event.get("bot_id") or event.get("subtype") == "message_changed":
            return

        text = event.get("text", "")
        message_ts = event.get("ts")

        if not text or not message_ts:
            return

        # Keyword filter (case-insensitive)
        text_lower = text.lower()
        matched_keywords = [kw for kw in INCIDENT_KEYWORDS if kw in text_lower]

        if not matched_keywords:
            # Not an incident-related message
            return

        try:
            # Get permalink for linking
            permalink_response = client.chat_getPermalink(
                channel=channel, message_ts=message_ts
            )
            message_link = permalink_response.get("permalink", "")

            # Add to cache
            status_update = StatusUpdate(
                message_ts=message_ts,
                channel_id=channel,
                message_text=text,
                message_link=message_link,
                posted_at=datetime.now(),
                keywords_matched=matched_keywords,
                embedding=None,  # Lazy-loaded on first search
            )

            status_cache.add_update(status_update)

            logger.info(
                f"Status update cached | channel={channel} | "
                f"keywords={matched_keywords} | text={text[:100]}"
            )

        except Exception as e:
            logger.error(f"Error caching status update | error={e}")
