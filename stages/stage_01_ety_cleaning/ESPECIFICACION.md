# Etapa 1 – Limpieza del reporte ETY

## Archivo de entrada

| Elemento | Valor esperado |
| --- | --- |
| Reporte | ETY de pagos, «Todos Pagos X Comprobante» (por ejemplo `ETY_CAM_PAGOS_3_AP656-*.xlsx`) |
| Cantidad | Un archivo por procesamiento |
| Hoja | La primera hoja del archivo (el sistema la exporta como `sheet1`; el nombre no se valida) |
| Filas 1 a 3 | Título, cantidad de registros y rango de fechas («De Fecha = …», «A Fecha = …») |
| Fila de encabezados | 4 |
| Datos | Desde la fila 5 |

Columnas obligatorias (24), exactamente en este orden:

Beneficiario Pago, Identificación, Tercero Principal, FECHA DE PAGO, VR. BRUTO, VR. RTEFTE,
VR. RETEIVA, VR. RETEICA, VR. TASAS, Importe, Asiento, Descripción, LNP, Comprobante,
Documento, Nº Sec Doc, Más Info, Dpto, Cd Fnd, Subfideicomiso, Cuenta, Proy, Producto, Programa.

## Reglas

### Paso 1 – Validación de estructura (implementado)

Si el archivo no cumple, el procesamiento se detiene sin generar resultados y se explica qué falla.

| Código | Validación |
| --- | --- |
| EST-001 | El archivo se puede abrir como Excel (.xlsx) |
| EST-003 | Están las 24 columnas en la fila 4 (si los encabezados están en otra fila, se indica en cuál) |
| EST-004 | No hay columnas adicionales |
| EST-005 | No hay encabezados repetidos |
| EST-006 | No hay columnas con datos sin encabezado |
| EST-007 | Se cargó exactamente un archivo |
| EST-008 | Las columnas están en el orden del reporte (se indica la primera posición distinta) |

Los encabezados se comparan sin tener en cuenta espacios sobrantes.

### Paso 2 – Eliminar las filas de título (implementado)

| Código | Regla |
| --- | --- |
| LIM-003 | Se eliminan las filas 1, 2 y 3 (título «Todos Pagos X Comprobante», cantidad de registros y rango de fechas). Quedan en la hoja *Eliminados* del log, con su contenido en la columna donde estaba cada valor. No cuentan como registros eliminados. |

### Pasos siguientes (por especificar)

- Limpieza de textos, conversión de tipos, duplicados, validaciones y transformaciones.
- Tipos de cada columna confirmados en `config.py` (códigos como texto, valores como número, fecha de pago como fecha); se aplicarán en la conversión de tipos.

## Archivo de salida

Los registros del reporte con los encabezados en la fila 1 (sin las filas de título).

## Tareas manuales

Por definir.
