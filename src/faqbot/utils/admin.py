"""Admin utilities for permission checking and parsing."""

import re
from typing import List, Tuple

from faqbot.config import Config


def is_admin(user_id: str, config: Config) -> bool:
    """Check if user is configured as admin.

    Args:
        user_id: Slack user ID (e.g., "U123456789")
        config: Config object with slack_admin_user_ids

    Returns:
        True if user is in admin list, False otherwise
    """
    if not config.slack_admin_user_ids:
        return False
    admin_ids = [uid.strip() for uid in config.slack_admin_user_ids.split(",")]
    return user_id in admin_ids


def parse_mentions_and_question(text: str) -> Tuple[List[str], str]:
    """Extract user mentions and clean question text.

    Args:
        text: Raw command text (e.g., "<@U123> <@U456> what is the SLA?")

    Returns:
        Tuple of (user_ids, cleaned_question)
        Example: (["U123", "U456"], "what is the SLA?")
    """
    mention_pattern = r"<@(U[A-Z0-9]+)>"
    user_ids = re.findall(mention_pattern, text)
    cleaned_question = re.sub(mention_pattern, "", text).strip()
    return user_ids, cleaned_question
