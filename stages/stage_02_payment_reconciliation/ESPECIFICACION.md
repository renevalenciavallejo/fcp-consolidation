# Etapa 2 – Conciliación de pagos

## Archivo de entrada

| Elemento | Valor esperado |
| --- | --- |
| Archivo | El reporte ETY de pagos procesado en la Etapa 1 (por ejemplo `ETY_CAM_PAGOS_3_AP656-38426564_E01_procesado.xlsx`) |
| Cantidad | Un archivo por procesamiento |
| Hoja | La primera hoja del archivo (la Etapa 1 conserva el nombre del reporte original, por ejemplo `sheet1`; el nombre no se valida) |
| Fila de encabezados | 1 (la Etapa 1 ya quitó las filas de título) |
| Datos | Desde la fila 2 |

Columnas obligatorias (25), exactamente en este orden: las 24 del reporte ETY con la columna **Diferencia** en la K, a la derecha de Importe.

Beneficiario Pago, Identificación, Tercero Principal, FECHA DE PAGO, VR. BRUTO, VR. RTEFTE,
VR. RETEIVA, VR. RETEICA, VR. TASAS, Importe, Diferencia, Asiento, Descripción, LNP, Comprobante,
Documento, Nº Sec Doc, Más Info, Dpto, Cd Fnd, Subfideicomiso, Cuenta, Proy, Producto, Programa.

## Reglas

### Paso 1 – Validación de estructura (implementado)

Si el archivo no cumple, el procesamiento se detiene sin generar resultados y se explica qué falla.

| Código | Validación |
| --- | --- |
| EST-007 | Se cargó exactamente un archivo |
| EST-001 | El archivo se puede abrir como Excel (.xlsx) |
| EST-003 | Están las 25 columnas en la fila 1 (si los encabezados están en otra fila, se indica en cuál; por ejemplo, si se carga el reporte original sin pasar por la Etapa 1) |
| EST-004 | No hay columnas adicionales |
| EST-005 | No hay encabezados repetidos |
| EST-006 | No hay columnas con datos sin encabezado |
| EST-008 | Las columnas están en el orden en que las deja la Etapa 1 (se indica la primera posición distinta) |

### Pasos siguientes (por especificar)

- Reglas de conciliación de pagos.

## Archivo de salida

Por ahora, los mismos registros del archivo de entrada, con la misma apariencia. El nombre reemplaza el sufijo de la Etapa 1: `<nombre original>_E02_procesado.xlsx`.

- La columna **Diferencia** se lee con el valor que Excel guardó al abrir el archivo de la Etapa 1. Si ese archivo se carga sin haberlo abierto y guardado en Excel, la columna llega vacía (la fórmula todavía no tiene valor calculado).

## Tareas manuales

Por definir.
