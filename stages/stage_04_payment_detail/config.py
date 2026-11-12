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

# Reglas propias de la etapa (serie 4xx).
RULES = {
    "TRA-401": (
        "Generar el archivo con la estructura y el formato del Detalle de pago (columnas, encabezados, "
        "estilos, anchos y formatos de celda). Por ahora el archivo sale sin datos"
    ),
}

# Todas las reglas que aplica la etapa, en el orden en que se aplican. Es la lista que el
# usuario consulta en la interfaz y en la hoja Reglas del log.
# EST-002 no aplica: se usa la primera hoja del archivo sin importar su nombre.
APPLIED_RULES = [
    "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",  # Estructura
    *RULES,
]
