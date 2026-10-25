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
| Nombre | Debe terminar en `_E01_procesado` (se acepta el número de copia: `_1` o ` (1)`). Si no, se advierte pero no se detiene |

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
| Hoja | `Pagos` (la segunda pestaña; RESUMEN y H3 no se usan) |
| Fila de encabezados | 1 |
| Datos | Desde la fila 2 (las filas vacías del final se ignoran) |

Columnas obligatorias, en cualquier posición: **F Ejec** (fecha de ejecución del pago, columna A), **UN** (unidad de negocio, B), **Comprobante** (P) e **Impt Bruto** (T). El informe trae muchas más columnas (Factura, Impt Neto Pago, …), que se aceptan sin validarlas; algunas vienen repetidas, como «Nº Cuenta», y eso tampoco es un error. Un encabezado repetido sí es error si es una de las cuatro obligatorias.

En la interfaz, al cargar el reporte ETY se valida su estructura (Paso 1) y, si es correcta, aparece un campo de carga por cada fecha de pago, con la fecha en la etiqueta («Informe de pago del 22 de septiembre de 2026»). Si el reporte tiene errores de estructura, se muestran de inmediato y no aparecen los campos. Cada informe se valida y analiza apenas se carga, con las mismas reglas de los pasos 2 a 5 (estructura, UN AP656, F Ejec, comprobantes repetidos y total de Impt Bruto), Debajo de su campo aparece la información calculada (registros con UN AP656 de los leídos, registros descartados por Comprobante repetido, total de Impt Bruto y, si los hay, registros sin Impt Bruto numérico) o, si no pasa la validación, el mensaje de error. Debajo de los campos de carga, las pestañas «Log de ejecución» y «Acciones realizadas» muestran todo lo que se hizo con los archivos al cargarlos: la validación del reporte ETY y el análisis de cada informe. Al procesar, esas pestañas se reemplazan por el log completo del procesamiento. El botón Procesar se habilita cuando todas las fechas tienen su informe y ninguno tiene errores; al procesar se vuelven a aplicar todas las reglas y el resultado queda en el log.

## Reglas

### Paso 1 – Validación de estructura (implementado)

Si el archivo no cumple, el procesamiento se detiene sin generar resultados y se explica qué falla.

| Código | Validación |
| --- | --- |
| EST-007 | Se cargó exactamente un archivo |
| — | Advertencia (no detiene): el nombre del archivo no termina en `_E01_procesado`. Al cargarlo, la interfaz pregunta «¿Está seguro de que es el reporte ETY procesado en la Etapa 1?», y el aviso queda en el log de ejecución |
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
| EST-002 | Cada informe tiene la hoja `Pagos` |
| EST-003 | La hoja Pagos tiene las columnas F Ejec, UN, Comprobante e Impt Bruto en la fila 1 |
| EST-005 | Esas cuatro columnas no están repetidas |
| EST-006 | No hay columnas con datos sin encabezado |

### Paso 3 – Pagos del FCP (implementado)

| Código | Regla |
| --- | --- |
| LIM-201 | De cada informe se toman solo los registros con **UN** `AP656` (sin distinguir mayúsculas ni espacios sobrantes). Los de otras unidades de negocio no se usan. En el log de ejecución se indica cuántos se tomaron de cada informe («130 de 463 registros con UN AP656»); no se listan uno a uno. El reporte ETY no cambia |

### Paso 4 – Fecha de los informes (implementado)

| Código | Validación |
| --- | --- |
| VAL-201 | La **F Ejec** de cada registro con UN AP656 (solo el día, sin la hora) es la fecha del campo donde se cargó el informe |

Si algún registro tiene otra fecha (o la tiene vacía o no válida), el procesamiento **se detiene sin generar resultados**: casi siempre significa que el informe se cargó en el campo de otra fecha. El mensaje indica el informe, la fecha del campo, las fechas encontradas y las filas de la hoja Pagos (hasta 10 por fecha; las demás se cuentan). Se revisan todos los informes antes de detenerse, para mostrar todos los problemas de una vez.

### Paso 5 – Comprobantes repetidos y total de Impt Bruto (implementado)

Se hace **en memoria**, sobre los registros con UN AP656: los informes de pago no se modifican y no hacen parte del archivo de salida.

| Código | Regla |
| --- | --- |
| TIP-003 | **Comprobante** se lee como código (texto, con sus ceros a la izquierda), para reconocer el mismo comprobante aunque venga escrito distinto |
| TIP-005 | **Impt Bruto** se convierte a moneda. Un valor que no es número queda como estaba y se reporta como Error en la hoja Acciones |
| DUP-201 | Dentro de cada informe, si un Comprobante se repite (por ejemplo, el mismo pago partido en dos transferencias con el mismo Impt Bruto), se deja un solo registro: el primero. Cada descartado aparece como «Fila eliminada» en la hoja Acciones, con todos sus datos y la fila del que se conservó. Un comprobante que aparece en informes de fechas distintas no se toma como repetido. Los registros sin Comprobante no se comparan entre sí |
| TRA-201 | Se informa en el log de ejecución el total de **Impt Bruto** de cada informe (con su fecha y cantidad de registros) y el total de todos los informes. Los valores que no son número no se suman y se avisa cuántos son |

Ejemplo con los informes reales del 28, 29 y 30 de septiembre de 2026: se descartan la fila 421 del 28 (comprobante 00157395, se conserva la 420) y la fila 227 del 29 (00157353, se conserva la 225). Totales: $ 1.215.024.240,87, $ 6.370.226.836,84 y $ 19.781.705.464,59; en total $ 27.366.956.542,30 en 375 registros.

### Pasos siguientes (por especificar)

- Reglas de conciliación de pagos.

## Archivo de salida

Por ahora, los mismos registros del reporte ETY, con la misma apariencia. El nombre sale del reporte ETY (no de los informes) y reemplaza el sufijo de la Etapa 1: `<nombre original>_E02_procesado.xlsx`.

- La columna **Diferencia** se lee con el valor que Excel guardó al abrir el archivo de la Etapa 1. Si ese archivo se carga sin haberlo abierto y guardado en Excel, la columna llega vacía (la fórmula todavía no tiene valor calculado).

## Tareas manuales

- Si el procesamiento se detiene por VAL-201, cargar cada informe en el campo de su fecha (o pedir a Tesorería el informe correcto) y procesar de nuevo.
- Las demás, por definir.
