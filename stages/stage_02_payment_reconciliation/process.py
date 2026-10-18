"""Lógica de la Etapa 2 - Conciliación de pagos.

La validación de estructura la hace el ejecutor antes de llamar a process().
Por ahora la etapa solo recibe el archivo procesado en la Etapa 1; las reglas de
conciliación se agregan aquí, en el orden de ESPECIFICACION.md, a medida que se
especifiquen.
"""

import pandas as pd

from core.audit import AuditLog


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    return inputs["ety_processed"]
