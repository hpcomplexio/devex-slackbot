"""Slack message formatting utilities."""


def format_answer_for_slack(answer: str) -> str:
    """Format answer for Slack display.

    Currently just returns answer as-is since Claude generates markdown
    that Slack supports. Could add additional formatting later.
    """
    return answer


def format_error_message(error: str) -> str:
    """Format error message for Slack."""
    return f"Sorry, I encountered an error: {error}"


def format_no_answer_message() -> str:
    """Format message when bot can't answer."""
    return "I don't have enough information in the FAQ to answer this question confidently. Please check the FAQ page or ask a team member."
