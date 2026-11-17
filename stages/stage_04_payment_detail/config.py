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

# CONTRATO según CONCEPTO cuando su fórmula da #¡VALOR! (regla TRA-413): término que se busca en
# CONCEPTO -> valor de CONTRATO. Se busca sin distinguir mayúsculas ni tildes, pero los «_» y los
# espacios cuentan (por eso algunos términos aparecen con las dos formas). Si CONCEPTO contiene
# varios términos, gana el más largo (el más específico: «ADR_PROY_PROD_PIDAR» antes que
# «PROY_PROD»); con el mismo largo, el primero de esta lista. Si no contiene ninguno, la celda
# conserva la fórmula (#¡VALOR!) para que el usuario la ajuste manualmente.
CONTRACT_BY_CONCEPT = {
    "DESPLAZAMIENTO": "GV",
    "COMPRA_PREDIO": "CP",
    "COMPRA DEL PREDIO": "CP",
    "PROY_PROD": "PROVEEDORES",
    "SEMBRANDO_VIDA": "PP",
    "SUMINISTROS": "SV",
    "PENSION": "PS",
    "BEPS": "PS",
    "RENTA BASICA": "RB",
    "RENTA_BASICA": "RB",
    "ASIGNACION UNICA": "RB",
    "ASIGNACION_UNICA": "RB",
    "ASIGNACION MENSUAL": "RB",
    "ASIGNACION_MENSUAL": "RB",
    "COMPARECIENTES": "RB",
    "INGRESO BASICO": "RB",
    "INGRESO_BASICO": "RB",
    "DAPRE": "PROMOTORES",
    "DAFT": "PROMOTORES",
    "RENHACEMOS": "DECRETO",
    "RENHA": "DECRETO",
    "SUSTITUCION_ALISTAMIENTO": "PROVEEDORES",
    "SUSTITUCION_ASISTENCIA ALIMENTARIA INMEDIATA": "PF",
    "SUSTITUCION_ATENCIÓN DIFERENCIAL": "ATENCIÓN DIFERENCIAL",
    "POLIZAS_CONTRATO": "POLIZA",
    "CAJA_MENOR": "CM",
    "CAJA MENOR": "CM",
    "ADR_PROY_PROD_PIDAR": "PIDAR",
    "ADR__PROY_PROD_PIDAR": "PIDAR",
}
CONTRACT_COLUMN = "CONTRATO"
CONTRACT_ERROR = "#¡VALOR!"   # Lo que muestra Excel cuando la fórmula de CONTRATO no encuentra el contrato

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

# Columna del Detalle de pago con el año en que se genera el archivo (al presionar Procesar),
# como número (por ejemplo, 2026). Es el mismo en todos los registros.
GENERATION_YEAR_COLUMN = "RANGO"

# TIPO_DE_PAGO y NO_BENEFICIARIOS (regla TRA-412). Si CONCEPTO contiene la expresión
# BENEF_<número de beneficiarios>_ (por ejemplo BENEF_14_), el pago es masivo y el número de
# beneficiarios es ese número. Si no la contiene, o el número es 1 (BENEF_1_), el pago es
# individual, con 1 beneficiario.
PAYMENT_TYPE_COLUMN = "TIPO_DE_PAGO"
BENEFICIARIES_COLUMN = "NO_BENEFICIARIOS"
BENEFICIARIES_PREFIX = "BENEF_"     # Texto que antecede al número (distingue mayúsculas)
MASS_PAYMENT = "MASIVO"             # TIPO_DE_PAGO cuando se encuentra la expresión (con más de 1)
INDIVIDUAL_PAYMENT = "INDIVIDUAL"   # TIPO_DE_PAGO cuando no se encuentra, o con BENEF_1_
INDIVIDUAL_BENEFICIARIES = 1        # NO_BENEFICIARIOS de un pago individual

# PERIODO_DE_COBRO (regla TRA-414). Se calcula en Python a partir de CONCEPTO y se escribe como
# texto (no como fórmula): «Febrero de 2026» o, si el periodo abarca varios meses, «Febrero a
# Marzo de 2026». CONCEPTO trae el periodo en formatos muy distintos (1-28-FEBRERO-2026,
# 01 FEB - 28 FEB 2026, DEL 01 AL 31 DE MARZO DEL 2026, 6_febrero_2026 al 6_marzo_2026...).
PERIOD_COLUMN = "PERIODO_DE_COBRO"
PAYMENT_DATE_COLUMN = "FECHA_DE_PAGO"   # De aquí sale el año si CONCEPTO no lo trae
# Solo se mira CONCEPTO hasta este texto (sin mayúsculas ni tildes): lo que sigue («AUTORIZACION
# DE PAGO_2026...», facturas) tiene números y palabras como «PAGO» que se confundirían con
# años y meses («AGO»).
PERIOD_END_MARKER = "AUTORIZACI"
# Caracteres que se tratan como espacios, para que «1-28-FEBRERO-2026» y «6_febrero_2026» se
# lean igual que «01 FEB 2026».
PERIOD_SEPARATORS = ["_", "-", "*", "'", "/", ".", ","]
# Meses tal como se escriben en PERIODO_DE_COBRO. En CONCEPTO se buscan como palabra suelta, con
# el nombre completo (JULIO) o la abreviatura de 3 letras (JUL), sin distinguir mayúsculas ni
# tildes. Pueden ir pegados a números («JULIO2026»), pero no a otras letras, para no confundir
# palabras como «PAGO» (AGO) o «MAYOR» (MAYO).
MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
MONTH_ABBREVIATION_LENGTH = 3
# Año del periodo: el primer número de 4 cifras entre 2000 y 2099 que aparece después del último
# mes encontrado (expresión regular). Si no hay, se usa el año de FECHA_DE_PAGO.
PERIOD_YEAR_PATTERN = r"(?<!\d)20\d{2}(?!\d)"
# Texto de PERIODO_DE_COBRO: con un solo mes y con un rango (primer y último mes que aparecen).
PERIOD_SINGLE_MONTH = "{start} de {year}"
PERIOD_MONTH_RANGE = "{start} a {end} de {year}"

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

# PAC vigente. Cuando cambie, se actualiza solo aquí: lo usan los Subfideicomisos de
# SUBTRUST_RESOURCES y los Programas 0001 y 0002 de PROGRAM_EXCEPTIONS.
CURRENT_PAC = "PAC JULIO 2026"

# Relación Subfideicomiso -> recursos (RECURSOS).
SUBTRUST_RESOURCES = {
    "1001": CURRENT_PAC,
    "1002": CURRENT_PAC,
    "1003": CURRENT_PAC,
    "1004": CURRENT_PAC,
    "1005": CURRENT_PAC,
    "1006": CURRENT_PAC,
    "1007": CURRENT_PAC,
    "1008": CURRENT_PAC,
    "1009": CURRENT_PAC,
    "2010": CURRENT_PAC,
    "2011": CURRENT_PAC,
    "2013": "PAC BID PRESTAMO SEP2019",
    "2016": "CENIT",
    "2017": CURRENT_PAC,
    "2018": "BID FACILIDAD",
    "2019": CURRENT_PAC,
    "2020": "KFW",
    "2021": "AFD",
    "2022": "BID FACILIDAD",
    "2023": "VISIÓN AMAZONIA",
    "2024": CURRENT_PAC,
    "2025": "BID FACILIDAD",
    "2026": "BID FACILIDAD",
    "2027": "FONDO PAZ",
    "2028": "FONDO PAZ",
    "2029": "FONDO PAZ",
    "2030": "FONDO PAZ",
    "2031": CURRENT_PAC,
    "2032": "FONDO PAZ",
    "2033": "FONDO PAZ",
    "2034": "OTROS RECURSOS ANT",
    "2035": "CONVENIO IGAC 1231-23",
    "2036": "CONVENIO ART-KFW",
    "2038": "CONVENIO ADR 1141-24",
    "2039": "CONVENIO MADR 2403-25",
    "2041": CURRENT_PAC,
    "2042": CURRENT_PAC,
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

# Columna del Detalle de pago con el Programa de cada registro (texto, con sus ceros).
PROGRAM_COLUMN = "PROGRAMA"

# Excepción por Programa: si el PROGRAMA de un registro es uno de estos, RECURSOS y
# FUENTE_DE_RECURSOS toman estos valores y no los de su Subfideicomiso. Con cualquier otro
# Programa (o sin Programa) se aplica la relación por Subfideicomiso.
PROGRAM_RESOURCES = {
    "0001": CURRENT_PAC,
    "0002": CURRENT_PAC,
    "0005": "RENDIMIENTOS",
    "0016": "CLAUSULA DE APREMIO",
}
PROGRAM_FUNDING_SOURCES = {
    "0001": "PGN",
    "0002": "PGN",
    "0005": "OTROS",
    "0016": "OTROS",
}

# Columnas del Detalle de pago que se llenan según el Subfideicomiso de cada registro, en este
# orden: regla, columna, relación por Subfideicomiso y, si tiene, la excepción por Programa
# (que prevalece). Un Subfideicomiso que no está en la relación (o vacío) deja la celda vacía
# y se informa en el log, para completarla manualmente.
SUBTRUST_RELATIONS = [
    {"rule": "TRA-407", "column": "NOMBRE_SUBFIDEICOMISO_PAGO", "values": SUBTRUST_NAMES},
    {"rule": "TRA-408", "column": "RECURSOS", "values": SUBTRUST_RESOURCES,
     "program_values": PROGRAM_RESOURCES},
    {"rule": "TRA-406", "column": "FUENTE_DE_RECURSOS", "values": FUNDING_SOURCES,
     "program_values": PROGRAM_FUNDING_SOURCES},
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
    "TRA-411": (
        "Asignar a todos los registros, en RANGO, el año en que se genera el archivo (por ejemplo, 2026)"
    ),
    "TRA-412": (
        "Asignar TIPO_DE_PAGO y NO_BENEFICIARIOS: si CONCEPTO contiene la expresión "
        "BENEF_<número de beneficiarios>_ (por ejemplo, BENEF_14_), MASIVO y ese número (14). Si no la "
        "contiene, o es BENEF_1_, INDIVIDUAL y 1"
    ),
    "TRA-414": (
        "Asignar PERIODO_DE_COBRO a partir de los meses que menciona CONCEPTO antes de «AUTORIZACION», "
        "por nombre completo o abreviatura (FEBRERO o FEB): «Febrero de 2026» con un solo mes, o «Febrero "
        "a Marzo de 2026» con el primer y el último mes si son distintos. El año es el que sigue al "
        "último mes; si CONCEPTO no lo trae, el de FECHA_DE_PAGO. Si CONCEPTO no menciona ningún mes, "
        "la celda queda vacía y se informa en el log. Se escribe como texto, no como fórmula"
    ),
    "TRA-407": (
        "Asignar NOMBRE_SUBFIDEICOMISO_PAGO según el SUBFIDEICOMISO de cada registro. Si el "
        "Subfideicomiso no está en la relación o está vacío, la celda queda vacía y se informa en el log"
    ),
    "TRA-408": (
        "Asignar RECURSOS según el SUBFIDEICOMISO de cada registro (por ejemplo, PAC JULIO 2026, FONDO PAZ "
        "o el convenio). Excepción: con PROGRAMA 0001 o 0002, PAC JULIO 2026; con 0005, RENDIMIENTOS; "
        "con 0016, CLAUSULA DE APREMIO. Si el Subfideicomiso no está en la relación o está vacío, la "
        "celda queda vacía y se informa en el log"
    ),
    "TRA-406": (
        "Asignar FUENTE_DE_RECURSOS (PGN u OTROS) según el SUBFIDEICOMISO de cada registro. Excepción: "
        "con PROGRAMA 0001 o 0002, PGN; con 0005 o 0016, OTROS. Si el Subfideicomiso no está en la "
        "relación o está vacío, la celda queda vacía y se informa en el log"
    ),
    "TRA-403": (
        "Calcular VALIDACION con la misma fórmula de Diferencia del ETY: VR_BRUTO - VR_RTEFTE - VR_RETEIVA "
        "- VR_RETEICA - VR_TASAS - VR_NETO (fórmula de Excel en cada fila)"
    ),
    "TRA-404": (
        "Calcular CONTRATO con la fórmula del Detalle de pago, que toma de CONCEPTO el número que sigue "
        "a «CONTRATO» (por ejemplo, «..._CONTRATO_303-2026_...» -> 303; fórmula de Excel en cada fila)"
    ),
    "TRA-413": (
        "Cuando la fórmula de CONTRATO da #¡VALOR!, asignar CONTRATO según el término que contenga "
        "CONCEPTO (por ejemplo, DESPLAZAMIENTO -> GV, RENTA_BASICA -> RB, CAJA MENOR -> CM), sin "
        "distinguir mayúsculas ni tildes. Si contiene varios, gana el más largo. Si no contiene ninguno, "
        "se deja la fórmula (#¡VALOR!) para ajustarlo manualmente"
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
