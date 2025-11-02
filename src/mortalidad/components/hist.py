"""Histogram component."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
from dash import dcc, html
from plotly.graph_objects import Figure

from mortalidad.data_loader import GRUPO_EDAD_LABELS

AGE_ORDER = list(GRUPO_EDAD_LABELS.values())


def build_age_histogram(
    data: pd.DataFrame,
    *,
    title: str = "Distribución por grupo de edad",
) -> Figure:
    """Return a histogram-like bar chart ordered by age groups."""
    required = {"grupo_edad", "grupo_edad_label", "causa_cod"}
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

    counts = (
        data.groupby("grupo_edad_label", as_index=False)
        .agg(total=("causa_cod", "size"))
        .set_index("grupo_edad_label")
        .reindex(AGE_ORDER, fill_value=0)
        .reset_index()
    )

    figure = px.bar(
        counts,
        x="grupo_edad_label",
        y="total",
        category_orders={"grupo_edad_label": AGE_ORDER},
        title=title,
    )
    figure.update_traces(
        hovertemplate="%{x}<br>%{y:,} defunciones<extra></extra>",
        marker_color="#2471a3",
    )
    figure.update_layout(
        template="plotly_white",
        xaxis_title="Grupo de edad",
        yaxis_title="Defunciones",
        margin=dict(l=10, r=10, t=60, b=100),
    )
    figure.update_xaxes(tickangle=-35)
    figure.update_yaxes(tickformat=",")
    return figure


def render(data: pd.DataFrame | None = None, title: str | None = None) -> html.Div:
    """Render the age distribution histogram card."""
    dataset = data if data is not None else pd.DataFrame()
    figure = build_age_histogram(
        dataset,
        title=title or "Distribución por grupo de edad",
    )
    return html.Div(
        className="card-content",
        children=[
            dcc.Graph(
                id="mortality-hist",
                figure=figure,
                config={"displaylogo": False, "responsive": True},
            ),
        ],
    )


__all__ = ["build_age_histogram", "render"]
