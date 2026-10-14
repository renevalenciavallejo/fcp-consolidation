"""Lógica de la Etapa 1 - Limpieza del reporte ETY.

La validación de estructura y la eliminación de las filas de título las hace el
ejecutor antes de llamar a process(). Aquí van las reglas propias de la etapa,
en el orden de ESPECIFICACION.md.
"""

import pandas as pd

from core.audit import AuditLog
from core.cleaning import convert_columns
from stages.stage_01_ety_cleaning.config import INPUTS

# Tipo de cada columna del reporte, según config.INPUTS.
COLUMN_TYPES = INPUTS["ety_report"]["columns"]


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    df = inputs["ety_report"]
    df = convert_currency_columns(df, audit)
    return df


def convert_currency_columns(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Convierte a moneda las columnas de valores (E a J: VR. BRUTO ... Importe). Regla TIP-005.

    Los valores que no son número quedan como estaban y se reportan como Error.
    """
    currency_columns = {c: t for c, t in COLUMN_TYPES.items() if t == "currency"}
    return convert_columns(df, currency_columns, audit)
