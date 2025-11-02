"""Smoke tests to validate package importability."""

from mortalidad import get_version


def test_get_version_returns_string() -> None:
    """Ensure get_version returns a non-empty string."""
    version = get_version()
    assert isinstance(version, str)
    assert version != ""
