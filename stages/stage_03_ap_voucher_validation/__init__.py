"""Etapa 3 - Validación con el AP Voucher."""

from stages.stage_03_ap_voucher_validation import config
from stages.stage_03_ap_voucher_validation.process import process

NAME = "Etapa 3 - Validación con el AP Voucher"
DESCRIPTION = (
    "Valida la estructura del reporte ETY de pagos procesado en la Etapa 2 y recibe el archivo "
    "AP Voucher. Las validaciones del reporte ETY contra el AP Voucher se agregarán a medida que "
    "se especifiquen."
)
INPUTS = config.INPUTS
RULES = config.RULES
APPLIED_RULES = config.APPLIED_RULES

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "APPLIED_RULES", "process"]
