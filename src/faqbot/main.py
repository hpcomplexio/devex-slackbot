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
from .status.cache import StatusUpdateCache
from .search.suggestions import FAQSuggestionService


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

            # Use API key if available, otherwise fall back to OAuth
            if config.notion_api_key:
                self.logger.info("Using Notion API key authentication")
                self.content_source = NotionClient(config.notion_api_key)
            else:
                from .mcp.token_manager import NotionTokenManager
                self.logger.info("Using Notion OAuth authentication")
                token_manager = NotionTokenManager(
                    config.notion_oauth_client_id,
                    config.notion_oauth_client_secret,
                    config.notion_oauth_refresh_token
                )
                self.content_source = NotionClient(token_manager)
        else:  # markdown
            self.content_source = None  # No API client needed for markdown

        self.embedding_model = EmbeddingModel()

        # Create BM25 index if hybrid search is enabled
        bm25_index = None
        if config.hybrid_search_enabled:
            from .retrieval.bm25_index import BM25Index
            bm25_index = BM25Index()
            self.logger.info("Hybrid search enabled - BM25 index will be built with FAQs")

        self.vector_store = VectorStore(
            dimension=self.embedding_model.dimension,
            bm25_index=bm25_index
        )
        self.claude_client = ClaudeClient(config.anthropic_api_key)
        self.thread_tracker = ThreadTracker()
        self.metrics = BotMetrics()

        # Create status update cache (Phase 1)
        self.status_cache = StatusUpdateCache(ttl_hours=config.status_cache_ttl_hours)

        # Initial FAQ sync
        self.logger.info("Performing initial FAQ sync...")
        self.sync_faq()

        # Create FAQ suggestion service (Phase 2)
        self.suggestion_service = FAQSuggestionService(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
            min_similarity=config.suggestion_min_similarity,
        )

        # Create reranked search if enabled
        reranked_search = None
        if config.reranking_enabled:
            from .retrieval.reranker import CrossEncoderReranker, RerankedSearch

            self.logger.info(
                f"Reranking enabled - using model: {config.reranking_model}"
            )
            reranker = CrossEncoderReranker(model_name=config.reranking_model)

            reranked_search = RerankedSearch(
                base_search=self.vector_store,
                reranker=reranker,
                embedding_model=self.embedding_model,
                retrieval_top_k=config.reranking_retrieval_top_k,
                rerank_top_k=config.reranking_top_k,
                use_hybrid=config.hybrid_search_enabled,
                hybrid_semantic_top_k=config.hybrid_semantic_top_k,
                hybrid_bm25_top_k=config.hybrid_bm25_top_k,
            )

        # Create pipeline with status cache, hybrid search, and reranking (Phase 3)
        self.pipeline = AnswerPipeline(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
            claude_client=self.claude_client,
            top_k=config.top_k,
            min_similarity=config.min_similarity,
            min_gap=config.min_gap,
            status_cache=self.status_cache,
            hybrid_search_enabled=config.hybrid_search_enabled,
            hybrid_semantic_top_k=config.hybrid_semantic_top_k,
            hybrid_bm25_top_k=config.hybrid_bm25_top_k,
            reranked_search=reranked_search,
        )

        # Create Slack app with all handlers (Phase 4-5)
        self.app, self.handler = create_slack_app(
            config=config,
            pipeline=self.pipeline,
            suggestion_service=self.suggestion_service,
            status_cache=self.status_cache,
            thread_tracker=self.thread_tracker,
            metrics=self.metrics,
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
