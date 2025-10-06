"""Helper utilities shared by CLI entrypoints."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "[%(asctime)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_CHOICES: tuple[str, ...] = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")


def configure_logger(name: str, level: str) -> logging.Logger:
    """Configure and return a logger that writes to stdout."""

    numeric_level = getattr(logging, level.upper())
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(numeric_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    logger.addHandler(handler)
    logger.propagate = False
    return logger


__all__ = ["configure_logger", "LOG_LEVEL_CHOICES"]
