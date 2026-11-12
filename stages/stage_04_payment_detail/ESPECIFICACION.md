# Etapa 4 – Integración al Detalle de pago

Objetivo: integrar la información del reporte ETY procesado en la Etapa 3 al archivo **Detalle de pago**. La etapa genera un archivo con la misma estructura y el mismo formato del Detalle de pago, que el usuario importa después manualmente a ese archivo.

**Estado actual:** se carga y valida el reporte ETY y se genera el archivo con la estructura y el formato del Detalle de pago, **sin datos**. La integración de los registros se agregará cuando se especifique.

## Archivo de entrada

### Reporte ETY procesado en la Etapa 3

| Elemento | Valor esperado |
| --- | --- |
| Archivo | El reporte ETY de pagos procesado en la Etapa 3 (por ejemplo `ETY_CAM_PAGOS_3_AP656-38426564_E03_procesado.xlsx`) |
| Cantidad | Un archivo por procesamiento |
| Hoja | La primera hoja del archivo (el nombre no se valida) |
| Fila de encabezados | 1 |
| Datos | Desde la fila 2 |
| Nombre | Debe contener `E03_procesado`, en cualquier parte (sin distinguir mayúsculas). Si no, se advierte («¿Está seguro de que es el reporte ETY procesado en la Etapa 3?») pero no se detiene |

Columnas obligatorias (25), exactamente en este orden (las mismas que deja la Etapa 3):

Beneficiario Pago, Identificación, Tercero Principal, FECHA DE PAGO, VR. BRUTO, VR. RTEFTE,
VR. RETEIVA, VR. RETEICA, VR. TASAS, Importe, Diferencia, Asiento, Descripción, LNP, Comprobante,
Documento, Nº Sec Doc, Más Info, Dpto, Cd Fnd, Subfideicomiso, Cuenta, Proy, Producto, Programa.

## Reglas

### Paso 1 – Validación de estructura (implementado)

El reporte se valida apenas se carga. Si no cumple, los errores aparecen debajo de su campo, Procesar queda deshabilitado y, si se procesa por la línea de comandos, se detiene sin generar resultados.

| Código | Validación |
| --- | --- |
| EST-007 | Se cargó exactamente un reporte ETY |
| — | Advertencia (no detiene): el nombre del reporte no contiene `E03_procesado` |
| EST-001 | El archivo se puede abrir como Excel (.xlsx) |
| EST-003 | Tiene las 25 columnas en la fila 1 (si los encabezados están en otra fila, se indica en cuál) |
| EST-004 | No tiene columnas adicionales |
| EST-005 | No tiene encabezados repetidos |
| EST-006 | No tiene columnas con datos sin encabezado |
| EST-008 | Las columnas están en el orden en que las deja la Etapa 3 (se indica la primera posición distinta) |

### Paso 2 – Archivo con el formato del Detalle de pago (TRA-401, implementado)

Se genera el archivo de salida con la estructura y el formato del Detalle de pago (tomados de `DetallePagoEjemploFormato.xlsx`). Por ahora **sin datos**: solo la fila de encabezados.

## Archivo de salida

- Hoja `Hoja1` con las 34 columnas del Detalle de pago, en este orden: ITEM, IDENTIFICACION, TERCERO, FECHA_DE_PAGO, VR_BRUTO, VR_RTEFTE, VR_RETEIVA, VR_RETEICA, VR_TASAS, VR_NETO, VALIDACION, ASIENTO, COMPROBANTE, NO_SEC_DOC, CONTRATO, VIGENCIA, SUBFIDEICOMISO, NOMBRE_SUBFIDEICOMISO_PAGO, CUENTA, TIPO_DE_PAGO, NO_BENEFICIARIOS, CONCEPTO, FIDUCIARIA_QUE_EFECTUO_EL_PAGO, INFORME_SEMANAL, PERIODO_DE_COBRO, RECURSOS, PROGRAMA, GL, Q_PAGOS, CONTRATO_2, AMORTIZACION_ANTICIPO, MULTA, FUENTE_DE_RECURSOS, RANGO.
- Encabezados: Calibri 11 en negrita, letra blanca sobre azul (verde en VIGENCIA y PROGRAMA), centrados, con ajuste de texto y bordes finos; fila de 58 de alto.
- Anchos de columna iguales a los del Detalle de pago.
- Formatos de celda de cada columna (para los datos que se agreguen): ITEM con número entero, FECHA_DE_PAGO como fecha (`d/mm/aaaa`), los valores (VR_BRUTO a VALIDACION, AMORTIZACION_ANTICIPO y MULTA) con formato de contabilidad en pesos, Q_PAGOS como texto y las demás generales; Calibri 11 y centrados, salvo TERCERO, VR_BRUTO a VR_NETO y CONCEPTO.
- Como en todas las etapas, la fila de encabezados queda inmovilizada y con filtros.
- Nombre: el del reporte ETY con `E03_procesado` cambiado por `E04_procesado` (`ETY_sept_E03_procesado.xlsx` → `ETY_sept_E04_procesado.xlsx`); el log, con `E04_log`.

La configuración de este formato está en `OUTPUT_LAYOUT` (`config.py`). El archivo de ejemplo no se guarda en el repositorio porque contiene datos reales.

## Tareas manuales

- Importar el archivo generado al Detalle de pago (por ahora sin datos).

## Pendiente por especificar

- Cómo se llena cada columna del Detalle de pago a partir del reporte ETY (incluidas las fórmulas de ITEM, VALIDACION, CONTRATO y CONTRATO_2 del ejemplo) y las columnas que no vienen del ETY.
