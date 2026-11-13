# Etapa 4 – Integración al Detalle de pago

Objetivo: integrar la información del reporte ETY procesado en la Etapa 3 al archivo **Detalle de pago**. La etapa genera un archivo con la misma estructura y el mismo formato del Detalle de pago, que el usuario importa después manualmente a ese archivo.

**Estado actual:** se carga y valida el reporte ETY y se genera el archivo con la estructura y el formato del Detalle de pago, con los valores de 16 columnas del ETY copiados fila por fila, 5 columnas con valores fijos, VALIDACION calculada con la fórmula de Diferencia y CONTRATO con la fórmula del Detalle de pago. Las demás columnas se agregarán cuando se especifiquen.

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

Se genera el archivo de salida con la estructura y el formato del Detalle de pago (tomados de `DetallePagoEjemploFormato.xlsx`), con una fila por cada registro del reporte ETY, en el mismo orden.

### Paso 3 – Copia de los datos del ETY (TRA-402, implementado)

El prefijo «656-» se agrega a cada Comprobante no vacío (si ya lo trae, no se repite); los vacíos quedan vacíos.

Debajo de los encabezados, los valores del reporte ETY se copian fila por fila, **sin modificarlos**, según esta correspondencia:

| Reporte ETY | Detalle de pago |
| --- | --- |
| B (Identificación) | B (IDENTIFICACION) |
| C (Tercero Principal) | C (TERCERO) |
| D (FECHA DE PAGO) | D (FECHA_DE_PAGO) |
| E (VR. BRUTO) | E (VR_BRUTO) |
| F (VR. RTEFTE) | F (VR_RTEFTE) |
| G (VR. RETEIVA) | G (VR_RETEIVA) |
| H (VR. RETEICA) | H (VR_RETEICA) |
| I (VR. TASAS) | I (VR_TASAS) |
| J (Importe) | J (VR_NETO) |
| L (Asiento) | L (ASIENTO) |
| O (Comprobante) | M (COMPROBANTE), con el prefijo «656-» (`00153414` → `656-00153414`) |
| Q (Nº Sec Doc) | N (NO_SEC_DOC) |
| R (Más Info) | V (CONCEPTO) |
| U (Subfideicomiso) | Q (SUBFIDEICOMISO) |
| V (Cuenta) | S (CUENTA) |
| Y (Programa) | AA (PROGRAMA) |

IDENTIFICACION, SUBFIDEICOMISO y CUENTA se escriben como **número** (el ETY los trae como texto), para que Excel no la marque como «Número almacenado como texto»; lo que se ve no cambia. Solo se convierten los valores con únicamente dígitos y sin ceros a la izquierda; los demás (por ejemplo, con guion) se copian como texto y el log indica cuántos son.

Las fechas y los valores se copian como fecha y número; se ven con el formato de la columna destino del Detalle de pago (fecha `d/mm/aaaa` y contabilidad en pesos), no con el del ETY. Las demás columnas del Detalle de pago quedan vacías (con su formato y bordes). El log de ejecución indica cuántos registros se copiaron.

### Paso 4 – Valores fijos (TRA-405, implementado)

A todos los registros se les asignan los mismos valores que tienen todos los registros del Detalle de pago:

| Columna | Valor |
| --- | --- |
| W (FIDUCIARIA_QUE_EFECTUO_EL_PAGO) | FIDUPREVISORA |
| AB (GL) | 656 (número) |
| AC (Q_PAGOS) | 1 (texto, como en el Detalle de pago, cuya columna tiene formato de texto) |
| AE (AMORTIZACION_ANTICIPO) | 0 (se ve como «$ -» por el formato de contabilidad) |
| AF (MULTA) | 0 (se ve como «$ -») |

### Paso 5 – NOMBRE_SUBFIDEICOMISO_PAGO (TRA-407, implementado)

La columna R (NOMBRE_SUBFIDEICOMISO_PAGO) se llena según el SUBFIDEICOMISO (columna Q) de cada registro, con esta relación (`SUBTRUST_NAMES` en `config.py`):

| Subfideicomiso | Nombre |
| --- | --- |
| 1001 | REINCORPORACION |
| 1002, 2016, 2030, 2032, 2033 | PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET |
| 1003, 2045 | SUSTITUCION |
| 1004 | PRIMERA INFANCIA ICBF |
| 1005 | TEJIENDO PAZ - FUNCIONAMIENTO |
| 1006 | JUSTICIA ESPECIAL PARA LA PAZ |
| 1007 | IMPLEMENTACION |
| 1008 | AGENCIA NACIONAL DE TIERRAS |
| 1009 | SOCIEDAD DE ACTIVOS ESPECIALES - SAE |
| 2010 | HERENCIA COLOMBIA |
| 2011 | COLOMBIA SOSTENIBLE |
| 2013 | BID PRESTAMO |
| 2017 | AMBIENTE Y DESARROLLO SOSTENIBLE |
| 2018, 2022, 2025, 2026 | BID FACILIDAD |
| 2019, 2034, 2043 | AGENCIA NACIONAL DE TIERRAS (2) |
| 2020, 2036 | KFW |
| 2021 | AFD |
| 2023 | VISION AMAZONIA |
| 2024 | NIÑEZ Y ADOLESCENCIA ICBF |
| 2027 | ZONA ZEII CATATUMBO |
| 2028, 2031, 2035 | CATASTRO MULTIPROPOSITO |
| 2029 | ZONA ZEII CATATUMBO - CATASTRO |
| 2038 | AGENCIA DE DESARROLLO RURAL - ADR |
| 2039 | MINISTERIO DE AGRICULTURA Y DESARROLLO RURAL |
| 2041 | ACCIONES COMUNITARIAS Y RESTAURATIVAS -ARN |
| 2042, 2048, 2049, 2054 | SERVICIO SOCIAL PARA LA PAZ |
| 2044 | ATENCION INTEGRAL DE LAS VICTIMAS |
| 2047 | MINISTERIO DE TRABAJO |

Los nombres se escriben sin espacios al final (en el Detalle de pago el mismo nombre aparece con y sin espacio final, y Excel los tomaría como valores distintos). Si el Subfideicomiso no está en la relación o está vacío, la celda queda vacía y el log de ejecución lo indica con ✗, para completarla manualmente. No detiene el proceso.

### Paso 6 – FUENTE_DE_RECURSOS (TRA-406, implementado)

La columna AG (FUENTE_DE_RECURSOS) se llena según el SUBFIDEICOMISO (columna Q) de cada registro, con esta relación (`FUNDING_SOURCES` en `config.py`):

| Fuente | Subfideicomisos |
| --- | --- |
| PGN | 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 2010, 2011, 2013, 2017, 2019, 2024, 2031, 2041, 2042 |
| OTROS | 2016, 2018, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2032, 2033, 2034, 2035, 2036, 2038, 2039, 2043, 2044, 2045, 2047, 2048, 2049, 2054 |

Si el Subfideicomiso no está en la relación o está vacío, la celda queda vacía y el log de ejecución lo indica con ✗ (cuántos registros y qué Subfideicomisos), para completarla manualmente. No detiene el proceso.

### Paso 7 – VALIDACION (TRA-403, implementado)

La columna K (Diferencia) del ETY corresponde a K (VALIDACION). En el ETY, Diferencia es una fórmula de Excel (regla TRA-101 de la Etapa 1) y su resultado no queda guardado en el archivo mientras no se abra y guarde en Excel, así que su valor no se puede copiar. VALIDACION se escribe en cada fila con la misma fórmula sobre las columnas copiadas: `=E2-F2-G2-H2-I2-J2` (VR_BRUTO − VR_RTEFTE − VR_RETEIVA − VR_RETEICA − VR_TASAS − VR_NETO), igual a la del Detalle de pago. El resultado aparece al abrir el archivo en Excel, con formato de contabilidad en pesos.

### Paso 8 – CONTRATO (TRA-404, implementado)

Una vez copiado CONCEPTO, la columna O (CONTRATO) se escribe en cada fila con la misma fórmula del Detalle de pago (`DetallePagoEjemploFormato.xlsx`), sobre CONCEPTO de la misma fila. Toma el número que sigue a «CONTRATO» (`..._CONTRATO_303-2026_...` → `303`). El resultado aparece al abrir el archivo en Excel. Si CONCEPTO no contiene «CONTRATO», Excel muestra `#¡VALOR!`, igual que en el Detalle de pago.

## Archivo de salida

- Hoja `Hoja1` con las 34 columnas del Detalle de pago, en este orden: ITEM, IDENTIFICACION, TERCERO, FECHA_DE_PAGO, VR_BRUTO, VR_RTEFTE, VR_RETEIVA, VR_RETEICA, VR_TASAS, VR_NETO, VALIDACION, ASIENTO, COMPROBANTE, NO_SEC_DOC, CONTRATO, VIGENCIA, SUBFIDEICOMISO, NOMBRE_SUBFIDEICOMISO_PAGO, CUENTA, TIPO_DE_PAGO, NO_BENEFICIARIOS, CONCEPTO, FIDUCIARIA_QUE_EFECTUO_EL_PAGO, INFORME_SEMANAL, PERIODO_DE_COBRO, RECURSOS, PROGRAMA, GL, Q_PAGOS, CONTRATO_2, AMORTIZACION_ANTICIPO, MULTA, FUENTE_DE_RECURSOS, RANGO.
- Encabezados: Calibri 11 en negrita, letra blanca sobre azul (verde en VIGENCIA y PROGRAMA), centrados, con ajuste de texto y bordes finos; fila de 58 de alto.
- Anchos de columna iguales a los del Detalle de pago.
- Formatos de celda de cada columna (en las filas copiadas y en la columna completa, para los datos que se agreguen): ITEM con número entero, FECHA_DE_PAGO como fecha (`d/mm/aaaa`), los valores (VR_BRUTO a VALIDACION, AMORTIZACION_ANTICIPO y MULTA) con formato de contabilidad en pesos, Q_PAGOS como texto y las demás generales; Calibri 11 y centrados, salvo TERCERO, VR_BRUTO a VR_NETO y CONCEPTO.
- Como en todas las etapas, la fila de encabezados queda inmovilizada y con filtros.
- Nombre: el del reporte ETY con `E03_procesado` cambiado por `E04_procesado` (`ETY_sept_E03_procesado.xlsx` → `ETY_sept_E04_procesado.xlsx`); el log, con `E04_log`.

La configuración de este formato está en `OUTPUT_LAYOUT` (`config.py`). El archivo de ejemplo no se guarda en el repositorio porque contiene datos reales.

## Tareas manuales

- Completar las columnas que la herramienta deja vacías e importar el archivo generado al Detalle de pago.

## Pendiente por especificar

- Cómo se llenan las demás columnas del Detalle de pago (incluidas las fórmulas de ITEM y CONTRATO_2 del ejemplo).
