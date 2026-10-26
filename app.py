"""Interfaz principal (Streamlit). No contiene reglas de negocio: solo recibe
archivos, llama al ejecutor y muestra o entrega los resultados.

Ejecutar con: uv run streamlit run app.py
"""

from dataclasses import dataclass
from io import BytesIO

import pandas as pd
import streamlit as st

from core.audit import AuditLog
from core.errors import UNEXPECTED_ERROR_MESSAGE, log_exception
from core.runner import (
    StageError,
    analyze_date_file,
    file_name_warnings,
    load_date_sources,
    run_stage,
    save_result,
)
from core.settings import APP_NAME, APP_VERSION, DOWNLOAD_BUTTON_COLOR, DOWNLOAD_BUTTON_HOVER_COLOR
from core.stage import applied_rules, date_label, input_specs, stage_rules
from stages import STAGES

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.set_page_config(page_title=APP_NAME, layout="wide")

# Streamlit no permite elegir el color de cada botón: los de descarga se pintan de verde
# con CSS, ubicándolos por su `key` (Streamlit agrega la clase st-key-<key>).
st.html(f"""
<style>
.st-key-download_output button, .st-key-download_log button {{
    background-color: {DOWNLOAD_BUTTON_COLOR};
    border-color: {DOWNLOAD_BUTTON_COLOR};
    color: white;
}}
.st-key-download_output button:hover, .st-key-download_log button:hover {{
    background-color: {DOWNLOAD_BUTTON_HOVER_COLOR};
    border-color: {DOWNLOAD_BUTTON_HOVER_COLOR};
    color: white;
}}
</style>
""")

# Estado que sobrevive entre recargas de la página (por ejemplo, al descargar un archivo).
st.session_state.setdefault("result", None)
st.session_state.setdefault("saved_paths", None)
st.session_state.setdefault("result_stage", None)
st.session_state.setdefault("uploader_version", 0)
# Archivos de las entradas por fecha (por ejemplo, los informes de pago), por etapa, entrada y
# fecha. Se guardan aquí y no en el cargador para conservarlos si se vuelve a cargar el ETY.
st.session_state.setdefault("saved_reports", {})


@dataclass
class SavedFile:
    """Archivo cargado en una entrada por fecha, guardado en memoria."""

    name: str
    data: bytes
    file_id: str    # Identificador de la carga, para no volver a analizar el mismo archivo


def reset() -> None:
    """Limpia los resultados y los archivos cargados para empezar de nuevo."""
    st.session_state.result = None
    st.session_state.saved_paths = None
    st.session_state.result_stage = None
    st.session_state.uploader_version += 1
    st.session_state.saved_reports = {}
    st.session_state.analysis_cache = {}


# --- Barra lateral ---------------------------------------------------------

st.sidebar.title(APP_NAME)
st.sidebar.caption(f"Versión {APP_VERSION}")

if not STAGES:
    st.info("Todavía no hay etapas disponibles en esta versión de la herramienta.")
    st.stop()

# Botones de opción (no lista desplegable): todas las etapas quedan a la vista y se elige con un clic.
stage_index = st.sidebar.radio(
    "Etapa",
    options=range(len(STAGES)),
    format_func=lambda i: STAGES[i].NAME,
    on_change=reset,
)
stage = STAGES[stage_index]

# --- Etapa y carga de archivos ---------------------------------------------

st.title(stage.NAME)
st.write(stage.DESCRIPTION)
with st.expander("Reglas que aplica esta etapa"):
    st.caption("En el orden en que se aplican. Los códigos son los mismos que aparecen en el log.")
    # Lista numerada en texto (no tabla): dentro de la sección se lee mejor sin bordes.
    st.markdown("\n".join(
        f"{number}. **{code}** · {description}"
        for number, (code, description) in enumerate(applied_rules(stage), start=1)
    ))

# Log de lo que se hace con los archivos al cargarlos (antes de Procesar): líneas del log de
# ejecución y tablas de acciones, en el orden de los campos de carga. Se arma de nuevo en cada
# ejecución de la página con los análisis guardados, y se muestra abajo, en pestañas.
load_log = {"lines": [], "actions": []}


def add_to_load_log(lines: list[str], actions: pd.DataFrame | None = None) -> None:
    load_log["lines"].extend(lines)
    if actions is not None and not actions.empty:
        load_log["actions"].append(actions)


def load_dates(source_files: list):
    """Fechas de las entradas por fecha y datos del archivo de origen (o su error de estructura).

    Se guardan en session_state por archivo cargado: Streamlit vuelve a ejecutar la página
    con cada archivo que se carga y así el reporte no se lee una y otra vez. La lectura y
    la validación del archivo quedan en el log de carga.
    """
    cache_key = (stage_index, file_ids(source_files))
    cache = st.session_state.setdefault("dates_cache", {})
    if cache_key not in cache:
        audit = AuditLog(stage_rules(stage))
        try:
            cache[cache_key] = (load_date_sources(stage, files, audit), audit.step_lines(), audit.actions_df())
        except StageError as error:
            cache[cache_key] = (error, error.steps, None)
        except Exception as error:
            # Nunca mostrar un traceback: el detalle queda en errores.log. No se guarda, para reintentar.
            log_exception(error)
            return StageError(UNEXPECTED_ERROR_MESSAGE, [])
    sources, lines, actions = cache[cache_key]
    add_to_load_log(lines, actions)
    return sources


def show_step_log(placeholder, lines: list[str]) -> None:
    """Muestra el log de ejecución como un bloque de texto, una línea por paso y resultado."""
    placeholder.code("\n".join(lines), language=None)


def show_actions(actions) -> None:
    """Tabla con todo lo que se hizo, en el orden en que ocurrió."""
    if actions.empty:
        st.write("No se hizo ningún cambio, eliminación ni hallazgo.")
        return
    count = "1 acción" if len(actions) == 1 else f"{len(actions)} acciones"
    st.caption(f"{count}, en el orden en que se hicieron.")
    # Las celdas vacías se muestran en blanco, no como "None".
    st.dataframe(actions.fillna("").astype(str), hide_index=True, width="stretch")


def file_ids(uploaded_files: list) -> tuple:
    """Identifica los archivos cargados, para guardar en session_state lo que se calculó con ellos."""
    return tuple(getattr(f, "file_id", f.name) for f in uploaded_files)


def load_analysis(spec, sources, day, uploaded):
    """Análisis del archivo de una fecha: log e información calculada (o el error que lo detuvo).

    Se guarda en session_state por archivo cargado, como las fechas: Streamlit vuelve a
    ejecutar la página con cada clic y así cada informe se analiza una sola vez. El análisis
    compara el archivo con el de origen (por ejemplo, el reporte ETY): si este cambia, se
    analiza de nuevo.
    """
    source_key = spec.per_date[0]
    cache_key = (stage_index, spec.key, day, file_ids([uploaded]), file_ids(files[source_key]))
    cache = st.session_state.setdefault("analysis_cache", {})
    if cache_key not in cache:
        try:
            cache[cache_key] = analyze_date_file(stage, spec.key, day, uploaded, sources.data[source_key])
        except StageError as error:
            cache[cache_key] = error
        except Exception as error:
            # Nunca mostrar un traceback: el detalle queda en errores.log. No se guarda, para reintentar.
            log_exception(error)
            return StageError(UNEXPECTED_ERROR_MESSAGE, [])
    return cache[cache_key]


def show_analysis(uploaded, analysis) -> bool:
    """Debajo del cargador: la información calculada o, si no pasó la validación, el error.

    La información va en verde si la etapa no encontró diferencias (por ejemplo, los totales
    coinciden con el reporte ETY) y en rojo si las encontró; en ese caso la primera línea
    describe la diferencia y se resalta. El detalle de lo que se hizo va
    al log de carga (pestañas de abajo). Devuelve si el archivo es válido: las diferencias se
    revisan, pero no impiden procesar.
    """
    if isinstance(analysis, StageError):
        add_to_load_log(analysis.steps)
        problems = "\n".join(f"- {p}" for p in analysis.problems)
        st.error(f"{analysis.message}\n\n{problems}\n\nCorrija el archivo y vuelva a cargarlo.")
        return False
    add_to_load_log(analysis.audit.step_lines(), analysis.audit.actions_df())
    # «$» se escapa: en Markdown, dos signos de pesos en un texto se toman como una fórmula.
    lines = [line.replace("$", "\\$") for line in analysis.summary]
    if analysis.ok:
        details = "\n".join(bullet(line) for line in lines)
        st.success(f"«{uploaded.name}» pasó la validación.\n\n{details}", icon=":material/check_circle:")
    else:
        headline, *rest = lines
        details = "\n".join(bullet(line) for line in rest)
        st.error(f"**{headline}**\n\n{details}", icon=":material/error:")
    return True


def bullet(line: str) -> str:
    """Elemento de lista en Markdown. Las líneas que empiezan con dos espacios van dentro de la anterior."""
    return f"    - {line.strip()}" if line.startswith("  ") else f"- {line}"


def show_load_log() -> None:
    """Pestañas con lo que se hizo al cargar los archivos, igual que los resultados de Procesar."""
    st.caption("Lo que se hizo al cargar los archivos. Al procesar, se reemplaza por el log completo.")
    tab_log, tab_actions = st.tabs(["Log de ejecución", "Acciones realizadas"])
    with tab_log:
        show_step_log(st.empty(), load_log["lines"])
    with tab_actions:
        tables = load_log["actions"]
        show_actions(pd.concat(tables, ignore_index=True) if tables else pd.DataFrame())


def date_uploaders(spec) -> tuple[dict, bool]:
    """Un cargador por cada fecha de la entrada de origen (por ejemplo, FECHA DE PAGO del ETY).

    Cada archivo se valida y analiza apenas se carga: debajo de su cargador aparece la
    información calculada (o el error) y el detalle va al log de carga. Devuelve
    {fecha: archivo} y si ya está todo lo necesario para procesar: las fechas se conocen
    (el archivo de origen está cargado y es válido), ningún archivo tiene errores y, si la
    entrada es obligatoria, hay uno por cada fecha.

    Los archivos se guardan por fecha (saved_reports) y no en el cargador: si el usuario
    corrige el reporte de origen y lo vuelve a cargar, las fechas que ya tenían archivo lo
    conservan y se vuelven a analizar contra el reporte nuevo. Streamlit borra lo que tiene
    un cargador cuando deja de mostrarse (por ejemplo, mientras se quita el reporte), así
    que el cargador solo sirve para recibir el archivo.
    """
    source_key, column = spec.per_date
    source = next(s for s in input_specs(stage) if s.key == source_key)
    if not files[source_key]:
        st.markdown(f"**{spec.label}**")
        st.caption(f"Cargue primero «{source.label}»: aquí aparecerá un campo por cada fecha de {column}.")
        return {}, False
    sources = load_dates(files[source_key])
    if isinstance(sources, StageError):
        # Sin título: el error es del archivo de origen y se ve justo debajo de su cargador.
        problems = "\n".join(f"- {p}" for p in sources.problems)
        st.error(f"{sources.message}\n\n{problems}\n\nCorrija el archivo y vuelva a cargarlo.")
        return {}, False
    st.markdown(f"**{spec.label}**")
    days = sources.dates.get(spec.key, [])
    if not days:
        st.info(f"La columna {column} no tiene fechas: no se necesita ningún archivo.")
        return {}, True
    st.caption(f"Cargue un solo archivo .xlsx por cada fecha de {column} ({len(days)} en total).")
    loaded = {}
    all_valid = True
    for day in days:
        saved = saved_file_input(spec, day)
        if saved is not None:
            loaded[day] = saved
            # Un archivo con errores bloquea Procesar: el procesamiento se detendría por lo mismo.
            all_valid = show_analysis(saved, load_analysis(spec, sources, day, saved)) and all_valid
    return loaded, all_valid and (len(loaded) == len(days) or not spec.required)


def saved_file_input(spec, day):
    """Campo de una fecha: el archivo guardado con un botón para quitarlo o, si no hay, el cargador.

    Al cargar un archivo se guarda en memoria y la página se vuelve a mostrar con él. Para
    reemplazarlo se quita y se carga otro. Devuelve el archivo listo para leer, o None.
    """
    store_key = (stage_index, spec.key, day)
    saved = st.session_state.saved_reports.get(store_key)
    if saved is None:
        uploaded = st.file_uploader(
            date_label(spec, day),
            type=["xlsx"],
            key=f"upload_{stage_index}_{spec.key}_{day.isoformat()}_{st.session_state.uploader_version}",
        )
        if uploaded is None:
            return None
        st.session_state.saved_reports[store_key] = SavedFile(
            uploaded.name, uploaded.getvalue(), getattr(uploaded, "file_id", uploaded.name)
        )
        st.rerun()
    st.markdown(date_label(spec, day))
    row = st.container(horizontal=True, vertical_alignment="center")
    row.markdown(f":material/description: «{saved.name}»")
    row.button(
        "Quitar", icon=":material/close:", key=f"remove_{stage_index}_{spec.key}_{day.isoformat()}",
        on_click=st.session_state.saved_reports.pop, args=(store_key, None),
    )
    file = BytesIO(saved.data)
    file.name = saved.name
    file.file_id = saved.file_id
    return file


files = {}
# Entradas por fecha que todavía no tienen lo necesario para procesar.
incomplete_date_inputs = []
for spec in input_specs(stage):
    if spec.per_date:
        files[spec.key], complete = date_uploaders(spec)
        if not complete:
            incomplete_date_inputs.append(spec.key)
        continue
    label = spec.label if spec.required else f"{spec.label} (opcional)"
    uploaded = st.file_uploader(
        label,
        type=["xlsx"],
        accept_multiple_files=spec.multiple,
        key=f"upload_{stage_index}_{spec.key}_{st.session_state.uploader_version}",
    )
    # Los textos del cargador de Streamlit están en plural y no se pueden cambiar; esto los aclara.
    st.caption("Puede cargar varios archivos .xlsx." if spec.multiple else "Cargue un solo archivo .xlsx.")
    if spec.multiple:
        files[spec.key] = list(uploaded or [])
    else:
        files[spec.key] = [uploaded] if uploaded is not None else []
    for warning in file_name_warnings(spec, files[spec.key]):
        st.warning(warning, icon=":material/warning:")

missing_required = bool(incomplete_date_inputs) or any(
    spec.required and not files[spec.key] for spec in input_specs(stage) if not spec.per_date
)
uploaded_count = sum(len(f) for f in files.values())


# Fila de botones: Procesar y, cuando hay resultados, las descargas y «Nuevo procesamiento».
buttons_row = st.container(horizontal=True)

if buttons_row.button("Procesar", type="primary", icon=":material/play_arrow:", disabled=missing_required):
    st.session_state.result = None
    # Espacio para el mensaje de error, justo debajo del botón (como el mensaje de éxito).
    message_area = st.empty()
    # Log en vivo, siempre visible. Al terminar se vacía: los resultados (abajo) lo vuelven a mostrar.
    # Si el proceso se detiene, queda en pantalla para ver en qué paso falló.
    log_placeholder = st.empty()
    lines: list[str] = []

    def show_line(line: str) -> None:
        lines.append(line)
        show_step_log(log_placeholder, lines)

    try:
        with st.spinner("Procesando…"):
            result = run_stage(stage, files, progress=show_line)
            st.session_state.saved_paths = save_result(result)
        st.session_state.result = result
        st.session_state.result_stage = stage_index
        log_placeholder.empty()
    except StageError as error:
        problems = "\n".join(f"- {p}" for p in error.problems)
        fix = "Corrija el archivo y vuelva a cargarlo." if uploaded_count == 1 else "Corrija los archivos y vuelva a cargarlos."
        message_area.error(f"{error.message}\n\n{problems}\n\n{fix}")
    except Exception as error:
        log_exception(error)
        message_area.error(UNEXPECTED_ERROR_MESSAGE)

# --- Resultados ------------------------------------------------------------


def show_results(result, saved_paths, buttons_row) -> None:
    """Muestra los botones de descarga junto a Procesar, el log de ejecución, la tabla de
    acciones y la ruta de la copia guardada."""
    buttons_row.download_button(
        "Descargar archivo procesado",
        data=result.output_bytes,
        file_name=result.output_file_name,
        mime=XLSX_MIME,
        icon=":material/download:",
        key="download_output",
    )
    buttons_row.download_button(
        "Descargar log",
        data=result.log_bytes,
        file_name=result.log_file_name,
        mime=XLSX_MIME,
        icon=":material/download:",
        key="download_log",
    )
    buttons_row.button("Nuevo procesamiento", icon=":material/restart_alt:", on_click=reset)

    st.success("Procesamiento terminado. Revise el log antes de pasar a la siguiente etapa.")

    tab_log, tab_actions = st.tabs(["Log de ejecución", "Acciones realizadas"])
    with tab_log:
        show_step_log(st.empty(), result.audit.step_lines())
    with tab_actions:
        show_actions(result.audit.actions_df())

    output_path, log_path = saved_paths
    st.caption(f"Copia guardada en: {output_path.parent}")


result = st.session_state.result
if (result is None or st.session_state.result_stage != stage_index) and load_log["lines"]:
    show_load_log()
if result is not None and st.session_state.result_stage == stage_index:
    try:
        show_results(result, st.session_state.saved_paths, buttons_row)
    except Exception as error:
        # Nunca mostrar un traceback: el detalle queda en errores.log.
        log_exception(error)
        st.error(
            "Ocurrió un error inesperado al mostrar los resultados. "
            "Presione «Nuevo procesamiento» y procese de nuevo. Si el error se repite, "
            "cierre la herramienta, vuelva a abrirla y comparta el archivo 'errores.log' "
            "con la persona que mantiene la herramienta."
        )
        buttons_row.button(
            "Nuevo procesamiento", icon=":material/restart_alt:", on_click=reset, key="reset_after_error"
        )
