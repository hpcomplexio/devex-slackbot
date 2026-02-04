"""Claude API wrapper for answer generation."""

from anthropic import Anthropic
from typing import Optional


class ClaudeClient:
    """Wrapper for Claude API."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: Claude 3.5 Sonnet)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def generate_answer(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1000
    ) -> Optional[str]:
        """Generate answer using Claude.

        Args:
            system_prompt: System prompt with instructions
            user_prompt: User prompt with question and context
            max_tokens: Maximum tokens to generate

        Returns:
            Generated answer or None if error
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text

            return None

        except Exception as e:
            raise RuntimeError(f"Claude API error: {e}")
