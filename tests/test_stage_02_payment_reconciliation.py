"""Etapa 2: carga del archivo procesado en la Etapa 1 y de los informes de pago, con datos inventados."""

from datetime import date, datetime
from io import BytesIO

import pytest
from openpyxl import load_workbook

from core.runner import StageError, input_dates, run_stage
from core.stage import applied_rules
from stages import STAGES, stage_01_ety_cleaning, stage_02_payment_reconciliation
from tests.helpers import make_xlsx
from tests.test_stage_01_ety_cleaning import COLUMNS, OUTPUT_COLUMNS, ROW, distinct, ety_file


def stage_1_output(rows=distinct(ROW, ROW)):
    """Archivo procesado en la Etapa 1, tal como lo descarga el usuario."""
    result = run_stage(stage_01_ety_cleaning, {"ety_report": [ety_file(rows=rows, name="ETY_sept.xlsx")]})
    file = BytesIO(result.output_bytes)
    file.name = result.output_file_name
    return file


# Fecha de pago de ROW (28/09/2026), sin la hora.
PAYMENT_DAY = date(2026, 9, 28)


def treasury_report(name="tesoreria_28.xlsx"):
    """Informe de pago de Tesorería. Su estructura todavía no está especificada."""
    return make_xlsx([["Columna"], ["valor"]], name=name)


def with_date(row, value):
    row = list(row)
    row[COLUMNS.index("FECHA DE PAGO")] = value
    return row


def run(*files, treasury=None):
    if treasury is None:
        treasury = {PAYMENT_DAY: treasury_report()}
    return run_stage(stage_02_payment_reconciliation, {"ety_processed": list(files), "treasury_reports": treasury})


def test_stage_2_is_registered_after_stage_1():
    assert STAGES[:2] == [stage_01_ety_cleaning, stage_02_payment_reconciliation]


def test_expected_columns_are_the_stage_1_output():
    assert list(stage_02_payment_reconciliation.INPUTS["ety_processed"]["columns"]) == OUTPUT_COLUMNS


def test_stage_1_output_is_accepted():
    result = run(stage_1_output())
    assert result.summary.rows_read == 2 and result.summary.rows_output == 2
    assert result.output_file_name == "ETY_sept_E02_procesado.xlsx"
    sheet = load_workbook(BytesIO(result.output_bytes)).active
    assert sheet.title == "sheet1" and [c.value for c in sheet[1]] == OUTPUT_COLUMNS


def test_original_report_is_rejected():
    # El reporte sin procesar (títulos en las filas 1 a 3, sin Diferencia) no corresponde a esta etapa.
    with pytest.raises(StageError) as error:
        run(ety_file())
    assert any("EST-003" in p for p in error.value.problems)


def test_columns_out_of_order_are_rejected():
    columns = list(OUTPUT_COLUMNS)
    columns[0], columns[1] = columns[1], columns[0]
    with pytest.raises(StageError) as error:
        run(make_xlsx([columns, [None] * len(columns)], sheet="sheet1"))
    assert any("EST-008" in p for p in error.value.problems)


def test_only_one_file_allowed():
    with pytest.raises(StageError) as error:
        run(stage_1_output(), stage_1_output())
    assert any("EST-007" in p and "un solo archivo" in p for p in error.value.problems)


def test_applied_rules_are_structure_rules():
    codes = [code for code, _ in applied_rules(stage_02_payment_reconciliation)]
    assert codes == ["EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008"]


def test_payment_dates_are_unique_sorted_and_ignore_empty_cells():
    rows = distinct(
        with_date(ROW, datetime(2026, 9, 30)), ROW, with_date(ROW, datetime(2026, 9, 28, 15, 0)),
        with_date(ROW, None),
    )
    dates = input_dates(stage_02_payment_reconciliation, {"ety_processed": [stage_1_output(rows)]})
    assert dates == {"treasury_reports": [date(2026, 9, 28), date(2026, 9, 30)]}


def test_payment_dates_need_the_ety_report():
    assert input_dates(stage_02_payment_reconciliation, {"ety_processed": []}) == {}


def test_payment_dates_validate_the_ety_report_structure():
    with pytest.raises(StageError) as error:
        input_dates(stage_02_payment_reconciliation, {"ety_processed": [ety_file()]})
    assert any("EST-003" in p for p in error.value.problems)


def test_one_treasury_report_per_date_is_logged():
    result = run(stage_1_output())
    steps = {step.title: step.details for step in result.audit.steps}
    assert steps["Verificando: Informe de pago, uno por fecha"] == ["✓ 28/09/2026: tesoreria_28.xlsx"]
    assert "Abriendo «tesoreria_28.xlsx» (Informe de pago del 28 de septiembre de 2026)" in steps
    # La salida conserva el nombre del reporte ETY, aunque se hayan cargado varios archivos.
    assert result.output_file_name == "ETY_sept_E02_procesado.xlsx"


def test_missing_treasury_report_stops_processing():
    rows = distinct(ROW, with_date(ROW, datetime(2026, 9, 29)))
    with pytest.raises(StageError) as error:
        run(stage_1_output(rows))
    assert error.value.problems == ["[EST-007] Falta cargar: Informe de pago del 29 de septiembre de 2026."]


def test_treasury_report_for_a_date_not_in_the_ety_report_is_rejected():
    treasury = {PAYMENT_DAY: treasury_report(), date(2026, 9, 1): treasury_report("otro.xlsx")}
    with pytest.raises(StageError) as error:
        run(stage_1_output(), treasury=treasury)
    assert any("EST-007" in p and "otro.xlsx" in p and "1 de septiembre de 2026" in p for p in error.value.problems)


def test_treasury_report_that_is_not_xlsx_is_rejected():
    file = BytesIO(b"no es un excel")
    file.name = "tesoreria.xlsx"
    with pytest.raises(StageError) as error:
        run(stage_1_output(), treasury={PAYMENT_DAY: file})
    assert any("EST-001" in p and "tesoreria.xlsx" in p for p in error.value.problems)
