"""Bar chart component."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from plotly.graph_objects import Figure


def build_top_homicide_bars(
    data: pd.DataFrame,
    *,
    top_n: int = 5,
    title: str = "Top 5 ciudades con más homicidios (X95)",
) -> Figure:
    """Return a bar chart with the top cities ranked by homicide X95 counts."""
    required = {"homicidio_x95", "muni_cod", "municipio", "depto", "causa_cod"}
    if data.empty or not required.issubset(data.columns):
        figure = go.Figure()
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

    filtered = data[data["homicidio_x95"] == 1]
    if filtered.empty:
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

    ranked = (
        filtered.groupby(["muni_cod", "municipio", "depto"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values(["total", "municipio"], ascending=[False, True])
        .head(top_n)
    )

    figure = go.Figure(
        go.Bar(
            x=ranked["municipio"],
            y=ranked["total"],
            text=ranked["total"].map(lambda value: f"{value:,}"),
            marker_color="#c0392b",
            hovertemplate="%{x}<br>%{y:,} homicidios<extra></extra>",
        )
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title="Municipio",
        yaxis_title="Homicidios (X95)",
        margin=dict(l=10, r=10, t=60, b=40),
        height=380,
    )
    figure.update_yaxes(tickformat=",")
    return figure


def render(data: pd.DataFrame | None = None, title: str | None = None) -> html.Div:
    """Render the homicide bar chart card."""
    dataset = data if data is not None else pd.DataFrame()
    figure = build_top_homicide_bars(
        dataset,
        title=title or "Top 5 ciudades con más homicidios (X95)",
    )
    return html.Div(
        className="card-content",
        children=[
            dcc.Graph(
                id="mortality-bars",
                figure=figure,
                style={"width": "100%", "height": "100%", "minHeight": "320px"},
                config={"displaylogo": False, "responsive": True},
            ),
        ],
    )


__all__ = ["build_top_homicide_bars", "render"]
