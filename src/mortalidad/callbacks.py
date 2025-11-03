"""Callbacks registry for the Dash application."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any, Protocol, TypeVar, cast

import pandas as pd
from dash import Dash, Input, Output, State, dcc
from dash.exceptions import PreventUpdate
from flask_caching import SimpleCache  # type: ignore[attr-defined]

from .components import bars, hist, lines
from .components import map as map_component
from .components import pie, stacked, table
from .config import get_settings
from .data_loader import GRUPO_EDAD_LABELS, load_data

LOGGER = logging.getLogger(__name__)


class CacheProtocol(Protocol):
    """Subset of cache methods used by the callbacks."""

    def get(self, key: str, default: object | None = None) -> object: ...

    def set(self, key: str, value: object, timeout: int | None = None) -> bool: ...


CallbackFunc = TypeVar("CallbackFunc", bound=Callable[..., Any])

SETTINGS = get_settings()
CACHE_TIMEOUT = SETTINGS.cache_timeout
SimpleCacheFactory = cast(Callable[..., CacheProtocol], SimpleCache)
_CACHE: CacheProtocol = SimpleCacheFactory(default_timeout=CACHE_TIMEOUT)
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
    month_range: tuple[int, int],
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


def _sanitize_select(value: str | None) -> str | None:
    if value in (None, "", "all", "Todos"):
        return None
    return str(value)


def _sanitize_months(months: Iterable[int] | None) -> tuple[int, int]:
    if not months:
        return (1, 12)
    values = sorted(int(m) for m in months)
    start, end = values[0], values[-1]
    if start > end:
        start, end = end, start
    return (max(1, start), min(12, end))


def get_filters_state(
    department_value: str | None,
    municipality_value: str | None,
    sex_value: str | None,
    homicide_values: Iterable[str] | None,
    month_values: Iterable[int] | None,
) -> pd.DataFrame:
    """Return a filtered DataFrame based on UI selections."""
    department = _sanitize_select(department_value)
    municipality = _sanitize_select(municipality_value)
    sex = str(sex_value or "all").upper()
    homicide_only = bool(
        homicide_values and "x95" in {item.lower() for item in homicide_values}
    )
    month_range = _sanitize_months(month_values)

    cache_key = _filters_cache_key(
        department, municipality, sex, homicide_only, month_range
    )
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
    exported["sexo"] = pd.Categorical(
        exported["sexo"], categories=["Mujeres", "Hombres"], ordered=True
    )
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
    aggregated["grupo_edad_label"] = pd.Categorical(
        aggregated["grupo_edad_label"], categories=order, ordered=True
    )
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
        .assign(
            label=lambda frame: frame["depto"], value=lambda frame: frame["depto_cod"]
        )[["label", "value"]]
        .to_dict("records")
    )
    options_list = cast(list[dict[str, str]], options)
    return [{"label": "Todos", "value": "all"}] + options_list


def _build_municipality_options(df: pd.DataFrame) -> list[dict[str, str]]:
    options = (
        df[["muni_cod", "municipio"]]
        .drop_duplicates()
        .sort_values("municipio")
        .assign(
            label=lambda frame: frame["municipio"],
            value=lambda frame: frame["muni_cod"],
        )[["label", "value"]]
        .to_dict("records")
    )
    options_list = cast(list[dict[str, str]], options)
    return [{"label": "Todos", "value": "all"}] + options_list


def register_callbacks(app: Dash) -> None:
    """Register Dash callbacks for reactive components."""
    LOGGER.debug("Registering callbacks for %s", app)

    def callback(
        *args: object, **kwargs: object
    ) -> Callable[[CallbackFunc], CallbackFunc]:
        decorator = app.callback(*args, **kwargs)
        return cast(Callable[[CallbackFunc], CallbackFunc], decorator)

    @callback(
        Output("filter-department", "options"),
        Input("app-title", "children"),
    )
    def populate_department_options(_: str) -> list[dict[str, str]]:
        dataframe = _get_base_dataframe()
        return _build_department_options(dataframe)

    @callback(
        Output("filter-municipality", "options"),
        Output("filter-municipality", "value"),
        Input("filter-department", "value"),
        State("filter-municipality", "value"),
    )
    def update_municipality_options(
        department_value: str | None, current_value: str | None
    ) -> tuple[list[dict[str, str]], str]:
        dataframe = _get_base_dataframe()
        department = _sanitize_select(department_value)
        if department:
            dataframe = dataframe[dataframe["depto_cod"] == department]
        options = _build_municipality_options(dataframe)
        option_values = {option["value"] for option in options}
        if department and _sanitize_select(current_value) not in option_values:
            return options, "all"
        return options, current_value or "all"

    @callback(
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
    )
    def update_visualizations(
        department_value: str | None,
        municipality_value: str | None,
        sex_value: str | None,
        homicide_values: Iterable[str] | None,
        month_values: Iterable[int] | None,
    ) -> tuple[Any, Any, Any, Any, Any, Any, Any, str]:
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

    def _export_payload(
        filtered: pd.DataFrame,
        builder: Callable[[pd.DataFrame], pd.DataFrame],
    ) -> pd.DataFrame:
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

    @callback(
        Output("download-map", "data"),
        Input("export-map", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_map(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _map_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "mapa_departamentos.csv",
                index=False,
            ),
        )

    @callback(
        Output("download-lines", "data"),
        Input("export-lines", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_lines(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _monthly_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "serie_mensual.csv",
                index=False,
            ),
        )

    @callback(
        Output("download-bars", "data"),
        Input("export-bars", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_bars(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _homicide_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "top_homicidios.csv",
                index=False,
            ),
        )

    @callback(
        Output("download-pie", "data"),
        Input("export-pie", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_pie(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _low_mortality_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "ciudades_menor_mortalidad.csv",
                index=False,
            ),
        )

    @callback(
        Output("download-stacked", "data"),
        Input("export-stacked", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_stacked(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _stacked_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "sexo_departamento.csv",
                index=False,
            ),
        )

    @callback(
        Output("download-hist", "data"),
        Input("export-hist", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_hist(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _hist_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "distribucion_grupo_edad.csv",
                index=False,
            ),
        )

    @callback(
        Output("download-table", "data"),
        Input("export-table", "n_clicks"),
        *common_states,
        prevent_initial_call=True,
    )
    def export_table(
        n_clicks: int,
        department: str | None,
        municipality: str | None,
        sex: str | None,
        homicide: Iterable[str] | None,
        months: Iterable[int] | None,
    ) -> dict[str, Any]:
        if not n_clicks:
            raise PreventUpdate
        filtered = get_filters_state(department, municipality, sex, homicide, months)
        export_df = _export_payload(filtered, _table_export)
        return cast(
            dict[str, Any],
            dcc.send_data_frame(
                export_df.to_csv,
                "top_causas.csv",
                index=False,
            ),
        )


__all__ = ["get_filters_state", "register_callbacks"]
