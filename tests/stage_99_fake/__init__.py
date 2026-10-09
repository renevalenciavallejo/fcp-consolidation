"""Etapa ficticia, solo para probar el núcleo. No contiene reglas de negocio reales."""

from tests.stage_99_fake import config
from tests.stage_99_fake.process import process

NAME = "Etapa 99 - Etapa de prueba"
DESCRIPTION = "Etapa ficticia para probar el ejecutor."
INPUTS = config.INPUTS
RULES = config.RULES

__all__ = ["NAME", "DESCRIPTION", "INPUTS", "RULES", "process"]
