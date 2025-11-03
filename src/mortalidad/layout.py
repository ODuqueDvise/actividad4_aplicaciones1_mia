"""Application layout definitions for the Dash interface."""

from __future__ import annotations

from dash import Dash, dcc, html

from .components import bars, hist, lines
from .components import map as map_component
from .components import pie, stacked, table


def build_layout(_: Dash) -> html.Div:
    """Generate the accessible layout for the Dash application."""
    return html.Div(
        className="app-shell",
        children=[
            html.Header(
                className="app-header",
                role="banner",
                children=[
                    html.Div(
                        className="header-text",
                        children=[
                            html.H1(
                                "Mortalidad Colombia",
                                className="app-title",
                                id="app-title",
                            ),
                            html.P(
                                (
                                    "Análisis interactivo de mortalidad por "
                                    "territorio y causa."
                                ),
                                className="app-subtitle",
                                id="app-subtitle",
                            ),
                            html.Div(
                                className="header-meta",
                                children=[
                                    html.Span(
                                        "Fuente: Estadísticas Vitales 2019 (DANE)"
                                    ),
                                    html.Span("Proyecto académico | Maestría IA 2025"),
                                    html.Span("Aplicaciones 1 | Orlando Duque"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Main(
                className="app-main",
                role="main",
                children=[
                    html.Section(
                        className="filters-section",
                        role="region",
                        **{"aria-labelledby": "filtros-titulo"},
                        children=[
                            html.Div(
                                className="filters-header",
                                children=[
                                    html.H2("Filtros", id="filtros-titulo"),
                                    html.P(
                                        (
                                            "Refina los indicadores para comparar "
                                            "territorios y causas."
                                        ),
                                        className="filters-description",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="filters-grid",
                                children=[
                                    html.Div(
                                        className="filter-item",
                                        children=[
                                            html.Label(
                                                "Departamento",
                                                className="filter-label",
                                                htmlFor="filter-department",
                                            ),
                                            dcc.Dropdown(
                                                id="filter-department",
                                                options=[],
                                                placeholder="Seleccione departamento",
                                                multi=False,
                                                clearable=True,
                                                persistence=True,
                                                persistence_type="session",
                                                searchable=True,
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="filter-item",
                                        children=[
                                            html.Label(
                                                "Municipio",
                                                className="filter-label",
                                                htmlFor="filter-municipality",
                                            ),
                                            dcc.Dropdown(
                                                id="filter-municipality",
                                                options=[],
                                                placeholder="Seleccione municipio",
                                                multi=False,
                                                clearable=True,
                                                persistence=True,
                                                persistence_type="session",
                                                searchable=True,
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="filter-item",
                                        children=[
                                            html.Label(
                                                "Sexo",
                                                className="filter-label",
                                                htmlFor="filter-sex",
                                            ),
                                            dcc.RadioItems(
                                                id="filter-sex",
                                                options=[
                                                    {"label": "Todos", "value": "all"},
                                                    {"label": "Mujeres", "value": "F"},
                                                    {"label": "Hombres", "value": "M"},
                                                ],
                                                value="all",
                                                labelStyle={"display": "inline-flex"},
                                                inputClassName="filter-radio",
                                                persistence=True,
                                                persistence_type="session",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="filter-item",
                                        children=[
                                            html.Label(
                                                "Causa específica",
                                                className="filter-label",
                                                htmlFor="filter-homicide",
                                            ),
                                            dcc.Checklist(
                                                id="filter-homicide",
                                                options=[
                                                    {
                                                        "label": (
                                                            "Mostrar solo homicidios "
                                                            "con arma de fuego (X95)"
                                                        ),
                                                        "value": "x95",
                                                    }
                                                ],
                                                value=[],
                                                inputClassName="filter-checkbox",
                                                persistence=True,
                                                persistence_type="session",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="filter-item filter-slider",
                                        children=[
                                            html.Label(
                                                "Meses",
                                                className="filter-label",
                                                htmlFor="filter-months",
                                            ),
                                            dcc.RangeSlider(
                                                id="filter-months",
                                                min=1,
                                                max=12,
                                                step=1,
                                                value=[1, 12],
                                                marks={
                                                    month: {"label": str(month)}
                                                    for month in range(1, 13)
                                                },
                                                allowCross=False,
                                                persistence=True,
                                                persistence_type="session",
                                                updatemode="mouseup",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Section(
                        className="viz-section",
                        role="region",
                        **{"aria-label": "Visualizaciones de mortalidad"},
                        children=[
                            html.Div(
                                className="viz-grid",
                                children=[
                                    html.Section(
                                        className="viz-card map-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-map-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Mapa de mortalidad por "
                                                            "departamento"
                                                        ),
                                                        id="viz-map-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-map",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar datos del "
                                                                "mapa"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-map"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=map_component.render(
                                                    title=(
                                                        "Mapa coroplético por "
                                                        "departamento"
                                                    )
                                                ),
                                            ),
                                        ],
                                    ),
                                    html.Section(
                                        className="viz-card line-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-line-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Tendencia mensual de "
                                                            "muertes"
                                                        ),
                                                        id="viz-line-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-lines",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar serie "
                                                                "mensual"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-lines"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=lines.render(
                                                    title="Muertes por mes",
                                                ),
                                            ),
                                        ],
                                    ),
                                    html.Section(
                                        className="viz-card bars-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-bars-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Top 5 ciudades con más "
                                                            "homicidios (X95)"
                                                        ),
                                                        id="viz-bars-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-bars",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar ranking de "
                                                                "homicidios"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-bars"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=bars.render(
                                                    title=(
                                                        "Top 5 ciudades con más "
                                                        "homicidios (X95)"
                                                    ),
                                                ),
                                            ),
                                        ],
                                    ),
                                    html.Section(
                                        className="viz-card pie-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-pie-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Ciudades con menor "
                                                            "mortalidad (top 10)"
                                                        ),
                                                        id="viz-pie-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-pie",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar ranking de "
                                                                "menor mortalidad"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-pie"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=pie.render(
                                                    title=(
                                                        "10 ciudades con menor "
                                                        "mortalidad"
                                                    ),
                                                ),
                                            ),
                                        ],
                                    ),
                                    html.Section(
                                        className="viz-card table-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-table-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Principales causas de "
                                                            "muerte"
                                                        ),
                                                        id="viz-table-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-table",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar top de "
                                                                "causas"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-table"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=table.render(),
                                            ),
                                        ],
                                    ),
                                    html.Section(
                                        className="viz-card stacked-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-stacked-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Muertes por sexo y "
                                                            "departamento"
                                                        ),
                                                        id="viz-stacked-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-stacked",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar datos sexo "
                                                                "por departamento"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-stacked"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=stacked.render(
                                                    title=(
                                                        "Muertes por sexo y "
                                                        "departamento"
                                                    )
                                                ),
                                            ),
                                        ],
                                    ),
                                    html.Section(
                                        className="viz-card hist-card",
                                        role="region",
                                        **{"aria-labelledby": "viz-hist-title"},
                                        children=[
                                            html.Div(
                                                className="card-header",
                                                children=[
                                                    html.H3(
                                                        (
                                                            "Distribución por "
                                                            "grupo de edad"
                                                        ),
                                                        id="viz-hist-title",
                                                    ),
                                                    html.Button(
                                                        "Exportar CSV",
                                                        id="export-hist",
                                                        className="btn-export",
                                                        type="button",
                                                        **{
                                                            "aria-label": (
                                                                "Descargar "
                                                                "distribución por edad"
                                                            ),
                                                        },
                                                    ),
                                                    dcc.Download(id="download-hist"),
                                                ],
                                            ),
                                            dcc.Loading(
                                                className="loading-wrapper",
                                                type="circle",
                                                children=hist.render(
                                                    title=(
                                                        "Distribución por "
                                                        "grupo de edad"
                                                    )
                                                ),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


__all__ = ["build_layout"]
