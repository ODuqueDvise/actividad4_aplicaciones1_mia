"""Smoke tests for the Dash application."""

from dash import Dash

from mortalidad.app import app, create_app


def test_create_app_returns_dash_instance() -> None:
    """Ensure the factory creates a Dash app."""
    test_app = create_app()
    assert isinstance(test_app, Dash)
    assert test_app.server is not None


def test_index_returns_success() -> None:
    """Ensure the root endpoint is reachable."""
    client = app.server.test_client()
    response = client.get("/")
    assert response.status_code == 200
