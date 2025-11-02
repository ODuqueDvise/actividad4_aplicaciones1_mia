"""Tests for data ingestion pipeline."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from mortalidad import data_loader
from mortalidad.data_loader import MORTALITY_SCHEMA

EXPECTED_COLUMNS = [
    "depto_cod",
    "depto",
    "muni_cod",
    "municipio",
    "sexo",
    "grupo_edad",
    "grupo_edad_label",
    "fecha",
    "anio",
    "mes",
    "causa_cod",
    "causa",
    "homicidio_x95",
    "lat",
    "lon",
]


@pytest.fixture()
def synthetic_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create synthetic Excel inputs and patch settings."""
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)

    records_df = pd.DataFrame(
        {
            "DPTO_OCURRE": [11],
            "MUN_OCURRE": [11001],
            "SEXO": ["M"],
            "GRUPO_EDAD1": [5],
            "FECHA_DEF": [pd.Timestamp("2019-05-10")],
            "CAUSA_DEF": ["x95"],
        }
    )
    causes_df = pd.DataFrame(
        {
            "CODIGO": ["X95"],
            "DESCRIPCION": ["Agresión con arma de fuego (homicidio)"],
        }
    )
    divipola_df = pd.DataFrame(
        {
            "COD_DEPTO": [11],
            "NOM_DEPTO": ["Bogotá D.C."],
            "COD_MPIO": [11001],
            "NOM_MPIO": ["Bogotá D.C."],
            "LAT": [4.711],
            "LON": [-74.0721],
        }
    )

    records_df.to_excel(raw_dir / "NoFetal2019.xlsx", index=False, engine="openpyxl")
    causes_df.to_excel(raw_dir / "CodigosDeMuerte.xlsx", index=False, engine="openpyxl")
    divipola_df.to_excel(raw_dir / "Divipola.xlsx", index=False, engine="openpyxl")

    settings_stub = SimpleNamespace(data_dir=raw_dir, env="test", port=8050)
    monkeypatch.setattr(data_loader, "get_settings", lambda: settings_stub)

    return raw_dir


def test_load_data_processes_and_caches(synthetic_env: Path) -> None:
    """Ensure the pipeline processes inputs and stores cache."""
    df = data_loader.load_data(force_refresh=True)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 1

    record = df.iloc[0]
    assert record["depto_cod"] == "11"
    assert record["depto"] == "Bogotá D.C."
    assert record["muni_cod"] == "11001"
    assert record["municipio"] == "Bogotá D.C."
    assert record["sexo"] == "M"
    assert record["grupo_edad"] == 5
    assert record["grupo_edad_label"] == "15 a 19 años"
    assert record["anio"] == 2019
    assert record["mes"] == 5
    assert record["causa_cod"] == "X95"
    assert record["causa"] == "Agresión con arma de fuego (homicidio)"
    assert record["homicidio_x95"] == 1
    assert pytest.approx(record["lat"], rel=1e-4) == 4.711
    assert pytest.approx(record["lon"], rel=1e-4) == -74.0721

    cache_path = synthetic_env.parent / "processed" / "mortalidad_2019.parquet"
    assert cache_path.exists()

    validated = MORTALITY_SCHEMA.validate(df.copy())
    assert len(validated) == 1


def test_load_data_reuses_cache(synthetic_env: Path) -> None:
    """Ensure cache is reused when source files remain unchanged."""
    cache_path = synthetic_env.parent / "processed" / "mortalidad_2019.parquet"
    data_loader.load_data(force_refresh=True)
    mtime_before = cache_path.stat().st_mtime

    df_cached = data_loader.load_data()
    mtime_after = cache_path.stat().st_mtime

    assert mtime_after == mtime_before
    assert len(df_cached) == 1
    assert df_cached.iloc[0]["causa_cod"] == "X95"
