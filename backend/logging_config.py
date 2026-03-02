"""Structured logging configuration with request ID tracking for Sanad AI backend."""

import logging
import sys
import uuid
from contextvars import ContextVar

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    """Inject request_id into every log record."""
    def filter(self, record):
        record.request_id = request_id_var.get("-")
        return True


def setup_logging():
    """Configure structured logging with request ID tracking."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s]: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
        force=True,
    )

    # Add request ID filter to root logger
    root = logging.getLogger()
    root.addFilter(RequestIDFilter())

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
