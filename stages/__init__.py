"""Registro de las etapas disponibles, en el orden del proceso.

Para agregar una etapa: crear su carpeta stages/stage_NN_<name>/, importarla
aquí y añadirla a la lista STAGES (ver CLAUDE.md, sección 14).
"""

from stages import stage_01_ety_cleaning, stage_02_payment_reconciliation

STAGES = [
    stage_01_ety_cleaning,
    stage_02_payment_reconciliation,
]
