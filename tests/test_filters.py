"""Tests for Slack message filters."""

import pytest
from src.faqbot.slack.filters import (
    is_bot_message,
    is_message_edit,
    is_in_allowed_channel,
    is_question,
    should_process_message,
)


def test_is_bot_message():
    """Test bot message detection."""
    # Bot message with user matching bot_user_id
    assert is_bot_message({"user": "BOT123"}, "BOT123") is True

    # Bot message with bot_id field
    assert is_bot_message({"bot_id": "B123", "user": "U123"}, "BOT456") is True

    # Regular user message
    assert is_bot_message({"user": "U123"}, "BOT456") is False


def test_is_message_edit():
    """Test message edit detection."""
    assert is_message_edit({"subtype": "message_changed"}) is True
    assert is_message_edit({"subtype": "message_deleted"}) is False
    assert is_message_edit({}) is False


def test_is_in_allowed_channel():
    """Test allowed channel check."""
    allowed = ["C123", "C456"]
    assert is_in_allowed_channel("C123", allowed) is True
    assert is_in_allowed_channel("C456", allowed) is True
    assert is_in_allowed_channel("C789", allowed) is False


def test_is_question():
    """Test question detection."""
    # Question marks
    assert is_question("What is this?") is True
    assert is_question("Help?") is True

    # Question words
    assert is_question("How do I do this") is True
    assert is_question("What is the answer") is True
    assert is_question("Where can I find") is True
    assert is_question("When does it start") is True
    assert is_question("Why is this happening") is True
    assert is_question("Can you help me") is True
    assert is_question("Is this correct") is True
    assert is_question("Are we there yet") is True
    assert is_question("Do you know") is True
    assert is_question("Will this work") is True

    # Not questions
    assert is_question("This is a statement") is False
    assert is_question("Hello there") is False
    assert is_question("Thanks for the help") is False
    assert is_question("") is False


def test_should_process_message():
    """Test full message processing logic."""
    bot_id = "BOT123"
    allowed = ["C123"]

    # Valid question
    event = {"user": "U123", "channel": "C123", "text": "How do I do this?"}
    should_process, reason = should_process_message(event, bot_id, allowed)
    assert should_process is True
    assert reason == "passed"

    # Bot message
    event = {"user": "BOT123", "channel": "C123", "text": "How do I do this?"}
    should_process, reason = should_process_message(event, bot_id, allowed)
    assert should_process is False
    assert reason == "bot_message"

    # Message edit
    event = {
        "user": "U123",
        "channel": "C123",
        "text": "How do I do this?",
        "subtype": "message_changed",
    }
    should_process, reason = should_process_message(event, bot_id, allowed)
    assert should_process is False
    assert reason == "message_edit"

    # Wrong channel
    event = {"user": "U123", "channel": "C999", "text": "How do I do this?"}
    should_process, reason = should_process_message(event, bot_id, allowed)
    assert should_process is False
    assert "channel_not_allowed" in reason

    # Not a question
    event = {"user": "U123", "channel": "C123", "text": "This is a statement"}
    should_process, reason = should_process_message(event, bot_id, allowed)
    assert should_process is False
    assert reason == "not_a_question"
