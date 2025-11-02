"""Map component for geospatial visualizations."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html


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

    required = {"depto_cod", "depto", "lat", "lon", "causa_cod"}
    if not required.issubset(data.columns):
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

    aggregated = _aggregate_by_department(data)

    if geojson and geojson.get("features"):
        figure = go.Figure(
            go.Choropleth(
                locations=aggregated["depto_cod"],
                z=aggregated["total"],
                text=aggregated["depto"],
                featureidkey="properties.depto_cod",
                geojson=geojson,
                colorscale="Reds",
                marker_line_color="#f2f5f9",
                colorbar_title="Defunciones",
                hovertemplate="%{text}<br>Total: %{z:,} muertes<extra></extra>",
            )
        )
        figure.update_geos(fitbounds="locations", visible=False)
    else:
        marker_sizes = (
            aggregated["total"]
            .clip(lower=1)
            .pow(0.6)
            .mul(12)
            .tolist()
        )
        hover_text = [
            f"{row.depto}<br>Total: {row.total:,} muertes"
            for row in aggregated.itertuples()
        ]
        figure = go.Figure(
            go.Scattergeo(
                lat=aggregated["lat"],
                lon=aggregated["lon"],
                text=hover_text,
                marker=dict(
                    size=marker_sizes,
                    color=aggregated["total"],
                    colorscale="Reds",
                    reversescale=False,
                    colorbar=dict(title="Defunciones"),
                    opacity=0.85,
                ),
                hovertemplate="%{text}<extra></extra>",
            )
        )
        figure.update_geos(
            scope="south america",
            showcountries=True,
            countrycolor="#aab2bd",
            showland=True,
            landcolor="#fdfdfd",
        )

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
                config={"displaylogo": False, "responsive": True},
            ),
        ],
    )


__all__ = ["build_choropleth_figure", "render"]
