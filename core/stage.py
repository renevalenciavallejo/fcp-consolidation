"""Lectura del contrato de una etapa.

Las etapas declaran sus entradas como diccionarios (solo datos) en su config.py.
Aquí se convierten a una estructura fija para que el resto del núcleo no tenga
que adivinar llaves ni valores por defecto.
"""

import re
from dataclasses import dataclass
from datetime import date
from types import ModuleType

from core.rules import COMMON_RULES, STRUCTURE_RULES
from core.settings import MONTH_NAMES

# Tipos de columna permitidos en la configuración de una entrada.
COLUMN_TYPES = ("text", "code", "number", "currency", "date")


@dataclass
class InputSpec:
    """Descripción de una entrada de la etapa (ver config.INPUTS)."""

    key: str
    label: str
    multiple: bool
    required: bool
    sheet: str | None              # None = primera hoja del archivo, sin importar su nombre
    header_row: int
    # None = estructura todavía sin especificar: solo se verifica que el archivo abra como .xlsx.
    columns: dict[str, str] | None
    allow_extra_columns: bool = False
    check_column_order: bool = False
    # Entrada con un archivo por cada fecha distinta de otra entrada: (entrada, columna).
    per_date: tuple[str, str] | None = None
    # Final esperado del nombre del archivo (por ejemplo «_E01_procesado»). Si no lo tiene, solo se advierte.
    name_suffix: str | None = None


def input_specs(stage: ModuleType) -> list[InputSpec]:
    """Convierte el diccionario INPUTS de la etapa en una lista de InputSpec."""
    specs = []
    for key, data in stage.INPUTS.items():
        per_date = data.get("per_date")
        spec = InputSpec(
            key=key,
            label=data["label"],
            multiple=data.get("multiple", False),
            required=data.get("required", True),
            sheet=data.get("sheet"),
            header_row=data.get("header_row", 1),
            columns=data.get("columns"),
            allow_extra_columns=data.get("allow_extra_columns", False),
            check_column_order=data.get("check_column_order", False),
            per_date=(per_date["input"], per_date["column"]) if per_date else None,
            name_suffix=data.get("name_suffix"),
        )
        if per_date and per_date["input"] not in [s.key for s in specs]:
            raise ValueError(
                f"La entrada '{key}' depende de '{per_date['input']}', que debe declararse antes en INPUTS."
            )
        for column, column_type in (spec.columns or {}).items():
            if column_type not in COLUMN_TYPES:
                raise ValueError(
                    f"Tipo '{column_type}' no válido para la columna '{column}' "
                    f"de la entrada '{key}'. Use uno de: {', '.join(COLUMN_TYPES)}"
                )
        specs.append(spec)
    return specs


def date_label(spec: InputSpec, day: date) -> str:
    """Nombre que ve el usuario para el archivo de una fecha: «Informe de pago del 28 de junio de 2026»."""
    return f"{spec.label} del {day.day} de {MONTH_NAMES[day.month - 1]} de {day.year}"


def stage_rules(stage: ModuleType) -> dict[str, str]:
    """Catálogo completo de reglas que puede usar la etapa (comunes + propias)."""
    return {**COMMON_RULES, **getattr(stage, "RULES", {})}


def applied_rules(stage: ModuleType) -> list[tuple[str, str]]:
    """Reglas que aplica la etapa, en el orden en que se aplican: (código, descripción).

    El orden sale de APPLIED_RULES en el config.py de la etapa, que puede incluir
    reglas comunes (estructura, títulos, conversión). Si la etapa no lo declara,
    se usan sus reglas propias en el orden de RULES. Es lo que el usuario consulta
    en la interfaz y en la hoja Reglas del log.
    """
    catalog = {**STRUCTURE_RULES, **stage_rules(stage)}
    codes = getattr(stage, "APPLIED_RULES", None) or list(getattr(stage, "RULES", {}))
    unknown = [code for code in codes if code not in catalog]
    if unknown:
        raise ValueError(f"APPLIED_RULES de {stage.__name__} usa reglas no declaradas: {', '.join(unknown)}")
    return [(code, catalog[code]) for code in codes]


def stage_prefix(stage: ModuleType) -> str:
    """Prefijo de los archivos generados, por ejemplo 'E01_area_reports'.

    Se toma del nombre de la carpeta de la etapa (stage_NN_<name>) para que no
    haya que repetirlo en la configuración.
    """
    folder = stage.__name__.split(".")[-1]
    match = re.fullmatch(r"stage_(\d+)_(.+)", folder)
    if not match:
        return f"E00_{folder}"
    return f"E{int(match.group(1)):02d}_{match.group(2)}"
