# Historial de cambios

Formato: `MAYOR.MENOR.PARCHE`. La versión se define en `pyproject.toml`.

## Sin publicar

- Etapa 1 – Limpieza del reporte ETY: validación de la estructura del reporte de pagos (primera hoja, encabezados en la fila 4, 24 columnas en orden).
- Opciones de entrada `sheet: None` (primera hoja, sin validar el nombre) y `check_column_order` (regla EST-008).
- Si los encabezados de un archivo están en otra fila, el mensaje de error indica en cuál.
- Tipo de columna `currency` (moneda, regla TIP-005): se convierte como número y se escribe con formato de moneda.
- Etapa 1: las columnas E a J (VR. BRUTO a Importe) se convierten a moneda.
- Etapa 1: se eliminan las filas con Descripción «Distribución Caja» (regla LIM-101), registradas en Eliminados.
- Función `comparable_text` para comparar textos sin tener en cuenta mayúsculas, tildes ni espacios sobrantes.
- Etapa 1: columna Diferencia a la derecha de Importe con la fórmula `=E-F-G-H-I-J` de Excel (regla TRA-101).
- Soporte de fórmulas de Excel en el archivo de salida (`ExcelFormula`), con referencias por nombre de columna.
- Registro de columnas calculadas en el log (`AuditLog.column_added`, sección «Columnas agregadas» del Resumen).
- Etapa 1: los registros con Comprobante repetido se señalan como Advertencia (VAL-101) y la tabla se ordena por Comprobante (TRA-102).
- Funciones `flag_repeated_values` y `sort_rows`, y registro de transformaciones de tabla en el log (`AuditLog.transformation`).
- Las filas de título anteriores a los encabezados (filas 1 a 3 del reporte ETY) quedan registradas en la hoja Eliminados (regla LIM-003) y se informan aparte en el resumen.
- La interfaz muestra un log de ejecución en vivo (cada paso y su resultado: archivos verificados, estructura validada, filas de título eliminadas, reglas de la etapa) en lugar de las métricas de resultados. Si el proceso se detiene, el log indica en qué paso.
- Nueva hoja «Ejecución» en el log de Excel con los mismos pasos. La CLI imprime el mismo log en lugar del resumen de conteos.
- Las pestañas Hallazgos, Cambios y Eliminados de la interfaz se reemplazan por una sola tabla, «Acciones realizadas», en el orden en que ocurrió cada acción, con el paso, la acción realizada y todas las columnas del registro. La columna Archivo solo aparece cuando se procesan varios archivos. También queda en la nueva hoja «Acciones» del log (las hojas Hallazgos, Cambios y Eliminados se conservan).
- Los archivos generados conservan el nombre del archivo original y agregan al final `_E01_procesado` o `_E01_log`, sin fecha (antes `E01_ety_cleaning_procesado_<fecha>`). Si ya existe un archivo con ese nombre en `output/`, se agrega `_1`, `_2`, …
- `AuditLog.step`, `note` y `finish_step` para declarar los pasos; el resultado de cada paso se calcula a partir de lo registrado.

## 0.1.0 – Arquitectura base

- Ejecutor con el flujo estándar de una etapa: verificación de entradas, lectura, validación estricta de estructura, procesamiento y construcción de resultados.
- Lectura de Excel con columnas internas de origen (archivo y fila) y validación de hoja, encabezados y columnas.
- Registro de auditoría (`AuditLog`) con cambios, hallazgos y eliminaciones, individuales y en bloque.
- Funciones comunes de limpieza y conversión: textos, números (formato colombiano y estadounidense), fechas (día/mes), códigos y duplicados.
- Archivo de salida con formato estándar y resaltado de hallazgos; log en Excel con hojas Resumen, Hallazgos, Cambios y Eliminados.
- Interfaz Streamlit, línea de comandos y scripts de inicio para Windows y macOS.
- Pruebas unitarias y estructura para pruebas con casos históricos.
- Aún no hay etapas registradas.
