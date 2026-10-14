"""Configuración de la Etapa 1 - Limpieza del reporte ETY. Solo datos."""

# Entradas que necesita la etapa.
INPUTS = {
    "ety_report": {
        "label": "Reporte ETY de pagos (Todos Pagos X Comprobante)",  # Texto que ve el usuario
        "multiple": False,      # Se procesa un reporte a la vez
        "required": True,
        "sheet": None,          # None = primera hoja; el nombre de la hoja no se valida
        "header_row": 4,        # Las filas 1 a 3 son el título, la cantidad de registros y el rango de fechas
        "check_column_order": True,   # Las columnas deben estar en el mismo orden del reporte
        # Columnas obligatorias, en el orden del reporte, y su tipo:
        # "text", "code", "number", "currency" (moneda), "date".
        "columns": {
            "Beneficiario Pago": "code",
            "Identificación": "code",
            "Tercero Principal": "text",
            "FECHA DE PAGO": "date",
            "VR. BRUTO": "currency",
            "VR. RTEFTE": "currency",
            "VR. RETEIVA": "currency",
            "VR. RETEICA": "currency",
            "VR. TASAS": "currency",
            "Importe": "currency",
            "Asiento": "code",
            "Descripción": "text",
            "LNP": "code",
            "Comprobante": "code",
            "Documento": "text",
            "Nº Sec Doc": "code",
            "Más Info": "text",
            "Dpto": "code",
            "Cd Fnd": "code",
            "Subfideicomiso": "code",
            "Cuenta": "code",
            "Proy": "code",
            "Producto": "code",
            "Programa": "code",
        },
    },
}

# Columna L del reporte y valor que identifica las filas que se eliminan.
# Se compara sin tener en cuenta mayúsculas, tildes ni espacios sobrantes.
DESCRIPTION_COLUMN = "Descripción"
CASH_DISTRIBUTION_VALUE = "Distribución Caja"

# Reglas propias de la etapa. Se usa la serie 1xx para no chocar con las reglas comunes.
RULES = {
    "LIM-101": "Eliminar las filas con Descripción «Distribución Caja»",
}
