"""Configuración de la Etapa 1 - Limpieza del reporte ETY. Solo datos."""

# Entradas que necesita la etapa.
INPUTS = {
    "ety_report": {
        "label": "Reporte ETY de pagos",  # Texto que ve el usuario
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

# Columna calculada que se agrega a la derecha de AMOUNT_COLUMN (columna J).
# Sirve para identificar los registros cuya diferencia no es 0.
AMOUNT_COLUMN = "Importe"
DIFFERENCE_COLUMN = "Diferencia"
# Fórmula de Excel: {Nombre} es la celda de esa columna en la misma fila (=E2-F2-G2-H2-I2-J2).
DIFFERENCE_FORMULA = "={VR. BRUTO}-{VR. RTEFTE}-{VR. RETEIVA}-{VR. RETEICA}-{VR. TASAS}-{Importe}"

# Columna O del archivo de salida: los registros con el mismo valor se señalan
# para revisión y la tabla se ordena por esta columna para que queden juntos.
VOUCHER_COLUMN = "Comprobante"

# Columna E. Antes del paso 7 se eliminan los registros con Diferencia 0 de un
# Comprobante cuando esta columna vale 0 (o está vacía) en todos ellos.
GROSS_AMOUNT_COLUMN = "VR. BRUTO"

# Eliminación de duplicados (paso 7). Solo se evalúan los registros con Diferencia 0,
# agrupados por VOUCHER_COLUMN. Diferencia se calcula en memoria con estas columnas:
# la primera menos todas las demás (VR. BRUTO - VR. RTEFTE - ... - Importe).
DIFFERENCE_TERMS = ["VR. BRUTO", "VR. RTEFTE", "VR. RETEIVA", "VR. RETEICA", "VR. TASAS", "Importe"]
# Decimales con los que se decide si la Diferencia es 0 (2 = al centavo). Evita que
# residuos como 0,0000000019, que Excel muestra como 0, dejen un grupo sin evaluar.
DIFFERENCE_DECIMALS = 2
# Columnas que no se comparan en los casos 2.1 y 2.2: pueden tener valores distintos
# entre filas que sí son duplicadas (columnas D, L, N y Q del archivo de salida).
DUPLICATE_IGNORED_COLUMNS = ["FECHA DE PAGO", "Asiento", "LNP", "Nº Sec Doc"]
# Caso 2.2: si las filas del grupo solo difieren en estas columnas, se conserva la primera.
DUPLICATE_TOLERATED_COLUMNS = ["Dpto", "Cd Fnd", "Producto"]
# Caso 2.3: si difieren en alguna de estas, no se elimina ninguna fila del grupo.
DUPLICATE_BLOCKING_COLUMNS = ["Subfideicomiso", "Cuenta", "Programa"]

# Reglas propias de la etapa, en el orden en que se aplican.
# Se usa la serie 1xx para no chocar con las reglas comunes.
RULES = {
    "LIM-101": "Eliminar las filas con Descripción «Distribución Caja»",
    "TRA-101": "Agregar la columna Diferencia: VR. BRUTO - VR. RTEFTE - VR. RETEIVA - VR. RETEICA - VR. TASAS - Importe",
    "TRA-102": "Ordenar los registros por Comprobante",
    "LIM-102": "Eliminar los registros con Diferencia 0 de un Comprobante cuando VR. BRUTO es 0 (o está vacío) en todos ellos",
    "DUP-101": "Eliminar registros idénticos con el mismo Comprobante y Diferencia 0, sin comparar FECHA DE PAGO, Asiento, LNP ni Nº Sec Doc (caso 2.1)",
    "DUP-102": "Eliminar registros con el mismo Comprobante y Diferencia 0 que solo difieren en Dpto, Cd Fnd y/o Producto, sin comparar FECHA DE PAGO, Asiento, LNP ni Nº Sec Doc (caso 2.2)",
    "VAL-101": "Identificar los registros con Comprobante repetido",
}

# Todas las reglas que aplica la etapa (comunes y propias), en el orden en que se
# aplican. Es la lista que el usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 no aplica: se usa la primera hoja sin importar su nombre.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    "LIM-003",   # Filas de título
    "TIP-005",   # Moneda en las columnas E a J
    *RULES,
]
