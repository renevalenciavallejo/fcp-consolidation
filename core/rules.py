"""Catálogo de reglas comunes a todas las etapas.

Solo datos: código de la regla y su descripción en español. Las reglas propias
de cada etapa se declaran en el `config.py` de la etapa, en el diccionario RULES.
"""

# Reglas de estructura: si fallan, el procesamiento se detiene sin generar resultados.
STRUCTURE_RULES = {
    "EST-001": "El archivo no se pudo abrir como Excel (.xlsx)",
    "EST-002": "La hoja esperada no existe en el archivo",
    "EST-003": "Faltan columnas obligatorias",
    "EST-004": "El archivo tiene columnas que no se esperaban",
    "EST-005": "Hay encabezados repetidos",
    "EST-006": "Hay una columna con datos pero sin encabezado",
    "EST-007": "Falta una entrada obligatoria o sobran archivos",
    "EST-008": "Las columnas no están en el orden esperado",
}

# Reglas comunes que sí quedan registradas en el log.
COMMON_RULES = {
    "LIM-001": "Quitar espacios sobrantes y caracteres invisibles en textos",
    "LIM-002": "Eliminar filas completamente vacías",
    "LIM-003": "Eliminar las filas anteriores a los encabezados (títulos del reporte)",
    "TIP-001": "Convertir a número",
    "TIP-002": "Convertir a fecha (día/mes/año)",
    "TIP-003": "Normalizar códigos como texto",
    "TIP-004": "Convertir a texto",
    "TIP-005": "Convertir a moneda",
    "DUP-001": "Eliminar registros duplicados",
}
