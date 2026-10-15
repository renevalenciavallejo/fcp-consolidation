"""Lógica de la etapa de prueba: ejercita las funciones comunes del núcleo."""

import pandas as pd

from core.audit import AuditLog
from core.cleaning import convert_columns, remove_duplicates, remove_empty_rows, remove_extra_spaces
from core.settings import WARNING
from tests.stage_99_fake.config import DUPLICATE_KEY, INPUTS, VALID_SOURCES


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    # Cada regla abre un paso del log de ejecución, que el usuario ve en pantalla.
    df = inputs["reports"]
    audit.step("Quitando espacios sobrantes")
    df = remove_extra_spaces(df, audit)
    audit.step("Eliminando filas vacías")
    df = remove_empty_rows(df, audit)
    audit.step("Convirtiendo tipos de datos")
    df = convert_columns(df, INPUTS["reports"]["columns"], audit)
    audit.step("Agregando nombres del catálogo")
    df = add_catalog_names(df, inputs["catalog"], audit)
    audit.step("Eliminando duplicados")
    df = remove_duplicates(df, DUPLICATE_KEY, audit)
    audit.step("Revisando fuentes")
    check_sources(df, audit)
    audit.step("Calculando valor en millones")
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
