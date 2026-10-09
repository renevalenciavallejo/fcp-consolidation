# Entradas de la etapa de prueba: una con varios archivos y una con uno solo.
INPUTS = {
    "reports": {
        "label": "Reportes de prueba",
        "multiple": True,
        "required": True,
        "sheet": "Ejecucion",
        "header_row": 1,
        "columns": {
            "Codigo": "code",
            "Fecha": "date",
            "Valor": "number",
            "Fuente": "text",
        },
    },
    "catalog": {
        "label": "Catálogo de prueba",
        "multiple": False,
        "required": False,
        "sheet": "Catalogo",
        "header_row": 2,
        "columns": {
            "Codigo": "code",
            "Nombre": "text",
        },
    },
}

# Columnas que identifican un duplicado.
DUPLICATE_KEY = ["Codigo", "Fecha", "Valor"]

# Valores permitidos en la columna Fuente.
VALID_SOURCES = ["PGN", "Cooperación"]

# Reglas propias de la etapa de prueba.
RULES = {
    "VAL-901": "La fuente debe estar en el catálogo de fuentes",
}
