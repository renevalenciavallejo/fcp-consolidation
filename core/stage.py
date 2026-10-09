"""Lectura del contrato de una etapa.

Las etapas declaran sus entradas como diccionarios (solo datos) en su config.py.
Aquí se convierten a una estructura fija para que el resto del núcleo no tenga
que adivinar llaves ni valores por defecto.
"""

import re
from dataclasses import dataclass
from types import ModuleType

from core.rules import COMMON_RULES

# Tipos de columna permitidos en la configuración de una entrada.
COLUMN_TYPES = ("text", "code", "number", "date")


@dataclass
class InputSpec:
    """Descripción de una entrada de la etapa (ver config.INPUTS)."""

    key: str
    label: str
    multiple: bool
    required: bool
    sheet: str
    header_row: int
    columns: dict[str, str]
    allow_extra_columns: bool = False


def input_specs(stage: ModuleType) -> list[InputSpec]:
    """Convierte el diccionario INPUTS de la etapa en una lista de InputSpec."""
    specs = []
    for key, data in stage.INPUTS.items():
        spec = InputSpec(
            key=key,
            label=data["label"],
            multiple=data.get("multiple", False),
            required=data.get("required", True),
            sheet=data["sheet"],
            header_row=data.get("header_row", 1),
            columns=data["columns"],
            allow_extra_columns=data.get("allow_extra_columns", False),
        )
        for column, column_type in spec.columns.items():
            if column_type not in COLUMN_TYPES:
                raise ValueError(
                    f"Tipo '{column_type}' no válido para la columna '{column}' "
                    f"de la entrada '{key}'. Use uno de: {', '.join(COLUMN_TYPES)}"
                )
        specs.append(spec)
    return specs


def stage_rules(stage: ModuleType) -> dict[str, str]:
    """Catálogo completo de reglas que puede usar la etapa (comunes + propias)."""
    return {**COMMON_RULES, **getattr(stage, "RULES", {})}


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
