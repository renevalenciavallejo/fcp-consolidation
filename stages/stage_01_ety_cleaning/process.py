"""Lógica de la Etapa 1 - Limpieza del reporte ETY.

La validación de estructura y la eliminación de las filas de título las hace el
ejecutor antes de llamar a process(). Aquí van las reglas propias de la etapa,
en el orden de ESPECIFICACION.md. Cada regla abre un paso del log de ejecución
(audit.step) para que el usuario vea en pantalla qué se está haciendo.
"""

import pandas as pd

from core.audit import AuditLog, data_columns, is_empty
from core.cleaning import comparable_text, convert_columns, flag_repeated_values, sort_rows
from core.settings import CURRENCY_FORMAT_EXCEL, SOURCE_ROW, WARNING
from core.writer import ExcelFormula
from stages.stage_01_ety_cleaning.config import (
    AMOUNT_COLUMN,
    CASH_DISTRIBUTION_VALUE,
    DESCRIPTION_COLUMN,
    DIFFERENCE_COLUMN,
    DIFFERENCE_DECIMALS,
    DIFFERENCE_FORMULA,
    DIFFERENCE_TERMS,
    DUPLICATE_BLOCKING_COLUMNS,
    DUPLICATE_IGNORED_COLUMNS,
    DUPLICATE_TOLERATED_COLUMNS,
    GROSS_AMOUNT_COLUMN,
    INPUTS,
    MORE_INFO_COLUMN,
    NO_PROGRAM_REMOVAL_TEXTS,
    PROGRAM_COLUMN,
    VOUCHER_COLUMN,
)

# Tipo de cada columna del reporte, según config.INPUTS.
COLUMN_TYPES = INPUTS["ety_report"]["columns"]
# Columnas de valores (E a J), en el orden del reporte.
CURRENCY_COLUMNS = [c for c, t in COLUMN_TYPES.items() if t == "currency"]


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    df = inputs["ety_report"]
    audit.step(f"Convirtiendo a moneda las columnas {CURRENCY_COLUMNS[0]} a {CURRENCY_COLUMNS[-1]}")
    df = convert_currency_columns(df, audit)
    audit.step(f"Eliminando las filas con {DESCRIPTION_COLUMN} «{CASH_DISTRIBUTION_VALUE}»")
    df = remove_cash_distribution_rows(df, audit)
    audit.step(f"Agregando la columna {DIFFERENCE_COLUMN}")
    df = add_difference_column(df, audit)
    audit.step(f"Ordenando por {VOUCHER_COLUMN}")
    df = sort_rows(df, VOUCHER_COLUMN, audit, "TRA-102")
    audit.step(f"Eliminando los comprobantes con {GROSS_AMOUNT_COLUMN} en 0 (con {DIFFERENCE_COLUMN} 0)")
    df = remove_zero_gross_vouchers(df, audit)
    audit.step(f"Eliminando registros duplicados por {VOUCHER_COLUMN} (con {DIFFERENCE_COLUMN} 0)")
    df = remove_duplicate_vouchers(df, audit)
    audit.step(f"Eliminando los registros sin {PROGRAM_COLUMN} por su {MORE_INFO_COLUMN}")
    df = remove_no_program_rows(df, audit)
    # Al final de la depuración, para que solo se marquen los que siguen repetidos.
    audit.step(f"Revisando registros con {VOUCHER_COLUMN} repetido")
    flag_repeated_vouchers(df, audit)
    return df


def convert_currency_columns(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Convierte a moneda las columnas de valores (E a J: VR. BRUTO ... Importe). Regla TIP-005.

    Los valores que no son número quedan como estaban y se reportan como Error.
    """
    return convert_columns(df, {c: COLUMN_TYPES[c] for c in CURRENCY_COLUMNS}, audit)


def remove_cash_distribution_rows(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Elimina las filas con Descripción «Distribución Caja» (columna L). Regla LIM-101.

    Cada eliminada queda en la hoja Acciones del log con todos sus datos.
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


def flag_repeated_vouchers(df: pd.DataFrame, audit: AuditLog) -> None:
    """Señala como Advertencia los registros con Comprobante repetido (columna O). Regla VAL-101.

    No elimina registros: el usuario revisa si son duplicados reales. La celda
    queda resaltada en amarillo y el hallazgo aparece en la hoja Acciones del log.
    """
    flag_repeated_values(
        df, VOUCHER_COLUMN, audit, "VAL-101", WARNING,
        "Revisar si el registro está duplicado",
    )


def difference_values(df: pd.DataFrame) -> pd.Series:
    """Calcula en memoria el valor de la columna Diferencia (VR. BRUTO - ... - Importe).

    En el archivo la columna es una fórmula que Excel calcula al abrirlo; aquí se
    hace la misma resta, en el mismo orden y sin redondear. Las celdas vacías
    valen 0, como en Excel. Si algún valor no es número, el resultado es None.
    """
    def row_difference(row) -> float | None:
        values = [0.0 if is_empty(row[c]) else row[c] for c in DIFFERENCE_TERMS]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            return None
        result = values[0]
        for value in values[1:]:
            result -= value
        return result

    return pd.Series([row_difference(row) for _, row in df.iterrows()], index=df.index, dtype=object)


def zero_difference(df: pd.DataFrame) -> pd.Series:
    """True en los registros cuya Diferencia es 0 al centavo (DIFFERENCE_DECIMALS).

    Se compara al centavo porque la resta exacta puede dejar residuos que Excel
    muestra como 0. Si la Diferencia no se puede calcular, el registro no cuenta.
    """
    return pd.Series(
        [d is not None and round(d, DIFFERENCE_DECIMALS) == 0 for d in difference_values(df)],
        index=df.index,
        dtype=bool,   # Con la tabla vacía, pandas tomaría la máscara como una lista de columnas
    )


def remove_zero_gross_vouchers(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Elimina los registros con Diferencia 0 de un Comprobante cuando VR. BRUTO es 0
    en todos ellos. Regla LIM-102.

    Se agrupa por Comprobante (estén o no juntas las filas) y solo entre los
    registros con Diferencia 0; los demás se conservan. Un comprobante de una sola
    fila también cuenta. Una celda vacía vale 0, como en la fórmula de Diferencia;
    un valor que no es número no tiene Diferencia, así que no llega a evaluarse.
    """
    evaluated = df[zero_difference(df)]
    to_remove = pd.Series(False, index=df.index)
    reasons = pd.Series("", index=df.index, dtype=object)
    for voucher, group in evaluated.groupby(VOUCHER_COLUMN, sort=False):
        if not all(is_empty(v) or v == 0 for v in group[GROSS_AMOUNT_COLUMN]):
            continue
        records = "el registro" if len(group) == 1 else f"los {len(group)} registros"
        to_remove[group.index] = True
        reasons[group.index] = (
            f"{GROSS_AMOUNT_COLUMN} en 0 en {records} del {VOUCHER_COLUMN} {voucher} con {DIFFERENCE_COLUMN} 0"
        )
    return audit.remove_rows(df, to_remove, "LIM-102", reasons)


def differing_columns(group: pd.DataFrame, columns: list[str]) -> set[str]:
    """Columnas en las que no todas las filas del grupo tienen el mismo valor (vacíos iguales entre sí)."""
    def key(value):
        return None if is_empty(value) else value

    return {c for c in columns if len({key(v) for v in group[c]}) > 1}


def remove_duplicate_vouchers(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Elimina duplicados entre los registros con Diferencia 0 y el mismo Comprobante. Reglas DUP-101 y DUP-102.

    Diferencia 0 significa que la resta redondeada al centavo da 0 (DIFFERENCE_DECIMALS).
    Por cada grupo (mismo Comprobante, Diferencia 0, sin importar si las filas
    están juntas):
    - 2.1: todas las columnas iguales -> se conserva la primera, se eliminan las demás (DUP-101).
    - 2.2: solo difieren en Dpto, Cd Fnd y/o Producto -> igual (DUP-102).
    En 2.1 y 2.2 no se comparan FECHA DE PAGO, Asiento, LNP ni Nº Sec Doc
    (DUPLICATE_IGNORED_COLUMNS); la fila
    que se conserva mantiene sus propios valores en esas columnas.
    - 2.3: difieren en Subfideicomiso, Cuenta o Programa -> no se elimina nada.
    - 2.4: difieren en cualquier otra columna -> no se elimina nada.
    "La primera" es la que está más arriba en el archivo original (menor fila de origen).
    No se reordena ni se modifica nada: las filas que quedan conservan su posición.
    """
    evaluated = df[zero_difference(df)]
    # Diferencia es una fórmula derivada de las demás columnas: no se compara.
    # Las columnas ignoradas tampoco: pueden variar entre filas que sí son duplicadas.
    not_compared = {DIFFERENCE_COLUMN, *DUPLICATE_IGNORED_COLUMNS}
    compared = [c for c in data_columns(df) if c not in not_compared]

    to_remove = pd.Series(False, index=df.index)
    reasons = pd.Series("", index=df.index, dtype=object)
    rules = pd.Series("", index=df.index, dtype=object)
    kept_groups = {"2.3": [], "2.4": []}
    for voucher, group in evaluated.groupby(VOUCHER_COLUMN, sort=False):
        if len(group) < 2:
            continue
        differing = differing_columns(group, compared)
        if differing & set(DUPLICATE_BLOCKING_COLUMNS):
            kept_groups["2.3"].append(voucher)
            continue
        if differing - set(DUPLICATE_TOLERATED_COLUMNS):
            kept_groups["2.4"].append(voucher)
            continue
        rule, case = ("DUP-101", "2.1") if not differing else ("DUP-102", "2.2")
        first = group[SOURCE_ROW].idxmin()
        for index in group.index.drop(first):
            to_remove.at[index] = True
            rules.at[index] = rule
            reasons.at[index] = (
                f"Duplicado de la fila {group.at[first, SOURCE_ROW]} "
                f"({VOUCHER_COLUMN} {voucher}, caso {case})"
            )

    for rule in ("DUP-101", "DUP-102"):
        mask = to_remove & (rules == rule)
        if mask.any():
            df = audit.remove_rows(df, mask[df.index], rule, reasons[df.index])
    audit.note(audit.step_summary())
    for case, label in (("2.3", "difieren en Subfideicomiso, Cuenta o Programa"), ("2.4", "difieren en otras columnas")):
        if kept_groups[case]:
            vouchers = ", ".join(str(v) for v in kept_groups[case])
            count = len(kept_groups[case])
            groups = "Se conserva 1 grupo" if count == 1 else f"Se conservan {count} grupos"
            audit.note(f"{groups} porque {label} (caso {case}): {vouchers}")
    return df


def remove_no_program_rows(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Elimina los registros sin Programa (columna Y) cuyo Más Info (columna R) contiene
    alguno de los textos de NO_PROGRAM_REMOVAL_TEXTS. Regla LIM-103.

    El texto se busca dentro de la celda, sin tener en cuenta mayúsculas, tildes ni
    espacios sobrantes. Cada eliminada queda en la hoja Acciones con el texto encontrado.
    """
    targets = [(text, comparable_text(text)) for text in NO_PROGRAM_REMOVAL_TEXTS]
    to_remove = pd.Series(False, index=df.index)
    reasons = pd.Series("", index=df.index, dtype=object)
    for index, row in df.iterrows():
        # comparable_text deja vacía una celda con solo espacios: cuenta como sin Programa.
        if comparable_text(row[PROGRAM_COLUMN]):
            continue
        more_info = comparable_text(row[MORE_INFO_COLUMN])
        found = next((text for text, target in targets if target in more_info), None)
        if found:
            to_remove.at[index] = True
            reasons.at[index] = f"Sin {PROGRAM_COLUMN} y {MORE_INFO_COLUMN} con «{found}»"
    return audit.remove_rows(df, to_remove, "LIM-103", reasons)
