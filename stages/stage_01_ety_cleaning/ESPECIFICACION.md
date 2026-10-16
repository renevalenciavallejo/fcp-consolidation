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

### Paso 3 – Convertir a moneda las columnas E a J (implementado)

| Código | Regla |
| --- | --- |
| TIP-005 | VR. BRUTO, VR. RTEFTE, VR. RETEIVA, VR. RETEICA, VR. TASAS e Importe se convierten a número y se escriben con formato de moneda (`$ #,##0.00`). Se aceptan números de Excel y textos en formato colombiano o estadounidense, con `$` y negativos. |

- Un valor que no se puede convertir queda como estaba, resaltado en rojo, y se registra como hallazgo **Error**.
- Un valor como `1,234` se interpreta con la coma decimal y genera una **Advertencia** por ambigüedad.
- Solo se registra un cambio cuando el valor visible cambia (por ejemplo, el texto `$ 1.000.000`); los valores que ya eran números no generan cambios.

### Paso 4 – Eliminar las filas de «Distribución Caja» (implementado)

| Código | Regla |
| --- | --- |
| LIM-101 | Se eliminan las filas cuya columna L (Descripción) es «Distribución Caja». La comparación no tiene en cuenta mayúsculas, tildes ni espacios sobrantes. |

- Cada fila eliminada queda en la hoja *Eliminados* del log con todos sus datos y el motivo «Descripción «Distribución Caja»».
- En los reportes de ejemplo, la columna L solo tiene «Cuentas a Pagar» y «Distribución Caja»; después de este paso quedan solo las filas de «Cuentas a Pagar».

### Paso 5 – Agregar la columna Diferencia (implementado)

| Código | Regla |
| --- | --- |
| TRA-101 | Se agrega la columna **Diferencia** a la derecha de Importe (queda en la columna K) con la fórmula de Excel `=E2-F2-G2-H2-I2-J2` en cada fila (VR. BRUTO − VR. RTEFTE − VR. RETEIVA − VR. RETEICA − VR. TASAS − Importe), con formato de moneda. |

- El objetivo es identificar los registros con un valor diferente de 0: el usuario filtra la columna en Excel. La herramienta no genera hallazgos por este paso.
- La fórmula es exacta (sin redondeo). Por la forma en que Excel guarda los decimales, algunos registros que cuadran al centavo pueden mostrar un residuo mínimo (por ejemplo, 0,0000000001) y aparecer como diferentes de 0 al filtrar.
- La columna queda registrada en la hoja *Resumen* del log («Columnas agregadas»), no celda por celda.
- Desde este paso, las columnas que estaban de la K en adelante (Asiento … Programa) se corren una posición a la derecha.

### Paso 6 – Identificar comprobantes repetidos y ordenar (implementado)

| Código | Regla |
| --- | --- |
| VAL-101 | Cada registro cuyo **Comprobante** (columna O del archivo de salida) se repite en otro registro se señala como **Advertencia**: la celda queda resaltada en amarillo y el registro aparece en la hoja *Hallazgos* («Comprobante repetido en N registros», acción sugerida «Revisar si el registro está duplicado»). |
| TRA-102 | Los registros se ordenan por Comprobante para que los repetidos queden juntos. El orden es estable (dentro del mismo comprobante se conserva el orden original) y los vacíos irían al final. |

- No se elimina ningún registro: el usuario decide si es un duplicado real.
- Se cuentan solo los registros que siguen en el archivo: las filas de «Distribución Caja» y los duplicados del paso 7 ya se eliminaron. Por eso la revisión VAL-101 se ejecuta **después** del paso 7 (el ordenamiento TRA-102 va antes).
- El ordenamiento queda en la hoja *Resumen* del log («Transformaciones»). La columna *Fila origen* de Hallazgos, Cambios y Eliminados sigue indicando la fila del reporte original.
- En los reportes de ejemplo, antes del paso 7 había 17 comprobantes repetidos (38 registros) y 18 (36 registros); después del paso 7 quedan resaltados 22 registros en cada uno.

### Paso 7 – Eliminación de registros duplicados (implementado)

**Alcance:** la única modificación es eliminar filas completas. No se ordena, mueve ni modifica nada más; las filas que se conservan mantienen su posición. La agrupación es solo lógica, en memoria (no se usan agrupaciones, esquemas ni subtotales de Excel).

**Registros que se evalúan:** solo los que tienen **Diferencia 0**. Como la columna Diferencia es una fórmula, la herramienta hace la misma resta en memoria (VR. BRUTO − VR. RTEFTE − VR. RETEIVA − VR. RETEICA − VR. TASAS − Importe) y la compara con 0 **redondeada al centavo**: la resta exacta puede dejar residuos mínimos (por ejemplo 0,0000000019) que Excel muestra como 0. Las demás filas se conservan y no participan.

**Grupos:** registros evaluados con el mismo **Comprobante**, estén o no contiguos. Se comparan todas las columnas del reporte (Diferencia no, porque se deriva de las demás); dos celdas vacías se consideran iguales.

| Caso | Condición | Acción | Código |
| --- | --- | --- | --- |
| 2.1 | Todas las filas del grupo son idénticas, sin tener en cuenta FECHA DE PAGO (D), Asiento (L), LNP (N) ni Nº Sec Doc (Q) | Conservar la primera, eliminar las demás | DUP-101 |
| 2.2 | Solo difieren en Dpto (S) y/o Cd Fnd (T); el resto es igual, sin tener en cuenta FECHA DE PAGO (D), Asiento (L), LNP (N) ni Nº Sec Doc (Q) | Conservar la primera, eliminar las demás | DUP-102 |
| 2.3 | Difieren en al menos una de Subfideicomiso (U), Cuenta (V) o Programa (Y) | No eliminar ninguna | — |
| 2.4 | Difieren en cualquier otra columna | No eliminar ninguna | — |

- FECHA DE PAGO (D), Asiento (L), LNP (N) y Nº Sec Doc (Q) no se comparan: una diferencia en esas columnas no lleva el grupo al caso 2.4. La fila que se conserva mantiene sus propios valores en esas columnas (no se modifican ni se combinan con los de las eliminadas).
- Si un grupo cumple 2.2 y 2.3 a la vez, prevalece 2.3, aunque las demás diferencias estén solo en D, L, N, Q, S o T.
- «La primera» es la fila del grupo que está más arriba en el **archivo original** (menor fila de origen), aunque el paso 6 haya ordenado la tabla.
- Un grupo con una sola fila no se modifica.
- Cada fila eliminada queda en *Eliminados* con el motivo «Duplicado de la fila N (Comprobante X, caso 2.1/2.2)». En el log de ejecución se listan además los comprobantes de los grupos conservados por los casos 2.3 y 2.4.
- En los reportes de ejemplo se eliminan 9 y 7 filas (todas por el caso 2.2). Los grupos 2.4 que quedan difieren en Proy o Producto (primer reporte) y en FECHA DE PAGO y Nº Sec Doc (segundo reporte).

### Pasos siguientes (por especificar)

- Limpieza de textos, conversión de tipos, duplicados, validaciones y transformaciones.
- Tipos de cada columna confirmados en `config.py` (códigos como texto, valores como número, fecha de pago como fecha); se aplicarán en la conversión de tipos.

## Archivo de salida

Los registros del reporte con los encabezados en la fila 1 (sin las filas de título) y las columnas E a J con formato de moneda, sin las filas de «Distribución Caja» con la columna Diferencia en la K ordenados por Comprobante (columna O) y sin los duplicados del paso 7.

## Tareas manuales

Por definir.
