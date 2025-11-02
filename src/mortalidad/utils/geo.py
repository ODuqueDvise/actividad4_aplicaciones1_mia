"""Geospatial helpers for Divipola codes."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from ..config import get_settings


def normalize_department_code(code: str) -> str:
    """Return a zero-padded department code compatible with Divipola."""
    cleaned = code.strip()
    if not cleaned.isdigit():
        raise ValueError(f"El código '{code}' debe contener solo dígitos.")
    return cleaned.zfill(2)


def load_divipola(
    reader: Callable[[Path], pd.DataFrame] | None = None,
    path: Path | None = None,
) -> pd.DataFrame:
    """Load the Divipola catalog for spatial joins."""
    settings = get_settings()
    catalog_path = path or settings.data_dir / "Divipola.xlsx"
    if reader is None:
        raise NotImplementedError(
            "Proporciona una función lectora (por ejemplo, pandas.read_excel) como argumento."
        )
    return reader(catalog_path)


__all__ = ["normalize_department_code", "load_divipola"]
