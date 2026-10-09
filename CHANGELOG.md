# Historial de cambios

Formato: `MAYOR.MENOR.PARCHE`. La versión se define en `pyproject.toml`.

## 0.1.0 – Arquitectura base

- Ejecutor con el flujo estándar de una etapa: verificación de entradas, lectura, validación estricta de estructura, procesamiento y construcción de resultados.
- Lectura de Excel con columnas internas de origen (archivo y fila) y validación de hoja, encabezados y columnas.
- Registro de auditoría (`AuditLog`) con cambios, hallazgos y eliminaciones, individuales y en bloque.
- Funciones comunes de limpieza y conversión: textos, números (formato colombiano y estadounidense), fechas (día/mes), códigos y duplicados.
- Archivo de salida con formato estándar y resaltado de hallazgos; log en Excel con hojas Resumen, Hallazgos, Cambios y Eliminados.
- Interfaz Streamlit, línea de comandos y scripts de inicio para Windows y macOS.
- Pruebas unitarias y estructura para pruebas con casos históricos.
- Aún no hay etapas registradas.
