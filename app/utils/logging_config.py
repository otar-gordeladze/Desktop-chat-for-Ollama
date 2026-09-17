"""Logging configuration."""
from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Configure concise console logging for development and packaged builds."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
