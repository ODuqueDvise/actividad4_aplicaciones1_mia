"""Integration and unit tests for callback utilities."""

from __future__ import annotations

import pandas as pd
import pytest

from mortalidad import callbacks
from mortalidad.app import create_app


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Return a synthetic dataset for callback tests."""
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


@pytest.fixture(autouse=True)
def patch_base_dataframe(monkeypatch: pytest.MonkeyPatch, sample_df: pd.DataFrame) -> None:
    """Patch data access to use the synthetic dataset."""
    callbacks._CACHE = type(callbacks._CACHE)(default_timeout=callbacks.CACHE_TIMEOUT)
    monkeypatch.setattr(callbacks, "_get_base_dataframe", lambda: sample_df.copy())


def test_get_filters_state_homicides_only(sample_df: pd.DataFrame) -> None:
    """Filtering state must respect homicide flag."""
    result = callbacks.get_filters_state(
        department_value=None,
        municipality_value=None,
        sex_value="all",
        homicide_values=["x95"],
        month_values=[5, 8],
    )
    assert (result["homicidio_x95"] == 1).all()
    assert len(result) == sample_df[sample_df["homicidio_x95"] == 1].shape[0]


def test_dash_callbacks_render(dash_duo) -> None:
    """Dash app should render layout and respond to filter interactions."""
    app = create_app()
    dash_duo.start_server(app)

    dash_duo.wait_for_element("#mortality-map")
    dash_duo.select_dcc_dropdown("#filter-department", "Bogotá")
    dash_duo.wait_for_text_to_equal("#mortality-table-message", "", timeout=3)

    graph = dash_duo.find_element("#mortality-lines")
    assert graph is not None
