"""Etapa 3 - Cruce con el AP Voucher."""

from stages.stage_03_ap_voucher_validation import config
from stages.stage_03_ap_voucher_validation.process import process, result_notice

NAME = "Etapa 3 - Cruce con el AP Voucher"
DESCRIPTION = (
    "Señala los comprobantes del reporte ETY procesado en la Etapa 2 que están cerrados o "
    "cancelados en el AP Voucher, para que se verifiquen manualmente."
)
INPUTS = config.INPUTS
RULES = config.RULES
APPLIED_RULES = config.APPLIED_RULES
RULE_FILLS = config.RULE_FILLS
# Notificación con los comprobantes cerrados y cancelados encontrados y su color.
RESULT_NOTICE = result_notice

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "APPLIED_RULES", "RULE_FILLS", "RESULT_NOTICE", "process"]
