"""Último valor usado de los parámetros de cada etapa (por ejemplo, el PAC vigente).

Los parámetros son valores que el usuario escribe al procesar porque cambian con el
tiempo; así no hay que modificar el código cuando cambian. Las interfaces proponen el
último valor usado, que se guarda en parametros.json (en la carpeta de la herramienta)
después de cada procesamiento exitoso. El ejecutor no lee ni escribe este archivo:
recibe los valores ya escritos.
"""

import json
from pathlib import Path
from types import ModuleType

from core.settings import PARAMETERS_FILE
from core.stage import parameter_specs, stage_prefix


def saved_parameters(stage: ModuleType, path: Path = PARAMETERS_FILE) -> dict[str, str]:
    """Valor que se propone para cada parámetro de la etapa: el último usado o, si nunca se
    ha usado (o el archivo no existe o está dañado), el valor por defecto de config.py."""
    values = {spec.key: spec.default for spec in parameter_specs(stage)}
    saved = _read(path).get(stage_prefix(stage), {})
    for key in values:
        if isinstance(saved.get(key), str) and saved[key].strip():
            values[key] = saved[key]
    return values


def save_parameters(stage: ModuleType, values: dict[str, str], path: Path = PARAMETERS_FILE) -> None:
    """Guarda los valores usados en el procesamiento, para proponerlos la próxima vez.

    Conserva los de las demás etapas. Si no se puede escribir el archivo, se lanza el error:
    las interfaces lo registran en errores.log sin detener la entrega de resultados.
    """
    if not values:
        return
    data = _read(path)
    # Sin espacios sobrantes, igual que los usa el ejecutor.
    data[stage_prefix(stage)] = {key: " ".join(str(value).split()) for key, value in values.items()}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    """Contenido del archivo; vacío si no existe o no es un JSON válido (por ejemplo, si se
    editó a mano y quedó mal escrito), para que la herramienta siga funcionando."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
