"""Lógica de la Etapa 1 - Limpieza del reporte ETY.

La validación de estructura del reporte la hace el ejecutor antes de llamar a
process(), con la configuración de config.INPUTS. Las reglas de limpieza se
agregan aquí a medida que se especifican en ESPECIFICACION.md.
"""

import pandas as pd

from core.audit import AuditLog


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    """Devuelve el reporte sin cambios mientras no haya reglas de limpieza especificadas."""
    return inputs["ety_report"]
