"""Construcción de archivos de Excel con el formato estándar de la herramienta."""

from datetime import date, datetime
from io import BytesIO
from typing import Any

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

# Orden de prioridad de las severidades cuando una celda tiene varios hallazgos.
SEVERITY_PRIORITY = list(SEVERITY_FILLS)


def build_output(df: pd.DataFrame, findings: list[Finding], sheet_name: str = "Datos") -> bytes:
    """Genera el archivo de salida: datos procesados sin columnas internas.

    Las celdas con hallazgos se resaltan según la severidad.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    write_table(sheet, df[data_columns(df)])
    _highlight_findings(sheet, df, findings)
    return to_bytes(workbook)


def write_table(sheet: Worksheet, df: pd.DataFrame) -> None:
    """Escribe un DataFrame con encabezados en negrita, filtros, paneles inmovilizados y anchos ajustados."""
    columns = list(df.columns)
    sheet.append([str(c) for c in columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for values in df.itertuples(index=False):
        sheet.append([_excel_value(v) for v in values])

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, (datetime, date)):
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


def _excel_value(value: Any) -> Any:
    """Prepara un valor para Excel: vacíos como celda vacía y fechas de pandas como datetime."""
    if is_empty(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        return value.item()  # Tipos de numpy -> tipos de Python
    return value


def _adjust_widths(sheet: Worksheet) -> None:
    for column_cells in sheet.columns:
        longest = 0
        for cell in column_cells:
            if cell.value is None:
                continue
            if isinstance(cell.value, (datetime, date)):
                length = 10
            elif isinstance(cell.value, float):
                length = len(f"{cell.value:,.2f}")
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
