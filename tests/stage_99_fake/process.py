"""Lógica de la etapa de prueba: ejercita las funciones comunes del núcleo."""

import pandas as pd

from core.audit import AuditLog
from core.cleaning import convert_columns, remove_duplicates, remove_empty_rows, remove_extra_spaces
from core.settings import WARNING
from tests.stage_99_fake.config import DUPLICATE_KEY, INPUTS, VALID_SOURCES


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    df = inputs["reports"]
    df = remove_extra_spaces(df, audit)
    df = remove_empty_rows(df, audit)
    df = convert_columns(df, INPUTS["reports"]["columns"], audit)
    df = add_catalog_names(df, inputs["catalog"], audit)
    df = remove_duplicates(df, DUPLICATE_KEY, audit)
    check_sources(df, audit)
    df = add_value_in_millions(df, audit)
    return df


def add_catalog_names(df: pd.DataFrame, catalog: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Agrega la columna Nombre desde el catálogo (si se cargó)."""
    catalog = convert_columns(remove_extra_spaces(catalog, audit), INPUTS["catalog"]["columns"], audit)
    names = dict(zip(catalog["Codigo"], catalog["Nombre"]))
    df = df.copy()
    df["Nombre"] = df["Codigo"].map(names).astype(object)
    return df


def check_sources(df: pd.DataFrame, audit: AuditLog) -> None:
    """Marca como advertencia las fuentes que no están en la lista permitida."""
    invalid = ~df["Fuente"].isin(VALID_SOURCES)
    audit.finding_column(
        df, invalid, "Fuente", WARNING, "VAL-901", "Fuente no reconocida", "Revisar la fuente"
    )


def add_value_in_millions(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Agrega una columna calculada a partir de Valor."""
    df = df.copy()
    df["Valor (millones)"] = [
        v / 1_000_000 if isinstance(v, float) else None for v in df["Valor"]
    ]
    return df
