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


# Encabezados de la hoja Pagos del informe de Tesorería (las primeras columnas y «Nº Cuenta»,
# que viene repetida en el informe real).
PAYMENT_COLUMNS = ["F Ejec", "UN", "NEGOCIO", "Nº Cuenta", "Comprobante", "Nº Cuenta"]


def payment(day=datetime(2026, 9, 28, 2, 0), unit="AP656"):
    """Registro de la hoja Pagos: la F Ejec trae hora, como en el informe real."""
    return [day, unit, "NEGOCIOS", "001", "00153417", "002"]


def treasury_report(name="tesoreria_28.xlsx", payments=None):
    """Informe de pago de Tesorería: RESUMEN en la primera hoja y los pagos en la hoja Pagos."""
    if payments is None:
        payments = [payment(), payment(unit="AP198"), payment(day=datetime(2026, 9, 29), unit="AP198")]
    return make_xlsx(
        [["CICLO DE PAGOS"], ["NEGOCIOS"]], sheet="RESUMEN", name=name,
        extra_sheets={"Pagos": [PAYMENT_COLUMNS, *payments]},
    )


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
    # Se leen los 2 registros del ETY y los 3 de la hoja Pagos del informe; la salida es el ETY.
    assert result.summary.rows_read == 5 and result.summary.rows_output == 2
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


def test_applied_rules():
    codes = [code for code, _ in applied_rules(stage_02_payment_reconciliation)]
    assert codes == [
        "EST-007", "EST-001", "EST-002", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",
        "LIM-201", "VAL-201",
    ]


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


def test_treasury_report_without_payments_sheet_is_rejected():
    with pytest.raises(StageError) as error:
        run(stage_1_output(), treasury={PAYMENT_DAY: make_xlsx([["F Ejec", "UN"]], name="t.xlsx")})
    assert any("EST-002" in p and "'Pagos'" in p for p in error.value.problems)


def test_treasury_report_needs_execution_date_and_business_unit():
    file = make_xlsx([["x"]], sheet="RESUMEN", name="t.xlsx", extra_sheets={"Pagos": [["F Ejec", "Otra"]]})
    with pytest.raises(StageError) as error:
        run(stage_1_output(), treasury={PAYMENT_DAY: file})
    assert any("EST-003" in p and "'UN'" in p for p in error.value.problems)


def test_only_business_unit_ap656_is_checked():
    # Los pagos de otras unidades (AP198 del 29/09) no se validan: solo se cuentan.
    result = run(stage_1_output())
    steps = {step.title: step.details for step in result.audit.steps}
    assert steps["Tomando de los informes de pago los registros con UN AP656"] == [
        "✓ tesoreria_28.xlsx: 1 de 3 registros con UN AP656"
    ]
    assert steps["Verificando que la F Ejec corresponda a la fecha de cada informe"] == [
        "✓ tesoreria_28.xlsx: 1 registros del 28/09/2026"
    ]
    # Filtrar el informe no cambia el reporte ETY ni deja acciones en el log.
    assert result.summary.rows_output == 2 and result.audit.actions == []


def test_business_unit_ignores_case_and_spaces():
    report = treasury_report(payments=[payment(unit=" ap656 ")])
    result = run(stage_1_output(), treasury={PAYMENT_DAY: report})
    steps = {step.title: step.details for step in result.audit.steps}
    assert steps["Tomando de los informes de pago los registros con UN AP656"] == [
        "✓ tesoreria_28.xlsx: 1 de 1 registros con UN AP656"
    ]


def test_execution_date_different_from_the_loaded_date_stops_processing():
    # Informe del 29/09 cargado en el campo del 28/09.
    payments = [payment(datetime(2026, 9, 29, 2, 0)), payment(), payment(None), payment(datetime(2026, 9, 29))]
    with pytest.raises(StageError) as error:
        run(stage_1_output(), treasury={PAYMENT_DAY: treasury_report(payments=payments)})
    assert error.value.message == "La F Ejec de 1 informe de pago no coincide con la fecha del campo donde se cargó."
    assert error.value.problems == [
        "[VAL-201] «tesoreria_28.xlsx» se cargó como informe del 28/09/2026, pero 3 de sus 4 registros "
        "con UN AP656 tienen otra F Ejec: 29/09/2026 en 2 registros (filas 2, 5); vacía o no válida en "
        "1 registro (fila 4). Verifique que cargó el informe en el campo de su fecha."
    ]
    assert "▸ Verificando que la F Ejec corresponda a la fecha de cada informe" in error.value.steps


def test_each_treasury_report_is_checked_against_its_own_date():
    rows = distinct(ROW, with_date(ROW, datetime(2026, 9, 29)))
    treasury = {
        PAYMENT_DAY: treasury_report(),
        date(2026, 9, 29): treasury_report("tesoreria_29.xlsx", [payment(datetime(2026, 9, 28))] * 12),
    }
    with pytest.raises(StageError) as error:
        run(stage_1_output(rows), treasury=treasury)
    assert len(error.value.problems) == 1
    problem = error.value.problems[0]
    assert "«tesoreria_29.xlsx» se cargó como informe del 29/09/2026" in problem
    assert "(filas 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 y 2 más)" in problem
