"""Interfaz principal (Streamlit). No contiene reglas de negocio: solo recibe
archivos, llama al ejecutor y muestra o entrega los resultados.

Ejecutar con: uv run streamlit run app.py
"""

import streamlit as st

from core.errors import UNEXPECTED_ERROR_MESSAGE, log_exception
from core.runner import StageError, input_dates, run_stage, save_result
from core.settings import APP_NAME, APP_VERSION, DOWNLOAD_BUTTON_COLOR, DOWNLOAD_BUTTON_HOVER_COLOR
from core.stage import applied_rules, date_label, input_specs
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


def reset() -> None:
    """Limpia los resultados y los archivos cargados para empezar de nuevo."""
    st.session_state.result = None
    st.session_state.saved_paths = None
    st.session_state.result_stage = None
    st.session_state.uploader_version += 1


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

def load_dates(source_files: list) -> dict | StageError:
    """Fechas de las entradas por fecha (o el error de estructura del archivo de origen).

    Se guardan en session_state por archivo cargado: Streamlit vuelve a ejecutar la página
    con cada archivo que se carga y así el reporte no se lee una y otra vez.
    """
    cache_key = (stage_index, tuple(getattr(f, "file_id", f.name) for f in source_files))
    cache = st.session_state.setdefault("dates_cache", {})
    if cache_key not in cache:
        try:
            cache[cache_key] = input_dates(stage, files)
        except StageError as error:
            cache[cache_key] = error
        except Exception as error:
            # Nunca mostrar un traceback: el detalle queda en errores.log. No se guarda, para reintentar.
            log_exception(error)
            return StageError(UNEXPECTED_ERROR_MESSAGE, [])
    return cache[cache_key]


def date_uploaders(spec) -> tuple[dict, bool]:
    """Un cargador por cada fecha de la entrada de origen (por ejemplo, FECHA DE PAGO del ETY).

    Devuelve {fecha: archivo cargado} y si ya está todo lo necesario para procesar: las
    fechas se conocen (el archivo de origen está cargado y es válido) y, si la entrada es
    obligatoria, hay un archivo por cada fecha.
    """
    source_key, column = spec.per_date
    source = next(s for s in input_specs(stage) if s.key == source_key)
    if not files[source_key]:
        st.markdown(f"**{spec.label}**")
        st.caption(f"Cargue primero «{source.label}»: aquí aparecerá un campo por cada fecha de {column}.")
        return {}, False
    dates = load_dates(files[source_key])
    if isinstance(dates, StageError):
        # Sin título: el error es del archivo de origen y se ve justo debajo de su cargador.
        problems = "\n".join(f"- {p}" for p in dates.problems)
        st.error(f"{dates.message}\n\n{problems}\n\nCorrija el archivo y vuelva a cargarlo.")
        return {}, False
    st.markdown(f"**{spec.label}**")
    days = dates.get(spec.key, [])
    if not days:
        st.info(f"La columna {column} no tiene fechas: no se necesita ningún archivo.")
        return {}, True
    st.caption(f"Cargue un solo archivo .xlsx por cada fecha de {column} ({len(days)} en total).")
    loaded = {}
    for day in days:
        uploaded = st.file_uploader(
            date_label(spec, day),
            type=["xlsx"],
            # La fecha va en la llave: si se cambia el reporte, se conservan los archivos de las fechas que siguen.
            key=f"upload_{stage_index}_{spec.key}_{day.isoformat()}_{st.session_state.uploader_version}",
        )
        if uploaded is not None:
            loaded[day] = uploaded
    return loaded, len(loaded) == len(days) or not spec.required


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

missing_required = bool(incomplete_date_inputs) or any(
    spec.required and not files[spec.key] for spec in input_specs(stage) if not spec.per_date
)
uploaded_count = sum(len(f) for f in files.values())


def show_step_log(placeholder, lines: list[str]) -> None:
    """Muestra el log de ejecución como un bloque de texto, una línea por paso y resultado."""
    placeholder.code("\n".join(lines), language=None)


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


def show_actions(actions) -> None:
    """Tabla con todo lo que se hizo, en el orden en que ocurrió."""
    if actions.empty:
        st.write("No se hizo ningún cambio, eliminación ni hallazgo.")
        return
    st.caption(f"{len(actions)} acciones, en el orden en que se hicieron.")
    # Las celdas vacías se muestran en blanco, no como "None".
    st.dataframe(actions.fillna("").astype(str), hide_index=True, width="stretch")


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
