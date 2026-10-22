"""Configuración de la Etapa 2 - Conciliación de pagos. Solo datos."""

# Entradas que necesita la etapa.
INPUTS = {
    "ety_processed": {
        "label": "Reporte ETY procesado en la Etapa 1",  # Texto que ve el usuario
        "multiple": False,      # Se procesa un reporte a la vez
        "required": True,
        "sheet": None,          # None = primera hoja; la Etapa 1 conserva el nombre del reporte original
        "header_row": 1,        # La Etapa 1 ya quitó las filas de título
        "check_column_order": True,   # Las columnas deben estar en el orden en que las deja la Etapa 1
        # Columnas del archivo de salida de la Etapa 1, en orden, y su tipo:
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
    "treasury_reports": {
        "label": "Informe de pago",   # La interfaz agrega la fecha: «... del 28 de septiembre de 2026»
        # Un archivo por cada fecha distinta de FECHA DE PAGO del reporte ETY (las vacías se ignoran).
        # Todas las fechas son obligatorias.
        "per_date": {"input": "ety_processed", "column": "FECHA DE PAGO"},
        "required": True,
        "sheet": "Pagos",       # Segunda pestaña del informe; las demás (RESUMEN, H3) no se usan
        "header_row": 1,
        # Solo se exigen las columnas que usa la etapa. El informe trae muchas más (y alguna
        # repetida, como «Nº Cuenta»), que se aceptan sin validarlas.
        "allow_extra_columns": True,
        "columns": {
            "F Ejec": "date",
            "UN": "code",
        },
    },
}

# Columna del informe de pago con la unidad de negocio de cada pago.
BUSINESS_UNIT_COLUMN = "UN"

# Unidad de negocio del FCP: el informe de Tesorería trae los pagos de todas las unidades.
BUSINESS_UNIT = "AP656"

# Columna del informe de pago con la fecha de ejecución del pago.
EXECUTION_DATE_COLUMN = "F Ejec"

# Cuántas filas se nombran como ejemplo en un mensaje de error; las demás solo se cuentan.
MAX_ROWS_IN_MESSAGE = 10

# Reglas propias de la etapa (serie 2xx).
RULES = {
    "LIM-201": "Tomar de cada informe de pago solo los registros con UN AP656",
    "VAL-201": (
        "Validar que la F Ejec de esos registros sea la fecha del campo donde se cargó el informe "
        "(si no, se detiene sin generar resultados)"
    ),
}

# Todas las reglas que aplica la etapa, en el orden en que se aplican. Es la lista que el
# usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 aplica a los informes de pago (hoja Pagos); el reporte ETY usa su primera hoja.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-002", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    *RULES,
]
