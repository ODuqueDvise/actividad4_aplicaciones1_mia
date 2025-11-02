"""Line chart component."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import dcc, html
from plotly.graph_objects import Figure


def build_monthly_line_figure(
    data: pd.DataFrame,
    *,
    title: str = "Muertes por mes",
) -> Figure:
    """Build a line chart summarising deaths per month."""
    required = {"anio", "mes", "causa_cod"}
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

    monthly = (
        data.groupby(["anio", "mes"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values(["anio", "mes"])
    )
    monthly["mes_label"] = monthly["mes"].map(lambda m: f"{m:02d}")

    figure = px.line(
        monthly,
        x="mes_label",
        y="total",
        markers=True,
        title=title,
    )
    figure.update_traces(
        hovertemplate="Mes %{x}: %{y:,} defunciones<extra></extra>",
        line_shape="linear",
    )
    figure.update_layout(
        template="plotly_white",
        xaxis_title="Mes",
        yaxis_title="Defunciones",
        margin=dict(l=10, r=10, t=60, b=40),
    )
    figure.update_yaxes(tickformat=",")
    return figure


def render(data: pd.DataFrame | None = None, title: str | None = None) -> html.Div:
    """Render the monthly line chart using the provided dataset."""
    dataset = data if data is not None else pd.DataFrame()
    figure = build_monthly_line_figure(
        dataset,
        title=title or "Muertes por mes",
    )
    return html.Div(
        className="card-content",
        children=[
            dcc.Graph(
                id="mortality-lines",
                figure=figure,
                config={"displaylogo": False, "responsive": True},
            ),
        ],
    )


__all__ = ["build_monthly_line_figure", "render"]
