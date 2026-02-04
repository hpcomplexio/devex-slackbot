"""Message filtering logic for Slack events."""

from typing import Dict, Any, List


def is_bot_message(event: Dict[str, Any], bot_user_id: str) -> bool:
    """Check if message is from a bot."""
    user = event.get("user")
    return user == bot_user_id or "bot_id" in event


def is_message_edit(event: Dict[str, Any]) -> bool:
    """Check if message is an edit."""
    return event.get("subtype") == "message_changed"


def is_in_allowed_channel(channel: str, allowed_channels: List[str]) -> bool:
    """Check if message is in an allowed channel."""
    return channel in allowed_channels


def is_question(text: str) -> bool:
    """Detect if message is a question.

    Checks for:
    1. Contains question mark
    2. Starts with question words (how, what, where, when, why, who, can, is, are, etc.)
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    # Check for question mark
    if "?" in text:
        return True

    # Check for question words at the start
    question_words = [
        "how",
        "what",
        "where",
        "when",
        "why",
        "who",
        "which",
        "whom",
        "whose",
        "can",
        "could",
        "would",
        "should",
        "is",
        "are",
        "was",
        "were",
        "do",
        "does",
        "did",
        "will",
        "have",
        "has",
        "had",
    ]

    for word in question_words:
        if text_lower.startswith(word + " "):
            return True

    return False


def should_process_message(
    event: Dict[str, Any], bot_user_id: str, allowed_channels: List[str]
) -> tuple[bool, str]:
    """Check if message should be processed.

    Returns:
        (should_process, reason)
    """
    # Check if bot message
    if is_bot_message(event, bot_user_id):
        return False, "bot_message"

    # Check if message edit
    if is_message_edit(event):
        return False, "message_edit"

    # Check if in allowed channel
    channel = event.get("channel")
    if not is_in_allowed_channel(channel, allowed_channels):
        return False, f"channel_not_allowed:{channel}"

    # Check if question
    text = event.get("text", "")
    if not is_question(text):
        return False, "not_a_question"

    return True, "passed"
