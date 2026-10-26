"""Configuración de la Etapa 3 - Cruce con el AP Voucher. Solo datos."""

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
        "sheet": None,          # None = primera hoja
        "header_row": 20,       # Las filas 1 a 19 son el título y los parámetros del reporte
        # El reporte trae muchas otras columnas (algunas con el encabezado repetido): se aceptan.
        "allow_extra_columns": True,
        # Columnas que usa la etapa y su tipo.
        "columns": {
            "Comprobante": "code",      # Columna E
            "Estado Cierre": "text",    # Columna K
            "Acción": "text",           # Columna BF
        },
    },
}

# Columnas del reporte ETY y del AP Voucher que se comparan.
ETY_VOUCHER_COLUMN = "Comprobante"
ETY_GROSS_COLUMN = "VR. BRUTO"
AP_VOUCHER_COLUMN = "Comprobante"

# Cada búsqueda en el AP Voucher: regla, columna del AP Voucher, valor que se filtra,
# texto para los mensajes y nombre del color con que se resalta (el de RULE_FILLS), que
# aparece en la notificación de resultados. Se aplican en este orden.
AP_VOUCHER_CHECKS = [
    {"rule": "VAL-301", "column": "Estado Cierre", "value": "Cerrado", "state": "cerrado", "color": "naranja claro"},
    {"rule": "VAL-302", "column": "Acción", "value": "Cancelado", "state": "cancelado", "color": "gris claro"},
]

# Color de resaltado (RGB) de la celda Comprobante en el archivo de salida, por regla. Son
# distintos al amarillo de las advertencias generales para que el usuario distinga cada caso.
RULE_FILLS = {
    "VAL-301": "F8CBAD",   # Naranja claro: comprobante cerrado en el AP Voucher
    "VAL-302": "D9D9D9",   # Gris claro: comprobante cancelado en el AP Voucher
}

# Máximo de comprobantes que se listan en el log de ejecución (todos quedan en Acciones).
MAX_VOUCHERS_IN_NOTE = 20

# Máximo de filas del AP Voucher que se citan en el detalle de cada hallazgo.
MAX_ROWS_IN_DETAIL = 5

# Reglas propias de la etapa (serie 3xx).
RULES = {
    "VAL-301": (
        "Identificar los comprobantes del reporte ETY que están en el AP Voucher con Estado Cierre "
        "«Cerrado» (se señalan como Advertencia, en naranja claro; no detiene el proceso)"
    ),
    "VAL-302": (
        "Identificar los comprobantes del reporte ETY que están en el AP Voucher con Acción "
        "«Cancelado» (se señalan como Advertencia, en gris claro; no detiene el proceso)"
    ),
}

# Todas las reglas que aplica la etapa, en el orden en que se aplican. Es la lista que el
# usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 no aplica: se usa la primera hoja de cada archivo sin importar su nombre.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    "LIM-003",   # Filas de título del AP Voucher
    *RULES,
]
