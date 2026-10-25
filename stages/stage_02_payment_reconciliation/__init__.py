"""Etapa 2 - Conciliación de pagos."""

from stages.stage_02_payment_reconciliation import config
from stages.stage_02_payment_reconciliation.process import analyze_payment_report, process

NAME = "Etapa 2 - Conciliación de pagos"
DESCRIPTION = (
    "Valida la estructura del reporte ETY de pagos procesado en la Etapa 1 y recibe el informe "
    "de pago de Tesorería de cada fecha de pago del reporte. De cada informe toma los pagos con "
    "UN AP656, verifica que su F Ejec sea la fecha del campo donde se cargó, deja un registro por "
    "Comprobante e informa el total de Impt Bruto."
)
INPUTS = config.INPUTS
RULES = config.RULES
APPLIED_RULES = config.APPLIED_RULES
# Análisis de cada informe de pago apenas se carga en la interfaz, antes de Procesar.
# Devuelve la información calculada que se muestra debajo del campo del informe.
INPUT_ANALYSIS = {"treasury_reports": analyze_payment_report}

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "APPLIED_RULES", "INPUT_ANALYSIS", "process"]
