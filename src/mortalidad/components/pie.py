"""Pie chart component."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import dcc, html
from plotly.graph_objects import Figure


def build_lowest_mortality_pie(
    data: pd.DataFrame,
    *,
    top_n: int = 10,
    title: str = "10 ciudades con menor mortalidad",
) -> Figure:
    """Return a pie chart with the cities that have the lowest mortality counts."""
    required = {"municipio", "muni_cod", "causa_cod"}
    if data.empty or not required.issubset(data.columns):
        figure = Figure()
        figure.update_layout(
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
        return figure

    totals = (
        data.groupby(["muni_cod", "municipio"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values("total", ascending=True)
        .head(top_n)
    )
    figure = px.pie(
        totals,
        names="municipio",
        values="total",
        title=title,
        hole=0.35,
    )
    figure.update_traces(
        textinfo="label+percent",
        hovertemplate=(
            "%{label}<br>Total: %{value:,} muertes (%{percent})<extra></extra>"
        ),
    )
    figure.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=10),
        height=360,
        legend_title="Municipio",
    )
    return figure


def render(data: pd.DataFrame | None = None, title: str | None = None) -> html.Div:
    """Render the pie chart card for the lowest mortality cities."""
    dataset = data if data is not None else pd.DataFrame()
    figure = build_lowest_mortality_pie(
        dataset,
        title=title or "10 ciudades con menor mortalidad",
    )
    return html.Div(
        className="card-content",
        children=[
            dcc.Graph(
                id="mortality-pie",
                figure=figure,
                style={"width": "100%", "height": "100%", "minHeight": "320px"},
                config={"displaylogo": False, "responsive": True},
            ),
        ],
    )


__all__ = ["build_lowest_mortality_pie", "render"]
