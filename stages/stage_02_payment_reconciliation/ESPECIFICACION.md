# Etapa 2 – Conciliación de pagos

## Archivos de entrada

La etapa recibe dos tipos de archivo: el reporte ETY procesado en la Etapa 1 y un informe de pago de Tesorería por cada fecha de pago del reporte.

### Reporte ETY procesado

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

### Informes de pago de Tesorería

| Elemento | Valor esperado |
| --- | --- |
| Archivo | El informe de pagos que remite la Tesorería para una fecha |
| Cantidad | Uno por cada fecha distinta de la columna **FECHA DE PAGO** (D) del reporte ETY, todos obligatorios. Normalmente hasta 5 (pagos de una semana, en días hábiles) |
| Fechas | Se toma solo el día (sin la hora). Las celdas vacías se ignoran (no piden informe) |
| Estructura | **Por especificar.** Por ahora solo se verifica que cada archivo abra como .xlsx |

En la interfaz, al cargar el reporte ETY se valida su estructura (Paso 1) y, si es correcta, aparece un campo de carga por cada fecha de pago, con la fecha en la etiqueta («Informe de pago del 22 de septiembre de 2026»). Si el reporte tiene errores de estructura, se muestran de inmediato y no aparecen los campos. El botón Procesar se habilita cuando todas las fechas tienen su informe.

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

### Paso 2 – Informes de pago por fecha (implementado)

| Código | Validación |
| --- | --- |
| EST-007 | Hay un informe por cada fecha de pago del reporte ETY y ninguno de una fecha que no esté en el reporte |
| EST-001 | Cada informe se puede abrir como Excel (.xlsx) |

### Pasos siguientes (por especificar)

- Estructura de los informes de pago de Tesorería y su validación (incluida la verificación de que cada informe corresponda a su fecha).
- Reglas de conciliación de pagos.

## Archivo de salida

Por ahora, los mismos registros del reporte ETY, con la misma apariencia. El nombre sale del reporte ETY (no de los informes) y reemplaza el sufijo de la Etapa 1: `<nombre original>_E02_procesado.xlsx`.

- La columna **Diferencia** se lee con el valor que Excel guardó al abrir el archivo de la Etapa 1. Si ese archivo se carga sin haberlo abierto y guardado en Excel, la columna llega vacía (la fórmula todavía no tiene valor calculado).

## Tareas manuales

Por definir.
