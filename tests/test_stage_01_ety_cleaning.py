"""Etapa 1: validación de estructura del reporte ETY, con datos inventados."""

from datetime import datetime
from io import BytesIO

import pytest
from openpyxl import load_workbook

from core.runner import StageError, run_stage
from stages import stage_01_ety_cleaning
from tests.helpers import make_xlsx

COLUMNS = list(stage_01_ety_cleaning.INPUTS["ety_report"]["columns"])
# Columnas del archivo de salida: las del reporte más Diferencia a la derecha de Importe (K).
OUTPUT_COLUMNS = [*COLUMNS[:10], "Diferencia", *COLUMNS[10:]]

ROW = [
    "0010000001", "12345678", "PERSONA DE PRUEBA", datetime(2026, 9, 28, 2, 0), 1000000, 0, 0,
    5000, 0, 995000, "AP00000001", "Cuentas a Pagar", 1, "00000001", "Pago Estándar",
    "CE0000000001", "DS_PRUEBA", "20025", "23-26", "1002", "4147", "2", "100212", "0002",
]


TITLE_ROWS = [
    ["Todos Pagos X Comprobante", " 1"],
    ["De Fecha = 2026-09-28"],
    ["A Fecha = 2026-09-30"],
]


def ety_file(header=COLUMNS, rows=(ROW,), sheet="sheet1", titles=TITLE_ROWS, name="ety.xlsx"):
    return make_xlsx([*titles, list(header), *[list(r) for r in rows]], sheet=sheet, name=name)


def run(*files):
    return run_stage(stage_01_ety_cleaning, {"ety_report": list(files)})


def stage_error(*files) -> StageError:
    with pytest.raises(StageError) as error:
        run(*files)
    return error.value


def problems_for(*files) -> list[str]:
    return stage_error(*files).problems


def test_messages_speak_of_a_single_file():
    error = stage_error(ety_file(titles=[]))
    assert error.message == "La estructura del archivo no es la esperada."


def test_valid_report_is_processed():
    result = run(ety_file(rows=(ROW, ROW)))
    assert result.summary.rows_read == 2
    assert result.output_file_name.startswith("E01_ety_cleaning_procesado_")


def test_header_spaces_are_tolerated():
    header = [f" {c} " for c in COLUMNS]
    assert run(ety_file(header=header)).summary.rows_read == 1


def test_any_sheet_name_is_accepted():
    assert run(ety_file(sheet="Hoja1")).summary.rows_read == 1


def test_column_order_is_validated():
    header = list(COLUMNS)
    header[4], header[5] = header[5], header[4]  # VR. BRUTO <-> VR. RTEFTE
    problems = problems_for(ety_file(header=header))
    assert len(problems) == 1
    assert "EST-008" in problems[0] and "posición 5" in problems[0] and "'VR. BRUTO'" in problems[0]


def test_missing_column():
    header = [c for c in COLUMNS if c != "Importe"]
    row = [v for c, v in zip(COLUMNS, ROW) if c != "Importe"]
    problems = problems_for(ety_file(header=header, rows=(row,)))
    assert any("EST-003" in p and "'Importe'" in p for p in problems)


def test_extra_column():
    problems = problems_for(ety_file(header=[*COLUMNS, "Otra"], rows=([*ROW, "x"],)))
    assert any("EST-004" in p and "'Otra'" in p for p in problems)


def test_title_rows_removed():
    problems = problems_for(ety_file(titles=[]))
    assert len(problems) == 1 and "están en la fila 1" in problems[0]


def test_only_one_file_allowed():
    problems = problems_for(ety_file(name="a.xlsx"), ety_file(name="b.xlsx"))
    assert any("EST-007" in p and "un solo archivo" in p for p in problems)


def test_title_rows_are_removed_and_logged():
    result = run(ety_file(rows=(ROW, ROW)))
    summary = result.summary
    assert summary.rows_output == 2
    assert summary.rows_removed == 0          # Las filas de título no son registros
    assert summary.title_rows_removed == 3

    removals = result.audit.removals_df()
    assert list(removals["Fila origen"]) == [1, 2, 3]
    assert set(removals["Código de regla"]) == {"LIM-003"}
    assert removals.iloc[0]["Beneficiario Pago"] == "Todos Pagos X Comprobante"  # Columna A
    assert removals.iloc[0]["Identificación"] == " 1"                            # Columna B

    sheet = load_workbook(BytesIO(result.output_bytes)).active
    assert [c.value for c in sheet[1]] == OUTPUT_COLUMNS  # La salida empieza con los encabezados
    assert sheet["A2"].value == ROW[0]


CURRENCY_COLUMNS = ["VR. BRUTO", "VR. RTEFTE", "VR. RETEIVA", "VR. RETEICA", "VR. TASAS", "Importe"]


def test_columns_e_to_j_are_currency():
    assert COLUMNS[4:10] == CURRENCY_COLUMNS  # Columnas E a J del reporte


def test_currency_columns_are_converted_and_formatted():
    row = list(ROW)
    row[COLUMNS.index("VR. BRUTO")] = "$ 1.000.000"   # Texto con formato colombiano
    row[COLUMNS.index("Importe")] = "995000"          # Texto con un número simple
    result = run(ety_file(rows=(ROW, row)))

    sheet = load_workbook(BytesIO(result.output_bytes)).active
    for letter in "EFGHIJ":
        for number in (2, 3):
            cell = sheet[f"{letter}{number}"]
            assert isinstance(cell.value, (int, float)), cell.coordinate  # Excel guarda 1000000.0 como 1000000
            assert cell.number_format == '"$" #,##0.00', cell.coordinate
    assert sheet["E3"].value == 1000000.0
    assert sheet["D2"].number_format != '"$" #,##0.00'  # La fecha no es moneda

    # Solo se registra el cambio cuyo valor visible cambió.
    changes = [(c.source_row, c.column, c.old_value, c.new_value) for c in result.audit.changes]
    assert changes == [(6, "VR. BRUTO", "$ 1.000.000", 1000000.0)]
    assert result.audit.changes[0].rule == "TIP-005"


def test_invalid_currency_value_is_reported():
    row = list(ROW)
    row[COLUMNS.index("VR. RTEFTE")] = "sin valor"
    result = run(ety_file(rows=(row,)))

    findings = [(f.source_row, f.column, f.severity, f.rule) for f in result.audit.findings]
    assert findings == [(5, "VR. RTEFTE", "Error", "TIP-005")]
    sheet = load_workbook(BytesIO(result.output_bytes)).active
    assert sheet["F2"].value == "sin valor"           # Se conserva el valor original
    assert sheet["F2"].fill.fill_type == "solid"      # Resaltado como error



def with_description(description):
    row = list(ROW)
    row[COLUMNS.index("Descripción")] = description
    return row


def test_cash_distribution_rows_are_removed_and_logged():
    rows = (
        with_description("Cuentas a Pagar"),
        with_description("Distribución Caja"),
        with_description(" distribucion  CAJA "),   # Variación de escritura
        with_description("Cuentas a Pagar"),
    )
    result = run(ety_file(rows=rows))

    assert result.summary.rows_read == 4
    assert result.summary.rows_output == 2
    assert result.summary.rows_removed == 2

    removed = [r for r in result.audit.removals if r.rule == "LIM-101"]
    assert [r.source_row for r in removed] == [6, 7]
    assert removed[0].reason == "Descripción «Distribución Caja»"
    assert removed[0].row_data["Beneficiario Pago"] == ROW[0]  # Se guarda el registro completo

    sheet = load_workbook(BytesIO(result.output_bytes)).active
    descriptions = [sheet[f"M{r}"].value for r in range(2, sheet.max_row + 1)]  # L se corrió a M
    assert descriptions == ["Cuentas a Pagar", "Cuentas a Pagar"]



def test_difference_column_has_formula_right_of_importe():
    rows = (with_description("Distribución Caja"), ROW, ROW)
    result = run(ety_file(rows=rows))

    sheet = load_workbook(BytesIO(result.output_bytes)).active
    assert sheet["J1"].value == "Importe" and sheet["K1"].value == "Diferencia"
    assert sheet["L1"].value == "Asiento"
    # La fila de Distribución Caja se eliminó: las fórmulas usan la fila de salida.
    assert sheet["K2"].value == "=E2-F2-G2-H2-I2-J2"
    assert sheet["K3"].value == "=E3-F3-G3-H3-I3-J3"
    assert sheet["K2"].number_format == '"$" #,##0.00'

    added = result.audit.added_columns
    assert [(a.column, a.rule, a.rows) for a in added] == [("Diferencia", "TRA-101", 2)]
    assert result.summary.cells_changed == 0  # La columna nueva no cuenta como celdas modificadas

    summary = load_workbook(BytesIO(result.log_bytes))["Resumen"]
    sections = [row for row in summary.iter_rows(values_only=True) if row[0] == "Columnas agregadas"]
    assert len(sections) == 1 and sections[0][1].startswith("Diferencia (TRA-101") and sections[0][2] == "2 filas"
