"""Central logging configuration for the AION POC project."""

from __future__ import annotations

import logging
from logging.config import dictConfig
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from .config.settings import get_settings


STANDARD_LOG_RECORD_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
    "taskName",
}


class StructuredFormatter(logging.Formatter):
    """Formatter that appends any custom ``extra`` key-values to the message."""

    def format(self, record: logging.LogRecord) -> str:
        base_message = super().format(record)

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in STANDARD_LOG_RECORD_KEYS and not key.startswith("_")
        }

        if not extras:
            return base_message

        rendered_pairs = " ".join(f"{key}={value!r}" for key, value in sorted(extras.items()))
        return f"{base_message} | {rendered_pairs}"


_config_lock = Lock()
_config_state = {"configured": False}


def _resolve_log_file(base_path: Path, file_path: Path | None) -> Path | None:
    if file_path is None:
        return None
    if file_path.is_absolute():
        return file_path
    return (base_path / file_path).resolve()


def configure_logging(force: bool = False) -> None:
    """Configure application-wide logging using project settings."""

    if _config_state["configured"] and not force:
        return

    with _config_lock:
        if _config_state["configured"] and not force:
            return

        settings = get_settings()
        logging_settings = settings.logging

        level = logging_settings.level.upper()
        formatter_config: Dict[str, Any] = {
            "()": "aion_poc.logging_config.StructuredFormatter",
            "format": logging_settings.format,
            "datefmt": logging_settings.datefmt,
        }

        handlers: Dict[str, Any] = {}
        root_handlers: list[str] = []

        if logging_settings.enable_console:
            handlers["console"] = {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            }
            root_handlers.append("console")

        log_file_path: Path | None = None
        if logging_settings.enable_file:
            if logging_settings.log_file is not None:
                log_file_path = _resolve_log_file(settings.project_root, logging_settings.log_file)
            else:
                resolved_dir = _resolve_log_file(settings.project_root, logging_settings.log_dir)
                if resolved_dir is None:
                    raise ValueError("Could not resolve log directory")
                log_file_path = resolved_dir / logging_settings.log_filename

            if log_file_path is None:
                raise ValueError("File logging is enabled but no log file path could be determined")

            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "standard",
                "filename": str(log_file_path),
                "maxBytes": logging_settings.max_bytes,
                "backupCount": logging_settings.backup_count,
                "encoding": "utf-8",
            }
            root_handlers.append("file")

        if not root_handlers:
            raise ValueError("Logging configuration must enable at least one handler")

        config: Dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": formatter_config,
            },
            "handlers": handlers,
            "root": {
                "level": level,
                "handlers": root_handlers,
            },
        }

        dictConfig(config)
        logging.captureWarnings(True)
        logging.getLogger().propagate = logging_settings.propagate

        _config_state["configured"] = True
