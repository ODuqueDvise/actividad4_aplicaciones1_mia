"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from mortalidad import cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_ingest_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path) -> None:
    sample_df = pd.DataFrame({"value": [1, 2, 3]})

    monkeypatch.setattr(cli, "load_data", lambda force_refresh=False: sample_df)
    settings = cli.get_settings()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    new_settings = settings.model_copy(update={"data_dir": raw_dir})
    monkeypatch.setattr(cli, "get_settings", lambda: new_settings)

    result = runner.invoke(cli.cli, ["ingest"])

    assert result.exit_code == 0
    assert "Datos procesados" in result.output


def test_validate_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True)
    cache_path = processed_dir / "mortalidad_2019.parquet"
    df = pd.DataFrame({
        "depto_cod": ["11"],
        "depto": ["Bogotá"],
        "muni_cod": ["11001"],
        "municipio": ["Bogotá"],
        "sexo": ["M"],
        "grupo_edad": [5],
        "grupo_edad_label": ["15 a 19 años"],
        "fecha": pd.to_datetime(["2019-01-01"]),
        "anio": [2019],
        "mes": [1],
        "causa_cod": ["X95"],
        "causa": ["Homicidio"],
        "homicidio_x95": [1],
        "lat": [4.7],
        "lon": [-74.0],
    })
    df.to_parquet(cache_path)

    settings = cli.get_settings()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    new_settings = settings.model_copy(update={"data_dir": raw_dir})
    monkeypatch.setattr(cli, "get_settings", lambda: new_settings)

    result = runner.invoke(cli.cli, ["validate"])

    assert result.exit_code == 0
    assert "Validación exitosa" in result.output


def test_validate_without_file(monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path) -> None:
    settings = cli.get_settings()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    new_settings = settings.model_copy(update={"data_dir": raw_dir})
    monkeypatch.setattr(cli, "get_settings", lambda: new_settings)

    result = runner.invoke(cli.cli, ["validate"])

    assert result.exit_code != 0
    assert "Ejecuta primero" in result.output


def test_serve_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path) -> None:
    calls: dict[str, dict[str, object]] = {}

    class DummyApp:
        def run(self, host: str, port: int, debug: bool) -> None:  # type: ignore[override]
            calls["run"] = {"host": host, "port": port, "debug": debug}

    monkeypatch.setattr(cli, "app", DummyApp())
    settings = cli.get_settings()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    new_settings = settings.model_copy(update={"port": 9000, "env": "development", "data_dir": raw_dir})
    monkeypatch.setattr(cli, "get_settings", lambda: new_settings)

    result = runner.invoke(cli.cli, ["serve", "--host", "127.0.0.1", "--port", "8100", "--debug"])

    assert result.exit_code == 0
    assert calls["run"] == {"host": "127.0.0.1", "port": 8100, "debug": True}
