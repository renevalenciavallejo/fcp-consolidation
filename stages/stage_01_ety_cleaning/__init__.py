"""Etapa 1 - Limpieza del reporte ETY de pagos."""

from stages.stage_01_ety_cleaning import config
from stages.stage_01_ety_cleaning.process import process

NAME = "Etapa 1 - Limpieza del reporte ETY"
DESCRIPTION = (
    "Valida la estructura del reporte ETY de pagos, convierte los "
    "valores a moneda, agrega la columna Diferencia, elimina las filas de «Distribución Caja» y "
    "los comprobantes con VR. BRUTO en 0, elimina los duplicados según reglas definidas y señala "
    "los comprobantes repetidos."
)
INPUTS = config.INPUTS
RULES = config.RULES
APPLIED_RULES = config.APPLIED_RULES

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "APPLIED_RULES", "process"]
