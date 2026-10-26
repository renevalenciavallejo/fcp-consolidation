"""Configuración de la Etapa 3 - Validación con el AP Voucher. Solo datos."""

# Entradas que necesita la etapa.
INPUTS = {
    "ety_processed": {
        "label": "Reporte ETY procesado en la Etapa 2",  # Texto que ve el usuario
        "multiple": False,      # Se procesa un reporte a la vez
        "required": True,
        "sheet": None,          # None = primera hoja; las etapas anteriores conservan el nombre del reporte original
        "header_row": 1,        # La Etapa 1 ya quitó las filas de título
        "check_column_order": True,   # Las columnas deben estar en el orden en que las deja la Etapa 2
        # Texto que la Etapa 2 pone en el nombre. Si el nombre no lo contiene, se advierte (no se detiene).
        "name_contains": "E02_procesado",
        # Columnas del archivo de salida de la Etapa 2 (las mismas de la Etapa 1), en orden, y su tipo:
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
            "Diferencia": "currency",   # Columna K, agregada en la Etapa 1 (regla TRA-101)
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
    "ap_voucher": {
        "label": "Archivo AP Voucher",
        "multiple": False,
        "required": True,
        "sheet": None,          # Por especificar: por ahora se usa la primera hoja
        "header_row": 1,        # Por especificar
        # Estructura todavía sin especificar: por ahora solo se verifica que abra como .xlsx.
        "columns": None,
    },
}

# Reglas propias de la etapa (serie 3xx). Se agregan a medida que se especifiquen.
RULES = {}

# Todas las reglas que aplica la etapa, en el orden en que se aplican. Es la lista que el
# usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 no aplica: se usa la primera hoja de cada archivo sin importar su nombre.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    *RULES,
]
