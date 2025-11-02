"""Command-line interface for data ingestion, validation, and serving."""

from __future__ import annotations

import logging
from typing import Optional

import click
import pandas as pd

from .app import app
from .config import get_settings
from .data_loader import MORTALITY_SCHEMA, get_parquet_engine, load_data
from .logging import configure_logging

LOGGER = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Mortality dashboard utilities."""
    configure_logging()


@cli.command()
@click.option("--force", is_flag=True, help="Ignora caché y rehace la ingestión.")
def ingest(force: bool) -> None:
    """Run data ingestion pipeline and persist parquet output."""
    settings = get_settings()
    LOGGER.info("Iniciando ingestión (force=%s)", force)
    df = load_data(force_refresh=force)
    cache_path = settings.data_dir.parent / "processed" / "mortalidad_2019.parquet"
    click.echo(f"Datos procesados: {len(df)} filas → {cache_path}")


@cli.command()
def validate() -> None:
    """Validate processed dataset against Pandera schema."""
    settings = get_settings()
    cache_path = settings.data_dir.parent / "processed" / "mortalidad_2019.parquet"
    if not cache_path.exists():
        raise click.ClickException(
            f"No se encontró {cache_path}. Ejecuta primero `mortalidad ingest`."
        )
    df = pd.read_parquet(cache_path, engine=get_parquet_engine())
    MORTALITY_SCHEMA.validate(df, lazy=True)
    click.echo(f"Validación exitosa: {len(df)} registros cumplen el esquema.")


@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", type=int, default=None, help="Puerto HTTP para servir la app.")
@click.option("--debug/--no-debug", default=None, help="Activa modo depuración.")
def serve(host: str, port: Optional[int], debug: Optional[bool]) -> None:
    """Launch the Dash development server."""
    settings = get_settings()
    run_port = port or settings.port
    run_debug = debug if debug is not None else settings.is_development
    click.echo(f"Sirviendo en http://{host}:{run_port} (debug={run_debug})")
    app.run(host=host, port=run_port, debug=run_debug)


if __name__ == "__main__":
    cli()
