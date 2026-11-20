"""Etapa 4 - Integración al Detalle de pago."""

from stages.stage_04_payment_detail import config
from stages.stage_04_payment_detail.process import process

NAME = "Etapa 4 - Integración al Detalle de pago"
DESCRIPTION = (
    "Genera, a partir del reporte ETY procesado en la Etapa 3, un archivo con la estructura y el "
    "formato del Detalle de pago, con los datos del ETY, para importarlo manualmente."
)
INPUTS = config.INPUTS
RULES = config.RULES
APPLIED_RULES = config.APPLIED_RULES
# Valores que el usuario escribe al procesar, porque cambian con el tiempo (el PAC vigente).
PARAMETERS = config.PARAMETERS
# El archivo de salida toma la estructura y el formato del Detalle de pago, no los del reporte ETY.
OUTPUT_LAYOUT = config.OUTPUT_LAYOUT

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "APPLIED_RULES", "PARAMETERS", "OUTPUT_LAYOUT", "process"]
