"""Registro de errores técnicos.

El usuario nunca ve un traceback: ve un mensaje claro en español, y el detalle
técnico queda en errores.log para quien mantiene la herramienta.
"""

import logging

from core.settings import ERROR_LOG_FILE

# Mensaje que ve el usuario cuando ocurre un error inesperado.
UNEXPECTED_ERROR_MESSAGE = (
    "Ocurrió un error inesperado y no se generaron resultados. "
    f"El detalle técnico quedó guardado en el archivo '{ERROR_LOG_FILE.name}' "
    "de la carpeta de la herramienta. Compártalo con la persona que mantiene la herramienta."
)

_logger = logging.getLogger("fcp")


def log_exception(error: BaseException) -> None:
    """Guarda en errores.log la fecha, hora y el detalle técnico del error."""
    if not _logger.handlers:
        handler = logging.FileHandler(ERROR_LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(handler)
        _logger.setLevel(logging.ERROR)
        _logger.propagate = False
    _logger.error("Error inesperado", exc_info=error)
