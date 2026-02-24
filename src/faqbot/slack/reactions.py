"""Slack reaction-based search handlers."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from slack_bolt import App

from ..pipeline.answer import AnswerPipeline
from ..search.suggestions import FAQSuggestion, FAQSuggestionService
from ..state.dedupe import ThreadTracker
from ..state.interaction_log import InteractionLog
from ..state.metrics import BotMetrics
from ..state.receipt_tracker import ReceiptTracker


SEARCH_EMOJI = "mag"  # 🔍 magnifying glass
ACKNOWLEDGMENT_EMOJI = "white_check_mark"  # ✅ checkmark


def setup_reaction_handlers(
    app: App,
    suggestion_service: FAQSuggestionService,
    pipeline: AnswerPipeline,
    thread_tracker: ThreadTracker,
    metrics: BotMetrics,
    interaction_log: Optional[InteractionLog],
    receipt_tracker: Optional[ReceiptTracker],
    logger: logging.Logger,
):
    """Set up reaction-based search and acknowledgment handlers.

    Args:
        app: Slack Bolt app
        suggestion_service: FAQ suggestion service
        pipeline: Answer generation pipeline
        thread_tracker: Thread deduplication tracker
        metrics: Bot metrics tracker
        interaction_log: Interaction logger (optional)
        receipt_tracker: Receipt tracker (optional)
        logger: Logger instance
    """

    @app.event("reaction_added")
    def handle_reaction_router(event: Dict[str, Any], client: Any):
        """Route reactions to appropriate handlers (🔍 search or ✅ acknowledgment)."""
        try:
            reaction = event.get("reaction")

            # Route to search handler
            if reaction == SEARCH_EMOJI:
                handle_search_reaction(event, client)
                return

            # Route to acknowledgment handler
            if reaction == ACKNOWLEDGMENT_EMOJI and receipt_tracker:
                handle_acknowledgment_reaction(event, client)
                return

            # Ignore other reactions
            return

        except Exception as e:
            logger.error(f"Error routing reaction | error={e}", exc_info=True)

    def handle_search_reaction(event: Dict[str, Any], client: Any):
        """Handle 🔍 reaction to trigger FAQ search."""
        try:
            reaction = event.get("reaction")
            if reaction != SEARCH_EMOJI:
                return

            user_id = event.get("user")
            item = event.get("item", {})
            channel_id = item.get("channel")
            message_ts = item.get("ts")

            # Retrieve original message
            response = client.conversations_history(
                channel=channel_id,
                latest=message_ts,
                inclusive=True,
                limit=1,
            )

            if not response.get("messages"):
                logger.warning(f"Could not retrieve message | ts={message_ts}")
                return

            original_message = response["messages"][0]
            message_text = original_message.get("text", "")
            message_user = original_message.get("user")

            # Only allow message author to trigger (prevent spam)
            if user_id != message_user:
                logger.debug(
                    f"Reaction from non-author ignored | user={user_id} | author={message_user}"
                )
                return

            thread_ts = original_message.get("thread_ts", message_ts)

            # Check if already answered
            if thread_tracker.is_answered(thread_ts):
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="This question already has an FAQ response in the thread!",
                    thread_ts=thread_ts,
                )
                logger.info(
                    f"Reaction search blocked - already answered | thread={thread_ts}"
                )
                return

            # Search FAQs
            logger.info(
                f"Reaction search triggered | user={user_id} | text={message_text[:100]}"
            )
            suggestions = suggestion_service.search(message_text, top_k=5)

            # Get status updates if pipeline has status cache
            status_results = []
            if hasattr(pipeline, "status_cache") and pipeline.status_cache:
                from ..status.cache import INCIDENT_KEYWORDS

                query_embedding = suggestion_service.embedding_model.embed(message_text)
                question_keywords = [
                    kw for kw in INCIDENT_KEYWORDS if kw in message_text.lower()
                ]

                if question_keywords or len(pipeline.status_cache.updates) > 0:
                    status_results = pipeline.status_cache.search_semantic(
                        query_embedding,
                        suggestion_service.embedding_model,
                        top_k=2,
                        min_similarity=0.50,
                    )

            if not suggestions and not status_results:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="No matching FAQs or status updates found. Try rephrasing or contact support.",
                    thread_ts=thread_ts,
                )
                logger.info(f"No results found | text={message_text[:100]}")
                return

            # Send ephemeral suggestions with buttons
            blocks = build_suggestion_blocks(
                suggestions, status_results, thread_ts, channel_id
            )
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Found {len(suggestions)} FAQ match(es) and {len(status_results)} related status update(s)",
                blocks=blocks,
                thread_ts=thread_ts,
            )

            logger.info(
                f"Suggestions sent | faqs={len(suggestions)} | status={len(status_results)}"
            )
            # metrics.increment_reaction_searches()  # Will add in Phase 7

        except Exception as e:
            logger.error(f"Error handling reaction | error={e}")
            # metrics.increment_errors()

    def handle_acknowledgment_reaction(event: Dict[str, Any], client: Any):
        """Handle ✅ reaction for read receipt tracking."""
        try:
            if not receipt_tracker:
                return

            user_id = event.get("user")
            item = event.get("item", {})
            message_ts = item.get("ts")

            # Check if this message is tracked for receipts
            record = receipt_tracker.get_record(message_ts)
            if not record:
                return  # Not a tracked message

            # Mark user as acknowledged
            success = receipt_tracker.mark_acknowledged(message_ts, user_id)

            if success:
                logger.info(f"Acknowledgment tracked | user={user_id} | message_ts={message_ts}")

                # Update interaction log if available
                if interaction_log:
                    interaction_log.update_engagement(
                        thread_ts=record.thread_ts,
                        reaction=ACKNOWLEDGMENT_EMOJI
                    )
            else:
                logger.debug(
                    f"Acknowledgment not tracked | user={user_id} | message_ts={message_ts} | reason=not_mentioned_or_already_acked"
                )

        except Exception as e:
            logger.error(f"Error handling acknowledgment reaction | error={e}", exc_info=True)

    @app.action(re.compile(r"post_faq_.*"))
    def handle_post_faq_button(ack: Any, action: Dict[str, Any], body: Dict[str, Any], client: Any):
        """Handle 'Post Answer' button click."""
        ack()

        try:
            payload = json.loads(action["value"])
            block_id = payload["block_id"]
            thread_ts = payload["thread_ts"]
            channel_id = payload["channel_id"]
            user_id = body["user"]["id"]

            logger.info(
                f"Post FAQ button clicked | block={block_id} | thread={thread_ts}"
            )

            # Check if thread was already answered while user was deciding
            if thread_tracker.is_answered(thread_ts):
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="This thread was already answered while you were reviewing suggestions.",
                    thread_ts=thread_ts,
                )
                return

            # Retrieve chunk from vector store
            from ..retrieval.store import get_chunk_by_id

            chunk = get_chunk_by_id(pipeline.vector_store, block_id)

            if not chunk:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="Error: Could not find FAQ content. Please try again.",
                    thread_ts=thread_ts,
                )
                logger.error(f"Chunk not found | block_id={block_id}")
                return

            # Generate full answer using the specific FAQ chunk
            # Build a focused question from the chunk heading
            question = chunk.heading
            result = pipeline.answer_question(question)

            if not result.answered:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"Could not generate answer: {result.reason}",
                    thread_ts=thread_ts,
                )
                logger.warning(
                    f"Answer generation failed | block={block_id} | reason={result.reason}"
                )
                return

            # Post answer in thread (public)
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=result.answer,
            )

            # Mark thread as answered
            thread_tracker.mark_answered(thread_ts)

            logger.info(f"FAQ answer posted | thread={thread_ts} | block={block_id}")
            # metrics.increment_answers_sent()

        except Exception as e:
            logger.error(f"Error posting FAQ answer | error={e}")
            # metrics.increment_errors()


def build_suggestion_blocks(
    suggestions: List[FAQSuggestion],
    status_results: List[tuple],
    thread_ts: Optional[str],
    channel_id: str,
) -> List[Dict[str, Any]]:
    """Build Slack Block Kit blocks for FAQ suggestions and status updates.

    Args:
        suggestions: List of FAQ suggestions
        status_results: List of (StatusUpdate, similarity) tuples
        thread_ts: Thread timestamp (None for slash commands without thread context)
        channel_id: Channel ID

    Returns:
        List of Slack blocks
    """
    blocks = []

    # Header
    if suggestions and status_results:
        header_text = "🔍 *Found matching FAQs and related status updates:*"
    elif suggestions:
        header_text = "🔍 *Found matching FAQs:*"
    else:
        header_text = "📢 *Found related status updates:*"

    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text},
        }
    )

    blocks.append({"type": "divider"})

    # FAQ suggestions
    for i, suggestion in enumerate(suggestions, 1):
        # Suggestion details
        section_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. {suggestion.heading}*\n"
                    f"_{suggestion.content_preview}_\n"
                    f"Similarity: {suggestion.similarity:.0%}"
                ),
            },
        }

        # Only add "Post Answer" button if we have thread context (reaction-based search)
        # Slash commands don't have thread_ts, so they only get view links
        if thread_ts is not None:
            section_block["accessory"] = {
                "type": "button",
                "text": {"type": "plain_text", "text": "📝 Post Answer"},
                "style": "primary",
                "action_id": f"post_faq_{i}",
                "value": json.dumps(
                    {
                        "block_id": suggestion.block_id,
                        "thread_ts": thread_ts,
                        "channel_id": channel_id,
                    }
                ),
            }

        blocks.append(section_block)

        # Link to full FAQ
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"<{suggestion.url}|View full FAQ in Notion>",
                    }
                ],
            }
        )

    # Status updates section
    if status_results:
        if suggestions:
            blocks.append({"type": "divider"})

        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "📢 *Related Status Updates:*"},
            }
        )

        for status, similarity in status_results[:2]:  # Show top 2
            time_str = status.posted_at.strftime("%Y-%m-%d %H:%M")
            message_preview = status.message_text[:150]
            if len(status.message_text) > 150:
                message_preview += "..."

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*[{time_str}]* {message_preview}\nRelevance: {similarity:.0%}",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View"},
                        "url": status.message_link,
                    },
                }
            )

    # Footer with usage hint
    blocks.append({"type": "divider"})

    # Different footer text for reactions vs slash commands
    if thread_ts is not None:
        # Reaction-based search: has "Post Answer" buttons
        footer_text = "💡 Click *Post Answer* to share the full FAQ response in the thread, or view the Notion page for more details."
    else:
        # Slash command: no "Post Answer" buttons
        footer_text = "💡 View the Notion FAQ pages for complete documentation, or check the status update links for real-time incident information."

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": footer_text,
                }
            ],
        }
    )

    return blocks
