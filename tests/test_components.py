"""Unit tests for visualization components."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest
from dash import dash_table

from mortalidad.components import bars, hist, lines
from mortalidad.components import map as map_component
from mortalidad.components import pie, stacked, table
from mortalidad.data_loader import GRUPO_EDAD_LABELS


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Return a synthetic dataset emulating the processed mortality frame."""
    return pd.DataFrame(
        {
            "depto_cod": ["11", "11", "05", "05", "76"],
            "depto": ["Bogotá", "Bogotá", "Antioquia", "Antioquia", "Valle"],
            "muni_cod": ["11001", "11001", "05001", "05001", "76001"],
            "municipio": ["Bogotá D.C.", "Bogotá D.C.", "Medellín", "Medellín", "Cali"],
            "sexo": ["M", "F", "M", "F", "M"],
            "grupo_edad": [5, 6, 7, 5, 6],
            "grupo_edad_label": [
                "15 a 19 años",
                "20 a 24 años",
                "25 a 34 años",
                "15 a 19 años",
                "20 a 24 años",
            ],
            "fecha": pd.to_datetime(
                ["2019-05-10", "2019-06-11", "2019-07-09", "2019-07-10", "2019-08-01"]
            ),
            "anio": [2019, 2019, 2019, 2019, 2019],
            "mes": [5, 6, 7, 7, 8],
            "causa_cod": ["X95", "A10", "X95", "B20", "X95"],
            "causa": [
                "Agresión con arma de fuego (homicidio)",
                "Enfermedades infecciosas",
                "Agresión con arma de fuego (homicidio)",
                "Enfermedades virales",
                "Agresión con arma de fuego (homicidio)",
            ],
            "homicidio_x95": [1, 0, 1, 0, 1],
            "lat": [4.711, 4.711, 6.244, 6.244, 3.451],
            "lon": [-74.072, -74.072, -75.581, -75.581, -76.532],
        }
    )


def test_build_choropleth_returns_figure(sample_df: pd.DataFrame) -> None:
    """The map builder must return a non-empty Plotly figure."""
    figure = map_component.build_choropleth_figure(sample_df)
    assert isinstance(figure, go.Figure)
    assert len(figure.data) >= 1
    trace_types = {trace.type for trace in figure.data}
    expected_types = {"choroplethmapbox", "scattermapbox"}
    assert trace_types & expected_types


def test_map_renders_multiple_markers_for_single_department(
    sample_df: pd.DataFrame,
) -> None:
    """When a single department is present, the map must display municipal markers."""
    bogota_df = sample_df[sample_df["depto_cod"] == "11"].copy()
    bogota_df.loc[1, "muni_cod"] = "11002"
    bogota_df.loc[1, "municipio"] = "Usaquén"
    bogota_df.loc[1, "lat"] = 4.754
    bogota_df.loc[1, "lon"] = -74.03

    figure = map_component.build_choropleth_figure(bogota_df)
    assert isinstance(figure, go.Figure)
    scatter_traces = [trace for trace in figure.data if trace.type == "scattermapbox"]
    assert scatter_traces
    assert len(scatter_traces[0]["lat"]) == bogota_df["muni_cod"].nunique()


def test_build_monthly_line_contains_scatter_trace(sample_df: pd.DataFrame) -> None:
    """Line chart must produce a scatter trace with months."""
    figure = lines.build_monthly_line_figure(sample_df)
    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "scatter"
    assert set(figure.data[0].x) == {"05", "06", "07", "08"}


def test_build_homicide_bars_sorted(sample_df: pd.DataFrame) -> None:
    """Bars chart should focus on homicide records and be sorted."""
    figure = bars.build_top_homicide_bars(sample_df)
    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "bar"
    assert figure.data[0].x[0] == "Bogotá D.C."


def test_build_lowest_mortality_pie(sample_df: pd.DataFrame) -> None:
    """Pie chart must contain a pie trace with expected labels."""
    figure = pie.build_lowest_mortality_pie(sample_df)
    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "pie"
    assert set(figure.data[0].labels) == {"Bogotá D.C.", "Medellín", "Cali"}


def test_build_stacked_bar_mode(sample_df: pd.DataFrame) -> None:
    """Stacked bar should define stack mode and contain both sexes."""
    figure = stacked.build_stacked_bar_figure(sample_df)
    assert isinstance(figure, go.Figure)
    assert figure.layout.barmode == "stack"
    trace_names = {trace.name for trace in figure.data}
    assert {"Hombres", "Mujeres"}.issubset(trace_names)


def test_build_age_histogram_respects_order(sample_df: pd.DataFrame) -> None:
    """Histogram must respect logical order of age labels."""
    figure = hist.build_age_histogram(sample_df)
    assert isinstance(figure, go.Figure)
    categories = list(figure.data[0].x)
    expected_order = [
        label for label in GRUPO_EDAD_LABELS.values() if label in categories
    ]
    assert categories == expected_order


def test_build_top_causes_table_returns_datatable(sample_df: pd.DataFrame) -> None:
    """Table builder must produce a Dash DataTable."""
    datatable = table.build_top_causes_table(sample_df)
    assert isinstance(datatable, dash_table.DataTable)
    assert len(datatable.columns) == 3
