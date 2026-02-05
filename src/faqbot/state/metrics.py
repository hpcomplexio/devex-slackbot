"""Metrics and logging helpers."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BotMetrics:
    """Track bot metrics."""

    questions_detected: int = 0
    answers_sent: int = 0
    answers_skipped: int = 0
    errors: int = 0
    messages_filtered: Dict[str, int] = field(default_factory=dict)

    # New metrics for suggestion features (Phase 4-5)
    reaction_searches: int = 0
    slash_commands: int = 0
    suggestions_shown: int = 0
    suggestions_clicked: int = 0

    # New metrics for status monitoring (Phase 1-3)
    status_updates_cached: int = 0
    status_correlations_shown: int = 0

    def increment_questions(self) -> None:
        """Increment questions detected counter."""
        self.questions_detected += 1

    def increment_answers_sent(self) -> None:
        """Increment answers sent counter."""
        self.answers_sent += 1

    def increment_answers_skipped(self, reason: str) -> None:
        """Increment answers skipped counter."""
        self.answers_skipped += 1

    def increment_errors(self) -> None:
        """Increment errors counter."""
        self.errors += 1

    def increment_filtered(self, reason: str) -> None:
        """Increment filtered messages counter by reason."""
        self.messages_filtered[reason] = self.messages_filtered.get(reason, 0) + 1

    # New metric methods for suggestion features
    def increment_reaction_searches(self) -> None:
        """Increment reaction-based searches counter."""
        self.reaction_searches += 1

    def increment_slash_commands(self) -> None:
        """Increment slash command uses counter."""
        self.slash_commands += 1

    def increment_suggestions_shown(self, count: int) -> None:
        """Increment suggestions shown counter.

        Args:
            count: Number of suggestions shown in this interaction
        """
        self.suggestions_shown += count

    def increment_suggestions_clicked(self) -> None:
        """Increment suggestions clicked counter (user clicked 'Post Answer')."""
        self.suggestions_clicked += 1

    # New metric methods for status monitoring
    def increment_status_updates_cached(self) -> None:
        """Increment status updates cached counter."""
        self.status_updates_cached += 1

    def increment_status_correlations_shown(self) -> None:
        """Increment status correlations shown counter."""
        self.status_correlations_shown += 1

    # Calculated metrics
    def suggestion_ctr(self) -> float:
        """Calculate click-through rate for suggestions.

        Returns:
            CTR as a percentage (0-100), or 0 if no suggestions shown
        """
        if self.suggestions_shown == 0:
            return 0.0
        return (self.suggestions_clicked / self.suggestions_shown) * 100

    def summary(self) -> str:
        """Get metrics summary."""
        lines = [
            "Bot Metrics:",
            f"  Questions detected: {self.questions_detected}",
            f"  Answers sent: {self.answers_sent}",
            f"  Answers skipped: {self.answers_skipped}",
            f"  Errors: {self.errors}",
            "  Messages filtered:",
        ]
        for reason, count in self.messages_filtered.items():
            lines.append(f"    {reason}: {count}")

        # Add suggestion metrics
        lines.extend(
            [
                "",
                "Suggestion Features:",
                f"  Reaction searches: {self.reaction_searches}",
                f"  Slash commands: {self.slash_commands}",
                f"  Suggestions shown: {self.suggestions_shown}",
                f"  Suggestions clicked: {self.suggestions_clicked}",
                f"  Click-through rate: {self.suggestion_ctr():.1f}%",
            ]
        )

        # Add status monitoring metrics
        lines.extend(
            [
                "",
                "Status Monitoring:",
                f"  Status updates cached: {self.status_updates_cached}",
                f"  Status correlations shown: {self.status_correlations_shown}",
            ]
        )

        return "\n".join(lines)
