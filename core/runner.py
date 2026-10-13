"""Ejecutor: flujo estándar de cualquier etapa (ver CLAUDE.md, sección 5).

Trabaja en memoria: recibe archivos (rutas, BytesIO o archivos cargados en
Streamlit) y devuelve el archivo de salida y el log como bytes. Cada interfaz
decide qué hacer con ellos.
"""

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
from core.reader import ReadResult, combine, read_file
from core.settings import OUTPUT_DIR
from core.stage import input_specs, stage_prefix, stage_rules
from core.writer import build_output

# Pasos que se informan a la interfaz mientras avanza el procesamiento.
STEPS = [
    "Verificando archivos cargados",
    "Leyendo y validando la estructura de los archivos",
    "Aplicando las reglas de la etapa",
    "Generando el archivo de salida y el log",
]


class StageError(Exception):
    """Problema que impide procesar (estructura inválida, archivos faltantes).

    `problems` tiene un mensaje en español por cada problema encontrado, para
    que el usuario pueda corregirlos todos de una vez.
    """

    def __init__(self, message: str, problems: list[str]):
        super().__init__(message)
        self.message = message
        self.problems = problems


@dataclass
class StageResult:
    """Todo lo que produce un procesamiento."""

    summary: RunSummary
    audit: AuditLog
    output_file_name: str
    log_file_name: str
    output_bytes: bytes
    log_bytes: bytes


ProgressCallback = Callable[[int, int, str], None]


def run_stage(
    stage: ModuleType,
    files: dict[str, list[Any]],
    progress: ProgressCallback | None = None,
) -> StageResult:
    """Ejecuta una etapa completa sobre los archivos dados.

    `files` tiene una llave por entrada declarada en la etapa y, como valor, la
    lista de archivos de esa entrada. Lanza StageError si los archivos no
    cumplen la estructura esperada; en ese caso no se genera ningún resultado.
    """
    started_at = datetime.now()
    start = time.perf_counter()
    specs = input_specs(stage)

    def report(step: int) -> None:
        if progress is not None:
            progress(step, len(STEPS), STEPS[step - 1])

    # 1. Verificación de entradas
    report(1)
    problems = check_inputs(specs, files)
    if problems:
        raise StageError(_inputs_message(files), problems)

    # 2 y 3. Lectura y validación estricta, archivo por archivo
    report(2)
    read_results: dict[str, list[ReadResult]] = {}
    for spec in specs:
        read_results[spec.key] = [read_file(f, spec) for f in files.get(spec.key, [])]
    problems = [p for results in read_results.values() for r in results for p in r.problems]
    if problems:
        failed = sum(1 for results in read_results.values() for r in results if r.problems)
        raise StageError(_structure_message(failed, _count_files(files)), problems)
    inputs = {spec.key: combine(read_results[spec.key], spec) for spec in specs}

    # 4. Procesamiento de la etapa
    report(3)
    audit = AuditLog(stage_rules(stage))
    output = stage.process(inputs, audit)
    if not isinstance(output, pd.DataFrame):
        raise TypeError(f"La etapa {stage.__name__} debe devolver un DataFrame en process().")

    # 5. Construcción de resultados
    report(4)
    prefix = stage_prefix(stage)
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    output_name = f"{prefix}_procesado_{timestamp}.xlsx"
    log_name = f"{prefix}_log_{timestamp}.xlsx"

    input_files = [
        InputFileInfo(spec.label, r.file_name, r.rows) for spec in specs for r in read_results[spec.key]
    ]
    output_bytes = build_output(output, audit.findings)
    summary = RunSummary(
        stage_name=stage.NAME,
        started_at=started_at,
        duration_seconds=time.perf_counter() - start,
        output_file_name=output_name,
        rows_read=sum(info.rows for info in input_files),
        rows_output=len(output),
        rows_removed=len(audit.removals),
        cells_changed=len({(c.source_file, c.source_row, c.column) for c in audit.changes}),
        findings_by_severity=audit.findings_by_severity(),
        rule_counts=audit.rule_counts(),
        input_files=input_files,
    )
    log_bytes = build_log(summary, audit)
    return StageResult(summary, audit, output_name, log_name, output_bytes, log_bytes)


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
