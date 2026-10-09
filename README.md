# Herramienta de consolidación FCP

Herramienta que procesa, paso a paso, los archivos de Excel de la consolidación del informe de ejecución presupuestal y financiera del FCP.

En cada etapa usted carga los archivos y la herramienta:

1. Revisa que tengan la estructura esperada.
2. Aplica automáticamente la limpieza y las validaciones de esa etapa.
3. Le entrega un **archivo procesado** y un **archivo de log** con todos los cambios y hallazgos.

Sus archivos originales **nunca se modifican**. Todo se ejecuta en su equipo: no se envía información a internet.

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
6. Revise el resumen y los hallazgos, y descargue el **archivo procesado** y el **log**.
7. Haga las correcciones manuales que indica el log y continúe con la siguiente etapa.

Para cerrar la herramienta, cierre la ventana negra (consola) que se abrió al iniciarla.

### Dónde quedan los archivos

Además de la descarga, la herramienta guarda una copia de cada resultado en la carpeta **`output`** dentro de la carpeta de la herramienta. Nunca reemplaza un archivo anterior.

### Cómo leer el log

El log es un archivo de Excel con cuatro hojas:

- **Resumen:** datos generales del procesamiento (archivos, cantidades, hallazgos).
- **Hallazgos:** problemas encontrados. Los de severidad **Error** deben corregirse antes de la siguiente etapa; las **Advertencias** deben revisarse.
- **Cambios:** cada celda que la herramienta modificó, con el valor anterior y el nuevo.
- **Eliminados:** cada registro que se quitó (filas vacías, duplicados, etc.) y el motivo.

La columna **Fila origen** indica la fila en su archivo original, para que pueda ubicarla fácilmente en Excel.

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
