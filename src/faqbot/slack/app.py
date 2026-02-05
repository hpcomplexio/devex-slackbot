"""Slack Bolt app setup."""

import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from ..config import Config
from ..pipeline.answer import AnswerPipeline
from ..search.suggestions import FAQSuggestionService
from ..state.dedupe import ThreadTracker
from ..state.metrics import BotMetrics
from ..status.cache import StatusUpdateCache
from .handlers import setup_message_handler


def create_slack_app(
    config: Config,
    pipeline: AnswerPipeline,
    suggestion_service: FAQSuggestionService,
    status_cache: StatusUpdateCache,
    thread_tracker: ThreadTracker,
    metrics: BotMetrics,
    logger: logging.Logger,
) -> tuple[App, SocketModeHandler]:
    """Create and configure Slack app with all handlers.

    Args:
        config: Application configuration
        pipeline: Answer generation pipeline
        suggestion_service: FAQ suggestion service
        status_cache: Status update cache
        thread_tracker: Thread deduplication tracker
        metrics: Bot metrics tracker
        logger: Logger instance

    Returns:
        (app, handler) tuple
    """
    # Create Bolt app
    app = App(token=config.slack_bot_token)

    # Set up message handler (existing auto-answer functionality)
    setup_message_handler(
        app, pipeline, thread_tracker, metrics, config.slack_allowed_channels, logger
    )

    # Set up status monitoring (Phase 1)
    if config.status_monitoring_enabled and config.slack_status_channels:
        from ..status.monitor import setup_status_monitoring

        setup_status_monitoring(
            app, status_cache, config.slack_status_channels, logger
        )
        logger.info(
            f"Status monitoring enabled for channels: {', '.join(config.slack_status_channels)}"
        )

    # Set up reaction-based search (Phase 4)
    if config.reaction_search_enabled:
        from .reactions import setup_reaction_handlers

        setup_reaction_handlers(
            app, suggestion_service, pipeline, thread_tracker, metrics, logger
        )
        logger.info("Reaction-based search enabled (🔍 emoji)")

    # Set up slash command (Phase 5)
    if config.slash_command_enabled:
        from .slash_commands import setup_slash_commands

        setup_slash_commands(
            app, suggestion_service, pipeline, metrics, logger
        )
        logger.info("Slash command enabled (/ask)")

    # Create Socket Mode handler
    handler = SocketModeHandler(app, config.slack_app_token)

    logger.info("Slack app initialized with all handlers")
    return app, handler
