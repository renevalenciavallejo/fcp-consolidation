"""Lógica de la Etapa 3 - Validación con el AP Voucher.

La validación de estructura la hace el ejecutor antes de llamar a process(): el
reporte ETY procesado en la Etapa 2 y el archivo AP Voucher. Aquí van las reglas
propias de la etapa, en el orden de ESPECIFICACION.md. Las validaciones contra el
AP Voucher se agregan a medida que se especifiquen.
"""

import pandas as pd

from core.audit import AuditLog


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    # Mientras no haya reglas especificadas, la salida es el reporte ETY sin cambios.
    return inputs["ety_processed"]
