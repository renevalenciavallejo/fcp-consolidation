"""Lógica de la Etapa 4 - Integración al Detalle de pago.

La validación de estructura del reporte ETY la hace el ejecutor antes de llamar a
process(). Aquí van las reglas propias de la etapa, en el orden de ESPECIFICACION.md.
"""

import re

import pandas as pd

from core.audit import AuditLog, is_empty
from core.cleaning import normalize_code
from core.settings import SOURCE_FILE, SOURCE_ROW
from core.writer import ExcelFormula
from stages.stage_04_payment_detail.config import (
    COLUMN_MAPPING,
    CONCEPT_COLUMN,
    CONTRACT_PREFIX,
    CONTRACT_SEPARATORS,
    CONTRACT_WORD,
    VALIDITY_COLUMN,
    FIXED_VALUES,
    FORMULA_COLUMNS,
    FORMULA_COLUMNS_AFTER_VALIDITY,
    MAX_SUBTRUSTS_IN_NOTE,
    NUMBER_COLUMNS,
    OUTPUT_LAYOUT,
    SUBTRUST_COLUMN,
    SUBTRUST_RELATIONS,
    VALUE_PREFIXES,
)


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    ety = inputs["ety_processed"]
    audit.step("Generando el archivo con la estructura del Detalle de pago")
    detail = empty_payment_detail(ety, audit)
    audit.step("Copiando los datos del reporte ETY al Detalle de pago")
    detail = copy_ety_values(ety, detail, audit)
    audit.step("Asignando los valores fijos del Detalle de pago")
    assign_fixed_values(detail, audit)
    for relation in SUBTRUST_RELATIONS:
        audit.step(f"Asignando {relation['column']} según el {SUBTRUST_COLUMN}")
        assign_from_subtrust(detail, relation, audit)
    for formula in FORMULA_COLUMNS:
        audit.step(f"Calculando {formula['column']}")
        add_formula(detail, formula, audit)
    audit.step(f"Asignando {VALIDITY_COLUMN}")
    assign_validity(detail, audit)
    for formula in FORMULA_COLUMNS_AFTER_VALIDITY:
        audit.step(f"Calculando {formula['column']}")
        add_formula(detail, formula, audit)
    return detail


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


def assign_fixed_values(detail: pd.DataFrame, audit: AuditLog) -> None:
    """Asigna a todos los registros el valor fijo de cada columna de FIXED_VALUES. Regla TRA-405.

    Son los valores que tienen todos los registros del Detalle de pago (por ejemplo, la
    fiduciaria FIDUPREVISORA y el GL 656).
    """
    for column, value in FIXED_VALUES.items():
        detail[column] = [value] * len(detail)
    values = ", ".join(f"{column} = {_shown(value)}" for column, value in FIXED_VALUES.items())
    audit.transformation("TRA-405", f"Valores fijos en {len(detail)} registros: {values}")


def assign_from_subtrust(detail: pd.DataFrame, relation: dict, audit: AuditLog) -> None:
    """Llena la columna con el valor que le corresponde al SUBFIDEICOMISO de cada registro,
    según su relación (SUBTRUST_RELATIONS). Reglas TRA-407 (NOMBRE_SUBFIDEICOMISO_PAGO),
    TRA-408 (RECURSOS) y TRA-406 (FUENTE_DE_RECURSOS).

    El Subfideicomiso se compara como código (1002 y «1002» son el mismo). Si no está en
    la relación o está vacío, la celda queda vacía y el log lo indica con ✗, para que el
    usuario la complete; no detiene el proceso.
    """
    column, rule, values = relation["column"], relation["rule"], relation["values"]
    subtrusts = detail[SUBTRUST_COLUMN].map(normalize_code)
    # dtype=object: los vacíos quedan como None, sin que pandas los convierta en NaN.
    detail[column] = pd.Series([values.get(code) for code in subtrusts], index=detail.index, dtype=object)
    missing = detail[column].map(is_empty)
    audit.transformation(rule, f"{column} asignada en {int((~missing).sum())} de {len(detail)} registros")
    audit.note(audit.step_summary())
    if missing.any():
        unknown = ["(vacío)" if is_empty(code) else code for code in dict.fromkeys(subtrusts[missing])]
        shown = ", ".join(unknown[:MAX_SUBTRUSTS_IN_NOTE])
        if len(unknown) > MAX_SUBTRUSTS_IN_NOTE:
            shown += f" y {len(unknown) - MAX_SUBTRUSTS_IN_NOTE} más"
        audit.note(
            f"[{rule}] {int(missing.sum())} registros sin {column}: el {SUBTRUST_COLUMN} "
            f"no está en la relación o está vacío ({shown}). Complételos manualmente",
            ok=False,
        )


def _shown(value: object) -> str:
    """Valor para el log: los textos entre comillas («1») para distinguirlos de los números (1)."""
    return f"«{value}»" if isinstance(value, str) else str(value)


def add_formula(detail: pd.DataFrame, formula: dict, audit: AuditLog) -> None:
    """Escribe en cada fila la fórmula de Excel de la columna (FORMULA_COLUMNS y
    FORMULA_COLUMNS_AFTER_VALIDITY). Reglas TRA-403, TRA-404 y TRA-410.

    openpyxl no calcula fórmulas: el resultado aparece al abrir el archivo en Excel.
    - VALIDACION: la fórmula de Diferencia del ETY, porque su resultado no queda guardado
      en el archivo y no se puede copiar.
    - CONTRATO: la fórmula del Detalle de pago, que toma el número de contrato de CONCEPTO.
    - CONTRATO_2: la fórmula del Detalle de pago, que une CONTRATO y VIGENCIA.
    """
    column = formula["column"]
    detail[column] = [ExcelFormula(formula["formula"], formula["format"])] * len(detail)
    audit.transformation(formula["rule"], f"{column}: fórmula de Excel en {len(detail)} filas")


def assign_validity(detail: pd.DataFrame, audit: AuditLog) -> None:
    """VIGENCIA según el CONTRATO y el CONCEPTO de cada registro. Regla TRA-409.

    Si el CONTRATO es un número, la vigencia es el número que sigue a
    «CONTRATO_<número>-» en CONCEPTO (CONTRATO_1345-2025 -> 2025). Si el CONTRATO está
    vacío o no es un número, o CONCEPTO no tiene esa expresión, VIGENCIA queda vacía.
    """
    values = []
    not_number = not_found = 0
    for concept in detail[CONCEPT_COLUMN]:
        text = "" if is_empty(concept) else str(concept)
        contract = contract_number(text)
        if contract is None or not contract.isdigit():
            not_number += 1
            values.append(None)
            continue
        match = re.search(rf"{re.escape(CONTRACT_PREFIX)}{re.escape(contract)}-(\d+)", text)
        if match is None:
            not_found += 1
        values.append(int(match.group(1)) if match else None)
    detail[VALIDITY_COLUMN] = pd.Series(values, index=detail.index, dtype=object)
    assigned = len(detail) - not_number - not_found
    detail_text = (
        f"{VALIDITY_COLUMN} asignada en {assigned} de {len(detail)} registros; "
        f"vacía en {not_number} porque el {CONTRACT_WORD} está vacío o no es un número"
    )
    if not_found:
        detail_text += f" y en {not_found} porque {CONCEPT_COLUMN} no tiene la expresión {CONTRACT_PREFIX}<número>-<vigencia>"
    audit.transformation("TRA-409", detail_text)


def contract_number(concept: str) -> str | None:
    """El resultado de la fórmula de CONTRATO del Detalle de pago para ese CONCEPTO.

    Repite los pasos de la fórmula de Excel (FORMULA_COLUMNS), porque la herramienta no
    calcula fórmulas y VIGENCIA depende del resultado:
    1. Busca «CONTRATO» sin distinguir mayúsculas (SEARCH); si no está, la fórmula da
       #¡VALOR! y aquí se devuelve None.
    2. Desde ahí, cambia espacios, «/» y «-» por «_» y quita «CONTRATO_» (SUBSTITUTE,
       que sí distingue mayúsculas).
    3. Toma el texto hasta el siguiente «_»; si no hay, la fórmula da #¡VALOR! (None).
    """
    start = concept.upper().find(CONTRACT_WORD.upper())
    if start < 0:
        return None
    text = concept
    for separator in CONTRACT_SEPARATORS:
        text = text.replace(separator, "_")
    text = text[start:].replace(CONTRACT_PREFIX, "")
    end = text.find("_")
    return text[:end] if end >= 0 else None


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
