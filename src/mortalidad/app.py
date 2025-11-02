"""Dash application entry point."""

from __future__ import annotations

import logging

from dash import Dash

from .callbacks import register_callbacks
from .config import get_settings
from .layout import build_layout
from .logging import configure_logging, register_exception_handlers

LOGGER = logging.getLogger(__name__)


def create_app() -> Dash:
    """Factory that builds and configures the Dash application."""
    configure_logging()
    settings = get_settings()
    LOGGER.info("Creating Dash app in %s mode", settings.env)
    app = Dash(
        __name__,
        title="Mortalidad Colombia 2019",
        suppress_callback_exceptions=True,
    )
    register_exception_handlers(app)
    app.layout = build_layout(app)
    register_callbacks(app)
    return app


app: Dash = create_app()
server = app.server


def main() -> None:
    """Launch the Dash development server."""
    settings = get_settings()
    LOGGER.info("Starting server on port %s", settings.port)
    app.run_server(
        host="0.0.0.0",
        port=settings.port,
        debug=settings.is_development,
    )


if __name__ == "__main__":
    main()
