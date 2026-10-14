"""Construcción del archivo de log en Excel (Resumen, Hallazgos, Cambios, Eliminados)."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from openpyxl import Workbook

from core.audit import AuditLog
from core.settings import APP_NAME, APP_VERSION, DATE_FORMAT_TEXT
from core.writer import to_bytes, write_table


@dataclass
class InputFileInfo:
    """Un archivo de entrada y cuántos registros se leyeron de él."""

    input_label: str
    file_name: str
    rows: int


@dataclass
class RunSummary:
    """Datos generales de un procesamiento, para la hoja Resumen y la interfaz."""

    stage_name: str
    started_at: datetime
    duration_seconds: float
    output_file_name: str
    rows_read: int
    rows_output: int
    rows_removed: int              # Registros de datos eliminados (sin contar filas de título)
    cells_changed: int
    findings_by_severity: dict[str, int]
    rule_counts: dict[str, int]
    input_files: list[InputFileInfo] = field(default_factory=list)
    title_rows_removed: int = 0    # Filas de título anteriores a los encabezados


def build_log(summary: RunSummary, audit: AuditLog) -> bytes:
    """Genera el log en Excel con las cuatro hojas definidas en los lineamientos."""
    workbook = Workbook()
    sheets = {
        "Resumen": _summary_table(summary, audit),
        "Hallazgos": audit.findings_df(),
        "Cambios": audit.changes_df(),
        "Eliminados": audit.removals_df(),
    }
    workbook.remove(workbook.active)
    for title, table in sheets.items():
        write_table(workbook.create_sheet(title), table)
    return to_bytes(workbook)


def _summary_table(summary: RunSummary, audit: AuditLog) -> pd.DataFrame:
    """Resumen como una sola tabla (Sección, Concepto, Valor) para poder filtrarla."""
    rows = [
        ("General", "Herramienta", APP_NAME),
        ("General", "Versión de la herramienta", APP_VERSION),
        ("General", "Etapa", summary.stage_name),
        ("General", "Fecha y hora", summary.started_at.strftime(f"{DATE_FORMAT_TEXT} %H:%M:%S")),
        ("General", "Duración (segundos)", round(summary.duration_seconds, 2)),
        ("General", "Archivo de salida", summary.output_file_name),
    ]
    for info in summary.input_files:
        rows.append(("Archivos de entrada", f"{info.input_label}: {info.file_name}", f"{info.rows} registros leídos"))
    rows += [
        ("Totales", "Registros leídos", summary.rows_read),
        ("Totales", "Registros en salida", summary.rows_output),
        ("Totales", "Registros eliminados", summary.rows_removed),
        ("Totales", "Filas de título eliminadas", summary.title_rows_removed),
        ("Totales", "Celdas modificadas", summary.cells_changed),
    ]
    for added in audit.added_columns:
        rows.append(("Columnas agregadas", f"{added.column} ({added.rule} - {audit.rules[added.rule]})", f"{added.rows} filas"))
    for severity, count in summary.findings_by_severity.items():
        rows.append(("Hallazgos por severidad", severity, count))
    for rule, count in summary.rule_counts.items():
        rows.append(("Aplicaciones por regla", f"{rule} - {audit.rules[rule]}", count))
    return pd.DataFrame(rows, columns=["Sección", "Concepto", "Valor"], dtype=object)
