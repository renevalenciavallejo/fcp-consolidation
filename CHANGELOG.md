# Historial de cambios

Formato: `MAYOR.MENOR.PARCHE`. La versión se define en `pyproject.toml`.

## Sin publicar

- Etapa 1 – Limpieza del reporte ETY: validación de la estructura del reporte de pagos (primera hoja, encabezados en la fila 4, 24 columnas en orden).
- Opciones de entrada `sheet: None` (primera hoja, sin validar el nombre) y `check_column_order` (regla EST-008).
- Si los encabezados de un archivo están en otra fila, el mensaje de error indica en cuál.
- Las filas de título anteriores a los encabezados (filas 1 a 3 del reporte ETY) quedan registradas en la hoja Eliminados (regla LIM-003) y se informan aparte en el resumen.

## 0.1.0 – Arquitectura base

- Ejecutor con el flujo estándar de una etapa: verificación de entradas, lectura, validación estricta de estructura, procesamiento y construcción de resultados.
- Lectura de Excel con columnas internas de origen (archivo y fila) y validación de hoja, encabezados y columnas.
- Registro de auditoría (`AuditLog`) con cambios, hallazgos y eliminaciones, individuales y en bloque.
- Funciones comunes de limpieza y conversión: textos, números (formato colombiano y estadounidense), fechas (día/mes), códigos y duplicados.
- Archivo de salida con formato estándar y resaltado de hallazgos; log en Excel con hojas Resumen, Hallazgos, Cambios y Eliminados.
- Interfaz Streamlit, línea de comandos y scripts de inicio para Windows y macOS.
- Pruebas unitarias y estructura para pruebas con casos históricos.
- Aún no hay etapas registradas.
