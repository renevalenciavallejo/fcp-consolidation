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

# Columnas U y V del archivo de salida (T y U del reporte): cada Cuenta debe pertenecer a su Subfideicomiso (VAL-102).
SUBTRUST_COLUMN = "Subfideicomiso"
ACCOUNT_COLUMN = "Cuenta"
# Cuentas bancarias de cada Subfideicomiso: {código: [4 últimos dígitos de cada cuenta]}.
# El ETY solo trae los 4 últimos dígitos. Sale del Excel «RELACIÓN SUBCUENTAS Y CUENTAS
# BANCARIAS» (columnas D y G); si se abre una cuenta nueva, se agrega aquí.
# La cuenta 000-3063120 (CONVENIO ART - ICBF - FCP) no se incluye porque en ese Excel no tiene código.
SUBTRUST_ACCOUNTS = {
    "1001": ["4139", "6297"],  # REINCORPORACION
    "1002": ["4147"],  # PDET
    "2016": ["4279"],  # PDET - CONVENIO
    "2030": ["9203", "5815"],  # PDET - CONVENIO
    "2032": ["4880", "5823"],  # PDET - MEJORAMIENTOS
    "2033": ["4898"],  # PDET - UNIVERSIDAD
    "2046": ["0378", "5849"],  # PDET- CANCILLERIA
    "1003": ["4154", "6270", "0216", "0343", "0377"],  # SUSTITUCION
    "2045": ["0375", "5856"],  # SUSTITUCION RENHACEMOS
    "1004": ["4162"],  # PRIMERA INFANCIA ICBF
    "1005": ["4170"],  # TEJIENDO PAZ - FUNCIONAMIENTO
    "1007": ["4196"],  # IMPLEMENTACIÓN
    "2019": ["4212"],  # AGENCIA NACIONAL DE TIERRAS 20192
    "2034": ["0999", "0181", "5831"],  # CONVENIO ANT 1217 DE 2023
    "2043": ["0351", "5864"],  # CONVENIO ANT 2428 DE 2024
    "2010": ["4220"],  # HERENCIA COLOMBIA
    "2013": ["4253"],  # BID PRESTAMO
    "2017": ["4287"],  # AMBIENTE Y DESARROLLO SOSTENIBLE
    "2020": ["4532", "6344"],  # KFW-CONVENIO
    "2036": ["0239", "5872"],  # CONVENIO ART
    "2024": ["7546"],  # NIÑEZ Y ADOLESCENCIA ICBF
    "2035": ["0191", "5880"],  # CONVENIO IGAC
    "2031": ["8692"],  # CATASTRO MULTIPROPÓSITO
    "2028": ["9344", "5914"],  # CATASTRO MULTIPROPÓSITO-CONVENIO
    "2014": ["4261"],  # RECAUDO
    "2038": ["7687"],  # ADR
    "2039": ["0346", "5922"],  # MADR 2403
    "2051": ["0604", "5930"],  # MADR 2514
    "2053": ["0623", "5948"],  # MADR - AUNAP
    "2044": ["0350", "5955"],  # UARIV
    "2042": ["0372"],  # SERVICIO SOCIAL PARA LA PAZ
    "2048": ["0544", "5963"],  # SERVICIO SOCIAL PARA LA PAZ - CONVENIO MEN DAFP
    "2049": ["0545", "5971"],  # SERVICIO SOCIAL PARA LA PAZ - CONVENIO DAFP
    "2054": ["0659", "5989"],  # SERVICIO SOCIAL PARA LA PAZ - CONVENIO MEN
    "2047": ["0546", "6011"],  # MINISTERIO DE TRABAJO
    "2041": ["0597"],  # ACCIONES COMUNITARIAS Y RESTAURATIVAS
    "2052": ["0603", "6029"],  # FCAS- AECID-ART FASE I
    "2055": ["0700"],  # Contrapartida-FCAS- AECID-ART FASE I-
}

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
    "VAL-102": "Marcar la Cuenta de los registros en los que Subfideicomiso y Cuenta no están relacionados o falta alguno de los dos",
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
