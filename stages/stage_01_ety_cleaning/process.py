"""Lógica de la Etapa 1 - Limpieza del reporte ETY.

La validación de estructura y la eliminación de las filas de título las hace el
ejecutor antes de llamar a process(). Aquí van las reglas propias de la etapa,
en el orden de ESPECIFICACION.md.
"""

import pandas as pd

from core.audit import AuditLog
from core.cleaning import comparable_text, convert_columns
from core.settings import CURRENCY_FORMAT_EXCEL
from core.writer import ExcelFormula
from stages.stage_01_ety_cleaning.config import (
    AMOUNT_COLUMN,
    CASH_DISTRIBUTION_VALUE,
    DESCRIPTION_COLUMN,
    DIFFERENCE_COLUMN,
    DIFFERENCE_FORMULA,
    INPUTS,
)

# Tipo de cada columna del reporte, según config.INPUTS.
COLUMN_TYPES = INPUTS["ety_report"]["columns"]


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    df = inputs["ety_report"]
    df = convert_currency_columns(df, audit)
    df = remove_cash_distribution_rows(df, audit)
    df = add_difference_column(df, audit)
    return df


def convert_currency_columns(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Convierte a moneda las columnas de valores (E a J: VR. BRUTO ... Importe). Regla TIP-005.

    Los valores que no son número quedan como estaban y se reportan como Error.
    """
    currency_columns = {c: t for c, t in COLUMN_TYPES.items() if t == "currency"}
    return convert_columns(df, currency_columns, audit)


def remove_cash_distribution_rows(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Elimina las filas con Descripción «Distribución Caja» (columna L). Regla LIM-101.

    Cada eliminada queda en la hoja Eliminados del log con todos sus datos.
    """
    target = comparable_text(CASH_DISTRIBUTION_VALUE)
    is_cash_distribution = df[DESCRIPTION_COLUMN].map(lambda value: comparable_text(value) == target)
    return audit.remove_rows(
        df, is_cash_distribution, "LIM-101", f"Descripción «{CASH_DISTRIBUTION_VALUE}»"
    )


def add_difference_column(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Agrega la columna Diferencia a la derecha de Importe, con una fórmula de Excel. Regla TRA-101.

    Se deja como fórmula (no como valor) para que se recalcule si el usuario
    corrige algún valor en Excel. Los registros con diferencia distinta de 0 se
    identifican filtrando esta columna.
    """
    df = df.copy()
    position = df.columns.get_loc(AMOUNT_COLUMN) + 1
    formula = ExcelFormula(DIFFERENCE_FORMULA, CURRENCY_FORMAT_EXCEL)
    df.insert(position, DIFFERENCE_COLUMN, [formula] * len(df))
    audit.column_added(DIFFERENCE_COLUMN, "TRA-101", len(df))
    return df
