"""Configuración general de la herramienta (valores que no dependen de una etapa)."""

import tomllib
from pathlib import Path

# Carpeta raíz de la aplicación (donde están app.py y pyproject.toml).
BASE_DIR = Path(__file__).resolve().parent.parent


def _read_version() -> str:
    """Lee la versión desde pyproject.toml para que exista una sola fuente de verdad."""
    with open(BASE_DIR / "pyproject.toml", "rb") as file:
        return tomllib.load(file)["project"]["version"]


# Nombre visible de la herramienta.
APP_NAME = "Herramienta de consolidación FCP"

# Versión de la herramienta (MAYOR.MENOR.PARCHE). Aparece en la interfaz y en el log.
APP_VERSION = _read_version()

# Carpeta donde se guarda una copia de los archivos generados.
OUTPUT_DIR = BASE_DIR / "output"

# Archivo donde se guarda el detalle técnico de los errores inesperados.
ERROR_LOG_FILE = BASE_DIR / "errores.log"

# Severidades de los hallazgos, tal como aparecen en el log.
ERROR = "Error"              # Requiere corrección manual antes de la siguiente etapa
WARNING = "Advertencia"      # Revisar
INFO = "Información"         # Solo para conocimiento

# Color de resaltado (RGB hexadecimal) de las celdas con hallazgos, por severidad.
SEVERITY_FILLS = {
    ERROR: "FFC7CE",     # Rojo claro
    WARNING: "FFEB9C",   # Amarillo claro
}

# Color de los botones de descarga en la interfaz: verde, porque entregan el resultado.
# El azul de Procesar es el color principal del tema (.streamlit/config.toml).
DOWNLOAD_BUTTON_COLOR = "#2E7D32"
DOWNLOAD_BUTTON_HOVER_COLOR = "#1B5E20"   # Más oscuro al pasar el mouse

# Formatos de Excel para el archivo de salida.
DATE_FORMAT_EXCEL = "dd/mm/yyyy"
NUMBER_FORMAT_EXCEL = "#,##0.00"
# Moneda. Excel muestra los separadores según la configuración regional del
# equipo (en Colombia: $ 1.234.567,89).
CURRENCY_FORMAT_EXCEL = '"$" #,##0.00'

# Formato de fecha en textos (log, mensajes).
DATE_FORMAT_TEXT = "%d/%m/%Y"

# Ancho máximo (en caracteres) de una columna al ajustar anchos automáticamente.
MAX_COLUMN_WIDTH = 50

# Prefijo de las columnas internas que agrega el lector y que no van al archivo de salida.
INTERNAL_PREFIX = "_"
SOURCE_FILE = "_source_file"   # Nombre del archivo del que proviene el registro
SOURCE_ROW = "_source_row"     # Fila real del registro en ese archivo de Excel
