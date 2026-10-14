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

# Reglas propias de la etapa (se agregan a medida que se especifican).
RULES = {}
