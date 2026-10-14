"""Interfaz principal (Streamlit). No contiene reglas de negocio: solo recibe
archivos, llama al ejecutor y muestra o entrega los resultados.

Ejecutar con: uv run streamlit run app.py
"""

import streamlit as st

from core.errors import UNEXPECTED_ERROR_MESSAGE, log_exception
from core.runner import StageError, run_stage, save_result
from core.settings import APP_NAME, APP_VERSION, ERROR, INFO, WARNING
from core.stage import input_specs
from stages import STAGES

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.set_page_config(page_title=APP_NAME, layout="wide")

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

stage_index = st.sidebar.selectbox(
    "Etapa",
    options=range(len(STAGES)),
    format_func=lambda i: STAGES[i].NAME,
    on_change=reset,
)
stage = STAGES[stage_index]

# --- Etapa y carga de archivos ---------------------------------------------

st.title(stage.NAME)
st.write(stage.DESCRIPTION)

files = {}
for spec in input_specs(stage):
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

missing_required = any(spec.required and not files[spec.key] for spec in input_specs(stage))
single_file_stage = len(input_specs(stage)) == 1 and not input_specs(stage)[0].multiple
uploaded_count = sum(len(f) for f in files.values())

if st.button("Procesar", type="primary", disabled=missing_required):
    st.session_state.result = None
    progress_bar = st.progress(0, text="Iniciando…")

    def show_progress(step: int, total: int, text: str) -> None:
        progress_bar.progress(step / total, text=f"Paso {step} de {total}: {text}")

    try:
        result = run_stage(stage, files, progress=show_progress)
        st.session_state.saved_paths = save_result(result)
        st.session_state.result = result
        st.session_state.result_stage = stage_index
        progress_bar.progress(1.0, text="Procesamiento terminado")
    except StageError as error:
        progress_bar.empty()
        problems = "\n".join(f"- {p}" for p in error.problems)
        fix = "Corrija el archivo y vuelva a cargarlo." if uploaded_count == 1 else "Corrija los archivos y vuelva a cargarlos."
        st.error(f"{error.message}\n\n{problems}\n\n{fix}")
    except Exception as error:
        progress_bar.empty()
        log_exception(error)
        st.error(UNEXPECTED_ERROR_MESSAGE)

if missing_required and st.session_state.result is None:
    if single_file_stage:
        st.caption("Cargue el archivo para habilitar el botón Procesar.")
    else:
        st.caption("Cargue todos los archivos obligatorios para habilitar el botón Procesar.")

# --- Resultados ------------------------------------------------------------


def show_results(result, saved_paths) -> None:
    """Muestra métricas, tablas del log, botones de descarga y la ruta de la copia guardada."""
    summary = result.summary
    st.success("Procesamiento terminado. Revise el log antes de pasar a la siguiente etapa.")

    columns = st.columns(4)
    columns[0].metric("Registros leídos", summary.rows_read)
    columns[1].metric("Registros en salida", summary.rows_output)
    columns[2].metric("Registros eliminados", summary.rows_removed)
    columns[3].metric("Celdas modificadas", summary.cells_changed)
    columns = st.columns(3)
    columns[0].metric("Hallazgos: Error", summary.findings_by_severity[ERROR])
    columns[1].metric("Hallazgos: Advertencia", summary.findings_by_severity[WARNING])
    columns[2].metric("Hallazgos: Información", summary.findings_by_severity[INFO])
    if summary.title_rows_removed:
        st.caption(
            f"Además se quitaron {summary.title_rows_removed} filas de título del reporte "
            "(anteriores a los encabezados). Se pueden ver en la pestaña Eliminados."
        )

    tab_findings, tab_changes, tab_removals = st.tabs(["Hallazgos", "Cambios", "Eliminados"])
    for tab, table in [
        (tab_findings, result.audit.findings_df()),
        (tab_changes, result.audit.changes_df()),
        (tab_removals, result.audit.removals_df()),
    ]:
        with tab:
            if table.empty:
                st.write("No hay registros.")
            else:
                st.dataframe(table.astype(str), hide_index=True, width="stretch")

    columns = st.columns(2)
    columns[0].download_button(
        "Descargar archivo procesado",
        data=result.output_bytes,
        file_name=result.output_file_name,
        mime=XLSX_MIME,
    )
    columns[1].download_button(
        "Descargar log",
        data=result.log_bytes,
        file_name=result.log_file_name,
        mime=XLSX_MIME,
    )

    output_path, log_path = saved_paths
    st.caption(f"Copia guardada en: {output_path.parent}")

    st.button("Nuevo procesamiento", on_click=reset)


result = st.session_state.result
if result is not None and st.session_state.result_stage == stage_index:
    try:
        show_results(result, st.session_state.saved_paths)
    except Exception as error:
        # Nunca mostrar un traceback: el detalle queda en errores.log.
        log_exception(error)
        st.error(
            "Ocurrió un error inesperado al mostrar los resultados. "
            "Presione «Nuevo procesamiento» y procese de nuevo. Si el error se repite, "
            "cierre la herramienta, vuelva a abrirla y comparta el archivo 'errores.log' "
            "con la persona que mantiene la herramienta."
        )
        st.button("Nuevo procesamiento", on_click=reset, key="reset_after_error")
