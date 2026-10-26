# Etapa 3 – Cruce con el AP Voucher

## Archivos de entrada

La etapa recibe dos archivos: el reporte ETY procesado en la Etapa 2 y el archivo AP Voucher.

### Reporte ETY procesado

| Elemento | Valor esperado |
| --- | --- |
| Archivo | El reporte ETY de pagos procesado en la Etapa 2 (por ejemplo `ETY_CAM_PAGOS_3_AP656-38426564_E02_procesado.xlsx`) |
| Cantidad | Un archivo por procesamiento |
| Hoja | La primera hoja del archivo (las etapas anteriores conservan el nombre del reporte original, por ejemplo `sheet1`; el nombre no se valida) |
| Fila de encabezados | 1 |
| Datos | Desde la fila 2 |
| Nombre | Debe contener `E02_procesado`, en cualquier parte (sin distinguir mayúsculas). Si no, se advierte («¿Está seguro de que es el reporte ETY procesado en la Etapa 2?») pero no se detiene |

Columnas obligatorias (25), exactamente en este orden (las mismas que deja la Etapa 1 y conserva la Etapa 2):

Beneficiario Pago, Identificación, Tercero Principal, FECHA DE PAGO, VR. BRUTO, VR. RTEFTE,
VR. RETEIVA, VR. RETEICA, VR. TASAS, Importe, Diferencia, Asiento, Descripción, LNP, Comprobante,
Documento, Nº Sec Doc, Más Info, Dpto, Cd Fnd, Subfideicomiso, Cuenta, Proy, Producto, Programa.

### Archivo AP Voucher

| Elemento | Valor esperado |
| --- | --- |
| Archivo | Reporte «Información Revisión Voucher» (por ejemplo `AP_REVISION_VOUCHER-38426575-0110-Original.xlsx`) |
| Cantidad | Un archivo por procesamiento, obligatorio |
| Hoja | La primera hoja del archivo (el nombre no se valida) |
| Filas 1 a 19 | Título y parámetros del reporte (UN, fechas, horas). No son datos: quedan en Acciones como filas de título (LIM-003) |
| Fila de encabezados | 20 |
| Datos | Desde la fila 21 |

Columnas obligatorias: Comprobante (columna E), Estado Cierre (columna K) y Acción (columna BF). Se buscan por su nombre, no por su letra. El reporte trae otras columnas (113 en total), que se aceptan sin validarse; algunas tienen el encabezado repetido (Nombre, Tipo Documento, Identificación, Cuenta) y se conserva la primera.

El AP Voucher solo se consulta en memoria: no hace parte del archivo de salida y nunca se modifica.

## Reglas

### Paso 1 – Validación de estructura (implementado)

Si un archivo no cumple, el procesamiento se detiene sin generar resultados y se explica qué falla.

| Código | Validación |
| --- | --- |
| EST-007 | Se cargó exactamente un reporte ETY y un archivo AP Voucher |
| — | Advertencia (no detiene): el nombre del reporte ETY no contiene `E02_procesado` |
| EST-001 | Ambos archivos se pueden abrir como Excel (.xlsx) |
| EST-003 | El reporte ETY tiene las 25 columnas en la fila 1 (si los encabezados están en otra fila, se indica en cuál) |
| EST-004 | El reporte ETY no tiene columnas adicionales |
| EST-005 | El reporte ETY no tiene encabezados repetidos |
| EST-006 | El reporte ETY no tiene columnas con datos sin encabezado |
| EST-008 | Las columnas del reporte ETY están en el orden en que las deja la Etapa 2 (se indica la primera posición distinta) |
| EST-003 | El AP Voucher tiene las columnas Comprobante, Estado Cierre y Acción en la fila 20 |
| EST-005 | El AP Voucher no tiene repetidas las columnas Comprobante, Estado Cierre ni Acción |

### Paso 2 – Comprobantes cerrados en el AP Voucher (VAL-301)

1. Del AP Voucher se toman los registros con Estado Cierre «Cerrado» (sin distinguir mayúsculas, tildes ni espacios sobrantes).
2. De esos registros se obtienen los comprobantes únicos (los repetidos se cuentan una vez). Se comparan como códigos: se conservan los ceros a la izquierda y se ignoran los espacios.
3. Se buscan en el reporte ETY los registros cuyo Comprobante está en esa lista.
4. Cada uno queda como **Advertencia** en su registro del ETY: aparece en «Acciones realizadas» (con las filas del AP Voucher donde está cerrado) y la celda Comprobante se resalta en **naranja claro** en el archivo de salida.
5. El log de ejecución informa cuántos registros cerrados y comprobantes únicos tiene el AP Voucher y, con ✗, cuántos comprobantes del ETY están cerrados y cuáles son. No detiene el proceso.

### Paso 3 – Comprobantes cancelados en el AP Voucher (VAL-302)

Igual que el paso 2, pero con los registros del AP Voucher cuya Acción es «Cancelado». La celda Comprobante se resalta en **gris claro**.

Si un comprobante está cerrado y cancelado, tiene las dos advertencias en Acciones y la celda queda en gris claro (el color del último paso).

Los colores son distintos al amarillo de las advertencias generales (por ejemplo, los comprobantes repetidos de la Etapa 1) para que el usuario distinga cada caso.

### Al cargar los archivos

- Cada archivo (reporte ETY y AP Voucher) se valida apenas se carga, **solo en su estructura** (paso 1). Si tiene errores, aparecen debajo de su campo y Procesar queda deshabilitado; si pasa, no se muestra nada. Lo que se hizo queda en las pestañas «Log de ejecución» y «Acciones realizadas».
- La búsqueda de comprobantes cerrados y cancelados (pasos 2 y 3) se hace solo al presionar Procesar.

### Al terminar el procesamiento

Debajo del mensaje de procesamiento terminado aparece una notificación de información con los resultados. Por cada búsqueda indica el color con que se resaltan los comprobantes en el archivo de salida (naranja claro los cerrados, gris claro los cancelados) y cuáles comprobantes del reporte ETY se encontraron, con su fila (hasta 20 por búsqueda; todos están en Acciones), o «ninguno».

## Archivo de salida

Los mismos registros del reporte ETY, sin cambios y con la misma apariencia, con los comprobantes cerrados (naranja claro) y cancelados (gris claro) resaltados. El nombre sale del reporte ETY: es el mismo nombre con `E02_procesado` cambiado por `E03_procesado` en su lugar (`ETY_sept_E02_procesado.xlsx` → `ETY_sept_E03_procesado.xlsx`); el log, con `E03_log`.

## Tareas manuales

- Revisar cada comprobante del ETY cerrado o cancelado en el AP Voucher (hoja Acciones del log) y hacer las verificaciones manuales del caso.
