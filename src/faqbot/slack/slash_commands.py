"""Slack slash command handlers for FAQ search."""

import logging
from typing import Any, Dict

from slack_bolt import App

from ..pipeline.answer import AnswerPipeline
from ..search.suggestions import FAQSuggestionService
from ..state.metrics import BotMetrics
from .reactions import build_suggestion_blocks


def setup_slash_commands(
    app: App,
    suggestion_service: FAQSuggestionService,
    pipeline: AnswerPipeline,
    metrics: BotMetrics,
    logger: logging.Logger,
):
    """Set up slash command handlers.

    Args:
        app: Slack Bolt app
        suggestion_service: FAQ suggestion service
        pipeline: Answer generation pipeline
        metrics: Bot metrics tracker
        logger: Logger instance
    """

    @app.command("/ask")
    def handle_ask_command(ack: Any, command: Dict[str, Any], respond: Any):
        """Handle /ask slash command for FAQ search.

        Args:
            ack: Acknowledgement function (must call within 3 seconds)
            command: Command payload from Slack
            respond: Function to send response
        """
        ack()  # Must acknowledge within 3 seconds

        try:
            question = command["text"].strip()
            user_id = command["user_id"]
            channel_id = command["channel_id"]

            # Validate input
            if not question or len(question) < 3:
                respond(
                    {
                        "response_type": "ephemeral",
                        "text": (
                            "ℹ️ *Usage:* `/ask [your question]`\n\n"
                            "*Examples:*\n"
                            "• `/ask how do I deploy to kubernetes?`\n"
                            "• `/ask what are the authentication steps?`\n"
                            "• `/ask troubleshoot build failures`"
                        ),
                    }
                )
                logger.info(f"Slash command - empty query | user={user_id}")
                return

            logger.info(
                f"Slash command | user={user_id} | channel={channel_id} | query={question[:100]}"
            )

            # Search FAQs
            suggestions = suggestion_service.search(question, top_k=5)

            # Get status updates if pipeline has status cache
            status_results = []
            if hasattr(pipeline, "status_cache") and pipeline.status_cache:
                from ..status.cache import INCIDENT_KEYWORDS

                query_embedding = suggestion_service.embedding_model.embed(question)
                question_keywords = [
                    kw for kw in INCIDENT_KEYWORDS if kw in question.lower()
                ]

                if question_keywords or len(pipeline.status_cache.updates) > 0:
                    status_results = pipeline.status_cache.search_semantic(
                        query_embedding,
                        suggestion_service.embedding_model,
                        top_k=2,
                        min_similarity=0.50,
                    )

            # No results found
            if not suggestions and not status_results:
                respond(
                    {
                        "response_type": "ephemeral",
                        "text": (
                            "❌ No matching FAQs or status updates found.\n\n"
                            "*Suggestions:*\n"
                            "• Try rephrasing your question\n"
                            "• Check the <https://notion.so/faq|FAQ page> directly\n"
                            "• Ask in the support channel"
                        ),
                    }
                )
                logger.info(f"No results | query={question[:100]}")
                # metrics.increment_slash_commands()  # Will add in Phase 7
                return

            # High confidence: send immediate answer (public response)
            if suggestions and suggestions[0].similarity >= 0.70:
                logger.info(
                    f"High confidence answer | similarity={suggestions[0].similarity:.2f}"
                )

                # Generate full answer
                result = pipeline.answer_question(question)

                if result.answered and result.answer:
                    # Post public answer with FAQ attribution
                    answer_text = result.answer

                    # Add source attribution
                    answer_text += f"\n\n_Source: {suggestions[0].heading}_"

                    respond(
                        {
                            "response_type": "in_channel",  # Public response
                            "text": answer_text,
                        }
                    )

                    logger.info(
                        f"Answer sent publicly | block={suggestions[0].block_id}"
                    )
                    # metrics.increment_answers_sent()
                    # metrics.increment_slash_commands()
                    return

            # Medium/low confidence: show suggestions (ephemeral)
            logger.info(
                f"Showing suggestions | faqs={len(suggestions)} | status={len(status_results)}"
            )

            # Use same block builder as reactions
            # Note: thread_ts is None for slash commands (not in thread context)
            blocks = build_suggestion_blocks(
                suggestions, status_results, thread_ts=None, channel_id=channel_id
            )

            respond(
                {
                    "response_type": "ephemeral",
                    "text": f"Found {len(suggestions)} FAQ match(es) and {len(status_results)} related status update(s)",
                    "blocks": blocks,
                }
            )

            logger.info(f"Suggestions sent | count={len(suggestions)}")
            # metrics.increment_slash_commands()

        except Exception as e:
            logger.error(f"Error handling slash command | error={e}")
            respond(
                {
                    "response_type": "ephemeral",
                    "text": "❌ Sorry, I encountered an error processing your request. Please try again.",
                }
            )
            # metrics.increment_errors()
