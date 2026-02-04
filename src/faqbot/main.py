"""Main entry point for the FAQ bot."""

import asyncio
import signal
import sys
import time
from threading import Thread

from .config import Config
from .logging import setup_logging, log_event, log_error
from .retrieval.embeddings import EmbeddingModel
from .retrieval.store import VectorStore
from .llm.claude import ClaudeClient
from .pipeline.answer import AnswerPipeline
from .slack.app import create_slack_app
from .state.dedupe import ThreadTracker
from .state.metrics import BotMetrics


class FAQBot:
    """Main FAQ bot application."""

    def __init__(self, config: Config):
        """Initialize bot with configuration."""
        self.config = config
        self.logger = setup_logging()
        self.running = True

        # Initialize components
        self.logger.info("Initializing components...")
        self.logger.info(f"FAQ source: {config.faq_source}")

        # Initialize FAQ source-specific client
        if config.faq_source == "notion":
            from .notion.client import NotionClient
            self.content_source = NotionClient(config.notion_api_key)
        else:  # markdown
            self.content_source = None  # No API client needed for markdown

        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore(dimension=self.embedding_model.dimension)
        self.claude_client = ClaudeClient(config.anthropic_api_key)
        self.thread_tracker = ThreadTracker()
        self.metrics = BotMetrics()

        # Initial FAQ sync
        self.logger.info("Performing initial FAQ sync...")
        self.sync_faq()

        # Create pipeline
        self.pipeline = AnswerPipeline(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
            claude_client=self.claude_client,
            top_k=config.top_k,
            min_similarity=config.min_similarity,
            min_gap=config.min_gap,
        )

        # Create Slack app
        self.app, self.handler = create_slack_app(
            bot_token=config.slack_bot_token,
            app_token=config.slack_app_token,
            pipeline=self.pipeline,
            thread_tracker=self.thread_tracker,
            metrics=self.metrics,
            allowed_channels=config.slack_allowed_channels,
            logger=self.logger,
        )

        self.logger.info("✓ Bot initialized successfully")

    def sync_faq(self) -> None:
        """Sync FAQ content from source and update vector store."""
        try:
            start_time = time.time()
            log_event(self.logger, "FAQ sync started")

            # Fetch and chunk content based on source
            if self.config.faq_source == "notion":
                from .notion.chunking import chunk_by_headings

                # Fetch from Notion
                page, blocks = self.content_source.get_page_content(
                    self.config.notion_faq_page_id
                )
                chunks = chunk_by_headings(page, blocks, self.config.notion_faq_page_id)

            else:  # markdown
                from .markdown.reader import read_markdown_file, parse_markdown_blocks
                from .markdown.chunking import chunk_markdown

                # Read and parse markdown file
                content = read_markdown_file(self.config.faq_file_path)
                blocks = parse_markdown_blocks(content)
                chunks = chunk_markdown(blocks, self.config.faq_file_path)

            # Generate embeddings
            chunk_texts = [f"{chunk.heading}\n{chunk.content}" for chunk in chunks]
            embeddings = self.embedding_model.embed_batch(chunk_texts)

            # Update vector store
            self.vector_store.add_chunks(chunks, embeddings)

            elapsed = time.time() - start_time
            log_event(
                self.logger,
                "FAQ sync completed",
                source=self.config.faq_source,
                chunks=len(chunks),
                elapsed_seconds=f"{elapsed:.2f}",
            )

        except Exception as e:
            log_error(self.logger, "FAQ sync failed", error=str(e))
            # Don't crash the bot, just log the error

    def run_background_sync(self) -> None:
        """Run periodic FAQ sync in background."""
        interval_seconds = self.config.faq_sync_interval * 60

        while self.running:
            time.sleep(interval_seconds)
            if self.running:  # Check again after sleep
                self.sync_faq()
                self.logger.info(f"Tracked threads: {self.thread_tracker.size()}")
                self.logger.info(f"\n{self.metrics.summary()}")

    def start(self) -> None:
        """Start the bot."""
        # Start background sync thread
        sync_thread = Thread(target=self.run_background_sync, daemon=True)
        sync_thread.start()

        # Set up signal handlers
        def signal_handler(sig, frame):
            self.logger.info("Shutting down...")
            self.running = False
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start Slack app (blocking)
        self.logger.info("Starting Slack bot...")
        self.logger.info(f"Allowed channels: {', '.join(self.config.slack_allowed_channels)}")
        self.logger.info(f"FAQ sync interval: {self.config.faq_sync_interval} minutes")
        self.logger.info("✓ Bot is running. Press Ctrl+C to stop.")

        try:
            self.handler.start()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self.running = False


def main():
    """Main entry point."""
    try:
        # Load configuration
        config = Config.from_env()
        config.validate()

        # Create and start bot
        bot = FAQBot(config)
        bot.start()

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
