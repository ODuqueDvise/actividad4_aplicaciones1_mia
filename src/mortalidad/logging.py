"""Logging configuration module with structured output."""

from __future__ import annotations

import json
import logging
from logging import config as logging_config
from typing import Any

from dash import Dash

from .config import get_settings


class JsonFormatter(logging.Formatter):
    """Serialize log records as JSON strings for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _development_config() -> dict[str, Any]:
    """Return logging configuration for development environments."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": "DEBUG",
            }
        },
        "root": {"level": "DEBUG", "handlers": ["console"]},
    }


def _production_config() -> dict[str, Any]:
    """Return logging configuration for production environments."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JsonFormatter,
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            }
        },
        "handlers": {
            "json": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": "INFO",
            }
        },
        "root": {"level": "INFO", "handlers": ["json"]},
    }


def configure_logging() -> None:
    """Configure logging based on the current environment."""
    settings = get_settings()
    config = _production_config() if settings.is_production else _development_config()
    logging_config.dictConfig(config)


def register_exception_handlers(app: Dash) -> None:
    """Attach exception handlers to the underlying Flask application."""
    server = app.server

    @server.errorhandler(Exception)  # type: ignore[misc]
    def handle_exception(error: Exception) -> tuple[str, int]:
        logging.exception("Unhandled exception", exc_info=error)
        message = (
            '<div style="padding:2rem;font-family:Inter,sans-serif;">'
            "<h1>Algo salió mal</h1>"
            "<p>Ocurrió un error inesperado. Intenta recargar la página o "
            "contáctanos si persiste.</p>"
            "</div>"
        )
        return message, 500


__all__ = ["configure_logging", "register_exception_handlers", "JsonFormatter"]
