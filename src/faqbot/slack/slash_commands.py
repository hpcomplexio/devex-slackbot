"""Slack slash command handlers for FAQ search."""

import logging
import time
from typing import Any, Dict, Optional

from slack_bolt import App

from ..config import Config
from ..pipeline.answer import AnswerPipeline
from ..search.suggestions import FAQSuggestionService
from ..state.interaction_log import InteractionLog, InteractionRecord
from ..state.metrics import BotMetrics
from ..state.receipt_tracker import ReceiptTracker
from ..utils.admin import parse_mentions_and_question
from .reactions import build_suggestion_blocks


def setup_slash_commands(
    app: App,
    config: Config,
    suggestion_service: FAQSuggestionService,
    pipeline: AnswerPipeline,
    metrics: BotMetrics,
    interaction_log: Optional[InteractionLog],
    receipt_tracker: Optional[ReceiptTracker],
    logger: logging.Logger,
):
    """Set up slash command handlers.

    Args:
        app: Slack Bolt app
        config: Config object
        suggestion_service: FAQ suggestion service
        pipeline: Answer generation pipeline
        metrics: Bot metrics tracker
        interaction_log: Interaction logger (optional)
        receipt_tracker: Receipt tracker (optional)
        logger: Logger instance
    """

    @app.command("/ask")
    def handle_ask_command(ack: Any, command: Dict[str, Any], respond: Any, client: Any):
        """Handle /ask slash command for FAQ search.

        Args:
            ack: Acknowledgement function (must call within 3 seconds)
            command: Command payload from Slack
            respond: Function to send response
        """
        ack()  # Must acknowledge within 3 seconds

        try:
            raw_text = command["text"].strip()
            user_id = command["user_id"]
            channel_id = command["channel_id"]
            thread_ts = command.get("thread_ts")  # May be None if not in thread

            # Check for mentions first
            mentioned_user_ids, question = parse_mentions_and_question(raw_text)

            # If mentions found and receipt tracker enabled, handle as mention-tracked question
            if mentioned_user_ids and receipt_tracker:
                return handle_ask_with_mentions(
                    command, respond, client, question, mentioned_user_ids,
                    pipeline, receipt_tracker, interaction_log, logger
                )

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

            # Log interaction
            if interaction_log:
                interaction_log.log_interaction(
                    InteractionRecord(
                        id=None,
                        timestamp=time.time(),
                        interaction_type="slash_command",
                        user_id=user_id,
                        channel_id=channel_id,
                        thread_ts="",  # Slash commands don't have thread context
                        question_text=question,
                        answered=False,  # Showing suggestions, not direct answer
                        confidence_score=suggestions[0].similarity if suggestions else None,
                        confidence_ratio=None,
                        answer_text=None,
                        block_ids=[s.block_id for s in suggestions[:3]],
                        status_updates_shown=len(status_results),
                        user_clicked_button=False,
                        user_reactions=[],
                    )
                )

        except Exception as e:
            logger.error(f"Error handling slash command | error={e}")
            respond(
                {
                    "response_type": "ephemeral",
                    "text": "❌ Sorry, I encountered an error processing your request. Please try again.",
                }
            )
            # metrics.increment_errors()

    def handle_ask_with_mentions(
        command: Dict[str, Any],
        respond: Any,
        client: Any,
        question: str,
        mentioned_user_ids: list,
        pipeline: AnswerPipeline,
        receipt_tracker: ReceiptTracker,
        interaction_log: Optional[InteractionLog],
        logger: logging.Logger,
    ) -> None:
        """Handle /ask command with user mentions for read receipt tracking.

        Args:
            command: Command payload from Slack
            respond: Function to send response
            client: Slack client
            question: Cleaned question text (mentions removed)
            mentioned_user_ids: List of mentioned user IDs
            pipeline: Answer pipeline
            receipt_tracker: Receipt tracker
            interaction_log: Interaction logger (optional)
            logger: Logger instance
        """
        try:
            user_id = command["user_id"]
            channel_id = command["channel_id"]
            thread_ts = command.get("thread_ts")

            logger.info(
                f"Slash command with mentions | user={user_id} | mentions={len(mentioned_user_ids)} | question={question[:80]}"
            )

            # Generate answer (reuse existing pipeline)
            result = pipeline.answer_question(question)

            if not result.answered:
                # Low confidence - don't post
                respond(
                    {
                        "response_type": "ephemeral",
                        "text": (
                            f"❌ Not confident enough to answer (confidence: {result.confidence.top_score:.2f}).\n\n"
                            "The answer would not be reliable. Please rephrase or ask in a support channel."
                        ),
                    }
                )
                logger.info(f"Low confidence, not posting | confidence={result.confidence.top_score:.2f}")
                return

            # Format answer with mentions
            mention_text = " ".join([f"<@{uid}>" for uid in mentioned_user_ids])
            formatted_answer = f"{mention_text}\n\n{result.answer}"

            # Post to channel
            response = client.chat_postMessage(
                channel=channel_id,
                text=formatted_answer,
                thread_ts=thread_ts  # preserve thread if in one
            )

            message_ts = response["ts"]
            actual_thread_ts = response.get("thread_ts", message_ts)

            # Add ✅ reaction from bot as a hint
            client.reactions_add(
                channel=channel_id,
                timestamp=message_ts,
                name="white_check_mark"
            )

            # Track in receipt tracker
            receipt_tracker.track_message(
                message_ts=message_ts,
                channel_id=channel_id,
                thread_ts=actual_thread_ts,
                question=question,
                answer_preview=result.answer[:200] if result.answer else "",
                mentioned_user_ids=mentioned_user_ids,
            )

            # Log interaction
            if interaction_log:
                interaction_log.log_interaction(
                    InteractionRecord(
                        id=None,
                        timestamp=time.time(),
                        interaction_type="slash_command",
                        user_id=user_id,
                        channel_id=channel_id,
                        thread_ts=actual_thread_ts,
                        question_text=question,
                        answered=True,
                        confidence_score=result.confidence.top_score if result.confidence else None,
                        confidence_ratio=result.confidence.ratio if result.confidence else None,
                        answer_text=result.answer,
                        block_ids=[],
                        status_updates_shown=len(result.status_updates) if result.status_updates else 0,
                        user_clicked_button=False,
                        user_reactions=[],
                    )
                )

            # Respond ephemerally to command issuer
            respond(
                {
                    "response_type": "ephemeral",
                    "text": f"✅ Answer posted with mentions. Tracking acknowledgments from {len(mentioned_user_ids)} user(s)."
                }
            )

            logger.info(f"Answer posted with mentions | message_ts={message_ts} | mentions={len(mentioned_user_ids)}")

        except Exception as e:
            logger.error(f"Error handling mention-tracked command | error={e}", exc_info=True)
            respond(
                {
                    "response_type": "ephemeral",
                    "text": f"❌ Error processing command: {str(e)}"
                }
            )
