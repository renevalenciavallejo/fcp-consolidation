# Herramienta de consolidación FCP

Herramienta que automatiza parte del proceso de consolidación del informe de ejecución presupuestal y financiera del FCP. Procesa, por etapas, los archivos de Excel del proceso; por ahora cubre las tres primeras etapas (ver [Qué hace la herramienta](#qué-hace-la-herramienta)).

En cada etapa usted carga los archivos y la herramienta:

1. Revisa que tengan la estructura esperada.
2. Aplica automáticamente las tareas definidas para esa etapa (limpieza, eliminación de duplicados y validaciones, incluido el cruce con otros reportes, como los informes de Tesorería o el AP Voucher).
3. Le entrega un **archivo procesado** y un **archivo de log** con todos los cambios y hallazgos, para que haga las revisiones y correcciones manuales antes de continuar con la siguiente etapa.

Sus archivos originales **nunca se modifican**. Todo se ejecuta en su equipo: no se envía información a internet.

---

## Qué hace la herramienta

El proceso de consolidación tiene más etapas y pasos de los que hoy cubre la herramienta. Por ahora, la herramienta automatiza las **tres primeras etapas**; las demás se siguen haciendo manualmente y se irán agregando a medida que se definan sus reglas. Dentro de cada etapa, la herramienta aplica los pasos que ya están definidos; las tareas que aún no están automatizadas siguen a cargo del usuario.

Las etapas se hacen en orden. El archivo procesado de una etapa es el que se carga en la siguiente.

| Etapa | Archivos que se cargan | Resultado |
| --- | --- | --- |
| 1. Limpieza del reporte ETY | Reporte ETY de pagos | Reporte limpio, sin duplicados y con la columna Diferencia (`..._E01_procesado.xlsx`) |
| 2. Conciliación de pagos | Reporte de la Etapa 1 y un informe de pago de Tesorería por cada fecha de pago | Reporte con los comprobantes que no están en Tesorería señalados (`..._E02_procesado.xlsx`) |
| 3. Cruce con el AP Voucher | Reporte de la Etapa 2 y el AP Voucher | Reporte con los comprobantes cerrados o cancelados señalados (`..._E03_procesado.xlsx`) |

En todas las etapas, lo primero es revisar la estructura de cada archivo (hoja, encabezados, columnas y su orden). Si algo no corresponde, la herramienta se detiene sin generar resultados y explica qué falta y dónde. Cada etapa también guarda un **log** en Excel con todo lo que se hizo.

### Etapa 1 – Limpieza del reporte ETY

Se carga **un** reporte ETY de pagos (24 columnas, encabezados en la fila 4). La herramienta:

1. Quita las tres filas de título del reporte.
2. Convierte a moneda VR. BRUTO, VR. RTEFTE, VR. RETEIVA, VR. RETEICA, VR. TASAS e Importe.
3. Elimina las filas de «Distribución Caja».
4. Agrega la columna **Diferencia** (VR. BRUTO menos retenciones, tasas e Importe), como fórmula de Excel.
5. Ordena por Comprobante.
6. Entre los registros con Diferencia 0, elimina:
   - los comprobantes que tienen VR. BRUTO en 0 en todos sus registros;
   - los duplicados del mismo Comprobante que son iguales o que solo difieren en Dpto, Cd Fnd o Producto (se conserva el primero). Si difieren en Subfideicomiso, Cuenta, Programa u otra columna, se conservan todos.
7. Elimina los registros sin Programa cuyo Más Info contiene «REN-RENDIMIENTOS», «Pago de ReteICA» o «rendimientos bancarios».
8. Señala en amarillo los comprobantes que siguen repetidos, para revisarlos.

### Etapa 2 – Conciliación de pagos

Se carga el reporte procesado en la Etapa 1. Al cargarlo, aparece un campo por cada fecha de pago del reporte (columna FECHA DE PAGO) para cargar el **informe de pago de Tesorería** de esa fecha. Todos son obligatorios.

Cada informe se revisa apenas se carga, y debajo de su campo aparece el resultado:

1. Se usan solo los pagos de la hoja Pagos con UN **AP656**.
2. Se verifica que su F Ejec sea la fecha del campo donde se cargó. Si no lo es, casi siempre es porque el informe se cargó en el campo de otra fecha, y no se puede procesar.
3. Si un Comprobante se repite en el informe, se cuenta una sola vez.
4. Se calcula el total de Impt Bruto y se compara con el total de VR. BRUTO del reporte ETY de esa fecha. Si son iguales, el resultado aparece en **verde**; si no, en **rojo**, con la diferencia.
5. Se buscan los comprobantes del reporte ETY de esa fecha que no están en el informe. Si falta alguno, el resultado aparece en rojo y los lista.

Una diferencia en los totales o un comprobante que falta no impiden procesar. Al procesar, cada comprobante que falta queda señalado como Error (en rojo) en el archivo procesado. Los informes de Tesorería no se modifican ni hacen parte del archivo procesado.

Si corrige el reporte ETY y lo vuelve a cargar, los informes de las fechas que siguen en el reporte se conservan y se revisan de nuevo, sin cargarlos otra vez.

### Etapa 3 – Cruce con el AP Voucher

Se cargan el reporte procesado en la Etapa 2 y el **AP Voucher** (reporte «Información Revisión Voucher»). Al presionar Procesar, la herramienta busca en el reporte ETY los comprobantes que en el AP Voucher están:

- **Cerrados** (Estado Cierre «Cerrado»): se resaltan en **naranja claro**.
- **Cancelados** (Acción «Cancelado»): se resaltan en **gris claro**.

Al terminar, una notificación lista los comprobantes encontrados de cada caso. El reporte ETY no cambia: solo se resaltan esos comprobantes, para revisarlos manualmente. El AP Voucher no se modifica.

---

## Instalación (solo la primera vez)

La herramienta usa un programa llamado **uv**, que se encarga de instalar todo lo demás (Python y las librerías). Solo hay que instalarlo una vez.

### Windows

1. Abra el menú Inicio, escriba **PowerShell** y ábralo.
2. Copie y pegue este comando y presione Enter:

   ```
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. Cuando termine, cierre la ventana de PowerShell.

### macOS

1. Abra la aplicación **Terminal** (búsquela con Cmd + Espacio).
2. Copie y pegue este comando y presione Enter:

   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Cuando termine, cierre la ventana de Terminal.

---

## Uso

1. Abra la carpeta de la herramienta.
2. Haga doble clic en:
   - **Windows:** `start_windows.bat`
   - **macOS:** `start_mac.command` (la primera vez, si macOS lo bloquea: clic derecho > **Abrir** > **Abrir**).
3. La primera vez tarda unos minutos mientras se instalan los componentes. Luego se abre la herramienta en su navegador.
4. En la barra lateral, elija la **etapa**.
5. Cargue los archivos que pide la etapa y presione **Procesar**.
6. Revise el log de ejecución y las acciones realizadas, y descargue el **archivo procesado** y el **log**.
7. Haga las correcciones manuales que indica el log y continúe con la siguiente etapa.

Para cerrar la herramienta, cierre la ventana negra (consola) que se abrió al iniciarla.

### Dónde quedan los archivos

Además de la descarga, la herramienta guarda una copia de cada resultado en la carpeta **`output`** dentro de la carpeta de la herramienta. Nunca reemplaza un archivo anterior.

### Cómo leer el log

Mientras procesa, la herramienta muestra en pantalla cada paso que va haciendo y su resultado (por ejemplo, «Eliminando las filas de título del reporte → 3 filas eliminadas: filas 1, 2 y 3»). Si el proceso se detiene, ahí se ve en qué paso y por qué.

Al terminar, los resultados se organizan en dos pestañas: **Log de ejecución** (los pasos) y **Acciones realizadas**: todo lo que la herramienta hizo, una fila por acción (fila eliminada, valor modificado, hallazgo, columna agregada…), en el mismo orden en que se hizo.

El log es un archivo de Excel con tres hojas:

- **Ejecución:** los mismos pasos que se vieron en pantalla, con su resultado.
- **Acciones:** la misma tabla de acciones realizadas que se vio en pantalla: cada registro eliminado y su motivo, cada valor modificado, cada hallazgo y cada columna agregada. Los hallazgos de severidad **Error** deben corregirse antes de la siguiente etapa; las **Advertencias** deben revisarse.
- **Reglas:** las reglas que aplica la etapa, en orden, con el código que aparece en la hoja Acciones.

La columna **Fila** indica la fila en su archivo original, para que pueda ubicarla fácilmente en Excel.

En el archivo procesado, las celdas con hallazgos quedan resaltadas: **rojo claro** para los errores, **amarillo claro** para las advertencias y, en la Etapa 3, **naranja claro** (comprobantes cerrados) y **gris claro** (comprobantes cancelados).

### Si algo sale mal

- Si la herramienta indica que un archivo no tiene la estructura esperada, el mensaje dice qué archivo y qué falta. Corríjalo y vuelva a cargarlo.
- Si aparece un "error inesperado", envíe el archivo `errores.log` (está en la carpeta de la herramienta) a la persona que mantiene la herramienta.

---

## Para quien mantiene la herramienta

Ver `CLAUDE.md` (lineamientos de desarrollo). Comandos principales:

```
uv sync                       # Instalar el entorno
uv run streamlit run app.py   # Abrir la interfaz
uv run pytest                 # Ejecutar las pruebas
```
