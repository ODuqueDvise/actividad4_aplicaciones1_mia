"""Stacked chart component."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from plotly.graph_objects import Figure


def _order_sexes(sexes: Iterable[str]) -> list[str]:
    order = ["F", "M", "NR"]
    sex_list = [sex for sex in order if sex in sexes]
    for sex in sexes:
        if sex not in sex_list:
            sex_list.append(sex)
    return sex_list


def build_stacked_bar_figure(
    data: pd.DataFrame,
    *,
    normalize: bool = False,
    title: str = "Muertes por sexo y departamento",
) -> Figure:
    """Return a stacked (or normalized) bar chart by sex."""
    required = {"depto", "sexo", "causa_cod"}
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

    grouped = (
        data.groupby(["depto", "sexo"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values(["depto", "sexo"])
    )

    departments = grouped["depto"].unique().tolist()
    sexes = _order_sexes(grouped["sexo"].unique().tolist())

    figure = go.Figure()
    display_names = {"M": "Hombres", "F": "Mujeres", "NR": "No reportado"}
    for sex in sexes:
        subset = grouped[grouped["sexo"] == sex]
        y_values = subset.set_index("depto")["total"].reindex(departments, fill_value=0)
        figure.add_bar(
            x=departments,
            y=y_values,
            name=display_names.get(sex, sex),
            hovertemplate="%{x}<br>%{y:,} defunciones<extra></extra>",
        )

    figure.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title="Departamento",
        yaxis_title="Defunciones",
        barmode="stack",
        margin=dict(l=10, r=10, t=60, b=60),
        height=400,
    )
    figure.update_yaxes(tickformat=",")
    if normalize:
        figure.update_layout(barnorm="percent", yaxis_title="Porcentaje de defunciones")

    return figure


def render(
    data: pd.DataFrame | None = None,
    *,
    normalize: bool = False,
    title: str | None = None,
) -> html.Div:
    """Render the stacked bar chart card."""
    dataset = data if data is not None else pd.DataFrame()
    figure = build_stacked_bar_figure(
        dataset,
        normalize=normalize,
        title=title or "Muertes por sexo y departamento",
    )
    return html.Div(
        className="card-content",
        children=[
            dcc.Graph(
                id="mortality-stacked",
                figure=figure,
                style={"width": "100%", "height": "100%", "minHeight": "340px"},
                config={"displaylogo": False, "responsive": True},
            ),
        ],
    )


__all__ = ["build_stacked_bar_figure", "render"]
