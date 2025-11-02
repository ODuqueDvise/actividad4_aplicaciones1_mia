"""Callbacks registry for the Dash application."""

from __future__ import annotations

import logging
from typing import Any, Iterable, Tuple

import pandas as pd
from dash import Dash, Input, Output, State, dcc
from dash.exceptions import PreventUpdate
from flask_caching import SimpleCache

from .components import (
    bars,
    hist,
    lines,
    map as map_component,
    pie,
    stacked,
    table,
)
from .config import get_settings
from .data_loader import GRUPO_EDAD_LABELS, load_data

LOGGER = logging.getLogger(__name__)

SETTINGS = get_settings()
CACHE_TIMEOUT = SETTINGS.cache_timeout
_CACHE = SimpleCache(default_timeout=CACHE_TIMEOUT)
_BASE_DATA_KEY = "mortality_base_dataframe"


def _get_base_dataframe() -> pd.DataFrame:
    cached = _CACHE.get(_BASE_DATA_KEY)
    if cached is None:
        LOGGER.info("Loading mortality dataset into cache")
        cached = load_data(force_refresh=False)
        _CACHE.set(_BASE_DATA_KEY, cached)
    return cached.copy()


def _filters_cache_key(
    depto: str | None,
    muni: str | None,
    sex: str,
    homicide_only: bool,
    month_range: Tuple[int, int],
) -> str:
    return "::".join(
        [
            depto or "all",
            muni or "all",
            sex,
            "1" if homicide_only else "0",
            f"{month_range[0]}-{month_range[1]}",
        ]
    )


def _sanitize_select(value: Any) -> str | None:
    if value in (None, "", "all", "Todos"):
        return None
    return str(value)


def _sanitize_months(months: Iterable[int] | None) -> Tuple[int, int]:
    if not months:
        return (1, 12)
    values = sorted(int(m) for m in months)
    start, end = values[0], values[-1]
    if start > end:
        start, end = end, start
    return (max(1, start), min(12, end))


def get_filters_state(
    department_value: Any,
    municipality_value: Any,
    sex_value: Any,
    homicide_values: Iterable[str] | None,
    month_values: Iterable[int] | None,
) -> pd.DataFrame:
    """Return a filtered DataFrame based on UI selections."""
    department = _sanitize_select(department_value)
    municipality = _sanitize_select(municipality_value)
    sex = str(sex_value or "all").upper()
    homicide_only = bool(homicide_values and "x95" in {item.lower() for item in homicide_values})
    month_range = _sanitize_months(month_values)

    cache_key = _filters_cache_key(department, municipality, sex, homicide_only, month_range)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()

    df = _get_base_dataframe()
    start, end = month_range
    df = df[(df["mes"] >= start) & (df["mes"] <= end)]

    if department:
        df = df[df["depto_cod"] == department]
    if municipality:
        df = df[df["muni_cod"] == municipality]
    if sex in {"M", "F"}:
        df = df[df["sexo"] == sex]
    if homicide_only:
        df = df[df["homicidio_x95"] == 1]

    filtered = df.reset_index(drop=True)
    _CACHE.set(cache_key, filtered)
    return filtered.copy()


def _map_export(df: pd.DataFrame) -> pd.DataFrame:
    required = {"depto_cod", "depto", "lat", "lon", "causa_cod"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["depto_cod", "depto", "total", "lat", "lon"])
    return (
        df.groupby(["depto_cod", "depto"], as_index=False)
        .agg(total=("causa_cod", "size"), lat=("lat", "mean"), lon=("lon", "mean"))
        .sort_values("total", ascending=False)
    )


def _monthly_export(df: pd.DataFrame) -> pd.DataFrame:
    required = {"anio", "mes", "causa_cod"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["anio", "mes", "mes_label", "total"])
    exported = (
        df.groupby(["anio", "mes"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values(["anio", "mes"])
    )
    exported["mes_label"] = exported["mes"].map(lambda month: f"{month:02d}")
    return exported[["anio", "mes", "mes_label", "total"]]


def _homicide_export(df: pd.DataFrame) -> pd.DataFrame:
    required = {"homicidio_x95", "muni_cod", "municipio", "depto", "causa_cod"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["muni_cod", "municipio", "depto", "total"])
    filtered = df[df["homicidio_x95"] == 1]
    return (
        filtered.groupby(["muni_cod", "municipio", "depto"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values("total", ascending=False)
        .head(5)
    )


def _low_mortality_export(df: pd.DataFrame) -> pd.DataFrame:
    required = {"muni_cod", "municipio", "causa_cod"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["muni_cod", "municipio", "total"])
    return (
        df.groupby(["muni_cod", "municipio"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values("total", ascending=True)
        .head(10)
    )


def _stacked_export(df: pd.DataFrame) -> pd.DataFrame:
    required = {"depto", "sexo", "causa_cod"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["depto", "sexo", "total"])
    mapping = {"F": "Mujeres", "M": "Hombres"}
    exported = (
        df.groupby(["depto", "sexo"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .assign(sexo=lambda frame: frame["sexo"].map(mapping).fillna(frame["sexo"]))
    )
    exported["sexo"] = pd.Categorical(exported["sexo"], categories=["Mujeres", "Hombres"], ordered=True)
    return exported.sort_values(["depto", "sexo"]).reset_index(drop=True)


def _hist_export(df: pd.DataFrame) -> pd.DataFrame:
    required = {"grupo_edad", "grupo_edad_label", "causa_cod"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["grupo_edad_label", "total"])
    order = list(GRUPO_EDAD_LABELS.values())
    aggregated = (
        df.groupby(["grupo_edad", "grupo_edad_label"], as_index=False)
        .agg(total=("causa_cod", "size"))
        .sort_values("grupo_edad")
    )
    aggregated["grupo_edad_label"] = pd.Categorical(aggregated["grupo_edad_label"], categories=order, ordered=True)
    aggregated = aggregated.sort_values(["grupo_edad_label"]).drop(columns="grupo_edad")
    return aggregated.reset_index(drop=True)


def _table_export(df: pd.DataFrame) -> pd.DataFrame:
    records = table.top_causes_records(df)
    export_df = pd.DataFrame.from_records(records)
    if not export_df.empty:
        export_df = export_df[["causa_cod", "causa", "total"]]
    return export_df


def _build_department_options(df: pd.DataFrame) -> list[dict[str, str]]:
    options = (
        df[["depto_cod", "depto"]]
        .drop_duplicates()
        .sort_values("depto")
        .assign(label=lambda frame: frame["depto"], value=lambda frame: frame["depto_cod"])
        [["label", "value"]]
        .to_dict("records")
    )
    return [{"label": "Todos", "value": "all"}] + options


def _build_municipality_options(df: pd.DataFrame) -> list[dict[str, str]]:
    options = (
        df[["muni_cod", "municipio"]]
        .drop_duplicates()
        .sort_values("municipio")
        .assign(label=lambda frame: frame["municipio"], value=lambda frame: frame["muni_cod"])
        [["label", "value"]]
        .to_dict("records")
    )
    return [{"label": "Todos", "value": "all"}] + options


def register_callbacks(app: Dash) -> None:
    """Register Dash callbacks for reactive components."""
    LOGGER.debug("Registering callbacks for %s", app)

    @app.callback(Output("filter-department", "options"), Input("filter-global-scope", "value"))
    def populate_department_options(_: Any) -> list[dict[str, str]]:
        dataframe = _get_base_dataframe()
        return _build_department_options(dataframe)

    @app.callback(
        Output("filter-municipality", "options"),
        Output("filter-municipality", "value"),
        Input("filter-department", "value"),
        State("filter-municipality", "value"),
    )
    def update_municipality_options(department_value: Any, current_value: Any) -> tuple[list[dict[str, str]], Any]:
        dataframe = _get_base_dataframe()
        department = _sanitize_select(department_value)
        if department:
            dataframe = dataframe[dataframe["depto_cod"] == department]
        options = _build_municipality_options(dataframe)
        option_values = {option["value"] for option in options}
        if department and _sanitize_select(current_value) not in option_values:
            return options, "all"
        return options, current_value or "all"

    @app.callback(
        Output("mortality-map", "figure"),
        Output("mortality-lines", "figure"),
        Output("mortality-bars", "figure"),
        Output("mortality-pie", "figure"),
        Output("mortality-stacked", "figure"),
        Output("mortality-hist", "figure"),
        Output("mortality-table", "data"),
        Output("mortality-table-message", "children"),
        Input("filter-department", "value"),
        Input("filter-municipality", "value"),
        Input("filter-sex", "value"),
        Input("filter-homicide", "value"),
        Input("filter-months", "value"),
        Input("filter-global-scope", "value"),
    )
    def update_visualizations(
        department_value: Any,
        municipality_value: Any,
        sex_value: Any,
        homicide_values: Iterable[str] | None,
        month_values: Iterable[int] | None,
        scope_value: Any,
    ) -> tuple[Any, ...]:
        del scope_value
        filtered = get_filters_state(
            department_value,
            municipality_value,
            sex_value,
            homicide_values,
            month_values,
        )
        map_fig = map_component.build_choropleth_figure(filtered)
        line_fig = lines.build_monthly_line_figure(filtered)
        bars_fig = bars.build_top_homicide_bars(filtered)
        pie_fig = pie.build_lowest_mortality_pie(filtered)
        stacked_fig = stacked.build_stacked_bar_figure(filtered)
        hist_fig = hist.build_age_histogram(filtered)
        table_data = table.top_causes_records(filtered)
        message = "Sin datos para filtros seleccionados." if filtered.empty else ""
        return (
            map_fig,
            line_fig,
            bars_fig,
            pie_fig,
            stacked_fig,
            hist_fig,
            table_data,
            message,
        )

    def _export_payload(filtered: pd.DataFrame, builder) -> pd.DataFrame:
        if filtered.empty:
            raise PreventUpdate
        export_df = builder(filtered)
        if export_df.empty:
            raise PreventUpdate
        return export_df

    common_states = (
        State("filter-department", "value"),
        State("filter-municipality", "value"),
        State("filter-sex", "value"),
        State("filter-homicide", "value"),
        State("filter-months", "value"),
    )

    @app.callback(
        Output("download-map", "data"),
        Input("export-map", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_map(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _map_export)
        return dcc.send_data_frame(export_df.to_csv, "mapa_departamentos.csv", index=False)

    @app.callback(
        Output("download-lines", "data"),
        Input("export-lines", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_lines(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _monthly_export)
        return dcc.send_data_frame(export_df.to_csv, "serie_mensual.csv", index=False)

    @app.callback(
        Output("download-bars", "data"),
        Input("export-bars", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_bars(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _homicide_export)
        return dcc.send_data_frame(export_df.to_csv, "top_homicidios.csv", index=False)

    @app.callback(
        Output("download-pie", "data"),
        Input("export-pie", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_pie(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _low_mortality_export)
        return dcc.send_data_frame(export_df.to_csv, "ciudades_menor_mortalidad.csv", index=False)

    @app.callback(
        Output("download-stacked", "data"),
        Input("export-stacked", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_stacked(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _stacked_export)
        return dcc.send_data_frame(export_df.to_csv, "sexo_departamento.csv", index=False)

    @app.callback(
        Output("download-hist", "data"),
        Input("export-hist", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_hist(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _hist_export)
        return dcc.send_data_frame(export_df.to_csv, "distribucion_grupo_edad.csv", index=False)

    @app.callback(
        Output("download-table", "data"),
        Input("export-table", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_table(n_clicks: int, department, municipality, sex, homicide, months):
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _table_export)
        return dcc.send_data_frame(export_df.to_csv, "top_causas.csv", index=False)


__all__ = ["get_filters_state", "register_callbacks"]
