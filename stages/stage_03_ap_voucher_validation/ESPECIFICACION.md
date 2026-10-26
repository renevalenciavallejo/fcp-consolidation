# Etapa 3 – Validación con el AP Voucher

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
| Cantidad | Un archivo por procesamiento, obligatorio |
| Estructura | **Por especificar** (hoja, fila de encabezados y columnas). Por ahora solo se verifica que abra como .xlsx |

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

### Pasos siguientes (por especificar)

- Estructura del archivo AP Voucher.
- Validaciones del reporte ETY contra el AP Voucher.

## Archivo de salida

Por ahora, los mismos registros del reporte ETY, con la misma apariencia. El nombre sale del reporte ETY: es el mismo nombre con `E02_procesado` cambiado por `E03_procesado` en su lugar (`ETY_sept_E02_procesado.xlsx` → `ETY_sept_E03_procesado.xlsx`); el log, con `E03_log`.

## Tareas manuales

- Por definir.
