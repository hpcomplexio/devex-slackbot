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
        return "\n".join(lines)
