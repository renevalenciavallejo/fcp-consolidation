# Historial de cambios

Formato: `MAYOR.MENOR.PARCHE`. La versión se define en `pyproject.toml`.

## Sin publicar

- Etapa 3: el AP Voucher se lee con python-calamine (nueva dependencia y opción de entrada `fast_read`). Con el archivo real (21.000 registros), la validación al cargarlo pasa de unos 17 s a 1,6 s. Las demás entradas se siguen leyendo con openpyxl.
- Procesar es mucho más rápido con archivos grandes: el registro completo de cada acción (hoja Acciones) se arma solo cuando se necesita, en lugar de prepararlo de antemano para todos los registros leídos. Con el AP Voucher real, Procesar en la Etapa 3 pasa de unos 38 s a 1,8 s.
- Mientras se valida la estructura de un archivo cargado aparece un mensaje de espera debajo de su campo, para que la pantalla no parezca congelada con archivos grandes como el AP Voucher.
- Etapas 1 y 3: el reporte ETY se valida en su estructura apenas se carga, como en la Etapa 2. Si tiene errores, aparecen debajo de su campo y deshabilitan Procesar; lo que se hizo queda en las pestañas «Log de ejecución» y «Acciones realizadas».
- Etapa 3: el AP Voucher se valida en su estructura apenas se carga (si tiene errores, aparecen debajo de su campo y deshabilitan Procesar). Los comprobantes cerrados y cancelados se buscan solo al procesar y, al terminar, una notificación de información los lista e indica el color de cada caso. Nueva opción de etapa `RESULT_NOTICE`.
- Etapa 3: se lee el AP Voucher (encabezados en la fila 20; las filas 1 a 19 de título quedan en Acciones; columnas obligatorias Comprobante, Estado Cierre y Acción, las demás se aceptan). Se señalan como Advertencia los registros del reporte ETY cuyo comprobante está en el AP Voucher con Estado Cierre «Cerrado» (regla VAL-301, resaltado en naranja claro) o con Acción «Cancelado» (regla VAL-302, resaltado en gris claro). El log de ejecución lista los comprobantes encontrados y Acciones indica las filas del AP Voucher. No detiene el procesamiento; el reporte ETY sale sin cambios.
- Nueva opción de etapa `RULE_FILLS`: color de resaltado propio para los hallazgos de una regla, en lugar del color de su severidad.
- Etapa 3 – Cruce con el AP Voucher: carga y validación de la estructura del reporte ETY procesado en la Etapa 2 (25 columnas en orden, encabezados en la fila 1; advertencia si el nombre no contiene `E02_procesado`) y carga del archivo AP Voucher (por ahora solo se verifica que abra como .xlsx). Las validaciones contra el AP Voucher se agregarán a medida que se especifiquen.
- Etapa 2: la advertencia del nombre del reporte ETY aparece solo si el nombre no contiene `E01_procesado` (antes, si no terminaba en `_E01_procesado`). La opción de entrada `name_suffix` pasa a ser `name_contains`.
- El archivo descargado conserva el nombre del archivo cargado y cambia la marca de la etapa anterior por la de la etapa actual en el mismo lugar (`ETY_E01_procesado_v2` → `ETY_E02_procesado_v2`); antes, si la marca no estaba al final, se agregaba otra.
- Etapa 2: el botón Procesar y, al terminar, los de descarga y «Nuevo procesamiento» quedan justo debajo del campo del reporte ETY.
- El log en vivo del procesamiento se muestra en la pestaña «Log de ejecución» de la sección de abajo, en lugar de un bloque aparte.
- Si después de procesar se cambia algún archivo cargado (por ejemplo, se corrige el reporte ETY), los resultados dejan de mostrarse y hay que procesar de nuevo.
- Etapa 1: después de eliminar duplicados y antes de señalar los comprobantes repetidos, se eliminan los registros sin Programa cuyo Más Info contiene «REN-RENDIMIENTOS», «Pago de ReteICA» o «rendimientos bancarios» (regla LIM-103). Cada uno queda en la hoja Acciones del log.
- Etapa 2: se identifican los comprobantes del reporte ETY que no están en el informe de pago de su fecha (regla VAL-203). Al cargar el informe, la notificación se pone roja y lista cada comprobante con su VR. BRUTO (hasta 20); al procesar, cada uno queda como Error en su registro del ETY (resaltado en la salida y en Acciones). No detiene el procesamiento.
- Etapa 2: los informes de pago se conservan por fecha. Si se corrige el reporte ETY y se vuelve a cargar (o se carga otro), las fechas que ya tenían informe lo reutilizan y se vuelven a validar contra el nuevo ETY, sin cargarlos de nuevo; las fechas nuevas piden archivo. Cada informe se muestra con un botón «Quitar» para reemplazarlo. «Nuevo procesamiento» los borra.
- Etapa 2: el total de Impt Bruto de cada informe de pago se compara con el total de VR. BRUTO del reporte ETY de la misma FECHA DE PAGO (regla VAL-202). Al cargar el informe, la sección debajo de su campo queda verde si son iguales y roja si no (con la diferencia resaltada y solo los dos totales); al procesar, la diferencia queda en el log. No detiene el procesamiento.
- Etapa 2: cada informe de pago se valida y analiza apenas se carga (estructura, UN AP656, F Ejec, comprobantes repetidos y total de Impt Bruto). Debajo de su campo aparece la información calculada (registros AP656, descartados y total de Impt Bruto) o, si no pasa la validación, el error; en ese caso Procesar queda deshabilitado. Debajo de los campos de carga, las pestañas «Log de ejecución» y «Acciones realizadas» muestran todo lo que se hizo con los archivos al cargarlos (validación del ETY y análisis de cada informe); al procesar, se reemplazan por el log completo. Nueva opción de etapa `INPUT_ANALYSIS`.
- Etapa 2: en memoria, se deja un solo registro por Comprobante en cada informe de pago (regla DUP-201; los descartados quedan en Acciones) y se informa el total de Impt Bruto de cada informe y de todos (regla TRA-201). Comprobante e Impt Bruto pasan a ser columnas obligatorias de la hoja Pagos.
- Corrección: una etapa con entrada por fecha ya no falla cuando la columna de origen no tiene fechas.
- Etapa 2: si el nombre del reporte ETY no termina en `_E01_procesado`, se muestra una advertencia al cargarlo («¿Está seguro de que es el reporte ETY procesado en la Etapa 1?») y queda en el log de ejecución. No detiene el procesamiento. Nueva opción de entrada `name_suffix`.
- Etapa 2: de cada informe de pago de Tesorería se lee la hoja Pagos (columnas obligatorias F Ejec y UN; las demás se aceptan), se toman solo los registros con UN AP656 (regla LIM-201) y se verifica que su F Ejec sea la fecha del campo donde se cargó el informe; si no coincide, se detiene sin generar resultados e indica el informe, las fechas y las filas (regla VAL-201).
- Con `allow_extra_columns`, las columnas no declaradas pueden tener encabezados repetidos (se conserva la primera).
- Los registros de una entrada por fecha llevan la columna interna `_input_date` con la fecha de su archivo.
- Etapa 2: al cargar el reporte ETY se valida su estructura y aparece un campo para cargar el informe de pago de Tesorería de cada fecha distinta de FECHA DE PAGO (las vacías se ignoran). Todos son obligatorios; por ahora solo se verifica que abran como .xlsx.
- Entradas por fecha (`per_date` en `INPUTS`): un archivo por cada fecha distinta de una columna de otra entrada. `columns: None` indica una estructura todavía sin especificar. En la línea de comandos, cada archivo va con su fecha: `aaaa-mm-dd=ruta`.
- El nombre de los archivos generados sale de la primera entrada de la etapa cuando esta tiene un solo archivo, aunque se carguen otros archivos de apoyo.

- La etapa se elige en la barra lateral con botones de opción, todas a la vista, en lugar de una lista desplegable.
- Etapa 2 – Conciliación de pagos: carga y validación de la estructura del archivo procesado en la Etapa 1 (25 columnas en orden, encabezados en la fila 1). Las reglas de conciliación se agregarán a medida que se especifiquen.
- El nombre de los archivos generados ya no crece cuando el archivo de entrada trae el número de copia (`_E01_procesado_1` o `_E01_procesado (1)`).
- El log queda con tres hojas: Ejecución, Acciones (la misma tabla «Acciones realizadas» de la interfaz) y Reglas. Se quitan Resumen, Hallazgos, Cambios y Eliminados, cuyo contenido ya está en Acciones.
- El usuario puede consultar las reglas que aplica la etapa, en orden y con su código: en la interfaz (sección plegable «Reglas que aplica esta etapa») y en la nueva hoja «Reglas» del log. Cada etapa declara el orden en `APPLIED_RULES`.
- Las reglas de estructura (EST) se describen como lo que se valida.
- Etapa 1: la descripción y la etiqueta de carga ya no incluyen «(Todos Pagos X Comprobante)»; la descripción enumera las reglas aplicadas.
- Etapa 1, paso 7: Producto (X) se suma a Dpto y Cd Fnd como diferencia aceptada en el caso 2.2.
- Etapa 1: antes de buscar duplicados se eliminan los registros con Diferencia 0 de un Comprobante cuando VR. BRUTO es 0 (o está vacío) en todos ellos (regla LIM-102).
- El archivo procesado conserva la apariencia del archivo original: nombre de la hoja (antes siempre «Datos»), estilo de los encabezados, fuente y formato de cada columna y anchos. Las columnas nuevas toman el estilo de la columna a su izquierda; los formatos de moneda, fórmulas y fechas que exigen las reglas se mantienen.
- Etapa 1 – Limpieza del reporte ETY: validación de la estructura del reporte de pagos (primera hoja, encabezados en la fila 4, 24 columnas en orden).
- Opciones de entrada `sheet: None` (primera hoja, sin validar el nombre) y `check_column_order` (regla EST-008).
- Si los encabezados de un archivo están en otra fila, el mensaje de error indica en cuál.
- Tipo de columna `currency` (moneda, regla TIP-005): se convierte como número y se escribe con formato de moneda.
- Etapa 1: las columnas E a J (VR. BRUTO a Importe) se convierten a moneda.
- Etapa 1: se eliminan las filas con Descripción «Distribución Caja» (regla LIM-101), registradas en Eliminados.
- Función `comparable_text` para comparar textos sin tener en cuenta mayúsculas, tildes ni espacios sobrantes.
- Etapa 1: columna Diferencia a la derecha de Importe con la fórmula `=E-F-G-H-I-J` de Excel (regla TRA-101).
- Soporte de fórmulas de Excel en el archivo de salida (`ExcelFormula`), con referencias por nombre de columna.
- Registro de columnas calculadas en el log (`AuditLog.column_added`, sección «Columnas agregadas» del Resumen).
- Etapa 1: los registros con Comprobante repetido se señalan como Advertencia (VAL-101) y la tabla se ordena por Comprobante (TRA-102).
- Funciones `flag_repeated_values` y `sort_rows`, y registro de transformaciones de tabla en el log (`AuditLog.transformation`).
- Las filas de título anteriores a los encabezados (filas 1 a 3 del reporte ETY) quedan registradas en la hoja Eliminados (regla LIM-003) y se informan aparte en el resumen.
- La interfaz muestra un log de ejecución en vivo (cada paso y su resultado: archivos verificados, estructura validada, filas de título eliminadas, reglas de la etapa) en lugar de las métricas de resultados. Si el proceso se detiene, el log indica en qué paso.
- Nueva hoja «Ejecución» en el log de Excel con los mismos pasos. La CLI imprime el mismo log en lugar del resumen de conteos.
- Las pestañas Hallazgos, Cambios y Eliminados de la interfaz se reemplazan por una sola tabla, «Acciones realizadas», en el orden en que ocurrió cada acción, con el paso, la acción realizada y todas las columnas del registro. La columna Archivo solo aparece cuando se procesan varios archivos. También queda en la nueva hoja «Acciones» del log (las hojas Hallazgos, Cambios y Eliminados se conservan).
- Los archivos generados conservan el nombre del archivo original y agregan al final `_E01_procesado` o `_E01_log`, sin fecha (antes `E01_ety_cleaning_procesado_<fecha>`). Si ya existe un archivo con ese nombre en `output/`, se agrega `_1`, `_2`, …
- Etapa 1, paso 7: eliminación de duplicados entre registros con Diferencia 0 (al centavo) y el mismo Comprobante, según los casos 2.1 a 2.4 (reglas DUP-101 y DUP-102). La revisión de comprobantes repetidos (VAL-101) pasa a ejecutarse después, para marcar solo los que siguen repetidos.
- Etapa 1, paso 7: los casos 2.1 y 2.2 no comparan FECHA DE PAGO (D), Asiento (L), LNP (N) ni Nº Sec Doc (Q); una diferencia solo en esas columnas ya no deja el grupo en el caso 2.4.
- `AuditLog.step_summary()` (antes privado) para agregar detalle a un paso sin perder su resumen automático.
- `AuditLog.step`, `note` y `finish_step` para declarar los pasos; el resultado de cada paso se calcula a partir de lo registrado.

## 0.1.0 – Arquitectura base

- Ejecutor con el flujo estándar de una etapa: verificación de entradas, lectura, validación estricta de estructura, procesamiento y construcción de resultados.
- Lectura de Excel con columnas internas de origen (archivo y fila) y validación de hoja, encabezados y columnas.
- Registro de auditoría (`AuditLog`) con cambios, hallazgos y eliminaciones, individuales y en bloque.
- Funciones comunes de limpieza y conversión: textos, números (formato colombiano y estadounidense), fechas (día/mes), códigos y duplicados.
- Archivo de salida con formato estándar y resaltado de hallazgos; log en Excel con hojas Resumen, Hallazgos, Cambios y Eliminados.
- Interfaz Streamlit, línea de comandos y scripts de inicio para Windows y macOS.
- Pruebas unitarias y estructura para pruebas con casos históricos.
- Aún no hay etapas registradas.
