"""Structured logging setup."""

import logging
import sys
from typing import Any, Dict


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured logging for the application."""
    logger = logging.getLogger("faqbot")
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Format: timestamp - level - message
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


def log_event(logger: logging.Logger, event: str, **kwargs: Any) -> None:
    """Log a structured event with context."""
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"{event} | {context}")


def log_error(logger: logging.Logger, error: str, **kwargs: Any) -> None:
    """Log an error with context."""
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(f"{error} | {context}")
