"""Ejecutor: flujo estándar de cualquier etapa (ver CLAUDE.md, sección 5).

Trabaja en memoria: recibe archivos (rutas, BytesIO o archivos cargados en
Streamlit) y devuelve el archivo de salida y el log como bytes. Cada interfaz
decide qué hacer con ellos.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd

from core.audit import AuditLog
from core.cleaning import parse_date
from core.log_report import InputFileInfo, RunSummary, build_log
from core.reader import ReadResult, combine, file_name, read_file
from core.settings import CURRENCY_FORMAT_EXCEL, DATE_FORMAT_TEXT, INPUT_DATE, OUTPUT_DIR
from core.stage import InputSpec, applied_rules, date_label, input_specs, stage_prefix, stage_rules
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


@dataclass
class DateFileAnalysis:
    """Resultado de analizar el archivo de una fecha apenas se carga (analyze_date_file)."""

    audit: AuditLog        # Log de ejecución y acciones del análisis
    summary: list[str]     # Información calculada por la etapa, para mostrar debajo del cargador
    ok: bool = True        # False si la etapa encontró diferencias (la interfaz lo muestra en rojo)


@dataclass
class DateSources:
    """Archivos de origen de las entradas por fecha, ya leídos y validados (load_date_sources)."""

    dates: dict[str, list[date]]      # Fechas de cada entrada por fecha
    data: dict[str, pd.DataFrame]     # Datos de cada entrada de origen, para analizar cada archivo


# Marca que la herramienta agrega a los archivos procesados (por ejemplo "_E01_procesado").
PROCESSED_MARK = r"(_E\d{2}_procesado)"
# Número que se agrega cuando ya existe una copia: "_1" en output/ o " (1)" del navegador.
COPY_NUMBER = r"(_\d+| \(\d+\))?$"

# Recibe cada línea del log de ejecución apenas se produce.
ProgressCallback = Callable[[str], None]

# Archivos cargados por entrada: una lista o, en las entradas por fecha, {fecha: archivo}.
StageFiles = dict[str, list[Any] | dict[date, Any]]


def run_stage(
    stage: ModuleType,
    files: StageFiles,
    progress: ProgressCallback | None = None,
) -> StageResult:
    """Ejecuta una etapa completa sobre los archivos dados.

    `files` tiene una llave por entrada declarada en la etapa y, como valor, la
    lista de archivos de esa entrada. En una entrada por fecha (`per_date`), el
    valor es un diccionario {fecha: archivo}. Lanza StageError si los archivos no
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
    names = [file_name(f) for spec in specs for f in _files_of(spec, files)]
    audit.multiple_files = len(names) > 1
    audit.note(f"{'1 archivo' if len(names) == 1 else f'{len(names)} archivos'}: {', '.join(names)}")
    # Un nombre inesperado no detiene el proceso (el usuario pudo renombrar el archivo), pero queda en el log.
    for spec in specs:
        for warning in file_name_warnings(spec, _files_of(spec, files)):
            audit.note(f"Advertencia: {warning}", ok=False)

    # 2 y 3. Lectura y validación estricta, archivo por archivo
    read_results: dict[str, list[ReadResult]] = {}
    for spec in specs:
        if not spec.per_date:
            read_results[spec.key] = [read_and_report(f, spec, audit) for f in files.get(spec.key, [])]
    _stop_on_structure_problems(read_results, files, audit)
    inputs = {key: combine(results, _spec(specs, key)) for key, results in read_results.items()}

    # Las entradas por fecha se verifican después, porque sus fechas salen de otra entrada ya validada.
    for spec in specs:
        if spec.per_date:
            read_results[spec.key] = read_per_date(spec, files.get(spec.key) or {}, inputs, audit)
            inputs[spec.key] = combine(read_results[spec.key], spec)
            if INPUT_DATE not in inputs[spec.key].columns:
                # Sin fechas no hay archivos y la tabla llega vacía: la etapa igual puede usar la columna.
                inputs[spec.key][INPUT_DATE] = pd.Series(dtype=object)
    _stop_on_structure_problems(read_results, files, audit)
    inputs = {spec.key: inputs[spec.key] for spec in specs}  # En el orden en que se declararon
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
    # El nombre sale de la entrada principal (la primera); las demás son de apoyo.
    output_name, log_name = result_file_names(stage, [file_name(f) for f in _files_of(specs[0], files)])

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

    Si el archivo ya viene procesado por otra etapa, se cambia esa marca por la de esta
    etapa, en el mismo lugar del nombre, para que no crezca de etapa en etapa
    (`ETY_sept_E01_procesado` -> `ETY_sept_E02_procesado`; `ETY_E01_procesado_v2` ->
    `ETY_E02_procesado_v2`). El número de copia que sigue a la marca se quita.
    Con varios archivos no hay un único nombre original y se usa el de la etapa.
    """
    code, stage_name = stage_prefix(stage).split("_", 1)
    if len(input_names) != 1:
        return f"{stage_name}_{code}_procesado.xlsx", f"{stage_name}_{code}_log.xlsx"
    stem = Path(input_names[0]).stem
    # El número de copia solo se quita si va justo después de la marca (`_E01_procesado_1`).
    stem = re.sub(PROCESSED_MARK + COPY_NUMBER, lambda match: match.group(1), stem, flags=re.IGNORECASE)
    if not re.search(PROCESSED_MARK, stem, re.IGNORECASE):
        return f"{stem}_{code}_procesado.xlsx", f"{stem}_{code}_log.xlsx"
    # Se cambia solo la primera marca. El reemplazo es una función para que una «\» del nombre
    # no se tome como parte de la expresión regular.
    output = re.sub(PROCESSED_MARK, lambda _: f"_{code}_procesado", stem, count=1, flags=re.IGNORECASE)
    log = re.sub(PROCESSED_MARK, lambda _: f"_{code}_log", stem, count=1, flags=re.IGNORECASE)
    return f"{output}.xlsx", f"{log}.xlsx"


def file_name_warnings(spec: InputSpec, files: list[Any]) -> list[str]:
    """Advertencias por archivos cuyo nombre no contiene el texto esperado (`name_contains`).

    Sirve para detectar a tiempo que se cargó un archivo equivocado, por ejemplo el reporte
    original en lugar del procesado en la etapa anterior. El texto puede estar en cualquier
    parte del nombre y no se distinguen mayúsculas. No detiene el procesamiento.
    """
    if not spec.name_contains:
        return []
    expected = spec.name_contains.casefold()
    return [
        f"El nombre de «{file_name(f)}» no contiene «{spec.name_contains}». "
        f"¿Está seguro de que es el {spec.label[0].lower()}{spec.label[1:]}?"
        for f in files
        if expected not in Path(file_name(f)).stem.casefold()
    ]


def output_formats(specs: list) -> dict[str, str]:
    """Formato de Excel por columna según el tipo declarado en las entradas de la etapa."""
    return {
        column: CURRENCY_FORMAT_EXCEL
        for spec in specs
        for column, column_type in (spec.columns or {}).items()
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


def read_and_report(file: Any, spec, audit: AuditLog, day: date | None = None) -> ReadResult:
    """Lee y valida un archivo, y deja en el log de ejecución si se pudo abrir y si su
    estructura es la esperada (con cada problema encontrado). `day` es la fecha del
    archivo en una entrada por fecha, para que el log diga a cuál corresponde."""
    result = read_file(file, spec)
    for_day = f" ({date_label(spec, day)})" if day else ""
    audit.step(f"Abriendo «{result.file_name}»{for_day}")
    if not result.opened:
        for problem in result.problems:
            audit.note(problem, ok=False)
        return result
    if spec.columns is None:
        audit.note("Archivo .xlsx válido (su estructura todavía no se valida)")
        return result
    audit.note("Archivo .xlsx válido")
    audit.step(f"Validando la estructura de «{result.file_name}»")
    for problem in result.problems:
        audit.note(problem, ok=False)
    if not result.problems:
        order = " en el orden esperado" if spec.check_column_order else ""
        records = "1 registro" if result.rows == 1 else f"{result.rows} registros"
        required = " obligatorias" if spec.allow_extra_columns else ""
        audit.note(f"{len(spec.columns)} columnas{required}{order}, {records}")
    return result


def input_dates(stage: ModuleType, files: StageFiles) -> dict[str, list[date]]:
    """Fechas de cada entrada por fecha, para que la interfaz pida un archivo por fecha.

    Lee y valida el archivo del que salen las fechas (por ejemplo, el reporte ETY).
    Lanza StageError si su estructura no es la esperada. Una entrada cuyo archivo de
    origen todavía no se ha cargado no aparece en el resultado.
    """
    return load_date_sources(stage, files).dates


def load_date_sources(stage: ModuleType, files: StageFiles, audit: AuditLog | None = None) -> DateSources:
    """Lee y valida los archivos de los que salen las fechas de las entradas por fecha.

    Devuelve las fechas de cada entrada por fecha y los datos de cada entrada de origen,
    que la interfaz pasa a analyze_date_file. Lanza StageError si la estructura no es la
    esperada. Si se pasa `audit`, la lectura y la validación quedan en ese log (la
    interfaz lo muestra al cargar los archivos).
    """
    specs = input_specs(stage)
    if audit is None:
        audit = AuditLog(stage_rules(stage))
    dates = {}
    data = {}
    for spec in specs:
        if not spec.per_date:
            continue
        source_key, column = spec.per_date
        source = _spec(specs, source_key)
        source_files = files.get(source_key) or []
        if not source_files:
            continue
        results = [read_and_report(f, source, audit) for f in source_files]
        _stop_on_structure_problems({source_key: results}, {source_key: source_files}, audit)
        data[source_key] = combine(results, source)
        dates[spec.key] = dates_in(data[source_key], column)
    audit.finish_step()
    return DateSources(dates, data)


def analyze_date_file(
    stage: ModuleType,
    key: str,
    day: date,
    file: Any,
    source: pd.DataFrame,
    progress: ProgressCallback | None = None,
) -> DateFileAnalysis:
    """Valida y analiza el archivo de una fecha apenas se carga, sin esperar a Procesar.

    Abre el archivo, valida su estructura y, si la etapa lo declara en INPUT_ANALYSIS,
    le aplica sus reglas (por ejemplo, las de un informe de pago), que pueden comparar
    el archivo con `source`, los datos de la entrada de la que salen las fechas (por
    ejemplo, el reporte ETY). Devuelve el log de ese análisis, la información calculada
    por la etapa y si encontró diferencias. Lanza StageError si la
    estructura no es la esperada o si una regla detiene el proceso. No genera archivos:
    Procesar vuelve a aplicar todo y deja el resultado en el log.
    """
    spec = _spec(input_specs(stage), key)
    audit = AuditLog(stage_rules(stage), on_line=progress)
    # La etapa recibe este archivo junto con otros (el de origen de las fechas), así que
    # las acciones llevan el nombre del archivo, como al procesar.
    audit.multiple_files = True
    result = read_and_report(file, spec, audit, day)
    _stop_on_structure_problems({key: [result]}, {key: [file]}, audit)
    if result.data is not None:
        result.data[INPUT_DATE] = day
    data = combine([result], spec)
    audit.remember_source_rows(data)
    remove_title_rows({key: [result]}, audit)
    analyze = getattr(stage, "INPUT_ANALYSIS", {}).get(key)
    summary, ok = analyze(data, source, day, audit) if analyze else ([], True)
    audit.finish_step()
    return DateFileAnalysis(audit, summary, ok)


def dates_in(data: pd.DataFrame, column: str) -> list[date]:
    """Fechas distintas de una columna, ordenadas y sin la hora.

    Las celdas vacías se ignoran. Las que no son una fecha también: la Etapa 1 ya
    las reporta como hallazgo y no tienen un archivo que pedir.
    """
    days = set()
    for value in data[column]:
        try:
            parsed = parse_date(value)
        except ValueError:
            continue
        if parsed is not None:
            days.add(parsed.date())
    return sorted(days)


def read_per_date(
    spec: InputSpec, files: dict[date, Any], inputs: dict[str, pd.DataFrame], audit: AuditLog
) -> list[ReadResult]:
    """Verifica que haya un archivo por cada fecha de la entrada de origen y los lee.

    Las fechas salen de la columna configurada en `per_date`. Si falta el archivo de
    una fecha obligatoria, o se cargó uno de una fecha que no está en el origen, se
    detiene sin generar resultados. Regla EST-007. Cada registro leído lleva en la
    columna interna `_input_date` la fecha de su archivo, para que la etapa pueda
    compararla con los datos.
    """
    source_key, column = spec.per_date
    days = dates_in(inputs[source_key], column)
    audit.step(f"Verificando: {spec.label}, uno por fecha")
    problems = []
    if spec.required:
        problems += [f"[EST-007] Falta cargar: {date_label(spec, day)}." for day in days if day not in files]
    problems += [
        f"[EST-007] Se cargó «{file_name(file)}» como {date_label(spec, day)}, "
        f"pero esa fecha no está en la columna {column}."
        for day, file in files.items() if day not in days
    ]
    if problems:
        for problem in problems:
            audit.note(problem, ok=False)
        message = f"Los archivos de «{spec.label}» no corresponden a las fechas de la columna {column}."
        raise StageError(message, problems, audit.step_lines())
    if not days:
        audit.note(f"La columna {column} no tiene fechas: no se necesita ningún archivo")
    for day in days:
        audit.note(f"{day.strftime(DATE_FORMAT_TEXT)}: {file_name(files[day])}")
    results = [read_and_report(files[day], spec, audit, day) for day in days]
    for day, result in zip(days, results):
        if result.data is not None:
            result.data[INPUT_DATE] = day
    return results


def _spec(specs: list[InputSpec], key: str) -> InputSpec:
    return next(spec for spec in specs if spec.key == key)


def _files_of(spec: InputSpec, files: StageFiles) -> list[Any]:
    """Archivos cargados en una entrada, sea una lista o un diccionario por fecha."""
    loaded = files.get(spec.key) or []
    return list(loaded.values()) if isinstance(loaded, dict) else list(loaded)


def _stop_on_structure_problems(
    read_results: dict[str, list[ReadResult]], files: StageFiles, audit: AuditLog
) -> None:
    """Detiene el procesamiento si algún archivo leído tiene problemas de estructura."""
    problems = [p for results in read_results.values() for r in results for p in r.problems]
    if problems:
        failed = sum(1 for results in read_results.values() for r in results if r.problems)
        audit.finish_step()
        raise StageError(_structure_message(failed, _count_files(files)), problems, audit.step_lines())


def _count_files(files: StageFiles) -> int:
    return sum(len(f or []) for f in files.values())


def _inputs_message(files: StageFiles) -> str:
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


def check_inputs(specs: list, files: StageFiles) -> list[str]:
    """Verifica que estén las entradas obligatorias y que no sobren archivos. Regla EST-007.

    El archivo de cada fecha de una entrada por fecha se verifica después, al leer la
    entrada de la que salen las fechas (read_per_date).
    """
    problems = []
    known = [spec.key for spec in specs]
    for key in files:
        if key not in known:
            problems.append(f"[EST-007] La entrada '{key}' no existe en esta etapa. Entradas válidas: {', '.join(known)}.")
    for spec in specs:
        if spec.per_date:
            if not isinstance(files.get(spec.key) or {}, dict):
                problems.append(f"[EST-007] '{spec.label}' necesita un archivo por fecha, con la fecha de cada uno.")
            continue
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
