"""Admin command for viewing read receipt status."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List

from slack_bolt import App

from ..config import Config
from ..state.receipt_tracker import ReceiptRecord, ReceiptTracker
from ..utils.admin import is_admin


def setup_receipt_command(
    app: App,
    config: Config,
    receipt_tracker: ReceiptTracker,
    logger: logging.Logger,
) -> None:
    """Set up /faq-receipts admin command.

    Args:
        app: Slack Bolt app
        config: Config object
        receipt_tracker: Receipt tracker
        logger: Logger instance
    """

    @app.command("/faq-receipts")
    def handle_faq_receipts(ack: Any, command: Dict[str, Any], respond: Any):
        """Handle /faq-receipts command to view pending acknowledgments."""
        ack()

        try:
            user_id = command["user_id"]

            # Check admin permission
            if not is_admin(user_id, config):
                respond(
                    {
                        "response_type": "ephemeral",
                        "text": "❌ This command is restricted to admins."
                    }
                )
                logger.info(f"Receipt command denied | user={user_id} | reason=not_admin")
                return

            text = command.get("text", "").strip()

            # Parse optional @user filter
            filter_user_id = None
            if text.startswith("<@"):
                match = re.search(r"<@(U[A-Z0-9]+)>", text)
                if match:
                    filter_user_id = match.group(1)

            # Get pending receipts
            pending = receipt_tracker.get_pending_receipts(user_id=filter_user_id)

            logger.info(
                f"Receipt command | user={user_id} | filter_user={filter_user_id} | pending_count={len(pending)}"
            )

            # No pending receipts
            if not pending:
                if filter_user_id:
                    respond(
                        {
                            "response_type": "ephemeral",
                            "text": f"✅ <@{filter_user_id}> has no pending acknowledgments!"
                        }
                    )
                else:
                    respond(
                        {
                            "response_type": "ephemeral",
                            "text": "✅ No pending acknowledgments!"
                        }
                    )
                return

            # Build formatted report
            blocks = build_receipt_report_blocks(pending)

            respond(
                {
                    "response_type": "ephemeral",
                    "blocks": blocks,
                    "text": f"📋 Read Receipt Status ({len(pending)} pending)"
                }
            )

        except Exception as e:
            logger.error(f"Error handling receipt command | error={e}", exc_info=True)
            respond(
                {
                    "response_type": "ephemeral",
                    "text": f"❌ Error processing command: {str(e)}"
                }
            )


def build_receipt_report_blocks(pending: List[ReceiptRecord]) -> List[Dict[str, Any]]:
    """Build Slack Block Kit blocks for receipt status report.

    Args:
        pending: List of pending receipt records

    Returns:
        List of Slack blocks
    """
    blocks = []

    # Header
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 Read Receipt Status"
            }
        }
    )

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⏳ Pending Acknowledgments ({len(pending)})*"
            }
        }
    )

    blocks.append({"type": "divider"})

    # Show each pending record
    for idx, record in enumerate(pending[:10], 1):  # Limit to 10 for UI
        # Calculate who's waiting
        waiting_users = [uid for uid in record.mentioned_user_ids if uid not in record.acknowledged_user_ids]
        acked_users = record.acknowledged_user_ids

        # Time ago
        time_ago = get_time_ago(record.posted_at)
        time_str = datetime.fromtimestamp(record.posted_at).strftime("%b %d, %I:%M %p")

        # Build text
        question_preview = record.question[:60] + "..." if len(record.question) > 60 else record.question

        text_lines = [
            f"*{idx}. \"{question_preview}\"*",
            f"Posted: {time_str} ({time_ago})",
        ]

        # Who's waiting
        if waiting_users:
            waiting_mentions = " ".join([f"<@{uid}>" for uid in waiting_users])
            text_lines.append(f"⏳ Waiting on: {waiting_mentions} ({len(acked_users)} of {len(record.mentioned_user_ids)} acknowledged)")
        else:
            text_lines.append("✅ All users acknowledged!")

        # Who's acknowledged
        if acked_users:
            acked_mentions = " ".join([f"<@{uid}>" for uid in acked_users])
            text_lines.append(f"✅ Acknowledged: {acked_mentions}")

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(text_lines)
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Message"},
                    "url": f"https://slack.com/app_redirect?channel={record.channel_id}&message_ts={record.message_ts}"
                }
            }
        )

    if len(pending) > 10:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_... and {len(pending) - 10} more pending acknowledgments_"
                    }
                ]
            }
        )

    # Footer
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 *Tip:* Use `/faq-receipts @user` to filter by specific user"
                }
            ]
        }
    )

    return blocks


def get_time_ago(timestamp: float) -> str:
    """Get human-readable time ago string.

    Args:
        timestamp: Unix timestamp

    Returns:
        Human-readable string like "3 hours ago"
    """
    import time

    now = time.time()
    diff = now - timestamp

    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(diff / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
