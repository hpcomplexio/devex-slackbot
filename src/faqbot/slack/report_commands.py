"""DM-based report command for interaction analytics."""

import csv
import io
import re
import time
from datetime import datetime
from typing import List, Optional, Tuple

from slack_bolt import App

from ..config import Config
from ..state.interaction_log import InteractionLog, InteractionRecord
from ..utils.admin import is_admin


def parse_time_range(text: str) -> Tuple[float, float]:
    """Parse natural language time expressions for reports.

    Supports:
    - "report" -> last 24 hours
    - "report 7d" or "report last week" -> last 7 days
    - "report 2026-02-15" -> that specific day
    - "report 2026-02-15 to 2026-02-18" -> date range

    Args:
        text: User's message text

    Returns:
        Tuple of (start_timestamp, end_timestamp)
    """
    now = time.time()
    text_lower = text.lower().strip()

    # Default: last 24 hours
    if text_lower == "report":
        return now - 86400, now

    # Pattern: "7d", "3 days", "last week"
    if "7d" in text_lower or "last week" in text_lower or "7 days" in text_lower:
        return now - (7 * 86400), now

    # Pattern: "YYYY-MM-DD"
    date_pattern = r"(\d{4}-\d{2}-\d{2})"
    dates = re.findall(date_pattern, text)

    if len(dates) == 1:
        # Single date: start of day to end of day
        start_ts = datetime.strptime(dates[0], "%Y-%m-%d").timestamp()
        end_ts = start_ts + 86400
        return start_ts, end_ts

    if len(dates) == 2:
        # Date range
        start_ts = datetime.strptime(dates[0], "%Y-%m-%d").timestamp()
        end_ts = datetime.strptime(dates[1], "%Y-%m-%d").timestamp() + 86400
        return start_ts, end_ts

    # Fallback: last 24 hours
    return now - 86400, now


def generate_report(
    interactions: List[InteractionRecord],
    start_time: float,
    end_time: float,
) -> str:
    """Generate formatted report text from interactions.

    Args:
        interactions: List of interaction records
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        Formatted report text
    """
    if not interactions:
        return "📊 FAQ Bot Interaction Report\n\nNo interactions found in the specified time period."

    # Calculate summary stats
    total = len(interactions)
    answered = sum(1 for i in interactions if i.answered)
    skipped = total - answered

    answered_records = [i for i in interactions if i.answered and i.confidence_score is not None]
    avg_confidence = (
        sum(i.confidence_score for i in answered_records if i.confidence_score is not None) / len(answered_records)
        if answered_records
        else 0.0
    )

    # Count by type
    type_counts = {}
    for interaction in interactions:
        type_counts[interaction.interaction_type] = type_counts.get(interaction.interaction_type, 0) + 1

    # Find low-confidence questions
    low_confidence = [
        i for i in interactions
        if not i.answered and i.confidence_score is not None
    ]
    low_confidence.sort(key=lambda i: i.confidence_score if i.confidence_score else 0, reverse=True)

    # Find high engagement
    high_engagement = [
        i for i in interactions
        if i.answered and (i.user_clicked_button or len(i.user_reactions) > 0)
    ]
    high_engagement.sort(
        key=lambda i: len(i.user_reactions) + (1 if i.user_clicked_button else 0),
        reverse=True
    )

    # Format dates
    start_date = datetime.fromtimestamp(start_time).strftime("%b %d")
    end_date = datetime.fromtimestamp(end_time).strftime("%b %d, %Y")
    days = int((end_time - start_time) / 86400)

    # Build report
    lines = [
        "📊 FAQ Bot Interaction Report",
        f"Period: {start_date} - {end_date} ({days} days)",
        "",
        "📈 Summary",
        f"• Total questions: {total}",
        f"• Answered: {answered} ({answered * 100 // total if total > 0 else 0}%)",
        f"• Skipped (low confidence): {skipped} ({skipped * 100 // total if total > 0 else 0}%)",
        f"• Avg confidence (answered): {avg_confidence:.2f}" if answered_records else "• Avg confidence: N/A",
        "",
    ]

    # Low confidence questions
    if low_confidence:
        lines.append("💬 Top Questions Asked (with low confidence)")
        for idx, interaction in enumerate(low_confidence[:5], 1):
            q_preview = interaction.question_text[:80] + "..." if len(interaction.question_text) > 80 else interaction.question_text
            conf = interaction.confidence_score if interaction.confidence_score else 0.0
            ratio = interaction.confidence_ratio if interaction.confidence_ratio else 0.0
            lines.append(f"{idx}. \"{q_preview}\" - confidence: {conf:.2f}, ratio: {ratio:.2f}")
        lines.append("")

    # High engagement
    if high_engagement:
        lines.append("👍 High Engagement (reactions/clicks)")
        for idx, interaction in enumerate(high_engagement[:5], 1):
            q_preview = interaction.question_text[:80] + "..." if len(interaction.question_text) > 80 else interaction.question_text
            reaction_count = len(interaction.user_reactions)
            click_count = 1 if interaction.user_clicked_button else 0
            lines.append(f"{idx}. \"{q_preview}\" - {reaction_count} reactions, {click_count} clicks")
        lines.append("")

    # Interaction types
    lines.append("🔍 Interaction Types")
    for itype, count in type_counts.items():
        type_label = itype.replace("_", " ").title()
        lines.append(f"• {type_label}: {count}")
    lines.append("")
    lines.append("📎 Detailed log attached as CSV")

    return "\n".join(lines)


def generate_csv(interactions: List[InteractionRecord]) -> str:
    """Generate CSV export of interactions.

    Args:
        interactions: List of interaction records

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID",
        "Timestamp",
        "Date",
        "Type",
        "User ID",
        "Channel ID",
        "Thread TS",
        "Question",
        "Answered",
        "Confidence Score",
        "Confidence Ratio",
        "Answer Preview",
        "Block IDs",
        "Status Updates",
        "User Clicked Button",
        "User Reactions",
    ])

    # Data rows
    for record in interactions:
        date_str = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        answer_preview = (record.answer_text[:100] + "...") if record.answer_text and len(record.answer_text) > 100 else (record.answer_text or "")

        writer.writerow([
            record.id or "",
            record.timestamp,
            date_str,
            record.interaction_type,
            record.user_id,
            record.channel_id,
            record.thread_ts,
            record.question_text,
            "Yes" if record.answered else "No",
            f"{record.confidence_score:.3f}" if record.confidence_score is not None else "",
            f"{record.confidence_ratio:.3f}" if record.confidence_ratio is not None else "",
            answer_preview,
            ",".join(record.block_ids),
            record.status_updates_shown,
            "Yes" if record.user_clicked_button else "No",
            ",".join(record.user_reactions),
        ])

    return output.getvalue()


def setup_dm_report_handler(
    app: App,
    config: Config,
    interaction_log: InteractionLog,
    logger,
) -> None:
    """Set up DM message handler for report requests.

    Args:
        app: Slack Bolt app
        config: Config object
        interaction_log: InteractionLog instance
        logger: Logger instance
    """

    @app.event("message")
    async def handle_dm_report_request(event, say, client):
        """Handle DM messages that request reports."""

        # Debug logging
        logger.info(f"Message event received | channel={event.get('channel', 'N/A')} | subtype={event.get('subtype', 'N/A')} | bot_id={event.get('bot_id', 'N/A')}")

        # Only respond in DM channels (DM channel IDs start with 'D')
        channel_id = event.get("channel", "")
        if not channel_id.startswith("D"):
            logger.info(f"Skipping non-DM channel: {channel_id}")
            return

        # Ignore bot messages and message edits
        if event.get("subtype") or event.get("bot_id"):
            return

        user_id = event["user"]
        text = event["text"].lower().strip()

        # Check for report keywords
        if not any(keyword in text for keyword in ["report", "show interactions", "stats"]):
            return  # Not a report request, ignore

        logger.info(f"DM report request | user={user_id} | text={text[:50]}")

        # Check admin permission
        if not is_admin(user_id, config):
            await say("❌ Sorry, reports are restricted to admins.")
            logger.info(f"DM report denied | user={user_id} | reason=not_admin")
            return

        # Parse time range from natural language
        start_time, end_time = parse_time_range(text)

        # Query interaction log
        try:
            interactions = interaction_log.get_interactions(
                start_time=start_time,
                end_time=end_time
            )

            # Generate report
            report_text = generate_report(interactions, start_time, end_time)

            # Send as DM
            await say(report_text)

            # Attach CSV if there are interactions
            if interactions:
                csv_data = generate_csv(interactions)
                client.files_upload_v2(
                    channel=event["channel"],
                    content=csv_data,
                    filename=f"faq_report_{int(start_time)}_to_{int(end_time)}.csv",
                    title="Detailed Interaction Log"
                )

            logger.info(f"DM report sent | user={user_id} | count={len(interactions)}")

        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            await say(f"❌ Error generating report: {str(e)}")
