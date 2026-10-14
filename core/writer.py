"""Construcción de archivos de Excel con el formato estándar de la herramienta."""

from datetime import date, datetime
from io import BytesIO
from typing import Any

import re
from dataclasses import dataclass

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from core.audit import Finding, data_columns, is_empty
from core.settings import (
    DATE_FORMAT_EXCEL,
    MAX_COLUMN_WIDTH,
    NUMBER_FORMAT_EXCEL,
    SEVERITY_FILLS,
    SOURCE_FILE,
    SOURCE_ROW,
)

# Referencia a otra columna dentro de una fórmula: {Nombre de la columna}.
COLUMN_REFERENCE = re.compile(r"\{([^}]+)\}")

# Ancho (en caracteres) de las columnas con fórmulas, cuyo texto no es lo que se ve.
FORMULA_COLUMN_WIDTH = 16


@dataclass(frozen=True)
class ExcelFormula:
    """Fórmula de Excel que se escribe en cada fila del archivo de salida.

    Las columnas se nombran entre llaves y se convierten en la celda de la misma
    fila al escribir, por ejemplo "={VR. BRUTO}-{Importe}" -> "=E2-J2". Así la
    fórmula sigue siendo correcta aunque cambie la posición de las columnas.
    """

    template: str
    number_format: str | None = None


# Orden de prioridad de las severidades cuando una celda tiene varios hallazgos.
SEVERITY_PRIORITY = list(SEVERITY_FILLS)


def build_output(
    df: pd.DataFrame,
    findings: list[Finding],
    column_formats: dict[str, str] | None = None,
    sheet_name: str = "Datos",
) -> bytes:
    """Genera el archivo de salida: datos procesados sin columnas internas.

    `column_formats` indica un formato de Excel por columna (por ejemplo, moneda);
    las demás columnas usan el formato según el tipo de valor.
    Las celdas con hallazgos se resaltan según la severidad.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    write_table(sheet, df[data_columns(df)], column_formats)
    _highlight_findings(sheet, df, findings)
    return to_bytes(workbook)


def write_table(sheet: Worksheet, df: pd.DataFrame, column_formats: dict[str, str] | None = None) -> None:
    """Escribe un DataFrame con encabezados en negrita, filtros, paneles inmovilizados y anchos ajustados."""
    columns = list(df.columns)
    sheet.append([str(c) for c in columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    letters = {column: get_column_letter(i + 1) for i, column in enumerate(columns)}
    for row_number, values in enumerate(df.itertuples(index=False), start=2):
        sheet.append([_excel_value(v, letters, row_number) for v in values])

    formats = column_formats or {}
    formula_formats = _formula_formats(df)
    for row in sheet.iter_rows(min_row=2):
        for cell, column in zip(row, columns):
            if column in formula_formats:
                if formula_formats[column]:
                    cell.number_format = formula_formats[column]
                continue
            is_number = isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)
            if column in formats and is_number:
                cell.number_format = formats[column]
            elif isinstance(cell.value, (datetime, date)):
                cell.number_format = DATE_FORMAT_EXCEL
            elif isinstance(cell.value, float):
                cell.number_format = NUMBER_FORMAT_EXCEL

    if columns:
        sheet.auto_filter.ref = sheet.dimensions
    sheet.freeze_panes = "A2"
    _adjust_widths(sheet)


def to_bytes(workbook: Workbook) -> bytes:
    """Guarda el libro en memoria y devuelve su contenido."""
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _excel_value(value: Any, letters: dict[str, str] | None = None, row_number: int = 0) -> Any:
    """Prepara un valor para Excel: vacíos como celda vacía, fechas de pandas como datetime
    y fórmulas con las referencias a columnas convertidas en celdas de la fila."""
    if isinstance(value, ExcelFormula):
        return _resolve_formula(value, letters or {}, row_number)
    if is_empty(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        return value.item()  # Tipos de numpy -> tipos de Python
    return value


def _resolve_formula(formula: ExcelFormula, letters: dict[str, str], row_number: int) -> str:
    def cell_reference(match: re.Match) -> str:
        column = match.group(1)
        if column not in letters:
            raise ValueError(f"La fórmula '{formula.template}' usa la columna '{column}', que no existe.")
        return f"{letters[column]}{row_number}"

    return COLUMN_REFERENCE.sub(cell_reference, formula.template)


def _formula_formats(df: pd.DataFrame) -> dict[str, str | None]:
    """Columnas que contienen fórmulas y el formato de número que llevan."""
    formats = {}
    for column in df.columns:
        first = next((v for v in df[column] if isinstance(v, ExcelFormula)), None)
        if first is not None:
            formats[column] = first.number_format
    return formats


def _adjust_widths(sheet: Worksheet) -> None:
    for column_cells in sheet.columns:
        longest = 0
        for cell in column_cells:
            if cell.value is None:
                continue
            if isinstance(cell.value, (datetime, date)):
                length = 10
            elif isinstance(cell.value, float):
                length = len(f"$ {cell.value:,.2f}")
            elif isinstance(cell.value, str) and cell.value.startswith("="):
                length = FORMULA_COLUMN_WIDTH
            else:
                length = len(str(cell.value))
            longest = max(longest, length)
        letter = get_column_letter(column_cells[0].column)
        sheet.column_dimensions[letter].width = min(longest + 2, MAX_COLUMN_WIDTH)


def _highlight_findings(sheet: Worksheet, df: pd.DataFrame, findings: list[Finding]) -> None:
    """Colorea las celdas que tienen hallazgos. Si el registro o la columna ya no están, se omite."""
    if SOURCE_FILE not in df.columns or SOURCE_ROW not in df.columns:
        return
    output_rows = {
        (file, int(row)): position + 2  # +2: encabezado y Excel empieza en 1
        for position, (file, row) in enumerate(zip(df[SOURCE_FILE], df[SOURCE_ROW]))
    }
    output_columns = {c: i + 1 for i, c in enumerate(data_columns(df))}

    severity_by_cell: dict[tuple[int, int], str] = {}
    for finding in findings:
        if finding.severity not in SEVERITY_FILLS:
            continue
        row = output_rows.get((finding.source_file, finding.source_row))
        column = output_columns.get(finding.column)
        if row is None or column is None:
            continue
        current = severity_by_cell.get((row, column))
        if current is None or SEVERITY_PRIORITY.index(finding.severity) < SEVERITY_PRIORITY.index(current):
            severity_by_cell[(row, column)] = finding.severity

    for (row, column), severity in severity_by_cell.items():
        color = SEVERITY_FILLS[severity]
        sheet.cell(row=row, column=column).fill = PatternFill("solid", start_color=color, end_color=color)
