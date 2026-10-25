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
        # Final del nombre que pone la Etapa 1. Si no lo tiene, se advierte (no se detiene).
        "name_suffix": "_E01_procesado",
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
            "Comprobante": "code",      # Columna P
            "Impt Bruto": "currency",   # Columna T
        },
    },
}

# Columna del informe de pago con la unidad de negocio de cada pago.
BUSINESS_UNIT_COLUMN = "UN"

# Unidad de negocio del FCP: el informe de Tesorería trae los pagos de todas las unidades.
BUSINESS_UNIT = "AP656"

# Columna del informe de pago con la fecha de ejecución del pago.
EXECUTION_DATE_COLUMN = "F Ejec"

# Columna del informe de pago que identifica cada pago: un comprobante repetido en un
# informe es el mismo pago (por ejemplo, partido en dos transferencias).
PAYMENT_VOUCHER_COLUMN = "Comprobante"

# Columna del informe de pago con el valor bruto del pago, que se totaliza.
PAYMENT_GROSS_COLUMN = "Impt Bruto"

# Columnas del reporte ETY con la fecha de pago y el valor bruto de cada pago. El total de
# VR. BRUTO de cada fecha se compara con el total de Impt Bruto del informe de esa fecha.
ETY_PAYMENT_DATE_COLUMN = "FECHA DE PAGO"
ETY_GROSS_COLUMN = "VR. BRUTO"

# Columna del reporte ETY con el comprobante de cada pago. Cada comprobante del ETY de una
# fecha debe estar en el informe de pago de esa fecha (columna Comprobante del informe).
ETY_VOUCHER_COLUMN = "Comprobante"

# Cuántos comprobantes faltantes se listan en la notificación debajo del campo del informe;
# los demás se cuentan y quedan todos en la tabla de acciones.
MAX_VOUCHERS_IN_NOTICE = 20

# Cuántas filas se nombran como ejemplo en un mensaje de error; las demás solo se cuentan.
MAX_ROWS_IN_MESSAGE = 10

# Reglas propias de la etapa (serie 2xx).
RULES = {
    "LIM-201": "Tomar de cada informe de pago solo los registros con UN AP656",
    "VAL-201": (
        "Validar que la F Ejec de esos registros sea la fecha del campo donde se cargó el informe "
        "(si no, se detiene sin generar resultados)"
    ),
    "DUP-201": (
        "Dejar un solo registro por Comprobante en cada informe de pago (se conserva el primero; "
        "solo en memoria, el informe no se modifica)"
    ),
    "TRA-201": "Calcular el total de Impt Bruto de cada informe de pago y de todos los informes",
    "VAL-202": (
        "Verificar que el total de Impt Bruto de cada informe de pago sea igual al total de VR. BRUTO "
        "del reporte ETY con la misma FECHA DE PAGO (si no, se avisa; no detiene el proceso)"
    ),
    "VAL-203": (
        "Identificar los comprobantes del reporte ETY que no están en el informe de pago de su "
        "FECHA DE PAGO (se señalan como Error; no detiene el proceso)"
    ),
}

# Todas las reglas que aplica la etapa, en el orden en que se aplican. Es la lista que el
# usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 aplica a los informes de pago (hoja Pagos); el reporte ETY usa su primera hoja.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-002", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    "LIM-201", "VAL-201",
    "TIP-003", "TIP-005",   # Comprobante como código e Impt Bruto como moneda
    "DUP-201", "TRA-201", "VAL-202", "VAL-203",
]
