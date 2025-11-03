"""Table component."""

from __future__ import annotations

from typing import cast

import pandas as pd
from dash import dash_table, html


def top_causes_records(
    data: pd.DataFrame, *, limit: int = 10
) -> list[dict[str, object]]:
    """Return the top mortality causes sorted by frequency."""
    if data.empty:
        return []
    aggregated = (
        data.groupby(["causa_cod", "causa"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values("total", ascending=False)
        .head(limit)
    )
    return cast(list[dict[str, object]], aggregated.to_dict("records"))


def build_top_causes_table(
    data: pd.DataFrame,
    *,
    limit: int = 10,
) -> dash_table.DataTable:
    """Build a Dash DataTable with the top mortality causes."""
    records = top_causes_records(data, limit=limit)
    table = dash_table.DataTable(
        id="mortality-table",
        columns=[
            {"name": "Código", "id": "causa_cod"},
            {"name": "Causa", "id": "causa"},
            {
                "name": "Total",
                "id": "total",
                "type": "numeric",
                "format": {"specifier": ",d"},
            },
        ],
        data=records,
        page_size=limit,
        sort_action="native",
        filter_action="none",
        export_format="csv",
        style_table={"overflowX": "auto"},
        style_cell={
            "padding": "0.65rem",
            "fontSize": "0.95rem",
            "textAlign": "left",
        },
        style_header={
            "backgroundColor": "#0a3d62",
            "color": "#ffffff",
            "fontWeight": "600",
        },
        style_data_conditional=[
            {
                "if": {"column_id": "total"},
                "textAlign": "right",
            }
        ],
    )
    return table


def render(data: pd.DataFrame | None = None) -> html.Div:
    """Render the table card for the top mortality causes."""
    dataset = data if data is not None else pd.DataFrame()
    table_component = build_top_causes_table(dataset)
    message = html.P(
        "",
        id="mortality-table-message",
        className="empty-state",
        role="status",
    )
    return html.Div(
        className="card-content",
        children=[
            table_component,
            message,
        ],
    )


__all__ = ["build_top_causes_table", "top_causes_records", "render"]
