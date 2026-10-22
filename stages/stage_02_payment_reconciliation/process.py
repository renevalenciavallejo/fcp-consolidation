"""Lógica de la Etapa 2 - Conciliación de pagos.

La validación de estructura la hace el ejecutor antes de llamar a process(): el
reporte ETY procesado en la Etapa 1 y la hoja Pagos de cada informe de pago de
Tesorería (uno por fecha). Aquí van las reglas propias de la etapa, en el orden de
ESPECIFICACION.md. Las reglas de conciliación se agregan a medida que se especifiquen.
"""

from datetime import date
from typing import Any

import pandas as pd

from core.audit import AuditLog
from core.cleaning import comparable_text, parse_date
from core.runner import StageError
from core.settings import DATE_FORMAT_TEXT, INPUT_DATE, SOURCE_FILE, SOURCE_ROW
from stages.stage_02_payment_reconciliation.config import (
    BUSINESS_UNIT,
    BUSINESS_UNIT_COLUMN,
    EXECUTION_DATE_COLUMN,
    MAX_ROWS_IN_MESSAGE,
)


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    audit.step(f"Tomando de los informes de pago los registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT}")
    payments = filter_business_unit(inputs["treasury_reports"], audit)
    audit.step(f"Verificando que la {EXECUTION_DATE_COLUMN} corresponda a la fecha de cada informe")
    check_execution_dates(payments, audit)
    return inputs["ety_processed"]


def filter_business_unit(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Deja solo los pagos de la unidad de negocio del FCP (UN AP656). Regla LIM-201.

    El informe de Tesorería trae los pagos de todas las unidades de negocio. Los
    demás registros no son del FCP: en el log solo se cuenta cuántos se tomaron de
    cada informe, porque listarlos uno a uno (cientos por informe) taparía lo importante.
    """
    target = comparable_text(BUSINESS_UNIT)
    keep = df[BUSINESS_UNIT_COLUMN].map(lambda value: comparable_text(value) == target).astype(bool)
    for name, in_file in keep.groupby(df[SOURCE_FILE], sort=False):
        audit.note(
            f"{name}: {in_file.sum()} de {len(in_file)} registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT}"
        )
    return df[keep]


def check_execution_dates(df: pd.DataFrame, audit: AuditLog) -> None:
    """Verifica que la F Ejec de cada pago sea la fecha del campo donde se cargó su informe. Regla VAL-201.

    Una fecha distinta indica, casi siempre, que el informe se cargó en el campo de
    otra fecha. Por eso se detiene sin generar resultados, como un error de estructura,
    y se explica qué informe falla, con qué fechas y en qué filas.
    """
    problems = []
    for (name, day), rows in df.groupby([SOURCE_FILE, INPUT_DATE], sort=False):
        found = rows[EXECUTION_DATE_COLUMN].map(execution_day)
        is_wrong = found != day
        if not is_wrong.any():
            audit.note(f"{name}: {len(rows)} registros del {day.strftime(DATE_FORMAT_TEXT)}")
        else:
            problems.append(date_problem(name, day, rows[is_wrong], found[is_wrong], len(rows)))
    if problems:
        for problem in problems:
            audit.note(problem, ok=False)
        audit.finish_step()
        count = "1 informe" if len(problems) == 1 else f"{len(problems)} informes"
        message = (
            f"La {EXECUTION_DATE_COLUMN} de {count} de pago no coincide con la fecha del campo donde se cargó."
        )
        raise StageError(message, problems, audit.step_lines())


def execution_day(value: Any) -> date | None:
    """Día de ejecución de un pago, sin la hora. None si está vacío o no es una fecha."""
    try:
        parsed = parse_date(value)
    except ValueError:
        return None
    return parsed.date() if parsed else None


def date_problem(name: str, day: date, wrong: pd.DataFrame, found: pd.Series, total: int) -> str:
    """Mensaje para el usuario: qué fechas se encontraron en el informe y en qué filas."""
    details = []
    for value, rows in wrong.groupby(found.map(_date_text), sort=False):
        records = "1 registro" if len(rows) == 1 else f"{len(rows)} registros"
        details.append(f"{value} en {records} ({_rows_text(list(rows[SOURCE_ROW]))})")
    return (
        f"[VAL-201] «{name}» se cargó como informe del {day.strftime(DATE_FORMAT_TEXT)}, pero "
        f"{len(wrong)} de sus {total} registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT} tienen otra "
        f"{EXECUTION_DATE_COLUMN}: {'; '.join(details)}. Verifique que cargó el informe en el campo de su fecha."
    )


def _date_text(value: date | None) -> str:
    return value.strftime(DATE_FORMAT_TEXT) if value else "vacía o no válida"


def _rows_text(rows: list[int]) -> str:
    """Filas de ejemplo para el mensaje; si son muchas, las demás solo se cuentan."""
    shown = ", ".join(str(row) for row in rows[:MAX_ROWS_IN_MESSAGE])
    hidden = len(rows) - MAX_ROWS_IN_MESSAGE
    label = "fila" if len(rows) == 1 else "filas"
    return f"{label} {shown}" + (f" y {hidden} más" if hidden > 0 else "")
