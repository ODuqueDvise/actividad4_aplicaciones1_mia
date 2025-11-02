"""Paquete principal para la aplicación mortalidad-colombia-2019."""

from importlib import metadata
from importlib.metadata import PackageNotFoundError


def get_version() -> str:
    """Return the package version installed in the environment."""
    try:
        return metadata.version("mortalidad-colombia-2019")
    except PackageNotFoundError:
        return "0.0.0"


__all__ = ["get_version"]
