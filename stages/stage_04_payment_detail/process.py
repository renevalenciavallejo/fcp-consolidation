"""Lógica de la Etapa 4 - Integración al Detalle de pago.

La validación de estructura del reporte ETY la hace el ejecutor antes de llamar a
process(). Aquí van las reglas propias de la etapa, en el orden de ESPECIFICACION.md.
"""

import pandas as pd

from core.audit import AuditLog, is_empty
from core.cleaning import normalize_code
from core.settings import SOURCE_FILE, SOURCE_ROW
from core.writer import ExcelFormula
from stages.stage_04_payment_detail.config import (
    ACCOUNTING_FORMAT,
    COLUMN_MAPPING,
    NUMBER_COLUMNS,
    OUTPUT_LAYOUT,
    VALIDATION_COLUMN,
    VALIDATION_FORMULA,
    VALUE_PREFIXES,
)


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    ety = inputs["ety_processed"]
    audit.step("Generando el archivo con la estructura del Detalle de pago")
    detail = empty_payment_detail(ety, audit)
    audit.step("Copiando los datos del reporte ETY al Detalle de pago")
    detail = copy_ety_values(ety, detail, audit)
    audit.step(f"Calculando {VALIDATION_COLUMN}")
    return add_validation(detail, audit)


def empty_payment_detail(ety: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Tabla del Detalle de pago con sus columnas en orden, una fila por registro del ETY,
    todas vacías. Regla TRA-401.

    El formato (encabezados, anchos, formatos de celda) lo aplica el ejecutor con
    OUTPUT_LAYOUT. Cada fila conserva el archivo y la fila de origen del registro del
    ETY, para que los hallazgos se puedan ubicar en la salida.
    """
    columns = list(OUTPUT_LAYOUT["columns"])
    detail = pd.DataFrame(None, index=ety.index, columns=columns, dtype=object)
    detail[SOURCE_FILE] = ety[SOURCE_FILE]
    detail[SOURCE_ROW] = ety[SOURCE_ROW]
    audit.transformation("TRA-401", f"Archivo con las {len(columns)} columnas y el formato del Detalle de pago")
    return detail


def copy_ety_values(ety: pd.DataFrame, detail: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Copia los valores del ETY, fila por fila y sin cambios, a su columna del Detalle de pago. Regla TRA-402.

    Las fechas y los valores se copian tal como vienen del ETY (fecha y número); el
    formato con que se ven es el de la columna destino en el Detalle de pago.
    """
    for ety_column, detail_column in COLUMN_MAPPING.items():
        detail[detail_column] = ety[ety_column]
    pairs = ", ".join(f"{source} → {target}" for source, target in COLUMN_MAPPING.items())
    records = "1 registro" if len(ety) == 1 else f"{len(ety)} registros"
    audit.transformation("TRA-402", f"{records} del reporte ETY copiados: {pairs}")
    for column in NUMBER_COLUMNS:
        write_as_numbers(detail, column, audit)
    for column, prefix in VALUE_PREFIXES.items():
        add_prefix(detail, column, prefix, audit)
    return detail.reset_index(drop=True)


def add_prefix(detail: pd.DataFrame, column: str, prefix: str, audit: AuditLog) -> None:
    """Antepone el prefijo a cada valor no vacío de la columna (00153414 -> 656-00153414). Regla TRA-402.

    Las celdas vacías quedan vacías. Un valor que ya trae el prefijo no se repite.
    """
    def with_prefix(value: object) -> object:
        if is_empty(value):
            return value
        text = normalize_code(value)
        return text if text.startswith(prefix) else f"{prefix}{text}"

    detail[column] = detail[column].map(with_prefix)
    filled = int((~detail[column].map(is_empty)).sum())
    audit.transformation("TRA-402", f"{column}: prefijo «{prefix}» agregado a {filled} valores")


def add_validation(detail: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """VALIDACION con la fórmula de Diferencia del ETY, en cada fila. Regla TRA-403.

    No se copia el valor de Diferencia porque en el ETY es una fórmula cuyo resultado no
    queda guardado en el archivo (openpyxl no calcula fórmulas). La misma fórmula sobre las
    columnas copiadas da el mismo resultado al abrir el archivo en Excel.
    """
    detail[VALIDATION_COLUMN] = [ExcelFormula(VALIDATION_FORMULA, ACCOUNTING_FORMAT)] * len(detail)
    audit.transformation("TRA-403", f"{VALIDATION_COLUMN}: fórmula {VALIDATION_FORMULA} en {len(detail)} filas")
    return detail


def write_as_numbers(detail: pd.DataFrame, column: str, audit: AuditLog) -> None:
    """Escribe como número los valores de la columna que el ETY trae como texto. Regla TRA-402.

    El valor que se ve no cambia (1085283965 sigue siendo 1085283965); solo deja de
    ser texto, para que Excel lo reconozca como número. Los valores con otros caracteres
    o con ceros a la izquierda se dejan como texto y se cuentan en el log.
    """
    numbers = detail[column].map(as_number)
    converted = numbers.map(lambda v: isinstance(v, int)) & detail[column].map(lambda v: isinstance(v, str))
    detail[column] = numbers
    kept = detail[column].map(lambda v: isinstance(v, str))
    audit.transformation(
        "TRA-402",
        f"{column}: {int(converted.sum())} valores escritos como número"
        + (f"; {int(kept.sum())} quedan como texto (tienen otros caracteres o ceros a la izquierda)" if kept.any() else ""),
    )


def as_number(value: object) -> object:
    """El texto como número entero si tiene solo dígitos y no empieza por cero; si no, el mismo valor."""
    if isinstance(value, str) and value.isdigit() and value.isascii() and not value.startswith("0"):
        return int(value)
    return value
