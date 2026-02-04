"""Slack Bolt app setup."""

import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from ..pipeline.answer import AnswerPipeline
from ..state.dedupe import ThreadTracker
from ..state.metrics import BotMetrics
from .handlers import setup_message_handler


def create_slack_app(
    bot_token: str,
    app_token: str,
    pipeline: AnswerPipeline,
    thread_tracker: ThreadTracker,
    metrics: BotMetrics,
    allowed_channels: list,
    logger: logging.Logger,
) -> tuple[App, SocketModeHandler]:
    """Create and configure Slack app.

    Args:
        bot_token: Slack bot token
        app_token: Slack app token for Socket Mode
        pipeline: Answer generation pipeline
        thread_tracker: Thread deduplication tracker
        metrics: Bot metrics tracker
        allowed_channels: List of allowed channel IDs
        logger: Logger instance

    Returns:
        (app, handler) tuple
    """
    # Create Bolt app
    app = App(token=bot_token)

    # Set up message handler
    setup_message_handler(
        app, pipeline, thread_tracker, metrics, allowed_channels, logger
    )

    # Create Socket Mode handler
    handler = SocketModeHandler(app, app_token)

    logger.info("Slack app initialized")
    return app, handler
