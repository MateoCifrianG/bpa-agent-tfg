"""
Structured JSON logging for BPA-Agent.
Call setup_logging() once at startup; all loggers inherit the config.
"""
import logging
import json
import sys
import time
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """Emits each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        # Include any extra fields passed via logger.info(..., extra={...})
        _SKIP = {
            "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "name", "message",
        }
        for key, val in record.__dict__.items():
            if key not in _SKIP and not key.startswith("_"):
                doc[key] = val
        return json.dumps(doc, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure root logger. Called once from lifespan."""
    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# Module-level logger for convenience
logger = logging.getLogger("bpa")
