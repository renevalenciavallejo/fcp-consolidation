"""Lógica de la Etapa 4 - Integración al Detalle de pago.

La validación de estructura del reporte ETY la hace el ejecutor antes de llamar a
process(). Aquí van las reglas propias de la etapa, en el orden de ESPECIFICACION.md.
"""

import pandas as pd

from core.audit import AuditLog
from stages.stage_04_payment_detail.config import OUTPUT_LAYOUT


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    ety = inputs["ety_processed"]
    audit.step("Generando el archivo con la estructura del Detalle de pago")
    return empty_payment_detail(ety, audit)


def empty_payment_detail(ety: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Tabla del Detalle de pago con sus columnas en orden y sin registros. Regla TRA-401.

    El formato (encabezados, anchos, formatos de celda) lo aplica el ejecutor con
    OUTPUT_LAYOUT. La integración de los registros del reporte ETY se agregará
    cuando se especifique.
    """
    columns = list(OUTPUT_LAYOUT["columns"])
    audit.transformation(
        "TRA-401",
        f"Archivo con las {len(columns)} columnas y el formato del Detalle de pago, sin datos por ahora "
        f"(los {len(ety)} registros del reporte ETY todavía no se integran)",
    )
    return pd.DataFrame(columns=columns, dtype=object)
