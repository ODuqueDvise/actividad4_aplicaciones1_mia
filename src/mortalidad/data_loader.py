"""Data ingestion and preparation utilities for the mortality dataset."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

if getattr(np, "string_", None) is None:
    setattr(np, "string_", np.bytes_)

if getattr(np, "float_", None) is None:
    setattr(np, "float_", np.float64)

if getattr(np, "int_", None) is None:
    setattr(np, "int_", np.int64)

import pandera as pa
from pandera import Check, Column, DataFrameSchema

from .config import get_settings
from .logging import configure_logging

LOGGER = logging.getLogger(__name__)

RAW_FILENAMES = {
    "records": "NoFetal2019.xlsx",
    "causes": "CodigosDeMuerte.xlsx",
    "divipola": "Divipola.xlsx",
}
CACHE_FILENAME = "mortalidad_2019.parquet"

RECORDS_COLUMN_MAP = {
    "DPTO_OCURRE": "depto_cod",
    "DEPTO_OCURRE": "depto_cod",
    "MUN_OCURRE": "muni_cod",
    "MUNI_OCURRE": "muni_cod",
    "SEXO": "sexo",
    "SEXO_DEF": "sexo",
    "GRUPO_EDAD1": "grupo_edad",
    "FECHA_DEF": "fecha",
    "FECHA_OCURR": "fecha",
    "CAUSA_DEF": "causa_cod",
    "COD_DEPARTAMENTO": "depto_cod",
    "COD_MUNICIPIO": "muni_cod",
    "COD_MUERTE": "causa_cod",
}

CAUSES_COLUMN_MAP = {
    "CODIGO": "causa_cod",
    "COD_CAUSA": "causa_cod",
    "DESCRIPCION": "causa",
    "NOMBRE": "causa",
}

DIVIPOLA_COLUMN_MAP = {
    "COD_DEPTO": "depto_cod",
    "COD_DEPARTAMENTO": "depto_cod",
    "NOM_DEPTO": "depto",
    "NOM_DEPARTAMENTO": "depto",
    "COD_MPIO": "muni_cod",
    "COD_MUNICIPIO": "muni_cod",
    "NOM_MPIO": "municipio",
    "NOM_MUNICIPIO": "municipio",
    "LAT": "lat",
    "LATITUD": "lat",
    "LON": "lon",
    "LONGITUD": "lon",
}

ALLOWED_SEXES = {"M", "F", "NR"}

GRUPO_EDAD_LABELS: dict[int, str] = {
    1: "Menor de 1 año",
    2: "1 a 4 años",
    3: "5 a 9 años",
    4: "10 a 14 años",
    5: "15 a 19 años",
    6: "20 a 24 años",
    7: "25 a 34 años",
    8: "35 a 44 años",
    9: "45 a 54 años",
    10: "55 a 64 años",
    11: "65 a 74 años",
    12: "75 años o más",
}

MORTALITY_SCHEMA = DataFrameSchema(
    {
        "depto_cod": Column(str, checks=Check.str_length(2, 5)),
        "depto": Column(str, checks=Check.str_length(1, None)),
        "muni_cod": Column(str, checks=Check.str_length(4, 6)),
        "municipio": Column(str, checks=Check.str_length(1, None)),
        "sexo": Column(str, checks=Check.isin(sorted(ALLOWED_SEXES))),
        "grupo_edad": Column(int, checks=Check.isin(sorted(GRUPO_EDAD_LABELS.keys()))),
        "grupo_edad_label": Column(str, checks=Check.str_length(1, None)),
        "fecha": Column(pa.DateTime),
        "anio": Column(int, checks=[Check.eq(2019)]),
        "mes": Column(int, checks=Check.isin(list(range(1, 13)))),
        "causa_cod": Column(str, checks=Check.str_length(3, 5)),
        "causa": Column(str, nullable=True),
        "homicidio_x95": Column(int, checks=Check.isin([0, 1])),
        "lat": Column(float, nullable=True),
        "lon": Column(float, nullable=True),
    },
    coerce=True,
)


@dataclass(frozen=True)
class _SettingsSnapshot:
    data_dir: Path
    env: str
    port: int


def _normalize_code(series: pd.Series, width: int) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.replace(".0", "", regex=False)
        .str.replace(r"\.0$", "", regex=True)
        .fillna("")
        .str.zfill(width)
    )


def _normalize_sex(value: object) -> str:
    if value is None:
        return "NR"
    text = str(value).strip().upper()
    mapping = {
        "MASCULINO": "M",
        "HOMBRE": "M",
        "1": "M",
        "FEMENINO": "F",
        "MUJER": "F",
        "2": "F",
        "F": "F",
        "M": "M",
        "3": "NR",
        "9": "NR",
        "SIN INFORMACION": "NR",
        "SIN INFORMACIÓN": "NR",
        "NR": "NR",
        "0": "NR",
    }
    normalized = mapping.get(text, text)
    if normalized not in ALLOWED_SEXES:
        normalized = "NR"
    return normalized


def _read_excel(base_path: Path, filename: str) -> pd.DataFrame:
    file_path = base_path / filename
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo requerido: {file_path}")
    LOGGER.info("Leyendo archivo %s", file_path)
    return pd.read_excel(file_path, engine="openpyxl")


def _latest_modification(paths: Iterable[Path]) -> float:
    return max(path.stat().st_mtime for path in paths if path.exists())


def get_parquet_engine() -> str:
    if sys.version_info >= (3, 13):
        return "fastparquet"
    try:
        import pyarrow  # type: ignore # noqa: F401

        return "pyarrow"
    except ImportError:
        return "fastparquet"


def _prepare_records(raw: pd.DataFrame) -> pd.DataFrame:
    standard_columns = {
        "depto_cod",
        "muni_cod",
        "sexo",
        "grupo_edad",
        "fecha",
        "causa_cod",
    }
    available = set(raw.columns)

    if {"FECHA_DEF", "FECHA_OCURR"} & available:
        missing_columns = set(RECORDS_COLUMN_MAP) - available
        if missing_columns:
            raise ValueError(
                f"Columnas faltantes en registros principales: {missing_columns}"
            )
        records = raw.rename(columns=RECORDS_COLUMN_MAP)[
            ["depto_cod", "muni_cod", "sexo", "grupo_edad", "fecha", "causa_cod"]
        ].copy()
        records["fecha"] = pd.to_datetime(
            records["fecha"], errors="raise"
        ).dt.tz_localize(None)
    elif {"AÑO", "MES", "COD_DEPARTAMENTO", "COD_MUNICIPIO", "COD_MUERTE"}.issubset(
        available
    ):
        if "COD_DANE" in raw.columns:
            muni_codes = raw["COD_DANE"].astype("string").str.strip()
        else:
            dept_part = (
                raw["COD_DEPARTAMENTO"].astype("string").str.strip().str.zfill(2)
            )
            muni_part = raw["COD_MUNICIPIO"].astype("string").str.strip().str.zfill(3)
            muni_codes = dept_part + muni_part
        records = pd.DataFrame(
            {
                "depto_cod": raw["COD_DEPARTAMENTO"],
                "muni_cod": muni_codes,
                "sexo": raw.get("SEXO"),
                "grupo_edad": raw.get("GRUPO_EDAD1"),
                "fecha": pd.to_datetime(
                    {
                        "year": raw["AÑO"],
                        "month": raw["MES"],
                        "day": 1,
                    },
                    errors="coerce",
                ),
                "causa_cod": raw["COD_MUERTE"],
            }
        )
        records = records.dropna(subset=["fecha"])
    else:
        raise ValueError(
            "Estructura de NoFetal2019.xlsx no soportada. Se requieren columnas "
            "FECHA_DEF/FECHA_OCURR o AÑO/MES."
        )

    if not standard_columns.issubset(records.columns):
        raise ValueError(
            "No se pudieron estandarizar las columnas necesarias del "
            "registro de defunciones."
        )

    records["depto_cod"] = _normalize_code(records["depto_cod"], width=2)
    records["muni_cod"] = _normalize_code(records["muni_cod"], width=5)
    records["causa_cod"] = records["causa_cod"].astype("string").str.strip().str.upper()
    records["sexo"] = records["sexo"].apply(_normalize_sex)
    records["grupo_edad"] = pd.to_numeric(records["grupo_edad"], errors="raise").astype(
        "int16"
    )

    records["fecha"] = records["fecha"].dt.tz_localize(None)
    records["anio"] = records["fecha"].dt.year.astype("int16")
    records["mes"] = records["fecha"].dt.month.astype("int16")
    records["grupo_edad_label"] = (
        records["grupo_edad"].map(GRUPO_EDAD_LABELS).fillna("Sin clasificación")
    )
    records["homicidio_x95"] = (
        records["causa_cod"].str.startswith("X95", na=False).astype("int8")
    )
    return records


def _prepare_causes(raw: pd.DataFrame) -> pd.DataFrame:
    columns = set(raw.columns)
    code3_col = "Código de la CIE-10 tres caracteres"
    desc3_col = "Descripción  de códigos mortalidad a tres caracteres"
    code4_col = "Código de la CIE-10 cuatro caracteres"
    desc4_col = "Descripcion  de códigos mortalidad a cuatro caracteres"

    if {code3_col, desc3_col}.issubset(columns):
        records: list[dict[str, str]] = []
        cleaned = raw.dropna(how="all")
        for _, row in cleaned.iterrows():
            code3 = str(row.get(code3_col, "")).strip()
            desc3 = str(row.get(desc3_col, "")).strip()
            if code3 and code3.lower() != "nan":
                records.append(
                    {"causa_cod": code3.upper(), "causa": desc3 or "Sin descripción"}
                )

            code4 = str(row.get(code4_col, "")).strip()
            desc4 = str(row.get(desc4_col, "")).strip()
            if code4 and code4.lower() != "nan":
                records.append(
                    {
                        "causa_cod": code4.upper(),
                        "causa": desc4 or desc3 or "Sin descripción",
                    }
                )

        causes = pd.DataFrame.from_records(records)
        if causes.empty:
            raise ValueError(
                "No se pudieron extraer códigos de la hoja de causas CIE-10."
            )
        causes = causes.drop_duplicates(subset="causa_cod")
        return causes

    missing_columns = set(CAUSES_COLUMN_MAP) - columns
    if missing_columns:
        raise ValueError(f"Columnas faltantes en catálogo de causas: {missing_columns}")
    causes = raw.rename(columns=CAUSES_COLUMN_MAP)[["causa_cod", "causa"]].copy()
    causes["causa_cod"] = causes["causa_cod"].astype("string").str.strip().str.upper()
    causes["causa"] = causes["causa"].astype("string").str.strip()
    return causes.drop_duplicates(subset="causa_cod")


def _prepare_divipola(raw: pd.DataFrame, source: Path) -> pd.DataFrame:
    columns = set(raw.columns)
    standard_columns = {"depto_cod", "depto", "muni_cod", "municipio", "lat", "lon"}

    if not standard_columns.issubset(columns):
        alt_required = {
            "COD_DEPARTAMENTO",
            "COD_MUNICIPIO",
            "DEPARTAMENTO",
            "MUNICIPIO",
        }
        if alt_required.issubset(columns):
            depto_cod = raw["COD_DEPARTAMENTO"].astype("string").str.strip()
            if "COD_DANE" in raw.columns:
                muni_cod = raw["COD_DANE"].astype("string").str.strip()
            else:
                dept_part = (
                    raw["COD_DEPARTAMENTO"].astype("string").str.strip().str.zfill(2)
                )
                muni_part = (
                    raw["COD_MUNICIPIO"].astype("string").str.strip().str.zfill(3)
                )
                muni_cod = dept_part + muni_part

            renamed = pd.DataFrame(
                {
                    "depto_cod": depto_cod,
                    "depto": raw["DEPARTAMENTO"],
                    "muni_cod": muni_cod,
                    "municipio": raw["MUNICIPIO"],
                    "lat": raw.get("LAT", pd.NA),
                    "lon": raw.get("LON", pd.NA),
                }
            )
        else:
            missing_columns = set(DIVIPOLA_COLUMN_MAP) - columns
            raise ValueError(
                f"Columnas faltantes en catálogo Divipola: {missing_columns}"
            )
    else:
        renamed = raw.rename(columns=DIVIPOLA_COLUMN_MAP)[
            ["depto_cod", "depto", "muni_cod", "municipio", "lat", "lon"]
        ].copy()

    try:
        geo = pd.read_excel(source, sheet_name="Hoja3", header=0, engine="openpyxl")
        geo = geo.rename(
            columns={
                "Departamento": "depto_cod",
                "Unnamed: 1": "depto",
                "Municipio": "muni_cod",
                "Unnamed: 3": "municipio",
                "Localización": "lon",
                "Unnamed: 6": "lat",
            }
        )
        geo = geo.iloc[1:]
        for col in ["depto_cod", "muni_cod"]:
            geo[col] = geo[col].astype("string").str.strip()
        geo["depto_cod"] = geo["depto_cod"].str.zfill(2)
        geo["muni_cod"] = geo["muni_cod"].str.zfill(5)
        geo["municipio"] = geo["municipio"].astype("string").str.strip()
        geo["depto"] = geo["depto"].astype("string").str.strip()
        geo_lon = geo["lon"].astype("string").str.replace(",", ".")
        geo_lat = geo["lat"].astype("string").str.replace(",", ".")
        geo["lon"] = pd.to_numeric(geo_lon, errors="coerce")
        geo["lat"] = pd.to_numeric(geo_lat, errors="coerce")
        renamed = renamed.merge(
            geo,
            on=["depto_cod", "muni_cod"],
            how="left",
            suffixes=("", "_geo"),
        )
        for column in ["depto", "municipio", "lat", "lon"]:
            geo_column = f"{column}_geo"
            if geo_column in renamed.columns:
                renamed[column] = renamed[column].fillna(renamed[geo_column])
                renamed = renamed.drop(columns=geo_column)
    except Exception:  # noqa: BLE001
        pass

    csv_catalog = source.parent / "dane_municipios.csv"
    if csv_catalog.exists():
        try:
            coords = pd.read_csv(csv_catalog, dtype=str, encoding="utf-8")
            coords = coords.rename(
                columns={
                    "COD_DPTO": "depto_cod",
                    "NOM_DPTO": "depto",
                    "COD_MPIO": "muni_cod",
                    "NOM_MPIO": "municipio",
                    "LATITUD": "lat",
                    "LONGITUD": "lon",
                }
            )
            coords["depto_cod"] = (
                coords["depto_cod"].astype("string").str.replace(r"\D", "", regex=True)
            )
            coords["depto_cod"] = coords["depto_cod"].str.zfill(2)
            coords["muni_cod"] = (
                coords["muni_cod"].astype("string").str.replace(r"\D", "", regex=True)
            )
            coords["muni_cod"] = coords["muni_cod"].str.zfill(5)
            coords["depto"] = coords["depto"].astype("string").str.strip().str.title()
            coords["municipio"] = (
                coords["municipio"].astype("string").str.strip().str.title()
            )
            coords["lat"] = pd.to_numeric(coords["lat"], errors="coerce")
            coords["lon"] = pd.to_numeric(coords["lon"], errors="coerce")
            renamed = renamed.merge(
                coords[["depto_cod", "muni_cod", "depto", "municipio", "lat", "lon"]],
                on=["depto_cod", "muni_cod"],
                how="left",
                suffixes=("", "_catalog"),
            )
            for column in ["depto", "municipio", "lat", "lon"]:
                catalog_column = f"{column}_catalog"
                if catalog_column in renamed.columns:
                    renamed[column] = renamed[column].fillna(renamed[catalog_column])
                    renamed = renamed.drop(columns=catalog_column)
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "No fue posible enriquecer coordenadas desde %s", csv_catalog
            )

    renamed["depto_cod"] = _normalize_code(renamed["depto_cod"], width=2)
    renamed["muni_cod"] = _normalize_code(renamed["muni_cod"], width=5)
    renamed["depto"] = renamed["depto"].astype("string").str.strip().str.title()
    renamed["municipio"] = renamed["municipio"].astype("string").str.strip().str.title()
    renamed["lat"] = pd.to_numeric(renamed["lat"], errors="coerce")
    renamed["lon"] = pd.to_numeric(renamed["lon"], errors="coerce")
    return renamed.drop_duplicates(subset=["depto_cod", "muni_cod"])


def _merge_datasets(
    records: pd.DataFrame, causes: pd.DataFrame, divipola: pd.DataFrame
) -> pd.DataFrame:
    merged = records.merge(causes, on="causa_cod", how="left")
    merged = merged.merge(
        divipola,
        on=["depto_cod", "muni_cod"],
        how="left",
        validate="many_to_one",
    )
    return merged[
        [
            "depto_cod",
            "depto",
            "muni_cod",
            "municipio",
            "sexo",
            "grupo_edad",
            "grupo_edad_label",
            "fecha",
            "anio",
            "mes",
            "causa_cod",
            "causa",
            "homicidio_x95",
            "lat",
            "lon",
        ]
    ]


def _snapshot_settings() -> _SettingsSnapshot:
    settings = get_settings()
    return _SettingsSnapshot(
        data_dir=settings.data_dir,
        env=settings.env,
        port=settings.port,
    )


def load_data(force_refresh: bool = False) -> pd.DataFrame:
    """Load, transform, validate, and cache the mortality dataset."""
    configure_logging()
    settings = _snapshot_settings()
    raw_dir = settings.data_dir
    processed_dir = raw_dir.parent / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    cache_path = processed_dir / CACHE_FILENAME

    raw_paths = [raw_dir / filename for filename in RAW_FILENAMES.values()]
    if (
        not force_refresh
        and cache_path.exists()
        and cache_path.stat().st_mtime >= _latest_modification(raw_paths)
    ):
        LOGGER.info("Cargando datos desde caché %s", cache_path)
        cached_df = pd.read_parquet(cache_path, engine=get_parquet_engine())
        return MORTALITY_SCHEMA.validate(cached_df)

    records_raw = _read_excel(raw_dir, RAW_FILENAMES["records"])
    causes_path = raw_dir / RAW_FILENAMES["causes"]
    causes_raw = _read_excel(raw_dir, RAW_FILENAMES["causes"])
    if all(str(col).startswith("Unnamed") for col in causes_raw.columns):
        LOGGER.info("Releyendo catálogo de causas con encabezado en fila 9")
        causes_raw = pd.read_excel(causes_path, engine="openpyxl", header=8)
    divipola_path = raw_dir / RAW_FILENAMES["divipola"]
    divipola_raw = _read_excel(raw_dir, RAW_FILENAMES["divipola"])

    records = _prepare_records(records_raw)
    causes = _prepare_causes(causes_raw)
    divipola = _prepare_divipola(divipola_raw, divipola_path)

    dataset = _merge_datasets(records, causes, divipola)
    dataset["depto"] = dataset["depto"].fillna("Sin informacin")
    dataset["municipio"] = dataset["municipio"].fillna("Sin informacin")
    dataset = dataset[dataset["grupo_edad"].isin(GRUPO_EDAD_LABELS)].reset_index(
        drop=True
    )

    validated = MORTALITY_SCHEMA.validate(dataset, lazy=True)

    LOGGER.info("Guardando datos procesados en %s", cache_path)
    validated.to_parquet(cache_path, index=False, engine=get_parquet_engine())

    return validated


__all__ = ["load_data", "MORTALITY_SCHEMA", "GRUPO_EDAD_LABELS", "get_parquet_engine"]
