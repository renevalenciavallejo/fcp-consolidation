"""Etapa 1 - Limpieza del reporte ETY de pagos."""

from stages.stage_01_ety_cleaning import config
from stages.stage_01_ety_cleaning.process import process

NAME = "Etapa 1 - Limpieza del reporte ETY"
DESCRIPTION = (
    "Valida que el reporte ETY de pagos (Todos Pagos X Comprobante) tenga la estructura esperada. "
    "Las reglas de limpieza se agregarán a medida que se especifiquen."
)
INPUTS = config.INPUTS
RULES = config.RULES

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "process"]
