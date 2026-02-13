"""Slack message event handlers."""

import logging
from typing import Any, Dict

from slack_bolt import App

from ..pipeline.answer import AnswerPipeline
from ..state.dedupe import ThreadTracker
from ..state.metrics import BotMetrics
from .filters import should_process_message
from .formatting import format_answer_for_slack, format_no_answer_message, format_searching_message


def setup_message_handler(
    app: App,
    pipeline: AnswerPipeline,
    thread_tracker: ThreadTracker,
    metrics: BotMetrics,
    allowed_channels: list,
    logger: logging.Logger,
):
    """Set up message event handler.

    Args:
        app: Slack Bolt app
        pipeline: Answer generation pipeline
        thread_tracker: Thread deduplication tracker
        metrics: Bot metrics tracker
        allowed_channels: List of allowed channel IDs
        logger: Logger instance
    """

    @app.event("message")
    def handle_message(event: Dict[str, Any], say: Any, client: Any):
        """Handle incoming message events."""
        try:
            # Get bot user ID
            bot_user_id = client.auth_test()["user_id"]

            # Filter message
            should_process, reason = should_process_message(
                event, bot_user_id, allowed_channels
            )

            if not should_process:
                metrics.increment_filtered(reason)
                logger.debug(f"Filtered message | reason={reason}")
                return

            # Extract message details
            text = event.get("text", "")
            channel = event.get("channel")
            message_ts = event.get("ts")
            thread_ts = event.get("thread_ts", message_ts)  # Use message_ts if not in thread

            logger.info(
                f"Question detected | channel={channel} | thread={thread_ts} | text={text[:100]}"
            )
            metrics.increment_questions()

            # Check if thread already answered
            if thread_tracker.is_answered(thread_ts):
                logger.info(f"Thread already answered | thread={thread_ts}")
                metrics.increment_filtered("thread_already_answered")
                return

            # Send "searching" message immediately
            say(text=format_searching_message(), thread_ts=thread_ts)

            # Generate answer
            logger.info(f"Generating answer | question={text[:100]}")
            result = pipeline.answer_question(text)

            if not result.answered:
                conf = result.confidence
                logger.info(
                    f"Answer skipped | reason={result.reason} | "
                    f"top_score={conf.top_score if conf else None} | "
                    f"ratio={conf.ratio if conf and conf.ratio else None}"
                )
                metrics.increment_answers_skipped(result.reason)
                # Send "can't answer" message
                say(text=format_no_answer_message(), thread_ts=thread_ts)
                return

            # Send answer in thread
            formatted_answer = format_answer_for_slack(result.answer)
            say(text=formatted_answer, thread_ts=thread_ts)

            # Mark thread as answered
            thread_tracker.mark_answered(thread_ts)

            conf = result.confidence
            logger.info(
                f"Answer sent | thread={thread_ts} | "
                f"top_score={conf.top_score if conf else None} | "
                f"ratio={conf.ratio if conf and conf.ratio else None}"
            )
            metrics.increment_answers_sent()

        except Exception as e:
            logger.error(f"Error handling message | error={e}")
            metrics.increment_errors()
            # Don't re-raise to prevent bot from crashing
