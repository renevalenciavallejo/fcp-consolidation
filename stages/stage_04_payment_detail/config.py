"""Configuración de la Etapa 4 - Integración al Detalle de pago. Solo datos."""

# Entradas que necesita la etapa.
INPUTS = {
    "ety_processed": {
        "label": "Reporte ETY procesado en la Etapa 3",  # Texto que ve el usuario
        "multiple": False,      # Se procesa un reporte a la vez
        "required": True,
        "sheet": None,          # None = primera hoja; las etapas anteriores conservan el nombre del reporte original
        "header_row": 1,        # La Etapa 1 ya quitó las filas de título
        "check_column_order": True,   # Las columnas deben estar en el orden en que las deja la Etapa 3
        # Texto que la Etapa 3 pone en el nombre. Si el nombre no lo contiene, se advierte (no se detiene).
        "name_contains": "E03_procesado",
        # Columnas del archivo de salida de la Etapa 3 (las mismas de las Etapas 1 y 2), en orden,
        # y su tipo: "text", "code", "number", "currency" (moneda), "date".
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
}

# Formatos de número del archivo Detalle de pago (tal como están en Excel).
ACCOUNTING_FORMAT = '_("$"* #,##0.00_);_("$"* \\(#,##0.00\\);_("$"* "-"??_);_(@_)'   # Contabilidad con $
DATE_FORMAT = "d/mm/yyyy;@"
INTEGER_FORMAT = "#,##0"
TEXT_FORMAT = "@"

# Azul y verde de los encabezados del Detalle de pago.
HEADER_BLUE = "2F75B5"
HEADER_GREEN = "00B050"

# Estructura y formato del archivo de salida: los del archivo Detalle de pago (tomados
# de DetallePagoEjemploFormato.xlsx). El usuario importa este archivo manualmente al
# Detalle de pago, así que deben coincidir.
OUTPUT_LAYOUT = {
    "sheet_name": "Hoja1",
    "header_height": 58,    # Alto de la fila de encabezados
    # Encabezados: negrita, letra blanca sobre azul, centrados y con ajuste de texto.
    "header": {"font": "Calibri", "size": 11, "bold": True, "color": "FFFFFF", "fill": HEADER_BLUE},
    "data": {"font": "Calibri", "size": 11},
    # Columnas en orden, con su ancho, formato de número (si no es «General»), alineación
    # horizontal de los datos (si no es la normal) y relleno del encabezado (si no es el azul).
    "columns": {
        "ITEM": {"width": 14.18, "format": INTEGER_FORMAT, "align": "center"},
        "IDENTIFICACION": {"width": 14.82, "align": "center"},
        "TERCERO": {"width": 43.73},
        "FECHA_DE_PAGO": {"width": 11, "format": DATE_FORMAT, "align": "center"},
        "VR_BRUTO": {"width": 18.36, "format": ACCOUNTING_FORMAT},
        "VR_RTEFTE": {"width": 14.54, "format": ACCOUNTING_FORMAT},
        "VR_RETEIVA": {"width": 13.36, "format": ACCOUNTING_FORMAT},
        "VR_RETEICA": {"width": 13.36, "format": ACCOUNTING_FORMAT},
        "VR_TASAS": {"width": 15, "format": ACCOUNTING_FORMAT},
        "VR_NETO": {"width": 18.36, "format": ACCOUNTING_FORMAT},
        "VALIDACION": {"width": 15.63, "format": ACCOUNTING_FORMAT, "align": "center"},
        "ASIENTO": {"width": 11.73, "align": "center"},
        "COMPROBANTE": {"width": 13.36, "align": "center"},
        "NO_SEC_DOC": {"width": 13.63, "align": "center"},
        "CONTRATO": {"width": 10.63, "align": "center"},
        "VIGENCIA": {"width": 9.18, "align": "center", "header_fill": HEADER_GREEN},
        "SUBFIDEICOMISO": {"width": 10.82, "align": "center"},
        "NOMBRE_SUBFIDEICOMISO_PAGO": {"width": 56.63, "align": "center"},
        "CUENTA": {"width": 7.91, "align": "center"},
        "TIPO_DE_PAGO": {"width": 11.18, "align": "center"},
        "NO_BENEFICIARIOS": {"width": 10.63, "align": "center"},
        "CONCEPTO": {"width": 88.27},
        "FIDUCIARIA_QUE_EFECTUO_EL_PAGO": {"width": 14.63, "align": "center"},
        "INFORME_SEMANAL": {"width": 10.63, "align": "center"},
        "PERIODO_DE_COBRO": {"width": 22.36, "align": "center"},
        "RECURSOS": {"width": 14.63, "align": "center"},
        "PROGRAMA": {"width": 10.82, "align": "center", "header_fill": HEADER_GREEN},
        "GL": {"width": 4.18, "align": "center"},
        "Q_PAGOS": {"width": 9.27, "format": TEXT_FORMAT, "align": "center"},
        "CONTRATO_2": {"width": 11.45, "align": "center"},
        "AMORTIZACION_ANTICIPO": {"width": 12.91, "format": ACCOUNTING_FORMAT, "align": "center"},
        "MULTA": {"width": 7.54, "format": ACCOUNTING_FORMAT, "align": "center"},
        "FUENTE_DE_RECURSOS": {"width": 13, "align": "center"},
        "RANGO": {"width": 7.91, "align": "center"},
    },
}

# Columnas del reporte ETY que se copian, fila por fila y sin cambios, a la columna del
# Detalle de pago indicada. Las demás columnas del Detalle de pago quedan vacías.
COLUMN_MAPPING = {
    "Identificación": "IDENTIFICACION",
    "Tercero Principal": "TERCERO",
    "FECHA DE PAGO": "FECHA_DE_PAGO",
    "VR. BRUTO": "VR_BRUTO",
    "VR. RTEFTE": "VR_RTEFTE",
    "VR. RETEIVA": "VR_RETEIVA",
    "VR. RETEICA": "VR_RETEICA",
    "VR. TASAS": "VR_TASAS",
    "Importe": "VR_NETO",
    "Asiento": "ASIENTO",
    "Comprobante": "COMPROBANTE",
    "Nº Sec Doc": "NO_SEC_DOC",
    "Más Info": "CONCEPTO",
    "Subfideicomiso": "SUBFIDEICOMISO",
    "Cuenta": "CUENTA",
    "Programa": "PROGRAMA",
}

# Texto que se antepone al copiar el valor de una columna (columna del Detalle de pago: prefijo).
# El Detalle de pago identifica el comprobante con el código del negocio: 00153414 -> 656-00153414.
VALUE_PREFIXES = {"COMPROBANTE": "656-"}

# Columnas del Detalle de pago que se calculan con una fórmula de Excel en cada fila, después
# de copiar los datos, en este orden: regla, columna, fórmula (las columnas se nombran entre
# llaves y se convierten en la celda de la misma fila) y formato de número (None = General).
# - VALIDACION es la Diferencia del ETY. En el ETY, Diferencia es una fórmula de Excel (regla
#   TRA-101 de la Etapa 1) cuyo resultado no queda guardado en el archivo hasta que se abre y
#   guarda en Excel, así que no se puede copiar su valor: se escribe la misma fórmula (como en
#   el Detalle de pago: =+E2-F2-G2-H2-I2-J2).
# - CONTRATO es la fórmula del Detalle de pago (DetallePagoEjemploFormato.xlsx), que toma de
#   CONCEPTO el número que sigue a «CONTRATO» («..._CONTRATO_303-2026_...» -> 303). Si CONCEPTO
#   no contiene «CONTRATO», Excel muestra #¡VALOR!, igual que en el Detalle de pago.
CONTRACT_TEXT = (
    'MID(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({CONCEPTO}," ","_"),"/","_"),"-","_"),'
    'SEARCH("CONTRATO",{CONCEPTO},1),LEN({CONCEPTO}))'
)
FORMULA_COLUMNS = [
    {
        "rule": "TRA-403",
        "column": "VALIDACION",
        "formula": "={VR_BRUTO}-{VR_RTEFTE}-{VR_RETEIVA}-{VR_RETEICA}-{VR_TASAS}-{VR_NETO}",
        "format": ACCOUNTING_FORMAT,
    },
    {
        "rule": "TRA-404",
        "column": "CONTRATO",
        "formula": (
            f'=MID(SUBSTITUTE({CONTRACT_TEXT},"CONTRATO_",""),1,'
            f'SEARCH("_",SUBSTITUTE({CONTRACT_TEXT},"CONTRATO_",""),1)-1)'
        ),
        "format": None,
    },
]

# VIGENCIA (regla TRA-409). Solo se llena si el CONTRATO (el resultado de su fórmula) es un
# número; entonces se busca en CONCEPTO la expresión CONTRATO_<número>-<vigencia> (por ejemplo
# CONTRATO_1345-2025) y se toma la vigencia. Como CONTRATO es una fórmula de Excel que la
# herramienta no calcula, su resultado se obtiene con la misma lógica de la fórmula, usando
# estos textos. Si cambia la fórmula de CONTRATO, hay que revisar contract_number() en process.py.
VALIDITY_COLUMN = "VIGENCIA"
CONCEPT_COLUMN = "CONCEPTO"
CONTRACT_WORD = "CONTRATO"           # Palabra que busca la fórmula (sin distinguir mayúsculas)
CONTRACT_PREFIX = "CONTRATO_"        # Texto que quita la fórmula (distingue mayúsculas)
CONTRACT_SEPARATORS = [" ", "/", "-"]  # Caracteres que la fórmula cambia por «_»

# Columnas con fórmula que usan VIGENCIA: se escriben después de asignarla (mismos datos que
# FORMULA_COLUMNS). CONTRATO_2 es la fórmula del Detalle de pago (DetallePagoEjemploFormato.xlsx):
# une CONTRATO y VIGENCIA con un guion (=+CONCATENATE(O2,"-",P2) -> 303-2026).
FORMULA_COLUMNS_AFTER_VALIDITY = [
    {
        "rule": "TRA-410",
        "column": "CONTRATO_2",
        "formula": '=+CONCATENATE({CONTRATO},"-",{VIGENCIA})',
        "format": None,
    },
]

# Columnas del Detalle de pago donde los números que en el ETY vienen como texto (códigos)
# se escriben como número, para que Excel no los marque como «Número almacenado como texto».
# Solo los valores formados únicamente por dígitos y sin ceros a la izquierda; los demás se
# copian como texto, para no cambiar lo que se ve.
NUMBER_COLUMNS = ["IDENTIFICACION", "SUBFIDEICOMISO", "CUENTA"]

# Valor fijo que se asigna a todos los registros en estas columnas del Detalle de pago (el
# mismo de todos los registros anteriores del Detalle de pago). Se escriben con el tipo que
# tienen allí: GL, AMORTIZACION_ANTICIPO y MULTA como número; Q_PAGOS como texto (su columna
# tiene formato de texto).
FIXED_VALUES = {
    "FIDUCIARIA_QUE_EFECTUO_EL_PAGO": "FIDUPREVISORA",
    "GL": 656,
    "Q_PAGOS": "1",
    "AMORTIZACION_ANTICIPO": 0,
    "MULTA": 0,
}

# Columna del Detalle de pago con el Subfideicomiso de cada registro, del que salen las
# columnas de SUBTRUST_RELATIONS.
SUBTRUST_COLUMN = "SUBFIDEICOMISO"

# Relación Subfideicomiso -> nombre del Subfideicomiso (NOMBRE_SUBFIDEICOMISO_PAGO). Los
# nombres van sin espacios al final: en el Detalle de pago el mismo nombre aparece con y sin
# espacio final, y Excel los tomaría como valores distintos en filtros y tablas dinámicas.
SUBTRUST_NAMES = {
    "1001": "REINCORPORACION",
    "1002": "PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET",
    "1003": "SUSTITUCION",
    "1004": "PRIMERA INFANCIA ICBF",
    "1005": "TEJIENDO PAZ - FUNCIONAMIENTO",
    "1006": "JUSTICIA ESPECIAL PARA LA PAZ",
    "1007": "IMPLEMENTACION",
    "1008": "AGENCIA NACIONAL DE TIERRAS",
    "1009": "SOCIEDAD DE ACTIVOS ESPECIALES - SAE",
    "2010": "HERENCIA COLOMBIA",
    "2011": "COLOMBIA SOSTENIBLE",
    "2013": "BID PRESTAMO",
    "2016": "PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET",
    "2017": "AMBIENTE Y DESARROLLO SOSTENIBLE",
    "2018": "BID FACILIDAD",
    "2019": "AGENCIA NACIONAL DE TIERRAS (2)",
    "2020": "KFW",
    "2021": "AFD",
    "2022": "BID FACILIDAD",
    "2023": "VISION AMAZONIA",
    "2024": "NIÑEZ Y ADOLESCENCIA ICBF",
    "2025": "BID FACILIDAD",
    "2026": "BID FACILIDAD",
    "2027": "ZONA ZEII CATATUMBO",
    "2028": "CATASTRO MULTIPROPOSITO",
    "2029": "ZONA ZEII CATATUMBO - CATASTRO",
    "2030": "PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET",
    "2031": "CATASTRO MULTIPROPOSITO",
    "2032": "PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET",
    "2033": "PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET",
    "2034": "AGENCIA NACIONAL DE TIERRAS (2)",
    "2035": "CATASTRO MULTIPROPOSITO",
    "2036": "KFW",
    "2038": "AGENCIA DE DESARROLLO RURAL - ADR",
    "2039": "MINISTERIO DE AGRICULTURA Y DESARROLLO RURAL",
    "2041": "ACCIONES COMUNITARIAS Y RESTAURATIVAS -ARN",
    "2042": "SERVICIO SOCIAL PARA LA PAZ",
    "2043": "AGENCIA NACIONAL DE TIERRAS (2)",
    "2044": "ATENCION INTEGRAL DE LAS VICTIMAS",
    "2045": "SUSTITUCION",
    "2047": "MINISTERIO DE TRABAJO",
    "2048": "SERVICIO SOCIAL PARA LA PAZ",
    "2049": "SERVICIO SOCIAL PARA LA PAZ",
    "2054": "SERVICIO SOCIAL PARA LA PAZ",
}

# Relación Subfideicomiso -> recursos (RECURSOS). «PAC JULIO 2026» es el PAC vigente: cuando
# cambie, se actualiza aquí en todos los Subfideicomisos que lo usan.
SUBTRUST_RESOURCES = {
    "1001": "PAC JULIO 2026",
    "1002": "PAC JULIO 2026",
    "1003": "PAC JULIO 2026",
    "1004": "PAC JULIO 2026",
    "1005": "PAC JULIO 2026",
    "1006": "PAC JULIO 2026",
    "1007": "PAC JULIO 2026",
    "1008": "PAC JULIO 2026",
    "1009": "PAC JULIO 2026",
    "2010": "PAC JULIO 2026",
    "2011": "PAC JULIO 2026",
    "2013": "PAC BID PRESTAMO SEP2019",
    "2016": "CENIT",
    "2017": "PAC JULIO 2026",
    "2018": "BID FACILIDAD",
    "2019": "PAC JULIO 2026",
    "2020": "KFW",
    "2021": "AFD",
    "2022": "BID FACILIDAD",
    "2023": "VISIÓN AMAZONIA",
    "2024": "PAC JULIO 2026",
    "2025": "BID FACILIDAD",
    "2026": "BID FACILIDAD",
    "2027": "FONDO PAZ",
    "2028": "FONDO PAZ",
    "2029": "FONDO PAZ",
    "2030": "FONDO PAZ",
    "2031": "PAC JULIO 2026",
    "2032": "FONDO PAZ",
    "2033": "FONDO PAZ",
    "2034": "OTROS RECURSOS ANT",
    "2035": "CONVENIO IGAC 1231-23",
    "2036": "CONVENIO ART-KFW",
    "2038": "CONVENIO ADR 1141-24",
    "2039": "CONVENIO MADR 2403-25",
    "2041": "PAC JULIO 2026",
    "2042": "PAC JULIO 2026",
    "2043": "CONVENIO ANT 2428-24",
    "2044": "CONVENIO UARIV 2420-24",
    "2045": "CONVENIO RENHACEMOS",
    "2047": "MIN TRABAJO 1638 -25",
    "2048": "CONVENIO 1566-25 MEN",
    "2049": "CONVENIO 1675 -25 DAFP",
    "2054": "CONVENIO 764-26 MEN",
}

# Relación Subfideicomiso -> fuente de recursos (FUENTE_DE_RECURSOS).
FUNDING_SOURCES = {
    "1001": "PGN",
    "1002": "PGN",
    "1003": "PGN",
    "1004": "PGN",
    "1005": "PGN",
    "1006": "PGN",
    "1007": "PGN",
    "1008": "PGN",
    "1009": "PGN",
    "2010": "PGN",
    "2011": "PGN",
    "2013": "PGN",
    "2016": "OTROS",
    "2017": "PGN",
    "2018": "OTROS",
    "2019": "PGN",
    "2020": "OTROS",
    "2021": "OTROS",
    "2022": "OTROS",
    "2023": "OTROS",
    "2024": "PGN",
    "2025": "OTROS",
    "2026": "OTROS",
    "2027": "OTROS",
    "2028": "OTROS",
    "2029": "OTROS",
    "2030": "OTROS",
    "2031": "PGN",
    "2032": "OTROS",
    "2033": "OTROS",
    "2034": "OTROS",
    "2035": "OTROS",
    "2036": "OTROS",
    "2038": "OTROS",
    "2039": "OTROS",
    "2041": "PGN",
    "2042": "PGN",
    "2043": "OTROS",
    "2044": "OTROS",
    "2045": "OTROS",
    "2047": "OTROS",
    "2048": "OTROS",
    "2049": "OTROS",
    "2054": "OTROS",
}

# Columnas del Detalle de pago que se llenan según el Subfideicomiso de cada registro, en este
# orden: regla, columna y relación. Un Subfideicomiso que no está en la relación (o vacío) deja
# la celda vacía y se informa en el log, para completarla manualmente.
SUBTRUST_RELATIONS = [
    {"rule": "TRA-407", "column": "NOMBRE_SUBFIDEICOMISO_PAGO", "values": SUBTRUST_NAMES},
    {"rule": "TRA-408", "column": "RECURSOS", "values": SUBTRUST_RESOURCES},
    {"rule": "TRA-406", "column": "FUENTE_DE_RECURSOS", "values": FUNDING_SOURCES},
]

# Máximo de Subfideicomisos sin relación que se listan en el log de ejecución.
MAX_SUBTRUSTS_IN_NOTE = 20

# Reglas propias de la etapa (serie 4xx).
RULES = {
    "TRA-401": (
        "Generar el archivo con la estructura y el formato del Detalle de pago (columnas, encabezados, "
        "estilos, anchos y formatos de celda)"
    ),
    "TRA-402": (
        "Copiar los valores del reporte ETY, fila por fila y sin cambios, a las columnas del Detalle de pago: "
        "Identificación → IDENTIFICACION, Tercero Principal → TERCERO, FECHA DE PAGO → FECHA_DE_PAGO, "
        "VR. BRUTO → VR_BRUTO, VR. RTEFTE → VR_RTEFTE, VR. RETEIVA → VR_RETEIVA, VR. RETEICA → VR_RETEICA, "
        "VR. TASAS → VR_TASAS, Importe → VR_NETO, Asiento → ASIENTO, Comprobante → COMPROBANTE (con el "
        "prefijo «656-»), Nº Sec Doc → NO_SEC_DOC, Más Info → CONCEPTO, Subfideicomiso → SUBFIDEICOMISO, Cuenta → CUENTA "
        "y Programa → PROGRAMA. IDENTIFICACION, SUBFIDEICOMISO y CUENTA se escriben como número (si tienen "
        "solo dígitos y no empiezan por cero)"
    ),
    "TRA-405": (
        "Asignar a todos los registros los valores fijos del Detalle de pago: FIDUCIARIA_QUE_EFECTUO_EL_PAGO "
        "«FIDUPREVISORA», GL 656, Q_PAGOS «1», AMORTIZACION_ANTICIPO 0 y MULTA 0"
    ),
    "TRA-407": (
        "Asignar NOMBRE_SUBFIDEICOMISO_PAGO según el SUBFIDEICOMISO de cada registro. Si el "
        "Subfideicomiso no está en la relación o está vacío, la celda queda vacía y se informa en el log"
    ),
    "TRA-408": (
        "Asignar RECURSOS según el SUBFIDEICOMISO de cada registro (por ejemplo, PAC JULIO 2026, FONDO PAZ "
        "o el convenio). Si el Subfideicomiso no está en la relación o está vacío, la celda queda vacía y "
        "se informa en el log"
    ),
    "TRA-406": (
        "Asignar FUENTE_DE_RECURSOS (PGN u OTROS) según el SUBFIDEICOMISO de cada registro. Si el "
        "Subfideicomiso no está en la relación o está vacío, la celda queda vacía y se informa en el log"
    ),
    "TRA-403": (
        "Calcular VALIDACION con la misma fórmula de Diferencia del ETY: VR_BRUTO - VR_RTEFTE - VR_RETEIVA "
        "- VR_RETEICA - VR_TASAS - VR_NETO (fórmula de Excel en cada fila)"
    ),
    "TRA-404": (
        "Calcular CONTRATO con la fórmula del Detalle de pago, que toma de CONCEPTO el número que sigue "
        "a «CONTRATO» (por ejemplo, «..._CONTRATO_303-2026_...» -> 303; fórmula de Excel en cada fila)"
    ),
    "TRA-409": (
        "Asignar VIGENCIA: si el CONTRATO es un número, se busca en CONCEPTO la expresión "
        "CONTRATO_<número>-<vigencia> (por ejemplo, CONTRATO_1345-2025 -> 2025) y se toma la vigencia. "
        "Si el CONTRATO está vacío o no es un número, o no se encuentra la expresión, VIGENCIA queda "
        "vacía"
    ),
    "TRA-410": (
        "Calcular CONTRATO_2 con la fórmula del Detalle de pago, que une CONTRATO y VIGENCIA con un guion "
        "(por ejemplo, 303-2026; fórmula de Excel en cada fila). Las demás columnas del Detalle de pago "
        "quedan vacías"
    ),
}

# Todas las reglas que aplica la etapa, en el orden en que se aplican. Es la lista que el
# usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 no aplica: se usa la primera hoja del archivo sin importar su nombre.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    *RULES,
]
