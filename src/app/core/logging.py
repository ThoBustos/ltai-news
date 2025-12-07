"""Loguru logging configuration."""

import os
import sys
from pathlib import Path

from loguru import logger

# Remove default handler
logger.remove()

# Get log level from environment, default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure console handler with colors
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
)

# Optional: Add file handler for production (rotating logs)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",  # Keep logs for 30 days
    compression="zip",  # Compress old logs
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=LOG_LEVEL,
    enqueue=True,  # Thread-safe logging
)


def setup_logging() -> None:
    """Initialize logging configuration."""
    logger.info(f"Logging initialized with level: {LOG_LEVEL}")


# Export logger instance
__all__ = ["logger", "setup_logging"]

