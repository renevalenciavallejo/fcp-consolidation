# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Lineamientos – Herramienta de procesamiento de archivos Excel (FCP)

> Documento de referencia para el desarrollo de la herramienta. Complementa `ContextoProyectoFCP.md` (documento del proyecto, no está en el repositorio).

## 0. Estado actual y comandos

- La arquitectura base está construida (`core/`, `app.py`, `cli.py`, pruebas). No inventar etapas ni reglas; esperar la `ESPECIFICACION.md` de cada una.
- Etapas registradas: `stage_01_ety_cleaning` (Limpieza del reporte ETY). Un reporte por procesamiento, cualquier nombre de hoja, orden de columnas obligatorio. Implementados: validación de estructura y eliminación de las filas de título (1 a 3); `process()` devuelve los datos sin cambios hasta que se especifiquen las reglas de limpieza.
- `tests/stage_99_fake/` es una etapa ficticia que **solo** sirve para probar el núcleo. No registrarla en `STAGES`.

```bash
uv sync                                   # Instalar/actualizar el entorno
uv run streamlit run app.py               # Abrir la interfaz
uv run pytest                             # Todas las pruebas
uv run pytest tests/test_cleaning.py      # Un archivo
uv run pytest tests/test_cleaning.py::test_parse_number   # Una prueba
uv run python cli.py --stage 1 --input area_reports "ruta/a.xlsx" "ruta/b.xlsx"
```

## 1. Propósito

Aplicación local e independiente, con interfaz web en Streamlit, que procesa por etapas los archivos de Excel del proceso de consolidación del informe de ejecución presupuestal y financiera del FCP.

En cada ciclo el usuario elige una etapa y carga uno o varios archivos (según la etapa). La herramienta:

1. Valida que cada archivo tenga la estructura esperada.
2. Aplica automáticamente las tareas estandarizadas (limpieza, duplicados, formatos, validaciones, consolidación, transformaciones).
3. Genera un **archivo nuevo** con los cambios y un **archivo de log** con todos los cambios y hallazgos.
4. Nunca modifica los archivos originales.

El usuario revisa el log, hace las tareas manuales y carga el resultado en la siguiente etapa.

## 2. Principios

- **Incremental:** se automatiza una etapa a la vez. Cada etapa debe funcionar por sí sola.
- **Trazabilidad total:** todo cambio, eliminación o hallazgo queda en el log. Si no está en el log, no debió pasar.
- **Originales intactos:** los archivos de entrada solo se leen.
- **Simplicidad:** el mantenedor tiene conocimientos básicos de Python. Se prefiere código obvio sobre código ingenioso.
- **Independencia:** sin Power BI, sin bases de datos, sin servicios en la nube. Todo se ejecuta localmente en el equipo del usuario.
- **Multiplataforma:** debe funcionar igual en Windows y macOS.

## 3. Tecnologías

| Uso                                       | Tecnología                         |
| ----------------------------------------- | ---------------------------------- |
| Lenguaje                                  | Python 3.14                        |
| Gestión de Python, entorno y dependencias | uv (`pyproject.toml` + `uv.lock`)  |
| Interfaz de usuario                       | Streamlit (ejecución local)        |
| Manejo de datos                           | pandas                             |
| Lectura/escritura Excel                   | openpyxl                           |
| Pruebas                                   | pytest (dependencia de desarrollo) |
| Control de versiones                      | git                                |

Reglas:

- **No usar pip, `requirements.txt` ni `venv` manual.** Todo se gestiona con uv (`uv sync`, `uv add <paquete>`, `uv add --dev <paquete>`, `uv run ...`).
- La versión de Python se fija en `.python-version` (3.14). uv la instala automáticamente si el equipo no la tiene.
- El proyecto es una aplicación, no un paquete (`[tool.uv] package = false`). Los módulos se importan desde la raíz (`core`, `stages`); pytest lo permite con `pythonpath = ["."]`.
- `uv.lock` se versiona en git para que todos los equipos usen exactamente las mismas versiones.
- No agregar dependencias nuevas sin justificarlo y consultarlo antes.
- Usar `pathlib` para rutas. Prohibido concatenar rutas como texto.
- Usar siempre codificación UTF-8.
- No usar comandos ni librerías específicas de un sistema operativo.
- Formato soportado en v1: `.xlsx`.

## 4. Arquitectura

Tres capas, con dependencias en un solo sentido: `interfaces → core/stages`.

1. **Interfaces**
   - `app.py` (Streamlit): interfaz principal del usuario.
   - `cli.py` (línea de comandos, no interactiva): para pruebas y uso avanzado.
   - Ninguna interfaz contiene lógica de negocio. Solo reciben archivos, llaman al ejecutor y muestran o entregan resultados.
2. **Ejecutor (`core/runner.py`)**: `run_stage(stage, files, progress)` orquesta el flujo estándar de cualquier etapa (sección 5) y `save_result` guarda la copia en `output/`.
3. **Etapas (`stages/stage_NN_<name>/`)**: solo contienen las reglas de negocio de esa etapa y su configuración.

**El núcleo trabaja en memoria.** El ejecutor recibe archivos (`BytesIO`, archivos cargados en Streamlit o rutas) y devuelve un `StageResult` con el archivo de salida y el log como `bytes`. Cada interfaz decide qué hacer con ellos. Los problemas de estructura se lanzan como `StageError` (con la lista `problems` en español); cualquier otra excepción es un error técnico (sección 8.4).

### 4.1 Estructura de carpetas

```
fcp-consolidation/
├── app.py / cli.py            # Interfaces
├── .streamlit/config.toml     # Configuración local de Streamlit (ver 9.2)
├── start_windows.bat / start_mac.command   # Doble clic para iniciar
├── README.md / CHANGELOG.md
├── core/
│   ├── settings.py            # Versión (leída de pyproject.toml), carpetas, colores, formatos, severidades
│   ├── rules.py               # Catálogo de reglas comunes (EST, LIM, TIP, DUP)
│   ├── stage.py               # InputSpec y lectura del contrato de una etapa
│   ├── runner.py              # Flujo estándar de una etapa
│   ├── reader.py              # Lectura de Excel y validación de estructura
│   ├── writer.py              # Archivo de salida y formato común de tablas
│   ├── audit.py               # Clase AuditLog
│   ├── log_report.py          # Excel de log y RunSummary
│   ├── cleaning.py            # Funciones reutilizables (espacios, fechas, números, códigos, duplicados)
│   └── errors.py              # Registro de errores técnicos en errores.log
├── stages/
│   ├── __init__.py            # Registro de etapas disponibles (STAGES)
│   └── stage_NN_<name>/       # __init__.py, config.py, process.py, ESPECIFICACION.md
├── output/                    # Copia local de los archivos generados (no se versiona)
└── tests/
    ├── helpers.py             # make_xlsx(): crea archivos de prueba en memoria
    ├── stage_99_fake/         # Etapa ficticia para probar el núcleo
    ├── test_cleaning.py / test_audit.py / test_reader.py / test_runner.py
    ├── test_stages.py         # Comparación contra casos históricos
    └── cases/                 # Datos reales (NO se versionan en git)
        └── stage_NN/<week>/
            ├── inputs/<id_entrada>/*.xlsx   # Una carpeta por entrada de la etapa
            └── expected.xlsx
```

### 4.2 Entradas de una etapa

Cada etapa declara en su `config.py` las entradas que necesita. Una etapa puede tener:

- Una sola entrada con un solo archivo.
- Una entrada que acepta **varios archivos con la misma estructura** (por ejemplo, un archivo por área). El lector los une en un solo `DataFrame`.
- **Varias entradas con estructuras distintas** (por ejemplo, un reporte de compromisos y un reporte de pagos).

Cada entrada define: identificador, etiqueta para el usuario, si acepta varios archivos, si es obligatoria, hoja, fila de encabezados y columnas esperadas con su tipo. Opcionales:

- `sheet: None`: usa la primera hoja sin validar su nombre (útil cuando el sistema que exporta cambia el nombre).
- `allow_extra_columns` (por defecto `False`: columnas no declaradas detienen el proceso).
- `check_column_order` (por defecto `False`): exige que las columnas estén en el orden declarado en `columns` (EST-008).

Al leer, el lector agrega a cada registro dos columnas internas:

- `_source_file`: nombre del archivo del que proviene.
- `_source_row`: número de fila real en ese archivo de Excel.

Las filas anteriores a los encabezados (títulos del reporte) no forman parte de los datos: el lector las guarda en `ReadResult.title_rows` y el ejecutor las registra en *Eliminados* con la regla común `LIM-003`, antes de llamar a `process`. Se informan aparte («Filas de título eliminadas») y no cuentan como registros eliminados.

Estas columnas permiten que el log siempre apunte al archivo y la fila que el usuario puede buscar. Se eliminan del archivo de salida. Las etapas deben conservarlas en el `DataFrame` que devuelven para que funcione el resaltado de hallazgos.

**Valores leídos:** el lector usa openpyxl y entrega cada celda tal como está guardada en Excel (texto, número o fecha nativa), sin inferencia de tipos de pandas (`DataFrame` con `dtype=object`). No se convierte todo a texto porque eso volvería ambiguos los números y fechas nativos (`1.234` o `05/03/2024`). La conversión explícita la hace `convert_columns` según el tipo declarado. Los encabezados se comparan después de limpiar espacios; las filas vacías al final de la hoja se ignoran.

### 4.3 Contrato de una etapa

Cada etapa expone en su `__init__.py`:

```python
NAME = "Etapa 1 - Consolidación de reportes de áreas"   # Texto visible para el usuario
DESCRIPTION = "Une los reportes de las áreas, limpia y valida los datos."
INPUTS = config.INPUTS
RULES = config.RULES      # Opcional: reglas propias {código: descripción}

def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    """Recibe los datos de cada entrada, ya leídos y validados, y devuelve
    los datos procesados. Todo cambio, hallazgo o eliminación se reporta en `audit`."""
```

- `inputs` tiene una llave por cada entrada declarada. Si la entrada acepta varios archivos, su `DataFrame` ya contiene todos los archivos unidos. Una entrada opcional no cargada llega como `DataFrame` vacío con sus columnas.
- La etapa **no lee ni escribe archivos** y **no interactúa con la interfaz**. Todo se reporta a través de `audit`.
- `process` se organiza como una secuencia de funciones pequeñas, una por regla, en el orden del flujo (sección 5). `tests/stage_99_fake/process.py` muestra el patrón.
- El prefijo de los archivos generados (`E01_area_reports`) sale del nombre de la carpeta; por eso debe seguir el formato `stage_NN_<name>`.

### 4.4 Registro de etapas

`stages/__init__.py` contiene la lista `STAGES` con las etapas disponibles en el orden del proceso. Agregar una etapa = crear su carpeta, importarla y añadirla a esta lista (importación explícita, sin carga dinámica). El número de etapa en la CLI es la posición en esta lista.

### 4.5 Clase `AuditLog`

Clase en `core/audit.py`. Recibe el catálogo de reglas (comunes + `RULES` de la etapa) y rechaza códigos no declarados o severidades inválidas.

- `change(source_file, source_row, column, old_value, new_value, rule)`
- `finding(source_file, source_row, column, severity, rule, description, value, suggested_action)`
- `removal(source_file, source_row, rule, reason, row_data)`

En bloque, para no escribir ciclos celda por celda en las etapas:

- `change_column(df, column, new_values, rule, changed=None)`: registra solo las celdas que cambian.
- `finding_column(df, mask, column, severity, rule, description, suggested_action)`
- `remove_rows(df, mask, rule, reason)`: registra y devuelve el `DataFrame` sin esas filas (`reason` puede ser texto o una `Series` por fila).

## 5. Flujo estándar de una etapa

El ejecutor siempre sigue este orden:

1. **Verificación de entradas:** están todas las entradas obligatorias y no hay archivos de más en las entradas de un solo archivo.
2. **Lectura:** cada archivo se lee en la hoja configurada. Se agregan `_source_file` y `_source_row`. Los archivos de una misma entrada se unen.
3. **Validación de estructura (estricta), archivo por archivo:** hoja, encabezados, columnas obligatorias, columnas sobrantes y, si se configura, orden de columnas. Si cualquier archivo falla, **se detiene sin generar resultados** y se explican todos los problemas de todos los archivos.
4. **Procesamiento de la etapa** (`process`), que internamente sigue este orden:
   1. Limpieza (espacios, caracteres invisibles, filas vacías, filas de totales).
   2. Conversión de tipos (fechas, números, códigos).
   3. Consolidación (unión o cruce de entradas), si aplica.
   4. Eliminación de duplicados.
   5. Validaciones de negocio (generan hallazgos).
   6. Transformaciones (cálculos, columnas nuevas, reestructuración).
5. **Construcción de resultados:** archivo de salida y archivo de log, en memoria. Se quitan las columnas internas del archivo de salida.
6. **Entrega:** la interfaz muestra el resumen, ofrece la descarga y guarda una copia en `output/`.

## 6. Configuración

- Por ahora vive en el código, en `config.py` de cada etapa y en `core/settings.py`.
- Los `config.py` contienen **solo datos** (constantes, listas, diccionarios). Nada de lógica.
- Constantes en MAYÚSCULAS, con un comentario en español que explique cada una.
- Cualquier valor que pueda cambiar (nombres de columnas, catálogos, umbrales, llaves de duplicados) va en configuración, nunca escrito directamente en `process.py`.
- Los nombres de columnas se escriben exactamente como aparecen en los archivos de Excel (en español), aunque el código esté en inglés.
- Diseñar pensando en que más adelante la configuración pueda leerse desde un archivo externo, sin cambiar la lógica.

Ejemplo:

```python
# stages/stage_01_area_reports/config.py

# Entradas que necesita la etapa.
INPUTS = {
    "area_reports": {
        "label": "Reportes de las áreas",   # Texto que ve el usuario
        "multiple": True,                   # Acepta varios archivos con la misma estructura
        "required": True,
        "sheet": "Ejecucion",
        "header_row": 1,                    # 1 = primera fila de la hoja
        # Columnas obligatorias y su tipo: "text", "code", "number", "date"
        "columns": {
            "Codigo Proyecto": "code",
            "Fecha Registro": "date",
            "Valor Comprometido": "number",
            "Fuente": "text",
        },
    },
}

# Columnas que, juntas, identifican un registro duplicado
DUPLICATE_KEY = ["Codigo Proyecto", "Fecha Registro", "Valor Comprometido"]

# Valores permitidos por columna
VALID_VALUES = {
    "Fuente": ["PGN", "Cooperación", "Otros"],
}

# Reglas propias de la etapa: código y descripción en español
RULES = {
    "VAL-001": "La fuente debe ser uno de los valores permitidos",
}
```

## 7. Reglas y códigos

Cada regla tiene un código único que aparece en el log, para poder rastrear qué la produjo.

- Formato: `<TIPO>-<NNN>`, por ejemplo `LIM-001`.
- Tipos: `EST` estructura, `LIM` limpieza, `TIP` conversión de tipos, `CON` consolidación, `DUP` duplicados, `VAL` validación de negocio, `TRA` transformación.
- Las reglas comunes están en `core/rules.py` (`EST-001…008` aparecen en los mensajes de error de estructura; `LIM-001…003`, `TIP-001…004` y `DUP-001` quedan en el log). Las específicas de cada etapa, en el `RULES` de su `config.py`, sin repetir códigos comunes.

## 8. Archivos generados

### 8.1 Entrega y nombres

- En Streamlit, el usuario descarga ambos archivos con botones de descarga.
- Además, se guarda automáticamente una copia en la carpeta `output/` de la aplicación.
- Nunca se sobrescribe un archivo existente (`save_result` agrega `_1`, `_2`, …).
- Nombres:
  - Salida: `E<NN>_<nombre_etapa>_procesado_<AAAAMMDD_HHMMSS>.xlsx`
  - Log: `E<NN>_<nombre_etapa>_log_<AAAAMMDD_HHMMSS>.xlsx`

### 8.2 Archivo de salida

- Contiene los datos procesados con la estructura que espera la etapa siguiente.
- Formato mínimo: encabezados en negrita, filtros activos, anchos de columna ajustados, fechas como fecha (`dd/mm/aaaa`) y valores como número con separador de miles.
- Las celdas con hallazgos se resaltan con color según severidad (Error: rojo claro, Advertencia: amarillo claro).

### 8.3 Archivo de log (Excel)

| Hoja           | Columnas                                                                                                                                                                                                                                                             |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Resumen**    | Tabla Sección / Concepto / Valor: versión de la herramienta, etapa, archivos de entrada (nombre y registros leídos de cada uno), archivo de salida, fecha y hora, duración, registros en salida, registros eliminados, celdas modificadas, hallazgos por severidad, cantidad de aplicaciones por regla |
| **Hallazgos**  | Archivo origen, fila origen, columna, severidad, código de regla, descripción, valor encontrado, acción sugerida                                                                                                                                                     |
| **Cambios**    | Archivo origen, fila origen, columna, valor anterior, valor nuevo, código de regla, descripción de la regla                                                                                                                                                          |
| **Eliminados** | Archivo origen, fila origen, código de regla, motivo, seguido de todas las columnas del registro eliminado                                                                                                                                                           |

- **Fila origen** = número de fila en el archivo de entrada (el que el usuario ve en Excel).
- Severidades: `Error` (requiere corrección manual antes de la siguiente etapa), `Advertencia` (revisar), `Información`.
- Todas las hojas con filtros activos y paneles inmovilizados en el encabezado.

### 8.4 Errores técnicos

- El usuario nunca ve un _traceback_ de Python. Ve un mensaje claro en español (`core/errors.py`).
- El detalle técnico se guarda en `errores.log`, en la carpeta de la aplicación, con fecha y hora.

## 9. Interfaces

### 9.1 Streamlit (`app.py`)

Flujo:

1. **Barra lateral:** nombre y versión de la herramienta, y selección de la etapa (en el orden del proceso).
2. **Área principal:** nombre y descripción de la etapa.
3. **Un cargador de archivos por cada entrada declarada**, con su etiqueta. Solo acepta `.xlsx` y permite varios archivos cuando la entrada lo indica.
4. **Botón "Procesar"**, deshabilitado hasta que estén cargadas todas las entradas obligatorias.
5. **Indicador de progreso** por paso.
6. **Resultados:** métricas, pestañas con tablas de Hallazgos, Cambios y Eliminados, botones de descarga y ruta de la copia en `output/`.
7. **Botón "Nuevo procesamiento"** para limpiar la pantalla.

Reglas:

- Todos los textos de la interfaz en español y en lenguaje no técnico.
- Los resultados se guardan en `st.session_state` para que descargar un archivo no vuelva a ejecutar el procesamiento.
- Los errores se muestran con `st.error` y un mensaje claro de qué hacer.
- `app.py` debe ser delgado: no contiene reglas de negocio.
- Se puede probar sin navegador con `streamlit.testing.v1.AppTest` (no admite carga de archivos; para los resultados, precargar `session_state`).

### 9.2 Configuración de Streamlit (`.streamlit/config.toml`)

Desactiva estadísticas de uso, limita el servidor a `localhost` y fija `maxUploadSize = 200` MB. La aplicación **solo se ejecuta localmente**. No se publica en Streamlit Community Cloud ni en ningún servidor.

### 9.3 Inicio para el usuario final

- `start_windows.bat` y `start_mac.command` ejecutan `uv run streamlit run app.py` desde la carpeta de la herramienta, lo que abre la herramienta en el navegador.
- El usuario solo necesita instalar uv una vez (documentado en el `README.md`).
- `start_mac.command` debe tener permisos de ejecución.

### 9.4 Línea de comandos (`cli.py`)

Solo modo no interactivo: `--stage N` y `--input <id_entrada> <archivos...>` (repetible). Guarda los resultados en `output/`, muestra un resumen en español y termina con código 0 (éxito), 1 (error de procesamiento) o 2 (argumentos inválidos).

## 10. Manejo de datos

- Convertir explícitamente con `core/cleaning.py`. No confiar en la conversión automática de pandas.
- **Textos:** quitar espacios al inicio y final, espacios dobles, espacios no separables (`\xa0`), saltos de línea y caracteres invisibles. No quitar tildes ni cambiar mayúsculas salvo que la regla lo indique. Una celda con solo espacios queda vacía.
- **Códigos:** siempre texto. Conservar ceros a la izquierda; se quita el `.0` de códigos guardados como número.
- **Números:** soportar formato colombiano (`1.234.567,89`), formato estadounidense, símbolo `$` y negativos con signo o entre paréntesis. Con un solo separador se asume uso colombiano (`1,5` = 1.5; `45.000` = 45000); `1,234` genera además una Advertencia por ambigüedad. Si un valor no se puede convertir, se registra un hallazgo Error y la celda conserva el valor original (resaltada); nunca se reemplaza silenciosamente por cero o vacío.
- **Fechas:** soportar fechas nativas de Excel, número serial de Excel, texto `dd/mm/aaaa` y `aaaa-mm-dd`. Asumir día/mes (nunca mes/día). Si es ambiguo (año de dos dígitos) o inválido, se registra un hallazgo.
- **Cambios por conversión:** solo se registran cuando el valor visible cambia (`"1.234,5"` → 1234.5), no cuando solo cambia el tipo (`"1234"` → 1234).
- **Vacíos:** distinguir vacío de cero (`core.audit.is_empty`).
- **Filas a eliminar:** filas completamente vacías y filas de totales o subtotales (según reglas de cada etapa), siempre registradas en _Eliminados_.
- **Varios archivos:** los duplicados se buscan tanto dentro de cada archivo como entre archivos (`remove_duplicates`). El motivo indica el archivo y la fila del registro original.
- **Confidencialidad:** sin envío de datos a internet, sin telemetría. Los datos reales no se suben a git.

## 11. Estilo de código

- **Código en inglés:** nombres de variables, funciones, clases, módulos, carpetas y constantes.
- **En español:** comentarios, _docstrings_, mensajes al usuario (interfaz, errores, log) y documentación (`README.md`, `ESPECIFICACION.md`, `CHANGELOG.md`).
- Los nombres de columnas de Excel se mantienen tal como vienen en los archivos (español).
- Funciones pequeñas que hagan una sola cosa, con un _docstring_ corto que explique qué hace y por qué.
- Clases solo cuando simplifiquen (`AuditLog`, `dataclasses` para estructuras de datos). Sin herencia ni patrones complejos.
- Usar _type hints_ sencillos.
- Seguir PEP 8.
- Comentarios que expliquen el **porqué**, no el qué.
- Sin "magia": nada de metaprogramación, decoradores propios ni carga dinámica innecesaria.

## 12. Pruebas

- **Unitarias** (`test_cleaning.py`, `test_audit.py`, `test_reader.py`, `test_runner.py`): datos pequeños inventados creados con `tests/helpers.make_xlsx`, incluyendo casos raros (vacíos, formatos mixtos, textos con caracteres invisibles). El flujo completo se prueba con `tests/stage_99_fake`.
- **Históricas** (`test_stages.py`): para cada etapa de `STAGES` y cada caso en `tests/cases/stage_NN/<week>/`, se procesan los archivos de `inputs/<id_entrada>/` y se compara contra `expected.xlsx`. El reporte de diferencias indica fila, columna, valor obtenido y valor esperado. Sin casos, la prueba aparece como omitida.
- Las pruebas llaman directamente al ejecutor, sin pasar por Streamlit.
- Una diferencia no es automáticamente un error de la herramienta: puede ser un error del proceso manual. Se analiza y documenta.
- Ninguna etapa se considera lista sin pasar los casos históricos disponibles.

## 13. Versionamiento y documentación

- `.gitignore` excluye `tests/cases/`, `output/`, todos los `.xlsx`, `.venv/`, `__pycache__/` y `errores.log`.
- La versión se cambia **solo** en `pyproject.toml` (`MAYOR.MENOR.PARCHE`); `core/settings.py` la lee de ahí. Aparece en la interfaz y en el log.
- `CHANGELOG.md` actualizado en cada versión.
- `README.md` con instrucciones de instalación y uso para Windows y macOS, paso a paso, para alguien sin experiencia técnica.
- Cada etapa tiene su `ESPECIFICACION.md`: archivos de entrada esperados, reglas aplicadas (con código), archivo de salida y tareas manuales que siguen siendo responsabilidad del usuario.

## 14. Cómo agregar una etapa

1. Escribir `ESPECIFICACION.md` con el usuario de negocio **antes** de programar.
2. Crear la carpeta `stages/stage_NN_<name>/` con `__init__.py` (contrato 4.3), `config.py` (incluyendo `INPUTS` y `RULES`) y `process.py`. Tomar `tests/stage_99_fake/` como modelo.
3. Registrar la etapa en `stages/__init__.py`.
4. Reunir al menos un caso histórico en `tests/cases/stage_NN/`.
5. Ejecutar pruebas y revisar diferencias.
6. Verificar la etapa en Streamlit.
7. Actualizar `CHANGELOG.md` y la versión.

## 15. Fuera de alcance en v1

- Ejecutable empaquetado (PyInstaller u otro).
- Publicación en servidores o en la nube.
- Encadenamiento automático de etapas.
- Integración con Power BI o bases de datos.
- Configuración en archivos externos.
- Formatos distintos de `.xlsx`.

## 16. Instrucciones para Claude Code

- El mantenedor tiene conocimientos básicos de Python: al proponer o hacer cambios, explicar en lenguaje sencillo qué se hizo y por qué.
- **No inventar reglas de negocio.** Si una regla no está en la `ESPECIFICACION.md` de la etapa, preguntar.
- Usar siempre uv para gestionar dependencias y ejecutar comandos.
- Consultar antes de agregar dependencias o cambiar la arquitectura.
- Respetar el contrato de etapa (sección 4.3) y el flujo estándar (sección 5).
- Toda transformación nueva debe reportarse en `AuditLog`. Si no aparece en el log, la implementación está incompleta.
- Agregar o actualizar pruebas con cada cambio.

## 17. Supuestos por confirmar

- Cada etapa genera **un solo archivo** de salida.
- Cada archivo de entrada tiene **una hoja** a procesar.
- Los archivos de entrada son `.xlsx`.
