"""Construcción del archivo de log en Excel (Ejecución, Acciones, Reglas)."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from openpyxl import Workbook

from core.audit import AuditLog
from core.writer import to_bytes, write_table


@dataclass
class InputFileInfo:
    """Un archivo de entrada y cuántos registros se leyeron de él."""

    input_label: str
    file_name: str
    rows: int


@dataclass
class RunSummary:
    """Datos generales de un procesamiento, para la interfaz y la línea de comandos."""

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
    # Reglas que aplica la etapa, en orden: (código, descripción). Van en la hoja Reglas.
    applied_rules: list[tuple[str, str]] = field(default_factory=list)


def build_log(summary: RunSummary, audit: AuditLog) -> bytes:
    """Genera el log en Excel con tres hojas: Ejecución (los pasos, como en pantalla),
    Acciones (la misma tabla «Acciones realizadas» de la interfaz) y Reglas."""
    workbook = Workbook()
    sheets = {
        "Ejecución": audit.steps_df(),
        "Acciones": audit.actions_df(),
        "Reglas": rules_table(summary.applied_rules),
    }
    workbook.remove(workbook.active)
    for title, table in sheets.items():
        write_table(workbook.create_sheet(title), table)
    return to_bytes(workbook)


def rules_table(rules: list[tuple[str, str]]) -> pd.DataFrame:
    """Tabla de reglas de la etapa (Orden, Código, Regla), para la interfaz y el log."""
    return pd.DataFrame(
        [(number, code, description) for number, (code, description) in enumerate(rules, start=1)],
        columns=["Orden", "Código", "Regla"],
        dtype=object,
    )
