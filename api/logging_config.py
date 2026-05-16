"""Centralized logging configuration for WebScraper."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "webscraper.log"


def setup_logging(level: str = "INFO"):
    """Configure root logger with file + console output."""
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler (rotating, 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    root = logging.getLogger("webscraper")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Also configure child loggers
    for name in ["scraper", "scheduler", "api"]:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

    return LOG_FILE


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the webscraper namespace."""
    return logging.getLogger(f"webscraper.{name}")
