"""Catálogo de reglas comunes a todas las etapas.

Solo datos: código de la regla y su descripción en español. Las reglas propias
de cada etapa se declaran en el `config.py` de la etapa, en el diccionario RULES.
"""

# Reglas de estructura: si fallan, el procesamiento se detiene sin generar resultados.
# Se describen como lo que se valida, porque así aparecen en la lista de reglas de la etapa.
STRUCTURE_RULES = {
    "EST-001": "Validar que el archivo se pueda abrir como Excel (.xlsx)",
    "EST-002": "Validar que exista la hoja esperada",
    "EST-003": "Validar que estén todas las columnas obligatorias",
    "EST-004": "Validar que no haya columnas que no se esperaban",
    "EST-005": "Validar que no haya encabezados repetidos",
    "EST-006": "Validar que no haya columnas con datos y sin encabezado",
    "EST-007": "Validar que se carguen los archivos obligatorios y no sobren archivos",
    "EST-008": "Validar que las columnas estén en el orden esperado",
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
