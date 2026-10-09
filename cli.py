"""Interfaz de línea de comandos (no interactiva), para pruebas y uso avanzado.

Ejemplo:
    uv run python cli.py --stage 1 --input area_reports "ruta/archivo1.xlsx" "ruta/archivo2.xlsx"
"""

import argparse
import sys
from pathlib import Path

from core.errors import UNEXPECTED_ERROR_MESSAGE, log_exception
from core.runner import StageError, run_stage, save_result
from core.settings import APP_NAME, APP_VERSION
from core.stage import input_specs
from stages import STAGES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument("--stage", type=int, required=True, help="Número de la etapa (1, 2, ...)")
    parser.add_argument(
        "--input",
        nargs="+",
        action="append",
        default=[],
        metavar=("ENTRADA", "ARCHIVO"),
        help="Identificador de la entrada seguido de uno o varios archivos. Se puede repetir.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not 1 <= args.stage <= len(STAGES):
        print(f"La etapa {args.stage} no existe. Etapas disponibles: {len(STAGES)}.")
        for number, stage in enumerate(STAGES, start=1):
            print(f"  {number}. {stage.NAME}")
        return 2
    stage = STAGES[args.stage - 1]

    files: dict[str, list[Path]] = {}
    for key, *paths in args.input:
        if not paths:
            print(f"La entrada '{key}' no tiene archivos.")
            return 2
        files.setdefault(key, []).extend(Path(p) for p in paths)
    for paths in files.values():
        for path in paths:
            if not path.is_file():
                print(f"No se encontró el archivo: {path}")
                return 2

    print(f"{stage.NAME}")
    try:
        result = run_stage(stage, files, progress=lambda step, total, text: print(f"  [{step}/{total}] {text}"))
        output_path, log_path = save_result(result)
    except StageError as error:
        print(error.message)
        for problem in error.problems:
            print(f"  - {problem}")
        print("Entradas de la etapa:")
        for spec in input_specs(stage):
            print(f"  {spec.key}: {spec.label}")
        return 1
    except Exception as error:
        log_exception(error)
        print(UNEXPECTED_ERROR_MESSAGE)
        return 1

    summary = result.summary
    print("Resumen:")
    print(f"  Registros leídos:     {summary.rows_read}")
    print(f"  Registros en salida:  {summary.rows_output}")
    print(f"  Registros eliminados: {summary.rows_removed}")
    print(f"  Celdas modificadas:   {summary.cells_changed}")
    for severity, count in summary.findings_by_severity.items():
        print(f"  Hallazgos {severity}: {count}")
    print(f"Archivo procesado: {output_path}")
    print(f"Log:               {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
