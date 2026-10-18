"""Ejecutor: flujo estándar de cualquier etapa (ver CLAUDE.md, sección 5).

Trabaja en memoria: recibe archivos (rutas, BytesIO o archivos cargados en
Streamlit) y devuelve el archivo de salida y el log como bytes. Cada interfaz
decide qué hacer con ellos.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd

from core.audit import AuditLog
from core.log_report import InputFileInfo, RunSummary, build_log
from core.reader import ReadResult, combine, file_name, read_file
from core.settings import CURRENCY_FORMAT_EXCEL, OUTPUT_DIR
from core.stage import applied_rules, input_specs, stage_prefix, stage_rules
from core.writer import SheetStyle, build_output

class StageError(Exception):
    """Problema que impide procesar (estructura inválida, archivos faltantes).

    `problems` tiene un mensaje en español por cada problema encontrado, para
    que el usuario pueda corregirlos todos de una vez. `steps` es el log de
    ejecución hasta el momento del error, para mostrar en qué paso falló.
    """

    def __init__(self, message: str, problems: list[str], steps: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.problems = problems
        self.steps = steps or []


@dataclass
class StageResult:
    """Todo lo que produce un procesamiento."""

    summary: RunSummary
    audit: AuditLog
    output_file_name: str
    log_file_name: str
    output_bytes: bytes
    log_bytes: bytes


# Sufijo que la herramienta agrega a los archivos procesados (por ejemplo "_E01_procesado").
PROCESSED_SUFFIX = r"_E\d{2}_procesado$"

# Recibe cada línea del log de ejecución apenas se produce.
ProgressCallback = Callable[[str], None]


def run_stage(
    stage: ModuleType,
    files: dict[str, list[Any]],
    progress: ProgressCallback | None = None,
) -> StageResult:
    """Ejecuta una etapa completa sobre los archivos dados.

    `files` tiene una llave por entrada declarada en la etapa y, como valor, la
    lista de archivos de esa entrada. Lanza StageError si los archivos no
    cumplen la estructura esperada; en ese caso no se genera ningún resultado.
    `progress` recibe cada línea del log de ejecución mientras avanza.
    """
    started_at = datetime.now()
    start = time.perf_counter()
    specs = input_specs(stage)
    # Se crea desde el inicio para que la verificación y la validación también queden en el log.
    audit = AuditLog(stage_rules(stage), on_line=progress)

    # 1. Verificación de entradas
    audit.step("Verificando archivos cargados")
    problems = check_inputs(specs, files)
    if problems:
        for problem in problems:
            audit.note(problem, ok=False)
        raise StageError(_inputs_message(files), problems, audit.step_lines())
    names = [file_name(f) for spec in specs for f in files.get(spec.key, [])]
    audit.multiple_files = len(names) > 1
    audit.note(f"{'1 archivo' if len(names) == 1 else f'{len(names)} archivos'}: {', '.join(names)}")

    # 2 y 3. Lectura y validación estricta, archivo por archivo
    read_results: dict[str, list[ReadResult]] = {}
    for spec in specs:
        read_results[spec.key] = [read_and_report(f, spec, audit) for f in files.get(spec.key, [])]
    problems = [p for results in read_results.values() for r in results for p in r.problems]
    if problems:
        failed = sum(1 for results in read_results.values() for r in results if r.problems)
        audit.finish_step()
        raise StageError(_structure_message(failed, _count_files(files)), problems, audit.step_lines())
    inputs = {spec.key: combine(read_results[spec.key], spec) for spec in specs}
    for data in inputs.values():
        audit.remember_source_rows(data)

    # 4. Procesamiento de la etapa
    title_rows = remove_title_rows(read_results, audit)
    audit.finish_step()
    # La etapa abre un paso (audit.step) antes de cada regla, para que se vea en el log.
    output = stage.process(inputs, audit)
    if not isinstance(output, pd.DataFrame):
        raise TypeError(f"La etapa {stage.__name__} debe devolver un DataFrame en process().")

    # 5. Construcción de resultados
    audit.step("Generando el archivo de salida y el log")
    output_name, log_name = result_file_names(stage, names)

    input_files = [
        InputFileInfo(spec.label, r.file_name, r.rows) for spec in specs for r in read_results[spec.key]
    ]
    output_bytes = build_output(output, audit.findings, output_formats(specs), output_style(read_results))
    summary = RunSummary(
        stage_name=stage.NAME,
        started_at=started_at,
        duration_seconds=time.perf_counter() - start,
        output_file_name=output_name,
        rows_read=sum(info.rows for info in input_files),
        rows_output=len(output),
        rows_removed=len(audit.removals) - title_rows,
        title_rows_removed=title_rows,
        cells_changed=len({(c.source_file, c.source_row, c.column) for c in audit.changes}),
        findings_by_severity=audit.findings_by_severity(),
        rule_counts=audit.rule_counts(),
        input_files=input_files,
        applied_rules=applied_rules(stage),
    )
    # Se anota antes de construir el log para que también quede en su hoja Ejecución.
    audit.note(f"Terminado en {summary.duration_seconds:.1f} s".replace(".", ","))
    audit.finish_step()
    log_bytes = build_log(summary, audit)
    return StageResult(summary, audit, output_name, log_name, output_bytes, log_bytes)


def result_file_names(stage: ModuleType, input_names: list[str]) -> tuple[str, str]:
    """Nombres del archivo procesado y del log: el nombre del archivo original, sin
    cambios, seguido de la etapa (`ETY_sept.xlsx` -> `ETY_sept_E01_procesado.xlsx`).

    Si el archivo ya viene procesado por otra etapa, se quita ese sufijo para que el
    nombre no crezca de etapa en etapa (`ETY_sept_E01_procesado` -> `ETY_sept_E02_...`).
    Con varios archivos no hay un único nombre original y se usa el de la etapa.
    """
    code, stage_name = stage_prefix(stage).split("_", 1)
    if len(input_names) == 1:
        base = re.sub(PROCESSED_SUFFIX, "", Path(input_names[0]).stem)
    else:
        base = stage_name
    return f"{base}_{code}_procesado.xlsx", f"{base}_{code}_log.xlsx"


def output_formats(specs: list) -> dict[str, str]:
    """Formato de Excel por columna según el tipo declarado en las entradas de la etapa."""
    return {
        column: CURRENCY_FORMAT_EXCEL
        for spec in specs
        for column, column_type in spec.columns.items()
        if column_type == "currency"
    }


def output_style(read_results: dict[str, list[ReadResult]]) -> SheetStyle | None:
    """Apariencia que tendrá el archivo de salida: la del primer archivo cargado.

    Con varios archivos se toma el primero de la primera entrada, que es el que
    tiene la estructura principal de la etapa.
    """
    for results in read_results.values():
        for result in results:
            if result.style:
                return result.style
    return None


def remove_title_rows(read_results: dict[str, list[ReadResult]], audit: AuditLog) -> int:
    """Registra como eliminadas las filas anteriores a los encabezados. Regla LIM-003.

    El lector ya las dejó por fuera de los datos (no son registros); aquí solo se
    deja constancia en el log. Devuelve cuántas filas se registraron.
    """
    if any(result.title_rows for results in read_results.values() for result in results):
        audit.step("Eliminando las filas de título del reporte")
    count = 0
    for results in read_results.values():
        for result in results:
            for row_number, content in result.title_rows:
                audit.removal(
                    result.file_name, row_number, "LIM-003",
                    "Fila de título del reporte, anterior a los encabezados", content,
                )
                count += 1
    return count


def read_and_report(file: Any, spec, audit: AuditLog) -> ReadResult:
    """Lee y valida un archivo, y deja en el log de ejecución si se pudo abrir y si su
    estructura es la esperada (con cada problema encontrado)."""
    result = read_file(file, spec)
    audit.step(f"Abriendo «{result.file_name}»")
    if not result.opened:
        for problem in result.problems:
            audit.note(problem, ok=False)
        return result
    audit.note("Archivo .xlsx válido")
    audit.step(f"Validando la estructura de «{result.file_name}»")
    for problem in result.problems:
        audit.note(problem, ok=False)
    if not result.problems:
        order = " en el orden esperado" if spec.check_column_order else ""
        records = "1 registro" if result.rows == 1 else f"{result.rows} registros"
        audit.note(f"{len(spec.columns)} columnas{order}, {records}")
    return result


def _count_files(files: dict[str, list[Any]]) -> int:
    return sum(len(f or []) for f in files.values())


def _inputs_message(files: dict[str, list[Any]]) -> str:
    """Mensaje principal cuando los archivos cargados no son los que pide la etapa."""
    count = _count_files(files)
    if count == 0:
        return "No se cargó ningún archivo."
    if count == 1:
        return "El archivo cargado no corresponde a lo que necesita la etapa."
    return "Los archivos cargados no corresponden a lo que necesita la etapa."


def _structure_message(failed: int, total: int) -> str:
    """Mensaje principal de los errores de estructura, en singular o plural según el caso."""
    if total == 1:
        return "La estructura del archivo no es la esperada."
    if failed == 1:
        return f"La estructura de 1 de los {total} archivos no es la esperada."
    return f"La estructura de {failed} de los {total} archivos no es la esperada."


def check_inputs(specs: list, files: dict[str, list[Any]]) -> list[str]:
    """Verifica que estén las entradas obligatorias y que no sobren archivos. Regla EST-007."""
    problems = []
    known = [spec.key for spec in specs]
    for key in files:
        if key not in known:
            problems.append(f"[EST-007] La entrada '{key}' no existe en esta etapa. Entradas válidas: {', '.join(known)}.")
    for spec in specs:
        count = len(files.get(spec.key) or [])
        if spec.required and count == 0:
            problems.append(f"[EST-007] Falta cargar: {spec.label}.")
        if not spec.multiple and count > 1:
            problems.append(f"[EST-007] '{spec.label}' acepta un solo archivo y se cargaron {count}.")
    return problems


def save_result(result: StageResult, folder: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    """Guarda una copia del archivo de salida y del log. Nunca sobrescribe un archivo existente."""
    folder.mkdir(parents=True, exist_ok=True)
    output_path = _write_new_file(folder, result.output_file_name, result.output_bytes)
    log_path = _write_new_file(folder, result.log_file_name, result.log_bytes)
    return output_path, log_path


def _write_new_file(folder: Path, name: str, content: bytes) -> Path:
    """Escribe el archivo; si ya existe uno con ese nombre, agrega _1, _2, ... al final."""
    path = folder / name
    counter = 1
    while True:
        try:
            with open(path, "xb") as file:  # "x": falla si el archivo ya existe
                file.write(content)
            return path
        except FileExistsError:
            path = folder / f"{Path(name).stem}_{counter}{Path(name).suffix}"
            counter += 1
