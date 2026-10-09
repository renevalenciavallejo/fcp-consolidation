"""Lectura de archivos de Excel y validación estricta de su estructura.

Las celdas se leen con openpyxl tal como están guardadas en Excel (texto,
número o fecha), sin dejar que pandas adivine tipos. Así no se pierden ceros a
la izquierda ni se confunden formatos; la conversión explícita la hacen las
funciones de core/cleaning.py.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from core.audit import is_empty
from core.cleaning import clean_text
from core.settings import SOURCE_FILE, SOURCE_ROW
from core.stage import InputSpec


@dataclass
class ReadResult:
    """Resultado de leer un archivo: los datos (si la estructura es válida) y los problemas."""

    file_name: str
    data: pd.DataFrame | None
    problems: list[str]

    @property
    def rows(self) -> int:
        return 0 if self.data is None else len(self.data)


def file_name(file: Any) -> str:
    """Nombre del archivo, ya sea una ruta, un archivo cargado en Streamlit o un BytesIO."""
    if isinstance(file, (str, Path)):
        return Path(file).name
    return Path(getattr(file, "name", "archivo.xlsx")).name


def read_file(file: Any, spec: InputSpec) -> ReadResult:
    """Lee un archivo de una entrada y valida su estructura.

    Si hay algún problema de estructura, `data` es None y `problems` explica qué
    falta o sobra. El archivo original solo se lee, nunca se modifica.
    """
    name = file_name(file)
    try:
        workbook = load_workbook(_as_source(file), data_only=True)
    except Exception:
        return ReadResult(name, None, [f"[EST-001] {name}: no se pudo abrir. Verifique que sea un archivo .xlsx válido."])

    if spec.sheet not in workbook.sheetnames:
        sheets = ", ".join(workbook.sheetnames)
        return ReadResult(
            name, None, [f"[EST-002] {name}: no tiene la hoja '{spec.sheet}'. Hojas encontradas: {sheets}."]
        )

    rows = list(workbook[spec.sheet].iter_rows(min_row=1, min_col=1, values_only=True))
    workbook.close()

    header = rows[spec.header_row - 1] if len(rows) >= spec.header_row else ()
    data_rows = _trim_trailing_empty(rows[spec.header_row:])
    width = max([len(header), *(len(r) for r in data_rows)], default=0)

    problems: list[str] = []
    positions: dict[str, int] = {}
    for position in range(width):
        title = header[position] if position < len(header) else None
        title = clean_text(str(title)) if title is not None else ""
        if title == "":
            if any(position < len(r) and not _empty_cell(r[position]) for r in data_rows):
                letter = get_column_letter(position + 1)
                problems.append(f"[EST-006] {name}: la columna {letter} tiene datos pero no tiene encabezado.")
            continue
        if title in positions:
            problems.append(f"[EST-005] {name}: el encabezado '{title}' está repetido.")
            continue
        positions[title] = position

    missing = [c for c in spec.columns if c not in positions]
    if missing:
        problems.append(
            f"[EST-003] {name}: faltan las columnas {_quote(missing)} "
            f"en la fila {spec.header_row} de la hoja '{spec.sheet}'."
        )
    extra = [c for c in positions if c not in spec.columns]
    if extra and not spec.allow_extra_columns:
        problems.append(f"[EST-004] {name}: tiene columnas que no se esperaban: {_quote(extra)}.")

    if problems:
        return ReadResult(name, None, problems)

    columns = list(positions)
    records = []
    for offset, row in enumerate(data_rows):
        record = [row[positions[c]] if positions[c] < len(row) else None for c in columns]
        # Fila real en Excel: la que el usuario puede buscar en su archivo.
        records.append([*record, name, spec.header_row + 1 + offset])
    data = pd.DataFrame(records, columns=[*columns, SOURCE_FILE, SOURCE_ROW], dtype=object)
    return ReadResult(name, data, [])


def combine(results: list[ReadResult], spec: InputSpec) -> pd.DataFrame:
    """Une en un solo DataFrame los archivos de una entrada que tienen la misma estructura."""
    frames = [r.data for r in results if r.data is not None]
    if not frames:
        return pd.DataFrame(columns=[*spec.columns, SOURCE_FILE, SOURCE_ROW], dtype=object)
    return pd.concat(frames, ignore_index=True)


def _as_source(file: Any) -> Any:
    """Devuelve algo que openpyxl pueda abrir, empezando siempre desde el inicio del archivo."""
    if isinstance(file, (str, Path)):
        return Path(file)
    if hasattr(file, "seek"):
        file.seek(0)
    if hasattr(file, "getvalue"):
        return BytesIO(file.getvalue())
    return file


def _empty_cell(value: Any) -> bool:
    return is_empty(value) or (isinstance(value, str) and clean_text(value) == "")


def _trim_trailing_empty(rows: list[tuple]) -> list[tuple]:
    """Quita las filas vacías del final de la hoja.

    Excel a veces reporta filas con formato pero sin datos después del último
    registro; no son registros y no deben aparecer como eliminados.
    """
    end = len(rows)
    while end > 0 and all(_empty_cell(v) for v in rows[end - 1]):
        end -= 1
    return rows[:end]


def _quote(names: list[str]) -> str:
    return ", ".join(f"'{n}'" for n in names)
