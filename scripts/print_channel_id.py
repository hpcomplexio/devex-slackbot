"""Utility script to print Slack channel IDs."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from faqbot.config import Config
from slack_bolt import App


def main():
    """List channels and their IDs."""
    try:
        # Load config
        config = Config.from_env()

        # Create Slack app
        app = App(token=config.slack_bot_token)

        # List conversations
        print("Fetching channels...")
        result = app.client.conversations_list(types="public_channel,private_channel")

        channels = result["channels"]
        print(f"\n Found {len(channels)} channels:\n")
        print(f"{'Channel Name':<30} Channel ID")
        print("-" * 60)

        for channel in sorted(channels, key=lambda c: c["name"]):
            name = channel["name"]
            channel_id = channel["id"]
            print(f"{name:<30} {channel_id}")

        print("\nAdd channel IDs to SLACK_ALLOWED_CHANNELS in your .env file")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
