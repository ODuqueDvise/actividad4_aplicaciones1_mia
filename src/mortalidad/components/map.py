"""Map component for geospatial visualizations."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from ..config import get_settings

SETTINGS = get_settings()


def _normalize_code(value: Any, width: int) -> str:
    text = "" if value is None else str(value).strip()
    digits = "".join(char for char in text if char.isdigit())
    return digits.zfill(width)


@lru_cache(maxsize=1)
def _reference_coordinates() -> pd.DataFrame:
    """Load static municipality coordinates as a fallback for missing values."""
    settings = get_settings()
    candidates = [
        settings.data_dir / "dane_municipios.csv",
        settings.data_dir.parent / "dane_municipios.csv",
    ]
    csv_path: Path | None = None
    for path in candidates:
        if path.exists():
            csv_path = path
            break
    if csv_path is None:
        return pd.DataFrame(columns=["muni_cod", "lat", "lon", "depto", "depto_cod"])

    coords = pd.read_csv(csv_path, dtype=str, encoding="utf-8")
    coords = coords.rename(
        columns={
            "COD_DPTO": "depto_cod",
            "NOM_DPTO": "depto",
            "COD_MPIO": "muni_cod",
            "NOM_MPIO": "municipio",
            "LATITUD": "lat",
            "LONGITUD": "lon",
        }
    )
    coords["depto_cod"] = coords["depto_cod"].map(lambda value: _normalize_code(value, width=2))
    coords["muni_cod"] = coords["muni_cod"].map(lambda value: _normalize_code(value, width=5))
    coords["depto"] = coords["depto"].astype("string").str.strip().str.title()
    coords["municipio"] = coords["municipio"].astype("string").str.strip().str.title()
    coords["lat"] = pd.to_numeric(coords["lat"], errors="coerce")
    coords["lon"] = pd.to_numeric(coords["lon"], errors="coerce")
    return coords.dropna(subset=["lat", "lon"])


def _fill_missing_coordinates(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the dataset with missing coordinates filled when possible."""
    dataset = data.copy()
    dataset["lat"] = pd.to_numeric(dataset.get("lat"), errors="coerce")
    dataset["lon"] = pd.to_numeric(dataset.get("lon"), errors="coerce")

    if {"muni_cod"}.issubset(dataset.columns):
        reference = _reference_coordinates()
        if not reference.empty:
            dataset = dataset.merge(
                reference[["muni_cod", "lat", "lon"]],
                on="muni_cod",
                how="left",
                suffixes=("", "_ref"),
            )
            dataset["lat"] = dataset["lat"].fillna(dataset["lat_ref"])
            dataset["lon"] = dataset["lon"].fillna(dataset["lon_ref"])
            dataset = dataset.drop(columns=[col for col in dataset.columns if col.endswith("_ref")])

    return dataset


def _compute_bounds(data: pd.DataFrame) -> Tuple[float, float, float, float]:
    """Return latitude and longitude bounds with a safety margin."""
    lat_min = float(data["lat"].min())
    lat_max = float(data["lat"].max())
    lon_min = float(data["lon"].min())
    lon_max = float(data["lon"].max())
    lat_margin = max(0.8, (lat_max - lat_min) * 0.2)
    lon_margin = max(0.8, (lon_max - lon_min) * 0.2)
    return (
        lat_min - lat_margin,
        lat_max + lat_margin,
        lon_min - lon_margin,
        lon_max + lon_margin,
    )


def _marker_sizes(totals: pd.Series, *, min_size: float = 8.0, max_size: float = 28.0) -> list[float]:
    """Scale bubble sizes proportionally to the totals."""
    if totals.empty:
        return []
    min_total = float(totals.min())
    max_total = float(totals.max())
    if max_total <= 0:
        return [min_size] * len(totals)
    if max_total == min_total:
        midpoint = (min_size + max_size) / 2
        return [midpoint] * len(totals)
    normalized = (totals - min_total) / (max_total - min_total)
    scaled = min_size + normalized * (max_size - min_size)
    return scaled.tolist()


def _estimate_zoom(lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> float:
    """Estimate a zoom level that keeps Colombia in view."""
    lat_span = max(lat_max - lat_min, 1.0)
    lon_span = max(lon_max - lon_min, 1.0)
    max_span = max(lat_span, lon_span)
    zoom = 5.4 - (max_span / 9.0)
    return max(4.0, min(6.2, zoom))


def _aggregate_by_department(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate records by department computing totals and centroid averages."""
    return (
        data.groupby(["depto_cod", "depto"], dropna=False, as_index=False)
        .agg(
            total=("causa_cod", "size"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
        .sort_values("total", ascending=False)
    )


def _aggregate_by_municipality(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate records by municipality to provide more granular markers."""
    return (
        data.groupby(["depto_cod", "depto", "muni_cod", "municipio"], dropna=False, as_index=False)
        .agg(
            total=("causa_cod", "size"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
        .sort_values("total", ascending=True)
    )


def build_choropleth_figure(
    data: pd.DataFrame,
    *,
    geojson: Dict[str, Any] | None = None,
    title: str = "Mapa coroplético por departamento",
) -> go.Figure:
    """Return a choropleth or scattergeo map describing mortality by department."""
    if data.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            title=title,
            annotations=[
                dict(
                    text="Sin datos para filtros seleccionados",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#5f6b7a"),
                )
            ],
        )
        return fig

    dataset = _fill_missing_coordinates(data)

    required = {"depto_cod", "depto", "muni_cod", "municipio", "lat", "lon", "causa_cod"}
    if not required.issubset(dataset.columns):
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            title=title,
            annotations=[
                dict(
                    text="Sin datos para filtros seleccionados",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#5f6b7a"),
                )
            ],
        )
        return fig

    dept_aggregated = _aggregate_by_department(dataset)
    dept_aggregated = dept_aggregated.dropna(subset=["lat", "lon"])
    muni_aggregated = _aggregate_by_municipality(dataset)
    muni_aggregated = muni_aggregated.dropna(subset=["lat", "lon"])

    if muni_aggregated.empty and not dept_aggregated.empty:
        muni_aggregated = dept_aggregated.assign(
            muni_cod=lambda frame: frame["depto_cod"],
            municipio=lambda frame: frame["depto"],
        )

    if dept_aggregated.empty and muni_aggregated.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            title=title,
            annotations=[
                dict(
                    text="Sin datos para filtros seleccionados",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#5f6b7a"),
                )
            ],
        )
        return fig

    reference_for_bounds = muni_aggregated if not muni_aggregated.empty else dept_aggregated
    lat_min, lat_max, lon_min, lon_max = _compute_bounds(reference_for_bounds)
    center_lat = float(reference_for_bounds["lat"].mean())
    center_lon = float(reference_for_bounds["lon"].mean())
    zoom = _estimate_zoom(lat_min, lat_max, lon_min, lon_max)

    figure = go.Figure()

    show_department_layer = (
        not dept_aggregated.empty
        and dept_aggregated["depto_cod"].dropna().nunique() > 1
        and geojson
        and geojson.get("features")
    )

    if show_department_layer:
        figure.add_trace(
            go.Choroplethmapbox(
                geojson=geojson,
                featureidkey="properties.depto_cod",
                locations=dept_aggregated["depto_cod"],
                z=dept_aggregated["total"],
                text=dept_aggregated["depto"],
                colorscale="Viridis",
                zmin=float(dept_aggregated["total"].min()),
                zmax=float(dept_aggregated["total"].max()),
                hovertemplate="%{text}<br>Total: %{z:,} muertes<extra></extra>",
                marker_line_width=0.5,
                marker_line_color="#f2f5f9",
                name="Departamentos",
                colorbar=dict(title="Defunciones"),
                legendgroup="departamentos",
            )
        )

    if not muni_aggregated.empty:
        size_min, size_max = (10, 28) if show_department_layer else (8, 26)
        marker_sizes = _marker_sizes(muni_aggregated["total"], min_size=size_min, max_size=size_max)
        hover_text = [
            f"{row.municipio} ({row.depto})<br>Total: {row.total:,} muertes"
            for row in muni_aggregated.itertuples()
        ]
        total_min = float(muni_aggregated["total"].min())
        total_max = float(muni_aggregated["total"].max())
        showscale = total_max != total_min and not show_department_layer
        marker_kwargs: dict[str, Any] = {
            "size": marker_sizes,
            "color": muni_aggregated["total"],
            "opacity": 0.82,
        }
        if showscale:
            marker_kwargs.update(
                {
                    "colorscale": "Viridis",
                    "cmin": total_min,
                    "cmax": total_max,
                    "showscale": True,
                    "colorbar": dict(title="Defunciones"),
                }
            )
        else:
            marker_kwargs["color"] = "#2b6cb0"

        figure.add_trace(
            go.Scattermapbox(
                lat=muni_aggregated["lat"],
                lon=muni_aggregated["lon"],
                text=hover_text,
                marker=marker_kwargs,
                hovertemplate="%{text}<extra></extra>",
                mode="markers",
                name="Municipios",
                showlegend=False,
            )
        )

    mapbox_config: dict[str, Any] = {
        "style": "open-street-map",
        "center": {
            "lat": center_lat if not pd.isna(center_lat) else 4.5,
            "lon": center_lon if not pd.isna(center_lon) else -74.1,
        },
        "zoom": zoom,
        "bearing": 0,
        "pitch": 0,
    }
    if SETTINGS.mapbox_token:
        mapbox_config["accesstoken"] = SETTINGS.mapbox_token

    figure.update_layout(mapbox=mapbox_config, uirevision="colombia-map")

    figure.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=10),
        title=title,
    )
    return figure


def render(
    data: pd.DataFrame | None = None,
    *,
    geojson: Dict[str, Any] | None = None,
    title: str | None = None,
) -> html.Div:
    """Render the choropleth card using the provided dataset."""
    dataset = data if data is not None else pd.DataFrame()
    figure = build_choropleth_figure(
        dataset,
        geojson=geojson,
        title=title or "Mapa coroplético por departamento",
    )
    return html.Div(
        className="card-content",
        children=[
            dcc.Graph(
                id="mortality-map",
                figure=figure,
                style={"width": "100%", "height": "100%", "minHeight": "360px"},
                config={
                    "displaylogo": False,
                    "responsive": True,
                    "scrollZoom": True,
                    "modeBarButtonsToAdd": [
                        "zoomInMapbox",
                        "zoomOutMapbox",
                        "resetViewMapbox",
                    ],
                    "modeBarButtonsToRemove": ["toggleSpikelines"],
                },
            ),
        ],
    )


__all__ = ["build_choropleth_figure", "render"]
